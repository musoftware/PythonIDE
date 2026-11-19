"""Debugger extras: Watch window, conditional breakpoints, Run to Cursor,
Break on Exceptions. Works with both the built-in agents (radide.debugger.Session)
and Debug Adapter Protocol sessions (radide.dap.DapSession)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QDockWidget, QHBoxLayout, QInputDialog, QLineEdit, QPushButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)


def install(win) -> None:
    win.bp_conditions = {}           # (code file, 0-based line) -> condition
    win._watch_pending = []          # watch items waiting for an eval result
    win._run_to = None               # (file, 1-based line) temporary breakpoint

    # ---------------------------------------------------------------- Watch dock
    box = QWidget()
    tree = QTreeWidget()
    tree.setHeaderLabels(["Expression", "Value"])
    tree.setColumnWidth(0, 200)
    tree.setRootIsDecorated(False)
    entry = QLineEdit(placeholderText="Add a watch expression and press Enter")
    remove = QPushButton("Remove")
    row = QHBoxLayout()
    row.addWidget(entry, 1)
    row.addWidget(remove)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(tree, 1)
    lay.addLayout(row)
    dock = QDockWidget("Watch", win)
    dock.setObjectName("Watch")
    dock.setWidget(box)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    win.tabifyDockWidget(win.dock_locals, dock)
    win.dock_watch = dock
    win.watch_tree = tree

    def add_watch():
        expr = entry.text().strip()
        if expr:
            QTreeWidgetItem(tree, [expr, ""])
            entry.clear()
            refresh()
    entry.returnPressed.connect(add_watch)
    remove.clicked.connect(lambda: [tree.takeTopLevelItem(tree.indexOfTopLevelItem(i)) for i in tree.selectedItems()])

    def refresh():
        s = win.session
        if s is None or not s.paused:
            return
        for i in range(tree.topLevelItemCount()):
            it = tree.topLevelItem(i)
            win._watch_pending.append(it)
            s.evaluate(it.text(0))

    # route eval results: watches first, then hover tips / Immediate (radide/tools.py)
    from .. import tools
    if not getattr(tools, "_watch_wrapped", False):
        original = tools.on_eval_result

        def on_eval_result(w, text):
            pending = getattr(w, "_watch_pending", None)
            if pending:
                item = pending.pop(0)
                try:
                    item.setText(1, text)
                except RuntimeError:       # item removed meanwhile
                    pass
                return True
            return original(w, text)
        tools.on_eval_result = on_eval_result
        tools._watch_wrapped = True

    # ---------------------------------------------------------------- stop hook
    orig_stopped = win._on_stopped

    def on_stopped(info):
        orig_stopped(info)
        if win._run_to is not None and win.session is not None:       # remove the temporary breakpoint
            f, line = win._run_to
            win._run_to = None
            if (line - 1) not in win.breakpoints.get(f, set()):
                win.session.set_breakpoint(f, line, False)
        refresh()
    win._on_stopped = on_stopped

    # ---------------------------------------------------------------- actions
    debug_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Debug")

    def current_file_line():
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

    def edit_condition():
        cur = current_file_line()
        if cur is None:
            return
        f, line, ed = cur
        old = win.bp_conditions.get((f, line), "")
        cond, ok = QInputDialog.getText(win, "Breakpoint Condition",
                                        f"Stop at line {line + 1} only when this expression is true\n"
                                        "(empty = always stop):", text=old)
        if not ok:
            return
        if line not in ed.breakpoints():
            ed.toggle_breakpoint(line)
            line = ed.getCursorPosition()[0] if line not in ed.breakpoints() else line
        if cond.strip():
            win.bp_conditions[(f, line)] = cond.strip()
        else:
            win.bp_conditions.pop((f, line), None)
        if win.session is not None:
            win.session.set_breakpoint(f, line + 1, True, cond.strip())
        win.statusBar().showMessage(f"Breakpoint at line {line + 1}: "
                                    f"{'when ' + cond.strip() if cond.strip() else 'always'}", 5000)

    def run_to_cursor():
        cur = current_file_line()
        if cur is None:
            return
        f, line, _ed = cur
        s = win.session
        if s is None or not s.running():
            win._run_to = (f, line + 1)
            original = win._all_breakpoints

            def with_temp():
                bps = original()
                return bps + [(f, line + 1, "")]
            win._all_breakpoints = with_temp
            try:
                win.run_project(debug=True)
            finally:
                win._all_breakpoints = original
            return
        win._run_to = (f, line + 1)
        s.set_breakpoint(f, line + 1, True)
        if s.paused:
            s.cont()

    exc = QAction("Break on &Exceptions", win, checkable=True)
    exc.setChecked(win.settings.value("debug/break_on_exception", True) in (True, "true"))

    def toggle_exc(on):
        win.settings.setValue("debug/break_on_exception", on)
        s = win.session
        if s is not None and hasattr(s, "set_break_on_exception"):
            s.set_break_on_exception(on)
    exc.toggled.connect(toggle_exc)

    debug_menu.addSeparator()
    a = debug_menu.addAction("Breakpoint &Condition...", edit_condition)
    a.setShortcut(QKeySequence("Alt+F9"))
    a = debug_menu.addAction("Run to &Cursor", run_to_cursor)
    a.setShortcut(QKeySequence("Ctrl+F10"))
    debug_menu.addAction(exc)
    debug_menu.addAction(dock.toggleViewAction())
    win.a_break_on_exception = exc
