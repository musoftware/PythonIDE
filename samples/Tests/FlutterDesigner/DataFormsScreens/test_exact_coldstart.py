"""Exact preview cold starts (live.LivePreview.start_exact: flutter run -d web-server shown in QtWebEngine).

    python samples/Tests/FlutterDesigner/DataFormsScreens/test_exact_coldstart.py [runs] [--watchdog off|on]

Copies this project to a temporary folder and starts the exact preview *runs* times (default 15), each time with
a new LivePreview / QWebEngineView and a new `flutter run` process. For every run it records the seconds until
flutter run printed the URL, until the app connected (Dart VM Service line = LivePreview's "ready") and until the
page created its Flutter view (flutter-view / flt-glass-pane element), and how many times the watchdog reloaded
the page. ``--watchdog off`` disables the reload watchdog to see whether a first load stays blank on its own.
A run that shows no Flutter view within 240 s fails. Prints a table and returns 1 when a run failed.
"""
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from PyQt6.QtCore import QEventLoop, QTimer  # noqa: E402
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402,F401 - before QApplication
from PyQt6.QtWidgets import QApplication  # noqa: E402

RUN_TIMEOUT_S = 240


def copy_project(dst: Path) -> Path:
    def ignore(_d, names):
        return [n for n in names if n in (".dart_tool", "build", ".idea")]
    shutil.copytree(HERE, dst, ignore=ignore)
    return dst


def one_run(app, folder: Path, watchdog: bool) -> dict:
    from radide.flutterdesign import live
    view = QWebEngineView()
    view.resize(420, 860)
    view.setWindowTitle("RAD IDE exact preview cold start test")
    view.show()
    lv = live.LivePreview(view=view)
    if not watchdog:
        lv.EXACT_WATCHDOG_S = 10 ** 6
    errors: list[str] = []
    lv.log.connect(lambda lvl, t: lvl == "error" and errors.append(t[:200]))
    out = {"url": None, "ready": None, "view": None, "reloads": 0, "errors": errors, "exit": None}
    t0 = time.time()
    lv.start_exact(folder, "/")
    lv.exact.urlReady.connect(lambda _u: out.__setitem__("url", round(time.time() - t0, 1)))
    seen = {"view": False}

    def poll():
        if lv.exact is None or lv.exact.session is None:
            return
        if lv.exact.session.ready and out["ready"] is None:
            out["ready"] = round(time.time() - t0, 1)
        if out["url"] is not None:
            def got(has):
                if has and not seen["view"]:
                    seen["view"] = True
                    out["view"] = round(time.time() - t0, 1)
            lv.page.runJavaScript("!!document.querySelector('flutter-view, flt-glass-pane')", got)
    timer = QTimer()
    timer.setInterval(500)
    timer.timeout.connect(poll)
    timer.start()
    loop = QEventLoop()
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    deadline.start(RUN_TIMEOUT_S * 1000)
    done = QTimer()
    done.setInterval(250)
    done.timeout.connect(lambda: seen["view"] and loop.quit())
    done.start()
    loop.exec()
    timer.stop()
    done.stop()
    out["reloads"] = int(getattr(lv, "_exact_reloads", 0) or 0)
    # stop flutter run (the process this test started) and wait for it to end
    runner = lv.exact
    ended = {"code": None}
    if runner is not None:
        runner.finished.connect(lambda c: ended.__setitem__("code", c))
        lv.stop_exact(load_host=False)
        t1 = time.time()
        while ended["code"] is None and time.time() - t1 < 30:
            app.processEvents()
            time.sleep(0.05)
    out["exit"] = ended["code"]
    view.close()
    view.deleteLater()
    app.processEvents()
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    runs = int(args[0]) if args else 15
    watchdog = "--watchdog" not in sys.argv or sys.argv[sys.argv.index("--watchdog") + 1] != "off"
    app = QApplication.instance() or QApplication(sys.argv)
    tmp = Path(tempfile.mkdtemp(prefix="rad_exact_"))
    folder = copy_project(tmp / "DataFormsScreens")
    rows, fails = [], 0
    try:
        for i in range(1, runs + 1):
            r = one_run(app, folder, watchdog)
            ok = r["view"] is not None
            fails += not ok
            rows.append(r)
            print(f"run {i:2d}: url {r['url']}s  connected {r['ready']}s  flutter view {r['view']}s  "
                  f"reloads {r['reloads']}  {'ok' if ok else 'FAIL (blank)'}  errors {r['errors'][:2]}",
                  flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    blank_first = sum(1 for r in rows if r["reloads"])
    print(f"runs: {len(rows)}  shown: {len(rows) - fails}  failed: {fails}  needed a watchdog reload: {blank_first}"
          f"  (watchdog {'on' if watchdog else 'off'})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
