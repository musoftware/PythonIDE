# rad3d_scene.gd - RAD IDE 3D scene runtime for Godot 4 (copied into the project by RAD IDE, do not edit).
# The scene script <Scene>.gd extends this file and writes VB-style handlers:
#   func Scene_Load():            once, when the scene starts
#   func Scene_Update(delta):     every frame
#   func Player_Collect(item):    the player touched a "collectible" entity (it is removed afterwards)
# Test hooks (environment): RAD3D_FRAMES=n quits after n frames and prints a summary line,
# RAD3D_KEYS="w:5-60,space:20-25" holds keys between frames, RAD3D_SCREENSHOT=file.png saves the last frame.
extends Node3D

var score := 0
var vars := {}
var player: Node3D = null
var sim_keys := {}
var _camera: Camera3D = null
var _cam_offset := Vector3.ZERO
var _frames := 0
var _quit_after := 0
var _key_script := []

const KEYS := {"w": KEY_W, "a": KEY_A, "s": KEY_S, "d": KEY_D, "up": KEY_UP, "down": KEY_DOWN,
	"left": KEY_LEFT, "right": KEY_RIGHT, "space": KEY_SPACE}


func _ready() -> void:
	var players := get_tree().get_nodes_in_group("player")
	if players.size() > 0:
		player = players[0]
	for c in find_children("*", "Camera3D", true, false):
		_camera = c
		break
	if _camera != null and player != null:
		_cam_offset = _camera.global_position - player.global_position
	for item in get_tree().get_nodes_in_group("collectible"):
		if item is Area3D:
			item.body_entered.connect(_on_collect.bind(item))
	_quit_after = int(OS.get_environment("RAD3D_FRAMES")) if OS.get_environment("RAD3D_FRAMES") != "" else 0
	for part in OS.get_environment("RAD3D_KEYS").split(",", false):
		var kv := part.split(":")
		if kv.size() == 2 and KEYS.has(kv[0].strip_edges().to_lower()):
			var span := kv[1].split("-")
			if span.size() == 2:
				_key_script.append([KEYS[kv[0].strip_edges().to_lower()], int(span[0]), int(span[1])])
	if has_method("Scene_Load"):
		call("Scene_Load")


func key_down(code: int) -> bool:
	return Input.is_key_pressed(code) or sim_keys.has(code)


func find(entity_name: String) -> Node:
	return find_child(entity_name, true, false)


func _on_collect(body: Node, item: Node) -> void:
	if body != player or not is_instance_valid(item) or item.is_queued_for_deletion():
		return
	score += 1
	if has_method("Player_Collect"):
		call("Player_Collect", item)
	item.queue_free()


func _process(delta: float) -> void:
	for n in get_tree().get_nodes_in_group("spin"):
		if n is Node3D:
			n.rotate_y(deg_to_rad(90.0) * delta)
	if _camera != null and player != null and is_instance_valid(player):
		_camera.global_position = player.global_position + _cam_offset
	if has_method("Scene_Update"):
		call("Scene_Update", delta)
	_test_tick()


func _test_tick() -> void:
	for k in _key_script:
		if _frames == k[1]:
			sim_keys[k[0]] = true
		elif _frames == k[2]:
			sim_keys.erase(k[0])
	_frames += 1
	if _quit_after > 0 and _frames >= _quit_after:
		var shot := OS.get_environment("RAD3D_SCREENSHOT")
		if shot != "" and DisplayServer.get_name() != "headless":
			get_viewport().get_texture().get_image().save_png(shot)
		var p := player.global_position if player != null else Vector3.ZERO
		print("rad3d-test: %d frames score=%d player=(%.2f,%.2f,%.2f)" % [_frames, score, p.x, p.y, p.z])
		get_tree().quit()
