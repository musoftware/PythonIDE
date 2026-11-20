"""Project actions of Python projects (see docs/PROJECT_ACTIONS.md):

* **Django** - manage.py: startapp, makemigrations, migrate, showmigrations, createsuperuser, shell, dbshell,
  collectstatic, test, check, Run Server (= the IDE's website run); right-click an app folder: New View /
  Model / Form, register the models in the admin, New Template, makemigrations / migrate of this app;
  templates -> New Template; migrations -> Migrate / Show; models.py -> makemigrations ...
* **Flask** - flask routes / shell, New Blueprint, flask db migrate / upgrade (Flask-Migrate).
* **FastAPI** - open /docs, New Router module, alembic revision / upgrade (alembic.ini).
* **Python** (every Python project) - pip install -r requirements.txt, pip freeze > requirements.txt,
  create / recreate .venv, pytest, ruff / black, build a wheel (python -m build), Build EXE / Installer.
* **Jupyter** - convert notebooks to a Python script / HTML (the IDE's notebook model).
* **pygame / Arcade / Ursina** games - run, Export to Godot (pygame), Build EXE / Installer.
* **Kivy** - buildozer.spec, buildozer android debug (WSL on Windows), Build EXE / Installer.

The framework helpers of ``radide/web_site/frameworks`` (django.py, flask.py, fastapi.py, python_web.py)
are reused for the settings module, the Flask --app target, the FastAPI app module, parsing models ...
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import sys
from pathlib import Path

from ..project_actions import Action, Field, Provider, Separator, Submenu, matches, read_text

SKIP = {".venv", "venv", "env", ".git", "__pycache__", "node_modules", ".radide", ".radide_backup", "build",
        "dist", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "staticfiles", "media", "site-packages"}
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# ============================================================================ small helpers
def _language(folder: Path, project) -> str:
    lang = str(getattr(project, "language", "") or "") if project is not None else ""
    if project is not None and Path(getattr(project, "folder", "") or ".").resolve() != Path(folder).resolve():
        lang = ""
    if not lang:
        try:
            from ..web_site.frameworks.python_web import project_language
            lang = project_language(folder)
        except Exception:  # noqa: BLE001
            lang = ""
    return lang


def _web_cfg(folder: Path) -> dict:
    try:
        from ..web_site.frameworks.python_web import web_block
        return web_block(folder)
    except Exception:  # noqa: BLE001
        return {}


def _requirements_text(folder: Path) -> str:
    out = []
    for n in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile", "setup.py"):
        p = folder / n
        if p.is_file():
            out.append(read_text(p))
    return "\n".join(out).lower()


def _requires(folder: Path, package: str) -> bool:
    """*package* is named in requirements.txt / pyproject.toml / Pipfile / setup.py."""
    return re.search(rf"(?<![\w-]){re.escape(package.lower())}(?![\w-])", _requirements_text(folder)) is not None


def _cls(name: str) -> str:
    """snake_case / kebab -> CamelCase ("blog_post" -> "BlogPost")."""
    parts = re.split(r"[_\-\s]+", name.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def _snake(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name.strip())
    return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_").lower()


def _ident(ctx, value: str, what: str = "name") -> str | None:
    v = str(value or "").strip()
    if IDENT.match(v):
        return v
    ctx.log(f"*** '{v}' is not a valid {what} (letters, digits and _ ; not starting with a digit)")
    try:
        ctx.win.statusBar().showMessage(f"Invalid {what}: {v}", 6000)
    except Exception:  # noqa: BLE001
        pass
    return None


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _write(p: Path, text: str) -> None:
    """Write *text*, keeping the CRLF / LF line ends of an existing file."""
    nl = "\n"
    try:
        if b"\r\n" in p.read_bytes()[:4096]:
            nl = "\r\n"
    except OSError:
        pass
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline=nl)


def _line_of(text: str, needle: str) -> int:
    i = text.find(needle)
    return text.count("\n", 0, i) + 1 if i >= 0 else 1


_IMPORT_RX = re.compile(r"^(?:from[ \t]+\S+[ \t]+import[ \t]+(?:\([^)]*\)|[^\n]*)|import[ \t]+[^\n]*)\n?", re.M)
_TOP_RX = re.compile(r"^(?:def |class |async def |@|if __name__)", re.M)


def _insert_import_line(text: str, line: str) -> str:
    """Insert *line* (an import statement) after the imports at the top of the module."""
    top = _TOP_RX.search(text)
    limit = top.start() if top else len(text)
    last = None
    for m in _IMPORT_RX.finditer(text):
        if m.start() >= limit:
            break
        last = m
    if last is not None:
        end = last.end()
        if not text[last.start():end].endswith("\n"):
            return text[:end] + "\n" + line + "\n" + text[end:]
        return text[:end] + line + "\n" + text[end:]
    m = re.match(r'\s*(?:[rRuU]?("""|\'\'\')(?:.|\n)*?\1)[^\n]*\n', text)      # after a module docstring
    if m:
        return text[:m.end()] + "\n" + line + "\n" + text[m.end():]
    return line + "\n\n" + text if text.strip() else line + "\n"


def add_import(text: str, module: str, *names: str) -> str:
    """``from module import names`` - merged into an existing one-line import of *module*."""
    names = tuple(n for n in names if n)
    if not names:
        return text
    m = re.search(rf"^from[ \t]+{re.escape(module)}[ \t]+import[ \t]+([^\n(]+)$", text, re.M)
    if m:
        have = [x.strip() for x in m.group(1).split("#")[0].split(",") if x.strip()]
        add = [n for n in names if n not in have]
        if not add:
            return text
        new = ", ".join(sorted(set(have + add), key=lambda s: (s.lower(), s)))
        return text[:m.start(1)] + new + text[m.end(1):]
    m = re.search(rf"^from[ \t]+{re.escape(module)}[ \t]+import[ \t]+\(([^)]*)\)", text, re.M)
    if m:
        have = [x.split("#")[0].strip() for x in m.group(1).replace("\n", ",").split(",")]
        add = [n for n in names if n not in have]
        if not add:
            return text
        return text[:m.end()] + f"\nfrom {module} import {', '.join(add)}" + text[m.end():]
    return _insert_import_line(text, f"from {module} import {', '.join(names)}")


def _append_block(text: str, block: str) -> str:
    """*block* appended with two blank lines before it (PEP 8)."""
    return text.rstrip() + "\n\n\n" + block.strip("\n") + "\n" if text.strip() else block.strip("\n") + "\n"


def _venv(folder: Path) -> Path | None:
    for n in (".venv", "venv"):
        if (folder / n / "pyvenv.cfg").is_file():
            return folder / n
    return None


def _tool_argv(ctx, tool: str, *args) -> list[str]:
    """[tool, ...] when the tool is on PATH / in the .venv, else [python, -m, tool, ...]."""
    try:
        argv, _ = ctx.resolve_argv([tool])
        if Path(argv[0]).is_absolute():
            return [tool, *args]
    except Exception:  # noqa: BLE001
        pass
    return ["python", "-m", tool, *args]


def _with_hint(ctx, package: str, on_done=None):
    """on_done that adds a tip when a command failed in a project without a .venv."""
    def done(run):
        if run.exit_code not in (0, -2) and _venv(ctx.folder) is None and package:
            ctx.log(f"Tip: the project has no .venv - use Python > Create .venv (it installs requirements.txt), "
                    f"or Python > Install Package... '{package}'.")
        if on_done is not None:
            on_done(run)
    return done


NOT_OPENED = (".sqlite3", ".sqlite", ".db", ".pyc", ".log", ".exe", ".whl", ".zip", ".gz", ".apk")


def _cli(ctx, argv, package: str = "", opens=None, on_done=None, **kw):
    """ctx.run_cli for generators (makemigrations, flask db migrate, alembic revision ...): the files the command
    names in its output open in the editor - not every file that appeared meanwhile (a db.sqlite3 written by the
    IDE's background indexer must not open)."""
    eff = opens if opens is not None else (ctx.action.opens if ctx.action is not None else "none")
    if eff != "created":
        return ctx.run_cli(argv, opens=eff, on_done=_with_hint(ctx, package, on_done), **kw)
    import time
    from ..project_actions import MAX_OPEN, files_in_output
    t0 = time.time()

    def done(run):
        if run.exit_code == 0:
            files = [p for p in files_in_output(run.output, [run.cwd, ctx.folder], t0)
                     if p.suffix.lower() not in NOT_OPENED and p.name != "__init__.py"]
            run.created = files
            if files:
                ctx.refresh_tree()
                for p in files[:MAX_OPEN]:
                    ctx.open_file(p)
                ctx.log("Created: " + ", ".join(ctx.rel(p) for p in files))
        if on_done is not None:
            on_done(run)
    return ctx.run_cli(argv, opens="none", on_done=_with_hint(ctx, package, done), **kw)


def _ide_run(ctx, fallback_argv: list[str] | None = None, env: dict | None = None) -> None:
    """Run the project the way F5 / Ctrl+F5 does (website: DevServer + Preview), else run a command."""
    win, project = ctx.win, ctx.project
    same = project is not None and Path(getattr(project, "folder", "")).resolve() == ctx.folder
    if same and getattr(project, "kind", "") == "website":
        try:
            from ..features.web_workspace import run_website
            if run_website(win, project) is not None:
                return
        except Exception as e:  # noqa: BLE001
            ctx.log(f"*** run: {e}")
    elif same and fallback_argv is None and hasattr(win, "run_project"):
        win.run_project(debug=False)
        return
    if fallback_argv:
        ctx.run_cli(fallback_argv, env=env, opens="none", title=" ".join(fallback_argv[1:4]))


