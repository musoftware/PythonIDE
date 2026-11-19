"""AI in the editor and the designers (docs/CONTRACTS.md 9.4).

* Inline completions (ghost text) in Monaco: radide/web/editor.html registers an inline
  completions provider that asks Python through the `rad` QWebChannel bridge; the request goes
  to ai.default("complete").  Debounced, Tab accepts, Esc dismisses, Alt+\\ asks explicitly.
  The "AI" button of the status bar turns it on/off.  CLI agents (they spend the user's quota and
  are slow) are only asked on Alt+\\; local models and API keys are asked automatically.
* Ctrl+I inline edit: a prompt box over the selection -> the streamed replacement is shown as a
  diff in the box -> Accept (Ctrl+Enter) / Reject (Esc) / Review in the side-by-side diff view.
* Editor right-click "AI" submenu: Explain, Fix, Refactor, Add comments, Generate docs,
  Generate tests, Translate to another language of the IDE.
* Error List "Fix with AI" / "Explain with AI", Git Changes "Generate commit message",
  form designer "Generate Form with AI..." and "Generate Event Handler with AI...".

Explanations go to the AI Chat panel when it is installed (radide/features/ai_chat.py), else to
a result window.  Everything uses radide.ai (9.1) and radide.ai.diffview (9.3)."""
from __future__ import annotations

import difflib
import json
import keyword
import re
import time
from collections import OrderedDict
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QShortcut, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget, QMenu, QMessageBox, QPlainTextEdit,
                             QPushButton, QTextBrowser, QToolButton, QVBoxLayout)

from .. import ai, theme

INLINE_KEY = "ai/inline/enabled"
DELAY_KEY = "ai/inline/delay"
ANSWER_LANG_KEY = "ai/answer_language"
LANG_NOTE = {"Arabic": "Write the whole answer in Arabic (اكتب الإجابة كاملة باللغة العربية), "
                       "keep code and identifiers as they are."}
ANSWER_LANGS = [("English", "English"), ("Arabic", "العربية (Arabic)")]

_WIN = None                       # the last MainWindow this feature was installed into


def _settings():
    return ai.settings()


def _bool(v, default=False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes", "on")


def inline_enabled() -> bool:
    return _bool(_settings().value(INLINE_KEY, True), True)


def inline_delay() -> int:
    try:
        return max(150, min(3000, int(_settings().value(DELAY_KEY, 450))))
    except (TypeError, ValueError):
        return 450


def answer_language() -> str:
    v = str(_settings().value(ANSWER_LANG_KEY, "English") or "English")
    return v if v in dict(ANSWER_LANGS) else "English"


def _win_of(widget):
    w = widget.window() if widget is not None else None
    if w is not None and hasattr(w, "_ai_editor"):
        return w
    return _WIN


def ready(p) -> tuple[bool, str]:
    """p.available(), but a local server (Ollama / LM Studio) is always tried: radide.ai starts
    Ollama on demand, and a busy server can miss the quick detection probe - the request itself
    then reports a clear error."""
    ok, why = p.available()
    if not ok and p.kind == "local" and p.enabled():
        return True, ""
    return ok, why


def _log(win, text: str):
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        pass


def _status(win, text: str, ms: int = 5000):
    try:
        win.statusBar().showMessage(text, ms)
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ editor helpers
def is_monaco(ed) -> bool:
    return hasattr(ed, "resolve_inline")


def editor_path(ed) -> str:
    return str(getattr(ed, "path", "") or "")


def editor_language(ed) -> str:
    if hasattr(ed, "language_id"):
        try:
            lang = ed.language_id()
            if not lang.startswith("rad-"):
                return lang
        except Exception:  # noqa: BLE001
            pass
    plugin = getattr(ed, "plugin", None)
    if plugin is not None and getattr(plugin, "display_name", ""):
        return plugin.display_name
    from ..ai.context import lang_of
    return lang_of(editor_path(ed)) or "text"


def get_selection(ed) -> tuple[int, int, int, int]:
    """(l1, c1, l2, c2) ordered, 0-based."""
    if hasattr(ed, "_selection") and is_monaco(ed):
        l1, c1, l2, c2 = ed._selection
    else:
        cur = ed.textCursor()
        doc = ed.document()
        a, b = sorted((cur.anchor(), cur.position()))
        ba, bb = doc.findBlock(a), doc.findBlock(b)
        l1, c1, l2, c2 = ba.blockNumber(), a - ba.position(), bb.blockNumber(), b - bb.position()
    if (l2, c2) < (l1, c1):
        l1, c1, l2, c2 = l2, c2, l1, c1
    return l1, c1, l2, c2


def get_cursor(ed) -> tuple[int, int]:
    return tuple(ed.getCursorPosition())


def editor_lines(ed) -> list[str]:
    return ed.toPlainText().split("\n")


def text_of_range(ed, rng) -> str:
    l1, c1, l2, c2 = rng
    lines = editor_lines(ed)
    if l1 >= len(lines):
        return ""
    if l1 == l2:
        return lines[l1][c1:c2]
    return "\n".join([lines[l1][c1:]] + lines[l1 + 1:l2] + [lines[min(l2, len(lines) - 1)][:c2]])


def offset_of(text: str, line: int, col: int) -> int:
    lines = text.split("\n")
    line = max(0, min(line, len(lines) - 1))
    return sum(len(x) + 1 for x in lines[:line]) + min(col, len(lines[line]))


def full_lines(ed, l1: int, l2: int) -> tuple[int, int, int, int]:
    lines = editor_lines(ed)
    l2 = min(l2, len(lines) - 1)
    return l1, 0, l2, len(lines[l2])


def selection_scope(ed, whole_limit: int = 200, around: int = 25):
    """Range an AI command works on: the selection (whole lines), else the whole file when it is
    small, else the lines around the cursor."""
    l1, c1, l2, c2 = get_selection(ed)
    if (l1, c1) != (l2, c2):
        if l2 > l1 and c2 == 0:
            l2 -= 1
        return full_lines(ed, l1, l2), "selection"
    lines = editor_lines(ed)
    if len(lines) <= whole_limit:
        return full_lines(ed, 0, len(lines) - 1), "file"
    line = get_cursor(ed)[0]
    return full_lines(ed, max(0, line - around), min(len(lines) - 1, line + around)), "lines"


def replace_range(ed, rng, new_text: str) -> None:
    l1, c1, l2, c2 = rng
    ed.beginUndoAction()
    try:
        ed.setSelection(l1, c1, l2, c2)
        ed.replaceSelectedText(new_text)
    finally:
        ed.endUndoAction()


def set_whole_text(ed, text: str) -> None:
    lines = editor_lines(ed)
    replace_range(ed, (0, 0, len(lines) - 1, len(lines[-1])), text)


def caret_point(ed, callback, line: int | None = None) -> None:
    """callback(QPoint top_left_in_editor, line_height) of the caret (or of the selection start)."""
    if is_monaco(ed):
        def got(v):
            try:
                x, y, h = (int(v[0]), int(v[1]), int(v[2] or 18))
            except Exception:  # noqa: BLE001
                x, y, h = 40, 40, 18
            callback(QPoint(x, y), h)
        if ed._ready:
            ed.page().runJavaScript("radCaretPoint()", got)
        else:
            got(None)
        return
    try:
        r = ed.cursorRect()
        p = ed.viewport().mapTo(ed, r.topLeft())
        callback(p, r.height())
    except Exception:  # noqa: BLE001
        callback(QPoint(40, 40), 18)


def indent_of(s: str) -> str:
    return s[:len(s) - len(s.lstrip(" \t"))]


def common_indent(text: str) -> str:
    ind = None
    for ln in text.split("\n"):
        if not ln.strip():
            continue
        i = indent_of(ln)
        if ind is None or len(i) < len(ind):
            ind = i
    return ind or ""


def reindent(text: str, base: str) -> str:
    """Move a block so its least-indented lines start with *base*."""
    cur = common_indent(text)
    out = []
    for ln in text.split("\n"):
        if not ln.strip():
            out.append("")
            continue
        out.append(base + (ln[len(cur):] if ln.startswith(cur) else ln.lstrip()))
    return "\n".join(out)


def strip_fences(text: str) -> str:
    """The code of an answer: its (longest) fenced block, else the text without stray fences."""
    blocks = ai.extract_code_blocks(text or "")
    if blocks:
        return max(blocks, key=lambda b: len(b[1]))[1] if len(blocks) > 1 else blocks[0][1]
    t = (text or "").strip("\n")
    t = re.sub(r"^\s*```[\w#+.\-]*[^\n]*\n?", "", t)
    t = re.sub(r"\n?```\s*$", "", t)
    return t


def partial_code(text: str) -> str:
    """While streaming: the code inside the (first, possibly unclosed) fence; '' before it opens."""
    m = re.search(r"```[\w#+.\-]*[^\n]*\n", text)
    if not m:
        return "" if "```" in text or not text.strip() else text
    body = text[m.end():]
    end = body.find("\n```")
    return body if end < 0 else body[:end]


def fit_replacement(original: str, new: str, insert: bool, cur_indent: str = "") -> str:
    """Make a model's replacement fit the range it replaces (indentation, final newline)."""
    new = new.replace("\r\n", "\n")
    if insert:
        if "\n" in new.strip("\n"):
            body = reindent(new.strip("\n"), cur_indent)
            return body[len(cur_indent):] if body.startswith(cur_indent) else body.lstrip()
        return new.strip("\n").lstrip() if cur_indent else new.strip("\n")
    base = common_indent(original)
    if original.strip() and new.strip() and common_indent(new) != base:
        new = reindent(new, base)            # the model shifted the whole block (or dropped its indent)
    if original.endswith("\n") and not new.endswith("\n"):
        new += "\n"
    elif not original.endswith("\n"):
        new = new.rstrip("\n")
    return new


# ============================================================================ prompts
EDIT_SYSTEM = ("You are an expert programmer working inside an IDE. You rewrite one part of a file according "
               "to the user's instruction. Reply with ONLY the complete replacement code for that part, in a "
               "single fenced code block. Keep the surrounding indentation and coding style. Do not repeat the "
               "code before or after the part, do not add explanations.")

INSERT_SYSTEM = ("You are an expert programmer working inside an IDE. You write new code that is inserted at the "
                 "cursor according to the user's instruction. Reply with ONLY that code in a single fenced code "
                 "block, indented for the cursor position. No explanations.")


def _fence(lang: str, text: str) -> str:
    f = "```"
    while f in text:
        f += "`"
    return f"{f}{lang}\n{text}\n{f}"


def edit_prompt(ed, rng, instruction: str, extra: str = "") -> tuple[str, str]:
    """(system, user) for rewriting *rng* of the editor (or inserting at it when it is empty)."""
    lines = editor_lines(ed)
    l1, c1, l2, c2 = rng
    lang = editor_language(ed)
    name = Path(editor_path(ed)).name or "untitled"
    insert = (l1, c1) == (l2, c2)
    before = "\n".join(lines[max(0, l1 - 80):l1])
    after = "\n".join(lines[l2 + 1:l2 + 41])
    if insert:
        cur = lines[l1] if l1 < len(lines) else ""
        before = "\n".join(lines[max(0, l1 - 80):l1] + [cur[:c1] + "<CURSOR>" + cur[c1:]])
        user = (f"File: {name} (language: {lang})\n\nCode around the cursor (context, do not repeat it):\n"
                f"{_fence(lang, before + chr(10) + after)}\n\n")
    else:
        part = text_of_range(ed, rng)
        whole = len(lines) <= l2 - l1 + 1
        user = f"File: {name} (language: {lang})\n\n"
        if before.strip():
            user += f"Code before the part (context only):\n{_fence(lang, before)}\n\n"
        user += ("The whole file to rewrite:\n" if whole else "THE PART TO REWRITE:\n") + _fence(lang, part) + "\n\n"
        if after.strip():
            user += f"Code after the part (context only):\n{_fence(lang, after)}\n\n"
    if extra:
        user += extra.rstrip() + "\n\n"
    user += f"Instruction: {instruction}"
    return (INSERT_SYSTEM if insert else EDIT_SYSTEM), user


ACTIONS = {
    # id: (menu text, kind, instruction)   kind: edit = rewrite + diff, ask = explanation window
    "explain": ("Explain", "ask", "Explain what this code does, step by step, and point out anything surprising "
                "or wrong."),
    "fix": ("Fix", "edit", "Find and fix the bugs in this code (errors, wrong logic, edge cases). Keep the "
            "behaviour that is correct."),
    "refactor": ("Refactor", "edit", "Refactor this code to be cleaner and easier to read without changing its "
                 "behaviour (better names, smaller functions, remove duplication)."),
    "comments": ("Add Comments", "edit", "Add short helpful comments to this code. Do not change the code itself."),
    "docs": ("Generate Docs", "edit", "Add documentation comments (docstrings / doc comments in the usual style "
             "of the language) to every function, class and module in this code. Do not change the code itself."),
    "tests": ("Generate Tests", "ask", "Write unit tests for this code using the usual test framework of the "
              "language. Put all the test code in one fenced code block, then explain briefly how to run them."),
}


def _ask_system() -> str:
    lang = answer_language()
    return ("You are an expert programmer helping inside an IDE. Use Markdown with fenced code blocks. "
            f"Write your answer in {lang}" + (" (keep code, identifiers and technical terms as they are)."
                                               if lang != "English" else "."))


# ============================================================================ inline completions
class InlineCompleter(QObject):
    """Answers the Monaco inline completion requests (MonacoEditor.inline_provider)."""

    def __init__(self, ctl: "AIEditor"):
        super().__init__(ctl)
        self.ctl = ctl
        self.jobs: dict = {}                 # (id(editor), req) -> ChatJob
        self.cache: OrderedDict = OrderedDict()
        self.backoff_until = 0.0
        self.last_error = ""
        self.requests = 0                    # statistics (tests / tooltip)
        self.answers = 0

    def provider(self, explicit: bool):
        p, model = ai.default("complete")
        ok, why = ready(p)
        if not ok:
            return None, model, why or f"{p.name} is not available"
        if not explicit and p.kind in ("cli", "web"):
            return None, model, f"{p.name} is asked only with Alt+\\ (it is slow and uses your quota)"
        return p, model, ""

    def request(self, ed, req: int, line: int, col: int, explicit: bool):
        if not explicit and (not inline_enabled() or time.time() < self.backoff_until):
            ed.resolve_inline(req, None)
            return
        p, model, why = self.provider(explicit)
        if p is None:
            if explicit:
                _status(self.ctl.win, f"AI completion: {why}", 8000)
            ed.resolve_inline(req, None)
            return
        text = ed.toPlainText()
        off = offset_of(text, line, col)
        prefix, suffix = text[:off], text[off:]
        key = (p.id, model, prefix[-2000:], suffix[:400])
        if key in self.cache:
            self.cache.move_to_end(key)
            ed.resolve_inline(req, self.cache[key] or None)
            return
        for k in [k for k in self.jobs if k[0] == id(ed)]:          # only the newest request matters
            self._cancel_key(k)
        self.requests += 1
        try:
            job = p.complete(prefix, suffix, editor_language(ed), model=model or None)
        except Exception as e:  # noqa: BLE001
            ed.resolve_inline(req, None)
            self._failed(str(e), explicit)
            return
        k = (id(ed), req)
        self.jobs[k] = job
        self.ctl.set_busy(True)
        limit = QTimer(self)
        limit.setSingleShot(True)
        limit.timeout.connect(lambda: self._cancel_key(k))
        limit.start(60000 if explicit else 20000)

        def done(t, ok=True):
            limit.stop()
            if self.jobs.pop(k, None) is None:
                return
            self.ctl.set_busy(bool(self.jobs))
            if not ok:
                ed.resolve_inline(req, None)
                if t != "Cancelled":
                    self._failed(t, explicit)
                return
            t = t or ""
            core = prefix.rsplit("\n", 1)[-1].lstrip()
            if core and t.startswith(core) and len(t) > len(core):
                t = t[len(core):]                 # the model repeated what is already typed on the line
            if not t.strip():
                t = ""
            self.cache[key] = t
            while len(self.cache) > 200:
                self.cache.popitem(last=False)
            self.answers += 1 if t else 0
            self.last_error = ""
            ed.resolve_inline(req, t or None)
            if explicit and not t:
                _status(self.ctl.win, "AI completion: no suggestion here", 4000)
        job.finished.connect(lambda t: done(t, True))
        job.failed.connect(lambda e: done(e, False))

    def _cancel_key(self, k):
        job = self.jobs.get(k)
        if job is not None:
            job.cancel()            # failed("Cancelled") -> done() resolves the request

    def cancel(self, ed, req: int):
        self._cancel_key((id(ed), req))

    def _failed(self, msg: str, explicit: bool):
        self.last_error = msg
        self.backoff_until = time.time() + (5 if explicit else 60)
        first = msg.strip().splitlines()[0] if msg.strip() else "failed"
        _status(self.ctl.win, f"AI completion failed: {first[:200]}", 10000)
        self.ctl.update_button()


# ============================================================================ inline edit (Ctrl+I)
class DiffHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str):
        try:
            from ..ai.diffview import colors
            c = colors()
            add, rem = c["add"], c["del"]
        except Exception:  # noqa: BLE001
            add, rem = QColor("#d7f5dc"), QColor("#f9d6d5")
        fmt = QTextCharFormat()
        if text.startswith("+"):
            fmt.setBackground(add)
        elif text.startswith("-"):
            fmt.setBackground(rem)
        else:
            return
        self.setFormat(0, max(1, len(text)), fmt)


