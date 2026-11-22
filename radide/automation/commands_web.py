"""Web workspace commands of the automation channel (the web E2E journeys, samples/Tests/E2E/Web).

Everything a user does in a web site project, as the UI does it: write a file in the code editor, the Databases
workspace (connection + SQL Query tab + table grid), the Design View (GrapesJS), Site > Run, the Preview
(QtWebEngine) and Site > Publish. Long operations return at once; the client polls ``web_server`` / ``job``."""
from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QEventLoop, QTimer

from .registry import AutomationError, command
from .commands_core import pump


def _wait(pred, timeout_s: float, step_ms: int = 100) -> bool:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        try:
            if pred():
                return True
        except Exception:  # noqa: BLE001 - half-built objects
            pass
        pump(step_ms)
    try:
        return bool(pred())
    except Exception:  # noqa: BLE001
        return False


def _run_js(page, expr: str, timeout_s: float = 15.0):
    box = {}
    loop = QEventLoop()

    def done(v):
        box["v"] = v
        loop.quit()
    page.runJavaScript(f"(function(){{try{{return ({expr});}}catch(e){{return 'ERR:'+e;}}}})()", done)
    QTimer.singleShot(int(timeout_s * 1000), loop.quit)
    if "v" not in box:
        loop.exec()
    return box.get("v")


def _project(ctx):
    p = ctx.win.project
    if p is None:
        raise AutomationError("no project is open")
    return p


@command("web_write_file", doc="New File (if missing) + the code editor + Save All: path (absolute or relative to "
                               "the active project), text")
def _write_file(ctx, path: str, text: str):
    from ..features import web_workspace as ww
    p = Path(path)
    if not p.is_absolute():
        p = Path(_project(ctx).folder) / p
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        ww.create_file(ctx.win, p.parent, p.name, "")
        pump(50)
    ed = ww.open_file(ctx.win, p)
    if ed is None:
        raise AutomationError(f"the editor did not open {p}")
    ed.setText(text)
    pump(50)
    ctx.win.save_all()
    pump(50)
    got = p.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    return {"path": str(p), "saved": got == text.replace("\r\n", "\n").strip(), "chars": len(got)}


@command("web_db_sql", doc="Databases workspace: add the SQLite file (path relative to the project) as a "
                           "connection, run sql in a SQL Query tab, open table; returns errors and the table rows")
def _db_sql(ctx, path: str, sql: str = "", table: str = "", name: str = "store"):
    win = ctx.win
    project = _project(ctx)
    panel = getattr(win, "databases", None)
    if panel is None:
        raise AutomationError("the Databases workspace is not installed")
    getattr(win, "a_databases", None) and win.a_databases.trigger()
    db = Path(path) if Path(path).is_absolute() else Path(project.folder) / path
    db.parent.mkdir(parents=True, exist_ok=True)
    cid = panel.add_sqlite(db, project, name)
    errors, ran = [], 0
    if sql:
        qv = panel.open_query(cid, sql)
        res = qv.run(wait=True) or []
        ran = len(res)
        errors = [r.message for r in res if not r.ok]
    rows = []
    if table:
        panel.refresh_connection(cid)
        tv = panel.open_table(cid, table)
        pump(200)
        m = getattr(tv, "model", None)
        if m is not None:
            rows = [[str(m.value(r, c)) for c in range(m.columnCount())] for r in range(m.rowCount())]
    return {"connection": cid, "statements": ran, "errors": errors, "rows": rows}


@command("web_design", doc="Design View (GrapesJS) of a page: wait until ready, append html inside the first "
                           "element matching target, optional css on it, save; returns blocks and the saved size")
