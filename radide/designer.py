"""VB-style form designer.

A fake XP window with a grid surface; selection handles, multi-select
(Ctrl+click / rubber band), move/resize with snap-to-grid, containers
(Panel/GroupBox), a menu strip and a component tray for non-visual
components (Timer, MenuStrip)."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (QHBoxLayout, QMenu, QScrollArea, QToolButton, QWidget)

from .controls import CONTROL_TYPES
from .document import FormDocument
from .model import Control
from .preview import apply_props, make_preview
from .toolbox import MIME, TOOL_STATE, control_icon

GRID = 8
HANDLE = 7
BORDER = 4
CAPTION = 26
MENU_H = 20
FORM_BACK = "#ECE9D8"      # VB 2005 / Windows XP "Control" colour
MIN_SIZE = 8
MARGIN = 10

# handle index -> (moves left, moves top, moves right, moves bottom)
HANDLE_EDGES = [(1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0), (0, 0, 1, 0),
                (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1), (1, 0, 0, 0)]
HANDLE_CURSORS = [Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeVerCursor,
                  Qt.CursorShape.SizeBDiagCursor, Qt.CursorShape.SizeHorCursor] * 2


def snap(v: int) -> int:
    return int(round(v / GRID) * GRID)


def handle_rects(r: QRect) -> list[QRect]:
    cx, cy = r.center().x(), r.center().y()
    pts = [(r.left(), r.top()), (cx, r.top()), (r.right(), r.top()), (r.right(), cy),
           (r.right(), r.bottom()), (cx, r.bottom()), (r.left(), r.bottom()), (r.left(), cy)]
    h = HANDLE // 2
    return [QRect(x - h, y - h, HANDLE, HANDLE) for x, y in pts]


class Surface(QWidget):
    """The form's client area. Paints background + grid; hosts previews."""

    def __init__(self, view: "DesignerView"):
        super().__init__(view.frame)
        self.view = view

    def paintEvent(self, _e):
        p = QPainter(self)
        back = self.view.doc.form.props.get("BackColor") or FORM_BACK
        p.fillRect(self.rect(), QColor(back))
        p.setPen(QColor(0, 0, 0, 140))
        for x in range(0, self.width(), GRID):
            for y in range(0, self.height(), GRID):
                p.drawPoint(x, y)


