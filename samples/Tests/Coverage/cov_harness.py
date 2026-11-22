"""Harness of the functional coverage tests (samples/Tests/Coverage/<Area>/test_*.py).

Each test script opens the IDE offscreen (QSettings org RADIDE-TEST-CRAWL, app "cov-<name>", cleared before and
after; nothing external is started: browsers, Explorer, hh.exe and QProcess.startDetached are recorded in
``RECORDED``), works on a sandbox copy of a sample project and checks the *effect* of a menu command:

    from cov_harness import *                      # noqa: F401,F403
    w = start("build_menu")                         # QApplication + MainWindow
    proj = open_sample(w, "python-tk")              # crawl_common.CONTEXTS id, or a path relative to the repo
    act = action(w, "Build", "Build Solution")      # the QAction of a menu path (aboutToShow emitted on the way)
    trigger(act)                                    # modal dialogs that open are passed to on_modal handlers
    check("Output says the build ran", wait(lambda: "Build:" in w.output.toPlainText(), 20))
    finish(w)                                       # prints N/M passed, exits with the number of failures

``on_modal(handler)`` registers a function called with every modal dialog that opens while ``trigger`` /
``pump`` / ``wait`` run; it returns True when it handled (closed) the dialog. Unhandled dialogs are rejected and
recorded in ``DIALOGS`` (title, class).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Crawler"))
import crawl_common as C  # noqa: E402

RESULTS: list[tuple[str, bool]] = []
DIALOGS: list[tuple[str, str]] = []
HANDLERS: list = []
RECORDED = C.RECORDED
APP_NAME = ["cov"]
_SANDBOX = [None]


def sandbox() -> Path:
    if _SANDBOX[0] is None:
        import tempfile
        base = Path(os.environ.get("QA_OUT") or tempfile.gettempdir()) / "radide-coverage" / APP_NAME[0]
        shutil.rmtree(base, ignore_errors=True)
        base.mkdir(parents=True, exist_ok=True)
        _SANDBOX[0] = base
    return _SANDBOX[0]


def check(name: str, cond, detail="") -> bool:
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:800]}]"), flush=True)
    return bool(cond)


def _tick():
    from PyQt6.QtWidgets import QApplication, QDialog
    m = QApplication.activeModalWidget()
    if m is None or getattr(_tick, "busy", False):
        return
    _tick.busy = True
    try:
        for h in list(HANDLERS):
            try:
                if h(m):
                    return
            except Exception as e:  # noqa: BLE001
                print(f"[cov] modal handler failed: {e!r}", flush=True)
        DIALOGS.append((m.windowTitle(), type(m).__name__))
        m.reject() if isinstance(m, QDialog) else m.close()
    finally:
        _tick.busy = False


def on_modal(handler) -> None:
    HANDLERS.append(handler)


def clear_modal_handlers() -> None:
    HANDLERS.clear()


def start(name: str):
    """Boot the IDE offscreen; returns the MainWindow."""
    APP_NAME[0] = "cov-" + name
    if os.environ.get("COV_MONACO") != "1":      # the built-in editor: synchronous text/cursor, no Monaco warm-up
        os.environ["RADIDE_CRAWL_BUILTIN_EDITOR"] = "1"
    C.boot(APP_NAME[0])
    from PyQt6.QtCore import QTimer
    t = QTimer()
    t.setInterval(100)
    t.timeout.connect(_tick)
    t.start()
    C._cov_timer = t
    w = C.window()
    return w


def open_sample(w, ctx_or_path: str) -> Path:
    """Copy a sample project into the sandbox and open it. *ctx_or_path*: a crawl_common.CONTEXTS id
    ("python-tk", "web", "vb6" ...) or a folder relative to the repository."""
    sb = sandbox()
    if ctx_or_path in C.CONTEXTS:
        return C.open_context(w, ctx_or_path, sb)
    src = ROOT / ctx_or_path
    dst = sb / "projects" / src.name
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=C.COPY_IGNORE)
    target = dst
    slns = list(dst.glob("*.radsln"))
    if slns:
        target = slns[0]
    w.open_project(target, ask=False)
    C.pump(2.0)
    return dst


def pump(sec: float = 0.3) -> None:
    C.pump(sec)


def wait(pred, timeout: float = 10.0) -> bool:
    return C.wait(pred, timeout)


def menu_of(w, *path: str):
    """The QMenu at a menu-bar path ("Build", "Mobile App"); aboutToShow is emitted so dynamic menus fill."""
    menu = None
    actions = w.menuBar().actions()
    for part in path:
        found = None
        for a in actions:
            if C.clean(a.text()).lower() == part.lower() and a.menu() is not None:
                found = a.menu()
                break
        if found is None:
            return None
        menu = found
        try:
            menu.aboutToShow.emit()
        except Exception:  # noqa: BLE001
            pass
        actions = menu.actions()
    return menu


def action(w, *path: str):
    """The QAction at a menu-bar path, e.g. action(w, "Build", "Build Solution") (texts without & and ...)."""
    menu = menu_of(w, *path[:-1])
    if menu is None:
        return None
    for a in menu.actions():
        if not a.isSeparator() and C.clean(a.text()).lower() == path[-1].lower():
            return a
    return None


def palette_command(cmd_id: str):
    from radide.features import command_palette as cp
    return next((c for c in cp.commands() if c.id == cmd_id), None)


def trigger(act, settle: float = 0.5) -> bool:
    """Trigger an action (enabled check included); modal dialogs go to the on_modal handlers."""
    if act is None:
        return False
    if not act.isEnabled():
        return False
    act.trigger()
    pump(settle)
    return True


def output_text(w) -> str:
    return w.output.toPlainText()


def tracebacks(w) -> list[str]:
    import re
    return [ln for ln in output_text(w).splitlines() if re.search(r"Traceback \(most recent|failed to load", ln)]


def shot(widget, name: str) -> str:
    p = sandbox() / "shots"
    p.mkdir(exist_ok=True)
    f = p / f"{name}.png"
    widget.grab().save(str(f))
    return str(f)


def finish(w=None) -> None:
    if w is not None:
        tb = tracebacks(w)
        check("no tracebacks in the Output window", not tb, tb[:5])
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}", flush=True)
    if DIALOGS:
        print("dialogs auto-closed:", DIALOGS[:20], flush=True)
    if w is not None:
        try:
            w.close()
            pump(0.5)
        except Exception:  # noqa: BLE001
            pass
    C.clear_settings(APP_NAME[0])
    try:                                   # helpers this test started (VS Code extension host, servers ...)
        import psutil
        for ch in psutil.Process().children(recursive=True):
            ch.kill()
    except Exception:  # noqa: BLE001
        pass
    sys.stdout.flush()
    os._exit(len(RESULTS) - ok)


__all__ = ["C", "DIALOGS", "RECORDED", "ROOT", "action", "check", "clear_modal_handlers", "finish", "menu_of",
           "on_modal", "open_sample", "output_text", "palette_command", "pump", "sandbox", "shot", "start",
           "tracebacks", "trigger", "wait"]
