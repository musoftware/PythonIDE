# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Room1 - Gem Hunter, a top-down Godot 4 game made in RAD IDE.  Room1.tscn is generated from Room1.scene (edit
# the room in RAD IDE's scene designer: tile map walls, the Hero with the top_down behaviour, gems with the
# collectible behaviour, enemies with enemy_patrol).  This script adds the rules:
#   * a 60 second countdown (add_timer + RoundTimer_Tick) shown with show_message,
#   * three lives - touching an enemy costs one and restarts the room,
#   * the best score saved with save_data / load_data (user:// folder of the game),
#   * R restarts, Escape quits.
# Helpers: find("Hero"), group_of(node), score, lives, add_score(n), restart_scene(), show_message(), add_timer().
extends "res://radgame/radgame_scene.gd"

const ROUND_SECONDS := 60
static var time_left := ROUND_SECONDS
var last_score := -1


# the scene: the scene starts
func Scene_Load():
	if lives <= 0:
		lives = 3
	add_timer("RoundTimer", 1000)
	var best = load_data("best", 0)
	show_message("Collect all the gems!  Best: %d" % best, 2)
	print("ROOM gems=%d lives=%d time=%d" % [find_group("Gem").size(), lives, time_left])


# the scene: every frame - report the score when a gem was collected
func Scene_Update(dt):
	if score != last_score:
		if last_score >= 0:
			print("GEM score=%d left=%d" % [score, find_group("Gem").size()])
		last_score = score
		if find_group("Gem").is_empty():
			finish("All gems collected!")


# RoundTimer: one second passed
func RoundTimer_Tick():
	time_left -= 1
	if time_left in [30, 10, 5]:
		show_message("%d seconds left" % time_left, 1)
	if time_left <= 0:
		finish("Time is up!")


# the scene: a key goes down
func Scene_KeyDown(key):
	if key == "escape":
		quit_game()
	elif key == "r":
		new_game()


# Hero: touches another object (other)
func Hero_Collide(other):
	if group_of(other) == "Enemy":
		lives -= 1
		print("HIT lives=%d" % lives)
		if lives <= 0:
			finish("Caught by a guard!")
		else:
			restart_scene()


func finish(text: String) -> void:
	var best = max(int(load_data("best", 0)), score)
	save_data("best", best)
	print("GAMEOVER %s score=%d best=%d" % [text, score, best])
	show_message("%s  Score %d  (R = again)" % [text, score], 4)


func new_game() -> void:
	score = 0
	lives = 3
	time_left = ROUND_SECONDS
	restart_scene()
