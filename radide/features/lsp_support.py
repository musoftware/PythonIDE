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
        if not hasattr(ed, "_js") or getattr(ed, "lsp", None) is not None:
            return
        if not getattr(ed, "_rad_lang_hook", False) and hasattr(ed, "languageChanged"):
            ed._rad_lang_hook = True           # "Open as PHP" / Language Mode: attach the new language's server
            ed.languageChanged.connect(lambda _lang, e=ed: QTimer.singleShot(0, lambda: attach(e)))
        if win.project is not None:
            root = Path(win.project.folder)
        elif Path(ed.path).is_absolute():
            root = Path(ed.path).parent        # a loose file without a project
        else:
            return
        lang = ed.language_id()
        client = win.lsp_manager.client_for(lang, root)
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
        if not getattr(ed, "_rad_def_hook", False):
            ed._rad_def_hook = True
            ed.definitionRequested.connect(lambda line, col, e=ed: definition(e, line, col))
        from ..lsp import display_name
        win.statusBar().showMessage(f"Language server: {display_name(client.argv)} ({lang})", 4000)

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
            if callable(getattr(win, "open_file", None)) and p.is_file():
                try:
                    if win.open_file(p, target_line + 1) is not None:
                        return
                except Exception:  # noqa: BLE001
                    pass
            win.statusBar().showMessage(f"Defined in {p} line {target_line + 1}", 6000)
        ed.lsp.definition(ed.path, line, col, done)

    # every Monaco editor of this window (also files opened by win.open_file) gets a server when ready
    try:
        from ..monaco_editor import MonacoEditor
        MonacoEditor.ready_hooks.append(lambda ed: attach(ed) if ed.window() is win else None)
    except ImportError:                      # QtWebEngine missing: the built-in editor has no LSP
        pass

    # the IDE's code / module editors get a server (attach again when one was not available before)
    win.extension_points.on("code_view_requested", lambda _n, cv: QTimer.singleShot(0, lambda: attach(cv.editor)),
                            "language servers")
    win.extension_points.on("module_view_shown", lambda _f, mv: QTimer.singleShot(0, lambda: attach(mv.editor)),
                            "language servers")

    def stop_servers() -> None:
        win.lsp_manager.stop_all()
        win._lsp_editors.clear()
    win.extension_points.on("projects_reset", stop_servers, "language servers")

    win.extension_points.add_shutdown_step(lambda: win.lsp_manager.stop_all(), "language servers")
