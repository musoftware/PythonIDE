"""Base class for language plugins.

To support a new scripting language, add a module in this package that
defines a subclass of LanguagePlugin and sets PLUGIN = MyPlugin().
The IDE discovers it automatically.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..controls import CONTROL_TYPES, FORM_EVENTS, menu_leaves
from ..model import Control, Form


@dataclass
class Completion:
    name: str
    kind: str = ""        # keyword | function | method | class | variable | property | module | control | event
    detail: str = ""      # signature / description shown next to the item


@dataclass
class PackageManager:
    """How a language installs libraries (NuGet, pip, npm, cargo, ...). Commands are
    argv lists run in the project folder; "{name}" / "{query}" / "{version}" are replaced.
    A command may be None when the tool has no such operation."""
    name: str                                   # "pip", "NuGet", "npm", ...
    tool: str                                   # executable looked up in PATH
    list_cmd: list[str] | None = None           # installed packages
    search_cmd: list[str] | None = None
    install_cmd: list[str] | None = None
    uninstall_cmd: list[str] | None = None
    init_cmd: list[str] | None = None           # create the manifest (package.json, .csproj, Cargo.toml...)
    manifest: str = ""                          # file that records dependencies (requirements.txt, ...)
    search_url: str = ""                        # website to browse packages ({query})


@dataclass
class RunSpec:
    program: str
    args: list[str]
    cwd: Path
    env: dict | None = None


class LanguagePlugin:
    id: str = ""                 # e.g. "python-tk"
    display_name: str = ""       # e.g. "Python (Tkinter)"
    code_ext: str = ""           # e.g. ".py"
    interpreter_names: list[str] = []   # executables to look for in PATH
    interpreter_hints: list[str] = []   # extra absolute paths to try

    # --- syntax highlighting (used by the generic RegexLexer) ---
    keywords: list[str] = []
    builtins: list[str] = []
    case_sensitive: bool = True
    line_comments: list[str] = ["#"]
    block_comment: tuple[str, str] | None = None
    string_quotes: list[str] = ['"', "'"]

    # ------------------------------------------------------------------ files
    def code_file(self, form_name: str) -> str:
        return f"{form_name}{self.code_ext}"

    def designer_file(self, form_name: str) -> str:
        return f"{form_name}_designer{self.code_ext}"

    # ------------------------------------------------------------- generation
    def generate_designer(self, form: Form, user_code: str) -> str:
        """Return the auto-generated GUI code for *form*."""
        raise NotImplementedError

    def new_code(self, form: Form, is_startup: bool) -> str:
        """Template for the user-editable code file of a new form."""
        raise NotImplementedError

    def on_form_added(self, startup_code: str, form_name: str) -> str:
        """Let the startup file reference a newly added form (import/load)."""
        return startup_code

    # ---------------------------------------------------------------- events
    def handler_name(self, owner: str, event: str) -> str:
        return f"{owner}_{event}"

    def handler_for(self, form: Form, ctrl: Control | None, event: str) -> str:
        """Handler name for an event. For MenuStrip, *event* is a menu item name."""
        if ctrl is not None and ctrl.type in ("MenuStrip", "ToolStrip"):
            return self.handler_name(event, "Click")
        return self.handler_name(ctrl.name if ctrl else form.name, event)

    def events_for(self, ctrl: Control | None) -> list[str]:
        if ctrl is None:
            return list(FORM_EVENTS)
        if ctrl.type in ("MenuStrip", "ToolStrip"):
            return [it["Name"] for it in menu_leaves(ctrl.props.get("Items", []))]
        return CONTROL_TYPES[ctrl.type].all_events()

    def used_events(self, form: Form, ctrl: Control | None, user_code: str) -> list[str]:
        """Events of ctrl (None = form) that have a handler in user code."""
        return [e for e in self.events_for(ctrl)
                if self.find_handler(user_code, self.handler_for(form, ctrl, e)) >= 0]

    def rename_symbol(self, code: str, old: str, new: str) -> str:
        """Rename an object in user code: `old`, `old_Event`, `oldDesigner`."""
        flags = 0 if self.case_sensitive else re.I
        return re.sub(rf"\b{re.escape(old)}(?=\b|_|Designer\b)", new, code, flags=flags)

    def find_handler(self, code: str, name: str) -> int:
        """Return 0-based line of the handler definition, or -1."""
        raise NotImplementedError

    def add_handler(self, code: str, name: str, form: Form, args: str | None = None) -> tuple[str, int]:
        """Insert an empty handler (args = event-args kind, see controls.EVENT_ARGS).
        Return (new_code, line_for_cursor)."""
        raise NotImplementedError

    # ------------------------------------------------------------- project files
    def module_template(self, name: str) -> str:
        """Content of a new code module (no form)."""
        return ""

    def on_file_added(self, startup_code: str, filename: str) -> str:
        """Let the startup file reference a new module."""
        return startup_code

    def on_file_removed(self, code: str, filename: str) -> str:
        """Remove references (import/load lines) to a deleted file."""
        stem = Path(filename).stem
        flags = 0 if self.case_sensitive else re.I
        rx = re.compile(rf"^\s*(load\s+[\"']{re.escape(filename)}[\"']|from\s+{re.escape(stem)}\s+import\b"
                        rf"|import\s+{re.escape(stem)}\b).*$", flags)
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    def _find_line(self, code: str, pattern: str, flags=0) -> int:
        rx = re.compile(pattern, flags)
        for i, line in enumerate(code.splitlines()):
            if rx.search(line):
                return i
        return -1

    # ------------------------------------------------------------------- run
    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        for n in self.interpreter_names:
            p = shutil.which(n)
            if p:
                return p
        for h in self.interpreter_hints:
            if Path(h).exists():
                return h
        return ""

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        return RunSpec(interpreter, [self.code_file(startup_form)], folder)

    # ----------------------------------------------------------------- debug
    # Debug agents speak a tiny line protocol over stdin/stdout:
    #   agent -> IDE : "@@RADDBG@@<kind>|<field>|<field>..."
    #       stop|file|line|reason   var|name|type|value   frame|func|file|line
    #       wait   eval|text   done
    #   IDE -> agent : c (continue) s (step into) n (step over) o (step out)
    #       q (quit)  e <expr>  b <file>|<line>  B <file>|<line>
    supports_debug: bool = False

    # ----------------------------------------------------------- packages / polyglot
    package_manager: PackageManager | None = None   # see docs/CONTRACTS.md

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        """argv that serves the functions of *module_file* to other languages over
        the RAD Hub worker protocol (docs/CONTRACTS.md). None = not supported."""
        return None

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str,
                   breakpoints: list[tuple[str, int]]) -> RunSpec:
        raise NotImplementedError

    @staticmethod
    def breakpoints_env(breakpoints: list[tuple[str, int]]) -> str:
        return ";".join(f"{Path(f).name.lower()}|{line}" for f, line in breakpoints)

    # ------------------------------------------------------------ completion
    def completions(self, code: str, line: int, col: int, path: Path,
                    names: dict[str, str] | None = None) -> list[Completion]:
        """IntelliSense items at (line, col) (0-based). *names* maps form object
        names to their control type. Default: keywords, builtins, names, words."""
        prefix_line = code.splitlines()[line][:col] if code.splitlines()[line:line + 1] else ""
        if prefix_line.rstrip().endswith(".") or re.search(r"\.\w*$", prefix_line):
            return []
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(b, "function") for b in self.builtins]
        out += [Completion(n, "control", t) for n, t in (names or {}).items()]
        seen = {c.name.lower() for c in out}
        for w in re.findall(r"[A-Za-z_]\w{2,}", code):
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(Completion(w, "variable"))
        return out

    def calltip(self, code: str, line: int, col: int, path: Path,
                names: dict[str, str] | None = None) -> str:
        """Signature help for the call around (line, col), or ""."""
        return ""


def quote(s: str, quotes=('"', "'")) -> str:
    """Return a string literal using a quote char not present in *s*."""
    s = str(s)
    for q in quotes:
        if q not in s:
            return f"{q}{s}{q}"
    return '"' + s.replace('"', "'") + '"'
