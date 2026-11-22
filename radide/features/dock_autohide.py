"""Visual Studio "Auto Hide" (the pin button) for every tool window - the IDE's "minimize".

* Every docked tool window (QDockWidget of the main window, also the ones features create later) gets a
  pin button in its title bar, just left of Qt's Float / Close buttons (right of them in Arabic RTL).
  The button is a child of the dock laid over the *native* title bar, so the title keeps its theme style
  (QDockWidget::title in radide/theme.py) and Qt keeps dragging / docking / floating / double-click.
* Auto-hiding a window hides the dock - Qt keeps its place in the layout (also its tab group) - and moves
  its content into a slide-out panel. The window gets a tab in a thin strip (a QToolBar outside the dock
  areas) on the edge it was docked to; tabified windows are auto-hidden together, as in VS.
* Hovering a tab slides the window out over the editor (an overlay, the layout does not reflow), clicking
  it slides it out and focuses it. It hides again when the focus or a click goes elsewhere, the mouse leaves
  a window opened by hovering, or Escape is pressed. The pin of the slid-out window docks the whole group
  back where it was (QDockWidget.show() restores Qt's placeholder).
* Window > Auto Hide (the active tool window) / Auto Hide All. View > <window> and any dock.show() of an
  auto-hidden window slide it out. The list survives restarts (QSettings "autohide/docks"; the docks are
  saved hidden in the workbench's saveState()).
* Only the Visual Studio layout: the VS Code / Agent layouts of the workbench put the windows back while
  they are active and auto-hide them again when the VS layout returns.

    mgr = win.autohide            # AutoHide
    mgr.auto_hide(dock) / mgr.restore(dock) / mgr.slide_out(dock) / mgr.hide_panel() / mgr.auto_hide_all()
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from PyQt6.QtCore import QEvent, QObject, QPoint, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QAbstractButton, QApplication, QDockWidget, QFrame, QHBoxLayout, QMenu,
                             QStackedLayout, QTabBar, QToolBar, QToolButton, QVBoxLayout, QWidget)

KEY = "autohide/docks"
ANIM_MS = 140            # slide animation (0 = none)
HOVER_MS = 350           # hover delay before a tab slides its window out
DA = Qt.DockWidgetArea
EDGE_OF = {DA.LeftDockWidgetArea: "left", DA.RightDockWidgetArea: "right",
           DA.TopDockWidgetArea: "top", DA.BottomDockWidgetArea: "bottom"}
TB_AREA = {"left": Qt.ToolBarArea.LeftToolBarArea, "right": Qt.ToolBarArea.RightToolBarArea,
           "top": Qt.ToolBarArea.TopToolBarArea, "bottom": Qt.ToolBarArea.BottomToolBarArea}
VERTICAL = ("left", "right")
_NATIVE = ("qt_dockwidget_floatbutton", "qt_dockwidget_closebutton")


# ============================================================================ helpers
def _t() -> dict:
    try:
        from .. import theme
        return theme.current()
    except Exception:  # noqa: BLE001
        return {"window": "#F0F0EA", "border": "#A0AFC3", "title1": "#F6F7F9", "title2": "#D8DFEA",
                "title_text": "#000000", "tab": "#E4E4DE", "tab_text": "#333333", "menu_sel": "#C1D2EE",
                "menu_sel_text": "#000000", "accent": "#316AC5", "base": "#FFFFFF"}


def _tr(text: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


def _alive(obj) -> bool:
    if obj is None:
        return False
    try:
        from PyQt6 import sip
        return not sip.isdeleted(obj)
    except Exception:  # noqa: BLE001
        return True


def pin_icon(color: str, horizontal: bool, size: int = 16) -> QIcon:
    """VS pin: upright = docked (click to auto-hide), lying = auto-hidden (click to dock)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if horizontal:
        p.translate(size, 0)
        p.rotate(90)
    s = size / 16.0
    pen = QPen(QColor(color), max(1.0, 1.2 * s))
    p.setPen(pen)
    p.drawRect(QRectF(5.5 * s, 1.5 * s, 5 * s, 6.5 * s))           # head
    p.drawLine(QPoint(round(8.5 * s), round(2 * s)), QPoint(round(8.5 * s), round(8 * s)))
    p.drawLine(QPoint(round(3.5 * s), round(8.5 * s)), QPoint(round(12.5 * s), round(8.5 * s)))   # collar
    p.drawLine(QPoint(round(8 * s), round(9 * s)), QPoint(round(8 * s), round(14.5 * s)))         # needle
    p.end()
    return QIcon(pm)


def close_icon(color: str, size: int = 16) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(color), 1.6))
    a, b = size * 0.28, size * 0.72
    p.drawLine(QPoint(round(a), round(a)), QPoint(round(b), round(b)))
    p.drawLine(QPoint(round(b), round(a)), QPoint(round(a), round(b)))
    p.end()
    return QIcon(pm)


def _button_qss(t: dict) -> str:
    return ("QToolButton { border: 1px solid transparent; background: transparent; padding: 0px; }"
            f"QToolButton:hover {{ border: 1px solid {t['border']}; background: {t['menu_sel']}; }}"
            f"QToolButton:pressed {{ background: {t['accent']}; }}")


@dataclass(eq=False)
class Group:
    edge: str
    docks: list = field(default_factory=list)
    size: int = 0