def diff_lines(old: str, new: str, partial: bool = False) -> str:
    a, b = old.split("\n"), new.split("\n")
    if partial:                       # still streaming: compare with the same number of old lines
        a = a[:max(len(b), 1)] if len(b) < len(a) else a
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            out += ["  " + x for x in a[i1:i2]]
        else:
            out += ["- " + x for x in a[i1:i2]]
            out += ["+ " + x for x in b[j1:j2]]
    return "\n".join(out)


class InlineEditBox(QFrame):
    """The Ctrl+I box: instruction -> streamed diff -> Accept / Reject."""

    def __init__(self, ctl: "AIEditor", ed, rng, instruction: str = "", extra: str = "", title: str = "",
                 anchor: QPoint | None = None, line_h: int = 18):
        super().__init__(ed)
        self.ctl, self.ed, self.rng, self.extra = ctl, ed, rng, extra
        self.original = text_of_range(ed, rng)
        self.insert = rng[:2] == rng[2:]
        lines = editor_lines(ed)
        self.cur_indent = indent_of(lines[rng[0]])[:rng[1]] if rng[0] < len(lines) else ""
        self.job = None
        self.result = None
        self._last_render = 0.0
        self.setObjectName("radAiInlineEdit")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 5, 6, 6)
        lay.setSpacing(4)
        top = QHBoxLayout()
        self.caption = QLabel(title or ("AI: insert code" if self.insert else "AI: edit selection"))
        f = self.caption.font()
        f.setBold(True)
        self.caption.setFont(f)
        top.addWidget(self.caption)
        self.provider = QLabel()
        theme.role(self.provider, "muted")
        top.addWidget(self.provider, 1)
        close = QToolButton(text="x")
        close.setAutoRaise(True)
        close.setToolTip("Close (Esc)")
        close.clicked.connect(self.reject)
        top.addWidget(close)
        lay.addLayout(top)
        row = QHBoxLayout()
        self.prompt = QLineEdit(instruction)
        self.prompt.setPlaceholderText("Describe the change - e.g. 'add error handling'  (Enter = generate)")
        self.prompt.setClearButtonEnabled(True)
        self.prompt.returnPressed.connect(self.generate)
        row.addWidget(self.prompt, 1)
        self.b_go = QPushButton("Generate")
        self.b_go.clicked.connect(self.generate)
        row.addWidget(self.b_go)
        lay.addLayout(row)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.view.setFont(QFont("Consolas", 9))
        self._hl = DiffHighlighter(self.view.document())
        self.view.hide()
        lay.addWidget(self.view, 1)
        self.state = QLabel()
        theme.role(self.state, "muted")
        self.state.hide()
        lay.addWidget(self.state)
        btns = QHBoxLayout()
        self.b_accept = QPushButton("Accept")
        self.b_accept.setToolTip("Replace the code (Ctrl+Enter)")
        self.b_accept.clicked.connect(self.accept)
        self.b_reject = QPushButton("Reject")
        self.b_reject.setToolTip("Keep the original code (Esc)")
        self.b_reject.clicked.connect(self.reject)
        self.b_review = QPushButton("Review Diff...")
        self.b_review.setToolTip("Open the side-by-side diff view (accept single changes, edit the result)")
        self.b_review.clicked.connect(self.review)
        self.b_stop = QPushButton("Stop")
        self.b_stop.clicked.connect(self.stop)
        for b in (self.b_accept, self.b_reject, self.b_review, self.b_stop):
            btns.addWidget(b)
            b.hide()
        btns.addStretch(1)
        lay.addLayout(btns)
        QShortcut(QKeySequence("Esc"), self, self.reject, context=Qt.ShortcutContext.WidgetWithChildrenShortcut)
        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(seq), self, self._ctrl_enter, context=Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._restyle()
        theme.changed.connect(self._restyle)
        p, model = ai.default("edit")
        self.provider.setText(f"{p.name}" + (f" - {model}" if model else ""))
        self.anchor, self.line_h = anchor or QPoint(40, 40), line_h
        self._place(compact=True)
        self.show()
        self.raise_()
        self.prompt.setFocus()

    def _restyle(self, *_a):
        try:
            self.setStyleSheet(f"#radAiInlineEdit {{ background: {theme.color('base')}; "
                               f"border: 1px solid {theme.color('accent')}; border-radius: 4px; }}")
        except Exception:  # noqa: BLE001
            pass

    def _place(self, compact: bool):
        ed = self.ed
        w = max(320, min(ed.width() - 24, 760))
        h = 74 if compact else max(150, min(int(ed.height() * 0.55), 160 + 16 * self.view.blockCount()))
        x = max(8, min(self.anchor.x() - 30, ed.width() - w - 16))
        below = self.anchor.y() + self.line_h + 2
        y = below if below + h <= ed.height() - 4 or self.anchor.y() < h + 8 else self.anchor.y() - h - 4
        y = max(2, min(y, max(2, ed.height() - h - 4)))
        self.setGeometry(x, y, w, h)

    # ------------------------------------------------------------ flow
    def generate(self):
        instr = self.prompt.text().strip()
        if not instr:
            self.prompt.setFocus()
            return
        self.stop(silent=True)
        self.ctl.remember_prompt(instr)
        system, user = edit_prompt(self.ed, self.rng, instr, self.extra)
        p, model = ai.default("edit")
        ok, why = ready(p)
        if not ok:
            self._show_state(f"{p.name}: {why}  (Tools > Options > AI)", error=True)
            return
        self.result = None
        self.view.clear()
        self.view.show()
        self._show_state(f"Generating with {p.name}...")
        for b in (self.b_accept, self.b_review):
            b.hide()
        self.b_stop.show()
        self.b_reject.show()
        self.b_go.setText("Regenerate")
        self._place(compact=False)
        win = self.ctl.win
        self.job = p.chat([ai.Message("user", user)], model=model or None, system=system, temperature=0.2,
                          purpose="edit", cwd=str(Path(editor_path(self.ed)).parent) if editor_path(self.ed) else None)
        self.job.delta.connect(self._delta)
        self.job.finished.connect(self._finished)
        self.job.failed.connect(self._failed)
        _status(win, f"AI edit: asking {p.name}...", 3000)

    def _delta(self, _s):
        now = time.time()
        if now - self._last_render < 0.12:
            return
        self._last_render = now
        code = partial_code(self.job.text if self.job is not None else "")
        if code:
            self._render(code, partial=True)

    def _render(self, new: str, partial: bool):
        sb = self.view.verticalScrollBar()
        at_end = sb.value() >= sb.maximum() - 4
        self.view.setPlainText(diff_lines(self.original.rstrip("\n"), new.rstrip("\n"), partial) if not self.insert
                               else "\n".join("+ " + x for x in new.rstrip("\n").split("\n")))
        if at_end and partial:
            sb.setValue(sb.maximum())
        self._place(compact=False)

    def _finished(self, text: str):
        self.job = None
        self.b_stop.hide()
        new = fit_replacement(self.original, strip_fences(text), self.insert, self.cur_indent)
        if not new.strip() and not self.original.strip():
            self._show_state("The AI returned no code. Try another instruction.", error=True)
            return
        self.result = new
        self._render(new, partial=False)
        same = new == self.original
        self._show_state("No changes." if same else
                         "Ctrl+Enter = Accept, Esc = Reject.  Review Diff... picks single changes.")
        self.b_accept.setVisible(not same)
        self.b_review.setVisible(not same)
        self.b_reject.show()
        self.b_accept.setDefault(True)
        self.b_accept.setFocus()

    def _failed(self, msg: str):
        self.job = None
        self.b_stop.hide()
        if msg != "Cancelled":
            self._show_state(msg.strip().splitlines()[0][:300] if msg.strip() else "Failed", error=True)

    def _show_state(self, text: str, error: bool = False):
        theme.role(self.state, "error" if error else "muted")
        self.state.setText(text)
        self.state.setWordWrap(True)
        self.state.show()
        if error:
            self.b_reject.show()

    def _ctrl_enter(self):
        if self.result is not None and self.b_accept.isVisible():
            self.accept()
        else:
            self.generate()

    def stop(self, silent: bool = False):
        if self.job is not None:
            job, self.job = self.job, None
            job.cancel()
            if not silent:
                self._show_state("Stopped.")
        self.b_stop.hide()

    def _apply(self, new: str) -> bool:
        cur = text_of_range(self.ed, self.rng)
        rng = self.rng
        if cur != self.original:                 # the text moved meanwhile: find the original again
            full = self.ed.toPlainText()
            k = full.find(self.original) if self.original else -1
            if k < 0:
                QMessageBox.warning(self, "AI edit", "The code was changed while the AI was working - "
                                    "the result was not applied.")
                return False
            before = full[:k]
            l1 = before.count("\n")
            c1 = len(before) - (before.rfind("\n") + 1)
            end = full[:k + len(self.original)]
            rng = (l1, c1, end.count("\n"), len(end) - (end.rfind("\n") + 1))
        replace_range(self.ed, rng, new)
        self.ctl.last_applied = (editor_path(self.ed), rng, new)
        return True

    def accept(self):
        if self.result is None:
            return
        if self._apply(self.result):
            _status(self.ctl.win, "AI edit applied (Ctrl+Z to undo)", 4000)
            self.close_box()

    def review(self):
        if self.result is None:
            return
        try:
            from ..ai.diffview import DiffReview
        except Exception:  # noqa: BLE001
            return
        text = DiffReview(self.ctl.win, editor_path(self.ed) or "selection", self.original, self.result,
                          title="Review AI edit").exec()
        if text is not None and self._apply(text):
            self.close_box()

    def reject(self):
        self.stop(silent=True)
        self.close_box()

    def close_box(self):
        try:
            theme.changed.disconnect(self._restyle)
        except Exception:  # noqa: BLE001
            pass
        if self.ctl.box is self:
            self.ctl.box = None
        ed = self.ed
        self.hide()
        self.deleteLater()
        try:
            ed.setFocus()
        except Exception:  # noqa: BLE001
            pass


