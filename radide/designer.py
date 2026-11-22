"""VB-style form designer.

A fake XP window with a grid surface; selection handles, multi-select
(Ctrl+click / rubber band), move/resize with snap-to-grid, containers
(Panel/GroupBox), a menu strip and a component tray for non-visual
components (Timer, MenuStrip, dialogs). TabControl pages are switched by
clicking their tabs; docked controls snap to the container edges and anchored
ones follow when the form is resized; Lock Controls and a Tab Order mode
(click controls in sequence to number them) are available."""
from __future__ import annotations

from PyQt6.QtCore import QLine, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QHBoxLayout, QMenu, QScrollArea, QToolButton, QWidget)

from .controls import CONTROL_TYPES, MENU_TYPES, TOOLSTRIP_H
from .document import PASTE_STEP, FormDocument, is_docked
from .layout import tab_page
from .mobile.frame import PhoneChrome
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
SNAP_DIST = 4              # snaplines: an edge this close to another control's edge sticks to it
SNAPLINE = "#0064FF"       # VS draws edge snaplines blue


def design_visible(form, c: Control) -> bool:
    """False for controls on a TabControl page that is not the selected one (or inside one)."""
    seen = set()
    while c is not None and c.parent and c.name not in seen:
        seen.add(c.name)
        parent = form.find(c.parent)
        if parent is None:
            return True
        if parent.type == "TabControl" and tab_page(c) != int(parent.props.get("SelectedIndex", 0) or 0):
            return False
        c = parent
    return True


def toolstrip_of(form) -> Control | None:
    return next((c for c in form.controls if c.type == "ToolStrip"), None)

# handle index -> (moves left, moves top, moves right, moves bottom)
HANDLE_EDGES = [(1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0), (0, 0, 1, 0),
                (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1), (1, 0, 0, 0)]
HANDLE_CURSORS = [Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeVerCursor,
                  Qt.CursorShape.SizeBDiagCursor, Qt.CursorShape.SizeHorCursor] * 2


def snap(v: int) -> int:
    return int(round(v / GRID) * GRID)


