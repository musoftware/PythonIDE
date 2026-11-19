"""Attach ready-made Language Servers (radide/lsp.py) to Monaco editors.

Every Monaco editor whose language has an installed server gets completion,
hover, signature help, go to definition and live diagnostics from it. Editors
without a server keep using the language plugin's own IntelliSense."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer


def install(win) -> None:
    from ..lsp import LspManager
    win.lsp_manager = LspManager(win)
    win._lsp_editors = {}            # resolved path -> editor

    def attach(ed):
        if not hasattr(ed, "_js") or win.project is None or getattr(ed, "lsp", None) is not None:
            return
        lang = ed.language_id()
        client = win.lsp_manager.client_for(lang, win.project.folder)
        if client is None:
            return
        ed.lsp = client
        key = str(Path(ed.path).resolve()).lower()
        win._lsp_editors[key] = ed
        if not getattr(client, "_rad_connected", False):
            client._rad_connected = True
            client.diagnostics.connect(lambda path, diags: show_diags(path, diags))
            client.log.connect(lambda _t: None)
        client.did_open(ed.path, ed.text(), lang)
        ed.definitionRequested.connect(lambda line, col, e=ed: definition(e, line, col))
        win.statusBar().showMessage(f"Language server: {Path(client.argv[0]).name} ({lang})", 4000)

    def show_diags(path, diags):
        ed = win._lsp_editors.get(str(Path(path).resolve()).lower())
        if ed is not None:
            ed.set_diagnostics(diags)

    def definition(ed, line, col):
        if ed.lsp is None:
            from ..tools import goto_definition
            goto_definition(win)
            return

        def done(res):
            if not res:
                from ..tools import goto_definition
                goto_definition(win)
                return
            path, target_line = res
            p = Path(path)
            if win.project and p.parent.resolve() == win.project.folder.resolve():
                target = win._editor_for_file(p.name)
                if target is not None:
                    target.goto_line(target_line)
                    return
            win.statusBar().showMessage(f"Defined in {p} line {target_line + 1}", 6000)
        ed.lsp.definition(ed.path, line, col, done)

    # wrap the IDE's editor factories so new editors get a server
    orig_codeview = win._codeview

    def codeview(name):
        cv = orig_codeview(name)
        QTimer.singleShot(0, lambda: attach(cv.editor))
        return cv
    win._codeview = codeview

    orig_open_module = win.open_module

    def open_module(filename):
        orig_open_module(filename)
        mv = win.modviews.get(filename)
        if mv is not None:
            QTimer.singleShot(0, lambda: attach(mv.editor))
    win.open_module = open_module

    orig_reset = win._reset

    def reset():
        win.lsp_manager.stop_all()
        win._lsp_editors.clear()
        orig_reset()
    win._reset = reset

    orig_close = win.closeEvent

    def close_event(e):
        orig_close(e)
        if e.isAccepted():
            win.lsp_manager.stop_all()
    win.closeEvent = close_event
