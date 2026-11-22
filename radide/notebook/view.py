"""The notebook editor tab: tool bar + one QWebEngine page that shows every cell (one Monaco editor per
cell, in the same page - light even with many cells).  Python owns the document (radide.notebook.model)
and the kernel (radide.notebook.kernel); the page reports edits and commands over QWebChannel.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, Qt, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu,
                             QMessageBox, QSizePolicy, QToolBar, QToolButton, QVBoxLayout, QWidget)

from .. import theme
from . import kernel as K
from .model import Cell, Notebook
from .render import markdown_to_html, outputs_to_html, strip_ansi

HTML = Path(__file__).resolve().parent / "notebook.html"

# Jupyter completion types -> Monaco CompletionItemKind
_KIND = {"function": 1, "builtin_function_or_method": 1, "magic": 1, "method": 0, "instance": 4,
         "statement": 4, "param": 4, "module": 8, "class": 5, "type": 5, "keyword": 17, "path": 20,
         "property": 9, "path-file": 20, "dict key": 13}


def _settings() -> QSettings:
    from PyQt6.QtCore import QCoreApplication
    org = QCoreApplication.organizationName()
    if org.upper().startswith("RADIDE-TEST"):
        return QSettings(org, QCoreApplication.applicationName() or org)
    from ..paths import qsettings      # an INI file in <install>\settings for a portable build
    return qsettings()


def _key(path: Path | None) -> str:
    return re.sub(r"[\\/:]+", "_", str(Path(path).resolve()).lower()) if path else ""


def offset_of(text: str, line: int, col: int) -> int:
    lines = text.split("\n")
    line = max(0, min(line, len(lines) - 1))
    return sum(len(x) + 1 for x in lines[:line]) + min(col, len(lines[line]))


def line_col(text: str, offset: int) -> tuple[int, int]:
    before = text[:max(0, offset)]
    return before.count("\n"), len(before) - (before.rfind("\n") + 1)


class _Page(QWebEnginePage):
    """Only the notebook page itself may load; links go to the user's browser."""
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):  # noqa: N802 - Qt override
        if url.isLocalFile() and Path(url.toLocalFile()).resolve() == HTML:
            return True
        if is_main_frame and url.scheme() in ("http", "https") and \
                nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
        return False

    def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            print(f"[notebook] {message} ({source}:{line})")


class _Bridge(QObject):
    def __init__(self, view: "NotebookView"):
        super().__init__(view)
        self.v = view

    @pyqtSlot()
    def jsReady(self):
        self.v._on_ready()

    @pyqtSlot(str, str)
    def jsChanged(self, cid, text):
        self.v._on_changed(cid, text)

    @pyqtSlot(str)
    def jsSelect(self, cid):
        self.v.selected = cid
        self.v.selectionChanged.emit(cid)

    @pyqtSlot(str, str, str)
    def jsCommand(self, cmd, cid, arg):
        QTimer.singleShot(0, lambda: self.v.command(cmd, cid or self.v.selected, arg))

    @pyqtSlot(int, str, int, int)
    def jsComplete(self, req, cid, line, col):
        self.v._complete(req, cid, line, col)

    @pyqtSlot(int, str, int, int)
    def jsHover(self, req, cid, line, col):
        self.v._hover(req, cid, line, col)

    @pyqtSlot(str)
    def jsOpenLink(self, url):
        u = QUrl(url)
        if u.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(u)


