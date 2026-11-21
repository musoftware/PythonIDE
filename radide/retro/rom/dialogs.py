"""Dialogs of the ROM workbench: Go To Offset, Find / Replace, Create Patch, Apply Patch."""
from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                             QVBoxLayout, QWidget)

ROM_FILTER = ("ROMs and images (*.nes *.fds *.gb *.gbc *.gba *.sfc *.smc *.md *.gen *.bin *.sms *.gg *.a26 *.a78 "
              "*.xex *.atr *.car *.prg *.d64 *.t64 *.tap *.tzx *.sna *.exe *.com *.rom);;All files (*)")
PATCH_FILTER = "Patches (*.ips *.bps *.ups);;IPS (*.ips);;BPS (*.bps);;UPS (*.ups);;All files (*)"


def parse_offset(text: str, hex_default: bool = True, current: int = 0) -> int:
    """"0x1F0" / "$1F0" / "1F0h" / "1F0" (hex default) / "#496" or "496d" (decimal) / "+10" "-0x20" (relative)."""
    t = text.strip().replace("_", "").replace(" ", "")
    if not t:
        raise ValueError("empty offset")
    rel = 0
    if t[0] in "+-":
        rel = 1 if t[0] == "+" else -1
        t = t[1:]
    low = t.lower()
    if low.startswith("0x"):
        v = int(t[2:], 16)
    elif t.startswith("$"):
        v = int(t[1:], 16)
    elif low.endswith("h") and re.fullmatch(r"[0-9a-f]+h", low):
        v = int(t[:-1], 16)
    elif t.startswith("#"):
        v = int(t[1:], 10)
    elif low.endswith("d") and t[:-1].isdigit():
        v = int(t[:-1], 10)
    else:
        v = int(t, 16 if hex_default else 10)
    return current + rel * v if rel else v


