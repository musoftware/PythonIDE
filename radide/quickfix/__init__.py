"""Built-in quick fixes (the light bulb / Ctrl+. / Alt+Enter), with or without a language server.

A provider is a function ``fn(ctx: Context) -> list[Action]`` registered for one or more languages::

    from radide import quickfix
    quickfix.register(("python",), my_provider)

``collect(ctx)`` runs every provider of ``ctx.language`` (and the generic ``"*"`` ones), drops duplicates and
puts the preferred actions first. radide/features/refactor.py merges the result with the language server's
``textDocument/codeAction`` answer (``merge``: an action whose edit gives the same text, or whose title is the
same, is shown once - the server's copy wins) and radide/quickfix/ui.py shows the menu, the preview and the
light bulb.

Providers live in lang_*.py (python, dotnet, web = JavaScript / TypeScript / PHP, systems = Rust / Go / Java)
and generic.py ("Create method 'X'"); installs (pip, npm, cargo, go get, composer, dotnet add package) go through
installers.py and the shared progress API (radide/progress.py). Pure Python: no Qt here, so the providers can be
unit-tested without a window.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# file extension -> quick-fix language id (Monaco ids where they exist)
EXT_LANG = {".py": "python", ".pyw": "python", ".cs": "csharp", ".vb": "vbnet", ".js": "javascript",
            ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript", ".ts": "typescript",
            ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript", ".rs": "rust", ".go": "go",
            ".java": "java", ".php": "php", ".phtml": "php"}
IDENT = re.compile(r"[A-Za-z_][\w]*")


@dataclass
class Action:
    """One entry of the Quick Actions menu."""
    title: str
    kind: str = "quickfix"                     # quickfix | refactor | source
    edits: dict | None = None                  # {path: [[l1, c1, l2, c2, text], ...]} (0-based)
    run: Callable | None = None                # fn(win, ed) after the edits (installs, dialogs ...)
    preferred: bool = False
    disabled: str = ""                         # a reason -> shown greyed out with this tool tip
    detail: str = ""                           # preview text for actions without edits ("pip install ...")
    provider: str = ""
    fixes: list = field(default_factory=list)  # diagnostics the action fixes (their squiggles go away)
    lsp: dict | None = None                    # the server's CodeAction / Command (merge)

    def file_edits(self, path) -> list:
        if not self.edits:
            return []
        key = _key(path)
        return next((e for p, e in self.edits.items() if _key(p) == key), [])


@dataclass
class Context:
    text: str
    path: Path
    language: str
    line: int
    col: int
    word: str = ""
    wstart: int = 0
    wend: int = 0
    diagnostics: list = field(default_factory=list)   # [{line, col, endLine, endCol, message, code}] on the line
    win: object = None
    ed: object = None
    plugin_id: str = ""
    cheap: bool = False                        # the light bulb: no network / subprocess / big project scans

    @property
    def lines(self) -> list[str]:
        cached = self.__dict__.get("_lines")
        if cached is None:
            cached = self.text.split("\n")
            self.__dict__["_lines"] = cached
        return cached

    @property
    def line_text(self) -> str:
        return self.lines[self.line] if 0 <= self.line < len(self.lines) else ""

    @property
    def project_folder(self) -> Path:
        """A RAD project (project.radproj), the IDE's open project / folder, else the file's folder."""
        cached = self.__dict__.get("_folder")
        if cached is not None:
            return cached
        found = rad_project_folder(self.path)
        if found is None:
            proj = getattr(self.win, "project", None)
            folder = getattr(proj, "folder", None)
            try:
                if folder is not None and Path(self.path).resolve().is_relative_to(Path(folder).resolve()):
                    found = Path(folder)
            except (OSError, ValueError):
                found = None
        found = found or Path(self.path).parent
        self.__dict__["_folder"] = found
        return found

    def diag_names(self) -> list[str]:
        """Identifiers the diagnostics on this line call unknown / undefined / unresolved."""
        return [n for d in self.diagnostics for n in unresolved_names(d.get("message", ""))]

    def edit(self, edits: list) -> dict:
        return {str(self.path): edits}


def _key(p) -> str:
    try:
        return str(Path(p).resolve()).lower()
    except OSError:
        return str(p).lower()


def rad_project_folder(path) -> Path | None:
    """The folder of the RAD project (project.radproj) that holds *path*, else None."""
    try:
        p = Path(path).resolve()
    except OSError:
        return None
    for d in [p.parent, *list(p.parent.parents)[:3]]:
        if (d / "project.radproj").is_file():
            return d
    return None


# messages of the common compilers / servers that name an unknown identifier or module
_UNRESOLVED = [
    re.compile(r"undefined name ['\"`]([\w.]+)['\"`]", re.I),                      # pyflakes / pylsp
    re.compile(r"['\"`]([\w.]+)['\"`] is not defined", re.I),                      # pyright / eslint
    re.compile(r"Import ['\"`]([\w.]+)['\"`] could not be resolved", re.I),        # pyright
    re.compile(r"No module named ['\"`]([\w.]+)['\"`]", re.I),
    re.compile(r"Unable to import ['\"`]([\w.]+)['\"`]", re.I),                    # pylint
    re.compile(r"The (?:type or namespace )?name ['\"`]([\w.<>,]+)['\"`] (?:could not be found|does not exist)",
               re.I),                                                              # CS0246 / CS0103
    re.compile(r"['\"`]([\w.]+)['\"`] is not declared", re.I),                     # BC30451 (VB)
    re.compile(r"Type ['\"`]([\w.]+)['\"`] is not defined", re.I),                 # BC30002 (VB)
    re.compile(r"Cannot find (?:name|module) ['\"`]([^'\"`]+)['\"`]", re.I),       # TS2304 / TS2307
    re.compile(r"Could not find a declaration file for module ['\"`]([^'\"`]+)['\"`]", re.I),   # TS7016
    re.compile(r"(?:failed to resolve|unresolved import|use of undeclared (?:crate or module|type))"
               r"[^`]*`([\w:]+)`", re.I),                                         # rustc / rust-analyzer
    re.compile(r"cannot find (?:type|value|struct|function|macro|trait) `([\w]+)`", re.I),
    re.compile(r"undefined: (\w+)", re.I),                                         # go
    re.compile(r"could not import ([\w./-]+)", re.I),                             # gopls
    re.compile(r"cannot find symbol[\s\S]*?symbol:\s*(?:class|variable|method)\s+(\w+)", re.I),   # javac
    re.compile(r"(\w+) cannot be resolved(?: to a type)?", re.I),                 # jdt.ls
    re.compile(r"Undefined (?:type|function|class|constant) ['\"`]?([\w\\]+)", re.I),   # intelephense
]


def unresolved_names(message: str) -> list[str]:
    out = []
    for rx in _UNRESOLVED:
        for m in rx.finditer(message or ""):
            n = m.group(1).strip()
            if n and n not in out:
                out.append(n)
    return out


# ============================================================================ registry
PROVIDERS: dict[str, list] = {}


def register(languages, fn) -> None:
    for lang in ([languages] if isinstance(languages, str) else languages):
        lst = PROVIDERS.setdefault(lang, [])
        if fn not in lst:
            lst.append(fn)


def unregister(fn) -> None:
    for lst in PROVIDERS.values():
        if fn in lst:
            lst.remove(fn)


_loaded = False


def load_builtin() -> None:
    """Import the bundled providers (idempotent)."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    import importlib
    for mod in ("lang_python", "lang_dotnet", "lang_web", "lang_systems", "generic"):     # they register
        importlib.import_module(f"{__name__}.{mod}")