def _open_site_path(ctx, path: str) -> None:
    """Open *path* of the running site (started when needed) in the Preview."""
    try:
        from ..features import web_workspace as ww
        srv = ww._ensure_server(ctx.win, ctx.folder)
        if srv is None:
            ctx.log(f"*** cannot start the site to open {path}")
            return
        url = srv.url_for(path)
        prev = getattr(ctx.win, "web_preview", None)
        if prev is not None:
            prev.open_url(url)
        ctx.log(f"Opened {url}")
    except Exception as e:  # noqa: BLE001
        ctx.log(f"*** open {path}: {e}")


def _publish(ctx) -> None:
    pub = getattr(ctx.win, "publisher", None)
    if pub is None:
        ctx.log("*** the Publish / installer feature is not available")
        return
    pub.open_dialog()


def _publish_action() -> Action:
    return Action("publish", "Build EXE / Installer...", _publish, opens="none",
                  tip="Build a Windows program and a setup (Inno Setup) into the project's Publish folder")


# ---------------------------------------------------------------- templates (Django / Jinja)
def _templates_root(folder: Path, start: Path) -> Path | None:
    """The 'templates' folder that contains *start* (or None)."""
    for d in [start, *start.parents]:
        if d.name == "templates":
            return d
        if d == folder:
            break
    return None


def _base_template(folder: Path, troot: Path | None) -> tuple[str, str]:
    """(name of a base template to extend, its content block) - ("", "") when there is none."""
    cands = [troot] if troot is not None else []
    cands += [folder / "templates", folder / "app" / "templates"]
    for t in cands:
        if t is not None and (t / "base.html").is_file():
            blocks = re.findall(r"{%-?\s*block\s+(\w+)", _read(t / "base.html"))
            block = "content" if "content" in blocks else next((b for b in blocks if b != "title"), "")
            return "base.html", block
    return "", ""


def template_text(folder: Path, troot: Path | None, title: str, extends: bool = True) -> str:
    base, block = _base_template(folder, troot) if extends else ("", "")
    if base and block:
        return (f'{{% extends "{base}" %}}\n\n{{% block title %}}{title}{{% endblock %}}\n\n'
                f"{{% block {block} %}}\n<h1>{title}</h1>\n<p></p>\n{{% endblock %}}\n")
    return (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <title>{title}</title>\n'
            f"</head>\n<body>\n  <h1>{title}</h1>\n</body>\n</html>\n")


def _new_template_action(folder_rel: str) -> Action:
    def run(ctx):
        name = str(ctx.values.get("name") or "").strip().replace("\\", "/").strip("/")
        if not name:
            return
        if not Path(name).suffix:
            name += ".html"
        target = ctx.path(folder_rel) / name
        if target.exists():
            ctx.log(f"*** {ctx.rel(target)} already exists")
            ctx.open_file(target)
            return
        troot = _templates_root(ctx.folder, ctx.path(folder_rel))
        title = _cls(Path(name).stem).replace("_", " ") or "Page"
        _write(target, template_text(ctx.folder, troot, title, bool(ctx.values.get("extends", True))))
    return Action("new-template", "New Template...", run,
                  ask=[Field("name", "File name", default="page.html", help="e.g. about.html or blog/list.html"),
                       Field("extends", "Extend base.html", "bool", default=True)],
                  tip="A template in this folder (extends base.html when there is one)")


