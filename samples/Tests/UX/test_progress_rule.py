"""The progress rule: "any operation expected to take time must have a progress bar".

Part 1 (offscreen) - the shared API radide/progress.py:
  no UI for tasks that finish under DELAY_MS, determinate / indeterminate bars, the dialog (status line,
  elapsed time, log, Cancel), the status-bar indicator with several concurrent tasks, cancel, thread-safe
  coalesced updates from many threads, run_blocking (result / error / Cancelled), run_command and download
  (local HTTP server), track_process (QProcess), percent parsing, accessible names, Arabic texts.
Part 2 (static) - progress_rule_scan.py: long-running call patterns in radide/ that are neither wrapped by
  radide.progress nor justified in progress_allowlist.json; no stale allowlist keys.
Part 3 - converted call sites still route through radide.progress (guards against regressions).

    python samples/Tests/UX/test_progress_rule.py          (exit code = failures)
"""
from __future__ import annotations

import http.server
import os
import sys
import tempfile
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from PyQt6.QtCore import QCoreApplication, QProcess, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMainWindow, QProgressBar  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-PROGRESS")
QCoreApplication.setApplicationName("RADIDE-TEST-PROGRESS")
app = QApplication(sys.argv[:1])
QSettings().clear()

from radide import progress as P  # noqa: E402

RESULTS: list[tuple[str, bool]] = []
SCRATCH = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="radide-progress-")
os.makedirs(SCRATCH, exist_ok=True)


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def pump(sec=0.2):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        time.sleep(0.005)


def wait(pred, timeout=10.0):
    t = time.time()
    while time.time() - t < timeout:
        app.processEvents()
        if pred():
            return True
        time.sleep(0.005)
    return False


def dialogs():
    return [w for w in app.topLevelWidgets() if isinstance(w, P.ProgressDialog) and w.isVisible()]


