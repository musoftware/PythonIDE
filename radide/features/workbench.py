"""Workbench layouts - CONTRACTS 9.2: one button switches the whole IDE between

  * Visual Studio  ("vs")     - today's menus, tool bars and docks,
  * VS Code        ("vscode") - Activity Bar + one Side Bar + editor (breadcrumbs) + bottom Panel + blue status bar,
  * Agent          ("agent")  - Antigravity style: the Agent Manager is the main surface, the editor on the right.

Switching is live (View > Layout, the VS | Code | Agent switch in the menu bar corner, Ctrl+K Ctrl+L).
Nothing is duplicated: the *existing* dock widgets (Solution Explorer, Find Results, Git Changes, Locals,
Watch, Call Stack, Databases, Error List, Output, Terminal, Immediate, Requests ...) are only moved to other
dock areas, get other title bars and are shown/hidden. Every mode keeps its own QMainWindow.saveState()
(QSettings "workbench/state/<mode>") so the user's arrangement per mode survives; the window geometry is saved
per mode too ("workbench/geometry/<mode>") and restored at start-up.

Hook for other features (AI Chat, Agent Manager, Web Chats, ...):

    from radide.features import workbench
    workbench.register_view("chat", "AI Chat", icon="chat", factory=lambda win: win.dock_ai_chat,
                            modes=("vscode", "agent"), area="side", order=70)

  * view ids "chat", "agents" and "webchats" replace the built-in entries (which otherwise look the dock up
    lazily: win.dock_ai_chat / win.dock_agents / win.dock_ai_web, a dock named "AI Chat" / "Agent Manager" /
    "AI Web Chats", or a bare widget win.ai_chat / win.agent_manager / win.ai_web, else a placeholder),
  * factory(win) returns a QDockWidget (preferred), a list of docks (shown together, split vertically) or a
    QWidget (wrapped in a dock "wb.view.<id>"); None means "not ready yet, ask again later",
  * icon: a QIcon, or a built-in icon name (explorer, search, scm, run, packages, database, chat, agent, globe,
    editor, settings, toolbox, terminal, puzzle),
  * area: "side" (Activity Bar + Side Bar), "panel" (bottom Panel) or "right" (secondary side bar),
  * action=callable(win) instead of a factory makes the Activity Bar button run a command.
  Registration works before or after this module is installed.
  workbench.get(win) -> Workbench (.mode, .set_mode(m), .show_view(id), .toggle_sidebar(), .toggle_panel(),
  .toggle_zen(), .reset_layout(), signal modeChanged(str)).
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QByteArray, QEvent, QObject, QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QDockWidget, QHBoxLayout, QLabel, QLineEdit, QMenu,
                             QPushButton, QSizePolicy, QTabWidget, QToolBar, QToolButton, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from . import command_palette as cp

MODES = ("vs", "vscode", "agent")
MODE_TITLES = {"vs": "Visual Studio", "vscode": "VS Code", "agent": "Agent"}
MODE_SHORT = {"vs": "VS", "vscode": "Code", "agent": "Agent"}
STATE_VERSION = 4
KEY = "workbench/"
L_AREA, R_AREA, B_AREA = (Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea,
                          Qt.DockWidgetArea.BottomDockWidgetArea)


# ============================================================================ icons (drawn, themed)
def _p_explorer(p):
    path = QPainterPath()
    path.moveTo(8, 3); path.lineTo(15, 3); path.lineTo(19, 7); path.lineTo(19, 18); path.lineTo(8, 18)
    path.closeSubpath()
    p.drawPath(path)
    p.drawPolyline([QPointF(15, 3), QPointF(15, 7), QPointF(19, 7)])
    p.drawPolyline([QPointF(5, 7), QPointF(5, 21), QPointF(15, 21)])


def _p_search(p):
    p.drawEllipse(QPointF(10.5, 10.5), 6, 6)
    p.drawLine(QPointF(15, 15), QPointF(20.5, 20.5))


def _p_scm(p):
    for c in ((7, 5), (7, 19), (17, 7)):
        p.drawEllipse(QPointF(*c), 2.2, 2.2)
    p.drawLine(QPointF(7, 7.2), QPointF(7, 16.8))
    path = QPainterPath(QPointF(17, 9.2))
    path.cubicTo(17, 14, 7, 12.5, 7, 16.8)
    p.drawPath(path)


def _p_run(p):
    path = QPainterPath()
    path.moveTo(7, 4.5); path.lineTo(18.5, 12); path.lineTo(7, 19.5); path.closeSubpath()
    p.drawPath(path)


def _p_packages(p):
    for x, y in ((4, 4.5), (4, 11.5), (11, 11.5)):
        p.drawRect(QRectF(x, y + 2, 6.5, 6.5))
    p.save()
    p.translate(17.5, 6.5)
    p.rotate(15)
    p.drawRect(QRectF(-3, -3, 6, 6))
    p.restore()


def _p_database(p):
    p.drawEllipse(QRectF(5, 3, 14, 5))
    p.drawLine(QPointF(5, 5.5), QPointF(5, 18.5))
    p.drawLine(QPointF(19, 5.5), QPointF(19, 18.5))
    p.drawArc(QRectF(5, 9.5, 14, 5), 180 * 16, 180 * 16)
    p.drawArc(QRectF(5, 16, 14, 5), 180 * 16, 180 * 16)


def _p_chat(p):
    path = QPainterPath()
    path.addRoundedRect(QRectF(3, 4, 18, 12.5), 3, 3)
    p.drawPath(path)
    p.drawPolyline([QPointF(8, 16.5), QPointF(7, 21), QPointF(12.5, 16.5)])
    p.save()
    p.setBrush(p.pen().color())
    for x in (8, 12, 16):
        p.drawEllipse(QPointF(x, 10.3), 0.6, 0.6)
    p.restore()


def _star(p, cx, cy, r):
    path = QPainterPath(QPointF(cx, cy - r))
    k = r * 0.18
    path.cubicTo(cx + k, cy - k, cx + k, cy - k, cx + r, cy)
    path.cubicTo(cx + k, cy + k, cx + k, cy + k, cx, cy + r)
    path.cubicTo(cx - k, cy + k, cx - k, cy + k, cx - r, cy)
    path.cubicTo(cx - k, cy - k, cx - k, cy - k, cx, cy - r)
    p.drawPath(path)


def _p_agent(p):
    _star(p, 11, 13, 8.5)
    _star(p, 19, 5, 3)


def _p_globe(p):
    p.drawEllipse(QPointF(12, 12), 9, 9)
    p.drawEllipse(QRectF(8, 3, 8, 18))
    p.drawLine(QPointF(3, 12), QPointF(21, 12))


def _p_editor(p):
    p.drawPolyline([QPointF(8, 7), QPointF(3, 12), QPointF(8, 17)])
    p.drawPolyline([QPointF(16, 7), QPointF(21, 12), QPointF(16, 17)])
    p.drawLine(QPointF(14, 4.5), QPointF(10, 19.5))


def _p_settings(p):
    p.drawEllipse(QPointF(12, 12), 3, 3)
    p.drawEllipse(QPointF(12, 12), 6.5, 6.5)
    for i in range(8):
        a = math.pi * i / 4
        p.drawLine(QPointF(12 + 6.5 * math.cos(a), 12 + 6.5 * math.sin(a)),
                   QPointF(12 + 9 * math.cos(a), 12 + 9 * math.sin(a)))


def _p_toolbox(p):
    p.drawRect(QRectF(3, 8, 18, 12))
    p.drawPolyline([QPointF(9, 8), QPointF(9, 5), QPointF(15, 5), QPointF(15, 8)])
    p.drawLine(QPointF(3, 13), QPointF(21, 13))


def _p_terminal(p):
    p.drawRect(QRectF(3, 5, 18, 14))
    p.drawPolyline([QPointF(7, 9.5), QPointF(10, 12), QPointF(7, 14.5)])
    p.drawLine(QPointF(12, 15), QPointF(17, 15))


def _p_puzzle(p):
    p.drawRect(QRectF(4, 7, 13, 13))
    p.drawEllipse(QPointF(10.5, 5.5), 2, 2)
    p.drawEllipse(QPointF(18.5, 13.5), 2, 2)


ICONS: dict[str, Callable] = {"explorer": _p_explorer, "search": _p_search, "scm": _p_scm, "run": _p_run,
                              "packages": _p_packages, "database": _p_database, "chat": _p_chat, "agent": _p_agent,
                              "globe": _p_globe, "editor": _p_editor, "settings": _p_settings,
                              "toolbox": _p_toolbox, "terminal": _p_terminal, "puzzle": _p_puzzle}


def make_icon(name: str, color: str, size: int = 24) -> QIcon:
    fn = ICONS.get(name, _p_puzzle)
    dpr = 2.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24, size / 24)
    pen = QPen(QColor(color), 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    try:
        fn(p)
    finally:
        p.end()
    return QIcon(pm)


def activity_icon(name: str, t: dict, size: int = 24) -> QIcon:
    """Dimmed when off, full colour when checked / hovered (like VS Code's Activity Bar)."""
    full = t["bar_text"]
    dim = full if t.get("dark") and t.get("muted") == full else _mix(full, t["toolbar2"], 0.42)
    on = make_icon(name, full, size).pixmap(size, size)
    off = make_icon(name, dim, size).pixmap(size, size)
    ic = QIcon()
    ic.addPixmap(off, QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(on, QIcon.Mode.Normal, QIcon.State.On)
    ic.addPixmap(on, QIcon.Mode.Active, QIcon.State.Off)
    ic.addPixmap(on, QIcon.Mode.Active, QIcon.State.On)
    return ic


def _mix(a: str, b: str, f: float) -> str:
    ca, cb = QColor(a), QColor(b)
    return QColor(round(ca.red() * (1 - f) + cb.red() * f), round(ca.green() * (1 - f) + cb.green() * f),
                  round(ca.blue() * (1 - f) + cb.blue() * f)).name()


def _t() -> dict:
    from .. import theme
    return theme.current()


def _theme_name() -> str:
    from .. import theme
    return theme.current_name()


# ============================================================================ registry
@dataclass
class ViewSpec:
    id: str
    title: str
    icon: object = None                  # QIcon | built-in icon name | None
    factory: Callable | None = None      # factory(win) -> QDockWidget | [QDockWidget] | QWidget | None
    modes: tuple = ("vscode", "agent")
    area: str = "side"                   # side | panel | right
    order: int = 100
    tooltip: str = ""
    action: Callable | None = None       # action(win): the Activity Bar button runs a command
    builtin: bool = False


_VIEWS: dict[str, ViewSpec] = {}
_WORKBENCHES: list = []


def register_view(view_id: str, title: str, icon=None, factory: Callable | None = None,
                  modes=("vscode", "agent"), area: str = "side", order: int = 100, tooltip: str = "",
                  action: Callable | None = None) -> ViewSpec:
    """Add (or replace) an Activity Bar / Side Bar / Panel entry - see the module docstring."""
    spec = ViewSpec(view_id, title, icon, factory, tuple(modes), area, order, tooltip, action)
    _VIEWS[view_id] = spec
    for wb in list(_WORKBENCHES):
        try:
            wb._on_registry(view_id)
        except Exception as e:  # noqa: BLE001
            try:
                wb.win.log(f"[workbench] register_view {view_id}: {e}")
            except Exception:  # noqa: BLE001
                pass
    return spec


def unregister_view(view_id: str) -> None:
    _VIEWS.pop(view_id, None)
    for wb in list(_WORKBENCHES):
        wb._made.pop(view_id, None)
        wb._on_registry(view_id)


def registered_views() -> list[ViewSpec]:
    return list(_VIEWS.values())


def get(win) -> "Workbench | None":
    return getattr(win, "workbench", None)


# ============================================================================ small widgets
class SideTitle(QWidget):
    """VS Code side bar section header: "EXPLORER" + small action buttons + close."""

    def __init__(self, wb: "Workbench", text: str, actions=(), closable=True):
        super().__init__()
        self.wb = wb
        self.setObjectName("wbSideTitle")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 4, 4)
        lay.setSpacing(2)
        self.label = QLabel(text.upper())
        self.label.setObjectName("wbSideTitleLabel")
        lay.addWidget(self.label, 1)
        for text_, tip, slot in actions:
            b = QToolButton()
            b.setObjectName("wbSideTitleButton")
            b.setText(text_)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(slot)
            lay.addWidget(b)
        if closable:
            b = QToolButton()
            b.setObjectName("wbSideTitleButton")
            b.setText("✕")
            b.setToolTip("Hide Side Bar (Ctrl+B)")
            b.setAutoRaise(True)
            b.clicked.connect(lambda: wb.toggle_sidebar(False))
            lay.addWidget(b)

    def set_text(self, text: str):
        self.label.setText(text.upper())


class SearchTitle(QWidget):
    """The Search view header: query box (+ Match Case / Regex) that fills the Find Results tree."""

    def __init__(self, wb: "Workbench"):
        super().__init__()
        self.wb = wb
        self.setObjectName("wbSideTitle")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 4, 6, 6)
        v.setSpacing(4)
        top = QHBoxLayout()
        lab = QLabel("SEARCH")
        lab.setObjectName("wbSideTitleLabel")
        top.addWidget(lab, 1)
        close = QToolButton()
        close.setObjectName("wbSideTitleButton")
        close.setText("✕")
        close.setAutoRaise(True)
        close.setToolTip("Hide Side Bar (Ctrl+B)")
        close.clicked.connect(lambda: wb.toggle_sidebar(False))
        top.addWidget(close)
        v.addLayout(top)
        row = QHBoxLayout()
        row.setSpacing(3)
        self.edit = QLineEdit()
        self.edit.setObjectName("wbSearchEdit")
        self.edit.setPlaceholderText("Search in the solution (Enter)")
        self.edit.setClearButtonEnabled(True)
        self.edit.returnPressed.connect(self.run)
        row.addWidget(self.edit, 1)
        self.case = QCheckBox("Aa")
        self.case.setToolTip("Match Case")
        self.regex = QCheckBox(".*")
        self.regex.setToolTip("Use Regular Expression")
        row.addWidget(self.case)
        row.addWidget(self.regex)
        v.addLayout(row)
        self.info = QLabel("")
        self.info.setObjectName("wbSearchInfo")
        v.addWidget(self.info)

    def run(self):
        n = search_solution(self.wb.win, self.edit.text(), self.case.isChecked(), self.regex.isChecked())
        self.info.setText("" if n is None else f"{n} result(s)" if n < SEARCH_LIMIT else f"{n}+ results (limit)")