# ============================================================================ result window
class ResultDialog(QDialog):
    """Streams a Markdown answer (Explain, Generate tests, Translate ...) with code actions."""

    def __init__(self, ctl: "AIEditor", title: str, messages, system: str, ed=None, suggest_name: str = "",
                 purpose: str = "chat", rerun_on_language: bool = True):
        super().__init__(ctl.win)
        self.ctl, self.ed, self.suggest_name = ctl, ed, suggest_name
        self.messages, self.system_fn, self.purpose = messages, system, purpose
        self.setWindowTitle(title)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(820, 620)
        self.setSizeGripEnabled(True)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.info = QLabel()
        theme.role(self.info, "muted")
        top.addWidget(self.info, 1)
        if rerun_on_language:
            top.addWidget(QLabel("Answer in:"))
            self.lang = QComboBox()
            for key, label in ANSWER_LANGS:
                self.lang.addItem(label, key)
            self.lang.setCurrentIndex(max(0, self.lang.findData(answer_language())))
            self.lang.currentIndexChanged.connect(self._lang_changed)
            top.addWidget(self.lang)
        lay.addLayout(top)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        lay.addWidget(self.view, 1)
        row = QHBoxLayout()
        self.b_stop = QPushButton("Stop")
        self.b_stop.clicked.connect(self.stop)
        self.b_again = QPushButton("Regenerate")
        self.b_again.clicked.connect(self.run)
        self.b_copy = QPushButton("Copy Code")
        self.b_copy.clicked.connect(self.copy_code)
        self.b_insert = QPushButton("Insert at Cursor")
        self.b_insert.clicked.connect(self.insert_code)
        self.b_save = QPushButton("Save as New File...")
        self.b_save.clicked.connect(self.save_code)
        self.b_close = QPushButton("Close")
        self.b_close.clicked.connect(self.close)
        for b in (self.b_stop, self.b_again, self.b_copy, self.b_insert, self.b_save):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self.b_close)
        lay.addLayout(row)
        self.job = None
        self.text = ""
        self._t = QTimer(self, interval=150, singleShot=True)
        self._t.timeout.connect(self._render)
        self.run()

    def _system(self) -> str:
        return self.system_fn() if callable(self.system_fn) else self.system_fn

    def _lang_changed(self):
        _settings().setValue(ANSWER_LANG_KEY, self.lang.currentData())
        self.run()

    def run(self):
        self.stop()
        p, model = ai.default(self.purpose)
        ok, why = ready(p)
        self.text = ""
        if not ok:
            self.info.setText(f"{p.name}: {why}")
            theme.role(self.info, "error")
            self.view.setPlainText("No AI provider is ready.  Open Tools > Options > AI to set one up "
                                   "(Ollama, a CLI agent signed in with your account, or an API key).")
            self._buttons()
            return
        theme.role(self.info, "muted")
        self.info.setText(f"{p.name}" + (f" - {model}" if model else "") + "   (streaming...)")
        self.view.setPlainText("...")
        msgs = list(self.messages)
        note = LANG_NOTE.get(answer_language(), "")
        if note and msgs:                  # small models follow the last line better than the system prompt
            last = ai.Message.of(msgs[-1])
            msgs[-1] = ai.Message(last.role, f"{last.content}\n\n{note}")
        self.job = p.chat(msgs, model=model or None, system=self._system(), purpose=self.purpose)
        self.job.delta.connect(lambda _s: self._t.isActive() or self._t.start())
        self.job.finished.connect(self._done)
        self.job.failed.connect(self._fail)
        self._buttons()

    def _render(self):
        if self.job is not None:
            self.text = self.job.text
        sb = self.view.verticalScrollBar()
        at_end = sb.value() >= sb.maximum() - 4
        self.view.setMarkdown(self.text or "...")
        if at_end:
            sb.setValue(sb.maximum())

    def _done(self, text):
        self.job = None
        self.text = text
        self._render()
        p, model = ai.default(self.purpose)
        self.info.setText(f"{p.name}" + (f" - {model}" if model else ""))
        self._buttons()

    def _fail(self, msg):
        self.job = None
        if msg != "Cancelled":
            theme.role(self.info, "error")
            self.info.setText(msg.strip().splitlines()[0][:300] if msg.strip() else "Failed")
            if not self.text:
                self.view.setPlainText(msg)
        self._buttons()

    def _buttons(self):
        busy = self.job is not None
        code = bool(ai.extract_code_blocks(self.text))
        self.b_stop.setEnabled(busy)
        self.b_again.setEnabled(not busy)
        for b in (self.b_copy, self.b_save):
            b.setEnabled(code and not busy)
        self.b_insert.setEnabled(code and not busy and self.ed is not None)

    def stop(self):
        if self.job is not None:
            job, self.job = self.job, None
            job.cancel()
        self._buttons()

    def code(self) -> str:
        blocks = ai.extract_code_blocks(self.text)
        return max(blocks, key=lambda b: len(b[1]))[1] if blocks else ""

    def copy_code(self):
        QApplication.clipboard().setText(self.code())
        _status(self.ctl.win, "Code copied", 2000)

    def insert_code(self):
        if self.ed is None:
            return
        line, col = get_cursor(self.ed)
        replace_range(self.ed, (line, col, line, col), self.code())

    def save_code(self):
        base = Path(editor_path(self.ed)).parent if self.ed is not None and editor_path(self.ed) else \
            (self.ctl.win.project.folder if getattr(self.ctl.win, "project", None) else Path.home())
        f, _ = QFileDialog.getSaveFileName(self, "Save code as", str(Path(base) / (self.suggest_name or "untitled.txt")))
        if not f:
            return
        Path(f).write_text(self.code() + "\n", encoding="utf-8")
        _status(self.ctl.win, f"Saved {f}", 4000)
        self.ctl.offer_add_to_project(Path(f))

    def closeEvent(self, e):
        self.stop()
        super().closeEvent(e)


