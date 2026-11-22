"""Shared set-up of the accessibility tests (samples/Tests/Accessibility).

Offscreen Qt, QSettings organisation "RADIDE-TEST-A11Y" (cleared before and after - other GUI tests run at the same
time), only widget.grab() pictures, message boxes answered automatically, a copy of samples/HelloPython opened (never
the sample itself). Import this module first: it creates the QApplication.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
ORG = "RADIDE-TEST-A11Y"         # radide.app.ide_settings() honours any "RADIDE-TEST*" organization

__import__("PyQt6.QtWebEngineWidgets")       # must be imported before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG)
app = QApplication.instance() or QApplication(sys.argv[:1])
QSettings().clear()
QSettings().sync()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))

SCRATCH = os.environ.get("A11Y_OUT") or tempfile.mkdtemp(prefix="radide_a11y_")
os.makedirs(SCRATCH, exist_ok=True)
RESULTS: list[tuple[str, bool, str]] = []
T0 = time.time()


def check(name: str, ok, detail="") -> bool:
    RESULTS.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name + (f"  - {str(detail)[:700]}" if detail and not ok else ""), flush=True)
    return bool(ok)


def info(text: str) -> None:
    print("INFO " + text, flush=True)


def pump(n: int = 10, ms: int = 5) -> None:
    for _ in range(n):
        app.processEvents()
        QTest.qWait(ms)


def project_copy(name: str = "HelloPython") -> str:
    dst = os.path.join(SCRATCH, "proj", name)
    if not os.path.isdir(dst):
        shutil.copytree(os.path.join(ROOT, "samples", name), dst)
    return dst


_killer = None


def auto_close_modals(on: bool = True) -> None:
    """Close modal dialogs a test did not expect (they would block the event loop)."""
    global _killer
    if on and _killer is None:
        _killer = QTimer()
        _killer.timeout.connect(lambda: (QApplication.activeModalWidget() or _Dummy).close())
        _killer.start(400)
    elif not on and _killer is not None:
        _killer.stop()
        _killer = None


class _Dummy:
    @staticmethod
    def close():
        return None


def main_window(open_designer: bool = True):
    """A MainWindow with a copy of HelloPython open (Form1 in the designer)."""
    from pathlib import Path
    from radide.app import MainWindow
    win = MainWindow()
    win.resize(1280, 820)
    win.show()
    win.activateWindow()
    pump(40)
    win.open_project(Path(project_copy()), ask=False)
    pump(20)
    if open_designer:
        win.open_designer("Form1")
        pump(20)
    return win


def finish(title: str) -> int:
    """Print the summary, clear the settings and return the number of failures (the exit code)."""
    fails = [r for r in RESULTS if not r[1]]
    print(f"\n{title}: {len(RESULTS) - len(fails)}/{len(RESULTS)} passed, {len(fails)} failed "
          f"({time.time() - T0:.0f} s)", flush=True)
    for name, _ok, detail in fails:
        print(f"  FAILED: {name}  {detail[:300]}", flush=True)
    QSettings().clear()
    QSettings().sync()
    return len(fails)


def close_all(*wins) -> None:
    for w in wins:
        try:
            w.close()
        except Exception:  # noqa: BLE001
            pass
    pump(5)