class Breadcrumbs(QLabel):
    def __init__(self, wb: "Workbench"):
        super().__init__()
        self.wb = wb
        self.setObjectName("wbCrumbs")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.linkActivated.connect(self._click)
        self._segments: list[str] = []

    def refresh(self):
        t = _t()
        segs, links = self._compute()
        self._segments = links
        if not segs:
            self.setText("")
            return
        sep = f'<span style="color:{t["muted"]}">&nbsp;›&nbsp;</span>'
        parts = []
        for i, s in enumerate(segs):
            esc = s.replace("&", "&amp;").replace("<", "&lt;")
            colour = t["text"] if i == len(segs) - 1 else t["muted"]
            if links[i]:
                parts.append(f'<a href="{i}" style="color:{colour}; text-decoration:none">{esc}</a>')
            else:
                parts.append(f'<span style="color:{colour}">{esc}</span>')
        self.setText(sep.join(parts))
        self.setToolTip(" / ".join(segs))

    def _compute(self):
        win = self.wb.win
        w = win.tabs.currentWidget()
        if w is None or type(w).__name__ == "StartPage":
            return [], []
        path = cp.current_file(win)
        if path is not None:
            for root in cp.project_roots(win):
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    continue
                parts = [root.name] + list(rel.parts)
                links = [""] + ["/".join(rel.parts[:i + 1]) + "/" for i in range(len(rel.parts) - 1)] + [rel.name]
                return parts, links
            return [path.parent.name, path.name], ["", path.name]
        d = win._current_designer() if hasattr(win, "_current_designer") else None
        proj = win.project_of_widget(w) if hasattr(win, "project_of_widget") else None
        proj = proj or getattr(win, "project", None)
        title = win.tabs.tabText(win.tabs.currentIndex()).rstrip("*").strip()
        if d is not None:
            name = getattr(getattr(d, "doc", None), "form", None)
            name = getattr(name, "name", None) or title
            return [getattr(proj, "name", "") or "Project", f"{name}.form", "Design"], ["", f"{name}.form", ""]
        return [title], [""]

    def _click(self, href: str):
        try:
            link = self._segments[int(href)]
        except (ValueError, IndexError):
            return
        cp.quick_open(self.wb.win, link if link.endswith("/") else "")


class Placeholder(QWidget):
    def __init__(self, wb: "Workbench", kind: str):
        super().__init__()
        self.wb, self.kind = wb, kind
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 24, 24, 24)
        v.addStretch(1)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.icon)
        if kind == "agents":
            title = "AI Agents not installed"
            text = ("The Agent Manager (radide/features/ai_agents.py) is not part of this build yet.\n\n"
                    "When it is installed, this is where you start agent tasks, watch every step, review the "
                    "file diffs and accept or undo them - with Claude Code, Gemini CLI, Codex, opencode or a "
                    "local Ollama model.\n\nMeanwhile you can run a CLI agent (claude, gemini, opencode ...) "
                    "yourself in the Terminal.")
        else:
            title = "AI Chat not installed"
            text = ("The AI Chat window (radide/features/ai_chat.py) is not part of this build yet.\n\n"
                    "When it is installed you can chat about your code here with a CLI agent signed in with "
                    "your own account, a local model (Ollama, LM Studio) or an API key.")
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = self.title.font()
        f.setPointSizeF(f.pointSizeF() * 1.35)
        f.setBold(True)
        self.title.setFont(f)
        v.addWidget(self.title)
        self.text = QLabel(text)
        self.text.setWordWrap(True)
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from .. import theme
        theme.role(self.text, "muted")
        v.addWidget(self.text)
        row = QHBoxLayout()
        row.addStretch(1)
        if getattr(wb.win, "dock_terminal", None) is not None:
            b = QPushButton("Open Terminal")
            b.clicked.connect(self._terminal)
            row.addWidget(b)
        if kind == "agents":
            b = QPushButton("Back to the Editor")
            b.clicked.connect(lambda: wb.set_mode(wb.last_editor_mode))
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        v.addStretch(2)
        self.restyle()

    def restyle(self):
        t = _t()
        self.icon.setPixmap(make_icon("agent" if self.kind == "agents" else "chat", t["muted"], 56).pixmap(56, 56))

    def _terminal(self):
        try:
            from .terminal import show_terminal
            show_terminal(self.wb.win)
        except Exception as e:  # noqa: BLE001
            self.wb.win.log(f"[workbench] terminal: {e}")


