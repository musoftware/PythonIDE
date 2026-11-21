"""The "8086 Assembly (Emulator)" project type in the real IDE window (offscreen, QSettings "RADIDE-TEST"):

1. the plugin is registered and New Project creates every template;
2. a copy of samples/Tests/Assembly/Emu8086Factorial opens, F5 stops at the first instruction, F10 steps,
   a breakpoint in the editor stops the run, the registers panel / Locals show the values, F11 enters the
   recursive procedure (call stack grows), Shift+F11 steps out, Step Back undoes, F5 runs to the end and the
   program output reaches the Output window and the emulator screen;
3. typing on the emulator screen feeds a program waiting in INT 21h;
4. an assembly error goes to the Error List (with the Arabic text when the UI is Arabic);
5. screenshots of the emulator dock (widget.grab only).

Run:  python samples/Tests/Assembly/Emu8086Tests/test_ide.py
"""
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")       # readable screenshots offscreen
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
import json  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
__import__("PyQt6.QtWebEngineWidgets")          # before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QKeyEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST-Emu8086")
app = QApplication(sys.argv[:1])
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))

from radide.app import MainWindow  # noqa: E402
from radide.languages import get_plugin  # noqa: E402

results = []
ERRORS = []
SHOTS = Path(os.environ.get("RADIDE_SHOTS", tempfile.gettempdir())) / "radide_emu8086"
SHOTS.mkdir(parents=True, exist_ok=True)
WORK = Path(tempfile.mkdtemp(prefix="radide_emu8086_"))


def _hook(*exc):
    import traceback
    ERRORS.append("".join(traceback.format_exception(*exc)))
    print(ERRORS[-1], file=sys.stderr, flush=True)


sys.excepthook = _hook


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  - {detail}" if detail and not ok else ""), flush=True)


def pump(sec=0.3):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        time.sleep(0.01)


def wait(cond, timeout=20.0):
    t = time.time()
    while time.time() - t < timeout:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.02)
    return False


def close_boxes():
    m = QApplication.activeModalWidget()
    if m is not None:
        m.close()


killer = QTimer()
killer.timeout.connect(close_boxes)
killer.start(300)


def current_line(win):
    st = getattr(win, "stopped_at", None)
    return st[1] + 1 if st else None


def line_of(text, needle):
    for i, ln in enumerate(text.splitlines(), start=1):
        if needle in ln:
            return i
    raise KeyError(needle)


