"""Characterization of the features that take part in Run / Debug, while they move from wrapping MainWindow
(run_project, _make_session, _on_stopped, _on_resumed, _on_finished, _all_breakpoints) to
radide/extension_points.py.

The window's own steps (start a program, create a session, show a stop, ...) are replaced by counters ON THE
CLASS before the window is created, so nothing is really run. Then, in the real MainWindow (offscreen):
  * F5 in an Expo project -> Expo runs it; in a Flutter project -> flutter run; a Godot project with its debug
    adapter -> the adapter (after Save All); a file a VS Code extension debugs -> the extension; in each case
    the window does not run it itself
  * a mobile (non-Flutter) project writes its files, a 3D project saves its scenes, then the window runs it
  * any other project -> the window runs it
  * a new session: assembly / DOS / retro tool sessions get their extras (by the plugin)
  * a stop / resume / end of the program: CPU view, native debug windows, debug views (generation bumped
    BEFORE the window shows the stop), Run to Cursor's temporary breakpoint removed
  * Run to Cursor with no program running: the window starts debugging with one extra temporary breakpoint,
    and afterwards the breakpoints are the user's again

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_run_debug.py [scratch]
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-rundebug"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QObject, QSettings, pyqtSignal  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ARCH-RUN_DEBUG")      # own store: tests run in parallel
QCoreApplication.setApplicationName("RADIDE-TEST-ARCH-RUN_DEBUG")
app = QApplication(sys.argv[:1])
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))

results: list[tuple[str, bool]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:800]}]"), flush=True)
    return bool(cond)


def pump(n: int = 10) -> None:
    for _ in range(n):
        app.processEvents()


COUNT: dict[str, int] = {}
ORDER: list[str] = []


def note(name):
    COUNT[name] = COUNT.get(name, 0) + 1
    ORDER.append(name)


class FakeSession(QObject):
    finished = pyqtSignal(int)

    def running(self):
        return False


BP_SEEN: list = []
from radide.app import MainWindow  # noqa: E402

# the window's own steps -> counters, on the class, before the window exists (the features keep the originals
# they find at install time; after the migration the window calls its internal methods)
own_run = "_run_project" if hasattr(MainWindow, "_run_project") else "run_project"
own_session = "_create_session" if hasattr(MainWindow, "_create_session") else "_make_session"
own_stopped = "_show_stopped" if hasattr(MainWindow, "_show_stopped") else "_on_stopped"
own_resumed = "_show_resumed" if hasattr(MainWindow, "_show_resumed") else "_on_resumed"
own_finished = "_show_finished" if hasattr(MainWindow, "_show_finished") else "_on_finished"
setattr(MainWindow, own_run, lambda self, debug=True: (note("window runs it"),
                                                       BP_SEEN.append(list(self._all_breakpoints())))[0])
setattr(MainWindow, own_session, lambda self, spec, debug, plugin, interp, startup=None: (note("window session"),
                                                                                          FakeSession())[1])
setattr(MainWindow, own_stopped, lambda self, info: (ORDER.append(f"window stop gen={getattr(self, '_dbgx_gen', 0)}"),
                                                     note("window shows the stop"))[1])
setattr(MainWindow, own_resumed, lambda self: note("window shows resumed"))
setattr(MainWindow, own_finished, lambda self, code, session=None: note("window shows the end"))

from radide import workspace  # noqa: E402

proj = SCRATCH / "RunDebug"
workspace.create_project(proj, "RunDebug", "python-tk")
win = MainWindow()
win.resize(1200, 800)
win.show()
pump()
win.open_project(proj, ask=False)
pump()

import radide.features.expo as expo  # noqa: E402
import radide.features.game_runtimes as game_runtimes  # noqa: E402
import radide.features.mobile as mobile  # noqa: E402
import radide.games.godot_dap as godot_dap  # noqa: E402

SAVED: list = []


def patch(obj, attr, val):
    SAVED.append((obj, attr, getattr(obj, attr)))
    setattr(obj, attr, val)


def restore():
    while SAVED:
        obj, attr, val = SAVED.pop()
        setattr(obj, attr, val)


def f5(name, setup, expect_handled_by, expect_window: bool, before=None):
    COUNT.clear()
    ORDER.clear()
    try:
        setup()
        win.run_project(debug=True)
        pump()
        if expect_handled_by:
            ok(f"F5 {name}: {expect_handled_by}", COUNT.get(expect_handled_by) == 1, COUNT)
        if before:
            ok(f"F5 {name}: '{before}' before the window runs it",
               before in ORDER and "window runs it" in ORDER and ORDER.index(before) < ORDER.index("window runs it"),
               ORDER)
        ok(f"F5 {name}: the window {'runs it' if expect_window else 'does not run it itself'}",
           (COUNT.get("window runs it") == 1) == expect_window, COUNT)
    finally:
        restore()


svc = getattr(win, "vsx_host", None)
if svc is not None:            # nobody debugs with an extension unless asked
    patch(svc, "should_debug_with_extension", lambda ed: False)
    base_vsx = SAVED.pop()     # keep this one for the whole test

f5("in an Expo project", lambda: (patch(expo, "is_expo", lambda w: True),
                                  patch(win.expo, "run", lambda debug: note("Expo runs it"))),
   "Expo runs it", False)
f5("in a Flutter project", lambda: (patch(mobile, "is_flutter", lambda w: True),
                                    patch(win.mobile, "run_flutter", lambda debug: note("flutter run"))),
   "flutter run", False)
f5("in a mobile (Kivy / BeeWare) project", lambda: (patch(mobile, "is_mobile", lambda w: True),
                                                    patch(win.mobile, "_write_files", lambda: note("mobile files"))),
   None, True, before="mobile files")
f5("in a Godot project", lambda: (patch(game_runtimes, "_is_godot", lambda w: True),
                                  patch(win, "run_plugin", lambda: SimpleNamespace(find_interpreter=lambda c: "godot.exe")),
                                  patch(win, "_configured_interpreter", lambda plugin, project=None: ""),
                                  patch(godot_dap, "start_debugging", lambda w, g: note("Godot debug adapter")),
                                  patch(win, "save_all", lambda: note("saved first") or True)),
   "Godot debug adapter", False, before=None)
ok("F5 in a Godot project: saved first", COUNT.get("saved first") == 1, COUNT)
if svc is not None:
    f5("on a file a VS Code extension debugs", lambda: (patch(svc, "active_editor", lambda: object()),
                                                        patch(svc, "should_debug_with_extension", lambda ed: True),
                                                        patch(svc, "debug_start", lambda ed=None: note("extension debugs") or True)),
       "extension debugs", False)
f5("in a 3D project", lambda: patch(win.scenes3d, "save_all", lambda: note("3D scenes saved")),
   None, True, before="3D scenes saved")
f5("in a plain Python Tk project", lambda: None, None, True)

# ------------------------------------------------------------------ sessions
import radide.features.asm_build_ui as asm_build_ui  # noqa: E402
import radide.features.dos_ide as dos_ide  # noqa: E402
import radide.features.retro_dev as retro_dev  # noqa: E402
try:
    patch(asm_build_ui, "_attach_session", lambda w, s, plugin, debug: note("assembly session extras"))
    patch(retro_dev, "_attach_session", lambda w, s: note("retro session extras"))
    patch(dos_ide, "refresh_errors", lambda w: note("DOS errors refreshed"))
    for label, plugin, want in (("an assembly plugin", SimpleNamespace(id="asm-nasm"), "assembly session extras"),
                                ("a retro tool plugin", SimpleNamespace(id="retro-x", retro_dev=True), "retro session extras"),
                                ("a Python plugin", SimpleNamespace(id="python-tk"), None)):
        COUNT.clear()
        s = win._make_session(SimpleNamespace(), True, plugin, "")
        ok(f"a new session of {label}: the window's session is returned", isinstance(s, FakeSession), type(s))
        if want:
            ok(f"a new session of {label}: {want}", COUNT.get(want) == 1, COUNT)
        else:
            ok(f"a new session of {label}: no tool extras",
               not any(k.endswith("extras") for k in COUNT), COUNT)
    dos_lang = next(iter(dos_ide.DOS_LANGS))
    COUNT.clear()
    s = win._make_session(SimpleNamespace(), True, SimpleNamespace(id=dos_lang), "")
    s.finished.emit(0)
    pump()
    ok("a DOS session: the Error List is refreshed when it finishes", COUNT.get("DOS errors refreshed") == 1, COUNT)
finally:
    restore()

# ------------------------------------------------------------------ stop / resume / end
try:
    patch(win.cpu_view, "on_stopped", lambda info: note("CPU view stop"))
    patch(win.cpu_view, "on_resumed", lambda: note("CPU view resumed"))
    patch(win.cpu_view, "on_finished", lambda: note("CPU view end"))
    patch(win.native_debug, "on_stopped", lambda info: note("native debug stop"))
    patch(win.native_debug, "on_resumed", lambda: note("native debug resumed"))
    patch(win.native_debug, "on_finished", lambda: note("native debug end"))
    info = SimpleNamespace(refs={}, thread_id=0, file="Form1.py", line=1)
    gen0 = getattr(win, "_dbgx_gen", 0)
    COUNT.clear()
    ORDER.clear()
    win._on_stopped(info)
    pump()
    for want in ("window shows the stop", "CPU view stop", "native debug stop"):
        ok(f"a stop: {want}", COUNT.get(want) == 1, COUNT)
    ok("a stop: the debug views' generation is bumped before the window shows the stop",
       f"window stop gen={gen0 + 1}" in ORDER, ORDER)
    COUNT.clear()
    win._on_resumed()
    pump()
    for want in ("window shows resumed", "CPU view resumed", "native debug resumed"):
        ok(f"resumed: {want}", COUNT.get(want) == 1, COUNT)
    ok("resumed: the debug views' generation is bumped", getattr(win, "_dbgx_gen", 0) == gen0 + 2,
       getattr(win, "_dbgx_gen", None))
    COUNT.clear()
    win.session = None
    win._on_finished(0, None)
    pump()
    for want in ("window shows the end", "CPU view end", "native debug end"):
        ok(f"end of the program: {want}", COUNT.get(want) == 1, COUNT)
finally:
    restore()

# Run to Cursor: removes its temporary breakpoint at the stop
try:
    removed: list = []
    win.session = SimpleNamespace(set_breakpoint=lambda f, line, on: removed.append((f, line, on)),
                                  running=lambda: True, paused=True)
    win._run_to = ("Form1.py", 7)
    win.breakpoints = {}
    win._on_stopped(SimpleNamespace(refs={}, thread_id=0))
    pump()
    ok("Run to Cursor: its temporary breakpoint is removed at the stop", removed == [("Form1.py", 7, False)]
       and win._run_to is None, (removed, win._run_to))
finally:
    win.session = None
    restore()

# Run to Cursor with nothing running: one extra breakpoint for that run only
try:
    win.breakpoints = {"Form1.py": {2}}
    BP_SEEN.clear()
    win.open_code("Form1")
    pump()
    cv = win.codeviews["Form1"]
    cv.editor.setCursorPosition(4, 0)
    act = next((a for a in win.findChildren(type(win.a_run)) if "Run to Cursor" in a.text().replace("&", "")), None)
    ok("Run to Cursor command found", act is not None)
    if act is not None:
        act.trigger()
        pump()
        seen = BP_SEEN[-1] if BP_SEEN else []
        ok("Run to Cursor: the window runs with the user's breakpoint and the temporary one",
           any(b[1] == 3 for b in seen) and any(b[1] == 5 for b in seen), seen)
        after = list(win._all_breakpoints())
        ok("Run to Cursor: afterwards only the user's breakpoints are left", all(b[1] != 5 for b in after), after)
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("Run to Cursor part", False, e)

try:
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