# ============================================================================ the controller
class AIEditor(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.box: InlineEditBox | None = None
        self.prompts: list[str] = []
        self.last_applied = None
        self.inline = InlineCompleter(self)
        self.windows: list = []
        self._hooked = set()
        self.button = None
        self.route_to_chat = True        # Explain -> the AI Chat panel when it exists

    # ------------------------------------------------------------ editor hooks
    def hook_editor(self, ed):
        if id(ed) in self._hooked:
            return
        self._hooked.add(id(ed))
        ed.destroyed.connect(lambda *_a, k=id(ed): self._hooked.discard(k))
        ed.contextMenuAboutToShow.connect(lambda m, e=ed: self.add_menu(m, e))
        if is_monaco(ed):
            ed.inlineEditRequested.connect(lambda x, y, h, e=ed: self.inline_edit(e, anchor=QPoint(x, y), line_h=h))
        else:
            sc = QShortcut(QKeySequence("Ctrl+I"), ed, lambda e=ed: self.inline_edit(e))
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)

    def add_menu(self, m: QMenu, ed):
        sub = m.addMenu("AI")
        sub.setObjectName("radAiMenu")
        sub.addAction("Edit with AI...\tCtrl+I", lambda: self.inline_edit(ed))
        if is_monaco(ed):
            sub.addAction("Suggest Completion\tAlt+\\", ed.trigger_inline_suggest)
        sub.addSeparator()
        for aid in ("explain", "fix", "refactor", "comments", "docs", "tests"):
            sub.addAction(ACTIONS[aid][0], lambda a=aid: self.run_action(ed, a))
        tr = sub.addMenu("Translate To")
        for title, plugin in self.translate_targets(ed):
            tr.addAction(title, lambda p=plugin: self.translate(ed, p))
        return sub

    # ------------------------------------------------------------ status bar button
    def make_button(self):
        b = QToolButton()
        b.setObjectName("radAiStatus")
        b.setAutoRaise(True)
        b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(b)
        self.a_inline = menu.addAction("Inline Completions (ghost text)")
        self.a_inline.setCheckable(True)
        self.a_inline.toggled.connect(self.set_inline)
        menu.addAction("Suggest Now\tAlt+\\", self.suggest_now)
        menu.addSeparator()
        self.a_prov = menu.addAction("")
        self.a_prov.setEnabled(False)
        menu.addAction("AI Settings...", self.open_settings)
        menu.aboutToShow.connect(self.update_button)
        b.setMenu(menu)
        self.button = b
        self.update_button()
        return b

    def set_busy(self, on: bool):
        self._busy = on
        self.update_button()

    def update_button(self):
        b = self.button
        if b is None:
            return
        on = inline_enabled()
        self.a_inline.blockSignals(True)
        self.a_inline.setChecked(on)
        self.a_inline.blockSignals(False)
        try:
            p, model = ai.default("complete")
            prov = f"{p.name}" + (f" - {model}" if model else "")
            auto = p.kind not in ("cli", "web")
        except Exception:  # noqa: BLE001
            prov, auto = "(no provider)", False
        self.a_prov.setText(f"Completions: {prov}")
        busy = getattr(self, "_busy", False)
        b.setText("AI ..." if busy else ("AI" if on else "AI off"))
        tip = [f"Inline AI completions: {'on' if on else 'off'}", f"Provider: {prov}"]
        if on and not auto:
            tip.append("This provider is asked only with Alt+\\ (CLI agents are slow and use your quota).")
        if self.inline.last_error:
            tip.append(f"Last error: {self.inline.last_error.splitlines()[0][:160]}")
        tip.append("Tab = accept, Esc = dismiss, Ctrl+I = edit with AI")
        b.setToolTip("\n".join(tip))

    def set_inline(self, on: bool):
        _settings().setValue(INLINE_KEY, bool(on))
        self.inline.backoff_until = 0
        self.push_inline_state()
        self.update_button()
        _status(self.win, f"AI inline completions {'on' if on else 'off'}", 3000)

    def push_inline_state(self, ed=None):
        from ..monaco_editor import MonacoEditor
        eds = [ed] if ed is not None else self.win.findChildren(MonacoEditor)
        for e in eds:
            try:
                e.set_inline_enabled(inline_enabled(), inline_delay())
            except Exception:  # noqa: BLE001
                pass

    def suggest_now(self):
        ed = self.current_editor()
        if ed is not None and is_monaco(ed):
            ed.trigger_inline_suggest()

    def open_settings(self):
        try:
            from .ai_settings import show_ai_settings
            show_ai_settings(self.win)
        except Exception as e:  # noqa: BLE001
            _log(self.win, f"[ai] cannot open the AI settings: {e}")

    # ------------------------------------------------------------ helpers
    def current_editor(self):
        from ..ai.context import current_editor
        ed, _p = current_editor(self.win)
        return ed if ed is not None and hasattr(ed, "contextMenuAboutToShow") else None

    def remember_prompt(self, text: str):
        if text in self.prompts:
            self.prompts.remove(text)
        self.prompts.insert(0, text)
        del self.prompts[30:]

    def translate_targets(self, ed):
        from ..languages import all_plugins
        cur = getattr(getattr(ed, "plugin", None), "id", "")
        seen, out = set(), []
        for p in sorted(all_plugins(), key=lambda p: (p.display_name or p.id).lower()):
            title = p.display_name or p.id
            if p.id == cur or not p.code_ext or title in seen:
                continue
            seen.add(title)
            out.append((title, p))
        return out

    def offer_add_to_project(self, path: Path):
        win = self.win
        proj = getattr(win, "project", None)
        if proj is None:
            return
        try:
            if path.parent.resolve() != Path(proj.folder).resolve() or path.name in proj.modules:
                return
        except OSError:
            return
        if getattr(proj, "kind", "") == "website":
            return
        if QMessageBox.question(win, "AI", f"Add {path.name} to the project '{proj.name}'?") \
                == QMessageBox.StandardButton.Yes:
            proj.modules.append(path.name)
            proj.save()
            try:
                win._fill_solution()
                win.open_module(path.name)
            except Exception as e:  # noqa: BLE001
                _log(win, f"[ai] {e}")

    # ------------------------------------------------------------ Ctrl+I
    def inline_edit(self, ed, instruction: str = "", rng=None, extra: str = "", title: str = "",
                    auto: bool = False, anchor: QPoint | None = None, line_h: int = 18):
        if ed is None:
            ed = self.current_editor()
            if ed is None:
                _status(self.win, "Open a code file first", 3000)
                return None
        if ed.isReadOnly():
            _status(self.win, "The editor is read-only", 3000)
            return None
        if self.box is not None:
            self.box.reject()
        if rng is None:
            l1, c1, l2, c2 = get_selection(ed)
            if (l1, c1) == (l2, c2):
                rng = (l1, c1, l1, c1)               # nothing selected: insert at the cursor
            else:
                if l2 > l1 and c2 == 0:
                    l2 -= 1
                rng = full_lines(ed, l1, l2)

        def open_at(pt, h):
            self.box = InlineEditBox(self, ed, rng, instruction, extra, title, pt, h)
            if auto and instruction:
                self.box.generate()
        if anchor is not None:
            open_at(anchor, line_h)
        else:
            caret_point(ed, open_at)
        return True

    # ------------------------------------------------------------ editor commands
    def run_action(self, ed, aid: str, extra: str = ""):
        title, kind, instruction = ACTIONS[aid]
        rng, scope = selection_scope(ed)
        if kind == "edit":
            if aid == "fix":
                probs = self.problems_for(ed)
                if probs:
                    extra = (extra + "\n" if extra else "") + "Problems reported by the IDE for this file:\n" + probs
            self.inline_edit(ed, instruction, rng=rng, extra=extra, title=f"AI: {title}", auto=True)
            return
        code = text_of_range(ed, rng)
        lang = editor_language(ed)
        name = Path(editor_path(ed)).name or "untitled"
        what = "the selected code" if scope == "selection" else f"the file {name}" if scope == "file" else \
            f"this part of {name}"
        prompt = f"{instruction}\n\nThis is {what} (language: {lang}):\n{_fence(lang, code)}"
        if aid == "explain" and self.ask_chat(ed, prompt, title="Explain"):
            return
        suggest = ""
        if aid == "tests":
            p = Path(editor_path(ed) or "code.txt")
            suggest = f"test_{p.stem}{p.suffix}" if p.suffix == ".py" else f"{p.stem}Test{p.suffix}"
        self.show_result(f"AI: {title} - {name}", prompt, ed=ed, suggest_name=suggest)

    def show_result(self, title: str, prompt: str, ed=None, suggest_name: str = "", purpose: str = "chat"):
        dlg = ResultDialog(self, title, [ai.Message("user", prompt)], _ask_system, ed=ed,
                           suggest_name=suggest_name, purpose=purpose)
        dlg.show()
        self.windows = [w for w in self.windows if _alive(w)] + [dlg]
        return dlg

    def translate(self, ed, plugin):
        rng, scope = selection_scope(ed, whole_limit=2000)
        code = text_of_range(ed, rng)
        src = editor_language(ed)
        dst = plugin.display_name or plugin.id
        prompt = (f"Translate this {src} code to {dst} (file extension {plugin.code_ext}). Keep the same behaviour, "
                  f"use idiomatic {dst} code and its standard library. Put the complete translated code in one "
                  f"fenced code block, then list briefly anything that could not be translated exactly.\n\n"
                  f"{_fence(src, code)}")
        stem = Path(editor_path(ed) or "code").stem
        self.show_result(f"AI: Translate to {dst}", prompt, ed=ed, suggest_name=f"{stem}{plugin.code_ext}")

    def ask_chat(self, ed=None, prompt: str | None = None, title: str = "") -> bool:
        """Send *prompt* to the AI Chat panel (9.3, radide/features/ai_chat.py) when it is installed
        (and route_to_chat is on).  Returns False when it is not - the caller shows a result window."""
        if getattr(self.win, "ai_chat", None) is None or not self.route_to_chat:
            return False
        try:
            from .ai_chat import ask
            return ask(self.win, prompt or "", send=bool(prompt)) is not None
        except Exception as e:  # noqa: BLE001
            _log(self.win, f"[ai] AI Chat: {e}")
            return False

    def problems_for(self, ed) -> str:
        from ..ai.context import problems
        name = Path(editor_path(ed)).name.lower()
        out = [f"- line {p['line']}: {p['severity']}: {p['message']}" for p in problems(self.win)
               if name and Path(p.get("file", "")).name.lower() == name]
        return "\n".join(out[:50])

    # ------------------------------------------------------------ Error List
    def error_list_menu(self, pos):
        tree = self.win.error_list
        it = tree.itemAt(pos)
        if it is None:
            return
        m = QMenu(tree)
        m.addAction("Fix with AI", lambda: self.fix_problem(it.text(0), it.text(1), it.text(2), it.text(3)))
        m.addAction("Explain with AI", lambda: self.explain_problem(it.text(0), it.text(1), it.text(2), it.text(3)))
        m.addSeparator()
        m.addAction("Copy", lambda: QApplication.clipboard().setText(
            f"{it.text(0)}: {it.text(1)} ({it.text(2)}:{it.text(3)})"))
        m.exec(tree.viewport().mapToGlobal(pos))

    def _open_problem(self, file: str, line: str):
        try:
            n = max(0, int(line) - 1)
        except ValueError:
            n = 0
        ed = self.win._editor_for_file(file) if file and getattr(self.win, "project", None) else None
        if ed is None:
            _status(self.win, f"Cannot open {file}", 4000)
            return None, n
        ed.goto_line(n)
        return ed, n

    def fix_problem(self, severity: str, message: str, file: str, line: str):
        ed, n = self._open_problem(file, line)
        if ed is None:
            return
        lines = editor_lines(ed)
        # a window around the problem (rewriting a whole file invites small models to drop code)
        a, b = max(0, n - 8), min(len(lines) - 1, n + 8)
        for _i in range(15):                         # widen to blank-line boundaries (whole blocks)
            if a > 0 and lines[a - 1].strip():
                a -= 1
            if b < len(lines) - 1 and lines[b + 1].strip():
                b += 1
        rng = full_lines(ed, a, b)
        instruction = f"Fix this {severity.lower() or 'problem'} reported at line {n + 1}: {message}"
        extra = f"The line with the problem:\n{_fence('', lines[n] if n < len(lines) else '')}"

        def later():
            self.inline_edit(ed, instruction, rng=rng, extra=extra, title="AI: Fix problem", auto=True)
        QTimer.singleShot(120, later)              # let the editor scroll to the line first

    def explain_problem(self, severity: str, message: str, file: str, line: str):
        ed, n = self._open_problem(file, line)
        code = ""
        if ed is not None:
            lines = editor_lines(ed)
            a, b = max(0, n - 15), min(len(lines), n + 16)
            code = "\n".join(f"{i + 1:4}: {lines[i]}" for i in range(a, b))
        lang = editor_language(ed) if ed is not None else ""
        prompt = (f"The IDE reports this {severity.lower() or 'problem'} in {file} at line {line}:\n\n"
                  f"    {message}\n\nExplain what it means and how to fix it.\n\n"
                  + (f"The code around it:\n{_fence(lang, code)}" if code else ""))
        if not self.ask_chat(ed, prompt, title="Explain problem"):
            self.show_result("AI: Explain problem", prompt, ed=ed)

    # ------------------------------------------------------------ Git
    def hook_git(self):
        panel = getattr(self.win, "git_panel", None)
        if panel is None or getattr(panel, "_ai_hooked", False):
            return
        panel._ai_hooked = True
        b = QToolButton(text="Generate Message with AI")
        b.setObjectName("radAiCommit")
        b.setToolTip("Write the commit message from the staged changes (or from all changes when nothing is "
                     "staged) with AI - click again to stop")
        b.clicked.connect(lambda: self.generate_commit_message(panel))
        lay = panel.b_commit.parentWidget().layout()
        lay.insertWidget(lay.indexOf(panel.msg), b)
        panel.b_ai_message = b
        self._git_job = None
        orig = panel._update_buttons

        def update_buttons(repo, remote=False):
            orig(repo, remote)
            b.setEnabled(repo)
        panel._update_buttons = update_buttons
        b.setEnabled(panel.b_commit.isEnabled())

    def commit_prompt(self, git) -> tuple[str, str] | None:
        _c, staged = git.run("diff", "--cached", "--no-color", "--stat", "--patch")
        note = ""
        if not staged.strip():
            _c, staged = git.run("diff", "HEAD", "--no-color", "--stat", "--patch")
            if not staged.strip():
                _c, staged = git.run("diff", "--no-color", "--stat", "--patch")
            note = "Nothing is staged; these are all the changes of the working tree.\n"
        _c, status = git.run("status", "--short")
        untracked = [ln[3:] for ln in status.splitlines() if ln.startswith("??")]
        if not staged.strip() and not untracked:
            return None
        diff = staged[:14000] + ("\n... (diff truncated)" if len(staged) > 14000 else "")
        user = note + (f"New untracked files: {', '.join(untracked[:40])}\n" if untracked and note else "")
        user += f"\n{_fence('diff', diff)}\n\nWrite the commit message for these changes."
        system = ("You write git commit messages. Format: one summary line in the imperative mood, at most 72 "
                  "characters (for example 'Add login form validation'), then if useful a blank line and a few "
                  "short '- ' bullet points with the important details. Reply with ONLY the commit message - no "
                  "code fences, no quotes, no introduction.")
        return system, user

    def generate_commit_message(self, panel):
        job = getattr(self, "_git_job", None)
        if job is not None:
            self._git_job = None
            job.cancel()
            return
        if panel.git is None or not panel.git.is_repo():
            QMessageBox.information(panel, "Git", "The project is not a git repository.")
            return
        pr = self.commit_prompt(panel.git)
        if pr is None:
            QMessageBox.information(panel, "Git", "There are no changes to describe.")
            return
        p, model = ai.default("commit")
        ok, why = ready(p)
        if not ok:
            QMessageBox.information(panel, "Git", f"{p.name}: {why}\n\nSet up an AI provider in Tools > Options > AI.")
            return
        old = panel.msg.toPlainText()
        panel.msg.setPlainText("")
        panel.msg.setPlaceholderText(f"Writing the message with {p.name}...")
        b = panel.b_ai_message
        b.setText("Stop")
        job = p.chat([ai.Message("user", pr[1])], model=model or None, system=pr[0], temperature=0.3,
                     purpose="commit", cwd=str(panel.git.folder) if hasattr(panel.git, "folder") else None)
        self._git_job = job

        def delta(_s):
            if self._git_job is job:
                panel.msg.setPlainText(clean_commit_message(job.text, partial=True))

        def end(text, ok):
            if self._git_job is job:
                self._git_job = None
            b.setText("Generate Message with AI")
            panel.msg.setPlaceholderText("Commit message (Ctrl+Enter to commit)")
            if ok:
                panel.msg.setPlainText(clean_commit_message(text))
                panel.msg.setFocus()
            else:
                if not panel.msg.toPlainText().strip():
                    panel.msg.setPlainText(old)
                if text != "Cancelled":
                    QMessageBox.warning(panel, "Git", f"AI commit message failed:\n{text}")
        job.delta.connect(delta)
        job.finished.connect(lambda t: end(t, True))
        job.failed.connect(lambda e: end(e, False))
        return job

    # ------------------------------------------------------------ designer
    def hook_designers(self, *_a):
        for name, view in list(getattr(self.win, "designers", {}).items()):
            if getattr(view, "_ai_hooked", False):
                continue
            view._ai_hooked = True
            view.contextActions.connect(lambda m, c, v=view: self.designer_menu(v, m, c))

    def form_name_of(self, view) -> str | None:
        for name, v in getattr(self.win, "designers", {}).items():
            if v is view:
                return name
        return None

    def designer_menu(self, view, m: QMenu, c):
        name = self.form_name_of(view)
        if name is None:
            return
        sub = m.addMenu("AI")
        if c is not None and c.type not in ("MenuStrip", "ToolStrip"):
            sub.addAction(f"Generate Event Handler for {c.name}...", lambda: self.generate_handler(name, c))
        elif c is None:
            sub.addAction(f"Generate Event Handler for {name}...", lambda: self.generate_handler(name, None))
        sub.addAction("Redesign This Form with AI...", lambda: self.generate_form(name))
        sub.addAction("Generate New Form with AI...", lambda: self.generate_form(None))

    def generate_form(self, replace_form: str | None = None):
        win = self.win
        if getattr(win, "project", None) is None or getattr(win.project, "kind", "") == "website":
            QMessageBox.information(win, "AI", "Open a forms project first (File > New Project).")
            return None
        dlg = GenerateFormDialog(self, replace_form)
        dlg.show()
        self.windows = [w for w in self.windows if _alive(w)] + [dlg]
        return dlg

    def generate_handler(self, form_name: str, ctrl):
        dlg = HandlerDialog(self, form_name, ctrl)
        dlg.show()
        self.windows = [w for w in self.windows if _alive(w)] + [dlg]
        return dlg


