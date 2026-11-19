"""Scene1 - Sky Hopper: hop Glim the firefly-bot through the crystal gates.

Space / Up / click = hop (the "flap" behaviour of Player does the physics). Every gate you pass scores a
point; the gates come faster and closer together as the score grows. Hitting a crystal or the ground ends
the run; the best score is kept in savegame.json (SaveData / LoadData).

Gates are made at run time from the hidden spawn templates PillarTop, PillarBottom and Gap (props
template=1) with Spawn(); their "scroll" behaviour moves them left and removes them off screen."""
import math

from radgame import *  # noqa: F401,F403 - the game helpers
from Scene1_designer import *  # noqa: F401,F403 - the objects of the scene

GATE_X = 420                 # new gates appear just right of the window
GROUND_Y = 520               # top of the ground strip
START_SPEED, MAX_SPEED = 150.0, 260.0
START_GAP, MIN_GAP = 150, 112
GATE_SPACING = 215           # pixels between two gates
MAX_STEP = 150               # the next gap is at most this much higher / lower (always reachable)

state = "ready"              # ready -> playing -> over
speed = START_SPEED
gap = START_GAP
over_time = 0.0
last_centre = 260


# the scene: the scene starts
def Scene_Load():
    global state, speed, gap, over_time, last_centre
    state, speed, gap, over_time, last_centre = "ready", START_SPEED, START_GAP, 0.0, 260
    game.score = 0
    game.vars["best"] = LoadData("best", 0)
    Player.enable("flap", False)              # hovers on the start screen
    for t in (ScoreText, GameOverText, ResultText, AgainText):
        t.hide()
    TitleText.show()
    HintText.show()
    set_speed(speed)


# the scene: every frame (dt = seconds since the last frame)
def Scene_Update(dt):
    if state == "ready":
        Player.y = 250 + 10 * math.sin(game.time * 4)          # bob up and down
        Player.rotation = 0
    elif state == "playing":
        if Player.bottom >= GROUND_Y:
            crash()
    elif state == "over" and Player.bottom >= GROUND_Y:          # lie on the ground
        Player.y = GROUND_Y - Player.height
        Player.enable("flap", False)


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
def Scene_KeyDown(key):
    if key == "escape":
        Quit()
    elif key in ("space", "up", "w", "enter"):
        tap()


# the scene: a mouse button goes down (screen pixels)
def Scene_MouseDown(x, y, button):
    tap()


# Player: touches another object (other)
def Player_Collide(other):
    if state != "playing":
        return
    if other.group in ("PillarTop", "PillarBottom", "Ground"):
        crash()
    elif other.group == "Gap":                 # flew through the gap of a gate
        Destroy(other)
        AddScore(1)
        PlaySound("point")
        if game.score % 5 == 0:
            harder()


# Player: flaps upwards (flap behaviour)
def Player_Flap():
    PlaySound("flap")


# GateTimer: the timer interval elapsed
def GateTimer_Tick():
    spawn_gate()


# ---------------------------------------------------------------- game flow
def tap():
    """Space / click: start on the title screen, play again after a crash."""
    if state == "ready":
        start()
    elif state == "over" and game.time - over_time > 0.6:
        RestartScene()


def start():
    global state
    state = "playing"
    TitleText.hide()
    HintText.hide()
    ScoreText.show()
    Player.enable("flap", True)               # this same key press also gives the first hop
    GateTimer.interval = gate_interval()
    GateTimer.start()
    spawn_gate()


def crash():
    global state, over_time
    state, over_time = "over", game.time
    PlaySound("hit")
    EnableBehaviour("scroll", False)          # the world stops
    GateTimer.stop()
    flap = Player.behaviour("flap")
    flap["keys"], flap["mouse"] = "", False    # no more hops: Glim falls to the ground
    if game.score > game.vars.get("best", 0):
        game.vars["best"] = game.score
        SaveData("best", game.score)
    ScoreText.hide()
    for t in (GameOverText, ResultText, AgainText):
        t.show()


def spawn_gate():
    """A pair of crystal columns with a gap at a random height, and the score zone in the gap."""
    global last_centre
    half = gap // 2
    centre = Random(max(60 + half, last_centre - MAX_STEP), min(GROUND_Y - 60 - half, last_centre + MAX_STEP))
    last_centre = centre
    top = Spawn("PillarTop", GATE_X, centre - half - PillarTop.height)
    bottom = Spawn("PillarBottom", GATE_X, centre + half)
    zone = Spawn("Gap", GATE_X + top.width - 10, centre - half)
    zone.h = gap
    for o in (top, bottom, zone):
        o.behaviour("scroll")["speed"] = speed


def harder():
    """Every 5 points: faster gates, a smaller gap."""
    global speed, gap
    speed = min(MAX_SPEED, speed + 15)
    gap = max(MIN_GAP, gap - 6)
    set_speed(speed)
    GateTimer.interval = gate_interval()


def gate_interval() -> float:
    return GATE_SPACING / speed * 1000


def set_speed(v):
    """The gates and the ground move together (the far scenery keeps its own slower speed)."""
    for o in [PillarTop, PillarBottom, Gap] + FindGroup("PillarTop") + FindGroup("PillarBottom") + \
            FindGroup("Gap") + FindGroup("Ground"):
        o.behaviour("scroll")["speed"] = v
