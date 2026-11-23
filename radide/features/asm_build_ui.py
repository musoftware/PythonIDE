"""Assembly projects in the IDE (radide/asm, radide/languages/asm_*.py, docs/ASSEMBLY.md).

* Error List: on every save the project's sources are assembled without linking (nasm / as / fasm / ml64,
  radide/asm/build.py ``Builder.check``); after Build / Run the rows of the last build (assembler and linker
  messages, radide/asm/errors.py) replace them. Double-click opens file:line.
* Program Input bar: a console program started with Ctrl+F5 reads its stdin from this bar (Enter sends a
  line, "End of input" closes stdin) - its output is in the Output window.
* Tools > Assembly Toolchains...: where NASM, FASM, GNU as / ld / gcc / gdb, MASM and GoLink are, one-click
  download of NASM / FASM / GoLink (official sites, SHA-256 checked), and the project's "asm" settings
  (architecture, linker, console mode, debug information, program or class library, GNU as syntax).
"""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFormLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)


def is_asm_project(project) -> bool:
    if project is None:
        return False
    if str(getattr(project, "language", "")).startswith("asm-"):
        return True
    langs = getattr(project, "form_languages", {}) or {}
    return any(str(v).startswith("asm-") for v in langs.values())


def _diag(d):
    from ..tools import Diag
    return Diag(d.severity, d.message, d.file, max(1, int(d.line or 1)))


# ============================================================================ Error List
def diag_provider(win) -> list:
    """tools.run_checks hook: syntax check of the Assembly sources (saved files) + the last build's link errors."""
    project = getattr(win, "project", None)
    if not is_asm_project(project):
        return []
    from ..asm import build as B
    from ..asm.errors import AsmDiag
    try:
        b = B.Builder(Path(project.folder), project, log=lambda _t: None)
        rows = b.check()
    except Exception:  # noqa: BLE001 - never break saving
        return []
    last = B.read_diagnostics(Path(project.folder))
    if last and not last.get("ok"):
        try:
            built = (Path(project.folder) / B.BUILD_DIR / B.DIAG_FILE).stat().st_mtime
            newest = max((Path(project.folder) / s).stat().st_mtime for s in b.sources() if s != "_radmain.asm")
        except (OSError, ValueError):
            built, newest = 0, 1
        if built >= newest:                      # nothing changed since: keep the linker messages
            keys = {(r.message, r.file, r.line) for r in rows}
            for x in last.get("diags", []):
                d = AsmDiag(**x)
                if (d.message, d.file, d.line) not in keys and ("undefined reference" in d.message or
                                                                "LNK" in d.message or not d.file):
                    rows.append(d)
    return [_diag(d) for d in rows]