# ============================================================================ Django
class Django(Provider):
    id, title, priority = "django", "Django", 60
    icon = ("Dj", "#0C4B33")
    markers = ("manage.py", "project.radproj")

    def detect(self, folder, project):
        if _language(folder, project) == "python-django":
            return True
        mp = folder / "manage.py"
        return mp.is_file() and "django" in read_text(mp).lower()

    # ---------------------------------------------------------------- project facts
    @staticmethod
    def apps(folder: Path) -> list[str]:
        """Relative POSIX paths of the app folders (folders with apps.py; one level of nesting)."""
        out = []
        try:
            for d in sorted(folder.iterdir()):
                if not d.is_dir() or d.name in SKIP or d.name.startswith("."):
                    continue
                if (d / "apps.py").is_file():
                    out.append(d.name)
                    continue
                if (d / "__init__.py").is_file() or d.name in ("apps", "src"):
                    for s in sorted(d.iterdir()):
                        if s.is_dir() and (s / "apps.py").is_file():
                            out.append(f"{d.name}/{s.name}")
        except OSError:
            pass
        return out

    @staticmethod
    def label(app_rel: str) -> str:
        return app_rel.rstrip("/").split("/")[-1]

    def app_of(self, folder: Path, rel: str) -> str | None:
        """The app folder that contains *rel* (or None)."""
        r = rel.strip("/")
        for a in sorted(self.apps(folder), key=len, reverse=True):
            if r == a or r.startswith(a + "/"):
                return a
        return None

    @staticmethod
    def models(folder: Path, app_rel: str) -> list[str]:
        try:
            from ..web_site.frameworks.django import parse_models
            return list(parse_models(folder / app_rel / "models.py"))
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def env(ctx) -> dict:
        env = {"DJANGO_COLORS": "nocolor"}
        try:
            from ..web_site.frameworks.django import settings_module
            env["DJANGO_SETTINGS_MODULE"] = settings_module(ctx.folder, _web_cfg(ctx.folder))
        except Exception:  # noqa: BLE001
            pass
        return env

    def manage(self, ctx, *args, on_done=None, opens=None, env=None, title=None):
        e = self.env(ctx)
        e.update(env or {})
        args = [str(a) for a in args]
        return _cli(ctx, ["python", "manage.py", *args], "Django", opens, on_done, env=e,
                    title=title or "manage.py " + " ".join(args[:3]))

    # ---------------------------------------------------------------- menus
    def actions(self, ctx):
        apps = self.apps(ctx.folder)
        labels = [self.label(a) for a in apps]
        return [
            Action("runserver", "Run Server", lambda c: _ide_run(c, ["python", "manage.py", "runserver"], self.env(c)),
                   toolbar=True, opens="none", icon="SP_MediaPlay",
                   tip="Start the site (Ctrl+F5): Preview, Requests, live reload"),
            Action("admin", "Open Admin", lambda c: _open_site_path(c, "/admin/"), opens="none",
                   tip="/admin/ of the running site in the Preview"),
            Separator(),
            self.startapp_action(),
            Action("makemigrations", "Make Migrations...", self._makemigrations, toolbar=True,
                   ask=[Field("app", "App", "choice", default="(all apps)", choices=["(all apps)", *labels])],
                   tip="manage.py makemigrations - the new migration files open in the editor"),
            Action("migrate", "Migrate", lambda c: self.manage(c, "migrate", "--noinput"), opens="none",
                   toolbar=True, tip="manage.py migrate - apply the migrations to the database"),
            Action("showmigrations", "Show Migrations", lambda c: self.manage(c, "showmigrations"), opens="none",
                   tip="manage.py showmigrations - applied [X] and pending [ ] migrations"),
            Separator(),
            Action("createsuperuser", "Create Superuser...", self._createsuperuser, opens="none",
                   ask=[Field("username", "User name", default="admin"),
                        Field("email", "E-mail", required=False, placeholder="admin@example.com"),
                        Field("password", "Password", help="at least 8 characters, not too common")],
                   tip="manage.py createsuperuser - an admin user for /admin/"),
            Action("shell", "Shell", lambda c: c.run_in_terminal(["python", "manage.py", "shell"]), opens="none",
                   tip="manage.py shell in the Terminal"),
            Action("dbshell", "Database Shell", lambda c: c.run_in_terminal(["python", "manage.py", "dbshell"]),
                   opens="none", tip="manage.py dbshell in the Terminal (needs the database's client, e.g. sqlite3)"),
            Separator(),
            Action("collectstatic", "Collect Static Files", lambda c: self.manage(c, "collectstatic", "--noinput"),
                   opens="none", refresh=True, tip="manage.py collectstatic - copy static files to STATIC_ROOT"),
            Action("test", "Run Tests", lambda c: self.manage(c, "test"), opens="none",
                   tip="manage.py test - the tests of all apps"),
            Action("check", "Check Project", lambda c: self.manage(c, "check"), opens="none",
                   tip="manage.py check - look for problems in the project"),
            Action("manage", "Run manage.py Command...", self._manage_any, opens="created",
                   ask=[Field("command", "Command", placeholder="e.g. seed_blog or sqlmigrate blog 0001")],
                   tip="Any manage.py command with its arguments"),
        ]

    def startapp_action(self) -> Action:
        return Action("startapp", "New App...", self._startapp, opens="none", refresh=True,
                      ask=[Field("name", "App name", default="shop", help="a Python name, e.g. shop or accounts")],
                      tip="manage.py startapp - adds it to INSTALLED_APPS and opens models.py / views.py")

    def folder_actions(self, ctx, rel_folder):
        rel = rel_folder.strip("/")
        if rel == "":
            return self.actions(ctx)
        apps = self.apps(ctx.folder)
        if rel in apps:
            return self.app_actions(ctx, rel)
        app = self.app_of(ctx.folder, rel)
        if matches(rel, "**/templates/**"):
            return [_new_template_action(rel)]
        if app is not None and matches(rel, "**/migrations"):
            lab = self.label(app)
            return [Action("migrate-app", f"Migrate {lab}", lambda c: self.manage(c, "migrate", lab, "--noinput"),
                           opens="none"),
                    Action("show-app", f"Show Migrations of {lab}", lambda c: self.manage(c, "showmigrations", lab),
                           opens="none"),
                    Action("makemigrations-app", f"Make Migrations for {lab}",
                           lambda c: self.manage(c, "makemigrations", lab))]
        if app is not None and matches(rel, "**/management/commands", "**/management"):
            return [self.command_action(app)]
        if app is not None and matches(rel, "**/tests"):
            mod = rel.replace("/", ".")
            return [Action("test-folder", "Run These Tests", lambda c: self.manage(c, "test", mod), opens="none")]
        return []

    def app_actions(self, ctx, app: str) -> list:
        lab = self.label(app)
        return [
            self.view_action(ctx, app), self.model_action(app), self.form_action(ctx, app),
            Action("admin-register", "Register Models in Admin", lambda c: self._register_admin(c, app),
                   opens="none", tip=f"admin.site.register(...) for the models of {lab} not registered yet"),
            Action("template-app", "New Template...", lambda c: self._app_template(c, app),
                   ask=[Field("name", "File name", default="page.html"),
                        Field("extends", "Extend base.html", "bool", default=True)],
                   tip=f"templates/{lab}/<name>"),
            self.command_action(app),
            Separator(),
            Action("makemigrations-app", f"Make Migrations for {lab}", lambda c: self.manage(c, "makemigrations", lab),
                   tip=f"manage.py makemigrations {lab}"),
            Action("migrate-app", f"Migrate {lab}", lambda c: self.manage(c, "migrate", lab, "--noinput"),
                   opens="none"),
            Action("test-app", f"Run Tests of {lab}", lambda c: self.manage(c, "test", lab), opens="none"),
        ]

    def file_actions(self, ctx, rel_file):
        rel = rel_file.strip("/")
        app = self.app_of(ctx.folder, rel)
        if app is None:
            return []
        lab = self.label(app)
        name = Path(rel).name
        if rel == f"{app}/models.py":
            return [Action("makemigrations-app", f"Make Migrations for {lab}",
                           lambda c: self.manage(c, "makemigrations", lab)),
                    self.model_action(app),
                    Action("admin-register", "Register Models in Admin", lambda c: self._register_admin(c, app),
                           opens="none")]
        if rel == f"{app}/views.py":
            return [self.view_action(ctx, app)]
        if rel == f"{app}/admin.py":
            return [Action("admin-register", "Register Models in Admin", lambda c: self._register_admin(c, app),
                           opens="none")]
        if rel == f"{app}/forms.py":
            return [self.form_action(ctx, app)]
        if matches(rel, "**/migrations/*.py") and re.match(r"\d{4}_", name):
            mig = Path(name).stem
            return [Action("migrate-to", "Migrate to This Migration",
                           lambda c: self.manage(c, "migrate", lab, mig, "--noinput"), opens="none",
                           tip=f"manage.py migrate {lab} {mig} (also rolls back the newer ones)"),
                    Action("sqlmigrate", "Show SQL of This Migration",
                           lambda c: self.manage(c, "sqlmigrate", lab, mig[:4]), opens="none")]
        if matches(rel, "**/management/commands/*.py") and name != "__init__.py":
            cmd = Path(name).stem
            return [Action("run-command", f"Run manage.py {cmd}", lambda c: self.manage(c, cmd), opens="none")]
        if name == "tests.py" or (name.startswith("test") and name.endswith(".py")):
            mod = rel[:-3].replace("/", ".")
            return [Action("test-file", "Run These Tests", lambda c: self.manage(c, "test", mod), opens="none")]
        return []

    # ---------------------------------------------------------------- commands
    def _startapp(self, ctx):
        name = _ident(ctx, ctx.values.get("name"), "app name")
        if name is None:
            return
        if (ctx.folder / name).exists():
            ctx.log(f"*** a folder '{name}' already exists in the project")
            return

        def done(run):
            if run.exit_code != 0:
                return
            self.add_installed_app(ctx, name)
            ctx.refresh_tree()
            for f in ("models.py", "views.py"):
                if (ctx.folder / name / f).is_file():
                    ctx.open_file(ctx.folder / name / f)
        self.manage(ctx, "startapp", name, on_done=done, opens="none")

    @staticmethod
    def add_installed_app(ctx, app: str) -> None:
        try:
            from ..web_site.frameworks.django import add_installed_app, settings_file
            sf = settings_file(ctx.folder, _web_cfg(ctx.folder))
            if sf is None:
                ctx.log(f"Add '{app}' to INSTALLED_APPS in your settings.")
                return
            text = _read(sf)
            new = add_installed_app(text, app)
            if new != text:
                _write(sf, new)
                ctx.log(f"Added '{app}' to INSTALLED_APPS in {ctx.rel(sf)}")
        except Exception as e:  # noqa: BLE001
            ctx.log(f"*** INSTALLED_APPS: {e}")

    def _makemigrations(self, ctx):
        app = str(ctx.values.get("app") or "")
        self.manage(ctx, "makemigrations", *([] if app in ("", "(all apps)") else [app]))

    def _createsuperuser(self, ctx):
        v = ctx.values
        self.manage(ctx, "createsuperuser", "--noinput", "--username", v.get("username", "admin"),
                    "--email", v.get("email", "") or "",
                    env={"DJANGO_SUPERUSER_PASSWORD": v.get("password", ""),
                         "DJANGO_SUPERUSER_USERNAME": v.get("username", "admin"),
                         "DJANGO_SUPERUSER_EMAIL": v.get("email", "") or ""},
                    title="manage.py createsuperuser")

    def _manage_any(self, ctx):
        try:
            args = shlex.split(str(ctx.values.get("command") or ""), posix=True)
        except ValueError:
            args = str(ctx.values.get("command") or "").split()
        if args and args[0] in ("manage.py", "python"):
            args = [a for a in args if a not in ("python", "manage.py")]
        if args:
            self.manage(ctx, *args)

    # ---------------------------------------------------------------- code generators
    def model_action(self, app: str) -> Action:
        return Action("new-model", "New Model...", lambda c: self._new_model(c, app), opens="none", refresh=True,
                      ask=[Field("name", "Model name", default="Product"),
                           Field("fields", "Fields", required=False,
                                 placeholder="name:char price:decimal published:bool category:fk:Category",
                                 help="name:type ...  types: char text int decimal float bool date datetime email "
                                      "url slug image file fk:<Model> m2m:<Model> user"),
                           Field("timestamps", "Add created / updated date fields", "bool", default=True),
                           Field("admin", "Register it in the admin", "bool", default=True),
                           Field("migrate", "Make migrations afterwards", "bool", default=False)],
                      tip=f"A model class in {self.label(app)}/models.py")

    FIELD_TYPES = {
        "char": "models.CharField(max_length=200)", "str": "models.CharField(max_length=200)",
        "text": "models.TextField(blank=True)", "int": "models.IntegerField(default=0)",
        "decimal": "models.DecimalField(max_digits=10, decimal_places=2, default=0)",
        "money": "models.DecimalField(max_digits=10, decimal_places=2, default=0)",
        "float": "models.FloatField(default=0)", "bool": "models.BooleanField(default=False)",
        "date": "models.DateField(null=True, blank=True)", "datetime": "models.DateTimeField(null=True, blank=True)",
        "time": "models.TimeField(null=True, blank=True)", "email": "models.EmailField(blank=True)",
        "url": "models.URLField(blank=True)", "slug": "models.SlugField(unique=True)",
        "image": 'models.ImageField(upload_to="images/", blank=True)',
        "file": 'models.FileField(upload_to="files/", blank=True)',
        "json": "models.JSONField(default=dict, blank=True)", "uuid": "models.UUIDField(editable=False, null=True)",
    }

    def model_code(self, name: str, spec: str, timestamps: bool) -> tuple[str, bool]:
        """(class code, needs 'from django.conf import settings')."""
        lines, str_field, needs_settings = [], "", False
        for tok in spec.replace(",", " ").split():
            parts = tok.split(":")
            fname = _snake(parts[0])
            if not IDENT.match(fname or "-"):
                continue
            kind = (parts[1] if len(parts) > 1 else "char").lower()
            if kind in ("fk", "foreignkey", "m2m", "o2o") and len(parts) > 2:
                target = parts[2]
                if target.lower() == "user":
                    target, needs_settings = "settings.AUTH_USER_MODEL", True
                elif target != "self":
                    target = f'"{target}"' if target[:1].isupper() and "." not in target else target
                else:
                    target = '"self"'
                if kind == "m2m":
                    code = f"models.ManyToManyField({target}, blank=True)"
                elif kind == "o2o":
                    code = f"models.OneToOneField({target}, on_delete=models.CASCADE)"
                else:
                    code = f"models.ForeignKey({target}, on_delete=models.CASCADE)"
            elif kind == "user":
                code, needs_settings = "models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)", True
            else:
                code = self.FIELD_TYPES.get(kind, self.FIELD_TYPES["char"])
            if not str_field and code.startswith(("models.CharField", "models.SlugField", "models.EmailField")):
                str_field = fname
            lines.append(f"    {fname} = {code}")
        if not lines:
            lines.append("    name = models.CharField(max_length=200)")
            str_field = "name"
        if timestamps:
            lines += ["    created = models.DateTimeField(auto_now_add=True)",
                      "    updated = models.DateTimeField(auto_now=True)"]
        meta = ["", "    class Meta:", f'        ordering = ["{"-created" if timestamps else "id"}"]']
        body = "\n".join(lines + meta)
        ret = f"self.{str_field}" if str_field else 'f"{self.__class__.__name__} {self.pk}"'
        code = (f"class {name}(models.Model):\n{body}\n\n    def __str__(self):\n"
                f"        return {ret if not str_field else 'str(' + ret + ')'}\n")
        return code, needs_settings

    def _new_model(self, ctx, app: str):
        name = _ident(ctx, _cls(str(ctx.values.get("name") or "")), "model name")
        if name is None:
            return
        mp = ctx.folder / app / "models.py"
        text = _read(mp) or "from django.db import models\n"
        if re.search(rf"^class\s+{name}\b", text, re.M):
            ctx.log(f"*** {name} is already in {ctx.rel(mp)}")
            ctx.open_file(mp, _line_of(text, f"class {name}"))
            return
        code, needs_settings = self.model_code(name, str(ctx.values.get("fields") or ""),
                                               bool(ctx.values.get("timestamps", True)))
        if "from django.db import models" not in text:
            text = add_import(text, "django.db", "models")
        if needs_settings:
            text = add_import(text, "django.conf", "settings")
        text = re.sub(r"\n# Create your models here\.\n?", "\n", text)
        text = _append_block(text, code)
        _write(mp, text)
        ctx.log(f"Added the model {name} to {ctx.rel(mp)}")
        if ctx.values.get("admin", True):
            self._register_admin(ctx, app, [name], open_it=False)
        ctx.open_file(mp, _line_of(text, f"class {name}("))
        if ctx.values.get("migrate"):
            self.manage(ctx, "makemigrations", self.label(app), opens="created")

    def _register_admin(self, ctx, app: str, only: list[str] | None = None, open_it: bool = True):
        ap = ctx.folder / app / "admin.py"
        models = only or self.models(ctx.folder, app)
        text = _read(ap) or "from django.contrib import admin\n"
        done = set(re.findall(r"admin\.site\.register\(\s*(\w+)", text))
        for args in re.findall(r"@admin\.register\(([^)]*)\)", text):
            done |= set(re.findall(r"\b(\w+)\b", args.split("site=")[0]))
        todo = [m for m in models if m not in done]
        if not todo:
            ctx.log(f"All the models of {self.label(app)} are registered in the admin.")
            if open_it:
                ctx.open_file(ap)
            return
        if "from django.contrib import admin" not in text:
            text = add_import(text, "django.contrib", "admin")
        text = add_import(text, ".models", *todo)
        text = re.sub(r"\n# Register your models here\.\n?", "\n", text)
        text = text.rstrip() + "\n\n" + "".join(f"admin.site.register({m})\n" for m in todo)
        _write(ap, text)
        ctx.log(f"Registered in the admin: {', '.join(todo)} ({ctx.rel(ap)})")
        if open_it:
            ctx.open_file(ap, _line_of(text, f"admin.site.register({todo[0]})"))

    def view_action(self, ctx, app: str) -> Action:
        models = self.models(ctx.folder, app)
        return Action("new-view", "New View...", lambda c: self._new_view(c, app), opens="none", refresh=True,
                      ask=[Field("name", "View name", default="about", help="a Python name, e.g. about or product_list"),
                           Field("kind", "Kind", "choice", default="Function",
                                 choices=["Function", "TemplateView", "ListView", "DetailView", "CreateView"]),
                           Field("model", "Model (List / Detail / Create views)", "choice", default="(none)",
                                 choices=["(none)", *models]),
                           Field("template", "Create the template", "bool", default=True),
                           Field("url", "Add a URL to urls.py", "bool", default=True)],
                      tip=f"A view in {self.label(app)}/views.py (+ template + URL)")

    def _template_dir(self, folder: Path, app: str) -> Path:
        lab = self.label(app)
        if (folder / app / "templates").is_dir():
            return folder / app / "templates" / lab
        if (folder / "templates").is_dir():
            return folder / "templates" / lab
        return folder / app / "templates" / lab

    def _new_view(self, ctx, app: str):
        v = ctx.values
        name = _ident(ctx, _snake(str(v.get("name") or "")), "view name")
        if name is None:
            return
        lab = self.label(app)
        kind = str(v.get("kind") or "Function")
        model = str(v.get("model") or "(none)")
        model = "" if model == "(none)" else model
        if kind in ("ListView", "DetailView", "CreateView") and not model:
            ctx.log(f"{kind} needs a model - making a TemplateView instead.")
            kind = "TemplateView"
        vp = ctx.folder / app / "views.py"
        text = _read(vp) or "from django.shortcuts import render\n"
        tname = f"{lab}/{name}.html"
        if kind == "Function":
            target = name
            if re.search(rf"^def\s+{name}\b", text, re.M):
                ctx.log(f"*** {name} is already in {ctx.rel(vp)}")
                ctx.open_file(vp, _line_of(text, f"def {name}"))
                return
            text = add_import(text, "django.shortcuts", "render")
            code = (f"def {name}(request):\n    context = {{}}\n"
                    f'    return render(request, "{tname}", context)\n')
            needle = f"def {name}("
            ref = f"views.{name}"
        else:
            target = _cls(name) + ("" if _cls(name).endswith("View") else "View")
            if re.search(rf"^class\s+{target}\b", text, re.M):
                ctx.log(f"*** {target} is already in {ctx.rel(vp)}")
                ctx.open_file(vp, _line_of(text, f"class {target}"))
                return
            text = add_import(text, "django.views.generic", kind)
            lines = [f"class {target}({kind}):"]
            if model:
                text = add_import(text, ".models", model)
                lines.append(f"    model = {model}")
            lines.append(f'    template_name = "{tname}"')
            if kind == "ListView":
                lines += [f'    context_object_name = "{_snake(model)}_list"', "    paginate_by = 20"]
            elif kind == "DetailView":
                lines.append(f'    context_object_name = "{_snake(model)}"')
            elif kind == "CreateView":
                lines += ['    fields = "__all__"', '    success_url = "/"']
            code = "\n".join(lines) + "\n"
            needle = f"class {target}("
            ref = f"views.{target}.as_view()"
        text = re.sub(r"\n# Create your views here\.\n?", "\n", text)
        text = _append_block(text, code)
        _write(vp, text)
        ctx.log(f"Added the view {target} to {ctx.rel(vp)}")
        opened = []
        if v.get("template", True):
            tp = self._template_dir(ctx.folder, app) / f"{name}.html"
            if not tp.exists():
                troot = tp.parent.parent
                body = template_text(ctx.folder, troot, _cls(name).replace("_", " ") or name)
                if kind == "ListView":
                    var = f"{_snake(model)}_list"
                    body = body.replace("<p></p>", f"<ul>\n  {{% for obj in {var} %}}\n    <li>{{{{ obj }}}}</li>\n"
                                                   f"  {{% empty %}}\n    <li>Nothing yet.</li>\n  {{% endfor %}}\n</ul>")
                elif kind == "DetailView":
                    body = body.replace("<p></p>", f"<p>{{{{ {_snake(model)} }}}}</p>")
                elif kind == "CreateView":
                    body = body.replace("<p></p>", '<form method="post">\n  {% csrf_token %}\n  {{ form.as_p }}\n'
                                                   '  <button type="submit">Save</button>\n</form>')
                _write(tp, body)
                ctx.log(f"Created {ctx.rel(tp)}")
                opened.append(tp)
        if v.get("url", True):
            self._add_url(ctx, app, name, ref, kind == "DetailView")
        ctx.refresh_tree()
        for p in opened:
            ctx.open_file(p)
        ctx.open_file(vp, _line_of(text, needle))

    def _add_url(self, ctx, app: str, name: str, ref: str, detail: bool) -> None:
        up = ctx.folder / app / "urls.py"
        route = f"{name.replace('_', '-')}/" + ("<int:pk>/" if detail else "")
        entry = f'    path("{route}", {ref}, name="{name}"),'
        if not up.is_file():
            lab = self.label(app)
            _write(up, f'from django.urls import path\n\nfrom . import views\n\napp_name = "{lab}"\n\n'
                       f"urlpatterns = [\n{entry}\n]\n")
            ctx.log(f"Created {ctx.rel(up)} - include it in the project's urls.py: "
                    f'path("{lab}/", include("{app.replace("/", ".")}.urls"))')
            return
        text = _read(up)
        if f'name="{name}"' in text or f"name='{name}'" in text:
            return
        m = re.search(r"urlpatterns\s*=\s*\[", text)
        close = -1
        if m is not None:
            depth = 0
            for i in range(m.end() - 1, len(text)):
                depth += {"[": 1, "]": -1}.get(text[i], 0)
                if depth == 0:
                    close = i
                    break
        if close < 0:
            text = text.rstrip() + f"\n\nurlpatterns += [\n{entry}\n]\n"
        else:
            inner = text[m.end():close].rstrip()
            sep = "," if inner.strip() and not inner.endswith(",") else ""
            text = text[:m.end()] + inner + sep + "\n" + entry + "\n" + text[close:]
        if "from . import views" not in text and "import views" not in text:
            text = add_import(text, ".", "views")
        _write(up, text)
        ctx.log(f"Added the URL '{route}' to {ctx.rel(up)}")

    def form_action(self, ctx, app: str) -> Action:
        models = self.models(ctx.folder, app)
        return Action("new-form", "New Form...", lambda c: self._new_form(c, app), opens="none", refresh=True,
                      ask=[Field("model", "Model", "choice", default="(plain Form)", choices=["(plain Form)", *models]),
                           Field("name", "Form name", required=False, placeholder="empty = <Model>Form / ContactForm")],
                      tip=f"A form class in {self.label(app)}/forms.py")

    def _new_form(self, ctx, app: str):
        v = ctx.values
        model = str(v.get("model") or "")
        model = "" if model.startswith("(") else model
        name = str(v.get("name") or "").strip() or (f"{model}Form" if model else "ContactForm")
        name = _ident(ctx, _cls(name), "form name")
        if name is None:
            return
        fp = ctx.folder / app / "forms.py"
        text = _read(fp) or "from django import forms\n"
        if re.search(rf"^class\s+{name}\b", text, re.M):
            ctx.log(f"*** {name} is already in {ctx.rel(fp)}")
            ctx.open_file(fp, _line_of(text, f"class {name}"))
            return
        text = add_import(text, "django", "forms") if "from django import forms" not in text else text
        if model:
            try:
                from ..web_site.frameworks.django import parse_models
                info = parse_models(ctx.folder / app / "models.py").get(model, {})
                fields = [f["name"] for f in info.get("fields", []) if f["name"] not in ("id", "created", "updated")]
            except Exception:  # noqa: BLE001
                fields = []
            text = add_import(text, ".models", model)
            flist = "[" + ", ".join(f'"{f}"' for f in fields) + "]" if fields else '"__all__"'
            code = f"class {name}(forms.ModelForm):\n    class Meta:\n        model = {model}\n        fields = {flist}\n"
        else:
            code = (f"class {name}(forms.Form):\n    name = forms.CharField(max_length=100)\n"
                    f"    email = forms.EmailField()\n    message = forms.CharField(widget=forms.Textarea)\n")
        text = _append_block(text, code)
        _write(fp, text)
        ctx.log(f"Added the form {name} to {ctx.rel(fp)}")
        ctx.open_file(fp, _line_of(text, f"class {name}("))

    def _app_template(self, ctx, app: str):
        name = str(ctx.values.get("name") or "").strip().replace("\\", "/").strip("/")
        if not name:
            return
        if not Path(name).suffix:
            name += ".html"
        tp = self._template_dir(ctx.folder, app) / name
        if tp.exists():
            ctx.open_file(tp)
            return
        _write(tp, template_text(ctx.folder, tp.parent.parent, _cls(Path(name).stem).replace("_", " "),
                                 bool(ctx.values.get("extends", True))))

    def command_action(self, app: str) -> Action:
        def run(c):
            name = _ident(c, _snake(str(c.values.get("name") or "")), "command name")
            if name is None:
                return
            base = c.folder / app / "management"
            for d in (base, base / "commands"):
                if not (d / "__init__.py").exists():
                    _write(d / "__init__.py", "")
            p = base / "commands" / f"{name}.py"
            if p.exists():
                c.open_file(p)
                return
            _write(p, '"""manage.py ' + name + '"""\nfrom django.core.management.base import BaseCommand\n\n\n'
                      "class Command(BaseCommand):\n"
                      f'    help = "{name.replace("_", " ").capitalize()}"\n\n'
                      "    def add_arguments(self, parser):\n"
                      '        parser.add_argument("--dry-run", action="store_true")\n\n'
                      "    def handle(self, *args, **options):\n"
                      '        self.stdout.write(self.style.SUCCESS("Done"))\n')
        return Action("new-command", "New Management Command...", run,
                      ask=[Field("name", "Command name", default="seed_data")],
                      tip=f"{self.label(app)}/management/commands/<name>.py (run: manage.py <name>)")


