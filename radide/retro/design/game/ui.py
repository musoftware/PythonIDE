"""The Qt editor shared by the four retro game designers (Atari 2600 / NES / Game Boy / DOS mode 13h).

``GameDesigner(design, path)`` is a document tab: tool bar (select / pencil / eraser / fill / rectangle /
picker, grid, zoom, undo / redo, palette, export PNG, generate, build & run), the Layers list (visibility +
current layer, "Objects" is the object layer), the colour / tile picker of the current layer, the canvas, the
object list and a Properties grid (object properties, or the screen settings when no object is selected).
Saving writes the design file and regenerates the code under ``gen/<name>/``.
"""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QImage, QKeySequence, QPainter, QPen, QUndoCommand, QUndoStack
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                             QScrollArea, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QToolBar,
                             QVBoxLayout, QWidget)

from . import SYSTEMS, TITLES, gen_dir
from . import atari2600 as A26
from . import nes as NES
from .model import Design, ident

ROLE = Qt.ItemDataRole.UserRole
OBJECTS = "Objects"
TOOLS = [("select", "Select / move objects", "S"), ("pencil", "Pencil", "P"), ("eraser", "Eraser", "E"),
         ("fill", "Fill", "F"), ("rect", "Rectangle", "R"), ("picker", "Pick value", "K")]
COLLISION_COLORS = [QColor(0, 0, 0, 0), QColor(230, 40, 40, 110), QColor(240, 170, 20, 120), QColor(40, 120, 240, 120),
                    QColor(160, 40, 220, 120)]


def to_qimage(w: int, h: int, buf, pal) -> QImage:
    img = QImage(bytes(buf), w, h, w, QImage.Format.Format_Indexed8)
    img.setColorTable([0xFF000000 | (r << 16) | (g << 8) | b for r, g, b in pal] + [0xFFFF00FF] * (256 - len(pal)))
    return img.copy()


class SnapCmd(QUndoCommand):
    def __init__(self, ed: "GameDesigner", before: dict, after: dict, text: str):
        super().__init__(text)
        self.ed, self.before, self.after, self.first = ed, before, after, True

    def redo(self):
        if self.first:
            self.first = False
            return
        self.ed.doc.restore(self.after)
        self.ed.refresh_all()

    def undo(self):
        self.ed.doc.restore(self.before)
        self.ed.refresh_all()


# ====================================================================== geometry helpers
def object_bounds(d: Design, o: dict) -> QRect:
    k = o.get("kind", "")
    x, y = int(o.get("x", 0)), int(o.get("y", 0))
    if d.system == "a2600":
        x0, x1 = A26.object_extent(d, o)
        if k.startswith("player"):
            spr = d.sprites.get(o.get("sprite", ""))
            h = spr["h"] if spr else 8
        else:
            h = max(1, int(o.get("height", 1)))
        return QRect(x0, y, max(1, x1 - x0), h)
    if d.system in ("nes", "gb"):
        return QRect(x, y, 8 * max(1, int(o.get("w", 1))), 8 * max(1, int(o.get("h", 1))))
    spr = d.sprites.get(o.get("sprite", ""))
    return QRect(x, y, spr["w"] if spr else 16, spr["h"] if spr else 16)


