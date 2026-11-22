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


def _make_scene3d(path: Path) -> None:
    from radide.games3d.model import default_scene
    default_scene(path.stem).save(path)


def _edit_scene3d(ed) -> None:
    ed.scene.sky = "#102030"
    ed.record()


def _make_page(path: Path) -> None:
    path.write_text("<!DOCTYPE html>\n<html><head><title>T</title></head><body><h1>Hello</h1></body></html>\n",
                    encoding="utf-8")


def _open_design_view(path: Path):
    from radide.web_site import design
    dv = design.open_design_view(win, path)
    import time
    t0 = time.time()                      # the page is in the browser engine: let it load before editing
    while time.time() - t0 < 20 and not getattr(dv, "_ready", True):
        pump()
    pump(20)
    return dv


def _edit_page(dv) -> None:
    dv._set_modified(True)


def _design_provider(win):
    return next((p for p in win.extension_points.document_providers()
                 if type(p).__name__ == "DesignViewDocuments"), None)


def _make_tform(path: Path) -> None:
    from radide.retro.design.textmode.model import new_screen
    new_screen(path.stem).save(path)


def _edit_tform(d) -> None:
    d.screen.props["title"] = "Edited by the test"


def _make_nes(path: Path) -> None:
    path.write_bytes(b"NES\x1a\x01\x01\x00\x00" + bytes(8) + bytes(16384 + 8192))


def _make_blob(path: Path) -> None:
    path.write_bytes(bytes(range(256)) * 8)


def _make_cur(path: Path) -> None:
    from radide.imaging.document import ImageDocument
    doc = ImageDocument.new_icon()
    doc.cursor = True
    doc.path = path
    doc.save()


def _make_gbmap(path: Path) -> None:
    from radide.retro.design.game import new_design
    new_design("gb", path.stem).save(path)


def _edit_design(ed) -> None:
    ed._begin()
    ed.doc.settings["edited_by_test"] = 1
    ed._commit("Test edit")


def _make_tbl(path: Path) -> None:
    from radide.retro.gfx.textable import ascii_table
    ascii_table().save(path)


def _edit_tbl(ed) -> None:
    from radide.retro.gfx.textable import TextTable
    t = TextTable(name=ed.retro_path.name)
    t.entries[b"\x41"] = "Z"
    ed.set_table(t)
    ed.set_modified(True)


def _make_nb(path: Path) -> None:
    from radide.notebook.model import Notebook
    Notebook.new(path).save(path)


def _edit_nb(v) -> None:
    v.set_modified(True)


def _make_fscreen(path: Path) -> None:
    from radide.flutterdesign.model import Screen
    Screen.new(path.name.split(".")[0]).save(path)


