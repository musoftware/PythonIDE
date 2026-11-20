"""Debugger views (Visual Studio style), for every engine (built-in agents, debugpy, gdb, Delve, JDWP ...):

* Locals and Watch become trees: objects, lists, dicts, arrays, structs, VB Types/Collections expand
  (children are asked lazily from the engine: DAP variablesReference, agent 'k <handle>', JDWP fields).
* Threads window (Debug > Windows > Threads): the program's threads; double-click shows that thread's
  call stack and locals.
* Breakpoint Settings (Debug > Breakpoint Settings...): condition, hit count (= / >= / multiple of) and
  "log a message instead of stopping" (logpoint, {expression} is replaced by its value).
* Debug > Attach to Process...: list the running processes and attach debugpy (Python), gdb (native),
  Delve (Go) or netcoredbg (.NET) to one; Stop detaches and the program keeps running.
* Debug > Install Delve: builds dlv into %LOCALAPPDATA%\\RADIDE\\tools\\dlv with the Go toolchain.

Engine API (radide/debug_extras.py): session.children(ref, cb), session.watch(expr, cb),
session.threads(cb), session.select_thread(tid); StopInfo.refs maps a variable name to its handle.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from .. import debug_extras as dx

REF = Qt.ItemDataRole.UserRole + 7          # child handle of an item
LOADED = Qt.ItemDataRole.UserRole + 8       # children already asked
PLACEHOLDER = "(loading...)"


# ====================================================================== expandable trees
def _gen(win) -> int:
    return getattr(win, "_dbgx_gen", 0)


def _set_expandable(item: QTreeWidgetItem, ref) -> None:
    item.takeChildren()
    item.setData(0, REF, ref or 0)
    item.setData(0, LOADED, False)
    if ref:
        QTreeWidgetItem(item, [PLACEHOLDER])
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
    else:
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)


def _on_expanded(win, item: QTreeWidgetItem, value_col: int, type_col: int) -> None:
    ref = item.data(0, REF)
    s = win.session
    if not ref or item.data(0, LOADED) or s is None or not hasattr(s, "children"):
        return
    item.setData(0, LOADED, True)
    gen = _gen(win)

    def got(kids):
        if gen != _gen(win):
            return                                    # the program went on meanwhile
        try:
            item.takeChildren()
        except RuntimeError:                          # tree cleared
            return
        if not kids:
            QTreeWidgetItem(item, ["(no members)"])
        for name, typ, value, child in kids:
            row = [""] * (max(value_col, type_col) + 1)
            row[0], row[value_col], row[type_col] = str(name), str(value), str(typ)
            it = QTreeWidgetItem(item, row)
            it.setToolTip(value_col, str(value)[:2000])
            _set_expandable(it, child)
    s.children(ref, got)


def _attach_tree(win, tree: QTreeWidget, value_col: int, type_col: int) -> None:
    tree.setRootIsDecorated(True)
    tree.itemExpanded.connect(lambda it: _on_expanded(win, it, value_col, type_col))


# ====================================================================== breakpoint settings dialog
class BreakpointDialog(QDialog):
    HITS = [("Always stop", ""), ("When the hit count is equal to", "=="),
            ("When the hit count is a multiple of", "%"), ("When the hit count is greater than or equal to", ">=")]

    def __init__(self, parent, line: int, text: str):
        super().__init__(parent)
        self.setWindowTitle(f"Breakpoint Settings - line {line}")
        d = dx.parse_bp(text)
        form = QFormLayout()
        self.cond = QLineEdit(d["cond"], placeholderText="e.g.  x > 3   (empty = always)")
        form.addRow("Condition (stop only when true):", self.cond)
        self.hit_kind = QComboBox()
        for label, _op in self.HITS:
            self.hit_kind.addItem(label)
        self.hit_n = QSpinBox(minimum=1, maximum=1_000_000)
        op, n = "", 1
        if d["hit"]:
            import re
            m = re.fullmatch(r"\s*(==|>=|>|%|=)?\s*(\d+)\s*", d["hit"])
            if m:
                op = {"=": "==", ">": ">=", None: "=="}.get(m.group(1), m.group(1))
                n = int(m.group(2)) + (1 if m.group(1) == ">" else 0)
        self.hit_kind.setCurrentIndex(next((i for i, (_l, o) in enumerate(self.HITS) if o == op), 0))
        self.hit_n.setValue(n)
        row = QHBoxLayout()
        row.addWidget(self.hit_kind, 1)
        row.addWidget(self.hit_n)
        form.addRow("Hit count:", row)
        self.hit_n.setEnabled(bool(op))
        self.hit_kind.currentIndexChanged.connect(lambda i: self.hit_n.setEnabled(i > 0))
        self.log_on = QCheckBox("Log a message to the Output window and continue (do not stop)")
        self.log_on.setChecked(bool(d["log"]))
        self.log = QLineEdit(d["log"], placeholderText="e.g.  total is {total}, i = {i}")
        self.log.setEnabled(bool(d["log"]))
        self.log_on.toggled.connect(self.log.setEnabled)
        hint = QLabel("Expressions in { } are replaced by their values.")
        from .. import theme
        theme.role(hint, "muted")
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self.log_on)
        lay.addWidget(self.log)
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(520, self.sizeHint().height())

    def value(self) -> str:
        op = self.HITS[self.hit_kind.currentIndex()][1]
        hit = f"{op}{self.hit_n.value()}" if op else ""
        return dx.encode_bp(self.cond.text(), hit, self.log.text() if self.log_on.isChecked() else "")


# ====================================================================== attach to process dialog
class AttachDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Attach to Process")
        self.procs: list[dict] = []
        self.filter = QLineEdit(placeholderText="Filter processes (name, PID or title)")
        self.only = QCheckBox("Only Python and debuggable programs")
        self.only.setChecked(False)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Process", "PID", "Kind", "Title"])
        self.tree.setRootIsDecorated(False)
        self.tree.setSortingEnabled(True)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tree.itemDoubleClicked.connect(lambda *_: self.accept())
        self.engine = QComboBox()
        self.engine.addItem("Automatic", "")
        for k, label in dx.ATTACH_ENGINES.items():
            self.engine.addItem(label, k)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        top = QHBoxLayout()
        top.addWidget(self.filter, 1)
        top.addWidget(self.only)
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Attach with:"))
        bottom.addWidget(self.engine, 1)
        bottom.addWidget(refresh)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.attach_btn = bb.addButton("Attach", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.tree, 1)
        lay.addLayout(bottom)
        lay.addWidget(bb)
        self.filter.textChanged.connect(self._fill)
        self.only.toggled.connect(self._fill)
        self.resize(760, 520)
        self.refresh()

    def refresh(self):
        import os
        me = os.getpid()
        self.procs = [p for p in dx.list_processes() if p["pid"] not in (0, 4, me)]
        self._fill()

    def _fill(self):
        text = self.filter.text().strip().lower()
        self.tree.clear()
        for p in self.procs:
            if self.only.isChecked() and p["kind"] == "native" and not p["title"]:
                continue
            hay = f"{p['name']} {p['pid']} {p['title']}".lower()
            if text and text not in hay:
                continue
            it = QTreeWidgetItem(self.tree, [p["name"], str(p["pid"]), p["kind"], p["title"]])
            it.setData(1, Qt.ItemDataRole.DisplayRole, p["pid"])
            it.setData(0, Qt.ItemDataRole.UserRole, p)
        self.tree.sortItems(0, Qt.SortOrder.AscendingOrder)

    def chosen(self):
        it = self.tree.currentItem()
        if it is None:
            return None, ""
        return it.data(0, Qt.ItemDataRole.UserRole), self.engine.currentData()


# ====================================================================== install
def install(win) -> None:
    win._dbgx_gen = 0
    win.locals.setHeaderLabels(["Name", "Value", "Type"])
    _attach_tree(win, win.locals, 1, 2)

    # ---------------------------------------------------------------- Threads dock
    threads = QTreeWidget()
    threads.setHeaderLabels(["", "ID", "Name"])
    threads.setRootIsDecorated(False)
    threads.setColumnWidth(0, 24)
    threads.setColumnWidth(1, 70)
    dock = QDockWidget("Threads", win)
    dock.setObjectName("Threads")
    dock.setWidget(threads)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    win.tabifyDockWidget(win.dock_stack, dock)
    dock.hide()
    win.dock_threads = dock
    win.threads_tree = threads

    def show_threads(current):
        s = win.session
        if s is None or not hasattr(s, "threads") or not s.paused:
            return
        gen = _gen(win)

        def got(items):
            if gen != _gen(win):
                return
            threads.clear()
            for tid, name in items:
                it = QTreeWidgetItem(threads, ["→" if tid == current else "", str(tid), name])
                it.setData(0, Qt.ItemDataRole.UserRole, tid)
                if tid == current:
                    f = QFont(it.font(2))
                    f.setBold(True)
                    for c in range(3):
                        it.setFont(c, f)
        s.threads(got)

    def thread_dclick(item):
        s = win.session
        tid = item.data(0, Qt.ItemDataRole.UserRole)
        if s is not None and s.paused and hasattr(s, "select_thread") and tid:
            s.select_thread(tid)
    threads.itemDoubleClicked.connect(thread_dclick)

    # ---------------------------------------------------------------- stop / resume hooks
    orig_stopped = win._on_stopped

    def on_stopped(info):
        win._dbgx_gen = _gen(win) + 1
        orig_stopped(info)
        refs = getattr(info, "refs", {}) or {}
        for i in range(win.locals.topLevelItemCount()):
            it = win.locals.topLevelItem(i)
            _set_expandable(it, refs.get(it.text(0)))
            it.setToolTip(1, it.text(1)[:2000])
        QTimer.singleShot(0, refresh_watch)           # after debugtools' evaluate-based refresh
        show_threads(getattr(info, "thread_id", 0))
    win._on_stopped = on_stopped

    orig_resumed = win._on_resumed

    def on_resumed():
        win._dbgx_gen = _gen(win) + 1
        orig_resumed()
    win._on_resumed = on_resumed

    def refresh_watch():
        tree = getattr(win, "watch_tree", None)
        s = win.session
        if tree is None or s is None or not s.paused or not hasattr(s, "watch"):
            return
        gen = _gen(win)
        for i in range(tree.topLevelItemCount()):
            it = tree.topLevelItem(i)

            def got(value, typ, ref, it=it):
                if gen != _gen(win) or value is None:  # None: the agent has no 'w' (debugtools' value stays)
                    return
                try:
                    it.setText(1, str(value))
                    it.setText(2, str(typ))
                    it.setToolTip(1, str(value)[:2000])
                    _set_expandable(it, ref)
                except RuntimeError:
                    pass
            s.watch(it.text(0), got)
    win.refresh_watch = refresh_watch

    # ---------------------------------------------------------------- after every feature is installed
    def late():
        tree = getattr(win, "watch_tree", None)
        if tree is not None:
            tree.setHeaderLabels(["Expression", "Value", "Type"])
            _attach_tree(win, tree, 1, 2)
            tree.model().rowsInserted.connect(            # a new watch: evaluate it now (with its children)
                lambda parent, *_a: None if parent.isValid() else QTimer.singleShot(50, refresh_watch))
        _build_menu(win, dock)
    QTimer.singleShot(0, late)


# ====================================================================== menu actions
def _debug_menu(win):
    return next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Debug"), None)


def _current_file_line(win):
    cv = win._current_code()
    if cv is None:
        return None
    ed = cv.editor
    line = ed.getCursorPosition()[0]
    name = next((n for n, v in win.codeviews.items() if v is cv), None)
    if name is not None:
        return win.plugin_for_form(name).code_file(name), line, ed
    mod = next((m for m, v in win.modviews.items() if v is cv), None)
    return (mod, line, ed) if mod else None


def breakpoint_settings(win, f=None, line=None, ed=None) -> bool:
    """Debug > Breakpoint Settings... for the caret line (or file/line given)."""
    if f is None:
        cur = _current_file_line(win)
        if cur is None:
            win.statusBar().showMessage("Open a code file and put the caret on a line first", 5000)
            return False
        f, line, ed = cur
    if not hasattr(win, "bp_conditions"):
        win.bp_conditions = {}
    dlg = BreakpointDialog(win, line + 1, win.bp_conditions.get((f, line), ""))
    if not dlg.exec():
        return False
    apply_breakpoint_settings(win, f, line, dlg.value(), ed)
    return True


def apply_breakpoint_settings(win, f, line, text, ed=None):
    if not hasattr(win, "bp_conditions"):
        win.bp_conditions = {}
    if text:
        win.bp_conditions[(f, line)] = text
    else:
        win.bp_conditions.pop((f, line), None)
    if ed is not None and line not in ed.breakpoints():
        ed.toggle_breakpoint(line)               # also tells the running session (app._on_bp_toggled)
    else:
        win.breakpoints.setdefault(f, set()).add(line)
        if win.session is not None:
            win.session.set_breakpoint(f, line + 1, True, text)
    win.statusBar().showMessage(f"Breakpoint at line {line + 1}: {dx.describe_bp(text)}", 6000)


def attach_to_process(win, proc=None, engine=""):
    """Debug > Attach to Process...  (proc / engine given = no dialog, used by tests)."""
    if win.session is not None and win.session.running():
        QMessageBox.information(win, "Attach to Process", "Stop the program being debugged first.")
        return None
    if proc is None:
        dlg = AttachDialog(win)
        if not dlg.exec():
            return None
        proc, engine = dlg.chosen()
        if proc is None:
            return None
    proc = dict(proc)
    proc.setdefault("path", dx.process_path(proc["pid"]))
    engine = engine or dx.attach_engine_for(proc)
    why = dx.attach_missing(engine)
    if why:
        QMessageBox.warning(win, "Attach to Process", why)
        return None
    cwd = Path(win.project.folder) if win.project is not None else Path(proc["path"] or ".").parent
    bps = win._all_breakpoints() if win.project is not None else []
    s = dx.make_attach_session(engine, proc["pid"], proc["path"], cwd, bps, win)
    s.break_on_exception = False
    win.locals.clear()
    win.callstack.clear()
    win.dock_output.show()
    win.log(f"------ Attach: {proc['name']} (PID {proc['pid']}) with {dx.ATTACH_ENGINES.get(engine, engine)} ------")
    s.output.connect(win._append_output)
    s.stopped.connect(lambda info: win._on_stopped(info))
    s.resumed.connect(lambda: win._on_resumed())
    from ..tools import on_eval_result
    s.evalResult.connect(lambda txt: on_eval_result(win, txt) or win.immediate.show_result(txt))
    s.finished.connect(lambda code: win._on_finished(code))
    s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
    win.session = s
    s.start()
    win.statusBar().showMessage(f"Attached to PID {proc['pid']} - Stop detaches", 8000)
    win._update_actions()
    return s


def break_all(win):
    """Debug > Break All: pause the program where it is (DAP 'pause')."""
    s = win.session
    dap = getattr(s, "dap", None) or s
    if dap is not None and hasattr(dap, "_request") and not getattr(dap, "paused", False):
        dap._request("pause", {"threadId": getattr(dap, "thread_id", 1) or 1})


def install_delve(win):
    from ..debug_extras import LOCAL, dlv_install_env, find_dlv, install_dlv_command
    if find_dlv():
        QMessageBox.information(win, "Install Delve", f"Delve is already installed:\n{find_dlv()}")
        return
    argv = install_dlv_command()
    if not argv:
        QMessageBox.warning(win, "Install Delve", "Go was not found (needed to build Delve). Install Go into "
                            "%LOCALAPPDATA%\\RADIDE\\toolchains\\go or add it to PATH.")
        return
    (LOCAL / "tools" / "dlv").mkdir(parents=True, exist_ok=True)
    p = QProcess(win)
    env = QProcessEnvironment()
    for k, v in dlv_install_env().items():
        env.insert(k, v)
    p.setProcessEnvironment(env)
    p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    p.readyReadStandardOutput.connect(lambda: win._append_output(bytes(p.readAllStandardOutput()).decode("utf-8", "replace")))
    p.finished.connect(lambda code, _s: win.log("Delve installed: " + find_dlv() if find_dlv()
                                                else f"*** Installing Delve failed (exit code {code})"))
    win.dock_output.show()
    win.log("------ Installing Delve: " + " ".join(argv) + " ------")
    p.start(argv[0], argv[1:])


def _build_menu(win, threads_dock):
    menu = _debug_menu(win)
    if menu is None:
        return
    menu.addSeparator()
    a = menu.addAction("Breakpoint &Settings (Condition, Hit Count, Log)...", lambda: breakpoint_settings(win))
    a.setToolTip("Condition, hit count and logpoint (print a message instead of stopping)")
    a = menu.addAction("&Attach to Process...", lambda: attach_to_process(win))
    a.setShortcut("Ctrl+Alt+P")
    win.a_attach_process = a
    a = menu.addAction("Brea&k All", lambda: break_all(win))
    a.setShortcut("Ctrl+Alt+Break")
    menu.addAction("Install &Delve (Go Debugger)", lambda: install_delve(win))
    windows = menu.addMenu("&Windows")
    for d in (getattr(win, "dock_locals", None), getattr(win, "dock_watch", None), getattr(win, "dock_stack", None),
              threads_dock, getattr(win, "dock_immediate", None)):
        if d is not None:
            act: QAction = d.toggleViewAction()
            windows.addAction(act)
    threads_dock.toggleViewAction().setShortcut("Ctrl+Alt+H")


__all__ = ["install", "breakpoint_settings", "apply_breakpoint_settings", "attach_to_process", "AttachDialog",
           "BreakpointDialog"]
