"""Project Actions - commands that depend on the KIND of project that is open (``php artisan`` for
Laravel, ``spark`` for CodeIgniter, ``manage.py`` for Django, npm scripts, Makefile targets ...).

The IDE shows them (``radide/features/project_menus.py``):

* a top-level menu per detected provider, after "Project" ("Laravel", "npm Scripts" ...), rebuilt when the
  active project changes (several providers can be active at once),
* a dynamic section at the end of the Project menu ("Laravel Commands" sub menus),
* Solution Explorer right-click: ``folder_actions`` / ``file_actions`` of the clicked folder / file at the top
  of the context menu (normal projects, website folder trees and foreign projects),
* a "Project Actions" tool bar with the actions marked ``toolbar=True``,
* Command Palette entries "<Provider>: <Action>".

Writing a provider (see docs/PROJECT_ACTIONS.md) - put a module in ``radide/project_actions_providers/``
(auto-discovered; it defines ``PROVIDERS = [MyProvider()]`` or calls ``register_provider``)::

    from radide.project_actions import Action, Field, Provider, Separator, Submenu, matches

    class Laravel(Provider):
        id, title, priority = "laravel", "Laravel", 50
        markers = ("artisan", "composer.json")            # their mtimes invalidate the detect() cache

        def detect(self, folder, project):                # fast: marker files only (result is cached)
            return (folder / "artisan").is_file() and composer_requires(folder, "laravel/framework")

        def actions(self, ctx):                           # top-level menu / Project menu / palette
            return [Action("serve", "Serve", lambda c: c.run_cli(["php", "artisan", "serve"]),
                           toolbar=True, opens="none"),
                    Separator(),
                    Submenu("Make", [self.make_controller()])]

        def folder_actions(self, ctx, rel_folder):        # Solution Explorer right-click on a folder
            if matches(rel_folder, "app/Http/Controllers/**"):
                return [self.make_controller()]
            return []

        def file_actions(self, ctx, rel_file):            # ... on a file
            if matches(rel_file, "database/migrations/*.php"):
                return [Action("migrate-this", "Run This Migration",
                               lambda c: c.run_cli(["php", "artisan", "migrate", "--path=" + rel_file]))]
            return []

        def make_controller(self):
            return Action("make-controller", "New Controller...",
                          lambda c: c.run_cli(["php", "artisan", "make:controller", c.values["name"],
                                               *(["--resource"] if c.values["resource"] else [])]),
                          ask=[Field("name", "Name", default="PostController"),
                               Field("resource", "Resource controller", "bool")])

API summary
-----------
* ``Field(name, label="", kind="text"|"bool"|"choice"|"path"|"multiline", default=None, choices=(), help="",
  required=None, placeholder="")`` - one input of the ask dialog (``required`` defaults to True for text).
* ``Action(id, title, run, icon=None, shortcut=None, group=None, ask=[], enabled=None, opens="created",
  toolbar=False, palette=True, tip="", refresh=None)`` - ``run(ctx)`` (or ``run(ctx, values)``); the answers of
  ``ask`` are in ``ctx.values``. ``enabled(ctx) -> bool``. ``opens="created"`` opens the files the command
  created (``"none"``: never). ``icon``: a QIcon, a ``radide.icons`` name, a ``"SP_..."`` standard icon or a
  ``("Lv", "#E8473C")`` letter badge. ``refresh``: refresh Solution Explorer after the command (default:
  when files were created).
* ``Separator()``, ``Submenu(title, items, icon=None)``.
* ``Provider``: ``id``, ``title``, ``priority`` (higher first), ``icon``, ``markers``, ``detect(folder, project)``,
  ``actions(ctx)``, ``folder_actions(ctx, rel_folder)``, ``file_actions(ctx, rel_file)`` (relative POSIX paths;
  the project root is ``""``), ``created_files(ctx, run) -> list[Path]`` (extra created-file detection).
* ``ActionContext`` (``ctx``): ``win``, ``project``, ``folder`` (Path), ``provider``, ``action``, ``values``,
  ``target`` / ``rel_target`` (the clicked folder / file, else None / ""), ``rel(path)``, ``path(rel)``,
  ``run_cli(argv, cwd=None, title=None, on_done=None, env=None, opens=None, stdin=None) -> CliRun``,
  ``run_in_terminal(argv, cwd=None)``, ``ask(fields, title=None, text="") -> dict | None``,
  ``confirm(text) -> bool``, ``open_file(path, line=None)``, ``refresh_tree()``, ``log(text)``,
  ``php()``, ``python()``, ``resolve_argv(argv) -> (argv, env)``.
  ``run_cli`` streams the output to the Output window (QProcess, cancellable with ``CliRun.cancel()`` or
  Stop Running Command), uses the project's tool chain (``php`` = the project's PHP version with the framework
  extensions, ``composer``, ``python`` = the project's ``.venv``, ``node_modules/.bin`` and ``.venv`` on PATH,
  ``npm`` / ``npx`` / ``yarn`` ... found on PATH) and, when it ends with exit code 0, refreshes the tree and
  OPENS the created files: paths named in the output ("Controller [app/Http/Controllers/X.php] created",
  "File created: app/Models/X.php") that exist and are new, plus the files that appeared in the project folder
  (a before/after snapshot, vendor / node_modules / .git / caches skipped). ``on_done(run)`` gets the CliRun
  (``run.exit_code``, ``run.output``, ``run.created``).
* Registry: ``register_provider(p)``, ``unregister_provider(id)``, ``providers()``, ``detect(folder, project)``
  -> active providers, ``run_action(ctx, action)``, ``running(win)`` -> CliRuns still running,
  ``matches(rel, *patterns)`` (``*`` = one path part, ``**`` = any depth; ``"app/Models/**"`` matches the
  folder itself and everything below), ``read_json(path)``, ``read_text(path)``, ``composer_requires(folder,
  package)``, ``package_json(folder)``.

Tests: ``ASK_HOOK = lambda fields, title: {...}`` answers the ask dialog without showing it.
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
import pkgutil
import re
import shutil
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

# ============================================================================ data model
FIELD_KINDS = ("text", "bool", "choice", "path", "multiline")


@dataclass
class Field:
    name: str
    label: str = ""
    kind: str = "text"
    default: Any = None
    choices: tuple | list = ()
    help: str = ""
    required: bool | None = None
    placeholder: str = ""

    def is_required(self) -> bool:
        return self.kind in ("text", "path") if self.required is None else bool(self.required)


@dataclass
class Action:
    id: str
    title: str
    run: Callable
    icon: Any = None
    shortcut: str | None = None
    group: str | None = None
    ask: list = field(default_factory=list)
    enabled: Callable | None = None
    opens: str = "created"
    toolbar: bool = False
    palette: bool = True
    tip: str = ""
    refresh: bool | None = None

    def is_enabled(self, ctx) -> bool:
        if self.enabled is None:
            return True
        try:
            return bool(self.enabled(ctx))
        except Exception:  # noqa: BLE001 - a broken check must not break the menu
            return False


class Separator:
    """A menu separator in an action list."""


@dataclass
class Submenu:
    title: str
    items: list = field(default_factory=list)
    icon: Any = None


class Provider:
    """Base class of a project-actions provider (override what you need)."""
    id: str = ""
    title: str = ""
    priority: int = 0
    icon: Any = None
    markers: tuple = ()

    def detect(self, folder: Path, project) -> bool:          # noqa: ARG002
        return False

    def actions(self, ctx) -> list:                            # noqa: ARG002
        return []

    def folder_actions(self, ctx, rel_folder: str) -> list:    # noqa: ARG002
        return []

    def file_actions(self, ctx, rel_file: str) -> list:        # noqa: ARG002
        return []

    def created_files(self, ctx, run) -> list:                 # noqa: ARG002
        return []

    def __repr__(self) -> str:
        return f"<Provider {self.id}>"


# ============================================================================ helpers for providers
_CASE_INSENSITIVE = sys.platform == "win32"
_RX_CACHE: dict[str, re.Pattern] = {}


def _glob_rx(pattern: str) -> re.Pattern:
    rx = _RX_CACHE.get(pattern)
    if rx is not None:
        return rx
    p = pattern.strip().replace("\\", "/").strip("/")
    out, i = "", 0
    while i < len(p):
        if p.startswith("/**", i) and i + 3 == len(p):            # "dir/**" = dir itself and below
            out += "(?:/.*)?"
            i += 3
        elif p.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif p.startswith("**", i):
            out += ".*"
            i += 2
        elif p[i] == "*":
            out += "[^/]*"
            i += 1
        elif p[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(p[i])
            i += 1
    rx = re.compile("^" + out + "$", re.I if _CASE_INSENSITIVE else 0)
    _RX_CACHE[pattern] = rx
    return rx


def matches(rel: str, *patterns: str) -> bool:
    """True when the relative POSIX path *rel* matches one of the glob *patterns*."""
    r = str(rel or "").replace("\\", "/").strip("/")
    return any(_glob_rx(p).match(r) for p in patterns)


_FILE_CACHE: dict[tuple[str, str], tuple[float, Any]] = {}


def _cached(path, kind: str, load):
    p = Path(path)
    try:
        m = p.stat().st_mtime
    except OSError:
        return None
    key = (str(p), kind)
    hit = _FILE_CACHE.get(key)
    if hit is not None and hit[0] == m:
        return hit[1]
    try:
        val = load(p)
    except Exception:  # noqa: BLE001 - broken file = nothing
        val = None
    _FILE_CACHE[key] = (m, val)
    return val


def read_text(path) -> str:
    return _cached(path, "text", lambda p: p.read_text(encoding="utf-8", errors="replace")) or ""


def read_json(path) -> Any:
    """Parsed JSON of *path* (cached by mtime; JSON with comments / trailing commas - tasks.json - too)."""
    def load(p):
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        try:
            return json.loads(text)
        except ValueError:
            return json.loads(_strip_jsonc(text))
    return _cached(path, "json", load)


def _strip_jsonc(text: str) -> str:
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def package_json(folder) -> dict:
    d = read_json(Path(folder) / "package.json")
    return d if isinstance(d, dict) else {}


def composer_json(folder) -> dict:
    d = read_json(Path(folder) / "composer.json")
    return d if isinstance(d, dict) else {}


def composer_requires(folder, package: str) -> bool:
    d = composer_json(folder)
    return any(package in (d.get(k) or {}) for k in ("require", "require-dev"))


# ============================================================================ registry
_PROVIDERS: dict[str, Provider] = {}
_LOADED = False
LOAD_ERRORS: list[str] = []
ASK_HOOK: Callable | None = None
_DETECT: dict[tuple[str, str], tuple[tuple, bool]] = {}


def register_provider(provider: Provider) -> Provider:
    """Add (or replace, same id) a provider."""
    if not provider.id:
        raise ValueError("a project-actions provider needs an id")
    _PROVIDERS[provider.id] = provider
    clear_cache()
    return provider


def unregister_provider(provider_id: str) -> None:
    _PROVIDERS.pop(provider_id, None)
    clear_cache()


def load_providers(force: bool = False) -> None:
    """Import every module of radide/project_actions_providers (once)."""
    global _LOADED
    if _LOADED and not force:
        return
    _LOADED = True
    try:
        from . import project_actions_providers as pkg
    except Exception:  # noqa: BLE001
        LOAD_ERRORS.append(traceback.format_exc())
        return
    for mod in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        if mod.name.startswith("_"):
            continue
        try:
            m = importlib.import_module(f"{pkg.__name__}.{mod.name}")
            found = getattr(m, "PROVIDERS", None)
            if found is None and callable(getattr(m, "providers", None)):
                found = m.providers()
            for p in found or []:
                register_provider(p)
        except Exception:  # noqa: BLE001 - a broken provider must not break the IDE
            LOAD_ERRORS.append(f"[project actions] provider module {mod.name}:\n{traceback.format_exc()}")


def providers() -> list[Provider]:
    load_providers()
    return sorted(_PROVIDERS.values(), key=lambda p: (-p.priority, p.title.lower()))


def provider(provider_id: str) -> Provider | None:
    load_providers()
    return _PROVIDERS.get(provider_id)


def clear_cache() -> None:
    _DETECT.clear()


def _stamp(folder: Path, markers) -> tuple:
    out = []
    for rel in ("", *markers):
        try:
            out.append((folder / rel).stat().st_mtime if rel else folder.stat().st_mtime)
        except OSError:
            out.append(-1.0)
    return tuple(out)


def detect(folder, project=None) -> list[Provider]:
    """The providers that apply to the project in *folder* (cached until the folder / markers change)."""
    if folder is None:
        return []
    folder = Path(folder)
    if not folder.is_dir():
        return []
    out = []
    for p in providers():
        key = (os.path.normcase(str(folder)), p.id)
        stamp = _stamp(folder, p.markers)
        hit = _DETECT.get(key)
        if hit is not None and hit[0] == stamp:
            ok = hit[1]
        else:
            try:
                ok = bool(p.detect(folder, project))
            except Exception:  # noqa: BLE001
                ok = False
                LOAD_ERRORS.append(f"[project actions] {p.id}.detect: {traceback.format_exc()}")
            _DETECT[key] = (stamp, ok)
        if ok:
            out.append(p)
    return out


def flatten(items) -> list[tuple[list[str], Action]]:
    """(sub menu path, action) of every Action of an action list (sub menus included)."""
    out = []
    for it in items or []:
        if isinstance(it, Action):
            out.append(([], it))
        elif isinstance(it, Submenu):
            out += [([it.title, *path], a) for path, a in flatten(it.items)]
    return out


def safe_items(fn, *args) -> list:
    try:
        return list(fn(*args) or [])
    except Exception:  # noqa: BLE001
        LOAD_ERRORS.append(traceback.format_exc())
        return []


# ============================================================================ files created by a command
SKIP_DIRS = {".git", ".svn", ".hg", "node_modules", "vendor", ".venv", "venv", "env", "__pycache__", ".dart_tool",
             ".idea", ".vs", ".gradle", ".next", ".nuxt", ".cache", ".mypy_cache", ".pytest_cache", ".tox",
             ".radide", "target", "bin", "obj", ".angular", ".expo", "Pods", ".pub-cache", ".phpunit.cache"}
SKIP_REL = {"storage/framework", "storage/logs", "bootstrap/cache", "writable/cache", "writable/logs",
            "writable/session", "writable/debugbar", "build", "dist", "public/build", "public/hot"}
SNAPSHOT_LIMIT = 40000


def snapshot(folder) -> set[str]:
    """Relative POSIX paths of the files of *folder* (heavy / generated folders skipped)."""
    root = Path(folder)
    out: set[str] = set()
    stack = [(root, "")]
    while stack and len(out) < SNAPSHOT_LIMIT:
        d, rel = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    r = f"{rel}/{e.name}" if rel else e.name
                    try:
                        is_dir = e.is_dir()
                    except OSError:
                        continue
                    if is_dir:
                        if e.name not in SKIP_DIRS and r not in SKIP_REL:
                            stack.append((Path(e.path), r))
                    else:
                        out.add(r)
        except OSError:
            continue
    return out


_PATH_TOKEN = re.compile(r"(?:[A-Za-z]:[\\/])?[\w.\-/\\]+\.[A-Za-z0-9]{1,10}")


def files_in_output(text: str, roots, since: float) -> list[Path]:
    """Existing files named in a command's output that were written at/after *since*."""
    out: list[Path] = []
    seen = set()
    for tok in _PATH_TOKEN.findall(text or ""):
        tok = tok.strip(".")
        if not tok or tok.lower().startswith(("http", "www.")):
            continue
        cands = [Path(tok)] if Path(tok).is_absolute() else [Path(r) / tok for r in roots]
        for c in cands:
            try:
                if c.is_file() and c.stat().st_mtime >= since - 2:
                    key = os.path.normcase(str(c.resolve()))
                    if key not in seen:
                        seen.add(key)
                        out.append(c.resolve())
                    break
            except OSError:
                continue
    return out