def _alive(w) -> bool:
    try:
        w.isVisible()
        return True
    except RuntimeError:
        return False


def clean_commit_message(text: str, partial: bool = False) -> str:
    t = (text or "").replace("\r\n", "\n")
    blocks = ai.extract_code_blocks(t)
    if blocks and not partial:
        t = blocks[0][1]
    t = re.sub(r"^\s*```[\w-]*\n?", "", t)
    t = re.sub(r"\n?```\s*$", "", t)
    t = re.sub(r"^\s*(here('| i)s|sure)[^\n]*:\s*\n", "", t, flags=re.I)
    t = re.sub(r"^\s*(commit message|message)\s*:\s*", "", t, flags=re.I)
    t = t.strip()
    ls = t.split("\n")
    if len(ls) > 1 and ls[1].strip():           # git wants a blank line after the summary
        ls.insert(1, "")
        t = "\n".join(ls)
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'`" and "\n" not in t:
        t = t[1:-1]
    return t if partial else t.strip()


# ============================================================================ form generation
def control_catalogue() -> str:
    from ..controls import CONTROL_TYPES
    rows = []
    for t in CONTROL_TYPES.values():
        if t.name == "ActiveX":
            continue
        extra = []
        for p in t.extra:
            s = p.name
            if p.choices:
                s += "=" + "|".join(str(c) for c in p.choices)
            elif p.kind in ("int", "bool"):
                s += f" ({p.kind})"
            extra.append(s)
        kind = "non-visual" if t.nonvisual else ("container" if t.container else "")
        rows.append(f"- {t.name}{' [' + kind + ']' if kind else ''}: {t.description}"
                    + (f" Props: {', '.join(extra)}." if extra else ""))
    return "\n".join(rows)


