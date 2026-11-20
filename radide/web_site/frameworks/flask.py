"""Flask projects (New Project > Web > Flask App) - an application factory.

Layout: ``app/__init__.py`` (``create_app()``), ``app/routes.py`` (a Blueprint ``main``),
``app/templates/`` (Jinja), ``app/static/``, ``config.py``, ``requirements.txt`` and the project's own
``.venv``. The dev server is ``flask --app app run --port <port>`` with ``--debug`` (Werkzeug reloader and
debugger; under the IDE debugger ``--no-reload --no-debugger``). ``web.app`` = the ``--app`` value.
"""
from __future__ import annotations

import re
from pathlib import Path

from .python_web import (Command, Framework, Log, PyWebPlugin, _read, create_venv, line_of,
                         register_framework_template, walk_files, write_files)

FLASK_REQ = ["Flask>=3.0,<4", "python-dotenv>=1.0"]


def app_target(folder: Path, cfg: dict | None = None) -> str:
    """The --app value: web.app, else a package with create_app, else app.py / wsgi.py."""
    cfg = cfg or {}
    if cfg.get("app"):
        return str(cfg["app"])
    folder = Path(folder)
    if (folder / "app" / "__init__.py").is_file():
        return "app"
    for n in ("app.py", "wsgi.py", "main.py", "application.py"):
        if (folder / n).is_file():
            return n[:-3]
    return "app"


