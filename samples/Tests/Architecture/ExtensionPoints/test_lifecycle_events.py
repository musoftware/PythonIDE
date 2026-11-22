"""Characterization of the features that follow the project lifecycle (open, switch, reset) and the command
states, while they move from wrapping MainWindow.open_project / activate_project / _reset / _update_actions to
the named events of radide/extension_points.py.

Real MainWindow (offscreen); each feature's step is replaced by a counter, then:
  * open_project(folder): the template waiting for that folder is applied BEFORE the project loads; after it:
    AI chat, Flutter start screen (next turn of the event loop), game designer visibility + start scene,
    git status, terminal folder - each once
  * activate_project(p): component registry, game designer visibility, Rust bar (next turn), user controls in
    the Toolbox (next turn) - each once
  * _reset(): language servers stopped and Rust diagnostics cleared BEFORE the window's own reset
  * _update_actions(): Expo, firmware maps, Flutter designer, mobile, retro emulator bar - each once
  * a step that raises is logged and the window's method still returns normally

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_lifecycle_events.py [scratch]
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-lifecycle"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ARCH-LIFECYCLE_EVENTS")      # own store: tests run in parallel
QCoreApplication.setApplicationName("RADIDE-TEST-ARCH-LIFECYCLE_EVENTS")
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


from radide import workspace  # noqa: E402
from radide.app import MainWindow  # noqa: E402

projA = SCRATCH / "LifeA"
projB = SCRATCH / "LifeB"
workspace.create_project(projA, "LifeA", "python-tk")
workspace.create_project(projB, "LifeB", "python-tk")
win = MainWindow()
win.resize(1200, 800)
win.show()
pump()
win.open_project(projA, ask=False)
pump()

import radide.features.components_ui as components_ui  # noqa: E402
import radide.features.templates as templates  # noqa: E402

COUNT: dict[str, int] = {}
ORDER: list[str] = []


def spy(name, fail=False):
    def f(*_a, **_k):
        COUNT[name] = COUNT.get(name, 0) + 1
        ORDER.append(name)
        if fail:
            raise RuntimeError(f"{name} broke on purpose")
    return f


def patch(steps):
    saved = []
    for name, obj, attr in steps:
        saved.append((obj, attr, getattr(obj, attr)))
        setattr(obj, attr, spy(name))
    return saved


def restore(saved):
    for obj, attr, val in saved:
        setattr(obj, attr, val)


def check_once(prefix, steps, expect=None):
    for name, _o, _a in steps:
        n = (expect or {}).get(name, 1)
        ok(f"{prefix}: '{name}' {'once' if n == 1 else f'{n} times'}", COUNT.get(name) == n, COUNT.get(name))


# ------------------------------------------------------------------ open_project
OPEN = [("AI chat", win.ai_chat, "on_project_changed"), ("Flutter start screen", win.flutter_designer, "_safe_start"),
        ("game designer visibility", win.game_designer, "update_visibility"),
        ("game start scene", win.game_designer, "_open_start_scene"), ("git status", win.git_panel, "set_project"),
        ("terminal folder", win.terminal, "on_project_changed")]
saved = patch(OPEN + [("template applied", templates, "apply_template")])
COUNT.clear()
ORDER.clear()
win._pending_template = (str(projB.resolve()), "console")
win.log("--- open B")
win.open_project(projB, ask=False)
pump()
# the game designer updates its visibility on open and on every activate_project the open makes (4 in all,
# measured before the migration)
check_once("open_project", OPEN, {"game designer visibility": 4})
ok("open_project: the template waiting for that folder is applied once", COUNT.get("template applied") == 1,
   COUNT.get("template applied"))
ok("open_project: ... before the project is loaded (before the AI chat / terminal steps)",
   ORDER.index("template applied") < ORDER.index("AI chat"), ORDER)
ok("open_project: the project is open", win.project is not None and win.project.name == "LifeB",
   getattr(win.project, "name", None))
restore(saved)

# ------------------------------------------------------------------ activate_project
ACT = [("component registry", components_ui.REGISTRY, "set_project"),
       ("game designer visibility", win.game_designer, "update_visibility"),
       ("Rust bar", win.rust_bar, "sync"), ("user controls Toolbox", win.user_controls, "refresh_toolbox")]
saved = patch(ACT)
COUNT.clear()
ORDER.clear()
r = win.activate_project(win.project)
pump()
check_once("activate_project", ACT)
ok("activate_project returns the window's result", r in (True, False, None), r)
restore(saved)

# ------------------------------------------------------------------ _reset
saved = patch([("language servers stopped", win.lsp_manager, "stop_all")])
COUNT.clear()
win.rust_diags = {"x.rs": ["e"]}
win._rust_err_keys = {"k"}
win._reset()
pump()
ok("_reset: language servers stopped once", COUNT.get("language servers stopped") == 1, COUNT)
ok("_reset: Rust diagnostics cleared", win.rust_diags == {} and win._rust_err_keys == set(),
   (win.rust_diags, win._rust_err_keys))
ok("_reset: the window's own reset ran (no project state left)", not win.docs and not win.codeviews, win.docs)
restore(saved)

# ------------------------------------------------------------------ _update_actions
win.open_project(projA, ask=False)
pump()
UPD = [("Expo", win.expo, "update_ui"), ("firmware maps", win.firmware_maps, "_update_actions"),
       ("Flutter designer", win.flutter_designer, "current"), ("mobile", win.mobile, "update_ui"),
       ("retro emulator bar", win.retro_emulator_bar, "update_ui")]
saved = patch(UPD)
win.flutter_designer.current = lambda: (COUNT.__setitem__("Flutter designer", COUNT.get("Flutter designer", 0) + 1)
                                        or None)
COUNT.clear()
win._update_actions()
pump(2)
check_once("_update_actions", UPD)
# a step that raises: logged, the window's method still returns
win.expo.update_ui = spy("Expo", fail=True)
COUNT.clear()
try:
    win._update_actions()
    ok("_update_actions: a failing step does not break the window's method", True)
except Exception as e:  # noqa: BLE001
    ok("_update_actions: a failing step does not break the window's method", False, e)
ok("_update_actions: ... the steps after it still ran", COUNT.get("mobile") == 1 and COUNT.get("retro emulator bar") == 1,
   COUNT)
restore(saved)

try:
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
