# Scene1 - translated from Scene1.py by RAD IDE (Export to Godot).
# Edit freely: this file is created once and kept on the next export. The scene Scene1.tscn is generated from Scene1.scene.
#
# Scene1 - Sky Hopper: hop Glim the firefly-bot through the crystal gates.
#
# Space / Up / click = hop (the "flap" behaviour of Player does the physics). Every gate you pass scores a
# point; the gates come faster and closer together as the score grows. Hitting a crystal or the ground ends
# the run; the best score is kept in savegame.json (SaveData / LoadData).
#
# Gates are made at run time from the hidden spawn templates PillarTop, PillarBottom and Gap (props
# template=1) with Spawn(); their "scroll" behaviour moves them left and removes them off screen.
extends "res://radgame/radgame_scene.gd"

# the objects of the scene used by this code (as in <Scene>_designer.py)
var AgainText: Node:
	get:
		return find("AgainText")
var GameOverText: Node:
	get:
		return find("GameOverText")
var Gap: Node:
	get:
		return find("Gap")
var HintText: Node:
	get:
		return find("HintText")
var PillarBottom: Node:
	get:
		return find("PillarBottom")
var PillarTop: Node:
	get:
		return find("PillarTop")
var Player: Node:
	get:
		return find("Player")
var ResultText: Node:
	get:
		return find("ResultText")
var ScoreText: Node:
	get:
		return find("ScoreText")
var TitleText: Node:
	get:
		return find("TitleText")
var GateTimer: Dictionary:
	get:
		return timers.get("GateTimer", {})

const GATE_X = 420   # new gates appear just right of the window
const GROUND_Y = 520   # top of the ground strip
const START_SPEED = 150.0
const MAX_SPEED = 260.0
const START_GAP = 150
const MIN_GAP = 112
const GATE_SPACING = 215   # pixels between two gates
const MAX_STEP = 150   # the next gap is at most this much higher / lower (always reachable)
var state_ = "ready"   # ready -> playing -> over
var speed = START_SPEED
var gap = START_GAP
var over_time = 0.0
var last_centre = 260


# the scene: the scene starts
func Scene_Load():
	state_ = "ready"
	speed = START_SPEED
	gap = START_GAP
	over_time = 0.0
	last_centre = 260
	score = 0
	vars["best"] = load_data("best", 0)
	enable_behaviour(Player, "flap", false)   # hovers on the start screen
	for t in [ScoreText, GameOverText, ResultText, AgainText]:
		hide_obj(t)
	show_obj(TitleText)
	show_obj(HintText)
	set_speed(speed)


# the scene: every frame (dt = seconds since the last frame)
func Scene_Update(dt):
	if state_ == "ready":
		setp(Player, "y", 250 + 10 * sin(game_time * 4))   # bob up and down
		setp(Player, "rotation", 0)
	elif state_ == "playing":
		if getp(Player, "bottom") >= GROUND_Y:
			crash()
	elif state_ == "over" and getp(Player, "bottom") >= GROUND_Y:   # lie on the ground
		setp(Player, "y", GROUND_Y - getp(Player, "height"))
		enable_behaviour(Player, "flap", false)


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown(key):
	if key == "escape":
		quit_game()
	elif key in ["space", "up", "w", "enter"]:
		tap()


# the scene: a mouse button goes down (screen pixels)
func Scene_MouseDown(x, y, button):
	tap()


# Player: touches another object (other)
func Player_Collide(other):
	if state_ != "playing":
		return
	if getp(other, "group") in ["PillarTop", "PillarBottom", "Ground"]:
		crash()
	elif getp(other, "group") == "Gap":   # flew through the gap of a gate
		destroy(other)
		add_score(1)
		play_sound("point")
		if score % 5 == 0:
			harder()


# Player: flaps upwards (flap behaviour)
func Player_Flap():
	play_sound("flap")


# GateTimer: the timer interval elapsed
func GateTimer_Tick():
	spawn_gate()


# ---------------------------------------------------------------- game flow
func tap():
	# Space / click: start on the title screen, play again after a crash.
	if state_ == "ready":
		start()
	elif state_ == "over" and game_time - over_time > 0.6:
		restart_scene()


func start():
	state_ = "playing"
	hide_obj(TitleText)
	hide_obj(HintText)
	show_obj(ScoreText)
	enable_behaviour(Player, "flap", true)   # this same key press also gives the first hop
	setp(GateTimer, "interval", gate_interval())
	timer_start(GateTimer)
	spawn_gate()


func crash():
	state_ = "over"
	over_time = game_time
	play_sound("hit")
	enable_behaviour_all("scroll", false)   # the world stops
	timer_stop(GateTimer)
	var flap = behaviour(Player, "flap")
	flap["keys"] = ""
	flap["mouse"] = false   # no more hops: Glim falls to the ground
	if score > vars.get("best", 0):
		vars["best"] = score
		save_data("best", score)
	hide_obj(ScoreText)
	for t in [GameOverText, ResultText, AgainText]:
		show_obj(t)


func spawn_gate():
	# A pair of crystal columns with a gap at a random height, and the score zone in the gap.
	var half = floori(gap / 2.0)
	var centre = randi_range(int(max(60 + half, last_centre - MAX_STEP)), int(min(GROUND_Y - 60 - half, last_centre + MAX_STEP)))
	last_centre = centre
	var top = spawn("PillarTop", GATE_X, centre - half - getp(PillarTop, "height"))
	var bottom = spawn("PillarBottom", GATE_X, centre + half)
	var zone = spawn("Gap", GATE_X + getp(top, "width") - 10, centre - half)
	setp(zone, "h", gap)
	for o in [top, bottom, zone]:
		behaviour(o, "scroll")["speed"] = speed


func harder():
	# Every 5 points: faster gates, a smaller gap.
	speed = min(MAX_SPEED, speed + 15)
	gap = max(MIN_GAP, gap - 6)
	set_speed(speed)
	setp(GateTimer, "interval", gate_interval())


func gate_interval():
	return GATE_SPACING / speed * 1000


func set_speed(v):
	# The gates and the ground move together (the far scenery keeps its own slower speed).
	for o in [PillarTop, PillarBottom, Gap] + find_group("PillarTop") + find_group("PillarBottom") + find_group("Gap") + find_group("Ground"):
		behaviour(o, "scroll")["speed"] = v
