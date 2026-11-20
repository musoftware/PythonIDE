"""Scene1 - Particles Showcase: emitter objects (torches: fire + smoke, snow over the whole sky, a star
fountain with a texture) made in the Particle Editor, plus particles from code: the orb leaves a trail
(Emit following an object), a click makes an explosion (Burst), coins sparkle when collected."""
from radgame import *  # noqa: F401,F403 - the game helpers
from Scene1_designer import *  # noqa: F401,F403 - the objects of the scene

torches_on = True


def Scene_Load():
    game.score = 0
    Emit("trail", Player)                 # follows the orb until the scene ends


def Scene_KeyDown(key):
    global torches_on
    if key == "f":
        Fountain.emitting = not Fountain.emitting
    elif key == "t":
        torches_on = not torches_on
        for e in (Flame1, Flame2, Smoke1):
            e.emitting = torches_on
    elif key == "escape":
        Quit()


def Scene_MouseDown(x, y, button):
    Burst("explosion", x, y)


def Player_Collide(other):
    if other.group == "Coin":
        Burst("coin", other)
        Destroy(other)
        AddScore(1)
        if game.score == 5:
            ShowMessage("All coins!", 2)
            Burst("explosion", Player, 120)