def _design(ctx, path: str, html: str, target: str = "body", style: dict | None = None, timeout_s: float = 180):
    from ..features import web_workspace as ww
    import json
    p = Path(path) if Path(path).is_absolute() else Path(_project(ctx).folder) / path
    before = p.read_text(encoding="utf-8")
    view = ww.open_design(ctx.win, p)
    if view is None:
        raise AutomationError("the Design View did not open")
    if not _wait(lambda: view.is_ready(), timeout_s, 200):
        raise AutomationError(f"GrapesJS was not ready in {timeout_s}s")
    pump(500)
    page = view.web.page()
    blocks = _run_js(page, "radEditor.BlockManager.getAll().length")
    n = _run_js(page, "(function(){var w=radEditor.getWrapper();var t=w.find(%s)[0]||w;var a=t.append(%s);"
                      "radEditor.select(a[0]);return a.length;})()" % (json.dumps(target), json.dumps(html)))
    if style:
        _run_js(page, "radEditor.getSelected().addStyle(%s) && 1" % json.dumps(style))
    pump(1200)
    saved = view.save()
    pump(300)
    after = p.read_text(encoding="utf-8")
    return {"blocks": blocks, "added": n, "saved": bool(saved), "before": len(before), "after": len(after),
            "ready": True}


@command("web_server", doc="the running dev server of the web site: running, ready, url, root, last requests")
def _server(ctx, requests: int = 0):
    srv = getattr(ctx.win, "web_server", None)
    if srv is None:
        return {"running": False}
    out = {"running": bool(srv.running), "ready": bool(srv.is_ready()), "url": srv.url, "root": str(srv.root),
           "start_url": srv.start_url()}
    if requests:
        out["requests"] = [{k: q.get(k) for k in ("method", "path", "status", "ms")}
                           for q in list(getattr(srv, "requests", []) or [])[-int(requests):]]
    return out


@command("web_preview", doc="the Preview (QtWebEngine): open url (optional), wait until loaded, device (title "
                            "substring, optional), returns url/title and the value of each JS expression in exprs",
         token=True)
def _preview(ctx, url: str = "", exprs: list | None = None, device: str = "", timeout_s: float = 30):
    pv = ctx.win.web_preview
    view = pv.view
    if view is None:
        raise AutomationError("no QtWebEngine")
    if device:
        i = next((k for k in range(pv.device.count()) if device.lower() in pv.device.itemText(k).lower()), -1)
        if i < 0:
            raise AutomationError(f"no device {device!r}")
        pv.device.setCurrentIndex(i)
        pump(600)
    if url:
        pv.open_url(url)
    part = url.split("://", 1)[-1].split("?")[0] if url else ""

    def loaded():
        if part and part.rstrip("/") not in view.url().toString():
            return False
        return _run_js(view.page(), "document.readyState", 3) == "complete"
    ok = _wait(loaded, timeout_s, 200)
    pump(500)
    vals = [_run_js(view.page(), e) for e in (exprs or [])]
    return {"loaded": ok, "url": view.url().toString(), "title": view.title(), "values": vals,
            "device": pv.device.currentText()}


@command("web_publish", doc="Site > Publish: a new profile (kind folder|ftp; fields = the dialog's f_* widgets, "
                            "e.g. f_remote, f_host, f_port, f_user, f_pass), Publish, wait; returns the log tail")
def _publish(ctx, kind: str = "folder", name: str = "", fields: dict | None = None, timeout_s: float = 600):
    from ..features.web_tools import PublishDialog
    dlg = PublishDialog(ctx.win, _project(ctx))
    dlg._e2e_keep = True
    dlg.show()
    pump(300)
    dlg.add_profile()
    dlg.f_name.setText(name or kind)
    i = dlg.f_kind.findData(kind)
    if i < 0:
        i = next((k for k in range(dlg.f_kind.count()) if kind.lower() in dlg.f_kind.itemText(k).lower()), 0)
    dlg.f_kind.setCurrentIndex(i)
    pump(100)
    for k, v in (fields or {}).items():
        w = getattr(dlg, k)
        if hasattr(w, "setChecked") and isinstance(v, bool):
            w.setChecked(v)
        elif hasattr(w, "setValue"):
            w.setValue(int(v))
        else:
            w.setText(str(v))
    dlg.start(dry_run=False)
    done = _wait(lambda: not dlg._busy, timeout_s, 200)
    log = ""
    for attr in ("log", "log_box", "output"):
        w = getattr(dlg, attr, None)
        if w is not None and hasattr(w, "toPlainText"):
            log = w.toPlainText()
            break
    dlg.close()
    return {"done": done, "log": log[-2000:]}
