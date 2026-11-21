"""Atari 2600 playfield editor: draw the 40 x N playfield, see which PF0 / PF1 / PF2 bit each block is,
export DASM / ca65 / ACME / C tables, or read / write the tables inside a ROM."""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QLabel,
                             QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter,
                             QToolBar, QVBoxLayout, QWidget)

from . import palettes
from .atari2600 import PF_BITS, PF_WIDTH, Playfield
from .ui_common import HexSpin, RetroDoc, SystemPaletteDialog

REG_COLORS = {"PF0": QColor(255, 120, 120, 60), "PF1": QColor(120, 200, 120, 60), "PF2": QColor(120, 150, 255, 60)}


class PlayfieldCanvas(QWidget):
    def __init__(self, ed: "PlayfieldEditor"):
        super().__init__()
        self.ed = ed
        self.cw, self.ch = 16, 8
        self._paint: int | None = None
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        return QSize(40 * self.cw + 1, 18 + self.ed.pf.height * self.ch + 1)

    def refresh(self) -> None:
        self.setFixedSize(self.sizeHint())
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        pf = self.ed.pf
        bg = QColor(*palettes.palette("a2600ntsc")[self.ed.bg])
        fg = QColor(*palettes.palette("a2600ntsc")[self.ed.fg])
        p.fillRect(0, 0, self.width(), 18, QColor(40, 40, 46))
        f = QFont(p.font())
        f.setPointSize(7)
        p.setFont(f)
        for half in range(2):
            for i, (reg, _b) in enumerate(PF_BITS):
                x = (half * PF_WIDTH + i) * self.cw
                p.fillRect(x, 0, self.cw, 18, REG_COLORS[reg])
            for reg, start, n in (("PF0", 0, 4), ("PF1", 4, 8), ("PF2", 12, 8)):
                p.setPen(QColor(230, 230, 230))
                label = reg if half == 0 or pf.asymmetric or not pf.reflect else reg + "~"
                p.drawText((half * PF_WIDTH + start) * self.cw, 0, n * self.cw, 18,
                           Qt.AlignmentFlag.AlignCenter, label)
        p.fillRect(0, 18, 40 * self.cw, pf.height * self.ch, bg)
        for y in range(pf.height):
            row = pf.display_row(y)
            for x, v in enumerate(row):
                if v:
                    p.fillRect(x * self.cw, 18 + y * self.ch, self.cw, self.ch, fg)
        p.setPen(QPen(QColor(120, 120, 140, 90), 1))
        for x in range(41):
            p.drawLine(x * self.cw, 18, x * self.cw, 18 + pf.height * self.ch)
        for y in range(pf.height + 1):
            p.drawLine(0, 18 + y * self.ch, 40 * self.cw, 18 + y * self.ch)
        p.setPen(QPen(QColor(255, 200, 0), 2))
        p.drawLine(20 * self.cw, 0, 20 * self.cw, 18 + pf.height * self.ch)
        p.end()

    def _xy(self, pos):
        x, y = int(pos.x()) // self.cw, (int(pos.y()) - 18) // self.ch
        if 0 <= x < 40 and 0 <= y < self.ed.pf.height:
            return x, y
        return None

    def mousePressEvent(self, e) -> None:
        xy = self._xy(e.position())
        if xy is None:
            return
        if e.button() == Qt.MouseButton.RightButton:
            self._paint = 0
        else:
            self._paint = 0 if self.ed.pf.get(*xy) else 1
        self.ed.begin_edit()
        self.ed.pf.set(xy[0], xy[1], self._paint)
        self.ed.changed()

    def mouseMoveEvent(self, e) -> None:
        xy = self._xy(e.position())
        if xy is not None:
            self.ed.show_bit(*xy)
            if self._paint is not None:
                self.ed.pf.set(xy[0], xy[1], self._paint)
                self.ed.changed()

    def mouseReleaseEvent(self, _e) -> None:
        self._paint = None


class BinaryDialog(QDialog):
    """Where the playfield tables are inside a ROM."""

    def __init__(self, parent, title: str, path: str = "", offset: int = 0, layout: str = "tables"):
        super().__init__(parent)
        self.setWindowTitle(title)
        f = QFormLayout(self)
        self.path = QLineEdit(path)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        f.addRow("ROM / binary file", self.path)
        f.addRow("", browse)
        self.offset = HexSpin()
        self.offset.setValue(offset)
        f.addRow("Offset", self.offset)
        self.layout_combo = QComboBox()
        self.layout_combo.addItem("Separate tables (PF0[], PF1[], PF2[])", "tables")
        self.layout_combo.addItem("Interleaved (PF0, PF1, PF2 per row)", "interleaved")
        self.layout_combo.setCurrentIndex(self.layout_combo.findData(layout))
        f.addRow("Layout", self.layout_combo)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _browse(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "ROM / binary file", self.path.text(),
                                           "Atari 2600 ROMs (*.a26 *.bin);;All files (*)")
        if p:
            self.path.setText(p)


