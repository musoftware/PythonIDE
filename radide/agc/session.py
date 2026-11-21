"""F5 / Ctrl+F5 for Apollo AGC projects.

* ``AgcSession`` - RAD IDE's built-in assembler + emulator, in-process: the "Apollo AGC" dock (DSKY,
  registers, erasable memory, channels, variables), breakpoints on source lines, F10 / F11 / Shift+F11,
  Locals = registers + the program's erasable variables, Watch / Immediate (symbols, registers, octal
  addresses). The CPU runs in real time (85 000 memory cycles per second) in timer slices.
* ``YaAgcSession`` - Virtual AGC: yaYUL builds the rope (errors -> Error List), yaAGC runs it and the DSKY
  panel connects to its socket; in debug mode yaAGC's debugger console is driven with break / step / next /
  cont / info registers (stop locations from its --fullname annotations).

``make_session`` picks one from the project's "agc" settings ("assembler": auto | builtin | yayul,
"run": emulator | yaagc).
"""
from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QTreeWidgetItem

from . import assembler, toolchain
from .cpu import MCT_SECONDS, decimal
from .isa import REGISTERS
from .machine import AgcMachine


def _lang() -> str:
    try:
        from ..i18n import language
        return language()
    except Exception:  # noqa: BLE001
        return "en"


def _stop_info(file, line, reason, variables, frames, refs=None):
    from ..debugger import StopInfo
    return StopInfo(Path(file).name, line, reason, variables, frames, refs or {})


# ============================================================================ IDE glue
def ensure_panel(win):
    """The "Apollo AGC" dock of the main window (created once)."""
    panel = getattr(win, "_agc_panel", None)
    if panel is not None:
        return panel
    from PyQt6.QtWidgets import QDockWidget

    from .ui import AgcPanel
    panel = AgcPanel(win)
    dock = QDockWidget("Apollo AGC", win)
    dock.setObjectName("Apollo AGC")
    dock.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    win._agc_panel = panel
    win._agc_dock = dock
    try:
        view_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "View")
        view_menu.addAction(dock.toggleViewAction())
    except (StopIteration, AttributeError):
        pass
    return panel


def show_diagnostics(win, rows, lang: str = "en") -> int:
    """rows: [(severity, message, file, line)] into the Error List (keeps rows of other sources). -> errors"""
    el = getattr(win, "error_list", None)
    if el is None:
        return sum(r[0] == "Error" for r in rows)
    old = getattr(win, "_agc_err_keys", set())
    for i in reversed(range(el.topLevelItemCount())):
        it = el.topLevelItem(i)
        if (it.text(0), it.text(1), it.text(2), it.text(3)) in old:
            el.takeTopLevelItem(i)
    keys = set()
    for sev, msg, f, line in rows:
        row = [sev, msg, Path(f).name, str(line)]
        it = QTreeWidgetItem(row)
        it.setForeground(0, Qt.GlobalColor.darkRed if sev == "Error" else Qt.GlobalColor.darkYellow)
        el.addTopLevelItem(it)
        keys.add(tuple(row))
    win._agc_err_keys = keys
    errors = sum(el.topLevelItem(i).text(0) == "Error" for i in range(el.topLevelItemCount()))
    warnings = sum(el.topLevelItem(i).text(0) == "Warning" for i in range(el.topLevelItemCount()))
    try:
        win.dock_errors.setWindowTitle(f"Error List ({errors} errors, {warnings} warnings)")
        if any(r[0] == "Error" for r in rows):
            win.dock_errors.show()
            win.dock_errors.raise_()
    except Exception:  # noqa: BLE001
        pass
    return sum(r[0] == "Error" for r in rows)


def program_rows(prog, lang: str = "en"):
    return [(d.severity, d.text(lang), d.file, d.line) for d in list(prog.errors) + list(prog.warnings)]


def editor_texts(win) -> dict:
    """Unsaved editor contents of .agc files (lower-case name -> text)."""
    out = {}
    for views in (getattr(win, "modviews", {}) or {}).items():
        name, view = views
        try:
            if str(name).lower().endswith(".agc"):
                out[Path(name).name.lower()] = view.editor.text()
        except Exception:  # noqa: BLE001
            pass
    return out


