"""More game runtimes in the IDE (CONTRACTS 10.2): F5 debugging of Godot projects through Godot's debug adapter.

(HTML5 Canvas games run as website projects - DevServer + Preview - and Ring / Arcade games through the normal
Run / Debug path; their plugins are radide/languages/html5_game.py, ring_game.py, arcade_game.py.)

Debug > Start (F5) of a Godot project starts a headless Godot editor and debugs the game through its DAP server
(radide/games/godot_dap.py); Ctrl+F5 and the scene designer's Play keep running ``godot --path`` directly.
Tools > Options: QSettings "games/godot_dap" = false turns the debug adapter off (F5 then just runs the game).
"""
from __future__ import annotations


def _is_godot(win) -> bool:
    p = getattr(win, "project", None)
    return p is not None and getattr(p, "language", "") == "godot"


def install(win) -> None:
    def run_godot(debug: bool) -> bool:
        """F5 in a Godot project: Godot's debug adapter (True); otherwise the window runs it (False)."""
        if debug and _is_godot(win) and not (win.session is not None and win.session.running()) and \
                str(win.settings.value("games/godot_dap", True)).lower() not in ("false", "0"):
            try:
                plugin = win.run_plugin()
                godot = plugin.find_interpreter(win._configured_interpreter(plugin))
            except Exception:  # noqa: BLE001
                godot = ""
            if godot:
                win.save_all()
                try:
                    from ..games.godot_dap import start_debugging
                    start_debugging(win, godot)
                    return True
                except Exception as e:  # noqa: BLE001 - fall back to a plain run
                    win.log(f"*** Godot debug adapter: {e} - running without the debugger")
        return False

    win.extension_points.add_run_handler(run_godot, "godot")       # radide/extension_points.py
