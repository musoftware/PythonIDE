"""Tools > Language Servers...: status and one-click install of the language servers and debug engines
that live in the IDE's private tools folder (radide/lsp_servers.py, radide/debug_more.py)."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)


class _Relay(QObject):
    log = pyqtSignal(str)
    done = pyqtSignal(str, bool)


def debug_rows() -> list[tuple[str, str, str]]:
    """(language, engine, status) of the GUI Bridge debug engines added in round 7 (+ Go/Delve)."""
    from ..bridgedebug import missing
    from ..languages import get_plugin
    rows = []
    for pid, label, eng, name in (("go-bridge", "Go", "dlv", "Delve (dlv dap)"),
                                  ("ruby-bridge", "Ruby", "rdbg", "debug gem (DAP over TCP)"),
                                  ("lua-bridge", "Lua", "luaagent", "RAD Lua agent (debug.sethook)"),
                                  ("perl-bridge", "Perl", "perlagent", "RAD Perl agent (perl -d:RadDbg)"),
                                  ("powershell-bridge", "PowerShell", "pses", "PowerShell Editor Services")):
        try:
            why = missing(eng, get_plugin(pid))
        except Exception as e:  # noqa: BLE001 - a missing plugin must not break the dialog
            why = str(e)
        rows.append((label, name, "ready" if not why else why))
    return rows


class LanguageServersDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        from .. import theme
        self.setWindowTitle("Language Servers and Debuggers")
        self.resize(860, 640)
        lay = QVBoxLayout(self)
        intro = QLabel("IntelliSense (completion, hover, go to definition, diagnostics) for these languages comes "
                       "from language servers installed in the IDE's own tools folder - no admin rights, no PATH "
                       "changes. Downloads are official releases (sha256 checked).")
        intro.setWordWrap(True)
        theme.role(intro, "muted")
        lay.addWidget(intro)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Language", "Server", "Status", ""])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table)
        h = QLabel("Debuggers for GUI Bridge projects (F5 / F9)")
        theme.role(h, "heading")
        lay.addWidget(h)
        self.dbg = QTableWidget(0, 3)
        self.dbg.setHorizontalHeaderLabels(["Language", "Engine", "Status"])
        self.dbg.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.dbg.verticalHeader().setVisible(False)
        self.dbg.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.dbg.setMinimumHeight(200)
        lay.addWidget(self.dbg)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        self.log.setPlaceholderText("Install output appears here.")
        lay.addWidget(self.log)
        row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        row.addStretch(1)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        row.addWidget(box)
        lay.addLayout(row)
        self.relay = _Relay(self)
        self.relay.log.connect(self.log.appendPlainText)
        self.relay.done.connect(self._done)
        self._busy = False
        self.refresh()

    def refresh(self):
        from .. import lsp_servers
        from ..lsp import display_name
        rows = lsp_servers.status()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["language"].capitalize() if r["language"] != "powershell"
                                                      else "PowerShell"))
            self.table.setItem(i, 1, QTableWidgetItem(r["name"]))
            st = QTableWidgetItem(f"installed - {display_name(r['found'])}" if r["found"] else
                                  (r["installable"] or "not installed - " + r["hint"]))
            st.setToolTip(" ".join(r["found"]) if r["found"] else r["hint"])
            self.table.setItem(i, 2, st)
            btn = QPushButton("Reinstall" if r["found"] else "Install")
            btn.setEnabled(not r["installable"] and not self._busy)
            btn.clicked.connect(lambda _c=False, lang=r["language"]: self.install(lang))
            self.table.setCellWidget(i, 3, btn)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        drows = debug_rows()
        self.dbg.setRowCount(len(drows))
        for i, (lang, eng, st) in enumerate(drows):
            for j, v in enumerate((lang, eng, st)):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.dbg.setItem(i, j, it)
        self.dbg.resizeColumnsToContents()
        self.dbg.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    def install(self, language: str):
        from .. import lsp_servers
        if self._busy:
            return
        self._busy = True
        self.refresh()
        self.log.appendPlainText(f"--- Installing {lsp_servers.NAMES.get(language, language)} ...")
        from .. import progress
        task = progress.track(f"Installing {lsp_servers.NAMES.get(language, language)}", self)

        def log(text):
            task.reporter.log(str(text))
            self.relay.log.emit(text)

        def work():
            try:
                ok = lsp_servers.install(language, log=log)
            except Exception as e:  # noqa: BLE001
                self.relay.log.emit(f"failed: {e}")
                ok = False
            task.complete(ok)
            self.relay.done.emit(language, ok)
        threading.Thread(target=work, daemon=True).start()

    def _done(self, language: str, ok: bool):
        self._busy = False
        self.log.appendPlainText(f"--- {'Installed' if ok else 'Install failed'}: {language}")
        self.refresh()
        win = self.parent()
        if ok and getattr(win, "lsp_manager", None) is not None:
            # forget the "no server" answer cached for this language so open editors pick it up
            for key in [k for k in win.lsp_manager.clients if k[0] == language and win.lsp_manager.clients[k] is None]:
                win.lsp_manager.clients.pop(key, None)


def attach_expo_debugger(win) -> str:
    """Debug the running Expo web page (radide/features/expo.py, ``npx expo start --web``): js-debug opens it in
    Edge / Chrome; breakpoints of the project's .jsx/.js files stop in the IDE (Locals, Call Stack, F10/F11).
    The Expo session keeps running; its debug commands are routed to js-debug. Returns '' or why not."""
    s = win.session
    url = getattr(s, "url", "")
    if s is None or not url or win.project is None:
        return "Start the Expo app first (F5) - its web page must be running."
    from ..debug_more import expo_web_debug_session
    bps = win._all_breakpoints() if callable(getattr(win, "_all_breakpoints", None)) else []
    d = expo_web_debug_session(url, win.project.folder, bps, win)
    if d is None:
        return "js-debug (tools\\js-debug), Node.js and Edge or Chrome are needed."
    old = getattr(s, "_rad_jsdebug", None)
    if old is not None and old.running():
        old.stop()
    s._rad_jsdebug = d
    s.debug = True
    s.paused = False

    def on_stop(info):
        s.paused = True
        win._on_stopped(info)

    def on_resume():
        s.paused = False
        win._on_resumed()
    d.stopped.connect(on_stop)
    d.resumed.connect(on_resume)
    d.output.connect(lambda t: win._append_output(t) if t.strip() else None)
    d.evalResult.connect(lambda t: win.immediate.show_result(t) if hasattr(win, "immediate") else None)
    d.failed.connect(lambda t: win.log(f"*** js-debug: {t}"))
    for name in ("cont", "step_into", "step_over", "step_out", "evaluate", "set_breakpoint", "children", "watch",
                 "threads", "select_thread", "set_break_on_exception"):
        setattr(s, name, getattr(d, name))
    if hasattr(s, "finished"):
        s.finished.connect(lambda *_a: d.stop() if d.running() else None)
    d.start()
    win.log(f"[debugger] js-debug opened {url} - breakpoints in .jsx / .js files stop here")
    return ""


def install(win) -> None:
    def show():
        LanguageServersDialog(win).exec()

    def debug_expo():
        why = attach_expo_debugger(win)
        if why:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(win, "Debug Expo Web Page", why)
    win.debug_expo_web = debug_expo
    debug = next((x.menu() for x in win.menuBar().actions()
                  if x.menu() is not None and x.text().replace("&", "") == "Debug"), None)
    if debug is not None:
        a = debug.addAction("Debug Expo Web Page (js-debug)")
        a.setStatusTip("React Native / Expo: stop at breakpoints of the running web page (Edge / Chrome)")
        a.triggered.connect(debug_expo)
    win.show_language_servers = show
    tools = next((x.menu() for x in win.menuBar().actions()
                  if x.menu() is not None and x.text().replace("&", "") == "Tools"), None)
    if tools is not None:
        a = tools.addAction("Language Servers and Debuggers...")
        a.setStatusTip("Install gopls, ruby-lsp, lua-language-server, PowerShell Editor Services, PLS; "
                       "debugger status for Go / Ruby / Lua / Perl / PowerShell")
        a.triggered.connect(show)
        win.a_language_servers = a
