"""Web IntelliSense commands (CONTRACTS 8.6).

* Edit > Language Mode... / Open as PHP - choose the language of the current file
  (remembered per file; the matching language server is attached).
* Edit > Emmet: Expand Abbreviation (Tab in HTML/PHP/CSS files, Ctrl+Shift+Enter anywhere).
* Tools > Install Web Language Servers - npm install vscode-langservers-extracted, intelephense,
  typescript and typescript-language-server into %LOCALAPPDATA%\\RADIDE\\lsp.
"""
from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QInputDialog


def _menu(win, title: str):
    for a in win.menuBar().actions():
        m = a.menu()
        if m is not None and a.text().replace("&", "").lower() == title.lower():
            return m
    return None


def current_monaco(win):
    """The Monaco editor of the active tab (None for designers / the built-in editor)."""
    cv = win._current_code() if hasattr(win, "_current_code") else None
    ed = getattr(cv, "editor", None)
    if ed is None:
        ed = getattr(win.tabs.currentWidget(), "editor", None) if hasattr(win, "tabs") else None
    return ed if ed is not None and hasattr(ed, "set_language") else None


def choose_language(win, ed=None) -> str | None:
    from ..monaco_editor import LANGUAGE_CHOICES
    ed = ed or current_monaco(win)
    if ed is None:
        win.statusBar().showMessage("Language Mode: open a code file first (Monaco editor)", 4000)
        return None
    titles = ["Auto Detect (by extension)"] + [t for t, _ in LANGUAGE_CHOICES]
    cur = ed.language_id()
    idx = next((i + 1 for i, (_t, lid) in enumerate(LANGUAGE_CHOICES) if lid == cur), 0)
    title, ok = QInputDialog.getItem(win, "Language Mode", f"Language for {ed.path.name}:", titles, idx, False)
    if not ok:
        return None
    lang = dict(LANGUAGE_CHOICES).get(title)
    ed.set_language(lang)
    win.statusBar().showMessage(f"{ed.path.name}: {title}", 4000)
    return lang


class _Installer(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(bool)


def install_servers(win):
    from .. import lsp
    if getattr(win, "_web_lsp_installing", False):
        return
    win._web_lsp_installing = True
    sig = _Installer(win)
    sig.line.connect(win.log)

    def finished(ok):
        win._web_lsp_installing = False
        mgr = getattr(win, "lsp_manager", None)
        if mgr is not None:              # forget "no server" results so open editors can attach now
            mgr.clients = {k: v for k, v in mgr.clients.items() if v is not None}
        state = lsp.web_servers_installed()
        win.log("Web language servers: " + ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in state.items()))
        win.statusBar().showMessage("Web language servers installed" if ok else "Installing web language servers failed",
                                    6000)
    sig.done.connect(finished)
    if hasattr(win, "dock_output"):
        win.dock_output.show()
        win.dock_output.raise_()
    win.log(f"Installing web language servers into {lsp.LSP_HOME} ...")
    from .. import progress
    task = progress.track("Installing web language servers", win)     # status-bar progress

    def line(text):
        task.reporter.log(str(text))
        sig.line.emit(text)

    def work():
        ok = False
        try:
            ok = lsp.install_web_servers(line)
        finally:
            task.complete(ok)
        sig.done.emit(ok)
    threading.Thread(target=work, daemon=True).start()


def install(win) -> None:
    edit = _menu(win, "Edit")
    tools = _menu(win, "Tools")

    lang = QAction("Language &Mode...", win)
    lang.setStatusTip("Choose the language of the current file (HTML, PHP, CSS, JavaScript, ...)")
    lang.triggered.connect(lambda: choose_language(win))
    as_php = QAction("Open as &PHP", win)
    as_php.triggered.connect(lambda: (current_monaco(win) or _none(win)) and current_monaco(win).set_language("php"))
    emmet = QAction("Emmet: E&xpand Abbreviation", win)
    emmet.triggered.connect(lambda: (current_monaco(win) or _none(win)) and current_monaco(win).emmet_expand())
    if edit is not None:
        edit.addSeparator()
        for a in (lang, as_php, emmet):
            edit.addAction(a)
    win.action_language_mode = lang

    inst = QAction("Install &Web Language Servers (HTML/CSS/JSON/PHP/JS/TS)", win)
    inst.triggered.connect(lambda: install_servers(win))
    if tools is not None:
        tools.addSeparator()
        tools.addAction(inst)


def _none(win):
    win.statusBar().showMessage("Open a code file first (Monaco editor)", 4000)
    return None
