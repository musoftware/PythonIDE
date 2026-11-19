"""New Project dialog (VS 2005 style)."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QStyle, QVBoxLayout)

from .languages import all_plugins
from .properties import valid_identifier


def default_location() -> Path:
    return Path.home() / "Documents" / "RAD IDE Projects"


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.resize(560, 380)
        self.templates = QListWidget()
        self.templates.setViewMode(QListWidget.ViewMode.IconMode)
        self.templates.setIconSize(QSize(40, 40))
        self.templates.setGridSize(QSize(150, 80))
        self.templates.setMovement(QListWidget.Movement.Static)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        for p in all_plugins():
            it = QListWidgetItem(icon, f"Windows Application\n{p.display_name}")
            it.setData(Qt.ItemDataRole.UserRole, p.id)
            self.templates.addItem(it)
        self.templates.setCurrentRow(0)
        self.desc = QLabel()
        self.templates.currentItemChanged.connect(self._update_desc)

        self.name = QLineEdit("WindowsApplication1")
        self.location = QLineEdit(str(default_location()))
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        loc_row = QHBoxLayout()
        loc_row.addWidget(self.location, 1)
        loc_row.addWidget(browse)

        form = QFormLayout()
        form.addRow("Name:", self.name)
        form.addRow("Location:", loc_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Templates:"))
        lay.addWidget(self.templates, 1)
        lay.addWidget(self.desc)
        lay.addLayout(form)
        lay.addWidget(buttons)
        self._update_desc()

    def _update_desc(self, *_):
        it = self.templates.currentItem()
        if it:
            self.desc.setText(f"A project for creating an application with a Windows user "
                              f"interface ({it.text().splitlines()[1]})")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Project Location", self.location.text())
        if d:
            self.location.setText(d)

    def _accept(self):
        if not valid_identifier(self.name.text()):
            QMessageBox.warning(self, "New Project", "Project name must be a valid identifier.")
            return
        if self.folder().exists() and any(self.folder().iterdir()):
            QMessageBox.warning(self, "New Project", f"Folder already exists and is not empty:\n{self.folder()}")
            return
        self.accept()

    def folder(self) -> Path:
        return Path(self.location.text()) / self.name.text()

    def language(self) -> str:
        return self.templates.currentItem().data(Qt.ItemDataRole.UserRole)