# ============================================================================ Flask
class Flask(Provider):
    id, title, priority = "flask", "Flask", 60
    icon = ("Fl", "#3B3B3B")
    markers = ("project.radproj", "requirements.txt", "pyproject.toml", "app.py")

    def detect(self, folder, project):
        lang = _language(folder, project)
        if lang == "python-flask":
            return True
        if lang.startswith("python-") and lang != "python-flask" and lang not in ("python-tk", "python-qt"):
            return False
        return _requires(folder, "flask") and any((folder / n).exists() for n in
                                                  ("app.py", "wsgi.py", "app/__init__.py", "main.py", "application.py"))

    @staticmethod
    def app(folder: Path) -> str:
        try:
            from ..web_site.frameworks.flask import app_target
            return app_target(folder, _web_cfg(folder))
        except Exception:  # noqa: BLE001
            return "app"

    def flask(self, ctx, *args, on_done=None, opens=None, title=None):
        args = [str(a) for a in args]
        return _cli(ctx, ["python", "-m", "flask", "--app", self.app(ctx.folder), *args], "Flask", opens, on_done,
                    env={"NO_COLOR": "1"}, title=title or "flask " + " ".join(args[:3]))

    @staticmethod
    def package_dir(folder: Path, app: str) -> Path | None:
        """The application package (app/ with __init__.py), or None for a single-module app."""
        p = folder / app.split(":")[0].replace(".", "/")
        return p if (p / "__init__.py").is_file() else None

    def has_migrate(self, folder: Path) -> bool:
        return _requires(folder, "flask-migrate") or (folder / "migrations" / "alembic.ini").is_file()

    def actions(self, ctx):
        items = [
            Action("run", "Run Server", lambda c: _ide_run(c, ["python", "-m", "flask", "--app",
                                                              self.app(c.folder), "run"]),
                   toolbar=True, opens="none", icon="SP_MediaPlay", tip="Start the site (Ctrl+F5)"),
            Action("routes", "Routes", lambda c: self.flask(c, "routes"), opens="none", toolbar=True,
                   tip="flask routes - the URL rules of the app"),
            Action("shell", "Flask Shell", lambda c: c.run_in_terminal(["python", "-m", "flask", "--app",
                                                                        self.app(c.folder), "shell"]),
                   opens="none", tip="flask shell in the Terminal (the app context is loaded)"),
            Action("command", "Run flask Command...", self._any, opens="created",
                   ask=[Field("command", "Command", placeholder="e.g. init-db")],
                   tip="A command of the app's CLI"),
            Separator(),
            self.blueprint_action(),
        ]
        if self.has_migrate(ctx.folder):
            items += [Separator(), Submenu("Database (Flask-Migrate)", self.db_actions(ctx))]
        return items

    def db_actions(self, ctx) -> list:
        no_mig = not (ctx.folder / "migrations").is_dir()
        return [
            Action("db-init", "flask db init", lambda c: self.flask(c, "db", "init"), opens="none", refresh=True,
                   enabled=lambda c: not (c.folder / "migrations").is_dir(),
                   tip="Create the migrations folder (once)"),
            Action("db-migrate", "New Migration (flask db migrate)...",
                   lambda c: self.flask(c, "db", "migrate", "-m", c.values.get("message") or "changes"),
                   enabled=lambda c: (c.folder / "migrations").is_dir(),
                   ask=[Field("message", "Message", default="changes")],
                   tip="Autogenerate a migration from the model changes (it opens in the editor)"),
            Action("db-upgrade", "Upgrade Database (flask db upgrade)", lambda c: self.flask(c, "db", "upgrade"),
                   opens="none", toolbar=not no_mig),
            Action("db-downgrade", "Downgrade One Step", lambda c: self.flask(c, "db", "downgrade"), opens="none"),
            Action("db-history", "Migration History", lambda c: self.flask(c, "db", "history"), opens="none"),
        ]

    def folder_actions(self, ctx, rel_folder):
        rel = rel_folder.strip("/")
        if rel == "":
            return self.actions(ctx)
        if matches(rel, "**/templates/**"):
            return [_new_template_action(rel)]
        pkg = self.package_dir(ctx.folder, self.app(ctx.folder))
        if pkg is not None and ctx.rel(pkg) == rel:
            return [self.blueprint_action()]
        if rel == "migrations" and self.has_migrate(ctx.folder):
            return self.db_actions(ctx)[1:]
        return []

    def blueprint_action(self) -> Action:
        return Action("new-blueprint", "New Blueprint...", self._new_blueprint, opens="none", refresh=True,
                      ask=[Field("name", "Name", default="admin", help="a Python name (module + blueprint name)"),
                           Field("prefix", "URL prefix", required=False, placeholder="empty = /<name>"),
                           Field("template", "Create templates/<name>/index.html", "bool", default=True),
                           Field("register", "Register it in the app", "bool", default=True)],
                      tip="A Blueprint module with an index route, registered in create_app()")

    def _any(self, ctx):
        args = str(ctx.values.get("command") or "").split()
        if args and args[0] == "flask":
            args = args[1:]
        if args:
            self.flask(ctx, *args)

    def _new_blueprint(self, ctx):
        v = ctx.values
        name = _ident(ctx, _snake(str(v.get("name") or "")), "blueprint name")
        if name is None:
            return
        prefix = str(v.get("prefix") or "").strip() or f"/{name}"
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        app = self.app(ctx.folder)
        pkg = self.package_dir(ctx.folder, app)
        base = pkg if pkg is not None else ctx.folder
        mod = base / f"{name}.py"
        if mod.exists():
            ctx.log(f"*** {ctx.rel(mod)} already exists")
            ctx.open_file(mod)
            return
        troot = base / "templates" if (base / "templates").is_dir() or pkg is not None else ctx.folder / "templates"
        make_tpl = bool(v.get("template", True))
        body = (f'"""The {name} blueprint ({prefix})."""\nfrom flask import Blueprint, render_template\n\n'
                f'bp = Blueprint("{name}", __name__, url_prefix="{prefix}")\n\n\n'
                f'@bp.route("/")\ndef index():\n')
        body += (f'    return render_template("{name}/index.html")\n' if make_tpl else
                 f'    return "{_cls(name)} works"\n')
        _write(mod, body)
        ctx.log(f"Created {ctx.rel(mod)}")
        opened = [mod]
        if make_tpl:
            tp = troot / name / "index.html"
            if not tp.exists():
                _write(tp, template_text(ctx.folder, troot, _cls(name)))
                opened.append(tp)
        if v.get("register", True):
            self._register(ctx, pkg, name)
        ctx.refresh_tree()
        for p in reversed(opened):
            ctx.open_file(p, _line_of(_read(p), "def index") if p == mod else None)

    def _register(self, ctx, pkg: Path | None, name: str) -> None:
        if pkg is not None:
            init = pkg / "__init__.py"
            text = _read(init)
            if f"{name}_bp" in text:
                return
            lines = text.split("\n")
            idx = None
            in_factory = False
            for i, ln in enumerate(lines):
                if re.match(r"def\s+create_app\b", ln):
                    in_factory = True
                elif in_factory and re.match(r"\s+return\s+app\b", ln):
                    idx = i
            if idx is None:
                ctx.log(f"Register the blueprint yourself: from .{name} import bp as {name}_bp; "
                        f"app.register_blueprint({name}_bp)")
                return
            ind = re.match(r"\s*", lines[idx]).group(0)
            lines[idx:idx] = [f"{ind}from .{name} import bp as {name}_bp",
                              f"{ind}app.register_blueprint({name}_bp)", ""]
            _write(init, "\n".join(lines))
            ctx.log(f"Registered the blueprint in {ctx.rel(init)}")
            return
        appf = ctx.folder / (self.app(ctx.folder).split(":")[0].replace(".", "/") + ".py")
        text = _read(appf)
        if not text or f"{name}_bp" in text:
            return
        reg = f"from {name} import bp as {name}_bp  # noqa: E402\napp.register_blueprint({name}_bp)\n"
        m = re.search(r"^if __name__\s*==", text, re.M)
        text = text[:m.start()] + reg + "\n\n" + text[m.start():] if m else text.rstrip() + "\n\n" + reg
        _write(appf, text)
        ctx.log(f"Registered the blueprint in {ctx.rel(appf)}")


