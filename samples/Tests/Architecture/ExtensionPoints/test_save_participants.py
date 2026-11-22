"""Characterization of the features that take part in Save All and the closing question without opening files
from File > Open (firmware workbench, firmware map editor, PE / MFC workbench), while they move from
wrapping MainWindow to radide/extension_points.py.

A fake document tab (is_modified / save / read_only) is put into each feature's own document list, in the
real MainWindow (offscreen) with a Python project open:
  * a modified document -> the IDE has unsaved changes (_any_modified)
  * Save All saves it (firmware workbench, map editor) and the unsaved state is gone; a read-only firmware
    workbench is not saved
  * PE / MFC workbench: Save All does NOT save it - saving an edited program always asks where (Save As) -
    so the IDE still reports unsaved changes afterwards (current behavior, kept)
  * firmware workbench: refilling Solution Explorer schedules its auto-open of an ECU project
  * once migrated: each feature is registered with win.extension_points

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_save_participants.py [scratch]
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
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-saveparts"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, pyqtSignal  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ARCH-SAVE_PARTICIPANTS")      # own store: tests run in parallel
QCoreApplication.setApplicationName("RADIDE-TEST-ARCH-SAVE_PARTICIPANTS")
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


class FakeDoc(QWidget):
    modifiedChanged = pyqtSignal(bool)

    def __init__(self, read_only: bool = False):
        super().__init__()
        self.modified = False
        self.read_only = read_only
        self.saves = 0

    def is_modified(self) -> bool:
        return self.modified

    def save(self) -> bool:
        self.saves += 1
        self.modified = False
        return True


from radide import workspace  # noqa: E402
from radide.app import MainWindow  # noqa: E402

proj = SCRATCH / "SaveParts"
workspace.create_project(proj, "SaveParts", "python-tk")
win = MainWindow()
win.resize(1200, 800)
win.show()
pump()
win.open_project(proj, ask=False)
pump()
ok("a fresh project has no unsaved changes", not win._any_modified())


def put(feature, doc, key: str) -> None:
    win._show_tab(doc, key)
    if isinstance(feature.docs, dict):
        feature.docs[key] = doc
    else:
        feature.docs.append(doc)


def take(feature, doc, key: str) -> None:
    if isinstance(feature.docs, dict):
        feature.docs.pop(key, None)
    elif doc in feature.docs:
        feature.docs.remove(doc)
    i = win.tabs.indexOf(doc)
    if i >= 0:
        win.tabs.removeTab(i)


for name, attr, saved_by_save_all in (("firmware workbench", "firmware_ide", True),
                                      ("firmware map editor", "firmware_maps", True),
                                      ("PE / MFC workbench", "pe_workbench", False)):
    feature = getattr(win, attr, None)
    if not ok(f"{name}: feature installed (win.{attr})", feature is not None):
        continue
    try:
        doc = FakeDoc()
        key = f"fake-{attr}"
        put(feature, doc, key)
        ok(f"{name}: no unsaved changes before an edit", not win._any_modified())
        doc.modified = True
        ok(f"{name}: a modified document -> the IDE has unsaved changes", win._any_modified())
        saved = win.save_all()
        pump()
        ok(f"{name}: Save All succeeds", saved is True, saved)
        if saved_by_save_all:
            ok(f"{name}: Save All saved it once", doc.saves == 1, doc.saves)
            ok(f"{name}: no unsaved changes after Save All", not win._any_modified())
        else:
            ok(f"{name}: Save All does not save it (an edited program is saved with Save As)", doc.saves == 0,
               doc.saves)
            ok(f"{name}: ... so the IDE still has unsaved changes", win._any_modified())
        take(feature, doc, key)
        if attr == "firmware_ide":
            ro = FakeDoc(read_only=True)
            ro.modified = True
            put(feature, ro, "fake-ro")
            win.save_all()
            pump()
            ok(f"{name}: a read-only workbench is not saved", ro.saves == 0, ro.saves)
            take(feature, ro, "fake-ro")
            calls = []
            orig = feature._maybe_auto_open
            feature._maybe_auto_open = lambda: calls.append(1)
            win._fill_solution()
            pump(10)
            feature._maybe_auto_open = orig
            ok(f"{name}: refilling Solution Explorer schedules its ECU auto-open", calls == [1], calls)
        ok(f"{name}: no unsaved changes left", not win._any_modified())
        if feature in win.extension_points.document_providers():
            ok(f"{name}: registered as a document provider", True)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        ok(f"{name}: part", False, e)

# ------------------------------------------------------------------ every way of saving: the same steps
try:
    ep = win.extension_points
    names = [n for n, _ in ep._after_save]
    for want in ("checks after save", "components", "mobile", "reports"):
        ok(f"save listener registered: {want}", want in names, names)
    ok("remote files take part in Save All (RemoteDocuments)",
       any(type(p).__name__ == "RemoteDocuments" for p in ep.document_providers()))
    seen: list = []
    ep.add_save_listener(lambda okv: seen.append(("after", okv)), "test", before=lambda: seen.append("before"))
    win.save_all()
    pump()
    ok("Save All from code: before / after listeners with the result", seen == ["before", ("after", True)], seen)
    seen.clear()
    win.a_save.trigger()                                 # the Save All command / Ctrl+S
    pump()
    ok("the Save All command (Ctrl+S) goes through the same steps", seen == ["before", ("after", True)], seen)
    fw = getattr(win, "firmware_ide", None)
    if fw is not None:
        doc = FakeDoc()
        put(fw, doc, "fake-ctrl-s")
        doc.modified = True
        win.a_save.trigger()
        pump()
        ok("Ctrl+S saves a document of a feature too (firmware workbench)", doc.saves >= 1 and not doc.modified,
           doc.saves)
        take(fw, doc, "fake-ctrl-s")
    calls = []
    import radide.tools as _tools
    orig_checks = _tools.run_checks
    _tools.run_checks = lambda w: calls.append(1)
    try:
        win.a_save.trigger()
        pump(10)
    finally:
        _tools.run_checks = orig_checks
    ok("the checks run after a successful Save All (once)", calls == [1], calls)
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("save steps part", False, e)

try:
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