@dataclass(eq=False)
class Rec:
    group: Group
    content: QWidget


# ============================================================================ widgets
class PinButton(QToolButton):
    """The Auto Hide button laid over a dock's native title bar."""

    def __init__(self, dock: QDockWidget, mgr: "AutoHide"):
        super().__init__(dock)
        self.dock, self.mgr = dock, mgr
        self.setObjectName("radAutoHideButton")
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip("Auto Hide")
        self.setProperty("i18n_skip", False)
        self.clicked.connect(lambda: mgr.auto_hide(self.dock))
        self.restyle()
        self.hide()

    def restyle(self):
        t = _t()
        self.setIcon(pin_icon(t["title_text"], False))
        self.setIconSize(QSize(12, 12))
        self.setStyleSheet(_button_qss(t))


class StripTab(QWidget):
    """One tab of an auto-hide strip (vertical text on the left / right edges, like VS)."""

    def __init__(self, mgr: "AutoHide", dock: QDockWidget, edge: str):
        super().__init__()
        self.mgr, self.dock, self.edge = mgr, dock, edge
        self.setObjectName("radAutoHideTab")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip(dock.windowTitle())

    def label(self) -> str:
        return _tr(self.dock.windowTitle()) if _alive(self.dock) else ""

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        w = max(40, fm.horizontalAdvance(self.label()) + 20)
        h = fm.height() + 8
        return QSize(h, w) if self.edge in VERTICAL else QSize(w, h)

    minimumSizeHint = sizeHint

    def paintEvent(self, _e):
        t = _t()
        p = QPainter(self)
        r = self.rect()
        hot = self.underMouse() or self.mgr.shown_dock() is self.dock
        p.fillRect(r, QColor(t["menu_sel"] if hot else t["tab"]))
        p.setPen(QColor(t["border"]))
        p.drawRect(r.adjusted(0, 0, -1, -1))
        if self.mgr.shown_dock() is self.dock:          # accent line on the editor side
            acc = QColor(t["accent"])
            inner = {"left": QRect(r.right() - 2, 0, 3, r.height()), "right": QRect(0, 0, 3, r.height()),
                     "top": QRect(0, r.bottom() - 2, r.width(), 3), "bottom": QRect(0, 0, r.width(), 3)}
            p.fillRect(inner[self.edge], acc)
        p.setPen(QColor(t["menu_sel_text"] if hot else t["tab_text"]))
        if self.edge in VERTICAL:
            p.translate(r.width(), 0)
            p.rotate(90)
            box = QRect(0, 0, r.height(), r.width())
        else:
            box = r
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, self.label())
        p.end()

    def enterEvent(self, e):
        self.update()
        self.mgr._hover_start(self.dock)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        self.mgr._hover_cancel()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.mgr._tab_clicked(self.dock)
            e.accept()
            return
        super().mousePressEvent(e)

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction("Dock", lambda: self.mgr.restore(self.dock))
        m.addAction("Close", lambda: self.mgr.close_dock(self.dock))
        m.exec(e.globalPos())


class Strip(QToolBar):
    def __init__(self, edge: str, win):
        super().__init__("Auto Hide", win)
        self.edge = edge
        self.setObjectName(f"radAutoHideStrip_{edge}")
        self.setMovable(False)
        self.setFloatable(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.toggleViewAction().setVisible(False)
        self.setProperty("i18n_skip", True)
        self.acts: list = []
        self.tabs: list[StripTab] = []
        self.hide()


class _Header(QWidget):
    def __init__(self, panel: "SlidePanel"):
        super().__init__(panel)
        self.panel = panel
        self.setObjectName("radAutoHideHeader")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 3, 2)
        lay.setSpacing(1)
        lay.addStretch(1)
        self.pin = QToolButton(self)
        self.pin.setObjectName("radAutoHidePin")
        self.pin.setToolTip("Dock")
        self.close_btn = QToolButton(self)
        self.close_btn.setObjectName("radAutoHideClose")
        self.close_btn.setToolTip("Close")
        for b in (self.pin, self.close_btn):
            b.setAutoRaise(True)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setIconSize(QSize(12, 12))
            lay.addWidget(b)
        self.setFixedHeight(self.fontMetrics().height() + 10)

    def restyle(self):
        t = _t()
        self.pin.setIcon(pin_icon(t["title_text"], True))
        self.close_btn.setIcon(close_icon(t["title_text"]))
        q = _button_qss(t)
        self.pin.setStyleSheet(q)
        self.close_btn.setStyleSheet(q)
        self.update()

    def paintEvent(self, _e):
        t = _t()
        p = QPainter(self)
        r = self.rect()
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0, QColor(t["title1"]))
        g.setColorAt(1, QColor(t["title2"]))
        p.fillRect(r, g)
        p.setPen(QColor(t["border"]))
        p.drawLine(r.bottomLeft(), r.bottomRight())
        d = self.panel.dock
        if _alive(d):
            f = self.font()
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(t["title_text"]))
            rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
            if rtl:
                box = QRect(self.pin.geometry().right() + 4, 0, 0, r.height())
                box.setRight(r.right() - 6)
            else:
                box = QRect(6, 0, max(0, self.pin.x() - 10), r.height())
            al = Qt.AlignmentFlag.AlignLeft          # logical: the right edge in RTL
            text = p.fontMetrics().elidedText(_tr(d.windowTitle()), Qt.TextElideMode.ElideRight, box.width())
            p.drawText(box, al | Qt.AlignmentFlag.AlignVCenter, text)
        p.end()


