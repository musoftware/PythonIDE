"""Scene1 - your game code. Double-click an object in the scene designer to add its event handler.

Every object of the scene is a name here (Player.x, Coin1.visible, ScoreText.text). Useful helpers:
game.score, game.lives, game.vars, GoToScene(name), RestartScene(), PlaySound(id), ShowMessage(text),
AddScore(n), IsKeyDown("left"), Find(name), FindGroup("Coin"), Clone(obj, x, y), AddTimer(name, ms)."""
from radgame import *  # noqa: F401,F403 - the game helpers
from Scene1_designer import *  # noqa: F401,F403 - the objects of the scene


# the scene: the scene starts
def Scene_Load():
    pass


# the scene: every frame (dt = seconds since the last frame)
def Scene_Update(dt):
    pass


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
def Scene_KeyDown(key):
    pass
