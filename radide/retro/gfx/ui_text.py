"""Text table (.tbl) editor and Script Dump / Insert - the game-translation tools.

Arabic translation of old games: the game draws one tile per byte from left to right.  "Add Arabic Letter
Forms" gives every contextual letter form its own byte; on insert, "Shape Arabic" picks the right form for
each letter and "Right-to-left (visual order)" reverses each line so the game shows it correctly.  Then draw
the glyphs into the game's font tiles with the Tile Editor (the code of each form is in the table).
"""
from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                             QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QToolBar, QVBoxLayout, QWidget)

from . import arabic
from .script import PointerSpec, Script, dump_pointers, dump_ranges, insert
from .textable import TextTable, ascii_table
from .ui_common import HexSpin, RetroDoc

RTL_NOTE = ("Arabic in old games: the game prints one tile per byte, left to right.  Give every letter form its "
            "own code (Add Arabic Letter Forms), draw those glyphs into the font tiles with the Tile Editor, and "
            "insert with 'Shape Arabic' + 'Right-to-left' so each line is stored in visual order.")

KINDS = [("char", "Character"), ("end", "End code (/)"), ("break", "Line break (*)")]


# ===================================================================== .tbl editor
class TableEditor(RetroDoc):
    kind = "Text Table"

    def __init__(self, win=None, path=None, parent=None):
        super().__init__(win, parent)
        self._build()
        if path:
            self.retro_path = Path(path)
            self.set_table(TextTable.load(path))
        else:
            self.set_table(ascii_table())
        self.set_modified(False)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        tb = QToolBar()
        tb.addAction("Add Row", self.add_row)
        tb.addAction("Delete Row", self.delete_rows)
        tb.addAction("Sort", self.sort_rows)
        tb.addSeparator()
        tb.addAction("New ASCII Table", lambda: (self.set_table(ascii_table()), self.set_modified(True)))
        tb.addWidget(QLabel(" Arabic from "))
        self.ar_start = HexSpin(0xFF)
        self.ar_start.setValue(0x80)
        tb.addWidget(self.ar_start)
        tb.addAction("Add Arabic Letter Forms", self.add_arabic)
        tb.addSeparator()
        tb.addAction("Check", self.check)
        tb.addAction("Save", self.save)
        tb.addAction("Save As...", self.save_as)
        lay.addWidget(tb)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.grid = QTableWidget(0, 3)
        self.grid.setHorizontalHeaderLabels(["Hex", "Text", "Kind"])
        self.grid.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.grid.itemChanged.connect(lambda _i: self._edited())
        self.grid.setFont(QFont("Segoe UI", 10))
        split.addWidget(self.grid)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel("Test: hex bytes -> text"))
        self.test_hex = QLineEdit("48 45 4C 4C 4F 00")
        self.test_hex.textChanged.connect(self._test)
        rl.addWidget(self.test_hex)
        self.test_text_out = QLineEdit()
        self.test_text_out.setReadOnly(True)
        rl.addWidget(self.test_text_out)
        rl.addWidget(QLabel("Test: text -> hex bytes"))
        self.test_text = QLineEdit("HELLO<end>")
        self.test_text.textChanged.connect(self._test)
        rl.addWidget(self.test_text)
        self.shape_check = QCheckBox("Shape Arabic + right-to-left (as inserted)")
        self.shape_check.toggled.connect(self._test)
        rl.addWidget(self.shape_check)
        self.test_hex_out = QLineEdit()
        self.test_hex_out.setReadOnly(True)
        rl.addWidget(self.test_hex_out)
        self.messages = QPlainTextEdit()
        self.messages.setReadOnly(True)
        rl.addWidget(self.messages, 1)
        note = QLabel(RTL_NOTE)
        note.setWordWrap(True)
        rl.addWidget(note)
        split.addWidget(right)
        split.setSizes([420, 380])
        lay.addWidget(split, 1)

    # ------------------------------------------------------------ table <-> grid
    def set_table(self, t: TextTable) -> None:
        self.grid.blockSignals(True)
        self.grid.setRowCount(0)
        rows = ([(b, v, "char") for b, v in t.entries.items()] + [(b, v, "end") for b, v in t.ends.items()]
                + [(b, v, "break") for b, v in t.breaks.items()])
        for b, v, k in rows:
            self._append(b.hex().upper(), "\\n" if v == "\n" else v, k)
        self.grid.blockSignals(False)
        self.messages.setPlainText("\n".join(t.errors) or f"{len(rows)} codes")
        self._test()

    def _append(self, hx: str, text: str, kind: str) -> None:
        r = self.grid.rowCount()
        blocked = self.grid.blockSignals(True)     # Add Row: no itemChanged before the Kind combo exists
        self.grid.insertRow(r)
        self.grid.setItem(r, 0, QTableWidgetItem(hx))
        self.grid.setItem(r, 1, QTableWidgetItem(text))
        self.grid.blockSignals(blocked)
        combo = QComboBox()
        for k, n in KINDS:
            combo.addItem(n, k)
        combo.setCurrentIndex(combo.findData(kind))
        combo.currentIndexChanged.connect(lambda _i: self._edited())
        self.grid.setCellWidget(r, 2, combo)

    def table(self) -> TextTable:
        lines = []
        for r in range(self.grid.rowCount()):
            hx = (self.grid.item(r, 0).text() if self.grid.item(r, 0) else "").replace(" ", "")
            tx = self.grid.item(r, 1).text() if self.grid.item(r, 1) else ""
            cw = self.grid.cellWidget(r, 2)
            kind = cw.currentData() if cw is not None else "char"
            if not hx:
                continue
            if kind == "end":
                lines.append(f"/{hx}={tx}")
            elif kind == "break":
                lines.append(f"*{hx}" + ("" if tx in ("", "\\n") else f"={tx}"))
            else:
                lines.append(f"{hx}={tx}")
        return TextTable.parse("\n".join(lines), self.retro_path.name if self.retro_path else "")

    def _edited(self) -> None:
        self.set_modified(True)
        self._test()

    def add_row(self) -> None:
        self._append("", "", "char")
        self.grid.scrollToBottom()
        self.set_modified(True)

    def delete_rows(self) -> None:
        for r in sorted({i.row() for i in self.grid.selectedIndexes()}, reverse=True):
            self.grid.removeRow(r)
        self._edited()

    def sort_rows(self) -> None:
        self.set_table(self.table())

    def add_arabic(self) -> None:
        t = arabic.arabic_table(self.ar_start.value(), base=self.table())
        self.set_table(t)
        self.set_modified(True)

    def check(self) -> list[str]:
        t = self.table()
        msgs = list(t.errors) + [f"duplicate text: {d}" for d in t.duplicates()]
        if not t.ends:
            msgs.append("no end code (/XX=) - dumps by range will not split strings")
        self.messages.setPlainText("\n".join(msgs) or "The table is OK.")
        return msgs

    def _test(self, *_a) -> None:
        t = self.table()
        try:
            data = bytes.fromhex(re.sub(r"[^0-9A-Fa-f]", "", self.test_hex.text()))
            self.test_text_out.setText(t.decode(data, stop_at_end=False)[0].replace("\n", "\\n"))
        except ValueError:
            self.test_text_out.setText("(odd number of hex digits)")
        text = self.test_text.text().replace("\\n", "\n")
        if self.shape_check.isChecked():
            text = arabic.prepare(text)
        data, problems = t.encode(text)
        self.test_hex_out.setText(" ".join(f"{b:02X}" for b in data) + (f"   ({'; '.join(problems)})" if problems else ""))

    # ------------------------------------------------------------ file
    def save(self) -> bool:
        if self.retro_path is None:
            return self.save_as()
        self.table().save(self.retro_path)
        self.set_modified(False)
        self.notify_written(self.retro_path)
        return True

    def save_as(self) -> bool:
        f, _ = QFileDialog.getSaveFileName(self, "Save Table", str(self.retro_path or "game.tbl"), "Tables (*.tbl)")
        if not f:
            return False
        self.retro_path = Path(f)
        return self.save()

    def reload_from_disk(self) -> None:
        if self.retro_path is not None and self.retro_path.is_file() and not self.is_modified():
            self.set_table(TextTable.load(self.retro_path))
            self.set_modified(False)


