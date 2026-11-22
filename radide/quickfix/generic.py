"""Generic quick fix: "Create method 'X'" for a call of a function that the file does not define (C#, VB.NET,
Python). With diagnostics only for a name they call unknown; without any diagnostic on the line it is offered in
the menu (not the light bulb) as a refactoring."""
from __future__ import annotations

import re

from . import Action, Context, followed_by_call, qualified_before, register


def _args(ctx: Context) -> list[str]:
    from .lang_dotnet import _call_args
    s = ctx.line_text
    i = s.find("(", ctx.wend)
    got = _call_args(s, i) if i >= 0 else None
    out = []
    for n, a in enumerate(got[0] if got else []):
        name = a if re.fullmatch(r"[A-Za-z_]\w*", a) else f"arg{n + 1}"
        out.append(name if name not in out else f"arg{n + 1}")
    return out


def _eligible(ctx: Context, declared: bool) -> bool:
    name = ctx.word
    if not name or not followed_by_call(ctx) or declared:
        return False
    if ctx.diagnostics:
        return name in ctx.diag_names()
    return not ctx.cheap


def _py(ctx: Context) -> list[Action]:
    from .lang_python import BUILTINS, defined_names
    recv = qualified_before(ctx)
    if recv and recv != "self":
        return []
    name = ctx.word
    if name in BUILTINS or not _eligible(ctx, name in defined_names(ctx.text) and not recv):
        return []
    if recv == "self" and re.search(rf"^\s*def\s+{re.escape(name)}\s*\(", ctx.text, re.M):
        return []
    args = _args(ctx)
    lines = ctx.lines
    if recv == "self":                       # a method at the end of the enclosing class
        cls = next((i for i in range(ctx.line, -1, -1) if re.match(r"^(\s*)class\s+\w+", lines[i])), None)
        if cls is None:
            return []
        indent = len(lines[cls]) - len(lines[cls].lstrip())
        end = len(lines)
        for i in range(cls + 1, len(lines)):
            s = lines[i]
            if s.strip() and len(s) - len(s.lstrip()) <= indent:
                end = i
                break
        while end > cls + 1 and not lines[end - 1].strip():
            end -= 1
        pad = " " * (indent + 4)
        body = f"\n{pad}def {name}(self{''.join(', ' + a for a in args)}):\n{pad}    pass\n"
        if end >= len(lines):
            last = len(lines) - 1
            edit = [last, len(lines[last]), last, len(lines[last]), body.rstrip("\n")]
        else:
            edit = [end, 0, end, 0, body]
        title = f"Create method '{name}'"
    else:                                    # a function before the top-level statement that calls it
        top = next((i for i in range(ctx.line, -1, -1) if lines[i] and not lines[i][0].isspace()
                    and not lines[i].startswith(("#", "@"))), 0)
        while top > 0 and lines[top - 1].startswith("@"):
            top -= 1
        edit = [top, 0, top, 0, f"def {name}({', '.join(args)}):\n    pass\n\n\n"]
        title = f"Create function '{name}'"
    return [Action(title, kind="quickfix" if ctx.diagnostics else "refactor", edits=ctx.edit([edit]),
                   fixes=list(ctx.diagnostics))]


def _matching_close(lines: list[str], start: int) -> int | None:
    depth, seen = 0, False
    for i in range(start, len(lines)):
        code = re.sub(r'"(?:\\.|[^"\\])*"|//.*$', "", lines[i])
        for ch in code:
            if ch == "{":
                depth += 1
                seen = True
            elif ch == "}":
                depth -= 1
                if seen and depth == 0:
                    return i
    return None


def _cs(ctx: Context) -> list[Action]:
    name = ctx.word
    if qualified_before(ctx) not in ("", "this"):
        return []
    declared = bool(re.search(rf"\b[\w<>\[\],?]+\s+{re.escape(name)}\s*(?:<[^>]*>)?\s*\([^;]*\)\s*(?:\{{|=>|$)",
                              ctx.text, re.M))
    try:
        from ..languages.csharp_bridge import RAD_HELPERS
    except ImportError:
        RAD_HELPERS = {}
    if name in RAD_HELPERS or not name[:1].isupper() and not ctx.diagnostics:
        return []
    if not _eligible(ctx, declared):
        return []
    lines = ctx.lines
    cls = next((i for i in range(ctx.line, -1, -1) if re.search(r"\b(?:class|struct|record)\s+\w+", lines[i])), None)
    if cls is None:
        return []
    close = _matching_close(lines, cls)
    if close is None or close < ctx.line:
        return []
    static = "static " if re.search(r"\bstatic\b", lines[cls]) or any(
        re.search(r"\bstatic\b[^=;]*\(", lines[i]) for i in range(ctx.line, cls, -1)
        if re.search(r"^\s*(?:(?:public|private|internal|protected|static|async|override|virtual)\s+)+[\w<>\[\]?]+\s+\w+\s*\(",
                     lines[i])) else ""
    indent = re.match(r"^\s*", lines[cls]).group(0) + "    "
    params = ", ".join(f"object {a}" for a in _args(ctx))
    body = (f"\n{indent}{static}void {name}({params})\n{indent}{{\n{indent}    "
            f"throw new System.NotImplementedException();\n{indent}}}\n")
    return [Action(f"Create method '{name}'", kind="quickfix" if ctx.diagnostics else "refactor",
                   edits=ctx.edit([[close, 0, close, 0, body]]), fixes=list(ctx.diagnostics))]


def _vb(ctx: Context) -> list[Action]:
    name = ctx.word
    if qualified_before(ctx) not in ("", "Me"):
        return []
    declared = bool(re.search(rf"^\s*(?:(?:Public|Private|Friend|Protected|Shared|Overrides)\s+)*(?:Sub|Function)\s+"
                              rf"{re.escape(name)}\b", ctx.text, re.M | re.I))
    if not _eligible(ctx, declared):
        return []
    lines = ctx.lines
    end = next((i for i in range(ctx.line, len(lines)) if re.match(r"^\s*End\s+(?:Class|Module|Structure)\b",
                                                                   lines[i], re.I)), None)
    params = ", ".join(f"{a} As Object" for a in _args(ctx))
    if end is None:
        last = len(lines) - 1
        edit = [last, len(lines[last]), last, len(lines[last]),
                f"\n\nPrivate Sub {name}({params})\n    Throw New NotImplementedException()\nEnd Sub"]
    else:
        ind = re.match(r"^\s*", lines[end]).group(0) + "    "
        edit = [end, 0, end, 0, f"\n{ind}Private Sub {name}({params})\n{ind}    Throw New NotImplementedException()\n"
                                f"{ind}End Sub\n"]
    return [Action(f"Create method '{name}'", kind="quickfix" if ctx.diagnostics else "refactor",
                   edits=ctx.edit([edit]), fixes=list(ctx.diagnostics))]


def provide(ctx: Context) -> list[Action]:
    if not ctx.word:
        return []
    if ctx.language == "python":
        return _py(ctx)
    if ctx.language == "csharp":
        return _cs(ctx)
    if ctx.language == "vbnet":
        return _vb(ctx)
    return []


register("*", provide)

__all__ = ["provide"]
