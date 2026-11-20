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
from ..references import ExportedFunction
from ..references import proxy_header as _proxy_header


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
    env: dict[str, str] | None = None           # extra environment variables for every command


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
    # Optional (expandable Locals/Watch, radide/debug_extras.py; pyagent + VB implement them):
    #   agent -> IDE : ref|name|handle (the var just sent has children)
    #       kid|name|type|value|handle-or-0 ... kend     watch|type|handle-or-0|value
    #   IDE -> agent : k <handle> (children)   w <expr> (Watch value)
    #   A condition "@@bp {json}" carries hit count / logpoint (debug_extras.parse_bp).
    supports_debug: bool = False

    # ----------------------------------------------------------- packages / polyglot
    package_manager: PackageManager | None = None   # see docs/CONTRACTS.md

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        """argv that serves the functions of *module_file* to other languages over
        the RAD Hub worker protocol (docs/CONTRACTS.md). None = not supported."""
        return None

    # ------------------------------------------------- solutions / References (CONTRACTS 7)
    def exported_functions(self, path: Path, text: str) -> list[ExportedFunction]:
        """Library side: public top-level functions of a code file (skip _private names and
        event handlers). Plugins usually implement it with ``simple_exports``."""
        return []

    def reference_proxy(self, lib: str, functions: list[ExportedFunction]) -> dict[str, str]:
        """Consumer side: {relative file name: content} written into the consumer project so
        that its code calls ``lib.function(args)`` natively (each function forwards to radcall
        with ``fn.target``). Include ``proxy_header(lib)`` in a comment. {} = not supported."""
        return {}

    def proxy_header(self, lib: str) -> str:
        """The AUTO-GENERATED mark of a proxy file as one comment line of this language."""
        text = _proxy_header(lib)
        if self.line_comments:
            return f"{self.line_comments[0]} {text}\n"
        if self.block_comment:
            return f"{self.block_comment[0]} {text} {self.block_comment[1]}\n"
        return text + "\n"

    def example_function(self, name: str) -> str:
        """Example code for a new Class Library module. Two accepted forms (see library_template):
        a *complete module* for library *name* whose first 3 lines mention "Class library", or
        the code of one example public function called *name* (appended to module_template).
        "" = none (a comment is written instead)."""
        return ""

    def library_template(self, name: str) -> str:
        """Content of the module of a new Class Library project *name*:
        example_function(name) when it is a complete module ("Class library" in its first
        3 lines), else module_template(name) + example_function("Add") (or a comment saying
        where functions go). Override when the example must go inside a class/namespace."""
        full = self.example_function(name) or ""
        if full and "class library" in "\n".join(full.splitlines()[:3]).lower():
            return full if full.endswith("\n") else full + "\n"
        text = self.module_template(name) or ""
        example = self.example_function("Add") or ""
        if not example:
            if self.line_comments:
                example = f"{self.line_comments[0]} Public functions of {name} go here - projects that reference " \
                          f"{name} can call them.\n"
            elif self.block_comment:
                example = f"{self.block_comment[0]} Public functions of {name} go here {self.block_comment[1]}\n"
        if text and not text.endswith("\n"):
            text += "\n"
        return text + example

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str,
                   breakpoints: list[tuple[str, int]]) -> RunSpec:
        raise NotImplementedError

    @staticmethod
    def breakpoints_env(breakpoints: list[tuple[str, int]]) -> str:
        out = []
        for bp in breakpoints:
            f, line = bp[0], bp[1]
            cond = bp[2] if len(bp) > 2 and bp[2] else ""
            out.append(f"{Path(f).name.lower()}|{line}" + (f"|{cond}" if cond else ""))
        return ";".join(out)

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


# ============================================================================ References helpers
_EVENT_NAMES: set[str] | None = None


def is_event_handler(name: str) -> bool:
    """True for ``<Object>_<Event>`` names (cmdGo_Click, Form1_Load, mnuOpen_Click, ...)."""
    global _EVENT_NAMES
    if _EVENT_NAMES is None:
        names = {e.lower() for e in FORM_EVENTS} | {"click"}
        for ct in CONTROL_TYPES.values():
            names |= {e.lower() for e in ct.all_events()}
        _EVENT_NAMES = names
    owner, us, event = name.rpartition("_")
    return bool(us and owner and event.lower() in _EVENT_NAMES)


_PARAM_SKIP = {"byval", "byref", "optional", "paramarray", "const", "final", "ref", "out", "in", "var",
               "mut", "readonly", "params", "this", "self", "cls", "struct", "unsigned", "signed", "inout"}


