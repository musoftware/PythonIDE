"""Shared base of the "enterprise" backend frameworks: ASP.NET Core, Spring Boot, Ruby on Rails / Sinatra and
NestJS (``aspnet.py``, ``spring.py``, ``rails.py``, ``nestjs.py`` next to this file).

Each framework is a website plugin (``FrameworkPlugin``, a :class:`~radide.web_site.project.WebSitePlugin`) so the
existing web workspace runs it: **F5 / Ctrl+F5** start the :class:`~radide.web_site.server.DevServer` with the
framework's own server behind it (``backend(server)``), the **Preview** and **Requests** docks work as for PHP or
Node sites, and the framework adds (``radide/features/enterprise_web.py``):

- ``routes(project) -> list[Route]`` - the *Routes* list (method, path, handler, file, line),
- ``cli_presets(project)`` / ``cli_argv(project, command)`` / ``cli_env(project)`` - the *CLI* panel
  (``dotnet ef`` / ``mvnw`` / ``rails g`` / ``nest g`` ...),
- ``completion_items(project, path, before)`` - route / view / action names for IntelliSense inside strings,
- ``debug_website(win, project, path)`` - F5 under the framework's debugger (netcoredbg, JDWP, js-debug ...),
- ``tool_status()`` - which tools are installed (shown in the panel, with an install button when we can).

Nothing here needs admin rights: tools go into ``%LOCALAPPDATA%\\RADIDE\\tools|toolchains``.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..project import WEBSITE, WebSitePlugin, web_config

LOCAL = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE"
TOOLS = LOCAL / "tools"
TOOLCHAINS = LOCAL / "toolchains"
EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SKIP_DIRS = {"node_modules", "bin", "obj", "target", "vendor", "dist", "build", ".git", "tmp", "log", "storage",
             ".gradle", ".mvn", ".idea", ".vs", "coverage", ".radide", ".radide_backup"}


@dataclass
class Route:
    method: str              # "GET", "POST", ... or "ANY"
    path: str                # "/products/{id}"
    handler: str = ""        # "ProductsController.Details", "products#show", ...
    file: str = ""           # absolute path of the file that declares it ("" = unknown)
    line: int = 0            # 1-based line (0 = unknown)
    name: str = ""           # route name / helper ("products_path", "Index" ...)

    def url_path(self) -> str:
        """A path the Preview can open (parameters dropped): "/products/{id}" -> "/products"."""
        parts = []
        for seg in self.path.split("/"):
            if not seg or "{" in seg or seg.startswith((":", "*", "(")):
                if seg and ("{" in seg or seg.startswith((":", "*"))):
                    break
                continue
            parts.append(seg)
        return "/" + "/".join(parts)


@dataclass
class Tool:
    name: str                # "netcoredbg"
    path: str                # where it was found ("" = missing)
    purpose: str             # "debugger", "language server", ...
    hint: str = ""           # how to get it
    installer: str = ""      # id passed to plugin.install_tool(id, log) ("" = no automatic install)


# ============================================================================ helpers
def which(*names: str) -> str:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return ""


def run(argv, cwd=None, env=None, timeout=120, log=None) -> tuple[int, str]:
    """Run a command (no window), return (exit code, combined output). *log* gets each output line."""
    full_env = dict(os.environ)
    full_env.update({k: str(v) for k, v in (env or {}).items()})
    try:
        p = subprocess.Popen([str(a) for a in argv], cwd=str(cwd) if cwd else None, env=full_env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             creationflags=NO_WINDOW)
    except OSError as e:
        if log:
            log(f"*** cannot run {argv[0]}: {e}")
        return 127, str(e)
    out: list[str] = []
    try:
        import threading
        timer = threading.Timer(timeout, lambda: _kill(p)) if timeout else None
        if timer:
            timer.start()
        for raw in iter(p.stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip()
            out.append(line)
            if log:
                log(line)
        p.wait()
        if timer:
            timer.cancel()
    finally:
        if p.poll() is None:
            _kill(p)
    return p.returncode, "\n".join(out)


def _kill(p) -> None:
    try:
        from ..server import kill_tree
        kill_tree(p)
    except Exception:  # noqa: BLE001
        try:
            p.kill()
        except OSError:
            pass


def safe_identifier(name: str, default: str = "WebApp") -> str:
    """A name usable as a C# namespace / Java artifact / Ruby constant: letters, digits, _ ; starts with a letter."""
    s = re.sub(r"[^A-Za-z0-9_]", "", name or "")
    if not s or not s[0].isalpha():
        s = default + s
    return s


