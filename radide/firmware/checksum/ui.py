"""Checksum toolkit dialog (Qt): the block list (add / edit / verify / correct, profiles) and the checksum finder.

    dlg = ChecksumDialog(parent, data=work_bytes, blocks=project.checksums, original=original_bytes,
                         writable=True, title="Checksums - MyEcu")
    if dlg.exec():
        project.checksums = dlg.blocks            # dlg.corrected_data holds the corrected bytes after "Correct"
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                             QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import algorithms as A
from .blocks import ChecksumBlock, correct, hx, load_profile, report, save_profile, to_int, verify
from .finder import DEFAULT_ALGORITHMS, find

DISCLAIMER = ("Presets are generic algorithms, not manufacturer specifications. A block is only trustworthy once "
              "it matches your original file - tick 'Verified' after you checked it.")


def _mono() -> QFont:
    f = QFont("Consolas")
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def ranges_text(ranges) -> str:
    return ", ".join(f"{hx(s)}-{hx(e)}" for s, e in ranges)


def parse_ranges(text: str) -> list[tuple[int, int]]:
    """"0x0-0x3FFE, 0x4000-0x8000" or one range per line; end exclusive. '+len' means a length."""
    out = []
    for part in text.replace("\n", ",").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "+" in part[1:]:
            a, b = part.split("+", 1)
            s = to_int(a)
            out.append((s, s + to_int(b)))
            continue
        a, sep, b = part.partition("-")
        if not sep:
            raise ValueError(f"'{part}' is not a range (start-end)")
        s, e = to_int(a), to_int(b)
        if e <= s:
            raise ValueError(f"range {part}: the end must be after the start")
        out.append((s, e))
    return out


# ============================================================================== block editor
class BlockEditor(QDialog):
    def __init__(self, parent=None, block: ChecksumBlock | None = None, data: bytes | None = None):
        super().__init__(parent)
        self.setWindowTitle("Checksum Block")
        self.setObjectName("checksumBlockEditor")
        self.data = data
        b = block or ChecksumBlock()
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(b.name)
        form.addRow("Name:", self.name)
        self.algo = QComboBox()
        for n, p in A.PRESETS.items():
            self.algo.addItem(f"{n}  -  {p.get('title', '')}", n)
        self.algo.addItem("Custom CRC...", "custom-crc")
        self.algo.addItem("Custom sum / XOR...", "custom-sum")
        form.addRow("Algorithm:", self.algo)
        # custom CRC
        self.crc_box = QGroupBox("Custom CRC (Rocksoft model)")
        g = QGridLayout(self.crc_box)
        self.c_width = QSpinBox()
        self.c_width.setRange(3, 64)
        self.c_width.setValue(16)
        self.c_poly, self.c_init, self.c_xor = QLineEdit("0x1021"), QLineEdit("0xFFFF"), QLineEdit("0x0")
        self.c_refin, self.c_refout = QCheckBox("Reflect input"), QCheckBox("Reflect output")
        for i, (lab, w) in enumerate((("Width (bits):", self.c_width), ("Poly:", self.c_poly), ("Init:", self.c_init),
                                      ("XorOut:", self.c_xor))):
            g.addWidget(QLabel(lab), i // 2, (i % 2) * 2)
            g.addWidget(w, i // 2, (i % 2) * 2 + 1)
        g.addWidget(self.c_refin, 2, 0, 1, 2)
        g.addWidget(self.c_refout, 2, 2, 1, 2)
        form.addRow(self.crc_box)
        # custom sum / xor
        self.sum_box = QGroupBox("Custom sum / XOR")
        g2 = QGridLayout(self.sum_box)
        self.s_type = QComboBox()
        self.s_type.addItems(["sum", "xor"])
        self.s_unit = QComboBox()
        self.s_unit.addItems(["1", "2", "4"])
        self.s_uend = QComboBox()
        self.s_uend.addItems(["be", "le"])
        self.s_width = QComboBox()
        self.s_width.addItems(["8", "16", "32"])
        self.s_comp = QComboBox()
        self.s_comp.addItems(["none", "ones", "twos"])
        for i, (lab, w) in enumerate((("Type:", self.s_type), ("Unit (bytes):", self.s_unit),
                                      ("Word order:", self.s_uend), ("Result bits:", self.s_width),
                                      ("Complement:", self.s_comp))):
            g2.addWidget(QLabel(lab), i // 2, (i % 2) * 2)
            g2.addWidget(w, i // 2, (i % 2) * 2 + 1)
        form.addRow(self.sum_box)
        self.ranges = QLineEdit(ranges_text(b.ranges))
        self.ranges.setPlaceholderText("0x0-0x3FFE, 0x4000-0x7FFC   (end exclusive; start+length also works)")
        form.addRow("Ranges:", self.ranges)
        self.skip = QLineEdit(ranges_text(b.skip))
        self.skip.setPlaceholderText("bytes left out, e.g. 0xC000-0xD000")
        form.addRow("Skip ranges:", self.skip)
        self.store = QLineEdit(hx(b.store))
        form.addRow("Stored at:", self.store)
        row = QHBoxLayout()
        self.width = QComboBox()
        self.width.addItems(["auto", "1", "2", "4", "8"])
        self.width.setCurrentText(str(b.width) if b.width else "auto")
        self.endian = QComboBox()
        self.endian.addItems(["be", "le"])
        self.endian.setCurrentText(b.endian)
        row.addWidget(QLabel("Width:"))
        row.addWidget(self.width)
        row.addWidget(QLabel("Byte order:"))
        row.addWidget(self.endian)
        row.addStretch(1)
        form.addRow(row)
        self.comp = QLineEdit(hx(b.complement_at) if b.complement_at >= 0 else "")
        self.comp.setPlaceholderText("optional: where ~value is stored (complement pair)")
        form.addRow("Complement copy at:", self.comp)
        self.mode = QComboBox()
        for k, t in (("skip", "Left out of the ranges"), ("fill00", "Counted as 00 bytes"),
                     ("fillFF", "Counted as FF bytes")):
            self.mode.addItem(t, k)
        self.mode.setCurrentIndex(max(0, self.mode.findData(b.store_mode)))
        form.addRow("Stored bytes:", self.mode)
        rep = QHBoxLayout()
        self.rep_count = QSpinBox()
        self.rep_count.setRange(1, 100000)
        self.rep_count.setValue(b.repeat_count)
        self.rep_stride = QLineEdit(hx(b.repeat_stride))
        rep.addWidget(QLabel("Repeat (multipoint):"))
        rep.addWidget(self.rep_count)
        rep.addWidget(QLabel("every"))
        rep.addWidget(self.rep_stride)
        rep.addWidget(QLabel("bytes"))
        form.addRow(rep)
        self.verified = QCheckBox("Verified against my original file")
        self.verified.setChecked(b.verified)
        form.addRow(self.verified)
        self.note = QLineEdit(b.note)
        form.addRow("Note:", self.note)
        lay.addLayout(form)
        self.preview = QLabel("")
        self.preview.setFont(_mono())
        self.preview.setWordWrap(True)
        lay.addWidget(self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.b_test = bb.addButton("Test", QDialogButtonBox.ButtonRole.ActionRole)
        self.b_test.clicked.connect(self.test)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._set_algo(b.algorithm)
        self.algo.currentIndexChanged.connect(self._algo_changed)
        self._algo_changed()

    def _set_algo(self, spec) -> None:
        if isinstance(spec, str) and spec in A.PRESETS:
            self.algo.setCurrentIndex(self.algo.findData(spec))
            return
        try:
            d = A.resolve(spec)
        except A.AlgorithmError:
            return
        name = A.short_name(d)
        if name in A.PRESETS:
            self.algo.setCurrentIndex(self.algo.findData(name))
        elif d["type"] == "crc":
            self.algo.setCurrentIndex(self.algo.findData("custom-crc"))
            self.c_width.setValue(d["width"])
            self.c_poly.setText(hx(d["poly"]))
            self.c_init.setText(hx(d["init"]))
            self.c_xor.setText(hx(d["xorout"]))
            self.c_refin.setChecked(d["refin"])
            self.c_refout.setChecked(d["refout"])
        elif d["type"] in ("sum", "xor"):
            self.algo.setCurrentIndex(self.algo.findData("custom-sum"))
            self.s_type.setCurrentText(d["type"])
            self.s_unit.setCurrentText(str(d["unit"]))
            self.s_uend.setCurrentText(d["unit_endian"])
            self.s_width.setCurrentText(str(d["width"]))
            self.s_comp.setCurrentText(d["complement"])

    def _algo_changed(self) -> None:
        k = self.algo.currentData()
        self.crc_box.setVisible(k == "custom-crc")
        self.sum_box.setVisible(k == "custom-sum")

    def algorithm(self):
        k = self.algo.currentData()
        if k == "custom-crc":
            return A.resolve({"type": "crc", "width": self.c_width.value(), "poly": to_int(self.c_poly.text()),
                              "init": to_int(self.c_init.text()), "xorout": to_int(self.c_xor.text()),
                              "refin": self.c_refin.isChecked(), "refout": self.c_refout.isChecked()})
        if k == "custom-sum":
            return A.resolve({"type": self.s_type.currentText(), "unit": int(self.s_unit.currentText()),
                              "unit_endian": self.s_uend.currentText(), "width": int(self.s_width.currentText()),
                              "complement": self.s_comp.currentText()})
        return k

    def block(self) -> ChecksumBlock:
        algo = self.algorithm()
        if isinstance(algo, dict):
            algo = {k: v for k, v in algo.items() if k not in ("name",)}
        comp = self.comp.text().strip()
        return ChecksumBlock(self.name.text().strip() or "Checksum", algo, parse_ranges(self.ranges.text()),
                             parse_ranges(self.skip.text()), to_int(self.store.text()),
                             0 if self.width.currentText() == "auto" else int(self.width.currentText()),
                             self.endian.currentText(), to_int(comp) if comp else -1, self.mode.currentData(),
                             self.rep_count.value(), to_int(self.rep_stride.text() or "0"), True,
                             self.verified.isChecked(), self.note.text())

    def test(self) -> bool:
        try:
            b = self.block()
        except (ValueError, A.AlgorithmError) as e:
            self.preview.setText(f"Error: {e}")
            return False
        if self.data is None:
            self.preview.setText(A.describe(b.algorithm))
            return True
        res = verify(self.data, [b])
        self.preview.setText("\n".join(r.line() for r in res[:20]))
        return True

    def _accept(self) -> None:
        try:
            b = self.block()
        except (ValueError, A.AlgorithmError) as e:
            QMessageBox.warning(self, "Checksum Block", str(e))
            return
        if not b.ranges:
            QMessageBox.warning(self, "Checksum Block", "Enter at least one range.")
            return
        self.result_block = b
        self.accept()


# ============================================================================== finder worker
class _FindWorker(QObject):
    progress = pyqtSignal(int, int, str)
    done = pyqtSignal(object)

    def __init__(self, data, kw):
        super().__init__()
        self.data, self.kw, self.stop = data, kw, False

    def run(self) -> None:
        try:
            res = find(self.data, progress=lambda i, n, name: self.progress.emit(i, n, name),
                       cancel=lambda: self.stop, **self.kw)
        except Exception as e:  # noqa: BLE001 - shown in the dialog
            res = e
        self.done.emit(res)


# ============================================================================== dialog
class ChecksumDialog(QDialog):
    blocksChanged = pyqtSignal()

    COLS = ["On", "Name", "Algorithm", "Ranges", "Skip", "Stored at", "Width", "Order", "Complement", "Verified",
            "Status"]

    def __init__(self, parent=None, data: bytes = b"", blocks=None, original: bytes | None = None,
                 writable: bool = True, title: str = "Checksums", profile_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("checksumDialog")
        self.resize(1000, 640)
        self.data = bytes(data)
        self.original = original
        self.blocks: list[ChecksumBlock] = [ChecksumBlock.from_dict(b.to_dict()) for b in blocks or []]
        self.writable = writable
        self.corrected_data: bytes | None = None
        self.last_results = []
        self.profile_dir = profile_dir
        self._thread = None
        self._worker = None
        self.found = []
        lay = QVBoxLayout(self)
        note = QLabel(DISCLAIMER)
        note.setWordWrap(True)
        note.setStyleSheet("color:#8a5a00")
        lay.addWidget(note)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self._blocks_tab()
        self._finder_tab()
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setFont(_mono())
        self.tabs.addTab(self.report, "Report")
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.refresh()

    # ------------------------------------------------------------------ blocks tab
    def _blocks_tab(self) -> None:
        w = QWidget()
        v = QVBoxLayout(w)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(lambda _i: self.edit_block())
        self.table.itemChanged.connect(self._on_check)
        v.addWidget(self.table, 1)
        for group in ((("Add...", self.add_block), ("Edit...", self.edit_block), ("Remove", self.remove_block),
                       ("Up", lambda: self.move(-1)), ("Down", lambda: self.move(1))),
                      (("Verify", self.verify), ("Correct", self.correct), (None, None),
                       ("Import Profile...", self.import_profile), ("Export Profile...", self.export_profile))):
            row = QHBoxLayout()
            for text, slot in group:
                if text is None:
                    row.addSpacing(12)
                    continue
                b = QPushButton(text)
                b.clicked.connect(slot)
                row.addWidget(b)
                setattr(self, "b_" + text.split("...")[0].lower().replace(" ", "_"), b)
            row.addStretch(1)
            v.addLayout(row)
        self.b_correct.setEnabled(self.writable)
        self.tabs.addTab(w, "Blocks")

    def refresh(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.blocks))
        res = {}
        if self.data:
            for b in self.blocks:
                rs = verify(self.data, [ChecksumBlock.from_dict({**b.to_dict(), "enabled": True})])
                res[id(b)] = rs
        for i, b in enumerate(self.blocks):
            on = QTableWidgetItem()
            on.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            on.setCheckState(Qt.CheckState.Checked if b.enabled else Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, on)
            rs = res.get(id(b), [])
            if not rs:
                status = ""
            elif all(r.ok for r in rs):
                status = "OK" if len(rs) == 1 else f"OK ({len(rs)})"
            else:
                bad = [r for r in rs if not r.ok]
                status = bad[0].line().split(": ", 1)[-1] if len(rs) == 1 else f"{len(bad)}/{len(rs)} wrong"
            vals = [b.name, A.short_name(b.algorithm), ranges_text(b.ranges), ranges_text(b.skip), hx(b.store),
                    str(b.value_width), b.endian.upper(), hx(b.complement_at) if b.complement_at >= 0 else "",
                    "yes" if b.verified else "no", status]
            if b.repeat_count > 1:
                vals[0] += f"  (x{b.repeat_count} every {hx(b.repeat_stride)})"
            for c, t in enumerate(vals, 1):
                it = QTableWidgetItem(t)
                if c == 10 and status:
                    it.setForeground(Qt.GlobalColor.darkGreen if status.startswith("OK") else Qt.GlobalColor.red)
                self.table.setItem(i, c, it)
        self.table.blockSignals(False)

    def _on_check(self, it) -> None:
        if it.column() == 0 and 0 <= it.row() < len(self.blocks):
            self.blocks[it.row()].enabled = it.checkState() == Qt.CheckState.Checked
            self.blocksChanged.emit()

    def _row(self) -> int:
        r = self.table.currentRow()
        return r if 0 <= r < len(self.blocks) else -1

    def add_block(self, block: ChecksumBlock | None = None) -> ChecksumBlock | None:
        if isinstance(block, ChecksumBlock):
            self.blocks.append(block)
            self.refresh()
            self.blocksChanged.emit()
            return block
        dlg = BlockEditor(self, None, self.data or None)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.blocks.append(dlg.result_block)
            self.refresh()
            self.table.selectRow(len(self.blocks) - 1)
            self.blocksChanged.emit()
            return dlg.result_block
        return None

    def edit_block(self) -> None:
        r = self._row()
        if r < 0:
            return
        b = self.blocks[r]
        dlg = BlockEditor(self, b, self.data or None)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            nb = dlg.result_block
            nb.enabled = b.enabled
            self.blocks[r] = nb
            self.refresh()
            self.table.selectRow(r)
            self.blocksChanged.emit()

    def remove_block(self) -> None:
        r = self._row()
        if r >= 0:
            del self.blocks[r]
            self.refresh()
            self.blocksChanged.emit()

    def move(self, delta: int) -> None:
        r = self._row()
        j = r + delta
        if r < 0 or not 0 <= j < len(self.blocks):
            return
        self.blocks[r], self.blocks[j] = self.blocks[j], self.blocks[r]
        self.refresh()
        self.table.selectRow(j)
        self.blocksChanged.emit()

    def verify(self) -> list:
        self.last_results = verify(self.data, self.blocks)
        self.report.setPlainText(report(self.last_results, "Verify"))
        self.refresh()
        self.tabs.setCurrentWidget(self.report)
        return self.last_results

    def correct(self) -> list:
        if not self.writable:
            return []
        buf = bytearray(self.corrected_data or self.data)
        self.last_results = correct(buf, self.blocks)
        self.corrected_data = bytes(buf)
        self.data = self.corrected_data
        self.report.setPlainText(report(self.last_results, "Correct") +
                                 "\n\nThe corrected values are written when you press OK.")
        self.refresh()
        self.tabs.setCurrentWidget(self.report)
        return self.last_results

    def import_profile(self, path: str = "") -> int:
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Import Checksum Profile", self.profile_dir,
                                                  "Checksum profiles (*.json);;All files (*)")
        if not path:
            return 0
        try:
            meta, blocks = load_profile(path)
        except (OSError, ValueError, A.AlgorithmError) as e:
            QMessageBox.warning(self, "Import Profile", str(e))
            return 0
        size = meta.get("file_size")
        if size and self.data and int(size) != len(self.data):
            QMessageBox.warning(self, "Import Profile", f"The profile was made for a {int(size):,}-byte file; "
                                f"this file has {len(self.data):,} bytes. Check every block.")
        self.blocks.extend(blocks)
        self.refresh()
        self.blocksChanged.emit()
        return len(blocks)

    def export_profile(self, path: str = "") -> str:
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Export Checksum Profile",
                                                  str(Path(self.profile_dir or ".") / "profile.ecuprofile.json"),
                                                  "Checksum profiles (*.json)")
        if not path:
            return ""
        save_profile(path, self.blocks, Path(path).stem, file_size=len(self.data) or None)
        return path

    # ------------------------------------------------------------------ finder tab
    def _finder_tab(self) -> None:
        w = QWidget()
        v = QVBoxLayout(w)
        info = QLabel("The finder tries the algorithms over ranges that start / end on boundaries and looks for a "
                      "matching value stored next to them in the ORIGINAL file. Every hit is a candidate: confirm "
                      "it (best: cross-check with a second original of the same layout) before adding it.")
        info.setWordWrap(True)
        v.addWidget(info)
        top = QHBoxLayout()
        self.f_src = QComboBox()
        self.f_src.addItem("Original file", "original")
        self.f_src.addItem("Current data", "data")
        if self.original is None:
            self.f_src.setCurrentIndex(1)
        top.addWidget(QLabel("Search in:"))
        top.addWidget(self.f_src)
        self.f_gran = QComboBox()
        self.f_gran.setEditable(True)
        self.f_gran.addItems(["auto", "0x100", "0x400", "0x1000", "0x4000", "0x10000"])
        top.addWidget(QLabel("Boundaries every:"))
        top.addWidget(self.f_gran)
        self.f_window = QSpinBox()
        self.f_window.setRange(2, 256)
        self.f_window.setValue(16)
        top.addWidget(QLabel("Window:"))
        top.addWidget(self.f_window)
        top.addStretch(1)
        v.addLayout(top)
        top2 = QHBoxLayout()
        self.f_holes = QCheckBox("Try one skipped hole (slower)")
        top2.addWidget(self.f_holes)
        self.f_8bit = QCheckBox("Include 8-bit")
        top2.addWidget(self.f_8bit)
        top2.addStretch(1)
        v.addLayout(top2)
        mid = QHBoxLayout()
        self.f_algos = QListWidget()
        self.f_algos.setMaximumWidth(220)
        for n in A.PRESETS:
            it = QListWidgetItem(n)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if n in DEFAULT_ALGORITHMS else Qt.CheckState.Unchecked)
            it.setToolTip(A.describe(n))
            self.f_algos.addItem(it)
        mid.addWidget(self.f_algos)
        right = QVBoxLayout()
        hints = QFormLayout()
        self.f_starts = QLineEdit()
        self.f_starts.setPlaceholderText("optional extra start offsets, e.g. 0x10000, 0x18000")
        self.f_ends = QLineEdit()
        self.f_ends.setPlaceholderText("optional extra end offsets")
        self.f_skip = QLineEdit()
        self.f_skip.setPlaceholderText("optional known holes, e.g. 0xC000-0xD000")
        self.f_confirm = QLineEdit()
        self.f_confirm.setPlaceholderText("optional: other original(s) of the same layout, separated by ;")
        bconf = QPushButton("...")
        bconf.setMaximumWidth(32)
        bconf.clicked.connect(self._pick_confirm)
        crow = QHBoxLayout()
        crow.addWidget(self.f_confirm)
        crow.addWidget(bconf)
        hints.addRow("Starts:", self.f_starts)
        hints.addRow("Ends:", self.f_ends)
        hints.addRow("Holes:", self.f_skip)
        hints.addRow("Cross-check with:", crow)
        right.addLayout(hints)
        self.f_table = QTableWidget(0, 7)
        self.f_table.setHorizontalHeaderLabels(["Score", "Algorithm", "Ranges", "Skip", "Stored at", "Order",
                                                "Complement"])
        self.f_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.f_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.f_table.horizontalHeader().setStretchLastSection(True)
        right.addWidget(self.f_table, 1)
        mid.addLayout(right, 1)
        v.addLayout(mid, 1)
        bot = QHBoxLayout()
        self.f_run = QPushButton("Find Checksums")
        self.f_run.clicked.connect(self.run_finder)
        self.f_cancel = QPushButton("Cancel")
        self.f_cancel.setEnabled(False)
        self.f_cancel.clicked.connect(self._cancel)
        self.f_add = QPushButton("Add Selected as Block")
        self.f_add.clicked.connect(self.add_selected)
        self.f_bar = QProgressBar()
        self.f_status = QLabel("")
        bot.addWidget(self.f_run)
        bot.addWidget(self.f_cancel)
        bot.addWidget(self.f_bar, 1)
        bot.addWidget(self.f_add)
        v.addLayout(bot)
        v.addWidget(self.f_status)
        self.tabs.addTab(w, "Checksum Finder")

    def _pick_confirm(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Other originals of the same layout", self.profile_dir,
                                                "All files (*)")
        if files:
            self.f_confirm.setText(";".join(files))

    def finder_kwargs(self) -> dict:
        algos = [self.f_algos.item(i).text() for i in range(self.f_algos.count())
                 if self.f_algos.item(i).checkState() == Qt.CheckState.Checked]
        g = self.f_gran.currentText().strip()
        others = []
        for f in self.f_confirm.text().split(";"):
            if f.strip():
                others.append(Path(f.strip()).read_bytes())
        ints = lambda t: [to_int(x) for x in t.replace(";", ",").split(",") if x.strip()]  # noqa: E731
        return {"algorithms": algos, "granularity": None if g in ("", "auto") else to_int(g),
                "window": self.f_window.value(), "search_holes": self.f_holes.isChecked(),
                "include_8bit": self.f_8bit.isChecked(), "starts": ints(self.f_starts.text()),
                "ends": ints(self.f_ends.text()), "holes": parse_ranges(self.f_skip.text()),
                "confirm_with": others}

    def finder_data(self) -> bytes:
        return self.original if self.f_src.currentData() == "original" and self.original is not None else self.data

    def run_finder(self, wait: bool = False) -> None:
        try:
            kw = self.finder_kwargs()
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Checksum Finder", str(e))
            return
        self.f_run.setEnabled(False)
        self.f_cancel.setEnabled(True)
        self.f_status.setText("Searching...")
        self._thread = QThread(self)
        self._worker = _FindWorker(self.finder_data(), kw)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_found)
        self._worker.done.connect(self._thread.quit)
        self._thread.start()

    def finder_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.stop = True

    def _on_progress(self, i: int, n: int, name: str) -> None:
        self.f_bar.setMaximum(max(1, n))
        self.f_bar.setValue(i)
        if name:
            self.f_status.setText(f"Trying {name}...")

    def _on_found(self, res) -> None:
        self.f_run.setEnabled(True)
        self.f_cancel.setEnabled(False)
        if isinstance(res, Exception):
            self.f_status.setText(f"Error: {res}")
            return
        self.found = res.candidates
        self.f_table.setRowCount(len(self.found))
        for i, c in enumerate(self.found):
            vals = [f"{c.score:.1f}", c.algorithm, ranges_text(c.ranges), ranges_text(c.skip), hx(c.store),
                    c.endian.upper(), hx(c.complement_at) if c.complement_at >= 0 else ""]
            for col, t in enumerate(vals):
                it = QTableWidgetItem(t)
                it.setToolTip(c.describe())
                self.f_table.setItem(i, col, it)
        self.f_table.resizeColumnsToContents()
        msg = f"{len(self.found)} candidate(s) from {res.tried:,} tries."
        if res.notes:
            msg += "  " + "  ".join(res.notes)
        self.f_status.setText(msg)
        self.f_status.setWordWrap(True)

    def add_selected(self) -> int:
        rows = sorted({i.row() for i in self.f_table.selectedIndexes()})
        n = 0
        for r in rows:
            if 0 <= r < len(self.found):
                b = self.found[r].to_block()
                b.verified = False
                self.blocks.append(b)
                n += 1
        if n:
            self.refresh()
            self.blocksChanged.emit()
            self.tabs.setCurrentIndex(0)
        return n

    def done(self, r: int) -> None:          # stop a running search before closing
        if self._worker is not None:
            self._worker.stop = True
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(10000)
        super().done(r)


__all__ = ["ChecksumDialog", "BlockEditor", "parse_ranges", "ranges_text", "DISCLAIMER"]
