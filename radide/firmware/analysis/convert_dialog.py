"""Firmware Converter dialog (PyQt6): convert between raw / Intel HEX / S-record / ELF, split / interleave EPROM
halves, byte-swap, cut into parts and merge files at addresses. Uses radide/firmware/formats; input files are
only read, results are always written to new files."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout,
                             QWidget)

from ..formats import FORMATS, load, save
from ..formats import split as sp


def _int(text: str, default: int = 0) -> int:
    t = text.strip()
    return int(t, 0) if t else default


class FirmwareConverterDialog(QDialog):
    def __init__(self, parent=None, path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Firmware Converter")
        self.resize(720, 480)
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.setProperty("i18n_skip", True)
        lay.addWidget(self.log)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        # ---- convert
        w = QWidget()
        f = QFormLayout(w)
        self.c_in = self._file_row(f, "Input file:", path)
        self.c_fmt = QComboBox()
        for k, (name, ext) in FORMATS.items():
            self.c_fmt.addItem(f"{name} ({ext})", k)
        f.addRow("Output format:", self.c_fmt)
        self.c_base = QLineEdit()
        self.c_base.setPlaceholderText("0x0 (raw input only)")
        f.addRow("Load address of a raw input:", self.c_base)
        self.c_fill = QLineEdit("0xFF")
        f.addRow("Fill byte for gaps (raw output):", self.c_fill)
        b = QPushButton("Convert...")
        b.clicked.connect(self.do_convert)
        f.addRow("", b)
        self.tabs.addTab(w, "Convert")

        # ---- split / swap
        w = QWidget()
        f = QFormLayout(w)
        self.s_in = self._file_row(f, "Input file:", path)
        self.s_op = QComboBox()
        for text, key in (("Split into even / odd bytes (two 8-bit EPROMs)", "deint"),
                          ("Split into even / odd 16-bit words", "deint16"),
                          ("Byte swap 16-bit (AB CD -> BA DC)", "swap2"),
                          ("Byte swap 32-bit (ABCD -> DCBA)", "swap4"),
                          ("Word swap 32-bit (ABCD -> CDAB)", "words"),
                          ("Cut into equal parts", "parts"),
                          ("Cut at sizes (e.g. 0x80000,0)", "sizes")):
            self.s_op.addItem(text, key)
        f.addRow("Operation:", self.s_op)
        self.s_parts = QSpinBox()
        self.s_parts.setRange(2, 16)
        f.addRow("Parts:", self.s_parts)
        self.s_sizes = QLineEdit("0x80000,0")
        f.addRow("Sizes:", self.s_sizes)
        b = QPushButton("Run...")
        b.clicked.connect(self.do_split)
        f.addRow("", b)
        self.tabs.addTab(w, "Split / Swap")

        # ---- merge
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Files and load addresses (HEX / S-record / ELF keep their own addresses; "
                           "write 'file @ 0x80000' for a raw file):"))
        self.m_list = QListWidget()
        self.m_list.setProperty("i18n_skip_items", True)
        v.addWidget(self.m_list, 1)
        row = QHBoxLayout()
        self.m_addr = QLineEdit()
        self.m_addr.setPlaceholderText("address for the next raw file, e.g. 0x80000")
        row.addWidget(self.m_addr)
        b = QPushButton("Add File...")
        b.clicked.connect(self.add_merge_file)
        row.addWidget(b)
        b = QPushButton("Remove")
        b.clicked.connect(lambda: self.m_list.takeItem(self.m_list.currentRow()))
        row.addWidget(b)
        b = QPushButton("Interleave even + odd...")
        b.clicked.connect(self.do_interleave)
        row.addWidget(b)
        b = QPushButton("Merge...")
        b.clicked.connect(self.do_merge)
        row.addWidget(b)
        v.addLayout(row)
        self.tabs.addTab(w, "Merge")

    # ------------------------------------------------------------------ helpers
    def _file_row(self, form, label: str, path: str) -> QLineEdit:
        row = QHBoxLayout()
        e = QLineEdit(path)
        b = QPushButton("Browse...")
        b.clicked.connect(lambda: self._browse(e))
        row.addWidget(e, 1)
        row.addWidget(b)
        form.addRow(label, row)
        return e

    def _browse(self, edit: QLineEdit) -> None:
        fn, _ = QFileDialog.getOpenFileName(self, "Firmware File", edit.text(), "All files (*.*)")
        if fn:
            edit.setText(fn)

    def say(self, text: str) -> None:
        self.log.appendPlainText(text)

    # ------------------------------------------------------------------ actions (also used by tests)
    def convert(self, src: str, dst: str, fmt: str, base: int = 0, fill: int = 0xFF) -> Path:
        mm = load(src, base=base)
        p = save(mm, dst, fmt, fill=fill)
        self.say(f"{Path(src).name} -> {p} ({FORMATS[fmt][0]}, {p.stat().st_size:,} bytes)")
        return p

    def do_convert(self) -> None:
        src = self.c_in.text().strip()
        if not src:
            return
        fmt = self.c_fmt.currentData()
        dst, _ = QFileDialog.getSaveFileName(self, "Save As", str(Path(src).with_suffix(FORMATS[fmt][1])))
        if dst:
            try:
                self.convert(src, dst, fmt, _int(self.c_base.text()), _int(self.c_fill.text(), 0xFF))
            except (OSError, ValueError, KeyError) as e:
                self.say(f"Error: {e}")

    def split(self, src: str, op: str, parts: int = 2, sizes: str = "") -> list[Path]:
        p = Path(src)
        data = p.read_bytes()
        if op == "deint":
            outs = sp.deinterleave(data, 2, 1)
            names = ["even", "odd"]
        elif op == "deint16":
            outs = sp.deinterleave(data, 2, 2)
            names = ["even16", "odd16"]
        elif op in ("swap2", "swap4"):
            outs = [sp.byteswap(data, 2 if op == "swap2" else 4)]
            names = [op]
        elif op == "words":
            outs = [sp.wordswap(data)]
            names = ["wordswap"]
        elif op == "parts":
            outs = sp.split_equal(data, parts)
            names = [f"part{i}" for i in range(len(outs))]
        else:
            outs = sp.split_sizes(data, [int(x, 0) for x in sizes.split(",") if x.strip()])
            names = [f"part{i}" for i in range(len(outs))]
        written = []
        for name, blob in zip(names, outs):
            dst = p.with_name(f"{p.stem}_{name}{p.suffix or '.bin'}")
            dst.write_bytes(blob)
            written.append(dst)
            self.say(f"Wrote {dst} ({len(blob):,} bytes)")
        return written

    def do_split(self) -> None:
        src = self.s_in.text().strip()
        if src:
            try:
                self.split(src, self.s_op.currentData(), self.s_parts.value(), self.s_sizes.text())
            except (OSError, ValueError) as e:
                self.say(f"Error: {e}")

    def add_merge_file(self) -> None:
        fns, _ = QFileDialog.getOpenFileNames(self, "Add Files", "", "All files (*.*)")
        for fn in fns:
            addr = self.m_addr.text().strip()
            self.m_list.addItem(f"{fn} @ {addr}" if addr else fn)

    def merge(self, specs: list[str], dst: str, fill: int = 0xFF) -> Path:
        maps = []
        for spec in specs:
            path, _at, addr = spec.partition(" @ ")
            maps.append((load(path.strip(), base=_int(addr)), 0))
        ov = sp.overlaps(maps)
        if ov:
            self.say("Warning: overlapping ranges " + ", ".join(f"0x{a:X}-0x{b:X}" for a, b in ov[:5]))
        m = sp.merge_maps(maps)
        p = save(m, dst, fill=fill)
        self.say(f"Merged {len(specs)} file(s) -> {p}: " + "; ".join(m.describe()))
        return p

    def do_merge(self) -> None:
        specs = [self.m_list.item(i).text() for i in range(self.m_list.count())]
        if not specs:
            return
        dst, _ = QFileDialog.getSaveFileName(self, "Save Merged Image", "", "Raw (*.bin);;Intel HEX (*.hex);;"
                                             "S-record (*.s19 *.s28 *.s37);;ELF (*.elf)")
        if dst:
            try:
                self.merge(specs, dst)
            except (OSError, ValueError, KeyError) as e:
                self.say(f"Error: {e}")

    def do_interleave(self) -> None:
        specs = [self.m_list.item(i).text().partition(" @ ")[0] for i in range(self.m_list.count())]
        if len(specs) != 2:
            self.say("Add exactly two files (even first, then odd).")
            return
        dst, _ = QFileDialog.getSaveFileName(self, "Save Interleaved Image", "", "Raw (*.bin)")
        if dst:
            try:
                out = sp.interleave([Path(specs[0]).read_bytes(), Path(specs[1]).read_bytes()])
                Path(dst).write_bytes(out)
                self.say(f"Wrote {dst} ({len(out):,} bytes)")
            except (OSError, ValueError) as e:
                self.say(f"Error: {e}")
