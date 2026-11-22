# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""The web journey against the REAL frozen RADIDE.exe, through the automation channel (radide/automation,
commands_web.py) - the seams of the installed build: the web templates, the PHP / Node / Python dev servers, the
bundled GrapesJS and Monaco, the Databases workspace, QtWebEngine and Publish inside the frozen exe.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Web\\journey_web_frozen.py <scratch> --onedir <build>\\dist\\RADIDE
                                                  [--stacks php,static,node,flask,fastapi] [--source]

The IDE runs in a portable copy of the build (settings inside the copy) on a hidden Win32 desktop, offscreen.
Per stack: New Project (real dialog) -> files typed in the code editor -> Databases workspace (SQL + table) ->
Design View -> Site > Run Site in Preview -> HTTP: pages, login, CRUD, API, Arabic -> Preview DOM (phone size) ->
Site > Publish (Local folder) -> the published copy runs on its own. Reports: <scratch>/report/web-<stack>/.
Exit code = number of failed steps. Stacks with hooks that need the in-process IDE (django: Django panel) are
covered by journey_web.py only.
"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import e2e_lib as E  # noqa: E402  (Browser, start / kill_tree, free_port, http_up; no Qt in this process)
import webcheck as W  # noqa: E402
from radauto import Desktop, Report, Skip, check  # noqa: E402
import e2e_common as C  # noqa: E402

FROZEN_STACKS = ("php", "static", "node", "flask", "fastapi")
HERO = ('<section class="hero" id="hero"><h1 id="hero-title">Welcome to RAD Store</h1>'
        '<p id="hero-text">Designed in the Design View of the frozen RAD IDE.</p>'
        '<a class="btn" href="PRODUCTS_URL">Browse products</a></section>')


def tool_ok(S) -> str:
    missing = [t for t in getattr(S, "TOOLS", []) if not shutil.which(t)]
    extra = getattr(S, "toolchain_check", None)
    why = extra() if callable(extra) else ""
    return (f"missing: {', '.join(missing)}" if missing else "") + (f" {why}" if why else "")


