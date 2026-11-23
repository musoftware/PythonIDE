"""Closing the IDE with no project open but an edited file in a feature's editor (here the image editor).

"Save changes?" -> Save must save the file AND close the IDE. It used to save the file, then Save All returned
False because there was no project, which the closing question takes for a failed save: the IDE stayed open
and asked again (only Discard closed it).

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_save_no_project.py [scratch]
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
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-savenoproject"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtGui import QColor, QImage  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ARCH-SAVE_NO_PROJECT")      # own store: tests run in parallel
QCoreApplication.setApplicationName("RADIDE-TEST-ARCH-SAVE_NO_PROJECT")
app = QApplication(sys.argv[:1])
QSettings().clear()
ASKED: list[str] = []
QMessageBox.question = staticmethod(lambda *a, **k: (ASKED.append("save?"), QMessageBox.StandardButton.Save)[1])
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


from radide.app import MainWindow  # noqa: E402

win = MainWindow()
win.resize(1100, 750)
win.show()
pump()
ok("no project is open", win.project is None)
png = SCRATCH / "loose.png"
img = QImage(16, 16, QImage.Format.Format_ARGB32)
img.fill(QColor("white"))
img.save(str(png))
before = png.read_bytes()
ed = win.open_any_file(png)
pump()
ok("a loose image opens in the image editor", type(ed).__name__ == "IconEditor", type(ed))
ed.doc.checkpoint()
ed.doc.set_pixel(2, 2, QColor("blue"))
ed.doc.set_modified(True)
pump()
ok("the IDE knows about the unsaved image", win._any_modified())
ok("Save All with no project but a saved file succeeds", win.save_all() is True)
ok("... and the image was written", png.read_bytes() != before)
ed.doc.checkpoint()
ed.doc.set_pixel(3, 3, QColor("red"))
ed.doc.set_modified(True)
pump()
ASKED.clear()
closed = win.close()
pump()
ok("closing: 'Save changes?' is asked once", ASKED == ["save?"], ASKED)
ok("closing: Save -> the IDE closes", closed is True, closed)
ok("closing: ... and the image was saved", not ed.doc.is_modified())

QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
