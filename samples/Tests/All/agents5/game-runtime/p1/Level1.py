"""Level1 - your game code. Double-click an object in the scene designer to add its event handler.

Every object of the scene is a name here (Player.x, Coin1.visible, Score.text). Useful helpers:
game.score, game.lives, game.vars, GoToScene(name), RestartScene(), PlaySound(id), ShowMessage(text),
AddScore(n), IsKeyDown("left"), Find(name), FindGroup("Coin"), Clone(obj, x, y), AddTimer(name, ms)."""
from radgame import *  # noqa: F401,F403 - the game helpers
from Level1_designer import *  # noqa: F401,F403 - the objects of the scene


# the scene: the scene starts
def Scene_Load():
    game.vars["start_score"] = game.score       # score when the level started
    ShowMessage("Collect the coins and reach the flag!", 2)


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
def Scene_KeyDown(key):
    if key == "escape":
        Quit()
    elif key == "r":
        RestartScene()


# Player: jumps (platformer)
def Player_Jump():
    PlaySound("jump")


# Player: touches another object (other)
def Player_Collide(other):
    if other.group == "Enemy":
        if Player.vy > 0 and Player.bottom - other.y < 14:   # landed on its head: stomp
            other.destroy()
            Player.vy = -320
            AddScore(5)
        else:
            LoseLife()
    elif other.name == "Goal":
        ShowMessage(f"You win! Score: {game.score}", 3)
        Player.behaviours.clear()                     # stop the player
        AddTimer("WinTimer", 3000)


# Player: fell below the level
def Player_OutOfWorld():
    LoseLife()


# WinTimer: the timer interval elapsed
def WinTimer_Tick():
    game.score = 0
    game.lives = 3
    RestartScene()


def LoseLife():
    """Back to the start of the level with one life less (and the score it started with)."""
    game.lives -= 1
    game.score = game.vars.get("start_score", 0)
    if game.lives <= 0:
        ShowMessage("Game over", 2)
        game.lives = 3
        game.score = 0
    RestartScene()
