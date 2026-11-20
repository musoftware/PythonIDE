"""Ring Samples gallery (Help > Ring Samples, Start Page, Activity Bar).

Every example that comes with the installed Ring - samples/, applications/, the extension tutorial, library
tests and the code examples of the Ring documentation - in one searchable tree with a highlighted code
preview and three actions:

* Run             runs the example in place with ring.exe (output in the Output window; GUI / game examples
                  open their window; examples that read the keyboard run in a console window).
* Open as Project copies the example folder to Documents\\RAD IDE Projects\\RingSamples\\<name> and opens it
                  as a Ring project (language ring-script: F5 runs/debugs the example's main file). The Ring
                  folder is never written to.
* Open Folder     shows the example's folder in Explorer.

The list comes from radide/ring_samples/index.json (tools/index_ring_samples.py, with the headless test
results) or, when that does not match the installed Ring, from a live scan. Nothing of Ring is copied
into the repository.
"""
from __future__ import annotations

import html
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QPointF, QProcess, QRectF, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (QComboBox, QDockWidget, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPlainTextEdit, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .. import ring_samples as rs

ENTRY_ROLE = Qt.ItemDataRole.UserRole + 41
KINDS = [("All kinds", ""), ("Console", "console"), ("GUI (RingQt, LibUI, OpenGL ...)", "gui"),
         ("Games (RayLib, LibSDL, Game Engine ...)", "game"), ("Web", "web")]
STATUSES = [("Any test result", ""), ("Tested: runs OK", "ok"), ("Tested: needs input", "input"),
            ("Tested: fails", "fail"), ("Tested: still running (timeout)", "timeout"), ("Not tested", "none")]
STATUS_MARK = {"ok": ("✓", "#2E7D32", "Runs OK in the headless test"),
               "input": ("⌨", "#1565C0", "Reads keyboard input"),
               "fail": ("✗", "#C62828", "Failed in the headless test"),
               "timeout": ("⏱", "#EF6C00", "Still running when the test stopped it")}
KIND_LABEL = {"console": "Console", "gui": "GUI", "game": "Game", "web": "Web"}
TOP_ORDER = ["Samples", "Applications", "Documentation", "Extensions Tutorial", "Library Tests"]


def ring_icon(color: str | None = None, size: int = 24) -> QIcon:
    """A ring with a stone (drawn, follows the theme)."""
    if color is None:
        try:
            from .. import theme
            color = theme.color("text")
        except Exception:  # noqa: BLE001
            color = "#444444"
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size * 2 / 24.0, size * 2 / 24.0)
    p.setPen(QPen(QColor(color), 2.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(4.5, 8.5, 15, 13))
    p.setBrush(QColor(color))
    p.drawPolygon(QPolygonF([QPointF(12, 1.5), QPointF(16, 5), QPointF(12, 9), QPointF(8, 5)]))
    p.end()
    return QIcon(pm)


# ===================================================================== the panel
class RingSamplesPanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.root: Path | None = None
        self.entries: list[dict] = []
        self.meta: dict = {}
        self.current: dict | None = None
        self.proc: QProcess | None = None
        self._loaded = False

        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(4)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search Ring samples (title, folder, library, description)...")
        self.search.setClearButtonEnabled(True)
        self.kind = QComboBox()
        for text, data in KINDS:
            self.kind.addItem(text, data)
        self.status = QComboBox()
        for text, data in STATUSES:
            self.status.addItem(text, data)
        top.addWidget(self.search, 1)
        top.addWidget(self.kind)
        top.addWidget(self.status)
        v.addLayout(top)
        self.info = QLabel("")
        self.info.setProperty("radRole", "muted")
        self.info.setWordWrap(True)
        v.addWidget(self.info)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.split = split
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        split.addWidget(self.tree)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 0, 0, 0)
        rv.setSpacing(4)
        self.title = QLabel("")
        f = self.title.font()
        f.setPointSizeF(f.pointSizeF() + 3)
        f.setBold(True)
        self.title.setFont(f)
        self.title.setWordWrap(True)
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        self.desc.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        buttons = QHBoxLayout()
        self.b_run = QPushButton("Run")
        self.b_run.setToolTip("Run the sample in place with ring.exe (output in the Output window)")
        self.b_stop = QPushButton("Stop")
        self.b_project = QPushButton("Open as Project")
        self.b_project.setToolTip("Copy the sample to Documents\\RAD IDE Projects\\RingSamples and open it "
                                  "as a Ring project (F5 runs it)")
        self.b_folder = QPushButton("Open Folder")
        self.b_doc = QPushButton("Documentation Page")
        for b in (self.b_run, self.b_stop, self.b_project, self.b_folder, self.b_doc):
            buttons.addWidget(b)
        buttons.addStretch(1)
        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        self.code.setFont(QFont("Consolas", 10))
        self.code.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        try:
            from ..editor import Highlighter
            from ..languages import get_plugin
            self._hl = Highlighter(get_plugin("ring-qt"), self.code.document())
        except Exception:  # noqa: BLE001 - preview without colours
            self._hl = None
        rv.addWidget(self.title)
        rv.addWidget(self.details)
        rv.addWidget(self.desc)
        rv.addLayout(buttons)
        rv.addWidget(self.code, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        v.addWidget(split, 1)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self.refill)
        self.search.textChanged.connect(lambda _t: self._timer.start())
        self.kind.currentIndexChanged.connect(lambda _i: self.refill())
        self.status.currentIndexChanged.connect(lambda _i: self.refill())
        self.tree.currentItemChanged.connect(lambda cur, _prev: self._on_item(cur))
        self.tree.itemActivated.connect(lambda it, _c: self._activate(it))
        self.b_run.clicked.connect(self.run_current)
        self.b_stop.clicked.connect(self.stop)
        self.b_project.clicked.connect(self.open_as_project)
        self.b_folder.clicked.connect(self.open_folder)
        self.b_doc.clicked.connect(self.open_doc_page)
        self._show_entry(None)

    # ------------------------------------------------------------------ data
    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self.root = find_root(self.win)
        try:
            self.entries, self.meta = rs.entries_for(self.root)
        except Exception as e:  # noqa: BLE001
            self.entries, self.meta = [], {}
            self.win.log(f"[Ring Samples] cannot read the samples: {e}")
        self.refill()

    def reload(self) -> None:
        self._loaded = False
        self.ensure_loaded()

    def _matches(self, e: dict, words: list[str], kind: str, status: str) -> bool:
        if kind and e.get("kind") != kind:
            return False
        if status:
            st = (e.get("test") or {}).get("status", "none")
            if st != status:
                return False
        cats = [w[3:] for w in words if w.startswith("in:")]
        if cats:
            low = [c.lower() for c in e["category"]]
            if not all(c in low for c in cats):
                return False
            words = [w for w in words if not w.startswith("in:")]
        if words:
            hay = " ".join([e["title"], e["id"], " ".join(e["category"]), e.get("description", ""),
                            " ".join(e.get("libs", [])), e.get("kind", "")]).lower()
            return all(w in hay for w in words)
        return True

    def refill(self, select_id: str | None = None) -> None:
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        words = [w for w in self.search.text().lower().split() if w]
        kind, status = self.kind.currentData() or "", self.status.currentData() or ""
        shown = [e for e in self.entries if self._matches(e, words, kind, status)]
        nodes: dict[tuple, QTreeWidgetItem] = {}
        counts: dict[tuple, int] = {}

        def node(path: tuple) -> QTreeWidgetItem:
            if path in nodes:
                return nodes[path]
            parent = self.tree.invisibleRootItem() if len(path) == 1 else node(path[:-1])
            it = QTreeWidgetItem([path[-1]])
            f = it.font(0)
            f.setBold(len(path) == 1)
            it.setFont(0, f)
            parent.addChild(it)
            nodes[path] = it
            return it

        def order(e):
            c = e["category"]
            top = TOP_ORDER.index(c[0]) if c[0] in TOP_ORDER else 99
            return (top, [x.lower() for x in c[1:]], e["title"].lower())
        sel = None
        for e in sorted(shown, key=order):
            path = tuple(e["category"])
            parent = node(path)
            for k in range(1, len(path) + 1):
                counts[path[:k]] = counts.get(path[:k], 0) + 1
            mark = STATUS_MARK.get((e.get("test") or {}).get("status", ""))
            it = QTreeWidgetItem([(mark[0] + "  " if mark else "") + e["title"]])
            it.setData(0, ENTRY_ROLE, e["id"])
            tip = e["id"]
            if mark:
                it.setForeground(0, QColor(mark[1]))
                tip += "\n" + mark[2] + (": " + e["test"].get("reason", "") if e["test"].get("reason") else "")
            it.setToolTip(0, tip)
            parent.addChild(it)
            if select_id and e["id"] == select_id:
                sel = it
        for path, it in nodes.items():
            it.setText(0, f"{path[-1]}  ({counts.get(path, 0)})")
            if words or len(path) == 1 and len(nodes) < 12:
                it.setExpanded(bool(words) or path[0] == "Samples")
        self.tree.setUpdatesEnabled(True)
        if sel is not None:
            self.tree.setCurrentItem(sel)
            self.tree.scrollToItem(sel)
        self._update_info(len(shown))

    def _update_info(self, n_shown: int) -> None:
        if self.root is None and not self.entries:
            self.info.setText(rs.INSTALL_HELP)
            return
        total = len(self.entries)
        s = (self.meta or {}).get("summary") or {}
        st = s.get("status") or {}
        parts = [f"{n_shown} of {total} examples"]
        if self.root is not None:
            parts.append(f"Ring: {self.root}")
        else:
            parts.append("Ring was not found - " + rs.INSTALL_HELP)
        if st:
            parts.append(f"Last test: {st.get('ok', 0)} OK, {st.get('input', 0)} need input, "
                         f"{st.get('fail', 0)} fail, {st.get('timeout', 0)} timeout")
        self.info.setText("   |   ".join(parts))

    def entry(self, entry_id: str) -> dict | None:
        return next((e for e in self.entries if e["id"] == entry_id), None)

    # ------------------------------------------------------------------ selection
    def _on_item(self, it) -> None:
        eid = it.data(0, ENTRY_ROLE) if it is not None else None
        self._show_entry(self.entry(eid) if eid else None)

    def _activate(self, it) -> None:
        if it is not None and it.data(0, ENTRY_ROLE):
            self.run_current()

    def select(self, entry_id: str) -> bool:
        e = self.entry(entry_id)
        if e is None:
            return False
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.kind.setCurrentIndex(0)
        self.status.setCurrentIndex(0)
        self.refill(select_id=entry_id)
        return True

    def _show_entry(self, e: dict | None) -> None:
        self.current = e
        has = e is not None and self.root is not None
        for b in (self.b_run, self.b_project, self.b_folder):
            b.setEnabled(has)
        self.b_doc.setVisible(bool(e and e.get("source") == "docs"))
        self.b_stop.setEnabled(self.proc is not None)
        if e is None:
            self.title.setText("Ring Samples")
            self.details.setText("")
            self.desc.setVisible(True)
            self.desc.setText("Pick a sample on the left. Run starts it with ring.exe; Open as Project copies it "
                              "into your projects folder and opens it in the IDE (F5 runs it)."
                              if self.root is not None else rs.INSTALL_HELP)
            self.code.setPlainText("")
            return
        esc = html.escape
        t = e.get("test") or {}
        rows = [f"<b>Kind:</b> {esc(KIND_LABEL.get(e.get('kind', ''), e.get('kind', '')))}"]
        if e.get("libs"):
            rows.append("<b>Libraries:</b> " + esc(", ".join(
                f"{x} ({rs.LIB_NAMES[x]})" if x in rs.LIB_NAMES else x for x in e["libs"])))
        if e.get("source") == "docs":
            d = e.get("doc") or {}
            rows.append(f"<b>From:</b> {esc(d.get('file', '').split('/')[-1])} (line {d.get('line', '?')})")
        else:
            rows.append(f"<b>Folder:</b> {esc(e['folder'])}")
            if len(e.get("files", [])) > 1:
                rows.append("<b>Files:</b> " + esc(", ".join(e["files"])))
        if e.get("input"):
            rows.append("<b>Input:</b> reads the keyboard - Run opens a console window")
        if t:
            mark = STATUS_MARK.get(t.get("status", ""), ("", "#666", ""))
            reason = f" - {esc(t['reason'])}" if t.get("reason") else ""
            rows.append(f"<b>Headless test:</b> <span style='color:{mark[1]}'>{mark[0]} "
                        f"{esc(t.get('status', ''))}</span>{reason}")
        self.title.setText(e["title"])
        self.details.setText("<br>".join(rows))
        self.desc.setText(e.get("description") or "")
        self.desc.setVisible(bool(e.get("description")))
        code = rs.code_of(self.root, e) if self.root is not None else ""
        self.code.setPlainText(code if code else "# (the file was not found in the installed Ring)")

    # ------------------------------------------------------------------ actions
    def _ring(self) -> str:
        if self.root is None:
            QMessageBox.information(self, "Ring Samples", rs.INSTALL_HELP)
            return ""
        return str(rs.ring_exe(self.root))

    def run_current(self) -> None:
        e = self.current
        exe = self._ring() if e else ""
        if not e or not exe:
            return
        try:
            f, cwd = rs.run_target(self.root, e)
        except OSError as ex:
            self.win.log(f"*** Ring Samples: {ex}")
            return
        if e.get("input") and sys.platform == "win32":
            # an interactive console: the Output window cannot type into the program
            subprocess.Popen(["cmd", "/c", exe, f.name, "&", "echo.", "&", "pause"], cwd=str(cwd),
                             creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
            self.win.log(f"[Ring Samples] {e['title']}: started in a console window (it reads the keyboard)")
            return
        self.stop()
        out = self.win.output
        try:
            self.win.dock_output.show()
            self.win.dock_output.raise_()
        except AttributeError:
            pass
        out.appendPlainText(f"------ Ring sample: {e['title']}  ({f}) ------")
        p = QProcess(self)
        p.setWorkingDirectory(str(cwd))
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda p=p: self._out(p))
        p.finished.connect(lambda code, _s, p=p, t=e["title"]: self._finished(p, code, t))
        p.errorOccurred.connect(lambda err, p=p: self.win.log(f"*** Ring Samples: {p.errorString()}")
                                if err == QProcess.ProcessError.FailedToStart else None)
        self.proc = p
        self.b_stop.setEnabled(True)
        p.start(exe, [f.name])

    def _out(self, p: QProcess) -> None:
        text = bytes(p.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n")
        if text:
            try:
                self.win._append_output(text)
            except AttributeError:
                self.win.output.insertPlainText(text)

    def _finished(self, p: QProcess, code: int, title: str) -> None:
        self._out(p)
        self.win.output.appendPlainText(f"------ {title}: exit code {code} ------")
        if p is self.proc:
            self.proc = None
            self.b_stop.setEnabled(False)
        p.deleteLater()

    def stop(self) -> None:
        p, self.proc = self.proc, None
        if p is not None and p.state() != QProcess.ProcessState.NotRunning:
            p.kill()
            p.waitForFinished(3000)
        self.b_stop.setEnabled(False)

    def open_as_project(self, _checked=False, run: bool = False, dest_parent: Path | None = None):
        e = self.current
        if not e or self._ring() == "":
            return None
        try:
            folder = rs.make_project(self.root, e, dest_parent)
        except Exception as ex:  # noqa: BLE001
            QMessageBox.warning(self, "Ring Samples", f"Cannot copy the sample:\n{ex}")
            return None
        self.win.log(f"[Ring Samples] {e['title']} copied to {folder}")
        self.win.open_project(folder)
        if run and getattr(self.win, "project", None) is not None:
            self.win.run_project(debug=True)
        return folder

    def open_folder(self) -> None:
        e = self.current
        if not e or self.root is None:
            return
        folder = rs.run_target(self.root, e)[1] if e.get("source") == "docs" else self.root / e["folder"]
        _open_path(folder)

    def open_doc_page(self) -> None:
        e = self.current
        if not e or self.root is None or e.get("source") != "docs":
            return
        stem = Path(e["doc"]["file"]).stem
        page = self.root / "documents" / "build" / "html" / f"{stem}.html"
        _open_path(page if page.exists() else self.root / "documents")


def _open_path(p: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(p))  # noqa: S606 - opening a folder/page for the user
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except OSError:
        pass


def find_root(win) -> Path | None:
    """The Ring folder - from the configured Ring interpreter (Tools > Interpreter Path) or the usual places."""
    hint = ""
    try:
        from ..languages import get_plugin
        plugin = get_plugin("ring-qt")
        configured = ""
        try:
            configured = win._configured_interpreter(plugin)
        except Exception:  # noqa: BLE001
            configured = str(win.settings.value("interpreter/ring-qt", "") or "")
        hint = plugin.find_interpreter(configured) or ""
    except Exception:  # noqa: BLE001
        pass
    return rs.find_ring_root(hint)


# ===================================================================== install
def ensure_dock(win) -> QDockWidget:
    dock = getattr(win, "dock_ring_samples", None)
    if dock is not None:
        return dock
    panel = RingSamplesPanel(win)
    dock = QDockWidget("Ring Samples", win)
    dock.setObjectName("dock_ring_samples")
    dock.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock, Qt.Orientation.Horizontal)
    win.ring_samples = panel
    win.dock_ring_samples = dock
    return dock