def language_of(path, ed=None) -> str:
    lang = EXT_LANG.get(Path(str(path)).suffix.lower(), "")
    if not lang and ed is not None and hasattr(ed, "language_id"):
        try:
            lid = ed.language_id()
        except Exception:  # noqa: BLE001
            lid = ""
        lang = {"python": "python", "csharp": "csharp", "javascript": "javascript", "typescript": "typescript",
                "rust": "rust", "go": "go", "java": "java", "php": "php"}.get(lid, "")
    return lang


def make_context(text: str, path, line: int, col: int, diagnostics=None, win=None, ed=None, cheap=False,
                 language: str = "") -> Context:
    from ..features.refactor import word_at
    word, s, e = word_at(text, line, col)
    diags = [d for d in (diagnostics or []) if d.get("line", -1) <= line <= d.get("endLine", d.get("line", -1))]
    plugin = getattr(ed, "plugin", None)
    return Context(text=text, path=Path(str(path)), language=language or language_of(path, ed), line=line, col=col,
                   word=word, wstart=s, wend=e, diagnostics=diags, win=win, ed=ed,
                   plugin_id=str(getattr(plugin, "id", "") or ""), cheap=cheap)


def collect(ctx: Context) -> list[Action]:
    """Every built-in action for ctx (providers that fail are skipped), duplicates dropped, preferred first."""
    load_builtin()
    out: list[Action] = []
    specific = list(PROVIDERS.get(ctx.language, []))
    for fn in specific + list(PROVIDERS.get("*", [])):
        if out and fn not in specific:        # the generic ones ("Create method") only when nothing better fits
            break
        try:
            got = fn(ctx) or []
        except Exception as e:  # noqa: BLE001 - a broken provider must never break the menu
            print(f"[quickfix] {getattr(fn, '__name__', fn)}: {e}")
            continue
        for a in got:
            if not a.provider:
                a.provider = getattr(fn, "__module__", "").rsplit(".", 1)[-1]
            out.append(a)
    return dedup(out, ctx.text, ctx.path)


def norm_title(title: str) -> str:
    t = re.sub(r"[\s'\"`“”‘’]+", " ", (title or "").lower()).strip()
    return t.rstrip(" ;.")


def result_text(action: Action, text: str, path) -> str | None:
    """The file's text after the action's edits (None when it has no edits for this file)."""
    from ..editkit import apply_edits_to_text
    edits = action.file_edits(path)
    if not edits:
        return None
    try:
        return apply_edits_to_text(text, edits)
    except Exception:  # noqa: BLE001
        return None


