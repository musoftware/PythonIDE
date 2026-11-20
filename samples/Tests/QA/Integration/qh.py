"""Shared QA harness for round-7 feature checks (test QSettings, widget.grab only)."""
import os, sys, time, json, atexit
REAL = os.environ.get("QA_REAL") == "1"          # real Windows display (window moved off-screen) for web content
if not REAL:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
import tempfile
OUT = os.environ.get("QA_OUT") or os.path.join(tempfile.gettempdir(), "radide-qa")
SHOTS = os.path.join(OUT, "shots"); os.makedirs(SHOTS, exist_ok=True)
WORK = os.path.join(OUT, "work"); os.makedirs(WORK, exist_ok=True)
import PyQt6.QtWebEngineWidgets  # noqa: F401
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer, QPoint
from PyQt6.QtWidgets import QApplication, QMessageBox
NAME = os.environ.get("QA_NAME", "qa7")
QCoreApplication.setOrganizationName("RADIDE-TEST"); QCoreApplication.setApplicationName("RADIDE-TEST-" + NAME)
app = QApplication(sys.argv[:1]); QSettings().clear()
MSGS = []
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, _n=_n, **k: (MSGS.append((_n, [str(x)[:300] for x in a[1:3]])),
                                                                   QMessageBox.StandardButton.Ok)[1]))
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:800]}]"), flush=True)
    return bool(cond)


def pump(sec=0.5):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents(); time.sleep(0.01)


def wait(pred, timeout=30.0, step=0.05):
    t = time.time()
    while time.time() - t < timeout:
        app.processEvents()
        try:
            if pred():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(step)
    return False


def window():
    from radide.app import MainWindow
    w = MainWindow(); w.resize(1500, 950)
    if REAL:
        w.move(QPoint(-3000, 50))
    w.show(); pump(4)
    return w


def shot(widget, name):
    p = os.path.join(SHOTS, name + ".png")
    widget.grab().save(p); print("SHOT", p, flush=True)
    return p


def finish(w=None):
    errs = []
    if w is not None:
        import re
        errs = [l for l in w.output.toPlainText().splitlines() if re.search(r"Traceback|failed to load", l)]
        check("no tracebacks in Output", not errs, errs[:10])
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}", flush=True)
    print("MSGS:", json.dumps(MSGS)[:1500], flush=True)
    if w is not None:
        try:
            w.close(); pump(1.5)
        except Exception as e:  # noqa: BLE001
            print("close error", e)
    QSettings().clear()
    sys.stdout.flush()
    os._exit(0 if ok == len(RESULTS) else 1)
