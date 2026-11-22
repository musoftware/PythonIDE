"""Run and Debug of a Python project use the same interpreter, and the Output window says which one.

    python samples/Tests/Debugger/test_python_run_debug_interpreter.py [scratch folder] [--pip]

The installed IDE ran programs with the newest Python but debugged with another one (debugpy was looked for only
in the IDE's own Python). Now the project's interpreter (its .venv first) runs the program in both cases; debugpy
comes from that interpreter, from the IDE (its launcher works for other Python versions) or is pip-installed into
the interpreter on demand.
  1. unit: debugpy_adapter_for() - own debugpy first, the IDE's debugpy next, the install hook last (a fake
     install that copies the IDE's debugpy into a scratch venv; with --pip a real "pip install debugpy").
  2. offscreen MainWindow, a Python Tk project from the template with its own .venv (made from another Python
     than the IDE's when one is installed, e.g. 3.14): F5 without debugging and F5 with a breakpoint both print
     the same sys.executable / version = the .venv's; the debug run stops at the breakpoint (debugpy) and the
     Output window shows "Python interpreter: <venv python> (Python x.y.z)" and the debugger used.
Exit code = number of failures."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
PIP = "--pip" in sys.argv
args = [a for a in sys.argv[1:] if a != "--pip"]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ["RADIDE_NO_VSX"] = "1"
SCRATCH = Path(args[0] if args else tempfile.mkdtemp(prefix="radide_pyinterp_")) / "py_run_debug_interp"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond), str(detail)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(detail)[:600]}]" if detail and not cond else ""), flush=True)
    return bool(cond)


def other_python() -> str:
    """A real Python of another version than the IDE's (py launcher), else the IDE's base Python."""
    mine = f"{sys.version_info[0]}.{sys.version_info[1]}"
    py = shutil.which("py")
    if py:
        r = subprocess.run([py, "-0p"], capture_output=True, text=True)
        for ln in r.stdout.splitlines():
            parts = ln.split()
            if len(parts) >= 2 and parts[0].startswith("-V:3.") and mine not in parts[0] and Path(parts[-1]).is_file():
                if "Astral" in parts[0]:
                    continue
                return parts[-1]
    return str(Path(getattr(sys, "_base_executable", "") or sys.executable))


def make_venv(folder: Path, base: str) -> str:
    r = subprocess.run([base, "-m", "venv", str(folder)], capture_output=True, text=True, timeout=600)
    py = folder / "Scripts" / "python.exe"
    return str(py) if r.returncode == 0 and py.is_file() else ""


__import__("PyQt6.QtWebEngineWidgets")              # before any QApplication
import debugpy  # noqa: E402  (the IDE's own, from its .venv)

IDE_DEBUGPY = Path(debugpy.__file__).parent

from radide import app as A  # noqa: E402

# ------------------------------------------------------------------ 1. unit: where debugpy comes from
base = other_python()
ok("another Python found for the project", Path(base).is_file(), base)
venv1 = make_venv(SCRATCH / "unit_venv", base)
ok("scratch venv created", venv1, base)
argv, how = A.debugpy_adapter_for(sys.executable)
ok("an interpreter with debugpy uses its own", argv and argv[0] == sys.executable and "this interpreter" in how,
   (argv, how))
argv, how = A.debugpy_adapter_for(venv1)
ok("without debugpy: the IDE's debugpy (the program still runs with its interpreter)",
   argv and os.path.normcase(argv[0]) == os.path.normcase(sys.executable) and "of the IDE" in how, (argv, how))
calls = []


def fake_install(py):
    calls.append(py)
    r = subprocess.run([py, "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], capture_output=True,
                       text=True)
    site = Path(r.stdout.strip())
    shutil.copytree(IDE_DEBUGPY, site / "debugpy", ignore=shutil.ignore_patterns("__pycache__"))
    return True


orig_has = A._has_debugpy
A._has_debugpy = lambda: False                         # an IDE without debugpy (a release build without it)
try:
    argv, how = A.debugpy_adapter_for(venv1, fake_install)
    ok("IDE without debugpy: installed into the interpreter on demand", calls == [venv1] and argv
       and argv[0] == venv1 and "installed" in how, (calls, argv, how))
    argv, how = A.debugpy_adapter_for(venv1, fake_install)
    ok("next time: the interpreter's own debugpy (no second install)", len(calls) == 1 and argv and argv[0] == venv1,
       (calls, argv))
    if PIP:
        venv2 = make_venv(SCRATCH / "pip_venv", base)
        from PyQt6.QtWidgets import QApplication as _QA  # noqa: E402
        _app0 = _QA.instance() or _QA(sys.argv[:1])

        class _W:                                        # the real MainWindow._install_debugpy on a stand-in
            settings = __import__("PyQt6.QtCore", fromlist=["QSettings"]).QSettings("RADIDE-TEST-LEFTOVER", "pip")
            log = staticmethod(lambda t: print("   " + t))
            _append_output = staticmethod(lambda t: None)

            class dock_output:  # noqa: N801
                show = staticmethod(lambda: None)
        argv, how = A.debugpy_adapter_for(venv2, lambda py: A.MainWindow._install_debugpy(_W(), py))
        ok("--pip: real pip install debugpy into the interpreter", argv and argv[0] == venv2, how)
finally:
    A._has_debugpy = orig_has
ok("old debugpy refused for Python 3.14", not A._debugpy_supports("1.6.7", "3.14.1") and A._debugpy_supports("1.8.22",
   "3.14.1"))

# ------------------------------------------------------------------ 2. the real IDE: Run and Debug
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv[:1])
ORG = os.environ.get("RADIDE_TEST_ORG", "RADIDE-TEST-LEFTOVER")
QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG + "-PYINTERP")
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)


def wait(cond, timeout=60.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.03)
    return False


from radide import workspace  # noqa: E402

folder = SCRATCH / "PyInterp"
workspace.create_project(folder, "PyInterp", "python-tk")
venv = make_venv(folder / ".venv", base)
ok("project .venv created", venv, base)
code = (folder / "Form1.py").read_text("utf-8")
main = 'if __name__ == "__main__":\n    Form1().show()\n'
ok("template main block", main in code)
code = code.replace(main, 'if __name__ == "__main__":\n    import sys\n    marker = "INTERP=" + sys.executable\n'
                          '    print(marker + " VERSION=" + sys.version.split()[0], flush=True)\n'
                          '    print("DONE", flush=True)\n')
(folder / "Form1.py").write_text(code, "utf-8")
bp_line = code.splitlines().index('    print("DONE", flush=True)')          # 0-based

from radide.app import MainWindow  # noqa: E402

win = MainWindow()
win.resize(1200, 800)
win.show()
wait(lambda: False, 1.0)
win.open_project(folder, ask=False)
wait(lambda: False, 1.0)
ok("the IDE picks the project's .venv", os.path.normcase(win._interpreter()) == os.path.normcase(venv),
   win._interpreter())


def out_text():
    return win.output.toPlainText()


def finished():
    return win.session is None or not win.session.running()


# Run
win.run_project(debug=False)
ok("Run finished", wait(lambda: "DONE" in out_text() and finished(), 90), out_text()[-600:])
run_out = out_text()
run_line = next((ln for ln in run_out.splitlines() if ln.startswith("INTERP=")), "")
ok("Run: the program runs with the .venv", os.path.normcase(venv) in os.path.normcase(run_line), run_line)
ok("Run: Output shows the interpreter", f"Python interpreter: {venv}" in run_out, run_out[:600])

# Debug with a breakpoint
win.open_code("Form1")
cv = win._codeview("Form1")
wait(lambda: getattr(cv.editor, "_ready", False), 60)
cv.editor.set_breakpoints([bp_line])
win.breakpoints["Form1.py"] = {bp_line}
win.run_project(debug=True)
ok("Debug: stopped at the breakpoint", wait(lambda: getattr(win.session, "paused", False), 90), out_text()[-800:])
s = win.session
from radide.dap import DapSession  # noqa: E402

ok("Debug: the debugpy engine", isinstance(s, DapSession), type(s))
if isinstance(s, DapSession):
    ok("Debug: the debuggee is the .venv's python", os.path.normcase(s.launch_args.get("python", [""])[0])
       == os.path.normcase(venv), s.launch_args.get("python"))
dbg_out = out_text()
ok("Debug: Output shows the interpreter and the debugger", f"Python interpreter: {venv}" in dbg_out
   and "Debugger: debugpy" in dbg_out, dbg_out[:800])
if s is not None:
    s.cont()
ok("Debug finished", wait(lambda: "DONE" in out_text() and finished(), 90), out_text()[-600:])
dbg_line = next((ln for ln in out_text().splitlines() if ln.startswith("INTERP=")), "")
ok("Run and Debug: the same interpreter and version", run_line and dbg_line == run_line, (run_line, dbg_line))
win.grab().save(str(SCRATCH.parent / "py_run_debug_interp.png"))

try:
    if win.session is not None and win.session.running():
        win.stop_project()
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c, _d in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