def show_ring_samples(win, query: str | None = None, entry_id: str | None = None, kind: str | None = None):
    dock = ensure_dock(win)
    dock.show()
    dock.raise_()
    panel = win.ring_samples
    panel.ensure_loaded()
    if not getattr(dock, "_rad_sized", False) and not dock.isFloating():
        dock._rad_sized = True
        try:
            win.resizeDocks([dock], [max(760, int(win.width() * 0.55))], Qt.Orientation.Horizontal)
        except Exception:  # noqa: BLE001
            pass
    if entry_id:
        panel.select(entry_id)
    elif query is not None or kind is not None:
        if kind is not None:
            i = panel.kind.findData(kind)
            panel.kind.setCurrentIndex(max(i, 0))
        if query is not None:
            panel.search.setText(query)
            panel.refill()
    return panel


START_LINKS = [("Browse all Ring samples...", None, None),
               ("Quick start (AQuickStart)", "in:aquickstart", None),
               ("GUI with RingQt", "in:usingqt", None),
               ("Games (RayLib, Game Engine, LibSDL)", None, "game"),
               ("Applications and games", "in:applications", None),
               ("Examples from the Ring documentation", "in:documentation", None)]


def _start_page_links(win) -> None:
    try:
        from ..app import StartPage
    except Exception:  # noqa: BLE001
        return
    for i in range(win.tabs.count()):
        page = win.tabs.widget(i)
        if isinstance(page, StartPage) and not getattr(page, "_rad_ring_samples", False) \
                and hasattr(page, "add_section"):
            sec = page.add_section("Ring Samples")
            for text, q, kind in START_LINKS:
                page.add_link(sec, text, lambda _=False, q=q, k=kind: show_ring_samples(win, q or "", kind=k or ""),
                              "Help > Ring Samples - every sample, application and documentation example "
                              "that comes with Ring")
            page._rad_ring_samples = True


