"""Characterization of the features that add to Solution Explorer after it is filled (databases panel, firmware
analysis / ECU project nodes, git colours, retro hints, web docks + preview reset, VB6 decoration), while they
move from wrapping MainWindow._fill_solution to win.extension_points.add_solution_contributor.

In the real MainWindow (offscreen) with a Python project open, each feature's step is replaced by a counter:
one refill of Solution Explorer (win._fill_solution) runs every step exactly once, and a step that raises
is logged without stopping the others or emptying the tree.

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_solution_contributors.py [scratch]
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
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-solcontrib"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ARCH-SOLUTION_CONTRIBUTORS")      # own store: tests run in parallel
QCoreApplication.setApplicationName("RADIDE-TEST-ARCH-SOLUTION_CONTRIBUTORS")
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


def pump(n: int = 5) -> None:
    for _ in range(n):
        app.processEvents()


from radide import workspace  # noqa: E402
from radide.app import MainWindow  # noqa: E402

proj = SCRATCH / "SolContrib"
workspace.create_project(proj, "SolContrib", "python-tk")
win = MainWindow()
win.resize(1200, 800)
win.show()
pump()
win.open_project(proj, ask=False)
pump()
from radide.foreign import vb6_project  # noqa: E402
vb6_project.install_hooks(win)          # installed when a VB6 project opens

import radide.features.retro_dev as retro_dev  # noqa: E402
import radide.features.web_workspace as web_workspace  # noqa: E402

COUNT: dict[str, int] = {}


def counter(name, fail=False):
    def f(*_a, **_k):
        COUNT[name] = COUNT.get(name, 0) + 1
        if fail:
            raise RuntimeError(f"{name} broke on purpose")
    return f


# (name, object, attribute) - the step each feature runs after Solution Explorer is filled
STEPS = [
    ("databases panel refresh", win.databases, "refresh"),
    ("firmware analysis nodes", win.firmware_analysis, "_add_tree_nodes"),
    ("ECU project nodes", win.ecu_project_feature, "_add_tree_nodes"),
    ("ECU project notice", win.ecu_project_feature, "_maybe_notice"),
    ("git colours", win.git_panel, "colour_solution"),
    ("retro hints", retro_dev, "_add_hint_nodes"),
    ("web designer docks", web_workspace, "update_designer_docks"),
    ("VB6 decoration", vb6_project, "decorate_tree"),
]
saved = {}
for name, obj, attr in STEPS:
    saved[name] = getattr(obj, attr)
    setattr(obj, attr, counter(name))
try:
    win._fill_solution()
    pump(10)
    for name, _o, _a in STEPS:
        ok(f"one refill runs '{name}' once", COUNT.get(name) == 1, COUNT.get(name))
    # a step that raises: logged, the others still run, the tree is still filled
    COUNT.clear()
    win.git_panel.colour_solution = counter("git colours", fail=True)
    log_before = win.output.toPlainText()
    win._fill_solution()
    pump(10)
    ok("a failing step does not stop the others",
       all(COUNT.get(n) == 1 for n, _o, _a in STEPS), COUNT)
    ok("... and Solution Explorer is still filled", win.solution.topLevelItemCount() > 0)
    ok("... and the failure is in the Output window", "broke on purpose" in win.output.toPlainText()[len(log_before):]
       or "git" in win.output.toPlainText()[len(log_before):].lower(), win.output.toPlainText()[-400:])
finally:
    for name, obj, attr in STEPS:
        setattr(obj, attr, saved[name])

try:
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