FORM_EXAMPLE = {
    "props": {"Text": "Login", "Width": 320, "Height": 180},
    "controls": [
        {"type": "Label", "props": {"Name": "lblUser", "Text": "User name:", "Left": 12, "Top": 16,
                                     "Width": 80, "Height": 17}},
        {"type": "TextBox", "props": {"Name": "txtUser", "Left": 100, "Top": 13, "Width": 190, "Height": 20}},
        {"type": "Button", "props": {"Name": "btnOK", "Text": "OK", "Left": 134, "Top": 100, "Width": 75,
                                      "Height": 23}},
        {"type": "MenuStrip", "props": {"Name": "MenuStrip1", "Items": [
            {"Text": "File", "Name": "mnuFile", "Items": [{"Text": "Exit", "Name": "mnuFileExit"}]}]}},
    ]}


def form_prompt(description: str, current_json: str = "") -> tuple[str, str]:
    from ..controls import COMMON_PROPS
    common = ", ".join(p.name for p in COMMON_PROPS)
    system = ("You design desktop forms (windows) for a Visual-Basic-like form designer. You reply with ONLY one "
              "JSON object in a ```json fenced block, no explanations.")
    user = ("Design a form as JSON with this shape:\n"
            '{"props": {"Text": <window title>, "Width": <px>, "Height": <px>}, '
            '"controls": [{"type": <control type>, "props": {...}}, ...]}\n\n'
            f"Control types you can use:\n{control_catalogue()}\n\n"
            f"Common props of visual controls: {common}. Left/Top/Width/Height are pixels; Left/Top are relative "
            "to the container named in \"Parent\" (\"\" = the form). Children of a GroupBox start at Top >= 20.\n"
            "Rules: give every control a meaningful unique Name with a VB prefix (lbl, txt, btn, chk, opt, lst, cbo, "
            "grp, pnl, ...); put a Label before every input; align controls on a grid with 8-12 px gaps; make the "
            "form just big enough for its controls (the title bar is not part of Height; leave 40 px at the bottom "
            "when there is a StatusBar); a MenuStrip needs about 24 px at the top, so start the controls at "
            "Top >= 32 when there is a menu. List props (Items, Columns, Rows, TabPages, Nodes) are strings "
            "separated by ';'. Menu Items are nested objects with Text, Name and optional Items.\n\n"
            f"Example:\n```json\n{json.dumps(FORM_EXAMPLE, ensure_ascii=False)}\n```\n\n")
    if current_json:
        user += f"The current form (redesign it, keep the names of controls that stay):\n```json\n{current_json}\n```\n\n"
    user += f"The form to design:\n{description.strip()}"
    return system, user


def _loads_lenient(text: str):
    blocks = ai.extract_code_blocks(text)
    cands = [b[1] for b in blocks if b[1].lstrip().startswith(("{", "["))] or [text]
    for c in cands:
        for attempt in range(3):
            s = c
            if attempt >= 1:
                s = re.sub(r"(?m)^\s*//.*$", "", s)
                s = re.sub(r",\s*([}\]])", r"\1", s)
            if attempt == 2:
                a, b = s.find("{"), s.rfind("}")
                if a < 0 or b <= a:
                    break
                s = s[a:b + 1]
            try:
                return json.loads(s)
            except ValueError:
                continue
    raise ValueError("The AI answer does not contain valid JSON.")


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name, fallback: str) -> str:
    s = re.sub(r"\W", "", str(name or ""), flags=re.ASCII)
    if not s or not _IDENT.match(s) or keyword.iskeyword(s):
        return fallback
    return s


def _coerce(pdef, value, warnings, where):
    kind = pdef.kind
    try:
        if kind == "int":
            return int(round(float(value)))
        if kind == "bool":
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on")
            return bool(value)
        if kind == "enum":
            for c in pdef.choices:
                if str(c).lower() == str(value).lower():
                    return c
            warnings.append(f"{where}: {pdef.name}={value!r} is not one of {', '.join(map(str, pdef.choices))}")
            return pdef.default
        if kind == "list":
            if isinstance(value, (list, tuple)):
                return ";".join(str(v) for v in value)
            return str(value)
        if kind == "menu":
            return value if isinstance(value, list) else pdef.default
        if kind in ("str", "color", "file", "font"):
            return "" if value is None else str(value)
    except (TypeError, ValueError):
        warnings.append(f"{where}: bad value for {pdef.name}: {value!r}")
        return pdef.default
    return value


def sanitize_form(data, name: str):
    """AI JSON -> a valid radide.model.Form (+ warnings).  Unknown types / props are dropped,
    names made unique identifiers, values coerced, parents checked, then round-tripped."""
    from ..controls import CONTROL_TYPES, FORM_PROPS
    from ..model import Control, Form
    warnings: list[str] = []
    if isinstance(data, list):
        data = {"controls": data}
    if not isinstance(data, dict):
        raise ValueError("The AI answer is not a JSON object.")
    if "form" in data and isinstance(data["form"], dict) and "controls" not in data:
        data = data["form"]
    form = Form()
    props = data.get("props") if isinstance(data.get("props"), dict) else \
        {k: v for k, v in data.items() if k in FORM_PROPS}
    for k, v in (props or {}).items():
        pdef = FORM_PROPS.get(k)
        if pdef is None:
            continue
        form.props[k] = _coerce(pdef, v, warnings, "Form")
    form.props["Name"] = name
    form.props["Width"] = max(120, min(int(form.props.get("Width") or 400), 2400))
    form.props["Height"] = max(80, min(int(form.props.get("Height") or 300), 1600))
    if not str(form.props.get("Text") or "").strip():
        form.props["Text"] = name
    types_ci = {k.lower(): k for k in CONTROL_TYPES}
    aliases = {"textfield": "TextBox", "entry": "TextBox", "edit": "TextBox", "checkbutton": "CheckBox",
               "radio": "RadioButton", "combobox": "ComboBox", "dropdown": "ComboBox", "listview": "ListView",
               "grid": "DataGridView", "datagrid": "DataGridView", "statusstrip": "StatusBar", "menu": "MenuStrip",
               "menubar": "MenuStrip", "toolbar": "ToolStrip", "frame": "GroupBox", "image": "PictureBox",
               "slider": "TrackBar", "spinbox": "NumericUpDown", "progress": "ProgressBar", "tabs": "TabControl",
               "tree": "TreeView", "datepicker": "DateTimePicker", "link": "LinkLabel"}
    taken: set[str] = {name.lower()}
    pending = []
    for i, raw in enumerate(data.get("controls") or []):
        if not isinstance(raw, dict):
            continue
        tname = str(raw.get("type") or raw.get("Type") or "")
        t = types_ci.get(tname.lower()) or aliases.get(tname.lower())
        if t is None or t == "ActiveX":
            warnings.append(f"control {i + 1}: unknown type {tname!r} - skipped")
            continue
        ctype = CONTROL_TYPES[t]
        rp = raw.get("props") if isinstance(raw.get("props"), dict) else \
            {k: v for k, v in raw.items() if k not in ("type", "Type")}
        cname = _ident(rp.get("Name"), "")
        if not cname or cname.lower() in taken:
            if cname:
                warnings.append(f"{cname}: duplicate name - renamed")
            cname = form.unique_name(ctype.prefix, taken)
        taken.add(cname.lower())
        props = ctype.default_props(cname)
        defs = {p.name: p for p in ctype.prop_defs()}
        for k, v in rp.items():
            if k in ("Name",):
                continue
            if k == "Parent":
                props["Parent"] = str(v or "")
                continue
            pdef = defs.get(k)
            if pdef is None:
                continue
            props[k] = _coerce(pdef, v, warnings, cname)
        if t in ("MenuStrip", "ToolStrip"):
            props["Items"] = _menu_items(props.get("Items"), taken)
        pending.append(Control(t, props))
    names = {c.name: c for c in pending}
    for c in pending:
        if c.ctype.nonvisual:
            for k in ("Left", "Top", "Width", "Height", "Parent"):
                if k in c.props and k not in {p.name for p in c.ctype.prop_defs()}:
                    c.props.pop(k, None)
            c.props["Parent"] = ""
            continue
        par = c.props.get("Parent") or ""
        if par and (par not in names or not names[par].ctype.container or par == c.name):
            warnings.append(f"{c.name}: parent {par!r} is not a container - put on the form")
            c.props["Parent"] = ""
        for k, lo in (("Left", 0), ("Top", 0), ("Width", 1), ("Height", 1)):
            try:
                c.props[k] = max(lo, int(c.props.get(k, lo)))
            except (TypeError, ValueError):
                c.props[k] = lo
    for c in pending:
        if c.type == "StatusBar" and c.props.get("Dock") in (None, "", "None"):
            c.props["Dock"] = "Bottom"           # a status line belongs at the bottom
    form.controls = pending
    form.ordered()                       # breaks parent cycles (orphans go to the form)
    _break_cycles(form)
    # make the form big enough for its (undocked, top-level) controls
    right = bottom = 0
    for c in form.visual():
        if c.parent or c.props.get("Dock") not in (None, "", "None"):
            continue
        right = max(right, int(c.props["Left"]) + int(c.props["Width"]))
        bottom = max(bottom, int(c.props["Top"]) + int(c.props["Height"]))
    extra = 22 if any(c.type == "StatusBar" for c in form.visual()) else 0
    if right + 12 > form.props["Width"]:
        warnings.append(f"form widened to {right + 12} px to fit its controls")
        form.props["Width"] = right + 12
    if bottom + 12 + extra > form.props["Height"]:
        warnings.append(f"form made taller ({bottom + 12 + extra} px) to fit its controls")
        form.props["Height"] = bottom + 12 + extra
    final = Form.from_dict(json.loads(json.dumps(form.to_dict())))
    if not final.controls:
        warnings.append("the form has no controls")
    return final, warnings


