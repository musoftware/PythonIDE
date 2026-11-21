"""Qt side of the retro emulators: Tools > Retro Emulators... (manager), the Retro Debugger dock (VICE binary
monitor / mGBA GDB stub: registers, memory, breakpoints, step) and Project > DOS Settings...
"""
from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                             QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from . import manager
from .catalog import EMULATORS, SYSTEM_TITLES

SETTINGS_KEY = "retro/emu/"


def _mono() -> QFont:
    f = QFont("Consolas", 9)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def apply_settings(settings) -> None:
    """Paths the user chose in the manager (QSettings retro/emu/<id>) -> manager.set_configured."""
    if settings is None:
        return
    for eid in EMULATORS:
        v = settings.value(SETTINGS_KEY + eid, "")
        manager.set_configured(eid, str(v or ""))


# ====================================================================== manager dialog
class _Bus(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(str, bool)


class EmulatorManager(QDialog):
    COLS = ["Emulator", "Systems", "Status", "Version", "Licence"]

    def __init__(self, win=None):
        super().__init__(win)
        self.win = win
        self.settings = getattr(win, "settings", None)
        self.setWindowTitle("Retro Emulators")
        self.resize(900, 520)
        lay = QVBoxLayout(self)
        intro = QLabel("Free emulators RAD IDE can start your ROMs and DOS programs in. Nothing is downloaded until "
                       "you press Download: the pinned build comes from the emulator's official release page, its "
                       "SHA-256 is checked, and it is kept portable in %LOCALAPPDATA%\\RADIDE\\tools.")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._selected)
        lay.addWidget(self.table, 2)
        self.notes = QLabel("")
        self.notes.setWordWrap(True)
        lay.addWidget(self.notes)
        row = QHBoxLayout()
        self.b_download = QPushButton("Download")
        self.b_browse = QPushButton("Browse...")
        self.b_folder = QPushButton("Open Folder")
        self.b_page = QPushButton("Official Page")
        self.b_remove = QPushButton("Remove")
        self.b_run = QPushButton("Run ROM...")
        for b in (self.b_download, self.b_browse, self.b_folder, self.b_page, self.b_remove):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self.b_run)
        lay.addLayout(row)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(_mono())
        self.log.setMaximumHeight(140)
        lay.addWidget(self.log, 1)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        self.bus = _Bus()
        self.bus.line.connect(self.log.appendPlainText)
        self.bus.done.connect(self._download_done)
        self.b_download.clicked.connect(self.download)
        self.b_browse.clicked.connect(self.browse)
        self.b_folder.clicked.connect(self.open_folder)
        self.b_page.clicked.connect(lambda: self.current() and webbrowser.open(EMULATORS[self.current()].page))
        self.b_remove.clicked.connect(self.remove)
        self.b_run.clicked.connect(lambda: run_rom_dialog(self.win or self))
        self.busy: set[str] = set()
        self.refresh()

    def current(self) -> str:
        r = self.table.currentRow()
        it = self.table.item(r, 0) if r >= 0 else None
        return it.data(Qt.ItemDataRole.UserRole) if it else ""

    def refresh(self) -> None:
        cur = self.current()
        rows = manager.status()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            systems = ", ".join(SYSTEM_TITLES.get(s, s) for s in r["systems"])
            if r["id"] in self.busy:
                st = "Downloading..."
            elif r["path"]:
                st = r["path"]
            else:
                st = "Not installed"
            vals = [r["title"], systems, st, r["version"] or ("-" if not r["path"] else ""),
                    r["licence"]]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, r["id"])
                if c == 2 and not r["path"]:
                    it.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(i, c, it)
            if r["id"] == cur:
                self.table.selectRow(i)
        if self.table.currentRow() < 0 and rows:
            self.table.selectRow(0)
        self.table.resizeColumnsToContents()
        self._selected()

    def _selected(self) -> None:
        eid = self.current()
        if not eid:
            return
        e = EMULATORS[eid]
        installed = bool(manager.find(eid))
        mine = (manager.install_dir(eid) / "RADIDE-SOURCE.json").is_file()
        self.notes.setText(f"{e.title} {e.version} ({e.licence}) - {e.notes}")
        self.b_download.setEnabled(eid not in self.busy)
        self.b_download.setText("Download Again" if mine else "Download")
        self.b_remove.setEnabled(mine and eid not in self.busy)
        self.b_folder.setEnabled(installed)

    def download(self) -> None:
        eid = self.current()
        if not eid or eid in self.busy:
            return
        e = EMULATORS[eid]
        self.busy.add(eid)
        self.refresh()
        self.log.appendPlainText(f"--- {e.title} {e.version} from {e.url}")

        def work():
            ok = False
            try:
                ok = manager.install(eid, log=self.bus.line.emit)
            except Exception as ex:  # noqa: BLE001
                self.bus.line.emit(f"*** {ex}")
            self.bus.done.emit(eid, ok)
        threading.Thread(target=work, daemon=True).start()

    def _download_done(self, eid: str, ok: bool) -> None:
        self.busy.discard(eid)
        self.log.appendPlainText(("Done: " if ok else "Failed: ") + EMULATORS[eid].title)
        self.refresh()

    def browse(self) -> None:
        eid = self.current()
        if not eid:
            return
        path, _ = QFileDialog.getOpenFileName(self, f"Locate {EMULATORS[eid].title}", "", "Programs (*.exe);;All (*)")
        if not path:
            return
        manager.set_configured(eid, path)
        if self.settings is not None:
            self.settings.setValue(SETTINGS_KEY + eid, path)
        self.refresh()

    def open_folder(self) -> None:
        eid = self.current()
        exe = manager.find(eid) if eid else ""
        if exe:
            import os
            try:
                os.startfile(str(Path(exe).parent))          # noqa: S606 - opens Explorer
            except (OSError, AttributeError):
                pass

    def remove(self) -> None:
        eid = self.current()
        if not eid:
            return
        if QMessageBox.question(self, "Remove", f"Remove the copy of {EMULATORS[eid].title} RAD IDE downloaded?") \
                != QMessageBox.StandardButton.Yes:
            return
        manager.uninstall(eid)
        self.refresh()


