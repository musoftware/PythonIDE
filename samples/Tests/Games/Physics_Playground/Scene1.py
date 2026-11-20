"""Scene1 - Physics Playground (pymunk): crates, a bouncing ball, a seesaw (pivot joint), a pendulum
(pin joint), a static wedge with an outline shape and a kinematic lift moved by code.

Click drops a crate (Spawn of the template CrateTemplate - it has a dynamic body), Space kicks the ball
with ApplyImpulse, R restarts. The bodies are set in the scene inspector (Physics body section)."""
import math

from radgame import *  # noqa: F401,F403 - the game helpers
from Scene1_designer import *  # noqa: F401,F403 - the objects of the scene


def Scene_Load():
    game.vars["crates"] = 4


def Scene_Update(dt):
    Lift.y = 380 + 90 * math.sin(game.time * 1.5)        # a kinematic body follows its object


def Scene_KeyDown(key):
    if key == "space":
        ApplyImpulse(Ball, 120, -520)
    elif key == "r":
        RestartScene()
    elif key == "escape":
        Quit()


def Scene_MouseDown(x, y, button):
    crate = Spawn("CrateTemplate", x - 20, y - 20)
    crate.rotation = Random(-30, 30)
    Burst("dust", x, y)
    game.vars["crates"] = game.vars["crates"] + 1