# ============================================================================ search (Search view)
SEARCH_LIMIT = 2000
_BINARY = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".exe", ".dll", ".so", ".dylib", ".pyd",
           ".pyc", ".zip", ".7z", ".gz", ".tar", ".rar", ".pdf", ".db", ".sqlite", ".sqlite3", ".woff", ".woff2",
           ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".wav", ".avi", ".mov", ".class", ".jar", ".o", ".obj", ".lib",
           ".a", ".bin", ".dat", ".psd", ".xlsx", ".docx", ".pptx"}


def search_solution(win, text: str, case: bool = False, regex: bool = False) -> int | None:
    """Find *text* in every text file of the solution; results go to the Find Results tree."""
    if not text:
        return None
    try:
        rx = re.compile(text if regex else re.escape(text), 0 if case else re.I)
    except re.error as e:
        win.statusBar().showMessage(f"Bad regular expression: {e}", 5000)
        return None
    tree = getattr(win, "find_results", None)
    if tree is None:
        return None
    tree.clear()
    hits = 0
    for path, shown in cp.list_files(cp.project_roots(win)):
        if path.suffix.lower() in _BINARY:
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:4096]:
            continue
        body = data.decode("utf-8", errors="replace")
        for i, ln in enumerate(body.splitlines(), 1):
            if rx.search(ln):
                it = QTreeWidgetItem([shown, str(i), ln.strip()[:200]])
                it.setData(0, Qt.ItemDataRole.UserRole, str(path))
                tree.addTopLevelItem(it)
                hits += 1
                if hits >= SEARCH_LIMIT:
                    break
        if hits >= SEARCH_LIMIT:
            break
    dock = getattr(win, "dock_find", None)
    if dock is not None:
        dock.setWindowTitle(f"Find Results ({hits} matches)")
    return hits


# ============================================================================ chord keys
class _Keys(QObject):
    """Ctrl+K Ctrl+L (next layout), Ctrl+K Z (Zen mode) and Esc Esc (leave Zen) without stealing the
    first Ctrl+K from the focused widget (Monaco has its own Ctrl+K chords)."""

    def __init__(self, wb: "Workbench"):
        super().__init__(wb)
        self.wb = wb
        self.pending = 0.0
        self.last_esc = 0.0

    def eventFilter(self, obj, ev):
        et = ev.type()
        if et != QEvent.Type.KeyPress and et != QEvent.Type.ShortcutOverride:
            return False
        fw = QApplication.focusWidget()
        if fw is not None and obj is not fw:
            return False
        if fw is None and not (isinstance(obj, QWidget) and obj.isWindow()):
            return False
        try:
            if obj.window() is not self.wb.win:
                return False
        except Exception:  # noqa: BLE001
            return False
        key = ev.key()
        mods = ev.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier |
                                 Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        ctrl = Qt.KeyboardModifier.ControlModifier
        now = time.monotonic()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return False
        if self.pending and now - self.pending < 2.0:
            if (key == Qt.Key.Key_L and mods == ctrl) or (key == Qt.Key.Key_Z and mods in (ctrl, Qt.KeyboardModifier.NoModifier)):
                if et == QEvent.Type.ShortcutOverride:
                    ev.accept()                  # no shortcut may take the second key of our chord
                    return True
                self.pending = 0.0
                QTimer.singleShot(0, self.wb.next_mode if key == Qt.Key.Key_L else self.wb.toggle_zen)
                return True
            self.pending = 0.0
            return False
        if et != QEvent.Type.KeyPress:
            return False
        if key == Qt.Key.Key_K and mods == ctrl:
            self.pending = now
            return False
        if key == Qt.Key.Key_Escape and self.wb.zen_active():
            if now - self.last_esc < 0.7:
                self.last_esc = 0.0
                QTimer.singleShot(0, self.wb.toggle_zen)
                return True
            self.last_esc = now
        return False


# ============================================================================ the workbench
_EXT_LANG = {".py": "Python", ".pyw": "Python", ".vb": "Visual Basic", ".bas": "Visual Basic", ".cls": "Visual Basic",
             ".frm": "VB6 Form", ".ring": "Ring", ".rh": "Ring", ".cs": "C#", ".ps1": "PowerShell", ".java": "Java",
             ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript React",
             ".ts": "TypeScript", ".tsx": "TypeScript React", ".php": "PHP", ".c": "C", ".h": "C", ".cpp": "C++",
             ".cc": "C++", ".hpp": "C++", ".rs": "Rust", ".f90": "Fortran", ".f": "Fortran", ".for": "Fortran",
             ".go": "Go", ".lua": "Lua", ".rb": "Ruby", ".pl": "Perl", ".pm": "Perl", ".dart": "Dart",
             ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS", ".less": "Less", ".json": "JSON",
             ".md": "Markdown", ".sql": "SQL", ".xml": "XML", ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML",
             ".ini": "Ini", ".txt": "Plain Text", ".bat": "Batch", ".cmd": "Batch", ".sh": "Shell Script",
             ".form": "Form", ".radsln": "Solution", ".radproj": "Project"}