def show_manager(win) -> EmulatorManager:
    dlg = EmulatorManager(win)
    dlg.show()
    win._retro_emu_manager = dlg
    return dlg


# ====================================================================== run a ROM
ROM_FILTER = ("ROMs and programs (*.a26 *.bin *.nes *.sfc *.smc *.gb *.gbc *.gba *.pce *.sms *.gg *.prg *.d64 "
              "*.t64 *.crt *.tap *.xex *.atr *.car *.com *.exe);;All files (*)")


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


def run_rom_dialog(win, debug: bool = False, path: str = ""):
    if not path:
        path, _ = QFileDialog.getOpenFileName(win, "Debug ROM in Emulator" if debug else "Run ROM in Emulator", "",
                                              ROM_FILTER)
    if not path:
        return None
    return start_rom(win, path, debug=debug)


def start_rom(win, path: str, system: str | None = None, debug: bool = False, symbols=None):
    from .launch import EmuError, run_rom
    apply_settings(getattr(win, "settings", None))
    if symbols is None:
        cands = [Path(path).with_suffix(e) for e in (".sym", ".lst", ".dbg", ".lbl", ".mlb", ".vs", ".labels")]
        symbols = [str(c) for c in cands if c.is_file()]
    try:
        proc = run_rom(path, system, debug=debug, symbols=symbols)
    except EmuError as e:
        QMessageBox.warning(win, "Retro Emulators", str(e))
        return None
    except OSError as e:
        QMessageBox.warning(win, "Retro Emulators", f"Cannot start the emulator: {e}")
        return None
    _log(win, f"[retro] {proc.emulator}: {' '.join(proc.command)}")
    win._retro_proc = proc
    if debug and proc.debug_backend:
        dock = ensure_debugger(win)
        dock.show()
        dock.raise_()
        dock.widget().attach(proc)
    return proc