# ====================================================================== canvas
class Canvas(QWidget):
    def __init__(self, ed: "GameDesigner"):
        super().__init__()
        self.ed = ed
        self.image = QImage()
        self.zoom = 2
        self.aspect = (2, 1) if ed.doc.system == "a2600" else (1, 1)
        self.drag_from: QPoint | None = None
        self.drag_to: QPoint | None = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_image(self, img: QImage) -> None:
        self.image = img
        self.setFixedSize(self.image.width() * self.zoom * self.aspect[0],
                          self.image.height() * self.zoom * self.aspect[1])
        self.update()

    def sx(self) -> int:
        return self.zoom * self.aspect[0]

    def sy(self) -> int:
        return self.zoom * self.aspect[1]

    def to_sys(self, p) -> QPoint:
        return QPoint(int(p.x()) // self.sx(), int(p.y()) // self.sy())

    def paintEvent(self, _e):
        p = QPainter(self)
        if self.image.isNull():
            return
        p.drawImage(QRect(0, 0, self.width(), self.height()), self.image)
        ed, d, sx, sy = self.ed, self.ed.doc, self.sx(), self.sy()
        col = d.layer("collision")
        if col is not None and col.visible:
            for cy in range(col.h):
                for cx in range(col.w):
                    v = col.get(cx, cy)
                    if v:
                        p.fillRect(cx * col.cw * sx, cy * col.ch * sy, col.cw * sx, col.ch * sy,
                                   COLLISION_COLORS[min(v, len(COLLISION_COLORS) - 1)])
        lay = ed.current_layer()
        if ed.grid and lay is not None:
            cw, ch = lay.cw * sx, lay.ch * sy
            if cw >= 4 and ch >= 4:
                p.setPen(QPen(QColor(255, 255, 255, 50), 1))
                for x in range(0, self.width(), cw):
                    p.drawLine(x, 0, x, self.height())
                for y in range(0, self.height(), ch):
                    p.drawLine(0, y, self.width(), y)
        if d.system == "a2600" and lay is not None and lay.kind == "playfield":
            p.setPen(QPen(QColor(255, 255, 0, 140), 1, Qt.PenStyle.DashLine))
            p.drawLine(80 * sx, 0, 80 * sx, self.height())
        if d.system == "nes" and lay is not None and lay.kind == "attributes":
            p.setPen(QPen(QColor(255, 255, 255, 150), 1))
            for x in range(0, self.width(), 16 * sx):
                p.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), 16 * sy):
                p.drawLine(0, y, self.width(), y)
            if self.zoom >= 2:
                for my in range(lay.h):
                    for mx in range(lay.w):
                        p.drawText(mx * 16 * sx + 3, my * 16 * sy + 12, str(lay.get(mx, my)))
        if d.system == "nes" and NES.screens(d) > 1:
            p.setPen(QPen(QColor(255, 80, 80, 160), 1, Qt.PenStyle.DashLine))
            for s in range(1, NES.screens(d)):
                p.drawLine(s * 256 * sx, 0, s * 256 * sx, self.height())
        if ed.objects_visible():
            for o in d.objects:
                if d.system == "a2600" and not o.get("enabled", True):
                    continue
                r = object_bounds(d, o)
                sel = o is ed.selected_object()
                p.setPen(QPen(QColor(255, 230, 0) if sel else QColor(255, 255, 255, 90), 2 if sel else 1,
                              Qt.PenStyle.SolidLine if sel else Qt.PenStyle.DotLine))
                p.drawRect(r.x() * sx, r.y() * sy, r.width() * sx - 1, r.height() * sy - 1)
        if self.drag_from is not None and self.drag_to is not None and ed.tool == "rect" and lay is not None:
            a, b = self.drag_from, self.drag_to
            x0, x1 = sorted((a.x() // lay.cw, b.x() // lay.cw))
            y0, y1 = sorted((a.y() // lay.ch, b.y() // lay.ch))
            p.setPen(QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine))
            p.drawRect(x0 * lay.cw * sx, y0 * lay.ch * sy, (x1 - x0 + 1) * lay.cw * sx - 1,
                       (y1 - y0 + 1) * lay.ch * sy - 1)

    def mousePressEvent(self, e):
        pt = self.to_sys(e.position())
        self.drag_from = self.drag_to = pt
        self.ed.press(pt, e.button())

    def mouseMoveEvent(self, e):
        pt = self.to_sys(e.position())
        self.ed.hover(pt)
        if e.buttons() != Qt.MouseButton.NoButton and self.drag_from is not None:
            self.drag_to = pt
            self.ed.drag(pt, e.buttons())
            self.update()

    def mouseReleaseEvent(self, e):
        pt = self.to_sys(e.position())
        start = self.drag_from
        self.drag_from = self.drag_to = None
        self.ed.release(start, pt, e.button())
        self.update()


# ====================================================================== picker (colours / tiles / values)
class Picker(QWidget):
    """A grid of choices for the current layer; ``choices`` = [(value, QImage-or-QColor, tooltip)]."""
    picked = pyqtSignal(int)
    edit = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.choices: list = []
        self.cols = 16
        self.cell = 18
        self.value = 0
        self.setMouseTracking(True)

    def set_choices(self, choices: list, cols: int, cell: int, value: int) -> None:
        self.choices, self.cols, self.cell, self.value = choices, max(1, cols), cell, value
        rows = (len(choices) + self.cols - 1) // self.cols
        self.setFixedSize(self.cols * cell + 1, max(1, rows) * cell + 1)
        self.update()

    def _index_at(self, pos) -> int:
        i = int(pos.y()) // self.cell * self.cols + int(pos.x()) // self.cell
        return i if 0 <= i < len(self.choices) and int(pos.x()) < self.cols * self.cell else -1

    def paintEvent(self, _e):
        p = QPainter(self)
        c = self.cell
        for i, (val, look, _tip) in enumerate(self.choices):
            r = QRect((i % self.cols) * c, (i // self.cols) * c, c, c)
            if isinstance(look, QImage):
                p.fillRect(r, QColor(40, 40, 40))
                p.drawImage(r.adjusted(1, 1, -1, -1), look)
            else:
                p.fillRect(r.adjusted(1, 1, -1, -1), look)
            if val == self.value:
                p.setPen(QPen(QColor(255, 255, 0), 2))
                p.drawRect(r.adjusted(1, 1, -1, -1))

    def mouseMoveEvent(self, e):
        i = self._index_at(e.position())
        self.setToolTip(self.choices[i][2] if i >= 0 else "")

    def mousePressEvent(self, e):
        i = self._index_at(e.position())
        if i >= 0:
            self.value = self.choices[i][0]
            self.update()
            self.picked.emit(self.value)

    def mouseDoubleClickEvent(self, e):
        i = self._index_at(e.position())
        if i >= 0:
            self.edit.emit(self.choices[i][0])


# ====================================================================== pixel editor
class PixelCanvas(QWidget):
    changed = pyqtSignal()

    def __init__(self, w: int, h: int, pixels: bytearray, colors: list):
        super().__init__()
        self.w, self.h, self.px, self.colors = w, h, bytearray(pixels), colors
        self.value = 1 if len(colors) > 1 else 0
        self.fill_mode = False
        self.zoom = max(6, min(28, 360 // max(w, h)))
        self._fit()

    def _fit(self):
        self.setFixedSize(self.w * self.zoom + 1, self.h * self.zoom + 1)

    def resize_to(self, w: int, h: int) -> None:
        old, ow, oh = self.px, self.w, self.h
        self.px = bytearray(w * h)
        for y in range(min(h, oh)):
            for x in range(min(w, ow)):
                self.px[y * w + x] = old[y * ow + x]
        self.w, self.h = w, h
        self.zoom = max(6, min(28, 360 // max(w, h)))
        self._fit()
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        z = self.zoom
        for y in range(self.h):
            for x in range(self.w):
                v = self.px[y * self.w + x]
                c = self.colors[v] if v < len(self.colors) else QColor(255, 0, 255)
                p.fillRect(x * z, y * z, z, z, c)
        p.setPen(QPen(QColor(128, 128, 128, 90), 1))
        for x in range(self.w + 1):
            p.drawLine(x * z, 0, x * z, self.h * z)
        for y in range(self.h + 1):
            p.drawLine(0, y * z, self.w * z, y * z)

    def _paint(self, pos, buttons):
        x, y = int(pos.x()) // self.zoom, int(pos.y()) // self.zoom
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        v = 0 if buttons & Qt.MouseButton.RightButton else self.value
        if self.fill_mode:
            src = self.px[y * self.w + x]
            if src == v:
                return
            todo = [(x, y)]
            while todo:
                cx, cy = todo.pop()
                if 0 <= cx < self.w and 0 <= cy < self.h and self.px[cy * self.w + cx] == src:
                    self.px[cy * self.w + cx] = v
                    todo += [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]
        else:
            self.px[y * self.w + x] = v
        self.update()
        self.changed.emit()

    def mousePressEvent(self, e):
        self._paint(e.position(), e.buttons())

    def mouseMoveEvent(self, e):
        if e.buttons() and not self.fill_mode:
            self._paint(e.position(), e.buttons())


class PixelEditor(QDialog):
    """Edit a w x h image of palette values. ``resizable`` = "h" (Atari player height) / "wh" / "".
    Left button paints the chosen colour, right button paints colour 0 (background / transparent)."""

    def __init__(self, parent, title: str, w: int, h: int, pixels, colors_rgb: list, resizable: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.colors = [QColor(*c) for c in colors_rgb]
        lay = QVBoxLayout(self)
        self.canvas = PixelCanvas(w, h, bytearray(pixels), self.colors)
        top = QHBoxLayout()
        self.w_spin, self.h_spin = QSpinBox(), QSpinBox()
        if resizable:
            if "w" in resizable:
                self.w_spin.setRange(1, 128)
                self.w_spin.setValue(w)
                top.addWidget(QLabel("Width"))
                top.addWidget(self.w_spin)
            self.h_spin.setRange(1, 200 if "w" in resizable else 64)
            self.h_spin.setValue(h)
            top.addWidget(QLabel("Height"))
            top.addWidget(self.h_spin)
            self.w_spin.valueChanged.connect(self._resize)
            self.h_spin.valueChanged.connect(self._resize)
        self.fill = QCheckBox("Fill")
        self.fill.toggled.connect(lambda on: setattr(self.canvas, "fill_mode", on))
        top.addWidget(self.fill)
        for text, fn in (("Flip H", self._flip_h), ("Flip V", self._flip_v), ("Clear", self._clear)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            top.addWidget(b)
        top.addStretch(1)
        lay.addLayout(top)
        sc = QScrollArea()
        sc.setWidget(self.canvas)
        sc.setMinimumSize(380, 300)
        lay.addWidget(sc, 1)
        self.swatches = Picker()
        n = len(self.colors)
        cols = 16 if n > 16 else max(2, n)
        self.swatches.set_choices([(i, c, f"colour {i}") for i, c in enumerate(self.colors)], cols,
                                  16 if n > 16 else 26, self.canvas.value)
        self.swatches.picked.connect(lambda v: setattr(self.canvas, "value", v))
        lay.addWidget(self.swatches)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _resize(self):
        w = self.w_spin.value() if self.w_spin.maximum() > 1 else self.canvas.w
        self.canvas.resize_to(w if w > 0 else self.canvas.w, self.h_spin.value())

    def _flip_h(self):
        c = self.canvas
        c.px = bytearray(c.px[y * c.w + (c.w - 1 - x)] for y in range(c.h) for x in range(c.w))
        c.update()

    def _flip_v(self):
        c = self.canvas
        c.px = bytearray(c.px[(c.h - 1 - y) * c.w + x] for y in range(c.h) for x in range(c.w))
        c.update()

    def _clear(self):
        self.canvas.px = bytearray(len(self.canvas.px))
        self.canvas.update()

    def result_pixels(self) -> tuple[int, int, bytearray]:
        return self.canvas.w, self.canvas.h, self.canvas.px


class NESPaletteDialog(QDialog):
    """The 8 NES palettes (4 background, 4 sprite): click a slot, then a colour of the 64-colour master palette."""

    def __init__(self, parent, palettes: list, master: list):
        super().__init__(parent)
        self.setWindowTitle("NES Palettes")
        self.pals = [list(p) for p in palettes]
        self.master = master
        self.slot = (0, 1)
        lay = QVBoxLayout(self)
        grid = QGridLayout()
        self.buttons = {}
        for pi in range(8):
            grid.addWidget(QLabel(("BG " if pi < 4 else "Sprite ") + str(pi % 4)), pi, 0)
            for ci in range(4):
                b = QPushButton()
                b.setFixedSize(34, 22)
                b.clicked.connect(lambda _c=False, a=pi, c=ci: self._select(a, c))
                grid.addWidget(b, pi, ci + 1)
                self.buttons[(pi, ci)] = b
        lay.addLayout(grid)
        self.picker = Picker()
        self.picker.set_choices([(i, QColor(*c), f"${i:02X}") for i, c in enumerate(master)], 16, 20, 0)
        self.picker.picked.connect(self._pick)
        lay.addWidget(QLabel("Colour 0 of BG 0 is the background colour shared by all palettes."))
        lay.addWidget(self.picker)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._refresh()

    def _select(self, pi: int, ci: int):
        self.slot = (pi, ci)
        self.picker.value = self.pals[pi][ci]
        self.picker.update()
        self._refresh()

    def _pick(self, v: int):
        pi, ci = self.slot
        if ci == 0:
            for p in self.pals:
                p[0] = v
        else:
            self.pals[pi][ci] = v
        self._refresh()

    def _refresh(self):
        for (pi, ci), b in self.buttons.items():
            v = self.pals[pi][0 if ci == 0 else ci] if ci else self.pals[0][0]
            r, g, bl = self.master[v & 0x3F]
            sel = "border: 2px solid yellow;" if (pi, ci) == self.slot else ""
            b.setStyleSheet(f"background: rgb({r},{g},{bl}); {sel}")
            b.setToolTip(f"${v:02X}")


# ====================================================================== properties grid
class PropertyGrid(QTableWidget):
    def __init__(self, ed: "GameDesigner"):
        super().__init__(0, 2)
        self.ed = ed
        self.setHorizontalHeaderLabels(["Property", "Value"])
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self._target = None

    def show_target(self, target: dict | None, schema: dict, title_key: str | None) -> None:
        self._target = target
        self.setRowCount(0)
        rows = []
        if title_key is not None:
            rows.append(("name", ("text", None)))
        rows += list(schema.items())
        self.setRowCount(len(rows))
        src = target if target is not None else self.ed.doc.settings
        for r, (key, (typ, extra)) in enumerate(rows):
            it = QTableWidgetItem(key)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.setItem(r, 0, it)
            self.setCellWidget(r, 1, self._editor(src, key, typ, extra))
        self.resizeRowsToContents()

    def _editor(self, src: dict, key: str, typ: str, extra):
        val = src.get(key)
        if typ == "text":
            w = QLineEdit(str(val or ""))
            w.editingFinished.connect(lambda k=key, w=w: self.ed.set_property(self._target, k, w.text().strip()))
            return w
        if typ == "bool":
            w = QCheckBox()
            w.setChecked(bool(val))
            w.toggled.connect(lambda on, k=key: self.ed.set_property(self._target, k, bool(on)))
            return w
        if typ in ("int", "color"):
            w = QSpinBox()
            lo, hi = extra if typ == "int" else (0, 127)
            w.setRange(lo, hi)
            try:
                w.setValue(int(val or 0))
            except (TypeError, ValueError):
                w.setValue(lo)
            if typ == "color":
                self._tint(w, int(val or 0))
            w.editingFinished.connect(lambda k=key, w=w, t=typ: (self.ed.set_property(self._target, k, w.value()),
                                                                 self._tint(w, w.value()) if t == "color" else None))
            return w
        if typ == "choice":
            w = QComboBox()
            w.addItems([str(c) for c in extra])
            if isinstance(val, str):
                w.setCurrentText(val)
            elif val is not None:
                w.setCurrentIndex(max(0, min(len(extra) - 1, int(val))))
            as_text = isinstance(val, str)
            w.currentIndexChanged.connect(lambda i, k=key, w=w, t=as_text: self.ed.set_property(
                self._target, k, w.currentText() if t else i))
            return w
        if typ == "sprite":
            w = QComboBox()
            w.addItems(sorted(self.ed.doc.sprites))
            w.setCurrentText(str(val or ""))
            w.currentTextChanged.connect(lambda t, k=key: self.ed.set_property(self._target, k, t))
            return w
        return QLabel(str(val))

    def _tint(self, w: QSpinBox, idx: int) -> None:
        try:
            r, g, b = A26.palette_rgb(self.ed.doc)[idx & 0x7F]
        except Exception:  # noqa: BLE001
            return
        fg = "black" if (r * 3 + g * 6 + b) > 1100 else "white"
        w.setStyleSheet(f"QSpinBox {{ background: rgb({r},{g},{b}); color: {fg}; }}")


# ====================================================================== the designer
class GameDesigner(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()

    def __init__(self, design: Design, path: Path | None = None, log=None):
        super().__init__()
        self.doc = design
        self.mod = SYSTEMS[design.system]
        self.path = Path(path) if path else None
        self.log = log or print
        self.undo = QUndoStack(self)
        self.tool = "pencil"
        self.grid = True
        self.cur_layer = design.layers[0].name if design.layers else OBJECTS
        self.values: dict[str, int] = {}        # current picker value per layer name
        self.sel_index = -1
        self.warnings: list[str] = []
        self.last_build: dict | None = None
        self._before = None
        self._last_cell = None
        self._dirty_render = False
        self._busy = False
        self._log_queue: list[str] = []
        self._build_ui()
        self.undo.cleanChanged.connect(lambda clean: self.modifiedChanged.emit(not clean))
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.refresh_all()

    # ------------------------------------------------------------ construction
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        tb = QToolBar()
        self.toolbar = tb
        grp = QActionGroup(self)
        self.tool_actions = {}
        for key, text, sc in TOOLS:
            a = QAction(text, self, checkable=True)
            a.setShortcut(QKeySequence(sc))
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            a.triggered.connect(lambda _c=False, k=key: self.set_tool(k))
            grp.addAction(a)
            tb.addAction(a)
            self.tool_actions[key] = a
        self.tool_actions[self.tool].setChecked(True)
        tb.addSeparator()
        self.a_grid = QAction("Grid", self, checkable=True)
        self.a_grid.setChecked(True)
        self.a_grid.toggled.connect(self._toggle_grid)
        tb.addAction(self.a_grid)
        tb.addAction("Zoom -", lambda: self.set_zoom(self.canvas.zoom - 1))
        self.zoom_label = QLabel(" 2x ")
        tb.addWidget(self.zoom_label)
        tb.addAction("Zoom +", lambda: self.set_zoom(self.canvas.zoom + 1))
        tb.addSeparator()
        self.a_undo = self.undo.createUndoAction(self, "Undo")
        self.a_redo = self.undo.createRedoAction(self, "Redo")
        self.a_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.a_redo.setShortcut(QKeySequence.StandardKey.Redo)
        for a in (self.a_undo, self.a_redo):
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            tb.addAction(a)
        tb.addSeparator()
        if self.doc.system == "nes":
            tb.addAction("Palettes...", self.edit_nes_palettes)
        tb.addAction("Edit Tile / Sprite...", self.edit_current_graphic)
        if self.doc.system in ("nes", "gb"):
            tb.addAction("Import Tiles...", lambda: self.import_tiles())
        tb.addAction("Export PNG...", lambda: self.export_png())
        tb.addSeparator()
        tb.addAction("Generate Code", lambda: self.generate())
        self.a_run = tb.addAction("Build && Run", lambda: self.build_and_run())
        lay.addWidget(tb)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)
        ll.addWidget(QLabel("Layers"))
        self.layer_list = QListWidget()
        self.layer_list.setMaximumHeight(130)
        self.layer_list.currentRowChanged.connect(self._layer_selected)
        self.layer_list.itemChanged.connect(self._layer_toggled)
        ll.addWidget(self.layer_list)
        self.picker_title = QLabel("")
        ll.addWidget(self.picker_title)
        self.picker = Picker()
        self.picker.picked.connect(self._picked)
        self.picker.edit.connect(self._edit_choice)
        psc = QScrollArea()
        psc.setWidget(self.picker)
        psc.setWidgetResizable(False)
        ll.addWidget(psc, 1)
        left.setMinimumWidth(200)
        left.setMaximumWidth(330)
        split.addWidget(left)

        self.canvas = Canvas(self)
        self.canvas.zoom = {"a2600": 3, "nes": 2, "gb": 3, "dos13h": 2}.get(self.doc.system, 2)
        sc = QScrollArea()
        sc.setWidget(self.canvas)
        sc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll = sc
        split.addWidget(sc)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.addWidget(QLabel("Objects"))
        self.obj_list = QListWidget()
        self.obj_list.currentRowChanged.connect(self._object_selected)
        rl.addWidget(self.obj_list, 1)
        row = QHBoxLayout()
        self.b_add = QPushButton("Add")
        self.b_add.clicked.connect(self.add_object)
        self.b_del = QPushButton("Delete")
        self.b_del.clicked.connect(self.delete_object)
        self.b_none = QPushButton("Screen")
        self.b_none.setToolTip("Show the screen settings in the Properties grid")
        self.b_none.clicked.connect(lambda: self.obj_list.setCurrentRow(-1))
        for b in (self.b_add, self.b_del, self.b_none):
            row.addWidget(b)
        if self.doc.system == "a2600":
            self.b_add.setEnabled(False)
            self.b_del.setEnabled(False)
        rl.addLayout(row)
        rl.addWidget(QLabel("Properties"))
        self.props = PropertyGrid(self)
        rl.addWidget(self.props, 2)
        right.setMaximumWidth(380)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([260, 900, 300])
        lay.addWidget(split, 1)
        self.status = QLabel("")
        self.status.setContentsMargins(6, 2, 6, 2)
        lay.addWidget(self.status)
        self.set_zoom(self.canvas.zoom)

    # ------------------------------------------------------------ state helpers
    def title(self) -> str:
        return (self.path.name if self.path else f"{self.doc.name}{self.mod.EXT}") + ("*" if self.is_modified() else "")

    def is_modified(self) -> bool:
        return not self.undo.isClean() or self.path is None and bool(self.undo.count())

    def current_layer(self):
        return None if self.cur_layer == OBJECTS else self.doc.layer(self.cur_layer)

    def objects_visible(self) -> bool:
        return self.doc.settings.get("_objects_visible", True) is not False

    def visible_set(self) -> set:
        s = {lay.name for lay in self.doc.layers if lay.visible}
        if self.objects_visible():
            s.add(OBJECTS)
        return s

    def selected_object(self) -> dict | None:
        return self.doc.objects[self.sel_index] if 0 <= self.sel_index < len(self.doc.objects) else None

    def set_tool(self, key: str) -> None:
        self.tool = key
        if key in self.tool_actions:
            self.tool_actions[key].setChecked(True)
        if key == "select" and self.cur_layer != OBJECTS:
            self._select_layer_name(OBJECTS)

    def _toggle_grid(self, on: bool) -> None:
        self.grid = on
        self.canvas.update()

    def set_zoom(self, z: int) -> None:
        self.canvas.zoom = max(1, min(8, z))
        self.zoom_label.setText(f" {self.canvas.zoom}x ")
        self.canvas.set_image(self.canvas.image)

    # ------------------------------------------------------------ refresh
    def refresh_all(self) -> None:
        self._fill_layers()
        self._fill_objects()
        self._fill_picker()
        self._fill_props()
        self.render()

    def render(self) -> None:
        w, h, buf, pal = self.mod.render_indexed(self.doc, self.visible_set())
        self.canvas.set_image(to_qimage(w, h, buf, pal))
        self._dirty_render = False

    def _tick(self) -> None:
        if self._dirty_render:
            self.render()
        if self._log_queue:
            q, self._log_queue = self._log_queue, []
            for line in q:
                try:
                    self.log(line)
                except Exception:  # noqa: BLE001
                    print(line)

    def _fill_layers(self) -> None:
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        names = [lay.name for lay in self.doc.layers] + [OBJECTS]
        for n in names:
            it = QListWidgetItem(n)
            it.setData(ROLE, n)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            vis = self.objects_visible() if n == OBJECTS else self.doc.layer(n).visible
            it.setCheckState(Qt.CheckState.Checked if vis else Qt.CheckState.Unchecked)
            self.layer_list.addItem(it)
        if self.cur_layer not in names:
            self.cur_layer = names[0]
        self.layer_list.setCurrentRow(names.index(self.cur_layer))
        self.layer_list.blockSignals(False)

    def _select_layer_name(self, name: str) -> None:
        for i in range(self.layer_list.count()):
            if self.layer_list.item(i).data(ROLE) == name:
                self.layer_list.setCurrentRow(i)
                return

    def _layer_selected(self, row: int) -> None:
        it = self.layer_list.item(row)
        if it is None:
            return
        self.cur_layer = it.data(ROLE) or it.text()
        if self.cur_layer == OBJECTS and self.tool not in ("select",):
            self.set_tool("select")
        elif self.cur_layer != OBJECTS and self.tool == "select":
            self.set_tool("pencil")
        self._fill_picker()
        self.canvas.update()

    def _layer_toggled(self, it: QListWidgetItem) -> None:
        on = it.checkState() == Qt.CheckState.Checked
        name = it.data(ROLE) or it.text()
        if name == OBJECTS:
            self.doc.settings["_objects_visible"] = on
        else:
            lay = self.doc.layer(name)
            if lay is not None:
                lay.visible = on
        self.render()

    def _fill_objects(self) -> None:
        self.obj_list.blockSignals(True)
        self.obj_list.clear()
        for o in self.doc.objects:
            extra = "" if o.get("enabled", True) else "  (off)"
            self.obj_list.addItem(f"{o.get('name', '?')}  [{o.get('kind', '')}]{extra}")
        if self.sel_index >= len(self.doc.objects):
            self.sel_index = -1
        self.obj_list.setCurrentRow(self.sel_index)
        self.obj_list.blockSignals(False)

    def _object_selected(self, row: int) -> None:
        self.sel_index = row
        self._fill_props()
        self.canvas.update()

    def _fill_props(self) -> None:
        o = self.selected_object()
        if o is None:
            schema = {k: v for k, v in self.mod.SETTINGS_SCHEMA.items()}
            self.props.show_target(None, schema, None)
        else:
            self.props.show_target(o, self.mod.schema_for(o), "name")

    # ------------------------------------------------------------ picker
    def _layer_value(self, lay) -> int:
        default = {"playfield": 1, "collision": 1, "tiles": 1, "attributes": 1, "linecolor": 0x46, "bitmap": 15}
        return self.values.get(lay.name, default.get(lay.kind, 1))

    def tile_image(self, index: int, pal_index: int = 0, sprite: bool = False) -> QImage:
        d = self.doc
        t = d.tile(index)
        tw, th = d.tile_w, d.tile_h
        if d.system == "nes":
            pb = NES.palette_bytes(d)
            base = (4 + pal_index if sprite else pal_index) * 4
            master = NES.master_palette()
            pal = [master[pb[base + i] & 0x3F] for i in range(4)]
            pal[0] = master[pb[0]]
        elif d.system == "gb":
            sh = self.mod.shades()
            bgp = int(d.settings.get("bgp", 0xE4))
            pal = [sh[(bgp >> (2 * i)) & 3] for i in range(4)]
        else:
            pal = self.mod.palette_rgb(d)
        return to_qimage(tw, th, t, pal)

    def _fill_picker(self) -> None:
        lay = self.current_layer()
        d = self.doc
        if lay is None:
            names = sorted(d.sprites) if d.sprites else []
            if d.system in ("nes", "gb"):
                base = 256 if d.system == "nes" else 0
                self.picker_title.setText("Sprite tiles (double-click to edit)")
                choices = [(i, self.tile_image(base + i, 0, sprite=True), f"tile {i}") for i in range(256)]
                self.picker.set_choices(choices, 16, 18, -1)
            else:
                self.picker_title.setText("Sprites (double-click to edit)")
                choices = []
                for i, n in enumerate(names):
                    s = d.sprites[n]
                    pal = self.mod.palette_rgb(d) if d.system == "dos13h" else [(0, 0, 0), (255, 255, 255)]
                    choices.append((i, to_qimage(s["w"], s["h"], s["pixels"], pal), n))
                self.picker.set_choices(choices, 4, 48, -1)
            return
        v = self._layer_value(lay)
        if lay.kind == "playfield":
            self.picker_title.setText("Playfield bit")
            self.picker.set_choices([(0, QColor(30, 30, 30), "off"), (1, QColor(230, 230, 230), "on")], 2, 32, v)
        elif lay.kind == "collision":
            self.picker_title.setText("Collision value (0 = none)")
            names = ["none", "solid", "hazard", "special", "trigger"]
            self.picker.set_choices([(i, COLLISION_COLORS[i] if i else QColor(30, 30, 30), names[i]) for i in range(5)],
                                    5, 28, v)
        elif lay.kind == "linecolor":
            self.picker_title.setText("Line colour (the rectangle tool paints a band of lines)")
            pal = A26.palette_rgb(d)
            self.picker.set_choices([(i, QColor(*pal[i]), f"${i << 1:02X}") for i in range(128)], 8, 22, v)
        elif lay.kind == "attributes":
            self.picker_title.setText("Background palette (double-click: edit palettes)")
            choices = []
            master = NES.master_palette()
            pb = NES.palette_bytes(d)
            for p in range(4):
                img = QImage(4, 1, QImage.Format.Format_RGB32)
                for i in range(4):
                    r, g, b = master[pb[p * 4 + i] & 0x3F]
                    img.setPixel(i, 0, 0xFF000000 | (r << 16) | (g << 8) | b)
                choices.append((p, img, f"palette {p}"))
            self.picker.set_choices(choices, 1, 40, v)
        elif lay.kind == "tiles":
            self.picker_title.setText("Tiles (double-click to edit)")
            pal_index = self.values.get("Attributes", 1) if d.system == "nes" else 0
            if d.system == "dos13h":
                choices = [(255, QColor(0, 0, 0, 0), "no tile")]
                choices += [(i, self.tile_image(i), f"tile {i}") for i in range(len(d.tiles))]
                choices.append((-2, QColor(60, 60, 60), "new tile"))
                self.picker.set_choices(choices, 6, 34, v)
            else:
                self.picker.set_choices([(i, self.tile_image(i, pal_index), f"tile {i}") for i in range(256)], 16, 18,
                                        v)
        elif lay.kind == "bitmap":
            self.picker_title.setText("Colour (double-click to edit)")
            pal = self.mod.palette_rgb(d)
            self.picker.set_choices([(i, QColor(*pal[i]), str(i)) for i in range(256)], 16, 14, v)

    def _picked(self, v: int) -> None:
        lay = self.current_layer()
        if lay is None:
            self.values[OBJECTS] = v
            return
        if lay.kind == "tiles" and v == -2:
            self.add_tile()
            return
        self.values[lay.name] = v
        if lay.kind == "attributes":
            self.values["Attributes"] = v

    def _edit_choice(self, v: int) -> None:
        lay = self.current_layer()
        d = self.doc
        if lay is None:
            if d.system in ("nes", "gb"):
                self.edit_tiles((256 if d.system == "nes" else 0) + v, 1, 1, sprite=True)
            else:
                names = sorted(d.sprites)
                if 0 <= v < len(names):
                    self.edit_sprite(names[v])
            return
        if lay.kind == "tiles" and v >= 0 and v != 255:
            self.edit_tiles(v, 1, 1)
        elif lay.kind == "attributes":
            self.edit_nes_palettes()
        elif lay.kind == "bitmap":
            self.edit_vga_color(v)

    # ------------------------------------------------------------ editing primitives
    def _begin(self) -> None:
        self._before = self.doc.snapshot()

    def _commit(self, text: str) -> None:
        if self._before is None:
            return
        after = self.doc.snapshot()
        if after != self._before:
            self.undo.push(SnapCmd(self, self._before, after, text))
        self._before = None

    def _cell(self, lay, pt: QPoint) -> tuple[int, int]:
        cx, cy = pt.x() // lay.cw, pt.y() // lay.ch
        if lay.kind == "playfield":
            cx = A26.edit_index(max(0, min(39, cx)), bool(self.doc.settings.get("reflect", True)))
        if lay.kind == "linecolor":
            cx = 0
        return cx, cy

    def _erase_value(self, lay) -> int:
        return lay.fill if lay.kind == "tiles" else 0

    def _apply(self, lay, cx: int, cy: int, v: int) -> bool:
        if lay.locked:
            return False
        return lay.set(cx, cy, v)

    def press(self, pt: QPoint, button) -> None:
        lay = self.current_layer()
        if self.tool == "select" or lay is None:
            self._press_object(pt)
            return
        cx, cy = self._cell(lay, pt)
        if self.tool == "picker" or button == Qt.MouseButton.MiddleButton:
            v = lay.get(cx, cy)
            self.values[lay.name] = v
            self.picker.value = v
            self.picker.update()
            return
        self._begin()
        right = button == Qt.MouseButton.RightButton
        v = self._erase_value(lay) if (self.tool == "eraser" or right) else self._layer_value(lay)
        if self.tool == "fill":
            lay.flood(cx, cy, v)
            self._commit("Fill")
            self.render()
        elif self.tool in ("pencil", "eraser"):
            self._apply(lay, cx, cy, v)
            self._last_cell = (cx, cy, v)
            self._dirty_render = True

    def drag(self, pt: QPoint, buttons) -> None:
        lay = self.current_layer()
        if self.tool == "select" or lay is None:
            self._drag_object(pt)
            return
        if self.tool in ("pencil", "eraser") and self._last_cell is not None:
            cx, cy = self._cell(lay, pt)
            lx, ly, v = self._last_cell
            n = max(abs(cx - lx), abs(cy - ly), 1)
            for i in range(n + 1):
                self._apply(lay, round(lx + (cx - lx) * i / n), round(ly + (cy - ly) * i / n), v)
            self._last_cell = (cx, cy, v)
            self._dirty_render = True

    def release(self, start: QPoint | None, pt: QPoint, button) -> None:
        lay = self.current_layer()
        if self.tool == "select" or lay is None:
            self._release_object()
            return
        if self.tool == "rect" and start is not None:
            self._begin()
            right = button == Qt.MouseButton.RightButton
            v = self._erase_value(lay) if right else self._layer_value(lay)
            (ax, ay), (bx, by) = self._cell(lay, start), self._cell(lay, pt)
            if lay.kind == "playfield":            # rectangle in screen columns, mapped to the stored half
                x0, x1 = sorted((start.x() // lay.cw, pt.x() // lay.cw))
                ys = sorted((ay, by))
                for y in range(ys[0], ys[1] + 1):
                    for x in range(max(0, x0), min(39, x1) + 1):
                        self._apply(lay, *self._cell(lay, QPoint(x * lay.cw, y)), v)
            else:
                for y in range(min(ay, by), max(ay, by) + 1):
                    for x in range(min(ax, bx), max(ax, bx) + 1):
                        self._apply(lay, x, y, v)
            self._commit("Rectangle")
            self.render()
            return
        if self.tool in ("pencil", "eraser"):
            self._last_cell = None
            self._commit("Paint" if self.tool == "pencil" else "Erase")
            self.render()

    def hover(self, pt: QPoint) -> None:
        lay = self.current_layer()
        txt = f"x {pt.x()}  y {pt.y()}"
        if lay is not None:
            cx, cy = self._cell(lay, pt)
            txt += f"   {lay.name} ({cx}, {cy}) = {lay.get(cx, cy)}"
        if self.warnings:
            txt += "   |   " + self.warnings[0]
        self.status.setText(txt)

    # ------------------------------------------------------------ objects on the canvas
    def _hit(self, pt: QPoint) -> int:
        for i in range(len(self.doc.objects) - 1, -1, -1):
            o = self.doc.objects[i]
            if self.doc.system == "a2600" and not o.get("enabled", True):
                continue
            if object_bounds(self.doc, o).adjusted(-1, -1, 1, 1).contains(pt):
                return i
        return -1

    def _press_object(self, pt: QPoint) -> None:
        i = self._hit(pt)
        self.sel_index = i
        self.obj_list.setCurrentRow(i)
        self._drag_origin = None
        if i >= 0:
            o = self.doc.objects[i]
            self._begin()
            self._drag_origin = (pt, int(o.get("x", 0)), int(o.get("y", 0)))

    def _drag_object(self, pt: QPoint) -> None:
        o = self.selected_object()
        org = getattr(self, "_drag_origin", None)
        if o is None or org is None:
            return
        p0, x0, y0 = org
        o["x"] = x0 + pt.x() - p0.x()
        o["y"] = y0 + pt.y() - p0.y()
        if self.doc.system == "a2600":
            o["x"] %= A26.WIDTH
            o["y"] = max(0, min(A26.lines(self.doc) - 1, o["y"]))
        self._dirty_render = True

    def _release_object(self) -> None:
        if getattr(self, "_drag_origin", None) is not None:
            self._drag_origin = None
            self._commit("Move object")
            self._fill_props()
            self.render()

    # ------------------------------------------------------------ properties / objects
    def set_property(self, target: dict | None, key: str, value) -> None:
        d = self.doc
        src = target if target is not None else d.settings
        if src.get(key) == value:
            return
        self._begin()
        if target is None and d.system == "a2600" and key == "tv":
            A26.set_tv(d, value)
        elif target is None and d.system == "nes" and key == "screens":
            NES.set_screens(d, value)
        elif key == "name" and target is not None:
            value = value or target.get("name", "Object")
            src[key] = value
        else:
            src[key] = value
        self._commit(f"Change {key}")
        self._fill_objects()
        if target is None and key in ("tv", "screens"):
            self.refresh_all()
        else:
            self.render()

    def add_object(self) -> None:
        d = self.doc
        if d.system == "a2600":
            return
        self._begin()
        if d.system == "dos13h":
            spr = sorted(d.sprites)[0] if d.sprites else ""
            o = {"name": d.unique_name("Sprite"), "kind": "sprite", "x": 140, "y": 90, "sprite": spr, "player": False}
        else:
            tile = max(0, self.values.get(OBJECTS, 0))
            o = {"name": d.unique_name("Sprite"), "kind": "sprite", "x": 64, "y": 64, "tile": tile, "w": 1, "h": 1, "palette": 0, "flip_h": False, "flip_v": False, "behind": False}
        d.objects.append(o)
        self.sel_index = len(d.objects) - 1
        self._commit("Add object")
        self.refresh_all()

    def delete_object(self) -> None:
        if self.doc.system == "a2600" or self.selected_object() is None:
            return
        self._begin()
        del self.doc.objects[self.sel_index]
        self.sel_index = -1
        self._commit("Delete object")
        self.refresh_all()

    # ------------------------------------------------------------ graphics editing
    def edit_current_graphic(self) -> None:
        o = self.selected_object()
        d = self.doc
        lay = self.current_layer()
        if o is not None:
            if d.system in ("nes", "gb"):
                base = 256 if d.system == "nes" else 0
                self.edit_tiles(base + int(o.get("tile", 0)), int(o.get("w", 1)), int(o.get("h", 1)), sprite=True,
                                pal_index=int(o.get("palette", 0)))
            elif o.get("sprite") in d.sprites:
                self.edit_sprite(o["sprite"])
            return
        if lay is not None and lay.kind == "tiles":
            v = self._layer_value(lay)
            if 0 <= v < len(d.tiles):
                self.edit_tiles(v, 1, 1)

    def edit_tiles(self, first: int, tw: int, th: int, sprite: bool = False, pal_index: int | None = None) -> bool:
        """Edit a block of tiles (a metasprite is laid out 16 tiles per row)."""
        d = self.doc
        tsz_w, tsz_h = d.tile_w, d.tile_h
        stride = 16
        W, H = tw * tsz_w, th * tsz_h
        px = bytearray(W * H)
        idx = lambda r, c: first + r * stride + c          # noqa: E731
        for r in range(th):
            for c in range(tw):
                t = d.tile(idx(r, c))
                for y in range(tsz_h):
                    px[(r * tsz_h + y) * W + c * tsz_w:(r * tsz_h + y) * W + (c + 1) * tsz_w] = \
                        t[y * tsz_w:(y + 1) * tsz_w]
        if d.system == "nes":
            pb = NES.palette_bytes(d)
            p = pal_index if pal_index is not None else self.values.get("Attributes", 1)
            base = ((4 if sprite else 0) + (p & 3)) * 4
            master = NES.master_palette()
            colors = [master[pb[base + i] & 0x3F] for i in range(4)]
        elif d.system == "gb":
            sh = self.mod.shades()
            bgp = int(d.settings.get("obp0" if sprite else "bgp", 0xE4))
            colors = [sh[(bgp >> (2 * i)) & 3] for i in range(4)]
        else:
            colors = self.mod.palette_rgb(d)
        dlg = PixelEditor(self, f"Tile {first}" + (f" ({tw}x{th})" if tw * th > 1 else ""), W, H, px, colors)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        _w, _h, new = dlg.result_pixels()
        self._begin()
        while len(d.tiles) <= idx(th - 1, tw - 1):
            d.tiles.append(bytearray(tsz_w * tsz_h))
        for r in range(th):
            for c in range(tw):
                t = bytearray(tsz_w * tsz_h)
                for y in range(tsz_h):
                    t[y * tsz_w:(y + 1) * tsz_w] = new[(r * tsz_h + y) * W + c * tsz_w:(r * tsz_h + y) * W +
                                                       (c + 1) * tsz_w]
                d.tiles[idx(r, c)] = t
        self._commit("Edit tiles")
        self.refresh_all()
        return True

    def edit_sprite(self, name: str) -> bool:
        d = self.doc
        s = d.sprites.get(name)
        if s is None:
            return False
        if d.system == "a2600":
            colors, resizable = [(20, 20, 20), (240, 240, 240)], "h"
        else:
            colors, resizable = self.mod.palette_rgb(d), "wh"
        dlg = PixelEditor(self, f"Sprite {name}", s["w"], s["h"], s["pixels"], colors, resizable)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        w, h, px = dlg.result_pixels()
        self._begin()
        s.update({"w": w, "h": h, "pixels": bytearray(px)})
        self._commit("Edit sprite")
        self.refresh_all()
        return True

    def add_tile(self) -> None:
        d = self.doc
        self._begin()
        d.tiles.append(bytearray(d.tile_w * d.tile_h))
        self._commit("New tile")
        lay = self.current_layer()
        if lay is not None:
            self.values[lay.name] = len(d.tiles) - 1
        self.refresh_all()
        self.edit_tiles(len(d.tiles) - 1, 1, 1)

    def import_tiles(self, path=None, first: int = 0) -> int:
        """Load tiles made in the retro tile editor (or any CHR data): NES .chr / .nes (CHR ROM), Game Boy
        .2bpp / .gb. Replaces tiles from *first* on; returns the number of tiles read."""
        from .compat import chr_offset, decode_tile
        d = self.doc
        if d.system not in ("nes", "gb"):
            return 0
        if path is None:
            filt = "NES tiles (*.chr *.nes)" if d.system == "nes" else "Game Boy tiles (*.2bpp *.chr *.gb)"
            f, _ = QFileDialog.getOpenFileName(self, "Import Tiles", str(self.path.parent if self.path else ""),
                                               filt + ";;All files (*)")
            if not f:
                return 0
            path = f
        data = Path(path).read_bytes()
        off = chr_offset(data) if d.system == "nes" else 0
        n = max(0, min(512 if d.system == "nes" else 256, (len(data) - off) // 16) - first)
        if n <= 0:
            return 0
        self._begin()
        fmt = "nes" if d.system == "nes" else "gb"
        for i in range(n):
            while len(d.tiles) <= first + i:
                d.tiles.append(bytearray(64))
            d.tiles[first + i] = decode_tile(fmt, data[off + i * 16:off + i * 16 + 16])
        self._commit("Import tiles")
        self.refresh_all()
        self.log(f"[game designer] imported {n} tiles from {Path(path).name}")
        return n

    def edit_nes_palettes(self) -> None:
        dlg = NESPaletteDialog(self, (self.doc.palette + NES.DEFAULT_PALETTES)[:8], NES.master_palette())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._begin()
            self.doc.palette = dlg.pals
            self._commit("Edit palettes")
            self.refresh_all()

    def edit_vga_color(self, i: int) -> None:
        r, g, b = self.mod.palette_rgb(self.doc)[i]
        c = QColorDialog.getColor(QColor(r, g, b), self, f"Colour {i}")
        if not c.isValid():
            return
        self._begin()
        while len(self.doc.palette) < 256:
            self.doc.palette.append([0, 0, 0])
        self.doc.palette[i] = [c.red() >> 2, c.green() >> 2, c.blue() >> 2]
        self._commit("Edit colour")
        self.refresh_all()

    # ------------------------------------------------------------ files
    def gen_folder(self) -> Path:
        if self.path is not None:
            return gen_dir(self.path)
        import tempfile
        return Path(tempfile.gettempdir()) / "radide-retro-design" / ident(self.doc.name)

    def save(self, path=None) -> bool:
        if path is not None:
            self.path = Path(path)
        if self.path is None:
            f, _ = QFileDialog.getSaveFileName(self, "Save Design", f"{self.doc.name}{self.mod.EXT}",
                                               f"{TITLES[self.doc.system]} (*{self.mod.EXT})")
            if not f:
                return False
            self.path = Path(f)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.doc.name != self.path.stem and self.path.stem:
            self.doc.name = self.path.stem
        self.doc.save(self.path)
        self.undo.setClean()
        self.modifiedChanged.emit(False)
        try:
            self.generate()
        except Exception as e:  # noqa: BLE001 - saving must not fail because of the generator
            self.log(f"[game designer] generate failed: {e}")
        self.saved.emit()
        return True

    def maybe_close(self) -> bool:
        if not self.is_modified():
            return True
        r = QMessageBox.question(self, "Game Designer", f"Save changes to {self.title().rstrip('*')}?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Yes:
            return self.save()
        return True

    def generate(self) -> dict:
        info = self.mod.generate(self.doc, self.gen_folder())
        self.warnings = list(info.get("warnings", []))
        self.log(f"[game designer] generated {len(info['files'])} files in {self.gen_folder()}")
        for w in self.warnings:
            self.log(f"  warning: {w}")
        return info

    def export_png(self, path=None) -> Path | None:
        if path is None:
            start = str((self.path.parent if self.path else Path.home()) / f"{self.doc.name}.png")
            f, _ = QFileDialog.getSaveFileName(self, "Export PNG", start, "PNG image (*.png)")
            if not f:
                return None
            path = f
        img = self.canvas.image
        ax, ay = self.canvas.aspect
        out = img.convertToFormat(QImage.Format.Format_RGB32).scaled(
            QSize(img.width() * ax, img.height() * ay), Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation)
        out.save(str(path))
        return Path(path)

    # ------------------------------------------------------------ build & run
    def build_and_run(self, run: bool = True, wait: bool = False, download: bool = True):
        """Generate, build with the system's toolchain (in a thread), check, then start the emulator."""
        if self._busy:
            return None
        self._busy = True
        self.a_run.setEnabled(False)
        doc = Design.from_dict(self.doc.to_dict())
        out = self.gen_folder()
        system = self.doc.system
        result = {}

        def work():
            from .build import build, run as run_rom
            try:
                res = build(doc, out, log=self._log_queue.append, download=download)
                result.update(res)
                if res.get("ok") and run:
                    proc = run_rom(res, system, log=self._log_queue.append)
                    result["process"] = proc
                    if proc is not None:
                        self._log_queue.append(f"[game designer] started {Path(res['rom']).name} in the emulator")
            except Exception as e:  # noqa: BLE001
                self._log_queue.append(f"*** build failed: {e}")
            finally:
                self._busy = False

        self._log_queue.append(f"[game designer] building {doc.name} ({TITLES[system]})...")
        th = threading.Thread(target=work, daemon=True)
        th.start()
        if wait:
            th.join()
            self._tick()
        QTimer.singleShot(200, self._watch_build)
        self.last_build = result
        return result

    def _watch_build(self) -> None:
        if self._busy:
            QTimer.singleShot(200, self._watch_build)
            return
        self.a_run.setEnabled(True)
        if self.last_build and self.last_build.get("missing"):
            self.status.setText(f"{self.last_build['missing']} is not installed - see the Output window")