def _bp_keys(breakpoints) -> set:
    out = set()
    for bp in breakpoints or []:
        try:
            out.add((Path(bp[0]).name.lower(), int(bp[1])))
        except (TypeError, ValueError, IndexError):
            pass
    return out


# ============================================================================ built-in emulator
class AgcSession(QObject):
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    SLICE = 0.03                 # seconds of wall time per timer slice
    MAX_LAG = 0.25               # never try to catch up more than this

    def __init__(self, win, folder: Path, startup_file: str, debug: bool, breakpoints, settings=None,
                 parent=None):
        super().__init__(parent or win)
        self.win = win
        self.folder = Path(folder)
        self.startup_file = startup_file
        self.debug = debug
        self.settings = settings or {}
        self.paused = False
        self.user_stopped = False
        self.caps = set()
        self._bps = _bp_keys(breakpoints)
        self.machine: AgcMachine | None = None
        self.program = None
        self.panel = None
        self._alive = False
        self._goal = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._slice)
        self._last = 0.0
        self._skip_bp = False
        self._dirty = False
        self.lang = _lang()

    # ------------------------------------------------------------------ IDE interface
    def running(self) -> bool:
        return self._alive

    def start(self) -> None:
        QTimer.singleShot(0, self._start)

    def _start(self) -> None:
        path = self.folder / self.startup_file
        prog = assembler.assemble_file(path, editor_texts(self.win))
        self.program = prog
        show_diagnostics(self.win, program_rows(prog, self.lang), self.lang)
        for d in prog.warnings:
            self.output.emit(f"{Path(d.file).name}({d.line}): warning: {d.text(self.lang)}\n")
        if not prog.ok:
            for d in prog.errors[:50]:
                self.output.emit(f"{Path(d.file).name}({d.line}): error: {d.text(self.lang)}\n")
            if any(d.code == "interp" for d in prog.errors):
                self.output.emit("\nThis program uses interpretive code: build it with yaYUL (Tools > Apollo AGC > "
                                 "Virtual AGC Toolchain..., then Project > Properties / \"agc\": "
                                 "{\"assembler\": \"yayul\"}).\n")
            self.output.emit(f"\n*** {len(prog.errors)} assembly error(s) - see the Error List\n")
            self.finished.emit(2)
            return
        self.output.emit(f"Assembled {path.name}: {prog.words()} words in "
                         f"{len({b for b, _o in prog.used})} fixed bank(s). Running in RAD IDE's AGC emulator "
                         f"({'debug' if self.debug else 'run'}). Click the DSKY and type: V N 0-9 Enter.\n")
        self.machine = AgcMachine(prog)
        self.machine.listeners.append(self._on_channel)
        self._apply_breakpoints()
        self.panel = ensure_panel(self.win)
        self.panel.session = self
        self.panel.dsky.set_model(self.machine.dsky)
        try:
            self.panel.dsky.keyPressed.disconnect()
            self.panel.dsky.proChanged.disconnect()
        except TypeError:
            pass
        self.panel.dsky.keyPressed.connect(self.key)
        self.panel.dsky.proChanged.connect(self.pro)
        dock = getattr(self.win, "_agc_dock", None)
        if dock is not None:
            dock.show()
            dock.raise_()
        self._alive = True
        self.panel.update_buttons(True, False)
        stop_entry = self.debug and str(self.settings.get("stop_at_entry", "false")).lower() in ("1", "true", "yes")
        if stop_entry:
            self._pause("entry")
        else:
            self._resume()
        self.panel.dsky.setFocus()

    def stop(self) -> None:
        if not self._alive:
            return
        self.user_stopped = True
        self._finish(0)

    def cont(self) -> None:
        if self._alive:
            self._goal = None
            self._resume(skip_bp=True)

    def pause(self) -> None:
        if self._alive and not self.paused:
            self._pause("pause")

    def step_into(self) -> None:
        if not self._can_step():
            return
        m = self.machine
        m.cpu.step()
        if m.current_line() is not None:
            self._pause("step")
            return
        self._goal = lambda: m.current_line() is not None
        self._resume(skip_bp=True, step=True)

    def step_over(self) -> None:
        if not self._can_step():
            return
        m = self.machine
        cpu = m.cpu
        word = cpu.fetch_word(cpu.Z) if cpu.pending_word is None else cpu.pending_word
        is_call = (word >> 12) == 0 and (word & 0o7777) not in (3, 4, 6) and not cpu.extend and (word & 0o7777) > 7
        if not is_call:
            return self.step_into()
        ret = cpu.location((cpu.Z + 1) & 0o7777)
        cpu.step()
        self._goal = lambda: cpu.location() == ret and m.current_line() is not None
        self._resume(skip_bp=False, step=True)

    def step_out(self) -> None:
        if not self._can_step():
            return
        m = self.machine
        cpu = m.cpu
        state = {"depth": 0, "out": False}

        def goal():
            if state["out"]:
                return m.current_line() is not None
            w = cpu.fetch_word(cpu.Z)
            if (w >> 12) == 0 and not cpu.extend:
                k = w & 0o7777
                if k == 2:
                    if state["depth"] == 0:
                        state["out"] = True
                    else:
                        state["depth"] -= 1
                elif k > 7:
                    state["depth"] += 1
            return False
        self._goal = goal
        self._resume(skip_bp=False, step=True)

    def reload(self) -> None:
        if not self._alive or self.program is None:
            return
        self.machine.cpu.reset()
        self.machine.dsky.clear()
        self.output.emit("\n------ AGC reset (GOJAM) ------\n")
        if self.paused:
            self._pause("entry")
        else:
            self._refresh(True)

    def key(self, name: str) -> None:
        if self.machine is None or not self._alive:
            return
        self.machine.press(name)
        if self.paused:
            self.output.emit(f"[AGC] key {name} queued (the CPU is paused)\n")

    def pro(self, pressed: bool) -> None:
        if self.machine is not None:
            self.machine.cpu.set_pro(pressed)

    def evaluate(self, expr: str) -> None:
        self.evalResult.emit(self._eval_text(expr))

    def watch(self, expr: str, cb) -> None:
        cb(self._eval_text(expr) if self.machine else "(not running)", "", 0)

    def children(self, ref, cb) -> None:
        cb([])

    def threads(self, cb) -> None:
        cb([(1, "AGC CPU")])

    def select_thread(self, tid) -> None:
        pass

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = "") -> None:
        key = (Path(filename).name.lower(), int(line))
        if on:
            self._bps.add(key)
        else:
            self._bps.discard(key)
        self._apply_breakpoints()

    def set_break_on_exception(self, on: bool) -> None:
        pass

    def send(self, cmd: str) -> None:
        pass

    # ------------------------------------------------------------------ internals
    def _apply_breakpoints(self) -> None:
        if self.machine is not None:
            self.machine.set_breakpoint_lines(self._bps if self.debug else set())

    def _can_step(self) -> bool:
        return self._alive and self.paused and self.machine is not None

    def _on_channel(self, ch: int, value: int) -> None:
        self._dirty = True

    def _resume(self, skip_bp: bool = False, step: bool = False) -> None:
        if self.paused:
            self.paused = False
            self.resumed.emit()
        self._skip_bp = skip_bp
        if self.panel is not None:
            self.panel.update_buttons(True, False)
            self.panel.status.setText("Apollo AGC: running")
        try:
            self.win._clear_current_line()
            self.win._set_run_state("Running (Apollo AGC)")
        except Exception:  # noqa: BLE001
            pass
        self._last = time.perf_counter()
        self._timer.start(0)

    def _slice(self) -> None:
        if not self._alive or self.paused:
            return
        m = self.machine
        now = time.perf_counter()
        dt = min(self.MAX_LAG, max(0.001, now - self._last))
        self._last = now
        budget = int(dt / MCT_SECONDS)
        end = m.cpu.mct + budget
        deadline = now + self.SLICE
        reason = None
        n = 0
        while m.cpu.mct < end:
            if self._skip_bp:
                self._skip_bp = False
            elif m.at_breakpoint():
                reason = "breakpoint"
                break
            m.cpu.step()
            n += 1
            if self._goal is not None and self._goal():
                reason = "step"
                break
            if n & 1023 == 0 and time.perf_counter() > deadline:
                break
        if reason is not None:
            self._goal = None
            self._pause(reason)
            return
        if self._dirty and self.panel is not None:
            self._dirty = False
            self._refresh(False)
        self._timer.start(int(self.SLICE * 1000 * 0.5))

    def _refresh(self, heavy: bool) -> None:
        if self.panel is not None:
            self.panel.refresh(heavy)

    def _pause(self, reason: str) -> None:
        self._timer.stop()
        self.paused = True
        m = self.machine
        if self.panel is not None:
            self.panel.update_buttons(True, True)
            self.panel.status.setText(f"Apollo AGC: paused ({reason}) at {m.cpu.location()[0]}"
                                      f"{m.cpu.location()[1]:o},{m.cpu.Z:04o}")
            self._refresh(True)
        line = m.current_line() or (str(self.folder / self.startup_file), 1)
        self.stopped.emit(_stop_info(line[0], line[1], reason, self._locals(), self._frames(line)))

    def _locals(self):
        m = self.machine
        cpu = m.cpu
        out = []
        for name, v in cpu.registers().items():
            if name in ("A", "Q"):
                over = ((v >> 15) & 1) != ((v >> 14) & 1)
                out.append((name, "register", f"{v:06o}" + (" overflow" if over else "") +
                            f" = {decimal((v & 0o37777) | ((v >> 1) & 0o40000))}"))
            elif name in ("L", "Z", "EB", "FB", "BB"):
                out.append((name, "register", f"{v:05o} = {decimal(v) if name == 'L' else v}"))
        prog = m.program
        if prog is not None:
            for name, loc in sorted(prog.symbols.items(), key=lambda kv: kv[1].pseudo()):
                if loc.kind == "E" and not (loc.bank == 0 and loc.off < 0o61) and name not in REGISTERS:
                    v = cpu.read_erasable(loc.bank, loc.off)
                    out.append((name, f"erasable {loc}", f"{v:05o} = {decimal(v)}"))
                    if len(out) > 120:
                        break
        return out

    def _label_at(self, loc) -> str:
        prog = self.machine.program
        if prog is None:
            return "AGC"
        best, best_off = "", -1
        kind, bank, off = loc
        for name, l in prog.symbols.items():
            if l.kind == kind and l.bank == bank and best_off < l.off <= off:
                best, best_off = name, l.off
        return best or "AGC"

    def _frames(self, line):
        m = self.machine
        cpu = m.cpu
        frames = [(self._label_at(cpu.location()), line[0], line[1])]
        q = cpu.reg(2) & 0o7777
        if 0o2000 <= q:
            loc = cpu.location((q - 1) & 0o7777)
            src = m.program.line_of.get(loc) if m.program else None
            if src:
                frames.append((self._label_at(loc), src[0], src[1]))
        return frames

    def _eval_text(self, expr: str) -> str:
        m = self.machine
        if m is None:
            return "(not running)"
        e = expr.strip()
        cpu = m.cpu
        regs = cpu.registers()
        if e.upper() in regs:
            v = regs[e.upper()]
            return f"{v:06o} = {decimal(v & 0o77777)}"
        hit = m.symbol_value(e)
        if hit is not None:
            loc, v = hit
            return f"{v:05o} = {decimal(v)}   ({loc})"
        try:
            a = int(e, 8)
        except ValueError:
            return f"(unknown: {e})"
        v = cpu.read(a)
        return f"[{a:04o}] = {v:05o} = {decimal(v & 0o77777)}"

    def _finish(self, code: int) -> None:
        if not self._alive:
            return
        self._alive = False
        self._timer.stop()
        self.paused = False
        if self.panel is not None:
            self.panel.update_buttons(False, False)
            self.panel.status.setText("Apollo AGC: stopped")
            self._refresh(True)
        self.output.emit(f"\n[AGC] stopped after {self.machine.cpu.instructions if self.machine else 0} "
                         f"instructions\n")
        self.finished.emit(code)


