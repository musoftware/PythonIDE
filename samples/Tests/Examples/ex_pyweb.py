# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Group "pyweb" of the example tests: Python games (pygame, arcade, kivy, ursina), Python web (Flask, Django,
FastAPI), static web + HTML5 canvas game, Godot and Expo (samples/Examples/{PythonGames,PythonWeb,Web,Godot,Mobile}).

    .venv\\Scripts\\python samples\\Tests\\Examples\\test_examples_scripting.py --group pyweb [--no-publish]

How each kind is checked (only processes started here are closed):
* games      - open: project + scenes load, the designer files list every scene object (kivy: real designer);
               build: py_compile; run: F5's run spec with the IDE's test hooks (RADGAME_FRAMES / RADGAME_KEYS,
               RAD3D_*, RADKIVY_*) - the game's own window must appear and the scripted keys must score;
               publish: Build > Publish (PyInstaller).
* web (py)   - open: the framework's route index; build: compileall in the project's .venv; run: the IDE's
               DevServer (creates the .venv, migrates, starts the framework server) + HTTP GET/POST that add a
               record and read it back; publish: a "Local folder" publish profile (radide.web_site.publish).
* static     - DevServer + HTTP for every page/asset, node --check for the scripts; HTML5 game: html5_headless.js
               plays the scene in Node.js with scripted keys; publish: Local folder profile.