FILES = {
    "app/__init__.py": '''"""{name} - Flask application factory."""
from flask import Flask


def create_app(config_object="config.DevelopmentConfig"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
''',
    "app/routes.py": '''from datetime import datetime

from flask import Blueprint, current_app, render_template, request

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    items = ["routes", "templates", "static files", "blueprints"]
    return render_template("index.html", items=items, now=datetime.now(),
                           site_name=current_app.config["SITE_NAME"])


@bp.route("/hello")
def hello():
    name = request.args.get("name", "World")
    return render_template("hello.html", name=name, site_name=current_app.config["SITE_NAME"])
''',
    "app/templates/base.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}{{ site_name }}{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/site.css') }}">
</head>
<body>
<header>
    <h1><a href="{{ url_for('main.index') }}">{{ site_name }}</a></h1>
    <nav>
        <a href="{{ url_for('main.index') }}">Home</a>
        <a href="{{ url_for('main.hello', name='Flask') }}">Hello</a>
    </nav>
</header>
<main>
{% block content %}{% endblock %}
</main>
<footer>Made with Flask and RAD IDE</footer>
</body>
</html>
''',
    "app/templates/index.html": '''{% extends "base.html" %}

{% block content %}
<h2>Welcome to {{ site_name }}</h2>
<p>This page comes from <code>app/routes.py</code> &rarr; <code>index()</code>.
   Edit <code>app/templates/index.html</code> and save: the preview reloads by itself.</p>
<ul>
{% for item in items %}
    <li>{{ loop.index }}. {{ item|title }}</li>
{% endfor %}
</ul>
<p>Server time: {{ now.strftime("%Y-%m-%d %H:%M:%S") }}</p>
{% endblock %}
''',
    "app/templates/hello.html": '''{% extends "base.html" %}

{% block content %}
<h2>Hello, {{ name }}!</h2>
<form action="{{ url_for('main.hello') }}">
    <input name="name" value="{{ name }}"> <button>Say hello</button>
</form>
{% endblock %}
''',
    "app/static/css/site.css": '''* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; color: #222; background: #f5f5f5; }
header { background: #222; color: #fff; padding: 14px 32px; display: flex; align-items: center; gap: 32px; }
header h1 { margin: 0; font-size: 22px; } header a { color: #fff; text-decoration: none; }
nav a { color: #9fd3ff; margin-right: 16px; }
main { max-width: 900px; margin: 24px auto; background: #fff; padding: 24px 32px; border-radius: 8px;
       box-shadow: 0 1px 3px rgba(0,0,0,.12); }
footer { text-align: center; color: #888; font-size: 12px; padding: 16px; }
''',
    "config.py": '''import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SITE_NAME = "{name}"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
''',
    ".flaskenv": "FLASK_APP=app\n",
    ".gitignore": ".venv/\n__pycache__/\ninstance/\n*.sqlite3\n",
}


class Flask(Framework):
    id = "flask"
    title = "Flask"
    plugin_id = "python-flask"
    package = "flask"
    template_lang = "jinja-html"
    ready_marker = r"Debugger PIN:"          # printed by every (re)started Werkzeug child
    log_filter = r'^\S+ - - \[[^\]]+\] "(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) '
    url_label = "Endpoints"

    def requirements(self) -> list[str]:
        return list(FLASK_REQ)

    def create(self, folder: Path, name: str, log: Log, python: str = "") -> dict:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        write_files(folder, {"requirements.txt": "\n".join(self.requirements()) + "\n"})
        write_files(folder, {k: v.replace("{name}", name) for k, v in FILES.items()})
        try:
            create_venv(folder, log, python)
        except Exception as e:  # noqa: BLE001 - the first run retries
            log(f"*** {e}\nThe first run (F5) creates the .venv and installs Flask.")
        log(f"Flask project '{name}' is ready. F5 = debug, Ctrl+F5 = run; panel: View > Flask.")
        return {"start": "/", "framework": "flask", "app": "app"}

    def server_args(self, folder: Path, cfg: dict, debug: bool) -> list[str]:
        args = ["-m", "flask", "--app", app_target(folder, cfg), "--debug", "run", "--host", "127.0.0.1",
                "--port", "{port}"]
        if debug:
            args += ["--no-reload", "--no-debugger"]
        elif self.reload(cfg) != "framework":
            args += ["--no-reload"]
        return args

    def server_env(self, folder: Path, cfg: dict) -> dict:
        return {"FLASK_APP": app_target(folder, cfg), "NO_COLOR": "1", "FLASK_SKIP_DOTENV": "0"}

    def runtime_script(self, folder: Path, cfg: dict) -> str:
        return RUNTIME_SCRIPT.replace("@@APP@@", app_target(folder, cfg))

    def static_index(self, folder: Path, cfg: dict) -> dict:
        urls = []
        for p in walk_files(folder, (".py",), 2000):
            text = _read(p)
            if ".route(" not in text and not re.search(r"\.(get|post|put|patch|delete)\(", text):
                continue
            bps = {m.group(1): m.group(2) for m in
                   re.finditer(r"^(\w+)\s*=\s*Blueprint\(\s*['\"]([\w.-]+)['\"]", text, re.M)}
            for m in re.finditer(r"@(\w+)\.(route|get|post|put|patch|delete)\(\s*['\"]([^'\"]*)['\"]([^)]*)\)"
                                 r"(?:\s*@[^\n]*)*\s*(?:async\s+)?def\s+(\w+)", text):
                var, verb, rule, rest, func = m.groups()
                ep = re.search(r"endpoint\s*=\s*['\"]([\w.]+)['\"]", rest)
                name = ep.group(1) if ep else func
                if var in bps:
                    name = f"{bps[var]}.{name}"
                methods = re.findall(r"['\"](GET|POST|PUT|PATCH|DELETE)['\"]", rest) or \
                    ([verb.upper()] if verb != "route" else ["GET"])
                urls.append({"name": name, "pattern": rule, "args": re.findall(r"<(?:\w+:)?(\w+)>", rule),
                             "methods": methods, "file": str(p), "line": line_of(text, m.start(5))})
        urls.append({"name": "static", "pattern": "/static/<path:filename>", "args": ["filename"]})
        settings = []
        cfgp = Path(folder) / "config.py"
        if cfgp.is_file():
            text = _read(cfgp)
            for m in re.finditer(r"^\s+([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", text, re.M):
                if m.group(1) not in {s["name"] for s in settings}:
                    settings.append({"name": m.group(1), "value": m.group(2).strip()[:80], "file": str(cfgp),
                                     "line": line_of(text, m.start(1))})
        for n in ("DEBUG", "SECRET_KEY", "TESTING", "SERVER_NAME", "SESSION_COOKIE_NAME", "MAX_CONTENT_LENGTH",
                  "TEMPLATES_AUTO_RELOAD", "JSON_SORT_KEYS"):
            if n not in {s["name"] for s in settings}:
                settings.append({"name": n, "value": "(Flask default)"})
        return {"urls": urls, "routes": urls, "settings": settings}

    def commands(self, folder: Path, cfg: dict) -> list[Command]:
        app = app_target(folder, cfg)
        return [
            Command("runserver", "Run Server", [], "Start the site (Ctrl+F5) - Preview, Requests, live reload"),
            Command("routes", "flask routes", ["-m", "flask", "--app", app, "routes"], "List the URL rules"),
            Command("shell", "flask shell", ["-m", "flask", "--app", app, "shell"], "Python shell with the app",
                    terminal=True),
            Command("pip", "pip install...", ["-m", "pip", "install", "{name}"], "Install a package into the .venv",
                    ask=["name"]),
            Command("freeze", "pip freeze", ["-m", "pip", "freeze"], "Installed packages"),
            Command("flask", "Run flask command...", ["-m", "flask", "--app", app, "{name}"],
                    "Run a command of the app's CLI (e.g. 'init-db')", ask=["name"]),
            Command("test", "Run tests", ["-m", "unittest", "discover", "-s", "tests", "-v"],
                    "python -m unittest discover -s tests"),
        ]


RUNTIME_SCRIPT = r'''
import inspect, json, os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("FLASK_APP", "@@APP@@")
out = {"framework": "flask", "urls": [], "templates": [], "settings": [], "static": [], "routes": []}
from flask.cli import ScriptInfo
app = ScriptInfo(app_import_path="@@APP@@").load_app()
with app.app_context():
    for rule in app.url_map.iter_rules():
        f = l = None
        view = app.view_functions.get(rule.endpoint)
        try:
            view = inspect.unwrap(view)
            f, l = inspect.getsourcefile(view), inspect.getsourcelines(view)[1]
        except Exception:
            pass
        item = {"name": rule.endpoint, "pattern": rule.rule, "args": sorted(rule.arguments),
                "methods": sorted(m for m in (rule.methods or []) if m not in ("HEAD", "OPTIONS")),
                "file": f, "line": l}
        out["urls"].append(item)
    out["routes"] = out["urls"]
    try:
        loader = app.jinja_env.loader
        for name in app.jinja_env.list_templates():
            full = ""
            try:
                src = loader.get_source(app.jinja_env, name)
                full = src[1] or ""
            except Exception:
                pass
            if "site-packages" not in full:
                out["templates"].append({"name": name, "file": full})
    except Exception as e:
        out["templates_error"] = str(e)
    for k, v in app.config.items():
        out["settings"].append({"name": k, "value": repr(v)[:80]})
    if app.static_folder and os.path.isdir(app.static_folder):
        for root, _ds, files in os.walk(app.static_folder):
            for fn in files:
                full = os.path.join(root, fn)
                out["static"].append({"name": os.path.relpath(full, app.static_folder).replace(os.sep, "/"),
                                      "file": full})
print("@@RADIDE-PYWEB@@" + json.dumps(out))
'''


FRAMEWORK = Flask()


class FlaskPlugin(PyWebPlugin):
    id = "python-flask"
    display_name = "Flask (Python)"
    framework = FRAMEWORK
    default_template = "flask-app"


register_framework_template(FRAMEWORK, "flask-app", "Flask App",
                            "A Flask application factory (create_app + a Blueprint) in its own .venv: Jinja "
                            "templates, static files, config classes. F5 debugs with breakpoints in routes; the "
                            "Flask panel lists the routes.", 10, "SP_DirIcon")

__all__ = ["Flask", "FlaskPlugin", "FRAMEWORK", "app_target"]