class _Grip(QWidget):
    """The inner edge of the slid-out window: drag to resize it."""

    def __init__(self, panel: "SlidePanel"):
        super().__init__(panel)
        self.panel = panel
        self._start = None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._start = (e.globalPosition().toPoint(), QRect(self.panel.geometry()))

    def mouseMoveEvent(self, e):
        if self._start is None:
            return
        (p0, g0), p = self._start, e.globalPosition().toPoint()
        dx, dy = p.x() - p0.x(), p.y() - p0.y()
        g = QRect(g0)
        edge = self.panel.edge
        if edge in VERTICAL:
            if self.panel.opens_right:
                g.setWidth(max(120, g0.width() + dx))
            else:
                g.setLeft(min(g0.right() - 120, g0.left() + dx))
        elif self.panel.opens_down:
            g.setHeight(max(80, g0.height() + dy))
        else:
            g.setTop(min(g0.bottom() - 80, g0.top() + dy))
        self.panel.setGeometry(g)
        self.panel.size_changed()

    def mouseReleaseEvent(self, _e):
        self._start = None


class SlidePanel(QFrame):
    """The overlay that shows an auto-hidden window over the editor."""

    def __init__(self, mgr: "AutoHide", win):
        super().__init__(win)
        self.mgr = mgr
        self.setObjectName("radAutoHidePanel")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.dock = None
        self.edge = "left"
        self.opens_right = True
        self.opens_down = True
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)
        self.header = _Header(self)
        lay.addWidget(self.header)
        self.body = QWidget(self)
        self.body.setObjectName("radAutoHideBody")
        self.stack = QStackedLayout(self.body)
        lay.addWidget(self.body, 1)
        self.grip = _Grip(self)
        self.header.pin.clicked.connect(lambda: self.dock is not None and mgr.restore(self.dock))
        self.header.close_btn.clicked.connect(lambda: self.dock is not None and mgr.close_dock(self.dock))
        self.anim = QPropertyAnimation(self, b"geometry", self)
        self.hide()

    def restyle(self):
        t = _t()
        self.setStyleSheet(f"#radAutoHidePanel {{ background: {t['window']}; border: 1px solid {t['border']}; }}")
        self.header.restyle()

    def place_grip(self):
        r, k = self.rect(), 5
        if self.edge in VERTICAL:
            rect = QRect(r.width() - k, 0, k, r.height()) if self.opens_right else QRect(0, 0, k, r.height())
            self.grip.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            rect = QRect(0, r.height() - k, r.width(), k) if self.opens_down else QRect(0, 0, r.width(), k)
            self.grip.setCursor(Qt.CursorShape.SizeVerCursor)
        self.grip.setGeometry(rect)
        self.grip.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.place_grip()

    def size_changed(self):
        rec = self.mgr._recs.get(self.dock)
        if rec is not None:
            rec.group.size = self.width() if self.edge in VERTICAL else self.height()
            self.mgr.save()