* godot      - scene -> .tscn export, Godot (found by the IDE's locator) imports and runs the game with
               RADGAME_FRAMES/KEYS; the Godot window must appear and a gem must be collected.
* expo       - designer check of both screens, store.js logic in Node, `npx expo export --platform web` when the
               npm packages could be installed (cached under the scratch folder).
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import exlib

HERE = Path(__file__).resolve().parent
CACHE = exlib.SCRATCH / "pyweb"              # copies with their .venv / node_modules kept between runs


# ============================================================================ helpers
def sync_copy(src: Path, keep=(".venv", "node_modules", ".godot")) -> Path:
    """Copy *src* to the scratch folder; the heavy folders of an earlier run (keep) stay so the next run is fast."""
    dst = CACHE / src.parent.name / src.name
    dst.mkdir(parents=True, exist_ok=True)
    for p in dst.iterdir():
        if p.name in keep:
            continue
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", ".venv", "node_modules", "Publish", "dist", "db.sqlite3", "*.db", "instance"))
    return dst


def compile_py(folder: Path, skip=(".venv", "node_modules", "Publish")) -> tuple[bool, str]:
    bad = []
    n = 0
    for p in folder.rglob("*.py"):
        if any(s in p.parts for s in skip):
            continue
        n += 1
        try:
            py_compile.compile(str(p), doraise=True, cfile=str(exlib.SCRATCH / "pyweb_pyc.tmp"))
        except py_compile.PyCompileError as e:
            bad.append(f"{p.name}: {e.msg[:200]}")
    return not bad, (f"{n} files compiled" if not bad else "; ".join(bad))


def header_check(src: Path, exts=(".py", ".js", ".jsx", ".gd", ".html", ".css")) -> list[str]:
    """Source files of the sample (not the IDE's generated runtimes) without the copyright header."""
    generated = {"radgame.py", "radgame_particles.py", "radgame_physics.py", "radgame.js", "scenes.js", "rad3d.py",
                 "radkivy.py", "radapp.js", "App.js", "index.js", "radgame_scene.gd", "manage.py", "asgi.py",
                 "wsgi.py", "settings.py", "apps.py"}
    out = []
    for p in src.rglob("*"):
        if p.suffix not in exts or p.name in generated or p.name.endswith(("_designer.py", "_designer.jsx")) \
                or ".venv" in p.parts or "node_modules" in p.parts or p.name == "__init__.py" and not p.read_text(
                encoding="utf-8").strip() or p.name == "Room1.tscn":
            continue
        if "Musoftware" not in p.read_text(encoding="utf-8", errors="replace")[:400]:
            out.append(str(p.relative_to(src)))
    return out


class Proc:
    """A started program with its output collected in a thread."""

    def __init__(self, argv, cwd, env):
        self.lines: list[str] = []
        self.p = subprocess.Popen(argv, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.p.stdout:
            self.lines.append(line.rstrip())

    def text(self) -> str:
        return "\n".join(self.lines)

    def wait(self, timeout):
        try:
            return self.p.wait(timeout)
        except subprocess.TimeoutExpired:
            exlib.stop_tree(self.p)
            return None


def run_with_window(folder: Path, lang: str, env_extra: dict, title: str, timeout=120, interpreter=""):
    """F5's run spec + test env; returns (window title or "", exit code, output)."""
    from radide.languages import get_plugin
    from radide.model import Project
    plugin = get_plugin(lang)
    project = Project.load(folder)
    interp = interpreter or plugin.find_interpreter("")
    spec = plugin.run_spec(folder, project.startup, interp)
    env = dict(spec.env or os.environ)
    env.update(env_extra)
    pr = Proc([spec.program, *spec.args], spec.cwd or folder, env)
    found = exlib.wait_window(pr.p, title, 60)
    code = pr.wait(timeout)
    time.sleep(0.3)
    return ((found[1] or "(untitled window)") if found else ""), code, pr.text()


def scene_open_check(folder: Path, scene_ext=".scene") -> tuple[bool, str]:
    """Every scene file parses and its generated designer file names every object (the scene designer's view)."""
    from radide.model import Project
    project = Project.load(folder)
    scenes = project.extra.get("scenes3d" if scene_ext == ".scene3d" else "scenes", [])
    notes, ok = [], bool(scenes)
    for s in scenes:
        data = json.loads((folder / f"{s}{scene_ext}").read_text(encoding="utf-8"))
        if scene_ext == ".scene3d":
            names = [e["name"] for e in data["entities"] if e["kind"] not in ("camera", "light")]
            designer = (folder / f"{s}_designer.py").read_text(encoding="utf-8")
        else:
            names = [o["name"] for ly in data["layers"] for o in ly.get("objects", [])]
            dfile = next((folder / f for f in (f"{s}_designer.py", f"{s}.tscn", "scenes.js") if (folder / f).exists()),
                         None)
            designer = dfile.read_text(encoding="utf-8") if dfile else ""
        missing = [n for n in names if n not in designer]
        ok &= not missing
        notes.append(f"{s}: {len(names)} objects" + (f", missing {missing[:5]}" if missing else ""))
    return ok, "; ".join(notes)


def publish_folder(folder: Path, res, expect=(), forbid=(".venv",)):
    """Site > Publish with the project's "Local folder" profile to a scratch destination."""
    from radide.model import Project
    from radide.web_site import publish as wp
    project = Project.load(folder)
    profiles = wp.load_profiles(project)
    prof = next((p for p in profiles if p.kind == "folder"), None)
    if prof is None:
        return res.step("publish", False, "no Local folder publish profile")
    dest = exlib.SCRATCH / "pyweb_publish" / folder.name
    shutil.rmtree(dest, ignore_errors=True)
    prof.remote_dir = str(dest)
    log: list[str] = []
    r = wp.Publisher(prof, wp.local_root(project, prof), None).run(log=log.append)
    files = [p for p in dest.rglob("*") if p.is_file()] if dest.exists() else []
    rel = {p.relative_to(dest).as_posix() for p in files}
    miss = [e for e in expect if e not in rel]
    bad = [f for f in rel if any(f.startswith(x + "/") or f == x for x in forbid)]
    res["size"] = f"{exlib.mb(sum(p.stat().st_size for p in files))} MB / {len(files)} files"
    return res.step("publish", bool(r.ok and files and not miss and not bad),
                    f"kind=web folder, {len(files)} files" + (f", missing {miss}" if miss else "")
                    + (f", should be excluded {bad[:3]}" if bad else "") + ("" if r.ok else f" error={r.error}"))


def publish_exe(folder: Path, res, opts, env_extra=None, title=""):
    """Build > Publish (PyInstaller) and start the published exe once: its window must appear."""
    if not opts.get("publish", True):
        return res.step("publish", "skipped", "--no-publish")
    r = exlib.publish(folder, exlib.SCRATCH / "pyweb_logs" / f"{folder.name}_publish.log")
    started = ""
    if r.get("ok"):
        res["size"] = f"{r['size_mb']} MB"
        exe = Path(r["dist"]) / r["exe"]
        pr = Proc([str(exe)], exe.parent, dict(os.environ, **(env_extra or {})))
        found = exlib.wait_window(pr.p, title, 90)
        pr.wait(60)
        started = f" published exe window={(found[1] or '(untitled window)') if found else ''!r}"
        r["ok"] = bool(found)
    return res.step("publish", bool(r.get("ok")), started.strip() + " " +
                    f"kind={r.get('kind')} exe={r.get('exe', '')} size={r.get('size_mb', '-')}MB "
                    f"python_inside={r.get('python_inside')}" + (f" error={r.get('error')}" if not r.get("ok") else ""))


def dev_server(folder: Path, lang: str):
    from radide.languages import get_plugin
    from radide.model import Project
    from radide.web_site.server import DevServer
    exlib.qapp()
    os.environ["RADIDE_PYWEB_NO_PROGRESS"] = "1"
    plugin = get_plugin(lang)
    project = Project.load(folder)
    interp = plugin.find_interpreter("") if getattr(plugin, "needs_interpreter", False) else ""
    srv = DevServer(project.folder, plugin, project=project, interpreter=interp)
    logs: list[str] = []
    srv.log.connect(lambda t: logs.append(str(t)))
    srv.start()
    return srv, logs


def wait_backend(srv, path="/", timeout=600) -> tuple[int, str]:
    """The DevServer answers 'starting...' pages until the framework listens; wait for a real page."""
    url = srv.url.rstrip("/") + path
    end = time.time() + timeout
    status, body = 0, ""
    while time.time() < end:
        try:
            status, body = exlib.http_get(url, 15)
        except Exception as e:  # noqa: BLE001
            status, body = 0, str(e)
        if status == 200 and "radide-starting" not in body and "is starting" not in body.lower():
            return status, body
        time.sleep(1.0)
    return status, body


class Browser:
    """urllib with cookies (Django CSRF / Flask flash messages)."""

    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, path):
        try:
            with self.op.open(self.base + path, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def post(self, path, data: dict, json_body=False, method="POST", referer=True):
        body = json.dumps(data).encode() if json_body else urllib.parse.urlencode(data).encode()
        headers = {"Content-Type": "application/json" if json_body else "application/x-www-form-urlencoded"}
        if referer:
            headers["Referer"] = self.base + path
        req = urllib.request.Request(self.base + path, data=body, method=method, headers=headers)
        try:
            with self.op.open(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")


def headers_step(src: Path, res):
    miss = header_check(src)
    if miss:
        res["notes"].append(f"files without the copyright header: {miss[:6]}")
    return not miss


# ============================================================================ games
def t_breakout(src: Path, res, opts):
    f = sync_copy(src)
    ok, note = scene_open_check(f)
    res.step("open", ok and headers_step(src, res), note)
    res.step("build", *compile_py(f))
    title, code, out = run_with_window(f, "pygame", {
        "RADGAME_FRAMES": "420", "RADGAME_FIXED_DT": "1", "RADGAME_KEYS": "space:10-12,left:30-60",
        "RADGAME_SAVE": str(f / "test_save.json")}, "Breakout")
    hits = re.findall(r"HIT Brick\d+ score=(\d+)", out)
    res.step("run", bool(title and "LAUNCH" in out and hits and code == 0),
             f"window={title!r} exit={code} launch={'LAUNCH' in out} bricks_hit={len(hits)} "
             f"score={hits[-1] if hits else 0}" + ("" if code == 0 else f" out={out[-300:]}"))
    publish_exe(f, res, opts, {"RADGAME_FRAMES": "240", "RADGAME_SAVE": str(f / "test_save.json")}, "Breakout")


def t_coins(src: Path, res, opts):
    f = sync_copy(src)
    res.step("open", headers_step(src, res) and (f / "main.py").exists(), "arcade project (code only, no designer)")
    res.step("build", *compile_py(f))
    title, code, out = run_with_window(f, "python-arcade", {
        "COIN_SEED": "7", "RADGAME_FRAMES": "240", "RADGAME_KEYS": "right:5-40,p:60-61,p:70-71"}, "Coin Collector")
    res.step("run", bool(title and "COIN score=1" in out and "PAUSE" in out and "radgame-test: 240 frames" in out),
             f"window={title!r} exit={code} coin={'COIN score=1' in out} pause={'PAUSE' in out}"
             + ("" if "radgame-test" in out else f" out={out[-300:]}"))
    (f / "highscore.txt").unlink(missing_ok=True)
    publish_exe(f, res, opts, {"RADGAME_FRAMES": "240"}, "Coin Collector")


KIVY_SCRIPT = '''
for i in range(8):
    right = [b for b in (scr.btnA, scr.btnB, scr.btnC, scr.btnD) if b.text == scr.current["capital"]][0]
    wrong = [b for b in (scr.btnA, scr.btnB, scr.btnC, scr.btnD) if b.text != scr.current["capital"]][0]
    (wrong if i == 1 else right).dispatch("on_release")
print("SCREEN", app.sm.current, flush=True)
'''


def t_quiz(src: Path, res, opts):
    f = sync_copy(src)
    ok, note = exlib.designer_check(f)
    res.step("open", ok and headers_step(src, res), note)
    res.step("build", *compile_py(f))
    title, code, out = run_with_window(f, "kivy", {"RADKIVY_AUTOSTOP": "10", "RADKIVY_EXEC": KIVY_SCRIPT,
                                                   "KIVY_NO_CONSOLELOG": "1"}, "")
    res.step("run", bool(title and "RESULT 7/8" in out and "SCREEN ResultScreen" in out),
             f"window={title!r} exit={code} answers={out.count('ANSWER')} result={'RESULT 7/8' in out}"
             + ("" if "RESULT" in out else f" out={out[-400:]}"))
    publish_exe(f, res, opts, {"RADKIVY_AUTOSTOP": "8"}, "")


def t_maze(src: Path, res, opts):
    f = sync_copy(src)
    ok, note = scene_open_check(f, ".scene3d")
    res.step("open", ok and headers_step(src, res), note)
    res.step("build", *compile_py(f))
    title, code, out = run_with_window(f, "python-ursina", {"RAD3D_FRAMES": "200", "RAD3D_KEYS": "d:5-200"},
                                       "Crystal Maze")
    m = re.search(r"rad3d-test: \d+ frames score=(\d+) player=\(([-\d.]+),", out)
    blocked = m and float(m.group(2)) < -3.0          # the wall at x=-2 stops the player
    res.step("run", bool(title and "CRYSTAL Crystal1" in out and m and int(m.group(1)) >= 1 and blocked),
             f"window={title!r} exit={code} crystal={'CRYSTAL Crystal1' in out} wall_blocks={bool(blocked)}"
             + ("" if m else f" out={out[-400:]}"))
    publish_exe(f, res, opts, {"RAD3D_FRAMES": "200"}, "Crystal Maze")


# ============================================================================ Python web
def _web_common(src: Path, lang: str, res):
    from radide.languages import get_plugin
    from radide.web_site.frameworks.python_web import framework_for
    f = sync_copy(src)
    fw = framework_for(lang)
    idx = fw.static_index(f, dict(json.loads((f / "project.radproj").read_text(encoding="utf-8")).get("web", {})))
    routes = [u.get("pattern") for u in idx.get("urls", [])]
    res.step("open", len(routes) >= 3 and headers_step(src, res), f"{len(routes)} routes in the framework index")
    return f, get_plugin(lang)


def _venv_compile(f: Path, res):
    from radide.web_site.frameworks.python_web import venv_python
    py = venv_python(f)
    if not py:
        return res.step("build", *compile_py(f))
    r = subprocess.run([py, "-m", "compileall", "-q", "-x", r"[\\/]\.venv[\\/]", "."], cwd=str(f),
                       capture_output=True, text=True)
    return res.step("build", r.returncode == 0, "compileall in the project's .venv" + (r.stdout[-300:] if r.returncode
                                                                                        else ""))


def t_flask(src: Path, res, opts):
    f, plugin = _web_common(src, "python-flask", res)
    srv, logs = dev_server(f, "python-flask")
    try:
        st, body = wait_backend(srv, "/")
        _venv_compile(f, res)
        b = Browser(srv.url)
        s1, b1 = b.post("/sign", {"name": "Test Visitor", "message": "Hello from the RAD IDE test", "rating": "4"})
        s2, b2 = b.post("/sign", {"name": "", "message": "x", "rating": "9"})
        s3, b3 = b.post("/api/entries", {"name": "Api", "message": "via JSON"}, json_body=True)
        s4, b4 = b.get("/api/entries")
        entries = json.loads(b4) if s4 == 200 else []
        ids = [e["id"] for e in entries if e["name"] == "Test Visitor"]
        s5, b5 = b.post(f"/delete/{ids[0]}", {}) if ids else (0, "")
        ok = (st == 200 and "Flask Guestbook" in body and s1 == 200 and "Hello from the RAD IDE test" in b1
              and "Please enter your name" in b2 and s3 == 201 and len(entries) >= 2 and s5 == 200
              and "was deleted" in b5)
        res.step("run", ok, f"GET / {st}, sign {s1}, validation {'ok' if 'Please enter' in b2 else 'missing'}, "
                            f"api POST {s3}, list {len(entries)}, delete {s5}"
                 + ("" if ok else f" log={' | '.join(logs[-6:])[-500:]}"))
    finally:
        srv.stop()
    publish_folder(f, res, expect=("app/__init__.py", "app/templates/index.html", "requirements.txt"),
                   forbid=(".venv", "instance"))


def t_django(src: Path, res, opts):
    f, plugin = _web_common(src, "python-django", res)
    srv, logs = dev_server(f, "python-django")
    try:
        st, body = wait_backend(srv, "/")
        _venv_compile(f, res)
        b = Browser(srv.url)
        s0, form = b.get("/books/new/")
        tok = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', form)
        data = {"title": "Test Driven Library", "author_name": "Ada Tester", "year": "2024", "genre": "science",
                "isbn": "978-0-00-000000-0", "csrfmiddlewaretoken": tok.group(1) if tok else ""}
        s1, b1 = b.post("/books/new/", data)
        m = re.search(r'/books/(\d+)/borrow/', b1)
        tok2 = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', b1)
        s2, b2 = (b.post(f"/books/{m.group(1)}/borrow/", {"borrower": "Omar", "csrfmiddlewaretoken": tok2.group(1)})
                  if m and tok2 else (0, ""))
        s3, b3 = b.get("/?q=Test+Driven")
        s4, b4 = b.get("/api/books/")
        books = json.loads(b4).get("books", []) if s4 == 200 else []
        lent = [x for x in books if x["title"] == "Test Driven Library" and not x["available"]]
        sa, ba = b.get("/admin/login/")
        ok = (st == 200 and "Django Library" in body and s1 == 200 and "Saved" in b1 and "lent to Omar" in b2
              and "Test Driven Library" in b3 and lent and sa == 200)
        res.step("run", ok, f"GET / {st}, add {s1} ({'saved' if 'Saved' in b1 else 'not saved'}), lend {s2}, "
                            f"search {'found' if 'Test Driven' in b3 else 'missing'}, api {len(books)} books, "
                            f"admin {sa}" + ("" if ok else f" log={' | '.join(logs[-6:])[-500:]}"))
    finally:
        srv.stop()
    publish_folder(f, res, expect=("manage.py", "core/models.py", "templates/base.html"),
                   forbid=(".venv", "db.sqlite3"))


def t_fastapi(src: Path, res, opts):
    f, plugin = _web_common(src, "python-fastapi", res)
    srv, logs = dev_server(f, "python-fastapi")
    try:
        st, body = wait_backend(srv, "/")
        _venv_compile(f, res)
        b = Browser(srv.url)
        s1, b1 = b.post("/api/tasks", {"title": "Write the README", "priority": "high"}, json_body=True)
        task = json.loads(b1) if s1 == 201 else {}
        s2, b2 = b.post(f"/api/tasks/{task.get('id', 0)}", {"done": True}, json_body=True, method="PATCH")
        s3, b3 = b.post("/api/tasks", {"title": "", "priority": "urgent"}, json_body=True)
        s4, b4 = b.get("/api/tasks?done=true")
        s5, b5 = b.get("/api/stats")
        s6, _ = b.get("/docs")
        s7, _ = b.get("/static/js/tasks.js")
        done = [t for t in (json.loads(b4) if s4 == 200 else []) if t["title"] == "Write the README"]
        ok = (st == 200 and "Tasks" in body and s1 == 201 and s2 == 200 and json.loads(b2).get("done") is True
              and s3 == 422 and done and s5 == 200 and s6 == 200 and s7 == 200)
        res.step("run", ok, f"GET / {st}, POST {s1}, PATCH {s2}, invalid {s3}, done-filter {len(done)}, stats {b5[:60]}, "
                            f"/docs {s6}, static {s7}" + ("" if ok else f" log={' | '.join(logs[-6:])[-500:]}"))
    finally:
        srv.stop()
    publish_folder(f, res, expect=("app/main.py", "app/static/js/tasks.js", "requirements.txt"),
                   forbid=(".venv", "tasks.db"))


# ============================================================================ static web / HTML5
def _node() -> str:
    return shutil.which("node") or ""


def t_static(src: Path, res, opts):
    f = sync_copy(src)
    pages = ["index.html", "about.html", "contact.html", "ar/index.html"]
    assets = ["css/site.css", "js/places.js", "js/contact.js", "js/site.js", "img/skyline.svg"]
    res.step("open", all((f / p).exists() for p in pages + assets) and headers_step(src, res),
             f"{len(pages)} pages, {len(assets)} assets")
    node = _node()
    bad = []
    for js in [a for a in assets if a.endswith(".js")]:
        if node and subprocess.run([node, "--check", str(f / js)], capture_output=True).returncode != 0:
            bad.append(js)
    res.step("build", not bad, "node --check " + ("ok" if node and not bad else (f"failed {bad}" if bad else "skipped")))
    srv, logs = dev_server(f, "static-web")
    try:
        got = {}
        for p in pages + assets:
            st, body = exlib.http_get(srv.url + p)
            got[p] = (st, body)
        rtl = 'dir="rtl"' in got["ar/index.html"][1] and "دليل المدينة" in got["ar/index.html"][1]
        okall = all(s == 200 for s, _ in got.values())
        form = 'id="contact"' in got["contact.html"][1] and "localStorage" in got["js/contact.js"][1]
        res.step("run", okall and rtl and form, f"{sum(s == 200 for s, _ in got.values())}/{len(got)} URLs 200, "
                                                 f"rtl={rtl}, form+localStorage={form}")
    finally:
        srv.stop()
    publish_folder(f, res, expect=tuple(pages + assets), forbid=("project.radproj",))


def t_html5(src: Path, res, opts):
    f = sync_copy(src)
    ok, note = scene_open_check(f)
    res.step("open", ok and headers_step(src, res), note)
    node = _node()
    chk = subprocess.run([node, "--check", str(f / "Space.js")], capture_output=True, text=True) if node else None
    res.step("build", bool(chk and chk.returncode == 0), "node --check Space.js" + ("" if node else " (no node)"))
    srv, logs = dev_server(f, "html5-game")
    try:
        urls = {p: exlib.http_get(srv.url + p)[0] for p in ("", "radgame.js", "scenes.js", "Space.js")}
    finally:
        srv.stop()
    r = subprocess.run([node, str(HERE / "html5_headless.js"), str(f), "Space", "900",
                        "space:5-900,left:100-160,right:300-420"], capture_output=True, text=True, timeout=120)
    m = re.search(r"html5-test: frames=(\d+) score=(\d+) lives=(\d+)", r.stdout)
    played = bool(m and int(m.group(1)) == 900 and int(m.group(2)) >= 10 and not re.search(r"error=\S", r.stdout))
    res.step("run", all(v == 200 for v in urls.values()) and played,
             f"HTTP {urls}; headless play: {m.group(0) if m else r.stdout[-300:] + r.stderr[-300:]}")
    publish_folder(f, res, expect=("index.html", "radgame.js", "scenes.js", "Space.js"))


# ============================================================================ Godot / Expo
def t_godot(src: Path, res, opts):
    from radide.games import godot_export
    f = sync_copy(src)
    godot_export.export_project(f)
    ok, note = scene_open_check(f)
    res.step("open", ok and (f / "project.godot").exists() and headers_step(src, res), note + ", .tscn exported")
    exe = godot_export.godot_exe()
    if not exe:
        res.step("build", "skipped", "no Godot 4 found by the IDE's locator")
        res.step("run", "skipped", "no Godot")
        return
    r = subprocess.run([exe, "--headless", "--path", str(f), "--check-only", "--script", "Room1.gd"],
                       capture_output=True, text=True, timeout=180)
    parse_err = "Parse Error" in (r.stdout + r.stderr) or "SCRIPT ERROR" in (r.stdout + r.stderr)
    res.step("build", not parse_err, f"godot --check-only Room1.gd (Godot: {Path(exe).name})"
             + (f" {(r.stdout + r.stderr)[-300:]}" if parse_err else ""))
    title, code, out = run_with_window(f, "godot", {"RADGAME_FRAMES": "200", "RADGAME_KEYS": "left:2-80,down:80-110"},
                                       "GemHunter", timeout=180, interpreter=exe)
    m = re.search(r"RADGAME_RESULT frames=\d+ score=(\d+)", out)
    res.step("run", bool(title and "GEM score=10" in out and m),
             f"window={title!r} exit={code} gem={'GEM score=10' in out} {m.group(0) if m else out[-300:]}")
    res.step("publish", "n/a", "Godot games are exported with Godot's own export templates (Project > Export)")


def t_expo(src: Path, res, opts):
    f = sync_copy(src)
    ok, note = exlib.designer_check(f)
    res.step("open", ok and headers_step(src, res), note)
    node = _node()
    test_js = (
        "import('file:///' + process.argv[1].replace(/\\\\/g, '/')).then((m) => {"
        "m.addItem('Milk'); m.addItem('Bread'); m.addItem('milk'); m.updateItem(1, {bought: true});"
        "console.log(JSON.stringify({rows: m.rows(true).length, summary: m.summary(), removed: m.removeBought(),"
        "qty: m.store.items[0].qty}));});")
    shutil.copy(f / "store.js", f / "store_test.mjs")
    r = subprocess.run([node, "-e", test_js, str(f / "store_test.mjs")], capture_output=True, text=True, timeout=60)
    (f / "store_test.mjs").unlink(missing_ok=True)
    try:
        st = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        st = {}
    logic = st == {"rows": 1, "summary": "2 items - 1 still to buy", "removed": 1, "qty": 2}
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    export_note = "npm not found"
    exported = None
    if npm:
        if not (f / "node_modules").is_dir():
            subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=str(f), capture_output=True, text=True,
                           timeout=1500, shell=os.name == "nt")
        if (f / "node_modules" / "expo").is_dir():
            e = subprocess.run(["npx", "expo", "export", "--platform", "web", "--output-dir", "dist"], cwd=str(f),
                               capture_output=True, text=True, timeout=900, shell=os.name == "nt",
                               env=dict(os.environ, CI="1", EXPO_NO_TELEMETRY="1"))
            exported = (f / "dist" / "index.html").exists()
            export_note = "expo export --platform web " + ("ok" if exported else f"failed: {(e.stdout + e.stderr)[-300:]}")
            if exported:                  # the bundle holds the app's own screens and store
                bundle = " ".join(x.read_text(encoding="utf-8", errors="replace") for x in (f / "dist").rglob("*.js"))
                exported = all(w in bundle for w in ("lstItems", "btnClearBought", "still to buy"))
                export_note += "" if exported else " (the bundle misses the app's code)"
            if exported:
                res["size"] = f"{exlib.mb(exlib.dir_size(f / 'dist'))} MB web bundle"
        else:
            export_note = "npm install did not provide expo (offline?)"
    res.step("build", exported is not False, export_note)
    res.step("run", logic, f"store.js in Node: {st or r.stderr[-300:]}"
             + ("; app UI: F5 in the IDE (expo start --web)" if logic else ""))
    res.step("publish", "ok" if exported else "n/a", "web bundle = the expo export above" if exported else
             "phone builds use EAS (not part of the test)")


EXAMPLES = {
    "PythonGames/BreakoutGame": {"lang": "pygame", "test": t_breakout},
    "PythonGames/CoinCollector": {"lang": "python-arcade", "test": t_coins},
    "PythonGames/CapitalsQuiz": {"lang": "kivy", "test": t_quiz},
    "PythonGames/CrystalMaze3D": {"lang": "python-ursina", "test": t_maze},
    "PythonWeb/FlaskGuestbook": {"lang": "python-flask", "test": t_flask},
    "PythonWeb/DjangoLibrary": {"lang": "python-django", "test": t_django},
    "PythonWeb/FastApiTasks": {"lang": "python-fastapi", "test": t_fastapi},
    "Web/CityGuideSite": {"lang": "static-web", "test": t_static},
    "Web/SpaceDodgerHtml5": {"lang": "html5-game", "test": t_html5},
    "Godot/GemHunter2D": {"lang": "godot", "test": t_godot},
    "Mobile/ShoppingListExpo": {"lang": "expo", "test": t_expo},
}
