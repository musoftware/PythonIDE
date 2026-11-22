"""Characterization test of the editors that open their own files in the IDE (image editor, ...): what the
user sees must stay the same while they move from wrapping MainWindow's methods to the extension points
(radide/extension_points.py).

Per editor (one row of EDITORS), in the real MainWindow (offscreen) with a Python project open:
  * File > Open of its file type opens its editor as the current tab; opening it again reuses that tab
  * a .py file still opens in the code editor (the editor does not take files that are not its own)
  * after an edit the IDE knows there are unsaved changes (_any_modified); Save All writes the file and
    clears that state; the closing question then has nothing to ask
  * its Solution Explorer nodes are there (when it adds any)
  * when the editor is migrated: it is registered with win.extension_points (and no longer wraps the window)

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_document_providers.py [scratch]
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
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-docproviders"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtGui import QColor, QImage  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
ASKED: list[str] = []


def _question(*a, **k):
    ASKED.append(str(a[2] if len(a) > 2 else k.get("text", "")))
    return QMessageBox.StandardButton.Discard


QMessageBox.question = staticmethod(_question)
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


# ------------------------------------------------------------------ the editors
def _make_png(path: Path) -> None:
    img = QImage(16, 16, QImage.Format.Format_ARGB32)
    img.fill(QColor("white"))
    img.save(str(path))


def _edit_image(ed) -> None:
    ed.doc.checkpoint()
    ed.doc.set_pixel(3, 3, QColor("red"))
    ed.doc.set_modified(True)


def _image_tree(win) -> bool:
    tree = win.solution
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        if it.text(0) == "Resources":
            return True
        stack.extend(it.child(i) for i in range(it.childCount()))
    return False


def _make_report(path: Path) -> None:
    from radide.reports import new_report_file
    new_report_file(path.parent, path.name[:-len(".rpt.json")])


def _edit_report(ed) -> None:
    ed.push_undo()
    ed.defn["title"] = "Edited by the test"
    ed.set_modified(True)


def _report_tree(win) -> bool:
    tree = win.solution
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        if (it.data(0, 0x0100) or ("",))[0] == "reports":
            return True
        stack.extend(it.child(i) for i in range(it.childCount()))
    return False


def _before_save_report(proj: Path) -> None:
    (proj / "radreport.py").unlink(missing_ok=True)       # Save All puts the report runtime back


def _after_save_report(proj: Path) -> bool:
    return (proj / "radreport.py").is_file()


def _make_scene(path: Path) -> None:
    from radide.games.model import Scene
    Scene.new("Level1").save(path)


def _edit_scene(ed) -> None:
    ed.change("Resize", lambda: setattr(ed.scene, "width", ed.scene.width + 32))


# name, feature attribute on win, file, make(path), editor class, edit(ed), tree check, open_module (a project
# file opened from Solution Explorer), before_save(proj) / after_save(proj) (work Save All does afterwards)
EDITORS = [
    dict(name="image editor", feature="image_feature", file="logo.png", make=_make_png,
         cls="radide.imaging.editor.IconEditor", edit=_edit_image, tree=_image_tree),
    dict(name="report designer", feature="reports", file="Sales.rpt.json", make=_make_report,
         cls="radide.reports.designer.ReportDesigner", edit=_edit_report, tree=_report_tree, module=True,
         before_save=_before_save_report, after_save=_after_save_report),
    # (its Solution Explorer scenes are shown for game projects only: not this Python Tk project)
    dict(name="game scene designer", feature="game_designer", file="Level1.scene", make=_make_scene,
         cls="radide.games.scene_editor.SceneEditor", edit=_edit_scene, module=True),
]

# ------------------------------------------------------------------ the IDE
from radide import workspace  # noqa: E402
from radide.app import MainWindow  # noqa: E402

proj = SCRATCH / "DocProv"
workspace.create_project(proj, "DocProv", "python-tk")
win = MainWindow()
win.resize(1200, 800)
win.show()
pump()
win.open_project(proj, ask=False)
pump()
ok("a fresh project has no unsaved changes", not win._any_modified())

for row in EDITORS:
    name, feat_attr, fname, make, cls_path, edit = (row[k] for k in ("name", "feature", "file", "make",
                                                                     "cls", "edit"))
    tree_check = row.get("tree")
    try:
        mod, _, cls_name = cls_path.rpartition(".")
        cls = getattr(__import__(mod, fromlist=[cls_name]), cls_name)
        path = proj / fname
        make(path)
        before = path.read_bytes()
        ed = win.open_any_file(path)
        pump()
        ok(f"{name}: File > Open opens its editor", isinstance(ed, cls), type(ed))
        ok(f"{name}: ... as the current tab", win.tabs.currentWidget() is ed)
        tabs = win.tabs.count()
        again = win.open_any_file(path)
        pump()
        ok(f"{name}: opening it again reuses the tab", again is ed and win.tabs.count() == tabs,
           (again is ed, tabs, win.tabs.count()))
        if row.get("module"):
            via = win.open_module(fname)
            pump()
            ok(f"{name}: opened from Solution Explorer (open_module) in the same tab", via is ed, type(via))
        ok(f"{name}: no unsaved changes before an edit", not win._any_modified())
        edit(ed)
        pump()
        ok(f"{name}: after an edit the IDE has unsaved changes", win._any_modified())
        if row.get("before_save"):
            row["before_save"](proj)
        saved = win.save_all()
        pump()
        ok(f"{name}: Save All succeeds", saved is True, saved)
        ok(f"{name}: Save All wrote the file", path.read_bytes() != before)
        if row.get("after_save"):
            ok(f"{name}: its work after Save All was done", row["after_save"](proj))
        ok(f"{name}: no unsaved changes after Save All", not win._any_modified())
        ASKED.clear()
        ok(f"{name}: closing asks nothing after Save All", win._confirm_close_inner() and not ASKED, ASKED)
        if tree_check is not None:
            win._fill_solution()
            pump()
            ok(f"{name}: its Solution Explorer nodes are there", tree_check(win))
        feature = getattr(win, feat_attr, None)
        points = getattr(win, "extension_points", None)
        if points is not None and feature is not None and feature in points.document_providers():
            ok(f"{name}: registered as a document provider", True)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        ok(f"{name}: part", False, e)

# a file that is nobody's: the code editor
try:
    py = proj / "helper.py"
    py.write_text("x = 1\n", encoding="utf-8")
    ed = win.open_any_file(py)
    pump()
    ok("a .py file still opens in the code editor", ed is not None and hasattr(ed, "text") and "x = 1" in ed.text(),
       type(ed))
except Exception as e:  # noqa: BLE001
    ok("code editor part", False, e)

try:
    for i in range(win.tabs.count()):
        w = win.tabs.widget(i)
        e = getattr(w, "editor", None)
        if e is not None and hasattr(e, "setModified"):
            e.setModified(False)
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