def next_grid(v: int, direction: int) -> int:
    """The next grid line after *v* going right / down (direction > 0) or left / up (< 0)."""
    return (v // GRID + 1) * GRID if direction > 0 else ((v - 1) // GRID) * GRID


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
        if self.view.phone.paint_surface(p, self):          # phone form (radide/mobile/frame.py)
            return
        back = self.view.form_props().get("BackColor") or FORM_BACK
        p.fillRect(self.rect(), QColor(back))
        # the grid dots: one GRIDxGRID tile repeated (a drawPoint per dot cost ~4 ms per repaint)
        tile = getattr(self, "_grid_tile", None)
        if tile is None:
            tile = QPixmap(GRID, GRID)
            tile.fill(Qt.GlobalColor.transparent)
            tp = QPainter(tile)
            tp.setPen(QColor(0, 0, 0, 140))
            tp.drawPoint(0, 0)
            tp.end()
            self._grid_tile = tile
        p.drawTiledPixmap(self.rect(), tile)


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
        self.start_abs: dict[int, QRect] = {}   # form coordinates of the dragged controls at the press
        self.snaplines: list[QLine] = []        # shown while a drag sticks to another control's edge
        self.create_tool = None                 # click-drag with a Toolbox tool draws the new control

    def _on_tool_changed(self, _tool=None):
        self.unsetCursor()

    # ---------------------------------------------------------------- helpers
    @property
    def form(self):
        return self.doc.form

    def abs_rect(self, c: Control) -> QRect:
        """Where c is drawn - the previewed visual state / timeline geometry when one is shown."""
        dp = self.view.design_props
        p = dp(c)
        x, y = int(p["Left"]), int(p["Top"])
        seen = set()
        parent = self.form.find(c.parent) if c.parent else None
        while parent is not None and parent.name not in seen:
            seen.add(parent.name)
            pp = dp(parent)
            ox, oy = self.form.client_offset(parent)
            x += int(pp["Left"]) + ox
            y += int(pp["Top"]) + oy
            parent = self.form.find(parent.parent) if parent.parent else None
        return QRect(x, y, int(p["Width"]), int(p["Height"]))

    def start_rect(self, c: Control) -> QRect:
        """Geometry a move / resize starts from (what the designer shows for c)."""
        p = self.view.design_props(c)
        return QRect(int(p["Left"]), int(p["Top"]), int(p["Width"]), int(p["Height"]))

    def shown(self) -> list[Control]:
        """Visual controls the designer currently shows (z-order, containers first)."""
        return [c for c in self.form.ordered() if design_visible(self.form, c)]

    def control_at(self, pos: QPoint) -> Control | None:
        for c in reversed(self.shown()):
            if self.abs_rect(c).contains(pos):
                return c
        return None

    def container_at(self, pos: QPoint, exclude: list[Control]) -> str:
        banned = set()
        for c in exclude:
            banned.add(id(c))
            banned |= {id(d) for d in self.form.descendants(c)}
        for c in reversed(self.shown()):
            if c.ctype.container and id(c) not in banned and self.abs_rect(c).contains(pos):
                return c.name
        return ""

    def handle_at(self, pos: QPoint) -> int:
        c = self.doc.selected
        if c is None or c.ctype.nonvisual or self.doc.locked or self.view.tab_order_mode:
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
            self.view.begin_live()      # the drag's steps update geometry only; the rest on release

    # ------------------------------------------------------------------ snaplines
    def _snap_targets(self, ref: Control, moving: list[Control]) -> list[QRect]:
        """Rectangles (form coordinates) a drag of *moving* may line up with: the other controls of
        ref's container and the container's client area (Visual Studio's snaplines)."""
        banned = set()
        for c in moving:
            banned.add(id(c))
            banned |= {id(d) for d in self.form.descendants(c)}
        out = [self.abs_rect(c) for c in self.shown() if c.parent == ref.parent and id(c) not in banned]
        parent = self.form.find(ref.parent) if ref.parent else None
        if parent is None:
            fp = self.view.form_props()
            out.append(QRect(0, 0, int(fp["Width"]), int(fp["Height"])))
        else:
            from .layout import client_size
            ox, oy = self.form.client_origin(parent)
            cw, ch = client_size(self.form, parent)
            out.append(QRect(ox, oy, cw, ch))
        return out

    @staticmethod
    def _best_edge(edges: list[int], targets: list[int]):
        """(offset, target) of the closest edge / target pair within SNAP_DIST, else None."""
        best = None
        for e in edges:
            for t in targets:
                d = t - e
                if abs(d) <= SNAP_DIST and (best is None or abs(d) < abs(best[0])):
                    best = (d, t)
        return best

    def _snap_lines(self, box: QRect, others: list[QRect], xs: list[int], ys: list[int]) -> list[QLine]:
        lines = []
        for x in xs:
            hits = [r for r in others if x in (r.left(), r.left() + r.width())] + [box]
            lines.append(QLine(x, min(r.top() for r in hits), x, max(r.top() + r.height() for r in hits)))
        for y in ys:
            hits = [r for r in others if y in (r.top(), r.top() + r.height())] + [box]
            lines.append(QLine(min(r.left() for r in hits), y, max(r.left() + r.width() for r in hits), y))
        return lines

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, e):
        self.setFocus()
        self.view.end_live()            # a drag whose release never arrived
        pos = e.position().toPoint()
        mods = e.modifiers()
        # VS: Ctrl+click and Shift+click add a control to the selection / take it out again
        ctrl_key = bool(mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier))
        self.recorded = False
        self.snaplines = []
        if e.button() != Qt.MouseButton.LeftButton:
            hit = self.control_at(pos)
            if hit not in self.doc.selection:
                self.doc.select(hit)
            return
        if TOOL_STATE.current:
            tool = TOOL_STATE.current
            ctype = CONTROL_TYPES.get(tool)
            if ctype is None or ctype.nonvisual or tool in MENU_TYPES or self.view.phone.active:
                self.view.create_control(tool, pos)
                TOOL_STATE.set(None)
                return
            # VS: click = default size at the point, click-drag = draw the control's rectangle
            self.mode = "create"
            self.create_tool = tool
            self.press = pos
            self.band = QRect(pos, pos)
            return
        if self.view.tab_order_mode:
            hit = self.control_at(pos)
            if hit is not None:
                self.view.assign_tab_index(hit, restart=bool(mods & Qt.KeyboardModifier.ControlModifier))
            self.mode = None
            return
        self.press = pos
        hit = self.control_at(pos)
        if hit is not None and hit.type == "TabControl" and self._click_tab(hit, pos):
            self.mode = None
            return
        self.handle = self.handle_at(pos) if not ctrl_key else -1
        if self.handle >= 0:
            self.mode = "resize"
            c = self.doc.selected
            self.view.blend_begin_edit()    # Record off: the edit is on the designed form, not the timeline
            group = [x for x in self._movable() if not is_docked(x)]
            if c not in group:
                group.append(c)
            self.starts = {id(x): self.start_rect(x) for x in group}      # VS: every selected control resizes
            self.start_abs = {id(x): self.abs_rect(x) for x in group}
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
        if self.doc.locked:
            self.mode = None
            return
        self.mode = "move"
        self.view.blend_begin_edit()        # Record off: the edit is on the designed form, not the timeline
        self.starts = {id(c): self.start_rect(c) for c in self._movable()}
        self.start_abs = {id(c): self.abs_rect(c) for c in self._movable()}
        self.view.phone.begin_drag(self._movable())     # children of a Column / Row follow the mouse

    def _click_tab(self, tc: Control, pos: QPoint) -> bool:
        """A click on the tab bar of a TabControl shows that page (VS behaviour)."""
        w = self.view.previews.get(id(tc))
        if w is None or not hasattr(w, "tab_at"):
            return False
        r = self.abs_rect(tc)
        idx = w.tab_at(pos - r.topLeft())
        if idx < 0:
            return False
        self.doc.select(tc)
        if idx != int(tc.props.get("SelectedIndex", 0) or 0):
            self.doc.set_prop(tc, "SelectedIndex", idx, record=False)
        return True

    def _move_delta(self, movable: list[Control], dx: int, dy: int, free: bool) -> tuple[int, int]:
        """How far the dragged group moves: the PRIMARY control goes to the grid (or sticks to another
        control's edge - a snapline - when one is within SNAP_DIST); the others keep their distance to it.
        Alt (free) = no snapping at all, as in Visual Studio."""
        self.snaplines = []
        if free:
            return dx, dy
        prim = self.doc.selected if self.doc.selected in movable else movable[0]
        s = self.starts[id(prim)]
        ddx, ddy = snap(s.x() + dx) - s.x(), snap(s.y() + dy) - s.y()
        if self.view.phone.active:
            return ddx, ddy
        boxes = [self.start_abs[id(c)] for c in movable if id(c) in self.start_abs]
        if not boxes:
            return ddx, ddy
        box = boxes[0]
        for b in boxes[1:]:
            box = box.united(b)
        others = self._snap_targets(prim, movable)
        bx = self._best_edge([box.left() + dx, box.left() + box.width() + dx],
                             [v for r in others for v in (r.left(), r.left() + r.width())])
        by = self._best_edge([box.top() + dy, box.top() + box.height() + dy],
                             [v for r in others for v in (r.top(), r.top() + r.height())])
        xs, ys = [], []
        if bx is not None:
            ddx = dx + bx[0]
            xs.append(bx[1])
        if by is not None:
            ddy = dy + by[0]
            ys.append(by[1])
        if xs or ys:
            self.snaplines = self._snap_lines(box.translated(ddx, ddy), others, xs, ys)
        return ddx, ddy

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        dx, dy = pos.x() - self.press.x(), pos.y() - self.press.y()
        free = bool(e.modifiers() & Qt.KeyboardModifier.AltModifier)
        if self.mode in ("band", "create"):
            self.band = QRect(self.press, pos).normalized()
            self.update()
            return
        if self.mode == "move":
            if abs(dx) < 2 and abs(dy) < 2 and not self.recorded:
                return
            movable = [c for c in self._movable() if id(c) in self.starts]
            if not movable:
                return
            self._record()
            ddx, ddy = self._move_delta(movable, dx, dy, free)
            for c in movable:     # size: the base value (a previewed state / keyframe size stays as is)
                s = self.starts[id(c)]
                gb = self.view.geometry_base(c)
                self.doc.set_geometry(c, s.x() + ddx, s.y() + ddy, int(gb["Width"]), int(gb["Height"]),
                                      relayout=False)
            self.doc.relayout_docked()   # docked controls snap once per step, not once per moved control
            self.update()
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
            sa = self.start_abs.get(id(c), QRect(s))
            ox, oy = sa.x() - s.x(), sa.y() - s.y()          # local -> form coordinates
            others = [] if (free or self.view.phone.active) else self._snap_targets(c, [c])
            txs = [v for r in others for v in (r.left(), r.left() + r.width())]
            tys = [v for r in others for v in (r.top(), r.top() + r.height())]
            xs, ys = [], []

            def edge(v, off, targets, lines):
                if free:
                    return v
                hit = self._best_edge([v + off], targets)
                if hit is not None:
                    lines.append(hit[1])
                    return hit[1] - off
                return snap(v)
            if ml: left = min(edge(left + dx, ox, txs, xs), right - MIN_SIZE)
            if mt: top = min(edge(top + dy, oy, tys, ys), bottom - MIN_SIZE)
            if mr: right = max(edge(right + dx, ox, txs, xs), left + MIN_SIZE)
            if mb: bottom = max(edge(bottom + dy, oy, tys, ys), top + MIN_SIZE)
            new = (left, top, right - left, bottom - top)
            old = (s.left(), s.top(), s.width(), s.height())
            self.snaplines = self._snap_lines(QRect(left + ox, top + oy, right - left, bottom - top),
                                              others, xs, ys) if (xs or ys) else []
            gb = self.view.geometry_base(c)
            base = [int(gb[k]) for k in ("Left", "Top", "Width", "Height")]
            # edges the gesture did not move keep their base value (matters while previewing a state)
            self.doc.set_geometry(c, *[n if n != o else b for n, o, b in zip(new, old, base)])
            # VS: the other selected controls change their edges by the same amounts
            dl, dt = left - s.left(), top - s.top()
            dr, db = right - (s.left() + s.width()), bottom - (s.top() + s.height())
            for o in self._movable():
                so = self.starts.get(id(o))
                if o is c or so is None:
                    continue
                w = max(MIN_SIZE, so.width() + dr - dl)
                h = max(MIN_SIZE, so.height() + db - dt)
                self.doc.set_geometry(o, so.left() + dl, so.top() + dt, w, h, relayout=False)
            self.doc.relayout_docked()
            self.update()
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
        self.snaplines = []
        self.view.end_live()            # ONE controlChanged per dragged control (Properties, previews ...)
        pos = e.position().toPoint()
        if mode == "create":
            band, self.band = self.band, QRect()
            tool, self.create_tool = self.create_tool, None
            TOOL_STATE.set(None)
            if tool:
                if band.width() >= 4 and band.height() >= 4:
                    self.view.create_control(tool, band.topLeft(), band.size())
                else:
                    self.view.create_control(tool, self.press)
            self.update()
            return
        if mode == "band":
            band = self.band
            self.band = QRect()
            if band.width() > 2 or band.height() > 2:
                # VS: the band selects the controls of the container it was drawn on (here: the form)
                hits = [c for c in self.shown() if not c.parent and self.abs_rect(c).intersects(band)]
                mods = e.modifiers()
                if mods & Qt.KeyboardModifier.ControlModifier:          # Ctrl: toggle
                    sel = list(self.doc.selection)
                    for c in hits:
                        sel.remove(c) if c in sel else sel.append(c)
                    hits = sel
                elif mods & Qt.KeyboardModifier.ShiftModifier:          # Shift: add
                    hits = self.doc.selection + [c for c in hits if c not in self.doc.selection]
                self.doc.select_many(hits)
            self.update()
        elif mode == "move" and self.recorded and not self.view.blend_recording() and not self._variant_shown():
            moved = self._movable()
            # VS: the controls go into the container under the mouse pointer (or out to the form)
            target = self.container_at(pos, moved)
            for c in moved:
                self.doc.reparent(c, target)
            self.update()
        if mode == "move":           # dropped inside a Column / Row: take that place in the order
            self.view.phone.end_drag(self._movable() if self.recorded and not self.view.blend_recording()
                                     and not self._variant_shown() else [])
        if mode in ("move", "resize") and self.recorded:
            self.doc.drop_noop()         # a drag that ended where it started is no undo step
        self.update()

    def _variant_shown(self) -> bool:
        """A layout size is shown: a drag moves the control on that size, never into another container."""
        vp = getattr(self.view, "_variant_preview", None)
        return bool(vp is not None and vp.active)

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
    def tab_cycle(self) -> list[Control]:
        """What Tab / Shift+Tab step through: the shown controls, then the component tray."""
        return self.shown() + self.form.nonvisual()

    def focusNextPrevChild(self, nxt: bool) -> bool:
        """VS: Tab selects the next control of the form, Shift+Tab the previous one (focus stays here)."""
        if self.view.tab_order_mode or self.mode is not None:
            return True
        items = self.tab_cycle()
        if not items:
            return True
        cur = self.doc.selected
        i = items.index(cur) if cur in items else -1
        j = (i + 1) % len(items) if nxt else ((i - 1) % len(items) if i >= 0 else len(items) - 1)
        self.doc.select(items[j])
        return True

    def cancel_drag(self) -> bool:
        """Esc during a mouse gesture: the drag is undone (VS); returns True when there was one."""
        mode, self.mode = self.mode, None
        if mode is None:
            return False
        self.snaplines = []
        self.band = QRect()
        if mode == "create":
            self.create_tool = None
            TOOL_STATE.set(None)
        if mode in ("move", "resize") and self.recorded:
            self.view.end_live()
            self.doc.cancel_gesture()
            self.view.phone.end_drag([])
        self.recorded = False
        self.update()
        return True

    def _key_delta(self, prim: Control, movable: list[Control], step: tuple[int, int], resize: bool) -> tuple[int, int]:
        """Ctrl+arrow: to the next grid line or the next edge of another control, whichever is nearer
        (Ctrl+Shift+arrow: the same for the right / bottom edge)."""
        r = self.abs_rect(prim)
        others = [] if self.view.phone.active else self._snap_targets(prim, movable)
        out = []
        for axis in (0, 1):
            d = step[axis]
            if not d:
                out.append(0)
                continue
            p = self.view.design_props(prim)
            local = int(p["Left" if axis == 0 else "Top"])
            size = int(p["Width" if axis == 0 else "Height"])
            start = r.left() if axis == 0 else r.top()
            edges = [local + size] if resize else [local, local + size]
            grid_edge = local + size if resize else local         # the Location (or the far edge) to the grid
            cands = [next_grid(grid_edge, d) - grid_edge]
            off = start - local                          # local -> form coordinates
            for o in others:
                lo, hi = (o.left(), o.left() + o.width()) if axis == 0 else (o.top(), o.top() + o.height())
                for e in edges:
                    cands += [t - (e + off) for t in (lo, hi)]
            cands = [c for c in cands if c * d > 0]
            out.append(min(cands, key=abs) if cands else d * GRID)
        return out[0], out[1]

    def keyPressEvent(self, e):
        k = e.key()
        mods = e.modifiers()
        if k == Qt.Key.Key_Escape:
            if self.cancel_drag():
                return
            if self.view.tab_order_mode:
                self.view.set_tab_order_mode(False)
                return
            if TOOL_STATE.current:
                TOOL_STATE.set(None)
                return
            # VS: Esc selects the container of the selected control (then the form)
            c = self.doc.selected
            parent = self.form.find(c.parent) if c is not None and c.parent else None
            self.doc.select(parent)
            return
        if not self.doc.selection or self.mode is not None:
            return super().keyPressEvent(e)
        if k == Qt.Key.Key_Delete:
            self.doc.remove_controls(list(self.doc.selection))
            return
        step = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0),
                Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}.get(k)
        if not step:
            return super().keyPressEvent(e)
        if self.doc.locked or self.view.tab_order_mode:
            return
        movable = [c for c in self._movable() if not is_docked(c)]
        if not movable:
            return
        prim = self.doc.selected if self.doc.selected in movable else movable[0]
        resize = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        by_grid = bool(mods & Qt.KeyboardModifier.ControlModifier)
        self.view.blend_begin_edit()
        self.doc.checkpoint()
        dx, dy = self._key_delta(prim, movable, step, resize) if by_grid else step
        # from what is shown (a previewed state / keyframe); the other two values keep their base value
        for c in movable:
            p = self.view.design_props(c)
            gb = self.view.geometry_base(c)
            if resize:          # Shift+arrow: every selected control grows / shrinks (VS)
                self.doc.set_geometry(c, int(gb["Left"]), int(gb["Top"]),
                                      max(MIN_SIZE, int(p["Width"]) + dx), max(MIN_SIZE, int(p["Height"]) + dy),
                                      relayout=False)
            else:
                self.doc.set_geometry(c, int(p["Left"]) + dx, int(p["Top"]) + dy, int(gb["Width"]),
                                      int(gb["Height"]), relayout=False)
        self.doc.relayout_docked()
        self.doc.drop_noop()

    # ------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME) or e.mimeData().hasFormat("application/x-radide-dbsource"):
            e.acceptProposedAction()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, e):
        if e.mimeData().hasFormat("application/x-radide-dbsource"):     # a table from the Data Sources window
            from .features.data_sources import drop_on_designer
            drop_on_designer(self.view, bytes(e.mimeData().data("application/x-radide-dbsource")).decode(),
                             e.position().toPoint())
            e.acceptProposedAction()
            return
        name = bytes(e.mimeData().data(MIME)).decode()
        self.view.create_control(name, e.position().toPoint())
        TOOL_STATE.set(None)
        e.acceptProposedAction()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _e):
        p = QPainter(self)
        primary = self.doc.selected
        if self.view.tab_order_mode:
            self._paint_tab_order(p)
            return
        vp = getattr(self.view, "_variant_preview", None)
        if vp is not None and vp.active:          # controls hidden on the shown layout size: hatched
            for c in self.shown():
                if vp.hidden(c):
                    self._paint_hidden(p, self.abs_rect(c))
        locked = self.doc.locked
        for c in self.doc.selection:
            if c.ctype.nonvisual or not design_visible(self.form, c):
                continue
            r = self.abs_rect(c)
            p.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r.adjusted(-1, -1, 0, 0))
            if locked:            # VS shows a small padlock instead of the grab handles
                self._paint_lock(p, r.topLeft() + QPoint(2, 2))
                continue
            p.setPen(QPen(QColor("#000000")))
            # VB: primary selection has white handles, the others black
            p.setBrush(QColor("#ffffff") if c is primary else QColor("#000000"))
            for h in handle_rects(r):
                p.drawRect(h)
        if not self.band.isNull():
            p.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.band)
        if self.snaplines:
            p.setPen(QPen(QColor(SNAPLINE), 1))
            for ln in self.snaplines:
                p.drawLine(ln)


    @staticmethod
    def _paint_hidden(p: QPainter, r: QRect) -> None:
        """Diagonal orange hatch: the control is hidden on this layout size (Hide on this size)."""
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(247, 99, 12, 30))
        p.drawRect(r)
        from PyQt6.QtGui import QBrush
        p.setBrush(QBrush(QColor(247, 99, 12, 150), Qt.BrushStyle.BDiagPattern))
        p.drawRect(r)
        p.setPen(QPen(QColor("#F7630C"), 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(r.adjusted(0, 0, -1, -1))
        p.restore()

    @staticmethod
    def _paint_lock(p: QPainter, at: QPoint) -> None:
        p.save()
        p.setPen(QPen(QColor("#404040"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(at.x() + 2, at.y(), 6, 7, 0, 180 * 16)
        p.setBrush(QColor("#F0C419"))
        p.drawRect(at.x() + 1, at.y() + 4, 8, 6)
        p.restore()

    def tab_label(self, c: Control) -> str:
        """'2' for a control on the form, '1.0' for the first control of container 1 ..."""
        parts = []
        seen = set()
        while c is not None and c.name not in seen:
            seen.add(c.name)
            parts.insert(0, str(int(c.props.get("TabIndex", 0) or 0)))
            c = self.form.find(c.parent) if c.parent else None
        return ".".join(parts)

    def _paint_tab_order(self, p: QPainter) -> None:
        f = QFont("Segoe UI", 8, QFont.Weight.Bold)
        p.setFont(f)
        fm = QFontMetrics(f)
        done = self.view.tab_assigned
        for c in self.shown():
            text = self.tab_label(c)
            r = self.abs_rect(c)
            box = QRect(r.left(), r.top(), fm.horizontalAdvance(text) + 8, fm.height() + 2)
            p.setPen(QColor("#000000"))
            p.setBrush(QColor("#FFFFFF") if id(c) in done else QColor("#1E5FBF"))
            p.drawRect(box)
            p.setPen(QColor("#1E5FBF") if id(c) in done else QColor("#FFFFFF"))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)


class FormFrame(QWidget):
    """Paints a Windows-XP style window (caption + optional menu strip) around
    the design surface and lets the user resize the form from its edges."""

    def __init__(self, view: "DesignerView"):
        super().__init__()
        self.view = view
        self.setMouseTracking(True)
        self._resizing = None
        self._recorded = False
        self._press = QPoint()
        self._start = (0, 0)
        self.menu_rects: list[tuple[QRect, dict]] = []
        self.tool_rects: list[tuple[QRect, dict]] = []

    def menu_height(self) -> int:
        """Height of the menu strip + tool strip drawn above the client area."""
        if self.view.phone.active:
            return 0
        form = self.view.doc.form
        return (MENU_H if form.menu() else 0) + (TOOLSTRIP_H if toolstrip_of(form) else 0)

    def _strip_top(self) -> int:
        return BORDER + CAPTION + (MENU_H if self.view.doc.form.menu() else 0)

    def _in_strip(self, pos: QPoint) -> bool:
        if toolstrip_of(self.view.doc.form) is None:
            return False
        top = self._strip_top()
        return top <= pos.y() < top + TOOLSTRIP_H

    def _tool_hit(self, pos: QPoint):
        for r, item in self.tool_rects:
            if r.contains(pos):
                return item
        return None

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
        if self.view.phone.active:          # a phone has no menu strip and is not resized by its edges
            doc.select(None)
            return
        menu = doc.form.menu()
        hit = self._menu_hit(pos)
        if menu is not None and hit:
            doc.select(menu)
            self.view.popup_menu_item(hit[1], self.mapToGlobal(hit[0].bottomLeft()))
            return
        if menu is not None and BORDER + CAPTION <= pos.y() < BORDER + CAPTION + MENU_H:
            doc.select(menu)
            return
        if self._in_strip(pos):
            doc.select(toolstrip_of(doc.form))
            return
        doc.select(None)
        self._resizing = self._edge(pos)
        self._press = pos
        fp = self.view.form_props()
        self._start = (int(fp["Width"]), int(fp["Height"]))
        self._recorded = False

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        if self.view.phone.active:
            return
        if self._resizing:
            dx, dy = pos.x() - self._press.x(), pos.y() - self._press.y()
            doc = self.view.doc
            fp = self.view.geometry_base(None)  # what set_prop compares with (a layout size's own size)
            w = max(80, snap(self._start[0] + dx)) if self._resizing[0] else None
            h = max(60, snap(self._start[1] + dy)) if self._resizing[1] else None
            if (w is None or w == fp.get("Width")) and (h is None or h == fp.get("Height")):
                return                          # still on the same grid step: nothing to do
            if not self._recorded:              # ONE undo step for the whole drag, on its first change
                doc.checkpoint()
                self._recorded = True
                self.view.begin_live()          # steps: frame + anchored children only; the rest on release
            # set_prop moves / resizes anchored and docked controls with the form
            if w is not None:
                doc.set_prop(None, "Width", w, record=False)
            if h is not None:
                doc.set_prop(None, "Height", h, record=False)
            return
        edge = self._edge(pos)
        cursors = {(True, True): Qt.CursorShape.SizeFDiagCursor,
                   (True, False): Qt.CursorShape.SizeHorCursor,
                   (False, True): Qt.CursorShape.SizeVerCursor}
        self.setCursor(cursors[edge]) if edge else self.unsetCursor()

    def mouseReleaseEvent(self, _e):
        self._resizing = None
        self.view.end_live()                    # one controlChanged(None) + anchored children

    def mouseDoubleClickEvent(self, e):
        pos = e.position().toPoint()
        menu = self.view.doc.form.menu()
        if menu is not None and BORDER + CAPTION <= pos.y() < BORDER + CAPTION + MENU_H:
            self.view.edit_menu(menu)
            return
        if self._in_strip(pos):
            strip = toolstrip_of(self.view.doc.form)
            item = self._tool_hit(pos)
            if item is not None and item.get("Name"):
                self.view.doc.eventRequested.emit(strip, item["Name"])
            else:
                self.view.edit_menu(strip)
            return
        self.view.doc.eventRequested.emit(None, "Load")

    def contextMenuEvent(self, e):
        self.view.show_context_menu(None, e.globalPos())

    def paintEvent(self, _e):
        p = QPainter(self)
        if self.view.phone.paint(p, self):          # phone / tablet frame (radide/mobile/frame.py)
            return
        from .usercontrols import paint_frame
        if paint_frame(self, p):                    # a user control: no window caption
            return
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
                   str(self.view.form_props().get("Text", "")))
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
        self._paint_toolstrip(p, r)
        if active:   # VB shows resize handles on the form itself when selected
            p.setPen(QColor("#000000"))
            p.setBrush(QColor("#ffffff"))
            w, h = r.width(), r.height()
            for x, y in ((w - HANDLE, h // 2), (w // 2, h - HANDLE), (w - HANDLE, h - HANDLE)):
                p.drawRect(x, y, HANDLE - 1, HANDLE - 1)


    def _paint_toolstrip(self, p: QPainter, r: QRect) -> None:
        self.tool_rects = []
        doc = self.view.doc
        strip = toolstrip_of(doc.form)
        if strip is None:
            return
        tr = QRect(BORDER, self._strip_top(), r.width() - 2 * BORDER, TOOLSTRIP_H)
        g = QLinearGradient(0, tr.top(), 0, tr.bottom())
        g.setColorAt(0, QColor("#FAFAFA"))
        g.setColorAt(1, QColor("#E3E3E3"))
        p.fillRect(tr, g)
        p.setPen(QColor("#B8B8B8"))
        p.drawLine(tr.left(), tr.bottom(), tr.right(), tr.bottom())
        f = QFont("Segoe UI", 9)
        p.setFont(f)
        fm = QFontMetrics(f)
        x = tr.left() + 4
        items = strip.props.get("Items", [])
        for it in items:
            if it.get("Text") == "-":
                p.setPen(QColor("#A0A0A0"))
                p.drawLine(x + 2, tr.top() + 4, x + 2, tr.bottom() - 4)
                x += 6
                continue
            text = it.get("Text", "") + (" \u25be" if it.get("Items") else "")
            w = fm.horizontalAdvance(text) + 14
            br = QRect(x, tr.top() + 2, w, TOOLSTRIP_H - 5)
            p.setPen(QColor("#C9C9C9"))
            p.setBrush(QColor("#F4F4F4"))
            p.drawRoundedRect(br, 2, 2)
            p.setPen(QColor("#000000"))
            p.drawText(br, Qt.AlignmentFlag.AlignCenter, text)
            self.tool_rects.append((br, it))
            x += w + 2
        if not items:
            p.setPen(QColor("#808080"))
            p.drawText(QRect(x, tr.top(), 260, TOOLSTRIP_H), Qt.AlignmentFlag.AlignVCenter,
                       "Tool strip - double-click to add buttons")
        if doc.selected is strip:
            p.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(tr.adjusted(0, 0, -1, -1))


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
        if self.ctrl.type in MENU_TYPES:
            self.view.edit_menu(self.ctrl)
        else:
            ev = self.ctrl.ctype.default_event
            if ev:
                self.view.doc.eventRequested.emit(self.ctrl, ev)


class DesignerView(QScrollArea):
    """Hosts one FormDocument's visual designer."""
    contextActions = pyqtSignal(object, object)   # (QMenu, Control|None) - app may add items
    tabOrderModeChanged = pyqtSignal(bool)

    def __init__(self, doc: FormDocument, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.tab_order_mode = False
        self.tab_next: dict[str, int] = {}          # container name -> next TabIndex to give
        self.tab_assigned: set[int] = set()         # ids of controls numbered in this session
        self._tab_recorded = False
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
        self.phone = PhoneChrome(self)             # mobile forms: phone frame + device bar
        self.setWidget(self.content)
        self.zoom = 1.0                            # designer zoom (radide/designer_zoom.py)
        self._zoom_host = None
        doc.structureChanged.connect(self.rebuild)
        doc.controlChanged.connect(self.on_control_changed)
        doc.liveChanged.connect(self.on_live_changed)
        doc.selectionChanged.connect(self._on_selection)
        # bound method of a QObject: PyQt disconnects it when the overlay is deleted (a lambda
        # would outlive a closed designer and raise "wrapped C/C++ object deleted" -> abort)
        TOOL_STATE.changed.connect(self.overlay._on_tool_changed)
        self.rebuild()

    # ------------------------------------------------------------ Blend preview hooks
    def design_props(self, c: Control) -> dict:
        """c's properties as previewed (selected visual state / timeline position), else c.props."""
        lp = getattr(self, "_loc_preview", None)          # a mirrored (RightToLeftLayout) language
        if lp is not None and lp.mirrored:
            return lp.design_props(c)
        vp = getattr(self, "_variant_preview", None)      # a layout size is shown (radide/features/variants.py)
        if vp is not None and vp.active:
            return self._blend_over(c, vp.design_props(c))
        bp = getattr(self, "_blend_preview", None)
        if bp is not None:
            try:
                return bp.design_props(c)
            except (TypeError, ValueError, KeyError, AttributeError):
                pass
        return c.props

    def form_props(self) -> dict:
        """The form's properties as previewed (a custom state's Text / BackColor / size ...)."""
        lp = getattr(self, "_loc_preview", None)          # the Language being edited (its Text)
        if lp is not None and lp.code:
            return lp.form_props()
        vp = getattr(self, "_variant_preview", None)      # a layout size is shown: its client area
        if vp is not None and vp.active:
            return self._blend_over(None, vp.design_props(None))
        bp = getattr(self, "_blend_preview", None)
        if bp is not None:
            try:
                return bp.design_props(None)
            except (TypeError, ValueError, KeyError, AttributeError):
                pass
        return self.doc.form.props

    def _blend_over(self, c, props: dict) -> dict:
        """*props* (a layout size's values) with a previewed visual state / timeline position on top."""
        bp = getattr(self, "_blend_preview", None)
        if bp is None or not (bp.state or bp.timeline is not None):
            return props
        try:
            shown = bp.design_props(c)
        except (TypeError, ValueError, KeyError, AttributeError):
            return props
        base = c.props if c is not None else self.doc.form.props
        diff = {k: v for k, v in shown.items() if base.get(k) != v}
        if not diff:
            return props
        out = dict(props)
        out.update(diff)
        return out

    def geometry_base(self, c: Control) -> dict:
        """The values a move / resize keeps for the edges it does not change: c.props, or what a layout
        size shows for c (Edit: This size only / a previewed size)."""
        vp = getattr(self, "_variant_preview", None)
        if vp is not None and vp.active:
            return vp.design_props(c)
        return c.props if c is not None else self.doc.form.props

    def blend_begin_edit(self) -> None:
        """A move / resize of the designed form starts: with timeline Record off a scrubbed timeline
        preview is dropped first (the edit changes the base values, and the control must follow the mouse)."""
        bp = getattr(self, "_blend_preview", None)
        if bp is None or bp.timeline is None or self.blend_recording():
            return
        release = getattr(bp, "timeline_release", None)
        if callable(release):
            release()

    def blend_recording(self) -> bool:
        """True while edits are recorded into a visual state or as timeline keyframes."""
        bp = getattr(self, "_blend_preview", None)
        return bool(bp is not None and (bp.recording or bp.key_recorder is not None))

    # ------------------------------------------------------------ layout
    def layout_form(self) -> None:
        if self.phone.layout():
            self.zoom_fit()
            return
        fp = self.form_props()
        w, h = int(fp["Width"]), int(fp["Height"])
        mh = self.frame.menu_height()
        fw, fh = w + 2 * BORDER, h + CAPTION + mh + 2 * BORDER
        self.frame.setGeometry(MARGIN, MARGIN, fw, fh)
        self.surface.setGeometry(BORDER, BORDER + CAPTION + mh, w, h)
        self.overlay.setGeometry(0, 0, w, h)
        tray_h = 40 if self.tray.isVisibleTo(self.content) else 0
        total_w = max(fw + 2 * MARGIN, int(self.viewport().width() / max(0.25, getattr(self, "zoom", 1.0))))
        self.tray.setGeometry(0, fh + 2 * MARGIN, total_w, tray_h)
        self.content.resize(total_w, fh + 2 * MARGIN + tray_h + 4)
        self.frame.update()
        self.surface.update()
        self.zoom_fit()

    # ------------------------------------------------------------ zoom (Ctrl+wheel, 25% - 400%)
    def set_zoom(self, factor: float) -> None:
        from .designer_zoom import set_zoom
        set_zoom(self, factor)

    def zoom_fit(self) -> None:
        if getattr(self, "_zoom_host", None) is not None:
            self._zoom_host.fit()

    def wheelEvent(self, e):
        from .designer_zoom import wheel
        if not wheel(self, e):
            super().wheelEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.layout_form()

    def showEvent(self, e):
        super().showEvent(e)
        self.phone.announce()       # the Toolbox shows the Mobile group for phone forms

    def rebuild(self) -> None:
        self.phone.refresh()
        for w in self.previews.values():
            w.setParent(None)
            w.deleteLater()
        self.previews.clear()
        for c in self.doc.form.ordered():
            parent = self.previews.get(id(self.doc.form.find(c.parent))) if c.parent else None
            host = getattr(parent, "client", parent) if parent is not None else self.surface
            self.previews[id(c)] = make_preview(c, host, self.doc.path.parent)
        self.sync_pages()
        self.overlay.raise_()
        self.tray.rebuild()
        self.layout_form()
        self.overlay.update()

    def sync_pages(self) -> None:
        """Show only the controls on the selected page of each TabControl."""
        form = self.doc.form
        for c in form.visual():
            w = self.previews.get(id(c))
            if w is not None and c.parent:
                parent = form.find(c.parent)
                if parent is not None and parent.type == "TabControl":
                    w.setVisible(tab_page(c) == int(parent.props.get("SelectedIndex", 0) or 0))

    def on_control_changed(self, ctrl) -> None:
        vp = getattr(self, "_variant_preview", None)
        if vp is not None:
            vp.invalidate()                     # the shown size is worked out again from the new values
        if ctrl is None or ctrl.type in MENU_TYPES:
            self.layout_form()
        elif id(ctrl) in self.previews:
            if vp is not None and vp.active:    # the control as the shown layout size has it
                vp.apply(ctrl)
            else:
                apply_props(self.previews[id(ctrl)], ctrl)
            if ctrl.type == "TabControl" or "TabPage" in ctrl.props:
                self.sync_pages()
        self.overlay.update()

    def on_live_changed(self, ctrl) -> None:
        """One step of a drag (FormDocument.begin_live): only geometry follows the mouse - the full
        preview update (apply_props, Blend / localization previews, Properties ...) runs on release."""
        vp = getattr(self, "_variant_preview", None)
        if vp is not None:
            vp.invalidate()
        if ctrl is None or ctrl.type in MENU_TYPES:
            self.layout_form()
        else:
            w = self.previews.get(id(ctrl))
            if w is not None:
                p = self.design_props(ctrl)
                try:
                    w.setGeometry(int(p["Left"]), int(p["Top"]), max(4, int(p["Width"])), max(4, int(p["Height"])))
                except (KeyError, TypeError, ValueError):
                    apply_props(w, ctrl)
        self.overlay.update()

    def live_drag_ok(self) -> bool:
        """A drag may use the cheap live path - not while edits are recorded into a visual state /
        timeline keyframes, in a mirrored (RightToLeftLayout) language or on a phone form: there the
        listeners rewrite every step (record, mirror, Column / Row order)."""
        lp = getattr(self, "_loc_preview", None)
        vp = getattr(self, "_variant_preview", None)      # This size only: every step becomes an override
        return not (self.blend_recording() or (lp is not None and lp.mirrored) or self.phone.active
                    or (vp is not None and vp.active))

    def begin_live(self) -> None:
        if self.live_drag_ok():
            self.doc.begin_live()

    def end_live(self) -> None:
        if self.doc.live:
            self.doc.end_live()

    def _on_selection(self, c):
        # selecting a control on a hidden page (Properties / Document Outline) shows that page
        form = self.doc.form
        if c is not None and not c.ctype.nonvisual:
            x, seen = c, set()
            while x.parent and x.name not in seen:
                seen.add(x.name)
                parent = form.find(x.parent)
                if parent is None:
                    break
                if parent.type == "TabControl" and tab_page(x) != int(parent.props.get("SelectedIndex", 0) or 0):
                    self.doc.set_prop(parent, "SelectedIndex", tab_page(x), record=False)
                x = parent
        self.overlay.update()
        self.frame.update()
        self.tray.sync()

    # ------------------------------------------------------------ lock / tab order
    def set_locked(self, on: bool) -> None:
        self.doc.set_locked(on)
        self.overlay.update()

    def set_tab_order_mode(self, on: bool) -> None:
        on = bool(on)
        if on == self.tab_order_mode:
            return
        self.tab_order_mode = on
        self.tab_next = {}
        self.tab_assigned = set()
        self._tab_recorded = False
        if on:
            TOOL_STATE.set(None)
        self.overlay.update()
        self.overlay.setFocus()
        self.tabOrderModeChanged.emit(on)

    def assign_tab_index(self, c: Control, restart: bool = False) -> None:
        """Tab Order mode: give *c* the next TabIndex of its container (0, 1, 2 ... in click order).
        restart (Ctrl+click, VS): *c* keeps its number and the numbering goes on from it."""
        if restart:
            self.tab_next[c.parent] = int(c.props.get("TabIndex", 0) or 0) + 1
            self.tab_assigned.add(id(c))
            self.overlay.update()
            return
        if not self._tab_recorded:
            self.doc.checkpoint()
            self._tab_recorded = True
        n = self.tab_next.get(c.parent, 0)
        self.tab_next[c.parent] = n + 1
        self.tab_assigned.add(id(c))
        self.doc.set_prop(c, "TabIndex", n, record=False)
        self.overlay.update()

    # ------------------------------------------------------------ actions
    def create_control(self, type_name: str, pos: QPoint, size: QSize | None = None) -> None:
        """A Toolbox tool placed at *pos* (form coordinates); *size*: the rectangle drawn with a
        click-drag (VS), else the control's default size."""
        ctype = CONTROL_TYPES[type_name]
        if type_name in MENU_TYPES:
            existing = next((c for c in self.doc.form.controls if c.type == type_name), None)
            if existing is not None:
                self.doc.select(existing)
                return
        if self.tab_order_mode:
            self.set_tab_order_mode(False)
        parent = "" if ctype.nonvisual else self.overlay.container_at(pos, [])
        px, py = self.doc.form.client_origin(self.doc.form.find(parent) if parent else None)
        x, y = snap(pos.x() - px), snap(pos.y() - py)
        ctrl = self.doc.add_control(type_name, x, y, parent)
        if size is not None and not ctype.nonvisual:      # same undo step as the new control
            w = max(MIN_SIZE, snap(pos.x() - px + size.width()) - x)
            h = max(MIN_SIZE, snap(pos.y() - py + size.height()) - y)
            self.doc.set_geometry(ctrl, x, y, w, h)
        self.phone.placed(ctrl, pos)
        self.overlay.setFocus()
        if type_name in MENU_TYPES:
            self.edit_menu(ctrl)

    def add_default(self, type_name: str) -> Control | None:
        """Toolbox double-click (VS): the control goes into the selected container (or next to the
        selected control, else onto the form) near its top-left corner, one step further while taken."""
        ctype = CONTROL_TYPES.get(type_name)
        if ctype is None:
            return None
        if type_name in MENU_TYPES or ctype.nonvisual:
            self.create_control(type_name, QPoint(0, 0))
            return self.doc.selected
        if self.tab_order_mode:
            self.set_tab_order_mode(False)
        parent = self.doc.paste_target()
        used = {(int(c.props["Left"]), int(c.props["Top"])) for c in self.doc.form.children(parent)}
        x = y = 2 * GRID
        while (x, y) in used and x < 100 * PASTE_STEP:
            x, y = x + PASTE_STEP, y + PASTE_STEP
        ctrl = self.doc.add_control(type_name, x, y, parent)
        self.overlay.setFocus()
        return ctrl

    def edit_menu(self, ctrl: Control) -> None:
        from .controls import menu_names
        from .menu_editor import edit_menu
        taken = {c.name for c in self.doc.form.controls} | {self.doc.form.name}
        for other in self.doc.form.controls:        # menu and tool strip item names must not clash
            if other.type in MENU_TYPES and other is not ctrl:
                taken |= set(menu_names(other.props.get("Items", [])))
        items = edit_menu(ctrl.props.get("Items", []), taken, self, flat=ctrl.type == "ToolStrip")
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
            if c.type == "ToolStrip":
                m.addAction("Edit Buttons...", lambda: self.edit_menu(c))
            if not c.ctype.nonvisual:
                m.addSeparator()
                m.addAction("Bring to Front", lambda: self.doc.reorder(list(self.doc.selection), True))
                m.addAction("Send to Back", lambda: self.doc.reorder(list(self.doc.selection), False))
        m.addSeparator()
        m.addAction("Cut", self.doc.cut).setEnabled(bool(self.doc.selection))
        m.addAction("Copy", self.doc.copy).setEnabled(bool(self.doc.selection))
        m.addAction("Paste", lambda: self.doc.paste()).setEnabled(self.doc.can_paste())
        m.addAction("Delete", lambda: self.doc.remove_controls(list(self.doc.selection))) \
            .setEnabled(bool(self.doc.selection))
        m.addSeparator()
        a = m.addAction("Lock Controls", lambda: self.set_locked(not self.doc.locked))
        a.setCheckable(True)
        a.setChecked(self.doc.locked)
        self.contextActions.emit(m, c)
        m.exec(at)