def hot_reload(win, rom: str | None = None):
    """Reload the ROM in the running emulator (VICE in place, others restarted)."""
    from .launch import last_process
    proc = getattr(win, "_retro_proc", None) or last_process()
    if proc is None:
        _log(win, "[retro] No emulator was started from RAD IDE yet.")
        return None
    how = "hot reload" if proc.can_hot_reload() else "restart"
    proc.reload(rom)
    _log(win, f"[retro] {proc.emulator}: {how} of {proc.rom}")
    dock = getattr(win, "_retro_debug_dock", None)
    if dock is not None and proc.debug_backend:
        dock.widget().attach(proc)
    return proc


# ====================================================================== Retro Debugger
class RetroDebugger(QWidget):
    """Registers + memory + breakpoints of an emulator through its debug protocol."""

    def __init__(self, win=None):
        super().__init__(win)
        self.win = win
        self.proc = None
        self.backend = ""
        self.client = None
        self.prev: dict = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        bar = QHBoxLayout()
        self.status = QLabel("Not connected. Debug a C64 program (VICE) or a GBA ROM (mGBA) to attach.")
        self.b_break = QPushButton("Break")
        self.b_cont = QPushButton("Continue")
        self.b_step = QPushButton("Step Into")
        self.b_over = QPushButton("Step Over")
        self.b_refresh = QPushButton("Refresh")
        self.b_reload = QPushButton("Reload ROM")
        for b in (self.b_break, self.b_cont, self.b_step, self.b_over, self.b_refresh, self.b_reload):
            bar.addWidget(b)
        bar.addStretch(1)
        lay.addLayout(bar)
        lay.addWidget(self.status)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Registers"))
        self.regs = QTreeWidget()
        self.regs.setHeaderLabels(["Register", "Value", "Dec"])
        self.regs.setFont(_mono())
        ll.addWidget(self.regs, 2)
        ll.addWidget(QLabel("Breakpoints"))
        brow = QHBoxLayout()
        self.bp_edit = QLineEdit()
        self.bp_edit.setPlaceholderText("address, e.g. $080D or 0x080000D0 or a label")
        self.b_bp = QPushButton("Add")
        brow.addWidget(self.bp_edit)
        brow.addWidget(self.b_bp)
        ll.addLayout(brow)
        self.bps = QTreeWidget()
        self.bps.setHeaderLabels(["Address", "Label"])
        self.bps.setFont(_mono())
        ll.addWidget(self.bps, 1)
        split.addWidget(left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Memory"))
        self.addr = QLineEdit("$0800")
        self.b_go = QPushButton("Go")
        mrow.addWidget(self.addr, 1)
        mrow.addWidget(self.b_go)
        rl.addLayout(mrow)
        self.mem = QPlainTextEdit()
        self.mem.setReadOnly(True)
        self.mem.setFont(_mono())
        self.mem.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        rl.addWidget(self.mem)
        split.addWidget(right)
        split.setSizes([320, 560])
        lay.addWidget(split, 1)
        self.b_break.clicked.connect(self.do_break)
        self.b_cont.clicked.connect(self.do_continue)
        self.b_step.clicked.connect(lambda: self.do_step(False))
        self.b_over.clicked.connect(lambda: self.do_step(True))
        self.b_refresh.clicked.connect(self.refresh)
        self.b_reload.clicked.connect(lambda: hot_reload(self.win) if self.win is not None else None)
        self.b_go.clicked.connect(self.show_memory)
        self.addr.returnPressed.connect(self.show_memory)
        self.b_bp.clicked.connect(self.add_breakpoint)
        self.bp_edit.returnPressed.connect(self.add_breakpoint)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._poll)
        self.bp_numbers: dict[int, int] = {}
        self._update_buttons()

    # ------------------------------------------------------------------ attach
    def attach(self, proc) -> bool:
        self.detach()
        self.proc = proc
        self.backend = proc.debug_backend
        try:
            if self.backend == "vice-monitor":
                self.client = proc.monitor(retry_for=15)
                self.addr.setText("$0801")
            elif self.backend == "gdb-rsp":
                self.client = proc.gdb(retry_for=15)
                self.addr.setText("0x08000000")
            else:
                self.status.setText(f"{proc.emulator}: use the emulator's own debugger window.")
                return False
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Cannot connect to {proc.emulator}: {e}")
            self.client = None
            return False
        self.status.setText(f"Connected to {proc.emulator} ({'VICE binary monitor' if self.backend == 'vice-monitor' else 'GDB stub'}"
                            f" on port {proc.monitor_port or proc.gdb_port}).")
        self.refresh()
        return True

    def detach(self) -> None:
        self.timer.stop()
        self.client = None
        self.backend = ""
        self.bp_numbers.clear()
        self.bps.clear()

    @property
    def running(self) -> bool:
        if self.client is None:
            return False
        return bool(getattr(self.client, "running", False)) if self.backend == "vice-monitor" else self.timer.isActive()

    def _update_buttons(self) -> None:
        on = self.client is not None
        for b in (self.b_break, self.b_cont, self.b_step, self.b_refresh, self.b_bp, self.b_go):
            b.setEnabled(on)
        self.b_over.setEnabled(on and self.backend == "vice-monitor")
        self.b_reload.setEnabled(self.proc is not None)

    # ------------------------------------------------------------------ helpers
    def parse_addr(self, text: str) -> int | None:
        t = text.strip()
        if not t:
            return None
        labels = getattr(self.proc, "labels", {}) or {}
        for a, n in labels.items():
            if n.lower() == t.lower().lstrip("."):
                return a
        try:
            if t.startswith("$"):
                return int(t[1:], 16)
            if t.lower().startswith("0x"):
                return int(t, 16)
            if all(c in "0123456789abcdefABCDEF" for c in t) and any(c.isalpha() for c in t):
                return int(t, 16)
            return int(t, 16 if self.backend == "vice-monitor" else 0)
        except ValueError:
            return None

    def _fmt(self, v: int) -> str:
        return f"${v:04X}" if self.backend == "vice-monitor" and v <= 0xFFFF else f"0x{v:08X}"

    # ------------------------------------------------------------------ commands
    def do_break(self) -> None:
        if self.client is None:
            return
        try:
            if self.backend == "vice-monitor":
                self.client.pause()
            else:
                if self.timer.isActive():
                    self.timer.stop()
                    self.client.interrupt()
                else:
                    self.client.interrupt()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Break failed: {e}")
        self.timer.stop()
        self.refresh()

    def do_continue(self) -> None:
        if self.client is None:
            return
        try:
            if self.backend == "vice-monitor":
                self.client.exit_monitor()
            else:
                self.client.cont()
            self.status.setText("Running...")
            self.timer.start()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Continue failed: {e}")
        self._update_buttons()

    def do_step(self, over: bool = False) -> None:
        if self.client is None:
            return
        try:
            if self.backend == "vice-monitor":
                self.client.step(1, over=over)
                self.client.wait_stopped(3)
            else:
                self.client.step()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Step failed: {e}")
        self.refresh()

    def add_breakpoint(self) -> None:
        a = self.parse_addr(self.bp_edit.text())
        if a is None or self.client is None:
            return
        try:
            if self.backend == "vice-monitor":
                self.bp_numbers[a] = self.client.checkpoint_set(a)
            else:
                running = self.timer.isActive()
                if running:
                    self.timer.stop()
                    self.client.interrupt()
                self.client.set_breakpoint(a)
                self.bp_numbers[a] = a
                if running:
                    self.client.cont()
                    self.timer.start()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Breakpoint failed: {e}")
            return
        it = QTreeWidgetItem([self._fmt(a), (getattr(self.proc, "labels", {}) or {}).get(a, "")])
        self.bps.addTopLevelItem(it)
        self.bp_edit.clear()

    def _poll(self) -> None:
        if self.client is None:
            self.timer.stop()
            return
        try:
            if self.backend == "vice-monitor":
                ev = self.client.wait_stopped(0.05)
                if ev is not None:
                    self.timer.stop()
                    label = (getattr(self.proc, "labels", {}) or {}).get(ev.pc, "")
                    self.status.setText(f"Stopped at {self._fmt(ev.pc)} {label}".strip()
                                        + (f" (breakpoint {ev.checkpoint})" if ev.checkpoint >= 0 else ""))
                    self.refresh(keep_status=True)
            else:
                r = self.client.wait_stop(0.02)
                if r is not None:
                    self.timer.stop()
                    self.status.setText(f"Stopped ({r})")
                    self.refresh(keep_status=True)
        except Exception as e:  # noqa: BLE001
            self.timer.stop()
            self.status.setText(f"Connection lost: {e}")
            self.client = None
            self._update_buttons()

    def refresh(self, keep_status: bool = False) -> None:
        self._update_buttons()
        if self.client is None or self.timer.isActive():
            return
        try:
            regs = self.client.registers()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Cannot read registers: {e}")
            return
        self.regs.clear()
        labels = getattr(self.proc, "labels", {}) or {}
        for name, val in regs.items():
            it = QTreeWidgetItem([name, self._fmt(val) if name.upper() in ("PC", "SP", "LR") or val > 0xFF
                                  else f"${val:02X}" if self.backend == "vice-monitor" else f"0x{val:08X}", str(val)])
            if self.prev.get(name, val) != val:
                it.setForeground(1, Qt.GlobalColor.red)
            if name.upper() == "PC" and val in labels:
                it.setToolTip(1, labels[val])
            self.regs.addTopLevelItem(it)
        if self.backend == "vice-monitor" and "FL" in regs:
            fl = regs["FL"]
            flags = "".join(c if fl & (1 << (7 - i)) else "-" for i, c in enumerate("NV-BDIZC"))
            self.regs.addTopLevelItem(QTreeWidgetItem(["Flags", flags, ""]))
        self.prev = regs
        if not keep_status:
            pc = regs.get("PC", regs.get("pc"))
            if pc is not None:
                self.status.setText(f"Paused at {self._fmt(pc)} {labels.get(pc, '')}".strip())
        self.show_memory()

    def show_memory(self) -> None:
        if self.client is None or self.timer.isActive():
            return
        a = self.parse_addr(self.addr.text())
        if a is None:
            return
        n = 256
        try:
            if self.backend == "vice-monitor":
                a &= 0xFFFF
                data = self.client.memory_get(a, min(0xFFFF, a + n - 1))
            else:
                data = self.client.read_memory(a, n)
        except Exception as e:  # noqa: BLE001
            self.mem.setPlainText(f"Cannot read memory: {e}")
            return
        self.mem.setPlainText(hex_dump(data, a, 4 if self.backend == "vice-monitor" else 8))


