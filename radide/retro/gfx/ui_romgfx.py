"""Tile Editor dialogs for ROM data: palettes stored in the ROM (rompal.py) and compressed graphics (compress.py).

* **ROM Palette...**: point at a palette table (offset, layout, sub-palette) or pick one of the detected
  candidates; the tiles are drawn in those colours and colour edits (double-click a slot) are written back.
* **Compressed Graphics...**: choose a codec and an offset (or **Find Graphics** to scan the ROM), open the
  block: the sheet shows the decompressed tiles; Save recompresses them into the ROM after a size check.
"""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from . import compress, rompal
from .ui_common import HexSpin


def _tr(text: str) -> str:
    try:
        from ... import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


def swatch_icon(colors, w: int = 12, h: int = 12) -> QIcon:
    colors = list(colors)[:32]
    pm = QPixmap(max(1, w * len(colors)), h)
    pm.fill(QColor(0, 0, 0))
    p = QPainter(pm)
    for i, (r, g, b) in enumerate(colors):
        p.fillRect(i * w, 0, w, h, QColor(r, g, b))
    p.end()
    return QIcon(pm)


class _Swatches(QLabel):
    def show_colors(self, colors) -> None:
        colors = list(colors)
        self.setPixmap(swatch_icon(colors, 22, 22).pixmap(22 * max(1, len(colors)), 22))


