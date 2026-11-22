"""Shared harness of the Robustness/Controls and Robustness/Files tests (non-default controls, project files).

* PASS / FAIL lines, a summary, exit code = number of failures.
* Isolated: component packages go to a temporary RADIDE_COMPONENTS_DIR, the GUI tests use the QSettings
  organisation "RADIDE-TEST-NONDEF" (cleared before and after), widget.grab only, no browser, no dialogs.
* WORK is a fresh temporary folder per script (removed at the end unless KEEP_WORK=1).
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

WORK = Path(tempfile.mkdtemp(prefix="radide-nondef-"))
COMP_DIR = WORK / "_user_components"
COMP_DIR.mkdir()
os.environ["RADIDE_COMPONENTS_DIR"] = str(COMP_DIR)        # never touch the real %APPDATA%\RADIDE\components
os.environ.pop("RADIDE_COMPONENT_PATH", None)

RESULTS: list[tuple[str, bool]] = []
SAMPLES = ROOT / "samples"
COMPONENT_SAMPLES = SAMPLES / "Tests" / "Components"


def check(name: str, cond, detail="") -> bool:
    ok = bool(cond)
    RESULTS.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{str(detail)[:900]}]"), flush=True)
    return ok


def raises(fn, exc=Exception):
    """The exception *fn()* raises (None when it does not raise / raises something else than *exc*)."""
    try:
        fn()
    except exc as e:  # noqa: BLE001
        return e
    return None


def finish(app=None) -> None:
    ok = sum(1 for _, c in RESULTS if c)
    failed = [n for n, c in RESULTS if not c]
    print(f"SUMMARY: {ok}/{len(RESULTS)} passed, {len(failed)} failed" + (f": {failed}" if failed else ""),
          flush=True)
    if app is not None:
        try:
            from PyQt6.QtCore import QSettings
            QSettings().clear()
        except Exception:  # noqa: BLE001
            pass
    if not os.environ.get("KEEP_WORK"):
        _rmtree(WORK)
    else:
        print("WORK kept:", WORK)
    sys.stdout.flush()
    os._exit(min(len(failed), 255))


def _rmtree(p: Path) -> None:
    def onerr(func, path, _exc):
        try:
            os.chmod(path, 0o666)
            func(path)
        except OSError:
            pass
    shutil.rmtree(p, onerror=onerr)


def copy_tree(src: Path, name: str) -> Path:
    dst = WORK / name
    if dst.exists():
        _rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "Publish", "_build", "bin", "obj"))
    return dst


# ============================================================================ GUI part
def gui():
    """(QApplication, MSGS, QUESTIONS) for an offscreen IDE test; message boxes are recorded, not shown."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
    import PyQt6.QtWebEngineWidgets  # noqa: F401  (must be imported before the QApplication)
    from PyQt6.QtCore import QCoreApplication, QSettings
    from PyQt6.QtWidgets import QApplication, QMessageBox
    QCoreApplication.setOrganizationName("RADIDE-TEST-NONDEF")
    QCoreApplication.setApplicationName("RADIDE-TEST-NONDEF-" + Path(sys.argv[0]).stem)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    QSettings().clear()
    msgs: list = []
    answers = {"question": QMessageBox.StandardButton.Yes}

    def question(*a, **k):
        msgs.append(("question", [str(x)[:400] for x in a[1:3]]))
        return answers["question"]
    QMessageBox.question = staticmethod(question)
    for n in ("warning", "critical", "information"):
        setattr(QMessageBox, n, staticmethod(lambda *a, _n=n, **k: (msgs.append((_n, [str(x)[:600] for x in a[1:3]])),
                                                                     QMessageBox.StandardButton.Ok)[1]))
    return app, msgs, answers


def pump(app, sec: float = 0.3) -> None:
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        time.sleep(0.01)


def main_window(app):
    from radide.app import MainWindow
    w = MainWindow()
    w.resize(1400, 900)
    w.show()
    pump(app, 2.5)
    return w


def close_window(app, w) -> None:
    try:
        for d in list(getattr(w, "docs", {}).values()):
            d.set_modified(False)
        for cv in list(getattr(w, "codeviews", {}).values()):
            cv.editor.setModified(False)
        w.close()
        pump(app, 1.0)
    except Exception as e:  # noqa: BLE001
        print("close error", e)
