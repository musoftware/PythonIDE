"""FastAPI projects (New Project > Web > FastAPI App).

Layout: ``app/main.py`` (``app = FastAPI()``: a JSON API, a Jinja2 home page, ``/static``),
``app/templates/``, ``app/static/``, ``requirements.txt`` and the project's own ``.venv``. The dev server is
``uvicorn app.main:app --port <port> --reload`` (no ``--reload`` under the IDE debugger). ``web.app`` = the
``module:attribute`` of the application. The panel lists the routes and opens ``/docs`` / ``/redoc``.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .python_web import (Command, Framework, Log, PyWebPlugin, _read, create_venv, line_of,
                         register_framework_template, walk_files, write_files)

FASTAPI_REQ = ["fastapi>=0.115", "uvicorn>=0.30", "jinja2>=3.1", "python-multipart>=0.0.9"]


def app_target(folder: Path, cfg: dict | None = None) -> str:
    cfg = cfg or {}
    if cfg.get("app"):
        return str(cfg["app"])
    folder = Path(folder)
    for rel, target in (("app/main.py", "app.main:app"), ("main.py", "main:app"), ("app.py", "app:app"),
                        ("src/main.py", "src.main:app")):
        if (folder / rel).is_file():
            return target
    return "app.main:app"


FILES = {
    "app/__init__.py": "",
    "app/main.py": '''"""{name} - FastAPI application."""
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent

app = FastAPI(title="{name}")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


class Message(BaseModel):
    text: str


MESSAGES: list[Message] = [Message(text="Hello from FastAPI")]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"messages": MESSAGES, "now": datetime.now()})


@app.get("/api/messages", response_model=list[Message])
def list_messages():
    return MESSAGES


@app.post("/api/messages", response_model=Message, status_code=201)
def add_message(message: Message):
    MESSAGES.append(message)
    return message


@app.get("/api/messages/{index}", response_model=Message)
def get_message(index: int):
    if not 0 <= index < len(MESSAGES):
        raise HTTPException(status_code=404, detail="Message not found")
    return MESSAGES[index]
''',
    "app/templates/index.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>FastAPI</title>
    <link rel="stylesheet" href="{{ url_for('static', path='css/site.css') }}">
</head>
<body>
<header><h1>FastAPI</h1><nav><a href="/docs">API docs (/docs)</a> <a href="/redoc">ReDoc</a></nav></header>
<main>
    <p>Rendered by <code>app/main.py</code> &rarr; <code>home()</code> at {{ now.strftime("%H:%M:%S") }}.</p>
    <ul id="list">
    {% for m in messages %}
        <li>{{ m.text }}</li>
    {% endfor %}
    </ul>
    <form id="add"><input name="text" placeholder="New message" required> <button>Add</button></form>
</main>
<script>
document.getElementById('add').addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = e.target.text.value;
    const r = await fetch('/api/messages', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                            body: JSON.stringify({text})});
    if (r.ok) { const li = document.createElement('li'); li.textContent = text;
                document.getElementById('list').appendChild(li); e.target.reset(); }
});
</script>
</body>
</html>
''',
    "app/static/css/site.css": '''* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; color: #222; background: #f3f7f7; }
header { background: #009688; color: #fff; padding: 14px 32px; display: flex; align-items: center; gap: 32px; }
header h1 { margin: 0; font-size: 22px; } nav a { color: #e0fffb; margin-right: 16px; }
main { max-width: 900px; margin: 24px auto; background: #fff; padding: 24px 32px; border-radius: 8px;
       box-shadow: 0 1px 3px rgba(0,0,0,.12); }
''',
    ".gitignore": ".venv/\n__pycache__/\n*.db\n",
}


class FastAPI(Framework):
    id = "fastapi"
    title = "FastAPI"
    plugin_id = "python-fastapi"
    package = "fastapi"
    template_lang = "jinja-html"
    ready_marker = r"Application startup complete"
    log_filter = r'^\s*INFO:\s+[\d.:]+ - "(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) '
    url_label = "Routes"
    # uvicorn --reload stops its worker with CTRL_C_EVENT on Windows, which needs a console the IDE's
    # windowless server does not have: the IDE restarts uvicorn itself (web.reload = "framework" to try it)
    reload_mode = "ide" if os.name == "nt" else "framework"

    def requirements(self) -> list[str]:
        return list(FASTAPI_REQ)

    def create(self, folder: Path, name: str, log: Log, python: str = "") -> dict:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        write_files(folder, {"requirements.txt": "\n".join(self.requirements()) + "\n"})
        write_files(folder, {k: v.replace("{name}", name) for k, v in FILES.items()})
        try:
            create_venv(folder, log, python)
        except Exception as e:  # noqa: BLE001 - the first run retries
            log(f"*** {e}\nThe first run (F5) creates the .venv and installs FastAPI.")
        log(f"FastAPI project '{name}' is ready. F5 = debug, Ctrl+F5 = run; /docs = the API docs.")
        return {"start": "/", "framework": "fastapi", "app": "app.main:app"}

    def server_args(self, folder: Path, cfg: dict, debug: bool) -> list[str]:
        args = ["-m", "uvicorn", app_target(folder, cfg), "--host", "127.0.0.1", "--port", "{port}",
                "--no-use-colors", "--no-access-log"]
        if not debug and self.reload(cfg) == "framework":
            args += ["--reload"]
        return args

    def server_env(self, folder: Path, cfg: dict) -> dict:
        return {"NO_COLOR": "1"}

    def runtime_script(self, folder: Path, cfg: dict) -> str:
        return RUNTIME_SCRIPT.replace("@@APP@@", app_target(folder, cfg))

    def static_index(self, folder: Path, cfg: dict) -> dict:
        urls = []
        for p in walk_files(folder, (".py",), 2000):
            text = _read(p)
            if not re.search(r"@\w+\.(get|post|put|patch|delete|api_route|websocket)\(", text):
                continue
            prefixes = {m.group(1): m.group(2) for m in
                        re.finditer(r"^(\w+)\s*=\s*APIRouter\([^)]*?prefix\s*=\s*['\"]([^'\"]*)['\"]", text, re.M)}
            for m in re.finditer(r"@(\w+)\.(get|post|put|patch|delete|api_route|websocket)\(\s*['\"]([^'\"]*)['\"]"
                                 r"([^)]*)\)(?:\s*@[^\n]*)*\s*(?:async\s+)?def\s+(\w+)", text):
                var, verb, path, rest, func = m.groups()
                nm = re.search(r"\bname\s*=\s*['\"]([\w.-]+)['\"]", rest)
                full = prefixes.get(var, "") + path
                urls.append({"name": nm.group(1) if nm else func, "pattern": full,
                             "args": re.findall(r"\{(\w+)(?::\w+)?\}", full),
                             "methods": [verb.upper()] if verb not in ("api_route",) else ["GET"],
                             "file": str(p), "line": line_of(text, m.start(5))})
        urls.append({"name": "static", "pattern": "/static", "args": ["path"]})
        return {"urls": urls, "routes": urls}

    def commands(self, folder: Path, cfg: dict) -> list[Command]:
        return [
            Command("runserver", "Run Server", [], "Start the site (Ctrl+F5) - Preview, Requests, live reload"),
            Command("docs", "Open /docs", [], "Swagger UI of the API in the Preview"),
            Command("redoc", "Open /redoc", [], "ReDoc of the API in the Preview"),
            Command("openapi", "Open /openapi.json", [], "The OpenAPI schema"),
            Command("pip", "pip install...", ["-m", "pip", "install", "{name}"], "Install a package into the .venv",
                    ask=["name"]),
            Command("freeze", "pip freeze", ["-m", "pip", "freeze"], "Installed packages"),
            Command("test", "Run tests", ["-m", "unittest", "discover", "-s", "tests", "-v"],
                    "python -m unittest discover -s tests (FastAPI TestClient needs httpx)"),
        ]


RUNTIME_SCRIPT = r'''
import importlib, inspect, json, os, sys
sys.path.insert(0, os.getcwd())
out = {"framework": "fastapi", "urls": [], "routes": [], "templates": [], "static": []}
mod, _, attr = "@@APP@@".partition(":")
app = getattr(importlib.import_module(mod), attr or "app")
def walk(routes, prefix=""):
    for r in routes:
        path = prefix + getattr(r, "path", "")
        sub = getattr(r, "routes", None)
        ep = getattr(r, "endpoint", None)
        if sub and ep is None and not hasattr(r, "methods"):
            app_ = getattr(r, "app", None)
            if getattr(r, "name", "") == "static" or type(app_).__name__ == "StaticFiles":
                out["urls"].append({"name": r.name, "pattern": path, "args": ["path"], "methods": ["GET"]})
                continue
            walk(sub, path)
            continue
        f = l = None
        try:
            fn = inspect.unwrap(ep)
            f, l = inspect.getsourcefile(fn), inspect.getsourcelines(fn)[1]
        except Exception:
            pass
        methods = sorted(m for m in (getattr(r, "methods", None) or []) if m not in ("HEAD", "OPTIONS"))
        import re as _re
        out["urls"].append({"name": getattr(r, "name", ""), "pattern": path, "methods": methods,
                            "args": _re.findall(r"\{(\w+)(?::\w+)?\}", path), "file": f, "line": l})
walk(app.routes)
out["routes"] = out["urls"]
print("@@RADIDE-PYWEB@@" + json.dumps(out))
'''


FRAMEWORK = FastAPI()


class FastAPIPlugin(PyWebPlugin):
    id = "python-fastapi"
    display_name = "FastAPI (Python)"
    framework = FRAMEWORK
    default_template = "fastapi-app"


register_framework_template(FRAMEWORK, "fastapi-app", "FastAPI App",
                            "A FastAPI application with uvicorn in its own .venv: a JSON API with Pydantic models, "
                            "a Jinja2 page, static files; /docs in the Preview. F5 debugs with breakpoints in "
                            "routes.", 10, "SP_DriveNetIcon")

__all__ = ["FastAPI", "FastAPIPlugin", "FRAMEWORK", "app_target"]
