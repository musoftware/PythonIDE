"""Tile map / metatile editor (NES nametables, Game Boy BG maps, generic byte maps).

Left: the tile set (tiles read from a CHR / ROM file at an offset); click a tile to paint with it.
Centre: the map; left button paints, right button picks the tile under the mouse.  Metatiles are 2x2 blocks:
"Make Metatile" takes the 2x2 cells at the last clicked cell, the Metatile tool stamps them.
The map exports as assembler (ca65, DASM, RGBDS, NASM, ACME, WLA) or C data, optionally compressed into
metatiles, and can be read from / written into a ROM.  The document is saved as ``.rtmap`` (JSON).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
                             QScrollArea, QSpinBox, QSplitter, QToolBar, QVBoxLayout, QWidget)

from . import palettes
from .codecs import FORMATS, get_format
from .tilemap import ASM_SYNTAX, KINDS, TileMap
from .tilesheet import TileSheet, suggested_offset
from .ui_common import HexSpin, RetroDoc, block_image

NES_SUBPALETTES = [[0x0F, 0x16, 0x27, 0x30], [0x0F, 0x1A, 0x2A, 0x30], [0x0F, 0x12, 0x22, 0x30],
                   [0x0F, 0x07, 0x17, 0x28]]


class TileSource:
    """The tiles a map refers to: a file + offset + format (decoded once, cached per palette)."""

    def __init__(self):
        self.sheet: TileSheet | None = None
        self.system = "nes"
        self.palettes = [list(p) for p in NES_SUBPALETTES]
        self._cache: dict[tuple[int, int], object] = {}

    def load(self, path: str, offset: int, fmt: str) -> None:
        data = Path(path).read_bytes()
        f = get_format(fmt)
        self.sheet = TileSheet(bytearray(data), f, offset=offset, cols=16, rows=16)
        self.system = f.system
        if f.system != "nes":
            base = palettes.default_slots(f.system, f.colors)
            self.palettes = [list(base) for _ in range(4)]
        self._cache.clear()

    def image(self, tile: int, pal: int):
        key = (tile, pal)
        if key not in self._cache:
            colors = self.colors(pal)
            block = self.sheet.get_tile(tile) if self.sheet else None
            if block is None:
                block = [[-1] * 8 for _ in range(8)]
            self._cache[key] = block_image(block, colors, self.sheet.fmt.aspect if self.sheet else 1)
        return self._cache[key]

    def colors(self, pal: int):
        sp = palettes.palette(self.system)
        return [sp[i % len(sp)] for i in self.palettes[pal % len(self.palettes)]]


class TilePicker(QWidget):
    def __init__(self, ed: "TilemapEditor"):
        super().__init__()
        self.ed = ed
        self.z = 2

    def sizeHint(self) -> QSize:
        return QSize(16 * 8 * self.z + 1, 16 * 8 * self.z + 1)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(30, 30, 34))
        s = 8 * self.z
        for t in range(256):
            p.drawImage(QRect((t % 16) * s, (t // 16) * s, s, s), self.ed.src.image(t, self.ed.pal_spin.value()))
        t = self.ed.cur_tile
        p.setPen(QPen(QColor("#ff3030"), 2))
        p.drawRect((t % 16) * s, (t // 16) * s, s, s)
        p.end()

    def mousePressEvent(self, e) -> None:
        s = 8 * self.z
        x, y = int(e.position().x()) // s, int(e.position().y()) // s
        if 0 <= x < 16 and 0 <= y < 16:
            self.ed.cur_tile = y * 16 + x
            self.ed.set_tool("tile")
            self.update()
            self.ed.update_status()


class MapCanvas(QWidget):
    def __init__(self, ed: "TilemapEditor"):
        super().__init__()
        self.ed = ed
        self.z = 2
        self._painting = False
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        m = self.ed.map
        s = 8 * self.z
        return QSize(m.width * s + 1, m.height * s + 1)

    def refresh(self) -> None:
        self.setFixedSize(self.sizeHint())
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        m = self.ed.map
        s = 8 * self.z
        for y in range(m.height):
            for x in range(m.width):
                p.drawImage(QRect(x * s, y * s, s, s), self.ed.src.image(m.get(x, y), m.get_pal(x, y)))
        if self.ed.grid.isChecked():
            p.setPen(QPen(QColor(120, 120, 150, 90), 1))
            for x in range(m.width + 1):
                p.drawLine(x * s, 0, x * s, m.height * s)
            for y in range(m.height + 1):
                p.drawLine(0, y * s, m.width * s, y * s)
            if m.kind == "nes":
                p.setPen(QPen(QColor(255, 200, 0, 110), 1))
                for x in range(0, m.width + 1, 2):
                    p.drawLine(x * s, 0, x * s, m.height * s)
                for y in range(0, m.height + 1, 2):
                    p.drawLine(0, y * s, m.width * s, y * s)
        cx, cy = self.ed.cursor
        p.setPen(QPen(QColor("#ff3030"), 2))
        p.drawRect(cx * s, cy * s, s * (2 if self.ed.tool == "meta" else 1), s * (2 if self.ed.tool == "meta" else 1))
        p.end()

    def _xy(self, pos):
        s = 8 * self.z
        x, y = int(pos.x()) // s, int(pos.y()) // s
        m = self.ed.map
        return (x, y) if 0 <= x < m.width and 0 <= y < m.height else None

    def mousePressEvent(self, e) -> None:
        xy = self._xy(e.position())
        if xy is None:
            return
        self.ed.cursor = xy
        if e.button() == Qt.MouseButton.RightButton:
            self.ed.cur_tile = self.ed.map.get(*xy)
            self.ed.pal_spin.setValue(self.ed.map.get_pal(*xy))
            self.ed.picker.update()
            self.ed.update_status()
            self.update()
            return
        self._painting = True
        self.ed.paint_at(*xy)

    def mouseMoveEvent(self, e) -> None:
        xy = self._xy(e.position())
        if xy is None:
            return
        self.ed.update_status(xy)
        if self._painting and self.ed.tool == "tile":
            self.ed.paint_at(*xy)

    def mouseReleaseEvent(self, _e) -> None:
        self._painting = False


class TilesetDialog(QDialog):
    def __init__(self, parent, path="", offset=0, fmt="nes"):
        super().__init__(parent)
        self.setWindowTitle("Tile Set")
        f = QFormLayout(self)
        self.path = QLineEdit(path)
        b = QPushButton("Browse...")
        b.clicked.connect(self._browse)
        f.addRow("CHR / ROM file", self.path)
        f.addRow("", b)
        self.fmt = QComboBox()
        for k, fm in FORMATS.items():
            if not fm.var_height:
                self.fmt.addItem(fm.name, k)
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(fmt)))
        f.addRow("Format", self.fmt)
        self.offset = HexSpin()
        self.offset.setValue(offset)
        f.addRow("Offset", self.offset)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _browse(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Tile Set", self.path.text(), "All files (*)")
        if p:
            self.path.setText(p)
            try:
                self.offset.setValue(suggested_offset(Path(p).read_bytes(), self.fmt.currentData()))
            except OSError:
                pass


class TilemapEditor(RetroDoc):
    kind = "Tile Map"

    def __init__(self, win=None, path=None, kind: str = "nes", parent=None):
        super().__init__(win, parent)
        self.map = TileMap.new(kind)
        self.src = TileSource()
        self.cur_tile = 0
        self.cursor = (0, 0)
        self.tool = "tile"
        self._undo: list[tuple[list[int], list[int]]] = []
        self._build()
        if path:
            self.load(path)
        self._sync_controls()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        tb = QToolBar()
        self.kind_combo = QComboBox()
        for k, (n, _w, _h) in KINDS.items():
            self.kind_combo.addItem(n, k)
        self.kind_combo.currentIndexChanged.connect(self._on_kind)
        tb.addWidget(self.kind_combo)
        tb.addWidget(QLabel(" W "))
        self.w_spin = QSpinBox()
        self.w_spin.setRange(1, 256)
        tb.addWidget(self.w_spin)
        tb.addWidget(QLabel(" H "))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(1, 256)
        tb.addWidget(self.h_spin)
        tb.addAction("Resize", self._on_resize)
        tb.addSeparator()
        tb.addAction("Tile Set...", self.tileset_dialog)
        tb.addWidget(QLabel(" Palette "))
        self.pal_spin = QSpinBox()
        self.pal_spin.setRange(0, 3)
        self.pal_spin.setToolTip("NES sub-palette (attribute) used when painting")
        self.pal_spin.valueChanged.connect(lambda _v: self.picker.update())
        tb.addWidget(self.pal_spin)
        self.grid = QCheckBox("Grid")
        self.grid.setChecked(True)
        self.grid.toggled.connect(lambda _c: self.canvas.update())
        tb.addWidget(self.grid)
        tb.addSeparator()
        self.tool_combo = QComboBox()
        for k, n in (("tile", "Paint Tile"), ("meta", "Stamp Metatile"), ("fill", "Fill Map")):
            self.tool_combo.addItem(n, k)
        self.tool_combo.currentIndexChanged.connect(lambda _i: self.set_tool(self.tool_combo.currentData()))
        tb.addWidget(self.tool_combo)
        tb.addAction("Make Metatile", self.make_metatile)
        tb.addAction("Undo", self.undo)
        lay.addWidget(tb)
        tb2 = QToolBar()
        tb2.addWidget(QLabel(" Export "))
        self.syntax = QComboBox()
        for k in ASM_SYNTAX:
            self.syntax.addItem(k, k)
        self.syntax.addItem("C array", "c")
        self.syntax.currentIndexChanged.connect(lambda _i: self.update_export())
        tb2.addWidget(self.syntax)
        tb2.addWidget(QLabel(" Label "))
        self.label_edit = QLineEdit("Map")
        self.label_edit.setMaximumWidth(140)
        self.label_edit.textChanged.connect(lambda _t: self.update_export())
        tb2.addWidget(self.label_edit)
        self.meta_check = QCheckBox("As metatiles")
        self.meta_check.toggled.connect(lambda _c: self.update_export())
        tb2.addWidget(self.meta_check)
        tb2.addAction("Copy", lambda: QGuiApplication.clipboard().setText(self.export_text()))
        tb2.addAction("Save As...", self.export_dialog)
        tb2.addSeparator()
        tb2.addAction("Read from ROM...", lambda: self.binary_dialog(False))
        tb2.addAction("Write to ROM...", lambda: self.binary_dialog(True))
        tb2.addAction("Save", self.save)
        lay.addWidget(tb2)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.picker = TilePicker(self)
        self.picker.setFixedSize(self.picker.sizeHint())
        ll.addWidget(self.picker)
        ll.addWidget(QLabel("Metatiles"))
        self.meta_list = QListWidget()
        self.meta_list.setIconSize(QSize(32, 32))
        self.meta_list.currentRowChanged.connect(lambda _r: self.set_tool("meta"))
        ll.addWidget(self.meta_list, 1)
        split.addWidget(left)
        self.canvas = MapCanvas(self)
        sc = QScrollArea()
        sc.setWidget(self.canvas)
        split.addWidget(sc)
        self.export = QPlainTextEdit()
        self.export.setReadOnly(True)
        self.export.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.export.setFont(QFont("Consolas", 9))
        split.addWidget(self.export)
        split.setSizes([280, 560, 300])
        lay.addWidget(split, 1)
        self.status = QLabel()
        lay.addWidget(self.status)

    # ------------------------------------------------------------ state
    def _sync_controls(self) -> None:
        for w, v in ((self.w_spin, self.map.width), (self.h_spin, self.map.height)):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)
        self.kind_combo.blockSignals(True)
        self.kind_combo.setCurrentIndex(self.kind_combo.findData(self.map.kind))
        self.kind_combo.blockSignals(False)
        ts = self.map.tileset
        tsf = self.tileset_path()
        if tsf is not None and tsf.is_file():
            try:
                self.src.load(str(tsf), int(ts.get("offset", 0)), ts.get("format", "nes"))
                if ts.get("palettes"):
                    self.src.palettes = [list(p) for p in ts["palettes"]]
            except (OSError, KeyError):
                pass
        self._fill_meta_list()
        self.canvas.refresh()
        self.picker.update()
        self.update_export()
        self.update_status()

    def set_tool(self, key: str) -> None:
        self.tool = key
        self.tool_combo.blockSignals(True)
        self.tool_combo.setCurrentIndex(self.tool_combo.findData(key))
        self.tool_combo.blockSignals(False)
        self.canvas.update()

    def update_status(self, xy=None) -> None:
        x, y = xy or self.cursor
        t = self.map.get(x, y) if x < self.map.width and y < self.map.height else 0
        self.status.setText(f"Cell {x},{y} = tile ${t:02X} palette {self.map.get_pal(x, y)} - painting with tile "
                            f"${self.cur_tile:02X}, palette {self.pal_spin.value()}  ({self.map.width}x"
                            f"{self.map.height}, {len(self.map.metatiles)} metatiles)")

    def _push(self) -> None:
        self._undo.append((list(self.map.cells), list(self.map.pal)))
        del self._undo[:-200]

    def undo(self) -> None:
        if self._undo:
            self.map.cells, self.map.pal = self._undo.pop()
            self.changed()

    def changed(self) -> None:
        self.canvas.update()
        self.update_export()
        self.set_modified(True)

    def paint_at(self, x: int, y: int) -> None:
        pal = self.pal_spin.value()
        if self.tool == "fill":
            self._push()
            self.map.cells = [self.cur_tile] * (self.map.width * self.map.height)
            self.map.pal = [pal] * (self.map.width * self.map.height)
        elif self.tool == "meta":
            row = self.meta_list.currentRow()
            if row < 0 or row >= len(self.map.metatiles):
                return
            self._push()
            self.map.place_metatile(row, x, y, pal)
        else:
            if self.map.get(x, y) == self.cur_tile and self.map.get_pal(x, y) == pal:
                return
            self._push()
            self.map.set(x, y, self.cur_tile, pal)
        self.changed()

    def make_metatile(self) -> None:
        x, y = self.cursor
        m = self.map
        if x + 1 >= m.width or y + 1 >= m.height:
            return
        self.map.metatiles.append([m.get(x, y), m.get(x + 1, y), m.get(x, y + 1), m.get(x + 1, y + 1)])
        self._fill_meta_list()
        self.meta_list.setCurrentRow(len(self.map.metatiles) - 1)
        self.set_modified(True)

    def _fill_meta_list(self) -> None:
        self.meta_list.blockSignals(True)
        self.meta_list.clear()
        for i, mt in enumerate(self.map.metatiles):
            pm = QPixmap(32, 32)
            p = QPainter(pm)
            for k, t in enumerate(mt):
                p.drawImage(QRect((k % 2) * 16, (k // 2) * 16, 16, 16), self.src.image(t, 0))
            p.end()
            self.meta_list.addItem(QListWidgetItem(QIcon(pm), f"{i}: " + " ".join(f"${t:02X}" for t in mt)))
        self.meta_list.blockSignals(False)

    def _on_kind(self, _i=None) -> None:
        kind = self.kind_combo.currentData()
        _n, w, h = KINDS[kind]
        self._push()
        old = self.map
        self.map = TileMap(w, h, kind, [], [], old.metatiles, old.tileset)
        for y in range(min(h, old.height)):
            for x in range(min(w, old.width)):
                self.map.set(x, y, old.get(x, y), old.get_pal(x, y))
        self._sync_controls()
        self.set_modified(True)

    def _on_resize(self) -> None:
        w, h = self.w_spin.value(), self.h_spin.value()
        old = self.map
        self.map = TileMap(w, h, old.kind, [], [], old.metatiles, old.tileset)
        for y in range(min(h, old.height)):
            for x in range(min(w, old.width)):
                self.map.set(x, y, old.get(x, y), old.get_pal(x, y))
        self._sync_controls()
        self.set_modified(True)

    # ------------------------------------------------------------ tile set
    def set_tileset(self, path: str, offset: int, fmt: str) -> None:
        self.src.load(path, offset, fmt)
        self.map.tileset = {"file": str(path), "offset": offset, "format": fmt, "palettes": self.src.palettes}
        self._fill_meta_list()
        self.picker.update()
        self.canvas.update()

    def tileset_dialog(self) -> None:
        ts = self.map.tileset
        d = TilesetDialog(self, str(self.tileset_path() or ""), int(ts.get("offset", 0)), ts.get("format", "nes"))
        if d.exec() and d.path.text():
            try:
                self.set_tileset(d.path.text(), d.offset.value(), d.fmt.currentData())
                self.set_modified(True)
            except OSError as e:
                QMessageBox.warning(self, "Tile Map", str(e))

    # ------------------------------------------------------------ export
    def export_text(self) -> str:
        label = self.label_edit.text().strip() or "Map"
        syn = self.syntax.currentData()
        if syn == "c":
            return self.map.export_c(label, self.meta_check.isChecked())
        return self.map.export_asm(label, syn, metatiles=self.meta_check.isChecked())

    def update_export(self) -> None:
        self.export.setPlainText(self.export_text())

    def export_dialog(self) -> None:
        ext = "h" if self.syntax.currentData() == "c" else "asm"
        f, _ = QFileDialog.getSaveFileName(self, "Export Map", f"map.{ext}", "Source (*.asm *.s *.inc *.h);;All (*)")
        if f:
            Path(f).write_text(self.export_text(), encoding="utf-8")

    def read_binary(self, path, offset: int) -> None:
        data = Path(path).read_bytes()[offset:]
        self._push()
        m = TileMap.from_bytes(data, self.map.kind, self.map.width, self.map.height)
        self.map.cells, self.map.pal = m.cells, m.pal
        self.changed()

    def write_binary(self, path, offset: int) -> int:
        p = Path(path)
        data = bytearray(p.read_bytes())
        blob = self.map.to_bytes()
        if offset + len(blob) > len(data):
            raise ValueError(f"the map ({len(blob)} bytes) does not fit at 0x{offset:X}")
        data[offset:offset + len(blob)] = blob
        p.write_bytes(bytes(data))
        self.notify_written(p)
        return len(blob)

    def binary_dialog(self, write: bool) -> None:
        d = QDialog(self)
        d.setWindowTitle("Write Map into ROM" if write else "Read Map from ROM")
        f = QFormLayout(d)
        path = QLineEdit(str(self.tileset_path() or ""))
        b = QPushButton("Browse...")
        b.clicked.connect(lambda: path.setText(QFileDialog.getOpenFileName(d, "ROM", path.text())[0] or path.text()))
        off = HexSpin()
        f.addRow("ROM / binary file", path)
        f.addRow("", b)
        f.addRow("Offset", off)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        if not d.exec() or not path.text():
            return
        try:
            if write:
                n = self.write_binary(path.text(), off.value())
                QMessageBox.information(self, "Tile Map", f"{n} bytes written.")
            else:
                self.read_binary(path.text(), off.value())
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Tile Map", str(e))

    # ------------------------------------------------------------ document
    def load(self, path) -> None:
        self.retro_path = Path(path)
        self.map = TileMap.load(path)

    def save(self) -> bool:
        if self.retro_path is None:
            f, _ = QFileDialog.getSaveFileName(self, "Save Tile Map", "map.rtmap", "Tile map (*.rtmap)")
            if not f:
                return False
            self.retro_path = Path(f)
        self.map.tileset["palettes"] = self.src.palettes
        self.map.save(self.retro_path)
        self.set_modified(False)
        return True

    def tileset_path(self) -> Path | None:
        """The tile set file (a relative path is relative to the .rtmap document)."""
        f = self.map.tileset.get("file")
        if not f:
            return None
        p = Path(f)
        if not p.is_absolute() and self.retro_path is not None:
            p = self.retro_path.parent / p
        return p

    @property
    def retro_watch(self) -> list:
        p = self.tileset_path()
        return [p] if p is not None else []

    def reload_from_disk(self) -> None:
        """The tile set file changed (the tile editor wrote it): redraw with the new tiles."""
        ts = self.map.tileset
        tsf = self.tileset_path()
        if tsf is not None and tsf.is_file():
            self.src.load(str(tsf), int(ts.get("offset", 0)), ts.get("format", "nes"))
            if ts.get("palettes"):
                self.src.palettes = [list(p) for p in ts["palettes"]]
            self._fill_meta_list()
            self.picker.update()
            self.canvas.update()