class Workbench(QObject):
    modeChanged = pyqtSignal(str)

    SIDE_WIDTH = 300
    PANEL_HEIGHT = 230

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.settings = win.settings
        self.mode = "vs"
        self.last_editor_mode = str(self.settings.value(KEY + "last_editor_mode", "vscode") or "vscode")
        if self.last_editor_mode not in ("vs", "vscode"):
            self.last_editor_mode = "vscode"
        self._applied = False
        self._busy = 0
        self._settle = 0.0
        self._active = {m: str(self.settings.value(KEY + f"side/{m}", d) or d)
                        for m, d in (("vscode", "explorer"), ("agent", "agents"))}
        self._side_hidden = {"vscode": False, "agent": False}
        self._widths: dict[tuple, int] = {}
        self._made: dict[str, list] = {}
        self._hosts: dict[str, QDockWidget] = {}
        self._titled: set = set()
        self._watched: set = set()
        self._panel_last: list[str] = []
        self._panel_current: str = ""
        self._zen: dict | None = None
        self._zen_actions: list = []
        self._status_key = None
        self._tick = 0
        self._builtin = self._builtin_views()
        # Visual Studio defaults, before anything is moved (used by Reset Layout / first VS restore)
        self._vs_default = win.saveState(STATE_VERSION)
        self._vs_corners = {c: win.corner(c) for c in Qt.Corner}
        self._build_editor_area()
        self._build_activity_bar()
        self._build_switcher()
        self._build_menu()
        self._build_status()
        self._register_commands()
        self._keys = _Keys(self)
        QApplication.instance().installEventFilter(self._keys)
        win.tabs.currentChanged.connect(lambda *_: self._on_tab_changed())
        from .. import theme
        from PyQt6 import sip
        theme.changed.connect(lambda *_: None if sip.isdeleted(self.win) else self.restyle())
        self._timer = QTimer(self, interval=500)
        self._timer.timeout.connect(self._poll)
        self.restyle()

    # ------------------------------------------------------------------ views
    def _builtin_views(self) -> dict[str, ViewSpec]:
        g = lambda *names: (lambda win: [getattr(win, n, None) for n in names])  # noqa: E731
        specs = [
            ViewSpec("explorer", "Explorer", "explorer", g("dock_solution"), order=10, tooltip="Explorer (Solution)"),
            ViewSpec("search", "Search", "search", g("dock_find"), order=20, tooltip="Search (Ctrl+Shift+F)"),
            ViewSpec("scm", "Source Control", "scm", g("dock_git"), order=30, tooltip="Source Control (Git)"),
            ViewSpec("run", "Run and Debug", "run", g("dock_locals", "dock_watch", "dock_stack", "dock_threads"),
                     modes=("vscode",),
                     order=40, tooltip="Run and Debug (F5)"),
            ViewSpec("packages", "Packages", "packages", None, modes=("vscode",), order=50,
                     tooltip="Packages / Extensions",
                     action=lambda win: getattr(win, "a_manage_packages", None) and win.a_manage_packages.trigger()),
            ViewSpec("databases", "Databases", "database", g("dock_databases"), modes=("vscode",), order=60,
                     tooltip="Databases"),
            ViewSpec("chat", "AI Chat", "chat", lambda win: self._discover("chat"), order=70, tooltip="AI Chat"),
            ViewSpec("agents", "Agents", "agent", lambda win: self._discover("agents"), order=80,
                     tooltip="Agent Manager"),
            ViewSpec("webchats", "AI Web Chats", "globe", lambda win: self._discover("webchats", placeholder=False),
                     order=90, tooltip="AI Web Chats"),
        ]
        for s in specs:
            s.builtin = True
        return {s.id: s for s in specs}

    _DISCOVER = {
        "chat": (("dock_ai_chat", "dock_chat", "ai_chat_dock"), ("AI Chat",), ("ai_chat", "chat_panel")),
        "agents": (("dock_agents", "dock_agent_manager", "dock_ai_agents"), ("Agent Manager", "Agents", "AI Agents"),
                   ("agent_manager", "agents_panel")),
        "webchats": (("dock_ai_web", "dock_web_chats", "dock_webchat"), ("AI Web Chats", "Web Chats"),
                     ("ai_web", "web_chats")),
    }

    def _discover(self, kind: str, placeholder: bool = True):
        win = self.win
        attrs, names, widgets = self._DISCOVER[kind]
        dock = next((getattr(win, a) for a in attrs if isinstance(getattr(win, a, None), QDockWidget)), None)
        if dock is None:
            dock = next((d for d in self._all_docks() if d.objectName() in names and d not in self._hosts.values()),
                        None)
        if dock is None:
            w = next((getattr(win, a) for a in widgets if isinstance(getattr(win, a, None), QWidget)), None)
            if w is not None:
                par = w.parentWidget()
                while par is not None and not isinstance(par, QDockWidget):
                    par = par.parentWidget()
                if par is not None:
                    dock = par
                elif w.parentWidget() is None or isinstance(w.parentWidget(), Placeholder):
                    host = self._host(kind)
                    if host.widget() is not w:
                        old = host.widget()
                        host.setWidget(w)
                        if isinstance(old, Placeholder):
                            old.deleteLater()
                    return [host]
        if dock is not None:
            host = self._hosts.get(kind)
            if host is not None and isinstance(host.widget(), Placeholder) and not host.isHidden():
                host.hide()
            return [dock]
        if not placeholder:
            return []
        host = self._host(kind)
        return [host]

    def _host(self, kind: str) -> QDockWidget:
        host = self._hosts.get(kind)
        if host is None:
            title = {"chat": "AI Chat", "agents": "Agent Manager", "webchats": "AI Web Chats"}[kind]
            host = QDockWidget(title, self.win)
            host.setObjectName(f"wb.host.{kind}")
            host.setWidget(Placeholder(self, kind) if kind != "webchats" else QWidget())
            self.win.addDockWidget(L_AREA, host)
            host.hide()
            self._hosts[kind] = host
        return host

    def specs(self) -> list[ViewSpec]:
        merged = dict(self._builtin)
        merged.update(_VIEWS)
        return sorted(merged.values(), key=lambda s: (s.order, s.title))

    def spec(self, view_id: str) -> ViewSpec | None:
        return _VIEWS.get(view_id) or self._builtin.get(view_id)

    def view_docks(self, view_id: str) -> list[QDockWidget]:
        s = self.spec(view_id)
        if s is None or s.factory is None:
            return []
        if not s.builtin and self._made.get(view_id):
            docks = [d for d in self._made[view_id] if _alive(d)]
            if docks:
                return docks
        try:
            r = s.factory(self.win)
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[workbench] view {view_id}: {e}")
            return []
        docks = self._normalize(view_id, s, r)
        if not s.builtin and docks:
            self._made[view_id] = docks
        return docks

    def _normalize(self, view_id, s, r) -> list[QDockWidget]:
        if r is None:
            return []
        items = r if isinstance(r, (list, tuple)) else [r]
        out = []
        for x in items:
            if isinstance(x, QDockWidget):
                out.append(x)
            elif isinstance(x, QWidget):
                d = QDockWidget(s.title, self.win)
                d.setObjectName(f"wb.view.{view_id}")
                d.setWidget(x)
                self.win.addDockWidget(B_AREA if s.area == "panel" else R_AREA if s.area == "right" else L_AREA, d)
                d.hide()
                out.append(d)
        return [d for d in out if _alive(d)]

    def side_views(self, mode: str | None = None) -> list[ViewSpec]:
        mode = mode or self.mode
        return [s for s in self.specs() if s.area == "side" and mode in s.modes]

    def _all_docks(self) -> list[QDockWidget]:
        return self.win.findChildren(QDockWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)

    def side_map(self, mode: str | None = None) -> dict[str, list[QDockWidget]]:
        out, seen = {}, set()
        for s in self.side_views(mode or ("vscode" if self.mode == "vs" else self.mode)):
            docks = [d for d in self.view_docks(s.id) if d is not None and id(d) not in seen]
            if docks:
                seen.update(id(d) for d in docks)
                out[s.id] = docks
        return out

    def side_docks(self) -> list[QDockWidget]:
        out = []
        for m in ("vscode", "agent"):
            for docks in self.side_map(m).values():
                out += [d for d in docks if d not in out]
        return out

    def panel_docks(self) -> list[QDockWidget]:
        names = ("dock_errors", "dock_output", "dock_terminal", "dock_immediate", "dock_web_requests", "dock_reports")
        out = [getattr(self.win, n, None) for n in names]
        for s in self.specs():
            if s.area == "panel":
                out += self.view_docks(s.id)
        side = set(id(d) for d in self.side_docks())
        res = []
        for d in out:
            if isinstance(d, QDockWidget) and _alive(d) and id(d) not in side and d not in res:
                res.append(d)
        return res

    def right_docks(self) -> list[QDockWidget]:
        out = [getattr(self.win, n, None) for n in ("dock_toolbox", "dock_props")]
        for s in self.specs():
            if s.area == "right":
                out += self.view_docks(s.id)
        return [d for d in out if isinstance(d, QDockWidget) and _alive(d)]

    def view_of(self, dock) -> str | None:
        m = self.mode if self.mode != "vs" else "vscode"
        for vid, docks in self.side_map(m).items():
            if dock in docks:
                return vid
        return None

    # ------------------------------------------------------------------ chrome building
    def _build_editor_area(self):
        win = self.win
        tabs = win.takeCentralWidget()
        box = QWidget()
        box.setObjectName("wbEditorArea")
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.crumbs = Breadcrumbs(self)
        self.crumbs.hide()
        v.addWidget(self.crumbs)
        v.addWidget(tabs, 1)
        win.setCentralWidget(box)
        self.editor_area = box

    def _build_activity_bar(self):
        bar = QToolBar("Activity Bar", self.win)
        bar.setObjectName("wb.activitybar")
        bar.setOrientation(Qt.Orientation.Vertical)
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setAllowedAreas(Qt.ToolBarArea.LeftToolBarArea)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        bar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        bar.toggleViewAction().setVisible(False)
        self.win.addToolBar(Qt.ToolBarArea.LeftToolBarArea, bar)
        bar.hide()
        self.activity = bar
        self._act_actions: dict[str, QAction] = {}

    def _rebuild_activity(self):
        bar = self.activity
        bar.clear()
        self._act_actions = {}
        mode = self.mode if self.mode != "vs" else "vscode"
        t = _t()
        size = 22 if mode == "agent" else 24
        bar.setIconSize(QSize(size, size))
        smap = self.side_map(mode)
        for s in self.side_views(mode):
            if s.id not in smap and s.action is None:
                continue
            if s.id == "packages" and getattr(self.win, "a_manage_packages", None) is None:
                continue
            a = QAction(self._icon(s, t), s.title, bar)
            a.setToolTip(s.tooltip or s.title)
            a.setProperty("wbNoPalette", True)
            a.setProperty("wbIcon", s.icon if isinstance(s.icon, str) else "")
            a.setCheckable(s.action is None)
            a.triggered.connect(lambda _c=False, vid=s.id: self._on_activity(vid))
            bar.addAction(a)
            self._act_actions[s.id] = a
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        bar.addWidget(spacer)
        if mode == "agent":
            a = QAction(activity_icon("editor", t, size), "Editor", bar)
            a.setToolTip(f"Back to the Editor ({MODE_TITLES[self.last_editor_mode]} layout)")
            a.setProperty("wbNoPalette", True)
            a.setProperty("wbIcon", "editor")
            a.triggered.connect(lambda: self.set_mode(self.last_editor_mode))
            bar.addAction(a)
            self._act_editor = a
        a = QAction(activity_icon("settings", t, size), "Manage", bar)
        a.setToolTip("Manage: Command Palette, Options, Color Theme, Layout")
        a.setProperty("wbNoPalette", True)
        a.setProperty("wbIcon", "settings")
        a.triggered.connect(self._manage_menu)
        bar.addAction(a)
        self._act_manage = a
        for b in bar.findChildren(QToolButton):
            b.setFixedSize(QSize(40, 40) if mode == "agent" else QSize(48, 46))
        self._sync_activity_checks()

    def _icon(self, s: ViewSpec, t: dict) -> QIcon:
        if isinstance(s.icon, QIcon):
            return s.icon
        size = 22 if self.mode == "agent" else 24
        return activity_icon(s.icon if isinstance(s.icon, str) else "puzzle", t, size)

    def _manage_menu(self):
        m = QMenu(self.win)
        m.addAction("Command Palette...\tCtrl+Shift+P", lambda: cp.show_palette(self.win))
        m.addAction("Quick Open...\tCtrl+P", lambda: cp.quick_open(self.win))
        opts = getattr(self.win, "a_options", None)
        if opts is not None:
            m.addAction(opts)
        th = m.addMenu("Color Theme")
        from .. import theme
        for name in theme.THEME_NAMES:
            a = th.addAction(name, lambda n=name: set_theme(self.win, n))
            a.setCheckable(True)
            a.setChecked(_setting_theme(self.win) == name)
        m.addSeparator()
        m.addMenu(self.layout_menu)
        btn = self.activity.widgetForAction(self._act_manage)
        pos = btn.mapToGlobal(btn.rect().topRight()) if btn is not None else self.win.cursor().pos()
        m.exec(pos)

    def _build_switcher(self):
        w = QWidget()
        w.setObjectName("wbSwitch")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 1, 6, 1)
        lay.setSpacing(0)
        self.switch_buttons: dict[str, QToolButton] = {}
        for i, m in enumerate(MODES):
            b = QToolButton()
            b.setObjectName(f"wbSwitch_{m}")
            b.setProperty("wbPos", "first" if i == 0 else "last" if i == len(MODES) - 1 else "mid")
            b.setText(MODE_SHORT[m])
            b.setToolTip(f"{MODE_TITLES[m]} layout  (Ctrl+K Ctrl+L: next layout)")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.clicked.connect(lambda _c=False, m_=m: self.set_mode(m_))
            lay.addWidget(b)
            self.switch_buttons[m] = b
        self.switcher = w
        self.win.menuBar().setCornerWidget(w, Qt.Corner.TopRightCorner)
        w.show()

    def _build_menu(self):
        win = self.win
        menu = QMenu("&Layout", win)
        self.layout_menu = menu
        grp = QActionGroup(menu)
        grp.setExclusive(True)
        self.mode_actions: dict[str, QAction] = {}
        for m in MODES:
            a = QAction(MODE_TITLES[m], menu)
            a.setCheckable(True)
            a.triggered.connect(lambda _c=False, m_=m: self.set_mode(m_))
            grp.addAction(a)
            menu.addAction(a)
            self.mode_actions[m] = a
        menu.addSeparator()
        self.a_next = menu.addAction("Next Layout\tCtrl+K, Ctrl+L", self.next_mode)
        self.a_sidebar = QAction("Toggle &Side Bar", win)
        self.a_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        self.a_sidebar.triggered.connect(lambda: self.toggle_sidebar())
        self.a_panel = QAction("Toggle &Panel", win)
        self.a_panel.setShortcut(QKeySequence("Ctrl+J"))
        self.a_panel.triggered.connect(lambda: self.toggle_panel())
        self.a_zen = QAction("&Zen Mode\tCtrl+K Z", win)
        self.a_zen.setCheckable(True)
        self.a_zen.triggered.connect(lambda: self.toggle_zen())
        for a in (self.a_sidebar, self.a_panel):
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            win.addAction(a)
            menu.addAction(a)
        menu.addAction(self.a_zen)
        menu.addSeparator()
        self.a_reset = menu.addAction("&Reset Current Layout", self.reset_layout)
        view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
        if view is not None:
            acts = view.actions()
            # right after Command Palette / Quick Open (command_palette.py puts them first)
            anchor = next((a for a in acts if a.isSeparator()), acts[0] if acts else None)
            view.insertMenu(anchor, menu)
        else:
            win.menuBar().addMenu(menu)

    def _build_status(self):
        sb = self.win.statusBar()
        self.st_branch = None
        self.st_lang = QToolButton()
        self.st_pos = QToolButton()
        self.st_ai = QToolButton()
        for b, tip in ((self.st_pos, "Go to Line/Column (Ctrl+G)"), (self.st_lang, "Language of the file"),
                       (self.st_ai, "AI provider for chat - click for the AI options")):
            b.setObjectName("wbStatusItem")
            b.setAutoRaise(True)
            b.setToolTip(tip)
            b.hide()
            sb.addPermanentWidget(b)
        self.st_pos.clicked.connect(lambda: cp.goto_line(self.win))
        self.st_lang.clicked.connect(lambda: cp.show_palette(self.win, ">"))
        self.st_ai.clicked.connect(self._ai_options)

    def _ai_options(self):
        for name in ("a_ai_settings", "a_ai_options", "a_options"):
            a = getattr(self.win, name, None)
            if a is not None:
                a.trigger()
                return

    def _register_commands(self):
        win = self.win
        for vid, title in (("explorer", "Explorer"), ("search", "Search"), ("scm", "Source Control"),
                           ("run", "Run and Debug"), ("databases", "Databases"), ("chat", "AI Chat"),
                           ("agents", "Agents"), ("webchats", "AI Web Chats")):
            cp.register_command(f"workbench.view.{vid}", f"Show {title}", lambda v=vid: self.reveal_view(v), "View")
        from .. import theme
        for name in theme.THEME_NAMES:
            cp.register_command(f"workbench.theme.{name}", f"Color Theme: {name}",
                                lambda n=name: set_theme(win, n), "Preferences")
        cp.register_command("workbench.focusEditor", "Focus Active Editor",
                            lambda: (win.tabs.currentWidget() or win.tabs).setFocus(), "View")

    # ------------------------------------------------------------------ style
    def qss(self) -> str:
        t = _t()
        ab = t["toolbar2"]
        hover = _mix(ab, t["bar_text"], 0.12)
        return f"""
QToolBar#wb\\.activitybar {{ background: {ab}; border: none; border-right: 1px solid {t['toolbar_border']};
                            padding: 0; spacing: 0; }}
QToolBar#wb\\.activitybar QToolButton {{ border: none; border-left: 2px solid transparent; background: transparent;
                                        margin: 0; padding: 0; }}
QToolBar#wb\\.activitybar QToolButton:hover {{ background: {hover}; }}
QToolBar#wb\\.activitybar QToolButton:checked {{ border-left: 2px solid {t['link']}; background: {hover}; }}
"""

    def title_qss(self) -> str:
        t = _t()
        return f"""
QWidget#wbSideTitle {{ background: {t['alt_base']}; border-bottom: 1px solid {t['border']}; }}
QLabel#wbSideTitleLabel {{ color: {t['muted']}; font-weight: bold; font-size: 8pt; letter-spacing: 1px; }}
QToolButton#wbSideTitleButton {{ color: {t['muted']}; border: none; padding: 1px 4px; background: transparent; }}
QToolButton#wbSideTitleButton:hover {{ color: {t['text']}; background: {_mix(t['alt_base'], t['text'], 0.12)}; }}
QLineEdit#wbSearchEdit {{ background: {t['base']}; color: {t['text']}; border: 1px solid {t['border']};
                          padding: 3px 4px; }}
QLineEdit#wbSearchEdit:focus {{ border: 1px solid {t['highlight']}; }}
QLabel#wbSearchInfo {{ color: {t['muted']}; }}
QCheckBox {{ color: {t['text']}; }}
"""

    def switch_qss(self) -> str:
        t = _t()
        return f"""
QWidget#wbSwitch {{ background: transparent; }}
QWidget#wbSwitch QToolButton {{ background: {t['button']}; color: {t['button_text']}; border: 1px solid {t['border']};
                                padding: 1px 9px; margin: 0; border-radius: 0; }}
QWidget#wbSwitch QToolButton[wbPos="first"] {{ border-top-left-radius: 3px; border-bottom-left-radius: 3px; }}
QWidget#wbSwitch QToolButton[wbPos="last"] {{ border-top-right-radius: 3px; border-bottom-right-radius: 3px; }}
QWidget#wbSwitch QToolButton:hover:!checked {{ background: {_mix(t['button'], t['highlight'], 0.18)}; }}
QWidget#wbSwitch QToolButton:checked {{ background: {t['highlight']}; color: {t['highlight_text']};
                                        border-color: {t['highlight']}; }}
"""

    def crumbs_qss(self) -> str:
        t = _t()
        return (f"QLabel#wbCrumbs {{ background: {t['base']}; color: {t['muted']}; padding: 3px 10px;"
                f" border-bottom: 1px solid {t['border']}; }}")

    def tabs_qss(self) -> str:
        t = _t()
        return f"""
QTabBar::tab {{ background: {t['tab']}; color: {t['tab_text']}; border: none; border-right: 1px solid {t['border']};
                padding: 6px 14px; margin: 0; }}
QTabBar::tab:selected {{ background: {t['base']}; color: {t['text']}; border-top: 2px solid {t['link']}; }}
QTabBar::tab:hover:!selected {{ background: {t['tab_hover']}; }}
"""

    def status_colors(self) -> tuple[str, str, str]:
        t = _t()
        if _theme_name() == "High Contrast" or (t.get("_vsx") and getattr(self.win, "session", None) is None):
            return t["status"], t["status_text"], t["border"]      # (a VS Code colour theme: its status bar)
        if getattr(self.win, "session", None) is not None:
            return "#CC6633", "#FFFFFF", "#CC6633"           # debugging (VS Code orange)
        if getattr(self.win, "project", None) is None:
            return "#68217A", "#FFFFFF", "#68217A"           # no folder open (VS Code purple)
        return "#007ACC", "#FFFFFF", "#007ACC"

    def _apply_status_style(self, force=False):
        sb = self.win.statusBar()
        if self.mode == "vs":
            if force or self._status_key is not None:
                sb.setStyleSheet("")
                self._status_key = None
            return
        bg, fg, border = self.status_colors()
        key = (bg, fg, border, _theme_name())
        if key == self._status_key and not force:
            return
        self._status_key = key
        hover = _mix(bg, fg, 0.18)
        sb.setStyleSheet(f"""
QStatusBar {{ background: {bg}; color: {fg}; border-top: 1px solid {border}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {fg}; background: transparent; }}
QToolButton#wbStatusItem {{ color: {fg}; background: transparent; border: none; padding: 0 6px; }}
QToolButton#wbStatusItem:hover {{ background: {hover}; }}
""")

    def restyle(self):
        try:
            self.activity.setStyleSheet(self.qss())
            self.switcher.setStyleSheet(self.switch_qss())
            self.crumbs.setStyleSheet(self.crumbs_qss())
            tq = self.title_qss()
            for d in list(self._titled):
                if _alive(d) and d.titleBarWidget() is not None:
                    d.titleBarWidget().setStyleSheet(tq)
            if self.mode != "vs":
                self.win.tabs.tabBar().setStyleSheet(self.tabs_qss())
                self._rebuild_activity()
                self.crumbs.refresh()
            self._apply_status_style(force=True)
            for host in self._hosts.values():
                w = host.widget()
                if isinstance(w, Placeholder):
                    w.restyle()
        except Exception as e:  # noqa: BLE001 - a theme change must never break the IDE
            self.win.log(f"[workbench] restyle: {e}")

    # ------------------------------------------------------------------ modes
    def next_mode(self):
        self.set_mode(MODES[(MODES.index(self.mode) + 1) % len(MODES)])

    def set_mode(self, mode: str, save: bool = True):
        if mode not in MODES:
            return
        if self._zen is not None:
            self.toggle_zen()
        if mode == self.mode and self._applied:
            self._sync_mode_widgets()
            return
        win = self.win
        if self._applied and save:
            self.save_mode_state(self.mode)
        size = win.size()
        plain = not (win.isMaximized() or win.isFullScreen())
        self._busy += 1
        try:
            self.mode = mode
            self._apply_chrome(mode)
            if not self._restore_state(mode):
                self._default_layout(mode)
            self._fixups(mode)
        finally:
            self._busy -= 1
            self._settle = time.monotonic() + 0.4
        if plain and self._applied:
            # docks shown for a moment while switching must not leave the window wider than before
            QTimer.singleShot(0, lambda: self._keep_size(size))
        self._applied = True
        if mode in ("vs", "vscode"):
            self.last_editor_mode = mode
            self.settings.setValue(KEY + "last_editor_mode", mode)
        self.settings.setValue(KEY + "mode", mode)
        self._sync_mode_widgets()
        self._on_tab_changed()
        if mode == "vs":
            self._timer.stop()
        else:
            self._timer.start()
            self._poll(force_ai=True)
        win.statusBar().showMessage(f"Layout: {MODE_TITLES[mode]}", 2500)
        self.modeChanged.emit(mode)

    def _keep_size(self, size):
        win = self.win
        if win.isMaximized() or win.isFullScreen():
            return
        hint = win.minimumSizeHint()
        want = QSize(max(size.width(), hint.width()), max(size.height(), hint.height()))
        if want != win.size():
            win.resize(want)

    def _sync_mode_widgets(self):
        for m, b in self.switch_buttons.items():
            b.setChecked(m == self.mode)
        for m, a in self.mode_actions.items():
            a.setChecked(m == self.mode)
        on = self.mode != "vs"
        self.a_sidebar.setEnabled(on)
        self.a_panel.setEnabled(on)

    def save_mode_state(self, mode: str | None = None):
        mode = mode or self.mode
        if self._zen is not None:
            return
        s = self.settings
        s.setValue(KEY + f"state/{mode}", self.win.saveState(STATE_VERSION))
        if not self.win.isFullScreen():
            s.setValue(KEY + f"geometry/{mode}", self.win.saveGeometry())
        if mode != "vs":
            s.setValue(KEY + f"side/{mode}", self._active.get(mode, ""))

    def save(self):
        """Remember the current mode and its layout (called on close)."""
        if self._zen is not None:
            self.toggle_zen()
        self.save_mode_state(self.mode)
        self.settings.setValue(KEY + "mode", self.mode)
        self.settings.sync()

    def _restore_state(self, mode: str) -> bool:
        data = self.settings.value(KEY + f"state/{mode}")
        if isinstance(data, QByteArray) and not data.isEmpty():
            self._materialize()
            try:
                return bool(self.win.restoreState(data, STATE_VERSION))
            except Exception:  # noqa: BLE001
                return False
        return False

    def _materialize(self):
        """Create the docks of registered views (so restoreState() can place them)."""
        for s in self.specs():
            if s.factory is not None:
                self.view_docks(s.id)

    def reset_layout(self):
        """Forget the saved arrangement of the current mode and build its default one."""
        self.settings.remove(KEY + f"state/{self.mode}")
        self._busy += 1
        try:
            self._apply_chrome(self.mode)
            self._default_layout(self.mode)
            self._fixups(self.mode)
        finally:
            self._busy -= 1
            self._settle = time.monotonic() + 0.4
        self._on_tab_changed()

    def _apply_chrome(self, mode: str):
        win = self.win
        if mode == "vs":
            self.activity.hide()
            for b in (self.st_lang, self.st_pos, self.st_ai):
                b.hide()
            self.crumbs.hide()
            win.tabs.tabBar().setStyleSheet("")
            for d in list(self._titled):
                if _alive(d):
                    old = d.titleBarWidget()
                    d.setTitleBarWidget(None)
                    if old is not None:
                        old.deleteLater()
            self._titled.clear()
            for c, area in self._vs_corners.items():
                win.setCorner(c, area)
            win.setTabPosition(B_AREA, QTabWidget.TabPosition.South)
            self._apply_status_style(force=True)
            return
        self._rebuild_activity()
        self.activity.show()
        win.setCorner(Qt.Corner.BottomLeftCorner, L_AREA)
        win.setCorner(Qt.Corner.TopLeftCorner, L_AREA)
        win.setCorner(Qt.Corner.BottomRightCorner, R_AREA)
        win.setCorner(Qt.Corner.TopRightCorner, R_AREA)
        win.setTabPosition(B_AREA, QTabWidget.TabPosition.North)
        win.tabs.tabBar().setStyleSheet(self.tabs_qss())
        self.crumbs.show()
        for b in (self.st_lang, self.st_pos, self.st_ai):
            b.show()
        self._apply_status_style(force=True)

    def _set_titles(self, mode: str):
        """VS Code style title bars: side views get "EXPLORER" headers, the Panel shows only its tabs."""
        tq = self.title_qss()
        smap = self.side_map(mode)
        for vid, docks in smap.items():
            s = self.spec(vid)
            for i, d in enumerate(docks):
                old = d.titleBarWidget()
                if vid == "search" and d is getattr(self.win, "dock_find", None):
                    if isinstance(old, SearchTitle):
                        continue
                    tw = SearchTitle(self)
                else:
                    text = s.title if i == 0 else d.windowTitle()
                    if isinstance(old, SideTitle) and getattr(old, "wb_view", None) == (vid, i, mode):
                        old.set_text(text if i == 0 else re.sub(r"\s*\(.*\)$", "", d.windowTitle()))
                        continue
                    tw = SideTitle(self, text, self._title_actions(vid) if i == 0 else (), closable=i == 0)
                    tw.wb_view = (vid, i, mode)
                    if i > 0:
                        d.windowTitleChanged.connect(
                            lambda txt, w=tw: _alive(w) and w.set_text(re.sub(r"\s*\(.*\)$", "", txt)))
                tw.setStyleSheet(tq)
                d.setTitleBarWidget(tw)
                if old is not None:
                    old.deleteLater()
                self._titled.add(d)
        for d in self.panel_docks():
            old = d.titleBarWidget()
            if old is not None and old.objectName() == "wbPanelTitle":
                continue
            tw = QWidget()
            tw.setObjectName("wbPanelTitle")
            tw.setFixedHeight(0)
            d.setTitleBarWidget(tw)
            if old is not None:
                old.deleteLater()
            self._titled.add(d)

    def _title_actions(self, vid: str):
        win = self.win
        if vid == "explorer":
            return [("⊕", "New Project / Add (File menu)", lambda: getattr(win, "a_new", None) and win.a_new.trigger()),
                    ("⊟", "Collapse All", lambda: win.solution.collapseAll())]
        if vid == "run":
            return [("▶", "Start Debugging (F5)", lambda: win.a_run.trigger()),
                    ("■", "Stop (Shift+F5)", lambda: win.a_stop.trigger())]
        if vid == "scm":
            return [("⟳", "Refresh", lambda: getattr(win, "git_panel", None) and win.git_panel.refresh())]
        if vid == "agents":
            return [("⤢", "Open the Agent layout", lambda: self.set_mode("agent"))] if self.mode != "agent" else []
        return []

    # ------------------------------------------------------------------ layouts
    def _place_group(self, docks: list[QDockWidget]):
        win = self.win
        prev = None
        for d in docks:
            if d.isFloating():
                d.setFloating(False)
            if prev is None:
                win.addDockWidget(L_AREA, d)
            else:
                win.splitDockWidget(prev, d, Qt.Orientation.Vertical)
            prev = d

    def _place_panel(self, docks: list[QDockWidget]):
        """All Panel docks in one tab group at the bottom (Output is the anchor when it is there)."""
        win = self.win
        if not docks:
            return
        out = getattr(win, "dock_output", None)
        anchor = out if out in docks else docks[0]
        if anchor.isFloating():
            anchor.setFloating(False)
        if win.dockWidgetArea(anchor) != B_AREA:
            vis = not anchor.isHidden()
            win.addDockWidget(B_AREA, anchor)
            anchor.setVisible(vis)
        for d in docks:
            if d is anchor or d in win.tabifiedDockWidgets(anchor):
                continue
            vis = not d.isHidden()
            if d.isFloating():
                d.setFloating(False)
            win.tabifyDockWidget(anchor, d)
            if d not in win.tabifiedDockWidgets(anchor) and win.tabifiedDockWidgets(anchor) is not None:
                # Qt does not move a dock that sits in another tab group: take it out first
                win.removeDockWidget(d)
                win.addDockWidget(B_AREA, d)
                win.tabifyDockWidget(anchor, d)
            d.setVisible(vis)

    def _default_layout(self, mode: str):
        win = self.win
        if mode == "vs":
            self._materialize()
            win.restoreState(self._vs_default, STATE_VERSION)
            for tb in win.findChildren(QToolBar):
                if tb is not self.activity and tb.parent() is win and tb.objectName() in ("Standard", "Debug"):
                    tb.show()
            return
        smap = self.side_map(mode)
        side_ids = set()
        for docks in smap.values():
            self._place_group(docks)
            side_ids.update(id(d) for d in docks)
        for d in self.side_docks():
            d.hide()
        # right: Toolbox above Properties (the designer's tools)
        right = [d for d in self.right_docks() if id(d) not in side_ids]
        prev = None
        for d in right:
            if d.isFloating():
                d.setFloating(False)
            if prev is None:
                win.addDockWidget(R_AREA, d)
            else:
                win.splitDockWidget(prev, d, Qt.Orientation.Vertical)
            prev = d
            d.hide()
        panel = self.panel_docks()
        self._place_panel(panel)
        web = self._is_web()
        for d in panel:
            name = d.objectName()
            on = mode == "vscode" and (name in ("Error List", "Output", "Terminal", "Immediate")
                                        or (name == "Requests" and web))
            d.setVisible(on)
        out = getattr(win, "dock_output", None)
        if mode == "vscode" and out is not None:
            out.raise_()
        # everything else (States, Timeline, Data, Outline ...) starts hidden: View menu brings it back
        known = side_ids | set(id(d) for d in self.side_docks() + right + panel)
        keep = {id(getattr(win, "dock_web_preview", None))}
        for d in self._all_docks():
            if id(d) not in known and id(d) not in keep and not d.isHidden():
                d.hide()
        for tb in win.findChildren(QToolBar):
            if tb is not self.activity and tb.parent() is win:
                tb.hide()
        want = self._active.get(mode) or ("agents" if mode == "agent" else "explorer")
        if want not in smap:
            want = "agents" if mode == "agent" and "agents" in smap else "explorer"
        self._active[mode] = want
        self._side_hidden[mode] = False
        width = self._agent_width() if mode == "agent" and want == "agents" else self.SIDE_WIDTH
        self._widths[(mode, want)] = width
        self.show_view(want, _internal=True)
        if mode == "vscode" and panel:
            vis = [d for d in panel if not d.isHidden()]
            if vis:
                win.resizeDocks([vis[0]], [self.PANEL_HEIGHT], Qt.Orientation.Vertical)
            if right:
                win.resizeDocks([right[0]], [270], Qt.Orientation.Horizontal)
        if mode in ("vscode", "agent"):
            self._follow_designer()

    def _agent_width(self) -> int:
        win = self.win
        w = win.width()
        scr = win.screen() or QApplication.primaryScreen()
        if scr is not None:
            w = min(w, scr.availableGeometry().width())
        return max(320, int(w * 0.55))

    def _fixups(self, mode: str):
        win = self.win
        self._watch_docks()
        if mode == "vs":
            self.activity.hide()
            return
        self.activity.show()
        for tb in win.findChildren(QToolBar):
            if tb is not self.activity and tb.parent() is win and not tb.isHidden():
                tb.hide()
        smap = self.side_map(mode)
        # every side view lives in the left area (docks created after the state was saved, moved by others ...)
        for vid, docks in smap.items():
            if any(d.isFloating() or win.dockWidgetArea(d) != L_AREA for d in docks):
                vis = any(not d.isHidden() for d in docks)
                self._place_group(docks)
                if not vis:
                    for d in docks:
                        d.hide()
        in_mode = set(id(d) for docks in smap.values() for d in docks)
        for d in self.side_docks():          # side views of the other mode only
            if id(d) not in in_mode and not d.isHidden():
                d.hide()
        side = set(in_mode)
        panel = [d for d in self.panel_docks() if id(d) not in side]
        if any(d.isFloating() or win.dockWidgetArea(d) != B_AREA for d in panel):
            self._place_panel(panel)
        for d in self.right_docks():
            if id(d) not in side and (d.isFloating() or win.dockWidgetArea(d) not in (R_AREA,)):
                vis = not d.isHidden()
                if d.isFloating():
                    d.setFloating(False)
                win.addDockWidget(R_AREA, d)
                d.setVisible(vis)
        # one side view at a time
        visible = [vid for vid, docks in smap.items() if any(not d.isHidden() for d in docks)]
        active = self._active.get(mode)
        if active in visible:
            pick = active
        elif visible:
            pick = visible[0]
        else:
            pick = None
        if pick is not None:
            self._active[mode] = pick
            self._side_hidden[mode] = False
            for vid in visible:
                if vid != pick:
                    for d in smap[vid]:
                        d.hide()
        else:
            self._side_hidden[mode] = True
        self._set_titles(mode)
        self._sync_activity_checks()

    def _watch_docks(self):
        for d in self._all_docks():
            if id(d) in self._watched:
                continue
            self._watched.add(id(d))
            d.visibilityChanged.connect(lambda vis, d=d: self._on_dock_visible(d, vis))

    def _is_web(self) -> bool:
        try:
            from ..web_site.project import is_website
            return any(is_website(p) for p in self.win.projects())
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------------ side bar / panel
    def side_visible(self) -> bool:
        if self.mode == "vs":
            return False
        # re-entrancy guard: a VS Code view container's factory evaluates its "when" clause, whose context
        # (vsx/context_keys.compute) asks side_visible() again -> unbounded mutual recursion (crawler hang)
        if getattr(self, "_side_visible_busy", False):
            return getattr(self, "_side_visible_last", False)
        self._side_visible_busy = True
        try:
            docks = self.side_map().get(self._active.get(self.mode), [])
            self._side_visible_last = any(not d.isHidden() for d in docks)
        finally:
            self._side_visible_busy = False
        return self._side_visible_last

    def _on_activity(self, vid: str):
        s = self.spec(vid)
        if s is None:
            return
        if s.action is not None and s.factory is None:
            try:
                s.action(self.win)
            except Exception as e:  # noqa: BLE001
                self.win.log(f"[workbench] {vid}: {e}")
            self._sync_activity_checks()
            return
        if vid == self._active.get(self.mode) and self.side_visible():
            self.toggle_sidebar(False)
        else:
            self.show_view(vid)

    def reveal_view(self, vid: str):
        """Show a view in any mode (in Visual Studio mode: its dock)."""
        if self.mode == "vs":
            docks = self.view_docks(vid)
            for d in docks:
                d.show()
                d.raise_()
            if not docks:
                s = self.spec(vid)
                if s is not None and s.action is not None:
                    s.action(self.win)
            return
        self.show_view(vid)

    def show_view(self, vid: str, _internal: bool = False):
        if self.mode == "vs":
            return self.reveal_view(vid)
        smap = self.side_map()
        docks = smap.get(vid)
        if not docks:
            s = self.spec(vid)
            if s is not None and s.action is not None:
                s.action(self.win)
            return
        win = self.win
        self._busy += 1
        try:
            cur = self._active.get(self.mode)
            if cur in smap and cur != vid:
                vis = [d for d in smap[cur] if not d.isHidden()]
                if vis and win.isVisible():
                    self._widths[(self.mode, cur)] = vis[0].width()
            for other, ds in smap.items():
                if other != vid:
                    for d in ds:
                        if not d.isHidden():
                            d.hide()
            if any(d.isFloating() or win.dockWidgetArea(d) != L_AREA for d in docks):
                self._place_group(docks)
            for d in docks:
                d.show()
                d.raise_()
            w = self._widths.get((self.mode, vid))
            if w is None:
                w = self._agent_width() if (self.mode == "agent" and vid == "agents") else self.SIDE_WIDTH
            win.resizeDocks([docks[0]], [w], Qt.Orientation.Horizontal)
            self._active[self.mode] = vid
            self._side_hidden[self.mode] = False
            if not _internal:
                self._set_titles(self.mode)
        finally:
            self._busy -= 1
        self._sync_activity_checks()
        if not _internal:
            inner = docks[0].widget()
            if inner is not None:
                inner.setFocus()

    def toggle_sidebar(self, show: bool | None = None):
        if self.mode == "vs":
            return
        vis = self.side_visible()
        show = (not vis) if show is None else show
        if show == vis:
            return
        if show:
            self.show_view(self._active.get(self.mode) or "explorer")
            return
        self._busy += 1
        try:
            docks = self.side_map().get(self._active.get(self.mode), [])
            if docks and self.win.isVisible():
                self._widths[(self.mode, self._active[self.mode])] = docks[0].width()
            for d in docks:
                d.hide()
            self._side_hidden[self.mode] = True
        finally:
            self._busy -= 1
        self._sync_activity_checks()

    def panel_visible(self) -> bool:
        return any(not d.isHidden() for d in self.panel_docks())

    def toggle_panel(self, show: bool | None = None):
        if self.mode == "vs":
            return
        docks = self.panel_docks()
        vis = self.panel_visible()
        show = (not vis) if show is None else show
        if show == vis:
            return
        self._busy += 1
        try:
            if not show:
                self._panel_last = [d.objectName() for d in docks if not d.isHidden()]
                cur = next((d for d in docks if not d.isHidden() and not d.visibleRegion().isEmpty()), None)
                self._panel_current = cur.objectName() if cur is not None else self._panel_current
                for d in docks:
                    d.hide()
            else:
                names = self._panel_last or ["Error List", "Output", "Terminal", "Immediate"]
                shown = [d for d in docks if d.objectName() in names] or docks[:1]
                if any(self.win.dockWidgetArea(d) != B_AREA for d in shown):
                    self._place_panel(shown)
                for d in shown:
                    d.show()
                cur = next((d for d in shown if d.objectName() == self._panel_current), shown[0] if shown else None)
                if cur is not None:
                    cur.raise_()
        finally:
            self._busy -= 1

    def _sync_activity_checks(self):
        active = self._active.get(self.mode)
        vis = self.side_visible()
        for vid, a in self._act_actions.items():
            if a.isCheckable():
                a.setChecked(vis and vid == active)

    def _on_dock_visible(self, dock, vis: bool):
        if self._busy or self.mode == "vs" or not vis or self._zen is not None:
            return
        if time.monotonic() < self._settle:
            return
        vid = self.view_of(dock)
        if vid is None:
            return
        if vid != self._active.get(self.mode) or self._side_hidden.get(self.mode):
            # someone showed a side view's dock (Find in Files, Git Changes, the debugger ...): make it active
            QTimer.singleShot(0, lambda v=vid: self._activate_later(v))

    def _activate_later(self, vid: str):
        if self.mode == "vs" or self._busy or self._zen is not None:
            return
        self.show_view(vid, _internal=True)
        self._set_titles(self.mode)

    def _follow_designer(self):
        """VS Code / Agent mode: Toolbox + Properties (secondary side bar) follow the form designer."""
        if self.mode not in ("vscode", "agent") or self._zen is not None:
            return
        win = self.win
        designer = (win._current_designer() is not None) if hasattr(win, "_current_designer") else False
        web_hidden = bool(getattr(win, "_web_docks_hidden", None))
        self._busy += 1
        try:
            for d in self.right_docks():
                if d in (getattr(win, "dock_toolbox", None), getattr(win, "dock_props", None)):
                    d.setVisible(designer and not web_hidden)
        finally:
            self._busy -= 1

    def _on_tab_changed(self):
        if self.mode == "vs":
            return
        try:
            self._follow_designer()
            self.crumbs.refresh()
            self._poll()
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[workbench] {e}")

    # ------------------------------------------------------------------ zen
    def zen_active(self) -> bool:
        return self._zen is not None

    def toggle_zen(self):
        win = self.win
        if self._zen is None:
            self._zen = {"state": win.saveState(STATE_VERSION), "full": win.isFullScreen(),
                         "max": win.isMaximized(), "crumbs": self.crumbs.isVisible()}
            have = set(id(a) for a in win.actions())
            self._zen_actions = []
            for _label, a in cp.menu_actions(win):      # shortcuts keep working with the menu bar hidden
                if id(a) not in have and not a.shortcut().isEmpty():
                    win.addAction(a)
                    self._zen_actions.append(a)
            self._busy += 1
            try:
                for d in self._all_docks():
                    d.hide()
                for tb in win.findChildren(QToolBar):
                    if tb.parent() is win:
                        tb.hide()
                win.menuBar().hide()
                win.statusBar().hide()
                self.crumbs.hide()
            finally:
                self._busy -= 1
            win.showFullScreen()
            self.a_zen.setChecked(True)
            win.statusBar().showMessage("Zen Mode - press Esc twice or Ctrl+K Z to leave", 4000)
            return
        z, self._zen = self._zen, None
        self._busy += 1
        try:
            for a in self._zen_actions:
                win.removeAction(a)
            self._zen_actions = []
            win.menuBar().show()
            win.statusBar().show()
            win.restoreState(z["state"], STATE_VERSION)
            self.crumbs.setVisible(z["crumbs"] or self.mode != "vs")
            if not z["full"]:
                if z["max"]:
                    win.showMaximized()
                else:
                    win.showNormal()
        finally:
            self._busy -= 1
            self._settle = time.monotonic() + 0.4
        self.a_zen.setChecked(False)
        self._sync_activity_checks()

    # ------------------------------------------------------------------ status bar
    def _poll(self, force_ai: bool = False):
        if self.mode == "vs":
            return
        win = self.win
        self._tick += 1
        self._apply_status_style()
        cv = win.tabs.currentWidget()
        ed = getattr(cv, "editor", None)
        if ed is not None and hasattr(ed, "getCursorPosition"):
            try:
                line, col = ed.getCursorPosition()
                self.st_pos.setText(f"Ln {line + 1}, Col {col + 1}")
                self.st_pos.show()
            except Exception:  # noqa: BLE001
                self.st_pos.hide()
        else:
            self.st_pos.hide()
        path = cp.current_file(win)
        if path is not None:
            self.st_lang.setText(_EXT_LANG.get(path.suffix.lower(), path.suffix.lstrip(".").upper() or "Plain Text"))
            self.st_lang.show()
        elif hasattr(win, "_current_designer") and win._current_designer() is not None:
            self.st_lang.setText("Form Designer")
            self.st_lang.show()
        else:
            self.st_lang.hide()
        if force_ai or self._tick % 10 == 1:
            self.st_ai.setText(ai_status_text())
            self.st_ai.show()

    # ------------------------------------------------------------------ registry events
    def _on_registry(self, view_id: str):
        self._made.pop(view_id, None)
        if self.mode == "vs":
            return
        self._busy += 1
        try:
            self._fixups(self.mode)
            self._rebuild_activity()
        finally:
            self._busy -= 1

    def refresh(self):
        """Look the AI docks up again (they may be created after the workbench) and fix the layout."""
        if self.mode != "vs":
            self._on_registry("")