def main():
    plugin = get_plugin("emu8086")
    check("plugin registered", plugin.display_name == "8086 Assembly (Emulator)")
    for tid, title, _d, _i in plugin.project_templates():
        p = plugin.create_new_project(WORK / tid, "T_" + tid, tid)
        ok = (WORK / tid / "main.asm").is_file() and json.loads((WORK / tid / "project.radproj").read_text())["language"] == "emu8086"
        check(f"New Project template '{title}'", ok and p.startup == "main")

    proj = WORK / "Emu8086Factorial"
    shutil.copytree(HERE.parent / "Emu8086Factorial", proj)
    src = (proj / "main.asm").read_text(encoding="utf-8")
    win = MainWindow()
    win.resize(1500, 950)
    win.show()
    pump(2)
    win.open_project(proj, ask=False)
    pump(1)
    check("project opened", win.project is not None and win.project.language == "emu8086")
    win.open_module("main.asm")
    pump(0.5)
    ed = win.modviews["main.asm"].editor
    bp_line = line_of(src, "mul word ptr [bp+4]")
    ed.toggle_breakpoint(bp_line - 1)
    pump(0.2)

    # ---- F5: paused at the first instruction
    win.run_project(debug=True)
    check("session started", wait(lambda: win.session is not None and win.session.paused, 15),
          win.output.toPlainText()[-800:])
    s = win.session
    first = line_of(src, "mov ax, @data")
    check("paused at the first instruction", current_line(win) == first, f"{current_line(win)} != {first}")
    panel = win._emu8086_panel
    check("emulator dock visible", win._emu8086_dock.isVisible())
    check("registers panel shows IP", panel.registers.edits["IP"].text() == f"{s.machine.cpu.ip:04X}")
    # ---- F10 twice: mov ax,@data / mov ds,ax
    s.step_over()
    wait(lambda: s.paused)
    s.step_over()
    wait(lambda: s.paused)
    check("step over moves two lines", current_line(win) == line_of(src, "push n"), current_line(win))
    ds = s.machine.cpu.s[3]
    check("DS = @data after two steps", ds == next(v.segment for v in s.program.variables if v.name == "n"))
    check("changed register is shown red", "d00000" in panel.registers.edits["DS"].styleSheet())
    # ---- F5: run to the breakpoint in factorial
    s.cont()
    check("stopped at the breakpoint", wait(lambda: s.paused and current_line(win) == bp_line, 10),
          current_line(win))
    locs = {win.locals.topLevelItem(i).text(0): win.locals.topLevelItem(i).text(1)
            for i in range(win.locals.topLevelItemCount())}
    check("Locals show registers and variables", "AX" in locs and "n" in locs and "result" in locs,
          list(locs)[:20])
    check("AX = 1 at the deepest level (factorial(1) returned 1)", s.machine.cpu.r[0] == 1,
          s.machine.cpu.r[0])
    frames = [win.callstack.item(i).text() for i in range(win.callstack.count())]
    check("call stack shows the recursion", sum("factorial" in f for f in frames) >= 6, frames)
    panel.tabs.setCurrentWidget(panel.stack)
    panel.refresh(True)
    check("stack view lists return addresses",
          any("return to line" in panel.stack.topLevelItem(i).text(2) for i in range(panel.stack.topLevelItemCount())))
    # ---- Step Back
    ax_before = s.machine.cpu.r[0]
    line_before = current_line(win)
    s.step_over()
    wait(lambda: s.paused)
    check("step over the mul changes AX", s.machine.cpu.r[0] == 2, s.machine.cpu.r[0])
    s.step_back()
    wait(lambda: s.paused)
    check("step back restores AX and the line", s.machine.cpu.r[0] == ax_before and current_line(win) == line_before,
          (s.machine.cpu.r[0], current_line(win)))
    # ---- Step Out
    ed.toggle_breakpoint(bp_line - 1)                         # remove the breakpoint
    pump(0.2)
    depth0 = len([f for f in frames if "factorial" in f])
    s.step_out()
    wait(lambda: s.paused)
    frames2 = [win.callstack.item(i).text() for i in range(win.callstack.count())]
    check("step out returns to the caller", len([f for f in frames2 if "factorial" in f]) == depth0 - 1,
          (depth0, frames2))
    shot = panel.grab()
    shot.save(str(SHOTS / "emu8086_paused.png"))
    # ---- variables view
    panel.tabs.setCurrentWidget(panel.variables)
    panel.refresh(True)
    names = [panel.variables.topLevelItem(i).text(0) for i in range(panel.variables.topLevelItemCount())]
    check("variables view lists the data labels", names[:3] == ["n", "result", "msg1"], names)
    panel.memory.show_address("msg1")
    check("memory view follows a variable name", "37 21 20 3D" in panel.memory.text.toPlainText())
    # ---- watch / immediate
    got = []
    s.watch("word ptr [bp+4]", lambda v, t, r: got.append(v))
    s.watch("n", lambda v, t, r: got.append(v))
    check("watch expressions", len(got) == 2 and got[1].endswith("= 7"), got)
    # ---- run to the end
    s.cont()
    check("program finished", wait(lambda: win.session is None, 15))
    out = win.output.toPlainText()
    check("output in the Output window", "7! = 5040" in out, out[-500:])
    check("output on the emulator screen", "7! = 5040" in panel.machine.screen_text())
    panel.grab().save(str(SHOTS / "emu8086_finished.png"))

    # ---- keyboard: a program waiting for a key in INT 21h
    proj2 = WORK / "Emu8086StringReverse"
    shutil.copytree(HERE.parent / "Emu8086StringReverse", proj2)
    win.open_project(proj2, ask=False)
    pump(1)
    win.run_project(debug=False)
    check("waiting for keyboard input", wait(lambda: win.session is not None and win.session.machine is not None
                                             and win.session.machine.waiting == "key", 10))
    for ch in "abc":
        ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A + (ord(ch) - ord("a")), Qt.KeyboardModifier.NoModifier, ch)
        panel.screen.keyPressEvent(ev)
    panel.screen.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier, "\r"))
    check("typed keys reach the program", wait(lambda: win.session is None, 10))
    check("reversed text printed", "Reversed: cba" in win.output.toPlainText(), win.output.toPlainText()[-300:])

    # ---- slow motion: the current line moves while the program runs, Pause stops it
    proj3 = WORK / "Emu8086BubbleSort"
    shutil.copytree(HERE.parent / "Emu8086BubbleSort", proj3)
    win.open_project(proj3, ask=False)
    pump(1)
    panel.speed.setValue(40)                                  # ~40 steps per second, animated
    win.run_project(debug=True)
    wait(lambda: win.session is not None and win.session.paused, 10)
    s = win.session
    s.cont()
    seen = set()
    t0 = time.time()
    while time.time() - t0 < 2.0:
        app.processEvents()
        seen.add(current_line(win))
        time.sleep(0.02)
    check("slow motion moves the current line", len(seen) >= 5 and not s.paused, sorted(x for x in seen if x))
    s.pause()
    check("pause stops the program", s.paused and win.session is s)
    steps_paused = s.machine.cpu.cycles
    pump(0.5)
    check("no steps while paused", s.machine.cpu.cycles == steps_paused)
    panel.speed.setValue(100)
    win.stop_project()
    check("stop ends the session", wait(lambda: win.session is None, 5))

    # ---- an assembly error -> Error List (Arabic text in Arabic UI)
    from radide import i18n
    i18n.load("ar")
    try:
        main_asm = proj2 / "main.asm"
        main_asm.write_text(main_asm.read_text(encoding="utf-8").replace("mov ds, ax", "mov ds, 5"), encoding="utf-8")
        mv = win.modviews.get("main.asm")
        if mv is not None:
            mv.editor.setText(main_asm.read_text(encoding="utf-8"))
        win.run_project(debug=True)
        wait(lambda: win.session is None, 10)
        rows = [(win.error_list.topLevelItem(i).text(0), win.error_list.topLevelItem(i).text(1))
                for i in range(win.error_list.topLevelItemCount())]
        check("assembly error in the Error List", any(r[0] == "Error" and "mov ax" in r[1] for r in rows), rows)
        import re
        check("Arabic error text", any(re.search(r"[؀-ۿ]", r[1]) for r in rows), rows)
        from radide.tools import run_checks
        diags = run_checks(win, show=True)                    # Check for Errors / save: the diag provider
        check("Check for Errors reports the assembly error",
              any(d.severity == "Error" and d.file == "main.asm" and "mov ax" in d.message for d in diags),
              [(d.severity, d.message, d.line) for d in diags])
    finally:
        i18n.load("en")
    out = win.output.toPlainText()
    check("no tracebacks", "Traceback" not in out and not ERRORS, (ERRORS[:1], out[-400:]))
    win.close()
    pump(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        QSettings().clear()
        shutil.rmtree(WORK, ignore_errors=True)
    ok = sum(1 for _n, c in results if c)
    print(f"{ok}/{len(results)} passed; FAILED: {[n for n, c in results if not c] or 'none'}; shots in {SHOTS}")
    sys.exit(0 if ok == len(results) else 1)