def split_params(params: str) -> list[str]:
    """Split a parameter list at top-level commas (brackets/quotes aware)."""
    out, depth, cur, q = [], 0, "", ""
    for ch in params:
        if q:
            cur += ch
            if ch == q:
                q = ""
            continue
        if ch in "\"'":
            q = ch
        elif ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        elif ch == "," and depth <= 0:
            out.append(cur)
            cur = ""
            continue
        cur += ch
    if cur.strip():
        out.append(cur)
    return [p.strip() for p in out if p.strip()]


def param_names(params: str, style: str = "auto") -> list[str]:
    """Parameter names of a parameter list written in (almost) any language.

    style: "auto" - ``a: int`` / ``a As Integer`` -> the word before ``:``/``As``, otherwise the
    last identifier (C, Java, C#: ``int a``); "first" - the first identifier (Go ``a int``,
    Fortran, Ring, Lua, ...); "last" - always the last identifier. ``self``/``this``/``cls``,
    defaults (``= 3``), sigils (``$a``, ``*args``, ``&b``) and modifiers (ByVal, ref, mut) go away."""
    names = []
    for piece in split_params(params):
        piece = piece.split("=", 1)[0].strip()
        m = re.match(r"(?i)^(.*?)\s+as\s+", piece)
        if style == "auto" and m:
            piece = m.group(1)
        elif style == "auto" and ":" in piece and "::" not in piece:
            piece = piece.split(":", 1)[0]
        piece = re.sub(r"<[^<>]*>|\[[^\]]*\]", " ", piece)       # generics / array brackets
        words = [w for w in re.findall(r"[A-Za-z_؀-ۿ][\w؀-ۿ]*", piece)
                 if w.lower() not in _PARAM_SKIP]
        if not words:
            continue
        names.append(words[0] if style == "first" else words[-1])
    if params.strip().lower() in ("void",):
        return []
    return names


def simple_exports(text: str, pattern: str, module: str, *, flags: int = re.M,
                   style: str = "auto", comment_prefixes: tuple[str, ...] = ("#", "//", "'", "--", ";", "!"),
                   kind_of=None, public=None, skip_private: bool = True,
                   skip_handlers: bool = True) -> list[ExportedFunction]:
    """Generic exported_functions(): find every match of *pattern* in *text*.

    *pattern* must have a ``name`` group and may have ``params`` (the text between the
    parentheses) and ``kind`` groups. ``kind_of(match) -> "function" | "sub"`` decides the kind
    (default: "sub" when the ``kind`` group is sub/void/procedure/subroutine, else "function").
    ``public(match) -> bool`` can drop non-exported definitions. The doc is the comment line(s)
    just above the definition (``///``, ``#``, ``'`` ...), or a docstring on the next line.
    Names starting with ``_`` and ``<Obj>_<Event>`` handlers are skipped."""
    out: list[ExportedFunction] = []
    lines = text.splitlines()
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln) + 1)
    import bisect
    seen: set[str] = set()
    for m in re.finditer(pattern, text, flags):
        name = m.group("name")
        if not name or name.lower() in seen:
            continue
        if skip_private and name.startswith("_"):
            continue
        if skip_handlers and is_event_handler(name):
            continue
        if public is not None and not public(m):
            continue
        gd = m.groupdict()
        params = param_names(gd.get("params") or "", style)
        if kind_of is not None:
            kind = kind_of(m) or "function"
        else:
            k = (gd.get("kind") or "").strip().lower()
            kind = "sub" if k in ("sub", "void", "procedure", "subroutine") else "function"
        line = bisect.bisect_right(starts, m.start()) - 1
        doc = _doc_above(lines, line, comment_prefixes) or _docstring_below(lines, line)
        seen.add(name.lower())
        out.append(ExportedFunction(name, params, module, doc, kind))
    return out


def _doc_above(lines: list[str], line: int, prefixes: tuple[str, ...]) -> str:
    i = line - 1
    block: list[str] = []
    while i >= 0:
        s = lines[i].strip()
        if not s:
            break
        if s.startswith(("/**", "*", "*/", "/*")):
            body = s.strip("/* ").strip()
            if body and not body.startswith("@"):
                block.insert(0, body)
            i -= 1
            continue
        pre = next((p for p in sorted(prefixes, key=len, reverse=True) if s.startswith(p)), None)
        if pre is None:
            break
        body = s.lstrip(pre[0]).strip().lstrip("/!").strip()
        if body:
            block.insert(0, body)
        i -= 1
    return block[0] if block else ""


def _docstring_below(lines: list[str], line: int) -> str:
    for s in lines[line + 1:line + 3]:
        s = s.strip()
        if s.startswith(('"""', "'''")):
            body = s[3:].split(s[:3])[0].strip()
            return body
        if s:
            break
    return ""
