# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Web journey: build the "RAD Store" web site with one web stack, entirely through the IDE, like a user.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Web\\journey_web.py <stack>     (stacks/<stack>.py)

Steps (each PASS / FAIL / SKIP, with screenshots):
  toolchain      the stack's tools are found (else every step SKIPs with the reason)
  new project    File > New Project > Web > <language> / <template>
  code           every source file written in the IDE's code editor (New File + type + Save All)
  database       Databases workspace: add the site's SQLite file, run the schema + seed script in a SQL Query
                 tab, open the table: the seeded rows are there
  design         Design View (GrapesJS) of the home page: a hero block is dropped and edited, saved; the page's
                 server code survives the round trip
  run            Site > Run Site in Preview (Ctrl+F5 path): the dev server starts, the Preview shows the home page
  pages          every page over HTTP: status codes, content, the designed hero, CSS / JS assets
  login          protected page redirects to the login page; wrong password refused; right one starts a session
  crud           add with a validation error (nothing saved), add, edit, delete - through the pages' own forms
                 (hidden CSRF fields kept), the list and the database agree after each step
  api            the JSON endpoint returns the products with the right content type
  arabic         the Arabic page: lang="ar", dir="rtl", Arabic text over HTTP and in the Preview's DOM
  preview        the Preview (QtWebEngine): DOM checks with runJavaScript, phone / tablet device sizes
  debug          F9 breakpoint in the request handler, F5, a request from the Preview pauses there; Locals /
                 call stack are filled; Continue finishes the request
  intellisense   language completions in the code editor (Monaco + the language's provider), HTML tag and CSS
                 property suggestions in Monaco's suggest widget
  publish folder Site > Publish with a Local folder profile (the Publish dialog)
  publish ftp    the same site to a local FTP server started by the test (pyftpdlib), files arrive
  published run  the published copy runs on its own server and answers the same pages
"""
from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import e2e_lib as E  # noqa: E402

STACK_NAME = (sys.argv[1] if len(sys.argv) > 1 else "php").strip()
S = importlib.import_module(f"stacks.{STACK_NAME}")
j = E.Journey("Web", STACK_NAME, getattr(S, "TITLE", STACK_NAME))
ROUTES = S.ROUTES
FEATURES = getattr(S, "FEATURES", {"db": True, "auth": True, "crud": True, "api": True, "debug": True})
CTX: dict = {}
j.allow_modal |= set(getattr(S, "ALLOW_MODALS", ()))     # the IDE's own progress dialogs (e.g. Creating Laravel App)


def tool_path(name: str) -> str:
    from radide.web_site.gallery import find_tool
    p = find_tool(name) if name in ("php", "composer", "node", "npm") else ""
    return p or shutil.which(name) or ""


def skip_all(reason: str):
    for s in ("new project", "code", "database", "design", "run", "pages", "login", "crud", "api", "arabic",
              "preview", "debug", "intellisense", "publish folder", "publish ftp", "published run"):
        with j.step(s):
            raise E.Skip(reason)
    j.finish(close=False)


# ============================================================================ 0. toolchain
with j.step("toolchain"):
    missing = [t for t in getattr(S, "TOOLS", []) if not tool_path(t)]
    extra = getattr(S, "toolchain_check", None)
    why = extra() if callable(extra) else ""
    if missing or why:
        reason = (f"missing: {', '.join(missing)}" if missing else "") + (f" {why}" if why else "")
        j.steps[-1:] = []
        print("SKIP journey:", reason)
        skip_all(reason.strip())
    j.note(", ".join(f"{t}={tool_path(t)}" for t in getattr(S, "TOOLS", [])))

win = j.window()
folder: Path | None = None
project = None
srv = None

# ============================================================================ 1. new project
with j.step("new project"):
    shutil.rmtree(j.work / S.NAME, ignore_errors=True)
    shutil.rmtree(j.work / (S.NAME + "Solution"), ignore_errors=True)
    prj = j.new_project(S.LANG, S.TEMPLATE, S.NAME)
    project = win.project
    folder = Path(project.folder)
    j.check((folder / "project.radproj").exists(), f"no project.radproj in {folder}")
    hook = getattr(S, "after_create", None)
    if callable(hook):
        j.note(hook(j, win, project, folder) or "")
    E.pump(0.5)
    j.shot(win, "ide_after_new_project")
    j.note(f"{project.language} at {folder}")
    CTX["folder"] = folder


def need_project():
    if folder is None:
        raise E.Skip("no project (New Project failed)")


# ============================================================================ 2. code
with j.step("code"):
    need_project()
    files = S.files() if callable(getattr(S, "files", None)) else {}
    written = j.write_files(folder, files)
    j.check(all((folder / r).exists() for r in written), "a file was not written")
    hook = getattr(S, "after_code", None)
    if callable(hook):
        j.note(hook(j, win, project, folder) or "")
    first = next(iter(files), None)
    if first:
        from radide.features import web_workspace as ww
        ww.open_file(win, folder / first)
        E.pump(0.8)
    j.shot(win, "ide_code_editor")
    j.note(f"{len(written)} files typed in the editor")


# ============================================================================ 3. database
def db_rows(sql: str):
    p = folder / S.DB_FILE
    with sqlite3.connect(p) as c:
        return c.execute(sql).fetchall()


with j.step("database"):
    need_project()
    if not FEATURES.get("db", True) or not getattr(S, "DB_FILE", None):
        raise E.Skip("this stack has no database (static site)")
    pre = getattr(S, "before_database", None)
    if callable(pre):
        j.note(pre(j, win, project, folder) or "")
    panel = win.databases
    win.a_databases.trigger()
    E.pump(0.3)
    dbp = folder / S.DB_FILE
    dbp.parent.mkdir(parents=True, exist_ok=True)
    cid = panel.add_sqlite(dbp, project, "store")
    j.check(cid, "add_sqlite returned no connection id")
    if getattr(S, "DB_SQL", ""):
        qv = panel.open_query(cid, S.DB_SQL)
        j.check(qv is not None, "SQL Query tab did not open")
        res = qv.run(wait=True)
        E.pump(0.5)
        bad = [r.message for r in (res or []) if not r.ok]
        j.check(res and not bad, f"SQL errors: {bad[:3]}")
        j.shot(qv, "db_query")
    panel.refresh_connection(cid)
    tv = panel.open_table(cid, "products")
    j.check(tv is not None, "the products table did not open")
    E.pump(0.5)
    model = getattr(tv, "model", None)
    n = model.rowCount() if model is not None and callable(getattr(model, "rowCount", None)) else -1
    j.shot(tv, "db_products_table")
    names = [r[0] for r in db_rows("SELECT name FROM products ORDER BY id")]
    j.check("Laptop" in names and "Phone" in names, f"seed rows missing: {names}")
    j.note(f"products table: {n} rows in the grid, {names}")
    panel.disconnect(cid) if callable(getattr(panel, "disconnect", None)) else None


# ============================================================================ 4. design view (GrapesJS)
HERO = ('<section class="hero" id="hero"><h1 id="hero-title">Welcome to RAD Store</h1>'
        '<p id="hero-text">Laptops, phones and more - designed in the RAD IDE Design View.</p>'
        '<a class="btn" href="PRODUCTS_URL">Browse products</a></section>')

with j.step("design"):
    need_project()
    page = getattr(S, "DESIGN", None)
    if not page:
        raise E.Skip(getattr(S, "DESIGN_SKIP", "no designable page in this stack"))
    from radide.features import web_workspace as ww
    path = folder / page
    before = path.read_text(encoding="utf-8")
    view = ww.open_design(win, path)
    j.check(view is not None, "Design View did not open")
    ok = E.wait(lambda: view.is_ready(), getattr(S, "DESIGN_TIMEOUT", 180))   # 25-60 s on a busy machine
    j.check(ok, "GrapesJS did not become ready in time (DESIGN_TIMEOUT)")
    E.pump(1.0)
    page_ = view.web.page()
    blocks = E.js(page_, "radEditor.BlockManager.getAll().map(b => b.getId()).slice(0, 60)")
    hero = HERO.replace("PRODUCTS_URL", ROUTES.get("products", "/products"))
    # a user drags the "Section" block onto the canvas, then edits its content: same model operations
    host = getattr(S, "DESIGN_TARGET", "#home")
    r = E.js(page_, "(function(){var w=radEditor.getWrapper();var t=w.find(%s)[0]||w;"
                    "var added=t.append(%s);radEditor.select(added[0]);"
                    "return w.find('#hero-title').length;})()" % (json.dumps(host), json.dumps(hero)))
    j.check(r == 1, f"hero not in the canvas: {r}; blocks={blocks}")
    # style it in the Style Manager (selected component): a centred hero
    E.js(page_, "radEditor.getSelected().addStyle({'text-align':'center'}) && 1")
    E.pump(1.5)
    view.sync_now() if callable(getattr(view, "sync_now", None)) else None
    E.pump(0.5)
    j.shot(view, "design_view_home")
    saved = view.save()
    E.pump(0.5)
    after = path.read_text(encoding="utf-8")
    j.check(saved and "Welcome to RAD Store" in after, f"saved={saved}; hero not in {page}")
    keep = getattr(S, "DESIGN_KEEP", [])
    lost = [k for k in keep if k in before and k not in after]
    j.check(not lost, f"server code lost by the designer round trip: {lost}")
    j.note(f"{len(blocks or [])} toolbox blocks; {page} {len(before)} -> {len(after)} chars")
    try:
        win.tabs.removeTab(win.tabs.indexOf(view))
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ 5. run
B = None
with j.step("run"):
    need_project()
    pre = getattr(S, "before_run", None)
    if callable(pre):
        j.note(pre(j, win, project, folder) or "")
    win.a_site_run.trigger()
    ok = E.wait(lambda: getattr(win, "web_server", None) is not None, 30)
    j.check(ok, f"no web server after Site > Run; output: {j.output_text()[-800:]}")
    srv = win.web_server
    tmo = getattr(S, "RUN_TIMEOUT", 180)
    ok = E.wait(lambda: srv.is_ready(), tmo, 0.3) if callable(getattr(srv, "is_ready", None)) else True
    j.check(ok, f"server not ready in {tmo}s: {j.output_text()[-1500:]}")
    base = srv.url.rstrip("/")
    j.check(E.http_up(base + ROUTES["home"], tmo), f"{base} does not answer: {j.output_text()[-1500:]}")
    B = E.Browser(base)
    view = win.web_preview.view
    E.page_loaded(view, "", 60)
    E.pump(1.0)
    j.shot(win.web_preview, "preview_home")
    j.shot(win, "ide_running")
    j.note(f"{base} ({type(srv).__name__})")
    CTX["base"] = base


def need_server():
    if B is None:
        raise E.Skip("the site is not running")


# ============================================================================ 6. pages
with j.step("pages"):
    need_server()
    r = B.get(ROUTES["home"])
    j.check(r.status == 200, f"home {r.status}")
    if getattr(S, "DESIGN", None):
        j.check("Welcome to RAD Store" in r.text, "the designed hero is not on the home page")
    else:
        j.check("RAD Store" in r.text, "home page has no 'RAD Store'")
    notes = [f"home {r.status}"]
    if "products" in ROUTES:
        r = B.get(ROUTES["products"])
        j.check(r.status == 200 and "Laptop" in r.text and "Phone" in r.text,
                f"products {r.status}: {r.text[:300]}")
        notes.append(f"products {r.status}")
    for key, want in (("css", "css"), ("js", "javascript")):
        if key in ROUTES:
            r = B.get(ROUTES[key])
            j.check(r.status == 200 and want in r.ctype, f"{key} {r.status} {r.ctype}")
            notes.append(f"{key} {r.status} {r.ctype.split(';')[0]}")
    r = B.get(getattr(S, "MISSING", "/no-such-page-404"))
    j.check(r.status == 404, f"missing page gives {r.status}")
    notes.append("missing 404")
    j.note(", ".join(notes))


# ============================================================================ 7. login
def login(user="admin", password="secret"):
    return B.submit(ROUTES["login"], {S.LOGIN_FIELDS[0] if hasattr(S, "LOGIN_FIELDS") else "username": user,
                                      S.LOGIN_FIELDS[1] if hasattr(S, "LOGIN_FIELDS") else "password": password})


with j.step("login"):
    need_server()
    if not FEATURES.get("auth", True):
        raise E.Skip(FEATURES.get("auth_skip", "no server-side login in this stack"))
    anon = E.Browser(B.base)
    r = anon.get(ROUTES["add"], follow=False)
    j.check(r.status in (301, 302, 303, 307, 401, 403), f"anonymous add page answers {r.status}")
    loc = r.headers.get("Location", "") if r.headers else ""
    r = login("admin", "wrong-password")
    j.check(r.status in (200, 401, 422) and re.search(S.LOGIN_ERROR if hasattr(S, "LOGIN_ERROR") else "Invalid",
                                                       r.text, re.I),
            f"wrong password: {r.status} {r.text[:300]}")
    r = login()
    j.check(r.status == 200 and "Log out" in r.text, f"login: {r.status} chain={r.chain} {r.text[:300]}")
    j.note(f"anonymous add -> {loc or r.status}; wrong password refused; logged in (cookies {sorted(B.cookies())})")


# ============================================================================ 8. CRUD
def api_products():
    r = B.get(ROUTES["api"], headers={"Accept": "application/json"})
    return r, (r.json() if r.status == 200 else None)


def find_id(name):
    _r, rows = api_products()
    for p in rows or []:
        if p.get("name") == name:
            return p.get("id")
    return None


with j.step("crud"):
    need_server()
    if not FEATURES.get("crud", True):
        raise E.Skip(FEATURES.get("crud_skip", "no server-side CRUD in this stack"))
    nf, pf = getattr(S, "PRODUCT_FIELDS", ("name", "price"))
    n0 = len(api_products()[1] or [])
    r = B.submit(ROUTES["add"], {nf: "", pf: "5"})
    j.check(re.search(getattr(S, "REQUIRED_ERROR", "Name is required|required|blank|empty"), r.text, re.I)
            and r.status in (200, 400, 422), f"empty name accepted? {r.status} {r.text[:400]}")
    j.check(len(api_products()[1] or []) == n0, "an invalid product was saved")
    r = B.submit(ROUTES["add"], {nf: "Tablet", pf: "300"})
    j.check(r.status == 200 and "Tablet" in r.text, f"add: {r.status} chain={r.chain} {r.text[:300]}")
    pid = find_id("Tablet")
    j.check(pid is not None, "Tablet not in the API after add")
    edit = ROUTES["edit"].format(id=pid)
    r = B.submit(edit, {nf: "Tablet Pro", pf: "350"}, form_match=getattr(S, "EDIT_FORM_MATCH", ""))
    j.check(r.status == 200 and "Tablet Pro" in r.text, f"edit: {r.status} chain={r.chain} {r.text[:300]}")
    if getattr(S, "DB_FILE", None) and (folder / S.DB_FILE).exists() and getattr(S, "DB_DIRECT_CHECK", True):
        rows = db_rows(f"SELECT name, price FROM {getattr(S, 'DB_TABLE', 'products')} WHERE name = 'Tablet Pro'")
        j.check(rows and abs(float(rows[0][1]) - 350) < 0.01, f"database row after edit: {rows}")
    dpage = ROUTES.get("delete_page", edit).format(id=pid)
    r = B.submit(dpage, {}, form_match=getattr(S, "DELETE_FORM_MATCH", "delete"))
    j.check(r.status == 200 and "Tablet Pro" not in r.text, f"delete: {r.status} chain={r.chain} {r.text[:300]}")
    j.check(find_id("Tablet Pro") is None, "still in the API after delete")
    j.note(f"validation, add (id {pid}), edit, delete OK; {n0} products before and after")


# ============================================================================ 9. API
with j.step("api"):
    need_server()
    if not FEATURES.get("api", True):
        raise E.Skip(FEATURES.get("api_skip", "no JSON API in this stack"))
    r, rows = api_products()
    j.check(r.status == 200 and "json" in r.ctype, f"api {r.status} {r.ctype}")
    j.check(isinstance(rows, list) and {"Laptop", "Phone"} <= {p.get("name") for p in rows},
            f"api rows: {str(rows)[:300]}")
    j.check(all({"id", "name", "price"} <= set(p) for p in rows), f"fields: {rows[:2]}")
    j.note(f"{len(rows)} products, {r.ctype}")


# ============================================================================ 10. Arabic RTL
with j.step("arabic"):
    need_server()
    r = B.get(ROUTES["ar"])
    j.check(r.status == 200, f"ar page {r.status}")
    j.check(re.search(r'<html[^>]*dir="rtl"', r.text) and re.search(r'<html[^>]*lang="ar"', r.text),
            "no <html lang=ar dir=rtl>")
    j.check("متجر" in r.text, "Arabic text missing")
    view = win.web_preview.view
    win.web_preview.open_url(B.url(ROUTES["ar"]))
    j.check(E.page_loaded(view, ROUTES["ar"].split("?")[0].rstrip("/") or "/", 40), "Preview did not load the page")
    E.pump(0.8)
    d = E.js(view.page(), "JSON.stringify({dir: getComputedStyle(document.body).direction, "
                          "lang: document.documentElement.lang, h1: (document.querySelector('h1')||{}).textContent})")
    d = json.loads(d) if isinstance(d, str) and d.startswith("{") else {}
    j.check(d.get("dir") == "rtl" and d.get("lang") == "ar", f"computed direction in the Preview: {d}")
    j.shot(win.web_preview, "preview_arabic_rtl")
    j.note(f"Preview: {d}")


# ============================================================================ 11. Preview DOM + devices
with j.step("preview"):
    need_server()
    view = win.web_preview.view
    path = ROUTES.get("products", ROUTES["home"])
    win.web_preview.open_url(B.url(path))
    j.check(E.page_loaded(view, path.split("?")[0], 40), "Preview did not load the products page")
    E.pump(getattr(S, "PREVIEW_SETTLE", 1.0))
    sel = getattr(S, "PREVIEW_ROWS", "#products tbody tr")
    cnt = E.wait(lambda: (E.js(view.page(), f"document.querySelectorAll({json.dumps(sel)}).length", 3) or 0) >= 2,
                 20, 0.3)
    n = E.js(view.page(), f"document.querySelectorAll({json.dumps(sel)}).length")
    css = E.js(view.page(), "getComputedStyle(document.body).fontFamily")
    j.check(cnt and n >= 2, f"rows in the Preview DOM: {n}")
    j.shot(win.web_preview, "preview_products_desktop")
    sizes = []
    pv = win.web_preview
    for i in range(pv.device.count()):
        t = pv.device.itemText(i)
        if any(k in t for k in ("Phone", "iPhone", "Tablet", "iPad", "Fold")):
            pv.device.setCurrentIndex(i)
            E.pump(1.0)
            vw = E.js(view.page(), "window.innerWidth")
            sizes.append(f"{t.split('(')[0].strip()}={vw}px")
            j.shot(pv, "preview_" + re.sub(r"\W+", "_", t.split("(")[0].strip()).lower())
            if len(sizes) >= 3:
                break
    pv.device.setCurrentIndex(0)
    E.pump(0.5)
    j.check(sizes, "no phone/tablet device sizes in the Preview")
    j.note(f"{n} rows; font {str(css)[:40]}; devices {sizes}")


# ============================================================================ 12. debug
with j.step("debug"):
    need_server()
    dbg = getattr(S, "DEBUG", None)
    if not dbg or not FEATURES.get("debug", True):
        raise E.Skip(getattr(S, "DEBUG_SKIP", "no debugger for this stack"))
    from radide.features import web_workspace as ww
    ww.stop_website(win)
    E.pump(1.0)
    path = folder / dbg["file"]
    ed = ww.open_file(win, path)
    lines = path.read_text(encoding="utf-8").splitlines()
    ln = next(i for i, t in enumerate(lines) if dbg["match"] in t)
    ed.toggle_breakpoint(ln)                       # F9 on that line
    E.pump(0.3)
    key = next((k for k, v in win.breakpoints.items() if ln in v), None)
    j.check(key is not None, f"F9 did not register a breakpoint: {win.breakpoints}")
    win.a_run.trigger()                            # F5 = Start Debugging
    tmo = getattr(S, "DEBUG_TIMEOUT", 180)
    ok = E.wait(lambda: getattr(win, "web_server", None) is not None and win.web_server.is_ready()
                and getattr(win, "session", None) is not None, tmo, 0.3)
    j.check(ok, f"debug session/server not started in {tmo}s; output: {j.output_text()[-1500:]}")
    base = win.web_server.url.rstrip("/")
    E.http_up(base + "/", 60) if dbg.get("warm", True) else None
    sess = win.session
    E.wait(lambda: getattr(sess, "ready", True), 30)
    E.pump(getattr(S, "DEBUG_SETTLE", 3.0))
    box = {}

    def req():
        try:
            box["r"] = E.Browser(base).get(dbg["path"], timeout=120)
        except Exception as e:  # noqa: BLE001
            box["e"] = e
    preview = dbg.get("trigger") == "preview"
    th = threading.Thread(target=req, daemon=True)
    if preview:            # client-side code: the Preview runs the page's script
        win.web_preview.open_url(base + dbg["path"])
    else:
        th.start()
    paused = E.wait(lambda: getattr(sess, "paused", False) or win.stopped_at is not None, 90, 0.2)
    E.pump(1.0)
    loc = win.callstack.item(0).text() if win.callstack.count() else ""
    names = [win.locals.topLevelItem(i).text(0) for i in range(win.locals.topLevelItemCount())]
    j.shot(win, "debug_paused")
    j.check(paused, f"the request did not pause at {dbg['file']}:{ln + 1}; output: {j.output_text()[-1200:]}")
    j.check(Path(dbg["file"]).name in loc or not loc, f"paused in {loc}")
    win.a_run.trigger()                            # F5 = Continue
    if preview:
        view = win.web_preview.view
        ok = E.wait(lambda: (E.js(view.page(), "document.querySelectorAll('#products tbody tr').length", 3) or 0)
                    >= 2, 30, 0.3)
        j.check(ok, "the page did not finish its script after Continue")
    else:
        th.join(60)
        r = box.get("r")
        j.check(r is not None and r.status == 200, f"request after Continue: {box}")
    ed.toggle_breakpoint(ln)
    win.a_stop.trigger()
    E.pump(1.5)
    ww.stop_website(win)
    E.pump(0.5)
    j.note(f"paused at {loc or dbg['file']}:{ln + 1}; locals {names[:8]}")


# ============================================================================ 13. IntelliSense
def suggest_rows(ed, text_before_cursor_line: int, col: int, typed: str, rounds: int = 30):
    E.js(ed.page(), f"(radEditor.setPosition({{lineNumber: {text_before_cursor_line}, column: {col}}}), "
                    "radEditor.focus(), 1)")
    E.js(ed.page(), f"(radEditor.trigger('keyboard', 'type', {{text: {json.dumps(typed)}}}), 1)")
    rows = []
    for _ in range(rounds):
        E.pump(0.3)
        raw = E.js(ed.page(), "JSON.stringify([...document.querySelectorAll('.suggest-widget.visible "
                              ".monaco-list-row')].map(e => e.getAttribute('aria-label') || e.textContent))", 3)
        rows = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
        if rows:
            break
    if not rows:
        E.js(ed.page(), "(radEditor.trigger('keyboard', 'editor.action.triggerSuggest', {}), 1)")
        for _ in range(rounds):
            E.pump(0.3)
            raw = E.js(ed.page(), "JSON.stringify([...document.querySelectorAll('.suggest-widget.visible "
                                  ".monaco-list-row')].map(e => e.getAttribute('aria-label') || e.textContent))", 3)
            rows = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
            if rows:
                break
    E.js(ed.page(), "(radEditor.trigger('keyboard', 'hideSuggestWidget', {}), 1)")
    return rows


def capture(ed, fn_name, *args, timeout=25.0):
    sent = []
    orig = ed._js
    mark = f"radResolve({args[0]},"
    ed._js = lambda code: sent.append(code) if code.startswith(mark) else orig(code)
    try:
        getattr(ed, fn_name)(*args)
        E.wait(lambda: bool(sent), timeout)
    finally:
        ed._js = orig
    for code in sent:
        payload = code[len("radResolve("):].split(",", 1)[1].rsplit(");", 1)[0]
        try:
            return json.loads(payload)
        except ValueError:
            return payload
    return None


def labels(items):
    out = []
    for i in items or []:
        lab = i.get("label") if isinstance(i, dict) else str(i)
        if isinstance(lab, dict):
            lab = lab.get("label", "")
        out.append(str(lab))
    return out


with j.step("intellisense"):
    need_project()
    spec = getattr(S, "INTELLI", None)
    if not spec:
        raise E.Skip("no IntelliSense probe for this stack")
    from radide.features import web_workspace as ww
    notes, fails = [], []
    # --- the language: completions after typing a prefix inside the server code
    path = folder / spec["file"]
    original = path.read_text(encoding="utf-8")
    ed = ww.open_file(win, path)
    monaco = type(ed).__name__ == "MonacoEditor"
    j.check(monaco, f"the code editor is {type(ed).__name__}, not Monaco")
    E.wait(lambda: getattr(ed, "_ready", True), 30)
    lines = original.split("\n")
    at = next(i for i, t in enumerate(lines) if spec["after"] in t) + 1
    indent = re.match(r"\s*", lines[at] if at < len(lines) else "").group()
    lines.insert(at, indent + spec["type"])
    ed.setText("\n".join(lines))
    E.pump(spec.get("settle", 1.0))
    col = len(indent) + len(spec["type"]) + 1
    items = labels(capture(ed, "_complete", 9101, at, col, timeout=spec.get("timeout", 30)))
    if not any(spec["expect"].lower() in x.lower() for x in items):
        rows = suggest_rows(ed, at + 1, col - 1, spec["type"][-1:])
        items += rows
    ok = any(spec["expect"].lower() in x.lower() for x in items)
    j.shot(ed, "intellisense_language")
    (notes if ok else fails).append(f"{spec['file']}: '{spec['type']}' -> {spec['expect']} "
                                    f"{'found' if ok else 'missing'} ({len(items)} items: {items[:6]})")
    ed.setText(original)
    ed.setModified(False) if hasattr(ed, "setModified") else None
    # --- HTML: '<inp' in a page -> input
    if spec.get("html_file"):
        hp = folder / spec["html_file"]
        htext = hp.read_text(encoding="utf-8")
        hed = ww.open_file(win, hp)
        E.wait(lambda: getattr(hed, "_ready", True), 30)
        hl = htext.split("\n")
        k = next((i for i, t in enumerate(hl) if "<body" in t), len(hl) - 2) + 1
        hl.insert(k, "")
        hed.setText("\n".join(hl))
        E.pump(0.8)
        rows = suggest_rows(hed, k + 1, 1, spec.get("html_type", "<inp"))
        ok = any("input" in r.lower() for r in rows)
        j.shot(hed, "intellisense_html")
        (notes if ok else fails).append(f"HTML '<inp' -> {rows[:5]}")
        hed.setText(htext)
        hed.setModified(False) if hasattr(hed, "setModified") else None
    # --- CSS: 'backg' in a rule -> background
    if spec.get("css_file"):
        cp = folder / spec["css_file"]
        ctext = cp.read_text(encoding="utf-8")
        ced = ww.open_file(win, cp)
        E.wait(lambda: getattr(ced, "_ready", True), 30)
        cl = ctext.split("\n") + [".e2e {", "  ", "}"]
        ced.setText("\n".join(cl))
        E.pump(0.8)
        rows = suggest_rows(ced, len(cl) - 1, 3, "backg")
        ok = any("background" in r.lower() for r in rows)
        j.shot(ced, "intellisense_css")
        (notes if ok else fails).append(f"CSS 'backg' -> {rows[:4]}")
        ced.setText(ctext)
        ced.setModified(False) if hasattr(ced, "setModified") else None
    win.save_all()
    E.pump(0.3)
    j.check(path.read_text(encoding="utf-8") == original, "probe text leaked into the file")
    j.check(not fails, "; ".join(fails))
    j.note("; ".join(notes))


# ============================================================================ 14. publish (Local folder)
PUB = j.work / "published" / S.NAME


def publish_dialog(kind: str, **fields):
    """Site > Publish..., a new profile of *kind*, fill the fields, Publish; returns (ok, log text)."""
    from radide.features.web_tools import PublishDialog
    dlg = PublishDialog(win, project)
    dlg._e2e_keep = True
    dlg.show()
    E.pump(0.4)
    dlg.add_profile()
    E.pump(0.2)
    dlg.f_name.setText(fields.pop("name", kind))
    i = dlg.f_kind.findData(kind)
    if i < 0:
        i = next(k for k in range(dlg.f_kind.count()) if kind.lower() in dlg.f_kind.itemText(k).lower())
    dlg.f_kind.setCurrentIndex(i)
    E.pump(0.2)
    for k, v in fields.items():
        w = getattr(dlg, k)
        if hasattr(w, "setChecked") and isinstance(v, bool):
            w.setChecked(v)
        elif hasattr(w, "setValue"):
            w.setValue(int(v))
        else:
            w.setText(str(v))
    extra_ex = getattr(S, "PUBLISH_EXCLUDES", [])      # typed into the dialog's Exclude box, one per line
    if extra_ex:
        dlg.f_excl.setPlainText(dlg.f_excl.toPlainText().rstrip() + "\n" + "\n".join(extra_ex))
    E.pump(0.2)
    dlg.start(dry_run=False)
    done = E.wait(lambda: not dlg._busy, 600, 0.2)
    E.pump(0.5)
    log = ""
    for attr in ("log", "log_box", "output"):
        w = getattr(dlg, attr, None)
        if w is not None and hasattr(w, "toPlainText"):
            log = w.toPlainText()
            break
    j.shot(dlg, f"publish_{kind}")
    dlg.close()
    E.pump(0.3)
    return done, log


with j.step("publish folder"):
    need_project()
    shutil.rmtree(PUB, ignore_errors=True)
    pre = getattr(S, "before_publish", None)
    if callable(pre):
        j.note(pre(j, win, project, folder) or "")
    done, log = publish_dialog("folder", name="Local folder", f_remote=str(PUB))
    j.check(done, "publish did not finish in 10 minutes")
    got = {p.relative_to(PUB).as_posix() for p in PUB.rglob("*") if p.is_file()} if PUB.exists() else set()
    miss = [e for e in getattr(S, "PUBLISH_EXPECT", []) if e not in got]
    bad = [e for e in getattr(S, "PUBLISH_FORBID", []) if e in got]
    j.check(got and not miss, f"missing in the published folder: {miss}; log: {log[-600:]}")
    j.check(not bad, f"published files that must be excluded: {bad}")
    j.note(f"{len(got)} files -> {PUB}")


# ============================================================================ 15. publish (FTP)
with j.step("publish ftp"):
    need_project()
    libs = Path(os.environ.get("E2E_PYLIBS") or (j.out.parent / "_pylibs"))
    if not (libs / "pyftpdlib").exists():
        code, out = E.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--target",
                           str(libs), "pyftpdlib"], timeout=300)
        if code != 0:
            raise E.Skip(f"pyftpdlib not available (pip: {out[-200:]})")
    ftp_root = j.work / "ftp_root"
    shutil.rmtree(ftp_root, ignore_errors=True)
    (ftp_root / "www").mkdir(parents=True)
    port = E.free_port()
    srv_py = j.work / "ftp_server.py"
    srv_py.write_text(
        "import sys\nsys.path.insert(0, sys.argv[1])\n"
        "from pyftpdlib.authorizers import DummyAuthorizer\nfrom pyftpdlib.handlers import FTPHandler\n"
        "from pyftpdlib.servers import FTPServer\n"
        "a = DummyAuthorizer(); a.add_user('deploy', 'pw-e2e', sys.argv[2], perm='elradfmwMT')\n"
        "h = FTPHandler; h.authorizer = a; h.passive_ports = range(int(sys.argv[4]), int(sys.argv[4]) + 20)\n"
        "FTPServer(('127.0.0.1', int(sys.argv[3])), h).serve_forever()\n", encoding="utf-8")
    pasv = E.free_port()
    p = E.start([sys.executable, "-I", srv_py, libs, ftp_root, port, pasv], log=j.work / "ftp_server.log")
    import socket
    up = E.wait(lambda: socket.create_connection(("127.0.0.1", port), 1).close() is None, 20, 0.3)
    j.check(up, "local FTP server did not start")
    from radide.web_site import publish as wp
    wp.set_password(win.settings, project.folder, "Local FTP", "pw-e2e")
    done, log = publish_dialog("ftp", name="Local FTP", f_host="127.0.0.1", f_port=port, f_user="deploy",
                               f_pass="pw-e2e", f_savepw=True, f_remote="/www", f_passive=True)
    E.kill_tree(p)
    got = {x.relative_to(ftp_root / "www").as_posix() for x in (ftp_root / "www").rglob("*") if x.is_file()}
    miss = [e for e in getattr(S, "PUBLISH_EXPECT", []) if e not in got]
    j.check(done and got and not miss, f"FTP publish: {len(got)} files, missing {miss}; log: {log[-600:]}")
    j.note(f"{len(got)} files uploaded to ftp://127.0.0.1:{port}/www")


# ============================================================================ 16. run the published copy
with j.step("published run"):
    need_project()
    if not PUB.exists():
        raise E.Skip("nothing published")
    fn = getattr(S, "serve_published", None)
    if not callable(fn):
        raise E.Skip("this stack's published output is not runnable on its own here")
    port = E.free_port()
    argv, cwd, env = fn(PUB, port, **({"php": tool_path("php")} if "php" in getattr(S, "TOOLS", []) else {}))
    if argv is None:
        raise E.Skip(cwd)
    p = E.start(argv, cwd=cwd, env=env, log=j.work / "published_server.log")
    base = f"http://127.0.0.1:{port}"
    ok = E.http_up(base + ROUTES["home"], getattr(S, "PUBLISHED_TIMEOUT", 120))
    log_text = lambda: (j.work / "published_server.log").read_text(encoding="utf-8", errors="replace")[-800:]  # noqa: E731
    j.check(ok, f"published site does not answer: {log_text()}")
    pb = E.Browser(base)
    r = pb.get(ROUTES["home"])
    j.check(r.status == 200 and ("Welcome to RAD Store" if getattr(S, "DESIGN", None) else "RAD Store") in r.text,
            f"published home {r.status}")
    seen = ["home"]
    for key in ("products", "ar", "api", "css"):
        if key in ROUTES and (key != "api" or FEATURES.get("api", True)):
            r = pb.get(ROUTES[key])
            j.check(r.status == 200, f"published {key}: {r.status} {r.text[:200]}")
            if key == "products":
                j.check("Laptop" in r.text, "published products page has no seeded product")
            seen.append(f"{key} {r.status}")
    if FEATURES.get("auth", True) and "login" in ROUTES:
        bb, B2 = B, pb
        r = B2.submit(ROUTES["login"], {getattr(S, "LOGIN_FIELDS", ("username", "password"))[0]: "admin",
                                        getattr(S, "LOGIN_FIELDS", ("username", "password"))[1]: "secret"})
        j.check(r.status == 200 and "Log out" in r.text, f"published login: {r.status}")
        seen.append("login")
    view = win.web_preview.view
    win.web_preview.open_url(base + ROUTES.get("products", ROUTES["home"]))
    E.page_loaded(view, str(port), 30)
    E.pump(0.8)
    j.shot(win.web_preview, "preview_published_site")
    E.kill_tree(p)
    j.note(f"{base}: {', '.join(seen)}")

j.finish()
