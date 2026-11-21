"""Qt views of calibration maps: the heat-map table model, the 2D curve chart, the rotatable 3D surface and the
whole-file "2D view" (value graph for spotting tables). QPainter only - no extra dependency."""
from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QAbstractScrollArea, QSizePolicy, QWidget

from .model import fmt_value


def tr_ui(text: str) -> str:
    """The UI language's text (radide/i18n catalog and patterns; English when not translated or outside the IDE).
    Used for combo box items and composed strings, which the IDE's automatic translation does not reach."""
    try:
        from ...i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001
        return text


def heat_color(t: float, alpha: int = 255) -> QColor:
    """0 -> blue, 0.5 -> green/yellow, 1 -> red (light enough for black text)."""
    t = 0.0 if not math.isfinite(t) else min(1.0, max(0.0, t))
    c = QColor.fromHsvF((1.0 - t) * 0.66, 0.55, 1.0)
    c.setAlpha(alpha)
    return c


def diff_color(rel: float) -> QColor:
    """Change relative to the original: red = up, blue = down; stronger with the size of the change."""
    a = min(1.0, abs(rel) * 4 + 0.25)
    return QColor.fromHsvF(0.0 if rel > 0 else 0.6, 0.15 + 0.6 * a, 1.0)


# ====================================================================== table model
class MapTableModel(QAbstractTableModel):
    """(rows, cols) physical values with axis headers, heat-map or difference colouring and editing."""
    cellEdited = pyqtSignal(int, int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.z = np.zeros((0, 0))
        self.ori: np.ndarray | None = None
        self.x = np.zeros(0)
        self.y = np.zeros(0)
        self.digits: int | None = None
        self.mode = "heat"                    # heat | diff | plain
        self.read_only = False
        self._lo = self._hi = 0.0
        self._bold = QFont()
        self._bold.setBold(True)

    def set_values(self, z, x, y, ori=None, digits=None) -> None:
        self.beginResetModel()
        self.z = np.asarray(z, dtype=np.float64)
        self.x, self.y = np.asarray(x), np.asarray(y)
        self.ori = None if ori is None else np.asarray(ori, dtype=np.float64)
        if self.ori is not None and self.ori.shape != self.z.shape:
            self.ori = None
        self.digits = digits
        if self.z.size:
            self._lo, self._hi = float(np.nanmin(self.z)), float(np.nanmax(self.z))
        self.endResetModel()

    def update_values(self, z) -> None:
        z = np.asarray(z, dtype=np.float64)
        if z.shape != self.z.shape:
            self.set_values(z, self.x, self.y, self.ori, self.digits)
            return
        self.z = z
        if z.size:
            self._lo, self._hi = float(np.nanmin(z)), float(np.nanmax(z))
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def changed(self) -> np.ndarray:
        if self.ori is None:
            return np.zeros(self.z.shape, dtype=bool)
        return self.z != self.ori

    # -------------------------------------------------------------- Qt
    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else self.z.shape[0] if self.z.ndim == 2 else 0

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else self.z.shape[1] if self.z.ndim == 2 else 0

    def fmt(self, v) -> str:
        return fmt_value(float(v), self.digits)

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        r, c = idx.row(), idx.column()
        v = self.z[r, c]
        changed = self.ori is not None and self.ori[r, c] != v
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self.fmt(v)
        if role == Qt.ItemDataRole.BackgroundRole:
            if self.mode == "diff":
                if not changed:
                    return None
                o = self.ori[r, c]
                rel = (v - o) / (abs(o) if o else max(1.0, abs(self._hi - self._lo)))
                return QBrush(diff_color(rel))
            if self.mode == "heat":
                span = self._hi - self._lo
                return QBrush(heat_color((v - self._lo) / span if span else 0.5))
            return None
        if role == Qt.ItemDataRole.ForegroundRole:
            return QBrush(QColor("#000000")) if self.mode != "plain" or changed else None
        if role == Qt.ItemDataRole.FontRole and changed:
            return self._bold
        if role == Qt.ItemDataRole.ToolTipRole:
            tip = f"{self.fmt(v)}"
            if self.x.size > c and self.z.shape[1] > 1:
                tip += f"\nX = {self.fmt(self.x[c])}"
            if self.y.size > r and self.z.shape[0] > 1:
                tip += f"\nY = {self.fmt(self.y[r])}"
            if changed:
                o = self.ori[r, c]
                pct = f" ({(v - o) / abs(o) * 100:+.1f}%)" if o else ""
                tip += f"\nOriginal: {self.fmt(o)}{pct}"
            return tip
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.fmt(self.x[section]) if section < self.x.size else str(section)
        return self.fmt(self.y[section]) if section < self.y.size else str(section)

    def flags(self, idx):
        f = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if not self.read_only:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def setData(self, idx, value, role=Qt.ItemDataRole.EditRole):  # noqa: N802
        if role != Qt.ItemDataRole.EditRole or self.read_only:
            return False
        try:
            v = float(str(value).strip().replace(",", "."))
        except ValueError:
            return False
        self.cellEdited.emit(idx.row(), idx.column(), v)
        return True


# ====================================================================== 2D chart
class CurveChart(QWidget):
    """Lines of a map (one per row, X = axis values); the original as dashed lines where it differs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.z = np.zeros((0, 0))
        self.ori = None
        self.x = np.zeros(0)
        self.y = np.zeros(0)
        self.unit = ""
        self.highlight_row = -1
        self.setMinimumSize(200, 140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_values(self, z, x, y, ori=None, unit: str = "") -> None:
        self.z = np.atleast_2d(np.asarray(z, dtype=np.float64))
        self.x, self.y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        self.ori = None if ori is None else np.atleast_2d(np.asarray(ori, dtype=np.float64))
        self.unit = unit
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        p.fillRect(self.rect(), pal.base())
        if self.z.size == 0:
            p.end()
            return
        left, top, right, bottom = 56, 12, 16, 28
        w, h = max(10, self.width() - left - right), max(10, self.height() - top - bottom)
        zs = [self.z] + ([self.ori] if self.ori is not None else [])
        lo = min(float(np.nanmin(a)) for a in zs)
        hi = max(float(np.nanmax(a)) for a in zs)
        if hi == lo:
            hi, lo = hi + 1, lo - 1
        xs = self.x if self.x.size == self.z.shape[1] else np.arange(self.z.shape[1], dtype=np.float64)
        x0, x1 = float(xs.min()), float(xs.max())
        if x1 == x0:
            x1 = x0 + 1

        def pt(xv, zv):
            return QPointF(left + (xv - x0) / (x1 - x0) * w, top + h - (zv - lo) / (hi - lo) * h)
        text = pal.text().color()
        grid = QColor(text)
        grid.setAlpha(40)
        p.setPen(QPen(grid))
        for i in range(5):
            yy = top + h * i / 4
            p.drawLine(QPointF(left, yy), QPointF(left + w, yy))
            p.setPen(text)
            p.drawText(QRectF(0, yy - 8, left - 6, 16), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                       fmt_value(hi - (hi - lo) * i / 4, 2 if abs(hi - lo) < 10 else None))
            p.setPen(QPen(grid))
        p.setPen(text)
        for i, xv in enumerate(xs):
            if len(xs) > 16 and i % max(1, len(xs) // 8):
                continue
            q = pt(xv, lo)
            p.drawText(QRectF(q.x() - 30, top + h + 4, 60, 18), int(Qt.AlignmentFlag.AlignHCenter), fmt_value(xv))
        rows = self.z.shape[0]
        for r in range(rows):
            col = heat_color(r / max(1, rows - 1)).darker(150) if rows > 1 else QColor("#1f6fd1")
            if self.ori is not None and np.any(self.ori[r] != self.z[r]):
                pen = QPen(col, 1.2, Qt.PenStyle.DashLine)
                p.setPen(pen)
                path = QPainterPath(pt(xs[0], self.ori[r, 0]))
                for c in range(1, len(xs)):
                    path.lineTo(pt(xs[c], self.ori[r, c]))
                p.drawPath(path)
            p.setPen(QPen(col, 2.4 if r == self.highlight_row else 1.6))
            path = QPainterPath(pt(xs[0], self.z[r, 0]))
            for c in range(1, len(xs)):
                path.lineTo(pt(xs[c], self.z[r, c]))
            p.drawPath(path)
            p.setBrush(col)
            for c in range(len(xs)):
                p.drawEllipse(pt(xs[c], self.z[r, c]), 2.2, 2.2)
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.end()


# ====================================================================== 3D surface
class Surface3D(QWidget):
    """Rotatable 3D surface (orthographic, painter's algorithm). Drag to rotate, wheel to zoom, double-click to
    reset the view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.z = np.zeros((0, 0))
        self.ori = None
        self.x = np.zeros(0)
        self.y = np.zeros(0)
        self.azimuth, self.elevation, self.zoom = -35.0, 30.0, 1.0
        self.show_original = False
        self._drag = None
        self.setMinimumSize(220, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setToolTip("Drag to rotate, mouse wheel to zoom, double-click to reset")

    def set_values(self, z, x, y, ori=None) -> None:
        self.z = np.atleast_2d(np.asarray(z, dtype=np.float64))
        self.x, self.y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        self.ori = None if ori is None else np.atleast_2d(np.asarray(ori, dtype=np.float64))
        self.update()

    def set_view(self, azimuth: float, elevation: float) -> None:
        self.azimuth, self.elevation = azimuth, max(-5.0, min(89.0, elevation))
        self.update()

    def mousePressEvent(self, e) -> None:  # noqa: N802
        self._drag = (e.position(), self.azimuth, self.elevation)

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._drag is None:
            return
        p0, a0, e0 = self._drag
        d = e.position() - p0
        self.set_view(a0 + d.x() * 0.5, e0 + d.y() * 0.4)

    def mouseReleaseEvent(self, _e) -> None:  # noqa: N802
        self._drag = None

    def mouseDoubleClickEvent(self, _e) -> None:  # noqa: N802
        self.azimuth, self.elevation, self.zoom = -35.0, 30.0, 1.0
        self.update()

    def wheelEvent(self, e) -> None:  # noqa: N802
        self.zoom = max(0.3, min(4.0, self.zoom * (1.1 if e.angleDelta().y() > 0 else 1 / 1.1)))
        self.update()

    def _project(self, X, Y, Z, cx, cy, scale):
        a, el = math.radians(self.azimuth), math.radians(self.elevation)
        ca, sa, ce, se = math.cos(a), math.sin(a), math.cos(el), math.sin(el)
        xr = X * ca - Y * sa
        yr = X * sa + Y * ca
        sx = cx + xr * scale
        sy = cy - (Z * ce - yr * se) * scale
        depth = yr * ce + Z * se
        return sx, sy, depth

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        p.fillRect(self.rect(), pal.base())
        z = self.z
        if z.size == 0:
            p.end()
            return
        if z.shape[0] == 1:                     # a curve: extrude to a ribbon
            z = np.vstack([z, z])
        rows, cols = z.shape
        lo, hi = float(np.nanmin(z)), float(np.nanmax(z))
        span = hi - lo or 1.0
        X = np.linspace(-1, 1, cols)[None, :].repeat(rows, 0)
        Y = np.linspace(-1, 1, rows)[:, None].repeat(cols, 1)
        Z = (z - lo) / span * 1.1 - 0.55
        cx, cy = self.width() / 2, self.height() / 2 + 10
        scale = min(self.width(), self.height()) * 0.33 * self.zoom
        sx, sy, depth = self._project(X, Y, Z, cx, cy, scale)
        text = pal.text().color()
        # floor + axes box
        corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        fl = [self._project(np.array(a), np.array(b), np.array(-0.55), cx, cy, scale) for a, b in corners]
        grid = QColor(text)
        grid.setAlpha(60)
        p.setPen(QPen(grid, 1))
        p.drawPolygon(QPolygonF([QPointF(float(s[0]), float(s[1])) for s in fl]))
        quads = []
        for r in range(rows - 1):
            for c in range(cols - 1):
                d = (depth[r, c] + depth[r + 1, c] + depth[r, c + 1] + depth[r + 1, c + 1]) / 4
                quads.append((d, r, c))
        quads.sort(key=lambda q: -q[0])
        outline = QColor(0, 0, 0, 90)
        for _d, r, c in quads:
            poly = QPolygonF([QPointF(sx[r, c], sy[r, c]), QPointF(sx[r, c + 1], sy[r, c + 1]),
                              QPointF(sx[r + 1, c + 1], sy[r + 1, c + 1]), QPointF(sx[r + 1, c], sy[r + 1, c])])
            t = ((z[r, c] + z[r, c + 1] + z[r + 1, c] + z[r + 1, c + 1]) / 4 - lo) / span
            p.setBrush(heat_color(t, 235))
            p.setPen(QPen(outline, 0.8))
            p.drawPolygon(poly)
        if self.show_original and self.ori is not None and self.ori.shape == self.z.shape:
            o = self.ori if self.ori.shape[0] > 1 else np.vstack([self.ori, self.ori])
            Zo = (o - lo) / span * 1.1 - 0.55
            ox, oy, _od = self._project(X, Y, Zo, cx, cy, scale)
            p.setPen(QPen(QColor(0, 0, 0, 160), 1, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for r in range(rows):
                p.drawPolyline(QPolygonF([QPointF(ox[r, c], oy[r, c]) for c in range(cols)]))
        # labels
        p.setPen(text)

        def label(xv, yv, zv, s):
            a, b, _ = self._project(np.array(xv), np.array(yv), np.array(zv), cx, cy, scale)
            p.drawText(QRectF(float(a) - 40, float(b) - 9, 80, 18), int(Qt.AlignmentFlag.AlignCenter), s)
        if self.x.size:
            label(-1, -1.3, -0.55, fmt_value(float(self.x[0])))
            label(0.75, -1.3, -0.55, fmt_value(float(self.x[-1])))
        if self.y.size and self.z.shape[0] > 1:
            label(1.35, -0.75, -0.55, fmt_value(float(self.y[0])))
            label(1.35, 1, -0.55, fmt_value(float(self.y[-1])))
        p.drawText(QRectF(6, 4, 200, 18), int(Qt.AlignmentFlag.AlignLeft),
                   f"{fmt_value(lo, None)} .. {fmt_value(hi, None)}")
        p.end()


# ====================================================================== whole-file 2D view
class FileGraph(QAbstractScrollArea):
    """The values of the whole file as a graph (min / max per pixel column): tables show up as regular
    patterns. Click to select an offset (``offsetClicked``); maps of the pack are drawn as bands."""
    offsetClicked = pyqtSignal(int)
    TYPES = [("8-bit", "u8", "le"), ("16-bit Lo-Hi", "u16", "le"), ("16-bit Hi-Lo", "u16", "be"),
             ("32-bit float Lo-Hi", "f32", "le"), ("32-bit float Hi-Lo", "f32", "be")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = b""
        self.dtype, self.endian = "u8", "le"
        self.bytes_per_px = 4
        self.cursor = -1
        self.bands: list[tuple[int, int, str]] = []        # (start, end, label)
        self.setMinimumHeight(140)
        self.horizontalScrollBar().valueChanged.connect(lambda _v: self.viewport().update())
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setToolTip("Click to go to an offset; Ctrl+wheel to zoom")

    def set_data(self, data) -> None:
        self.data = bytes(data)
        self._update_scroll()
        self.viewport().update()

    def set_type(self, dt: str, endian: str) -> None:
        self.dtype, self.endian = dt, endian
        self.viewport().update()

    def set_zoom(self, bytes_per_px: int) -> None:
        center = self.offset_at(self.viewport().width() // 2)
        self.bytes_per_px = max(1, min(1 << 16, int(bytes_per_px)))
        self._update_scroll()
        self.scroll_to(center)

    def _update_scroll(self) -> None:
        total = len(self.data) // self.bytes_per_px + 1
        sb = self.horizontalScrollBar()
        sb.setRange(0, max(0, total - self.viewport().width()))
        sb.setPageStep(self.viewport().width())

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._update_scroll()

    def offset_at(self, px: int) -> int:
        return (self.horizontalScrollBar().value() + px) * self.bytes_per_px

    def scroll_to(self, offset: int) -> None:
        self.horizontalScrollBar().setValue(max(0, offset // self.bytes_per_px - self.viewport().width() // 2))
        self.viewport().update()

    def goto(self, offset: int) -> None:
        self.cursor = offset
        self.scroll_to(offset)

    def wheelEvent(self, e) -> None:  # noqa: N802
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.set_zoom(self.bytes_per_px // 2 if e.angleDelta().y() > 0 else self.bytes_per_px * 2)
            return
        sb = self.horizontalScrollBar()
        sb.setValue(sb.value() - e.angleDelta().y())

    def mousePressEvent(self, e) -> None:  # noqa: N802
        off = self.offset_at(int(e.position().x()))
        if 0 <= off < len(self.data):
            self.cursor = off
            self.viewport().update()
            self.offsetClicked.emit(off)

    def paintEvent(self, _e) -> None:  # noqa: N802
        from .finder import value_profile
        p = QPainter(self.viewport())
        pal = self.palette()
        vw, vh = self.viewport().width(), self.viewport().height()
        p.fillRect(0, 0, vw, vh, pal.base())
        if not self.data:
            p.end()
            return
        start = self.offset_at(0)
        end = min(len(self.data), start + vw * self.bytes_per_px)
        from .model import dtype_size
        size = dtype_size(self.dtype)
        start -= start % size
        cells_px = max(1, self.bytes_per_px // size)
        n_px = max(1, (end - start) // max(1, cells_px * size))
        mins, maxs, _per = value_profile(self.data, self.dtype, self.endian, start, end, width=n_px)
        if not len(mins):
            p.end()
            return
        lo, hi = (0.0, 255.0) if self.dtype == "u8" else (0.0, 65535.0) if self.dtype == "u16" else \
            (float(np.percentile(mins, 2)), float(np.percentile(maxs, 98)))
        if hi <= lo:
            hi = lo + 1
        top, bottom = 4, vh - 18
        hgt = bottom - top
        for s, e, lbl in self.bands:
            if e < start or s > end:
                continue
            x0 = (s - start) / self.bytes_per_px
            x1 = max(x0 + 2, (e - start) / self.bytes_per_px)
            band = QColor(pal.highlight().color())
            band.setAlpha(45)
            p.fillRect(QRectF(x0, top, x1 - x0, hgt), band)
            if x1 - x0 > 40:
                p.setPen(pal.text().color())
                p.drawText(QRectF(x0 + 2, top, x1 - x0 - 4, 14), int(Qt.AlignmentFlag.AlignLeft), lbl)
        pen = QPen(QColor("#1f6fd1"))
        p.setPen(pen)
        step = vw / max(1, len(mins)) if len(mins) < vw else 1.0
        scale = hgt / (hi - lo)
        for i in range(len(mins)):
            x = i * step if len(mins) < vw else i * vw / len(mins)
            y1 = bottom - (min(max(maxs[i], lo), hi) - lo) * scale
            y0 = bottom - (min(max(mins[i], lo), hi) - lo) * scale
            p.drawLine(QPointF(x, y0), QPointF(x, min(y1, y0 - 0.5)))
        if self.cursor >= 0 and start <= self.cursor <= end:
            x = (self.cursor - start) / self.bytes_per_px
            p.setPen(QPen(QColor("#d12f2f"), 1))
            p.drawLine(QPointF(x, top), QPointF(x, bottom))
        p.setPen(pal.text().color())
        p.drawText(QRectF(4, bottom + 2, vw - 8, 16), int(Qt.AlignmentFlag.AlignLeft), f"0x{start:X}")
        p.drawText(QRectF(4, bottom + 2, vw - 8, 16), int(Qt.AlignmentFlag.AlignRight),
                   f"0x{end:X}   ({self.bytes_per_px} byte/px)")
        p.end()