# ===================================================================== ROM palette
class RomPaletteDialog(QDialog):
    def __init__(self, editor, parent=None):
        super().__init__(parent or editor)
        self.ed = editor
        self.setWindowTitle(_tr("Palette from ROM"))
        self.resize(560, 480)
        data = editor.file_data
        cur = editor.rom_pal
        lay = QVBoxLayout(self)
        intro = QLabel(_tr("Point at the palette table in the ROM (or pick a detected one). The tiles are drawn in "
                           "these colours; double-click a colour slot in the editor to change it - the bytes are "
                           "written back into the ROM when you save."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        form = QFormLayout()
        self.layout_combo = QComboBox()
        for k, name in rompal.LAYOUTS.items():
            self.layout_combo.addItem(_tr(name), k)
        form.addRow(_tr("Layout:"), self.layout_combo)
        self.offset = HexSpin(max(0, len(data) - 1))
        form.addRow(_tr("Offset:"), self.offset)
        self.index = QSpinBox()
        self.index.setRange(0, 255)
        form.addRow(_tr("Sub-palette:"), self.index)
        self.ncolors = QComboBox()
        for n in (4, 16):
            self.ncolors.addItem(str(n), n)
        form.addRow(_tr("Colours per palette:"), self.ncolors)
        self.slot = QSpinBox()
        self.slot.setRange(0, 3)
        self.slot.setValue(2)
        form.addRow(_tr("Colour slot of these bytes:"), self.slot)
        lay.addLayout(form)
        self.preview = _Swatches()
        lay.addWidget(self.preview)
        row = QHBoxLayout()
        b_det = QPushButton(_tr("Detect Palettes"))
        b_det.clicked.connect(self.detect)
        row.addWidget(b_det)
        row.addStretch(1)
        lay.addLayout(row)
        self.cands = QListWidget()
        self.cands.itemClicked.connect(self._pick)
        self.cands.itemDoubleClicked.connect(lambda it: (self._pick(it), self.accept()))
        lay.addWidget(self.cands, 1)
        self.status = QLabel()
        lay.addWidget(self.status)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        if cur is not None:
            self.layout_combo.setCurrentIndex(max(0, self.layout_combo.findData(cur.layout)))
            self.offset.setValue(cur.offset)
            self.index.setValue(cur.index)
            self.ncolors.setCurrentIndex(max(0, self.ncolors.findData(cur.colors_n)))
            self.slot.setValue(cur.slot)
        else:
            key = editor.sheet.fmt.key
            self.layout_combo.setCurrentIndex(max(0, self.layout_combo.findData(
                {"nes": "nes4", "gb": "gb_bgp", "snes4": "bgr555", "gba4": "bgr555", "genesis": "genesis"}.get(key,
                                                                                                         "nes4"))))
            if self.layout_combo.currentData() in ("bgr555", "genesis") and editor.sheet.fmt.colors == 16:
                self.ncolors.setCurrentIndex(1)
        for w in (self.layout_combo, self.ncolors):
            w.currentIndexChanged.connect(self._update)
        for w in (self.offset, self.index, self.slot):
            w.valueChanged.connect(self._update)
        self._update()

    def palette(self) -> rompal.RomPalette:
        base = list(self.ed.palette.slots) if self.ed.palette.custom is None and len(self.ed.palette.slots) == 4 \
            else [0x0F, 0x16, 0x27, 0x30]
        return rompal.RomPalette(self.layout_combo.currentData(), self.offset.value(), self.index.value(),
                                 self.ncolors.currentData() or 4, self.slot.value(), base)

    def _update(self, _v=None) -> None:
        lay = self.layout_combo.currentData()
        self.ncolors.setEnabled(lay in ("bgr555", "genesis"))
        self.slot.setEnabled(lay == "nes_slot")
        rp = self.palette()
        data = self.ed.file_data
        if not rp.valid(data):
            self.status.setText(_tr("The palette is past the end of the file."))
            self.preview.clear()
            return
        a, b = rp.span()
        self.preview.show_colors(rp.colors(data))
        self.status.setText(f"{_tr('Bytes')} 0x{a:X}-0x{b - 1:X}: " + " ".join(f"{x:02X}" for x in data[a:b]))

    def detect(self) -> None:
        lay = self.layout_combo.currentData()
        data = self.ed.file_data
        if lay == "bgr555":
            found = rompal.find_bgr555_palettes(data, colors=self.ncolors.currentData() or 4)
        else:
            found = [c for c in rompal.find_nes_palettes(data) if c.score >= 0.45]
            if not found:
                found = [c for c in rompal.find_nes_palettes(data, length=16) if c.score >= 0.45]
        self.cands.clear()
        for c in found:
            it = QListWidgetItem(swatch_icon(c.preview, 8, 14), c.label())
            it.setData(Qt.ItemDataRole.UserRole, (c.layout, c.offset))
            self.cands.addItem(it)
        self.cands.setIconSize(QSize(8 * 32, 14))
        self.status.setText(_tr("Palette candidates found:") + f" {len(found)}")
        self.found = found

    def _pick(self, it) -> None:
        layout, off = it.data(Qt.ItemDataRole.UserRole)
        self.layout_combo.setCurrentIndex(self.layout_combo.findData("nes4" if layout == "nes4" else layout))
        self.offset.setValue(off)
        self.index.setValue(0)


# ===================================================================== compressed graphics
class CompressedDialog(QDialog):
    def __init__(self, editor, parent=None):
        super().__init__(parent or editor)
        self.ed = editor
        self.found: list = []
        self.setWindowTitle(_tr("Compressed Graphics"))
        self.resize(640, 520)
        data = editor.file_data
        lay = QVBoxLayout(self)
        intro = QLabel(_tr("Many games keep their tiles compressed (CHR-RAM games copy them to the PPU at run time). "
                           "Choose the codec and where the block starts, or let Find Graphics scan the ROM. The "
                           "Tile Editor then shows the decompressed tiles; Save packs them again and writes them "
                           "back if they still fit."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        form = QFormLayout()
        self.codec = QComboBox()
        for k, c in compress.CODECS.items():
            self.codec.addItem(_tr(c.name), k)
        form.addRow(_tr("Codec:"), self.codec)
        self.offset = HexSpin(max(0, len(data) - 1))
        self.offset.setValue(editor.sheet.offset if editor.region is None else editor.region.offset)
        form.addRow(_tr("Offset:"), self.offset)
        self.tiles = QSpinBox()
        self.tiles.setRange(1, 65535)
        self.tiles.setValue(256)
        form.addRow(_tr("Tiles (codecs without a length):"), self.tiles)
        lay.addLayout(form)
        row = QHBoxLayout()
        self.scan_what = QComboBox()
        self.scan_what.addItem(_tr("This codec"), "one")
        self.scan_what.addItem(_tr("All codecs (slower)"), "all")
        b_find = QPushButton(_tr("Find Graphics"))
        b_find.clicked.connect(self.find)
        b_try = QPushButton(_tr("Test"))
        b_try.clicked.connect(self.test)
        row.addWidget(b_find)
        row.addWidget(self.scan_what)
        row.addWidget(b_try)
        row.addStretch(1)
        lay.addLayout(row)
        self.results = QListWidget()
        self.results.itemClicked.connect(self._pick)
        self.results.itemDoubleClicked.connect(lambda it: (self._pick(it), self.accept()))
        lay.addWidget(self.results, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        bb = QDialogButtonBox()
        self.b_open = bb.addButton(_tr("Open Block"), QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.codec.currentIndexChanged.connect(self._update)
        self._update()

    def _update(self, _i=None) -> None:
        c = compress.CODECS[self.codec.currentData()]
        self.tiles.setEnabled(c.needs_size)

    def choice(self) -> tuple[str, int, int | None]:
        c = compress.CODECS[self.codec.currentData()]
        return c.key, self.offset.value(), (self.tiles.value() * 16 if c.needs_size else None)

    def test(self) -> bool:
        key, off, size = self.choice()
        try:
            raw, used = compress.decompress(key, self.ed.file_data, off, size)
        except (compress.CodecError, IndexError, ValueError) as e:
            self.status.setText(f"{_tr('Not a valid block here')}: {e}")
            return False
        self.status.setText(f"{used} {_tr('bytes in the ROM')} -> {len(raw)} {_tr('bytes')} "
                            f"({len(raw) // 16} {_tr('tiles')})")
        return True

    def find(self) -> list:
        keys = None if self.scan_what.currentData() == "all" else [self.codec.currentData()]
        self.status.setText(_tr("Scanning..."))
        QApplication.processEvents()

        def progress(pos, end):
            self.status.setText(f"{_tr('Scanning...')} {pos * 100 // max(1, end)}%")
            QApplication.processEvents()
        self.found = compress.find_graphics(self.ed.file_data, keys, progress=progress)
        self.results.clear()
        for c in self.found:
            it = QListWidgetItem(c.label())
            it.setData(Qt.ItemDataRole.UserRole, (c.codec, c.offset, c.size))
            self.results.addItem(it)
        self.status.setText(_tr("Blocks found:") + f" {len(self.found)}")
        return self.found

    def _pick(self, it) -> None:
        codec, off, size = it.data(Qt.ItemDataRole.UserRole)
        self.codec.setCurrentIndex(self.codec.findData(codec))
        self.offset.setValue(off)
        self.tiles.setValue(max(1, size // 16))
        self.test()


class RegionBar(QWidget):
    """The strip above the sheet while a compressed block is open."""

    def __init__(self, editor):
        super().__init__()
        self.ed = editor
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        self.label = QLabel()
        lay.addWidget(self.label, 1)
        self.b_close = QPushButton(_tr("Back to the ROM bytes"))
        self.b_close.clicked.connect(lambda: editor.close_compressed())
        lay.addWidget(self.b_close)
        self.setStyleSheet("background: #FFF4C8; color: #222;")

    def refresh(self) -> None:
        r = self.ed.region
        if r is None:
            self.hide()
            return
        room, _fill = r.room(self.ed.file_data)
        self.label.setText(f"{_tr('Compressed block')}: {compress.CODECS[r.codec].name} {_tr('at')} 0x{r.offset:X}, "
                           f"{r.used} {_tr('bytes')} -> {r.size} {_tr('bytes')} ({r.size // 16} {_tr('tiles')}); "
                           f"{_tr('room for the packed data')}: {room} {_tr('bytes')}")
        self.show()


__all__ = ["CompressedDialog", "RegionBar", "RomPaletteDialog", "swatch_icon"]