def hex_dump(data: bytes, base: int, addr_digits: int = 4) -> str:
    rows = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hx = " ".join(f"{b:02X}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        rows.append(f"{base + i:0{addr_digits}X}  {hx:<47}  {asc}")
    return "\n".join(rows)


def ensure_debugger(win) -> QDockWidget:
    dock = getattr(win, "_retro_debug_dock", None)
    if dock is None:
        dock = QDockWidget("Retro Debugger", win)
        dock.setObjectName("RetroDebugger")
        dock.setWidget(RetroDebugger(win))
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        win._retro_debug_dock = dock
    return dock


# ====================================================================== DOS settings
class DosSettingsDialog(QDialog):
    def __init__(self, win, project):
        super().__init__(win)
        from .dos import CYCLES, MACHINES, SOUND, DosSettings, scan_dos_folder
        self.project = project
        self.setWindowTitle("DOS Settings")
        self.s = DosSettings.from_dict(project.extra.get("dos"))
        scan = scan_dos_folder(project.folder)
        progs = scan["exes"] + scan["coms"] + scan["bats"] + [f for v in scan["sources"].values() for f in v]
        form = QFormLayout(self)
        self.program = QComboBox()
        self.program.setEditable(True)
        self.program.addItems([""] + progs)
        self.program.setCurrentText(self.s.program or scan["start"])
        self.args = QLineEdit(self.s.args)
        self.cycles = QComboBox()
        self.cycles.setEditable(True)
        self.cycles.addItems(CYCLES)
        self.cycles.setCurrentText(self.s.cycles)
        self.machine = QComboBox()
        self.machine.addItems(MACHINES)
        self.machine.setCurrentText(self.s.machine)
        self.memsize = QSpinBox()
        self.memsize.setRange(1, 256)
        self.memsize.setValue(int(self.s.memsize))
        self.sound = QComboBox()
        self.sound.addItems(SOUND)
        self.sound.setCurrentText(self.s.sound)
        self.toolchain = QLineEdit(self.s.toolchain)
        tb = QPushButton("Browse...")
        tb.clicked.connect(self._browse)
        trow = QHBoxLayout()
        trow.addWidget(self.toolchain, 1)
        trow.addWidget(tb)
        self.build = QLineEdit(self.s.build)
        self.build.setPlaceholderText("e.g. TPC {src}  (empty = automatic)")
        self.exit_after = QCheckBox("Close DOSBox-X when the program ends")
        self.exit_after.setChecked(self.s.exit_after)
        self.fullscreen = QCheckBox("Full screen")
        self.fullscreen.setChecked(self.s.fullscreen)
        form.addRow("Program to start:", self.program)
        form.addRow("Arguments:", self.args)
        form.addRow("CPU cycles:", self.cycles)
        form.addRow("Machine:", self.machine)
        form.addRow("Memory (MB):", self.memsize)
        form.addRow("Sound card:", self.sound)
        form.addRow("DOS toolchain folder:", trow)
        form.addRow("Build command:", self.build)
        form.addRow(self.exit_after)
        form.addRow(self.fullscreen)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        form.addRow(box)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "DOS toolchain folder", self.toolchain.text())
        if d:
            self.toolchain.setText(d)

    def values(self) -> dict:
        s = self.s
        s.program = self.program.currentText().strip()
        s.args = self.args.text().strip()
        s.cycles = self.cycles.currentText().strip() or "auto"
        s.machine = self.machine.currentText()
        s.memsize = self.memsize.value()
        s.sound = self.sound.currentText()
        s.toolchain = self.toolchain.text().strip()
        s.build = self.build.text().strip()
        s.exit_after = self.exit_after.isChecked()
        s.fullscreen = self.fullscreen.isChecked()
        return s.to_dict()

    def accept(self) -> None:
        self.project.extra["dos"] = self.values()
        self.project.save()
        super().accept()


def dos_settings(win) -> None:
    p = getattr(win, "project", None)
    if p is None or getattr(p, "language", "") != "retro-dos":
        QMessageBox.information(win, "DOS Settings", "Open a DOS Program project first (New Project > Retro > "
                                                     "DOS Program, or File > Open Folder on a DOS program).")
        return
    DosSettingsDialog(win, p).exec()


__all__ = ["DosSettingsDialog", "EmulatorManager", "RetroDebugger", "apply_settings", "dos_settings",
           "ensure_debugger", "hex_dump", "hot_reload", "run_rom_dialog", "show_manager", "start_rom"]
