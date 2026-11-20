# Scene1 - your game code (Godot 4). The scene Scene1.tscn is generated from Scene1.scene;
# double-click an object in the RAD IDE scene designer to add its handler.
# Helpers: find("Player"), group_of(node), score, lives, add_score(n), go_to_scene("Level2"),
# restart_scene(), play_sound("coin"), show_message("text", 2), add_timer("Timer1", 1000).
# Exported from the pygame version: translate the Python lines (comments) under each func.
extends "res://radgame/radgame_scene.gd"

# GATE_X = 420                 # new gates appear just right of the window
var GATE_X
# GROUND_Y = 520               # top of the ground strip
var GROUND_Y
# START_SPEED, MAX_SPEED = 150.0, 260.0
var START_SPEED
var MAX_SPEED
# START_GAP, MIN_GAP = 150, 112
var START_GAP
var MIN_GAP
# GATE_SPACING = 215           # pixels between two gates
var GATE_SPACING
# MAX_STEP = 150               # the next gap is at most this much higher / lower (always reachable)
var MAX_STEP
# state = "ready"              # ready -> playing -> over
var state_   # renamed: 'state' is a name of the runtime
# speed = START_SPEED
var speed
# gap = START_GAP
var gap
# over_time = 0.0
var over_time
# last_centre = 260
var last_centre


# the scene: the scene starts
func Scene_Load():
	# global state, speed, gap, over_time, last_centre
	# state, speed, gap, over_time, last_centre = "ready", START_SPEED, START_GAP, 0.0, 260
	# game.score = 0
	# game.vars["best"] = LoadData("best", 0)
	# Player.enable("flap", False)              # hovers on the start screen
	# for t in (ScoreText, GameOverText, ResultText, AgainText):
	#     t.hide()
	# TitleText.show()
	# HintText.show()
	# set_speed(speed)
	pass


# the scene: every frame (dt = seconds since the last frame)
func Scene_Update(dt):
	# if state == "ready":
	#     Player.y = 250 + 10 * math.sin(game.time * 4)          # bob up and down
	#     Player.rotation = 0
	# elif state == "playing":
	#     if Player.bottom >= GROUND_Y:
	#         crash()
	# elif state == "over" and Player.bottom >= GROUND_Y:          # lie on the ground
	#     Player.y = GROUND_Y - Player.height
	#     Player.enable("flap", False)
	pass


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown(key):
	# if key == "escape":
	#     Quit()
	# elif key in ("space", "up", "w", "enter"):
	#     tap()
	pass


# the scene: a mouse button goes down (screen pixels)
func Scene_MouseDown(x, y, button):
	# tap()
	pass


# Player: touches another object (other)
func Player_Collide(other):
	# if state != "playing":
	#     return
	# if other.group in ("PillarTop", "PillarBottom", "Ground"):
	#     crash()
	# elif other.group == "Gap":                 # flew through the gap of a gate
	#     Destroy(other)
	#     AddScore(1)
	#     PlaySound("point")
	#     if game.score % 5 == 0:
	#         harder()
	pass


# Player: flaps upwards (flap behaviour)
func Player_Flap():
	# PlaySound("flap")
	pass


# GateTimer: the timer interval elapsed
func GateTimer_Tick():
	# spawn_gate()
	pass


func tap():
	# """Space / click: start on the title screen, play again after a crash."""
	# if state == "ready":
	#     start()
	# elif state == "over" and game.time - over_time > 0.6:
	#     RestartScene()
	pass


func start():
	# global state
	# state = "playing"
	# TitleText.hide()
	# HintText.hide()
	# ScoreText.show()
	# Player.enable("flap", True)               # this same key press also gives the first hop
	# GateTimer.interval = gate_interval()
	# GateTimer.start()
	# spawn_gate()
	pass


func crash():
	# global state, over_time
	# state, over_time = "over", game.time
	# PlaySound("hit")
	# EnableBehaviour("scroll", False)          # the world stops
	# GateTimer.stop()
	# flap = Player.behaviour("flap")
	# flap["keys"], flap["mouse"] = "", False    # no more hops: Glim falls to the ground
	# if game.score > game.vars.get("best", 0):
	#     game.vars["best"] = game.score
	#     SaveData("best", game.score)
	# ScoreText.hide()
	# for t in (GameOverText, ResultText, AgainText):
	#     t.show()
	pass


func spawn_gate():
	# """A pair of crystal columns with a gap at a random height, and the score zone in the gap."""
	# global last_centre
	# half = gap // 2
	# centre = Random(max(60 + half, last_centre - MAX_STEP), min(GROUND_Y - 60 - half, last_centre + MAX_STEP))
	# last_centre = centre
	# top = Spawn("PillarTop", GATE_X, centre - half - PillarTop.height)
	# bottom = Spawn("PillarBottom", GATE_X, centre + half)
	# zone = Spawn("Gap", GATE_X + top.width - 10, centre - half)
	# zone.h = gap
	# for o in (top, bottom, zone):
	#     o.behaviour("scroll")["speed"] = speed
	pass


func harder():
	# """Every 5 points: faster gates, a smaller gap."""
	# global speed, gap
	# speed = min(MAX_SPEED, speed + 15)
	# gap = max(MIN_GAP, gap - 6)
	# set_speed(speed)
	# GateTimer.interval = gate_interval()
	pass


func gate_interval():
	# return GATE_SPACING / speed * 1000
	pass


func set_speed(v):
	# """The gates and the ground move together (the far scenery keeps its own slower speed)."""
	# for o in [PillarTop, PillarBottom, Gap] + FindGroup("PillarTop") + FindGroup("PillarBottom") + \
	#         FindGroup("Gap") + FindGroup("Ground"):
	#     o.behaviour("scroll")["speed"] = v
	pass