# ===================================================================== part 1: API
def part_api():
    win = QMainWindow()
    win.resize(900, 600)
    sp = P.install_status_progress(win)
    check("install_status_progress is idempotent", P.install_status_progress(win) is sp)
    win.show()
    pump(0.1)

    # helpers
    check("percent_in parses tool output", P.percent_in("Receiving objects:  42% (21/50)") == 42
          and P.percent_in("pulling manifest 100%") == 100 and P.percent_in("no number") is None
          and P.percent_in("300% bogus") is None)
    check("n_of_m parses step N/M", P.n_of_m("Step 3/10 : RUN") == (3, 10) and P.n_of_m("x") is None)
    check("fmt helpers", P.fmt_bytes(1536) == "1.5 KB" and P.fmt_elapsed(65000) == "1:05")

    # no flicker: a quick task never shows anything
    done = {}
    t = P.run_task(lambda r: 41 + 1, "Quick task", win, on_done=lambda v: done.setdefault("v", v))
    wait(lambda: t.done)
    pump(P.DELAY_MS / 1000 + 0.2)
    check("quick task (<400 ms) shows no UI", not t.shown and not sp.isVisible() and not dialogs(),
          (t.shown, sp.isVisible()))
    check("quick task result reaches on_done in the GUI thread", done.get("v") == 42)

    t = P.run_task(lambda r: 1, "Quick dialog", win, mode="dialog")
    wait(lambda: t.done)
    pump(0.6)
    check("quick dialog task shows no dialog", not t.shown and not dialogs())

    # status bar: indeterminate, then determinate, several tasks
    gate1, gate2 = threading.Event(), threading.Event()
    stage = {}

    def busy(r):
        r.set_text("thinking")
        gate1.wait(10)
        return "a"

    def counted(r):
        r.set_total(4, "step 0")
        for i in range(4):
            r.step(f"step {i + 1}")
            stage["n"] = i + 1
            time.sleep(0.02)
        gate2.wait(10)
        return "b"
    ta = P.run_task(busy, "Indeterminate job", win)
    check("long task appears after the delay", wait(lambda: sp.isVisible(), 3) and ta.shown)
    tb = P.run_task(counted, "Determinate job", win, cancellable=True)
    check("second concurrent task appears too", wait(lambda: tb.shown, 3))
    wait(lambda: stage.get("n") == 4)
    pump(0.1)
    check("status bar lists both tasks", len(sp.tasks) == 2 and "(+1)" in sp.label.text(), sp.label.text())
    check("newest task is determinate 4/4", sp.bar.maximum() == 4 and sp.bar.value() == 4,
          (sp.bar.minimum(), sp.bar.maximum(), sp.bar.value()))
    check("status bar has accessible name + description",
          bool(sp.bar.accessibleName()) and "Indeterminate job" in sp.bar.accessibleDescription())
    sp.toggle_popup()
    pump(0.1)
    bars = sp.popup.findChildren(QProgressBar)
    check("popup shows one row per running task", sp.popup.isVisible() and len(bars) == 2, len(bars))
    check("indeterminate task shows a busy bar", any(b.maximum() == 0 for b in bars))
    sp.popup.hide()
    gate2.set()
    wait(lambda: tb.done)
    pump(0.05)
    check("finished task leaves the status bar", len(sp.tasks) == 1 and "(+1)" not in sp.label.text())
    gate1.set()
    wait(lambda: ta.done)
    pump(0.05)
    check("status bar hides when nothing runs", not sp.isVisible() and not sp.tasks)

    # cancel
    def loop(r):
        while True:
            r.check()
            time.sleep(0.01)
    errs = {}
    tc = P.run_task(loop, "Cancellable job", win, cancellable=True, on_error=lambda e: errs.setdefault("e", e))
    wait(lambda: tc.shown, 3)
    tc.cancel()
    check("cancel stops the work and reports Cancelled", wait(lambda: tc.done, 5)
          and isinstance(errs.get("e"), P.Cancelled))
    tn = P.Task("Not cancellable")
    tn.cancel()
    check("a task that is not cancellable ignores cancel", not tn.reporter.cancelled)

    # dialog presentation
    gate = threading.Event()

    def dl(r):
        for i in range(0, 101, 20):
            r.bytes(i * 1024, 100 * 1024, "file.zip")
            r.log(f"chunk {i}")
            time.sleep(0.01)
        gate.wait(10)
        return "ok"
    td = P.run_task(dl, "Downloading file", win, mode="dialog", cancellable=True)
    check("dialog appears for a long task", wait(lambda: bool(dialogs()), 3))
    d = dialogs()[0] if dialogs() else None
    if d:
        wait(lambda: d.bar.value() == 100 * 1024)
        pump(0.05)
        check("dialog is determinate from bytes", d.bar.maximum() == 100 * 1024 and d.bar.value() == 100 * 1024,
              (d.bar.maximum(), d.bar.value()))
        check("dialog status line shows the bytes", "100.0 KB" in d.status.text() or "chunk" in d.status.text(),
              d.status.text())
        check("dialog log receives lines", "chunk 100" in d.log.toPlainText())
        check("dialog has Cancel + elapsed + accessible names", d.b_cancel.isVisible() is True
              or d.b_cancel.isVisibleTo(d)) and check("dialog accessible names", all(
                  w.accessibleName() for w in (d.bar, d.status, d.elapsed, d.b_cancel, d.log)))
        d.reject()                                    # Esc = cancel
        check("Esc in the dialog cancels the task", td.reporter.cancelled)
    gate.set()
    wait(lambda: td.done)
    pump(0.1)
    check("dialog closes when the task ends", not dialogs())

    # run_blocking
    check("run_blocking returns the result", P.run_blocking(win, "Blocking", lambda r: (time.sleep(0.05), 7)[1]) == 7)
    try:
        P.run_blocking(win, "Failing", lambda r: 1 / 0)
        check("run_blocking raises the worker's error", False)
    except ZeroDivisionError:
        check("run_blocking raises the worker's error", True)
    ticks = {"n": 0}
    from PyQt6.QtCore import QTimer
    tm = QTimer(interval=20)
    tm.timeout.connect(lambda: ticks.__setitem__("n", ticks["n"] + 1))
    tm.start()
    P.run_blocking(win, "Slow blocking", lambda r: time.sleep(0.6), delay_ms=200)
    tm.stop()
    check("GUI event loop keeps running during run_blocking", ticks["n"] >= 10, ticks)

    def cancel_soon(r):
        time.sleep(0.5)
        while not r.cancelled:
            time.sleep(0.01)
        r.check()
    QTimer.singleShot(700, lambda: [x.task.cancel() for x in dialogs()])
    try:
        P.run_blocking(win, "Cancelled blocking", cancel_soon, cancellable=True, delay_ms=100)
        check("run_blocking raises Cancelled", False)
    except P.Cancelled:
        check("run_blocking raises Cancelled", True)

    # thread safety: 8 threads x 2000 updates, coalesced
    tt = P.Task("Stress")
    changes = {"n": 0}
    tt.changed.connect(lambda: changes.__setitem__("n", changes["n"] + 1))
    lines = {"n": 0}
    tt.line.connect(lambda _s: lines.__setitem__("n", lines["n"] + 1))
    tt.reporter.parse_percent = False
    tt.reporter.set_total(16000)

    def hammer():
        for _ in range(2000):
            tt.reporter.step()
        tt.reporter.log("x")
    ths = [threading.Thread(target=hammer) for _ in range(8)]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    pump(0.2)
    check("concurrent step() from 8 threads loses no update", tt.reporter.value == 16000, tt.reporter.value)
    check("updates are coalesced (far fewer repaints than updates)", 1 <= changes["n"] < 2000, changes["n"])
    check("every log line arrives in the GUI thread", lines["n"] == 8, lines["n"])

    # run_command (cancellable subprocess with lines)
    rep_task = P.Task("cmd")
    cp = P.run_command([sys.executable, "-c", "print('10%');print('done 100%')"], rep_task.reporter)
    pump(0.05)
    check("run_command returns output and parses NN%", cp.returncode == 0 and "done" in cp.stdout
          and rep_task.reporter.value == 100 and rep_task.reporter.total == 100, (cp, rep_task.reporter.snapshot()))
    rep2 = P.Task("cmd2", cancellable=True)
    threading.Timer(0.3, rep2.cancel).start()
    t0 = time.time()
    try:
        P.run_command([sys.executable, "-c", "import time; time.sleep(30)"], rep2.reporter)
        check("run_command is cancellable", False)
    except P.Cancelled:
        check("run_command is cancellable", time.time() - t0 < 10)

    # download from a local server (Content-Length -> bytes)
    data = os.urandom(300_000)

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        dest = os.path.join(SCRATCH, "dl.bin")
        res = P.run_blocking(win, "Download", lambda r: (P.download(f"http://127.0.0.1:{srv.server_port}/f", dest, r),
                                                         r.snapshot())[1])
        check("download writes the file", open(dest, "rb").read() == data)
        check("download reports bytes against Content-Length", res[0] == len(data) and res[1] == len(data), res)
    finally:
        srv.shutdown()

    # track_process
    proc = QProcess()
    tp = P.track_process(proc, "Child process", win, delay_ms=50)
    proc.start(sys.executable, ["-c", "import time; time.sleep(0.5)"])
    check("track_process shows in the status bar", wait(lambda: tp in sp.tasks, 3))
    check("track_process completes with the exit code", wait(lambda: tp.done, 10) and tp.result == 0)
    proc2 = QProcess()
    tp2 = P.track_process(proc2, "Killable", win, delay_ms=0)
    proc2.start(sys.executable, ["-c", "import time; time.sleep(30)"])
    proc2.waitForStarted(5000)
    tp2.cancel()
    check("track_process Cancel kills the process", wait(lambda: tp2.done, 10)
          and isinstance(tp2.error, P.Cancelled))

    # Arabic UI: texts translated
    from radide import i18n
    try:
        i18n.set_language(app, "ar")
        g = threading.Event()
        ta = P.run_task(lambda r: g.wait(10), "Background tasks", win, mode="dialog", cancellable=True)
        wait(lambda: bool(dialogs()), 3)
        d = dialogs()[0] if dialogs() else None
        shown = d and (i18n.shown(d.b_cancel), i18n.shown(d.head), i18n.shown(d, "windowTitle"))
        ok = d is not None and all(i18n._ARABIC.search(x) for x in shown)
        check("dialog texts follow the Arabic UI", ok, shown)
        check("accessible names follow the Arabic UI",
              d is not None and i18n._ARABIC.search(d.elapsed.accessibleName()) is not None)
        g.set()
        wait(lambda: ta.done)
    finally:
        i18n.set_language(app, "en")
    pump(0.1)
    win.close()


