"""Tools > NuGet Package Manager > Package Manager Console: the tool window of Visual Studio 2022.

    Package source: [All v] [gear]   Default project: [ConsoleApp v]                       [clear]
    +----------------------------------------------------------------------------------------------+
    | Each package is licensed to you by its owner. ...                                            |
    | PM> Install-Package Newtonsoft.Json -Version 13.0.3                                          |
    +----------------------------------------------------------------------------------------------+

The text after the last ``PM>`` prompt is editable: Enter runs it (radide.dotnet.nuget.console), Up / Down
walk the history (kept in QSettings), Tab completes commands, parameters, projects and package ids
(the search autocomplete endpoint), Esc clears the line. Commands run in a worker thread.
"""
from __future__ import annotations

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QMenu, QPlainTextEdit, QToolButton, QVBoxLayout,
                             QWidget)

from . import context as CX
from .config import effective_sources
from .console import ConsoleEngine
from .qtasync import alive, run_async, thread_log

PROMPT = "PM> "
BANNER = ("Each package is licensed to you by its owner. NuGet is not responsible for, nor does it grant any licenses "
          "to, third-party packages. Some packages may include dependencies which are governed by additional licenses. "
          "Follow the package source (feed) URL to determine any dependencies.\n\n"
          "Package Manager Console Host (RAD IDE)\n\n"
          "Type 'get-help' to see all available NuGet commands.\n")
MUTATING = ("install-package", "uninstall-package", "update-package", "restore-package")


class ConsoleEdit(QPlainTextEdit):
    def __init__(self, owner: "PackageManagerConsole"):
        super().__init__()
        self.owner = owner
        self.setObjectName("nugetConsoleText")
        self.setProperty("i18n_skip", True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(10)
        self.setFont(f)
        self.input_start = 0
        self.history: list[str] = []
        self.hpos = 0
        self.busy = False

    # text helpers
    def write(self, text: str) -> None:
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        if self.busy:
            c.insertText(text + "\n")
        else:                                     # output while idle goes above the prompt line
            c.setPosition(max(0, self.input_start - len(PROMPT)))
            c.insertText(text + "\n")
            self.input_start += len(text) + 1
        self.ensureCursorVisible()

    def prompt(self) -> None:
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        doc = self.toPlainText()
        if doc and not doc.endswith("\n"):
            c.insertText("\n")
        c.insertText(PROMPT)
        self.input_start = c.position()
        self.setTextCursor(c)
        self.ensureCursorVisible()

    def current_input(self) -> str:
        return self.toPlainText()[self.input_start:]

    def set_input(self, text: str) -> None:
        c = self.textCursor()
        c.setPosition(self.input_start)
        c.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        c.insertText(text)
        self.setTextCursor(c)

    def clear_all(self) -> None:
        self.setPlainText("")
        self.input_start = 0
        if not self.busy:
            self.prompt()

    # keys
    def keyPressEvent(self, e):
        k, c = e.key(), self.textCursor()
        if self.busy:
            if k == Qt.Key.Key_C and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                super().keyPressEvent(e)
            return
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line = self.current_input()
            c.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(c)
            self.owner.execute(line)
            return
        if k == Qt.Key.Key_Up or k == Qt.Key.Key_Down:
            if self.history:
                self.hpos = max(0, min(len(self.history), self.hpos + (-1 if k == Qt.Key.Key_Up else 1)))
                self.set_input(self.history[self.hpos] if self.hpos < len(self.history) else "")
            return
        if k == Qt.Key.Key_Tab:
            self.owner.complete()
            return
        if k == Qt.Key.Key_Escape:
            self.set_input("")
            return
        if k == Qt.Key.Key_Home:
            c.setPosition(self.input_start, QTextCursor.MoveMode.KeepAnchor if e.modifiers() &
                          Qt.KeyboardModifier.ShiftModifier else QTextCursor.MoveMode.MoveAnchor)
            self.setTextCursor(c)
            return
        if c.selectionStart() < self.input_start or c.position() < self.input_start:
            if e.matches(QKeySequence.StandardKey.Copy):
                super().keyPressEvent(e)
                return
            if k in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown) or \
                    e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                super().keyPressEvent(e)
                return
            c.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(c)
        if k == Qt.Key.Key_Backspace and c.position() <= self.input_start and not c.hasSelection():
            return
        super().keyPressEvent(e)

    def insertFromMimeData(self, source):
        c = self.textCursor()
        if c.position() < self.input_start:
            c.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(c)
        self.insertPlainText(source.text().replace("\r", "").split("\n")[0])


