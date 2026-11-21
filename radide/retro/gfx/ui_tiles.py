"""Tile / sprite editor working directly on the bytes of a ROM or binary file.

Left: the tile sheet (a page of ``columns x rows`` tiles from the offset); click a tile to edit it, drag with
the Select tool to choose a block.  Right: the zoomed editing area (pencil, fill, line; right-click picks a
colour), the colour slots, flip / rotate, and for Atari 2600 player graphics a preview with reflect and NUSIZ.
File > Save (Ctrl+S) writes the bytes back into the file; other open editors of the file are refreshed.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QKeySequence, QPainter, QPen
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QScrollArea,
                             QSpinBox, QSplitter, QToolBar, QVBoxLayout, QWidget)

from . import atari2600, palettes, pngio
from .codecs import FORMATS, get_format, guess_format
from .tilesheet import (ByteHistory, TileSheet, copy_block, draw_line, flip_h, flip_v, flood_fill, rotate_ccw,
                        rotate_cw, suggested_offset)
from .ui_common import HexSpin, PaletteBar, RetroDoc, block_image


# ===================================================================== sheet view
class SheetView(QWidget):
    """A page of tiles; emits the selected tile rectangle (tx, ty, tcols, trows)."""
    selected = pyqtSignal(int, int, int, int)
    hovered = pyqtSignal(int)

    def __init__(self, editor: "TileEditor"):
        super().__init__()
        self.ed = editor
        self.zoom = 3
        self.grid = True
        self.sel = (0, 0, 1, 1)
        self._drag: QPoint | None = None
        self.setMouseTracking(True)

    def cell(self) -> tuple[int, int]:
        s = self.ed.sheet
        return s.tw * s.fmt.aspect * self.zoom, s.th * self.zoom

    def sizeHint(self) -> QSize:
        cw, ch = self.cell()
        return QSize(cw * self.ed.sheet.cols + 1, ch * self.ed.sheet.rows + 1)

    def refresh(self) -> None:
        self.setFixedSize(self.sizeHint())
        self.update()

    def paintEvent(self, _e) -> None:
        s = self.ed.sheet
        p = QPainter(self)
        img = block_image(s.page(), self.ed.palette.colors(), s.fmt.aspect)
        p.drawImage(QRect(0, 0, img.width() * self.zoom, img.height() * self.zoom), img)
        cw, ch = self.cell()
        if self.grid:
            p.setPen(QPen(QColor(90, 90, 120, 160), 1))
            for i in range(s.cols + 1):
                p.drawLine(i * cw, 0, i * cw, s.rows * ch)
            for j in range(s.rows + 1):
                p.drawLine(0, j * ch, s.cols * cw, j * ch)
        tx, ty, tc, tr = self.sel
        p.setPen(QPen(QColor("#ff3030"), 2))
        p.drawRect(tx * cw, ty * ch, tc * cw, tr * ch)
        p.end()

    def _tile_xy(self, pos) -> tuple[int, int]:
        cw, ch = self.cell()
        s = self.ed.sheet
        return (max(0, min(s.cols - 1, int(pos.x()) // cw)), max(0, min(s.rows - 1, int(pos.y()) // ch)))

    def mousePressEvent(self, e) -> None:
        tx, ty = self._tile_xy(e.position())
        self._drag = QPoint(tx, ty)
        if self.ed.tool == "select":
            self.set_selection(tx, ty, 1, 1)
        else:
            n = self.ed.block_size
            s = self.ed.sheet
            self.set_selection(min(tx, s.cols - n) if s.cols >= n else 0,
                               min(ty, s.rows - n) if s.rows >= n else 0,
                               min(n, s.cols), min(n, s.rows))

    def mouseMoveEvent(self, e) -> None:
        tx, ty = self._tile_xy(e.position())
        self.hovered.emit(self.ed.sheet.tile_at(tx, ty))
        if self._drag is not None and self.ed.tool == "select":
            x0, y0 = self._drag.x(), self._drag.y()
            self.set_selection(min(x0, tx), min(y0, ty), abs(tx - x0) + 1, abs(ty - y0) + 1)

    def mouseReleaseEvent(self, _e) -> None:
        self._drag = None

    def set_selection(self, tx: int, ty: int, tc: int, tr: int) -> None:
        self.sel = (tx, ty, max(1, tc), max(1, tr))
        self.selected.emit(*self.sel)
        self.update()


# ===================================================================== zoomed pixel editor
class PixelView(QWidget):
    def __init__(self, editor: "TileEditor"):
        super().__init__()
        self.ed = editor
        self.block: list[list[int]] = [[0] * 8 for _ in range(8)]
        self.work: list[list[int]] | None = None      # block being drawn (stroke / line preview)
        self._start: tuple[int, int] | None = None
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)

    def scale(self) -> tuple[int, int]:
        h = len(self.block)
        w = len(self.block[0]) if h else 1
        asp = self.ed.sheet.fmt.aspect
        z = max(2, min((self.width() - 2) // max(1, w * asp), (self.height() - 2) // max(1, h)))
        return z * asp, z

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(30, 30, 34))
        b = self.work or self.block
        sx, sy = self.scale()
        colors = self.ed.palette.colors()
        for y, row in enumerate(b):
            for x, v in enumerate(row):
                r, g, bb = colors[v % len(colors)] if v >= 0 else (60, 60, 60)
                p.fillRect(x * sx, y * sy, sx, sy, QColor(r, g, bb))
        if self.ed.grid_check.isChecked() and sy >= 6:
            p.setPen(QPen(QColor(100, 100, 130, 120), 1))
            h, w = len(b), len(b[0]) if b else 0
            for x in range(w + 1):
                p.drawLine(x * sx, 0, x * sx, h * sy)
            for y in range(h + 1):
                p.drawLine(0, y * sy, w * sx, y * sy)
            p.setPen(QPen(QColor(255, 200, 0, 170), 1))
            tw, th = self.ed.sheet.tw, self.ed.sheet.th
            for x in range(0, w + 1, tw):
                p.drawLine(x * sx, 0, x * sx, h * sy)
            for y in range(0, h + 1, th):
                p.drawLine(0, y * sy, w * sx, y * sy)
        p.end()

    def _xy(self, pos) -> tuple[int, int] | None:
        sx, sy = self.scale()
        x, y = int(pos.x()) // sx, int(pos.y()) // sy
        if 0 <= y < len(self.block) and 0 <= x < len(self.block[0]):
            return x, y
        return None

    def mousePressEvent(self, e) -> None:
        xy = self._xy(e.position())
        if xy is None:
            return
        x, y = xy
        if e.button() == Qt.MouseButton.RightButton:            # eyedropper
            v = self.block[y][x]
            if v >= 0:
                self.ed.palette.current = v
                self.ed.palette.update()
            return
        color = self.ed.palette.current
        tool = self.ed.tool
        if tool == "fill":
            self.ed.commit_block(flood_fill(self.block, x, y, color), "Fill")
            return
        self._start = (x, y)
        self.work = copy_block(self.block)
        if tool in ("pencil", "select") and self.work[y][x] >= 0:
            self.work[y][x] = color
        self.update()

    def mouseMoveEvent(self, e) -> None:
        xy = self._xy(e.position())
        if xy is not None:
            self.ed.show_pixel_status(*xy)
        if self.work is None or xy is None or self._start is None:
            return
        x, y = xy
        color = self.ed.palette.current
        if self.ed.tool == "line":
            self.work = draw_line(self.block, self._start[0], self._start[1], x, y, color)
        else:
            self.work = draw_line(self.work, self._start[0], self._start[1], x, y, color)
            self._start = (x, y)
        self.update()

    def mouseReleaseEvent(self, _e) -> None:
        if self.work is not None:
            w, self.work, self._start = self.work, None, None
            self.ed.commit_block(w, "Line" if self.ed.tool == "line" else "Draw")


# ===================================================================== Atari 2600 preview
class PlayerPreview(QWidget):
    """The player bytes as the TIA draws them: 160 colour clocks per line, reflect and NUSIZ applied."""

    def __init__(self, editor: "TileEditor"):
        super().__init__()
        self.ed = editor
        self.nusiz = 0
        self.reflect = False
        self.setMinimumHeight(60)

    def sizeHint(self) -> QSize:
        return QSize(322, 80)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        colors = self.ed.palette.colors()
        bg, fg = QColor(*colors[0]), QColor(*colors[1 % len(colors)])
        p.fillRect(self.rect(), bg)
        rows = [r[:8] for r in self.ed.pixels.block]
        h = max(1, len(rows))
        sy = max(1, min(4, (self.height() - 4) // h))
        sx = max(1, self.width() // 170)
        for y, row in enumerate(rows):
            byte = sum((1 << (7 - i)) for i, v in enumerate(row) if v > 0)
            line = atari2600.player_scanline(byte, self.nusiz, self.reflect, x=8)
            for x, on in enumerate(line):
                if on:
                    p.fillRect(x * sx, 2 + y * sy, sx, sy, fg)
        p.end()


# ===================================================================== the editor document
class TileEditor(RetroDoc):
    kind = "Tile Editor"

    def __init__(self, win=None, path=None, data: bytes | None = None, fmt: str | None = None, parent=None):
        super().__init__(win, parent)
        self.history = ByteHistory()
        self.tool = "pencil"
        self.block_size = 1
        key = fmt or (guess_format(path) if path else "nes")
        raw = bytearray(data) if data is not None else bytearray(Path(path).read_bytes()) if path else bytearray(8192)
        self.retro_path = Path(path) if path else None
        self.sheet = TileSheet(raw, get_format(key))
        self.sheet.offset = suggested_offset(raw, key)
        self.edit_origin = (0, 0, 1, 1)
        self._build()
        self._apply_format(key, keep_offset=True)
        self.history.mark_clean()

    # ------------------------------------------------------------ UI
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        tb = QToolBar()
        tb.setObjectName("retroTileNav")
        self.fmt_combo = QComboBox()
        for k, f in FORMATS.items():
            self.fmt_combo.addItem(f.name, k)
        self.fmt_combo.setToolTip("Tile format")
        self.fmt_combo.currentIndexChanged.connect(lambda _i: self._apply_format(self.fmt_combo.currentData()))
        tb.addWidget(QLabel(" Format "))
        tb.addWidget(self.fmt_combo)
        self.h_label = QLabel(" Height ")
        self.h_spin = QSpinBox()
        self.h_spin.setRange(1, 255)
        self.h_spin.setValue(8)
        self.h_spin.setToolTip("Sprite height in scan lines (bytes per Atari 2600 player graphic)")
        self.h_spin.valueChanged.connect(self._on_height)
        self.a_h_label = tb.addWidget(self.h_label)
        self.a_h_spin = tb.addWidget(self.h_spin)
        self.bottom_up = QCheckBox("Upside down")
        self.bottom_up.setToolTip("The bytes are stored bottom line first (common in 2600 kernels)")
        self.bottom_up.toggled.connect(self._on_bottom_up)
        self.a_bottom_up = tb.addWidget(self.bottom_up)
        tb.addSeparator()
        tb.addWidget(QLabel(" Offset "))
        self.off_spin = HexSpin()
        self.off_spin.valueChanged.connect(self._on_offset)
        tb.addWidget(self.off_spin)
        for text, tip, delta in (("-1", "Back one byte", ("byte", -1)), ("+1", "Forward one byte", ("byte", 1)),
                                 ("-T", "Back one tile", ("tile", -1)), ("+T", "Forward one tile", ("tile", 1)),
                                 ("-R", "Back one row", ("row", -1)), ("+R", "Forward one row", ("row", 1)),
                                 ("PgUp", "Previous page", ("page", -1)), ("PgDn", "Next page", ("page", 1))):
            a = tb.addAction(text, lambda d=delta: self.step(*d))
            a.setToolTip(tip)
        tb.addSeparator()
        tb.addWidget(QLabel(" Columns "))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 64)
        self.cols_spin.setValue(16)
        self.cols_spin.valueChanged.connect(self._on_geometry)
        tb.addWidget(self.cols_spin)
        tb.addWidget(QLabel(" Rows "))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 128)
        self.rows_spin.setValue(16)
        self.rows_spin.valueChanged.connect(self._on_geometry)
        tb.addWidget(self.rows_spin)
        tb.addWidget(QLabel(" Zoom "))
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(1, 12)
        self.zoom_spin.setValue(3)
        self.zoom_spin.valueChanged.connect(self._on_zoom)
        tb.addWidget(self.zoom_spin)
        self.grid_check = QCheckBox("Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self._on_grid)
        tb.addWidget(self.grid_check)
        lay.addWidget(tb)

        tb2 = QToolBar()
        tb2.setObjectName("retroTileTools")
        group = QActionGroup(self)
        self.tool_actions: dict[str, QAction] = {}
        for key, text in (("pencil", "Pencil"), ("fill", "Fill"), ("line", "Line"), ("select", "Select")):
            a = QAction(text, self, checkable=True)
            a.triggered.connect(lambda _c, k=key: self.set_tool(k))
            group.addAction(a)
            tb2.addAction(a)
            self.tool_actions[key] = a
        self.tool_actions["pencil"].setChecked(True)
        tb2.addWidget(QLabel(" Edit "))
        self.block_combo = QComboBox()
        for n in (1, 2, 4, 8):
            self.block_combo.addItem(f"{n}x{n} tiles", n)
        self.block_combo.currentIndexChanged.connect(self._on_block_size)
        tb2.addWidget(self.block_combo)
        tb2.addSeparator()
        tb2.addAction("Flip H", lambda: self.transform(flip_h, "Flip Horizontal"))
        tb2.addAction("Flip V", lambda: self.transform(flip_v, "Flip Vertical"))
        tb2.addAction("Rotate Right", lambda: self.transform(rotate_cw, "Rotate", square=True))
        tb2.addAction("Rotate Left", lambda: self.transform(rotate_ccw, "Rotate", square=True))
        tb2.addAction("Clear", lambda: self.transform(lambda b: [[0 if v >= 0 else v for v in r] for r in b],
                                                      "Clear"))
        tb2.addSeparator()
        self.a_undo = tb2.addAction("Undo", self.undo)
        self.a_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.a_redo = tb2.addAction("Redo", self.redo)
        self.a_redo.setShortcut(QKeySequence.StandardKey.Redo)
        for a in (self.a_undo, self.a_redo):
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        tb2.addSeparator()
        tb2.addAction("Export PNG...", self.export_png_dialog)
        tb2.addAction("Import PNG...", self.import_png_dialog)
        tb2.addAction("Write to File", self.save)
        tb2.addSeparator()
        tb2.addWidget(QLabel(" Palette "))
        self.sys_combo = QComboBox()
        for k, (name, _c) in palettes.SYSTEM_PALETTES.items():
            self.sys_combo.addItem(name, k)
        self.sys_combo.currentIndexChanged.connect(self._on_system)
        tb2.addWidget(self.sys_combo)
        lay.addWidget(tb2)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.sheet_view = SheetView(self)
        self.sheet_view.selected.connect(self._on_selected)
        self.sheet_view.hovered.connect(self._on_hover)
        sc = QScrollArea()
        sc.setWidget(self.sheet_view)
        sc.setWidgetResizable(False)
        sc.setMinimumWidth(280)
        split.addWidget(sc)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 0, 0, 0)
        self.palette = PaletteBar()
        self.palette.slotsChanged.connect(self._redraw)
        self.pixels = PixelView(self)
        rl.addWidget(self.pixels, 1)
        rl.addWidget(QLabel("Colors (click = draw, double-click = system color, right-click in the editor = pick)"))
        rl.addWidget(self.palette)
        self.preview_box = QWidget()
        pl = QVBoxLayout(self.preview_box)
        pl.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel("NUSIZ"))
        self.nusiz_combo = QComboBox()
        for i, n in enumerate(atari2600.NUSIZ_NAMES):
            self.nusiz_combo.addItem(f"{i}: {n}", i)
        self.nusiz_combo.currentIndexChanged.connect(self._on_nusiz)
        row.addWidget(self.nusiz_combo)
        self.reflect_check = QCheckBox("Reflect (REFP)")
        self.reflect_check.toggled.connect(self._on_nusiz)
        row.addWidget(self.reflect_check)
        row.addStretch(1)
        pl.addLayout(row)
        self.preview = PlayerPreview(self)
        pl.addWidget(self.preview)
        self.asm_label = QLabel()
        self.asm_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.asm_label.setStyleSheet("font-family: Consolas, monospace;")
        pl.addWidget(self.asm_label)
        rl.addWidget(self.preview_box)
        self.status = QLabel()
        rl.addWidget(self.status)
        split.addWidget(right)
        split.setSizes([520, 420])
        lay.addWidget(split, 1)

    # ------------------------------------------------------------ format / navigation
    def _apply_format(self, key: str, keep_offset: bool = False) -> None:
        f = get_format(key)
        self.sheet.fmt = f
        if self.fmt_combo.currentData() != key:
            self.fmt_combo.blockSignals(True)
            self.fmt_combo.setCurrentIndex(self.fmt_combo.findData(key))
            self.fmt_combo.blockSignals(False)
        is2600 = key == "a2600"
        self.a_h_label.setVisible(f.var_height)
        self.a_h_spin.setVisible(f.var_height)
        self.a_bottom_up.setVisible(f.var_height)
        self.preview_box.setVisible(is2600)
        if is2600 and self.cols_spin.value() == 16:
            self.cols_spin.blockSignals(True)
            self.cols_spin.setValue(8)
            self.cols_spin.blockSignals(False)
            self.sheet.cols = 8
        self.sheet.tile_h = self.h_spin.value()
        system = f.system
        self.sys_combo.blockSignals(True)
        self.sys_combo.setCurrentIndex(self.sys_combo.findData(system))
        self.sys_combo.blockSignals(False)
        self.palette.set_slots(system, palettes.default_slots(system, f.colors))
        self.palette.current = min(1, f.colors - 1)
        if not keep_offset:
            self.sheet.offset = min(self.sheet.offset, max(0, len(self.sheet.data) - 1))
        self.off_spin.setMaximum(max(0, len(self.sheet.data) - 1))
        self._sync_offset()
        self._on_selected(*self.sheet_view.sel)

    def _sync_offset(self) -> None:
        self.off_spin.blockSignals(True)
        self.off_spin.setValue(self.sheet.offset)
        self.off_spin.blockSignals(False)
        self.sheet_view.refresh()

    def set_offset(self, off: int) -> None:
        self.sheet.offset = max(0, min(off, max(0, len(self.sheet.data) - 1)))
        self._sync_offset()
        self._load_block()

    def step(self, unit: str, n: int) -> None:
        s = self.sheet
        size = {"byte": 1, "tile": s.stride, "row": s.stride * s.cols, "page": s.page_bytes}[unit]
        self.set_offset(s.offset + n * size)

    def _on_offset(self, v: int) -> None:
        self.sheet.offset = v
        self.sheet_view.refresh()
        self._load_block()

    def _on_geometry(self, _v=None) -> None:
        self.sheet.cols, self.sheet.rows = self.cols_spin.value(), self.rows_spin.value()
        tx, ty, tc, tr = self.sheet_view.sel
        self.sheet_view.sel = (min(tx, self.sheet.cols - 1), min(ty, self.sheet.rows - 1),
                               min(tc, self.sheet.cols), min(tr, self.sheet.rows))
        self.sheet_view.refresh()
        self._on_selected(*self.sheet_view.sel)

    def _on_height(self, v: int) -> None:
        self.sheet.tile_h = v
        self.sheet_view.refresh()
        self._load_block()

    def _on_bottom_up(self, on: bool) -> None:
        self.sheet.bottom_up = on
        self._load_block()
        self.sheet_view.update()

    def _on_zoom(self, v: int) -> None:
        self.sheet_view.zoom = v
        self.sheet_view.refresh()

    def _on_grid(self, on: bool) -> None:
        self.sheet_view.grid = on
        self._redraw()

    def _on_system(self, _i=None) -> None:
        system = self.sys_combo.currentData()
        self.palette.set_slots(system, palettes.default_slots(system, self.sheet.fmt.colors))
        self._redraw()

    def _on_block_size(self, _i=None) -> None:
        self.block_size = self.block_combo.currentData()
        tx, ty, _tc, _tr = self.sheet_view.sel
        n = self.block_size
        s = self.sheet
        self.sheet_view.set_selection(min(tx, max(0, s.cols - n)), min(ty, max(0, s.rows - n)),
                                      min(n, s.cols), min(n, s.rows))

    def _on_nusiz(self, _v=None) -> None:
        self.preview.nusiz = self.nusiz_combo.currentData() or 0
        self.preview.reflect = self.reflect_check.isChecked()
        self.preview.update()

    def set_tool(self, key: str) -> None:
        self.tool = key
        self.tool_actions[key].setChecked(True)

    # ------------------------------------------------------------ selection / block
    def _on_selected(self, tx, ty, tc, tr) -> None:
        self.edit_origin = (tx, ty, tc, tr)
        self._load_block()

    def _load_block(self) -> None:
        tx, ty, tc, tr = self.edit_origin
        self.pixels.block = self.sheet.get_block(tx, ty, tc, tr)
        self.pixels.update()
        self.preview.update()
        idx = self.sheet.tile_at(tx, ty)
        off = self.sheet.tile_offset(idx)
        self.status.setText(f"Tile {idx} (0x{idx:X}) at offset 0x{off:X} - {tc}x{tr} tiles, "
                            f"{self.sheet.fmt.name}, file size 0x{len(self.sheet.data):X}")
        if self.sheet.fmt.key == "a2600":
            rows = self.sheet.get_tile(idx) or []
            vals = [sum(1 << (7 - i) for i, v in enumerate(r) if v > 0) for r in rows]
            if self.sheet.bottom_up:
                vals = vals[::-1]
            self.asm_label.setText("\n".join(f"    .byte %{v:08b}  ; ${v:02X}" for v in vals[:24]))

    def _on_hover(self, idx: int) -> None:
        off = self.sheet.tile_offset(idx)
        self.status.setText(f"Tile {idx} (0x{idx:X}) at offset 0x{off:X}")

    def show_pixel_status(self, x: int, y: int) -> None:
        tx, ty, _tc, _tr = self.edit_origin
        t = self.sheet.tile_at(tx + x // self.sheet.tw, ty + y // self.sheet.th)
        v = self.pixels.block[y][x] if y < len(self.pixels.block) and x < len(self.pixels.block[0]) else -1
        self.status.setText(f"Pixel {x},{y} in tile {t} (offset 0x{self.sheet.tile_offset(t):X}) = color {v}")

    def _redraw(self) -> None:
        self.sheet_view.update()
        self.pixels.update()
        self.preview.update()

    # ------------------------------------------------------------ editing
    def commit_block(self, block, _what: str = "Edit") -> None:
        tx, ty, _tc, _tr = self.edit_origin
        changes = self.sheet.set_block(tx, ty, block)
        if changes:
            self.history.push(changes)
            self.set_modified(self.history.modified)
        self._load_block()
        self.sheet_view.update()

    def transform(self, fn, what: str, square: bool = False) -> None:
        b = self.pixels.block
        if square and len(b) != len(b[0]):
            QMessageBox.information(self, "Tile Editor", "Rotating needs a square block "
                                                         "(the same number of pixels across and down).")
            return
        self.commit_block(fn(b), what)

    def undo(self) -> None:
        if self.history.undo(self.sheet.data) is not None:
            self.set_modified(self.history.modified)
            self._load_block()
            self.sheet_view.update()

    def redo(self) -> None:
        if self.history.redo(self.sheet.data) is not None:
            self.set_modified(self.history.modified)
            self._load_block()
            self.sheet_view.update()

    # ------------------------------------------------------------ PNG
    def export_png(self, path, whole_page: bool = True, scale: int = 1) -> Path:
        s = self.sheet
        block = s.page() if whole_page else self.pixels.block
        return pngio.export_png(path, block, self.palette.colors(), s.fmt.aspect, scale)

    def import_png(self, path) -> int:
        """Quantise a PNG into the tiles from the selected tile on; returns the number of tiles changed."""
        from PIL import Image
        s = self.sheet
        with Image.open(path) as img:
            w, h = img.width // s.fmt.aspect, img.height
            tx, ty, _tc, _tr = self.edit_origin
            tcols = max(1, min(-(-w // s.tw), s.cols - tx))
            trows = max(1, min(-(-h // s.th), s.rows - ty))
            block = pngio.image_to_block(img, self.palette.colors(), tcols * s.tw, trows * s.th, s.fmt.aspect)
        changes = s.set_block(tx, ty, block)
        self.history.push(changes)
        self.set_modified(self.history.modified)
        self._load_block()
        self.sheet_view.update()
        return len(changes)

    def export_png_dialog(self) -> None:
        start = str((self.retro_path.with_suffix(".png")) if self.retro_path else "tiles.png")
        f, _ = QFileDialog.getSaveFileName(self, "Export PNG", start, "PNG image (*.png)")
        if f:
            self.export_png(f, whole_page=True)
            self.log(f"[tile editor] exported the page to {f}")

    def import_png_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Import PNG", "", "Images (*.png *.bmp *.gif)")
        if f:
            n = self.import_png(f)
            self.log(f"[tile editor] imported {f}: {n} tiles changed")

    # ------------------------------------------------------------ file
    def save(self) -> bool:
        if self.retro_path is None:
            f, _ = QFileDialog.getSaveFileName(self, "Save Binary", "tiles.chr", "All files (*)")
            if not f:
                return False
            self.retro_path = Path(f)
        try:
            self.retro_path.write_bytes(bytes(self.sheet.data))
        except OSError as e:
            QMessageBox.warning(self, "Tile Editor", f"Cannot write the file:\n{e}")
            return False
        self.history.mark_clean()
        self.set_modified(False)
        self.log(f"[tile editor] wrote {len(self.sheet.data)} bytes to {self.retro_path}")
        self.notify_written(self.retro_path)
        return True

    def reload_from_disk(self) -> None:
        if self.retro_path is None or not self.retro_path.is_file():
            return
        if self.is_modified():
            self.log(f"[tile editor] {self.retro_path.name} changed on disk; the tile editor has unsaved "
                     f"changes and kept them")
            return
        self.sheet.data = bytearray(self.retro_path.read_bytes())
        self.history = ByteHistory()
        self.off_spin.setMaximum(max(0, len(self.sheet.data) - 1))
        self._load_block()
        self.sheet_view.refresh()