# ===================================================================== part 2: static scan
def part_static():
    import progress_rule_scan as S
    hits = S.scan()
    allow = S.load_allowlist()
    bad = S.unlisted(hits, allow)
    check("static scan finds the known patterns (sanity)", len(hits) > 10, len(hits))
    check("no long-running call outside radide.progress / the allowlist", not bad,
          "\n".join(f"{k}:{ln} {c}" for k, ln, _kind, c in bad[:20]))
    st = S.stale(hits, allow)
    check("no stale allowlist keys", not st, st[:10])
    todo = [k for k, v in allow.items() if not v or v.startswith("TODO")]
    check("every allowlist entry has a reason", not todo, todo[:10])
    # the scanner itself flags a fresh offender and accepts a wrapped one
    import ast
    src = ("import subprocess, urllib.request\n"
           "def bad(): subprocess.run(['npm','install'])\n"
           "def bad2(): urllib.request.urlopen('http://x')\n"
           "def ok(reporter): urllib.request.urlopen('http://x')\n"
           "def work(r): subprocess.check_output(['dotnet','build'])\n"
           "def go(w): run_task(work, 'x', w)\n"
           "def wf(p): p.waitForFinished(-1)\n")
    sc = S.Scan("x.py")
    tree = ast.parse(src)
    sc.wrapped_names = S._collect_wrapped(tree)
    sc.visit(tree)
    kinds = sorted(h[0] for h in sc.hits)
    check("scanner flags unwrapped npm / urlopen / waitForFinished(-1) and accepts wrapped ones",
          kinds == ["x.py::bad2::download", "x.py::bad::tool:npm", "x.py::wf::waitForFinished"], kinds)


