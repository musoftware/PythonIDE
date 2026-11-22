"""Core commands: hello / help / job / wait / exec / eval / output / errors / env / quit, answers for file
dialogs and automatic answers for message boxes."""
from __future__ import annotations

import contextlib
import io
import os
import sys
import time

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .registry import COMMANDS, AutomationError, command
from . import widgets as W


def pump(ms: int = 0) -> None:
    """Run the GUI event loop for *ms* milliseconds (0: just the pending events)."""
    if ms <= 0:
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        return
    loop = QEventLoop()
    QTimer.singleShot(int(ms), loop.quit)
    loop.exec()


@command("hello", doc="who is there: version, pid, frozen, portable, python, platform, settings file")
def _hello(ctx):
    from .. import __version__, paths
    try:
        sfile = ctx.win.settings.fileName()
    except Exception:  # noqa: BLE001
        sfile = ""
    return {"version": __version__, "pid": os.getpid(), "frozen": paths.frozen(), "portable": paths.portable(),
            "exe": paths.ide_exe(), "python": sys.executable, "platform": QApplication.platformName(),
            "install_dir": str(paths.install_dir()), "settings": sfile,
            "org": QCoreApplication.organizationName(), "commands": len(COMMANDS),
            "title": ctx.win.windowTitle()}


@command("help", doc="list the commands (name, doc, module)")
def _help(ctx):
    return [{"name": c.name, "doc": c.doc, "token": c.token, "module": c.module} for c in sorted(COMMANDS.values(),
                                                                                            key=lambda c: c.name)]


@command("job", doc="result of an async request: {done, ok, result | error}")
def _job(ctx, job: int, wait_ms: int = 0):
    end = time.monotonic() + wait_ms / 1000
    while True:
        j = ctx.server.jobs.get(int(job))
        if j is None:
            raise AutomationError(f"unknown job {job}")
        if j.get("done") or time.monotonic() >= end:
            return j
        pump(50)


@command("wait", doc="run the event loop for ms milliseconds (lets timers / threads finish)")
def _wait(ctx, ms: int = 200):
    pump(ms)
    return True


@command("wait_idle", doc="pump events until nothing changes for quiet_ms (max timeout_ms)")
def _wait_idle(ctx, quiet_ms: int = 300, timeout_ms: int = 10000):
    from PyQt6.QtCore import QThreadPool
    end = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < end:
        pump(quiet_ms)
        if QThreadPool.globalInstance().activeThreadCount() == 0:
            return True
    return False


def _ns(ctx):
    from . import widgets
    return {"win": ctx.win, "app": ctx.app, "ctx": ctx, "W": widgets, "pump": pump, "Path": __import__("pathlib").Path}


@command("exec", doc="run Python code in the IDE (needs the token); 'result' = return value, stdout captured",
         token=True)
def _exec(ctx, code: str):
    ns = _ns(ctx)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<automation>", "exec"), ns)  # noqa: S102 - the token-protected test hook
    return {"result": ns.get("result"), "stdout": buf.getvalue()[-20000:]}


@command("eval", doc="evaluate a Python expression in the IDE (needs the token)", token=True)
def _eval(ctx, expr: str):
    return eval(compile(expr, "<automation>", "eval"), _ns(ctx))  # noqa: S307


@command("output", doc="text of the Output window (tail: last n characters)")
def _output(ctx, tail: int = 0, clear: bool = False):
    t = ctx.win.output.toPlainText()
    if clear:
        ctx.win.output.clear()
    return t[-tail:] if tail else t


@command("errors", doc="rows of the Error List [{kind, description, file, line}]")
def _errors(ctx):
    el = getattr(ctx.win, "error_list", None)
    if el is None:
        return []
    rows = []
    for i in range(el.topLevelItemCount()):
        it = el.topLevelItem(i)
        rows.append({"kind": it.text(0), "description": it.text(1), "file": it.text(2), "line": it.text(3)})
    return rows


