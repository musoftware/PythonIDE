"""Map editor widgets of the Firmware & ECU workbench (Qt).

* ``MapEditor``  - one calibration map as a table (axes in the headers, heat colours, changed cells marked) with a
                   Text / 2D / 3D switch; edits go through a ``write(address, bytes)`` callback so they land in the
                   workbench's hex buffer (one undo stack for hex and map edits).
* ``CurveView``  - 2D view: one line per map row (or the curve), painted with QPainter.
* ``SurfaceView``- simple 3D wire-frame of a map (rotate with the mouse).
* ``WaveView``   - the whole file as a 2D curve around an offset (WinOLS "2D" mode, maps stand out as patterns).

Keys in the map table (WinOLS-like, docs/FIRMWARE.md "Keyboard"): + / - change the selected cells by one step,
Page Up / Page Down by ten steps, = sets a value, % changes by a percentage, T / 2 / 3 switch Text / 2D / 3D.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QInputDialog, QLabel, QStackedWidget,
                             QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from . import adapters as A

KEYS_HELP = [("+ / -", "Raise / lower the selected cells by one step"),
             ("Page Up / Page Down", "Raise / lower by ten steps"),
             ("=", "Set the selected cells to a value"),
             ("%", "Change the selected cells by a percentage"),
             ("T / 2 / 3", "Text / 2D / 3D view of the map")]


def _tr(text: str) -> str:
    """Pieces of composed labels are translated one by one (radide/i18n)."""
    try:
        from ...i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001
        return text


def heat(t: float) -> QColor:
    """0..1 -> blue, green, yellow, red (readable with dark text)."""
    t = max(0.0, min(1.0, t))
    stops = [(0.0, (120, 160, 255)), (0.35, (120, 220, 170)), (0.65, (240, 230, 120)), (1.0, (255, 130, 110))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            k = (t - a) / (b - a) if b > a else 0
            return QColor(*(int(ca[i] + (cb[i] - ca[i]) * k) for i in range(3)))
    return QColor(*stops[-1][1])


def fmt_value(v, m: A.MapDef, mode: str, factor: float | None = None, offset: float | None = None) -> str:
    if mode == "hex":
        w = m.width * 2
        return f"{int(v) & ((1 << (4 * w)) - 1):0{w}X}" if not m.cell.startswith("f") else f"{v:g}"
    if mode == "phys":
        f = m.factor if factor is None else factor
        o = m.offset if offset is None else offset
        p = v * f + o
        return f"{p:.0f}" if abs(p) >= 1000 or float(p).is_integer() else f"{p:.2f}".rstrip("0").rstrip(".")
    return f"{v:g}" if isinstance(v, float) else str(v)


class MapTable(QTableWidget):
    stepRequested = pyqtSignal(int)        # +1 / -1 / +10 / -10
    setRequested = pyqtSignal()
    percentRequested = pyqtSignal()
    viewRequested = pyqtSignal(int)        # 0 text, 1 2D, 2 3D
    KEYMAP = {Qt.Key.Key_Plus: ("step", 1), Qt.Key.Key_Minus: ("step", -1), Qt.Key.Key_PageUp: ("step", 10),
              Qt.Key.Key_PageDown: ("step", -10), Qt.Key.Key_Equal: ("set", 0), Qt.Key.Key_Percent: ("pct", 0),
              Qt.Key.Key_T: ("view", 0), Qt.Key.Key_2: ("view", 1), Qt.Key.Key_3: ("view", 2)}

    def event(self, e):
        if e.type() == e.Type.ShortcutOverride and e.key() in self.KEYMAP and \
                not e.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier) and \
                self.state() != QAbstractItemView.State.EditingState:
            e.accept()
            return True
        return super().event(e)

    def keyPressEvent(self, e):  # noqa: N802
        act = self.KEYMAP.get(e.key())
        if act is not None and self.state() != QAbstractItemView.State.EditingState and \
                not e.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            kind, v = act
            if kind == "step":
                self.stepRequested.emit(v)
            elif kind == "set":
                self.setRequested.emit()
            elif kind == "pct":
                self.percentRequested.emit()
            else:
                self.viewRequested.emit(v)
            return
        super().keyPressEvent(e)


class CurveView(QWidget):
    """Lines of a map (one per row) or a curve; x = axis values."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.xs: list = []
        self.rows: list[list] = []
        self.ys: list = []
        self.title = ""
        self.setMinimumHeight(180)

    def set_data(self, xs, ys, rows, title="") -> None:
        self.xs, self.ys, self.rows, self.title = list(xs), list(ys), [list(r) for r in rows], title
        self.update()

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        p.fillRect(self.rect(), pal.base())
        fg = pal.text().color()
        r = QRectF(self.rect()).adjusted(56, 24, -16, -30)
        p.setPen(QPen(fg, 1))
        p.drawText(QRectF(8, 2, self.width() - 16, 20), Qt.AlignmentFlag.AlignLeft, self.title)
        allv = [v for row in self.rows for v in row]
        if not allv or r.width() < 10 or r.height() < 10:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No map selected")
            return
        lo, hi = min(allv), max(allv)
        if hi == lo:
            hi = lo + 1
        n = max(len(row) for row in self.rows)
        grid = QColor(fg)
        grid.setAlpha(50)
        p.setPen(QPen(grid, 1))
        for i in range(5):
            y = r.top() + r.height() * i / 4
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(QPen(fg, 1))
            p.drawText(QRectF(0, y - 8, 52, 16), Qt.AlignmentFlag.AlignRight, f"{hi - (hi - lo) * i / 4:.0f}")
            p.setPen(QPen(grid, 1))
        p.setPen(QPen(fg, 1))
        for i, x in enumerate(self.xs[:n]):
            if n <= 16 or i % max(1, n // 12) == 0:
                px = r.left() + r.width() * i / max(1, n - 1)
                p.drawText(QRectF(px - 30, r.bottom() + 4, 60, 16), Qt.AlignmentFlag.AlignHCenter, str(x))
        for k, row in enumerate(self.rows):
            c = heat(k / max(1, len(self.rows) - 1))
            p.setPen(QPen(c, 2))
            path = QPainterPath()
            for i, v in enumerate(row):
                pt = QPointF(r.left() + r.width() * i / max(1, n - 1), r.bottom() - r.height() * (v - lo) / (hi - lo))
                path.lineTo(pt) if i else path.moveTo(pt)
            p.drawPath(path)


class SurfaceView(QWidget):
    """Wire-frame 3D view of a map; drag to rotate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[list] = []
        self.rot, self.tilt = 0.7, 0.55
        self._drag = None
        self.setMinimumHeight(180)

    def set_data(self, rows) -> None:
        self.rows = [list(r) for r in rows]
        self.update()

    def mousePressEvent(self, e):  # noqa: N802
        self._drag = (e.position(), self.rot, self.tilt)

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._drag is not None:
            d = e.position() - self._drag[0]
            self.rot = self._drag[1] + d.x() / 150
            self.tilt = max(0.1, min(1.4, self._drag[2] + d.y() / 150))
            self.update()

    def mouseReleaseEvent(self, _e):  # noqa: N802
        self._drag = None

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        allv = [v for row in self.rows for v in row]
        if not allv or len(self.rows) < 1:
            p.setPen(self.palette().text().color())
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No map selected")
            return
        lo, hi = min(allv), max(allv)
        span = (hi - lo) or 1
        ny, nx = len(self.rows), len(self.rows[0])
        cx, cy = self.width() / 2, self.height() / 2 + 20
        scale = min(self.width(), self.height()) / 2.6
        ca, sa, ct, st = math.cos(self.rot), math.sin(self.rot), math.cos(self.tilt), math.sin(self.tilt)

        def proj(i, j, v):
            x = (i / max(1, nx - 1) - 0.5) * 2
            y = (j / max(1, ny - 1) - 0.5) * 2
            z = (v - lo) / span * 1.2
            xr, yr = x * ca - y * sa, x * sa + y * ca
            return QPointF(cx + xr * scale, cy + yr * scale * st - z * scale * ct)
        for j in range(ny):
            for i in range(nx):
                v = self.rows[j][i]
                c = heat((v - lo) / span)
                p.setPen(QPen(c, 1.5))
                if i + 1 < nx:
                    p.drawLine(proj(i, j, v), proj(i + 1, j, self.rows[j][i + 1]))
                if j + 1 < ny:
                    p.drawLine(proj(i, j, v), proj(i, j + 1, self.rows[j + 1][i]))
        if ny == 1:
            p.setPen(self.palette().text().color())
            p.drawText(QRectF(8, 4, self.width(), 20), Qt.AlignmentFlag.AlignLeft, "Curve (1 row)")


class WaveView(QWidget):
    """The file as a curve of 8- or 16-bit values (WinOLS-style 2D mode); click to move the hex cursor."""
    offsetClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = b""
        self.start = 0
        self.width_cells = 1024
        self.cell = "u16be"
        self.marks: list[tuple[int, int]] = []     # (offset, size) of known maps
        self.cursor = 0
        self.setMinimumHeight(140)
        self.setMouseTracking(True)

    def set_data(self, data: bytes) -> None:
        self.data = data
        self.update()

    def show_at(self, offset: int) -> None:
        w = A.CELL.get(self.cell, (">H", 2))[1]
        self.cursor = offset
        self.start = max(0, offset - (self.width_cells * w) // 4)
        self.start -= self.start % w
        self.update()

    def wheelEvent(self, e):  # noqa: N802
        w = A.CELL.get(self.cell, (">H", 2))[1]
        step = (self.width_cells * w) // 8
        self.start = max(0, min(max(0, len(self.data) - w), self.start + (-step if e.angleDelta().y() > 0 else step)))
        self.start -= self.start % w
        self.update()

    def mousePressEvent(self, e):  # noqa: N802
        w = A.CELL.get(self.cell, (">H", 2))[1]
        i = int(e.position().x() / max(1, self.width()) * self.width_cells)
        off = self.start + i * w
        if 0 <= off < len(self.data):
            self.cursor = off
            self.offsetClicked.emit(off)
            self.update()

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        pal = self.palette()
        p.fillRect(self.rect(), pal.base())
        fg = pal.text().color()
        w = A.CELL.get(self.cell, (">H", 2))[1]
        vals = A.read_cells(self.data, self.start, min(self.width_cells, (len(self.data) - self.start) // w), self.cell)
        if not vals:
            return
        top = 20
        h = self.height() - top - 4
        full = float((1 << (8 * w)) - 1) if not self.cell.startswith("f") else (max(vals) or 1.0)
        sx = self.width() / max(1, self.width_cells)
        for off, size in self.marks:
            if off + size >= self.start and off <= self.start + self.width_cells * w:
                x0 = (off - self.start) / w * sx
                x1 = (off + size - self.start) / w * sx
                c = QColor(80, 160, 255, 50)
                p.fillRect(QRectF(x0, top, max(2.0, x1 - x0), h), c)
        p.setPen(QPen(QColor(90, 200, 120), 1))
        pts = QPolygonF([QPointF(i * sx, top + h - h * (v / full if full else 0)) for i, v in enumerate(vals)])
        p.drawPolyline(pts)
        cx = (self.cursor - self.start) / w * sx
        p.setPen(QPen(QColor(255, 120, 90), 1))
        p.drawLine(QPointF(cx, top), QPointF(cx, top + h))
        p.setPen(fg)
        p.setFont(QFont(self.font().family(), 8))
        p.drawText(QRectF(4, 2, self.width() - 8, 16), Qt.AlignmentFlag.AlignLeft,
                   f"0x{self.start:06X} - 0x{self.start + len(vals) * w:06X}   "
                   f"({A.CELL_TITLES.get(self.cell, self.cell)})")


class MapEditor(QWidget):
    """Table + 2D + 3D of one map. ``write(addr, data)`` stores edits; ``original`` marks changed cells."""
    edited = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.m: A.MapDef | None = None
        self.data_fn = lambda: b""
        self.original: bytes = b""
        self.write = None
        self.read_only = False
        self._raw: list[list] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 4, 6, 4)
        self.title = QLabel("No map selected - double-click a map in the project tree or in Potential Maps")
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        from PyQt6.QtWidgets import QSizePolicy
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title.setMinimumWidth(80)
        bar.addWidget(self.title, 1)
        bar.addWidget(QLabel("Values:"))
        self.mode = QComboBox()
        for key, label in (("raw", "Raw"), ("phys", "Physical (factor)"), ("hex", "Hex"), ("diff", "Diff vs original")):
            self.mode.addItem(_tr(label), key)
        self.mode.currentIndexChanged.connect(lambda _i: self.refresh())
        bar.addWidget(self.mode)
        self.view_btns = []
        for i, text in enumerate(("Text", "2D", "3D")):
            b = QToolButton()
            b.setText(text)
            b.setCheckable(True)
            b.setToolTip(f"{_tr(text + ' view')} ({'T23'[i]})")
            b.clicked.connect(lambda _c=False, i=i: self.set_view(i))
            bar.addWidget(b)
            self.view_btns.append(b)
        for text, step, tip in (("+1", 1, "Raise the selection by one step (+)"),
                                ("-1", -1, "Lower the selection by one step (-)")):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c=False, s=step: self.step(s))
            bar.addWidget(b)
        b = QToolButton()
        b.setText("Set Value...")
        b.setToolTip("Set the selected cells to a value (=)")
        b.clicked.connect(self.set_value)
        bar.addWidget(b)
        b = QToolButton()
        b.setText("%...")
        b.setToolTip("Change the selected cells by a percentage (%)")
        b.clicked.connect(self.percent)
        bar.addWidget(b)
        lay.addLayout(bar)
        self.stack = QStackedWidget()
        self.table = MapTable()
        self.table.setProperty("i18n_skip_items", True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                                   QAbstractItemView.EditTrigger.EditKeyPressed)
        self.table.horizontalHeader().setDefaultSectionSize(52)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.stepRequested.connect(self.step)
        self.table.setRequested.connect(self.set_value)
        self.table.percentRequested.connect(self.percent)
        self.table.viewRequested.connect(self.set_view)
        self.curve = CurveView()
        self.surface = SurfaceView()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.curve)
        self.stack.addWidget(self.surface)
        lay.addWidget(self.stack, 1)
        self.status = QLabel("")
        self.status.setContentsMargins(6, 2, 6, 2)
        lay.addWidget(self.status)
        self.set_view(0)

    # ------------------------------------------------------------------ api
    def set_map(self, m: A.MapDef | None) -> None:
        if m is not self.m:
            self.table.clearSelection()
            self.table.setRowCount(0)
        self.m = m
        self.refresh()

    def set_view(self, i: int) -> None:
        self.stack.setCurrentIndex(i)
        for k, b in enumerate(self.view_btns):
            b.setChecked(k == i)
        if i == 0:
            self.table.setFocus()

    def refresh(self) -> None:
        m = self.m
        data = self.data_fn()
        if m is None or not data:
            self.table.blockSignals(True)
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.table.blockSignals(False)
            self.curve.set_data([], [], [])
            self.surface.set_data([])
            return
        xs, ys, rows = A.read_map(data, m)
        self._raw = rows
        orig_rows = A.read_map(self.original, m)[2] if self.original and len(self.original) >= m.address + m.size \
            else []
        mode = self.mode.currentData()
        self.title.setText(f"{m.name}   [{m.kind}  {m.rows}x{m.cols}  {A.CELL_TITLES.get(m.cell, m.cell)}  "
                           f"@0x{m.address:06X}]" + (f"   {m.unit}" if m.unit else ""))
        t = self.table
        keep_sel = [(i.row(), i.column()) for i in t.selectedIndexes()] if t.rowCount() else []
        keep_cur = (t.currentRow(), t.currentColumn())
        t.blockSignals(True)
        t.clear()
        t.setRowCount(len(rows))
        t.setColumnCount(m.cols)
        ax = "phys" if mode == "phys" else "raw"
        t.setHorizontalHeaderLabels([fmt_value(x, m, ax, m.x_factor, 0) for x in xs[:m.cols]])
        t.setVerticalHeaderLabels([fmt_value(y, m, ax, m.y_factor, 0) for y in ys[:len(rows)]])
        allv = [v for r in rows for v in r]
        lo, hi = (min(allv), max(allv)) if allv else (0, 1)
        span = (hi - lo) or 1
        changed = 0
        bold = QFont(t.font())
        bold.setBold(True)
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                ov = orig_rows[r][c] if orig_rows and r < len(orig_rows) and c < len(orig_rows[r]) else v
                if mode == "diff":
                    text = f"{v - ov:+g}" if v != ov else "0"
                else:
                    text = fmt_value(v, m, mode)
                it = QTableWidgetItem(text)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it.setBackground(QBrush(heat((v - lo) / span)))
                it.setForeground(QBrush(QColor(20, 20, 20)))
                if v != ov:
                    changed += 1
                    it.setFont(bold)
                    it.setForeground(QBrush(QColor(150, 0, 0)))
                    it.setToolTip(f"Original: {ov}")
                if self.read_only:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                t.setItem(r, c, it)
        if 0 <= keep_cur[0] < t.rowCount() and 0 <= keep_cur[1] < t.columnCount():
            t.setCurrentCell(*keep_cur)
        for r, c in keep_sel:
            if r < t.rowCount() and c < t.columnCount():
                t.item(r, c).setSelected(True)
        t.blockSignals(False)
        self.curve.set_data(xs[:m.cols], ys[:len(rows)], rows, f"{m.name} ({m.unit})" if m.unit else m.name)
        self.surface.set_data(rows)
        parts = [_tr(f"min {lo}  max {hi}"), _tr(f"{changed} changed cell(s)")]
        if self.read_only:
            parts.append(_tr("read-only"))
        parts.append(_tr(f"factor {m.factor:g}") + (" " + _tr(f"offset {m.offset:g}") if m.offset else ""))
        self.status.setText("  -  ".join(parts))

    # ------------------------------------------------------------------ editing
    def _cells(self) -> list[tuple[int, int]]:
        sel = [(i.row(), i.column()) for i in self.table.selectedIndexes()]
        if not sel and self.table.currentRow() >= 0:
            sel = [(self.table.currentRow(), self.table.currentColumn())]
        return sel

    def _store(self, changes: dict[tuple[int, int], float]) -> int:
        if self.m is None or self.write is None or self.read_only or not changes:
            if self.read_only:
                self.message.emit("This file is open read-only.")
            return 0
        m = self.m
        n = 0
        for (r, c), v in sorted(changes.items()):
            self.write(A.cell_address(m, r, c), A.pack_cell(v, m.cell), f"map:{m.address}")
            n += 1
        self.refresh()
        self.edited.emit()
        return n

    def step(self, k: int) -> int:
        return self._store({(r, c): self._raw[r][c] + k for r, c in self._cells() if r < len(self._raw)})

    def set_value(self, value=None) -> int:
        if value is None:
            cur = self._cells()
            v0 = self._raw[cur[0][0]][cur[0][1]] if cur and self._raw else 0
            value, ok = QInputDialog.getDouble(self, "Set Value", "New raw value for the selected cells:", v0,
                                               -1e12, 1e12, 3)
            if not ok:
                return 0
        return self._store({(r, c): value for r, c in self._cells()})

    def percent(self, pct=None) -> int:
        if pct is None:
            pct, ok = QInputDialog.getDouble(self, "Change by %", "Percent (e.g. 5 or -3):", 0, -100, 1000, 2)
            if not ok:
                return 0
        return self._store({(r, c): self._raw[r][c] * (1 + pct / 100.0) for r, c in self._cells()
                            if r < len(self._raw)})

    def _on_item_changed(self, it: QTableWidgetItem) -> None:
        if self.m is None:
            return
        txt = it.text().strip()
        try:
            v = int(txt, 16) if self.mode.currentData() == "hex" else float(txt)
        except ValueError:
            self.refresh()
            return
        if self.mode.currentData() == "phys" and self.m.factor:
            v = (v - self.m.offset) / self.m.factor
        elif self.mode.currentData() == "diff":
            v = self._raw[it.row()][it.column()] + v
        self._store({(it.row(), it.column()): v})


__all__ = ["MapEditor", "MapTable", "CurveView", "SurfaceView", "WaveView", "heat", "KEYS_HELP"]