class GotoDialog(QDialog):
    def __init__(self, parent=None, current: int = 0, size: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Go To Offset")
        self.current, self.size = current, size
        lay = QFormLayout(self)
        self.edit = QLineEdit(f"{current:X}")
        self.edit.selectAll()
        self.hex = QCheckBox("Hexadecimal")
        self.hex.setChecked(True)
        lay.addRow("Offset:", self.edit)
        lay.addRow("", self.hex)
        lay.addRow("", QLabel(f"File size: 0x{size:X} ({size:,}).  +n / -n = relative, $ / 0x / h = hex, "
                              "# = decimal"))
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addRow(box)
        self.value = current

    def accept(self) -> None:
        try:
            v = parse_offset(self.edit.text(), self.hex.isChecked(), self.current)
        except ValueError:
            QMessageBox.warning(self, "Go To Offset", "Not a valid offset.")
            return
        self.value = max(0, min(v, self.size))
        super().accept()


class FindPanel(QWidget):
    """Find / Replace bar of a hex document (hex with ?? wildcards, text, text through the table)."""
    findRequested = pyqtSignal(bool)          # backward
    findAllRequested = pyqtSignal()
    replaceRequested = pyqtSignal(bool)       # all
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(["Hex", "Text", "Text (table)"])
        self.mode.setToolTip("Hex: A9 ?? 8D (?? any byte, A? nibble wildcard, * any run)")
        self.find = QLineEdit()
        self.find.setPlaceholderText("Find: A9 ?? 8D 00 20   or text")
        self.find.returnPressed.connect(lambda: self.findRequested.emit(False))
        self.case = QCheckBox("Match case")
        self.case.setChecked(True)
        self.wild = QCheckBox("Wildcards")
        self.wild.setToolTip("Text: ? = any character, * = any run")
        b_next = QPushButton("Find Next")
        b_next.clicked.connect(lambda: self.findRequested.emit(False))
        b_prev = QPushButton("Find Previous")
        b_prev.clicked.connect(lambda: self.findRequested.emit(True))
        b_all = QPushButton("Find All")
        b_all.clicked.connect(self.findAllRequested.emit)
        b_close = QPushButton("x")
        b_close.setFixedWidth(24)
        b_close.setToolTip("Close")
        b_close.clicked.connect(self._close)
        self.find.setMinimumWidth(160)
        for w in (QLabel("Find:"), self.mode, self.find, b_next, b_prev, b_all, b_close):
            row.addWidget(w)
        row.setStretch(2, 1)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        self.replace = QLineEdit()
        self.replace.setPlaceholderText("Replace with (hex bytes in Hex mode, text otherwise)")
        b_rep = QPushButton("Replace")
        b_rep.clicked.connect(lambda: self.replaceRequested.emit(False))
        b_rall = QPushButton("Replace All")
        b_rall.clicked.connect(lambda: self.replaceRequested.emit(True))
        self.status = QLabel("")
        self.replace.setMinimumWidth(160)
        for w in (QLabel("Replace:"), self.replace, b_rep, b_rall, self.case, self.wild, self.status):
            row2.addWidget(w)
        row2.setStretch(1, 1)
        lay.addLayout(row2)

    def _close(self) -> None:
        self.hide()
        self.closed.emit()

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() == Qt.Key.Key_Escape:
            self._close()
            return
        super().keyPressEvent(e)


def _file_row(parent, edit: QLineEdit, caption: str, flt: str, save: bool = False) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(edit, 1)
    b = QPushButton("...")
    b.setFixedWidth(30)

    def pick():
        start = edit.text() or ""
        if save:
            f, _ = QFileDialog.getSaveFileName(parent, caption, start, flt)
        else:
            f, _ = QFileDialog.getOpenFileName(parent, caption, start, flt)
        if f:
            edit.setText(f)
    b.clicked.connect(pick)
    row.addWidget(b)
    return row


class CreatePatchDialog(QDialog):
    """Original + modified file -> IPS / BPS / UPS."""

    def __init__(self, parent=None, original: str = "", modified: str = "", modified_data: bytes | None = None):
        super().__init__(parent)
        self.setWindowTitle("Create Patch")
        self.modified_data = modified_data
        lay = QFormLayout(self)
        self.orig = QLineEdit(original)
        self.mod = QLineEdit(modified)
        self.fmt = QComboBox()
        self.fmt.addItems(["BPS (recommended: CRC32 checks, any size)", "IPS (classic, up to 16 MB)",
                           "UPS (CRC32 checks, reversible)"])
        self.out = QLineEdit()
        self.meta = QLineEdit()
        self.meta.setPlaceholderText("author, version, notes (BPS metadata)")
        lay.addRow("Original (clean) file:", _file_row(self, self.orig, "Original file", ROM_FILTER))
        lay.addRow("Modified file:", _file_row(self, self.mod, "Modified file", ROM_FILTER))
        if modified_data is not None:
            lay.addRow("", QLabel("(the modified data is the document as it is in the editor, saved or not)"))
        lay.addRow("Format:", self.fmt)
        lay.addRow("Metadata:", self.meta)
        lay.addRow("Save patch as:", _file_row(self, self.out, "Save Patch", PATCH_FILTER, save=True))
        self.fmt.currentIndexChanged.connect(self._suggest)
        self.mod.textChanged.connect(self._suggest)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addRow(box)
        self._suggest()

    def format(self) -> str:
        return ("bps", "ips", "ups")[self.fmt.currentIndex()]

    def _suggest(self) -> None:
        base = self.mod.text() or self.orig.text()
        if not base:
            return
        p = Path(base)
        cur = self.out.text()
        if not cur or Path(cur).suffix.lower() in (".ips", ".bps", ".ups"):
            self.out.setText(str(p.with_suffix("." + self.format())))

    def accept(self) -> None:
        from .patches import PatchError, create_patch
        try:
            a = Path(self.orig.text()).read_bytes()
            b = self.modified_data if self.modified_data is not None else Path(self.mod.text()).read_bytes()
            out = Path(self.out.text())
            if not self.out.text().strip():
                raise ValueError("choose where to save the patch")
            if out.resolve() in (Path(self.orig.text()).resolve(),) or \
                    (self.mod.text() and out.resolve() == Path(self.mod.text()).resolve()):
                raise ValueError("the patch file must not overwrite a ROM")
            data = create_patch(a, b, self.format(), self.meta.text())
            out.write_bytes(data)
        except (OSError, ValueError, PatchError) as e:
            QMessageBox.warning(self, "Create Patch", str(e))
            return
        self.result_path = out
        self.result_size = len(data)
        super().accept()


class ApplyPatchDialog(QDialog):
    """ROM + patch -> a new patched file (the ROM itself is never changed)."""

    def __init__(self, parent=None, rom: str = "", patch: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Apply Patch")
        self.resize(560, 360)
        lay = QFormLayout(self)
        self.rom = QLineEdit(rom)
        self.patch = QLineEdit(patch)
        self.out = QLineEdit()
        self.info = QPlainTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(140)
        self.check = QCheckBox("Verify CRC32 (BPS / UPS)")
        self.check.setChecked(True)
        lay.addRow("ROM:", _file_row(self, self.rom, "ROM", ROM_FILTER))
        lay.addRow("Patch:", _file_row(self, self.patch, "Patch", PATCH_FILTER))
        lay.addRow("Patch info:", self.info)
        lay.addRow("", self.check)
        lay.addRow("Save patched ROM as:", _file_row(self, self.out, "Save Patched ROM", ROM_FILTER, save=True))
        self.rom.textChanged.connect(self._suggest)
        self.patch.textChanged.connect(self._describe)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addRow(box)
        self._suggest()
        self._describe()

    def _suggest(self) -> None:
        r = self.rom.text().strip()
        if r and not self.out.text().strip():
            p = Path(r)
            self.out.setText(str(p.with_name(f"{p.stem} (patched){p.suffix}")))

    def _describe(self) -> None:
        from .patches import describe_patch
        p = Path(self.patch.text().strip()) if self.patch.text().strip() else None
        if p is None or not p.is_file():
            self.info.setPlainText("")
            return
        try:
            rows = describe_patch(p.read_bytes())
        except OSError as e:
            rows = [("Error", str(e))]
        self.info.setPlainText("\n".join(f"{k}: {v}" for k, v in rows))

    def accept(self) -> None:
        from .patches import PatchError, apply_patch
        try:
            rom = Path(self.rom.text().strip())
            out = Path(self.out.text().strip())
            if not self.out.text().strip():
                raise ValueError("choose the output file")
            if out.resolve() == rom.resolve():
                raise ValueError("the patched ROM must be a new file - the original stays unchanged")
            data = apply_patch(rom.read_bytes(), Path(self.patch.text().strip()).read_bytes(),
                               self.check.isChecked())
            out.write_bytes(data)
        except (OSError, ValueError, PatchError) as e:
            QMessageBox.warning(self, "Apply Patch", str(e))
            return
        self.result_path = out
        super().accept()


__all__ = ["ApplyPatchDialog", "CreatePatchDialog", "FindPanel", "GotoDialog", "PATCH_FILTER", "ROM_FILTER",
           "parse_offset"]