# ============================================================================ Virtual AGC (yaYUL + yaAGC)
class YaAgcSession(QObject):
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, win, folder: Path, startup_file: str, debug: bool, breakpoints, settings=None,
                 parent=None):
        super().__init__(parent or win)
        self.win = win
        self.folder = Path(folder)
        self.startup_file = startup_file
        self.debug = debug
        self.settings = settings or {}
        self.port = int(self.settings.get("port", 19697) or 19697)
        self.paused = False
        self.user_stopped = False
        self.caps = set()
        self._bps = _bp_keys(breakpoints)
        self._build = None
        self._agc = None
        self._link = None
        self._buf = ""
        self._regs = {}
        self._alive = False
        self.machine = None
        self.lang = _lang()

    def running(self) -> bool:
        return self._alive

    def start(self) -> None:
        argv = toolchain.yayul_command(self.startup_file, str(self.settings.get("yayul_args", "")))
        if not argv:
            self.failed.emit("yaYUL is not installed: Tools > Apollo AGC > Virtual AGC Toolchain...")
            self.finished.emit(1)
            return
        self._alive = True
        self.output.emit(f"yaYUL {self.startup_file} ...\n")
        p = QProcess(self)
        p.setWorkingDirectory(str(self.folder))
        p.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        p.finished.connect(lambda code, _st: self._built(code))
        self._build = p
        p.start(argv[0], argv[1:])

    def _built(self, code: int) -> None:
        err = bytes(self._build.readAllStandardError()).decode("utf-8", "replace")
        out = bytes(self._build.readAllStandardOutput()).decode("utf-8", "replace")
        rows = [(sev, msg, f, line) for sev, f, line, msg in toolchain.parse_yayul_output(err)]
        n = show_diagnostics(self.win, rows, self.lang)
        tail = [ln for ln in out.splitlines()[-6:] if ln.strip()]
        self.output.emit("\n".join(tail) + "\n")
        rope = self.folder / (self.startup_file + ".bin")
        if code != 0 or n or not rope.exists():
            self.output.emit(f"*** yaYUL: {n} error(s) - see the Error List\n")
            self._done(2)
            return
        self.output.emit(f"Rope image {rope.name} ({rope.stat().st_size} bytes). Starting yaAGC on port "
                         f"{self.port} ...\n")
        argv = toolchain.yaagc_command(rope.name, self.port, self.debug, self.startup_file + ".symtab")
        if not argv:
            self.failed.emit("yaAGC is not installed: Tools > Apollo AGC > Virtual AGC Toolchain...")
            self._done(1)
            return
        p = QProcess(self)
        p.setWorkingDirectory(str(self.folder))
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._agc_output)
        p.finished.connect(lambda c, _s: self._done(c))
        self._agc = p
        p.start(argv[0], argv[1:])
        self._connect_dsky()
        if self.debug:
            for f, line in sorted(self._bps):
                self.send(f"break {f.upper() if f.upper() == f else f}:{line}")
            self.send("cont")

    def _connect_dsky(self) -> None:
        from .dsky_model import DskyModel
        from .yaagc import YaAgcLink
        panel = ensure_panel(self.win)
        panel.session = self
        model = DskyModel()
        panel.dsky.set_model(model)
        link = YaAgcLink(self.port, parent=self)
        link.channel.connect(lambda ch, v: (model.channel(ch, v), panel.dsky.refresh()))
        link.connected.connect(lambda: self.output.emit("DSKY connected to yaAGC.\n"))
        try:
            panel.dsky.keyPressed.disconnect()
            panel.dsky.proChanged.disconnect()
        except TypeError:
            pass
        panel.dsky.keyPressed.connect(link.send_key)
        panel.dsky.proChanged.connect(link.set_pro)
        link.start()
        self._link = link
        panel.update_buttons(True, False)
        panel.status.setText(f"Apollo AGC: yaAGC (port {self.port})")
        dock = getattr(self.win, "_agc_dock", None)
        if dock is not None:
            dock.show()
            dock.raise_()

    def _agc_output(self) -> None:
        from .yaagc import parse_registers, parse_stop
        text = bytes(self._agc.readAllStandardOutput()).decode("utf-8", "replace")
        self._buf = (self._buf + text)[-20000:]
        shown = text.replace("\x1a\x1a", "@")
        self.output.emit(shown)
        regs = parse_registers(text)
        if regs:
            self._regs.update(regs)
        stop = parse_stop(text)
        if stop is not None and self.debug:
            f, line, addr = stop
            self.paused = True
            self._buf = ""
            variables = [(k, "register", f"{v:06o}") for k, v in self._regs.items()]
            self.stopped.emit(_stop_info(f, line, "breakpoint", variables, [("AGC", f, line)]))
            self.send("info registers")

    def send(self, cmd: str) -> None:
        if self._agc is not None and self._agc.state() == QProcess.ProcessState.Running:
            self._agc.write((cmd + "\n").encode("utf-8"))

    def cont(self) -> None:
        self.paused = False
        self.resumed.emit()
        self.send("cont")

    def pause(self) -> None:
        pass

    def step_into(self) -> None:
        self.paused = False
        self.resumed.emit()
        self.send("step")

    def step_over(self) -> None:
        self.paused = False
        self.resumed.emit()
        self.send("next")

    def step_out(self) -> None:
        self.step_over()

    def evaluate(self, expr: str) -> None:
        self.send(f"print {expr}")

    def watch(self, expr: str, cb) -> None:
        cb("(see the Output window)", "", 0)

    def children(self, ref, cb) -> None:
        cb([])

    def threads(self, cb) -> None:
        cb([(1, "yaAGC")])

    def select_thread(self, tid) -> None:
        pass

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = "") -> None:
        if self.debug:
            self.send(f"break {Path(filename).name}:{line}" if on else f"clear {Path(filename).name}:{line}")

    def set_break_on_exception(self, on: bool) -> None:
        pass

    def stop(self) -> None:
        self.user_stopped = True
        self.send("quit")
        for p in (self._agc, self._build):
            if p is not None and p.state() != QProcess.ProcessState.NotRunning:
                p.kill()
        self._done(0)

    def _done(self, code: int) -> None:
        if not self._alive:
            return
        self._alive = False
        if self._link is not None:
            self._link.stop()
        panel = getattr(self.win, "_agc_panel", None)
        if panel is not None:
            panel.update_buttons(False, False)
            panel.status.setText("Apollo AGC: stopped")
        self.finished.emit(code)


# ============================================================================ chooser
def make_session(win, folder: Path, startup: str, debug: bool, breakpoints, settings: dict):
    want = str(settings.get("assembler", "auto")).lower()
    run = str(settings.get("run", "emulator")).lower()
    have = bool(toolchain.find("yayul")) and bool(toolchain.find("yaagc"))
    if want == "yayul" or run == "yaagc":
        if have:
            return YaAgcSession(win, folder, startup, debug, breakpoints, settings)
        try:
            win.log("*** Virtual AGC (yaYUL / yaAGC) is not installed: Tools > Apollo AGC > Virtual AGC "
                    "Toolchain... - trying RAD IDE's built-in assembler and emulator instead.")
        except Exception:  # noqa: BLE001
            pass
    elif want == "auto" and have:
        prog = assembler.assemble_file(Path(folder) / startup, editor_texts(win))
        if any(d.code == "interp" for d in prog.errors):
            return YaAgcSession(win, folder, startup, debug, breakpoints, settings)
    return AgcSession(win, folder, startup, debug, breakpoints, settings)


__all__ = ["AgcSession", "YaAgcSession", "editor_texts", "ensure_panel", "make_session", "program_rows",
           "show_diagnostics"]
