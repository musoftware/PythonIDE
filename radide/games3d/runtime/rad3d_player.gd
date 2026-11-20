# rad3d_player.gd - third-person player controller (RAD IDE, copied into the project; do not edit).
# WASD / arrow keys move on the ground plane, Space jumps; gravity comes from the scene (project setting).
extends CharacterBody3D

@export var speed := 5.0
@export var jump_velocity := 5.5
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)


func _scene():
	var s = get_parent()
	while s != null and not s.has_method("key_down"):
		s = s.get_parent()
	return s


func _down(s, a: int, b: int) -> bool:
	if s != null:
		return s.key_down(a) or s.key_down(b)
	return Input.is_key_pressed(a) or Input.is_key_pressed(b)


func _physics_process(delta: float) -> void:
	var s = _scene()
	if not is_on_floor():
		velocity.y -= gravity * delta
	elif _down(s, KEY_SPACE, KEY_SPACE):
		velocity.y = jump_velocity
	var dir := Vector3.ZERO
	if _down(s, KEY_W, KEY_UP):
		dir.z -= 1.0
	if _down(s, KEY_S, KEY_DOWN):
		dir.z += 1.0
	if _down(s, KEY_A, KEY_LEFT):
		dir.x -= 1.0
	if _down(s, KEY_D, KEY_RIGHT):
		dir.x += 1.0
	dir = dir.normalized()
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	move_and_slide()
	if global_position.y < -30.0:
		global_position = Vector3(0, 3, 0)
		velocity = Vector3.ZERO
