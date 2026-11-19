"""Prompt context from the IDE for @-mentions (docs/CONTRACTS.md 9.1):

    @file:path   a file (relative to the project / solution, or absolute; quotes allowed: @file:"a b.py")
    @selection   the selection (or the whole current file when nothing is selected)
    @current     the current file
    @problems    the Error List
    @form        the current form (.form JSON)
    @project     the file tree of the project / solution
    @git         git status + diff (staged and unstaged)
    @terminal    the last Terminal output
    @output      the last Output window text

gather(win, mentions) accepts a list (["@file:a.py", "@git"]) or a text containing mentions and
returns one markdown string truncated to a token budget (about 4 characters per token)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

MENTIONS = {
    "@file:": "a file of the project",
    "@selection": "the selected code (or the current file)",
    "@current": "the current file",
    "@problems": "the Error List",
    "@form": "the current form (.form JSON)",
    "@project": "the project's file tree",
    "@git": "git status and diff",
    "@terminal": "the last Terminal output",
    "@output": "the last Output window text",
}
_RX = re.compile(r'@(file:(?:"[^"]+"|\S+)|(?:selection|current|problems|form|project|git|terminal|output)\b)')
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".radide", ".radide_backup", "dist",
             "build", ".idea", ".vs", "vendor", ".mypy_cache", ".pytest_cache"}


def parse_mentions(text: str) -> list[str]:
    """The @-mentions of a text, in order, without duplicates."""
    out = []
    for m in _RX.finditer(text or ""):
        tok = "@" + m.group(1)
        if tok.startswith("@file:"):
            tok = "@file:" + tok[6:].strip('"').rstrip(".,;:)")
        if tok not in out:
            out.append(tok)
    return out


def strip_mentions(text: str) -> str:
    return re.sub(r"[ \t]{2,}", " ", _RX.sub("", text or "")).strip()


def lang_of(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".py": "python", ".pyw": "python", ".js": "javascript", ".ts": "typescript", ".html": "html",
            ".htm": "html", ".css": "css", ".php": "php", ".vb": "vb", ".bas": "vb", ".ring": "ring",
            ".json": "json", ".form": "json", ".sql": "sql", ".md": "markdown", ".xml": "xml",
            ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".java": "java", ".rb": "ruby", ".go": "go",
            ".rs": "rust", ".lua": "lua", ".tcl": "tcl", ".sh": "bash", ".ps1": "powershell"}.get(ext, ext[1:])


# ===================================================================== IDE accessors (all defensive)
def project_folder(win) -> Path | None:
    p = getattr(win, "project", None)
    if p is not None and getattr(p, "folder", None):
        return Path(p.folder)
    return None


def solution_folder(win) -> Path | None:
    sln = getattr(win, "sln", None)
    for attr in ("folder", "path"):
        v = getattr(sln, attr, None) if sln is not None else None
        if v:
            v = Path(v)
            return v if v.is_dir() else v.parent
    return project_folder(win)


def current_editor(win):
    """(editor widget, file path or '') of the active tab."""
    try:
        w = win._current_code() if hasattr(win, "_current_code") else None
    except Exception:  # noqa: BLE001
        w = None
    if w is None:
        tabs = getattr(win, "tabs", None)
        w = tabs.currentWidget() if tabs is not None else None
    if w is None:
        return None, ""
    ed = getattr(w, "editor", None) or (w if hasattr(w, "toPlainText") else None)
    path = ""
    for obj in (w, ed):
        for attr in ("path", "file_path", "filename"):
            v = getattr(obj, attr, None) if obj is not None else None
            if v and not callable(v):
                path = str(v)
                break
        if path:
            break
    if not path and getattr(w, "doc", None) is not None:
        path = str(getattr(w.doc, "path", "") or "")
    return ed, path


def editor_text(ed) -> str:
    if ed is None:
        return ""
    for name in ("toPlainText", "text"):
        f = getattr(ed, name, None)
        if callable(f):
            try:
                return str(f())
            except Exception:  # noqa: BLE001
                continue
    return ""


def selected_text(ed) -> str:
    if ed is None:
        return ""
    try:
        if hasattr(ed, "selectedText"):
            return str(ed.selectedText() or "")
        cur = ed.textCursor()
        return str(cur.selectedText()).replace(" ", "\n")
    except Exception:  # noqa: BLE001
        return ""


def problems(win) -> list[dict]:
    tree = getattr(win, "error_list", None)
    out = []
    if tree is None:
        return out
    try:
        for i in range(tree.topLevelItemCount()):
            it = tree.topLevelItem(i)
            out.append({"severity": it.text(0), "message": it.text(1), "file": it.text(2), "line": it.text(3)})
    except Exception:  # noqa: BLE001
        pass
    return out


def _open_text(win, path: Path) -> str | None:
    """The unsaved editor text of a file when it is open, else None."""
    try:
        for coll in ("codeviews", "modviews"):
            for v in (getattr(win, coll, None) or {}).values():
                p = getattr(getattr(v, "editor", None), "path", None) or getattr(v, "path", None)
                if p and os.path.normcase(str(Path(p).resolve())) == os.path.normcase(str(path.resolve())):
                    return editor_text(getattr(v, "editor", None))
    except Exception:  # noqa: BLE001
        pass
    return None


def resolve_file(win, name: str) -> Path | None:
    p = Path(name)
    if p.is_absolute():
        return p if p.is_file() else None
    for base in filter(None, (project_folder(win), solution_folder(win))):
        cand = base / name
        if cand.is_file():
            return cand
    base = solution_folder(win)
    if base is not None:                       # by file name anywhere in the tree
        for f in iter_files(base, limit=5000):
            if f.name.lower() == p.name.lower():
                return f
    return None


def iter_files(root: Path, limit: int = 2000):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            yield Path(dirpath) / fn
            n += 1
            if n >= limit:
                return


def file_tree(root: Path, limit: int = 400) -> str:
    lines = []
    for f in iter_files(root, limit):
        lines.append(str(f.relative_to(root)).replace("\\", "/"))
    if len(lines) >= limit:
        lines.append(f"... (more than {limit} files)")
    return "\n".join(lines)


def git_diff(win, max_chars: int = 30000) -> str:
    folder = solution_folder(win)
    if folder is None:
        return ""
    try:
        from ..features.git_panel import Git
    except Exception:  # noqa: BLE001
        return ""
    g = Git(folder)
    code, status = g.run("status", "--short", "--branch")
    if code != 0:
        return ""
    _c, staged = g.run("diff", "--cached", "--no-color")
    _c, unstaged = g.run("diff", "--no-color")
    out = f"$ git status --short --branch\n{status.strip()}\n"
    if staged.strip():
        out += f"\n$ git diff --cached\n{staged.strip()}\n"
    if unstaged.strip():
        out += f"\n$ git diff\n{unstaged.strip()}\n"
    return out[:max_chars]


def staged_diff(win, max_chars: int = 30000) -> str:
    """The staged diff (for commit messages); empty when nothing is staged."""
    folder = solution_folder(win)
    if folder is None:
        return ""
    try:
        from ..features.git_panel import Git
        _c, text = Git(folder).run("diff", "--cached", "--no-color")
    except Exception:  # noqa: BLE001
        return ""
    return text[:max_chars]


def _last_lines(widget, n_chars: int = 6000) -> str:
    try:
        t = widget.toPlainText()
    except Exception:  # noqa: BLE001
        return ""
    return t[-n_chars:]


def current_form_json(win) -> tuple[str, str]:
    """(form name, JSON text) of the current designer (or of the form of the current code view)."""
    d = None
    try:
        d = win._current_designer()
    except Exception:  # noqa: BLE001
        pass
    doc = getattr(d, "doc", None)
    if doc is None:
        w = getattr(getattr(win, "tabs", None), "currentWidget", lambda: None)()
        doc = getattr(w, "doc", None)
    form = getattr(doc, "form", None)
    if form is None:
        return "", ""
    try:
        data = form.to_dict()
    except Exception:  # noqa: BLE001
        return "", ""
    return str(getattr(form, "name", "") or ""), json.dumps(data, indent=1, ensure_ascii=False)


# ===================================================================== gather
def _fence(lang: str, text: str) -> str:
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{lang}\n{text.rstrip()}\n{fence}"


def section(win, mention: str) -> tuple[str, str] | None:
    """(title, body) for one mention, or None when it gives nothing."""
    m = mention.strip()
    if m.startswith("@file:"):
        name = m[6:].strip().strip('"')
        path = resolve_file(win, name)
        if path is None:
            return f"File {name}", "(file not found)"
        text = _open_text(win, path)
        if text is None:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                text = f"(cannot read: {e})"
        base = solution_folder(win)
        shown = str(path.relative_to(base)) if base and path.is_relative_to(base) else str(path)
        return f"File {shown}", _fence(lang_of(str(path)), text)
    if m in ("@selection", "@current"):
        ed, path = current_editor(win)
        sel = selected_text(ed) if m == "@selection" else ""
        if sel.strip():
            return f"Selected code in {Path(path).name or 'the editor'}", _fence(lang_of(path), sel)
        text = editor_text(ed)
        if not text.strip():
            return None
        return f"Current file {Path(path).name or ''}".strip(), _fence(lang_of(path), text)
    if m == "@problems":
        ps = problems(win)
        if not ps:
            return "Error List", "(no problems)"
        body = "\n".join(f"- {p['severity']}: {p['message']} ({p['file']}:{p['line']})" for p in ps[:200])
        return "Error List", body
    if m == "@form":
        name, js = current_form_json(win)
        if not js:
            return None
        return f"Form {name}", _fence("json", js)
    if m == "@project":
        root = solution_folder(win)
        if root is None:
            return None
        proj = getattr(win, "project", None)
        head = f"Project: {getattr(proj, 'name', '')} (language: {getattr(proj, 'language', '')}, " \
               f"kind: {getattr(proj, 'kind', '')})\nFolder: {root}\n" if proj is not None else f"Folder: {root}\n"
        return "Project files", head + _fence("", file_tree(root))
    if m == "@git":
        d = git_diff(win)
        return ("Git", _fence("diff", d)) if d else ("Git", "(not a git repository)")
    if m == "@terminal":
        term = getattr(win, "terminal", None)
        t = _last_lines(getattr(term, "out", None)) if term is not None else ""
        return ("Terminal output", _fence("", t)) if t.strip() else None
    if m == "@output":
        t = _last_lines(getattr(win, "output", None))
        return ("Output window", _fence("", t)) if t.strip() else None
    return None


def gather(win, mentions, budget_tokens: int = 8000) -> str:
    """Markdown context for the given mentions (list or text), within about budget_tokens."""
    if isinstance(mentions, str):
        mentions = parse_mentions(mentions)
    budget = max(500, int(budget_tokens) * 4)
    parts, used = [], 0
    for mention in mentions or []:
        try:
            sec = section(win, mention)
        except Exception as e:  # noqa: BLE001 - context must never break a request
            sec = (mention, f"(could not read: {e})")
        if sec is None:
            continue
        title, body = sec
        room = budget - used - len(title) - 10
        if room <= 200:
            parts.append(f"## {title}\n(omitted: context budget reached)")
            break
        if len(body) > room:
            body = body[:room] + "\n... (truncated)"
            if body.count("```") % 2:
                body += "\n```"
        parts.append(f"## {title}\n{body}")
        used += len(title) + len(body) + 10
    return "\n\n".join(parts)


def build_prompt(win, text: str, budget_tokens: int = 8000) -> str:
    """The user's text with the context of its @-mentions prepended."""
    ctx = gather(win, text, budget_tokens)
    q = strip_mentions(text) or text
    return f"Context from the IDE:\n\n{ctx}\n\n---\n\n{q}" if ctx else q


__all__ = ["MENTIONS", "parse_mentions", "strip_mentions", "gather", "build_prompt", "section", "problems",
           "current_editor", "selected_text", "editor_text", "current_form_json", "git_diff", "staged_diff",
           "file_tree", "resolve_file", "project_folder", "solution_folder", "lang_of"]