def _edit_fscreen(ed) -> None:
    ed.set_prop(ed.screen.tree.get("id"), "backgroundColor", "#112233")


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
    dict(name="3D scene editor", feature="scenes3d", file="World.scene3d", make=_make_scene3d,
         cls="radide.games3d.editor.Scene3DEditor", edit=_edit_scene3d, module=True),
    # web page Design View: opened by its own command (a .html file from File > Open is code), saved by Save All
    dict(name="web Design View", feature=_design_provider, file="index.html", make=_make_page,
         open=_open_design_view, cls="radide.web_site.design.DesignView", edit=_edit_page),
    dict(name="text-mode designer", feature="dos_designer", file="Main.tform", make=_make_tform,
         cls="radide.retro.design.textmode.designer.TuiDesigner", edit=_edit_tform, module=True),
    dict(name="retro game designer (.gbmap)", feature="retro_designs", file="Map1.gbmap", make=_make_gbmap,
         cls="radide.retro.design.game.ui.GameDesigner", edit=_edit_design),
    dict(name="retro text table (.tbl)", feature="retro_gfx", file="game.tbl", make=_make_tbl,
         cls="radide.retro.gfx.ui_text.TableEditor", edit=_edit_tbl),
    dict(name="notebook (.ipynb)", feature="notebook_feature", file="Analysis.ipynb", make=_make_nb,
         cls="radide.notebook.view.NotebookView", edit=_edit_nb),
    dict(name="Flutter screen designer", feature="flutter_designer", file="Home.fscreen.json", make=_make_fscreen,
         cls="radide.flutterdesign.designer.FlutterDesigner", edit=_edit_fscreen, module=True),
    # viewers of binary files: opened (and reused), no Save All part to check (a source ROM is read-only)
    dict(name="ROM workbench (.nes)", feature="rom_workbench", file="game.nes", make=_make_nes,
         cls="radide.retro.rom.hexdoc.HexDocument", module=True, readonly=True),
    dict(name="hex view (unknown binary)", feature=None, file="blob.xyz", make=_make_blob,
         cls="radide.features.editor_extras.HexEditorView", readonly=True, returns_none=True),
    # a cursor is an image: the image editor, not the hex view (.cur is binary and not in NOT_HEX_EXT)
    dict(name="cursor file (.cur)", feature="image_feature", file="arrow.cur", make=_make_cur,
         cls="radide.imaging.editor.IconEditor", readonly=True),
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
    name, feat_attr, fname, make, cls_path, edit = (row.get(k) for k in ("name", "feature", "file", "make",
                                                                         "cls", "edit"))
    tree_check = row.get("tree")
    try:
        mod, _, cls_name = cls_path.rpartition(".")
        cls = getattr(__import__(mod, fromlist=[cls_name]), cls_name)
        path = proj / fname
        make(path)
        before, before_mtime = path.read_bytes(), path.stat().st_mtime_ns
        opener = row.get("open") or win.open_any_file        # an editor with its own way in (Design View)
        how = "its own command" if row.get("open") else "File > Open"
        got = opener(path)
        pump()
        ed = win.tabs.currentWidget()
        ok(f"{name}: {how} opens its editor as the current tab", isinstance(ed, cls),
           f"current tab: {type(ed).__name__}")
        if row.get("returns_none"):            # the hex view's API: opens the tab, returns None
            ok(f"{name}: ... and returns None (its API)", got is None, type(got))
        else:
            ok(f"{name}: ... and returns that editor", got is ed, type(got))
        tabs = win.tabs.count()
        again = opener(path)
        pump()
        ok(f"{name}: opening it again reuses the tab", win.tabs.currentWidget() is ed and win.tabs.count() == tabs
           and (again is ed or (again is None and row.get("returns_none"))), (type(again), tabs, win.tabs.count()))
        if row.get("module"):
            via = win.open_module(fname)
            pump()
            ok(f"{name}: opened from Solution Explorer (open_module) in the same tab", via is ed, type(via))
        if row.get("readonly"):
            continue
        ok(f"{name}: no unsaved changes before an edit", not win._any_modified())
        edit(ed)
        pump()
        ok(f"{name}: after an edit the IDE has unsaved changes", win._any_modified())
        if row.get("before_save"):
            row["before_save"](proj)
        saved = win.save_all()
        pump()
        ok(f"{name}: Save All succeeds", saved is True, saved)
        ok(f"{name}: Save All wrote the file", path.read_bytes() != before or path.stat().st_mtime_ns != before_mtime)
        if row.get("after_save"):
            ok(f"{name}: its work after Save All was done", row["after_save"](proj))
        ok(f"{name}: no unsaved changes after Save All", not win._any_modified())
        ASKED.clear()
        ok(f"{name}: closing asks nothing after Save All", win._confirm_close_inner() and not ASKED, ASKED)
        edit(ed)                                   # the user's way: the Save All command / Ctrl+S
        pump()
        win.a_save.trigger()
        pump()
        ok(f"{name}: Ctrl+S (Save All command) saves it too", not win._any_modified())
        if tree_check is not None:
            win._fill_solution()
            pump()
            ok(f"{name}: its Solution Explorer nodes are there", tree_check(win))
        feature = feat_attr(win) if callable(feat_attr) else getattr(win, feat_attr, None)
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
