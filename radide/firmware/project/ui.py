"""ECU project dialogs (Qt): Versions (save / restore / compare with map-level diffs) and Build Settings."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                             QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                             QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..checksum.blocks import hx, to_int
from .model import CONTAINERS, EcuProject, EcuProjectError


def diff_text(d) -> str:
    lines = [f"{d.a}  ->  {d.b}", d.summary(), ""]
    if d.maps:
        lines.append("Changed maps:")
        lines += ["  " + m.line() for m in d.maps]
        lines.append("")
    if d.checksum_spans:
        lines.append("Checksum values changed: " + ", ".join(f"{hx(s)}-{hx(e - 1)}" for s, e in d.checksum_spans))
    if d.unmapped and d.maps:
        lines.append(f"Changes outside known maps: {len(d.unmapped)} range(s)")
    lines.append("")
    lines.append("Byte ranges:")
    for s, e in d.ranges[:300]:
        lines.append(f"  {hx(s)}-{hx(e - 1)}  ({e - s} bytes)")
    if len(d.ranges) > 300:
        lines.append(f"  ... {len(d.ranges) - 300} more")
    return "\n".join(lines)


class VersionsDialog(QDialog):
    """Named versions of the working copy; emits ``workChanged`` after a restore."""
    workChanged = pyqtSignal()
    compareRequested = pyqtSignal(str, str)          # two file paths for the side-by-side hex compare

    def __init__(self, parent, project: EcuProject):
        super().__init__(parent)
        self.ep = project
        self.setWindowTitle(f"Versions - {project.name}")
        self.setObjectName("ecuVersionsDialog")
        self.resize(900, 560)
        lay = QVBoxLayout(self)
        split = QSplitter()
        lay.addWidget(split, 1)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Version", "Name", "Created", "Note"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_diff)
        lv.addWidget(self.table, 1)
        row = QHBoxLayout()
        for text, slot in (("Save Version...", self.save_version), ("Restore", self.restore),
                           ("Delete", self.delete), ("Hex Compare", self.hex_compare)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        lv.addLayout(row)
        crow = QHBoxLayout()
        crow.addWidget(QLabel("Compare with:"))
        self.against = QComboBox()
        crow.addWidget(self.against, 1)
        lv.addLayout(crow)
        split.addWidget(left)
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        self.diff.setFont(f)
        split.addWidget(self.diff)
        split.setSizes([480, 420])
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.against.currentIndexChanged.connect(self.show_diff)
        self.refresh()

    def keys(self) -> list[str]:
        return ["original", "work"] + [v.id for v in self.ep.versions]

    def refresh(self) -> None:
        ks = self.keys()
        self.table.setRowCount(len(ks))
        for i, k in enumerate(ks):
            v = self.ep.version(k) if k not in ("original", "work") else None
            vals = ([k, self.ep.label(k), "", "read-only" if k == "original" else "edited in the hex / map editors"]
                    if v is None else [v.id, v.name, v.created, v.note])
            for c, t in enumerate(vals):
                self.table.setItem(i, c, QTableWidgetItem(t))
        cur = self.against.currentData()
        self.against.blockSignals(True)
        self.against.clear()
        for k in ks:
            self.against.addItem(self.ep.label(k), k)
        self.against.setCurrentIndex(max(0, self.against.findData(cur or "original")))
        self.against.blockSignals(False)

    def selected(self) -> str:
        r = self.table.currentRow()
        ks = self.keys()
        return ks[r] if 0 <= r < len(ks) else "work"

    def select(self, key: str) -> None:
        ks = self.keys()
        if key in ks:
            self.table.selectRow(ks.index(key))

    def show_diff(self) -> None:
        a, b = self.against.currentData() or "original", self.selected()
        try:
            d = self.ep.diff(a, b)
        except (EcuProjectError, OSError) as e:
            self.diff.setPlainText(str(e))
            return
        self.last_diff = d
        self.diff.setPlainText(diff_text(d))

    def save_version(self, name: str = "", note: str = "") -> object:
        if not name:
            name, ok = QInputDialog.getText(self, "Save Version", "Name of the version:")
            if not ok or not name.strip():
                return None
            note, _ok = QInputDialog.getText(self, "Save Version", "Note (what changed and why):")
        v = self.ep.snapshot(name.strip(), note or "")
        self.ep.save()
        self.refresh()
        self.select(v.id)
        return v

    def restore(self) -> None:
        k = self.selected()
        if k == "work":
            return
        if QMessageBox.question(self, "Restore", f"Make '{self.ep.label(k)}' the working copy?\n"
                                "The current working copy is saved as a version first if it is not saved yet.") \
                != QMessageBox.StandardButton.Yes:
            return
        saved = self.ep.restore(k)
        self.ep.save()
        self.refresh()
        self.workChanged.emit()
        if saved is not None:
            self.diff.appendPlainText(f"\nThe previous working copy was saved as {saved.id} {saved.name}.")

    def delete(self) -> None:
        k = self.selected()
        if k in ("original", "work"):
            return
        if QMessageBox.question(self, "Delete Version", f"Delete version '{self.ep.label(k)}'?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.ep.delete_version(k)
        self.ep.save()
        self.refresh()

    def _file(self, key: str) -> str:
        if key == "original":
            return str(self.ep.original_path)
        if key == "work":
            return str(self.ep.work_path)
        v = self.ep.version(key)
        return str(self.ep.path(v.file)) if v else ""

    def hex_compare(self) -> None:
        a, b = self._file(self.against.currentData() or "original"), self._file(self.selected())
        if a and b and a != b:
            self.compareRequested.emit(a, b)


class BuildSettingsDialog(QDialog):
    def __init__(self, parent, project: EcuProject):
        super().__init__(parent)
        self.ep = project
        self.setWindowTitle("ECU Build Settings")
        self.setObjectName("ecuBuildSettings")
        form = QFormLayout(self)
        self.container = QComboBox()
        for k, label in (("bin", "Raw binary (.bin)"), ("hex", "Intel HEX (.hex)"), ("s19", "Motorola S-record (.s19)"),
                         ("same", "Same as the original")):
            self.container.addItem(label, k)
        self.container.setCurrentIndex(max(0, self.container.findData(project.container)))
        form.addRow("Output container:", self.container)
        self.base = QLineEdit(hx(project.image_base))
        form.addRow("Address of offset 0:", self.base)
        self.out = QLineEdit(project.output)
        form.addRow("Output file:", self.out)
        self.on_save = QCheckBox("Correct checksums when the working copy is saved")
        self.on_save.setChecked(project.correct_on_save)
        self.on_build = QCheckBox("Correct checksums on Build")
        self.on_build.setChecked(project.correct_on_build)
        form.addRow(self.on_save)
        form.addRow(self.on_build)
        info = QLabel(f"Original: {project.original or '-'} ({project.original_format})")
        info.setWordWrap(True)
        form.addRow(info)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _ok(self) -> None:
        try:
            base = to_int(self.base.text())
        except ValueError:
            QMessageBox.warning(self, "Build Settings", "The address must be a number (e.g. 0x80000000).")
            return
        ep = self.ep
        ep.output = self.out.text().strip()
        ep.set_container(self.container.currentData() if self.container.currentData() in CONTAINERS else "bin")
        ep.image_base = base
        ep.correct_on_save = self.on_save.isChecked()
        ep.correct_on_build = self.on_build.isChecked()
        self.accept()


__all__ = ["VersionsDialog", "BuildSettingsDialog", "diff_text"]