class PlayfieldEditor(RetroDoc):
    kind = "2600 Playfield"

    def __init__(self, win=None, path=None, parent=None):
        super().__init__(win, parent)
        self.pf = Playfield(24, reflect=False)
        self.bg, self.fg = 0x80 >> 1, 0x1E >> 1
        self.bin_path, self.bin_offset, self.bin_layout = "", 0, "tables"
        self._undo: list[list[list[int]]] = []
        self._build()
        if path:
            self.load(path)
        self.changed(mark=False)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        tb = QToolBar()
        tb.addWidget(QLabel(" Rows "))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(1, 255)
        self.h_spin.setValue(self.pf.height)
        self.h_spin.valueChanged.connect(self._on_height)
        tb.addWidget(self.h_spin)
        self.reflect = QCheckBox("Reflect (CTRLPF REF)")
        self.reflect.toggled.connect(self._on_mode)
        tb.addWidget(self.reflect)
        self.asym = QCheckBox("Asymmetric (6 tables)")
        self.asym.toggled.connect(self._on_mode)
        tb.addWidget(self.asym)
        tb.addSeparator()
        tb.addAction("Background...", lambda: self._pick("bg"))
        tb.addAction("Playfield Color...", lambda: self._pick("fg"))
        tb.addSeparator()
        tb.addAction("Undo", self.undo)
        tb.addAction("Clear", self.clear)
        tb.addSeparator()
        tb.addAction("Read from ROM...", self.import_binary_dialog)
        tb.addAction("Write to ROM...", self.write_binary_dialog)
        tb.addAction("Save", self.save)
        lay.addWidget(tb)
        tb2 = QToolBar()
        tb2.addWidget(QLabel(" Export "))
        self.syntax = QComboBox()
        for k, n in (("dasm", "DASM"), ("ca65", "ca65"), ("acme", "ACME"), ("c", "C array")):
            self.syntax.addItem(n, k)
        self.syntax.currentIndexChanged.connect(lambda _i: self._update_asm())
        tb2.addWidget(self.syntax)
        self.label_edit = QLineEdit("Playfield")
        self.label_edit.setMaximumWidth(140)
        self.label_edit.textChanged.connect(lambda _t: self._update_asm())
        tb2.addWidget(QLabel(" Label "))
        tb2.addWidget(self.label_edit)
        self.reverse = QCheckBox("Bottom row first")
        self.reverse.setToolTip("Kernels that count the line counter down read the tables backwards")
        self.reverse.toggled.connect(lambda _c: self._update_asm())
        tb2.addWidget(self.reverse)
        tb2.addAction("Copy", self.copy_asm)
        tb2.addAction("Save As...", self.export_dialog)
        lay.addWidget(tb2)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.canvas = PlayfieldCanvas(self)
        sc = QScrollArea()
        sc.setWidget(self.canvas)
        split.addWidget(sc)
        self.asm = QPlainTextEdit()
        self.asm.setReadOnly(True)
        self.asm.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.asm.setFont(QFont("Consolas", 9))
        split.addWidget(self.asm)
        split.setSizes([680, 300])
        lay.addWidget(split, 1)
        self.info = QLabel("Left button draws / erases, right button erases.  The header shows which register "
                           "drives each block.")
        lay.addWidget(self.info)

    # ------------------------------------------------------------ editing
    def begin_edit(self) -> None:
        self._undo.append([list(r) for r in self.pf.rows])
        del self._undo[:-100]

    def undo(self) -> None:
        if self._undo:
            self.pf.rows = self._undo.pop()
            self.pf.height = len(self.pf.rows)
            self.h_spin.blockSignals(True)
            self.h_spin.setValue(self.pf.height)
            self.h_spin.blockSignals(False)
            self.changed()

    def clear(self) -> None:
        self.begin_edit()
        self.pf.rows = [[0] * 40 for _ in range(self.pf.height)]
        self.changed()

    def changed(self, mark: bool = True) -> None:
        self.canvas.refresh()
        self._update_asm()
        if mark:
            self.set_modified(True)

    def _update_asm(self) -> None:
        self.asm.setPlainText(self.export_text())

    def export_text(self) -> str:
        return self.pf.export_asm(self.label_edit.text().strip() or "Playfield", self.syntax.currentData(),
                                  self.reverse.isChecked())

    def show_bit(self, x: int, y: int) -> None:
        half, i = divmod(x, PF_WIDTH)
        if half and not self.pf.asymmetric and self.pf.reflect:
            i = PF_WIDTH - 1 - i
        reg, bit = PF_BITS[i]
        if half and self.pf.asymmetric:
            reg += " (right half)"
        self.info.setText(f"Row {y}, block {x} (colour clocks {x * 4}-{x * 4 + 3}) = {reg} bit {bit}")

    def _on_height(self, v: int) -> None:
        self.begin_edit()
        self.pf.resize(v)
        self.changed()

    def _on_mode(self, _c=None) -> None:
        was_asym = self.pf.asymmetric
        self.pf.reflect = self.reflect.isChecked()
        self.pf.asymmetric = self.asym.isChecked()
        if self.pf.asymmetric and not was_asym:            # start the right half from what was shown
            for y in range(self.pf.height):
                left = self.pf.rows[y][:PF_WIDTH]
                self.pf.rows[y] = left + (left[::-1] if self.pf.reflect else list(left))
        self.reflect.setEnabled(not self.pf.asymmetric)
        self.changed()

    def _pick(self, which: str) -> None:
        dlg = SystemPaletteDialog("a2600ntsc", getattr(self, which), self)
        if dlg.exec():
            setattr(self, which, dlg.value)
            self.canvas.update()

    # ------------------------------------------------------------ text export
    def copy_asm(self) -> None:
        QGuiApplication.clipboard().setText(self.export_text())

    def export_dialog(self) -> None:
        ext = "h" if self.syntax.currentData() == "c" else "asm"
        f, _ = QFileDialog.getSaveFileName(self, "Export Playfield", f"playfield.{ext}",
                                           "Assembler / C source (*.asm *.s *.inc *.h);;All files (*)")
        if f:
            Path(f).write_text(self.export_text(), encoding="utf-8")

    # ------------------------------------------------------------ ROM
    def import_binary(self, path, offset: int, layout: str = "tables") -> None:
        data = Path(path).read_bytes()
        self.begin_edit()
        pf = Playfield.from_binary(data, offset, self.pf.height, layout, self.pf.reflect, self.pf.asymmetric)
        self.pf.rows = pf.rows
        self.bin_path, self.bin_offset, self.bin_layout = str(path), offset, layout
        self.changed()

    def write_binary(self, path, offset: int, layout: str = "tables") -> int:
        p = Path(path)
        data = bytearray(p.read_bytes())
        changes = self.pf.to_binary(data, offset, layout)
        p.write_bytes(bytes(data))
        self.bin_path, self.bin_offset, self.bin_layout = str(path), offset, layout
        self.log(f"[playfield] wrote {len(changes)} changed bytes into {p.name} at 0x{offset:X}")
        self.notify_written(p)
        return len(changes)

    def bin_abs(self) -> str:
        """The ROM path of the document (relative to the .rtpf file)."""
        if self.bin_path and not Path(self.bin_path).is_absolute() and self.retro_path is not None:
            return str(self.retro_path.parent / self.bin_path)
        return self.bin_path

    def import_binary_dialog(self) -> None:
        d = BinaryDialog(self, "Read Playfield from ROM", self.bin_abs(), self.bin_offset, self.bin_layout)
        if d.exec() and d.path.text():
            try:
                self.import_binary(d.path.text(), d.offset.value(), d.layout_combo.currentData())
            except OSError as e:
                QMessageBox.warning(self, "Playfield", str(e))

    def write_binary_dialog(self) -> None:
        d = BinaryDialog(self, "Write Playfield into ROM", self.bin_abs(), self.bin_offset, self.bin_layout)
        if d.exec() and d.path.text():
            try:
                n = self.write_binary(d.path.text(), d.offset.value(), d.layout_combo.currentData())
                QMessageBox.information(self, "Playfield", f"{n} bytes changed.")
            except (OSError, ValueError) as e:
                QMessageBox.warning(self, "Playfield", str(e))

    # ------------------------------------------------------------ document (.rtpf)
    def to_json(self) -> dict:
        return {"format": "radide-playfield", "version": 1, "height": self.pf.height, "reflect": self.pf.reflect,
                "asymmetric": self.pf.asymmetric, "rows": ["".join(map(str, r)) for r in self.pf.rows],
                "bg": self.bg, "fg": self.fg, "binary": {"path": self.bin_path, "offset": self.bin_offset,
                                                         "layout": self.bin_layout}}

    def load(self, path) -> None:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        self.retro_path = Path(path)
        self.pf = Playfield(int(d.get("height", 24)), bool(d.get("reflect")), bool(d.get("asymmetric")))
        self.pf.rows = [[1 if c == "1" else 0 for c in (r + "0" * 40)[:40]] for r in d.get("rows", [])]
        self.pf.height = len(self.pf.rows) or self.pf.height
        if not self.pf.rows:
            self.pf.rows = [[0] * 40 for _ in range(self.pf.height)]
        self.bg, self.fg = int(d.get("bg", self.bg)), int(d.get("fg", self.fg))
        b = d.get("binary") or {}
        self.bin_path, self.bin_offset, self.bin_layout = b.get("path", ""), int(b.get("offset", 0)), \
            b.get("layout", "tables")
        for w, v in ((self.h_spin, self.pf.height),):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)
        for w, v in ((self.reflect, self.pf.reflect), (self.asym, self.pf.asymmetric)):
            w.blockSignals(True)
            w.setChecked(v)
            w.blockSignals(False)

    def save(self) -> bool:
        if self.retro_path is None:
            f, _ = QFileDialog.getSaveFileName(self, "Save Playfield", "playfield.rtpf", "Playfield (*.rtpf)")
            if not f:
                return False
            self.retro_path = Path(f)
        self.retro_path.write_text(json.dumps(self.to_json(), indent=1), encoding="utf-8")
        self.set_modified(False)
        return True

    def reload_from_disk(self) -> None:
        if self.retro_path is not None and self.retro_path.is_file() and not self.is_modified():
            self.load(self.retro_path)
            self.changed(mark=False)
