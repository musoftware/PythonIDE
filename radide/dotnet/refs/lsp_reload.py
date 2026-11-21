"""Make the C# / VB language server see reference changes.

After a project file changes, every running server of the window is told (workspace/didChangeWatchedFiles);
C# servers whose workspace contains the project are then restarted so they reload the project with its new
references (csharp-ls loads the solution once at start), and the open editors are attached again.
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QTimer

CS_KEYS = ("csharp", "c#", "cs", "vb", "fsharp")


def _under(path: Path, root: str) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except (ValueError, OSError):
        return False


def _path_uri(p) -> str:
    try:
        from ...lsp import path_uri
        return path_uri(Path(p))
    except Exception:  # noqa: BLE001
        return Path(p).resolve().as_uri()


def project_file_changed(win, project_file, restart: bool = True) -> list[str]:
    """Returns the roots of the servers that were notified (and restarted)."""
    mgr = getattr(win, "lsp_manager", None)
    if mgr is None:
        return []
    pf = Path(project_file)
    touched = []
    for key, client in list(mgr.clients.items()):
        lang, root = key
        if client is None or str(lang).lower() not in CS_KEYS:
            continue
        if not (_under(pf, root) or _under(Path(root), str(pf.parent))):
            continue
        touched.append(root)
        try:
            client._notify("workspace/didChangeWatchedFiles",
                           {"changes": [{"uri": _path_uri(pf), "type": 2}]})
        except Exception:  # noqa: BLE001
            pass
        if restart:
            QTimer.singleShot(250, lambda k=key: _restart(win, k))
    return touched


def _restart(win, key) -> None:
    mgr = getattr(win, "lsp_manager", None)
    if mgr is None:
        return
    client = mgr.clients.pop(key, None)
    if client is None:
        return
    editors = [ed for ed in list(getattr(win, "_lsp_editors", {}).values()) if getattr(ed, "lsp", None) is client]
    try:
        client.stop()
    except Exception:  # noqa: BLE001
        pass
    for ed in editors:
        ed.lsp = None
    try:
        from ...monaco_editor import MonacoEditor
        hooks = list(MonacoEditor.ready_hooks)
    except Exception:  # noqa: BLE001
        hooks = []
    for ed in editors:                       # lsp_support's ready hook attaches a fresh server
        for h in hooks:
            try:
                h(ed)
            except Exception:  # noqa: BLE001
                pass
    try:
        win.statusBar().showMessage(f"Language server reloaded for {os.path.basename(key[1])}", 4000)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["project_file_changed"]