class Overlay(QWidget):
    """Transparent layer above the previews that owns all mouse/keyboard input."""

    def __init__(self, view: "DesignerView"):
        super().__init__(view.surface)
        self.view = view
        self.doc = view.doc
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.mode = None            # None | move | resize | band
        self.handle = -1
        self.press = QPoint()
        self.starts: dict[int, QRect] = {}
        self.band = QRect()
        self.recorded = False

    # ---------------------------------------------------------------- helpers
    @property
    def form(self):
        return self.doc.form

    def abs_rect(self, c: Control) -> QRect:
        x, y = self.form.abs_pos(c)
        return QRect(x, y, int(c.props["Width"]), int(c.props["Height"]))

    def control_at(self, pos: QPoint) -> Control | None:
        for c in reversed(self.form.ordered()):
            if self.abs_rect(c).contains(pos):
                return c
        return None

    def container_at(self, pos: QPoint, exclude: list[Control]) -> str:
        banned = set()
        for c in exclude:
            banned.add(id(c))
            banned |= {id(d) for d in self.form.descendants(c)}
        for c in reversed(self.form.ordered()):
            if c.ctype.container and id(c) not in banned and self.abs_rect(c).contains(pos):
                return c.name
        return ""

    def handle_at(self, pos: QPoint) -> int:
        c = self.doc.selected
        if c is None or c.ctype.nonvisual:
            return -1
        for i, r in enumerate(handle_rects(self.abs_rect(c))):
            if r.adjusted(-2, -2, 2, 2).contains(pos):
                return i
        return -1

    def _movable(self) -> list[Control]:
        """Selected visual controls whose ancestors are not also selected."""
        sel = [c for c in self.doc.selection if not c.ctype.nonvisual]
        ids = {id(c) for c in sel}
        out = []
        for c in sel:
            p, ok = self.form.find(c.parent) if c.parent else None, True
            while p is not None:
                if id(p) in ids:
                    ok = False
                    break
                p = self.form.find(p.parent) if p.parent else None
            if ok:
                out.append(c)
        return out

    def _record(self):
        if not self.recorded:
            self.doc.checkpoint()
            self.recorded = True

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, e):
        self.setFocus()
        pos = e.position().toPoint()
        ctrl_key = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self.recorded = False
        if e.button() != Qt.MouseButton.LeftButton:
            hit = self.control_at(pos)
            if hit not in self.doc.selection:
                self.doc.select(hit)
            return
        if TOOL_STATE.current:
            self.view.create_control(TOOL_STATE.current, pos)
            TOOL_STATE.set(None)
            return
        self.press = pos
        self.handle = self.handle_at(pos) if not ctrl_key else -1
        if self.handle >= 0:
            self.mode = "resize"
            c = self.doc.selected
            self.starts = {id(c): QRect(int(c.props["Left"]), int(c.props["Top"]),
                                        int(c.props["Width"]), int(c.props["Height"]))}
            return
        hit = self.control_at(pos)
        if hit is None:
            if not ctrl_key:
                self.doc.select(None)
            self.mode = "band"
            self.band = QRect(pos, pos)
            return
        if ctrl_key:
            self.doc.select(hit, add=True)
            self.mode = None
            return
        if hit not in self.doc.selection:
            self.doc.select(hit)
        else:                       # make it primary, keep the group
            self.doc.selection.remove(hit)
            self.doc.selection.append(hit)
            self.doc.selectionChanged.emit(hit)
        self.mode = "move"
        self.starts = {id(c): QRect(int(c.props["Left"]), int(c.props["Top"]),
                                    int(c.props["Width"]), int(c.props["Height"]))
                       for c in self._movable()}

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        dx, dy = pos.x() - self.press.x(), pos.y() - self.press.y()
        if self.mode == "band":
            self.band = QRect(self.press, pos).normalized()
            self.update()
            return
        if self.mode == "move":
            if abs(dx) < 2 and abs(dy) < 2 and not self.recorded:
                return
            self._record()
            for c in self._movable():
                s = self.starts.get(id(c))
                if s is not None:
                    self.doc.set_geometry(c, snap(s.x() + dx), snap(s.y() + dy), s.width(), s.height())
            return
        if self.mode == "resize":
            c = self.doc.selected
            s = self.starts.get(id(c)) if c else None
            if s is None:
                return
            self._record()
            ml, mt, mr, mb = HANDLE_EDGES[self.handle]
            left, top = s.left(), s.top()
            right, bottom = left + s.width(), top + s.height()
            if ml: left = min(snap(left + dx), right - MIN_SIZE)
            if mt: top = min(snap(top + dy), bottom - MIN_SIZE)
            if mr: right = max(snap(right + dx), left + MIN_SIZE)
            if mb: bottom = max(snap(bottom + dy), top + MIN_SIZE)
            self.doc.set_geometry(c, left, top, right - left, bottom - top)
            return
        if TOOL_STATE.current:
            self.setCursor(Qt.CursorShape.CrossCursor)
            return
        h = self.handle_at(pos)
        if h >= 0:
            self.setCursor(HANDLE_CURSORS[h])
        elif self.control_at(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.unsetCursor()

    def mouseReleaseEvent(self, e):
        mode, self.mode = self.mode, None
        if mode == "band":
            band = self.band
            self.band = QRect()
            if band.width() > 2 or band.height() > 2:
                hits = [c for c in self.form.ordered() if self.abs_rect(c).intersects(band)]
                if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    hits = self.doc.selection + [c for c in hits if c not in self.doc.selection]
                self.doc.select_many(hits)
            self.update()
        elif mode == "move" and self.recorded:
            moved = self._movable()
            for c in moved:                    # drop into / out of containers
                r = self.abs_rect(c)
                target = self.container_at(r.center(), moved)
                self.doc.reparent(c, target)
            self.update()

    def mouseDoubleClickEvent(self, e):
        hit = self.control_at(e.position().toPoint())
        if hit:
            ev = CONTROL_TYPES[hit.type].default_event
            if ev:
                self.doc.eventRequested.emit(hit, ev)
        else:
            self.doc.eventRequested.emit(None, "Load")

    def contextMenuEvent(self, e):
        self.view.show_context_menu(self.control_at(e.pos()), e.globalPos())

    # --------------------------------------------------------------- keyboard
    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            TOOL_STATE.set(None)
            self.doc.select(None)
            return
        if not self.doc.selection:
            return super().keyPressEvent(e)
        if k == Qt.Key.Key_Delete:
            self.doc.remove_controls(list(self.doc.selection))
            return
        step = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0),
                Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}.get(k)
        if not step:
            return super().keyPressEvent(e)
        self.doc.checkpoint()
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            c = self.doc.selected
            if c is not None and not c.ctype.nonvisual:
                p = c.props
                self.doc.set_geometry(c, p["Left"], p["Top"], max(MIN_SIZE, p["Width"] + step[0]),
                                      max(MIN_SIZE, p["Height"] + step[1]))
        else:
            for c in self._movable():
                p = c.props
                self.doc.set_geometry(c, p["Left"] + step[0], p["Top"] + step[1], p["Width"], p["Height"])

    # ------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, e):
        name = bytes(e.mimeData().data(MIME)).decode()
        self.view.create_control(name, e.position().toPoint())
        TOOL_STATE.set(None)
        e.acceptProposedAction()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _e):
        p = QPainter(self)
        primary = self.doc.selected
        for c in self.doc.selection:
            if c.ctype.nonvisual:
                continue
            r = self.abs_rect(c)
            p.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r.adjusted(-1, -1, 0, 0))
            p.setPen(QPen(QColor("#000000")))
            # VB: primary selection has white handles, the others black
            p.setBrush(QColor("#ffffff") if c is primary else QColor("#000000"))
            for h in handle_rects(r):
                p.drawRect(h)
        if not self.band.isNull():
            p.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.band)