# ===================================================================== Script Dump / Insert
def parse_ranges(text: str) -> list[tuple[int, int]]:
    """``0x1000-0x1400, 2000-2100`` (hex; end exclusive) -> [(start, end)]."""
    out = []
    for part in re.split(r"[,;\s]+", text.strip()):
        if not part:
            continue
        a, sep, b = part.partition("-")
        if not sep:
            raise ValueError(f"'{part}' is not a range like 1000-1400")
        out.append((int(a, 16), int(b, 16)))
    return out


class ScriptEditor(RetroDoc):
    kind = "Script Dump/Insert"
    COLS = ["#", "Pointer", "Offset", "Max", "Original", "Translation", "Bytes"]

    def __init__(self, win=None, rom=None, table=None, parent=None):
        super().__init__(win, parent)
        self.script = Script()
        self.table: TextTable | None = None
        self.rom: bytes = b""
        self._filling = False
        self._build()
        if rom:
            self.rom_edit.setText(str(rom))
        if table:
            self.tbl_edit.setText(str(table))

    def title(self) -> str:
        return (Path(self.rom_edit.text()).name + " [script]") if self.rom_edit.text() else self.kind

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        top = QHBoxLayout()
        src = QGroupBox("Source")
        f = QFormLayout(src)
        self.rom_edit, self.tbl_edit = QLineEdit(), QLineEdit()
        for e in (self.rom_edit, self.tbl_edit):
            e.setMinimumWidth(180)
        for label, edit, filt in (("ROM", self.rom_edit, "All files (*)"), ("Table (.tbl)", self.tbl_edit,
                                                                           "Tables (*.tbl);;All files (*)")):
            row = QHBoxLayout()
            row.addWidget(edit)
            b = QPushButton("...")
            b.setMaximumWidth(30)
            b.clicked.connect(lambda _c, e=edit, ft=filt: e.setText(
                QFileDialog.getOpenFileName(self, "Open", e.text(), ft)[0] or e.text()))
            row.addWidget(b)
            f.addRow(label, row)
        self.mode = QComboBox()
        self.mode.addItem("Pointer table", "pointers")
        self.mode.addItem("Ranges (split at end codes)", "ranges")
        self.mode.currentIndexChanged.connect(self._mode_changed)
        f.addRow("Find strings by", self.mode)
        top.addWidget(src, 2)
        self.ptr_box = QGroupBox("Pointer table")
        pf = QFormLayout(self.ptr_box)
        self.ptr_off = HexSpin()
        self.ptr_count = QSpinBox()
        self.ptr_count.setRange(1, 65535)
        self.ptr_count.setValue(16)
        self.ptr_size = QComboBox()
        for n in (2, 3, 4):
            self.ptr_size.addItem(f"{n} bytes", n)
        self.ptr_endian = QComboBox()
        self.ptr_endian.addItem("Little endian (6502, Z80, SM83, x86)", "little")
        self.ptr_endian.addItem("Big endian (68000)", "big")
        self.ptr_base, self.ptr_add = HexSpin(), HexSpin()
        self.ptr_base.setToolTip("Subtracted from each pointer value (e.g. 8000 for a NES bank at $8000)")
        self.ptr_add.setToolTip("Added after that to get the file offset (e.g. 10 for the iNES header + bank)")
        for label, w in (("Table offset", self.ptr_off), ("Count", self.ptr_count), ("Size", self.ptr_size),
                         ("Byte order", self.ptr_endian), ("Base (subtract)", self.ptr_base),
                         ("Add (file offset)", self.ptr_add)):
            pf.addRow(label, w)
        top.addWidget(self.ptr_box, 1)
        self.rng_box = QGroupBox("Ranges")
        rf = QFormLayout(self.rng_box)
        self.ranges = QLineEdit("0-100")
        self.ranges.setToolTip("Hex start-end pairs, end exclusive: 1000-1400, 2000-2100")
        rf.addRow("Hex ranges", self.ranges)
        self.rng_box.setVisible(False)
        top.addWidget(self.rng_box, 1)
        ins = QGroupBox("Insert")
        inf = QFormLayout(ins)
        self.ins_mode = QComboBox()
        self.ins_mode.addItem("In place (each string keeps its space)", "inplace")
        self.ins_mode.addItem("Repack into region + fix pointers", "repack")
        inf.addRow("Mode", self.ins_mode)
        self.reg_start, self.reg_end = HexSpin(), HexSpin()
        self.reg_start.setToolTip("Free region for repacking (0 - 0 = the area the original strings used)")
        rr = QHBoxLayout()
        rr.addWidget(self.reg_start)
        rr.addWidget(QLabel("-"))
        rr.addWidget(self.reg_end)
        inf.addRow("Region", rr)
        self.pad = HexSpin(0xFF)
        inf.addRow("Pad byte", self.pad)
        self.shape = QCheckBox("Shape Arabic")
        self.rtl = QCheckBox("Right-to-left (visual order)")
        ar = QHBoxLayout()
        ar.addWidget(self.shape)
        ar.addWidget(self.rtl)
        inf.addRow("Arabic", ar)
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("output ROM (empty = <name>_translated.<ext>)")
        inf.addRow("Write to", self.out_edit)
        top.addWidget(ins, 1)
        lay.addLayout(top)
        tb = QToolBar()
        tb.addAction("Dump", self.dump)
        tb.addAction("Insert", self.do_insert)
        tb.addSeparator()
        tb.addAction("Save Sheet...", self.save_sheet_dialog)
        tb.addAction("Load Sheet...", self.load_sheet_dialog)
        lay.addWidget(tb)
        split = QSplitter(Qt.Orientation.Vertical)
        self.sheet = QTableWidget(0, len(self.COLS))
        self.sheet.setHorizontalHeaderLabels(self.COLS)
        hh = self.sheet.horizontalHeader()
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.sheet.setWordWrap(True)
        self.sheet.itemChanged.connect(self._on_item)
        self.sheet.setProperty("i18n_skip_items", True)
        split.addWidget(self.sheet)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(140)
        split.addWidget(self.report)
        lay.addWidget(split, 1)
        note = QLabel(RTL_NOTE)
        note.setWordWrap(True)
        lay.addWidget(note)

    def _mode_changed(self, _i=None) -> None:
        ptr = self.mode.currentData() == "pointers"
        self.ptr_box.setVisible(ptr)
        self.rng_box.setVisible(not ptr)

    # ------------------------------------------------------------ helpers
    def pointer_spec(self) -> PointerSpec:
        return PointerSpec(self.ptr_off.value(), self.ptr_count.value(), self.ptr_size.currentData(),
                           self.ptr_endian.currentData(), self.ptr_base.value(), self.ptr_add.value())

    def _load_sources(self) -> bool:
        try:
            self.rom = Path(self.rom_edit.text()).read_bytes()
            self.table = TextTable.load(self.tbl_edit.text())
        except OSError as e:
            QMessageBox.warning(self, "Script", f"Cannot read the ROM / table:\n{e}")
            return False
        if self.table.errors:
            self.report.setPlainText("Table problems:\n" + "\n".join(self.table.errors))
        return True

    def _prepare(self):
        if not (self.shape.isChecked() or self.rtl.isChecked()):
            return None
        return lambda s: arabic.prepare(s, self.shape.isChecked(), self.rtl.isChecked())

    # ------------------------------------------------------------ dump
    def dump(self) -> bool:
        if not self._load_sources():
            return False
        try:
            if self.mode.currentData() == "pointers":
                self.script = dump_pointers(self.rom, self.table, self.pointer_spec())
            else:
                self.script = dump_ranges(self.rom, self.table, parse_ranges(self.ranges.text()))
        except ValueError as e:
            QMessageBox.warning(self, "Script", str(e))
            return False
        self.fill_sheet()
        self.report.appendPlainText(f"Dumped {len(self.script.entries)} strings from {Path(self.rom_edit.text()).name}")
        return True

    def fill_sheet(self) -> None:
        self._filling = True
        self.sheet.setRowCount(len(self.script.entries))
        for r, e in enumerate(self.script.entries):
            vals = [str(e.index), "" if e.ptr_pos is None else f"{e.ptr_pos:X}", f"{e.offset:X}", str(e.length),
                    e.original, e.translation, ""]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c != 5:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.sheet.setItem(r, c, it)
            self._update_row(r)
        self.sheet.resizeRowsToContents()
        self._filling = False

    def _on_item(self, item: QTableWidgetItem) -> None:
        if self._filling or item.column() != 5:
            return
        e = self.script.entries[item.row()]
        e.translation = item.text()
        self._update_row(item.row())
        self.set_modified(True)

    def _update_row(self, r: int) -> None:
        if self.table is None:
            return
        e = self.script.entries[r]
        text = e.text_to_insert()
        prep = self._prepare()
        if prep and e.translation.strip():
            text = prep(text)
        data, problems = self.table.encode(text)
        end = self.table.end_code()
        if end is not None and not data.endswith(end) and e.original.endswith(self.table.end_label()):
            data += end
        bad = problems or (self.ins_mode.currentData() == "inplace" and len(data) > e.length)
        it = self.sheet.item(r, 6)
        if it is None:
            return
        self._filling, was = True, self._filling
        it.setText(f"{len(data)}/{e.length}" + (" !" if problems else ""))
        it.setToolTip("; ".join(problems) if problems else "")
        it.setForeground(QColor("#d03030") if bad else QColor("#208020"))
        self._filling = was

    # ------------------------------------------------------------ insert
    def output_path(self) -> Path:
        if self.out_edit.text().strip():
            return Path(self.out_edit.text().strip())
        p = Path(self.rom_edit.text())
        return p.with_name(p.stem + "_translated" + p.suffix)

    def do_insert(self) -> bool:
        if not self.script.entries:
            QMessageBox.information(self, "Script", "Dump the script first.")
            return False
        if not self._load_sources():
            return False
        region = None
        if self.reg_end.value() > self.reg_start.value():
            region = (self.reg_start.value(), self.reg_end.value())
        res = insert(self.rom, self.table, self.script, self.ins_mode.currentData(), region, self.pad.value(),
                     self._prepare())
        self.report.setPlainText(res.report())
        if not res.ok:
            return False
        out = self.output_path()
        out.write_bytes(bytes(res.rom))
        self.report.appendPlainText(f"Written to {out}")
        self.log(f"[script] inserted {len(self.script.entries)} strings into {out}")
        self.notify_written(out)
        if res.ok and self.ins_mode.currentData() == "repack":
            self.fill_sheet()
        return True

    # ------------------------------------------------------------ sheet files
    def save_sheet(self, path) -> None:
        Path(path).write_text(self.script.to_csv(), encoding="utf-8-sig")
        self.set_modified(False)

    def load_sheet(self, path) -> int:
        text = Path(path).read_text(encoding="utf-8-sig")
        if not self.script.entries:                  # no dump yet: the sheet itself has the offsets
            self.script = Script.from_csv(text)
            if any(e.ptr_pos is not None for e in self.script.entries):
                self.script.pointers = self.pointer_spec()
            n = len(self.script.entries)
        else:
            n = self.script.load_csv(text)
        if self.table is None and self.tbl_edit.text() and Path(self.tbl_edit.text()).is_file():
            self.table = TextTable.load(self.tbl_edit.text())
        self.fill_sheet()
        return n

    def save_sheet_dialog(self) -> None:
        f, _ = QFileDialog.getSaveFileName(self, "Save Sheet", "script.csv", "CSV (UTF-8) (*.csv)")
        if f:
            self.save_sheet(f)

    def load_sheet_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Load Sheet", "", "CSV (*.csv)")
        if f:
            n = self.load_sheet(f)
            self.report.appendPlainText(f"{n} translations loaded from {Path(f).name}")

    def save(self) -> bool:
        f, _ = QFileDialog.getSaveFileName(self, "Save Sheet", "script.csv", "CSV (UTF-8) (*.csv)")
        if not f:
            return False
        self.save_sheet(f)
        return True