# ============================================================================ FastAPI
class FastAPI(Provider):
    id, title, priority = "fastapi", "FastAPI", 60
    icon = ("FA", "#009688")
    markers = ("project.radproj", "requirements.txt", "pyproject.toml", "alembic.ini")

    def detect(self, folder, project):
        lang = _language(folder, project)
        if lang == "python-fastapi":
            return True
        if lang.startswith("python-") and lang not in ("python-tk", "python-qt"):
            return False
        return _requires(folder, "fastapi")

    @staticmethod
    def target(folder: Path) -> str:
        try:
            from ..web_site.frameworks.fastapi import app_target
            return app_target(folder, _web_cfg(folder))
        except Exception:  # noqa: BLE001
            return "app.main:app"

    def main_file(self, folder: Path) -> Path:
        return folder / (self.target(folder).split(":")[0].replace(".", "/") + ".py")

    def alembic(self, ctx, *args, opens=None):
        args = [str(a) for a in args]
        return _cli(ctx, _tool_argv(ctx, "alembic", *args), "alembic", opens, title="alembic " + " ".join(args[:3]))

    def actions(self, ctx):
        tgt = self.target(ctx.folder)
        items = [
            Action("run", "Run Server", lambda c: _ide_run(c, ["python", "-m", "uvicorn", tgt, "--reload"]),
                   toolbar=True, opens="none", icon="SP_MediaPlay", tip="Start the API (Ctrl+F5)"),
            Action("docs", "Open /docs", lambda c: _open_site_path(c, "/docs"), toolbar=True, opens="none",
                   tip="Swagger UI of the API in the Preview"),
            Action("redoc", "Open /redoc", lambda c: _open_site_path(c, "/redoc"), opens="none"),
            Separator(),
            self.router_action(),
            Separator(),
        ]
        items.append(Submenu("Database (Alembic)", self.alembic_actions(ctx)))
        return items

    def alembic_actions(self, ctx) -> list:
        if not (ctx.folder / "alembic.ini").is_file():
            return [Action("alembic-init", "Set Up Alembic (alembic init)", self._alembic_init, opens="none",
                           refresh=True, tip="alembic init alembic - migrations for SQLAlchemy models")]
        return [
            Action("alembic-revision", "New Migration (autogenerate)...",
                   lambda c: self.alembic(c, "revision", "--autogenerate", "-m", c.values.get("message") or "changes"),
                   ask=[Field("message", "Message", default="changes")],
                   tip="alembic revision --autogenerate (the new file opens in the editor)"),
            Action("alembic-upgrade", "Upgrade to Head", lambda c: self.alembic(c, "upgrade", "head"), opens="none"),
            Action("alembic-downgrade", "Downgrade One Step", lambda c: self.alembic(c, "downgrade", "-1"),
                   opens="none"),
            Action("alembic-current", "Current Revision", lambda c: self.alembic(c, "current"), opens="none"),
            Action("alembic-history", "History", lambda c: self.alembic(c, "history"), opens="none"),
        ]

    def _alembic_init(self, ctx):
        def done(run):
            if run.exit_code == 0:
                for rel in ("alembic.ini", "alembic/env.py"):
                    if (ctx.folder / rel).is_file():
                        ctx.open_file(ctx.folder / rel)
                ctx.log("Alembic is set up: set sqlalchemy.url in alembic.ini and target_metadata in alembic/env.py "
                        "(e.g. from app.database import Base; target_metadata = Base.metadata).")
        ctx.run_cli(_tool_argv(ctx, "alembic", "init", "alembic"), opens="none", title="alembic init",
                    on_done=_with_hint(ctx, "alembic", done))

    def folder_actions(self, ctx, rel_folder):
        rel = rel_folder.strip("/")
        if rel == "":
            return self.actions(ctx)
        if matches(rel, "**/templates/**"):
            return [_new_template_action(rel)]
        if matches(rel, "**/routers", "**/routes", "**/api"):
            return [self.router_action()]
        main_pkg = self.main_file(ctx.folder).parent
        if ctx.rel(main_pkg) == rel and main_pkg != ctx.folder:
            return [self.router_action()]
        if matches(rel, "alembic/**", "migrations/**") and (ctx.folder / "alembic.ini").is_file():
            return self.alembic_actions(ctx)
        return []

    def file_actions(self, ctx, rel_file):
        if ctx.path(rel_file) == self.main_file(ctx.folder):
            return [self.router_action(),
                    Action("docs", "Open /docs", lambda c: _open_site_path(c, "/docs"), opens="none")]
        return []

    def router_action(self) -> Action:
        return Action("new-router", "New Router Module...", self._new_router, opens="none", refresh=True,
                      ask=[Field("name", "Name", default="users", help="module name, e.g. users or orders"),
                           Field("prefix", "URL prefix", required=False, placeholder="empty = /<name>"),
                           Field("register", "Include it in the app (app.include_router)", "bool", default=True)],
                      tip="routers/<name>.py with an APIRouter and CRUD stubs")

    def _new_router(self, ctx):
        v = ctx.values
        name = _ident(ctx, _snake(str(v.get("name") or "")), "router name")
        if name is None:
            return
        prefix = str(v.get("prefix") or "").strip() or f"/{name}"
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        main = self.main_file(ctx.folder)
        pkg = main.parent
        rdir = pkg / "routers"
        mod = rdir / f"{name}.py"
        if mod.exists():
            ctx.log(f"*** {ctx.rel(mod)} already exists")
            ctx.open_file(mod)
            return
        if not (rdir / "__init__.py").exists():
            _write(rdir / "__init__.py", "")
        item = _cls(name[:-1] if name.endswith("s") and len(name) > 2 else name)
        _write(mod, f'"""{prefix} routes."""\nfrom fastapi import APIRouter, HTTPException\n\n'
                    f'router = APIRouter(prefix="{prefix}", tags=["{name}"])\n\n'
                    f"_items: dict[int, dict] = {{}}\n\n\n"
                    f'@router.get("/")\ndef list_{name}():\n    return list(_items.values())\n\n\n'
                    f'@router.get("/{{item_id}}")\ndef get_{_snake(item)}(item_id: int):\n'
                    f'    if item_id not in _items:\n        raise HTTPException(404, "{item} not found")\n'
                    f"    return _items[item_id]\n\n\n"
                    f'@router.post("/", status_code=201)\ndef create_{_snake(item)}(data: dict):\n'
                    f"    item_id = max(_items, default=0) + 1\n    _items[item_id] = {{\"id\": item_id, **data}}\n"
                    f"    return _items[item_id]\n")
        ctx.log(f"Created {ctx.rel(mod)}")
        if v.get("register", True) and main.is_file():
            text = _read(main)
            if f"{name}.router" not in text:
                in_pkg = (pkg / "__init__.py").is_file() and pkg != ctx.folder
                text = add_import(text, ".routers" if in_pkg else "routers", name)
                lines = text.split("\n")
                at = None
                for i, ln in enumerate(lines):
                    if re.match(r"app\s*=\s*FastAPI\(", ln):
                        depth, j = 0, i
                        while j < len(lines):
                            depth += lines[j].count("(") - lines[j].count(")")
                            if depth <= 0:
                                break
                            j += 1
                        at = j + 1
                        break
                if at is None:
                    lines += ["", f"app.include_router({name}.router)"]
                else:
                    while at < len(lines) and re.match(r"app\.(include_router|mount|add_middleware)\(", lines[at]):
                        at += 1
                    lines.insert(at, f"app.include_router({name}.router)")
                text = "\n".join(lines)
                _write(main, text)
                ctx.log(f"Included the router in {ctx.rel(main)}")
        ctx.refresh_tree()
        ctx.open_file(mod, _line_of(_read(mod), f"def list_{name}"))


