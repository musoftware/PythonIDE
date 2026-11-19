"""Agent Manager (docs/CONTRACTS.md 9.5) - Antigravity-style agent tasks in the IDE.

Dock "Agent Manager" (win.dock_agents, widget win.agent_manager), also the main surface of the workbench's
Agent layout and a view of the VS Code layout (workbench.register_view("agents", ...)).

  * left: a composer (task text, agent = provider/model, permission mode, max steps, folder) and the list of
    tasks (title, status, provider, start time) - several tasks run at the same time,
  * right: the selected task - conversation (plan, every step and its result, live), approval bar
    (Approve / Always / Reject), Changes (per-file diff review: Accept / Reject, Accept all, Undo all from the
    checkpoint), Artifacts (plan.md, walkthrough.md, screenshots of the web Preview),
  * an Inbox (bell) collects "needs approval" / "finished" notifications.

The engine is radide/ai/agents.py.  Files written by an agent update open editors that have no unsaved edits.
"""
from __future__ import annotations

import html
import re
import time
from pathlib import Path

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QFont, QKeySequence, QPainter, QPixmap, QShortcut
from PyQt6.QtWidgets import (QApplication, QComboBox, QDockWidget, QFileDialog, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit,
                             QPushButton, QSpinBox, QSplitter, QStackedWidget, QStyle, QStyledItemDelegate,
                             QTabWidget, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

from .. import theme
from ..ai import agents as A

TITLE = "Agent Manager"
_ARABIC = re.compile(r"[֐-ࣿיִ-﷿ﹰ-﻿]")
_LATIN = re.compile(r"[A-Za-z]")


def _c(token: str, fallback: str = "#808080") -> str:
    try:
        return theme.color(token)
    except Exception:  # noqa: BLE001
        return fallback


def _mix(a: str, b: str, f: float) -> str:
    ca, cb = QColor(a), QColor(b)
    return QColor(int(ca.red() + (cb.red() - ca.red()) * f), int(ca.green() + (cb.green() - ca.green()) * f),
                  int(ca.blue() + (cb.blue() - ca.blue()) * f)).name()


def is_rtl(text: str) -> bool:
    """The paragraph starts (first strong letter) with Arabic / Hebrew."""
    for ch in text or "":
        if _ARABIC.match(ch):
            return True
        if _LATIN.match(ch):
            return False
    return False


def _dir(text: str) -> str:
    return ' dir="rtl" align="right"' if is_rtl(text) else ' dir="ltr"'


# ============================================================================ markdown -> HTML (small, safe)
def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", lambda m: f'<code style="background:{_c("alt_base")};">{m.group(1)}</code>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(text: str, mono_bg: str = "") -> str:
    """Markdown subset (paragraphs, headings, lists, fenced code, inline code, bold) with a correct text
    direction for every paragraph (Arabic -> right-to-left, code always left-to-right)."""
    out: list[str] = []
    lines = (text or "").replace("\r\n", "\n").split("\n")
    i = 0
    para: list[str] = []
    bg = mono_bg or _c("alt_base")

    def flush():
        if para:
            t = " ".join(x.strip() for x in para)
            out.append(f"<p{_dir(t)} style='margin:2px 0 6px 0;'>{_inline(t)}</p>")
            para.clear()
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^\s*(```+|~~~+)\s*([\w#+.\-]*)", ln)
        if m:
            flush()
            fence = m.group(1)
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                code.append(lines[i])
                i += 1
            i += 1
            out.append(f"<pre dir='ltr' style='background:{bg}; padding:6px; margin:4px 0;'>"
                       f"{html.escape(chr(10).join(code))}</pre>")
            continue
        h = re.match(r"^(#{1,4})\s+(.*)", ln)
        li = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)", ln)
        if h:
            flush()
            size = {1: "130%", 2: "115%", 3: "105%", 4: "100%"}[len(h.group(1))]
            out.append(f"<p{_dir(h.group(2))} style='font-weight:600; font-size:{size}; margin:6px 0 3px 0;'>"
                       f"{_inline(h.group(2))}</p>")
        elif li:
            flush()
            mark = li.group(1)
            bullet = mark if mark[0].isdigit() else "•"
            body = li.group(2)
            body = re.sub(r"^\[( |x|X|~)\]\s*", lambda mm: {"x": "☑ ", "X": "☑ ", "~": "◐ "}.get(mm.group(1), "☐ "),
                          body)
            rtl = is_rtl(body)
            pad = "margin-right:14px;" if rtl else "margin-left:14px;"
            out.append(f"<p{_dir(body)} style='{pad} margin-top:1px; margin-bottom:1px;'>{bullet} {_inline(body)}</p>")
        elif not ln.strip():
            flush()
        else:
            para.append(ln)
        i += 1
    flush()
    return "".join(out)


# ============================================================================ editors follow agent writes
def _sync_editor(win, path: Path) -> None:
    try:
        from ..ai import diffview as dv
    except Exception:  # noqa: BLE001
        return
    try:
        ed = dv.find_open_editor(win, path)
    except Exception:  # noqa: BLE001
        ed = None
    if ed is None:
        _refresh_tree_later(win)
        return
    try:
        modified = bool(ed.isModified())
    except Exception:  # noqa: BLE001
        modified = False
    try:
        new = dv.read_text(path)[0]
    except Exception:  # noqa: BLE001
        return
    if modified:
        if dv.editor_text(ed) != new:
            win.log(f"[Agent] {path.name} was changed by an agent but has unsaved edits in the editor - not reloaded.")
        return
    dv.set_editor_text(ed, new, saved=True)


def _refresh_tree_later(win):
    t = getattr(win, "_agents_tree_timer", None)
    if t is None:
        t = QTimer(win)
        t.setSingleShot(True)
        t.setInterval(600)

        def go():
            for name in ("refresh_solution", "_fill_solution"):
                f = getattr(win, name, None)
                if callable(f):
                    try:
                        f()
                    except Exception:  # noqa: BLE001
                        pass
                    return
        t.timeout.connect(go)
        win._agents_tree_timer = t
    t.start()


# ============================================================================ task list
STATUS_COLOR = {"queued": "muted", "running": "accent", "waiting": "note", "done": "success", "failed": "error",
                "cancelled": "muted"}


class TaskDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(200, 50)

    def paint(self, p: QPainter, option, index):
        task: A.AgentTask = index.data(Qt.ItemDataRole.UserRole)
        if task is None:
            return super().paint(p, option, index)
        p.save()
        r = option.rect
        sel = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if sel:
            p.fillRect(r, QColor(_c("highlight")))
        elif hover:
            p.fillRect(r, QColor(_mix(_c("base"), _c("highlight"), 0.12)))
        text = QColor(_c("highlight_text") if sel else _c("text"))
        muted = QColor(_c("highlight_text") if sel else _c("muted"))
        # status dot (pulsing ring while running)
        col = QColor(_c(STATUS_COLOR.get(task.status, "muted")))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QRectF(r.left() + 10, r.top() + 13, 9, 9))
        if task.status == "waiting":
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(col)
            p.drawEllipse(QRectF(r.left() + 7, r.top() + 10, 15, 15))
        f = QFont(option.font)
        f.setBold(task.unread or task.status == "waiting")
        p.setFont(f)
        p.setPen(text)
        x = r.left() + 30
        w = r.width() - 36
        title = p.fontMetrics().elidedText(task.title, Qt.TextElideMode.ElideRight, w - 70)
        rtl_title = is_rtl(task.title)
        p.drawText(QRectF(x, r.top() + 5, w - 70, 20),
                   (Qt.AlignmentFlag.AlignRight if rtl_title else Qt.AlignmentFlag.AlignLeft)
                   | Qt.AlignmentFlag.AlignVCenter, title)
        f2 = QFont(option.font)
        f2.setPointSizeF(max(7.0, option.font.pointSizeF() - 1))
        p.setFont(f2)
        p.setPen(muted)
        when = time.strftime("%H:%M", time.localtime(task.started)) if task.started else ""
        p.drawText(QRectF(x + w - 68, r.top() + 5, 66, 20),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, when)
        n = len([c for c in task.changes.values() if c.status == "pending"])
        sub = f"{A.STATUS_TITLES.get(task.status, task.status)} · {task.provider_name()}"
        if n:
            sub += f" · {n} change(s) to review"
        p.drawText(QRectF(x, r.top() + 25, w, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   p.fontMetrics().elidedText(sub, Qt.TextElideMode.ElideRight, int(w)))
        p.setPen(QColor(_mix(_c("base"), _c("border"), 0.6)))
        p.drawLine(r.left() + 8, r.bottom(), r.right() - 8, r.bottom())
        p.restore()


# ============================================================================ the conversation
BADGES = {"read": "READ", "list": "LIST", "search": "SEARCH", "write": "WRITE", "edit": "EDIT", "command": "RUN",
          "web": "WEB", "tool": "TOOL", "plan": "PLAN", "approval": "REVIEW"}


class Conversation(QTextBrowser):
    """HTML rendering of a task's steps (throttled re-render; keeps the scroll at the bottom while live)."""

    action = pyqtSignal(str, str)           # verb, argument (open / diff / approve / reject / toggle)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self._anchor)
        self.task: A.AgentTask | None = None
        self.expanded: set[str] = set()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self.render)
        self.document().setDocumentMargin(10)

    def _anchor(self, url: QUrl):
        s = url.toString()
        if s.startswith(("http://", "https://")):
            QDesktopServices.openUrl(url)
            return
        verb, _, arg = s.partition(":")
        if verb == "toggle":
            if arg in self.expanded:
                self.expanded.discard(arg)
            else:
                self.expanded.add(arg)
            self.render()
            return
        self.action.emit(verb, QUrl.fromPercentEncoding(arg.encode()))

    def set_task(self, task):
        self.task = task
        self.expanded.clear()
        self.render(force_bottom=True)

    def schedule(self):
        if not self._timer.isActive():
            self._timer.start()

    # ------------------------------------------------------------------ render
    def render(self, force_bottom: bool = False):
        sb = self.verticalScrollBar()
        at_bottom = force_bottom or sb.value() >= sb.maximum() - 30
        old = sb.value()
        self.setHtml(self.html())
        sb.setValue(sb.maximum() if at_bottom else old)

    def html(self) -> str:
        t = self.task
        text, muted, base, border = _c("text"), _c("muted"), _c("base"), _c("border")
        if t is None:
            return (f"<div style='color:{muted}; margin:30px;'><p style='font-size:120%; color:{text};'>"
                    "No task selected</p><p>Describe a task on the left and press <b>Start</b>. The agent plans, "
                    "reads and writes files and runs commands in your project; you approve its actions and "
                    "review every changed file before you keep it.</p>"
                    "<p>Free options: a local model in Ollama (built-in agent loop), or a CLI agent signed in "
                    "with your own account (Claude Code, Gemini CLI, Codex, opencode ...).</p></div>")
        parts = [f"<div style='color:{text};'>"]
        for s in t.steps:
            parts.append(self._step(s, text, muted, base, border))
        if t.status == "running":
            parts.append(f"<p style='color:{muted};'><i>working...</i></p>")
        parts.append("</div>")
        return "".join(parts)

    def _badge(self, kind: str, status: str) -> str:
        col = {"write": _c("accent"), "edit": _c("accent"), "command": _c("note"), "plan": _c("heading"),
               "approval": _c("note")}.get(kind, _c("muted"))
        if status == "failed":
            col = _c("error")
        if status == "rejected":
            col = _c("disabled")
        label = BADGES.get(kind, kind.upper())
        return (f"<span style='background:{col}; color:{_c('base')}; font-size:80%; font-weight:600;'>"
                f"&nbsp;{label}&nbsp;</span>")

    @staticmethod
    def _status_mark(status: str) -> str:
        return {"running": f"<span style='color:{_c('accent')};'> ⟳ running</span>",
                "pending": f"<span style='color:{_c('note')}; font-weight:600;'> ● waiting for your approval</span>",
                "failed": f"<span style='color:{_c('error')};'> ✗ failed</span>",
                "rejected": f"<span style='color:{_c('disabled')};'> ⊘ rejected</span>",
                "done": f"<span style='color:{_c('success')};'> ✓</span>"}.get(status, "")

    def _pre(self, text: str, max_lines: int = 0, rtl_ok: bool = False) -> str:
        lines = (text or "").rstrip().split("\n")
        more = ""
        if max_lines and len(lines) > max_lines:
            more = f"... ({len(lines) - max_lines} more lines)\n"
            lines = lines[-max_lines:]
        body = more + "\n".join(lines)
        d = _dir(body) if rtl_ok else " dir='ltr'"
        return (f"<pre{d} style='background:{_c('alt_base')}; color:{_c('text')}; padding:5px; margin:2px 0 4px 0;'>"
                f"{html.escape(body)}</pre>")

    def _diff_html(self, diff: str, max_lines: int = 200) -> str:
        add_bg = _mix(_c("base"), _c("success"), 0.18)
        rem_bg = _mix(_c("base"), _c("error"), 0.18)
        rows = []
        lines = diff.splitlines()
        for ln in lines[:max_lines]:
            if ln.startswith(("+++", "---")):
                continue
            esc = html.escape(ln) or "&nbsp;"
            if ln.startswith("+"):
                rows.append(f"<span style='background:{add_bg};'>{esc}</span>")
            elif ln.startswith("-"):
                rows.append(f"<span style='background:{rem_bg};'>{esc}</span>")
            elif ln.startswith("@@"):
                rows.append(f"<span style='color:{_c('muted')};'>{esc}</span>")
            else:
                rows.append(esc)
        if len(lines) > max_lines:
            rows.append(f"<span style='color:{_c('muted')};'>... {len(lines) - max_lines} more lines</span>")
        return (f"<pre dir='ltr' style='background:{_c('alt_base')}; padding:5px; margin:2px 0 4px 0;'>"
                + "\n".join(rows) + "</pre>")

    def _step(self, s: A.Step, text, muted, base, border) -> str:
        q = QUrl.toPercentEncoding
        if s.kind == "user":
            bg = _mix(base, _c("accent"), 0.10)
            return (f"<table width='100%' cellpadding='8' style='margin:4px 0 10px 0;'><tr><td style='background:{bg};'>"
                    f"<p style='color:{muted}; font-size:85%; margin:0;'>{html.escape(s.title)}</p>"
                    f"{md_to_html(s.detail)}</td></tr></table>")
        if s.kind in ("message",):
            if not s.detail.strip():
                return f"<p style='color:{muted};'><i>thinking...</i></p>" if s.status == "running" else ""
            return f"<div style='margin:4px 0 8px 0;'>{md_to_html(s.detail)}</div>"
        if s.kind == "plan" and not s.tool:
            bg = _mix(base, _c("heading"), 0.07)
            return (f"<table width='100%' cellpadding='8' style='margin:4px 0 8px 0;'><tr><td style='background:{bg};'>"
                    f"{self._badge('plan', s.status)} <b>Plan</b>{md_to_html(s.detail)}</td></tr></table>")
        if s.kind == "info":
            return f"<p style='color:{muted}; font-size:88%; margin:2px 0;'>— {html.escape(s.title)}</p>"
        if s.kind == "error":
            bg = _mix(base, _c("error"), 0.12)
            return (f"<table width='100%' cellpadding='8' style='margin:6px 0;'><tr><td style='background:{bg};'>"
                    f"<b style='color:{_c('error')};'>Error</b>{self._pre(s.detail, rtl_ok=True)}</td></tr></table>")
        if s.kind == "result":
            bg = _mix(base, _c("success"), 0.12)
            return (f"<table width='100%' cellpadding='8' style='margin:8px 0;'><tr><td style='background:{bg};'>"
                    f"<b style='color:{_c('success')};'>✓ Finished</b>{md_to_html(s.detail)}</td></tr></table>")
        if s.kind == "approval":
            bg = _mix(base, _c("note"), 0.10)
            links = ""
            if s.status == "pending":
                links = (f"<p><a href='approve:{s.id}'><b>Approve and run</b></a> &nbsp;·&nbsp; "
                         f"<a href='reject:{s.id}'>Reject</a></p>")
            return (f"<table width='100%' cellpadding='8' style='margin:6px 0;'><tr><td style='background:{bg};'>"
                    f"{self._badge('approval', s.status)} <b>{html.escape(s.title)}</b>{self._status_mark(s.status)}"
                    f"{md_to_html(s.detail)}{links}</td></tr></table>")
        # tool steps
        head = f"{self._badge(s.kind, s.status)} "
        title = html.escape(s.title)
        if s.kind in ("read", "write", "edit") and s.path:
            title = (f"{html.escape(s.title.split(' ', 1)[0])} <a href='open:{q(s.path).data().decode()}'>"
                     f"{html.escape(s.path)}</a>")
        if s.kind == "command":
            title = f"Run <code>{html.escape(s.detail or s.title[5:])}</code>"
        head += f"<span>{title}</span>{self._status_mark(s.status)}"
        extra = ""
        if s.kind in ("write", "edit") and s.diff:
            add, rem = A.diff_stats(s.diff)
            head += (f" <span style='color:{_c('success')};'>+{add}</span> "
                     f"<span style='color:{_c('error')};'>-{rem}</span>")
            if s.status not in ("pending",) and s.path:
                head += f" &nbsp;<a href='diff:{q(s.path).data().decode()}'>review</a>"
        exp = s.id in self.expanded
        has_more = bool(s.output) or bool(s.diff)
        if s.status == "pending":
            if s.diff:
                extra += self._diff_html(s.diff)
            elif s.kind == "command":
                extra += self._pre(s.detail)
            extra += (f"<p style='margin:2px 0 6px 0;'><a href='approve:{s.id}'><b>Approve</b></a> &nbsp;·&nbsp; "
                      f"<a href='always:{s.id}'>Always allow</a> &nbsp;·&nbsp; <a href='reject:{s.id}'>Reject</a></p>")
        elif s.kind == "command" and s.output:
            extra += self._pre(s.output, 0 if exp else 12)
        elif exp:
            if s.diff:
                extra += self._diff_html(s.diff, 2000)
            if s.output and s.kind not in ("write", "edit"):
                extra += self._pre(s.output, 0, rtl_ok=True)
            elif s.output:
                extra += f"<p style='color:{muted}; margin:0 0 4px 0;'>{html.escape(s.output)}</p>"
        if has_more and s.status != "pending":
            head += f" &nbsp;<a href='toggle:{s.id}' style='color:{muted};'>{'hide' if exp else 'details'}</a>"
        if s.status == "failed" and s.output and not exp and s.kind != "command":
            extra += f"<p style='color:{_c('error')}; margin:0 0 4px 0;'>{html.escape(s.output[:400])}</p>"
        return f"<p dir='ltr' style='margin:3px 0;'>{head}</p>{extra}"


# ============================================================================ task view (right side)
class TaskView(QWidget):
    def __init__(self, panel: "AgentManagerWidget"):
        super().__init__(panel)
        self.panel = panel
        self.win = panel.win
        self.task: A.AgentTask | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        # header
        self.header = QFrame()
        self.header.setObjectName("agentHeader")
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(10, 6, 6, 6)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.title = QLabel("Agent Manager")
        f = self.title.font()
        f.setPointSizeF(f.pointSizeF() + 2)
        f.setBold(True)
        self.title.setFont(f)
        self.sub = QLabel("")
        theme.role(self.sub, "muted")
        col.addWidget(self.title)
        col.addWidget(self.sub)
        hl.addLayout(col, 1)
        self.b_stop = QPushButton("Stop")
        self.b_stop.setToolTip("Stop this task (kills its commands / CLI process)")
        self.b_undo = QPushButton("Undo all")
        self.b_undo.setToolTip("Restore every file this task touched from its checkpoint")
        self.b_more = QToolButton()
        self.b_more.setText("⋯")
        self.b_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more = QMenu(self.b_more)
        more.addAction("Open task folder", self._open_folder)
        more.addAction("Open checkpoint folder", self._open_checkpoint)
        more.addAction("Run again as a new task", self._rerun)
        more.addSeparator()
        more.addAction("Remove from list", self._remove)
        self.b_more.setMenu(more)
        for b in (self.b_stop, self.b_undo, self.b_more):
            hl.addWidget(b)
        self.b_stop.clicked.connect(lambda: self.task and self.task.stop())
        self.b_undo.clicked.connect(self._undo_all)
        lay.addWidget(self.header)
        # approval bar
        self.appr = QFrame()
        self.appr.setObjectName("agentApproval")
        al = QHBoxLayout(self.appr)
        al.setContentsMargins(10, 6, 6, 6)
        self.appr_text = QLabel()
        self.appr_text.setWordWrap(True)
        al.addWidget(self.appr_text, 1)
        self.b_approve = QPushButton("Approve")
        self.b_approve.setDefault(True)
        self.b_always = QPushButton("Always allow")
        self.b_always.setToolTip("Approve this and stop asking for this kind of action in this task")
        self.b_reject = QPushButton("Reject")
        for b in (self.b_approve, self.b_always, self.b_reject):
            al.addWidget(b)
        self.b_approve.clicked.connect(lambda: self.task and self.task.approve())
        self.b_always.clicked.connect(lambda: self.task and self.task.approve(always=True))
        self.b_reject.clicked.connect(self._reject)
        self.appr.hide()
        lay.addWidget(self.appr)
        # tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        lay.addWidget(self.tabs, 1)
        # conversation tab
        conv = QWidget()
        cl = QVBoxLayout(conv)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(4)
        self.conv = Conversation()
        self.conv.action.connect(self._on_action)
        cl.addWidget(self.conv, 1)
        row = QHBoxLayout()
        row.setContentsMargins(6, 0, 6, 6)
        self.follow = QLineEdit()
        self.follow.setPlaceholderText("Follow-up instruction for this task (Enter) ...")
        self.follow.returnPressed.connect(self._follow_up)
        self.b_send = QPushButton("Send")
        self.b_send.clicked.connect(self._follow_up)
        row.addWidget(self.follow, 1)
        row.addWidget(self.b_send)
        cl.addLayout(row)
        self.tabs.addTab(conv, "Conversation")
        # changes tab
        ch = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)
        self.files = QListWidget()
        self.files.currentItemChanged.connect(lambda *_: self._show_diff())
        self.files.itemDoubleClicked.connect(lambda it: self._open(it.data(Qt.ItemDataRole.UserRole)))
        ll.addWidget(self.files, 1)
        bl = QHBoxLayout()
        self.b_accept_all = QPushButton("Accept all")
        self.b_accept_all.clicked.connect(lambda: self.task and self.task.accept_all())
        self.b_undo2 = QPushButton("Undo all")
        self.b_undo2.clicked.connect(self._undo_all)
        bl.addWidget(self.b_accept_all)
        bl.addWidget(self.b_undo2)
        ll.addLayout(bl)
        ch.addWidget(left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        fr = QHBoxLayout()
        self.diff_title = QLabel("Select a file")
        self.diff_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        fr.addWidget(self.diff_title, 1)
        self.b_accept = QPushButton("Accept")
        self.b_accept.setToolTip("Keep this file as the agent wrote it (with the ticked changes only)")
        self.b_reject_file = QPushButton("Reject")
        self.b_reject_file.setToolTip("Restore this file from the checkpoint")
        self.b_open_file = QPushButton("Open")
        for b in (self.b_accept, self.b_reject_file, self.b_open_file):
            fr.addWidget(b)
        self.b_accept.clicked.connect(self._accept_file)
        self.b_reject_file.clicked.connect(self._reject_file)
        self.b_open_file.clicked.connect(lambda: self._open(self._cur_file()))
        rl.addLayout(fr)
        self.diff_stack = QStackedWidget()
        self.diff_plain = QTextBrowser()
        self.diff_stack.addWidget(self.diff_plain)
        self.diff_widget = None
        rl.addWidget(self.diff_stack, 1)
        ch.addWidget(right)
        ch.setSizes([220, 600])
        self.tabs.addTab(ch, "Changes")
        # artifacts tab
        ar = QSplitter(Qt.Orientation.Horizontal)
        al2 = QWidget()
        alay = QVBoxLayout(al2)
        alay.setContentsMargins(4, 4, 4, 4)
        self.arts = QListWidget()
        self.arts.currentItemChanged.connect(lambda *_: self._show_artifact())
        self.arts.itemDoubleClicked.connect(lambda it: QDesktopServices.openUrl(
            QUrl.fromLocalFile(it.data(Qt.ItemDataRole.UserRole))))
        alay.addWidget(self.arts, 1)
        self.b_shot = QPushButton("Capture Preview")
        self.b_shot.setToolTip("Save a screenshot of the web Preview (or the current editor tab) as an artifact")
        self.b_shot.clicked.connect(self._capture)
        alay.addWidget(self.b_shot)
        ar.addWidget(al2)
        self.art_stack = QStackedWidget()
        self.art_text = QTextBrowser()
        self.art_text.setOpenExternalLinks(True)
        self.art_img = QLabel()
        self.art_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_stack.addWidget(self.art_text)
        self.art_stack.addWidget(self.art_img)
        ar.addWidget(self.art_stack)
        ar.setSizes([200, 600])
        self.tabs.addTab(ar, "Artifacts")
        self.set_task(None)

    # ------------------------------------------------------------------ binding
    def set_task(self, task: A.AgentTask | None):
        old = self.task
        if old is not None:
            for sig, slot in ((old.step_added, self._on_step), (old.step_changed, self._on_step),
                              (old.status_changed, self._on_status), (old.changes_changed, self._fill_changes),
                              (old.artifacts_changed, self._fill_artifacts)):
                try:
                    sig.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
        self.task = task
        if task is not None:
            task.unread = False
            task.step_added.connect(self._on_step)
            task.step_changed.connect(self._on_step)
            task.status_changed.connect(self._on_status)
            task.changes_changed.connect(self._fill_changes)
            task.artifacts_changed.connect(self._fill_artifacts)
        self.conv.set_task(task)
        self._on_status()
        self._fill_changes()
        self._fill_artifacts()

    def _on_step(self, _s=None):
        self.conv.schedule()
        self._update_approval()

    def _on_status(self, _s=None):
        t = self.task
        has = t is not None
        for w in (self.b_stop, self.b_undo, self.b_more, self.follow, self.b_send, self.b_shot):
            w.setEnabled(has)
        if not has:
            self.title.setText("Agent Manager")
            self.sub.setText("Start a task on the left - several tasks can run at the same time.")
            self.appr.hide()
            return
        self.title.setText(t.title)
        self.title.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl(t.title) else Qt.LayoutDirection.LeftToRight)
        engine = "CLI agent" if t.engine == "cli" else "built-in agent loop"
        self.sub.setText(f"{A.STATUS_TITLES.get(t.status, t.status)} · {t.provider_name()} ({engine}) · "
                         f"{A.PERMISSION_TITLES.get(t.permission, t.permission)} · {t.root}")
        self.b_stop.setEnabled(t.running)
        self.follow.setEnabled(not t.running)
        self.b_send.setEnabled(not t.running)
        self.conv.schedule()
        self._update_approval()
        self.panel.refresh_list()

    def _update_approval(self):
        t = self.task
        s = t.pending_approval() if t is not None and t.status == "waiting" else None
        if s is None:
            self.appr.hide()
            return
        if s.kind == "approval":
            what = "The agent made a plan. Approve it to let the agent make the changes."
            self.b_always.hide()
        else:
            what = {"write": f"The agent wants to write <b>{html.escape(s.path)}</b>",
                    "edit": f"The agent wants to edit <b>{html.escape(s.path)}</b>",
                    "command": f"The agent wants to run <code>{html.escape(s.detail)}</code>"}.get(
                s.kind, html.escape(s.title))
            self.b_always.show()
        self.appr_text.setText(what)
        self.appr.show()

    def _reject(self):
        t = self.task
        if t is None:
            return
        reason = self.follow.text().strip()
        self.follow.clear()
        t.reject(reason=reason)

    def _follow_up(self):
        t = self.task
        text = self.follow.text().strip()
        if t is None or not text:
            return
        if t.status == "waiting":
            return
        if t.follow_up(text):
            self.follow.clear()

    # ------------------------------------------------------------------ actions from the conversation
    def _on_action(self, verb: str, arg: str):
        t = self.task
        if t is None:
            return
        step = next((s for s in t.steps if s.id == arg), None)
        if verb == "approve" and step is not None:
            t.approve(step)
        elif verb == "always" and step is not None:
            t.approve(step, always=True)
        elif verb == "reject" and step is not None:
            t.reject(step, self.follow.text().strip())
        elif verb == "open":
            self._open(arg)
        elif verb == "diff":
            self.tabs.setCurrentIndex(1)
            for i in range(self.files.count()):
                if self.files.item(i).data(Qt.ItemDataRole.UserRole) == arg:
                    self.files.setCurrentRow(i)
                    break

    def _open(self, rel: str | None):
        t = self.task
        if t is None or not rel:
            return
        p = t.root / rel
        if not p.is_file():
            self.win.statusBar().showMessage(f"{rel} does not exist (any more)", 4000)
            return
        try:
            from .web_workspace import open_file
            open_file(self.win, p)
            return
        except Exception:  # noqa: BLE001
            pass
        try:
            from .command_palette import open_path
            open_path(self.win, p)
        except Exception:  # noqa: BLE001
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def _open_folder(self):
        if self.task is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.task.root)))

    def _open_checkpoint(self):
        if self.task is not None:
            d = self.task.checkpoint.dir
            d.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _rerun(self):
        if self.task is not None:
            self.panel.composer_from(self.task)

    def _remove(self):
        if self.task is not None:
            self.panel.mgr.remove(self.task)

    def _undo_all(self):
        t = self.task
        if t is None or not t.checkpoint.manifest:
            return
        n = len(t.checkpoint.manifest)
        if QMessageBox.question(self, "Undo all", f"Restore {n} file(s) touched by this task from its checkpoint?\n"
                                "Files the task created are deleted.") != QMessageBox.StandardButton.Yes:
            return
        restored = t.undo_all()
        for rel in restored:
            p = t.root / rel
            if p.is_file():
                _sync_editor(self.win, p)
        _refresh_tree_later(self.win)

    # ------------------------------------------------------------------ changes
    def _fill_changes(self):
        t = self.task
        cur = self._cur_file()
        self.files.blockSignals(True)
        self.files.clear()
        pending = 0
        if t is not None:
            for ch in t.changes.values():
                diff = t.diff_of(ch.path)
                add, rem = A.diff_stats(diff)
                what = "deleted" if ch.deleted else ("new" if not ch.existed else "")
                mark = {"pending": "●", "accepted": "✓", "rejected": "↶"}.get(ch.status, "")
                it = QListWidgetItem(f"{mark} {ch.path}   +{add} -{rem}" + (f"  ({what})" if what else ""))
                it.setData(Qt.ItemDataRole.UserRole, ch.path)
                it.setToolTip(f"{ch.path} - {ch.status}" + ("" if ch.backup else " (no backup - too big to undo)"))
                if ch.status == "rejected":
                    it.setForeground(QColor(_c("disabled")))
                self.files.addItem(it)
                if ch.status == "pending":
                    pending += 1
        self.files.blockSignals(False)
        self.tabs.setTabText(1, f"Changes ({pending})" if pending else "Changes")
        rows = [self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())]
        if cur in rows:
            self.files.setCurrentRow(rows.index(cur))
        elif rows:
            self.files.setCurrentRow(0)
        self._show_diff()
        has = t is not None and bool(t.changes)
        self.b_accept_all.setEnabled(has and pending > 0)
        self.b_undo2.setEnabled(t is not None and bool(t.checkpoint.manifest))
        self.b_undo.setEnabled(t is not None and bool(t.checkpoint.manifest))
        self.panel.refresh_list()

    def _cur_file(self) -> str | None:
        it = self.files.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else None

    def _show_diff(self):
        t = self.task
        rel = self._cur_file()
        ch = t.changes.get(rel) if (t is not None and rel) else None
        for b in (self.b_accept, self.b_reject_file, self.b_open_file):
            b.setEnabled(ch is not None)
        if ch is None:
            self.diff_title.setText("Select a file" if t is not None and t.changes else "No changes yet")
            self.diff_plain.setHtml("")
            self.diff_stack.setCurrentWidget(self.diff_plain)
            return
        self.b_accept.setEnabled(ch.status == "pending")
        self.b_reject_file.setEnabled(ch.status != "rejected" and ch.backup)
        self.diff_title.setText(f"<b>{html.escape(rel)}</b> - {ch.status}")
        before = t.checkpoint.original_text(rel) if t.checkpoint.has(rel) else None
        p = t.root / rel
        after = A.read_text(p) if p.is_file() else None
        try:
            from ..ai.diffview import DiffWidget
            if self.diff_widget is not None:
                self.diff_stack.removeWidget(self.diff_widget)
                self.diff_widget.deleteLater()
            self.diff_widget = DiffWidget(str(p), before, after)
            self.diff_stack.addWidget(self.diff_widget)
            self.diff_stack.setCurrentWidget(self.diff_widget)
        except Exception:  # noqa: BLE001 - fallback: coloured unified diff
            self.diff_plain.setHtml(self.conv._diff_html(A.unified_diff(before, after, rel), 5000))
            self.diff_stack.setCurrentWidget(self.diff_plain)

    def _accept_file(self):
        t = self.task
        rel = self._cur_file()
        if t is None or not rel:
            return
        w = self.diff_widget
        if w is not None and self.diff_stack.currentWidget() is w and not getattr(w, "deleting", False):
            try:
                result = w.result_text()
                p = t.root / rel
                cur = A.read_text(p).replace("\r\n", "\n") if p.is_file() else None
                if cur is not None and result != cur:          # some hunks unticked: keep only the ticked ones
                    from ..ai.diffview import write_text
                    write_text(p, result)
                    _sync_editor(self.win, p)
            except Exception as e:  # noqa: BLE001
                self.win.log(f"[Agent] accept {rel}: {e}")
        t.accept_change(rel)

    def _reject_file(self):
        t = self.task
        rel = self._cur_file()
        if t is None or not rel:
            return
        if t.reject_change(rel):
            p = t.root / rel
            if p.is_file():
                _sync_editor(self.win, p)
            _refresh_tree_later(self.win)

    # ------------------------------------------------------------------ artifacts
    def _fill_artifacts(self):
        t = self.task
        cur = self.arts.currentItem().data(Qt.ItemDataRole.UserRole) if self.arts.currentItem() else None
        self.arts.blockSignals(True)
        self.arts.clear()
        if t is not None:
            for a in t.artifacts:
                it = QListWidgetItem(a.name)
                it.setData(Qt.ItemDataRole.UserRole, a.path)
                it.setData(Qt.ItemDataRole.UserRole + 1, a.kind)
                it.setToolTip(a.path)
                self.arts.addItem(it)
        self.arts.blockSignals(False)
        self.tabs.setTabText(2, f"Artifacts ({self.arts.count()})" if self.arts.count() else "Artifacts")
        paths = [self.arts.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.arts.count())]
        if cur in paths:
            self.arts.setCurrentRow(paths.index(cur))
        elif paths:
            self.arts.setCurrentRow(0)
        self._show_artifact()

    def _show_artifact(self):
        it = self.arts.currentItem()
        if it is None:
            self.art_text.setHtml(f"<p style='color:{_c('muted')};'>The plan and the walkthrough of the task appear "
                                  "here, and screenshots you capture of the web Preview.</p>")
            self.art_stack.setCurrentWidget(self.art_text)
            return
        path, kind = it.data(Qt.ItemDataRole.UserRole), it.data(Qt.ItemDataRole.UserRole + 1)
        if kind == "image":
            pm = QPixmap(path)
            if not pm.isNull() and pm.width() > 900:
                pm = pm.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)
            self.art_img.setPixmap(pm)
            self.art_stack.setCurrentWidget(self.art_img)
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            text = f"(cannot read: {e})"
        self.art_text.setHtml(f"<div style='color:{_c('text')};'>{md_to_html(text)}</div>")
        self.art_stack.setCurrentWidget(self.art_text)

    def _capture(self):
        t = self.task
        if t is None:
            return
        target = None
        pv = getattr(self.win, "web_preview", None)
        dock = getattr(self.win, "dock_web_preview", None)
        if pv is not None and dock is not None and dock.isVisible():
            target, name = pv, "preview"
        else:
            w = self.win.tabs.currentWidget() if hasattr(self.win, "tabs") else None
            target, name = (w, "editor") if w is not None else (self.win, "window")
        pm = target.grab()
        d = t.task_dir()
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{name}-{time.strftime('%H%M%S')}.png"
        pm.save(str(p))
        t.add_artifact(p.name, p, "image")
        t.save()
        self.tabs.setCurrentIndex(2)

    def restyle(self):
        t = theme.current()
        self.header.setStyleSheet(f"#agentHeader {{ background: {t['base']}; border-bottom: 1px solid {t['border']}; }}")
        self.appr.setStyleSheet(f"#agentApproval {{ background: {t['banner']}; border-bottom: 1px solid "
                                f"{t['banner_border']}; }} #agentApproval QLabel {{ color: {t['banner_text']}; }}")
        self.conv.render()
        self._show_artifact()


# ============================================================================ the whole panel
class Composer(QFrame):
    """New task: text, agent (provider + model), permission, max steps, folder."""

    start = pyqtSignal()
    _status = pyqtSignal(str, bool, str)

    def __init__(self, panel: "AgentManagerWidget"):
        super().__init__(panel)
        self.panel = panel
        self.setObjectName("agentComposer")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(5)
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Describe a task for an agent...  e.g. \"Add a Save button to Form1 and run "
                                     "the tests\"  /  اكتب المهمة هنا\n(Ctrl+Enter to start)")
        self.text.setFixedHeight(84)
        self.text.textChanged.connect(self._dir)
        lay.addWidget(self.text)
        r1 = QHBoxLayout()
        self.agent = QComboBox()
        self.agent.setToolTip("Who does the work: a CLI agent signed in with your account, or any AI provider "
                              "through the built-in agent loop (Ollama works free and offline)")
        self.agent.currentIndexChanged.connect(self._agent_changed)
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setMinimumWidth(90)
        self.model.setToolTip("Model (\"default\" = the agent's own default)")
        r1.addWidget(self.agent, 3)
        r1.addWidget(self.model, 2)
        lay.addLayout(r1)
        r2 = QHBoxLayout()
        self.perm = QComboBox()
        for k in A.PERMISSIONS:
            self.perm.addItem(A.PERMISSION_TITLES[k], k)
        self.perm.setToolTip("Ask every time: approve each write and command (CLI agents: review their plan first)\n"
                             "Auto-approve edits: files are written without asking; commands still ask\n"
                             "Auto-approve all: no questions (every change can still be reviewed and undone)")
        self.steps = QSpinBox()
        self.steps.setRange(1, 200)
        self.steps.setValue(25)
        self.steps.setPrefix("max ")
        self.steps.setSuffix(" steps")
        self.steps.setToolTip("Maximum number of model turns of the built-in agent loop")
        r2.addWidget(self.perm, 3)
        r2.addWidget(self.steps, 2)
        lay.addLayout(r2)
        r3 = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setPlaceholderText("Folder (the open project)")
        self.folder.setToolTip("The folder the agent works in")
        b = QToolButton()
        b.setText("...")
        b.clicked.connect(self._browse)
        self.b_start = QPushButton("Start")
        self.b_start.setDefault(True)
        self.b_start.clicked.connect(self.start.emit)
        r3.addWidget(self.folder, 1)
        r3.addWidget(b)
        r3.addWidget(self.b_start)
        lay.addLayout(r3)
        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        theme.role(self.hint, "muted")
        lay.addWidget(self.hint)
        QShortcut(QKeySequence("Ctrl+Return"), self.text, activated=self.start.emit)
        QShortcut(QKeySequence("Ctrl+Enter"), self.text, activated=self.start.emit)
        self._status.connect(self._on_status, Qt.ConnectionType.QueuedConnection)
        self.fill_agents()

    def _dir(self):
        rtl = is_rtl(self.text.toPlainText())
        opt = self.text.document().defaultTextOption()
        want = Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        if opt.textDirection() != want:
            opt.setTextDirection(want)
            opt.setAlignment(Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft)
            self.text.document().setDefaultTextOption(opt)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Folder for the agent", self.folder.text() or str(Path.home()))
        if d:
            self.folder.setText(d)

    # ------------------------------------------------------------------ agents
    def fill_agents(self):
        from .. import ai
        cur = self.agent.currentData()
        self.agent.blockSignals(True)
        self.agent.clear()
        try:
            provs = [p for p in ai.providers() if p.kind != "web" and p.enabled()]
        except Exception:  # noqa: BLE001
            provs = []
        cli = [p for p in provs if p.kind == "cli"]
        rest = [p for p in provs if p.kind != "cli"]
        for p in cli:
            self.agent.addItem(f"{p.name}  - CLI agent", p.id)
        if cli and rest:
            self.agent.insertSeparator(self.agent.count())
        for p in rest:
            self.agent.addItem(f"{p.name}  - built-in agent loop", p.id)
        try:
            dp, _dm = ai.default("agent")
            want = cur or dp.id
        except Exception:  # noqa: BLE001
            want = cur
        i = self.agent.findData(want)
        self.agent.setCurrentIndex(max(0, i))
        self.agent.blockSignals(False)
        self._agent_changed()
        self._detect(provs)

    def _detect(self, provs):
        import threading

        def work():
            for p in provs:
                try:
                    ok, why = p.available()
                except Exception as e:  # noqa: BLE001
                    ok, why = False, str(e)
                try:
                    self._status.emit(p.id, ok, why)
                except RuntimeError:
                    return
        threading.Thread(target=work, daemon=True).start()

    def _on_status(self, pid: str, ok: bool, why: str):
        i = self.agent.findData(pid)
        if i < 0:
            return
        base = self.agent.itemText(i).replace("✓ ", "").replace("○ ", "")
        self.agent.setItemText(i, ("✓ " if ok else "○ ") + base)
        self.agent.setItemData(i, why, Qt.ItemDataRole.ToolTipRole)
        if i == self.agent.currentIndex():
            self._hint(pid)

    def _agent_changed(self, *_a):
        from .. import ai
        pid = self.agent.currentData()
        if not pid:
            return
        try:
            p = ai.get(pid)
        except KeyError:
            return
        cur = self.model.currentText()
        self.model.blockSignals(True)
        self.model.clear()
        try:
            ms = p.models()
        except Exception:  # noqa: BLE001
            ms = []
        dm = ""
        try:
            dp, m = ai.default("agent")
            if dp.id == pid:
                dm = m
        except Exception:  # noqa: BLE001
            pass
        dm = dm or p.default_model
        for m in dict.fromkeys(([dm] if dm else []) + ms):
            self.model.addItem(m)
        if cur and self.panel.keep_model and self.model.findText(cur) >= 0:
            self.model.setCurrentText(cur)
        self.model.blockSignals(False)
        self.steps.setEnabled(p.kind != "cli")
        self._hint(pid)

    def _hint(self, pid: str):
        from .. import ai
        try:
            p = ai.get(pid)
            ok, why = p.available()
        except Exception:  # noqa: BLE001
            return
        how = ("Runs the CLI's own agent in the folder with your account; its steps appear live."
               if p.kind == "cli" else "Built-in agent loop: the model reads/writes files and runs commands "
               "through the IDE's tools.")
        self.hint.setText(("" if ok else f"⚠ {why}\n") + how)

    def folder_path(self) -> str:
        return self.folder.text().strip()


class AgentManagerWidget(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.mgr = A.manager()
        self.keep_model = True
        self.inbox: list[list] = []          # [time, task, kind, text, read]
        self.setObjectName("agentManager")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(self.split)
        # left column
        left = QWidget()
        left.setObjectName("agentLeft")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(10, 6, 6, 4)
        cap = QLabel("TASKS")
        f = cap.font()
        f.setBold(True)
        f.setPointSizeF(max(7.0, f.pointSizeF() - 1))
        cap.setFont(f)
        theme.role(cap, "muted")
        top.addWidget(cap, 1)
        self.b_inbox = QToolButton()
        self.b_inbox.setText("Inbox")
        self.b_inbox.setToolTip("Notifications: tasks that need approval or finished")
        self.b_inbox.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.inbox_menu = QMenu(self.b_inbox)
        self.inbox_menu.aboutToShow.connect(self._fill_inbox)
        self.b_inbox.setMenu(self.inbox_menu)
        self.b_new = QToolButton()
        self.b_new.setText("+ New")
        self.b_new.setToolTip("New task")
        self.b_new.clicked.connect(self.new_task)
        top.addWidget(self.b_inbox)
        top.addWidget(self.b_new)
        ll.addLayout(top)
        self.composer = Composer(self)
        self.composer.start.connect(self.start_task)
        ll.addWidget(self.composer)
        self.list = QListWidget()
        self.list.setItemDelegate(TaskDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.setFrameShape(QFrame.Shape.NoFrame)
        self.list.currentItemChanged.connect(self._select)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._list_menu)
        ll.addWidget(self.list, 1)
        self.split.addWidget(left)
        self.view = TaskView(self)
        self.split.addWidget(self.view)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([300, 700])
        self.mgr.task_added.connect(self._task_added)
        self.mgr.task_removed.connect(self._task_removed)
        self.mgr.task_changed.connect(lambda _t: self.refresh_list())
        self.mgr.notify.connect(self._notify)
        for t in self.mgr.tasks:
            self._task_added(t)
        theme.changed.connect(self.restyle)
        try:
            from .. import ai
            ai.hub().providers_changed.connect(self.composer.fill_agents)
            ai.hub().defaults_changed.connect(lambda _p: self.composer._agent_changed())
            ai.hub().models_changed.connect(lambda pid: pid == self.composer.agent.currentData()
                                            and self.composer._agent_changed())
        except Exception:  # noqa: BLE001
            pass
        self.restyle()
        self.update_inbox()

    # ------------------------------------------------------------------ folder
    def default_folder(self) -> str:
        try:
            from ..ai import context
            f = context.solution_folder(self.win)
            if f is not None:
                return str(f)
        except Exception:  # noqa: BLE001
            pass
        return ""

    def project_opened(self):
        f = self.default_folder()
        if f:
            self.composer.folder.setText(f)
            try:
                self.mgr.load_history(f)
            except Exception as e:  # noqa: BLE001
                self.win.log(f"[Agent] history: {e}")

    # ------------------------------------------------------------------ tasks
    def new_task(self):
        self.list.clearSelection()
        self.list.setCurrentItem(None)
        self.view.set_task(None)
        self.composer.show()
        self.composer.text.setFocus()

    def composer_from(self, t: A.AgentTask):
        self.composer.text.setPlainText(t.prompt)
        i = self.composer.agent.findData(t.provider_id)
        if i >= 0:
            self.composer.agent.setCurrentIndex(i)
        if t.model:
            self.composer.model.setCurrentText(t.model)
        self.composer.perm.setCurrentIndex(max(0, self.composer.perm.findData(t.permission)))
        self.composer.folder.setText(str(t.root))
        self.composer.text.setFocus()

    def start_task(self, prompt: str | None = None, folder: str | None = None, provider_id: str | None = None,
                   model: str | None = None, permission: str | None = None, max_steps: int | None = None):
        c = self.composer
        prompt = (prompt if prompt is not None else c.text.toPlainText()).strip()
        if not prompt:
            c.text.setFocus()
            return None
        folder = folder or c.folder_path() or self.default_folder()
        if not folder:
            d = QFileDialog.getExistingDirectory(self, "Folder for the agent", str(Path.home()))
            if not d:
                return None
            folder = d
            c.folder.setText(d)
        if not Path(folder).is_dir():
            QMessageBox.warning(self, TITLE, f"The folder does not exist:\n{folder}")
            return None
        pid = provider_id or c.agent.currentData() or ""
        mdl = model if model is not None else c.model.currentText().strip()
        perm = permission or c.perm.currentData() or "ask"
        steps = max_steps or c.steps.value()
        try:
            t = self.mgr.create(prompt, folder, provider_id=pid, model=mdl, permission=perm, max_steps=steps,
                                start=False)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, TITLE, f"Cannot start the task:\n{e}")
            return None
        if prompt is not None and prompt == c.text.toPlainText().strip():
            c.text.clear()
        self.select(t)
        t.start()
        return t

    def _task_added(self, t: A.AgentTask):
        it = QListWidgetItem()
        it.setData(Qt.ItemDataRole.UserRole, t)
        it.setToolTip(t.prompt[:500])
        idx = self.mgr.tasks.index(t) if t in self.mgr.tasks else 0
        self.list.insertItem(min(idx, self.list.count()), it)
        t.step_added.connect(lambda _s, t=t: self._task_activity(t))

    def _task_removed(self, t):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) is t:
                self.list.takeItem(i)
                break
        if self.view.task is t:
            self.view.set_task(None)

    def _task_activity(self, t):
        if self.view.task is t:
            t.unread = False
        self.refresh_list()

    def item_of(self, t) -> QListWidgetItem | None:
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) is t:
                return self.list.item(i)
        return None

    def select(self, t):
        it = self.item_of(t)
        if it is not None:
            self.list.setCurrentItem(it)

    def _select(self, cur, _prev=None):
        t = cur.data(Qt.ItemDataRole.UserRole) if cur is not None else None
        if t is not None and t is not self.view.task:
            self.view.set_task(t)
            for n in self.inbox:
                if n[1] is t and not (n[2] == "approval" and t.status == "waiting"):
                    n[4] = True
            self.update_inbox()

    def refresh_list(self):
        self.list.viewport().update()
        self.update_inbox()

    def _list_menu(self, pos):
        it = self.list.itemAt(pos)
        if it is None:
            return
        t = it.data(Qt.ItemDataRole.UserRole)
        m = QMenu(self)
        if t.running:
            m.addAction("Stop", t.stop)
        m.addAction("Run again as a new task", lambda: self.composer_from(t))
        m.addAction("Open folder", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(t.root))))
        m.addSeparator()
        m.addAction("Remove from list", lambda: self.mgr.remove(t))
        m.exec(self.list.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------ inbox
    def _notify(self, t, kind, text):
        read = self.view.task is t and self.isVisible() and kind != "approval"
        self.inbox.insert(0, [time.time(), t, kind, text, read])
        del self.inbox[50:]
        self.update_inbox()
        msg = {"approval": f"Agent '{t.title}' needs your approval: {text}",
               "done": f"Agent '{t.title}' finished.",
               "failed": f"Agent '{t.title}' failed.",
               "cancelled": f"Agent '{t.title}' stopped."}.get(kind, f"Agent '{t.title}': {kind}")
        try:
            self.win.statusBar().showMessage(msg, 8000)
            QApplication.alert(self.win, 0)
        except Exception:  # noqa: BLE001
            pass
        if kind == "approval":
            dock = getattr(self.win, "dock_agents", None)
            if dock is not None and not self.isVisible():
                self.win.log(f"[Agent] {msg} (View > Agent Manager)")

    def unread_count(self) -> int:
        return len([x for x in self.inbox if not x[4] and not (x[2] == "approval" and x[1].status != "waiting")])

    def update_inbox(self):
        n = self.unread_count()
        waiting = len([t for t in self.mgr.tasks if t.status == "waiting"])
        self.b_inbox.setText(f"Inbox ({n})" if n else "Inbox")
        self.b_inbox.setStyleSheet(f"QToolButton {{ color: {_c('note')}; font-weight: 600; }}" if waiting else "")
        dock = getattr(self.win, "dock_agents", None)
        if dock is not None:
            run = len(self.mgr.running())
            dock.setWindowTitle(TITLE + (f" ({waiting} waiting)" if waiting else (f" ({run} running)" if run else "")))

    def _fill_inbox(self):
        m = self.inbox_menu
        m.clear()
        if not self.inbox:
            a = m.addAction("No notifications")
            a.setEnabled(False)
            return
        for when, t, kind, text, read in self.inbox[:20]:
            label = {"approval": "Needs approval", "done": "Finished", "failed": "Failed",
                     "cancelled": "Stopped"}.get(kind, kind)
            if kind == "approval" and t.status != "waiting":
                label = "Approved / answered"
            a = m.addAction(f"{time.strftime('%H:%M', time.localtime(when))}  {label}: {t.title}")
            a.setToolTip(text[:300])
            if not read and not (kind == "approval" and t.status != "waiting"):
                f = a.font()
                f.setBold(True)
                a.setFont(f)
            a.triggered.connect(lambda _c=False, t=t: self.select(t))
        m.addSeparator()
        m.addAction("Mark all as read", self._read_all)
        m.addAction("Clear", self._clear_inbox)

    def _read_all(self):
        for n in self.inbox:
            n[4] = True
        self.update_inbox()

    def _clear_inbox(self):
        self.inbox.clear()
        self.update_inbox()

    # ------------------------------------------------------------------ look
    def restyle(self, *_a):
        t = theme.current()
        self.composer.setStyleSheet(f"#agentComposer {{ background: {t['alt_base']}; border-bottom: 1px solid "
                                    f"{t['border']}; }}")
        self.list.setStyleSheet(f"QListWidget {{ background: {t['base']}; }}")
        self.view.restyle()
        self.list.viewport().update()


# ============================================================================ install
def show(win, new: bool = False) -> AgentManagerWidget | None:
    w = getattr(win, "agent_manager", None)
    dock = getattr(win, "dock_agents", None)
    if w is None or dock is None:
        return None
    try:
        from . import workbench
        wb = workbench.get(win)
        if wb is not None and getattr(wb, "mode", "vs") != "vs":
            wb.show_view("agents")
    except Exception:  # noqa: BLE001
        pass
    dock.show()
    dock.raise_()
    if new:
        w.new_task()
    return w


def install(win) -> None:
    w = AgentManagerWidget(win)
    d = QDockWidget(TITLE, win)
    d.setObjectName(TITLE)
    d.setWidget(w)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    try:
        win.tabifyDockWidget(win.dock_output, d)
    except Exception:  # noqa: BLE001
        pass
    d.hide()
    win.dock_agents = d
    win.agent_manager = w
    w.project_opened()

    # editors follow the files agents write
    def on_written(p, win=win):
        try:
            from PyQt6 import sip
            if sip.isdeleted(win):
                return
        except Exception:  # noqa: BLE001
            pass
        _sync_editor(win, Path(p))
    A.on_file_written(on_written)
    win._agents_written_hook = on_written

    # menus
    a = QAction("Agent &Manager", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+M"))
    a.setToolTip("Antigravity-style agents: plan, edit files, run commands - you review every change")
    a.triggered.connect(lambda: show(win))
    win.a_agent_manager = a
    a2 = QAction("New Agent &Task...", win)
    a2.triggered.connect(lambda: show(win, new=True))
    win.a_new_agent_task = a2
    view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
    if view is not None:
        view.addSeparator()
        view.addAction(a)
        view.addAction(a2)
    try:
        from . import command_palette as cp
        cp.register_command("agents.show", "Agent Manager: Show", lambda: show(win), category="AI")
        cp.register_command("agents.new", "Agent Manager: New Task", lambda: show(win, new=True), category="AI")
        cp.register_command("agents.stop_all", "Agent Manager: Stop All Tasks", lambda: w.mgr.stop_all(),
                            category="AI")
    except Exception:  # noqa: BLE001
        pass
    # the workbench's Agent layout / VS Code side bar use this dock
    try:
        from . import workbench
        workbench.register_view("agents", "Agents", icon="agent", factory=lambda win_: win_.dock_agents,
                                modes=("vscode", "agent"), area="side", order=80, tooltip="Agent Manager")
    except Exception as e:  # noqa: BLE001
        win.log(f"[Agent] workbench: {e}")

    # follow the open project (folder + saved task history)
    orig = getattr(win, "_update_title", None)
    if callable(orig):
        def update_title(*a, _orig=orig, **k):
            r = _orig(*a, **k)
            try:
                f = w.default_folder()
                if f and f != getattr(w, "_last_folder", None):
                    w._last_folder = f
                    w.project_opened()
            except Exception:  # noqa: BLE001
                pass
            return r
        win._update_title = update_title

    orig_close = win.closeEvent

    def close_event(e):
        running = w.mgr.running()
        mine = [t for t in running if t.parent() is w.mgr]
        if mine:
            r = QMessageBox.question(win, TITLE, f"{len(mine)} agent task(s) are still running. Stop them and close?")
            if r != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
        orig_close(e)
        if e.isAccepted():
            for t in mine:
                t.stop()
            try:
                A._written_hooks.remove(on_written)
            except ValueError:
                pass
    win.closeEvent = close_event


__all__ = ["AgentManagerWidget", "TaskView", "Conversation", "Composer", "md_to_html", "is_rtl", "show", "install"]