def _break_cycles(form):
    for c in form.visual():
        seen, p = {c.name}, c.parent
        while p:
            if p in seen:
                c.props["Parent"] = ""
                break
            seen.add(p)
            par = form.find(p)
            p = par.parent if par is not None else ""


def _menu_items(items, taken: set[str], depth: int = 0) -> list:
    out = []
    if not isinstance(items, list) or depth > 4:
        return out
    for it in items:
        if isinstance(it, str):
            it = {"Text": it}
        if not isinstance(it, dict):
            continue
        text = str(it.get("Text") or "").strip()
        if not text:
            continue
        if text == "-":
            out.append({"Text": "-"})
            continue
        n = _ident(it.get("Name"), "")
        if not n or n.lower() in taken:
            base = "mnu" + (re.sub(r"\W", "", text.title(), flags=re.ASCII) or "Item")
            n, k = base, 2
            while n.lower() in taken:
                n, k = f"{base}{k}", k + 1
        taken.add(n.lower())
        d = {"Text": text, "Name": n}
        subs = _menu_items(it.get("Items"), taken, depth + 1)
        if subs:
            d["Items"] = subs
        out.append(d)
    return out


class GenerateFormDialog(QDialog):
    def __init__(self, ctl: AIEditor, replace_form: str | None = None):
        super().__init__(ctl.win)
        self.ctl, self.win, self.replace_form = ctl, ctl.win, replace_form
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Redesign Form with AI" if replace_form else "Generate Form with AI")
        self.resize(640, 560)
        self.job = None
        self.form = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Describe the window (any language - e.g. 'a login form with user name, "
                             "password, remember me and OK / Cancel'):"))
        self.desc = QPlainTextEdit()
        self.desc.setPlaceholderText("A customer form with name, phone, email, a notes box and Save / Close buttons")
        self.desc.setMaximumHeight(120)
        lay.addWidget(self.desc)
        row = QHBoxLayout()
        proj = self.win.project
        if replace_form:
            row.addWidget(QLabel(f"Form: <b>{replace_form}</b> (the change can be undone with Ctrl+Z)"))
            self.name = None
            self.lang = None
        else:
            row.addWidget(QLabel("Name:"))
            i = len(proj.forms) + 1
            while f"Form{i}" in proj.forms:
                i += 1
            self.name = QLineEdit(f"Form{i}")
            row.addWidget(self.name)
            row.addWidget(QLabel("Language:"))
            self.lang = QComboBox()
            from ..languages import all_plugins
            for p in sorted(all_plugins(), key=lambda p: p.display_name or p.id):
                if getattr(p, "kind", "") == "website" or not p.code_ext:
                    continue
                self.lang.addItem(p.display_name or p.id, p.id)
            self.lang.setCurrentIndex(max(0, self.lang.findData(proj.language)))
            row.addWidget(self.lang, 1)
        lay.addLayout(row)
        go = QHBoxLayout()
        self.b_gen = QPushButton("Generate")
        self.b_gen.setDefault(True)
        self.b_gen.clicked.connect(self.generate)
        go.addWidget(self.b_gen)
        self.status = QLabel()
        theme.role(self.status, "muted")
        self.status.setWordWrap(True)
        go.addWidget(self.status, 1)
        lay.addLayout(go)
        self.out = QListWidget()
        lay.addWidget(self.out, 1)
        self.raw = QPlainTextEdit()
        self.raw.setReadOnly(True)
        self.raw.setFont(QFont("Consolas", 8))
        self.raw.setMaximumHeight(110)
        self.raw.setPlaceholderText("AI answer")
        lay.addWidget(self.raw)
        bb = QDialogButtonBox()
        self.b_ok = bb.addButton("Apply to Form" if replace_form else "Create Form",
                                 QDialogButtonBox.ButtonRole.AcceptRole)
        self.b_ok.setEnabled(False)
        bb.addButton(QDialogButtonBox.StandardButton.Close)
        bb.accepted.connect(self.create)
        bb.rejected.connect(self.close)
        lay.addWidget(bb)
        p, model = ai.default("chat")
        self.status.setText(f"Uses {p.name}" + (f" - {model}" if model else ""))

    def generate(self):
        if self.job is not None:
            job, self.job = self.job, None
            job.cancel()
            self.b_gen.setText("Generate")
            self.status.setText("Stopped.")
            return
        desc = self.desc.toPlainText().strip()
        if not desc:
            self.desc.setFocus()
            return
        cur = ""
        if self.replace_form:
            doc = self.win._doc(self.replace_form)
            cur = json.dumps({"props": {k: doc.form.props.get(k) for k in ("Text", "Width", "Height")},
                              "controls": [c.to_dict() for c in doc.form.controls]}, ensure_ascii=False)
        system, user = form_prompt(desc, cur)
        p, model = ai.default("chat")
        ok, why = ready(p)
        if not ok:
            theme.role(self.status, "error")
            self.status.setText(f"{p.name}: {why}")
            return
        theme.role(self.status, "muted")
        self.status.setText(f"Designing with {p.name}...")
        self.raw.clear()
        self.out.clear()
        self.form = None
        self.b_ok.setEnabled(False)
        self.b_gen.setText("Stop")
        self.job = p.chat([ai.Message("user", user)], model=model or None, system=system, temperature=0.2,
                          purpose="chat")
        self.job.delta.connect(lambda s: (self.raw.moveCursor(self.raw.textCursor().MoveOperation.End),
                                          self.raw.insertPlainText(s)))
        self.job.finished.connect(self._done)
        self.job.failed.connect(self._fail)

    def form_name(self) -> str:
        return self.replace_form or (self.name.text().strip() if self.name is not None else "Form1")

    def _done(self, text: str):
        self.job = None
        self.b_gen.setText("Generate")
        self.raw.setPlainText(text)
        try:
            data = _loads_lenient(text)
            self.form, warnings = sanitize_form(data, self.form_name())
        except Exception as e:  # noqa: BLE001
            theme.role(self.status, "error")
            self.status.setText(f"{e}  Try Generate again or describe the form differently.")
            return
        f = self.form
        self.out.addItem(f"Form {f.name}: \"{f.props.get('Text')}\"  {f.props['Width']} x {f.props['Height']}")
        for c in f.controls:
            pos = "" if c.ctype.nonvisual else f"  at {c.props['Left']},{c.props['Top']}  " \
                                               f"{c.props['Width']} x {c.props['Height']}"
            text_ = c.props.get("Text")
            self.out.addItem(f"   {c.name} ({c.type})" + (f" \"{text_}\"" if text_ and text_ != c.name else "")
                             + (f"  in {c.parent}" if c.parent else "") + pos)
        for w in warnings:
            self.out.addItem(f"   note: {w}")
        theme.role(self.status, "success")
        self.status.setText(f"{len(f.controls)} controls - press "
                            f"{'Apply to Form' if self.replace_form else 'Create Form'}.")
        self.b_ok.setEnabled(bool(f.controls))

    def _fail(self, msg: str):
        self.job = None
        self.b_gen.setText("Generate")
        if msg != "Cancelled":
            theme.role(self.status, "error")
            self.status.setText(msg.strip().splitlines()[0][:300] if msg.strip() else "Failed")

    def create(self):
        if self.form is None:
            return
        try:
            name = apply_generated_form(self.win, self.form, self.replace_form,
                                        self.lang.currentData() if self.lang is not None else None)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "AI", str(e))
            return
        if name:
            self.close()

    def closeEvent(self, e):
        if self.job is not None:
            job, self.job = self.job, None
            job.cancel()
        super().closeEvent(e)


def apply_generated_form(win, form, replace_form: str | None = None, language: str | None = None) -> str | None:
    """Put a generated Form into the project: replace the design of an open form (undoable) or
    create a new form (files + designer code) and open it in the designer."""
    import os
    if replace_form:
        doc = win._doc(replace_form)
        doc.checkpoint()
        keep = doc.form.props.get("Name")
        doc.form.props.update({k: v for k, v in form.props.items() if k != "Name"})
        doc.form.props["Name"] = keep
        doc.form.controls = form.controls
        doc.selection = []
        doc.structureChanged.emit()
        doc.controlChanged.emit(None)
        doc.selectionChanged.emit(None)
        doc.set_modified()
        doc.undoStateChanged.emit()
        win.open_designer(replace_form)
        return replace_form
    from ..languages import plugin_for_form
    from ..workspace import create_form
    proj = win.project
    name = form.name
    if not _IDENT.match(name) or name.lower() in (f.lower() for f in proj.forms) or \
            name.lower() in (os.path.splitext(m)[0].lower() for m in proj.modules):
        raise ValueError(f"'{name}' is not a valid new form name.")
    win.save_all()
    create_form(proj, name, language)
    form.save(proj.form_path(name))
    fp = plugin_for_form(proj, name)
    code_path = proj.folder / fp.code_file(name)
    code = code_path.read_text(encoding="utf-8") if code_path.exists() else ""
    (proj.folder / fp.designer_file(name)).write_text(fp.generate_designer(form, code), encoding="utf-8")
    try:
        win._reload_startup_code()
    except Exception:  # noqa: BLE001
        pass
    win._fill_solution()
    win.open_designer(name)
    _log(win, f"[ai] Generated form {name} ({len(form.controls)} controls)")
    return name


