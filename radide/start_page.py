"""The Start Page tab: recent projects, New / Open, tips (moved out of radide/app.py)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QBoxLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget)

from . import APP_NAME
from .solution import EXT as SOLUTION_EXT

if TYPE_CHECKING:
    from .app import MainWindow


START_TIPS = [
    "Double-click a control on the form to write its default event handler (F7 shows the code).",
    "A solution can mix languages: add a Class Library in any language, then Add Reference and call it "
    "like normal code.",
    "F5 runs with the debugger, Ctrl+F5 without it. F9 sets a breakpoint, F10 / F11 step.",
    "Tools > Options > Environment switches the workbench between Visual Studio, VS Code and Agent layouts.",
    "Project > Manage Packages installs libraries into the project's own virtual environment (.venv).",
]


def link_button(text: str, slot, tip: str = "") -> QPushButton:
    """A flat, theme-coloured hyperlink-style button (Start Page)."""
    b = QPushButton(text)
    b.setFlat(True)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setProperty("radRole", "link")
    b.setStyleSheet("QPushButton { border: none; padding: 2px 0px; text-align: left; }"
                    "QPushButton:hover { text-decoration: underline; }")
    b.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    if tip:
        b.setToolTip(tip)
    b.clicked.connect(lambda _=False: slot())
    return b


class StartPage(QWidget):
    """Visual Studio 2005 style Start Page: Recent Projects on the left, Getting Started / templates /
    tips on the right. Features add their own boxes with add_section() / add_link()."""

    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(32, 22, 32, 22)
        lay.setSpacing(12)
        title = QLabel(f"<span style='font-size:20pt; font-weight:600'>{APP_NAME}</span>")
        title.setProperty("radRole", "heading")
        lay.addWidget(title)
        sub = QLabel("Visual RAD environment for scripting languages - design forms, write code, run and debug.")
        sub.setProperty("radRole", "muted")
        self._sub = sub
        lay.addWidget(sub)
        cols = QHBoxLayout()
        cols.setSpacing(18)
        self._cols = cols                  # side by side; one under the other on a narrow page
        lay.addLayout(cols, 1)
        self.left = QVBoxLayout()
        self.right = QVBoxLayout()
        for c, stretch in ((self.left, 2), (self.right, 3)):
            c.setSpacing(12)
            cols.addLayout(c, stretch)
        # left: Recent Projects (+ Open / Create links)
        self.recent_box, self.recent_lay = self._box("Recent Projects", self.left)
        self.left.addStretch(1)
        # right: Getting Started, then feature sections (templates, App Gallery ...), then tips
        _box, gs = self._box("Getting Started", self.right)
        for text, slot, tip in (
                ("Create a new project...", win.new_project, "File > New Project (Ctrl+Shift+N)"),
                ("Open a project or solution...", win.open_project_dialog, "File > Open Project (Ctrl+Shift+O)"),
                ("Open a file...", win.open_file_dialog, "File > Open File (Ctrl+O)"),
                ("Customize the IDE (Tools > Options)...", win.show_options, "Theme, fonts, layout, start-up")):
            gs.addWidget(link_button(text, slot, tip))
        self._sections_at = self.right.count()
        _box, tips = self._box("Did you know?", self.right)
        for t in START_TIPS:
            lbl = QLabel("•  " + t)
            lbl.setWordWrap(True)
            tips.addWidget(lbl)
        self.right.addStretch(1)
        self.refresh()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        narrow = self.width() < 760         # small screens: one column, the subtitle wraps
        want = QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        if self._cols.direction() != want:
            self._cols.setDirection(want)
        if self._sub.wordWrap() != narrow:
            self._sub.setWordWrap(narrow)

    def _box(self, title: str, column, index: int | None = None):
        box = QGroupBox(title)
        box.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 16px; margin-top: 4px; }")
        inner = QVBoxLayout(box)
        inner.setSpacing(2)
        if index is None:
            column.addWidget(box)
        else:
            column.insertWidget(index, box)
        return box, inner

    def add_section(self, title: str):
        """A new box in the right column (before the tips); returns its QVBoxLayout."""
        box, inner = self._box(title, self.right, self._sections_at)
        self._sections_at += 1
        return inner

    @staticmethod
    def add_link(layout, text: str, slot, tip: str = "") -> QPushButton:
        b = link_button(text, slot, tip)
        layout.addWidget(b)
        return b

    def refresh(self):
        """Rebuild the Recent Projects list."""
        lay = self.recent_lay

        def clear(layout):
            while layout.count():
                it = layout.takeAt(0)
                if it.widget() is not None:
                    it.widget().deleteLater()
                elif it.layout() is not None:
                    clear(it.layout())
        clear(lay)
        recent = self.win.recent_projects()
        if not recent:
            empty = QLabel("No recent projects yet.")
            empty.setProperty("radRole", "muted")
            lay.addWidget(empty)
        for path in recent:
            p = Path(path)
            name = p.stem if p.suffix.lower() == SOLUTION_EXT else p.name
            b = link_button(name, lambda f=path: self.win.open_project(Path(f)), path)
            lay.addWidget(b)
            where = QLabel(str(p.parent if p.suffix else p))
            where.setProperty("radRole", "muted")
            where.setIndent(14)
            where.setToolTip(path)
            f = QFont()
            f.setPointSizeF(max(7.0, f.pointSizeF() - 1))
            where.setFont(f)
            lay.addWidget(where)
        lay.addSpacing(8)
        row = QHBoxLayout()
        lbl = QLabel("Open:")
        row.addWidget(lbl)
        row.addWidget(link_button("Project...", self.win.open_project_dialog, "Open a project or solution"))
        row.addStretch(1)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel("Create:"))
        row.addWidget(link_button("Project...", self.win.new_project, "Create a new project"))
        row.addStretch(1)
        lay.addLayout(row)
