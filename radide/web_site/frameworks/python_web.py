"""Python web frameworks (Django, Flask, FastAPI) - the parts they share.

A Python web site is a website project (``"kind": "website"``) whose language is ``python-django``,
``python-flask`` or ``python-fastapi``. It has its **own virtual environment** in ``<project>/.venv``
(created with the framework's packages when the project is made, or by the first run).

- :class:`Framework` - what differs per framework: files of a new project, the dev-server command,
  the runtime introspection script, the static (no-run) index, management commands.
- :class:`PyWebPlugin` - the language plugin (``WebSitePlugin``): the DevServer runs
  ``manage.py runserver`` / ``flask run`` / ``uvicorn`` with the framework's own reloader; every time the
  server (re)starts after a code change the Preview reloads (``ready_marker``).
- **Index** (:func:`project_index`) - url names, template names, models and fields, settings, static files,
  routes and template context variables, read from the project: statically (regex / ast, always
  available) and dynamically (a script run in the project's venv imports the app and asks the framework:
  Django ``get_resolver()`` / ``apps.get_models()``, Flask ``app.url_map``, FastAPI ``app.routes``).
- **IntelliSense** (:func:`complete`, :func:`definition`) used by ``radide/features/python_web.py`` in
  Monaco: url names in ``reverse()`` / ``{% url %}`` / ``url_for()``, templates in ``render()`` /
  ``extends`` / ``include``, model field lookups after ``objects.filter(``, ``settings.``, static files,
  Django / Jinja template tags, filters and variables; F12 on url / template / static names.
- **Debugging** (:func:`start_debug`) - the server runs under debugpy (``--listen --wait-for-client``,
  the IDE's own debugpy, nothing installed into the project) and the IDE's debugpy adapter attaches over
  DAP: breakpoints in views / routes (and Django / Jinja templates) are hit by requests from the Preview.
"""
from __future__ import annotations

import ast
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..project import SiteTemplate, WebSitePlugin, register_template

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SKIP_DIRS = {".venv", "venv", "env", ".git", "__pycache__", "node_modules", ".radide", ".radide_backup",
             ".radide_deleted", ".idea", ".vscode", "staticfiles", ".mypy_cache", ".pytest_cache", "site-packages",
             "migrations"}
TEMPLATE_EXT = (".html", ".htm", ".jinja", ".jinja2", ".j2", ".txt", ".xml", ".email")
PY_KEYWORDS = ["False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue",
               "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in",
               "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"]
Log = Callable[[str], None]

# Monaco CompletionItemKind
K_METHOD, K_FUNCTION, K_FIELD, K_VARIABLE, K_CLASS, K_MODULE, K_PROPERTY = 0, 1, 3, 4, 5, 8, 9
K_VALUE, K_CONSTANT, K_KEYWORD, K_FILE, K_REFERENCE, K_FOLDER, K_SNIPPET = 13, 14, 17, 20, 21, 23, 27


# ============================================================================ venv
def venv_dir(folder) -> Path:
    return Path(folder) / ".venv"


def venv_python(folder) -> str:
    """python of <folder>/.venv ("" when there is none)."""
    for rel in (("Scripts", "python.exe"), ("bin", "python")):
        p = venv_dir(folder).joinpath(*rel)
        if p.is_file():
            return str(p)
    return ""


def site_packages(folder) -> Path | None:
    v = venv_dir(folder)
    win = v / "Lib" / "site-packages"
    if win.is_dir():
        return win
    found = sorted(v.glob("lib/python*/site-packages"))
    return found[0] if found else None


def has_package(folder, package: str) -> bool:
    sp = site_packages(folder)
    return bool(sp) and (sp / package).is_dir()


def base_python(configured: str = "") -> str:
    """A real Python (not a venv, not the Windows Store stub) to create project venvs with."""
    if configured and Path(configured).is_file() and "WindowsApps" not in configured:
        return configured
    base = getattr(sys, "_base_executable", "") or ""
    if base and Path(base).is_file() and "WindowsApps" not in base:
        return base
    for n in ("python", "python3", "py"):
        p = shutil.which(n)
        if p and "WindowsApps" not in p:
            return p
    return sys.executable


