"""Django projects (New Project > Web > Django App).

The project folder holds ``manage.py``, the settings package ``config/`` (``django-admin startproject config
.``), one app (``core``, ``manage.py startapp core``), project-level ``templates/`` and ``static/``, a SQLite
database and its own ``.venv``. The dev server is ``manage.py runserver 127.0.0.1:<port>`` (with Django's
auto-reloader; ``--noreload`` under the debugger). The panel runs makemigrations / migrate /
createsuperuser / shell / startapp / check / collectstatic / test.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

from .python_web import (Command, Framework, Log, PyWebPlugin, _read, create_venv, line_of, new_secret,
                         register_framework_template, run_logged, venv_python, walk_files, write_files)

DJANGO_REQ = "Django>=5.1,<6"


def settings_module(folder: Path, cfg: dict | None = None) -> str:
    """DJANGO_SETTINGS_MODULE of a project (web.settings, manage.py, or the folder with settings.py)."""
    cfg = cfg or {}
    if cfg.get("settings"):
        return str(cfg["settings"])
    text = _read(Path(folder) / "manage.py")
    m = re.search(r"DJANGO_SETTINGS_MODULE['\"]\s*,\s*['\"]([\w.]+)['\"]", text)
    if m:
        return m.group(1)
    for p in walk_files(folder, ("settings.py",), 200):
        rel = p.relative_to(folder).with_suffix("")
        return ".".join(rel.parts)
    return "config.settings"


def settings_file(folder: Path, cfg: dict | None = None) -> Path | None:
    mod = settings_module(folder, cfg)
    p = Path(folder).joinpath(*mod.split(".")).with_suffix(".py")
    if p.is_file():
        return p
    pkg = Path(folder).joinpath(*mod.split("."))
    return pkg / "__init__.py" if (pkg / "__init__.py").is_file() else None


BASE_HTML = """{% load static %}<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}{{ site_name }}{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/site.css' %}">
</head>
<body>
<header>
    <h1><a href="{% url 'core:home' %}">{{ site_name }}</a></h1>
    <nav>
        <a href="{% url 'core:home' %}">Home</a>
        <a href="{% url 'core:about' %}">About</a>
        <a href="{% url 'admin:index' %}">Admin</a>
    </nav>
</header>
<main>
{% block content %}{% endblock %}
</main>
<footer>Made with Django {{ django_version }} and RAD IDE</footer>
</body>
</html>
"""

HOME_HTML = """{% extends 'base.html' %}

{% block content %}
<h2>Welcome to {{ site_name }}</h2>
<p>This page is rendered by <code>core/views.py</code> &rarr; <code>home()</code>.
   Edit <code>templates/core/home.html</code> and save: the preview reloads by itself.</p>
<ul>
{% for item in items %}
    <li>{{ forloop.counter }}. {{ item|title }}</li>
{% empty %}
    <li>No items.</li>
{% endfor %}
</ul>
<p>Server time: {{ now|date:"Y-m-d H:i:s" }}</p>
{% endblock %}
"""

ABOUT_HTML = """{% extends 'base.html' %}

{% block title %}About - {{ block.super }}{% endblock %}

{% block content %}
<h2>About</h2>
<p>Use the <b>Django</b> panel (View &gt; Django) to run <code>makemigrations</code>, <code>migrate</code>,
   <code>createsuperuser</code> and the other <code>manage.py</code> commands.</p>
{% endblock %}
"""

SITE_CSS = """* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; color: #222; background: #f4f6f5; }
header { background: #0c4b33; color: #fff; padding: 14px 32px; display: flex; align-items: center; gap: 32px; }
header h1 { margin: 0; font-size: 22px; } header a { color: #fff; text-decoration: none; }
nav a { color: #c8f1dd; margin-right: 16px; }
main { max-width: 900px; margin: 24px auto; background: #fff; padding: 24px 32px; border-radius: 8px;
       box-shadow: 0 1px 3px rgba(0,0,0,.12); }
footer { text-align: center; color: #888; font-size: 12px; padding: 16px; }
"""

CORE_VIEWS = '''from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
import django


def home(request):
    items = ["models", "views", "templates", "admin"]
    return render(request, "core/home.html", {
        "site_name": settings.SITE_NAME,
        "items": items,
        "now": timezone.now(),
        "django_version": django.get_version(),
    })


def about(request):
    return render(request, "core/about.html", {"site_name": settings.SITE_NAME,
                                               "django_version": django.get_version()})
'''

CORE_URLS = '''from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
]
'''

PROJECT_URLS = '''"""URL configuration of {name}."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
'''

# used when Django cannot be installed now (offline): the same files startproject / startapp make
FALLBACK_SETTINGS = '''"""Django settings for {name}."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "{secret}"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {{
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        }},
    }},
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {{
    "default": {{
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }}
}}

AUTH_PASSWORD_VALIDATORS = [
    {{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
'''

FALLBACK_MANAGE = '''#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''

FALLBACK_WSGI = '''"""WSGI config."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
'''

FALLBACK_ASGI = FALLBACK_WSGI.replace("WSGI", "ASGI").replace("wsgi", "asgi")

FALLBACK_APP = {
    "__init__.py": "",
    "admin.py": "from django.contrib import admin\n\n# Register your models here.\n",
    "apps.py": 'from django.apps import AppConfig\n\n\nclass {Cls}Config(AppConfig):\n'
               '    default_auto_field = "django.db.models.BigAutoField"\n    name = "{app}"\n',
    "models.py": "from django.db import models\n\n# Create your models here.\n",
    "tests.py": "from django.test import TestCase\n\n# Create your tests here.\n",
    "views.py": "from django.shortcuts import render\n\n# Create your views here.\n",
    "migrations/__init__.py": "",
}


def add_installed_app(text: str, app: str) -> str:
    """settings.py text with *app* appended to INSTALLED_APPS (unchanged when it is there)."""
    if re.search(rf"""['"]{re.escape(app)}(\.apps\.\w+)?['"]""", text):
        return text
    return re.sub(r"(INSTALLED_APPS\s*=\s*\[[^\]]*?)(\n\])", rf'\1\n    "{app}",\2', text, count=1)


def patch_settings(text: str, apps: list[str], name: str) -> str:
    """Add the apps, the project templates/ folder, static/ and a few RAD IDE defaults to settings.py."""
    for app in apps:
        text = add_installed_app(text, app)
    text = re.sub(r"(['\"]DIRS['\"]\s*:\s*)\[\s*\]", r'\1[BASE_DIR / "templates"]', text, count=1)
    if "ALLOWED_HOSTS = []" in text:
        text = text.replace("ALLOWED_HOSTS = []", 'ALLOWED_HOSTS = ["127.0.0.1", "localhost"]')
    if "STATICFILES_DIRS" not in text:
        text = re.sub(r"(STATIC_URL\s*=\s*['\"][^'\"]*['\"]\s*\n)",
                      r'\1STATICFILES_DIRS = [BASE_DIR / "static"]\nSTATIC_ROOT = BASE_DIR / "staticfiles"\n',
                      text, count=1)
    if "SITE_NAME" not in text:
        text += f'\n# shown in the page header (templates/base.html)\nSITE_NAME = "{name}"\n'
    return text


class Django(Framework):
    id = "django"
    title = "Django"
    plugin_id = "python-django"
    package = "django"
    template_lang = "django-html"
    ready_marker = r"Starting development server at http"
    log_filter = r'^\[[^\]]+\] "(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) '
    default_app = "core"

    def requirements(self) -> list[str]:
        return [DJANGO_REQ]

    # ------------------------------------------------------------ new project
    def create(self, folder: Path, name: str, log: Log, python: str = "", app: str = "core") -> dict:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        write_files(folder, {"requirements.txt": "\n".join(self.requirements()) + "\n",
                             ".gitignore": ".venv/\n__pycache__/\ndb.sqlite3\nstaticfiles/\nmedia/\n"})
        py = ""
        try:
            py = create_venv(folder, log, python)
        except Exception as e:  # noqa: BLE001 - offline: write the same files ourselves
            log(f"*** {e}")
        generated = False
        if py and not (folder / "manage.py").exists():
            if run_logged([py, "-m", "django", "startproject", "config", "."], folder, log) == 0:
                generated = True
        if py and (folder / "manage.py").exists() and not (folder / app).exists():
            if run_logged([py, "manage.py", "startapp", app], folder, log) != 0:
                generated = False
        if not generated:
            log("Django is not installed in the project yet - writing the startproject / startapp files "
                "(the first run installs Django).")
            write_files(folder, {
                "manage.py": FALLBACK_MANAGE, "config/__init__.py": "",
                "config/settings.py": FALLBACK_SETTINGS.format(name=name, secret=new_secret()),
                "config/wsgi.py": FALLBACK_WSGI, "config/asgi.py": FALLBACK_ASGI,
            })
            write_files(folder, {f"{app}/{k}": v.format(Cls=app.capitalize(), app=app)
                                 for k, v in FALLBACK_APP.items()})
        sp = folder / "config" / "settings.py"
        sp.write_text(patch_settings(sp.read_text(encoding="utf-8"), [app], name), encoding="utf-8", newline="\n")
        write_files(folder, {"config/urls.py": PROJECT_URLS.format(name=name)}, overwrite=True)
        write_files(folder, {f"{app}/views.py": CORE_VIEWS}, overwrite=True)
        write_files(folder, {
            f"{app}/urls.py": CORE_URLS,
            "templates/base.html": BASE_HTML,
            f"templates/{app}/home.html": HOME_HTML,
            f"templates/{app}/about.html": ABOUT_HTML,
            "static/css/site.css": SITE_CSS,
        })
        if py:
            run_logged([py, "manage.py", "migrate", "--noinput"], folder, log)
        log(f"Django project '{name}' is ready. F5 = debug, Ctrl+F5 = run; panel: View > Django.")
        return {"start": "/", "framework": "django", "settings": "config.settings"}

    # ------------------------------------------------------------ dev server
    def server_args(self, folder: Path, cfg: dict, debug: bool) -> list[str]:
        args = ["manage.py", "runserver", "127.0.0.1:{port}"]
        if debug or self.reload(cfg) != "framework":
            args.append("--noreload")
        return args

    def server_env(self, folder: Path, cfg: dict) -> dict:
        env = {"DJANGO_SETTINGS_MODULE": settings_module(folder, cfg), "DJANGO_COLORS": "nocolor"}
        if cfg.get("fresh_templates", True):
            # django_boot/sitecustomize.py: no cached template loader with DEBUG = True (saved templates show
            # at once in the Preview, also under the debugger where Django's auto-reloader is off)
            boot = str(Path(__file__).resolve().parent / "django_boot")
            env["PYTHONPATH"] = os.pathsep.join(x for x in (boot, os.environ.get("PYTHONPATH", "")) if x)
            env["RADIDE_DJANGO_FRESH_TEMPLATES"] = "1"
        return env

    def prepare(self, folder: Path, cfg: dict, py: str) -> list[list[str]]:
        sf = settings_file(folder, cfg)
        if sf is not None and "sqlite3" in _read(sf) and not (Path(folder) / "db.sqlite3").exists():
            return [[py, "manage.py", "migrate", "--noinput"]]
        return []

    # ------------------------------------------------------------ introspection
    def runtime_script(self, folder: Path, cfg: dict) -> str:
        return RUNTIME_SCRIPT.replace("@@SETTINGS@@", settings_module(folder, cfg))

    def static_index(self, folder: Path, cfg: dict) -> dict:
        folder = Path(folder)
        urls = []
        for p in walk_files(folder, ("urls.py",), 500):
            text = _read(p)
            m = re.search(r"^app_name\s*=\s*['\"]([\w-]+)['\"]", text, re.M)
            ns = m.group(1) if m else ""
            for pm in re.finditer(r"\b(?:path|re_path|url)\(\s*r?(['\"])(.*?)\1(.*?)\bname\s*=\s*['\"]([\w.-]+)['\"]",
                                  text, re.S):
                pattern, name = pm.group(2), pm.group(4)
                args = re.findall(r"<(?:\w+:)?(\w+)>", pattern) or re.findall(r"\(\?P<(\w+)>", pattern)
                urls.append({"name": f"{ns}:{name}" if ns else name, "pattern": pattern, "args": args,
                             "file": str(p), "line": line_of(text, pm.start(4))})
        models = {}
        for p in walk_files(folder, ("models.py",), 500):
            models.update(parse_models(p))
        settings = []
        sf = settings_file(folder, cfg)
        if sf is not None:
            text = _read(sf)
            for m in re.finditer(r"^([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", text, re.M):
                settings.append({"name": m.group(1), "value": m.group(2).strip()[:80], "file": str(sf),
                                 "line": line_of(text, m.start())})
            for n in ("DEBUG", "SECRET_KEY", "INSTALLED_APPS", "DATABASES", "STATIC_URL", "MEDIA_URL", "MEDIA_ROOT",
                      "LOGIN_URL", "LOGIN_REDIRECT_URL", "LOGOUT_REDIRECT_URL", "TIME_ZONE", "LANGUAGE_CODE",
                      "DEFAULT_FROM_EMAIL", "EMAIL_BACKEND", "AUTH_USER_MODEL", "CACHES"):
                if n not in {s["name"] for s in settings}:
                    settings.append({"name": n, "value": "(Django default)"})
        return {"urls": urls, "models": models, "settings": settings}

    # ------------------------------------------------------------ panel
    def commands(self, folder: Path, cfg: dict) -> list[Command]:
        return [
            Command("runserver", "Run Server", [], "Start the site (Ctrl+F5) - Preview, Requests, live reload"),
            Command("makemigrations", "makemigrations", ["manage.py", "makemigrations"],
                    "Create migrations from the changes of your models"),
            Command("migrate", "migrate", ["manage.py", "migrate", "--noinput"], "Apply the migrations to the database"),
            Command("createsuperuser", "createsuperuser...", ["manage.py", "createsuperuser", "--noinput"],
                    "Create an admin user (username, e-mail, password)", ask=["username", "email", "password"]),
            Command("startapp", "startapp...", ["manage.py", "startapp", "{name}"],
                    "Create a new app (added to INSTALLED_APPS)", ask=["name"]),
            Command("shell", "shell", ["manage.py", "shell"], "Django shell in the Terminal", terminal=True),
            Command("check", "check", ["manage.py", "check"], "Look for problems in the project"),
            Command("showmigrations", "showmigrations", ["manage.py", "showmigrations"], "Applied / pending migrations"),
            Command("collectstatic", "collectstatic", ["manage.py", "collectstatic", "--noinput"],
                    "Copy static files into STATIC_ROOT (for deployment)"),
            Command("test", "test", ["manage.py", "test"], "Run the tests of all apps"),
            Command("manage", "Run command...", ["manage.py", "{name}"],
                    "Run any manage.py command with its arguments (e.g. 'seed_blog' or 'showmigrations blog')",
                    ask=["name"]),
            Command("admin", "Open Admin", [], "Open /admin/ in the Preview"),
        ]


def parse_models(p: Path) -> dict:
    """Models of one models.py (ast): {"Post": {"app", "file", "line", "fields": [{name, type, related}]}}."""
    text = _read(p)
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return {}
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [ast.unparse(b) for b in node.bases]
        if not any(b.endswith("Model") or b.endswith("AbstractUser") or b.endswith("AbstractBaseUser")
                   for b in bases):
            continue
        fields = [{"name": "id", "type": "AutoField", "related": None}]
        for st in node.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) and \
                    isinstance(st.value, ast.Call):
                fname = st.targets[0].id
                ftype = ast.unparse(st.value.func).split(".")[-1]
                if not ftype.endswith("Field") and ftype not in ("ForeignKey", "OneToOneField", "ManyToManyField"):
                    continue
                related = None
                if ftype in ("ForeignKey", "OneToOneField", "ManyToManyField") and st.value.args:
                    a = st.value.args[0]
                    related = a.value if isinstance(a, ast.Constant) else ast.unparse(a)
                    related = str(related).split(".")[-1]
                    if related in ("AUTH_USER_MODEL", "settings.AUTH_USER_MODEL"):
                        related = "User"
                fields.append({"name": fname, "type": ftype, "related": related})
        out[node.name] = {"app": p.parent.name, "file": str(p), "line": node.lineno, "fields": fields}
    return out


RUNTIME_SCRIPT = r'''
import inspect, json, os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "@@SETTINGS@@")
import django
django.setup()
from django.conf import settings
out = {"framework": "django", "urls": [], "templates": [], "models": {}, "settings": [], "static": []}

def where(obj):
    try:
        obj = inspect.unwrap(obj)
        return inspect.getsourcefile(obj), inspect.getsourcelines(obj)[1]
    except Exception:
        return None, None

try:
    from django.urls import URLPattern, URLResolver, get_resolver
    def walk(patterns, prefix, ns):
        for p in patterns:
            if isinstance(p, URLResolver):
                walk(p.url_patterns, prefix + str(p.pattern), ns + [p.namespace] if p.namespace else ns)
            elif isinstance(p, URLPattern) and p.name:
                cb = p.callback
                target = getattr(cb, "view_class", None) or getattr(cb, "cls", None) or cb
                f, l = where(target)
                pat = prefix + str(p.pattern)
                import re as _re
                args = _re.findall(r"<(?:\w+:)?(\w+)>", pat) or _re.findall(r"\(\?P<(\w+)>", pat)
                out["urls"].append({"name": ":".join(ns + [p.name]), "pattern": pat, "args": args,
                                    "file": f, "line": l})
    walk(get_resolver().url_patterns, "", [])
except Exception as e:
    out["urls_error"] = str(e)

try:
    from django.template import engines
    seen = set()
    for eng in engines.all():
        inner = getattr(eng, "engine", None)
        dirs = []
        if inner is not None:
            loaders = list(inner.template_loaders)
            while loaders:
                ld = loaders.pop(0)
                if hasattr(ld, "loaders"):
                    loaders.extend(ld.loaders)
                elif hasattr(ld, "get_dirs"):
                    dirs.extend(ld.get_dirs())
        else:
            dirs = list(getattr(eng, "dirs", []) or [])
        for d in dirs:
            d = str(d)
            if not os.path.isdir(d) or "site-packages" in d and "django" in d.lower() and "admin" not in d:
                continue
            for root, _ds, files in os.walk(d):
                for fn in files:
                    full = os.path.join(root, fn)
                    name = os.path.relpath(full, d).replace(os.sep, "/")
                    if name not in seen:
                        seen.add(name)
                        out["templates"].append({"name": name, "file": full})
except Exception as e:
    out["templates_error"] = str(e)

try:
    from django.apps import apps
    for m in apps.get_models():
        fields = []
        for f in m._meta.get_fields():
            rel = getattr(f, "related_model", None)
            fields.append({"name": f.name, "type": type(f).__name__,
                           "related": rel.__name__ if rel is not None and hasattr(rel, "__name__") else None})
        f, l = where(m)
        out["models"][m.__name__] = {"app": m._meta.app_label, "file": f, "line": l, "fields": fields,
                                     "table": m._meta.db_table}
except Exception as e:
    out["models_error"] = str(e)

for name in dir(settings):
    if name.isupper():
        try:
            v = repr(getattr(settings, name))
        except Exception:
            v = ""
        out["settings"].append({"name": name, "value": v[:80]})

try:
    from django.contrib.staticfiles import finders
    seen = set()
    for finder in finders.get_finders():
        for path, storage in finder.list([]):
            path = path.replace(os.sep, "/")
            if path in seen:
                continue
            seen.add(path)
            try:
                full = storage.path(path)
            except Exception:
                full = ""
            if "site-packages" in full:
                continue
            out["static"].append({"name": path, "file": full})
except Exception as e:
    out["static_error"] = str(e)

print("@@RADIDE-PYWEB@@" + json.dumps(out))
'''


FRAMEWORK = Django()


class DjangoPlugin(PyWebPlugin):
    id = "python-django"
    display_name = "Django (Python)"
    framework = FRAMEWORK
    default_template = "django-app"


register_framework_template(FRAMEWORK, "django-app", "Django App",
                            "A Django project (django-admin startproject + an app 'core') in its own .venv: "
                            "views, URL names, templates, static files, SQLite, admin. F5 debugs with breakpoints "
                            "in views; the Django panel runs manage.py commands.", 10)

__all__ = ["Django", "DjangoPlugin", "FRAMEWORK", "parse_models", "patch_settings", "settings_module", "venv_python"]
