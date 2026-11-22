"""AI Chat (docs/CONTRACTS.md 9.3) - the "AI Chat" dock, also shown in the VS Code side bar and
the Agent layout of radide/features/workbench.py.

* provider / model picker over every radide.ai provider (CLI agents signed in with the user's own
  account, local models such as Ollama, API keys, web chats); "Auto" = the best available free one,
* streaming Markdown answers (QWebEngine view, code highlighted with Pygments), every paragraph gets
  its own direction so Arabic questions and answers read right-to-left while code stays left-to-right,
* code blocks: Copy / Insert at cursor / Apply to file (diff review: radide/ai/diffview.py) /
  New file / Run in Terminal,
* @-mentions (@file:, @selection, @problems, @form, @project, @git, @terminal, @output) with
  completion, "Add file" / "Add selection" chips, Stop, Regenerate, New chat,
* history per project in <solution or project folder>/.radide/ai/chats/<id>.json,
* "Ask AI about This" in the editor and Solution Explorer context menus.

Other features can use:  ask(win, text, mentions=(), send=False), attach(win, mention),
insert_code(win, code), apply_code(win, code, path=None, lang="")."""
from __future__ import annotations

import html
import json
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PyQt6.QtCore import QEvent, QObject, QStringListModel, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence, QTextCursor, QTextOption
from PyQt6.QtWidgets import (QApplication, QComboBox, QCompleter, QDockWidget, QFileDialog, QHBoxLayout, QLabel,
                             QMenu, QMessageBox, QPlainTextEdit, QSizePolicy, QTextBrowser, QToolButton, QVBoxLayout,
                             QWidget)

from .. import theme

try:  # the chat view; a QTextBrowser is the fallback
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except Exception:  # noqa: BLE001
    QWebEngineView = None
    QWebEnginePage = None

ACT_HOST = "radchat.invalid"
SHELL_LANGS = {"bash", "sh", "shell", "console", "powershell", "ps1", "pwsh", "cmd", "bat", "batch", "zsh",
               "terminal", "ps"}
SYSTEM_PROMPT = (
    "You are the AI assistant inside RAD IDE, a Visual-Studio-style IDE (Windows Forms-like designer; Python, "
    "VB, Ring, PHP and web projects). Help the user program.\n"
    "- Answer in the language of the user's question (an Arabic question gets an Arabic answer); keep code, "
    "identifiers, commands and file names in English.\n"
    "- Use Markdown. Put code in fenced blocks with a language tag.\n"
    "- When you give a complete new version of a file, put its path after the language, e.g. "
    "```python path=src/main.py, and give the whole file. For a small change give only the changed "
    "function or block.\n"
    "- 'Context from the IDE' sections before the question contain files, the selection, errors etc."
)
HISTORY_CHARS = 48000


# ============================================================================ text direction
_RTL = re.compile("[֐-ࣿיִ-﷿ﹰ-﻿]")
_STRONG = re.compile("[A-Za-zÀ-ɏͰ-ϿЀ-ӿ֐-ࣿיִ-﷿ﹰ-﻿]")


def text_dir(text: str) -> str:
    """'rtl' when the first strong letter is Arabic / Hebrew (like HTML dir=auto), else 'ltr'.
    Markdown syntax, code spans and links are skipped."""
    t = re.sub(r"`[^`]*`|\]\([^)]*\)|https?://\S+", " ", text or "")
    m = _STRONG.search(t)
    return "rtl" if m and _RTL.match(m.group(0)) else "ltr"


LRM = "‎"
# an @ that starts a mention (not inside a word / an e-mail address) and has no LRM before it yet
_MENTION_AT = re.compile(r"(?<![\w‎])@(?=[\w\"]|$)", re.M)


def ltr_mentions(text: str) -> str:
    """Put an invisible LEFT-TO-RIGHT MARK before each @mention of a right-to-left line: '@' is a neutral
    character, so in Arabic text "@selection" was displayed as "selection@".  Display only - strip LRM
    (strip_lrm) before the text is sent."""
    if not text or "@" not in text:
        return text
    return "\n".join(_MENTION_AT.sub(LRM + "@", ln) if "@" in ln and text_dir(ln) == "rtl" else ln
                     for ln in text.split("\n"))


def strip_lrm(text: str) -> str:
    return text.replace(LRM, "")


# ============================================================================ highlighting
_ALIASES = {"vb": "vbnet", "vba": "vbnet", "form": "json", "ps1": "powershell", "pwsh": "powershell",
            "shell": "bash", "sh": "bash", "console": "bash", "cmd": "batch", "bat": "batch", "js": "javascript",
            "ts": "typescript", "py": "python", "html5": "html", "c++": "cpp", "c#": "csharp", "cs": "csharp"}


def highlight(code: str, lang: str) -> str:
    """HTML (spans with Pygments classes inside .hl) - plain escaped text when Pygments is missing."""
    lang = (lang or "").lower()
    try:
        from pygments import highlight as _hl
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name
        from pygments.util import ClassNotFound
    except Exception:  # noqa: BLE001
        return html.escape(code)
    if not lang or lang in ("text", "plain", "txt", "ring"):
        return html.escape(code)
    try:
        lexer = get_lexer_by_name(_ALIASES.get(lang, lang), stripnl=False, ensurenl=False)
    except ClassNotFound:
        return html.escape(code)
    except Exception:  # noqa: BLE001
        return html.escape(code)
    try:
        return _hl(code, lexer, HtmlFormatter(nowrap=True)).rstrip("\n")
    except Exception:  # noqa: BLE001
        return html.escape(code)


def pygments_css(dark: bool) -> str:
    try:
        from pygments.formatters import HtmlFormatter
        style = "github-dark" if dark else "vs"
        try:
            return HtmlFormatter(style=style).get_style_defs(".hl")
        except Exception:  # noqa: BLE001
            return HtmlFormatter(style="monokai" if dark else "default").get_style_defs(".hl")
    except Exception:  # noqa: BLE001
        return ""


# ============================================================================ markdown
class CodeBlock:
    __slots__ = ("lang", "code", "path", "info", "closed")

    def __init__(self, lang, code, path, info, closed):
        self.lang, self.code, self.path, self.info, self.closed = lang, code, path, info, closed