def run_logged(argv: list[str], cwd, log: Log, env: dict | None = None, timeout: float = 900) -> int:
    """Run a command, streaming its output lines to *log*; returns the exit code (-1 = not started)."""
    log("> " + " ".join(f'"{a}"' if " " in str(a) else str(a) for a in argv))
    full = dict(os.environ)
    full.update({"PYTHONUNBUFFERED": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    full.update(env or {})
    try:
        p = subprocess.Popen([str(a) for a in argv], cwd=str(cwd), env=full, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except OSError as e:
        log(f"*** cannot run {argv[0]}: {e}")
        return -1
    deadline = time.monotonic() + timeout
    for raw in iter(p.stdout.readline, b""):
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            log(line)
        if time.monotonic() > deadline:
            p.kill()
            log("*** timed out")
            break
    return p.wait()


def create_venv(folder, log: Log, python: str = "", requirements: str = "requirements.txt") -> str:
    """Create <folder>/.venv (when missing) and pip install the requirements; returns the venv python."""
    folder = Path(folder)
    py = venv_python(folder)
    if not py:
        base = base_python(python)
        log(f"Creating the project's virtual environment (.venv) with {base} ...")
        if run_logged([base, "-m", "venv", str(venv_dir(folder))], folder, log, timeout=300) != 0:
            raise RuntimeError("python -m venv failed (see the log)")
        py = venv_python(folder)
        if not py:
            raise RuntimeError("the virtual environment has no python")
    req = folder / requirements
    if req.is_file():
        log("Installing packages (pip install -r requirements.txt) ...")
        if run_logged([py, "-m", "pip", "install", "-r", str(req), "--disable-pip-version-check"], folder, log) != 0:
            raise RuntimeError("pip install failed - check the internet connection (see the log)")
    return py


def write_files(folder: Path, files: dict[str, str], overwrite: bool = False) -> None:
    for rel, text in files.items():
        p = Path(folder) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if overwrite or not p.exists():
            p.write_text(text, encoding="utf-8", newline="\n")


def new_secret() -> str:
    return "django-insecure-" + secrets.token_urlsafe(40)


def free_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


# ============================================================================ framework base
@dataclass
class Command:
    """A management command of the framework panel."""
    id: str
    title: str
    argv: list[str]                  # after the venv python; {name} etc. filled by the panel
    tip: str = ""
    ask: list[str] = field(default_factory=list)     # values asked first ("name", "username", ...)
    terminal: bool = False           # interactive: run in the Terminal (shell)


class Framework:
    id = ""
    title = ""
    plugin_id = ""
    package = ""                     # folder in site-packages that proves the framework is installed
    template_lang = "jinja-html"     # Monaco language of its templates
    ready_marker = ""                # regex: printed each time the server has (re)started
    log_filter = ""                  # regex: request-log lines not copied to the Output window
    default_app = ""
    url_label = "URL names"
    # "framework": the framework's own auto-reloader (runserver / flask --debug) + Preview reload when it is
    # up again; "ide": the IDE restarts the server after a .py change (web.reload overrides it)
    reload_mode = "framework"

    def reload(self, cfg: dict) -> str:
        mode = str((cfg or {}).get("reload") or self.reload_mode)
        return mode if mode in ("framework", "ide", "off") else self.reload_mode

    # ---- new project
    def requirements(self) -> list[str]:
        return []

    def create(self, folder: Path, name: str, log: Log, python: str = "") -> dict:
        """Write the files, create the venv, run the framework's generators. Returns web-block overrides."""
        raise NotImplementedError

    # ---- dev server
    def server_args(self, folder: Path, cfg: dict, debug: bool) -> list[str]:
        """argv after the venv python ("{port}" = the backend port)."""
        raise NotImplementedError

    def server_env(self, folder: Path, cfg: dict) -> dict:
        return {}

    def prepare(self, folder: Path, cfg: dict, py: str) -> list[list[str]]:
        """Extra commands run before the server (e.g. Django's first migrate)."""
        return []

    # ---- introspection
    def runtime_script(self, folder: Path, cfg: dict) -> str:
        return ""

    def static_index(self, folder: Path, cfg: dict) -> dict:
        return {}

    # ---- management panel
    def commands(self, folder: Path, cfg: dict) -> list[Command]:
        return []


# ============================================================================ plugin
class PyWebPlugin(WebSitePlugin):
    """Base of python-django / python-flask / python-fastapi."""
    framework: Framework = Framework()
    code_ext = ".py"
    web_kind = "python"
    needs_interpreter = True
    supports_debug = True
    interpreter_names = ["python", "python3", "py"]
    keywords = PY_KEYWORDS
    builtins = ("print len range str int float list dict set tuple open isinstance super property staticmethod "
                "classmethod enumerate zip sorted min max sum any all abs getattr setattr hasattr type").split()
    line_comments = ["#"]
    block_comment = None
    string_quotes = ['"', "'"]

    def __init__(self):
        from ...languages.base import PackageManager
        # pip of the project's .venv (Manage Packages: radide/features/packages.py treats "python*" ids so)
        self.package_manager = PackageManager(
            "pip", "{interpreter}",
            list_cmd=["{interpreter}", "-m", "pip", "list", "--format=freeze", "--disable-pip-version-check"],
            search_cmd=["{interpreter}", "-m", "pip", "index", "versions", "{query}", "--disable-pip-version-check"],
            install_cmd=["{interpreter}", "-m", "pip", "install", "{name}=={version}", "--disable-pip-version-check"],
            uninstall_cmd=["{interpreter}", "-m", "pip", "uninstall", "-y", "{name}"],
            manifest="requirements.txt", search_url="https://pypi.org/search/?q={query}")

    def find_interpreter(self, configured: str = "") -> str:
        return base_python(configured)

    def tool(self) -> str:
        return self.find_interpreter("")

    def module_template(self, name: str) -> str:
        return f'"""{name}.py"""\n'

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*(async\s+)?def\s+{re.escape(name)}\b")

    def completions(self, code, line, col, path, names=None):
        from ...languages.base import Completion
        out = [Completion(k, "keyword") for k in self.keywords] + [Completion(b, "function") for b in self.builtins]
        seen = {c.name for c in out}
        for w in re.findall(r"[A-Za-z_]\w{2,}", code):
            if w not in seen:
                seen.add(w)
                out.append(Completion(w, "variable"))
        return out

    # ---- dev server (radide/web_site/server.py)
    def backend(self, server) -> dict:
        fw = self.framework
        folder = Path(server.folder)
        cfg = dict(server.config)
        py = venv_python(folder) or str(venv_dir(folder) / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        debug = bool(getattr(server, "_pyweb_debug", False))
        prepare = []
        if not venv_python(folder):
            prepare.append([base_python(server.interpreter), "-m", "venv", str(venv_dir(folder))])
        if (not venv_python(folder) or (fw.package and not has_package(folder, fw.package))) and \
                (folder / "requirements.txt").is_file():
            prepare.append([py, "-m", "pip", "install", "-r", "requirements.txt", "--disable-pip-version-check"])
        prepare += fw.prepare(folder, cfg, py)
        env = {"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
        env.update(fw.server_env(folder, cfg))
        argv = [py] + fw.server_args(folder, cfg, debug)
        if fw.reload(cfg) == "framework":
            _hook_reload(server, fw)
        elif fw.reload(cfg) == "ide":
            _watch_python(server)
        spec = {"argv": argv, "cwd": folder, "env": env, "prepare": prepare, "timeout": 120 if debug else 60}
        if fw.log_filter:
            spec["log_filter"] = fw.log_filter
        return spec

    def debug_backend(self, server, spec: dict, port: int) -> dict:
        """Debug runs: the server under debugpy (listen + wait for the IDE), no auto-reloader."""
        import debugpy
        server._pyweb_debug = True
        fw = self.framework
        folder = Path(server.folder)
        cfg = dict(server.config)
        argv = list(spec["argv"])
        py = argv[0]
        args = fw.server_args(folder, cfg, True)
        dbg = [py, "-Xfrozen_modules=off", str(Path(debugpy.__file__).parent), "--listen", f"127.0.0.1:{port}",
               "--wait-for-client", "--configure-subProcess", "False"]
        env = {**(spec.get("env") or {}), "PYDEVD_DISABLE_FILE_VALIDATION": "1"}
        return {**spec, "argv": dbg + args, "env": env, "timeout": 600, "restart_on_change": False}

    def start_debug(self, win, project, path=None):
        """F5 (radide/web_site/debug.py calls it): run the site under debugpy and attach."""
        return start_debug(win, project, path)


def _hook_reload(server, fw: Framework) -> None:
    """After a code change the framework's reloader restarts the app; when it prints its ready line again
    the Preview reloads (the first ready line is the normal start)."""
    if getattr(server, "_pyweb_hooked", False) or not fw.ready_marker:
        return
    server._pyweb_hooked = True
    rx = re.compile(fw.ready_marker)
    state = {"seen": 0}

    def on_log(text: str):
        if rx.search(text or ""):
            state["seen"] += 1
            if state["seen"] > 1:
                server.notify_change(["(python server reloaded)"])
    server.log.connect(on_log)


def _watch_python(server) -> None:
    """reload mode "ide": restart the site's server when a .py file of the project changes (not while
    debugging - the debug session restarts itself, see _watch_code)."""
    if getattr(server, "_pyweb_watching", False):
        return
    server._pyweb_watching = True
    folder = Path(server.folder)

    def loop():
        sig = _code_signature(folder)
        while server.running:
            time.sleep(0.7)
            if getattr(server, "_pyweb_debug", False):
                continue
            new = _code_signature(folder)
            if new != sig:
                sig = new
                try:
                    server.log.emit("Python code changed - restarting the server...")
                except RuntimeError:
                    return
                server.restart_backend()
    threading.Thread(target=loop, daemon=True, name="radide-pyweb-watch").start()


# ============================================================================ templates (New Project)
def register_framework_template(fw: Framework, template_id: str, title: str, description: str,
                                order: int = 10, icon: str = "SP_ComputerIcon") -> None:
    def create(folder: Path, name: str) -> dict:
        def work(log):
            return fw.create(Path(folder), name, log)
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None and isinstance(app, QApplication) and \
                    os.environ.get("RADIDE_PYWEB_NO_PROGRESS") != "1":
                from ...features.app_gallery import run_with_progress
                parent = QApplication.activeWindow()
                return run_with_progress(parent, f"Creating {title}", work)
        except ImportError:
            pass
        return work(lambda s: print(s, flush=True))
    register_template(SiteTemplate(template_id, title, description, (fw.plugin_id,), create, order, icon,
                                   {"category": "Python", "heavy": True, "framework": fw.id}))


# ============================================================================ project helpers
def project_language(folder) -> str:
    try:
        data = json.loads((Path(folder) / "project.radproj").read_text(encoding="utf-8"))
        return str(data.get("language", ""))
    except (OSError, ValueError):
        return ""


def web_block(folder) -> dict:
    try:
        data = json.loads((Path(folder) / "project.radproj").read_text(encoding="utf-8"))
        web = data.get("web") or {}
        return web if isinstance(web, dict) else {}
    except (OSError, ValueError):
        return {}


def framework_for(plugin_id: str) -> Framework | None:
    try:
        from ...languages import get_plugin
        fw = getattr(get_plugin(plugin_id), "framework", None)
        return fw if isinstance(fw, Framework) and fw.id else None
    except KeyError:
        return None


def project_root_of(path) -> Path | None:
    """The Python web project that contains *path* (nearest project.radproj upwards), or None."""
    try:
        p = Path(path).resolve()
    except OSError:
        return None
    for d in [p] + list(p.parents):
        if (d / "project.radproj").is_file():
            return d if project_language(d).startswith("python-") and framework_for(project_language(d)) else None
    return None


def walk_files(folder, exts: tuple[str, ...] | None = None, limit: int = 20000):
    folder = Path(folder)
    n = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if exts is None or f.lower().endswith(exts):
                yield Path(dirpath) / f
                n += 1
                if n >= limit:
                    return


def template_dirs(folder) -> list[Path]:
    out = []
    for dirpath, dirnames, _files in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        if Path(dirpath).name == "templates":
            out.append(Path(dirpath))
            dirnames[:] = []
    return out


def static_dirs(folder) -> list[Path]:
    out = []
    for dirpath, dirnames, _files in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") and d != "templates"]
        if Path(dirpath).name == "static":
            out.append(Path(dirpath))
            dirnames[:] = []
    return out


def list_templates(folder) -> list[dict]:
    out, seen = [], set()
    for d in template_dirs(folder):
        for p in walk_files(d, TEMPLATE_EXT, 5000):
            name = p.relative_to(d).as_posix()
            if name not in seen:
                seen.add(name)
                out.append({"name": name, "file": str(p)})
    return out


def list_static(folder) -> list[dict]:
    out, seen = [], set()
    for d in static_dirs(folder):
        for p in walk_files(d, None, 5000):
            name = p.relative_to(d).as_posix()
            if name not in seen:
                seen.add(name)
                out.append({"name": name, "file": str(p)})
    return out


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def template_context(folder) -> dict[str, dict[str, dict]]:
    """template name -> {variable: {"model": Model or "", "many": bool}} from the views (ast):
    render(request, "t.html", {...}) / render_template("t.html", a=...) / TemplateResponse(...),
    and Django class-based views (template_name / model / context_object_name)."""
    out: dict[str, dict[str, dict]] = {}

    def model_of(node) -> tuple[str, bool]:
        """Post.objects.filter(...) -> ("Post", True); get_object_or_404(Post, ...) -> ("Post", False)."""
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in ("get_object_or_404",) and node.args and \
                    isinstance(node.args[0], ast.Name):
                return node.args[0].id, False
            if isinstance(f, ast.Name) and f.id in ("get_list_or_404",) and node.args and \
                    isinstance(node.args[0], ast.Name):
                return node.args[0].id, True
            if isinstance(f, ast.Attribute):
                many = f.attr not in ("get", "first", "last", "create", "get_or_create", "latest", "earliest")
                cur = f.value
                while isinstance(cur, (ast.Call, ast.Attribute)):
                    if isinstance(cur, ast.Attribute) and cur.attr == "objects" and isinstance(cur.value, ast.Name):
                        return cur.value.id, many
                    if isinstance(cur, ast.Attribute) and cur.attr == "query" and isinstance(cur.value, ast.Name):
                        return cur.value.id, many         # Flask-SQLAlchemy Model.query.all()
                    cur = cur.func if isinstance(cur, ast.Call) else cur.value
        return "", False

    for p in walk_files(folder, (".py",), 3000):
        text = _read(p)
        if "render" not in text and "template" not in text.lower():
            continue
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            continue
        app = p.parent.name
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            local: dict[str, tuple[str, bool]] = {}
            if isinstance(fn, ast.ClassDef):
                attrs = {}
                for st in fn.body:
                    if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                        attrs[st.targets[0].id] = st.value
                bases = " ".join(ast.unparse(b) for b in fn.bases)
                model = attrs.get("model")
                model = model.id if isinstance(model, ast.Name) else ""
                if not model and isinstance(attrs.get("queryset"), ast.Call):
                    model = model_of(attrs["queryset"])[0]
                tpl = attrs.get("template_name")
                tpl = tpl.value if isinstance(tpl, ast.Constant) and isinstance(tpl.value, str) else ""
                con = attrs.get("context_object_name")
                con = con.value if isinstance(con, ast.Constant) and isinstance(con.value, str) else ""
                kind = next((k for k in ("ListView", "DetailView", "UpdateView", "CreateView", "DeleteView",
                                         "FormView", "TemplateView") if k in bases), "")
                if not kind:
                    continue
                if not tpl and model:
                    tpl = f"{app}/{model.lower()}" + {"ListView": "_list", "DetailView": "_detail",
                                                       "UpdateView": "_form", "CreateView": "_form",
                                                       "DeleteView": "_confirm_delete"}.get(kind, "") + ".html"
                if not tpl:
                    continue
                vars_ = out.setdefault(tpl, {})
                if kind == "ListView":
                    for v in ("object_list", f"{model.lower()}_list" if model else "", con):
                        if v:
                            vars_[v] = {"model": model, "many": True}
                    for v in ("page_obj", "paginator", "is_paginated"):
                        vars_[v] = {"model": "", "many": False}
                elif kind in ("DetailView", "UpdateView", "DeleteView"):
                    for v in ("object", model.lower() if model else "", con):
                        if v:
                            vars_[v] = {"model": model, "many": False}
                if kind in ("UpdateView", "CreateView", "FormView"):
                    vars_["form"] = {"model": "", "many": False}
                vars_["view"] = {"model": "", "many": False}
                continue
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                    m = model_of(st.value)
                    if m[0]:
                        local[st.targets[0].id] = m
            for call in ast.walk(fn):
                if not isinstance(call, ast.Call):
                    continue
                f = call.func
                fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
                if fname not in ("render", "render_template", "TemplateResponse", "render_to_string",
                                 "render_to_response"):
                    continue
                args = list(call.args)
                tpl_node = None
                for a in args[:3]:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str) and "." in a.value:
                        tpl_node = a
                        break
                for kw in call.keywords:
                    if kw.arg in ("name", "template_name") and isinstance(kw.value, ast.Constant):
                        tpl_node = kw.value
                if tpl_node is None:
                    continue
                vars_ = out.setdefault(tpl_node.value, {})
                ctx = None
                after = args[args.index(tpl_node) + 1:] if tpl_node in args else []
                for a in after:
                    if isinstance(a, ast.Dict):
                        ctx = a
                for kw in call.keywords:
                    if kw.arg in ("context",) and isinstance(kw.value, ast.Dict):
                        ctx = kw.value
                    elif kw.arg and kw.arg not in ("name", "template_name", "request", "status_code", "headers",
                                                   "context", "status", "content_type", "using"):
                        m = model_of(kw.value) if not isinstance(kw.value, ast.Name) else local.get(kw.value.id,
                                                                                                    ("", False))
                        vars_[kw.arg] = {"model": m[0], "many": m[1]}
                if isinstance(ctx, ast.Dict):
                    for k, v in zip(ctx.keys, ctx.values):
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            m = model_of(v) if not isinstance(v, ast.Name) else local.get(v.id, ("", False))
                            vars_[k.value] = {"model": m[0], "many": m[1]}
    return out


# ============================================================================ index (static + runtime)
class _IndexState:
    def __init__(self, folder: Path, fw: Framework):
        self.folder = folder
        self.fw = fw
        self.static: dict = {}
        self.static_time = 0.0
        self.static_sig = None
        self.runtime: dict = {}
        self.runtime_sig = None
        self.runtime_running = False
        self.runtime_time = 0.0
        self.runtime_error = ""
        self.lock = threading.Lock()
        cache = folder / ".radide" / "pyweb_index.json"
        try:
            self.runtime = json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.runtime = {}


_STATES: dict[str, _IndexState] = {}
RUNTIME_MARK = "@@RADIDE-PYWEB@@"


def _signature(folder: Path) -> tuple:
    n, newest = 0, 0.0
    for p in walk_files(folder, (".py",) + TEMPLATE_EXT, 8000):
        try:
            newest = max(newest, p.stat().st_mtime)
        except OSError:
            pass
        n += 1
    return n, newest


def _state(folder, fw: Framework) -> _IndexState:
    key = str(Path(folder).resolve()).lower()
    st = _STATES.get(key)
    if st is None or st.fw is not fw:
        st = _IndexState(Path(folder).resolve(), fw)
        _STATES[key] = st
    return st


def run_runtime_index(folder, fw: Framework, timeout: float = 60) -> dict:
    """Run the framework's introspection script in the project's venv (blocking). {} + "error" on failure."""
    folder = Path(folder)
    py = venv_python(folder)
    if not py:
        return {"error": "the project has no .venv yet"}
    cfg = web_block(folder)
    script = fw.runtime_script(folder, cfg)
    if not script:
        return {}
    env = dict(os.environ)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(fw.server_env(folder, cfg))
    try:
        r = subprocess.run([py, "-c", script], cwd=str(folder), env=env, capture_output=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"error": str(e)}
    out = r.stdout.decode("utf-8", "replace")
    i = out.rfind(RUNTIME_MARK)
    if i < 0:
        err = r.stderr.decode("utf-8", "replace").strip().splitlines()
        return {"error": (err[-1] if err else f"exit code {r.returncode}")}
    try:
        data = json.loads(out[i + len(RUNTIME_MARK):].strip())
    except ValueError as e:
        return {"error": f"bad introspection output: {e}"}
    return data if isinstance(data, dict) else {}


def refresh_runtime(folder, fw: Framework, wait: bool = False, on_done: Callable | None = None) -> None:
    """(Re)read the runtime index in a background thread (wait=True: block until done)."""
    st = _state(folder, fw)
    with st.lock:
        if st.runtime_running:
            if not wait:
                return
        st.runtime_running = True

    def work():
        sig = _signature(st.folder)
        data = run_runtime_index(st.folder, fw)
        with st.lock:
            st.runtime_running = False
            st.runtime_time = time.time()
            st.runtime_sig = sig
            if data and not data.get("error"):
                st.runtime = data
                st.runtime_error = ""
                try:
                    cache = st.folder / ".radide" / "pyweb_index.json"
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(json.dumps(data), encoding="utf-8")
                except OSError:
                    pass
            else:
                st.runtime_error = (data or {}).get("error", "")
        if on_done is not None:
            try:
                on_done(st.runtime, st.runtime_error)
            except Exception:  # noqa: BLE001
                pass
    if wait:
        work()
    else:
        threading.Thread(target=work, daemon=True, name="radide-pyweb-index").start()


def project_index(folder, fw: Framework | None = None, refresh: bool = True) -> dict:
    """The merged index of a project (static parse, refreshed when files change, plus the last runtime
    introspection - started in the background when the code changed)."""
    folder = Path(folder).resolve()
    fw = fw or framework_for(project_language(folder))
    if fw is None:
        return {}
    st = _state(folder, fw)
    now = time.time()
    if now - st.static_time > 2.0 or not st.static:
        sig = _signature(folder)
        if sig != st.static_sig or not st.static:
            cfg = web_block(folder)
            data = {"templates": list_templates(folder), "static": list_static(folder), "urls": [], "models": {},
                    "settings": [], "routes": [], "context": {}}
            try:
                data.update({k: v for k, v in fw.static_index(folder, cfg).items() if v is not None})
            except Exception as e:  # noqa: BLE001 - a parse error must not break IntelliSense
                data["error"] = str(e)
            try:
                data["context"] = template_context(folder)
            except Exception:  # noqa: BLE001
                data["context"] = {}
            st.static, st.static_sig = data, sig
        st.static_time = now
        if refresh and venv_python(folder) and st.static_sig != st.runtime_sig and \
                now - st.runtime_time > 4.0 and not st.runtime_running:
            refresh_runtime(folder, fw)
    return merge(st.static, st.runtime)


def merge(static: dict, runtime: dict) -> dict:
    out = dict(static)
    if not runtime:
        return out
    # url names: runtime is complete (admin, includes); keep the static declaration line for F12
    decl = {u["name"]: u for u in static.get("urls", [])}
    short = {}
    for u in static.get("urls", []):
        short.setdefault(u["name"].split(":")[-1], u)
    urls = []
    for u in runtime.get("urls", []):
        s = decl.get(u["name"]) or short.get(u["name"].split(":")[-1])
        u = dict(u)
        if s is not None:
            u["decl_file"], u["decl_line"] = s.get("file"), s.get("line")
        urls.append(u)
    names = {u["name"] for u in urls}
    urls += [u for u in static.get("urls", []) if u["name"] not in names]
    urls.sort(key=lambda u: 0 if u.get("decl_file") or (u.get("file") and "site-packages" not in str(u["file"]))
              else 1)                                   # the project's own names before admin:... / docs
    out["urls"] = urls
    for key in ("templates", "static", "routes", "settings"):
        have = {x["name"] if isinstance(x, dict) else x for x in out.get(key, [])}
        extra = [x for x in runtime.get(key, []) if (x["name"] if isinstance(x, dict) else x) not in have]
        out[key] = list(out.get(key, [])) + extra
    models = dict(static.get("models", {}))
    for name, m in (runtime.get("models") or {}).items():
        models[name] = {**models.get(name, {}), **m}
    out["models"] = models
    out["runtime"] = True
    return out


def index_status(folder, fw: Framework | None = None) -> str:
    fw = fw or framework_for(project_language(folder))
    if fw is None:
        return ""
    st = _state(folder, fw)
    if st.runtime_running:
        return "reading the project..."
    if st.runtime_error:
        return f"runtime index: {st.runtime_error} (static index used)"
    if st.runtime:
        return "index from the running framework + source"
    return "index from the source code"


# ============================================================================ template language data
DJANGO_TAGS = {
    "autoescape": "autoescape on|off ... endautoescape", "block": "block name ... endblock",
    "comment": "comment ... endcomment", "csrf_token": "CSRF protection field for forms", "cycle": "cycle 'a' 'b'",
    "debug": "debugging information", "extends": "extends 'base.html' - parent template",
    "filter": "filter lower|... endfilter", "firstof": "first true variable", "for": "for item in items ... endfor",
    "empty": "inside for: no items", "if": "if condition ... endif", "elif": "elif condition", "else": "else",
    "ifchanged": "ifchanged ... endifchanged", "include": "include 'part.html' with x=y",
    "load": "load static humanize ...", "lorem": "lorem ipsum text", "now": "now 'Y-m-d'",
    "regroup": "regroup list by attr as name", "resetcycle": "reset a cycle", "spaceless": "spaceless ... endspaceless",
    "templatetag": "output {% etc.", "url": "url 'name' arg1 arg2 - reverse a URL name",
    "verbatim": "verbatim ... endverbatim", "widthratio": "widthratio value max width", "with": "with a=b ... endwith",
    "static": "static 'css/site.css' - URL of a static file (load static)", "get_static_prefix": "STATIC_URL",
    "csrf_input": "", "translate": "translate 'text' (load i18n)", "blocktranslate": "blocktranslate ... endblocktranslate",
    "trans": "trans 'text' (load i18n)", "blocktrans": "blocktrans ... endblocktrans",
    "endblock": "", "endfor": "", "endif": "", "endwith": "", "endautoescape": "", "endcomment": "", "endfilter": "",
    "endifchanged": "", "endspaceless": "", "endverbatim": "", "endblocktranslate": "", "endblocktrans": "",
}
DJANGO_FILTERS = ("add addslashes capfirst center cut date default default_if_none dictsort dictsortreversed "
                  "divisibleby escape escapejs escapeseq filesizeformat first floatformat force_escape get_digit "
                  "iriencode join json_script last length linebreaks linebreaksbr linenumbers ljust lower make_list "
                  "phone2numeric pluralize pprint random rjust safe safeseq slice slugify stringformat striptags "
                  "time timesince timeuntil title truncatechars truncatechars_html truncatewords "
                  "truncatewords_html unordered_list upper urlencode urlize urlizetrunc wordcount wordwrap yesno "
                  "intcomma intword naturalday naturaltime apnumber ordinal").split()
DJANGO_LIBRARIES = ["static", "humanize", "i18n", "l10n", "tz", "cache"]
DJANGO_GLOBALS = {"request": "HttpRequest", "user": "the logged-in user (auth)", "perms": "permissions",
                  "messages": "django.contrib.messages", "csrf_token": "CSRF token", "debug": "settings.DEBUG",
                  "MEDIA_URL": "", "STATIC_URL": ""}
JINJA_TAGS = {
    "block": "block name ... endblock", "extends": "extends 'base.html'", "include": "include 'part.html'",
    "import": "import 'macros.html' as m", "from": "from 'macros.html' import x", "macro": "macro name(args) ... endmacro",
    "call": "call macro() ... endcall", "filter": "filter upper ... endfilter", "set": "set x = value",
    "for": "for item in items ... endfor", "if": "if condition ... endif", "elif": "elif condition", "else": "else",
    "with": "with ... endwith", "raw": "raw ... endraw", "autoescape": "autoescape true ... endautoescape",
    "trans": "trans ... endtrans", "break": "loop controls", "continue": "loop controls",
    "endblock": "", "endfor": "", "endif": "", "endmacro": "", "endcall": "", "endfilter": "", "endset": "",
    "endwith": "", "endraw": "", "endautoescape": "", "endtrans": "",
}
JINJA_FILTERS = ("abs attr batch capitalize center count d default dictsort e escape filesizeformat first float "
                 "forceescape format groupby indent int items join last length list lower map max min pprint "
                 "random reject rejectattr replace reverse round safe select selectattr slice sort string striptags "
                 "sum title tojson trim truncate unique upper urlencode urlize wordcount wordwrap xmlattr").split()
JINJA_GLOBALS = {"url_for": "url_for('endpoint', **values)", "request": "the current request",
                 "session": "the session", "g": "flask.g", "config": "app.config",
                 "get_flashed_messages": "get_flashed_messages(with_categories=False)", "range": "range()",
                 "loop": "inside for: loop.index, loop.first ...", "self": "blocks of this template"}
ATTRS = {
    "forloop": "counter counter0 revcounter revcounter0 first last parentloop".split(),
    "loop": "index index0 revindex revindex0 first last length cycle depth previtem nextitem changed".split(),
    "request": "user path method GET POST COOKIES FILES META session headers scheme body get_full_path "
               "build_absolute_uri is_secure args form values json url base_url endpoint host query_params "
               "path_params cookies".split(),
    "user": "username email first_name last_name is_authenticated is_anonymous is_staff is_superuser is_active "
            "date_joined last_login get_full_name get_short_name pk id".split(),
    "block": ["super"],
    "page_obj": "number has_next has_previous next_page_number previous_page_number paginator object_list "
                "start_index end_index".split(),
    "form": "as_p as_div as_table as_ul errors non_field_errors fields is_bound hidden_fields visible_fields "
            "media".split(),
}
LOOKUPS = ("exact iexact contains icontains in gt gte lt lte startswith istartswith endswith iendswith range "
           "isnull regex iregex date year month day week week_day quarter time hour minute second").split()
QS_METHODS_KW = ("filter", "exclude", "get", "get_or_create", "update_or_create", "create", "update", "count")
QS_METHODS_STR = ("order_by", "values", "values_list", "only", "defer", "select_related", "prefetch_related",
                  "distinct", "annotate", "aggregate")


# ============================================================================ completion engine
def _item(label, kind, detail="", insert=None, rng=None, sort=None, filt=None, doc="") -> dict:
    d = {"label": label, "kind": kind, "detail": detail}
    if insert is not None:
        d["insertText"] = insert
    if rng is not None:
        d["range"] = rng
    if sort:
        d["sortText"] = sort
    if filt:
        d["filterText"] = filt
    if doc:
        d["documentation"] = doc
    return d


def _open_tag(before: str, opener: str, closer: str) -> int:
    """Index in *before* of the last *opener* that is not closed yet (-1 = none)."""
    i = before.rfind(opener)
    if i < 0 or before.find(closer, i + len(opener)) >= 0:
        return -1
    return i


def _string_prefix(before: str) -> tuple[str, int, str] | None:
    """Inside an unclosed string on this line: (quote, start column of the content, content so far)."""
    quote, start = None, -1
    i = 0
    while i < len(before):
        ch = before[i]
        if quote is None:
            if ch in "'\"":
                quote, start = ch, i + 1
        elif ch == "\\":
            i += 1
        elif ch == quote:
            quote = None
        i += 1
    if quote is None:
        return None
    return quote, start, before[start:]


def is_template(path, folder=None) -> bool:
    p = Path(path)
    return p.suffix.lower() in TEMPLATE_EXT and "templates" in {x.lower() for x in p.parts}


def template_name_of(path, idx: dict) -> str:
    sp = str(Path(path).resolve()).lower()
    for t in idx.get("templates", []):
        if str(Path(t["file"]).resolve()).lower() == sp:
            return t["name"]
    parts = Path(path).parts
    low = [x.lower() for x in parts]
    if "templates" in low:
        i = len(low) - 1 - low[::-1].index("templates")
        return "/".join(parts[i + 1:])
    return Path(path).name


def model_fields(idx: dict, model: str) -> list[dict]:
    m = (idx.get("models") or {}).get(model) or {}
    return list(m.get("fields") or [])


def find_model(idx: dict, name: str) -> str:
    models = idx.get("models") or {}
    if name in models:
        return name
    low = name.lower()
    for m in models:
        if m.lower() == low or m.lower() + "s" == low or m.lower() + "_list" == low:
            return m
    return ""


def complete(folder, path, text: str, line: int, col: int, fw: Framework | None = None) -> list[dict]:
    """IntelliSense items for the Python web project at (line, col) (0-based) of *path*."""
    folder = Path(folder)
    fw = fw or framework_for(project_language(folder))
    if fw is None:
        return []
    lines = text.split("\n")
    if line >= len(lines):
        return []
    before = lines[line][:col]
    idx = project_index(folder, fw)
    if is_template(path):
        return _complete_template(fw, idx, path, text, lines, line, col, before)
    if Path(path).suffix.lower() == ".py":
        return _complete_python(fw, idx, text, lines, line, col, before)
    return []


def _names_in_string(items: list[dict], line: int, start: int, col: int, kind: int, detail_fn,
                     doc_fn=None) -> list[dict]:
    rng = [line, start, line, col]
    out = []
    for i, it in enumerate(items):
        name = it["name"] if isinstance(it, dict) else str(it)
        out.append(_item(name, kind, detail_fn(it), insert=name, rng=rng, filt=name, sort=f"0{i:05d}",
                         doc=doc_fn(it) if doc_fn else ""))
    return out


def _url_detail(u: dict) -> str:
    pat = u.get("pattern") or u.get("rule") or u.get("path") or ""
    args = u.get("args") or []
    return (("/" + pat.lstrip("^/").rstrip("$")) if pat else "") + (f"   args: {', '.join(args)}" if args else "")


def _complete_python(fw, idx, text, lines, line, col, before) -> list[dict]:
    s = _string_prefix(before)
    if s is not None:
        quote, start, content = s
        head = before[:start - 1]
        # url names
        if re.search(r"\b(reverse|reverse_lazy|redirect|resolve_url|url_for|url_path_for)\(\s*$", head):
            return _names_in_string(idx.get("urls", []), line, start, col, K_REFERENCE, _url_detail)
        if fw.id == "flask" and re.search(r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*$", head):
            return _names_in_string(idx.get("static", []), line, start, col, K_FILE, lambda _i: "static file")
        # templates
        if re.search(r"\b(render|TemplateResponse)\(\s*\w+\s*,\s*$", head) or \
                re.search(r"\b(render_template|get_template|render_to_string|select_template|TemplateResponse)"
                          r"\(\s*(name\s*=\s*)?$", head) or \
                re.search(r"\btemplate_name\s*=\s*$", head) or re.search(r"\bname\s*=\s*$", head) and \
                "TemplateResponse" in before:
            return _names_in_string(idx.get("templates", []), line, start, col, K_FILE, lambda _i: "template")
        # settings / config keys
        if re.search(r"\b(config|settings)\[\s*$", head) or re.search(r"\bconfig\.get\(\s*$", head):
            return _names_in_string(idx.get("settings", []), line, start, col, K_CONSTANT,
                                    lambda i: str(i.get("value", ""))[:60])
        # order_by('field') ...
        call = _innermost_call(text, lines, line, col)
        if call and call[0] in QS_METHODS_STR and call[1]:
            return _field_items(idx, call[1], content, line, col, as_kwarg=False, prefix_ok="-?")
        return []
    # settings.NAME
    m = re.search(r"\bsettings\.(\w*)$", before)
    if m and fw.id == "django":
        rng = [line, col - len(m.group(1)), line, col]
        return [_item(x["name"], K_CONSTANT, str(x.get("value", ""))[:60], rng=rng)
                for x in idx.get("settings", [])]
    # Model.objects.filter(field__lookup=
    call = _innermost_call(text, lines, line, col)
    if call and (call[0] in QS_METHODS_KW or call[0] in ("get_object_or_404", "get_list_or_404")) and call[1]:
        w = re.search(r"(\w*)$", before).group(1)
        if re.search(r"[=]\s*\w*$", before) and not re.search(r"[,(]\s*\w*$", before):
            return []                                    # typing a value, not a keyword
        return _field_items(idx, call[1], w, line, col, as_kwarg=True)
    return []


def _innermost_call(text: str, lines: list[str], line: int, col: int) -> tuple[str, str] | None:
    """(method name, model name) of the call whose '(' encloses the cursor: Post.objects.filter( -> ("filter",
    "Post"); get_object_or_404(Post, ... -> ("get_object_or_404", "Post")."""
    start = sum(len(x) + 1 for x in lines[:line]) + col
    depth = 0
    i = start - 1
    lo = max(0, start - 2000)
    while i >= lo:
        ch = text[i]
        if ch in ")]}":
            depth += 1
        elif ch in "([{":
            if depth == 0:
                if ch != "(":
                    return None
                head = text[max(0, i - 400):i]
                m = re.search(r"(\w+)\s*$", head)
                if not m:
                    return None
                name = m.group(1)
                if name in ("get_object_or_404", "get_list_or_404"):
                    a = re.match(r"\s*([A-Z]\w*)", text[i + 1:start])
                    return (name, a.group(1)) if a else None
                mm = list(re.finditer(r"\b([A-Z]\w*)\s*\.\s*objects\b", head))
                if mm:
                    return name, mm[-1].group(1)
                mm = list(re.finditer(r"\b(?:self\.)?model\s*=\s*([A-Z]\w*)", text[:i]))
                if "self.get_queryset()" in head or "super().get_queryset()" in head:
                    return (name, mm[-1].group(1)) if mm else None
                return None
            depth -= 1
        i -= 1
    return None


def _field_items(idx, model, typed: str, line: int, col: int, as_kwarg: bool, prefix_ok: str = "") -> list[dict]:
    """field / field__lookup / related__field items for *model*, *typed* = the word typed so far."""
    typed = typed.lstrip("-")
    parts = typed.split("__")
    cur = model
    for seg in parts[:-1]:
        f = next((x for x in model_fields(idx, cur) if x["name"] == seg), None)
        if f is None or not f.get("related"):
            cur = ""
            break
        cur = find_model(idx, f["related"]) or f["related"]
    base = "__".join(parts[:-1])
    base = base + "__" if base else ""
    out = []
    rng = [line, col - len(typed), line, col]
    suffix = "=" if as_kwarg else ""
    if cur:
        for i, f in enumerate(model_fields(idx, cur)):
            label = base + f["name"]
            out.append(_item(label, K_FIELD, f"{cur}.{f['name']}: {f.get('type', '')}"
                             + (f" -> {f['related']}" if f.get("related") else ""), insert=label + suffix,
                             rng=rng, filt=label, sort=f"0{i:04d}"))
        if as_kwarg and not base:
            out.append(_item("pk", K_FIELD, f"{cur} primary key", insert="pk=", rng=rng, filt="pk", sort="00000"))
    if base and as_kwarg:
        last = parts[-2] if len(parts) > 1 else ""
        f = next((x for x in model_fields(idx, model if len(parts) == 2 else cur) if x["name"] == last), None) \
            if last else None
        if not (f and f.get("related")) or not cur:
            for i, lk in enumerate(LOOKUPS):
                out.append(_item(base + lk, K_KEYWORD, "field lookup", insert=base + lk + suffix, rng=rng,
                                 filt=base + lk, sort=f"1{i:04d}"))
    elif as_kwarg and cur:
        for f in model_fields(idx, cur):
            if not f.get("related"):
                for lk in ("icontains", "iexact", "in", "gt", "gte", "lt", "lte", "isnull", "startswith"):
                    label = f"{f['name']}__{lk}"
                    out.append(_item(label, K_KEYWORD, "field lookup", insert=label + suffix, rng=rng, filt=label,
                                     sort="2" + label))
    return out


def _template_vars(fw, idx, path, text_before: str) -> dict[str, dict]:
    """Variables available at a point of a template: the view's context + loop / with / set variables."""
    name = template_name_of(path, idx)
    vars_: dict[str, dict] = {}
    for k, v in (DJANGO_GLOBALS if fw.id == "django" else JINJA_GLOBALS).items():
        vars_[k] = {"model": "", "many": False, "detail": v or "context processor"}
    for k, v in (idx.get("context", {}).get(name) or {}).items():
        vars_[k] = {**v, "detail": ("list of " if v.get("many") else "") + (v.get("model") or "from the view")}
    # loop variables of unclosed for-loops / with / set
    for m in re.finditer(r"\{%-?\s*for\s+([\w\s,]+?)\s+in\s+([\w.]+)", text_before):
        src = m.group(2).split(".")[0]
        info = vars_.get(src, {})
        model = info.get("model", "") if info.get("many") else ""
        model = model or find_model(idx, src)
        for v in m.group(1).split(","):
            v = v.strip()
            if v:
                vars_[v] = {"model": model if model and "," not in m.group(1) else "", "many": False,
                            "detail": f"loop variable over {m.group(2)}"}
        vars_.setdefault("forloop" if fw.id == "django" else "loop", {"model": "", "many": False,
                                                                       "detail": "loop information"})
    for m in re.finditer(r"\{%-?\s*with\s+([^%]+)%\}", text_before):
        for a in re.finditer(r"(\w+)\s*=", m.group(1)):
            vars_.setdefault(a.group(1), {"model": "", "many": False, "detail": "with"})
    for m in re.finditer(r"\{%-?\s*set\s+(\w+)\s*=", text_before):
        vars_.setdefault(m.group(1), {"model": "", "many": False, "detail": "set"})
    return vars_


def _complete_template(fw, idx, path, text, lines, line, col, before) -> list[dict]:
    offset = sum(len(x) + 1 for x in lines[:line]) + col
    text_before = text[:offset]
    django = fw.id == "django"
    tag_i = _open_tag(before, "{%", "%}")
    var_i = _open_tag(before, "{{", "}}")
    s = _string_prefix(before[max(tag_i, var_i) + 2:]) if max(tag_i, var_i) >= 0 else None
    if tag_i >= 0 and tag_i > var_i:
        inner = before[tag_i + 2:].lstrip("-")
        if s is not None:
            quote, start, content = s
            start += tag_i + 2
            head = before[:start - 1]
            if re.search(r"\{%-?\s*url\s+$", head):
                return _names_in_string(idx.get("urls", []), line, start, col, K_REFERENCE, _url_detail)
            if re.search(r"\{%-?\s*(extends|include|import|from)\s+$", head):
                cur = template_name_of(path, idx)
                items = [t for t in idx.get("templates", []) if t["name"] != cur]
                return _names_in_string(items, line, start, col, K_FILE, lambda _i: "template")
            if re.search(r"\{%-?\s*static\s+$", head):
                return _names_in_string(idx.get("static", []), line, start, col, K_FILE, lambda _i: "static file")
            if "url_for(" in head:
                return _jinja_url_for(idx, head, line, start, col)
            return []
        m = re.match(r"\s*(\w*)$", inner)
        if m:                                           # the tag name
            word = m.group(1)
            rng = [line, col - len(word), line, col]
            tags = DJANGO_TAGS if django else JINJA_TAGS
            ends = _open_blocks(text_before, django)
            out = []
            for i, end in enumerate(ends[:1]):
                out.append(_item(end, K_KEYWORD, "close the open block", rng=rng, sort="0" + end))
            for k, d in tags.items():
                if k.startswith("end") and k not in ends:
                    continue
                out.append(_item(k, K_KEYWORD, d or "template tag", rng=rng, sort=("1" if not k.startswith("end")
                                                                                      else "2") + k))
            return out
        if re.match(r"\s*load\s+[\w\s]*$", inner):
            word = re.search(r"(\w*)$", before).group(1)
            return [_item(lib, K_MODULE, "template tag library", rng=[line, col - len(word), line, col])
                    for lib in DJANGO_LIBRARIES]
        return _expr_items(fw, idx, path, text_before, before, line, col)
    if var_i >= 0:
        if s is not None:
            quote, start, content = s
            start += var_i + 2
            head = before[:start - 1]
            if "url_for(" in head:
                return _jinja_url_for(idx, head, line, start, col)
            return []
        return _expr_items(fw, idx, path, text_before, before, line, col)
    return []


def _jinja_url_for(idx, head: str, line: int, start: int, col: int) -> list[dict]:
    if re.search(r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*$", head):
        return _names_in_string(idx.get("static", []), line, start, col, K_FILE, lambda _i: "static file")
    if re.search(r"url_for\(\s*$", head):
        return _names_in_string(idx.get("urls", []), line, start, col, K_REFERENCE, _url_detail)
    return []


def _open_blocks(text_before: str, django: bool) -> list[str]:
    """end tags of the blocks still open at the cursor, innermost first."""
    block_tags = {"block", "for", "if", "with", "autoescape", "comment", "filter", "ifchanged", "spaceless",
                  "verbatim", "blocktranslate", "blocktrans", "macro", "call", "raw", "trans"}
    stack = []
    for m in re.finditer(r"\{%-?\s*(\w+)", text_before):
        tag = m.group(1)
        if tag in block_tags:
            stack.append(tag)
        elif tag.startswith("end") and stack and stack[-1] == tag[3:]:
            stack.pop()
    return ["end" + t for t in reversed(stack)]


def _expr_items(fw, idx, path, text_before, before, line, col) -> list[dict]:
    django = fw.id == "django"
    m = re.search(r"\|\s*(\w*)$", before)
    if m:                                               # filters
        word = m.group(1)
        rng = [line, col - len(word), line, col]
        return [_item(f, K_FUNCTION, "filter", rng=rng) for f in (DJANGO_FILTERS if django else JINJA_FILTERS)]
    m = re.search(r"([A-Za-z_][\w.]*)\.(\w*)$", before)
    vars_ = _template_vars(fw, idx, path, text_before)
    if m:                                               # attributes: post.<...>
        chain, word = m.group(1).split("."), m.group(2)
        rng = [line, col - len(word), line, col]
        head = chain[0]
        model = (vars_.get(head) or {}).get("model") or ""
        if (vars_.get(head) or {}).get("many"):
            model = ""
        attrs: list[tuple[str, str]] = []
        if len(chain) == 1 and head in ATTRS and not model:
            attrs = [(a, head) for a in ATTRS[head]]
        else:
            cur = model or (find_model(idx, head) if len(chain) == 1 else "")
            for seg in chain[1:]:
                f = next((x for x in model_fields(idx, cur) if x["name"] == seg), None) if cur else None
                cur = (find_model(idx, f["related"]) or f["related"]) if f and f.get("related") else ""
                if seg == "user" and not cur:
                    attrs = [(a, "user") for a in ATTRS["user"]]
            if cur:
                attrs = [(f["name"], f"{cur}.{f['name']}: {f.get('type', '')}") for f in model_fields(idx, cur)]
                attrs += [("pk", "primary key"), ("get_absolute_url", "method")]
        return [_item(a, K_FIELD, d, rng=rng) for a, d in attrs]
    word = re.search(r"(\w*)$", before).group(1)
    rng = [line, col - len(word), line, col]
    return [_item(k, K_VARIABLE, v.get("detail", ""), rng=rng, sort=("0" if not v.get("detail", "").startswith(
        ("context", "HttpRequest", "the ")) else "1") + k) for k, v in vars_.items()]


# ============================================================================ go to definition
def _string_at(line_text: str, col: int) -> str:
    """The string literal (without quotes) around column *col*."""
    for m in re.finditer(r"(['\"])(.*?)(?<!\\)\1", line_text):
        if m.start() <= col <= m.end():
            return m.group(2)
    return ""


def definition(folder, path, text: str, line: int, col: int, fw: Framework | None = None) -> tuple[str, int] | None:
    """(file, 1-based line) for F12 on a url name, template name or static file name; None = not ours."""
    folder = Path(folder)
    fw = fw or framework_for(project_language(folder))
    if fw is None:
        return None
    lines = text.split("\n")
    if line >= len(lines):
        return None
    name = _string_at(lines[line], col)
    if not name:
        m = re.search(r"\{%-?\s*(?:extends|include)\s+(\S+)", lines[line])
        name = m.group(1).strip("'\"") if m else ""
    if not name:
        return None
    idx = project_index(folder, fw)
    for t in idx.get("templates", []):
        if t["name"] == name:
            return t["file"], 1
    for u in idx.get("urls", []):
        if u["name"] == name or (":" not in name and u["name"].split(":")[-1] == name and fw.id == "django"):
            f = u.get("decl_file") or u.get("file")
            ln = u.get("decl_line") or u.get("line") or 1
            if f and Path(f).is_file():
                return f, int(ln)
    for s in idx.get("static", []):
        if s["name"] == name:
            return s["file"], 1
    return None


# ============================================================================ debugging
def _debug_session_class():
    from ...dap import DapSession

    class PyWebDebugSession(DapSession):
        """DAP over TCP to the adapter that ``debugpy --listen <port> --wait-for-client`` opened inside the
        server process (no adapter process of our own)."""

        def __init__(self, cwd, breakpoints, port: int, framework: str, parent=None):
            super().__init__("debugpy", "", [], cwd, None, breakpoints, parent)
            self.port = port
            self.sock = None
            self.launch_args = {"type": "python", "request": "attach", "justMyCode": True,
                                "django": framework == "django", "jinja": framework in ("flask", "fastapi"),
                                "subProcess": False, "showReturnValue": True}

        # ---- transport: a TCP socket instead of the adapter's stdin/stdout
        def start(self, wait: float = 900.0):
            """Connect (retrying while the server is still starting - venv creation, pip, imports)."""
            from PyQt6.QtNetwork import QTcpSocket
            self.deadline = time.monotonic() + wait
            self.sock = QTcpSocket(self)
            self.sock.readyRead.connect(self._sock_read)
            self.sock.disconnected.connect(lambda: self._finish(0))
            self.sock.errorOccurred.connect(self._sock_error)
            self.sock.connected.connect(lambda: self._request(
                "initialize", {"clientID": "radide", "adapterID": "debugpy", "linesStartAt1": True,
                               "columnsStartAt1": True, "pathFormat": "path", "supportsRunInTerminalRequest": False,
                               "supportsVariableType": True}, self._on_initialize))
            self._try_connect()

        def _try_connect(self):
            if self.sock is not None and not self._done and not self.user_stopped:
                self.sock.abort()
                self.sock.connectToHost("127.0.0.1", self.port)

        def _sock_error(self, _err):
            from PyQt6.QtCore import QTimer
            from PyQt6.QtNetwork import QAbstractSocket
            if self._done or self.user_stopped or self.sock.state() == QAbstractSocket.SocketState.ConnectedState:
                return
            if _err == QAbstractSocket.SocketError.RemoteHostClosedError:
                return                                # the server ended: disconnected -> _finish
            if time.monotonic() < self.deadline:
                QTimer.singleShot(250, self._try_connect)
            else:
                self.failed.emit(f"cannot connect to debugpy on port {self.port}: {self.sock.errorString()}")
                self._finish(1)

        def running(self) -> bool:
            from PyQt6.QtNetwork import QAbstractSocket
            return self.sock is not None and self.sock.state() == QAbstractSocket.SocketState.ConnectedState

        def _send(self, msg):
            if self.sock is None:
                return
            body = json.dumps(msg).encode("utf-8")
            self.sock.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

        def _sock_read(self):
            self._buf += bytes(self.sock.readAll())
            while True:
                end = self._buf.find(b"\r\n\r\n")
                if end < 0:
                    return
                length = 0
                for ln in self._buf[:end].split(b"\r\n"):
                    if ln.lower().startswith(b"content-length:"):
                        length = int(ln.split(b":")[1])
                if len(self._buf) < end + 4 + length:
                    return
                body, self._buf = self._buf[end + 4:end + 4 + length], self._buf[end + 4 + length:]
                try:
                    self._dispatch(json.loads(body))
                except ValueError:
                    continue

        def _on_initialize(self, body, _msg):
            self._request("attach", self.launch_args)

        def stop(self):
            self.user_stopped = True
            if self.running():
                self._request("disconnect", {"terminateDebuggee": True})
                self.sock.flush()
                self.sock.waitForBytesWritten(500)
                self.sock.disconnectFromHost()
            self._finish(0)
    return PyWebDebugSession


def start_debug(win, project, path=None):
    """F5 on a Python web site: DevServer + server under debugpy + DAP attach. Returns True, or None to run
    without the debugger."""
    from PyQt6.QtCore import QTimer
    from ...features import web_workspace as ww
    from ...languages import get_plugin
    from ..debug import _wire
    plugin = get_plugin(project.language)
    fw = getattr(plugin, "framework", None)
    if fw is None:
        return None
    if win.session is not None and win.session.running():
        return True
    import importlib.util
    if importlib.util.find_spec("debugpy") is None:       # the IDE's own copy runs the server
        win.log("*** debugpy is not installed in the IDE's Python - running without the debugger "
                "(pip install debugpy).")
        return None
    if getattr(win, "web_server", None) is not None:
        ww.stop_website(win)
    win._sync_breakpoints()
    bps = win._all_breakpoints()
    folder = Path(project.folder).resolve()
    port = free_port()
    s = _debug_session_class()(folder, bps, port, fw.id, win)
    s.break_on_exception = win.settings.value("debug/break_on_exception", True) in (True, "true")
    win.output.clear()
    win.locals.clear()
    win.callstack.clear()
    win.dock_output.show()
    win.dock_output.raise_()
    win.log(f"------ Debug web site '{project.name}' ({fw.title} under debugpy) ------")
    _wire(win, s)
    win.session = s
    hook = lambda srv, spec: plugin.debug_backend(srv, spec, port)  # noqa: E731
    srv = ww.run_website(win, project, debug=False, path=path, backend_hook=hook)
    if srv is None:
        win.session = None
        return None
    s.start()                      # connects as soon as the server's debugpy listens (after venv / pip)
    win.statusBar().showMessage(f"Debugging {project.name} at {srv.url} - set breakpoints with F9")
    _watch_code(win, s, project, srv)

    def session_ended(_code):
        if getattr(win, "web_server", None) is srv:
            QTimer.singleShot(0, lambda: getattr(win, "web_server", None) is srv and ww.stop_website(win))
    s.finished.connect(session_ended)
    srv.stopped.connect(lambda: win.session is s and not s._done and QTimer.singleShot(0, s.stop))
    srv.backendExited.connect(lambda _c: win.session is s and not s._done and QTimer.singleShot(0, s.stop))
    win._update_actions()
    return True


def _watch_code(win, s, project, srv) -> None:
    """While debugging (no auto-reloader): a changed .py / template restarts the debug session, so the new
    code runs - unless the program is paused at a breakpoint."""
    from PyQt6.QtCore import QTimer
    folder = Path(project.folder).resolve()
    state = {"sig": _code_signature(folder)}
    timer = QTimer(s)
    timer.setInterval(1000)

    def check():
        if win.session is not s or s._done:
            timer.stop()
            return
        if not s.running():
            return                                    # still connecting
        sig = _code_signature(folder)
        if sig == state["sig"] or s.paused:
            if not s.paused:
                state["sig"] = sig
            return
        state["sig"] = sig
        timer.stop()
        win.log("[debug] Code changed - restarting the debug session to load it...")
        url = ""
        try:
            url = win.web_preview.current_url()
        except Exception:  # noqa: BLE001
            pass
        from urllib.parse import urlsplit
        page = urlsplit(url).path if url.startswith(srv.url) else None

        def again(_code=0):
            QTimer.singleShot(400, lambda: start_debug(win, project, page))
        s.finished.connect(again)
        s.stop()
    timer.timeout.connect(check)
    timer.start()


def _code_signature(folder: Path) -> tuple:
    n, total = 0, 0.0
    for p in walk_files(folder, (".py",), 5000):
        try:
            total += p.stat().st_mtime
            n += 1
        except OSError:
            pass
    return n, round(total, 3)


__all__ = ["Command", "Framework", "PyWebPlugin", "complete", "create_venv", "definition", "framework_for",
           "index_status", "is_template", "list_static", "list_templates", "project_index", "project_root_of",
           "refresh_runtime", "register_framework_template", "run_logged", "run_runtime_index", "start_debug",
           "template_context", "venv_python", "walk_files", "write_files"]
