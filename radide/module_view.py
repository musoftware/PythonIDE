"""The editor tab of a plain code module or a file without a form (moved out of radide/app.py)."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QVBoxLayout, QWidget


class ModuleView(QWidget):
    """Editor tab for a plain code module (no form)."""

    def __init__(self, plugin, path: Path):
        super().__init__()
        self.path = path
        from .editor import make_editor
        self.editor = make_editor(plugin, path)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.editor)