def split_command(command: str) -> list[str]:
    """Split a CLI command line typed by the user (Windows-friendly: keeps backslashes)."""
    try:
        return shlex.split(command, posix=False) if os.name == "nt" else shlex.split(command)
    except ValueError:
        return command.split()


def unquote_args(argv: list[str]) -> list[str]:
    return [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a for a in argv]


def walk_files(folder: Path, exts: tuple[str, ...], limit: int = 5000):
    """Files of *folder* with one of *exts* (skipping build output, packages, VCS folders)."""
    n = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.lower().endswith(exts):
                yield Path(dirpath) / f
                n += 1
                if n >= limit:
                    return


def read_text(p: Path) -> str:
    try:
        return Path(p).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def join_url(*parts: str) -> str:
    out = "/".join(p.strip("/") for p in parts if p and p.strip("/"))
    return "/" + out


def write_files(folder: Path, files: dict[str, str], overwrite: bool = False) -> None:
    for rel, text in files.items():
        p = Path(folder) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if overwrite or not p.exists():
            p.write_text(text, encoding="utf-8", newline="\n")


def string_context(before: str) -> tuple[str, str] | None:
    """If the cursor is inside a string literal on this line: (text before the opening quote, typed prefix)."""
    quote = None
    start = 0
    i = 0
    while i < len(before):
        c = before[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote, start = c, i
        i += 1
    if quote is None:
        return None
    return before[:start], before[start + 1:]


# ============================================================================ plugin base
class FrameworkPlugin(WebSitePlugin):
    """A backend framework web site (see the module docstring)."""
    project_kind = WEBSITE
    framework = ""                  # "aspnet" | "spring" | "rails" | "nestjs"
    framework_title = ""            # "ASP.NET Core"
    cli_title = "CLI"               # "dotnet CLI", "Rails generators" ...
    needs_interpreter = True
    supports_debug = True
    install_hint = ""
    view_ext: tuple[str, ...] = ()  # template files (.cshtml, .html, .erb ...)

    # ---- tools
    def tool(self) -> str:
        return self.find_interpreter("")

    def tool_status(self) -> list[Tool]:
        return []

    def install_tool(self, tool_id: str, log=print) -> bool:
        log(f"*** {tool_id}: no automatic install")
        return False

    # ---- CLI panel
    def cli_presets(self, project) -> list[tuple[str, str]]:
        """[(label, command line)] - ``{name}`` is replaced by the Name box of the panel."""
        return []

    def cli_env(self, project) -> dict:
        return {}

    def cli_argv(self, project, command: str) -> list[str]:
        """Turn a typed command line into argv (resolves the framework's executables)."""
        return unquote_args(split_command(command))

    def cli_internal(self, project, command: str, log=print) -> bool:
        """Commands the IDE runs itself (code generators without a CLI); True = handled."""
        return False

    # ---- routes / views
    def routes(self, project) -> list[Route]:
        return []

    def view_names(self, project) -> list[str]:
        return []

    def completion_items(self, project, path: Path, before: str) -> list[tuple[str, str, str]] | None:
        """IntelliSense items for the text *before* the cursor on its line: [(label, kind, detail)];
        None = not a framework context (the normal completion runs)."""
        return None

    # ---- debugging (F5)
    def debug_website(self, win, project, path=None):
        return None

    # ---- misc
    def config(self, project) -> dict:
        return web_config(project)

    def generate_designer(self, form, user_code: str) -> str:
        return ""


def filter_prefix(items, prefix: str):
    p = prefix.lower()
    seen = set()
    out = []
    for label, kind, detail in items:
        if label in seen:
            continue
        if not p or p in label.lower():
            seen.add(label)
            out.append((label, kind, detail))
    return out


__all__ = ["FrameworkPlugin", "LOCAL", "NO_WINDOW", "Route", "TOOLCHAINS", "TOOLS", "Tool", "filter_prefix",
           "join_url", "line_of", "read_text", "run", "safe_identifier", "split_command", "string_context",
           "unquote_args", "walk_files", "which", "write_files"]