# ============================================================================ event handlers
class HandlerDialog(QDialog):
    def __init__(self, ctl: AIEditor, form_name: str, ctrl):
        super().__init__(ctl.win)
        self.ctl, self.win, self.form_name, self.ctrl = ctl, ctl.win, form_name, ctrl
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        who = ctrl.name if ctrl is not None else form_name
        self.setWindowTitle(f"Generate Event Handler - {who}")
        self.resize(560, 300)
        self.job = None
        fp = self.win.plugin_for_form(form_name)
        self.fp = fp
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("Event:"))
        self.event = QComboBox()
        for ev in fp.events_for(ctrl):
            self.event.addItem(ev)
        de = ctrl.ctype.default_event if ctrl is not None else "Load"
        if de:
            self.event.setCurrentIndex(max(0, self.event.findText(de)))
        row.addWidget(self.event, 1)
        lay.addLayout(row)
        lay.addWidget(QLabel("What should happen? (any language)"))
        self.desc = QPlainTextEdit()
        self.desc.setPlaceholderText("Check that the name is not empty, then show a greeting in lblResult")
        lay.addWidget(self.desc, 1)
        self.status = QLabel()
        theme.role(self.status, "muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        bb = QDialogButtonBox()
        self.b_go = bb.addButton("Generate", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(QDialogButtonBox.StandardButton.Close)
        bb.accepted.connect(self.generate)
        bb.rejected.connect(self.close)
        lay.addWidget(bb)
        p, model = ai.default("edit")
        self.status.setText(f"Uses {p.name}" + (f" - {model}" if model else "") +
                            ". The code is shown as a diff before it is added.")

    def generate(self):
        if self.job is not None:
            return
        desc = self.desc.toPlainText().strip()
        if not desc:
            self.desc.setFocus()
            return
        ev = self.event.currentText()
        doc = self.win._doc(self.form_name)
        doc.eventRequested.emit(self.ctrl, ev)            # creates / finds the handler and opens the code
        cv = self.win.codeviews.get(self.form_name)
        if cv is None:
            self.status.setText("Cannot open the code of the form.")
            return
        ed = cv.editor
        handler = self.fp.handler_for(doc.form, self.ctrl, ev)
        code = ed.toPlainText()
        hline = self.fp.find_handler(code, handler)
        lines = code.split("\n")
        l1, c1, l2, c2 = get_selection(ed)
        target = l1 if (l1, c1) != (l2, c2) else get_cursor(ed)[0]
        if hline < 0 or target >= len(lines):
            target = min(len(lines) - 1, max(0, hline + 1))
        cur = lines[target]
        unit = "\t" if "\n\t" in code else "    "
        ind = indent_of(cur) if cur.strip() in ("pass", "") and indent_of(cur) else \
            indent_of(lines[hline] if 0 <= hline < len(lines) else "") + unit
        replace_line = cur.strip() in ("pass", "")
        self.target = (target, replace_line, ind, code)
        names = ", ".join(f"{c.name} ({c.type})" for c in doc.form.controls)
        lang = self.fp.display_name or self.fp.id
        ctx = "\n".join(lines[max(0, hline - 3):hline + 12]) if hline >= 0 else ""
        system = ("You write the body of an event handler for a Visual-Basic-like RAD IDE. Reply with ONLY the "
                  "statements of the body (no function header, no 'end' line) in one fenced code block.")
        user = (f"Language/toolkit: {lang}\nForm {self.form_name} has these controls: {names or '(none)'}\n"
                f"Handler: {handler} (event {ev} of {self.ctrl.name if self.ctrl else self.form_name})\n\n"
                f"The handler in the file now:\n{_fence('', ctx)}\n\nThe whole code file for reference:\n"
                f"{_fence('', code[:9000])}\n\nWhat the handler should do: {desc}")
        p, model = ai.default("edit")
        ok, why = ready(p)
        if not ok:
            theme.role(self.status, "error")
            self.status.setText(f"{p.name}: {why}")
            return
        self.ed = ed
        theme.role(self.status, "muted")
        self.status.setText(f"Writing {handler} with {p.name}...")
        self.b_go.setEnabled(False)
        self.job = p.chat([ai.Message("user", user)], model=model or None, system=system, temperature=0.2,
                          purpose="edit")
        self.job.finished.connect(self._done)
        self.job.failed.connect(self._fail)

    def new_code(self, answer: str) -> str:
        target, replace_line, ind, code = self.target
        body = reindent(strip_fences(answer).strip("\n"), ind)
        lines = code.split("\n")
        if replace_line:
            lines[target:target + 1] = body.split("\n")
        else:
            lines[target + 1:target + 1] = body.split("\n")
        return "\n".join(lines)

    def _done(self, text: str):
        self.job = None
        self.b_go.setEnabled(True)
        old = self.target[3]
        new = self.new_code(text)
        if self.ed.toPlainText() != old:
            self.status.setText("The code changed meanwhile - generate again.")
            return
        try:
            from ..ai.diffview import DiffReview
            res = DiffReview(self, editor_path(self.ed), old, new, title="Review the generated event handler").exec()
        except Exception:  # noqa: BLE001
            res = new
        if res is None:
            self.status.setText("Rejected.")
            return
        set_whole_text(self.ed, res)
        self.ed.goto_line(self.target[0])
        _status(self.win, "Event handler added (Ctrl+Z to undo)", 4000)
        self.close()

    def _fail(self, msg: str):
        self.job = None
        self.b_go.setEnabled(True)
        if msg != "Cancelled":
            theme.role(self.status, "error")
            self.status.setText(msg.strip().splitlines()[0][:300] if msg.strip() else "Failed")

    def closeEvent(self, e):
        if self.job is not None:
            job, self.job = self.job, None
            job.cancel()
        super().closeEvent(e)


# ============================================================================ install
def _menu(win, title: str):
    for a in win.menuBar().actions():
        if a.menu() is not None and a.text().replace("&", "") == title:
            return a.menu()
    return None


def install(win) -> None:
    global _WIN
    _WIN = win
    ctl = AIEditor(win)
    win._ai_editor = ctl
    win.ai_editor = ctl
    from .. import editor as editor_mod
    from ..monaco_editor import MonacoEditor

    def hook(ed):
        w = _win_of(ed)
        if w is not None and getattr(w, "_ai_editor", None) is not None:
            w._ai_editor.hook_editor(ed)
    if not any(getattr(h, "_rad_ai", False) for h in editor_mod.EDITOR_HOOKS):
        hook._rad_ai = True
        editor_mod.EDITOR_HOOKS.append(hook)

    def provider(ed, req, line, col, explicit):
        w = _win_of(ed)
        c = getattr(w, "_ai_editor", None) if w is not None else None
        if c is None:
            ed.resolve_inline(req, None)
            return
        c.inline.request(ed, req, line, col, explicit)

    def cancel(ed, req):
        w = _win_of(ed)
        c = getattr(w, "_ai_editor", None) if w is not None else None
        if c is not None:
            c.inline.cancel(ed, req)
    MonacoEditor.inline_provider = provider
    MonacoEditor.inline_cancel = cancel
    if not any(getattr(h, "_rad_ai", False) for h in MonacoEditor.ready_hooks):
        def ready(ed):
            ed.set_inline_enabled(inline_enabled(), inline_delay())
        ready._rad_ai = True
        MonacoEditor.ready_hooks.append(ready)

    # status bar button
    try:
        win.statusBar().addPermanentWidget(ctl.make_button())
        ai.hub().defaults_changed.connect(lambda *_a: ctl.update_button())
    except Exception as e:  # noqa: BLE001
        _log(win, f"[ai_editor] status button: {e}")

    # Edit > AI menu (no shortcuts on the actions: Ctrl+I / Alt+\ belong to the editors)
    edit = _menu(win, "Edit")
    if edit is not None:
        sub = edit.addMenu("AI")
        sub.addAction("Edit with AI...\tCtrl+I", lambda: ctl.inline_edit(None))
        sub.addAction("Suggest Inline Completion\tAlt+\\", ctl.suggest_now)
        sub.addSeparator()
        for aid in ("explain", "fix", "refactor", "comments", "docs", "tests"):
            sub.addAction(ACTIONS[aid][0], lambda a=aid: (lambda e: e is not None and ctl.run_action(e, a))(
                ctl.current_editor()))
        sub.addSeparator()
        a = sub.addAction("Inline Completions")
        a.setCheckable(True)
        a.setChecked(inline_enabled())
        a.toggled.connect(ctl.set_inline)
        sub.aboutToShow.connect(lambda a=a: (a.blockSignals(True), a.setChecked(inline_enabled()),
                                             a.blockSignals(False)))
        win.menu_ai_edit = sub
    proj = _menu(win, "Project")
    act = QAction("Generate Form with AI...", win)
    act.triggered.connect(lambda: ctl.generate_form(None))
    win.a_ai_generate_form = act
    if proj is not None:
        proj.addAction(act)

    # Error List, Git panel and designers exist / are created later
    def later():
        el = getattr(win, "error_list", None)
        if el is not None and el.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            el.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            el.customContextMenuRequested.connect(ctl.error_list_menu)
        ctl.hook_git()
        ctl.hook_designers()
    QTimer.singleShot(0, later)
    win.tabs.currentChanged.connect(ctl.hook_designers)


__all__ = ["AIEditor", "InlineEditBox", "ResultDialog", "GenerateFormDialog", "HandlerDialog", "sanitize_form",
           "form_prompt", "apply_generated_form", "clean_commit_message", "edit_prompt", "fit_replacement",
           "strip_fences", "inline_enabled", "install"]
