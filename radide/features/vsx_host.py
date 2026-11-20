"""VS Code extensions with code: the Node extension host (radide/vsx/host) wired into the IDE.

See radide/vsx/host_ide.py (editors, UI, language features, commands, debuggers) and radide/vsx/bridge.py
(the JSON-RPC protocol). The host starts shortly after the window when enabled extensions have a "main"
entry; "Reload" in the Extensions view restarts it."""
from __future__ import annotations


def install(win) -> None:
    from ..vsx import host_ide
    host_ide.install(win)