# ============================================================================ running commands
_RUNS: list["CliRun"] = []
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
MAX_OPEN = 8


def running(win=None) -> list["CliRun"]:
    return [r for r in _RUNS if r.is_running() and (win is None or r.ctx.win is win)]


class CliRun(QObject):
    """One command started by ``ctx.run_cli`` (QProcess; output -> Output window)."""
    finished = pyqtSignal(int)
    output_received = pyqtSignal(str)

    def __init__(self, ctx, argv, cwd, title, on_done=None, env=None, opens="created", stdin=None):
        super().__init__(ctx.win)
        self.ctx = ctx
        self.argv = [str(a) for a in argv]
        self.cwd = Path(cwd)
        self.title = title
        self.on_done = on_done
        self.env = dict(env or {})
        self.opens = opens
        self.stdin = stdin
        self.output = ""
        self.exit_code: int | None = None
        self.created: list[Path] = []
        self.cancelled = False
        self.proc: QProcess | None = None
        self._before: set[str] | None = None
        self._t0 = 0.0

    # ---------------------------------------------------------------- state
    def is_running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def command_line(self) -> str:
        return " ".join(f'"{a}"' if (" " in a or not a) else a for a in self.argv)

    # ---------------------------------------------------------------- start / stop
    def start(self) -> "CliRun":
        ctx, win = self.ctx, self.ctx.win
        argv, env = ctx.resolve_argv(self.argv)
        env.update(self.env)
        self.resolved = argv
        self._t0 = time.time()
        if self.opens == "created":
            self._before = snapshot(ctx.folder)
        _show_output(win)
        ctx.log(f"------ {self.title} ------")
        ctx.log(f"> {' '.join(self.argv)}    (in {self.cwd})")
        p = QProcess(self)
        p.setWorkingDirectory(str(self.cwd))
        e = QProcessEnvironment.systemEnvironment()
        for k, v in env.items():
            e.insert(str(k), str(v))
        p.setProcessEnvironment(e)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._read)
        p.finished.connect(self._done)
        p.errorOccurred.connect(self._error)
        self.proc = p
        _RUNS.append(self)
        _status(win, f"{self.title}: running...")
        p.start(argv[0], argv[1:])
        if self.stdin is not None and p.waitForStarted(5000):
            p.write(str(self.stdin).encode("utf-8"))
            p.closeWriteChannel()
        return self

    def cancel(self) -> None:
        if not self.is_running():
            return
        self.cancelled = True
        pid = self.proc.processId()
        try:
            from .features.terminal import kill_tree
            if pid:
                kill_tree(pid)
        except Exception:  # noqa: BLE001
            pass
        if self.is_running():
            self.proc.kill()
        self.ctx.log(f"------ {self.title}: stopped ------")

    def wait(self, ms: int = 120000) -> int | None:
        """Process events until the command ends (tests and scripts)."""
        from PyQt6.QtCore import QElapsedTimer, QEventLoop
        from PyQt6.QtWidgets import QApplication
        t = QElapsedTimer()
        t.start()
        while (self.exit_code is None) and t.elapsed() < ms:
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            if self.proc is not None and self.is_running():
                self.proc.waitForFinished(30)
        QApplication.processEvents()
        return self.exit_code

    # ---------------------------------------------------------------- process signals
    def _read(self) -> None:
        if self.proc is None:
            return
        raw = bytes(self.proc.readAllStandardOutput())
        if not raw:
            return
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("mbcs" if sys.platform == "win32" else "latin-1", errors="replace")
        text = ANSI.sub("", text.replace("\r\n", "\n"))
        self.output += text
        try:
            self.ctx.win._append_output(text)
        except Exception:  # noqa: BLE001
            pass
        self.output_received.emit(text)

    def _error(self, err) -> None:
        if err == QProcess.ProcessError.FailedToStart and self.exit_code is None:
            prog = self.proc.program() if self.proc is not None else self.argv[0]
            self.ctx.log(f"*** {self.title}: cannot start '{prog}' - is it installed / on PATH?")
            self._finish(-1)

    def _done(self, code, _status=None) -> None:
        self._read()
        self._finish(int(code))

    def _finish(self, code: int) -> None:
        if self.exit_code is not None:
            return
        self.exit_code = -2 if self.cancelled and code == 0 else code
        if self in _RUNS:
            _RUNS.remove(self)
        ctx, win = self.ctx, self.ctx.win
        if not self.cancelled:
            ctx.log(f"------ {self.title}: {'done' if code == 0 else f'failed (exit code {code})'} ------")
        _status(win, f"{self.title}: {'done' if code == 0 else ('stopped' if self.cancelled else f'failed ({code})')}")
        if code == 0 and self.opens == "created":
            try:
                self.created = self._detect_created()
            except Exception:  # noqa: BLE001
                self.created = []
        action = ctx.action
        refresh = action.refresh if action is not None and action.refresh is not None else bool(self.created)
        if refresh or self.created:
            ctx.refresh_tree()
        for p in self.created[:MAX_OPEN]:
            ctx.open_file(p)
        if self.created:
            ctx.log("Created: " + ", ".join(ctx.rel(p) for p in self.created))
        if self.on_done is not None:
            try:
                self.on_done(self)
            except Exception:  # noqa: BLE001
                ctx.log(f"*** {self.title}: {traceback.format_exc()}")
        try:
            from .features import project_menus
            project_menus.runs_changed(win)
        except Exception:  # noqa: BLE001
            pass
        self.finished.emit(self.exit_code)

    def _detect_created(self) -> list[Path]:
        ctx = self.ctx
        found = files_in_output(self.output, [self.cwd, ctx.folder], self._t0)
        if ctx.provider is not None:
            found += [Path(p) for p in safe_items(ctx.provider.created_files, ctx, self)]
        if self._before is not None:
            after = snapshot(ctx.folder)
            new = sorted(after - self._before, key=lambda r: (r.count("/"), r))
            found += [ctx.folder / r for r in new]
        out, seen = [], set()
        for p in found:
            try:
                p = Path(p).resolve()
                key = os.path.normcase(str(p))
                if key in seen or not p.is_file():
                    continue
                if not (p.is_relative_to(ctx.folder) or p.is_relative_to(self.cwd.resolve())):
                    continue
            except (OSError, ValueError):
                continue
            seen.add(key)
            out.append(p)
        return out