class FormFrame(QWidget):
    """Paints a Windows-XP style window (caption + optional menu strip) around
    the design surface and lets the user resize the form from its edges."""

    def __init__(self, view: "DesignerView"):
        super().__init__()
        self.view = view
        self.setMouseTracking(True)
        self._resizing = None
        self._press = QPoint()
        self._start = (0, 0)
        self.menu_rects: list[tuple[QRect, dict]] = []

    def menu_height(self) -> int:
        return MENU_H if self.view.doc.form.menu() else 0

    def _edge(self, pos: QPoint):
        r = self.rect()
        right = pos.x() >= r.width() - BORDER - 2
        bottom = pos.y() >= r.height() - BORDER - 2
        return (right, bottom) if (right or bottom) else None

    def _menu_hit(self, pos: QPoint):
        for r, item in self.menu_rects:
            if r.contains(pos):
                return r, item
        return None

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        doc = self.view.doc
        menu = doc.form.menu()
        hit = self._menu_hit(pos)
        if menu is not None and hit:
            doc.select(menu)
            self.view.popup_menu_item(hit[1], self.mapToGlobal(hit[0].bottomLeft()))
            return
        if menu is not None and BORDER + CAPTION <= pos.y() < BORDER + CAPTION + MENU_H:
            doc.select(menu)
            return
        doc.select(None)
        self._resizing = self._edge(pos)
        self._press = pos
        fp = doc.form.props
        self._start = (int(fp["Width"]), int(fp["Height"]))
        if self._resizing:
            doc.checkpoint()

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        if self._resizing:
            dx, dy = pos.x() - self._press.x(), pos.y() - self._press.y()
            doc = self.view.doc
            if self._resizing[0]:
                doc.set_prop(None, "Width", max(80, snap(self._start[0] + dx)), record=False)
            if self._resizing[1]:
                doc.set_prop(None, "Height", max(60, snap(self._start[1] + dy)), record=False)
            return
        edge = self._edge(pos)
        cursors = {(True, True): Qt.CursorShape.SizeFDiagCursor,
                   (True, False): Qt.CursorShape.SizeHorCursor,
                   (False, True): Qt.CursorShape.SizeVerCursor}
        self.setCursor(cursors[edge]) if edge else self.unsetCursor()

    def mouseReleaseEvent(self, _e):
        self._resizing = None

    def mouseDoubleClickEvent(self, e):
        pos = e.position().toPoint()
        menu = self.view.doc.form.menu()
        if menu is not None and BORDER + CAPTION <= pos.y() < BORDER + CAPTION + MENU_H:
            self.view.edit_menu(menu)
            return
        self.view.doc.eventRequested.emit(None, "Load")

    def contextMenuEvent(self, e):
        self.view.show_context_menu(None, e.globalPos())

    def paintEvent(self, _e):
        p = QPainter(self)
        r = self.rect()
        doc = self.view.doc
        active = doc.selected is None
        g = QLinearGradient(0, 0, 0, CAPTION + BORDER)
        g.setColorAt(0, QColor("#0A5FD8") if active else QColor("#7A96DF"))
        g.setColorAt(1, QColor("#0842B0") if active else QColor("#6D86C8"))
        p.fillRect(r, QColor("#0842B0") if active else QColor("#6D86C8"))
        p.fillRect(0, 0, r.width(), CAPTION + BORDER, g)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Trebuchet MS", 9, QFont.Weight.Bold))
        p.drawText(QRect(10, BORDER, r.width() - 90, CAPTION), Qt.AlignmentFlag.AlignVCenter,
                   str(doc.form.props.get("Text", "")))
        for i, colour in enumerate(("#2E6BEA", "#2E6BEA", "#D9542B")):
            x = r.width() - BORDER - 22 * (3 - i)
            br = QRect(x, BORDER + 3, 20, 20)
            p.setBrush(QColor(colour))
            p.setPen(QColor("#ffffff"))
            p.drawRoundedRect(br, 3, 3)
            p.setPen(QPen(QColor("#ffffff"), 2))
            c = br.center()
            if i == 0:
                p.drawLine(c.x() - 4, c.y() + 4, c.x() + 3, c.y() + 4)
            elif i == 1:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(c.x() - 4, c.y() - 4, 8, 8)
            else:
                p.drawLine(c.x() - 4, c.y() - 4, c.x() + 4, c.y() + 4)
                p.drawLine(c.x() + 4, c.y() - 4, c.x() - 4, c.y() + 4)
        # menu strip
        self.menu_rects = []
        menu = doc.form.menu()
        if menu is not None:
            mr = QRect(BORDER, BORDER + CAPTION, r.width() - 2 * BORDER, MENU_H)
            mg = QLinearGradient(0, mr.top(), 0, mr.bottom())
            mg.setColorAt(0, QColor("#F6F9FE"))
            mg.setColorAt(1, QColor("#DCE6F4"))
            p.fillRect(mr, mg)
            f = QFont("Segoe UI", 9)
            p.setFont(f)
            fm = QFontMetrics(f)
            x = mr.left() + 4
            items = menu.props.get("Items", [])
            for it in items:
                if it.get("Text") == "-":
                    continue
                w = fm.horizontalAdvance(it.get("Text", "")) + 16
                ir = QRect(x, mr.top(), w, MENU_H)
                p.setPen(QColor("#000000"))
                p.drawText(ir, Qt.AlignmentFlag.AlignCenter, it.get("Text", ""))
                self.menu_rects.append((ir, it))
                x += w
            if not items:
                p.setPen(QColor("#808080"))
                p.drawText(QRect(x, mr.top(), 200, MENU_H), Qt.AlignmentFlag.AlignVCenter,
                           "Type Here (double-click)")
            if doc.selected is menu:
                p.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DotLine))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(mr.adjusted(0, 0, -1, -1))
        if active:   # VB shows resize handles on the form itself when selected
            p.setPen(QColor("#000000"))
            p.setBrush(QColor("#ffffff"))
            w, h = r.width(), r.height()
            for x, y in ((w - HANDLE, h // 2), (w // 2, h - HANDLE), (w - HANDLE, h - HANDLE)):
                p.drawRect(x, y, HANDLE - 1, HANDLE - 1)


class ComponentTray(QWidget):
    """Strip under the form that shows non-visual components, as in VB 2005."""

    def __init__(self, view: "DesignerView"):
        super().__init__()
        self.view = view
        self.setAutoFillBackground(True)
        self.setStyleSheet("ComponentTray { background:#ffffff; border-top:1px solid #c0c0c0; }")
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(6, 6, 6, 6)
        self.lay.setSpacing(8)
        self.buttons: list[tuple[QToolButton, Control]] = []

    def rebuild(self):
        while self.lay.count():
            it = self.lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.buttons = []
        for c in self.view.doc.form.nonvisual():
            b = _TrayButton(self.view, c)
            self.lay.addWidget(b)
            self.buttons.append((b, c))
        self.lay.addStretch(1)
        self.setVisible(bool(self.buttons))
        self.sync()

    def sync(self):
        sel = self.view.doc.selection
        for b, c in self.buttons:
            b.setChecked(c in sel)


class _TrayButton(QToolButton):
    def __init__(self, view: "DesignerView", ctrl: Control):
        super().__init__()
        self.view, self.ctrl = view, ctrl
        self.setText(ctrl.name)
        self.setIcon(control_icon(ctrl.type))
        self.setIconSize(QSize(18, 18))
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setAutoRaise(True)

    def mousePressEvent(self, e):
        add = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self.view.doc.select(self.ctrl, add=add)
        self.view.overlay.setFocus()
        if e.button() == Qt.MouseButton.RightButton:
            self.view.show_context_menu(self.ctrl, e.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, _e):
        if self.ctrl.type == "MenuStrip":
            self.view.edit_menu(self.ctrl)
        else:
            ev = self.ctrl.ctype.default_event
            if ev:
                self.view.doc.eventRequested.emit(self.ctrl, ev)


class DesignerView(QScrollArea):
    """Hosts one FormDocument's visual designer."""
    contextActions = pyqtSignal(object, object)   # (QMenu, Control|None) - app may add items

    def __init__(self, doc: FormDocument, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWidgetResizable(False)
        self.content = QWidget()
        self.content.setStyleSheet("background:#ffffff;")
        self.frame = FormFrame(self)
        self.frame.setParent(self.content)
        self.surface = Surface(self)
        self.overlay = Overlay(self)
        self.tray = ComponentTray(self)
        self.tray.setParent(self.content)
        self.previews: dict[int, QWidget] = {}
        self.setWidget(self.content)
        doc.structureChanged.connect(self.rebuild)
        doc.controlChanged.connect(self.on_control_changed)
        doc.selectionChanged.connect(self._on_selection)
        TOOL_STATE.changed.connect(lambda _t: self.overlay.unsetCursor())
        self.rebuild()

    # ------------------------------------------------------------ layout
    def layout_form(self) -> None:
        fp = self.doc.form.props
        w, h = int(fp["Width"]), int(fp["Height"])
        mh = self.frame.menu_height()
        fw, fh = w + 2 * BORDER, h + CAPTION + mh + 2 * BORDER
        self.frame.setGeometry(MARGIN, MARGIN, fw, fh)
        self.surface.setGeometry(BORDER, BORDER + CAPTION + mh, w, h)
        self.overlay.setGeometry(0, 0, w, h)
        tray_h = 40 if self.tray.isVisibleTo(self.content) else 0
        total_w = max(fw + 2 * MARGIN, self.viewport().width())
        self.tray.setGeometry(0, fh + 2 * MARGIN, total_w, tray_h)
        self.content.resize(total_w, fh + 2 * MARGIN + tray_h + 4)
        self.frame.update()
        self.surface.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.layout_form()

    def rebuild(self) -> None:
        for w in self.previews.values():
            w.setParent(None)
            w.deleteLater()
        self.previews.clear()
        for c in self.doc.form.ordered():
            parent = self.previews.get(id(self.doc.form.find(c.parent))) if c.parent else None
            self.previews[id(c)] = make_preview(c, parent or self.surface, self.doc.path.parent)
        self.overlay.raise_()
        self.tray.rebuild()
        self.layout_form()
        self.overlay.update()

    def on_control_changed(self, ctrl) -> None:
        if ctrl is None or ctrl.type == "MenuStrip":
            self.layout_form()
        elif id(ctrl) in self.previews:
            apply_props(self.previews[id(ctrl)], ctrl)
        self.overlay.update()

    def _on_selection(self, _c):
        self.overlay.update()
        self.frame.update()
        self.tray.sync()

    # ------------------------------------------------------------ actions
    def create_control(self, type_name: str, pos: QPoint) -> None:
        ctype = CONTROL_TYPES[type_name]
        if type_name == "MenuStrip" and self.doc.form.menu():
            self.doc.select(self.doc.form.menu())
            return
        parent = "" if ctype.nonvisual else self.overlay.container_at(pos, [])
        px, py = (self.doc.form.abs_pos(self.doc.form.find(parent)) if parent else (0, 0))
        ctrl = self.doc.add_control(type_name, snap(pos.x() - px), snap(pos.y() - py), parent)
        self.overlay.setFocus()
        if type_name == "MenuStrip":
            self.edit_menu(ctrl)

    def edit_menu(self, ctrl: Control) -> None:
        from .menu_editor import edit_menu
        taken = {c.name for c in self.doc.form.controls} | {self.doc.form.name}
        items = edit_menu(ctrl.props.get("Items", []), taken, self)
        if items is not None:
            self.doc.set_prop(ctrl, "Items", items)

    def popup_menu_item(self, item: dict, at: QPoint) -> None:
        """Click on a top-level menu in the designer: show its items; picking
        one jumps to its Click handler (like VB)."""
        menu_ctrl = self.doc.form.menu()

        def build(qmenu: QMenu, items: list):
            for it in items:
                if it.get("Text") == "-":
                    qmenu.addSeparator()
                elif it.get("Items"):
                    build(qmenu.addMenu(it["Text"]), it["Items"])
                else:
                    a = qmenu.addAction(it.get("Text", ""))
                    a.triggered.connect(lambda _=False, n=it["Name"]:
                                        self.doc.eventRequested.emit(menu_ctrl, n))
        m = QMenu(self)
        if item.get("Items"):
            build(m, item["Items"])
        else:
            a = m.addAction(f"{item.get('Text')}  -> Click handler")
            a.triggered.connect(lambda: self.doc.eventRequested.emit(menu_ctrl, item["Name"]))
        m.addSeparator()
        m.addAction("Edit Menu...", lambda: self.edit_menu(menu_ctrl))
        m.exec(at)

    def show_context_menu(self, c: Control | None, at: QPoint) -> None:
        if c is not None and c not in self.doc.selection:
            self.doc.select(c)
        m = QMenu(self)
        m.addAction("View Code", lambda: self.doc.eventRequested.emit(None, ""))
        if c is not None:
            if c.type == "MenuStrip":
                m.addAction("Edit Menu...", lambda: self.edit_menu(c))
            if not c.ctype.nonvisual:
                m.addSeparator()
                m.addAction("Bring to Front", lambda: self.doc.reorder(c, True))
                m.addAction("Send to Back", lambda: self.doc.reorder(c, False))
        m.addSeparator()
        m.addAction("Cut", self.doc.cut).setEnabled(bool(self.doc.selection))
        m.addAction("Copy", self.doc.copy).setEnabled(bool(self.doc.selection))
        m.addAction("Paste", self.doc.paste).setEnabled(self.doc.can_paste())
        m.addAction("Delete", lambda: self.doc.remove_controls(list(self.doc.selection))) \
            .setEnabled(bool(self.doc.selection))
        self.contextActions.emit(m, c)
        m.exec(at)