# ===================================================================== part 3: converted call sites
CONVERTED = {
    # path: substrings that must stay in the file
    "radide/app.py": ["install_status_progress", "import_python_program(src, target, interp))"],
    # web / New Project
    "radide/web_site/frameworks/backend_common.py": ["run_blocking"],
    "radide/web_site/frameworks/aspnet.py": ["with_progress("],
    "radide/web_site/frameworks/nestjs.py": ["with_progress("],
    "radide/web_site/frameworks/spring.py": ["with_progress(", "reporter.bytes("],
    "radide/web_site/debug.py": ["run_blocking", "background_reporter"],
    "radide/web_site/php_toolchain.py": ["reporter.bytes("],
    "radide/features/app_gallery.py": ["progress.run_blocking"],
    "radide/features/php_frameworks.py": ["progress.track(", "class Background", "progress.run_blocking"],
    "radide/features/php_tools.py": ["progress.track_process"],
    "radide/features/rails_ide.py": ["with_progress("],
    "radide/features/web_extras.py": ["progress.track_process", "QEventLoop"],
    # .NET / desktop
    "radide/dotnet/templates/wizard.py": ["run_blocking", "Loading .NET project templates"],
    "radide/dotnet/sln/ops.py": ["_off_gui", "run_blocking"],
    "radide/foreign/vs_ui.py": ["run_blocking"],
    "radide/notebook/view.py": ["progress.run_command"],
    "radide/testing/__init__.py": ["reporter=None", "download(JUNIT_URL"],
    "radide/features/test_explorer.py": ['progress.track("Running tests"', "Downloading the JUnit console launcher"],
    "radide/features/game_designer.py": ['progress.run_blocking(win, "Export to Godot"'],
    "radide/features/flutter_designer.py": ["Importing the Dart screen"],
    "radide/features/retro_dev.py": ['progress.run_blocking(win, "Rebuild Check"'],
    "radide/features/docker_cloud.py": ["Lint Dockerfile"],
    "radide/tools.py": ["probe_pyinstaller"],
    # background tasks / updater / git / extensions
    "radide/features/ide_update.py": ['progress.run_blocking(parent, "Update"', "progress.run_command("],
    "radide/features/installer.py": ['progress.track("Publishing"', 'progress.track("Building the native exe"'],
    "radide/features/solution_ui.py": ['progress.track("Build Solution"'],
    "radide/features/language_servers.py": ["progress.track("],
    "radide/features/web_intellisense.py": ['progress.track("Installing web language servers"'],
    "radide/features/formatting.py": ['progress.track("Installing Prettier"'],
    "radide/features/rust_ide.py": ['progress.track("Installing rust-analyzer"'],
    "radide/features/vsx_market.py": ["run_bg_progress("],
    "radide/features/git_full.py": ["progress.track_process(p", 'progress.track("Downloading GitHub CLI"'],
    "radide/features/git_panel.py": ["progress.track_process(p"],
    "radide/features/ai_settings.py": ["progress.track_process(pr"],
}


def part_sites():
    for rel, needles in CONVERTED.items():
        try:
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        except OSError as e:
            check(f"converted site {rel}", False, e)
            continue
        missing = [n for n in needles if n not in src]
        check(f"converted site {rel} uses radide.progress", not missing, missing)


if __name__ == "__main__":
    try:
        part_api()
    except Exception as e:   # noqa: BLE001
        import traceback
        traceback.print_exc()
        check("part 1 ran to the end", False, e)
    part_static()
    part_sites()
    failed = sum(1 for _n, ok in RESULTS if not ok)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.exit(failed)