class NotebookView(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    variablesChanged = pyqtSignal(list)           # [[name, type, size, value], ...]
    kernelStatusChanged = pyqtSignal(str)
    selectionChanged = pyqtSignal(str)
    cellFinished = pyqtSignal(str, str)           # cell id, "ok" | "error" | "aborted"
    log = pyqtSignal(str)

    # set by radide.features.notebook: callable(view) -> radide.lsp.LspClient | None  (pylsp for cells)
    lsp_factory = None

    def __init__(self, path: Path | None = None, notebook: Notebook | None = None, parent=None):
        super().__init__(parent)
        self.path = Path(path).resolve() if path else None
        self.notebook = notebook or (Notebook.load(self.path) if self.path and self.path.exists()
                                     else Notebook.new(self.path))
        self.notebook.path = self.path
        self.kernel: K.KernelSession | None = None
        self.choice: K.KernelChoice | None = None
        self.choices: list[K.KernelChoice] = []
        self.selected: str | None = self.notebook.cells[0].id if self.notebook.cells else None
        self.variables: list = []
        self._modified = False
        self._ready = False
        self._pending_js: list[str] = []
        self._exec: dict[str, str] = {}               # msg_id -> cell id (user executions, in order)
        self._after_start: list = []                  # callables to run once the kernel is up
        self._clear_wait: set[str] = set()            # cells with clear_output(wait=True) pending
        self._display: dict[str, list] = {}           # display_id -> [(cell id, output dict)]
        self._dirty: set[str] = set()
        self._requests: dict[str, tuple] = {}         # msg_id -> (kind, data) for complete / inspect / vars
        self._completions: dict[int, dict] = {}
        self._deleted: list[tuple[int, Cell]] = []
        self._lsp_uri_text = ""
        self._build()
        self._flush_timer = QTimer(self, singleShot=True, interval=60, timeout=self._flush_outputs)
        theme.changed.connect(self._apply_theme)
        QTimer.singleShot(0, self._init_kernel_choice)

    # ================================================================== UI
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        tb = QToolBar("Notebook")
        tb.setIconSize(tb.iconSize())
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toolbar = tb

        def act(text, slot, tip="", shortcut=None):
            a = QAction(text, self)
            a.triggered.connect(lambda _c=False: slot())
            a.setToolTip(tip or text)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
                a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            tb.addAction(a)
            return a
        self.a_run = act("▶ Run", lambda: self.run_cell(self.selected, advance=True),
                         "Run the selected cell and select the next (Shift+Enter)")
        self.a_run_all = act("Run All", self.run_all, "Run every cell from the top")
        self.a_run_above = act("Run Above", self.run_above, "Run the cells above the selected cell")
        self.a_run_below = act("Run Below", self.run_below, "Run the selected cell and every cell below")
        tb.addSeparator()
        self.a_interrupt = act("■ Interrupt", self.interrupt, "Interrupt the kernel (stop the running cell)")
        self.a_restart = act("↻ Restart", lambda: self.restart(ask=True), "Restart the kernel (variables are lost)")
        self.a_restart_all = act("Restart && Run All", lambda: self.restart(ask=True, run_all=True),
                                 "Restart the kernel, then run every cell")
        tb.addSeparator()
        self.a_add_code = act("+ Code", lambda: self.add_cell("code"), "Insert a code cell below (B)")
        self.a_add_md = act("+ Markdown", lambda: self.add_cell("markdown"), "Insert a markdown cell below")
        self.a_clear = act("Clear Outputs", self.clear_all_outputs, "Clear the outputs of every cell")
        tb.addSeparator()
        more = QToolButton()
        more.setText("Export")
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(more)
        m.addAction("Python Script (.py)...", lambda: self.export_py())
        m.addAction("HTML Page (.html)...", lambda: self.export_html())
        m.addSeparator()
        self.a_lines = m.addAction("Line Numbers")
        self.a_lines.setCheckable(True)
        self.a_lines.setChecked(_settings().value("notebook/lineNumbers", False, type=bool))
        self.a_lines.toggled.connect(self._toggle_lines)
        more.setMenu(m)
        tb.addWidget(more)
        self.status = QLabel("Kernel: not started")
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        theme.role(self.status, "muted")
        self.status.setAccessibleName("Kernel status")
        top = QHBoxLayout()               # tool bar (may overflow into >>) | kernel status | kernel picker
        top.setContentsMargins(0, 0, 4, 0)
        top.setSpacing(4)
        tb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(tb, 1)
        top.addWidget(self.status)
        self.kernel_combo = QComboBox()
        self.kernel_combo.setMinimumContentsLength(22)
        self.kernel_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.kernel_combo.setToolTip("Kernel: the Python interpreter (with ipykernel) or Jupyter kernel that runs "
                                     "this notebook")
        self.kernel_combo.setAccessibleName("Kernel")
        self.kernel_combo.activated.connect(self._on_kernel_picked)
        top.addWidget(self.kernel_combo)
        lay.addLayout(top)

        self.web = QWebEngineView(self)
        self.web.setPage(_Page(self.web))
        self._bridge = _Bridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("nb", self._bridge)
        self.web.page().setWebChannel(self._channel)
        self.web.load(QUrl.fromLocalFile(str(HTML)))
        lay.addWidget(self.web, 1)
        self.setFocusProxy(self.web)

    def _js(self, code: str) -> None:
        if self._ready:
            self.web.page().runJavaScript(code)
        else:
            self._pending_js.append(code)

    def js_call(self, fn: str, *args) -> None:
        self._js(f"{fn}({', '.join(json.dumps(a) for a in args)});")

    def _cell_payload(self, c: Cell) -> dict:
        d = {"id": c.id, "type": c.cell_type, "source": c.source, "count": c.execution_count}
        if c.cell_type == "code":
            d["outputs"] = outputs_to_html(c.outputs)
        elif c.cell_type == "markdown":
            d["md"] = markdown_to_html(c.source, c.attachments)
        else:
            d["md"] = "<pre>" + c.source.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"
        return d

    def _on_ready(self) -> None:
        self._ready = True
        self._apply_theme()
        cells = [self._cell_payload(c) for c in self.notebook.cells]
        self.web.page().runJavaScript(
            f"nbLoad({json.dumps(cells)}, {json.dumps({'language': self._monaco_lang(), 'lineNumbers': self.a_lines.isChecked()})});")
        for code in self._pending_js:
            self.web.page().runJavaScript(code)
        self._pending_js.clear()
        QTimer.singleShot(200, self.warm_lsp)

    def warm_lsp(self) -> None:
        """Start pylsp early (its first answer takes seconds) with the cells as one virtual document."""
        client = self._lsp()
        if client is not None:
            try:
                client.did_change(self._lsp_path(), self._virtual_doc()[0])
            except Exception:  # noqa: BLE001
                pass

    def is_ready(self) -> bool:
        return self._ready

    def _apply_theme(self, *_a) -> None:
        if self._ready:
            self.web.page().runJavaScript(f"nbTheme({json.dumps(theme.monaco_theme())}, {json.dumps(theme.css_vars())});")
            self.web.page().setBackgroundColor(Qt.GlobalColor.transparent)

    def _toggle_lines(self, on: bool) -> None:
        _settings().setValue("notebook/lineNumbers", bool(on))
        self.js_call("nbLineNumbers", bool(on))

    def _monaco_lang(self) -> str:
        lang = (self.kernel.language if self.kernel is not None and self.kernel.kernel_info else
                self.notebook.language) or "python"
        return {"ir": "r", "julia": "julia", "c#": "csharp", "f#": "fsharp", "javascript": "javascript",
                "typescript": "typescript", "powershell": "powershell"}.get(lang, lang)

    # ================================================================== document
    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, on: bool) -> None:
        if on != self._modified:
            self._modified = on
            self.modifiedChanged.emit(on)

    def _on_changed(self, cid: str, text: str) -> None:
        c = self.notebook.cell(cid)
        if c is not None and c.source != text:
            c.source = text
            self.set_modified(True)

    def save(self, path: Path | None = None) -> bool:
        if path is None and self.path is None:
            return self.save_as()
        target = Path(path or self.path)
        try:
            self.notebook.save(target)
        except OSError as e:
            QMessageBox.warning(self, "Save Notebook", f"Cannot save {target.name}:\n{e}")
            return False
        self.path = target.resolve()
        err = self.notebook.validate()
        if err:
            self.log.emit(f"[notebook] {self.path.name}: saved; nbformat check: {err}")
        self.set_modified(False)
        self.saved.emit()
        return True

    def save_as(self) -> bool:
        start = str(self.path or Path.home() / "Untitled.ipynb")
        f, _ = QFileDialog.getSaveFileName(self, "Save Notebook As", start, "Jupyter Notebook (*.ipynb)")
        if not f:
            return False
        if not f.lower().endswith(".ipynb"):
            f += ".ipynb"
        return self.save(Path(f))

    def maybe_close(self) -> bool:
        """Called by the IDE before the tab closes: Save changes? and stop the kernel."""
        if self._modified:
            r = QMessageBox.question(self, "Notebook", f"Save changes to {self.title()}?",
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                     QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel:
                return False
            if r == QMessageBox.StandardButton.Save and not self.save():
                return False
        self.shutdown_kernel()
        return True

    def title(self) -> str:
        return self.path.name if self.path else "Untitled.ipynb"

    # ------------------------------------------------------------------ cell editing
    def add_cell(self, cell_type: str = "code", below: str | None = None, above: bool = False,
                 source: str = "", edit: bool = True) -> Cell:
        ref = below or self.selected
        i = self.notebook.index(ref) if ref else -1
        index = (i if above else i + 1) if i >= 0 else len(self.notebook.cells)
        c = self.notebook.insert(index, Cell(cell_type=cell_type, source=source))
        self.selected = c.id
        self.js_call("nbInsert", index, self._cell_payload(c) | {"editing": cell_type != "code" and not source},
                     edit)
        self.set_modified(True)
        return c

    def delete_cell(self, cid: str) -> None:
        i = self.notebook.index(cid)
        if i < 0:
            return
        c = self.notebook.remove(cid)
        self._deleted.append((i, c))
        self.js_call("nbRemove", cid)
        if not self.notebook.cells:
            self.selected = None
        self.set_modified(True)

    def undo_delete(self) -> None:
        if not self._deleted:
            return
        i, c = self._deleted.pop()
        self.notebook.insert(i, c)
        self.js_call("nbInsert", i, self._cell_payload(c), False)
        self.set_modified(True)

    def move_cell(self, cid: str, delta: int) -> None:
        j = self.notebook.move(cid, delta)
        if j >= 0:
            self.js_call("nbMove", cid, j)
            self.set_modified(True)

    def set_cell_type(self, cid: str, cell_type: str) -> None:
        c = self.notebook.cell(cid)
        if c is None or c.cell_type == cell_type:
            return
        c.cell_type = cell_type
        c.outputs, c.execution_count = [], None
        html = markdown_to_html(c.source) if cell_type == "markdown" else ""
        self.js_call("nbType", cid, cell_type, html)
        self.set_modified(True)

    def set_source(self, cid: str, text: str) -> None:
        c = self.notebook.cell(cid)
        if c is not None:
            c.source = text
            self.js_call("nbSource", cid, text)
            self.set_modified(True)

    def clear_output(self, cid: str) -> None:
        c = self.notebook.cell(cid)
        if c is not None and c.cell_type == "code":
            c.outputs = []
            self.js_call("nbOutputs", cid, "")
            self.set_modified(True)

    def clear_all_outputs(self) -> None:
        for c in self.notebook.cells:
            if c.cell_type == "code" and (c.outputs or c.execution_count is not None):
                c.outputs, c.execution_count = [], None
                self.js_call("nbOutputs", c.id, "")
                self.js_call("nbState", c.id, "idle", None)
        self.set_modified(True)

    def select(self, cid: str, edit: bool = False) -> None:
        self.selected = cid
        self.js_call("nbSelect", cid, edit)

    def command(self, cmd: str, cid: str | None, arg: str = "") -> None:
        if cmd in ("add_code", "add_code_below"):
            self.add_cell("code", below=cid)
        elif cmd == "add_code_above":
            self.add_cell("code", below=cid, above=True)
        elif cmd == "add_md_below":
            self.add_cell("markdown", below=cid)
        elif cid is None:
            return
        elif cmd == "run":
            self.run_cell(cid)
        elif cmd == "run_advance":
            self.run_cell(cid, advance=True)
        elif cmd == "run_insert":
            self.run_cell(cid)
            self.add_cell("code", below=cid)
        elif cmd == "delete":
            self.delete_cell(cid)
        elif cmd == "undo_delete":
            self.undo_delete()
        elif cmd == "move_up":
            self.move_cell(cid, -1)
        elif cmd == "move_down":
            self.move_cell(cid, 1)
        elif cmd == "toggle_type":
            c = self.notebook.cell(cid)
            if c is not None:
                self.set_cell_type(cid, "markdown" if c.cell_type == "code" else "code")
        elif cmd == "to_markdown":
            self.set_cell_type(cid, "markdown")
        elif cmd == "to_code":
            self.set_cell_type(cid, "code")
        elif cmd == "clear_output":
            self.clear_output(cid)

    # ================================================================== running
    def run_cell(self, cid: str | None, advance: bool = False) -> str | None:
        c = self.notebook.cell(cid) if cid else None
        if c is None:
            return None
        msg = None
        if c.cell_type == "markdown":
            self.js_call("nbMarkdown", c.id, markdown_to_html(c.source, c.attachments), False)
        elif c.cell_type == "code":
            msg = self._queue(c)
        if advance:
            i = self.notebook.index(cid)
            if i == len(self.notebook.cells) - 1:
                self.add_cell("code", below=cid)
            else:
                self.select(self.notebook.cells[i + 1].id, edit=self.notebook.cells[i + 1].cell_type == "code")
        return msg

    def run_cells(self, cells: list[Cell]) -> None:
        for c in cells:
            if c.cell_type == "markdown":
                self.js_call("nbMarkdown", c.id, markdown_to_html(c.source, c.attachments), False)
            elif c.cell_type == "code":
                self._queue(c)

    def run_all(self) -> None:
        self.run_cells(list(self.notebook.cells))

    def run_above(self) -> None:
        i = self.notebook.index(self.selected) if self.selected else -1
        self.run_cells(self.notebook.cells[:max(i, 0)])

    def run_below(self) -> None:
        i = self.notebook.index(self.selected) if self.selected else 0
        self.run_cells(self.notebook.cells[max(i, 0):])

    def _queue(self, c: Cell) -> str | None:
        if not c.source.strip():
            return None
        if (self.kernel is None or not self.kernel.alive()) and not self.start_kernel():
            return None
        if self.kernel.status in ("starting", "restarting"):
            self.js_call("nbState", c.id, "queued")
            self._after_start.append(lambda c=c: self._queue(c))
            return "pending"
        msg_id = self.kernel.execute(c.source)
        self._exec[msg_id] = c.id
        self.js_call("nbState", c.id, "queued")
        return msg_id

    def busy(self) -> bool:
        """Cells are queued or running (or the kernel is still starting with work waiting)."""
        return bool(self._exec) or bool(self._after_start)

    # ------------------------------------------------------------------ kernel
    def _init_kernel_choice(self) -> None:
        cid = _settings().value(f"notebook/kernel/{_key(self.path)}", "") if self.path else ""
        choice = K.choice_from_id(cid) if cid else None
        quick = K.discover(self.path.parent if self.path else None, include_specs=False, quick=True)             if choice is None else []
        if choice is None:
            choice = next((c for c in quick if c.kind == "python" and "RAD IDE" not in c.label
                           and K.has_ipykernel(c.python)[0]), None) or next(
                (c for c in quick if "RAD IDE" in c.label), None)
        self.choice = choice
        self.choices = [choice] if choice else []
        self._fill_combo()

    def refresh_kernels(self) -> None:
        extra = []
        s = _settings()
        for pid in ("python-tk", "python-qt"):
            v = s.value(f"interpreter/{pid}", "")
            if v:
                extra.append(v)
        found = K.discover(self.path.parent if self.path else None, extra=extra)
        if self.choice is not None and all(c.id != self.choice.id for c in found):
            found.insert(0, self.choice)
        self.choices = found
        self._fill_combo()

    def _fill_combo(self) -> None:
        cb = self.kernel_combo
        cb.blockSignals(True)
        cb.clear()
        for c in self.choices:
            cb.addItem(c.label, c.id)
            cb.setItemData(cb.count() - 1, c.python or c.spec_name, Qt.ItemDataRole.ToolTipRole)
        cb.insertSeparator(cb.count())
        cb.addItem("Find more kernels...", "__refresh__")
        cb.addItem("Browse for a Python interpreter...", "__browse__")
        if self.choice is not None:
            cb.setCurrentIndex(max(0, cb.findData(self.choice.id)))
        cb.blockSignals(False)

    def _on_kernel_picked(self, index: int) -> None:
        data = self.kernel_combo.itemData(index)
        if data == "__refresh__":
            self.status.setText("Looking for kernels...")
            self.refresh_kernels()
            self.status.setText(f"{len(self.choices)} kernels found")
            self.kernel_combo.showPopup()
            return
        if data == "__browse__":
            f, _ = QFileDialog.getOpenFileName(self, "Python interpreter for this notebook", "",
                                               "Python (python*.exe python*);;All files (*)")
            if not f:
                self._fill_combo()
                return
            choice = K.KernelChoice(f"py:{Path(f).resolve()}", f"Python ({Path(f).parent.name})", "python",
                                    python=str(Path(f).resolve()))
            self.choices.insert(0, choice)
        else:
            choice = next((c for c in self.choices if c.id == data), None)
        if choice is not None:
            self.set_kernel(choice)

    def set_kernel(self, choice: K.KernelChoice, start: bool = True) -> None:
        if self.choice is not None and self.choice.id == choice.id and self.kernel is not None and self.kernel.alive():
            return
        self.shutdown_kernel()
        self.choice = choice
        if self.path:
            _settings().setValue(f"notebook/kernel/{_key(self.path)}", choice.id)
        if all(c.id != choice.id for c in self.choices):
            self.choices.insert(0, choice)
        self._fill_combo()
        if start:
            self.start_kernel()

    def start_kernel(self) -> bool:
        if self.kernel is not None and self.kernel.alive():
            return True
        if self.choice is None:
            self._init_kernel_choice()
            if self.choice is None:
                QMessageBox.warning(self, "Notebook", "No Python interpreter was found. Pick one with "
                                    "'Browse for a Python interpreter...' in the kernel box.")
                return False
        if self.choice.kind == "python":
            ok, info = K.has_ipykernel(self.choice.python)
            if not ok and not self._offer_ipykernel(self.choice.python):
                return False
        self.kernel = K.KernelSession(self.choice, cwd=self.path.parent if self.path else None,
                                      session_name=str(self.path or ""), parent=self)
        k = self.kernel
        k.statusChanged.connect(lambda s, k=k: self._on_status(k, s))
        k.started.connect(lambda info, k=k: self._on_started(k, info))
        k.failed.connect(lambda e, k=k: self._on_failed(k, e))
        k.iopub.connect(lambda m, k=k: self._on_iopub(k, m))
        k.shellReply.connect(lambda m, k=k: self._on_reply(k, m))
        k.inputRequested.connect(lambda p, pw, k=k: self._on_input(k, p, pw))
        k.restarted.connect(lambda k=k: self._on_restarted(k))
        k.start()
        return True

    def _offer_ipykernel(self, python: str) -> bool:
        r = QMessageBox.question(
            self, "Notebook kernel",
            f"{python}\n\ndoes not have ipykernel (needed to run notebooks).\n\nInstall it now with pip?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return False
        import subprocess
        self.status.setText("Installing ipykernel...")
        self.log.emit(f"[notebook] {' '.join(K.install_ipykernel_command(python))}")
        from .. import progress
        try:                               # pip in a worker thread, its output in the progress dialog
            out = progress.run_blocking(self, "Installing ipykernel", lambda r: progress.run_command(
                K.install_ipykernel_command(python), r, timeout=600, creationflags=K.NO_WINDOW), cancellable=True)
        except progress.Cancelled:
            self.log.emit("[notebook] pip install ipykernel cancelled")
            return False
        except (OSError, subprocess.SubprocessError) as e:
            self.log.emit(f"[notebook] pip failed: {e}")
            return False
        self.log.emit((out.stdout or "")[-5000:])
        ok, _v = K.has_ipykernel(python, refresh=True)
        if not ok:
            QMessageBox.warning(self, "Notebook kernel", "ipykernel could not be installed - see the Output window.")
        return ok

    def interrupt(self) -> None:
        if self.kernel is not None and self.kernel.alive():
            self.kernel.interrupt()

    def restart(self, ask: bool = False, run_all: bool = False) -> None:
        if self.kernel is None or not self.kernel.alive():
            self.kernel = None
            self.start_kernel()
            if run_all:
                self.run_all()
            return
        if ask and QMessageBox.question(self, "Restart Kernel", "Restart the kernel? All variables are lost.") \
                != QMessageBox.StandardButton.Yes:
            return
        self._reset_running()
        self.kernel.restart()
        if run_all:
            self.run_all()                       # queued until the kernel is back (status "restarting")

    def shutdown_kernel(self) -> None:
        k = self.kernel
        self.kernel = None
        self._reset_running()
        if k is not None:
            try:
                k.statusChanged.disconnect()
            except TypeError:
                pass
            k.shutdown()
        self._set_status_text("not started")

    def _reset_running(self) -> None:
        for cid in set(self._exec.values()):
            c = self.notebook.cell(cid)
            self.js_call("nbState", cid, "idle", c.execution_count if c else None)
        self._exec.clear()
        self._after_start.clear()
        self._requests.clear()

    def _set_status_text(self, s: str) -> None:
        self.status.setText(f"Kernel: {s}")
        self.status.setToolTip(f"{self.choice.label if self.choice else 'no kernel'}: {s}")
        self.status.setAccessibleDescription(s)
        self.kernelStatusChanged.emit(s)

    def _on_status(self, k, s: str) -> None:
        if k is not self.kernel:
            return
        self._set_status_text(s)
        if s == "dead":
            self._reset_running()
            self.log.emit(f"[notebook] kernel stopped: {k.last_error or 'the process exited'}")

    def _on_started(self, k, info: dict) -> None:
        if k is not self.kernel:
            return
        li = info.get("language_info") or {}
        if li:
            self.notebook.metadata["language_info"] = {key: li[key] for key in
                                                      ("name", "version", "mimetype", "file_extension",
                                                       "pygments_lexer", "codemirror_mode", "nbconvert_exporter")
                                                      if key in li}
        ks = {"name": "python3" if self.choice.kind == "python" else self.choice.spec_name,
              "display_name": self.choice.label, "language": (li.get("name") or self.choice.language or "python")}
        self.notebook.metadata["kernelspec"] = ks
        self.js_call("nbLang", self._monaco_lang())
        self._prepare_kernel()
        pending, self._after_start = self._after_start, []
        for fn in pending:
            fn()

    def _prepare_kernel(self) -> None:
        if self.kernel is not None and self.kernel.is_python:
            self.kernel.execute(K.VARS_HELPER, silent=True, store_history=False, allow_stdin=False)

    def _on_restarted(self, k) -> None:
        if k is not self.kernel:
            return
        self.variables = []
        self.variablesChanged.emit([])
        self._prepare_kernel()
        pending, self._after_start = self._after_start, []
        for fn in pending:
            fn()

    def _on_failed(self, k, err: str) -> None:
        if k is not self.kernel:
            return
        self._reset_running()
        self.log.emit(f"[notebook] kernel failed: {err}")
        self._set_status_text("failed")
        QMessageBox.warning(self, "Notebook kernel", f"The kernel could not start:\n\n{err}")

    def _on_input(self, k, prompt: str, password: bool) -> None:
        if k is not self.kernel:
            return
        text, ok = QInputDialog.getText(self, "Input requested by the notebook", prompt or "input():",
                                        QLineEdit.EchoMode.Password if password else QLineEdit.EchoMode.Normal)
        k.send_input(text if ok else "")

    # ------------------------------------------------------------------ messages
    def _on_iopub(self, k, m: dict) -> None:
        if k is not self.kernel:
            return
        t = m["msg_type"]
        if t == "rad_log":
            self.log.emit("[notebook] " + m["content"].get("text", ""))
            return
        cid = self._exec.get(m["parent_header"].get("msg_id", ""))
        content = m["content"]
        if t == "update_display_data":
            did = (content.get("transient") or {}).get("display_id")
            for ccid, out in self._display.get(did, []):
                out["data"], out["metadata"] = content.get("data", {}), content.get("metadata", {})
                self._dirty.add(ccid)
            self._flush_timer.start()
            return
        if cid is None:
            return
        c = self.notebook.cell(cid)
        if c is None:
            return
        if t == "execute_input":
            c.execution_count = content.get("execution_count")
            if cid not in self._clear_wait:
                c.outputs = []
            self.js_call("nbState", cid, "running", c.execution_count)
            self._dirty.add(cid)
        elif t in ("stream", "display_data", "execute_result", "error"):
            if cid in self._clear_wait:
                self._clear_wait.discard(cid)
                c.outputs = []
            out = {"output_type": t}
            if t == "stream":
                out.update(name=content.get("name", "stdout"), text=content.get("text", ""))
                last = c.outputs[-1] if c.outputs else None
                if last and last.get("output_type") == "stream" and last.get("name") == out["name"]:
                    last["text"] += out["text"]
                    out = None
            elif t == "error":
                out.update(ename=content.get("ename", ""), evalue=content.get("evalue", ""),
                           traceback=content.get("traceback", []))
            else:
                out.update(data=content.get("data", {}), metadata=content.get("metadata", {}))
                if t == "execute_result":
                    out["execution_count"] = content.get("execution_count")
                did = (content.get("transient") or {}).get("display_id")
                if did:
                    self._display.setdefault(did, []).append((cid, out))
            if out is not None:
                c.outputs.append(out)
            self._dirty.add(cid)
            self.set_modified(True)
        elif t == "clear_output":
            if content.get("wait"):
                self._clear_wait.add(cid)
            else:
                c.outputs = []
                self._dirty.add(cid)
        self._flush_timer.start()

    def _flush_outputs(self) -> None:
        for cid in list(self._dirty):
            c = self.notebook.cell(cid)
            if c is not None:
                self.js_call("nbOutputs", cid, outputs_to_html(c.outputs))
        self._dirty.clear()

    def _on_reply(self, k, m: dict) -> None:
        if k is not self.kernel:
            return
        mid = m["parent_header"].get("msg_id", "")
        content = m["content"]
        if mid in self._exec:
            cid = self._exec.pop(mid)
            self._clear_wait.discard(cid)
            c = self.notebook.cell(cid)
            status = content.get("status", "ok")
            if c is not None:
                for p in content.get("payload") or []:
                    if p.get("source") == "page":
                        text = (p.get("data") or {}).get("text/plain", "")
                        c.outputs.append({"output_type": "stream", "name": "stdout", "text": strip_ansi(text)})
                        self._dirty.add(cid)
                    elif p.get("source") == "set_next_input" and p.get("text") and not p.get("replace"):
                        self.add_cell("code", below=cid, source=p["text"], edit=False)
                self._flush_outputs()
                count = content.get("execution_count", c.execution_count) if status != "aborted" else c.execution_count
                if status != "aborted":
                    c.execution_count = count
                self.js_call("nbState", cid, "error" if status == "error" else "idle", c.execution_count)
            self.cellFinished.emit(cid, status)
            if not self._exec:
                self.refresh_variables()
            return
        req = self._requests.pop(mid, None)
        if req is None:
            return
        kind, data = req
        if kind == "vars":
            v = K.parse_vars(content)
            if v is not None:
                self.variables = v
                self.variablesChanged.emit(v)
        elif kind == "complete":
            self._kernel_completions(data, content)
        elif kind == "inspect":
            req_id = data
            text = ""
            if content.get("found"):
                text = strip_ansi((content.get("data") or {}).get("text/plain", ""))
            self.js_call("nbResolve", req_id, ("```\n" + text[:4000] + "\n```") if text else None)

    def refresh_variables(self) -> None:
        if self.kernel is None or not self.kernel.alive() or not self.kernel.is_python:
            return
        mid = self.kernel.execute("", silent=True, store_history=False, allow_stdin=False,
                                  user_expressions={"v": "_rad_vars()"})
        self._requests[mid] = ("vars", None)

    def inspect_variable(self, name: str) -> None:
        """Variables window double-click: show the value in a new cell's output (DataFrames as tables)."""
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
            return
        c = self.add_cell("code", source=f"display({name})" if self.kernel and self.kernel.is_python else name,
                          edit=False)
        self.run_cell(c.id)

    # ================================================================== IntelliSense
    def _virtual_doc(self) -> tuple[str, dict[str, int]]:
        """All code cells as one Python file (magics blanked) for pylsp, and each cell's first line."""
        lines, starts = [], {}
        for c in self.notebook.cells:
            if c.cell_type != "code":
                continue
            starts[c.id] = len(lines)
            src = c.source.split("\n")
            cell_magic = bool(src) and src[0].lstrip().startswith("%%")
            for ln in src:
                s = ln.lstrip()
                if cell_magic or s.startswith(("%", "!", "?")) or s.endswith("?") and not s.startswith("#"):
                    lines.append(ln[:len(ln) - len(s)] + "pass" if s and not cell_magic else "")
                else:
                    lines.append(ln)
            lines.append("")
        return "\n".join(lines), starts

    def _lsp(self):
        f = type(self).lsp_factory
        if f is None or self._monaco_lang() != "python":
            return None
        try:
            return f(self)
        except Exception:  # noqa: BLE001
            return None

    def _lsp_path(self) -> Path:
        base = self.path or Path.cwd() / "Untitled.ipynb"
        return base.with_name(f".{base.stem}.radnb.py")

    def _complete(self, req: int, cid: str, line: int, col: int) -> None:
        c = self.notebook.cell(cid)
        if c is None:
            self.js_call("nbResolve", req, [])
            return
        state = {"kernel": None, "lsp": None, "waiting": 0, "line": line, "col": col, "cid": cid, "done": False}
        self._completions[req] = state
        if self._kernel_free():
            off = offset_of(c.source, line, col)
            mid = self.kernel.complete(c.source, off)
            self._requests[mid] = ("complete", (req, c.source))
            state["waiting"] += 1
        client = self._lsp()
        if client is not None:
            text, starts = self._virtual_doc()
            vline = starts.get(cid, 0) + line
            state["waiting"] += 1

            def got(items, req=req):
                st = self._completions.get(req)
                if st is not None:
                    st["lsp"] = items
                    st["waiting"] -= 1
                    self._maybe_resolve(req)
            try:
                client.completion(self._lsp_path(), text, vline, col, got)
            except Exception:  # noqa: BLE001
                state["waiting"] -= 1
        if state["waiting"] == 0:
            self._maybe_resolve(req)
        else:
            QTimer.singleShot(2500, lambda req=req: self._maybe_resolve(req, force=True))

    def _kernel_free(self) -> bool:
        """The kernel answers completions now: running, and no user cell queued (silent helpers are quick)."""
        return self.kernel is not None and self.kernel.alive() and             self.kernel.status in ("idle", "busy") and not self._exec

    def _kernel_completions(self, data, content: dict) -> None:
        req, code = data
        st = self._completions.get(req)
        if st is None:
            return
        items = []
        if content.get("status") == "ok":
            start, end = content.get("cursor_start", 0), content.get("cursor_end", 0)
            l1, c1 = line_col(code, start)
            l2, c2 = line_col(code, end)
            types = {(t.get("text")): t for t in (content.get("metadata") or {}).get("_jupyter_types_experimental") or []}
            for i, mt in enumerate(content.get("matches") or []):
                t = types.get(mt) or {}
                label = mt.rsplit(".", 1)[-1] if "." in mt and not mt.endswith(".") and "/" not in mt else mt
                items.append({"label": label, "insertText": mt, "filterText": mt,
                              "kind": _KIND.get(t.get("type", ""), 18), "detail": t.get("signature", "") or t.get("type", ""),
                              "sortText": f"0{i:05d}", "range": [l1, c1, l2, c2]})
        st["kernel"] = items
        st["waiting"] -= 1
        self._maybe_resolve(req)

    def _maybe_resolve(self, req: int, force: bool = False) -> None:
        st = self._completions.get(req)
        if st is None or st["done"] or (st["waiting"] > 0 and not force):
            return
        st["done"] = True
        self._completions.pop(req, None)
        items = list(st["kernel"] or [])
        seen = {i["insertText"].rsplit(".", 1)[-1] for i in items}
        for i, it in enumerate(st["lsp"] or []):
            if it.get("label", "").split("(")[0] in seen:
                continue
            it = dict(it)
            it["sortText"] = f"1{i:05d}"
            if it.get("range"):                      # virtual-document line -> cell line
                it["range"] = [st["line"], it["range"][1], st["line"], it["range"][3]]
            it.pop("additionalTextEdits", None)
            items.append(it)
        self.js_call("nbResolve", req, items)

    def _hover(self, req: int, cid: str, line: int, col: int) -> None:
        c = self.notebook.cell(cid)
        if c is None:
            self.js_call("nbResolve", req, None)
            return
        client = self._lsp()

        def kernel_inspect():
            if self._kernel_free():
                mid = self.kernel.inspect(c.source, offset_of(c.source, line, col))
                self._requests[mid] = ("inspect", req)
            else:
                self.js_call("nbResolve", req, None)
        if client is None:
            kernel_inspect()
            return
        text, starts = self._virtual_doc()
        try:
            client.did_change(self._lsp_path(), text)
        except Exception:  # noqa: BLE001
            kernel_inspect()
            return

        def got(md):
            if md:
                self.js_call("nbResolve", req, md)
            else:
                kernel_inspect()
        client.hover(self._lsp_path(), starts.get(cid, 0) + line, col, got)

    # ================================================================== export
    def export_py(self, path: Path | None = None) -> Path | None:
        if path is None:
            start = str((self.path or Path.home() / "Untitled.ipynb").with_suffix(".py"))
            f, _ = QFileDialog.getSaveFileName(self, "Export as Python Script", start, "Python (*.py)")
            if not f:
                return None
            path = Path(f)
        Path(path).write_text(self.notebook.to_py(), encoding="utf-8")
        self.log.emit(f"[notebook] exported {Path(path).name}")
        return Path(path)

    def export_html(self, path: Path | None = None) -> Path | None:
        if path is None:
            start = str((self.path or Path.home() / "Untitled.ipynb").with_suffix(".html"))
            f, _ = QFileDialog.getSaveFileName(self, "Export as HTML", start, "HTML (*.html)")
            if not f:
                return None
            path = Path(f)
        Path(path).write_text(self.notebook.to_html(self.title().rsplit(".", 1)[0]), encoding="utf-8")
        self.log.emit(f"[notebook] exported {Path(path).name}")
        return Path(path)

    # ================================================================== edit menu (IDE Edit > Undo ...)
    def edit_op(self, op: str) -> None:
        names = {"undo": "undo", "redo": "redo", "cut": "editor.action.clipboardCutAction",
                 "copy": "editor.action.clipboardCopyAction", "paste": "editor.action.clipboardPasteAction",
                 "select_all": "editor.action.selectAll"}
        if op in names:
            self._js("(function(){const e=monaco.editor.getEditors().find(x=>x.hasTextFocus());"
                     f"if(e)e.trigger('menu',{json.dumps(names[op])},null);}})();")
