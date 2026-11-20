# Room1 - your game code (Godot 4). The scene Room1.tscn is generated from Room1.scene;
# double-click an object in the RAD IDE scene designer to add its handler.
# Helpers: find("Player"), group_of(node), score, lives, add_score(n), go_to_scene("Level2"),
# restart_scene(), play_sound("coin"), show_message("text", 2), add_timer("Timer1", 1000).
extends "res://radgame/radgame_scene.gd"


# the scene: the scene starts
func Scene_Load():
	show_message("Collect all the gems!", 2)


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown(key):
	if key == "escape":
		quit_game()


# Hero: touches another object (other)
func Hero_Collide(other):
	if group_of(other) == "Enemy":
		score = 0
		restart_scene()
	elif find_group("Gem").is_empty():
		show_message("All gems collected!", 3)