def dedup(actions: list[Action], text: str, path) -> list[Action]:
    seen_titles, seen_results, out = set(), set(), []
    for a in actions:
        t = norm_title(a.title)
        r = result_text(a, text, path)
        other_files = {(_key(p), repr(e)) for p, e in (a.edits or {}).items() if _key(p) != _key(path)}
        rkey = (r, frozenset(other_files)) if r is not None else None
        if t in seen_titles or (rkey is not None and rkey in seen_results and a.run is None):
            continue
        seen_titles.add(t)
        if rkey is not None:
            seen_results.add(rkey)
        out.append(a)
    out.sort(key=lambda a: (bool(a.disabled), not a.preferred))
    return out


def from_lsp(item: dict) -> Action:
    """A server CodeAction / Command as an Action (applied by refactor.run_code_action)."""
    from ..editkit import workspace_changes
    edits = workspace_changes(item["edit"]) if isinstance(item.get("edit"), dict) else None
    kind = str(item.get("kind") or "")
    group = next((k for k in ("quickfix", "refactor", "source") if kind.startswith(k)), "")
    dis = item.get("disabled")
    return Action(title=str(item.get("title") or "?"), kind=group, edits=edits or None,
                  preferred=bool(item.get("isPreferred")),
                  disabled=(dis.get("reason", "disabled") if isinstance(dis, dict) else ""), provider="lsp", lsp=item)


def merge(builtin: list[Action], lsp_items: list, text: str, path) -> list[Action]:
    """The server's actions first (they know the code best), then the built-in ones they do not already offer."""
    server = [from_lsp(i) for i in (lsp_items or []) if isinstance(i, dict)]
    return dedup(server + list(builtin), text, path)


# ============================================================================ shared edit helpers
def insert_line_edit(lines: list[str], index: int, new_line: str) -> list:
    """[[index, 0, index, 0, new_line + "\\n"]] (or appended after the last line)."""
    if index >= len(lines):
        last = len(lines) - 1
        return [[last, len(lines[last]), last, len(lines[last]), "\n" + new_line]]
    return [[index, 0, index, 0, new_line + "\n"]]


def import_block_insert(lines: list[str], rx: re.Pattern, new_line: str, sort_key=None,
                        after: re.Pattern | None = None) -> list:
    """Insert *new_line* into the first block of lines matching *rx* (sorted when sort_key is given), else after
    the last line matching *after* (a package / namespace line) or the leading comments."""
    block = [i for i, ln in enumerate(lines) if rx.match(ln)]
    if block:
        first = [block[0]]
        for i in block[1:]:
            if i != first[-1] + 1:
                break
            first.append(i)
        ins = first[-1] + 1
        if sort_key is not None:
            for i in first:
                if sort_key(new_line) < sort_key(lines[i]):
                    ins = i
                    break
        return insert_line_edit(lines, ins, new_line)
    if after is not None:
        hits = [i for i, ln in enumerate(lines) if after.match(ln)]
        if hits:
            return [[hits[-1] + 1, 0, hits[-1] + 1, 0, "\n" + new_line + "\n"]] if hits[-1] + 1 < len(lines) \
                else insert_line_edit(lines, hits[-1] + 1, new_line)
    ins = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith(("#!", "//", "/*", "*", "#", "'", "<?php", "--")) and not s.startswith("#[") \
                and not s.startswith("#include"):
            ins = i + 1
            continue
        break
    ins = min(ins, len(lines))
    tail = "\n" if ins < len(lines) and lines[ins].strip() else ""
    if ins >= len(lines):
        return insert_line_edit(lines, ins, new_line)
    return [[ins, 0, ins, 0, new_line + "\n" + tail]]


def replace_word(ctx: Context, new: str) -> dict:
    return ctx.edit([[ctx.line, ctx.wstart, ctx.line, ctx.wend, new]])


def qualified_before(ctx: Context) -> str:
    """'np' for the caret on 'array' in 'np.array' -> the receiver, else ''."""
    before = ctx.line_text[:ctx.wstart]
    m = re.search(r"([A-Za-z_]\w*)\s*\.\s*$", before)
    return m.group(1) if m else ""


def followed_by_call(ctx: Context) -> bool:
    return bool(re.match(r"\s*\(", ctx.line_text[ctx.wend:]))


def candidates(ctx: Context) -> list[str]:
    """Names to fix: the diagnostics' unknown names on this line, else the word under the caret."""
    names = [n for n in ctx.diag_names()]
    if ctx.word and ctx.word not in names:
        names.append(ctx.word)
    return names


__all__ = ["Action", "Context", "register", "unregister", "collect", "merge", "dedup", "make_context",
           "language_of", "unresolved_names", "rad_project_folder", "import_block_insert", "insert_line_edit",
           "EXT_LANG", "PROVIDERS", "load_builtin", "from_lsp", "norm_title", "result_text"]