def install(win) -> None:
    win.show_ring_samples = lambda query=None, entry_id=None, kind=None: show_ring_samples(win, query, entry_id,
                                                                                            kind)
    help_menu = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None
                      and a.text().replace("&", "") == "Help"), None)
    if help_menu is None:
        help_menu = win.menuBar().addMenu("&Help")
    act = QAction("Ring &Samples...", win)
    act.setIcon(ring_icon())
    act.setToolTip("Every sample, application and documentation example that comes with Ring: run them or "
                   "open them as projects")
    act.triggered.connect(lambda: show_ring_samples(win))
    acts = help_menu.actions()
    before = acts[3] if len(acts) > 3 else None
    help_menu.insertAction(before, act)
    win.a_ring_samples = act
    try:
        _start_page_links(win)
        win.tabs.currentChanged.connect(lambda _i: _start_page_links(win))
    except Exception as e:  # noqa: BLE001
        win.log(f"[Ring Samples] start page: {e}")
    try:
        from . import workbench
        workbench.register_view("ring_samples", "Ring Samples", icon=ring_icon(),
                                action=lambda w: show_ring_samples(w), modes=("vscode", "agent"), area="side",
                                order=97, tooltip="Ring Samples - run or open every example that comes with Ring")
    except Exception as e:  # noqa: BLE001
        win.log(f"[Ring Samples] activity bar: {e}")


__all__ = ["RingSamplesPanel", "ensure_dock", "install", "ring_icon", "show_ring_samples"]
