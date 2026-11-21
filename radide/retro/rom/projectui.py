"""Patch Manager - the ROM Hacking project's document tab: the source ROM, the ordered patch list (enable /
disable, move, add, remove), Build / Run and "Capture Edits" (working copy -> new patch)."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
                             QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
                             QWidget)

from .detect import detect
from .dialogs import PATCH_FILTER, ROM_FILTER
from .patches import PatchError, crc32, describe_patch
from .project import RomProject

ROLE = Qt.ItemDataRole.UserRole


class PatchManager(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    openFile = pyqtSignal(str, bool)          # path, read-only
    runRequested = pyqtSignal()
    changed = pyqtSignal()                    # rom.json changed (Solution Explorer refresh)

    def __init__(self, folder, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.rp = RomProject.load(self.folder)
        self.path = self.folder / "rom.json"
        lay = QVBoxLayout(self)
        src = QGroupBox("Source ROM (never modified)")
        sl = QVBoxLayout(src)
        self.rom_label = QLabel()
        self.rom_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.rom_label.setWordWrap(True)
        row = QHBoxLayout()
        b_set = QPushButton("Set Source ROM...")
        b_set.clicked.connect(self.choose_rom)
        b_view = QPushButton("View (read-only)")
        b_view.clicked.connect(lambda: self.rp.rom_path and self.openFile.emit(str(self.rp.rom_path), True))
        row.addWidget(b_set)
        row.addWidget(b_view)
        row.addStretch(1)
        sl.addWidget(self.rom_label)
        sl.addLayout(row)
        lay.addWidget(src)
        grp = QGroupBox("Patches (applied from top to bottom on Build)")
        gl = QHBoxLayout(grp)
        self.list = QListWidget()
        self.list.itemChanged.connect(self._on_check)
        self.list.currentRowChanged.connect(self._on_row)
        self.list.itemDoubleClicked.connect(lambda it: self.openFile.emit(str(self.rp.path(it.data(ROLE))), False))
        gl.addWidget(self.list, 1)
        col = QVBoxLayout()
        for text, slot in (("Add Patch...", self.add_patch), ("Remove", self.remove_patch),
                           ("Move Up", lambda: self.move(-1)), ("Move Down", lambda: self.move(1)),
                           ("Edit Note...", self.edit_note)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            col.addWidget(b)
        col.addStretch(1)
        gl.addLayout(col)
        lay.addWidget(grp, 1)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(120)
        lay.addWidget(self.details)
        work = QGroupBox("Working copy")
        wl = QHBoxLayout(work)
        b_work = QPushButton("Edit Working Copy")
        b_work.setToolTip("Writes clean ROM + all patches to work/ and opens it in the hex editor")
        b_work.clicked.connect(self.edit_work)
        self.fmt = QComboBox()
        self.fmt.addItems(["ips", "bps", "ups"])
        b_cap = QPushButton("Capture Edits as Patch")
        b_cap.setToolTip("The difference between the working copy and clean ROM + patches becomes a new patch")
        b_cap.clicked.connect(self.capture)
        wl.addWidget(b_work)
        wl.addWidget(QLabel("Format:"))
        wl.addWidget(self.fmt)
        wl.addWidget(b_cap)
        wl.addStretch(1)
        lay.addWidget(work)
        bottom = QHBoxLayout()
        self.fixsum = QCheckBox("Fix the header checksum after patching")
        self.fixsum.toggled.connect(self._on_fixsum)
        b_build = QPushButton("Build")
        b_build.clicked.connect(lambda: self.build())
        b_run = QPushButton("Build && Run")
        b_run.clicked.connect(self.runRequested.emit)
        b_out = QPushButton("Open Output")
        b_out.clicked.connect(lambda: self.rp.output_path.is_file() and
                              self.openFile.emit(str(self.rp.output_path), True))
        bottom.addWidget(self.fixsum)
        bottom.addStretch(1)
        for b in (b_build, b_run, b_out):
            bottom.addWidget(b)
        lay.addLayout(bottom)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        lay.addWidget(self.log)
        self.refresh()

    # document protocol
    def is_modified(self) -> bool:
        return False

    def save(self) -> bool:
        return True

    def edit_op(self, _op: str) -> None:
        pass

    def reload_from_disk(self) -> None:
        self.rp = RomProject.load(self.folder)
        self.refresh()

    # ------------------------------------------------------------------ view
    def refresh(self) -> None:
        rp = self.rp
        p = rp.rom_path
        if p is None:
            self.rom_label.setText("<i>No source ROM yet.</i> Choose your own ROM / disk / tape image file.")
        elif not p.is_file():
            self.rom_label.setText(f"<b>Missing:</b> {p}")
        else:
            data = p.read_bytes()
            info = detect(data, p.name)
            now = f"{crc32(data):08X}"
            warn = "" if not rp.rom_crc32 or now == rp.rom_crc32.upper() else \
                f"  <span style='color:#c0392b'>CRC32 changed (recorded {rp.rom_crc32})</span>"
            where = "copied into the project" if not Path(rp.rom).is_absolute() else "referenced"
            self.rom_label.setText(f"<b>{p.name}</b> ({where}) - {info.system_name}"
                                   f"{' [' + info.format + ']' if info.format else ''}, {len(data):,} bytes, "
                                   f"CRC32 {now}{warn}<br>Output: {rp.rel(rp.output_path)}")
        self.list.blockSignals(True)
        self.list.clear()
        for e in rp.patches:
            it = QListWidgetItem(e.file + (f"   - {e.note}" if e.note else ""))
            it.setData(ROLE, e.file)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if e.enabled else Qt.CheckState.Unchecked)
            if not rp.path(e.file).is_file():
                it.setToolTip("file not found")
            self.list.addItem(it)
        self.list.blockSignals(False)
        self.fixsum.blockSignals(True)
        self.fixsum.setChecked(rp.fix_checksum)
        self.fixsum.blockSignals(False)

    def _save(self) -> None:
        self.rp.save()
        self.changed.emit()

    def _say(self, text: str) -> None:
        self.log.appendPlainText(text)

    def _on_check(self, it) -> None:
        i = self.list.row(it)
        if 0 <= i < len(self.rp.patches):
            self.rp.patches[i].enabled = it.checkState() == Qt.CheckState.Checked
            self._save()

    def _on_row(self, i: int) -> None:
        if not 0 <= i < len(self.rp.patches):
            self.details.setPlainText("")
            return
        e = self.rp.patches[i]
        p = self.rp.path(e.file)
        try:
            rows = describe_patch(p.read_bytes())
        except OSError as err:
            rows = [("Error", str(err))]
        self.details.setPlainText("\n".join(f"{k}: {v}" for k, v in rows) + (f"\nNote: {e.note}" if e.note else ""))

    def _on_fixsum(self, on: bool) -> None:
        self.rp.fix_checksum = on
        self._save()

    # ------------------------------------------------------------------ commands
    def choose_rom(self, path: str | None = None, copy: bool | None = None) -> bool:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Source ROM", str(self.folder), ROM_FILTER)
            if not path:
                return False
        if copy is None:
            ans = QMessageBox.question(self, "Source ROM", "Copy the ROM into the project (rom/)?\n\n"
                                       "Yes: the project is self-contained.\nNo: the project only references the file "
                                       "where it is.\n\nThe ROM itself is never changed.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            copy = ans == QMessageBox.StandardButton.Yes
        try:
            self.rp.set_rom(path, copy)
        except OSError as e:
            QMessageBox.warning(self, "Source ROM", str(e))
            return False
        self._save()
        self.refresh()
        self._say(f"Source ROM: {self.rp.rom} (CRC32 {self.rp.rom_crc32})")
        return True

    def add_patch(self, path: str | None = None) -> bool:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Add Patch", str(self.folder), PATCH_FILTER)
            if not path:
                return False
        e = self.rp.add_patch(path)
        self._save()
        self.refresh()
        self.list.setCurrentRow(len(self.rp.patches) - 1)
        self._say(f"Added {e.file}")
        return True

    def remove_patch(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self.rp.patches):
            e = self.rp.patches.pop(i)
            self._save()
            self.refresh()
            self._say(f"Removed {e.file} from the list (the file stays in patches/)")

    def move(self, delta: int) -> None:
        i = self.list.currentRow()
        self.rp.move_patch(i, delta)
        self._save()
        self.refresh()
        self.list.setCurrentRow(max(0, min(len(self.rp.patches) - 1, i + delta)))

    def edit_note(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self.rp.patches):
            text, ok = QInputDialog.getText(self, "Patch Note", "Note:", text=self.rp.patches[i].note)
            if ok:
                self.rp.patches[i].note = text
                self._save()
                self.refresh()

    def build(self) -> Path | None:
        try:
            out = self.rp.build(log=self._say)
        except (PatchError, OSError) as e:
            self._say(f"*** {e}")
            return None
        self.changed.emit()
        return out

    def edit_work(self) -> Path | None:
        try:
            p = self.rp.make_work_copy()
        except (PatchError, OSError) as e:
            QMessageBox.warning(self, "Working Copy", str(e))
            return None
        self._save()
        self._say(f"Working copy: {self.rp.work} - edit it, save, then Capture Edits as Patch")
        self.openFile.emit(str(p), False)
        return p

    def capture(self, stem: str | None = None) -> bool:
        if stem is None:
            stem, ok = QInputDialog.getText(self, "Capture Edits", "Name of the new patch:", text="edits")
            if not ok:
                return False
        try:
            e = self.rp.capture_edits(self.fmt.currentText(), stem or "edits")
        except (PatchError, OSError) as err:
            QMessageBox.warning(self, "Capture Edits", str(err))
            return False
        if e is None:
            self._say("The working copy has no changes.")
            return False
        self._save()
        self.refresh()
        self._say(f"New patch {e.file}")
        return True


__all__ = ["PatchManager"]
