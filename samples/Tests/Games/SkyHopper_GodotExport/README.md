# SkyHopper_GodotExport

**pygame -> Godot export with translated code** - `samples/SkyHopper` exported with Game > Export to Godot
(round 6). `Scene1.gd` was **translated from `Scene1.py` by rules** (radide/games/gd_translate.py, 74
statements, nothing left as TODO): constants / variables, `if / elif / for`, `global`, the scene objects
(`Player.y = ...` -> `setp(Player, "y", ...)`), `game.score` / `game.vars` / `game.time`, `Spawn`,
`Destroy`, `AddScore`, `SaveData` / `LoadData`, `PlaySound`, `EnableBehaviour`, `obj.enable()`,
`obj.behaviour()`, timers, `Random`, `math.sin`. Untranslatable lines would be kept as `# TODO` comments
(or translated by the AI provider when one is configured in Tools > Options > AI).

**Try it:** open the folder in Godot 4 (or `godot --path .` after `godot --headless --path . --import`):
title screen, Space / click to hop, gates spawn and speed up every 5 points, game over, best score kept,
Space to restart - the same game as the pygame version.

Automatic check (Godot headless + a scripted player, tests/autopilot.gd):
`python tests/run_autopilot.py 7` prints the score at each gate, the game over line and the restart.
The same autopilot for the pygame original: `python tests/py_autopilot.py ../../../SkyHopper`
(both reach each score within one frame of each other).
