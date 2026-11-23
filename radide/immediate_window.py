"""Debug > Windows > Immediate: evaluate an expression in the paused program (moved out of radide/app.py)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from .app import MainWindow


class ImmediateWindow(QWidget):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.input = QLineEdit()
        self.input.setFont(QFont("Consolas", 9))
        self.input.setPlaceholderText("Type an expression and press Enter (while paused)")
        self.input.returnPressed.connect(self._run)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lay.addWidget(self.log, 1)
        lay.addWidget(self.input)

    def _run(self):
        expr = self.input.text().strip()
        if not expr:
            return
        self.input.clear()
        self.log.appendPlainText(f"> {expr}")
        if self.win.session is None:
            self.log.appendPlainText("(no program is running)")
        else:
            self.win.session.evaluate(expr)

    def show_result(self, text: str):
        self.log.appendPlainText(text)
