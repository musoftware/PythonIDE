# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Crystal Maze 3D - a 3D maze made with Ursina (https://www.ursinaengine.org, MIT licence) in RAD IDE.

Shows: a 3D scene (Maze.scene3d) built in the IDE's 3D scene view - walls are "solid" cubes, crystals are
"collectible" + "spin" spheres, the player is a capsule with the "player" behaviour (WASD / arrows move,
Space jumps) - plus game code with the VB-style handlers rad3d.py calls: Scene_Load, Scene_Update(dt),
Player_Collect(item); an on-screen HUD (ursina Text) and a win condition (all crystals + reach the red pad).
"""
from ursina import Text, color

import rad3d

app = rad3d.start('Crystal Maze 3D')
scene = rad3d.load_scene('Maze')
TOTAL = sum(1 for n in scene if n.startswith("Crystal"))
state = {"time": 0.0, "won": False}
hud = Text(text="", position=(-0.85, 0.47), scale=1.4, color=color.white)


def Scene_Load():
    print(f"Collect the {TOTAL} crystals, then step on the red pad!", flush=True)


def Scene_Update(dt):
    if state["won"]:
        return
    state["time"] += dt
    hud.text = f"Crystals {rad3d.score}/{TOTAL}    Time {state['time']:5.1f} s"
    pad, player = scene["ExitPad"], rad3d.player
    if rad3d.score == TOTAL and player is not None and \
            abs(player.x - pad.x) < 0.9 and abs(player.z - pad.z) < 0.9:
        state["won"] = True
        hud.text = f"You escaped in {state['time']:.1f} s!"
        print(f"WIN time={state['time']:.1f}", flush=True)


def Player_Collect(item):
    print(f"CRYSTAL {item.name} score={rad3d.score}/{TOTAL}", flush=True)


rad3d.run(globals())