def _show_output(win) -> None:
    d = getattr(win, "dock_output", None)
    if d is not None:
        d.show()
        d.raise_()


def _status(win, text: str) -> None:
    try:
        win.statusBar().showMessage(text, 6000)
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ context
NODE_TOOLS = ("npm", "npx", "yarn", "pnpm", "bun", "ng", "vite", "nest", "expo", "tsc", "node")


class ActionContext:
    """What an action gets: the window, the project and helpers (see the module docstring)."""

    def __init__(self, win, project=None, folder=None, provider=None, target=None):
        self.win = win
        self.project = project if project is not None else getattr(win, "project", None)
        f = folder if folder is not None else (getattr(self.project, "folder", None) if self.project else None)
        self.folder = Path(f).resolve() if f else Path.cwd()
        self.provider = provider
        self.target = Path(target) if target else None
        self.action: Action | None = None
        self.values: dict = {}
        self.last_run: CliRun | None = None

    def with_provider(self, provider) -> "ActionContext":
        c = ActionContext(self.win, self.project, self.folder, provider, self.target)
        return c

    # ---------------------------------------------------------------- paths
    @property
    def rel_target(self) -> str:
        return self.rel(self.target) if self.target is not None else ""

    def rel(self, path) -> str:
        try:
            return Path(path).resolve().relative_to(self.folder).as_posix()
        except (ValueError, OSError):
            return str(path)

    def path(self, rel: str) -> Path:
        return self.folder / rel

    def log(self, text: str) -> None:
        try:
            self.win.log(text)
        except Exception:  # noqa: BLE001
            print(text)

    # ---------------------------------------------------------------- tool chain
    def php(self) -> str:
        try:
            from .features.php_tools import project_php
            php = project_php(self.win, self.project)
            if php:
                return php
        except Exception:  # noqa: BLE001
            pass
        try:
            from .web_site.frameworks.common import project_php
            return project_php(self.folder)
        except Exception:  # noqa: BLE001
            return shutil.which("php") or "php"

    def python(self) -> str:
        for rel in ((".venv", "Scripts", "python.exe"), (".venv", "bin", "python"),
                    ("venv", "Scripts", "python.exe"), ("venv", "bin", "python")):
            p = self.folder.joinpath(*rel)
            if p.is_file():
                return str(p)
        try:
            from .app import real_python
            exe = self.win.settings.value("interpreter/python", "") if hasattr(self.win, "settings") else ""
            if exe and Path(str(exe)).exists():
                return str(exe)
            return real_python(shutil.which("python") or sys.executable)
        except Exception:  # noqa: BLE001
            return shutil.which("python") or sys.executable

    def _path_dirs(self) -> list[str]:
        dirs = []
        for rel in (("node_modules", ".bin"), (".venv", "Scripts"), (".venv", "bin"), ("venv", "Scripts")):
            p = self.folder.joinpath(*rel)
            if p.is_dir():
                dirs.append(str(p))
        return dirs

    def resolve_argv(self, argv) -> tuple[list[str], dict]:
        """argv with argv[0] resolved for the project's tool chain, and the environment to add."""
        argv = [str(a) for a in argv]
        if not argv:
            raise ValueError("empty command")
        env: dict[str, str] = {"NO_COLOR": "1", "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        extra = self._path_dirs()
        name, rest = argv[0], argv[1:]
        low = Path(name).name.lower()
        low = low[:-4] if low.endswith((".exe", ".cmd", ".bat")) else low
        if low == "php" and not Path(name).is_absolute():
            php = self.php()
            try:
                from .web_site.frameworks.common import php_ext_args
                ext = php_ext_args(php)
            except Exception:  # noqa: BLE001
                ext = []
            argv = [php, *ext, *rest]
            if php and Path(php).is_absolute():
                extra.insert(0, str(Path(php).parent))
            env["COMPOSER_NO_INTERACTION"] = "1"
        elif low == "composer" and not Path(name).is_absolute():
            php = self.php()
            try:
                from .web_site import php_toolchain as tc
                cargv = tc.composer_argv(rest, php)
                if cargv:
                    argv = cargv
                env.update({k: v for k, v in tc.composer_env(php).items() if k != "PATH" and k not in os.environ})
            except Exception:  # noqa: BLE001
                pass
            if php and Path(php).is_absolute():
                extra.insert(0, str(Path(php).parent))
            env["COMPOSER_NO_INTERACTION"] = "1"
        elif low in ("python", "python3", "py") and not Path(name).is_absolute():
            argv = [self.python(), *rest]
        elif not Path(name).is_absolute():
            search = os.pathsep.join([*extra, os.environ.get("PATH", "")])
            exe = None
            if sys.platform == "win32" and low in NODE_TOOLS:
                exe = shutil.which(low + ".cmd", path=search)
            if exe is None and low == "make":
                exe = shutil.which("make", path=search) or shutil.which("mingw32-make", path=search)
            exe = exe or shutil.which(name, path=search)
            if exe:
                argv = [exe, *rest]
        if extra:
            env["PATH"] = os.pathsep.join([*extra, os.environ.get("PATH", "")])
        return argv, env

    # ---------------------------------------------------------------- run
    def run_cli(self, argv, cwd=None, title=None, on_done=None, env=None, opens=None, stdin=None) -> CliRun:
        """Run a command; output -> Output window; created files open when it succeeds."""
        if opens is None:
            opens = self.action.opens if self.action is not None else "none"
        title = title or " ".join(str(a) for a in argv[:4])
        run = CliRun(self, argv, cwd or self.folder, title, on_done, env, opens, stdin)
        self.last_run = run
        run.start()
        return run

    def run_in_terminal(self, argv, cwd=None) -> bool:
        """Interactive commands (tinker, a REPL): run them in the integrated terminal."""
        term = getattr(self.win, "terminal", None)
        if term is None:
            self.log("*** the Terminal is not available - run it from a command prompt: " + " ".join(argv))
            return False
        argv2, _env = self.resolve_argv(argv)
        cmd = " ".join(f'"{a}"' if " " in a else a for a in argv2)
        folder = str(cwd or self.folder)
        try:
            from .features.terminal import show_terminal
            show_terminal(self.win)
        except Exception:  # noqa: BLE001
            pass
        try:
            if term.folder() != folder:
                term.run_command(f'cd /d "{folder}"' if sys.platform == "win32" else f'cd "{folder}"')
        except Exception:  # noqa: BLE001
            pass
        term.run_command(cmd)
        return True

    # ---------------------------------------------------------------- UI helpers
    def ask(self, fields, title=None, text: str = "") -> dict | None:
        fields = list(fields or [])
        if not fields:
            return {}
        if ASK_HOOK is not None:
            res = ASK_HOOK(fields, title)
            if res is None:
                return None
            vals = {f.name: _default(f) for f in fields}
            vals.update(res)
            return vals
        if os.environ.get("QT_QPA_PLATFORM", "") == "offscreen":
            vals = {f.name: _default(f) for f in fields}
            return None if any(f.is_required() and not vals[f.name] for f in fields) else vals
        dlg = AskDialog(self.win, fields, title or (self.action.title if self.action else "Project Action"), text)
        return dlg.values() if dlg.exec() else None

    def confirm(self, text: str, title: str = "") -> bool:
        if ASK_HOOK is not None or os.environ.get("QT_QPA_PLATFORM", "") == "offscreen":
            return True
        from PyQt6.QtWidgets import QMessageBox
        return QMessageBox.question(self.win, title or (self.action.title if self.action else "Project Action"),
                                    text) == QMessageBox.StandardButton.Yes

    def open_file(self, path, line: int | None = None) -> None:
        p = Path(path)
        if not p.is_absolute():
            p = self.folder / p
        try:
            fn = getattr(self.win, "open_file", None)
            if callable(fn):
                fn(p, line)
            else:
                self.win.open_any_file(p)
        except Exception as e:  # noqa: BLE001
            self.log(f"*** cannot open {p}: {e}")

    def refresh_tree(self) -> None:
        try:
            _rescan_foreign(self.project)
        except Exception as e:  # noqa: BLE001
            self.log(f"*** refresh: {e}")
        try:
            if getattr(self.win, "project", None) is not None:
                self.win._fill_solution()
        except Exception as e:  # noqa: BLE001
            self.log(f"*** refresh: {e}")


def _rescan_foreign(project) -> None:
    """Foreign projects (opened .csproj / .iml / ...) list their files from a scan made when they opened: scan again
    so files a command created show up in Solution Explorer (forms / bindings are kept as they are)."""
    if project is None or not (getattr(project, "extra", None) or {}).get("foreign"):
        return
    if hasattr(project, "ms") and callable(getattr(project, "reload", None)):      # Visual Studio project
        project.reload()
        return
    ad = getattr(project, "adapter", None)
    if ad is None or not callable(getattr(ad, "scan", None)):
        return
    keep = (ad.bindings, list(ad.info), list(ad.modules))
    ad.bindings, ad.modules = {}, []
    try:
        ad.scan()
    except Exception:
        ad.modules = keep[2]
        raise
    finally:
        ad.bindings, ad.info = keep[0], keep[1]
    project.modules = list(ad.modules)


def _default(f: Field):
    if f.kind == "bool":
        return bool(f.default)
    if f.kind == "choice":
        return f.default if f.default is not None else (list(f.choices)[0] if f.choices else "")
    return "" if f.default is None else str(f.default)


# ============================================================================ the ask dialog
def _ask_dialog_class():
    from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

    class _AskDialog(QDialog):
        """Asks only for what an action needs: names as text boxes, options as check boxes."""

        def __init__(self, parent, fields, title, text=""):
            super().__init__(parent)
            self.setWindowTitle(title.replace("&", "").replace("...", ""))
            self.fields = fields
            self.widgets: dict[str, QWidget] = {}
            lay = QVBoxLayout(self)
            if text:
                lbl = QLabel(text)
                lbl.setWordWrap(True)
                lay.addWidget(lbl)
            form = QFormLayout()
            checks = QVBoxLayout()
            first = None
            for f in fields:
                label = f.label or f.name
                if f.kind == "bool":
                    w = QCheckBox(label)
                    w.setChecked(bool(f.default))
                    checks.addWidget(w)
                elif f.kind == "choice":
                    w = QComboBox()
                    w.addItems([str(c) for c in f.choices])
                    if f.default is not None:
                        w.setCurrentText(str(f.default))
                    form.addRow(label + ":", w)
                elif f.kind == "multiline":
                    w = QPlainTextEdit(str(f.default or ""))
                    w.setMaximumHeight(90)
                    form.addRow(label + ":", w)
                elif f.kind == "path":
                    w = QLineEdit(str(f.default or ""))
                    w.setPlaceholderText(f.placeholder)
                    row = QWidget()
                    h = QHBoxLayout(row)
                    h.setContentsMargins(0, 0, 0, 0)
                    h.addWidget(w, 1)
                    b = QPushButton("Browse...")
                    b.clicked.connect(lambda _c=False, e=w: e.setText(
                        QFileDialog.getExistingDirectory(self, "Select Folder", e.text()) or e.text()))
                    h.addWidget(b)
                    form.addRow(label + ":", row)
                else:
                    w = QLineEdit(str(f.default or ""))
                    w.setPlaceholderText(f.placeholder)
                    w.selectAll()
                    form.addRow(label + ":", w)
                if f.help:
                    w.setToolTip(f.help)
                if first is None and f.kind in ("text", "path", "multiline"):
                    first = w
                self.widgets[f.name] = w
            lay.addLayout(form)
            if checks.count():
                lay.addLayout(checks)
            self.box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            self.box.accepted.connect(self._ok)
            self.box.rejected.connect(self.reject)
            lay.addWidget(self.box)
            self.setMinimumWidth(380)
            if first is not None:
                first.setFocus()

        def values(self) -> dict:
            out = {}
            for f in self.fields:
                w = self.widgets[f.name]
                if f.kind == "bool":
                    out[f.name] = w.isChecked()
                elif f.kind == "choice":
                    out[f.name] = w.currentText()
                elif f.kind == "multiline":
                    out[f.name] = w.toPlainText()
                else:
                    out[f.name] = w.text().strip()
            return out

        def _ok(self):
            vals = self.values()
            for f in self.fields:
                if f.is_required() and not vals.get(f.name):
                    self.widgets[f.name].setFocus()
                    return
            self.accept()

    return _AskDialog


class _LazyAsk:
    _cls = None

    def __call__(self, *a, **k):
        if _LazyAsk._cls is None:
            _LazyAsk._cls = _ask_dialog_class()
        return _LazyAsk._cls(*a, **k)


AskDialog = _LazyAsk()


# ============================================================================ running an action
def _call_run(fn, ctx):
    try:
        n = len([p for p in inspect.signature(fn).parameters.values()
                 if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
    except (TypeError, ValueError):
        n = 1
    return fn(ctx, ctx.values) if n >= 2 else fn(ctx)


def run_action(ctx: ActionContext, action: Action, values: dict | None = None):
    """Ask for the action's fields, run it, and open what it created (commands that are not CLIs too)."""
    ctx.action = action
    if not action.is_enabled(ctx):
        _status(ctx.win, f"'{action.title.replace('&', '')}' is not available here")
        return None
    if values is None:
        values = ctx.ask(action.ask, title=action.title.replace("&", "").replace("...", ""))
        if values is None:
            return None
    ctx.values = dict(values)
    before = snapshot(ctx.folder) if action.opens == "created" else None
    t0 = time.time()
    ctx.last_run = None
    try:
        res = _call_run(action.run, ctx)
    except Exception as e:  # noqa: BLE001
        ctx.log(f"*** {action.title}: {e}\n{traceback.format_exc()}")
        return None
    if ctx.last_run is None and before is not None:          # a Python action: diff the folder now
        new = sorted(snapshot(ctx.folder) - before)
        created = [ctx.folder / r for r in new if (ctx.folder / r).is_file()
                   and (ctx.folder / r).stat().st_mtime >= t0 - 2]
        if created or action.refresh:
            ctx.refresh_tree()
        for p in created[:MAX_OPEN]:
            ctx.open_file(p)
    elif ctx.last_run is None and action.refresh:
        ctx.refresh_tree()
    return res if ctx.last_run is None else ctx.last_run


__all__ = ["Action", "ActionContext", "AskDialog", "CliRun", "Field", "LOAD_ERRORS", "Provider", "Separator",
           "Submenu", "clear_cache", "composer_json", "composer_requires", "detect", "files_in_output", "flatten",
           "load_providers", "matches", "package_json", "provider", "providers", "read_json", "read_text",
           "register_provider", "run_action", "running", "safe_items", "snapshot", "unregister_provider"]