_FENCE_OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*(.*)$")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_HR = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_LIST = re.compile(r"^(\s*)([-*+]|\d{1,4}[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_PATH_IN_LINE = re.compile(r"[`*\"']*((?:[\w.\-]+[/\\])*[\w.\-]+\.[A-Za-z0-9]{1,8})[`*\"']*:?\s*$")
_FILE_WORDS = re.compile(r"(?i)\b(file|path|filename|ملف)\b")


def fence_path(info: str, before: str = "") -> str:
    """The file path of a code block: ```python path=src/a.py | ```python:src/a.py | ```src/a.py |
    a preceding line such as **src/a.py** or `File: src/a.py`."""
    info = (info or "").strip()
    m = re.search(r"""(?:path|file|filename|title)\s*[=:]\s*["']?([^"'\s]+)""", info, re.I)
    if m:
        return m.group(1)
    first = info.split()[0] if info.split() else ""
    if ":" in first and not re.match(r"^[A-Za-z]:[\\/]", first):
        cand = first.split(":", 1)[1]
        if "." in cand or "/" in cand:
            return cand
    if first and ("/" in first or "\\" in first or re.search(r"\.[A-Za-z0-9]{1,8}$", first)) and \
            not re.fullmatch(r"[\w+#-]+", first):
        return first
    rest = info.split()[1:] if len(info.split()) > 1 else []
    for tok in rest:
        if re.search(r"\.[A-Za-z0-9]{1,8}$", tok) and not tok.startswith("{"):
            return tok.strip("\"'")
    line = (before or "").strip()
    if line and len(line) < 160:
        m = _PATH_IN_LINE.search(line)
        if m:
            cand = m.group(1)
            short = len(line) < 60 or _FILE_WORDS.search(line) or line.startswith(("**", "`", "#"))
            if short and not cand[0].isdigit() and not re.fullmatch(r"\d+(\.\d+)*", cand):
                return cand
    return ""


def fence_lang(info: str) -> str:
    first = (info or "").strip().split()[0] if (info or "").strip() else ""
    first = first.split(":", 1)[0] if ":" in first and not re.match(r"^[A-Za-z]:[\\/]", first) else first
    if "=" in first or "/" in first or "\\" in first:
        return ""
    if "." in first:                  # ```main.py -> python
        ext = first.rsplit(".", 1)[1].lower()
        return {"py": "python", "js": "javascript", "ts": "typescript", "php": "php", "html": "html", "css": "css",
                "vb": "vb", "ring": "ring", "json": "json", "sql": "sql", "md": "markdown", "sh": "bash",
                "ps1": "powershell"}.get(ext, ext)
    return first.lower().strip("{}.")


class _Md:
    """A small Markdown renderer made for chat answers that are still streaming (an unclosed
    fence is a code block).  Every block gets dir="rtl|ltr" from its own text."""

    def __init__(self, act_url):
        self.blocks: list[CodeBlock] = []
        self.act_url = act_url          # act_url(action, block_index) -> href or None (no buttons)

    # ---------------------------------------------------------- inline
    def inline(self, text: str) -> str:
        out, pos = [], 0
        for m in re.finditer(r"(`+)(.+?)\1", text):
            out.append(self._inline_plain(text[pos:m.start()]))
            out.append(f'<code dir="ltr">{html.escape(m.group(2).strip())}</code>')
            pos = m.end()
        out.append(self._inline_plain(text[pos:]))
        return "".join(out)

    def _inline_plain(self, s: str) -> str:
        links = []

        def keep(h):
            links.append(h)
            return f"\x00{len(links) - 1}\x00"

        def link(m):
            label, url = m.group(1), m.group(2).strip()
            if not re.match(r"(?i)^(https?|mailto|file):", url):
                return keep(f'<a href="{self._open_url(url)}">{html.escape(label)}</a>')
            return keep(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
        s = re.sub(r"\[([^\]\n]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", link, s)
        s = re.sub(r"(?i)\bhttps?://[^\s<>()\"']+[^\s<>()\"'.,;:!?]",
                   lambda m: keep(f'<a href="{html.escape(m.group(0), quote=True)}">{html.escape(m.group(0))}</a>'),
                   s)
        s = html.escape(s, quote=False)
        s = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w])__(?=\S)(.+?)(?<=\S)__(?![\w])", r"<b>\1</b>", s)
        s = re.sub(r"(?<![*\w])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![*\w])", r"<i>\1</i>", s)
        s = re.sub(r"(?<![\w])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w])", r"<i>\1</i>", s)
        s = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"<s>\1</s>", s)
        return re.sub(r"\x00(\d+)\x00", lambda m: links[int(m.group(1))], s)

    def _open_url(self, target: str) -> str:
        return f"https://{ACT_HOST}/open?p={QUrl.toPercentEncoding(target).data().decode()}"

    # ---------------------------------------------------------- blocks
    def render(self, text: str) -> str:
        return self._blocks((text or "").replace("\r\n", "\n").split("\n"))

    def _blocks(self, lines: list[str]) -> str:
        out, i, n = [], 0, len(lines)
        para: list[str] = []
        last_text = ""

        def flush():
            nonlocal para, last_text
            if para:
                raw = "\n".join(para)
                body = "<br>".join(self.inline(x.strip()) for x in para)
                out.append(f'<p dir="{text_dir(raw)}">{body}</p>')
                last_text = para[-1]
                para = []

        while i < n:
            line = lines[i]
            m = _FENCE_OPEN.match(line)
            if m and (m.group(2)[0] == "~" or "`" not in m.group(3)):
                before = para[-1] if para else last_text
                flush()
                indent, fence, info = len(m.group(1)), m.group(2), m.group(3)
                body, i, closed = [], i + 1, False
                while i < n:
                    cl = lines[i]
                    if re.match(rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$", cl):
                        closed = True
                        i += 1
                        break
                    body.append(cl[indent:] if cl[:indent].strip() == "" else cl)
                    i += 1
                out.append(self._code(info, "\n".join(body), before, closed))
                last_text = ""
                continue
            if not line.strip():
                flush()
                i += 1
                continue
            h = _HEADING.match(line)
            if h:
                flush()
                lvl = min(len(h.group(1)) + 1, 6) if len(h.group(1)) < 6 else 6
                out.append(f'<h{lvl} dir="{text_dir(h.group(2))}">{self.inline(h.group(2))}</h{lvl}>')
                last_text = h.group(2)
                i += 1
                continue
            if _HR.match(line) and not para:
                out.append("<hr>")
                i += 1
                continue
            if re.match(r"^\s{0,3}>", line):
                flush()
                q = []
                while i < n and re.match(r"^\s{0,3}>", lines[i]):
                    q.append(re.sub(r"^\s{0,3}>\s?", "", lines[i]))
                    i += 1
                inner = self._blocks(q)
                out.append(f'<blockquote dir="{text_dir(" ".join(q))}">{inner}</blockquote>')
                continue
            if "|" in line and i + 1 < n and _TABLE_SEP.match(lines[i + 1]) and lines[i + 1].count("-") >= 3:
                flush()
                rows = [line]
                i += 2
                while i < n and "|" in lines[i] and lines[i].strip():
                    rows.append(lines[i])
                    i += 1
                out.append(self._table(rows))
                continue
            lm = _LIST.match(line)
            if lm and (not para or lm.group(2)[0].isdigit() or lm.group(2) in "-*+"):
                flush()
                i = self._list(lines, i, out)
                continue
            para.append(line)
            i += 1
        flush()
        return "".join(out)

    def _list(self, lines, i, out) -> int:
        n = len(lines)
        first = _LIST.match(lines[i])
        base = len(first.group(1))
        ordered = first.group(2)[0].isdigit()
        start = int(re.match(r"\d+", first.group(2)).group(0)) if ordered else 1
        items: list[list[str]] = []
        while i < n:
            line = lines[i]
            m = _LIST.match(line)
            if m and len(m.group(1)) <= base + 1 and (m.group(2)[0].isdigit() == ordered):
                items.append([m.group(3)])
                i += 1
                continue
            if m and len(m.group(1)) <= base + 1:
                break                    # another kind of list starts
            if not line.strip():
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and (len(lines[j]) - len(lines[j].lstrip()) > base + 1 or
                              (_LIST.match(lines[j]) and len(_LIST.match(lines[j]).group(1)) <= base + 1
                               and _LIST.match(lines[j]).group(2)[0].isdigit() == ordered)):
                    if items:
                        items[-1].append("")
                    i += 1
                    continue
                break
            indent = len(line) - len(line.lstrip())
            if indent > base or (items and not _FENCE_OPEN.match(line) and not _HEADING.match(line)):
                if items:
                    cut = min(indent, base + 4) if indent > base else 0
                    items[-1].append(line[cut:] if indent > base else line)
                    i += 1
                    continue
            break
        tag = "ol" if ordered else "ul"
        st = f' start="{start}"' if ordered and start != 1 else ""
        all_text = " ".join(" ".join(x) for x in items)
        parts = []
        for it in items:
            # dedent continuation lines (nested lists / code)
            body = [it[0]] + [x[2:] if x.startswith("  ") else x for x in it[1:]]
            inner = self._blocks(body)
            if inner.startswith("<p ") and inner.count("<p ") == 1 and inner.endswith("</p>"):
                inner = inner[inner.index(">") + 1:-4]
            parts.append(f'<li dir="{text_dir(it[0])}">{inner}</li>')
        out.append(f'<{tag}{st} dir="{text_dir(all_text)}">{"".join(parts)}</{tag}>')
        return i

    def _table(self, rows: list[str]) -> str:
        def cells(r):
            r = r.strip()
            if r.startswith("|"):
                r = r[1:]
            if r.endswith("|"):
                r = r[:-1]
            return [c.strip() for c in re.split(r"(?<!\\)\|", r)]
        head = cells(rows[0])
        d = text_dir(" ".join(head + [c for r in rows[1:] for c in cells(r)]))
        h = "".join(f"<th>{self.inline(c)}</th>" for c in head)
        body = "".join("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in cells(r)) + "</tr>" for r in rows[1:])
        return f'<div class="tablewrap"><table dir="{d}"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>'

    def _code(self, info: str, code: str, before: str, closed: bool) -> str:
        lang = fence_lang(info)
        path = fence_path(info, before)
        idx = len(self.blocks)
        self.blocks.append(CodeBlock(lang, code, path, info, closed))
        label = html.escape(lang or "text")
        if path:
            label += f' <span class="path">{html.escape(path)}</span>'
        btns = ""
        if self.act_url is not None and closed:
            acts = [("copy", "Copy", "Copy to the clipboard"),
                    ("insert", "Insert", "Insert at the cursor of the current editor"),
                    ("apply", "Apply", "Apply to the file (shows the changes first)"),
                    ("newfile", "New file", "Save as a new file")]
            if lang in SHELL_LANGS:
                acts.append(("run", "Run", "Run in the Terminal"))
            btns = "".join(f'<a class="btn" title="{t}" href="{self.act_url(a, idx)}">{label_}</a>'
                           for a, label_, t in acts)
        return (f'<div class="code" dir="ltr"><div class="code-head"><span class="lang">{label}</span>'
                f'<span class="btns">{btns}</span></div>'
                f'<pre dir="ltr"><code class="hl">{highlight(code, lang)}</code></pre></div>')


def render_markdown(text: str, act_url=None) -> tuple[str, list[CodeBlock]]:
    md = _Md(act_url)
    return md.render(text), md.blocks


# ============================================================================ smart apply
def _strip_indent(lines):
    ind = [len(x) - len(x.lstrip()) for x in lines if x.strip()]
    return min(ind) if ind else 0


def _trivial(s: str) -> bool:
    s = s.strip()
    return len(s) < 4 or s in ("{", "}", "};", "end", "End If", "End Sub", "</div>", "?>", "<?php", "pass",
                               "else:", "try:", "return", "endif", "next", "loop", "wend")


def smart_apply(old: str, snippet: str) -> tuple[str | None, str]:
    """Merge a code block into a file -> (new text, how) where how is 'empty' | 'whole' | 'block'; (None, '')
    when the block does not match a part of the file."""
    old = (old or "").replace("\r\n", "\n")
    snip = (snippet or "").replace("\r\n", "\n").rstrip("\n")
    if not old.strip():
        return snip + "\n", "empty"
    a = old.split("\n")
    b = snip.split("\n")
    nonempty_a = [x for x in a if x.strip()]
    nonempty_b = [x for x in b if x.strip()]
    if not nonempty_b:
        return None, ""
    import difflib
    ratio = difflib.SequenceMatcher(None, [x.strip() for x in nonempty_a], [x.strip() for x in nonempty_b],
                                    autojunk=False).ratio()
    if len(nonempty_b) >= 0.6 * len(nonempty_a) or (ratio >= 0.6 and len(nonempty_b) >= 0.4 * len(nonempty_a)):
        out = snip + ("\n" if old.endswith("\n") else "")
        return out, "whole"
    first = next(x for x in b if x.strip())
    last = next(x for x in reversed(b) if x.strip())
    cands = [k for k, x in enumerate(a) if x.strip() == first.strip()] if not _trivial(first) else []
    if not cands:
        return None, ""
    best = None
    nb = len(b)
    for i in cands:
        j_end = None
        # 1) the last line of the snippet closes the block
        hits = [j for j in range(i, min(len(a), i + 3 * nb + 20)) if a[j].strip() == last.strip()]
        if hits and len(nonempty_b) > 1 and not _trivial(last):
            j_end = min(hits, key=lambda j: abs((j - i + 1) - nb)) + 1
        if j_end is None or len(nonempty_b) == 1:
            # 2) indentation block (Python, VB-ish) or braces
            ind = len(a[i]) - len(a[i].lstrip())
            if "{" in a[i] and a[i].count("{") > a[i].count("}"):
                depth, j = 0, i
                while j < len(a):
                    depth += a[j].count("{") - a[j].count("}")
                    j += 1
                    if depth <= 0:
                        break
                j_end = j
            else:
                j = i + 1
                while j < len(a) and (not a[j].strip() or len(a[j]) - len(a[j].lstrip()) > ind):
                    j += 1
                while j > i + 1 and not a[j - 1].strip():
                    j -= 1
                j_end = j if len(nonempty_b) > 1 else i + 1
        score = difflib.SequenceMatcher(None, [x.strip() for x in a[i:j_end]], [x.strip() for x in b]).ratio()
        if best is None or score > best[0]:
            best = (score, i, j_end)
    score, i, j_end = best
    if score < 0.25 and len(nonempty_b) > 2:
        return None, ""
    # keep the file's indentation
    old_ind = len(a[i]) - len(a[i].lstrip())
    new_ind = len(first) - len(first.lstrip())
    shift = old_ind - new_ind
    if shift > 0:
        b = [(" " * shift + x) if x.strip() else x for x in b]
    elif shift < 0:
        b = [x[-shift:] if x[:-shift].strip() == "" else x for x in b]
    return "\n".join(a[:i] + b + a[j_end:]), "block"


# ============================================================================ chat storage
def _chat_root(win) -> Path:
    try:
        from ..ai import context
        base = context.solution_folder(win)
    except Exception:  # noqa: BLE001
        base = None
    if base is not None:
        return Path(base) / ".radide" / "ai" / "chats"
    from PyQt6.QtCore import QCoreApplication
    org = QCoreApplication.organizationName()
    name = org if org.upper().startswith("RADIDE-TEST") else "RADIDE"
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(local) / name / "ai" / "chats"


def new_chat() -> dict:
    now = time.time()
    return {"id": time.strftime("%Y%m%d-%H%M%S", time.localtime(now)) + "-" + secrets.token_hex(2),
            "title": "", "created": now, "updated": now, "messages": []}


def list_chats(folder: Path) -> list[dict]:
    out = []
    try:
        files = list(folder.glob("*.json"))
    except OSError:
        return out
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("messages"), list):
                d["_file"] = str(f)
                out.append(d)
        except (OSError, ValueError):
            continue
    out.sort(key=lambda d: d.get("updated", 0), reverse=True)
    return out


def save_chat(folder: Path, chat: dict) -> Path | None:
    if not chat.get("messages"):
        return None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{chat['id']}.json"
        data = {k: v for k, v in chat.items() if not k.startswith("_")}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
        return path
    except OSError:
        return None


# ============================================================================ the transcript views
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style id="vars"></style><style id="hl"></style>
<style>
html,body{margin:0;padding:0;background:var(--rad-base);color:var(--rad-text);
 font:13px "Segoe UI","Segoe UI Variable",Tahoma,Arial,sans-serif;line-height:1.5}
#log{padding:8px 10px 24px 10px}
.msg{margin:0 0 12px 0;padding:6px 10px 8px 10px;border-radius:8px;overflow-wrap:anywhere}
.msg.user{background:var(--user-back);border:1px solid var(--rad-border)}
.msg.ai{background:transparent}
.who{font-size:11px;font-weight:600;color:var(--rad-muted);margin-bottom:2px;display:flex;gap:8px;
 direction:ltr;align-items:baseline}
.who .meta{font-weight:400}
.who .sp{flex:1}
.who a{font-weight:400}
p{margin:4px 0}
h2,h3,h4,h5,h6{margin:10px 0 4px 0;font-size:14px;color:var(--rad-heading)}
h2{font-size:15px}
ul,ol{margin:4px 0;padding-inline-start:22px}
li{margin:2px 0}
a{color:var(--rad-link);text-decoration:none}
a:hover{text-decoration:underline}
blockquote{margin:6px 0;padding:2px 10px;border-inline-start:3px solid var(--rad-border);color:var(--rad-muted)}
code{font-family:"Cascadia Mono",Consolas,"Courier New",monospace;font-size:12px;background:var(--code-back);
 padding:1px 4px;border-radius:3px;unicode-bidi:isolate}
.code{margin:6px 0;border:1px solid var(--rad-border);border-radius:6px;overflow:hidden;background:var(--code-back)}
.code-head{display:flex;align-items:center;gap:6px;padding:2px 6px;background:var(--code-head);
 font-size:11px;color:var(--rad-muted);direction:ltr}
.code-head .lang{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.code-head .path{color:var(--rad-text);margin-left:6px}
.code-head .btns{display:flex;gap:2px;flex-wrap:wrap;justify-content:flex-end}
.btn{padding:1px 7px;border-radius:4px;color:var(--rad-text)!important;border:1px solid transparent}
.btn:hover{background:var(--rad-base);border-color:var(--rad-border);text-decoration:none!important}
pre{margin:0;padding:8px 10px;overflow-x:auto;direction:ltr;text-align:left}
pre code{background:transparent;padding:0;font-size:12px;line-height:1.45;white-space:pre}
.hl{background:transparent!important}
table{border-collapse:collapse;margin:6px 0}
.tablewrap{overflow-x:auto}
th,td{border:1px solid var(--rad-border);padding:3px 8px;text-align:start}
th{background:var(--code-head)}
hr{border:0;border-top:1px solid var(--rad-border);margin:8px 0}
.ctx{margin-top:4px;font-size:11px;color:var(--rad-muted);direction:ltr}
.ctx span{display:inline-block;border:1px solid var(--rad-border);border-radius:9px;padding:0 7px;margin:2px 4px 0 0}
.err{color:var(--rad-error);border:1px solid var(--rad-error);border-radius:6px;padding:6px 8px;margin:4px 0;
 white-space:pre-wrap}
.note{color:var(--rad-muted);font-style:italic}
.cursor::after{content:"\\25CF";color:var(--rad-accent);animation:blink 1s steps(2,start) infinite;margin:0 3px}
@keyframes blink{to{visibility:hidden}}
.welcome{color:var(--rad-muted);padding:10px 4px}
.welcome h2{color:var(--rad-text)}
.welcome a.ex{display:block;margin:4px 0;padding:4px 8px;border:1px solid var(--rad-border);border-radius:6px;
 color:var(--rad-text)}
.welcome a.ex:hover{background:var(--user-back);text-decoration:none}
</style></head><body><div id="log"></div>
<script>
var log=document.getElementById('log');
function nearBottom(){return (window.innerHeight+window.scrollY)>=document.body.scrollHeight-60;}
function toBottom(){window.scrollTo(0,document.body.scrollHeight);}
function radTheme(vars,hl){document.getElementById('vars').textContent=vars;document.getElementById('hl').textContent=hl;}
function radAll(h){log.innerHTML=h;toBottom();}
function radSet(id,h,follow){var b=nearBottom();var e=document.getElementById(id);
 if(!e){e=document.createElement('div');log.appendChild(e);}
 e.outerHTML=h;if(b||follow)toBottom();}
function radRemove(id){var e=document.getElementById(id);if(e)e.remove();}
document.addEventListener('click',function(ev){var a=ev.target.closest('a.btn');
 if(a&&a.href.indexOf('/copy?')>0){var t=a.textContent;a.textContent='Copied';setTimeout(function(){a.textContent=t;},1200);}});
</script></body></html>"""


def page_css() -> tuple[str, str]:
    t = theme.current()
    from ..ai.diffview import _mix
    base, text = t["base"], t["text"]
    user = _mix(base, t["accent"], 0.10 if not t["dark"] else 0.16).name()
    code = _mix(base, t["text"], 0.04 if not t["dark"] else 0.06).name()
    head = _mix(base, t["text"], 0.09 if not t["dark"] else 0.12).name()
    vars_ = theme.css_vars() + f" :root {{ --user-back: {user}; --code-back: {code}; --code-head: {head}; " \
                               f"--rad-heading: {t['heading']}; }}"
    return vars_ + f" body {{ background: {base}; color: {text}; }}", pygments_css(bool(t["dark"]))


if QWebEnginePage is not None:
    class _Page(QWebEnginePage):
        action = pyqtSignal(QUrl)

        def acceptNavigationRequest(self, url, nav_type, is_main):  # noqa: N802
            if url.host() == ACT_HOST:
                self.action.emit(url)
                return False
            if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                QDesktopServices.openUrl(url)
                return False
            return super().acceptNavigationRequest(url, nav_type, is_main)

        def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802
            pass
else:
    _Page = None


class WebTranscript(QWidget):
    """The transcript in a QWebEngineView: radSet(id, html) updates one message in place."""

    action = pyqtSignal(QUrl)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.view = QWebEngineView(self)
        self.page = _Page(self.view)
        self.page.setBackgroundColor(Qt.GlobalColor.transparent)
        self.view.setPage(self.page)
        self.page.action.connect(self.action)
        lay.addWidget(self.view)
        self.ready = False
        self._queue: list[str] = []
        self.page.loadFinished.connect(self._loaded)
        self.page.setHtml(PAGE, QUrl(f"https://{ACT_HOST}/chat"))
        self.restyle()

    def _loaded(self, ok):
        self.ready = True
        q, self._queue = self._queue, []
        for js in q:
            self.page.runJavaScript(js)

    def js(self, code: str):
        if self.ready:
            self.page.runJavaScript(code)
        else:
            self._queue.append(code)

    def restyle(self):
        v, h = page_css()
        self.js(f"radTheme({json.dumps(v)}, {json.dumps(h)});")
        try:
            from PyQt6.QtGui import QColor
            self.page.setBackgroundColor(QColor(theme.color("base")))
        except Exception:  # noqa: BLE001
            pass

    def set_all(self, html_: str):
        self.js(f"radAll({json.dumps(html_)});")

    def set_message(self, mid: str, html_: str, follow: bool = False):
        self.js(f"radSet({json.dumps(mid)}, {json.dumps(html_)}, {'true' if follow else 'false'});")

    def remove(self, mid: str):
        self.js(f"radRemove({json.dumps(mid)});")

    def run_js(self, code: str, callback):
        self.page.runJavaScript(code, callback)


class TextTranscript(QTextBrowser):
    """Fallback without QtWebEngine: the whole transcript is re-rendered."""

    action = pyqtSignal(QUrl)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self._click)
        self._parts: dict[str, str] = {}
        self._order: list[str] = []
        self.ready = True

    def _click(self, url: QUrl):
        if url.host() == ACT_HOST:
            self.action.emit(url)
        else:
            QDesktopServices.openUrl(url)

    def restyle(self):
        v, h = page_css()
        self.document().setDefaultStyleSheet(
            "p,li{margin:2px 0} pre{background:%s} .who{color:%s} .err{color:%s}" % (
                theme.color("alt_base"), theme.color("muted"), theme.color("error")))
        self._render()

    def _render(self):
        sb = self.verticalScrollBar()
        at_end = sb.value() >= sb.maximum() - 30
        self.setHtml("".join(self._parts[k] for k in self._order))
        if at_end:
            sb.setValue(sb.maximum())

    def set_all(self, html_: str):
        self._parts = {"all": html_}
        self._order = ["all"]
        self._render()

    def set_message(self, mid, html_, follow=False):
        if "all" in self._parts and mid not in self._parts:
            pass
        if mid not in self._parts:
            self._order.append(mid)
        self._parts[mid] = html_
        self._render()

    def remove(self, mid):
        self._parts.pop(mid, None)
        if mid in self._order:
            self._order.remove(mid)
        self._render()

    def run_js(self, code, callback):
        callback(None)


# ============================================================================ the input box
class ChatInput(QPlainTextEdit):
    """Enter sends, Shift+Enter is a new line, @ opens the context completion, Up recalls the last question."""

    submit = pyqtSignal()

    def __init__(self, panel: "ChatPanel"):
        super().__init__(panel)
        self.panel = panel
        self.setPlaceholderText("Ask anything...  @ adds context (@file:, @selection, @problems ...).  "
                                "Enter sends, Shift+Enter = new line")
        self.setTabChangesFocus(True)
        opt = self.document().defaultTextOption()
        opt.setTextDirection(Qt.LayoutDirection.LayoutDirectionAuto)
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(opt)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.model = QStringListModel(self)
        self.completer = QCompleter(self.model, self)
        self.completer.setWidget(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated[str].connect(self._insert_completion)
        self.textChanged.connect(self._ltr_mentions)
        self.textChanged.connect(self._fit)
        self._fit()

    def text(self) -> str:
        """The text without the display-only LRM marks."""
        return strip_lrm(self.toPlainText())

    def _ltr_mentions(self):
        """Keep @mentions readable inside Arabic text (see ltr_mentions): insert LRM marks in place, so
        the caret and the undo history stay where the user expects."""
        doc = self.document()
        if "@" not in doc.toPlainText():
            return
        block = doc.begin()
        spots = []
        while block.isValid():
            t = block.text()
            if "@" in t and text_dir(t) == "rtl":
                spots += [block.position() + m.start() for m in _MENTION_AT.finditer(t)]
            block = block.next()
        if not spots:
            return
        self.blockSignals(True)
        try:
            cur = QTextCursor(doc)
            cur.beginEditBlock()
            for pos in reversed(spots):
                cur.setPosition(pos)
                cur.insertText(LRM)
            cur.endEditBlock()
        finally:
            self.blockSignals(False)

    def _fit(self):
        doc_h = int(self.document().size().height() * self.fontMetrics().lineSpacing())
        h = max(2 * self.fontMetrics().lineSpacing(), min(doc_h, 12 * self.fontMetrics().lineSpacing())) + 12
        self.setFixedHeight(h)
        self._dir()

    def _dir(self):
        # each paragraph already follows its own first strong letter; align the placeholder / caret too
        d = text_dir(self.toPlainText())
        want = Qt.LayoutDirection.RightToLeft if d == "rtl" else Qt.LayoutDirection.LeftToRight
        if self.layoutDirection() != want and self.toPlainText().strip():
            self.setLayoutDirection(want)
        elif not self.toPlainText().strip() and self.layoutDirection() != Qt.LayoutDirection.LeftToRight:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def _token(self) -> tuple[str, int]:
        cur = self.textCursor()
        block = cur.block().text()
        col = cur.positionInBlock()
        left = block[:col]
        m = re.search(r'@(file:"[^"]*|[\w:./\\\-]*)$', left)
        return (m.group(0), len(m.group(0))) if m else ("", 0)

    def _insert_completion(self, text: str):
        tok, n = self._token()
        cur = self.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, n)
        cur.insertText(text if text.endswith(":") else text + " ")
        self.setTextCursor(cur)
        if text.endswith(":"):
            QTimer.singleShot(0, self._complete)

    def _complete(self):
        tok, _n = self._token()
        if not tok:
            self.completer.popup().hide()
            return
        items = self.panel.mention_items(tok)
        self.model.setStringList(items)
        self.completer.setCompletionPrefix(tok)
        if self.completer.completionCount() == 0:
            self.completer.popup().hide()
            return
        r = self.cursorRect()
        r.setWidth(max(320, self.completer.popup().sizeHintForColumn(0) + 30))
        self.completer.complete(r)

    def keyPressEvent(self, e):
        popup = self.completer.popup()
        if popup.isVisible() and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab, Qt.Key.Key_Escape,
                                             Qt.Key.Key_Up, Qt.Key.Key_Down):
            if e.key() == Qt.Key.Key_Escape:
                popup.hide()
                return
            if e.key() in (Qt.Key.Key_Tab,):
                idx = popup.currentIndex()
                if not idx.isValid():
                    idx = self.completer.completionModel().index(0, 0)
                self._insert_completion(idx.data())
                popup.hide()
                return
            e.ignore()
            return
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submit.emit()
            return
        if e.key() == Qt.Key.Key_Up and not self.toPlainText().strip() and self.panel.last_question():
            self.setPlainText(self.panel.last_question())
            self.moveCursor(QTextCursor.MoveOperation.End)
            return
        super().keyPressEvent(e)
        if e.text() == "@" or (self._token()[0] and e.text() and not e.text().isspace()) or \
                e.key() == Qt.Key.Key_Backspace and self._token()[0]:
            self._complete()
        elif e.text().isspace():
            popup.hide()


# ============================================================================ the panel
class ChatPanel(QWidget):
    """The AI Chat window (win.ai_chat)."""

    busyChanged = pyqtSignal(bool)
    answered = pyqtSignal(str)        # the full answer text (tests, other features)

    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.chat = new_chat()
        self.job = None
        self.attachments: list[dict] = []
        self._render_pending = False
        self._streaming_idx = -1
        self._file_cache: tuple[float, list[str]] = (0.0, [])
        self.blocks: dict[int, list[CodeBlock]] = {}
        self._build()
        self.restyle()
        from PyQt6 import sip
        theme.changed.connect(lambda _n: None if sip.isdeleted(self) else self.restyle())
        try:
            from .. import ai
            ai.hub().providers_changed.connect(self.fill_providers)
            ai.hub().models_changed.connect(self._on_models)
            ai.hub().defaults_changed.connect(lambda p: p == "chat" and self.fill_providers())
        except Exception:  # noqa: BLE001
            pass
        QTimer.singleShot(0, self.fill_providers)
        QTimer.singleShot(0, self.load_latest)

    # ---------------------------------------------------------- UI
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        head = QWidget()
        head.setObjectName("aiChatHead")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(6, 2, 4, 2)
        hl.setSpacing(2)
        self.title = QLabel("New chat")
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        hl.addWidget(self.title, 1)

        def tb(text, tip, slot=None):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            if slot is not None:
                b.clicked.connect(slot)
            hl.addWidget(b)
            return b
        self.new_btn = tb("New", "New chat (Ctrl+N in the chat)", self.new_chat)
        self.hist_btn = tb("History ▾", "Earlier chats of this project")
        self.hist_menu = QMenu(self)
        self.hist_menu.aboutToShow.connect(self._fill_history)
        self.hist_btn.setMenu(self.hist_menu)
        self.hist_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more_btn = tb("⋯", "More")
        more = QMenu(self)
        more.addAction("Regenerate last answer", self.regenerate)
        more.addAction("Copy whole chat as Markdown", self.copy_markdown)
        more.addSeparator()
        more.addAction("Delete this chat", self.delete_chat)
        more.addAction("Open chats folder", self.open_folder)
        more.addSeparator()
        more.addAction("AI Settings...", self.open_settings)
        self.more_btn.setMenu(more)
        self.more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # the style's menu arrow was drawn clipped over the text ("History,"); the text carries a chevron
        head.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }"
                           "QToolButton { padding: 1px 5px; }")
        lay.addWidget(head)

        use_web = QWebEngineView is not None and not os.environ.get("RADIDE_CHAT_TEXTVIEW")
        self.view = WebTranscript(self) if use_web else TextTranscript(self)
        self.view.action.connect(self._on_action)
        self.view.setMinimumHeight(60)     # small: in the VS layout it shares the right column (a
        #                                    larger minimum made the window taller than a 900 px screen)
        lay.addWidget(self.view, 1)

        bottom = QWidget()
        bottom.setObjectName("aiChatBottom")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(6, 4, 6, 6)
        bl.setSpacing(3)
        self.chips = QWidget()
        self.chips_lay = QHBoxLayout(self.chips)
        self.chips_lay.setContentsMargins(0, 0, 0, 0)
        self.chips_lay.setSpacing(4)
        self.chips_lay.addStretch(1)
        self.chips.hide()
        bl.addWidget(self.chips)
        self.input = ChatInput(self)
        self.input.submit.connect(self.send_input)
        bl.addWidget(self.input)
        # two rows so nothing is cut in a narrow side bar:
        #   [+ File] [+ Selection] [@] ............ [Send]
        #   [provider ...................] [model ..........]
        row = QHBoxLayout()
        row.setSpacing(3)
        self.add_file_btn = QToolButton(text="+ File", toolTip="Add a file of the project as context")
        self.add_file_btn.setAutoRaise(True)
        self.add_file_btn.clicked.connect(self.add_file_dialog)
        self.add_sel_btn = QToolButton(text="+ Selection", toolTip="Add the editor's selection (or the current file)")
        self.add_sel_btn.setAutoRaise(True)
        self.add_sel_btn.clicked.connect(self.attach_selection)
        self.at_btn = QToolButton(text="@", toolTip="Insert a context mention")
        self.at_btn.setAutoRaise(True)
        self.at_btn.clicked.connect(self._at)
        self.provider = QComboBox()
        self.provider.setToolTip("AI provider (Tools > Options > AI to configure)")
        self.provider.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.provider.setMinimumContentsLength(6)
        self.provider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.provider.activated.connect(self._provider_chosen)
        self.provider.currentIndexChanged.connect(
            lambda _i: self.provider.setToolTip(f"AI provider: {self.provider.currentText()}\n"
                                                "(Tools > Options > AI to configure)"))
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setToolTip("Model (type any model name)")
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model.setMinimumContentsLength(6)
        self.model.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.model.activated.connect(lambda _i: self._model_chosen())
        self.model.lineEdit().editingFinished.connect(self._model_chosen)
        self.model.currentTextChanged.connect(self._model_shown)
        self.send_btn = QToolButton(text="Send", toolTip="Send (Enter)")
        self.send_btn.clicked.connect(self._send_or_stop)
        for w in (self.add_file_btn, self.add_sel_btn, self.at_btn):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.send_btn)
        row2 = QHBoxLayout()
        row2.setSpacing(3)
        row2.addWidget(self.provider, 3)
        row2.addWidget(self.model, 2)
        bl.addLayout(row2)
        bl.addLayout(row)
        self.status = QLabel()
        self.status.setWordWrap(True)
        theme.role(self.status, "muted")
        self.status.hide()
        bl.addWidget(self.status)
        lay.addWidget(bottom)
        self.setMinimumWidth(260)

    def restyle(self):
        t = theme.current()
        self.setStyleSheet(
            f"#aiChatHead {{ background: {t['header']}; border-bottom: 1px solid {t['border']}; }}"
            f"#aiChatHead QLabel {{ color: {t['header_text']}; }}"
            f"#aiChatBottom {{ background: {t['window']}; border-top: 1px solid {t['border']}; }}"
            f"ChatInput {{ background: {t['base']}; color: {t['text']}; border: 1px solid {t['border']};"
            f" border-radius: 4px; padding: 2px; }}"
            f"ChatInput:focus {{ border: 1px solid {t['accent']}; }}"
            f"QToolButton#chip {{ border: 1px solid {t['border']}; border-radius: 9px; padding: 0 6px;"
            f" background: {t['alt_base']}; color: {t['text']}; }}")
        self.view.restyle()
        self.render_all()

    # ---------------------------------------------------------- providers
    def fill_providers(self):
        try:
            from .. import ai
            provs = ai.providers()
            cur_p, cur_m = ai.default("chat")
            chosen = str(ai.settings().value("ai/default/chat/provider", "") or "")
        except Exception as e:  # noqa: BLE001
            self.provider.clear()
            self.provider.addItem(f"AI unavailable: {e}", "")
            return
        self.provider.blockSignals(True)
        self.provider.clear()
        self.provider.addItem(f"Auto ({cur_p.name})", "")
        self.provider.setItemData(0, "The best available free provider - now " + cur_p.name, Qt.ItemDataRole.ToolTipRole)
        kinds = {"local": "Local models", "cli": "CLI agents (your account)", "api": "API keys", "web": "Web chats"}
        for kind in ("local", "cli", "api", "web"):
            group = [p for p in provs if p.kind == kind and p.enabled()]
            if not group:
                continue
            self.provider.insertSeparator(self.provider.count())
            for p in group:
                try:
                    ok, why = p.available()
                except Exception as e:  # noqa: BLE001
                    ok, why = False, str(e)
                self.provider.addItem(p.name + ("" if ok else "  (not ready)"), p.id)
                i = self.provider.count() - 1
                self.provider.setItemData(i, f"{kinds[kind]}: {why or 'ready'}", Qt.ItemDataRole.ToolTipRole)
        idx = self.provider.findData(chosen) if chosen else 0
        self.provider.setCurrentIndex(max(0, idx))
        self.provider.blockSignals(False)
        self._fill_models(cur_p, cur_m)

    def current_provider(self):
        from .. import ai
        pid = self.provider.currentData() or ""
        if pid:
            try:
                p = ai.get(pid)
                m = self.model.currentText().strip() or p.default_model
                return p, m
            except KeyError:
                pass
        p, m = ai.default("chat")
        typed = self.model.currentText().strip()
        return p, typed or m

    def _fill_models(self, p=None, model=None):
        if p is None:
            p, model = self.current_provider()
        try:
            ms = p.models()
        except Exception:  # noqa: BLE001
            ms = []
        self.model.blockSignals(True)
        self.model.clear()
        for m in ms:
            self.model.addItem(m)
        model = model or p.default_model
        if model and self.model.findText(model) < 0:
            self.model.insertItem(0, model)
        self.model.setCurrentText(model or "")
        self.model.blockSignals(False)
        self._model_shown()
        self._show_ready(p)
        self.provider.setToolTip(f"AI provider: {self.provider.currentText()}\n(Tools > Options > AI to configure)")

    def _model_shown(self, _text=None):
        """Show the start of a long model name (an editable combo scrolls to the caret = the end, which cut
        the first letters) and put the full name in the tooltip."""
        le = self.model.lineEdit()
        if le is not None and not le.hasFocus():
            le.setCursorPosition(0)
        self.model.setToolTip(f"Model: {self.model.currentText() or '(default)'}\n(type any model name)")

    def _on_models(self, pid):
        p, m = self.current_provider()
        if p.id == pid:
            self._fill_models(p, m)

    def _show_ready(self, p):
        try:
            ok, why = p.available()
        except Exception as e:  # noqa: BLE001
            ok, why = False, str(e)
        if ok:
            self.status.hide()
        else:
            self.status.setText(f"{p.name}: {why}  -  Tools > Options > AI to set it up.")
            self.status.show()

    def _provider_chosen(self, _i):
        from .. import ai
        pid = self.provider.currentData() or ""
        if pid:
            p = ai.get(pid)
            ai.set_default("chat", pid, p.default_model)
        else:
            ai.set_default("chat", "")
        self.fill_providers()

    def _model_chosen(self):
        from .. import ai
        pid = self.provider.currentData() or ""
        m = self.model.currentText().strip()
        if pid:
            s = ai.settings()
            if str(s.value("ai/default/chat/model", "") or "") != m:
                ai.set_default("chat", pid, m)

    # ---------------------------------------------------------- mentions
    def project_files(self) -> list[str]:
        now = time.time()
        if now - self._file_cache[0] < 20 and self._file_cache[1]:
            return self._file_cache[1]
        out = []
        try:
            from ..ai import context
            root = context.solution_folder(self.win)
            if root is not None:
                for f in context.iter_files(Path(root), limit=3000):
                    out.append(str(f.relative_to(root)).replace("\\", "/"))
        except Exception:  # noqa: BLE001
            pass
        self._file_cache = (now, out)
        return out

    def mention_items(self, token: str) -> list[str]:
        from ..ai import context
        if token.lower().startswith("@file:"):
            out = []
            for f in self.project_files():
                out.append(f'@file:"{f}"' if " " in f else f"@file:{f}")
            return out
        return list(context.MENTIONS.keys())

    def _at(self):
        self.input.setFocus()
        self.input.insertPlainText("@")
        self.input._complete()

    # ---------------------------------------------------------- attachments
    def _add_chip(self, att: dict):
        for a in self.attachments:
            if a["label"] == att["label"] and a.get("mention") == att.get("mention"):
                return
        self.attachments.append(att)
        self._render_chips()

    def _render_chips(self):
        while self.chips_lay.count() > 1:
            it = self.chips_lay.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        for i, a in enumerate(self.attachments):
            b = QToolButton()
            b.setObjectName("chip")
            b.setText(a["label"] + "  x")
            b.setToolTip("Context sent with the next question - click to remove")
            b.clicked.connect(lambda _c=False, att=a: self._remove_chip(att))
            self.chips_lay.insertWidget(i, b)
        self.chips.setVisible(bool(self.attachments))

    def _remove_chip(self, att):
        if att in self.attachments:
            self.attachments.remove(att)
        self._render_chips()

    def attach(self, mention: str, label: str | None = None, text: str | None = None, lang: str = ""):
        """Add a context chip: a mention (@file:path, @problems ...) or a snapshot text."""
        if label is None:
            if mention.startswith("@file:"):
                label = Path(mention[6:].strip('"')).name
            else:
                label = mention.lstrip("@").capitalize()
        self._add_chip({"label": label, "mention": mention, "text": text, "lang": lang})

    def attach_file(self, path):
        from ..ai import context
        p = Path(path)
        root = context.solution_folder(self.win)
        try:
            shown = str(p.resolve().relative_to(Path(root).resolve())).replace("\\", "/") if root else str(p)
        except ValueError:
            shown = str(p)
        self.attach(f'@file:"{shown}"' if " " in shown else f"@file:{shown}", label=p.name)

    def attach_selection(self):
        from ..ai import context
        ed, path = context.current_editor(self.win)
        sel = context.selected_text(ed)
        name = Path(path).name if path else "editor"
        if sel.strip():
            n = sel.count("\n") + 1
            self.attach("@selection", label=f"Selection ({name}, {n} line{'s' if n != 1 else ''})", text=sel,
                        lang=context.lang_of(path))
        elif path:
            self.attach_file(path)
        else:
            self.win.statusBar().showMessage("Open a file in the editor first", 4000)

    def add_file_dialog(self):
        from ..ai import context
        root = context.solution_folder(self.win)
        names, _ = QFileDialog.getOpenFileNames(self, "Add files to the chat", str(root or Path.home()))
        for n in names:
            self.attach_file(n)

    def build_context(self, text: str, attachments: list[dict]) -> tuple[str, list[str]]:
        """(markdown context, labels) for the attachments and the @-mentions of the text."""
        from ..ai import context
        parts, labels = [], []
        mentions = []
        for a in attachments:
            if a.get("text") is not None:
                parts.append(f"## {a['label']}\n{context._fence(a.get('lang', ''), a['text'])}")
                labels.append(a["label"])
            elif a.get("mention"):
                mentions.append(a["mention"])
                labels.append(a["label"])
        for m in context.parse_mentions(text):
            if m not in mentions:
                mentions.append(m)
                labels.append(m.lstrip("@") if not m.startswith("@file:") else Path(m[6:]).name)
        budget = 9000 - sum(len(p) for p in parts) // 4
        if mentions:
            g = context.gather(self.win, mentions, budget_tokens=max(1500, budget))
            if g:
                parts.append(g)
        return "\n\n".join(parts), labels

    # ---------------------------------------------------------- sending
    def last_question(self) -> str:
        for m in reversed(self.chat["messages"]):
            if m["role"] == "user":
                return m["content"]
        return ""

    def busy(self) -> bool:
        return self.job is not None and not self.job.done

    def _send_or_stop(self):
        if self.busy():
            self.stop()
        else:
            self.send_input()

    def send_input(self):
        if self.busy():
            return
        text = strip_lrm(self.input.toPlainText()).strip()
        if not text and not self.attachments:
            return
        self.input.clear()
        self.input.completer.popup().hide()
        self.send(text or "Look at the attached context.")

    def send(self, text: str, attachments: list[dict] | None = None):
        """Ask a question (the chips are used and cleared when attachments is None)."""
        text = strip_lrm(text)
        if self.busy():
            self.stop()
        atts = list(self.attachments if attachments is None else attachments)
        if attachments is None:
            self.attachments = []
            self._render_chips()
        ctx, labels = self.build_context(text, atts)
        from ..ai import context
        q = context.strip_mentions(text) or text
        prompt = f"Context from the IDE:\n\n{ctx}\n\n---\n\n{q}" if ctx else q
        msg = {"role": "user", "content": text, "prompt": prompt, "context": labels, "time": time.time()}
        self.chat["messages"].append(msg)
        if not self.chat.get("title"):
            plain = re.sub(r'@file:"?([^"\s]+)"?', lambda m: Path(m.group(1)).name, text).replace("@", "")
            self.chat["title"] = re.sub(r"\s+", " ", plain).strip()[:70]
        self.title.setText(self.chat["title"] or "New chat")
        self._ask()

    def _system(self) -> str:
        s = SYSTEM_PROMPT
        proj = getattr(self.win, "project", None)
        if proj is not None:
            s += (f"\nThe open project: {getattr(proj, 'name', '')} (language: {getattr(proj, 'language', '')}, "
                  f"kind: {getattr(proj, 'kind', '') or 'forms'}), folder {getattr(proj, 'folder', '')}.")
        return s

    def provider_messages(self) -> list:
        """The conversation for the provider: the newest turns with their full context, older ones
        shortened to fit HISTORY_CHARS."""
        from .. import ai
        msgs = []
        for m in self.chat["messages"]:
            if m["role"] == "user":
                if msgs and msgs[-1]["role"] == "user":
                    msgs.pop()               # its answer failed / is missing: keep only the newer question
                msgs.append(m)
            elif m["role"] == "assistant" and m.get("content", "").strip() and not m.get("error"):
                msgs.append(m)
        out, used = [], 0
        for k, m in enumerate(reversed(msgs)):
            full = m.get("prompt") or m["content"] if m["role"] == "user" else m["content"]
            text = full if used + len(full) < HISTORY_CHARS or k == 0 else m["content"]
            if k > 0 and used + len(text) > HISTORY_CHARS:
                break
            used += len(text)
            out.append(ai.Message(m["role"], text))
        out.reverse()
        while out and out[0].role != "user":
            out.pop(0)
        return out

    def _ask(self):
        p, model = self.current_provider()
        history = self.provider_messages()
        ans = {"role": "assistant", "content": "", "provider": p.id, "provider_name": p.name, "model": model,
               "time": time.time()}
        self.chat["messages"].append(ans)
        self._streaming_idx = len(self.chat["messages"]) - 1
        self.render_all()
        cwd = None
        try:
            from ..ai import context
            f = context.solution_folder(self.win)
            cwd = str(f) if f else None
        except Exception:  # noqa: BLE001
            pass
        try:
            job = p.chat(history, model=model or None, system=self._system(), cwd=cwd,
                         purpose="chat")
        except Exception as e:  # noqa: BLE001
            self._failed(ans, f"{type(e).__name__}: {e}")
            return
        self.job = job
        job.delta.connect(lambda s, a=ans, j=job: self._delta(a, j, s))
        job.finished.connect(lambda t, a=ans, j=job: self._finished(a, j, t))
        job.failed.connect(lambda e, a=ans, j=job: self._failed(a, e, j))
        self._set_busy(True)

    def _delta(self, ans, job, s):
        if job is not self.job:
            return
        ans["content"] = job.text
        self._schedule_render()

    def _schedule_render(self):
        if not self._render_pending:
            self._render_pending = True
            QTimer.singleShot(70, self._render_streaming)

    def _render_streaming(self):
        self._render_pending = False
        i = self._streaming_idx
        if 0 <= i < len(self.chat["messages"]):
            self.view.set_message(f"m{i}", self.message_html(i))

    def _finished(self, ans, job, text):
        ans["content"] = text
        ans["elapsed"] = round(job.elapsed(), 1)
        usage = (job.meta or {}).get("usage")
        if usage:
            ans["usage"] = usage
        self._done(ans)
        self.answered.emit(text)

    def _failed(self, ans, err, job=None):
        if job is not None and job is not self.job and self.job is not None:
            return
        if job is not None and job.cancelled:
            ans["content"] = job.text
            ans["stopped"] = True
        else:
            ans["content"] = job.text if job is not None else ""
            ans["error"] = err
        if job is not None:
            ans["elapsed"] = round(job.elapsed(), 1)
        self._done(ans)

    def _done(self, ans):
        i = self.chat["messages"].index(ans) if ans in self.chat["messages"] else -1
        self._streaming_idx = -1
        self._set_busy(False)
        self.chat["updated"] = time.time()
        if i >= 0:
            self.view.set_message(f"m{i}", self.message_html(i))
        self.save()

    def stop(self):
        if self.busy():
            self.job.cancel()

    def regenerate(self):
        if self.busy():
            self.stop()
        msgs = self.chat["messages"]
        while msgs and msgs[-1]["role"] == "assistant":
            msgs.pop()
        if not msgs:
            return
        self._ask()

    def _set_busy(self, on: bool):
        self.send_btn.setText("Stop" if on else "Send")
        self.send_btn.setToolTip("Stop the answer" if on else "Send (Enter)")
        self.provider.setEnabled(not on)
        self.model.setEnabled(not on)
        self.busyChanged.emit(on)

    # ---------------------------------------------------------- rendering
    def _act(self, i: int):
        return lambda action, b: f"https://{ACT_HOST}/{action}?m={i}&b={b}"

    def message_html(self, i: int) -> str:
        m = self.chat["messages"][i]
        tm = time.strftime("%H:%M", time.localtime(m.get("time", time.time())))
        if m["role"] == "user":
            body, _b = render_markdown(ltr_mentions(m["content"]), None)
            ctx = ""
            if m.get("context"):
                ctx = '<div class="ctx">' + "".join(f"<span>{html.escape(c)}</span>" for c in m["context"]) + "</div>"
            return (f'<div class="msg user" id="m{i}"><div class="who"><span>You</span><span class="meta">{tm}</span>'
                    f'</div>{body}{ctx}</div>')
        streaming = i == self._streaming_idx
        body, blocks = render_markdown(m.get("content", ""), None if streaming else self._act(i))
        self.blocks[i] = blocks
        if streaming and not m.get("content"):
            body = '<p class="note">Thinking...</p>'
        if streaming:
            body += '<span class="cursor"></span>'
        meta = []
        if m.get("model"):
            meta.append(html.escape(m["model"]))
        if m.get("elapsed"):
            meta.append(f"{m['elapsed']:g} s")
        tail = ""
        if m.get("stopped"):
            tail += '<p class="note">(stopped)</p>'
        if m.get("error"):
            tail += (f'<div class="err" dir="{text_dir(m["error"])}">{html.escape(m["error"])}</div>'
                     f'<p><a href="https://{ACT_HOST}/retry?m={i}">Try again</a> &nbsp; '
                     f'<a href="https://{ACT_HOST}/settings?m={i}">AI Settings...</a></p>')
        links = ""
        if not streaming and i == len(self.chat["messages"]) - 1:
            links = (f'<span class="sp"></span><a href="https://{ACT_HOST}/copyall?m={i}">Copy</a>'
                     f'<a href="https://{ACT_HOST}/retry?m={i}">Regenerate</a>')
        elif not streaming:
            links = f'<span class="sp"></span><a href="https://{ACT_HOST}/copyall?m={i}">Copy</a>'
        name = html.escape(m.get("provider_name") or m.get("provider") or "AI")
        return (f'<div class="msg ai" id="m{i}"><div class="who"><span>{name}</span>'
                f'<span class="meta">{" - ".join(meta)}</span>{links}</div>{body}{tail}</div>')

    def welcome_html(self) -> str:
        try:
            p, m = self.current_provider()
            ok, why = p.available()
            st = f"Using <b>{html.escape(p.name)}</b>" + (f" ({html.escape(m)})" if m else "") + \
                 ("" if ok else f' - <span style="color:var(--rad-error)">{html.escape(why)}</span>')
        except Exception as e:  # noqa: BLE001
            st = html.escape(str(e))
        ex = [("Explain the current file", "Explain @current"),
              ("Find bugs in the selection", "Find bugs in @selection and show the fixed code"),
              ("Fix the errors of the Error List", "Fix these errors: @problems"),
              ("اشرح الكود المحدد بالعربي", "اشرح الكود ده بالتفصيل @selection")]
        links = "".join(f'<a class="ex" dir="{text_dir(t)}" href="https://{ACT_HOST}/example?q='
                        f'{QUrl.toPercentEncoding(q).data().decode()}">{html.escape(t)}</a>' for t, q in ex)
        return (f'<div class="welcome" id="welcome"><h2>AI Chat</h2><p>{st}</p>'
                f"<p>Ask about your code in any language. Add context with <code>@file:</code>, "
                f"<code>@selection</code>, <code>@problems</code>, <code>@project</code>, <code>@git</code> ... "
                f"Code blocks in answers have Copy, Insert, Apply (with a diff to review) and New file buttons.</p>"
                f"{links}<p>Free options: local models (Ollama, LM Studio) or CLI agents signed in with your own "
                f"account (Claude Code, Gemini CLI, Codex, Copilot ...) - Tools &gt; Options &gt; AI.</p></div>")

    def render_all(self):
        msgs = self.chat["messages"]
        if not msgs:
            self.blocks = {}
            self.view.set_all(self.welcome_html())
            return
        self.view.set_all("".join(self.message_html(i) for i in range(len(msgs))))

    # ---------------------------------------------------------- actions in the transcript
    def _on_action(self, url: QUrl):
        q = parse_qs(urlparse(url.toString()).query)
        act = url.path().strip("/")
        try:
            i = int(q.get("m", ["-1"])[0])
            b = int(q.get("b", ["-1"])[0])
        except ValueError:
            i = b = -1
        if act == "example":
            text = q.get("q", [""])[0]
            self.send(text)
            return
        if act == "open":
            self._open_link(q.get("p", [""])[0])
            return
        if act == "retry":
            self.regenerate()
            return
        if act == "settings":
            self.open_settings()
            return
        if act == "copyall" and 0 <= i < len(self.chat["messages"]):
            QApplication.clipboard().setText(self.chat["messages"][i].get("content", ""))
            self.win.statusBar().showMessage("Answer copied", 3000)
            return
        blocks = self.blocks.get(i) or []
        if not (0 <= b < len(blocks)):
            return
        blk = blocks[b]
        if act == "copy":
            QApplication.clipboard().setText(blk.code)
            self.win.statusBar().showMessage("Code copied", 3000)
        elif act == "insert":
            insert_code(self.win, blk.code)
        elif act == "apply":
            self.apply_block(blk)
        elif act == "newfile":
            self.new_file(blk)
        elif act == "run":
            run_in_terminal(self.win, blk.code, self)

    def _open_link(self, target: str):
        from ..ai import context
        target = target.split("#")[0]
        line = None
        m = re.match(r"^(.*?):(\d+)$", target)
        if m:
            target, line = m.group(1), int(m.group(2))
        p = context.resolve_file(self.win, target)
        if p is None:
            self.win.statusBar().showMessage(f"Not found: {target}", 4000)
            return
        open_path(self.win, p, line)

    def target_path(self, blk: CodeBlock) -> Path | None:
        from ..ai import context
        if blk.path:
            p = context.resolve_file(self.win, blk.path)
            if p is not None:
                return p
            root = context.project_folder(self.win) or context.solution_folder(self.win)
            cand = Path(blk.path)
            if not cand.is_absolute() and root is not None:
                return Path(root) / cand
            return cand
        _ed, path = context.current_editor(self.win)
        return Path(path) if path else None

    def apply_block(self, blk: CodeBlock, path=None, mode: str = "smart") -> bool:
        p = Path(path) if path else self.target_path(blk)
        if p is None:
            QMessageBox.information(self, "Apply", "Open the file to change in the editor first (or use New file).")
            return False
        return apply_code(self.win, blk.code, p, mode=mode, parent=self)

    def new_file(self, blk: CodeBlock):
        from ..ai import context
        root = context.project_folder(self.win) or context.solution_folder(self.win) or Path.home()
        ext = {"python": ".py", "javascript": ".js", "typescript": ".ts", "html": ".html", "css": ".css",
               "php": ".php", "vb": ".vb", "ring": ".ring", "json": ".json", "sql": ".sql", "bash": ".sh",
               "powershell": ".ps1", "markdown": ".md", "csharp": ".cs", "java": ".java", "cpp": ".cpp",
               "c": ".c", "xml": ".xml"}.get(blk.lang, ".txt")
        suggested = Path(root) / (blk.path or f"new_file{ext}")
        name, _ = QFileDialog.getSaveFileName(self, "Save code as a new file", str(suggested))
        if not name:
            return
        create_file(self.win, name, blk.code)

    # ---------------------------------------------------------- history
    def folder(self) -> Path:
        return _chat_root(self.win)

    def save(self):
        save_chat(self.folder(), self.chat)

    def new_chat(self):
        if self.busy():
            self.stop()
        self.save()
        self.chat = new_chat()
        self.blocks = {}
        self.title.setText("New chat")
        self.render_all()
        self.input.setFocus()

    def load_chat(self, data: dict):
        if self.busy():
            self.stop()
        self.save()
        self.chat = {k: v for k, v in data.items() if not k.startswith("_")}
        self.chat.setdefault("messages", [])
        self.title.setText(self.chat.get("title") or "Chat")
        self._streaming_idx = -1
        self.render_all()

    def load_latest(self):
        chats = list_chats(self.folder())
        if chats:
            self.load_chat(chats[0])
        else:
            self.chat = new_chat()
            self.title.setText("New chat")
            self.render_all()

    def on_project_changed(self):
        if self.busy():
            self.stop()
        self.save()
        self._file_cache = (0.0, [])
        self.chat = new_chat()
        self.load_latest()
        self.fill_providers()

    def _fill_history(self):
        m = self.hist_menu
        m.clear()
        chats = list_chats(self.folder())
        if not chats:
            a = m.addAction("(no saved chats)")
            a.setEnabled(False)
        for d in chats[:40]:
            when = time.strftime("%d %b %H:%M", time.localtime(d.get("updated", 0)))
            title = (d.get("title") or "Chat")[:60]
            a = m.addAction(f"{title}    {when}")
            a.setCheckable(True)
            a.setChecked(d.get("id") == self.chat.get("id"))
            a.triggered.connect(lambda _c=False, data=d: self.load_chat(data))
        m.addSeparator()
        m.addAction("New chat", self.new_chat)
        a = m.addAction("Delete all chats of this project...", self.delete_all)
        a.setEnabled(bool(chats))

    def delete_chat(self):
        f = self.folder() / f"{self.chat['id']}.json"
        try:
            if f.exists():
                f.unlink()
        except OSError:
            pass
        self.chat = new_chat()
        self.load_latest()

    def delete_all(self):
        if QMessageBox.question(self, "AI Chat", "Delete all saved chats of this project?") != \
                QMessageBox.StandardButton.Yes:
            return
        for d in list_chats(self.folder()):
            try:
                Path(d["_file"]).unlink()
            except OSError:
                pass
        self.chat = new_chat()
        self.render_all()

    def open_folder(self):
        f = self.folder()
        f.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(f)))

    def open_settings(self):
        try:
            from .ai_settings import show_ai_settings
            show_ai_settings(self.win)
        except Exception as e:  # noqa: BLE001
            QMessageBox.information(self, "AI Settings", f"Tools > Options > AI ({e})")

    def copy_markdown(self):
        out = []
        for m in self.chat["messages"]:
            who = "You" if m["role"] == "user" else (m.get("provider_name") or "AI")
            out.append(f"**{who}:**\n\n{m.get('content', '')}\n")
        QApplication.clipboard().setText("\n".join(out))
        self.win.statusBar().showMessage("Chat copied as Markdown", 3000)

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.StandardKey.New):
            self.new_chat()
            return
        if e.key() == Qt.Key.Key_Escape and self.busy():
            self.stop()
            return
        super().keyPressEvent(e)


# ============================================================================ code actions
def open_path(win, path, line=None):
    try:
        from .command_palette import open_path as _op
        _op(win, Path(path), line)
        return
    except Exception:  # noqa: BLE001
        pass
    opener = getattr(win, "open_file", None)
    if callable(opener):
        opener(str(path), line)
    else:
        win._editor_for_file(str(path))


def insert_code(win, code: str) -> bool:
    """Insert at the cursor (replacing the selection) of the current editor."""
    from ..ai import context
    ed, _path = context.current_editor(win)
    if ed is None or not hasattr(ed, "replaceSelectedText"):
        win.statusBar().showMessage("Open a code editor first - then Insert puts the code at its cursor", 5000)
        return False
    try:
        ed.beginUndoAction()
    except Exception:  # noqa: BLE001
        pass
    ed.replaceSelectedText(code)
    try:
        ed.endUndoAction()
    except Exception:  # noqa: BLE001
        pass
    try:
        ed.setFocus()
    except Exception:  # noqa: BLE001
        pass
    return True


def apply_code(win, code: str, path=None, lang: str = "", mode: str = "smart", parent=None) -> bool:
    """Apply a code block to a file through the diff review.  mode: smart (the whole file, or the
    matching function / block), whole, selection, cursor."""
    from ..ai import diffview
    from ..ai import context
    if path is None:
        _ed, cur = context.current_editor(win)
        path = cur or None
    if path is None:
        return False
    p = Path(path)
    ed = diffview.find_open_editor(win, p)
    old = diffview.editor_text(ed) if ed is not None else diffview.read_text(p)[0]
    note = ""
    new = None
    if mode == "smart":
        new, how = smart_apply(old, code)
        if new is None:
            sel = context.selected_text(ed) if ed is not None else ""
            if sel.strip() and sel in old:
                new = old.replace(sel, code.rstrip("\n") + ("\n" if sel.endswith("\n") else ""), 1)
                note = "The code replaces the selection of the editor."
            else:
                new = code.rstrip("\n") + "\n"
                note = ("The code block does not match a part of this file, so it replaces the whole file. "
                        "Untick the changes you do not want, or Reject and use Insert instead.")
        elif how == "block":
            note = "The code block replaces the matching part of the file."
    elif mode == "whole":
        new = code.rstrip("\n") + "\n"
    elif mode in ("selection", "cursor"):
        if ed is None:
            return False
        sel = context.selected_text(ed)
        if mode == "selection" and sel and sel in old:
            new = old.replace(sel, code, 1)
        else:
            line, col = ed.getCursorPosition()
            lines = old.split("\n")
            pos = sum(len(x) + 1 for x in lines[:line]) + col
            new = old[:pos] + code + old[pos:]
    if new is None:
        return False
    return diffview.apply_file_change(win, p, new, parent=parent or win, note=note,
                                      title=f"Apply AI changes - {p.name}")


def create_file(win, path, code: str) -> bool:
    from ..ai import diffview
    p = Path(path)
    if p.exists():
        return diffview.apply_file_change(win, p, code, parent=win, title=f"Replace {p.name}")
    try:
        diffview.write_text(p, code.rstrip("\n") + "\n")
    except OSError as e:
        QMessageBox.warning(win, "New file", f"Cannot write {p}:\n{e}")
        return False
    diffview._refresh_tree(win)
    QTimer.singleShot(50, lambda: open_path(win, p))
    return True


def run_in_terminal(win, code: str, parent=None) -> bool:
    cmds = []
    for line in code.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if not s or s.startswith("#") and not s.startswith("#!"):
            continue
        s = re.sub(r"^(\$|>|PS [^>]*>)\s+", "", s)
        cmds.append(s)
    if not cmds:
        return False
    term = getattr(win, "terminal", None)
    if term is None:
        QMessageBox.information(parent or win, "Run in Terminal", "The Terminal is not available.")
        return False
    shown = "\n".join(cmds[:20]) + ("\n..." if len(cmds) > 20 else "")
    if QMessageBox.question(parent or win, "Run in Terminal",
                            f"Run in the Terminal ({term.folder()}):\n\n{shown}") != QMessageBox.StandardButton.Yes:
        return False
    try:
        from .terminal import show_terminal
        show_terminal(win)
    except Exception:  # noqa: BLE001
        pass
    for c in cmds:
        term.run_command(c)
    return True


# ============================================================================ hooks into editors / explorer
class _MenuHook(QObject):
    """Adds "Ask AI about This" to the Solution Explorer menu: it notes the item under the mouse on
    the ContextMenu event and adds the action when the next top-level menu shows."""

    def __init__(self, win, panel_getter):
        super().__init__(win)
        self.win = win
        self.panel = panel_getter
        self.pending = None
        tree = getattr(win, "solution", None)
        if tree is not None:
            tree.viewport().installEventFilter(self)

    def eventFilter(self, obj, ev):  # noqa: N802
        t = ev.type()
        if t == QEvent.Type.ContextMenu and obj is getattr(self.win, "solution", None).viewport():
            item = self.win.solution.itemAt(ev.pos())
            self.pending = (explorer_target(self.win, item), time.time())
            QApplication.instance().installEventFilter(self)
            QTimer.singleShot(1500, self._clear)
        elif t == QEvent.Type.Show and isinstance(obj, QMenu) and self.pending is not None and \
                not isinstance(obj.parentWidget(), QMenu):
            target, when = self.pending
            self._clear()
            if target is not None and time.time() - when < 1.5:
                obj.addSeparator()
                a = obj.addAction("Ask AI about This")
                a.triggered.connect(lambda _c=False, tg=target: ask_about(self.win, tg))
        return False

    def _clear(self):
        if self.pending is not None or True:
            self.pending = None
            try:
                QApplication.instance().removeEventFilter(self)
            except Exception:  # noqa: BLE001
                pass


def explorer_target(win, item):
    """What a Solution Explorer item stands for: ("file", path) | ("project", None) | None."""
    if item is None:
        return ("project", None)
    data = item.data(0, Qt.ItemDataRole.UserRole)
    if not data or not isinstance(data, (tuple, list)) or len(data) < 2:
        return None
    kind, name = data[0], data[1]
    key = item.data(0, Qt.ItemDataRole.UserRole + 10)
    st = getattr(win, "_pstates", {}).get(key) if key else None
    proj = st["project"] if st else getattr(win, "project", None)
    if kind == "webfile":
        return ("file", Path(name))
    if kind in ("project", "solution", "webfolder"):
        return ("project", None)
    if proj is None:
        return None
    folder = Path(proj.folder)
    if kind == "module":
        return ("file", folder / name)
    if kind in ("design", "code", "generated"):
        try:
            from ..languages import plugin_for_form
            code = plugin_for_form(proj, name).code_file(name)
            if kind == "design" and (folder / f"{name}.form").exists():
                return ("file", folder / f"{name}.form")
            return ("file", folder / code)
        except Exception:  # noqa: BLE001
            return ("file", folder / f"{name}.form")
    return None


def ask_about(win, target):
    panel = getattr(win, "ai_chat", None)
    if panel is None:
        return
    show_chat(win)
    if target and target[0] == "file" and target[1]:
        panel.attach_file(target[1])
    elif target and target[0] == "project":
        panel.attach("@project", label="Project files")
    elif target and target[0] == "selection":
        panel.attach_selection()
    panel.input.setFocus()


def _hook_editor(win, ed):
    if ed is None or getattr(ed, "_ai_chat_hooked", False) or not hasattr(ed, "contextMenuAboutToShow"):
        return
    try:
        ed.contextMenuAboutToShow.connect(lambda m, e=ed: _editor_menu(win, m, e))
        ed._ai_chat_hooked = True
    except Exception:  # noqa: BLE001
        pass


def _editor_menu(win, m: QMenu, ed):
    a = QAction("Ask AI about This", m)
    a.setShortcut(QKeySequence("Ctrl+Alt+I"))
    a.triggered.connect(lambda: ask_about(win, ("selection", None)))
    first = m.actions()[0] if m.actions() else None
    m.insertAction(first, a)
    if first is not None:
        m.insertSeparator(first)


def _hook_open_editors(win):
    tabs = getattr(win, "tabs", None)
    if tabs is None:
        return
    for i in range(tabs.count()):
        _hook_editor(win, getattr(tabs.widget(i), "editor", None))


def show_chat(win, focus: bool = True):
    try:
        from . import workbench
        wb = workbench.get(win)
        if wb is not None and wb.mode != "vs":
            wb.show_view("chat")
            if focus:
                win.ai_chat.input.setFocus()
            return
    except Exception:  # noqa: BLE001
        pass
    d = win.dock_ai_chat
    d.show()
    d.raise_()
    if focus:
        win.ai_chat.input.setFocus()


def toggle_chat(win):
    d = win.dock_ai_chat
    if d.isVisible() and not d.visibleRegion().isEmpty() and win.ai_chat.input.hasFocus():
        d.hide()
    else:
        show_chat(win)


# ============================================================================ public helpers
def ask(win, text: str = "", mentions=(), send: bool = False):
    """Open the chat with a question (and context mentions); send=True asks at once."""
    panel = getattr(win, "ai_chat", None)
    if panel is None:
        return None
    show_chat(win)
    for m in mentions or ():
        panel.attach(m)
    if send and text:
        panel.send(text)
    elif text:
        panel.input.setPlainText(text)
        panel.input.moveCursor(QTextCursor.MoveOperation.End)
    return panel


def attach(win, mention: str, label: str | None = None, text: str | None = None):
    panel = getattr(win, "ai_chat", None)
    if panel is not None:
        panel.attach(mention, label=label, text=text)


def install(win) -> None:
    panel = ChatPanel(win)
    win.ai_chat = panel
    d = QDockWidget("AI Chat", win)
    d.setObjectName("AI Chat")
    d.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, d)
    sol = getattr(win, "dock_solution", None)
    if sol is not None:
        win.tabifyDockWidget(sol, d)
        sol.raise_()
    win.dock_ai_chat = d
    a = QAction("AI &Chat", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+I"))
    a.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    a.triggered.connect(lambda: show_chat(win))
    win.a_ai_chat = a
    win.addAction(a)
    view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
    if view is not None:
        view.addAction(a)
    tools = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "Tools"), None)
    if tools is not None:
        tools.addAction("Ask AI about the &Selection", lambda: ask_about(win, ("selection", None)))
    try:
        from . import workbench
        workbench.register_view("chat", "AI Chat", icon="chat", factory=lambda w: getattr(w, "dock_ai_chat", None),
                                modes=("vscode", "agent"), area="side", order=70, tooltip="AI Chat (Ctrl+Alt+I)")
    except Exception as e:  # noqa: BLE001
        win.log(f"[ai chat] workbench: {e}")
    # "Ask AI about This" in the editors and the Solution Explorer
    try:
        from .. import editor as _editor_mod
        hooks = getattr(_editor_mod, "EDITOR_HOOKS", None)
        if isinstance(hooks, list):
            hooks.append(lambda ed: _hook_editor(win, ed))
    except Exception:  # noqa: BLE001
        pass
    try:
        win.tabs.currentChanged.connect(lambda _i: _hook_open_editors(win))
        win.tabs.tabBar().tabMoved.connect(lambda *_a: _hook_open_editors(win))
    except Exception:  # noqa: BLE001
        pass
    win._ai_chat_menu_hook = _MenuHook(win, lambda: win.ai_chat)
    # follow the open project (history is per project)
    orig_open = win.open_project

    def open_project(*args, **kw):
        r = orig_open(*args, **kw)
        try:
            panel.on_project_changed()
        except Exception as e:  # noqa: BLE001
            win.log(f"[ai chat] {e}")
        return r
    win.open_project = open_project
    def stop_on_close() -> None:
        panel.stop()
        panel.save()
    win.extension_points.add_shutdown_step(stop_on_close, "AI chat")      # errors are logged


__all__ = ["ChatPanel", "render_markdown", "smart_apply", "text_dir", "fence_path", "ask", "attach",
           "insert_code", "apply_code", "create_file", "run_in_terminal", "show_chat", "list_chats", "save_chat"]
