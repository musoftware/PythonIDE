# Level1 - your game code (Godot 4). The scene Level1.tscn is generated from Level1.scene;
# double-click an object in the RAD IDE scene designer to add its handler.
# Helpers: find("Player"), group_of(node), score, lives, add_score(n), go_to_scene("Level2"),
# restart_scene(), play_sound("coin"), show_message("text", 2), add_timer("Timer1", 1000).
extends "res://radgame/radgame_scene.gd"


# the scene: the scene starts
func Scene_Load():
	show_message("Collect the coins and reach the flag!", 2)


# the scene: a key goes down (key = 'left', 'space', 'a', 'enter', 'escape' ...)
func Scene_KeyDown(key):
	if key == "escape":
		quit_game()
	elif key == "r":
		restart_scene()


# Player: jumps (platformer)
func Player_Jump():
	play_sound("jump")


# Player: touches another object (other)
func Player_Collide(other):
	var player := find("Player")
	if group_of(other) == "Enemy":
		if velocity(player).y > 0 and rect_of(player).end.y - rect_of(other).position.y < 14:
			destroy(other)
			set_velocity(player, Vector2(0, -320))
			add_score(5)
		else:
			lose_life()
	elif other.name == "Goal":
		show_message("You win! Score: %d" % score, 3)
		player.set_meta("behaviours", [])
		add_timer("WinTimer", 3000)


# Player: fell below the level
func Player_OutOfWorld():
	lose_life()


# WinTimer: the timer interval elapsed
func WinTimer_Tick():
	score = 0
	lives = 3
	restart_scene()

func lose_life():
	lives -= 1
	if lives <= 0:
		lives = 3
		score = 0
	restart_scene()