# ============================================================================ generic Python
PY_LANGS = ("pygame", "kivy", "godot")


class Python(Provider):
    id, title, priority = "python", "Python", 20
    icon = ("Py", "#3776AB")
    markers = ("project.radproj", "requirements.txt", "pyproject.toml", "setup.py", "manage.py")

    def detect(self, folder, project):
        lang = _language(folder, project)
        if lang.startswith("python") or lang in ("pygame", "kivy"):
            return True
        if lang:
            return False
        return any((folder / n).is_file() for n in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile",
                                                     "manage.py"))

    @staticmethod
    def framework_active(ctx) -> bool:
        return any(p.detect(ctx.folder, ctx.project) for p in (DJANGO, FLASK, FASTAPI))

    def pip(self, ctx, *args, on_done=None):
        args = [str(a) for a in args]
        return ctx.run_cli(["python", "-m", "pip", *args], opens="none", title="pip " + " ".join(args[:3]),
                           on_done=on_done)

    def actions(self, ctx):
        f = ctx.folder
        has_req = (f / "requirements.txt").is_file()
        has_venv = _venv(f) is not None
        alone = not self.framework_active(ctx)
        items = []
        if has_req:
            items.append(Action("pip-install-r", "Install Requirements", lambda c: self.pip(c, "install", "-r",
                                                                                         "requirements.txt"),
                                opens="none", tip="pip install -r requirements.txt (into the project's .venv)"))
        items += [
            Action("pip-install", "Install Package...", self._install, opens="none",
                   ask=[Field("package", "Package", placeholder="e.g. requests or django-environ==0.11"),
                        Field("save", "Add it to requirements.txt", "bool", default=True)]),
            Action("pip-freeze", "Freeze to requirements.txt", self._freeze, opens="none",
                   tip="pip freeze > requirements.txt"),
            Action("pip-list", "List Installed Packages", lambda c: self.pip(c, "list"), opens="none"),
            Separator(),
            Action("venv-create", "Recreate .venv" if has_venv else "Create .venv", self._venv, opens="none",
                   refresh=True, tip="python -m venv .venv, then pip install -r requirements.txt"),
            Separator(),
            Action("pytest", "Run Tests (pytest)", lambda c: c.run_cli(["python", "-m", "pytest", "-q"],
                                                                       opens="none", title="pytest",
                                                                       on_done=_with_hint(c, "pytest")),
                   opens="none", toolbar=alone, icon="SP_DialogApplyButton"),
            Action("unittest", "Run Tests (unittest)",
                   lambda c: c.run_cli(["python", "-m", "unittest", "discover", "-v"], opens="none",
                                       title="unittest discover"), opens="none"),
            Separator(),
            Submenu("Format and Lint", [
                Action("ruff-format", "Format Project (ruff)", lambda c: self._fmt(c, "ruff", "format", "."),
                       opens="none"),
                Action("black", "Format Project (black)", lambda c: self._fmt(c, "black", "."), opens="none"),
                Action("ruff-check", "Lint Project (ruff check)", lambda c: self._fmt(c, "ruff", "check", "."),
                       opens="none"),
                Action("ruff-fix", "Fix Lint Problems (ruff check --fix)",
                       lambda c: self._fmt(c, "ruff", "check", "--fix", "."), opens="none"),
            ]),
        ]
        build = []
        if (f / "pyproject.toml").is_file() or (f / "setup.py").is_file():
            build.append(Action("build-wheel", "Build Wheel (python -m build)", self._build, opens="none",
                                refresh=True, tip="sdist + wheel into dist/ (pip install build)"))
        if getattr(ctx.project, "kind", "") != "website" or not alone:
            build.append(_publish_action())
        if build:
            items += [Separator(), *build]
        return items

    def folder_actions(self, ctx, rel_folder):
        rel = rel_folder.strip("/")
        if rel == "":
            return [Submenu("Python", self.actions(ctx))] if self.framework_active(ctx) else self.actions(ctx)
        if matches(rel, "tests", "**/tests", "test", "**/test"):
            return [Action("pytest-folder", "Run Tests in This Folder (pytest)",
                           lambda c: c.run_cli(["python", "-m", "pytest", "-q", rel], opens="none",
                                               title=f"pytest {rel}"), opens="none")]
        return []

    def file_actions(self, ctx, rel_file):
        rel = rel_file.strip("/")
        name = Path(rel).name
        if matches(rel, "**/test_*.py", "**/*_test.py"):
            return [Action("pytest-file", "Run This Test File (pytest)",
                           lambda c: c.run_cli(["python", "-m", "pytest", "-q", rel], opens="none",
                                               title=f"pytest {name}"), opens="none")]
        if matches(rel, "**/requirements*.txt"):
            return [Action("pip-install-file", "Install These Requirements",
                           lambda c: self.pip(c, "install", "-r", rel), opens="none")]
        if name in ("pyproject.toml", "setup.py") and "/" not in rel:
            return [Action("pip-editable", "Install Project (pip install -e .)",
                           lambda c: self.pip(c, "install", "-e", "."), opens="none")]
        if name.endswith(".py") and not self.framework_active(ctx):
            return [Action("ruff-format-file", "Format This File (ruff)",
                           lambda c: self._fmt(c, "ruff", "format", rel), opens="none")]
        return []

    # ---------------------------------------------------------------- commands
    def _install(self, ctx):
        pkg = str(ctx.values.get("package") or "").strip()
        if not pkg:
            return
        save = bool(ctx.values.get("save", True))

        def done(run):
            if run.exit_code != 0 or not save:
                return
            req = ctx.folder / "requirements.txt"
            text = _read(req)
            names = pkg.split()
            have = {re.split(r"[<>=!~\[; ]", ln.strip(), maxsplit=1)[0].lower() for ln in text.splitlines()}
            add = [n for n in names if re.split(r"[<>=!~\[; ]", n, maxsplit=1)[0].lower() not in have]
            if add:
                _write(req, (text.rstrip() + "\n" if text.strip() else "") + "\n".join(add) + "\n")
                ctx.log(f"Added to requirements.txt: {', '.join(add)}")
                ctx.refresh_tree()
        self.pip(ctx, "install", *pkg.split(), on_done=done)

    def _freeze(self, ctx):
        req = ctx.folder / "requirements.txt"
        if req.is_file() and not ctx.confirm("Replace requirements.txt with the packages installed in the "
                                             "project's environment (pip freeze)?"):
            return

        def done(run):
            if run.exit_code != 0:
                return
            lines = [ln for ln in run.output.splitlines()
                     if ln.strip() and not ln.startswith(("#", "WARNING", "[notice]", "DEPRECATION"))]
            _write(req, "\n".join(lines) + "\n")
            ctx.log(f"Wrote {len(lines)} package(s) to requirements.txt")
            ctx.refresh_tree()
            ctx.open_file(req)
        self.pip(ctx, "freeze", "--exclude-editable", on_done=done)

    def _venv(self, ctx):
        f = ctx.folder
        old = _venv(f)
        if old is not None:
            if not ctx.confirm(f"Delete {old.name} and create it again (the packages are installed again from "
                               f"requirements.txt)?"):
                return
            try:
                shutil.rmtree(old)
            except OSError as e:
                ctx.log(f"*** cannot delete {old}: {e} - stop the programs that use it (a running site, the "
                        f"debugger) and try again")
                return
        try:
            from ..web_site.frameworks.python_web import base_python
            exe = str(ctx.win.settings.value("interpreter/python", "") or "") if hasattr(ctx.win, "settings") else ""
            py = base_python(exe)
        except Exception:  # noqa: BLE001
            py = shutil.which("python") or sys.executable

        def done(run):
            if run.exit_code != 0:
                return
            ctx.refresh_tree()
            if (f / "requirements.txt").is_file():
                self.pip(ctx, "install", "-r", "requirements.txt")
        ctx.run_cli([py, "-m", "venv", ".venv"], opens="none", title="python -m venv .venv", on_done=done)

    def _fmt(self, ctx, tool: str, *args):
        ctx.run_cli(_tool_argv(ctx, tool, *args), opens="none", title=f"{tool} {' '.join(args[:2])}",
                    on_done=_with_hint(ctx, tool, lambda r: self._reload_editors(ctx) if r.exit_code == 0 else None))

    @staticmethod
    def _reload_editors(ctx) -> None:
        fn = getattr(ctx.win, "reload_changed_files", None) or getattr(ctx.win, "_check_external_changes", None)
        if callable(fn):
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass

    def _build(self, ctx):
        def done(run):
            if run.exit_code == 0:
                dist = sorted((ctx.folder / "dist").glob("*"), key=lambda p: p.stat().st_mtime)[-2:]
                if dist:
                    ctx.log("Built: " + ", ".join(ctx.rel(p) for p in dist))
        ctx.run_cli(["python", "-m", "build"], opens="none", title="python -m build", on_done=_with_hint(ctx, "build",
                                                                                                         done))