def render_build_rows(win) -> None:
    """After a build: the Error List shows the build's rows (plus the non-assembly rows already there)."""
    from PyQt6.QtWidgets import QTreeWidgetItem
    project = getattr(win, "project", None)
    el = getattr(win, "error_list", None)
    if el is None or not is_asm_project(project):
        return
    from ..asm.build import read_diagnostics
    data = read_diagnostics(Path(project.folder))
    if not data:
        return
    asm_files = {Path(x.get("file", "")).name.lower() for x in data.get("diags", [])}
    for i in reversed(range(el.topLevelItemCount())):            # old rows of the same files / build rows
        it = el.topLevelItem(i)
        if it.text(0) in ("Error", "Warning") and (Path(it.text(2)).name.lower() in asm_files or
                                                    it.text(2).lower().endswith((".asm", ".s", ".inc")) or
                                                    not it.text(2)):
            el.takeTopLevelItem(i)
    for x in data.get("diags", []):
        it = QTreeWidgetItem([x["severity"], x["message"], x.get("file", ""), str(max(1, int(x.get("line") or 1)))])
        colour = {"Error": Qt.GlobalColor.darkRed, "Warning": Qt.GlobalColor.darkYellow}.get(x["severity"])
        if colour is not None:
            it.setForeground(0, colour)
        el.addTopLevelItem(it)
    errors = sum(el.topLevelItem(i).text(0) == "Error" for i in range(el.topLevelItemCount()))
    warnings = sum(el.topLevelItem(i).text(0) == "Warning" for i in range(el.topLevelItemCount()))
    try:
        win.dock_errors.setWindowTitle(f"Error List ({errors} errors, {warnings} warnings)")
        if not data.get("ok"):
            win.dock_errors.show()
            win.dock_errors.raise_()
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ Program Input bar
class ProgramInput(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.addWidget(QLabel("Input:"))
        self.edit = QLineEdit()
        self.edit.setMinimumWidth(240)
        self.edit.setPlaceholderText("Type a line for the running program and press Enter")
        self.edit.returnPressed.connect(self.send)
        lay.addWidget(self.edit, 1)
        b = QPushButton("Send")
        b.clicked.connect(self.send)
        lay.addWidget(b)
        e = QPushButton("End of input")
        e.setToolTip("Close the program's standard input (like Ctrl+Z in a console)")
        e.clicked.connect(self.end_input)
        lay.addWidget(e)

    def _session(self):
        s = getattr(self.win, "session", None)
        return s if s is not None and getattr(s, "running", lambda: False)() else None

    def send(self) -> None:
        s = self._session()
        text = self.edit.text()
        if s is None or not hasattr(s, "send"):
            return
        s.send(text)
        try:
            self.win._append_output(text + "\n")
        except Exception:  # noqa: BLE001
            pass
        self.edit.clear()

    def end_input(self) -> None:
        s = self._session()
        if s is None:
            return
        if callable(getattr(s, "end_input", None)):      # F5: the program's stdin pipe, never gdb's own stdin
            s.end_input()
            return
        proc = getattr(s, "proc", None)
        if proc is not None and getattr(s, "inner", None) is None:
            proc.closeWriteChannel()


def _input_dock(win) -> QDockWidget:
    dock = getattr(win, "dock_program_input", None)
    if dock is None:
        dock = QDockWidget("Program Input", win)
        dock.setObjectName("Program Input")
        dock.setWidget(ProgramInput(win))
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        out = getattr(win, "dock_output", None)
        if out is not None and not out.isFloating():      # a full-width row under the Output / Memory tabs
            win.splitDockWidget(out, dock, Qt.Orientation.Vertical)
        dock.hide()
        win.dock_program_input = dock
    return dock


def _asm_folder_exe(win) -> bool:
    """A loose assembly folder opened in place (radide/foreign/asm_folder.py) whose startup target is a console
    program (not an 8086 emulator target): it gets the Program Input bar too."""
    project = getattr(win, "project", None)
    adapter = getattr(project, "adapter", None)
    if getattr(adapter, "kind", "") != "asm":
        return False
    try:
        t = adapter.target(project.startup)
    except Exception:  # noqa: BLE001
        return False
    return t is not None and t.kind == "exe"


def _attach_session(win, s, plugin, debug: bool) -> None:
    project = win.project
    state = {"buf": "", "done": False}

    def on_output(text: str) -> None:
        if state["done"]:
            return
        state["buf"] = (state["buf"] + text)[-4000:]
        if "Build succeeded" in state["buf"] or "Build failed" in state["buf"]:
            state["done"] = True
            QTimer.singleShot(0, lambda: render_build_rows(win))

    s.output.connect(on_output)
    console = not project.forms
    try:
        from ..asm.build import settings_for
        external = settings_for(project, plugin.id).get("console") == "external"
    except Exception:  # noqa: BLE001
        external = False
    if console and not external and (not debug or callable(getattr(s, "end_input", None))):
        dock = _input_dock(win)
        dock.show()
        dock.raise_()
        try:
            dock.widget().edit.setFocus()
        except Exception:  # noqa: BLE001
            pass

    def finished(*_a):
        if not state["done"]:
            render_build_rows(win)

    s.finished.connect(finished)


# ============================================================================ Tools dialog
class _Relay(QObject):
    log = pyqtSignal(str)
    done = pyqtSignal()


class AsmToolchainsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Assembly Toolchains")
        self.resize(820, 620)
        lay = QVBoxLayout(self)
        intro = QLabel("Assemblers and linkers used by the Assembly projects. NASM, FASM and GoLink are downloaded "
                       "from their official sites into the IDE's own tools folder (no admin rights, no PATH change); "
                       "GNU as / ld / gcc / gdb come from the MinGW-w64 toolchain of the C support; MASM only from "
                       "an installed Visual Studio.")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Tool", "Path", ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        self.settings_box = self._settings_box()
        if self.settings_box is not None:
            lay.addWidget(self.settings_box)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        lay.addWidget(self.log)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.relay = _Relay()
        self.relay.log.connect(self.log.appendPlainText)
        self.relay.done.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        from ..asm import toolchain as tc
        rows = tc.status()
        self.table.setRowCount(len(rows))
        for i, (tool, title, path) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(title))
            self.table.setItem(i, 1, QTableWidgetItem(path or "not found"))
            if not path and tool in tc.RELEASES:
                b = QPushButton("Download")
                b.clicked.connect(lambda _c=False, t=tool: self.download(t))
                self.table.setCellWidget(i, 2, b)
            else:
                self.table.setCellWidget(i, 2, None)
                self.table.setItem(i, 2, QTableWidgetItem("ready" if path else "-"))
        self.table.resizeColumnToContents(0)

    def download(self, tool: str) -> None:
        from ..asm import toolchain as tc

        def work():
            tc.install(tool, self.relay.log.emit)
            self.relay.done.emit()
        threading.Thread(target=work, daemon=True).start()

    def _settings_box(self):
        project = getattr(self.win, "project", None)
        if not is_asm_project(project):
            return None
        from ..asm.build import settings_for
        s = settings_for(project)
        box = QGroupBox(f"Project settings: {project.name} ({project.language})")
        f = QFormLayout(box)
        self.arch = QComboBox()
        self.arch.addItems(["x64", "x86"])
        self.arch.setCurrentText(s["arch"])
        self.linker = QComboBox()
        self.linker.addItems(["gcc", "ld", "golink", "link", "none"])
        self.linker.setCurrentText(s["linker"])
        self.entry = QLineEdit(str(s.get("entry") or ""))
        self.subsystem = QComboBox()
        self.subsystem.addItems(["console", "windows"])
        self.subsystem.setCurrentText(s.get("subsystem") or "console")
        self.libs = QLineEdit(" ".join(s.get("libs") or []))
        self.libs.setPlaceholderText("user32 gdi32 ...")
        self.console = QComboBox()
        self.console.addItem("Output window + Program Input bar", "ide")
        self.console.addItem("Its own console window", "external")
        self.console.setCurrentIndex(1 if s.get("console") == "external" else 0)
        self.debug = QCheckBox("Debug information for gdb (line numbers)")
        self.debug.setChecked(bool(s.get("debug", True)))
        self.output = QComboBox()
        self.output.addItem("Program (_radapp.exe)", "exe")
        self.output.addItem("Class library (<Project>.dll + import library)", "dll")
        self.output.setCurrentIndex(1 if s.get("output") == "dll" else 0)
        self.syntax = QComboBox()                     # GNU as forms: which radgui include (AT&T / Intel)
        self.syntax.addItem("AT&T", "att")
        self.syntax.addItem("Intel (.intel_syntax noprefix)", "intel")
        self.syntax.setCurrentIndex(1 if s.get("syntax") == "intel" else 0)
        f.addRow("Architecture:", self.arch)
        f.addRow("Linker:", self.linker)
        f.addRow("Entry point:", self.entry)
        f.addRow("Subsystem:", self.subsystem)
        f.addRow("Extra libraries:", self.libs)
        f.addRow("Run console programs in:", self.console)
        f.addRow("Output:", self.output)
        if s.get("assembler") == "gas":
            f.addRow("Syntax (forms):", self.syntax)
        f.addRow("", self.debug)
        save = QPushButton("Save settings")
        save.clicked.connect(self.save_settings)
        f.addRow("", save)
        return box

    def save_settings(self) -> None:
        project = self.win.project
        cur = dict(project.extra.get("asm") or {})
        cur.update({"arch": self.arch.currentText(), "linker": self.linker.currentText(),
                    "entry": self.entry.text().strip() or None, "subsystem": self.subsystem.currentText(),
                    "libs": [x for x in self.libs.text().replace(",", " ").split() if x],
                    "console": self.console.currentData(), "debug": self.debug.isChecked(),
                    "output": self.output.currentData() if self.output.currentData() == "dll" else None})
        if cur.get("output") is None:
            cur.pop("output", None)
        if (cur.get("assembler") or project.language) in ("gas", "asm-gas"):
            cur["syntax"] = self.syntax.currentData()
        project.extra["asm"] = {k: v for k, v in cur.items() if v is not None}
        project.save()
        self.log.appendPlainText("Saved in project.radproj")


def show_toolchains(win) -> None:
    AsmToolchainsDialog(win).exec()


# ============================================================================ install
def install(win) -> None:
    providers = getattr(win, "diag_providers", None)
    if providers is None:
        win.diag_providers = providers = []
    providers.append(diag_provider)

    def on_session(s, debug, plugin) -> None:          # errors are logged, F5 goes on
        if str(getattr(plugin, "id", "")).startswith("asm-") or _asm_folder_exe(win):
            _attach_session(win, s, plugin, debug)
    win.extension_points.on("session_created", on_session, "assembly")

    win.show_asm_toolchains = lambda: show_toolchains(win)
    tools = next((x.menu() for x in win.menuBar().actions()
                  if x.menu() is not None and x.text().replace("&", "") == "Tools"), None)
    if tools is not None:
        a = tools.addAction("Assembly Toolchains...")
        a.setStatusTip("NASM, FASM, GNU as / ld, MASM, GoLink: status, download, project settings")
        a.triggered.connect(lambda: show_toolchains(win))
        win.a_asm_toolchains = a