def journey(env, name: str) -> dict:
    S = importlib.import_module(f"stacks.{name}")
    rep = Report(f"web-{name}", env.out / f"web-{name}")
    why = tool_ok(S)
    steps = ["new project", "code", "database", "design", "run", "pages", "login", "crud", "api", "arabic",
             "preview", "publish folder", "published run"]
    if why:
        rep.skip_rest(steps, why.strip())
        return rep.save()
    ide = C.launch(env, f"web-{name}")
    rep.ide = ide
    work = env.scratch / "work" / name
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    st: dict = {}

    def new_project():
        info = ide.call("new_project", language=S.LANG, template=S.TEMPLATE, name=S.NAME, location=str(work),
                        timeout_s=1800)
        info = ide.call("project") or info
        check(info and info.get("language") == S.LANG, f"project: {info}")
        st["folder"] = Path(info["folder"])
        for attr in ("CTX",):
            if isinstance(getattr(S, attr, None), dict):
                S.CTX["folder"] = str(st["folder"])
        if isinstance(getattr(S, "CTX_FOLDER", None), list):
            S.CTX_FOLDER[:] = [str(st["folder"])]
        hook = getattr(S, "after_create", None)
        if callable(hook) and name in ("static", "flask", "fastapi"):
            hook(None, None, None, st["folder"])       # these hooks only touch files
        return f"{info['language']} at {info['folder']}"

    def need():
        if "folder" not in st:
            raise Skip("no project")

    def code():
        need()
        files = S.files()
        bad = [r for r, t in files.items() if not ide.call("web_write_file", path=str(st["folder"] / r),
                                                           text=t).get("saved")]
        check(not bad, f"not saved: {bad}")
        return f"{len(files)} files typed in the editor"

    def database():
        need()
        if not W.features(S).get("db", True) or not getattr(S, "DB_FILE", None):
            raise Skip("no database in this stack")
        r = ide.call("web_db_sql", path=S.DB_FILE, sql=getattr(S, "DB_SQL", ""), table="products")
        check(not r["errors"], f"SQL errors {r['errors']}")
        names = [row[1] for row in r["rows"] if len(row) > 1]
        check("Laptop" in names and "Phone" in names, f"rows {r['rows']}")
        return f"{len(r['rows'])} rows {names}"

    def design():
        need()
        if not getattr(S, "DESIGN", None):
            raise Skip("no designable page")
        r = ide.call("web_design", path=S.DESIGN, target=getattr(S, "DESIGN_TARGET", "#home"),
                     html=HERO.replace("PRODUCTS_URL", S.ROUTES.get("products", "/")), style={"text-align": "center"})
        text = (st["folder"] / S.DESIGN).read_text(encoding="utf-8")
        check(r["saved"] and "Welcome to RAD Store" in text, f"design: {r}")
        lost = [k for k in getattr(S, "DESIGN_KEEP", []) if k not in text]
        check(not lost, f"server code lost: {lost}")
        return f"{r['blocks']} blocks, {r['before']} -> {r['after']} chars"

    def run():
        need()
        ide.trigger("Site/Run Site in Preview")
        tmo = getattr(S, "RUN_TIMEOUT", 180)
        s = ide.wait_for(lambda: (lambda v: v if v.get("running") and v.get("ready") else None)(
            ide.call("web_server")), timeout=tmo, desc="dev server ready")
        base = s["url"].rstrip("/")
        check(E.http_up(base + S.ROUTES["home"], tmo), f"{base} does not answer")
        st["B"] = E.Browser(base)
        return base

    def http(fn):
        def f():
            if "B" not in st:
                raise Skip("the site is not running")
            return fn()
        return f

    def login():
        if not W.features(S).get("auth", True):
            raise Skip(W.features(S).get("auth_skip", "no login"))
        return W.auth(S, st["B"], E.Browser)

    def crud():
        if not W.features(S).get("crud", True):
            raise Skip(W.features(S).get("crud_skip", "no CRUD"))
        return W.crud(S, st["B"])

    def preview():
        base = st["B"].base
        path = S.ROUTES.get("products", S.ROUTES["home"])
        sel = getattr(S, "PREVIEW_ROWS", "#products tbody tr")
        r = ide.call("web_preview", url=base + path, device="Phone", timeout_s=40,
                     exprs=[f"document.querySelectorAll({json.dumps(sel)}).length", "window.innerWidth"])
        time.sleep(1)
        r2 = ide.call("web_preview", exprs=[f"document.querySelectorAll({json.dumps(sel)}).length"])
        rows = max(r["values"][0] or 0, r2["values"][0] or 0)
        rep.shot("preview_phone", sel="@web_preview")
        ar = ide.call("web_preview", url=base + S.ROUTES["ar"], device="Desktop",
                      exprs=["getComputedStyle(document.body).direction"])
        check(r["loaded"] and rows >= 2, f"products in the Preview: {r}")
        check(ar["values"][0] == "rtl", f"Arabic page direction {ar['values']}")
        return f"{rows} rows at {r['values'][1]}px ({r['device']}), Arabic rtl"

    def publish():
        need()
        dest = work / "published"
        shutil.rmtree(dest, ignore_errors=True)
        r = ide.call("web_publish", kind="folder", name="Local folder", fields={"f_remote": str(dest)})
        got = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()} if dest.exists() else set()
        miss = [e for e in getattr(S, "PUBLISH_EXPECT", []) if e not in got]
        check(r["done"] and got and not miss, f"published {len(got)} files, missing {miss}; {r['log'][-300:]}")
        st["pub"] = dest
        return f"{len(got)} files"

    def published_run():
        if "pub" not in st:
            raise Skip("nothing published")
        fn = getattr(S, "serve_published", None)
        port = E.free_port()
        kw = {"php": shutil.which("php")} if "php" in getattr(S, "TOOLS", []) else {}
        argv, cwd, envv = fn(st["pub"], port, **kw)
        if argv is None:
            raise Skip(cwd)
        p = E.start(argv, cwd=cwd, env=envv, log=work / "published.log")
        try:
            base = f"http://127.0.0.1:{port}"
            check(E.http_up(base + S.ROUTES["home"], 120), "published site does not answer")
            pb = E.Browser(base)
            note = W.pages(S, pb)
            if W.features(S).get("api", True) and "api" in S.ROUTES:
                note += "; " + W.api(S, pb)
            return note
        finally:
            E.kill_tree(p)

    try:
        rep.step("new project", new_project, shot=True, critical=True)
        rep.step("code", code)
        rep.step("database", database)
        rep.step("design", design, shot=True)
        rep.step("run", run, shot=True)
        rep.step("pages", http(lambda: W.pages(S, st["B"])))
        rep.step("login", http(login))
        rep.step("crud", http(crud))
        rep.step("api", http(lambda: W.api(S, st["B"]) if W.features(S).get("api", True) else Skip("no API")))
        rep.step("arabic", http(lambda: W.arabic(S, st["B"])))
        rep.step("preview", http(preview))
        rep.step("publish folder", publish)
        rep.step("published run", published_run)
    except Exception as e:  # noqa: BLE001 - Abort of a critical step
        print("abort:", e)
    finally:
        try:
            ide.trigger("Site/Stop Web Server")
        except Exception:  # noqa: BLE001
            pass
        ide.quit()
        E.stop_all()
    return rep.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--onedir", help="the built dist/RADIDE folder (copied, never run in place)")
    ap.add_argument("--source", action="store_true", help="run python -m radide instead of the frozen exe")
    ap.add_argument("--stacks", default=",".join(FROZEN_STACKS))
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    env = C.Env(scratch=scratch, onedir=Path(a.onedir) if a.onedir else None, source=a.source,
                out=scratch / "report", desktop="RADIDE_E2E_WEB")
    if not a.source:
        if not env.onedir or not (env.onedir / "RADIDE.exe").exists():
            sys.exit("--onedir <dist/RADIDE> (with RADIDE.exe) or --source is required")
        C.portable_copy(env)
    total = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    rows = []
    with Desktop(env.desktop):
        for name in [s.strip() for s in a.stacks.split(",") if s.strip()]:
            if name not in FROZEN_STACKS:
                print(f"SKIP stack {name}: needs the in-process IDE (journey_web.py)")
                continue
            c = journey(env, name)
            rows.append((name, c))
            for k in total:
                total[k] += c[k]
    lines = ["# Web journeys - frozen RADIDE.exe", "", "| stack | PASS | FAIL | SKIP |", "|---|---|---|---|"]
    lines += [f"| {n} | {c['PASS']} | {c['FAIL']} | {c['SKIP']} |" for n, c in rows]
    lines += [f"| **total** | {total['PASS']} | {total['FAIL']} | {total['SKIP']} |"]
    (env.out / "summary_web.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    sys.exit(min(total["FAIL"], 100))


if __name__ == "__main__":
    main()