# ============================================================================ Jupyter
class Jupyter(Provider):
    id, title, priority = "jupyter", "Jupyter", 30
    icon = ("Ju", "#F37726")
    markers = ("project.radproj",)

    def detect(self, folder, project):
        lang = _language(folder, project).lower()
        if "jupyter" in lang or "notebook" in lang:
            return True
        return bool(self.notebooks(folder, 1))

    @staticmethod
    def notebooks(folder: Path, limit: int = 30) -> list[Path]:
        out = []
        try:
            for p in sorted(folder.iterdir()):
                if p.suffix.lower() == ".ipynb" and p.is_file():
                    out.append(p)
                elif p.is_dir() and p.name in ("notebooks", "nb"):
                    out += sorted(p.glob("*.ipynb"))
                if len(out) >= limit:
                    break
        except OSError:
            pass
        return out[:limit]

    def actions(self, ctx):
        nbs = self.notebooks(ctx.folder)
        items = [Action("new-notebook", "New Notebook...", self._new, opens="none", refresh=True,
                        ask=[Field("name", "File name", default="analysis.ipynb")])]
        if nbs:
            items += [Separator(), Action("all-py", "Convert All Notebooks to Scripts",
                                          lambda c: [self.convert(c, p, "py", open_it=False) for p in nbs] and
                                          c.refresh_tree(), opens="none")]
            for p in nbs:
                rel = ctx.rel(p)
                items.append(Submenu(rel, self.convert_actions(p)))
        return items

    def convert_actions(self, path: Path) -> list:
        return [Action("to-py", "Convert to Python Script", lambda c: self.convert(c, path, "py"), opens="none",
                       tip=f"{path.stem}.py next to the notebook (markdown cells become comments)"),
                Action("to-html", "Convert to HTML", lambda c: self.convert(c, path, "html"), opens="none",
                       tip=f"{path.stem}.html with the outputs")]

    def file_actions(self, ctx, rel_file):
        if rel_file.lower().endswith(".ipynb"):
            return self.convert_actions(ctx.path(rel_file))
        return []

    def convert(self, ctx, path: Path, fmt: str, open_it: bool = True):
        out = path.with_suffix("." + fmt)
        try:
            from ..notebook.model import Notebook
            nb = Notebook.load(path)
            text = nb.to_py() if fmt == "py" else nb.to_html(path.stem)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"*** cannot convert {path.name}: {e}")
            return None
        if out.exists() and open_it and not ctx.confirm(f"Replace {out.name}?"):
            return None
        out.write_text(text, encoding="utf-8")
        ctx.log(f"[notebook] {path.name} -> {ctx.rel(out)}")
        if open_it:
            ctx.refresh_tree()
            ctx.open_file(out)
        return out

    def _new(self, ctx):
        name = str(ctx.values.get("name") or "").strip()
        if not name:
            return
        if not name.lower().endswith(".ipynb"):
            name += ".ipynb"
        target = (ctx.target if ctx.target is not None and ctx.target.is_dir() else ctx.folder) / name
        if target.exists():
            ctx.open_file(target)
            return
        feat = getattr(ctx.win, "notebook_feature", None)
        if feat is not None:
            try:
                feat.new_notebook("blank", target)
                ctx.refresh_tree()
                return
            except Exception as e:  # noqa: BLE001
                ctx.log(f"*** new notebook: {e}")
        try:
            from ..notebook.model import Notebook
            import json
            nb = Notebook.from_py("# %%\n", target)
            target.write_text(json.dumps(nb.to_json(), indent=1), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            ctx.log(f"*** new notebook: {e}")
            return
        ctx.refresh_tree()
        ctx.open_file(target)


# ============================================================================ games (pygame / Arcade / Ursina)
class PythonGame(Provider):
    priority = 55

    def __init__(self, pid: str, title: str, lang: str, package: str, icon):
        self.id, self.title, self.lang, self.package, self.icon = pid, title, lang, package, icon
        self.markers = ("project.radproj", "requirements.txt", "main.py")

    def detect(self, folder, project):
        lang = _language(folder, project)
        if lang:
            return lang == self.lang
        if not _requires(folder, self.package):
            return False
        return True

    def actions(self, ctx):
        items = [Action("run", "Run Game", lambda c: _ide_run(c, None if self._same(c) else
                                                              ["python", self.main_file(c)]),
                        toolbar=True, opens="none", icon="SP_MediaPlay", tip="Run the game (Ctrl+F5)")]
        if self.lang == "pygame":
            items.append(Action("godot", "Export to Godot...", self._godot, opens="none",
                                enabled=lambda c: getattr(c.win, "game_designer", None) is not None and self._same(c),
                                tip="A Godot 4 project next to this one (scenes, art, behaviours)"))
        items += [Separator(), _publish_action(),
                  Action("pyinstaller", "Build One-File EXE (PyInstaller)", self._pyinstaller, opens="none",
                         refresh=True, tip="python -m PyInstaller --onefile --noconsole <main> (into dist/)"),
                  Separator(),
                  Action("install-pkg", f"Install {self.package}", lambda c: c.run_cli(
                      ["python", "-m", "pip", "install", self.package], opens="none",
                      title=f"pip install {self.package}"), opens="none")]
        return items

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder.strip("/") == "" else []

    @staticmethod
    def _same(ctx) -> bool:
        p = ctx.project
        return p is not None and Path(getattr(p, "folder", "")).resolve() == ctx.folder

    def main_file(self, ctx) -> str:
        start = str(getattr(ctx.project, "startup", "") or "") if self._same(ctx) else ""
        for cand in ([f"{start}.py", start] if start else []) + ["main.py", "game.py", "app.py"]:
            if cand and (ctx.folder / cand).is_file():
                return cand
        py = sorted(ctx.folder.glob("*.py"))
        return py[0].name if py else "main.py"

    def _godot(self, ctx):
        gd = getattr(ctx.win, "game_designer", None)
        if gd is None:
            ctx.log("*** the game designer is not loaded")
            return
        out = gd.export_godot()
        if out is not None:
            pg = Path(out) / "project.godot"
            if pg.is_file():
                ctx.open_file(pg)

    def _pyinstaller(self, ctx):
        main = self.main_file(ctx)
        args = ["python", "-m", "PyInstaller", "--noconfirm", "--onefile", "--noconsole", "--name",
                Path(main).stem if not self._same(ctx) else str(getattr(ctx.project, "name", Path(main).stem)), main]
        for d in ("assets", "images", "sounds", "data"):
            if (ctx.folder / d).is_dir():
                args[-1:-1] = ["--add-data", f"{d}{os.pathsep}{d}"]

        def done(run):
            if run.exit_code == 0:
                exe = sorted((ctx.folder / "dist").glob("*.exe" if os.name == "nt" else "*"))
                ctx.log("Built: " + ", ".join(ctx.rel(p) for p in exe) if exe else "Built into dist/")
        ctx.run_cli(args, opens="none", title="PyInstaller", on_done=_with_hint(ctx, "pyinstaller", done))


# ============================================================================ Kivy
class Kivy(Provider):
    id, title, priority = "kivy", "Kivy", 55
    icon = ("Kv", "#2E7D32")
    markers = ("project.radproj", "buildozer.spec", "requirements.txt")

    def detect(self, folder, project):
        lang = _language(folder, project)
        if lang:
            return lang == "kivy"
        return (folder / "buildozer.spec").is_file() or _requires(folder, "kivy")

    def actions(self, ctx):
        spec = ctx.folder / "buildozer.spec"
        same = PythonGame._same(ctx)
        items = [Action("run", "Run App", lambda c: _ide_run(c, None if same else ["python", "main.py"]),
                        toolbar=True, opens="none", icon="SP_MediaPlay", tip="Run the app in a phone-sized window"),
                 Separator()]
        if spec.is_file():
            items.append(Action("open-spec", "Open buildozer.spec", lambda c: c.open_file(spec), opens="none"))
        else:
            items.append(Action("make-spec", "Create buildozer.spec", self._spec,
                                tip="The Android build settings for Buildozer"))
        items += [Action("apk", "Build Android APK (buildozer android debug)", self._apk, opens="none",
                         enabled=lambda c: (c.folder / "buildozer.spec").is_file(),
                         tip="Buildozer runs on Linux: on Windows it runs in WSL"),
                  Separator(), _publish_action(),
                  Action("install-kivy", "Install Kivy", lambda c: c.run_cli(
                      ["python", "-m", "pip", "install", "kivy"], opens="none", title="pip install kivy"), opens="none")]
        return items

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder.strip("/") == "" else []

    def file_actions(self, ctx, rel_file):
        if rel_file == "buildozer.spec":
            return [Action("apk", "Build Android APK (buildozer android debug)", self._apk, opens="none")]
        return []

    def _spec(self, ctx):
        name = str(getattr(ctx.project, "name", "") or ctx.folder.name)
        try:
            from ..mobile.codegen_kivy import buildozer_spec
            text = buildozer_spec(name, re.sub(r"[^a-z0-9]", "", name.lower()) or "app")
        except Exception as e:  # noqa: BLE001
            ctx.log(f"*** buildozer.spec: {e}")
            return
        (ctx.folder / "buildozer.spec").write_text(text, encoding="utf-8")

    def _apk(self, ctx):
        if shutil.which("buildozer"):
            argv = ["buildozer", "android", "debug"]
        elif os.name == "nt" and shutil.which("wsl"):
            argv = ["wsl", "buildozer", "android", "debug"]
            ctx.log("Buildozer runs in WSL (install it there: pip install buildozer; it downloads the Android "
                    "SDK / NDK on the first build).")
        else:
            ctx.log("*** Buildozer is not installed (pip install buildozer - Linux / macOS / WSL)")
            return

        def done(run):
            if run.exit_code == 0:
                apks = sorted((ctx.folder / "bin").glob("*.apk"))
                if apks:
                    ctx.log("Built: " + ", ".join(ctx.rel(p) for p in apks))
        ctx.run_cli(argv, opens="none", title="buildozer android debug", on_done=done)


DJANGO, FLASK, FASTAPI = Django(), Flask(), FastAPI()
PROVIDERS = [DJANGO, FLASK, FASTAPI, Python(), Jupyter(),
             PythonGame("pygame", "pygame", "pygame", "pygame", ("pg", "#4E8F2F")),
             PythonGame("arcade", "Arcade", "python-arcade", "arcade", ("Ar", "#7B3FBF")),
             PythonGame("ursina", "Ursina", "python-ursina", "ursina", ("Ur", "#C2185B")),
             Kivy()]
