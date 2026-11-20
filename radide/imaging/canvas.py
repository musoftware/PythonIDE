"""The zoomable pixel canvas of the Icon / Image Editor and its tools.

Left button draws with the primary colour, right button with the secondary colour (like the VB / VS icon
editor). Drawing *replaces* pixels (alpha included) so semi-transparent icon pixels are exact; a moved
selection and text are blended over the picture.
"""
from __future__ import annotations

from collections import deque

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QInputDialog, QWidget

from .. import theme
from .document import ImageDocument, blank

TOOLS = [  # id, label, shortcut letter
    ("select", "Rectangle Select", "S"), ("pencil", "Pencil", "P"), ("eraser", "Eraser", "E"),
    ("fill", "Fill", "F"), ("picker", "Color Picker", "I"), ("line", "Line", "L"),
    ("rect", "Rectangle", "R"), ("rect_fill", "Filled Rectangle", "Shift+R"),
    ("ellipse", "Ellipse", "O"), ("ellipse_fill", "Filled Ellipse", "Shift+O"),
    ("text", "Text", "T"), ("hotspot", "Cursor Hot Spot", "H"),
]
SHAPES = ("line", "rect", "rect_fill", "ellipse", "ellipse_fill")
MARGIN = 12


# ---------------------------------------------------------------------- pixel geometry
def line_points(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    """Bresenham: every pixel of the line from a to b (both included)."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    pts = []
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def rect_points(a, b, filled: bool) -> list[tuple[int, int]]:
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    if filled:
        return [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
    pts = [(x, y0) for x in range(x0, x1 + 1)] + [(x, y1) for x in range(x0, x1 + 1)]
    pts += [(x0, y) for y in range(y0 + 1, y1)] + [(x1, y) for y in range(y0 + 1, y1)]
    return pts


def ellipse_points(a, b, filled: bool) -> list[tuple[int, int]]:
    """Pixels whose centre is inside the ellipse inscribed in the box a..b (inclusive); the outline is
    the inside pixels that touch an outside pixel (4-neighbourhood)."""
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    cx, cy = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
    rx, ry = (x1 - x0 + 1) / 2, (y1 - y0 + 1) / 2

    def inside(x, y):
        return ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0

    pts = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if inside(x, y) and (filled or not all(inside(x + dx, y + dy) for dx, dy in
                                                    ((1, 0), (-1, 0), (0, 1), (0, -1)))):
                pts.append((x, y))
    return pts


def shape_points(tool: str, a, b) -> list[tuple[int, int]]:
    if tool == "line":
        return line_points(a, b)
    if tool in ("rect", "rect_fill"):
        return rect_points(a, b, tool == "rect_fill")
    return ellipse_points(a, b, tool == "ellipse_fill")


def flood_fill(img: QImage, x: int, y: int, color: QColor) -> int:
    """4-way flood fill of the area of exactly the colour at (x, y); returns the pixel count."""
    w, h = img.width(), img.height()
    if not (0 <= x < w and 0 <= y < h):
        return 0
    if img.format() != QImage.Format.Format_ARGB32:
        img.convertTo(QImage.Format.Format_ARGB32)
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    px = memoryview(ptr).cast("I")
    stride = img.bytesPerLine() // 4
    target = px[y * stride + x]
    new = color.rgba()
    if target == new:
        return 0
    count = 0
    todo = deque([(x, y)])
    while todo:
        cx, cy = todo.pop()
        if px[cy * stride + cx] != target:
            continue
        lx = cx
        while lx > 0 and px[cy * stride + lx - 1] == target:
            lx -= 1
        rx = cx
        while rx < w - 1 and px[cy * stride + rx + 1] == target:
            rx += 1
        for i in range(lx, rx + 1):
            px[cy * stride + i] = new
            count += 1
            for ny in (cy - 1, cy + 1):
                if 0 <= ny < h and px[ny * stride + i] == target:
                    todo.append((i, ny))
    return count


def checker_brush(cell: int) -> QBrush:
    pm = QPixmap(cell * 2, cell * 2)
    pm.fill(QColor("#FFFFFF"))
    p = QPainter(pm)
    p.fillRect(0, 0, cell, cell, QColor("#CCCCCC"))
    p.fillRect(cell, cell, cell, cell, QColor("#CCCCCC"))
    p.end()
    return QBrush(pm)


# ---------------------------------------------------------------------- the canvas
class PixelCanvas(QWidget):
    colorPicked = pyqtSignal(QColor, int)       # colour, 0 = primary / 1 = secondary
    hover = pyqtSignal(int, int)                 # image coordinates (-1, -1 = outside)
    zoomChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal()

    def __init__(self, doc: ImageDocument, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.zoom = 12
        self.grid = True
        self.tool = "pencil"
        self.pen_size = 1
        self.primary = QColor(0, 0, 0, 255)
        self.secondary = QColor(255, 255, 255, 255)
        self.text_font = QFont("Segoe UI", 9)
        self._drag_button = None
        self._start = None
        self._last = None
        self._preview: list[tuple[int, int]] = []
        self._preview_color = QColor(0, 0, 0)
        self._end = None
        self.selection: QRect | None = None
        self._floating: QImage | None = None
        self._float_at = QPoint()
        self._grab_offset = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        doc.changed.connect(self.update)
        doc.structureChanged.connect(self._on_structure)
        theme.changed.connect(self._on_theme)
        self._on_structure()

    def _on_theme(self, _name: str = "") -> None:
        self.update()

    # ---------------------------------------------------------------- geometry
    def _on_structure(self) -> None:
        self.commit_floating()
        self.selection = None
        self.updateGeometry()
        self.resize(self.sizeHint())
        self.update()

    def sizeHint(self) -> QSize:
        f = self.doc.frame
        return QSize(f.width * self.zoom + 2 * MARGIN, f.height * self.zoom + 2 * MARGIN)

    def set_zoom(self, z: int) -> None:
        z = max(1, min(64, int(z)))
        if z != self.zoom:
            self.zoom = z
            self.updateGeometry()
            self.resize(self.sizeHint())
            self.update()
            self.zoomChanged.emit(z)

    def fit_zoom(self, avail: QSize) -> None:
        f = self.doc.frame
        z = min((avail.width() - 2 * MARGIN) // max(1, f.width), (avail.height() - 2 * MARGIN) // max(1, f.height))
        self.set_zoom(max(1, min(32, z)))

    def origin(self) -> QPoint:
        f = self.doc.frame
        ox = max(MARGIN, (self.width() - f.width * self.zoom) // 2)
        oy = max(MARGIN, (self.height() - f.height * self.zoom) // 2)
        return QPoint(ox, oy)

    def to_image(self, pos) -> tuple[int, int]:
        o = self.origin()
        return (int((pos.x() - o.x()) // self.zoom), int((pos.y() - o.y()) // self.zoom))

    def to_widget(self, x: int, y: int) -> QPoint:
        o = self.origin()
        return QPoint(o.x() + x * self.zoom, o.y() + y * self.zoom)

    def _inside(self, x, y) -> bool:
        f = self.doc.frame
        return 0 <= x < f.width and 0 <= y < f.height

    # ---------------------------------------------------------------- painting
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.color("stage")))
        f = self.doc.frame
        o = self.origin()
        z = self.zoom
        target = QRect(o.x(), o.y(), f.width * z, f.height * z)
        brush = checker_brush(8)
        brush.setTransform(brush.transform().translate(o.x(), o.y()))
        p.fillRect(target, brush)
        img = self.doc.composite()
        if self._preview or self._floating is not None:
            pr = QPainter(img)
            if self._floating is not None:
                pr.drawImage(self._float_at, self._floating)
            for (x, y) in self._preview:
                if 0 <= x < img.width() and 0 <= y < img.height():
                    img.setPixelColor(x, y, self._preview_color)
            pr.end()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.drawImage(target, img)
        if self.grid and z >= 6:
            pen = QPen(QColor(128, 128, 128, 90))
            pen.setWidth(1)
            p.setPen(pen)
            for x in range(1, f.width):
                p.drawLine(o.x() + x * z, o.y(), o.x() + x * z, target.bottom())
            for y in range(1, f.height):
                p.drawLine(o.x(), o.y() + y * z, target.right(), o.y() + y * z)
        p.setPen(QPen(QColor(theme.color("border")), 1))
        p.drawRect(target.adjusted(-1, -1, 0, 0))
        if self.selection is not None:
            r = self.selection
            wr = QRect(self.to_widget(r.x(), r.y()), QSize(r.width() * z, r.height() * z))
            pen = QPen(QColor("#FFFFFF"), 1, Qt.PenStyle.SolidLine)
            p.setPen(pen)
            p.drawRect(wr)
            pen = QPen(QColor("#000000"), 1, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(wr)
        if self.doc.cursor:
            hx, hy = f.hotspot
            c = self.to_widget(hx, hy) + QPoint(z // 2, z // 2)
            p.setPen(QPen(QColor("#FF0000"), 1))
            p.drawLine(c.x() - z, c.y(), c.x() + z, c.y())
            p.drawLine(c.x(), c.y() - z, c.x(), c.y() + z)
        p.end()

    # ---------------------------------------------------------------- colours
    def color_for(self, button) -> QColor:
        return self.secondary if button == Qt.MouseButton.RightButton else self.primary

    def _stamp(self, pts) -> list[tuple[int, int]]:
        n = self.pen_size
        if n <= 1:
            return list(pts)
        out = set()
        off = -(n // 2)
        for (x, y) in pts:
            for dy in range(n):
                for dx in range(n):
                    out.add((x + off + dx, y + off + dy))
        return list(out)

    def _put(self, pts, color: QColor) -> None:
        img = self.doc.image
        w, h = img.width(), img.height()
        for (x, y) in pts:
            if 0 <= x < w and 0 <= y < h:
                img.setPixelColor(x, y, color)
        self.doc.notify()

    # ---------------------------------------------------------------- public drawing API (also for scripts/tests)
    def draw_points(self, pts, color: QColor | None = None) -> None:
        """One undo step: set these pixels of the active layer."""
        self.doc.checkpoint()
        self._put(self._stamp(pts), color or self.primary)

    def draw_shape(self, tool: str, a, b, color: QColor | None = None) -> None:
        self.doc.checkpoint()
        pts = shape_points(tool, a, b)
        self._put(pts if tool.endswith("_fill") else self._stamp(pts), color or self.primary)

    def fill_at(self, x: int, y: int, color: QColor | None = None) -> int:
        self.doc.checkpoint()
        n = flood_fill(self.doc.image, x, y, color or self.primary)
        self.doc.notify()
        return n

    def draw_text(self, x: int, y: int, text: str, color: QColor | None = None, font: QFont | None = None) -> None:
        if not text:
            return
        self.doc.checkpoint()
        f = QFont(font or self.text_font)
        f.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        img = self.doc.image
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        p.setFont(f)
        p.setPen(color or self.primary)
        p.drawText(QRect(x, y, img.width() - x, img.height() - y),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), text)
        p.end()
        self.doc.notify()

    # ---------------------------------------------------------------- selection
    def select_all(self) -> None:
        self.commit_floating()
        f = self.doc.frame
        self.selection = QRect(0, 0, f.width, f.height)
        self.selectionChanged.emit()
        self.update()

    def deselect(self) -> None:
        self.commit_floating()
        self.selection = None
        self.selectionChanged.emit()
        self.update()

    def _lift(self) -> None:
        """The selected pixels become a floating piece that follows the mouse."""
        if self.selection is None or self._floating is not None:
            return
        self.doc.checkpoint()
        r = self.selection
        self._floating = self.doc.image.copy(r)
        self._float_at = r.topLeft()
        self._clear_rect(r)

    def _clear_rect(self, r: QRect) -> None:
        img = self.doc.image
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(r, QColor(0, 0, 0, 0))
        p.end()
        self.doc.notify()

    def commit_floating(self) -> None:
        if self._floating is None:
            return
        img = self.doc.image
        p = QPainter(img)
        p.drawImage(self._float_at, self._floating)
        p.end()
        self._floating = None
        self.doc.notify()

    def move_selection(self, dx: int, dy: int) -> None:
        if self.selection is None:
            return
        self._lift()
        self._float_at += QPoint(dx, dy)
        self.selection.translate(dx, dy)
        self.update()

    def copy(self) -> bool:
        if self.selection is None:
            return False
        src = self._floating if self._floating is not None else self.doc.image.copy(self.selection)
        QApplication.clipboard().setImage(src)
        return True

    def cut(self) -> bool:
        if not self.copy():
            return False
        self.delete()
        return True

    def delete(self) -> None:
        if self._floating is not None:
            self._floating = None
            self.doc.notify()
        elif self.selection is not None:
            self.doc.checkpoint()
            self._clear_rect(self.selection)

    def paste(self, image: QImage | None = None) -> bool:
        img = image if image is not None else QApplication.clipboard().image()
        if img is None or img.isNull():
            return False
        self.commit_floating()
        self.doc.checkpoint()
        self._floating = img.convertToFormat(QImage.Format.Format_ARGB32)
        self._float_at = QPoint(0, 0)
        self.selection = QRect(0, 0, img.width(), img.height())
        self.tool = "select"
        self.selectionChanged.emit()
        self.doc.notify()
        return True

    def crop_to_selection(self) -> None:
        if self.selection is None:
            return
        self.commit_floating()
        r = self.selection.intersected(QRect(0, 0, self.doc.frame.width, self.doc.frame.height))
        if r.isEmpty():
            return
        self.doc.checkpoint()
        for la in self.doc.frame.layers:
            la.image = la.image.copy(r)
        self.doc.structureChanged.emit()
        self.doc.notify()

    def flip(self, horizontal: bool) -> None:
        self.commit_floating()
        self.doc.checkpoint()
        img = self.doc.image
        if self.selection is None:
            self.doc.active_layer.image = img.mirrored(horizontal, not horizontal)
        else:
            r = self.selection
            piece = img.copy(r).mirrored(horizontal, not horizontal)
            p = QPainter(img)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.drawImage(r.topLeft(), piece)
            p.end()
        self.doc.notify()

    def rotate90(self) -> None:
        self.commit_floating()
        f = self.doc.frame
        if f.width != f.height:
            return
        from PyQt6.QtGui import QTransform
        self.doc.checkpoint()
        la = self.doc.active_layer
        la.image = la.image.transformed(QTransform().rotate(90))
        self.doc.notify()

    def invert_colors(self) -> None:
        self.doc.checkpoint()
        self.doc.image.invertPixels(QImage.InvertMode.InvertRgb)
        self.doc.notify()

    # ---------------------------------------------------------------- mouse
    def set_tool(self, tool: str) -> None:
        if tool != "select":
            self.commit_floating()
        self.tool = tool
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self.setFocus()
        x, y = self.to_image(e.position())
        self._drag_button = e.button()
        self._start = self._last = (x, y)
        color = self.color_for(e.button())
        t = self.tool
        if t in ("pencil", "eraser"):
            self.doc.checkpoint()
            self._put(self._stamp([(x, y)]), QColor(0, 0, 0, 0) if t == "eraser" else color)
        elif t == "fill":
            if self._inside(x, y):
                self.fill_at(x, y, color)
            self._drag_button = None
        elif t == "picker":
            if self._inside(x, y):
                c = self.doc.pixel(x, y, merged=True)
                which = 1 if e.button() == Qt.MouseButton.RightButton else 0
                if which:
                    self.secondary = c
                else:
                    self.primary = c
                self.colorPicked.emit(c, which)
            self._drag_button = None
        elif t in SHAPES:
            self._preview_color = color
            self._preview = shape_points(t, (x, y), (x, y))
            self.update()
        elif t == "select":
            if self.selection is not None and self.selection.contains(x, y):
                self._lift()
                self._grab_offset = (x - self._float_at.x(), y - self._float_at.y())
            else:
                self.commit_floating()
                self.selection = None
                self._grab_offset = None
                self.update()
        elif t == "text":
            self._drag_button = None
            if self._inside(x, y):
                text, ok = QInputDialog.getText(self, "Text", "Text to draw:")
                if ok and text:
                    self.draw_text(x, y, text, color)
        elif t == "hotspot":
            self._drag_button = None
            if self._inside(x, y):
                self.doc.checkpoint()
                self.doc.frame.hotspot = (x, y)
                self.doc.notify()

    def mouseMoveEvent(self, e) -> None:
        x, y = self.to_image(e.position())
        if self._inside(x, y):
            self.hover.emit(x, y)
        else:
            self.hover.emit(-1, -1)
        if self._drag_button is None or (x, y) == self._last:
            return
        t = self.tool
        color = self.color_for(self._drag_button)
        if t in ("pencil", "eraser"):
            self._put(self._stamp(line_points(self._last, (x, y))),
                      QColor(0, 0, 0, 0) if t == "eraser" else color)
        elif t in SHAPES:
            a, b = self._start, (x, y)
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier and t != "line":   # square / circle
                d = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
                b = (a[0] + (d if b[0] >= a[0] else -d), a[1] + (d if b[1] >= a[1] else -d))
            pts = shape_points(t, a, b)
            self._preview = pts if t.endswith("_fill") else self._stamp(pts)
            self._end = b
            self.update()
        elif t == "select":
            if self._grab_offset is not None and self._floating is not None:
                nx, ny = x - self._grab_offset[0], y - self._grab_offset[1]
                self._float_at = QPoint(nx, ny)
                self.selection = QRect(nx, ny, self._floating.width(), self._floating.height())
            else:
                f = self.doc.frame
                x0, x1 = sorted((self._start[0], x))
                y0, y1 = sorted((self._start[1], y))
                x0, y0 = max(0, x0), max(0, y0)
                x1, y1 = min(f.width - 1, x1), min(f.height - 1, y1)
                self.selection = QRect(x0, y0, x1 - x0 + 1, y1 - y0 + 1) if x1 >= x0 and y1 >= y0 else None
            self.update()
        self._last = (x, y)

    def mouseReleaseEvent(self, e) -> None:
        if self._drag_button is None:
            return
        t = self.tool
        if t in SHAPES and self._preview:
            self.doc.checkpoint()
            self._put(self._preview, self._preview_color)
        self._preview = []
        self._end = None
        self._drag_button = None
        self._grab_offset = None
        if t == "select":
            self.selectionChanged.emit()
        self.update()

    def leaveEvent(self, _e) -> None:
        self.hover.emit(-1, -1)

    def wheelEvent(self, e) -> None:
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            step = 1 if self.zoom < 8 else 2
            self.set_zoom(self.zoom + (step if e.angleDelta().y() > 0 else -step))
            e.accept()
        else:
            e.ignore()

    def keyPressEvent(self, e) -> None:
        k = e.key()
        moves = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if k in moves and self.selection is not None:
            self.move_selection(*moves[k])
        elif k == Qt.Key.Key_Delete:
            self.delete()
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            self.deselect()
        else:
            super().keyPressEvent(e)


__all__ = ["PixelCanvas", "TOOLS", "line_points", "rect_points", "ellipse_points", "flood_fill", "blank"]
