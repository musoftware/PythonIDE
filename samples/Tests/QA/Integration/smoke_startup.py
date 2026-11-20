"""QA round 7 smoke: IDE starts offscreen with every feature module loaded; menus for new features; no Output errors."""
import os, sys, re, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
import tempfile
OUT = os.path.join(os.environ.get("QA_OUT") or os.path.join(tempfile.gettempdir(), "radide-qa"), "out_smoke_"+(sys.argv[1] if len(sys.argv)>1 else "en")); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, ROOT)
import PyQt6.QtWebEngineWidgets  # noqa
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer
from PyQt6.QtWidgets import QApplication
QCoreApplication.setOrganizationName("RADIDE-TEST"); QCoreApplication.setApplicationName("RADIDE-TEST-qa7smoke")
app = QApplication(sys.argv[:1]); QSettings().clear()
LANG = sys.argv[1] if len(sys.argv)>1 else "en"
QSettings().setValue("options/ui_language", LANG); QSettings().sync()
import radide.features as F
import importlib
installed, failed = [], []
_orig_import = importlib.import_module
def _imp(name, *a, **k):
    m = _orig_import(name, *a, **k)
    if name.startswith("radide.features.") and callable(getattr(m, "install", None)):
        inst = m.install
        def wrapped(win, _i=inst, _n=name):
            try:
                _i(win); installed.append(_n.split(".")[-1])
            except Exception:
                failed.append(_n.split(".")[-1]); raise
        m.install = wrapped
    return m
importlib.import_module = _imp
from radide.app import MainWindow
def pump(sec=1.0):
    t = time.time()
    while time.time() - t < sec: app.processEvents(); time.sleep(0.02)
killer = QTimer(); killer.timeout.connect(lambda: QApplication.activeModalWidget() and QApplication.activeModalWidget().close()); killer.start(300)
t0 = time.time(); w = MainWindow(); w.resize(1400, 900); w.show(); pump(5)
importlib.import_module = _orig_import
print("startup %.1fs" % (time.time() - t0))
import pkgutil
feats = sorted(m.name for m in pkgutil.iter_modules(F.__path__) if not m.name.startswith("_"))
print("feature modules", len(feats), "installed", len(installed), "failed", failed)
print("not installed:", [f for f in feats if f not in installed])
txt = w.output.toPlainText()
bad = [l for l in txt.splitlines() if re.search(r"Traceback|failed to load|Error|error", l)]
print("OUTPUT-ERRORS", len(bad)); print("\n".join(bad[:60]))

def walk(menu, path=""):
    res = []
    for a in menu.actions():
        t = a.text().replace("&", "")
        if a.menu():
            res += walk(a.menu(), path + t + " > ")
        elif t:
            res.append(path + t)
    return res
allacts = []
for a in w.menuBar().actions():
    if a.menu():
        allacts += walk(a.menu(), a.text().replace("&", "") + " > ")
open(os.path.join(OUT, "menus.txt"), "w", encoding="utf-8").write("\n".join(allacts))
from radide import i18n
print("LANG in effect", i18n.language(), "rtl", QApplication.layoutDirection())
want = ["New Notebook", "Open Remote", "Remote Explorer", "Docker", "Split Editor Right", "Compare", "Hex Editor",
        "Code Snippets Manager", "Macro", "Keymap", "Image Editor", "Resources", "Language Servers and Debuggers",
        "Extensions", "Accessibility Check", "3D Scene", "Debug Expo"]
for k in want:
    hits = [x for x in allacts if k.lower() in x.lower() or i18n.tr(k) in x]
    print(("PASS " if hits else "FAIL ") + "menu " + k, hits[:3])
print("top menus:", [a.text() for a in w.menuBar().actions()])
w.grab().save(os.path.join(OUT, "ide_start.png"))
open(os.path.join(OUT, "output.txt"), "w", encoding="utf-8").write(w.output.toPlainText())
w.close(); pump(1); QSettings().clear(); print("DONE")
os._exit(0)