@command("set_env", doc="change the IDE's environment (what programs it starts inherit): set={}, unset=[]")
def _set_env(ctx, set: dict | None = None, unset: list | None = None):  # noqa: A002
    for k, v in (set or {}).items():
        os.environ[str(k)] = str(v)
    for k in unset or []:
        os.environ.pop(str(k), None)
    return {k: os.environ.get(k) for k in list((set or {}).keys()) + list(unset or [])}


@command("settings", doc="read (keys) and/or write (values) IDE settings")
def _settings(ctx, keys: list | None = None, values: dict | None = None):
    s = ctx.win.settings
    for k, v in (values or {}).items():
        s.setValue(k, v)
    if values:
        s.sync()
    return {k: s.value(k) for k in (keys or [])}


@command("quit", doc="close the IDE (force: no 'save changes?' questions)")
def _quit(ctx, force: bool = True, delay_ms: int = 100):
    def go():
        if force:                         # no "save changes?" question (the IDE closes right after)
            ctx.win._no_save_questions += 1
        ctx.win.close()
        QTimer.singleShot(3000, QApplication.quit)
    QTimer.singleShot(int(delay_ms), go)
    return True


# ------------------------------------------------------------------------------------ file dialogs
_ORIG: dict = {}


def _patch_file_dialogs(ctx):
    if _ORIG:
        return
    q = ctx.data.setdefault("file_answers", [])
    log = ctx.data.setdefault("file_dialog_log", [])

    def make(name, multi=False, dirs=False):
        orig = getattr(QFileDialog, name)
        _ORIG[name] = orig

        def fake(*a, **k):
            caption = a[1] if len(a) > 1 else k.get("caption", "")
            log.append({"kind": name, "caption": caption})
            if not q:
                return orig(*a, **k)
            ans = q.pop(0)
            if ans is None:                                  # "Cancel"
                return ([], "") if multi else ("" if dirs else ("", ""))
            if dirs:
                return str(ans)
            if multi:
                return ([str(x) for x in (ans if isinstance(ans, list) else [ans])], "")
            return (str(ans), "")
        setattr(QFileDialog, name, staticmethod(fake))
    make("getOpenFileName")
    make("getOpenFileNames", multi=True)
    make("getSaveFileName")
    make("getExistingDirectory", dirs=True)


@command("file_dialog", doc="queue answers for the next QFileDialog.get*() calls (None = Cancel)")
def _file_dialog(ctx, answers: list | None = None, clear: bool = False):
    _patch_file_dialogs(ctx)
    q = ctx.data["file_answers"]
    if clear:
        q.clear()
    q.extend(answers or [])
    return {"queued": list(q), "calls": ctx.data["file_dialog_log"][-20:]}


# ------------------------------------------------------------------------------------ auto answers
def _auto_tick(ctx):
    rules = ctx.data.get("auto_rules") or []
    if not rules:
        return
    for dlg in W.dialogs():
        if not isinstance(dlg, QMessageBox):
            continue
        text = (dlg.windowTitle() + "\n" + dlg.text() + "\n" + dlg.informativeText()).lower()
        for r in rules:
            if r.get("match", "").lower() in text:
                for b in dlg.buttons():
                    if W.clean(b.text()).lower() == W.clean(r.get("button", "")).lower():
                        ctx.data.setdefault("auto_log", []).append({"text": text[:300], "button": r["button"]})
                        b.click()
                        break
                break


@command("auto_dialogs", doc="answer message boxes automatically: rules=[{match, button}] ([] = off)")
def _auto_dialogs(ctx, rules: list | None = None):
    ctx.data["auto_rules"] = list(rules or [])
    t = ctx.data.get("auto_timer")
    if t is None:
        t = QTimer(ctx.app)
        t.setInterval(150)
        t.timeout.connect(lambda: _auto_tick(ctx))
        ctx.data["auto_timer"] = t
    t.start() if rules else t.stop()
    return {"rules": ctx.data["auto_rules"], "answered": ctx.data.get("auto_log", [])[-20:]}