def _alive(obj) -> bool:
    try:
        from PyQt6 import sip
        return obj is not None and not sip.isdeleted(obj)
    except Exception:  # noqa: BLE001
        return obj is not None


def ai_status_text() -> str:
    try:
        from .. import ai
        prov, model = ai.default("chat")
        if prov is None:
            return "AI: off"
        name = getattr(prov, "name", None) or getattr(prov, "id", "AI")
        return f"✨ {name}" + (f" · {model}" if model else "")
    except Exception:  # noqa: BLE001
        return "✨ AI: not configured"


def _setting_theme(win) -> str:
    try:
        from .settings import get as sget
        return sget(win, "theme")
    except Exception:  # noqa: BLE001
        return "Light"


def set_theme(win, name: str):
    """Switch the colour theme (saved like Tools > Options does)."""
    try:
        from .settings import KEY as SKEY
        from .settings import apply_all
        win.settings.setValue(SKEY + "theme", name)
        apply_all(win)
    except Exception:  # noqa: BLE001
        from .. import theme
        theme.apply(name)


# ============================================================================ install
def install(win) -> None:
    wb = Workbench(win)
    win.workbench = wb
    _WORKBENCHES.append(wb)
    # find results of the Search view carry the full path (web files are not modules of a project)

    def open_hit(item, _col):
        p = item.data(0, Qt.ItemDataRole.UserRole)
        if p:
            try:
                cp.open_path(win, Path(p), int(item.text(1)))
            except Exception as e:  # noqa: BLE001
                win.log(f"[workbench] {e}")
    if getattr(win, "find_results", None) is not None:
        win.find_results.itemDoubleClicked.connect(open_hit)
    mode = str(win.settings.value(KEY + "mode", "vs") or "vs")
    if mode not in MODES:
        mode = "vs"
    geo = win.settings.value(KEY + f"geometry/{mode}")
    if isinstance(geo, QByteArray) and not geo.isEmpty():
        win.restoreGeometry(geo)
    wb.set_mode(mode, save=False)
    def on_close() -> None:
        try:
            wb.save()
        finally:                          # the key filter / registry go even when the layout save failed
            QApplication.instance().removeEventFilter(wb._keys)
            if wb in _WORKBENCHES:
                _WORKBENCHES.remove(wb)
    win.extension_points.add_shutdown_step(on_close, "workbench")        # errors are logged
    # AI features installed after us (or creating their docks lazily) are picked up once the loop runs
    QTimer.singleShot(0, wb.refresh)
    QTimer.singleShot(1500, wb.refresh)


__all__ = ["MODES", "MODE_TITLES", "ViewSpec", "Workbench", "get", "make_icon", "register_view", "registered_views",
           "search_solution", "set_theme", "unregister_view", "ai_status_text"]