# ============================================================================ manager
class AutoHide(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self._recs: dict[QDockWidget, Rec] = {}
        self._groups: list[Group] = []
        self._buttons: dict[QDockWidget, PinButton] = {}
        self._suspended: list[tuple[str, list, int]] = []       # groups put back while not in the VS layout
        self._pending: list[dict] = self._load()                 # saved entries whose docks are not here yet
        self._internal = 0
        self._ready = False
        self._shown: QDockWidget | None = None
        self._hover = False
        self._out_ticks = 0
        self._app_filter = False
        self.strips: dict[str, Strip] = {}
        for edge in ("left", "right", "bottom"):
            self._make_strip(edge)
        self.panel = SlidePanel(self, win)
        self._hover_timer = QTimer(self, singleShot=True, interval=HOVER_MS)
        self._hover_timer.timeout.connect(self._hover_fire)
        self._hover_dock = None
        self._scan_timer = QTimer(self, singleShot=True, interval=0)
        self._scan_timer.timeout.connect(self.scan)
        self._poll = QTimer(self, interval=250)
        self._poll.timeout.connect(self._poll_hover)
        QApplication.instance().focusChanged.connect(self._on_focus)
        win.installEventFilter(self)
        for d in win.findChildren(QDockWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            self.attach(d)
        try:
            from .. import theme
            theme.changed.connect(self._on_theme)      # a bound slot: disconnected with the window
        except Exception:  # noqa: BLE001
            pass
        self.restyle()

    # ------------------------------------------------------------------ state
    def is_auto_hidden(self, d) -> bool:
        return d in self._recs

    handles = is_auto_hidden

    def shown_dock(self):
        return self._shown

    def auto_hidden(self) -> list[QDockWidget]:
        return [d for g in self._groups for d in g.docks]

    def group_of(self, d) -> list[QDockWidget]:
        r = self._recs.get(d)
        return list(r.group.docks) if r else []

    def edge_of(self, d) -> str | None:
        r = self._recs.get(d)
        return r.group.edge if r else None

    def _wb(self):
        return getattr(self.win, "workbench", None)

    def _vs(self) -> bool:
        wb = self._wb()
        return wb is None or getattr(wb, "mode", "vs") == "vs"

    # ------------------------------------------------------------------ persistence
    def _settings(self):
        return getattr(self.win, "settings", None)

    def _load(self) -> list[dict]:
        s = self._settings()
        if s is None:
            return []
        try:
            data = json.loads(str(s.value(KEY, "") or "[]"))
            return [e for e in data if isinstance(e, dict) and e.get("name") and e.get("edge") in TB_AREA]
        except Exception:  # noqa: BLE001
            return []

    def save(self):
        s = self._settings()
        if s is None:
            return
        out, gi = [], 0
        groups = [(g.edge, g.docks, g.size) for g in self._groups] + list(self._suspended)
        for edge, docks, size in groups:
            names = [d.objectName() for d in docks if _alive(d) and d.objectName()]
            for n in names:
                out.append({"name": n, "edge": edge, "group": gi, "size": int(size)})
            gi += 1 if names else 0
        for e in self._pending:                      # docks of features that did not create them yet
            out.append(dict(e, group=1000 + int(e.get("group", 0))))
        if out:
            s.setValue(KEY, json.dumps(out))
        else:
            s.remove(KEY)
        s.sync()

    def _apply_pending(self):
        if not self._pending:
            return
        names = {d.objectName(): d for d in self._buttons if _alive(d) and d.objectName()}
        groups: dict[int, list[dict]] = {}
        for e in self._pending:
            groups.setdefault(int(e.get("group", 0)), []).append(e)
        left = []
        for _gi, entries in sorted(groups.items()):
            docks = [names[e["name"]] for e in entries if e["name"] in names]
            left += [e for e in entries if e["name"] not in names]
            docks = [d for d in docks if d not in self._recs and not d.isFloating()]
            if not docks:
                continue
            edge, size = entries[0]["edge"], int(entries[0].get("size", 0) or 0)
            if self._vs():
                self._hide_group(docks, edge, size, save=False)
            else:
                self._suspended.append((edge, docks, size))
        self._pending = left

    # ------------------------------------------------------------------ docks
    def attach(self, d):
        if not _alive(d) or d in self._buttons or d.parent() is not self.win:
            return
        b = PinButton(d, self)
        self._buttons[d] = b
        d.installEventFilter(self)
        for name in _NATIVE:
            nb = d.findChild(QAbstractButton, name)
            if nb is not None:
                nb.installEventFilter(self)
        d.topLevelChanged.connect(lambda *_a, d_=d: self._place_button(d_))
        d.dockLocationChanged.connect(lambda *_a, d_=d: self._place_button(d_))
        d.featuresChanged.connect(lambda *_a, d_=d: self._place_button(d_))
        d.destroyed.connect(lambda *_a, d_=d: self._forget(d_))
        self._place_button(d)
        if self._ready and any(e["name"] == d.objectName() for e in self._pending):
            QTimer.singleShot(0, self._apply_pending)

    def scan(self):
        """Attach the docks features created since the last scan."""
        if not _alive(self.win):
            return
        for d in self.win.findChildren(QDockWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if d not in self._buttons:
                self.attach(d)

    def _forget(self, d):
        self._buttons.pop(d, None)
        if not _alive(self.win) or not _alive(self.panel):
            return
        rec = self._recs.pop(d, None)
        if rec is not None:
            if d in rec.group.docks:
                rec.group.docks.remove(d)
            if not rec.group.docks and rec.group in self._groups:
                self._groups.remove(rec.group)
            if self._shown is d:
                self.hide_panel()
            if _alive(rec.content):
                self.panel.stack.removeWidget(rec.content)
                rec.content.deleteLater()
            self._rebuild_strips()

    def _place_button(self, d):
        b = self._buttons.get(d)
        if b is None or not _alive(b) or not _alive(d):
            return
        show = (self._vs() and d.titleBarWidget() is None and not d.isFloating() and d not in self._recs
                and not (d.features() & QDockWidget.DockWidgetFeature.DockWidgetVerticalTitleBar)
                and self.win.dockWidgetArea(d) in EDGE_OF)
        if not show:
            b.hide()
            return
        natives = [w for w in (d.findChild(QAbstractButton, n) for n in _NATIVE)
                   if w is not None and not w.isHidden() and w.width() > 0]
        rtl = d.layoutDirection() == Qt.LayoutDirection.RightToLeft
        if natives:
            s = max(w.height() for w in natives)
            y = min(w.y() for w in natives)
            x = (max(w.geometry().right() for w in natives) + 2 if rtl
                 else min(w.x() for w in natives) - s - 1)
        else:
            s = max(14, d.fontMetrics().height())
            y = 3
            x = 4 if rtl else d.width() - s - 4
        b.setGeometry(x, y, s, s)
        b.show()
        b.raise_()

    def _place_buttons(self):
        for d in list(self._buttons):
            self._place_button(d)

    def _tab_order(self, group: list) -> list:
        """The docks of a tab group in the order of their tabs."""
        titles = {d.windowTitle(): d for d in group}
        for bar in self.win.findChildren(QTabBar, options=Qt.FindChildOption.FindDirectChildrenOnly):
            texts = [bar.tabText(i) for i in range(bar.count())]
            if bar.count() and set(texts) == set(titles) and len(texts) == len(group):
                return [titles[t] for t in texts]
        return group

    def auto_hide(self, d) -> bool:
        """Auto-hide a docked tool window together with the windows tabbed with it."""
        if not _alive(d) or d in self._recs or not self._vs() or d.isFloating():
            return False
        edge = EDGE_OF.get(self.win.dockWidgetArea(d))
        if edge is None:
            return False
        group = [d] + [o for o in self.win.tabifiedDockWidgets(d)
                       if o.parent() is self.win and not o.isHidden() and not o.isFloating() and o not in self._recs]
        group = self._tab_order(group)
        size = d.width() if edge in VERTICAL else d.height()
        self._hide_group(group, edge, size)
        return True

    def _hide_group(self, docks: list, edge: str, size: int, save: bool = True):
        docks = [d for d in docks if _alive(d) and d not in self._recs and d.parent() is self.win]
        if not docks:
            return
        fw = QApplication.focusWidget()
        focus_in = fw is not None and any(d.isAncestorOf(fw) for d in docks)
        g = Group(edge, docks, int(size) if size and size > 40 else (300 if edge in VERTICAL else 200))
        self._internal += 1
        try:
            for d in docks:
                content = d.widget()
                d.hide()
                if content is None:
                    content = QWidget()
                self.panel.stack.addWidget(content)
                self._recs[d] = Rec(g, content)
                b = self._buttons.get(d)
                if b is not None:
                    b.hide()
        finally:
            self._internal -= 1
        self._groups.append(g)
        self._rebuild_strips()
        if save:
            self.save()
        if focus_in:
            self._focus_editor()

    def restore(self, d, focus: bool = True) -> bool:
        """Dock an auto-hidden window (and its group) back where it was."""
        rec = self._recs.get(d)
        if rec is None:
            return False
        g = rec.group
        if self._shown in g.docks:
            self.hide_panel()
        self._unhide(g, show=True)
        if g in self._groups:
            self._groups.remove(g)
        if _alive(d):
            d.raise_()
        self._rebuild_strips()
        self.save()
        if focus and _alive(d) and d.widget() is not None:
            self._focus_content(d.widget())
        return True

    def _unhide(self, g: Group, show: bool):
        self._internal += 1
        try:
            for m in list(g.docks):
                r = self._recs.pop(m, None)
                if r is None or not _alive(m):
                    continue
                if _alive(r.content):
                    self.panel.stack.removeWidget(r.content)
                    m.setWidget(r.content)
                    r.content.show()
                if show:
                    m.show()
        finally:
            self._internal -= 1
        QTimer.singleShot(0, self._place_buttons)

    def close_dock(self, d):
        """Close button of a slid-out window: the window is closed (View menu shows it docked again)."""
        rec = self._recs.get(d)
        if rec is None:
            return
        if self._shown is d:
            self.hide_panel(focus_back=True)
        g = rec.group
        one = Group(g.edge, [d], g.size)
        self._recs[d] = Rec(one, rec.content)
        self._unhide(one, show=False)
        g.docks.remove(d)
        if not g.docks and g in self._groups:
            self._groups.remove(g)
        self._rebuild_strips()
        self.save()

    def auto_hide_all(self) -> int:
        if not self._vs():
            return 0
        n = 0
        for d in self.win.findChildren(QDockWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if (d in self._recs or d.isHidden() or d.isFloating() or d.titleBarWidget() is not None
                    or self.win.dockWidgetArea(d) not in EDGE_OF):
                continue
            if self.auto_hide(d):
                n += 1
        return n

    def restore_all(self):
        for g in list(self._groups):
            if g.docks:
                self.restore(g.docks[0], focus=False)

    def active_dock(self):
        """The tool window holding the focus (or the slid-out one)."""
        if self._shown is not None and self.panel.isVisible():
            return self._shown
        w = QApplication.focusWidget()
        while w is not None:
            if isinstance(w, QDockWidget) and w.parent() is self.win:
                return w
            w = w.parentWidget()
        return None

    def toggle_active(self):
        d = self.active_dock()
        if d is None:
            return
        if d in self._recs:
            self.restore(d)
        else:
            self.auto_hide(d)

    # ------------------------------------------------------------------ mode switching (workbench)
    def suspend(self):
        """Put every auto-hidden window back into its (hidden) dock - for the VS Code / Agent layouts."""
        self.hide_panel()
        for g in list(self._groups):
            self._suspended.append((g.edge, list(g.docks), g.size))
            self._unhide(g, show=False)
        self._groups.clear()
        self._rebuild_strips()

    def resume(self):
        if not self._vs() or not self._suspended:
            self._rebuild_strips()
            return
        susp, self._suspended = self._suspended, []
        for edge, docks, size in susp:
            self._hide_group([d for d in docks if _alive(d) and not d.isFloating()], edge, size, save=False)
        self._rebuild_strips()
        self.save()

    def _hook_workbench(self):
        wb = self._wb()
        if wb is None or getattr(wb, "_autohide_hooked", False):
            return
        wb._autohide_hooked = True
        orig = wb.set_mode

        def set_mode(mode, save=True):
            if getattr(wb, "mode", "vs") == "vs" and mode != "vs" and self._groups:
                self.suspend()           # before the VS state is saved: the docks are saved hidden
            r = orig(mode, save)
            if mode == "vs":
                self.resume()
            return r
        wb.set_mode = set_mode
        try:
            wb.modeChanged.connect(self._on_mode)
        except Exception:  # noqa: BLE001
            pass

    def _on_mode(self, mode: str):
        if mode != "vs":
            if self._groups:
                self.suspend()
        else:
            self.resume()
        self._place_buttons()

    # ------------------------------------------------------------------ strips
    def _make_strip(self, edge: str) -> Strip:
        st = self.strips.get(edge)
        if st is not None:
            return st
        st = Strip(edge, self.win)
        if edge == "top":
            self.win.addToolBarBreak(TB_AREA[edge])
        self.win.addToolBar(TB_AREA[edge], st)
        st.hide()
        self.strips[edge] = st
        self._restyle_strip(st)
        st.installEventFilter(self)         # a strip moved / resized later (style, font): the panel follows
        return st

    def _settle(self):
        """Apply the main window's pending layout now: hiding docks / showing a strip only posts a LayoutRequest,
        and a panel placed from the old geometry would overlap the strip (or the layout would reflow under it)
        when that request is handled later - on a busy machine that can be many milliseconds later."""
        try:
            lay = self.win.layout()
            if lay is not None:
                lay.activate()
        except RuntimeError:
            pass

    def _restyle_strip(self, st: Strip):
        t = _t()
        st.setStyleSheet(f"QToolBar#{st.objectName()} {{ background: {t['window']}; border: none; "
                         f"spacing: 3px; padding: 1px; }}")

    def _rebuild_strips(self):
        if not _alive(self.win) or not _alive(self.panel):
            return
        for edge in ("left", "right", "top", "bottom"):
            groups = [g for g in self._groups if g.edge == edge and g.docks]
            st = self.strips.get(edge)
            if st is None and not groups:
                continue
            st = self._make_strip(edge)
            for a in st.acts:
                st.removeAction(a)
                a.deleteLater()
            for w in st.tabs:
                w.deleteLater()
            st.acts, st.tabs = [], []
            for i, g in enumerate(groups):
                if i:
                    gap = QWidget()
                    gap.setFixedSize(8, 8)
                    st.acts.append(st.addWidget(gap))
                    st.tabs.append(gap)
                for d in g.docks:
                    tab = StripTab(self, d, edge)
                    st.acts.append(st.addWidget(tab))
                    st.tabs.append(tab)
            st.setVisible(bool(groups) and self._vs())
        self._settle()
        self._sync_tabs()

    def _sync_tabs(self):
        for st in self.strips.values():
            for w in st.tabs:
                w.update()

    def tab_for(self, d) -> StripTab | None:
        for st in self.strips.values():
            for w in st.tabs:
                if isinstance(w, StripTab) and w.dock is d:
                    return w
        return None

    # ------------------------------------------------------------------ slide out / in
    def show_dock(self, d):
        """View > <window> for an auto-hidden window: slide it out and focus it."""
        self.slide_out(d, focus=True)

    def slide_out(self, d, focus: bool = True, hover: bool = False) -> bool:
        rec = self._recs.get(d)
        if rec is None or not self._vs():
            return False
        if self._shown is d and self.panel.isVisible():
            self._hover = self._hover and hover
            if focus:
                self._focus_content(rec.content)
            return True
        if self._shown is not None:
            self.hide_panel()
        p = self.panel
        p.dock = d
        p.edge = rec.group.edge
        p.stack.setCurrentWidget(rec.content)
        rec.content.show()
        rect = self._panel_rect(rec.group)
        p.raise_()
        p.show()
        p.header.update()
        start = QRect(rect)
        if p.edge in VERTICAL:
            start.setWidth(1) if p.opens_right else start.setLeft(rect.right())
        else:
            start.setHeight(1) if p.opens_down else start.setTop(rect.bottom())
        p.anim.stop()
        if ANIM_MS > 0 and self.win.isVisible():
            p.setGeometry(start)
            p.anim.setDuration(ANIM_MS)
            p.anim.setStartValue(start)
            p.anim.setEndValue(rect)
            p.anim.start()
        else:
            p.setGeometry(rect)
        p.place_grip()
        self._shown = d
        self._hover = hover
        self._out_ticks = 0
        if hover:
            self._poll.start()
        self._install_app_filter(True)
        self._sync_tabs()
        if focus:
            QTimer.singleShot(0, lambda c=rec.content: self._focus_content(c))
        return True

    def _panel_rect(self, g: Group) -> QRect:
        win, p = self.win, self.panel
        self._settle()
        st = self.strips.get(g.edge)
        sg = st.geometry() if st is not None and st.isVisible() else QRect()
        c = win.centralWidget().geometry() if win.centralWidget() is not None else win.rect()
        if sg.isNull() or sg.isEmpty():
            sg = {"left": QRect(c.left(), c.top(), 0, c.height()), "right": QRect(c.right(), c.top(), 0, c.height()),
                  "top": QRect(c.left(), c.top(), c.width(), 0),
                  "bottom": QRect(c.left(), c.bottom(), c.width(), 0)}[g.edge]
        if g.edge in VERTICAL:
            w = max(120, min(g.size, int(win.width() * 0.8)))
            p.opens_right = sg.center().x() < win.width() // 2
            x = sg.right() + 1 if p.opens_right else sg.left() - w
            return QRect(x, sg.top(), w, max(80, sg.height()))
        x0, x1 = sg.left(), sg.right()
        for e in VERTICAL:                       # not over the vertical strips
            o = self.strips.get(e)
            if o is not None and o.isVisible():
                og = o.geometry()
                if og.center().x() < win.width() // 2:
                    x0 = max(x0, og.right() + 1)
                else:
                    x1 = min(x1, og.left() - 1)
        h = max(80, min(g.size, int(win.height() * 0.8)))
        p.opens_down = sg.center().y() < win.height() // 2
        y = sg.bottom() + 1 if p.opens_down else sg.top() - h
        return QRect(x0, y, max(120, x1 - x0 + 1), h)

    def hide_panel(self, focus_back: bool = False):
        p = self.panel
        if self._shown is None and not p.isVisible():
            return
        fw = QApplication.focusWidget()
        had_focus = fw is not None and (fw is p or p.isAncestorOf(fw))
        p.anim.stop()
        p.hide()
        self._shown = None
        self._hover = False
        self._poll.stop()
        self._install_app_filter(False)
        self._sync_tabs()
        if focus_back or had_focus:
            self._focus_editor()

    def _focus_editor(self):
        tabs = getattr(self.win, "tabs", None)
        w = tabs.currentWidget() if tabs is not None else self.win.centralWidget()
        target = getattr(w, "editor", None) or w
        if target is not None and target.isVisible():
            target.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self.win.setFocus(Qt.FocusReason.OtherFocusReason)

    def _focus_content(self, w):
        if not _alive(w) or not self.panel.isVisible():
            return
        target = w if w.focusPolicy() & Qt.FocusPolicy.TabFocus else None
        if target is None:
            fp = w.focusProxy()
            if fp is not None and fp.focusPolicy() & Qt.FocusPolicy.TabFocus:
                target = fp
        if target is None:
            target = next((c for c in w.findChildren(QWidget)
                           if c.isVisible() and c.isEnabled() and c.focusPolicy() & Qt.FocusPolicy.TabFocus), None)
        (target or self.panel).setFocus(Qt.FocusReason.OtherFocusReason)

    def _inside(self, w) -> bool:
        p = self.panel
        return w is not None and (w is p or p.isAncestorOf(w))

    def _install_app_filter(self, on: bool):
        app = QApplication.instance()
        if on and not self._app_filter:
            app.installEventFilter(self)
            self._app_filter = True
        elif not on and self._app_filter:
            app.removeEventFilter(self)
            self._app_filter = False

    def _on_focus(self, _old, new):
        if self._shown is None or not self.panel.isVisible() or new is None:
            return
        if self._inside(new):
            if self._hover:
                self._hover = False
                self._poll.stop()
            return
        if new.window() is self.win:
            QTimer.singleShot(0, self._hide_if_focus_outside)

    def _hide_if_focus_outside(self):
        if self._shown is None:
            return
        fw = QApplication.focusWidget()
        if fw is None or not self._inside(fw):
            self.hide_panel()

    # hover
    def _hover_start(self, d):
        self._hover_dock = d
        if self._shown is d and self.panel.isVisible():
            return
        self._hover_timer.start(HOVER_MS)

    def _hover_cancel(self):
        self._hover_timer.stop()

    def _hover_fire(self):
        d = self._hover_dock
        tab = self.tab_for(d)
        if tab is not None and tab.underMouse():
            self.slide_out(d, focus=False, hover=True)

    def _poll_hover(self):
        if not self._hover or self._shown is None:
            self._poll.stop()
            return
        fw = QApplication.focusWidget()
        if fw is not None and self._inside(fw):
            self._hover = False
            self._poll.stop()
            return
        pos = QCursor.pos()
        p = self.panel
        over = QRect(p.mapToGlobal(QPoint(0, 0)), p.size()).adjusted(-4, -4, 4, 4).contains(pos)
        tab = self.tab_for(self._shown)
        if tab is not None and QRect(tab.mapToGlobal(QPoint(0, 0)), tab.size()).contains(pos):
            over = True
        self._out_ticks = 0 if over else self._out_ticks + 1
        if self._out_ticks >= 2:
            self.hide_panel()

    def _tab_clicked(self, d):
        self._hover_timer.stop()
        if self._shown is d and self.panel.isVisible() and not self._hover:
            self.hide_panel(focus_back=True)
        else:
            self.slide_out(d, focus=True, hover=False)
            self._hover = False
            self._poll.stop()

    # ------------------------------------------------------------------ events
    def eventFilter(self, obj, ev):
        try:
            return self._event(obj, ev)
        except RuntimeError:          # the window is being destroyed
            return False

    def _event(self, obj, ev):
        et = ev.type()
        win = self.win
        if obj is win:
            if et in (QEvent.Type.ChildAdded, QEvent.Type.ChildPolished):
                # (ChildAdded comes from the QObject constructor: the child is no QDockWidget yet)
                if not self._scan_timer.isActive():
                    self._scan_timer.start()
            elif et == QEvent.Type.Resize:
                if self._shown is not None and self.panel.isVisible():
                    rec = self._recs.get(self._shown)
                    if rec is not None:
                        QTimer.singleShot(0, self._reposition)
            elif et == QEvent.Type.LayoutDirectionChange:
                QTimer.singleShot(0, self._relayout)
            return False
        if self._app_filter and et in (QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress) \
                and isinstance(obj, QWidget):
            if et == QEvent.Type.KeyPress and ev.key() == Qt.Key.Key_Escape and self._shown is not None:
                fw = QApplication.focusWidget()
                if self._inside(fw) or self._inside(obj):
                    self.hide_panel(focus_back=True)
                    return True
            elif et == QEvent.Type.MouseButtonPress and self._shown is not None:
                if obj.window() is win and not self._inside(obj) and not isinstance(obj, StripTab):
                    self.hide_panel()
            return False
        if isinstance(obj, Strip):
            if et in (QEvent.Type.Move, QEvent.Type.Resize) and self._shown is not None and self.panel.isVisible():
                QTimer.singleShot(0, self._reposition)
            return False
        if isinstance(obj, QDockWidget):
            if et == QEvent.Type.Show and obj in self._recs and not self._internal:
                wb = self._wb()
                busy = wb is not None and getattr(wb, "_busy", 0) > 0
                QTimer.singleShot(0, lambda d=obj, b=busy: self._external_show(d, b))
            if et in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutDirectionChange,
                      QEvent.Type.WindowTitleChange):
                QTimer.singleShot(0, lambda d=obj: self._place_button(d))
                if et == QEvent.Type.WindowTitleChange and obj in self._recs:
                    QTimer.singleShot(0, self._rebuild_strips)
            return False
        if isinstance(obj, QAbstractButton) and obj.objectName() in _NATIVE:
            if et in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
                d = obj.parentWidget()
                if isinstance(d, QDockWidget):
                    self._place_button(d)
        return False

    def _external_show(self, d, busy: bool):
        """A feature (or the View menu, a toggle action ...) showed an auto-hidden window."""
        if d not in self._recs or not _alive(d) or not d.isVisible():
            return
        if not self._vs():
            self.suspend()
            return
        if busy:                                  # Reset Window Layout & co: the window is docked again
            self.restore(d, focus=False)
            return
        self._internal += 1
        try:
            d.hide()
        finally:
            self._internal -= 1
        if self._ready and self.win.isVisible():
            self.slide_out(d, focus=False)

    def _reposition(self):
        if self._shown is None:
            return
        rec = self._recs.get(self._shown)
        if rec is not None:
            self.panel.anim.stop()
            self.panel.setGeometry(self._panel_rect(rec.group))

    def _relayout(self):
        self._rebuild_strips()
        self._place_buttons()
        self._reposition()

    def _on_theme(self, *_a):
        try:
            self.restyle()
        except RuntimeError:          # a window being destroyed
            pass

    def restyle(self):
        for b in self._buttons.values():
            if _alive(b):
                b.restyle()
        for st in self.strips.values():
            self._restyle_strip(st)
        self.panel.restyle()
        self._sync_tabs()

    def after_restore_state(self):
        """restoreState() may show the (empty) strips or the auto-hidden docks: put them right again."""
        self._internal += 1
        try:
            for d in self._recs:
                if _alive(d) and not d.isHidden():
                    d.hide()
        finally:
            self._internal -= 1
        for edge, st in self.strips.items():
            st.setVisible(self._vs() and any(g.edge == edge and g.docks for g in self._groups))
        self._place_buttons()

    # ------------------------------------------------------------------ start-up
    def start(self):
        self._hook_workbench()
        self._apply_pending()
        self._ready = True
        self._rebuild_strips()
        self._place_buttons()


# ============================================================================ menu / install
def _find_menu(win, name: str):
    for a in win.menuBar().actions():
        if a.text().replace("&", "").lower() == name.lower() and a.menu() is not None:
            return a.menu()
    return None


def _add_menu(win, mgr: AutoHide):
    wm = _find_menu(win, "Window")
    mb = win.menuBar()
    if wm is None:
        wm = QMenu("&Window", win)
        help_menu = _find_menu(win, "Help")
        if help_menu is not None:
            mb.insertMenu(help_menu.menuAction(), wm)
        else:
            mb.addMenu(wm)
    else:
        wm.addSeparator()
    a = wm.addAction("Auto &Hide", mgr.toggle_active)
    a.setObjectName("autohide_toggle")
    a.setCheckable(True)
    b = wm.addAction("Auto Hide &All", mgr.auto_hide_all)
    b.setObjectName("autohide_all")
    wm.addSeparator()

    def sync():
        d = mgr.active_dock()
        a.setEnabled(d is not None and mgr._vs())
        a.setChecked(d is not None and mgr.is_auto_hidden(d))
        b.setEnabled(mgr._vs())
    wm.aboutToShow.connect(sync)
    mgr.a_toggle, mgr.a_all = a, b


def get(win) -> AutoHide | None:
    return getattr(win, "autohide", None)


def install(win) -> None:
    mgr = AutoHide(win)
    win.autohide = mgr
    _add_menu(win, mgr)
    win.extension_points.on("layout_restored", lambda: mgr.after_restore_state(), "auto-hide docks")
    QTimer.singleShot(0, mgr.start)       # after every feature (the workbench restores its layout first)


__all__ = ["AutoHide", "get", "install", "pin_icon"]