class PackageManagerConsole(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.setObjectName("nugetConsole")
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Package source:"))
        self.source = QComboBox()
        self.source.setObjectName("nugetConsoleSource")
        self.source.setMinimumContentsLength(12)
        bar.addWidget(self.source)
        gear = QToolButton()
        gear.setText("⚙")
        gear.setToolTip("Package Manager Settings")
        gear.clicked.connect(self._settings)
        bar.addWidget(gear)
        bar.addSpacing(12)
        bar.addWidget(QLabel("Default project:"))
        self.project = QComboBox()
        self.project.setObjectName("nugetConsoleProject")
        self.project.setMinimumContentsLength(14)
        bar.addWidget(self.project)
        bar.addStretch(1)
        clear = QToolButton()
        clear.setText("✕")
        clear.setToolTip("Clear Console")
        clear.clicked.connect(lambda: self.text.clear_all())
        bar.addWidget(clear)
        lay.addLayout(bar)
        self.text = ConsoleEdit(self)
        lay.addWidget(self.text, 1)
        self.engine = ConsoleEngine(lambda: self._projects, self.text.write)
        _clear = thread_log(lambda _s: self.text.clear_all())
        self.engine.clear = lambda: _clear("")
        self._projects: list = []
        try:
            hist = QSettings().value("nuget/console_history", []) or []
            self.text.history = [str(h) for h in (hist if isinstance(hist, list) else [hist])][-100:]
        except Exception:  # noqa: BLE001
            self.text.history = []
        self.text.hpos = len(self.text.history)
        self.text.setPlainText(BANNER)
        self.text.prompt()
        self.refresh_context()

    # ------------------------------------------------------------------ context
    def refresh_context(self) -> None:
        try:
            projects = CX.dotnet_projects(self.win)
        except Exception:  # noqa: BLE001
            projects = []
        self._projects = projects
        folder = CX.solution_folder(self.win)
        self.engine.solution_folder = folder
        self.engine.solution_file = CX.solution_file(self.win)
        cur = self.project.currentText()
        self.project.blockSignals(True)
        self.project.clear()
        for p in projects:
            self.project.addItem(p.name)
        cp = CX.current_project(self.win, projects)
        i = self.project.findText(cur) if cur else -1
        if i < 0 and cp is not None:
            i = self.project.findText(cp.name)
        self.project.setCurrentIndex(max(0, i))
        self.project.blockSignals(False)
        cs = self.source.currentText()
        self.source.blockSignals(True)
        self.source.clear()
        srcs = [s for s in effective_sources(folder) if s.enabled]
        if len(srcs) > 1:
            self.source.addItem("All")
        for s in srcs:
            self.source.addItem(s.name)
        j = self.source.findText(cs) if cs else self.source.findText("nuget.org")
        self.source.setCurrentIndex(max(0, j))
        self.source.blockSignals(False)

    def _settings(self) -> None:
        from .options_ui import package_sources_dialog
        if package_sources_dialog(self.win, CX.solution_folder(self.win)):
            self.refresh_context()

    # ------------------------------------------------------------------ run
    def execute(self, line: str, done=None) -> None:
        line = line.strip()
        t = self.text
        t.busy = True
        c = t.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        c.insertText("\n")
        if line:
            if not t.history or t.history[-1] != line:
                t.history.append(line)
                try:
                    QSettings().setValue("nuget/console_history", t.history[-100:])
                except Exception:  # noqa: BLE001
                    pass
            t.hpos = len(t.history)
        if not line:
            t.busy = False
            t.prompt()
            if done:
                done(True)
            return
        self.refresh_context()
        self.engine.default_project = self.project.currentText()
        self.engine.source = self.source.currentText()
        self.engine.write = thread_log(t.write)
        self.engine.error = thread_log(lambda s: t.write(s))
        self.running = True

        def finished(ok, err):
            self.running = False
            if not alive(self):
                return
            if err is not None:
                t.write(f"{type(err).__name__}: {err}")
            t.busy = False
            t.prompt()
            if line.split(" ", 1)[0].lower() in MUTATING:
                self._after_change()
            if done:
                done(bool(ok) and err is None)
        run_async(self.engine.execute, finished, line)

    running = False

    def _after_change(self) -> None:
        for np in self._projects:
            CX.reload_in_ide(self.win, np)
        try:
            from .ui import PackageManagerView
            tabs = getattr(self.win, "tabs", None)
            for i in range(tabs.count() if tabs is not None else 0):
                w = tabs.widget(i)
                if isinstance(w, PackageManagerView):
                    w.refresh()
                    w.refresh_badges()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ completion
    def complete(self, done=None) -> None:
        line = self.text.current_input()
        self.engine.default_project = self.project.currentText()

        def got(items, err):
            if not alive(self) or err is not None:
                if done:
                    done([])
                return
            self.apply_completion(line, items or [])
            if done:
                done(items or [])
        run_async(self.engine.complete, got, line)

    def apply_completion(self, line: str, items: list[str]) -> None:
        if self.text.current_input() != line or not items:
            return
        word_start = len(line) - len(line.split(" ")[-1]) if not line.endswith(" ") else len(line)
        if len(items) == 1:
            self.text.set_input(line[:word_start] + items[0] + ("" if items[0].endswith(" ") else " "))
            return
        cur_word = line[word_start:]
        starting = [it for it in items if it.lower().startswith(cur_word.lower())] or items
        prefix = starting[0]
        for it in starting[1:]:
            while not it.lower().startswith(prefix.lower()):
                prefix = prefix[:-1]
        if len(prefix) > len(cur_word):
            self.text.set_input(line[:word_start] + prefix)
            line = self.text.current_input()
        menu = QMenu(self)
        for it in items[:30]:
            menu.addAction(it, lambda it=it, ln=line, ws=word_start: self.text.set_input(ln[:ws] + it + " "))
        if not getattr(self, "_no_popup", False):
            r = self.text.cursorRect()
            menu.popup(self.text.viewport().mapToGlobal(r.bottomLeft()))
        self._last_menu = menu


def install_dock(win):
    from PyQt6.QtWidgets import QDockWidget
    panel = PackageManagerConsole(win)
    dock = QDockWidget("Package Manager Console", win)
    dock.setObjectName("PackageManagerConsole")
    dock.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    try:
        win.tabifyDockWidget(win.dock_output, dock)
    except Exception:  # noqa: BLE001
        pass
    dock.hide()
    dock.visibilityChanged.connect(lambda vis: vis and panel.refresh_context())
    win.dock_nuget_console = dock
    win.nuget_console = panel
    return dock


__all__ = ["PackageManagerConsole", "ConsoleEdit", "install_dock", "PROMPT"]
