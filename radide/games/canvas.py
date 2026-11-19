"""The scene canvas of the game scene designer: a QGraphicsView showing the level (tile layers,
sprites, text and areas), the grid, the camera (game window) bounds, and the tools that edit them.

Geometry of an object (shared with the runtime): (x, y) is the top-left corner of the unrotated
box of size (w * scale, h * scale); rotation is in degrees, clockwise on screen, around the
centre of that box.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QStyle

from .. import theme
from .model import Layer, SceneObject, first_frame, frame_rect

ASSET_MIME = "application/x-radide-asset"      # drag from the asset browser: "<kind>:<id>"
HANDLES = ("tl", "t", "tr", "r", "br", "b", "bl", "l")
TOOLS = ("select", "paint", "erase", "rect", "fill")


def object_transform(o: SceneObject) -> QTransform:
    s = o.scale or 1.0
    cx, cy = o.w * s / 2, o.h * s / 2
    return QTransform().translate(cx, cy).rotate(o.rotation).translate(-cx, -cy).scale(s, s)


def _rot(dx: float, dy: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def _checker(p: QPainter, r: QRectF, size: float = 8) -> None:
    p.fillRect(r, QColor(200, 200, 200))
    p.save()
    p.setClipRect(r)
    dark = QColor(150, 150, 150)
    y, row = r.top(), 0
    while y < r.bottom():
        x = r.left() + (size if row % 2 else 0)
        while x < r.right():
            p.fillRect(QRectF(x, y, size, size), dark)
            x += size * 2
        y += size
        row += 1
    p.restore()


# ====================================================================== tile layer
class TileLayerItem(QGraphicsItem):
    """Draws one tile layer from its tileset (plus the red collision overlay when shown)."""

    def __init__(self, editor, layer: Layer, index: int):
        super().__init__()
        self.editor, self.layer, self.index = editor, layer, index
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemUsesExtendedStyleOption, True)
        self.setZValue(index * 1000)
        self.setVisible(layer.visible)

    def tile_size(self) -> tuple[int, int]:
        return self.editor.scene.tile_size(self.layer)

    def boundingRect(self) -> QRectF:
        tw, th = self.tile_size()
        return QRectF(0, 0, self.layer.cols * tw, self.layer.rows * th)

    def update_cells(self, cells) -> None:
        tw, th = self.tile_size()
        for c, r in cells:
            self.update(QRectF(c * tw, r * th, tw, th))

    def paint(self, p: QPainter, option, widget=None) -> None:
        ly = self.layer
        tw, th = self.tile_size()
        ts = self.editor.scene.assets.get("tilesets", {}).get(ly.tileset)
        pm = self.editor.pixmap(ts.get("image")) if ts else None
        ts_cols = max(1, pm.width() // tw) if pm is not None else 1
        ex = option.exposedRect
        c0, c1 = max(0, int(ex.left() // tw)), min(ly.cols - 1, int(ex.right() // tw))
        r0, r1 = max(0, int(ex.top() // th)), min(ly.rows - 1, int(ex.bottom() // th))
        coll = ly.collision and self.editor.show_collision
        red = QColor(230, 40, 40, 110)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        for r in range(r0, r1 + 1):
            row = ly.data[r]
            for c in range(c0, min(c1, len(row) - 1) + 1):
                t = row[c]
                if t < 0:
                    continue
                target = QRectF(c * tw, r * th, tw, th)
                if pm is not None:
                    p.drawPixmap(target, pm, QRectF((t % ts_cols) * tw, (t // ts_cols) * th, tw, th))
                else:              # no tileset image: coloured squares with the tile number
                    p.fillRect(target, QColor.fromHsv((t * 47) % 360, 120, 200))
                    p.setPen(QColor(0, 0, 0))
                    p.drawText(target, Qt.AlignmentFlag.AlignCenter, str(t))
                if coll:
                    p.fillRect(target, red)
        if coll:
            p.setPen(QPen(QColor(230, 40, 40), 0))
            p.drawRect(self.boundingRect())


# ====================================================================== objects
class ObjectItem(QGraphicsItem):
    """A sprite / text / area of a sprites or ui layer.  Move (Qt), resize and rotate (handles)."""

    def __init__(self, editor, layer: Layer, obj: SceneObject, index: int):
        super().__init__()
        self.editor, self.layer, self.obj, self.index = editor, layer, obj, index
        self._drag = None
        self._syncing = False
        F = QGraphicsItem.GraphicsItemFlag
        editable = not layer.locked
        self.setFlag(F.ItemIsSelectable, editable)
        self.setFlag(F.ItemIsMovable, editable)
        self.setFlag(F.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setVisible(layer.visible)
        self.sync_from_model()

    # ---------------------------------------------------------------- geometry
    def sync_from_model(self) -> None:
        o = self.obj
        self._syncing = True
        self.prepareGeometryChange()
        self.setPos(o.x, o.y)
        self.setTransform(object_transform(o))
        self.setZValue(self.index * 1000 + 1 + max(-499, min(499, o.z)))
        self.setOpacity(1.0 if o.visible else 0.35)
        self._syncing = False
        self.update()

    def _hsize(self) -> float:
        return 7.0 / max(0.05, self.editor.canvas.zoom * (self.obj.scale or 1.0))

    def _rot_off(self) -> float:
        return 22.0 / max(0.05, self.editor.canvas.zoom * (self.obj.scale or 1.0))

    def boundingRect(self) -> QRectF:
        m = self._hsize()
        return QRectF(-m, -m - self._rot_off(), self.obj.w + 2 * m, self.obj.h + 2 * m + self._rot_off())

    def shape(self):
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        if self.isSelected():
            path.addRect(self.boundingRect())
        else:
            path.addRect(QRectF(0, 0, self.obj.w, self.obj.h))
        return path

    def handle_points(self) -> dict:
        w, h = self.obj.w, self.obj.h
        pts = {"tl": (0, 0), "t": (w / 2, 0), "tr": (w, 0), "r": (w, h / 2), "br": (w, h),
               "b": (w / 2, h), "bl": (0, h), "l": (0, h / 2), "rot": (w / 2, -self._rot_off())}
        return {k: QPointF(*v) for k, v in pts.items()}

    def handle_at(self, pos: QPointF) -> str | None:
        if not self.isSelected() or len(self.scene().selectedItems()) != 1 or self.layer.locked:
            return None
        m = self._hsize() * 0.6 + 1.0 / max(0.05, self.editor.canvas.zoom * (self.obj.scale or 1.0))
        k = self.editor.canvas.zoom * (self.obj.scale or 1.0)
        small = min(self.obj.w, self.obj.h) * k < 28           # tiny sprite: corners + rotate only
        for name, pt in self.handle_points().items():
            if small and len(name) == 1:
                continue
            if abs(pos.x() - pt.x()) <= m and abs(pos.y() - pt.y()) <= m:
                return name
        return None

    # ---------------------------------------------------------------- painting
    def paint(self, p: QPainter, option, widget=None) -> None:
        o, ed = self.obj, self.editor
        r = QRectF(0, 0, o.w, o.h)
        if o.kind == "sprite":
            pm, src = None, None
            if o.spritesheet:
                sheet = ed.scene.assets.get("spritesheets", {}).get(o.spritesheet)
                pm = ed.pixmap(sheet.get("image")) if sheet else None
                if pm is not None:
                    src = QRectF(*frame_rect(sheet, first_frame(ed.scene, o), pm.width()))
            elif o.image:
                pm = ed.pixmap(ed.scene.assets.get("images", {}).get(o.image, ""))
                if pm is not None:
                    src = QRectF(pm.rect())
            if pm is not None:
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
                p.drawPixmap(r, pm, src)
            else:
                _checker(p, r)
                p.setPen(QColor(60, 60, 60))
                p.drawText(r, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, o.name)
        elif o.kind == "text":
            f = QFont(str(o.props.get("FontName") or "Segoe UI"))
            f.setPixelSize(max(4, int(o.props.get("FontSize") or 24)))
            p.setFont(f)
            p.setPen(QColor(str(o.props.get("ForeColor") or o.props.get("color") or "#FFFFFF")))
            p.drawText(r, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, o.text or o.name)
            if not self.isSelected():
                pen = QPen(QColor(255, 255, 255, 90), 0, Qt.PenStyle.DotLine)
                p.setPen(pen)
                p.drawRect(r)
        else:          # area (trigger zone)
            p.fillRect(r, QColor(255, 200, 0, 50))
            p.setPen(QPen(QColor(255, 170, 0), 0, Qt.PenStyle.DashLine))
            p.drawRect(r)
            p.drawText(r.adjusted(3, 2, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, o.name)
        if option.state & QStyle.StateFlag.State_Selected:
            self._paint_selection(p, r)

    def _paint_selection(self, p: QPainter, r: QRectF) -> None:
        acc = QColor(theme.color("accent"))
        p.setPen(QPen(acc, 0, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(r)
        if len(self.scene().selectedItems()) != 1 or self.layer.locked:
            return
        m = self._hsize()
        pts = self.handle_points()
        p.setPen(QPen(QColor(0, 0, 0), 0))
        p.drawLine(pts["t"], pts["rot"])
        p.setBrush(QColor(255, 255, 255))
        for k, pt in pts.items():
            if k == "rot":
                p.setBrush(acc)
                p.drawEllipse(pt, m * 0.7, m * 0.7)
                p.setBrush(QColor(255, 255, 255))
            else:
                p.drawRect(QRectF(pt.x() - m / 2, pt.y() - m / 2, m, m))

    # ---------------------------------------------------------------- interaction
    def hoverMoveEvent(self, e) -> None:
        h = self.handle_at(e.pos())
        cur = {"tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
               "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
               "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
               "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
               "rot": Qt.CursorShape.CrossCursor}.get(h)
        if cur is not None:
            self.setCursor(cur)
        elif self.layer.locked:
            self.unsetCursor()
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(e)

    def mousePressEvent(self, e) -> None:
        h = self.handle_at(e.pos()) if e.button() == Qt.MouseButton.LeftButton else None
        if h:
            o = self.obj
            self._drag = (h, e.scenePos(), (o.x, o.y, o.w, o.h, o.rotation))
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        if not self._drag:
            return super().mouseMoveEvent(e)
        h, start, (x0, y0, w0, h0, rot0) = self._drag
        o = self.obj
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if h == "rot":
            c = QPointF(o.x + o.w * o.scale / 2, o.y + o.h * o.scale / 2)
            d = e.scenePos() - c
            ang = math.degrees(math.atan2(d.y(), d.x())) + 90
            if shift:
                ang = round(ang / 15) * 15
            o.rotation = round(((ang + 180) % 360) - 180, 1)
        else:
            s = o.scale or 1.0
            dx, dy = _rot(e.scenePos().x() - start.x(), e.scenePos().y() - start.y(), -rot0)
            dx, dy = dx / s, dy / s
            nw, nh, sx, sy = w0, h0, 0.0, 0.0
            if "l" in h:
                nw, sx = w0 - dx, dx
            if "r" in h:
                nw = w0 + dx
            if h in ("tl", "t", "tr"):
                nh, sy = h0 - dy, dy
            if h in ("bl", "b", "br"):
                nh = h0 + dy
            if shift and len(h) == 2 and w0 > 0 and h0 > 0:      # corner + Shift: keep the aspect ratio
                k = max(nw / w0, nh / h0)
                nw, nh = w0 * k, h0 * k
                sx = w0 - nw if "l" in h else 0
                sy = h0 - nh if "t" in h else 0
            g = self.editor.snap_size()
            if g and rot0 == 0 and s == 1:
                if "l" in h:
                    left = round((x0 + sx) / g) * g
                    sx, nw = left - x0, x0 + w0 - left
                elif "r" in h:
                    nw = round((x0 + nw) / g) * g - x0
                if h in ("tl", "t", "tr"):
                    top = round((y0 + sy) / g) * g
                    sy, nh = top - y0, y0 + h0 - top
                elif h in ("bl", "b", "br"):
                    nh = round((y0 + nh) / g) * g - y0
            nw, nh = max(1.0, nw), max(1.0, nh)
            ox, oy = _rot(sx * s, sy * s, rot0)
            o.x, o.y, o.w, o.h = round(x0 + ox, 2), round(y0 + oy, 2), round(nw, 2), round(nh, 2)
        self.sync_from_model()
        self.editor.on_live_change()
        e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if self._drag:
            self._drag_rot0 = self._drag[2][4]
            self._drag = None
            e.accept()
            self.editor.commit_pending("Rotate" if self.obj.rotation != self._drag_rot0 else "Resize")
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e) -> None:
        self.editor.open_default_handler(self.obj)
        e.accept()

    def itemChange(self, change, value):
        GC = QGraphicsItem.GraphicsItemChange
        if change == GC.ItemPositionChange and not self._syncing:
            g = self.editor.snap_size()
            if g:
                return QPointF(round(value.x() / g) * g, round(value.y() / g) * g)
        elif change == GC.ItemPositionHasChanged and not self._syncing:
            self.obj.x, self.obj.y = round(self.pos().x(), 2), round(self.pos().y(), 2)
            self.editor.on_live_change()
        elif change == GC.ItemSelectedHasChanged:
            self.prepareGeometryChange()
        return super().itemChange(change, value)


# ====================================================================== the view
class SceneCanvas(QGraphicsView):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.gs = QGraphicsScene(self)
        self.setScene(self.gs)
        self.zoom = 1.0
        self.tool = "select"
        self.show_grid = True
        self.items_by_name: dict[str, ObjectItem] = {}
        self.tile_items: dict[str, TileLayerItem] = {}
        self._hover_cell = None
        self._stroke = None           # tile painting in progress: ("paint"|"rect", start cell)
        self._rect_item = None
        self._pan = None
        self._space = False
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.gs.selectionChanged.connect(editor.on_selection_changed)

    # ---------------------------------------------------------------- building
    def rebuild(self) -> None:
        sel = set(self.selected_names())
        self.gs.blockSignals(True)
        self.gs.clear()
        self._rect_item = None
        self.items_by_name, self.tile_items = {}, {}
        sc = self.editor.scene
        for i, ly in enumerate(sc.layers):
            if ly.type == "tiles":
                it = TileLayerItem(self.editor, ly, i)
                self.gs.addItem(it)
                self.tile_items[ly.name] = it
            else:
                for o in ly.objects:
                    it = ObjectItem(self.editor, ly, o, i)
                    self.gs.addItem(it)
                    self.items_by_name[o.name] = it
                    if o.name in sel and it.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable:
                        it.setSelected(True)
        ww, wh = sc.world_size()
        self.gs.setSceneRect(QRectF(-400, -300, ww + 800, wh + 600))
        self.gs.blockSignals(False)
        self.viewport().update()

    def selected_names(self) -> list[str]:
        try:
            return [it.obj.name for it in self.gs.selectedItems() if isinstance(it, ObjectItem)]
        except RuntimeError:
            return []

    def select_names(self, names) -> None:
        self.gs.blockSignals(True)
        self.gs.clearSelection()
        for n in names:
            it = self.items_by_name.get(n)
            if it is not None and it.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable:
                it.setSelected(True)
        self.gs.blockSignals(False)
        self.editor.on_selection_changed()

    def set_zoom(self, z: float) -> None:
        z = max(0.1, min(16.0, z))
        self.zoom = z
        self.setTransform(QTransform().scale(z, z))
        for it in self.items_by_name.values():
            it.prepareGeometryChange()
        self.editor.on_zoom_changed(z)

    def view_center(self) -> QPointF:
        return self.mapToScene(self.viewport().rect().center())

    # ---------------------------------------------------------------- drawing
    def drawBackground(self, p: QPainter, rect: QRectF) -> None:
        p.fillRect(rect, QColor(theme.color("stage")))
        sc = self.editor.scene
        ww, wh = sc.world_size()
        p.fillRect(QRectF(0, 0, ww, wh), QColor(sc.background))

    def drawForeground(self, p: QPainter, rect: QRectF) -> None:
        sc = self.editor.scene
        ww, wh = sc.world_size()
        world = QRectF(0, 0, ww, wh)
        bg = QColor(sc.background)
        light_bg = bg.lightness() > 128
        if self.show_grid:
            gw, gh = self.editor.grid_size()
            if gw * self.zoom >= 5 and gh * self.zoom >= 5:
                p.setPen(QPen(QColor(0, 0, 0, 45) if light_bg else QColor(255, 255, 255, 45), 0))
                area = rect.intersected(world)
                x = math.floor(area.left() / gw) * gw
                while x <= area.right():
                    p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
                    x += gw
                y = math.floor(area.top() / gh) * gh
                while y <= area.bottom():
                    p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
                    y += gh
        # level border and camera (game window) bounds
        p.setPen(QPen(QColor(theme.color("border")), 0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(world)
        cam = QPen(QColor(theme.color("accent")), 2 / self.zoom, Qt.PenStyle.DashLine)
        p.setPen(cam)
        p.drawRect(QRectF(0, 0, sc.width, sc.height))
        f = QFont("Segoe UI")
        f.setPixelSize(max(1, int(11 / self.zoom)))
        p.setFont(f)
        follow = sc.camera.get("follow")
        p.drawText(QPointF(4 / self.zoom, -5 / self.zoom),
                   f"Camera {sc.width}x{sc.height}" + (f"  (follows {follow})" if follow else ""))
        # tile brush preview
        if self._hover_cell is not None and self.tool != "select":
            ly = self.editor.active_layer()
            if ly is not None and ly.type == "tiles":
                tw, th = sc.tile_size(ly)
                c, r = self._hover_cell
                p.setPen(QPen(QColor(theme.color("accent")), 2 / self.zoom))
                p.setBrush(QBrush(QColor(255, 255, 255, 50)))
                p.drawRect(QRectF(c * tw, r * th, tw, th))

    # ---------------------------------------------------------------- tile tools
    def _cell_at(self, scene_pos: QPointF):
        ly = self.editor.active_layer()
        if ly is None or ly.type != "tiles":
            return None
        tw, th = self.editor.scene.tile_size(ly)
        c, r = int(math.floor(scene_pos.x() / tw)), int(math.floor(scene_pos.y() / th))
        return (c, r) if ly.inside(c, r) else None

    def _tile_tool_active(self) -> bool:
        ly = self.editor.active_layer()
        return (self.tool != "select" and ly is not None and ly.type == "tiles"
                and not ly.locked and ly.visible)

    def apply_tile_tool(self, tool: str, cell, end_cell=None) -> list:
        """Run a tile tool on the active layer (used by the mouse and by tests)."""
        ly = self.editor.active_layer()
        if ly is None or ly.type != "tiles" or cell is None:
            return []
        tile = -1 if tool == "erase" else self.editor.current_tile
        if tool in ("paint", "erase"):
            changed = [cell] if ly.paint(cell[0], cell[1], tile) else []
        elif tool == "rect":
            end = end_cell or cell
            changed = ly.fill_rect(cell[0], cell[1], end[0], end[1], tile)
        elif tool == "fill":
            changed = ly.flood_fill(cell[0], cell[1], tile)
        else:
            changed = []
        it = self.tile_items.get(ly.name)
        if it is not None and changed:
            it.update_cells(changed)
        return changed

    # ---------------------------------------------------------------- mouse
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.MiddleButton or (self._space and e.button() == Qt.MouseButton.LeftButton):
            self._pan = e.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()
            return
        self.editor.begin_edit()
        if e.button() == Qt.MouseButton.LeftButton and self._tile_tool_active():
            cell = self._cell_at(self.mapToScene(e.position().toPoint()))
            if cell is not None:
                if self.tool in ("paint", "erase"):
                    self._stroke = ("paint", cell)
                    self.apply_tile_tool(self.tool, cell)
                elif self.tool == "rect":
                    self._stroke = ("rect", cell)
                    self._update_rect_preview(cell, cell)
                elif self.tool == "fill":
                    self.apply_tile_tool("fill", cell)
                    self.editor.commit_pending("Fill")
            e.accept()
            return
        if e.button() == Qt.MouseButton.RightButton and self._tile_tool_active():
            cell = self._cell_at(self.mapToScene(e.position().toPoint()))     # right button = eyedropper
            ly = self.editor.active_layer()
            if cell is not None and ly.get(*cell) >= 0:
                self.editor.set_current_tile(ly.get(*cell))
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        if self._pan is not None:
            d = e.position() - self._pan
            self._pan = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            e.accept()
            return
        sp = self.mapToScene(e.position().toPoint())
        cell = self._cell_at(sp)
        if cell != self._hover_cell:
            self._hover_cell = cell
            self.viewport().update()
        self.editor.on_cursor(sp.x(), sp.y(), cell)
        if self._stroke is not None and cell is not None:
            kind, start = self._stroke
            if kind == "paint":
                self.apply_tile_tool(self.tool, cell)
            else:
                self._update_rect_preview(start, cell)
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._pan is not None:
            self._pan = None
            self.viewport().unsetCursor()
            e.accept()
            return
        if self._stroke is not None:
            kind, start = self._stroke
            self._stroke = None
            if kind == "rect":
                end = self._cell_at(self.mapToScene(e.position().toPoint())) or start
                if self._rect_item is not None:
                    self.gs.removeItem(self._rect_item)
                    self._rect_item = None
                self.apply_tile_tool("rect", start, end)
            self.editor.commit_pending({"paint": "Paint tiles", "erase": "Erase tiles",
                                        "rect": "Fill rectangle"}.get(self.tool, "Tiles"))
            e.accept()
            return
        super().mouseReleaseEvent(e)
        self.editor.commit_pending("Move")

    def _update_rect_preview(self, a, b) -> None:
        ly = self.editor.active_layer()
        tw, th = self.editor.scene.tile_size(ly)
        r = QRectF(min(a[0], b[0]) * tw, min(a[1], b[1]) * th,
                   (abs(a[0] - b[0]) + 1) * tw, (abs(a[1] - b[1]) + 1) * th)
        if self._rect_item is None:
            self._rect_item = QGraphicsRectItem()
            self._rect_item.setPen(QPen(QColor(theme.color("accent")), 0, Qt.PenStyle.DashLine))
            self._rect_item.setBrush(QColor(255, 255, 255, 60))
            self._rect_item.setZValue(1e6)
            self.gs.addItem(self._rect_item)
        self._rect_item.setRect(r)

    def wheelEvent(self, e) -> None:
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.set_zoom(self.zoom * (1.25 if e.angleDelta().y() > 0 else 0.8))
            e.accept()
            return
        super().wheelEvent(e)

    def leaveEvent(self, e) -> None:
        self._hover_cell = None
        self.viewport().update()
        super().leaveEvent(e)

    # ---------------------------------------------------------------- keys
    _EDIT_KEYS = {(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Z): "undo",
                  (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Y): "redo",
                  (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C): "copy",
                  (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_X): "cut",
                  (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_V): "paste",
                  (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_A): "select_all",
                  (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D): "duplicate",
                  (Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete): "delete"}

    def _edit_op(self, e):
        mods = e.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier |
                                Qt.KeyboardModifier.AltModifier)
        if mods == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and \
                e.key() == Qt.Key.Key_Z:
            return "redo"
        return self._EDIT_KEYS.get((Qt.KeyboardModifier(mods), Qt.Key(e.key())))

    def event(self, e):
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.ShortcutOverride and self._edit_op(e):
            e.accept()               # the canvas gets Ctrl+Z/C/V... instead of the IDE's Edit menu
            return True
        return super().event(e)

    def keyPressEvent(self, e) -> None:
        op = self._edit_op(e)
        if op:
            self.editor.edit_op(op)
            e.accept()
            return
        k = e.key()
        if k == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = True
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            return
        arrows = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if k in arrows and self.selected_names():
            step = (self.editor.snap_size() or 8) if e.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            self.editor.nudge(arrows[k][0] * step, arrows[k][1] * step)
            return
        tool_keys = {Qt.Key.Key_V: "select", Qt.Key.Key_B: "paint", Qt.Key.Key_E: "erase",
                     Qt.Key.Key_R: "rect", Qt.Key.Key_G: "fill"}
        if k in tool_keys and not e.modifiers():
            self.editor.set_tool(tool_keys[k])
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = False
            self.viewport().unsetCursor()
            return
        super().keyReleaseEvent(e)

    # ---------------------------------------------------------------- context menu
    def contextMenuEvent(self, e) -> None:
        if self._tile_tool_active():          # right button = eyedropper while painting tiles
            e.accept()
            return
        from PyQt6.QtWidgets import QMenu
        from .model import BEHAVIOURS, default_event
        ed = self.editor
        it = self.itemAt(e.pos())
        if isinstance(it, ObjectItem) and not it.isSelected() and                 it.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable:
            self.select_names([it.obj.name])
        objs = ed.selected_objects()
        pos = self.mapToScene(e.pos())
        m = QMenu(self)
        if len(objs) == 1:
            o = objs[0]
            m.addAction(f"View Code ({o.name}_{default_event(o)})", lambda: ed.open_default_handler(o))
            m.addSeparator()
        m.addAction("Cut", lambda: ed.edit_op("cut")).setEnabled(bool(objs))
        m.addAction("Copy", lambda: ed.edit_op("copy")).setEnabled(bool(objs))
        m.addAction("Paste", lambda: ed.edit_op("paste"))
        m.addAction("Duplicate", lambda: ed.edit_op("duplicate")).setEnabled(bool(objs))
        m.addAction("Delete", lambda: ed.edit_op("delete")).setEnabled(bool(objs))
        if objs:
            m.addSeparator()
            m.addAction("Bring to Front", lambda: ed.reorder(True))
            m.addAction("Send to Back", lambda: ed.reorder(False))
            bm = m.addMenu("Add Behaviour")
            for key, (label, _p, helptext) in BEHAVIOURS.items():
                a = bm.addAction(label, lambda k=key, ob=list(objs): ed.add_behaviour(ob, k))
                a.setToolTip(helptext)
            bm.setToolTipsVisible(True)
            if len(objs) == 1 and objs[0].kind == "sprite":
                name = objs[0].name
                m.addAction(f"Camera Follows {name}", lambda: ed.change(
                    "Camera", lambda: ed.scene.camera.__setitem__("follow", name), structural=True))
        else:
            m.addSeparator()
            m.addAction("Add Sprite from Image...", ed.import_image)
            m.addAction("Add Text", lambda: ed.add_object("text", pos))
            m.addAction("Add Area (trigger zone)", lambda: ed.add_object("area", pos))
            m.addSeparator()
            m.addAction("Scene Code (Scene_Load)", lambda: ed.open_handler(None, "Load"))
        m.exec(e.globalPos())

    # ---------------------------------------------------------------- drag & drop of assets
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasFormat(ASSET_MIME):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e) -> None:
        if e.mimeData().hasFormat(ASSET_MIME):
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e) -> None:
        if e.mimeData().hasFormat(ASSET_MIME):
            kind, _, aid = bytes(e.mimeData().data(ASSET_MIME)).decode("utf-8").partition(":")
            self.editor.add_from_asset(kind, aid, self.mapToScene(e.position().toPoint()))
            e.acceptProposedAction()
        else:
            super().dropEvent(e)
