# radgame_scene.gd - the RAD IDE game runtime for Godot 4 (copied into game projects as res://radgame/).
# Every exported scene's root script (your <Scene>.gd) extends this file. It moves the objects with
# their Behaviours (keyboard_move, platformer, top_down, bounce, follow_mouse, solid, collectible,
# enemy_patrol), detects collisions against TileMaps marked "collision" and solid sprites, and calls
# your VB-style handlers: Scene_Load(), Scene_Update(dt), Scene_KeyDown(key), Scene_KeyUp(key),
# Scene_MouseDown(x, y, button), <Obj>_Collide(other), <Obj>_Click(), <Obj>_Jump(), <Obj>_OutOfWorld(),
# <Timer>_Tick(). Objects named Coin1, Coin2 ... also fire the group handler Coin_Collide(other).
# Helpers: find("Player"), group_of(node), add_score(n), go_to_scene("Level2"), restart_scene(),
# play_sound("coin"), show_message("text", seconds), add_timer("Timer1", ms), quit_game(),
# spawn("Pipe", x, y) (copies a spawn template: props template=1), enable_behaviour(node, "scroll", false),
# save_data("best", n) / load_data("best", 0). Behaviours flap and scroll work like in radgame.py.
# Code translated from Python (radide/games/gd_translate.py) uses getp(obj, "y") / setp(obj, "y", v) for the
# radgame object attributes (x, y = top-left, width, bottom, rotation in degrees, text, group ...),
# show_obj / hide_obj, timer_start / timer_stop, enable_behaviour_all; particles: emit_particles(effect, x, y)
# / burst_particles(effect, x, y, n) and emitter objects; physics (scene "physics" enabled, object "physics"
# body / shape / mass / friction / elasticity, scene "joints"): apply_impulse(obj, ix, iy), set_body_velocity.
extends Node2D

static var score := 0
static var lives := 3
static var vars := {}
static var _all_frames := 0     # frames since the game started (RADGAME_FRAMES / RADGAME_KEYS, like radgame.py)

var settings := {}
var objects := {}            # name -> node
var world_size := Vector2(800, 600)
var view_size := Vector2(800, 600)
var held := {}
var pressed := {}
var frame := 0
var game_time := 0.0
var timers := {}
var _touching := {}
var _argc := {}
var _labels := []
var _message: Label
var _message_until := 0.0
var _camera: Camera2D
var _test_keys := []
var _test_frames := 0
var _pending_scene := ""
var _clicked := false
var _spawn_n := 0
var _trace := OS.get_environment("RADGAME_TRACE") != ""
var _physics_on := false
var _syncing_bodies := false
var _emitters := []          # CPUParticles2D nodes made by emitter objects / emit_particles()
var _music: AudioStreamPlayer
var _dot_texture: Texture2D

const ACTORS := ["platformer", "keyboard_move", "top_down", "follow_mouse"]


func _ready() -> void:
	settings = get_meta("rad_scene", {})
	view_size = Vector2(settings.get("width", 800), settings.get("height", 600))
	world_size = Vector2(settings.get("world_w", view_size.x), settings.get("world_h", view_size.y))
	RenderingServer.set_default_clear_color(Color(settings.get("background", "#6EC1E4")))
	for m in get_method_list():
		_argc[m["name"]] = m["args"].size()
	_collect(self)
	for t in settings.get("timers", []):
		add_timer(t.get("name", "Timer1"), t.get("interval", 1000), t.get("enabled", true))
	_camera = Camera2D.new()
	_camera.name = "RadCamera"
	_camera.anchor_mode = Camera2D.ANCHOR_MODE_FIXED_TOP_LEFT
	add_child(_camera)
	_camera.make_current()
	var ui := CanvasLayer.new()
	ui.layer = 50
	add_child(ui)
	_message = Label.new()
	_message.visible = false
	_message.add_theme_font_size_override("font_size", 36)
	_message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_message.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_message.position = Vector2(0, view_size.y / 2 - 30)
	_message.size = Vector2(view_size.x, 60)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.8)
	_message.add_theme_stylebox_override("normal", bg)
	ui.add_child(_message)
	var spec: String = OS.get_environment("RADGAME_KEYS")      # tests: "right:0-90,space:20-24"
	for part in spec.split(",", false):
		var kv := part.split(":")
		if kv.size() == 2:
			var r := kv[1].split("-")
			_test_keys.append([kv[0], int(r[0]), int(r[1])])
	_test_frames = int(OS.get_environment("RADGAME_FRAMES")) if OS.get_environment("RADGAME_FRAMES") != "" else 0
	_setup_physics()
	_setup_emitters()
	_update_camera()
	_fire_scene("Load", [])


func _collect(node: Node) -> void:
	for child in node.get_children():
		if child.has_meta("rad_kind"):
			objects[String(child.name)] = child
			child.set_meta("rad_state", {"vx": 0.0, "vy": 0.0, "on_ground": false, "alive": true})
			var pr: Dictionary = child.get_meta("props", {})
			if str(pr.get("template", "")).to_lower() in ["1", "true", "yes", "on"]:
				state(child)["alive"] = false          # a spawn template: hidden, inactive (spawn() copies it)
				state(child)["template"] = true
				child.visible = false
			if child is Label:
				_labels.append(child)
		_collect(child)


# ------------------------------------------------------------------ geometry
func rect_of(n: Node) -> Rect2:
	var s: Vector2 = n.get_meta("rad_size", Vector2(32, 32))
	if n is Control:
		return Rect2(n.position, s)
	if n.get_meta("rad_centered", false):
		return Rect2(n.position - s / 2.0, s)
	return Rect2(n.position, s)


func hit_rect(n: Node) -> Rect2:
	# The collision box: rect_of shrunk by props hitbox pixels on every side (as radgame.py).
	var r := rect_of(n)
	var k := float(n.get_meta("props", {}).get("hitbox", 0))
	if k > 0 and r.size.x > 2 * k and r.size.y > 2 * k:
		r = r.grow(-k)
	return r


func set_top_left(n: Node, p: Vector2) -> void:
	var s: Vector2 = n.get_meta("rad_size", Vector2(32, 32))
	if n.get_meta("rad_centered", false) and not (n is Control):
		n.position = p + s / 2.0
	else:
		n.position = p
	if n.has_meta("rad_body") and _syncing_bodies == false:
		_teleport_body(n)


func state(n: Node) -> Dictionary:
	return n.get_meta("rad_state")


func alive(n: Node) -> bool:
	return is_instance_valid(n) and n.has_meta("rad_state") and state(n)["alive"]


func has_behaviour(n: Node, t: String) -> bool:
	for b in n.get_meta("behaviours", []):
		if b.get("type", "") == t:
			return true
	return false


func behaviour(n: Node, t: String) -> Dictionary:
	for b in n.get_meta("behaviours", []):
		if b.get("type", "") == t:
			return b
	return {}


func group_of(n: Node) -> String:
	return n.get_meta("group", String(n.name))


func find(obj_name: String) -> Node:
	return objects.get(obj_name)


func find_group(group: String) -> Array:
	var out := []
	for n in objects.values():
		if alive(n) and group_of(n) == group:
			out.append(n)
	return out


func destroy(n: Node) -> void:
	state(n)["alive"] = false
	n.visible = false
	if state(n).get("spawned", false):
		objects.erase(String(n.name))
		n.queue_free()


func spawn(template_name: String, x: float, y: float) -> Node:
	# A copy of a scene object (usually a spawn template: props template=1) at (x, y).
	return clone_obj(find(template_name), x, y)


func clone_obj(t, x = null, y = null) -> Node:
	# A copy of a scene object at (x, y) (its own place when x / y are null).
	if t == null or not (t is Node):
		return null
	var at := rect_of(t).position
	if x != null:
		at.x = float(x)
	if y != null:
		at.y = float(y)
	x = at.x
	y = at.y
	var c: Node = t.duplicate()
	_spawn_n += 1
	c.name = "%s_%d" % [String(t.name), _spawn_n]
	t.get_parent().add_child(c)
	var bs: Array = []
	for d in t.get_meta("behaviours", []):
		bs.append(d.duplicate())
	c.set_meta("behaviours", bs)
	c.set_meta("rad_state", {"vx": 0.0, "vy": 0.0, "on_ground": false, "alive": true, "spawned": true})
	c.set_meta("group", group_of(t))
	c.visible = true
	for m in ["rad_body", "rad_emitter"]:
		if c.has_meta(m):
			c.remove_meta(m)
	objects[String(c.name)] = c
	set_top_left(c, Vector2(x, y))
	if _physics_on and c.has_meta("physics"):
		_make_body(c)
	if c.has_meta("particles"):
		_attach_emitter(c)
	return c


func enable_behaviour(n: Node, t: String, on: bool = true) -> void:
	for b in n.get_meta("behaviours", []):
		if b.get("type", "") == t:
			b["enabled"] = on


func save_data(key: String, value) -> void:
	# Keep a value after the game closes (user://savegame.json).
	var data := _saved()
	data[key] = value
	var f := FileAccess.open("user://savegame.json", FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(data))


func load_data(key: String, default_value = null):
	return _saved().get(key, default_value)


func _saved() -> Dictionary:
	if not FileAccess.file_exists("user://savegame.json"):
		return {}
	var f := FileAccess.open("user://savegame.json", FileAccess.READ)
	var d = JSON.parse_string(f.get_as_text()) if f != null else null
	return d if d is Dictionary else {}


# ------------------------------------------------------------------ collision
func blockers(r: Rect2, ignore: Node) -> Array:
	var out := []
	for tm in find_children("*", "TileMap", true, false):
		if not tm.get_meta("collision", false):
			continue
		var ts: Vector2 = Vector2(tm.tile_set.tile_size)
		var c0 := int(floor(r.position.x / ts.x))
		var c1 := int(floor((r.end.x - 0.01) / ts.x))
		var r0 := int(floor(r.position.y / ts.y))
		var r1 := int(floor((r.end.y - 0.01) / ts.y))
		for row in range(r0, r1 + 1):
			for col in range(c0, c1 + 1):
				if tm.get_cell_source_id(0, Vector2i(col, row)) != -1:
					out.append(Rect2(Vector2(col, row) * ts, ts))
	for n in objects.values():
		if n != ignore and alive(n) and has_behaviour(n, "solid"):
			var o := rect_of(n)
			if o.intersects(r):
				out.append(o)
	return out


func is_solid_at(p: Vector2, ignore: Node) -> bool:
	return blockers(Rect2(p, Vector2(1, 1)), ignore).size() > 0


func move_and_collide_obj(n: Node, d: Vector2) -> Vector2i:
	var hit := Vector2i.ZERO
	var steps := int(max(abs(d.x), abs(d.y)) / 8.0) + 1
	var s := d / steps
	for i in range(steps):
		if s.x != 0 and hit.x == 0:
			var r := rect_of(n)
			r.position.x += s.x
			for b in blockers(r, n):
				if r.intersects(b):
					r.position.x = b.position.x - r.size.x if s.x > 0 else b.end.x
					hit.x = 1
			set_top_left(n, r.position)
		if s.y != 0 and hit.y == 0:
			var r2 := rect_of(n)
			r2.position.y += s.y
			for b in blockers(r2, n):
				if r2.intersects(b):
					r2.position.y = b.position.y - r2.size.y if s.y > 0 else b.end.y
					hit.y = 1
			set_top_left(n, r2.position)
	return hit


func _standing(n: Node) -> bool:
	var r := rect_of(n)
	return blockers(Rect2(r.position.x + 1, r.end.y, max(1.0, r.size.x - 2), 1), n).size() > 0


# ------------------------------------------------------------------ input
func _key_name(e: InputEventKey) -> String:
	var k := OS.get_keycode_string(e.keycode).to_lower()
	if k == "enter" or k == "kp enter":
		return "enter"
	return k


func key_down(k: String) -> bool:
	return held.has(k)


func _axis(neg: Array, pos: Array) -> int:
	var v := 0
	for k in pos:
		if held.has(k):
			v += 1
			break
	for k in neg:
		if held.has(k):
			v -= 1
			break
	return v


func _press(k: String) -> void:
	if not held.has(k):
		held[k] = true
		pressed[k] = true
		_fire_scene("KeyDown", [k])


func _release(k: String) -> void:
	if held.has(k):
		held.erase(k)
		_fire_scene("KeyUp", [k])


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and not event.echo:
		if event.pressed:
			_press(_key_name(event))
		else:
			_release(_key_name(event))
	elif event is InputEventMouseButton and event.pressed:
		_clicked = true
		var p: Vector2 = event.position
		_fire_scene("MouseDown", [p.x, p.y, event.button_index])
		var wp := p + _camera.position
		for n in objects.values():
			if alive(n) and n.visible and rect_of(n).has_point(wp if not _in_ui(n) else p):
				_fire_object(n, "Click", [])
				break


func _in_ui(n: Node) -> bool:
	var p := n.get_parent()
	while p != null:
		if p is CanvasLayer:
			return true
		p = p.get_parent()
	return false


# ------------------------------------------------------------------ events
func _call(method: String, args: Array) -> bool:
	if not has_method(method):
		return false
	var n: int = _argc.get(method, args.size())
	if _trace:
		print("RADGAME_CALL %d %s" % [frame, method])
	callv(method, args.slice(0, n))
	return true


func _fire_scene(ev: String, args: Array) -> void:
	for who in ["Scene", String(name), "Game"]:
		if _call(who + "_" + ev, args):
			return


func _fire_object(n: Node, ev: String, args: Array) -> bool:
	var done := _call(String(n.name) + "_" + ev, args)
	var g := group_of(n)
	if g != String(n.name):
		done = _call(g + "_" + ev, args) or done
	return done


# ------------------------------------------------------------------ loop
func _physics_process(dt: float) -> void:
	for tk in _test_keys:
		if _all_frames == tk[1]:
			_press(tk[0])
		elif _all_frames == tk[2]:
			_release(tk[0])
	for t in timers.values():
		if t["enabled"] and t["interval"] > 0:
			t["acc"] += dt * 1000.0
			while t["acc"] >= t["interval"] - 0.000001 and t["enabled"]:
				t["acc"] -= t["interval"]
				_call(t["name"] + "_Tick", [])
	for n in objects.values():
		if not alive(n):
			continue
		for b in n.get_meta("behaviours", []):
			if b.get("enabled", true) == false:
				continue
			match b.get("type", ""):
				"flap": _flap(n, b, dt)
				"scroll": _scroll(n, b, dt)
				"platformer": _platformer(n, b, dt)
				"keyboard_move": _keyboard_move(n, b, dt)
				"top_down": _top_down(n, b, dt)
				"bounce": _bounce(n, b, dt)
				"follow_mouse": _follow_mouse(n, b, dt)
				"enemy_patrol": _patrol(n, b, dt)
		if not _in_ui(n) and rect_of(n).position.y > world_size.y + 200:
			if not _fire_object(n, "OutOfWorld", []):
				var actor := false
				for a in ACTORS:
					actor = actor or has_behaviour(n, a)
				if actor:
					restart_scene()
				else:
					destroy(n)
	_sync_bodies()
	_update_emitters()
	_collisions()
	_fire_scene("Update", [dt])
	_update_camera()
	_update_labels()
	if _message.visible and game_time > _message_until:
		_message.visible = false
	pressed.clear()
	_clicked = false
	frame += 1
	_all_frames += 1
	game_time += dt
	if _pending_scene != "":
		var target := _pending_scene
		_pending_scene = ""
		get_tree().change_scene_to_file("res://" + target + ".tscn")
		return
	if _test_frames > 0 and _all_frames >= _test_frames:
		var p: Node = find(String(settings.get("report", "")))
		var where := ""
		if p != null:
			where = " x=%d y=%d" % [int(rect_of(p).position.x), int(rect_of(p).position.y)]
		print("RADGAME_RESULT frames=%d score=%d lives=%d%s" % [frame, score, lives, where])
		_stop_sounds()
		get_tree().quit()


func _collisions() -> void:
	var list := []
	for n in objects.values():
		if alive(n) and not _in_ui(n) and not (n is Label) and not _is_pure_emitter(n):
			list.append(n)
	var now := {}
	var rects := []
	for n in list:
		rects.append(hit_rect(n))
	for i in range(list.size()):
		var ra: Rect2 = rects[i]
		for j in range(i + 1, list.size()):
			if ra.intersects(rects[j]):
				now[[String(list[i].name), String(list[j].name)]] = true
	for pair in now.keys():
		if _touching.has(pair):
			continue
		var a: Node = objects.get(pair[0])
		var b: Node = objects.get(pair[1])
		if not (alive(a) and alive(b)):
			continue
		for ab in [[a, b], [b, a]]:
			var c := behaviour(ab[1], "collectible")
			if not c.is_empty() and _is_actor(ab[0]):
				score += int(c.get("score", 1))
				if c.get("sound", "") != "":
					play_sound(c["sound"])
		_fire_object(a, "Collide", [b])
		_fire_object(b, "Collide", [a])
		for ab in [[a, b], [b, a]]:
			if has_behaviour(ab[1], "collectible") and _is_actor(ab[0]):
				destroy(ab[1])
	_touching = {}
	for pair in now.keys():
		if alive(objects.get(pair[0])) and alive(objects.get(pair[1])):
			_touching[pair] = true


func _is_actor(n: Node) -> bool:
	for a in ACTORS:
		if has_behaviour(n, a):
			return true
	return false


func _update_camera() -> void:
	var p := Vector2.ZERO
	var target: Node = null
	if settings.get("follow", null) != null:
		target = find(String(settings["follow"]))
	if target != null:
		p = rect_of(target).get_center() - view_size / 2.0
	p.x = clamp(p.x, 0.0, max(0.0, world_size.x - view_size.x))
	p.y = clamp(p.y, 0.0, max(0.0, world_size.y - view_size.y))
	_camera.position = p


func _update_labels() -> void:
	for l in _labels:
		var t: String = l.get_meta("template", l.text)
		var values := {"score": score, "lives": lives, "level": String(name)}
		values.merge(vars)
		l.text = t.format(values)


# ------------------------------------------------------------------ behaviours
func _flip(n: Node, left: bool) -> void:
	if n is Sprite2D or n is AnimatedSprite2D:
		n.flip_h = left


func _anim(n: Node, names: Array) -> void:
	if n is AnimatedSprite2D and n.sprite_frames != null:
		for a in names:
			if n.sprite_frames.has_animation(a):
				if n.animation != a:
					n.play(a)
				elif not n.is_playing():
					n.play(a)
				return


func _keys(b: Dictionary, dir: String) -> Array:
	var arrows: String = {"left": "left", "right": "right", "up": "up", "down": "down"}[dir]
	var wasd: String = {"left": "a", "right": "d", "up": "w", "down": "s"}[dir]
	match String(b.get("keys", "both")):
		"arrows": return [arrows]
		"wasd": return [wasd]
	return [arrows, wasd]


func _clamp_world(n: Node) -> void:
	var r := rect_of(n)
	set_top_left(n, Vector2(clamp(r.position.x, 0.0, world_size.x - r.size.x),
			clamp(r.position.y, 0.0, world_size.y - r.size.y)))


func _keyboard_move(n: Node, b: Dictionary, dt: float) -> void:
	var speed: float = b.get("speed", 200)
	var d := Vector2(_axis(_keys(b, "left"), _keys(b, "right")), _axis(_keys(b, "up"), _keys(b, "down")))
	if d.x != 0 and d.y != 0:
		d *= 0.7071
	if d.x != 0:
		_flip(n, d.x < 0)
	move_and_collide_obj(n, d * speed * dt)
	_clamp_world(n)


func _top_down(n: Node, b: Dictionary, dt: float) -> void:
	var speed: float = b.get("speed", 180)
	var d := Vector2(_axis(_keys(b, "left"), _keys(b, "right")), _axis(_keys(b, "up"), _keys(b, "down")))
	if d.length() > 0:
		d = d.normalized()
	move_and_collide_obj(n, d * speed * dt)
	_clamp_world(n)
	var st := state(n)
	if d.length() > 0:
		var face: String = ("right" if d.x > 0 else "left") if abs(d.x) >= abs(d.y) else ("down" if d.y > 0 else "up")
		st["facing"] = face
		if b.get("rotate", false):
			n.rotation = d.angle()
		_anim(n, ["walk_" + face, face, "walk", "run"])
	else:
		_anim(n, ["idle_" + String(st.get("facing", "down")), "idle"])


func _platformer(n: Node, b: Dictionary, dt: float) -> void:
	var st := state(n)
	var speed: float = b.get("speed", 220)
	var jump: float = b.get("jump", 520)
	var gravity: float = b.get("gravity", settings.get("gravity", 900))
	var ix := _axis(_keys(b, "left"), _keys(b, "right"))
	st["vx"] = ix * speed
	if ix != 0:
		_flip(n, ix < 0)
	st["coyote"] = 0.1 if st["on_ground"] else max(0.0, st.get("coyote", 0.0) - dt)
	if st["on_ground"]:
		st["jumps_left"] = int(b.get("jumps", 1))
	var jump_keys := ["space"] + (["up"] if "up" in _keys(b, "up") else []) + (["w"] if "w" in _keys(b, "up") else [])
	var hit_jump := false
	for k in jump_keys:
		hit_jump = hit_jump or pressed.has(k)
	st["buffer"] = 0.12 if hit_jump else max(0.0, st.get("buffer", 0.0) - dt)
	if st["buffer"] > 0 and (st["coyote"] > 0 or st.get("jumps_left", 0) > 0):
		st["vy"] = -jump
		st["buffer"] = 0.0
		st["coyote"] = 0.0
		st["jumps_left"] = st.get("jumps_left", 1) - 1
		st["on_ground"] = false
		_fire_object(n, "Jump", [])
	var holding := false
	for k in jump_keys:
		holding = holding or held.has(k)
	if st["vy"] < 0 and not holding:
		st["vy"] += gravity * dt * 1.5
	st["vy"] = min(st["vy"] + gravity * dt, float(b.get("max_fall", 900)))
	var hit := move_and_collide_obj(n, Vector2(st["vx"], st["vy"]) * dt)
	if hit.y != 0:
		st["vy"] = 0.0
	st["on_ground"] = _standing(n) and st["vy"] >= 0
	var r := rect_of(n)
	set_top_left(n, Vector2(clamp(r.position.x, 0.0, world_size.x - r.size.x), r.position.y))
	if st["on_ground"]:
		_anim(n, ["run", "walk"] if ix != 0 else ["idle"])
	else:
		_anim(n, ["jump", "fall"] if st["vy"] < 0 else ["fall", "jump"])


func _flap(n: Node, b: Dictionary, dt: float) -> void:
	var st := state(n)
	var gravity: float = float(b.get("gravity", settings.get("gravity", 900)))
	var kick := bool(b.get("mouse", true)) and _clicked
	for k in String(b.get("keys", "space,up,w")).split(",", false):
		if pressed.has(k.strip_edges().to_lower()):
			kick = true
	if kick:
		st["vy"] = -float(b.get("flap", 320))
		_fire_object(n, "Flap", [])
	st["vy"] = min(float(st["vy"]) + gravity * dt, float(b.get("max_fall", 600)))
	var r := rect_of(n)
	var y: float = r.position.y + float(st["vy"]) * dt
	if bool(b.get("ceiling", true)) and y < 0.0:
		y = 0.0
		st["vy"] = max(0.0, float(st["vy"]))
	set_top_left(n, Vector2(r.position.x, y))
	if bool(b.get("tilt", true)) and n is Node2D:
		var target: float = clamp(float(st["vy"]) * 0.15, -25.0, 80.0)
		n.rotation_degrees += (target - n.rotation_degrees) * min(1.0, dt * 12.0)


func _scroll(n: Node, b: Dictionary, dt: float) -> void:
	var dirs := {"left": Vector2(-1, 0), "right": Vector2(1, 0), "up": Vector2(0, -1), "down": Vector2(0, 1)}
	var dir: Vector2 = dirs.get(String(b.get("direction", "left")), Vector2(-1, 0))
	var r := rect_of(n)
	var p: Vector2 = r.position + dir * float(b.get("speed", 120)) * dt
	var origin: Vector2 = Vector2.ZERO if _in_ui(n) else _camera.position
	var gone := (dir.x < 0 and p.x + r.size.x < origin.x) or (dir.x > 0 and p.x > origin.x + view_size.x) or (dir.y < 0 and p.y + r.size.y < origin.y) or (dir.y > 0 and p.y > origin.y + view_size.y)
	if gone:
		var wr = b.get("wrap", false)
		if typeof(wr) != TYPE_BOOL and float(wr) > 1.0:
			p -= dir * float(wr)
		elif wr:
			var dist := 0.0
			for m in objects.values():
				if alive(m) and m.get_parent() == n.get_parent() and group_of(m) == group_of(n):
					dist += rect_of(m).size.x if dir.x != 0 else rect_of(m).size.y
			p -= dir * dist
		elif b.get("destroy", true):
			destroy(n)
			return
	set_top_left(n, p)


func _bounce(n: Node, b: Dictionary, dt: float) -> void:
	var st := state(n)
	if not st.has("init"):
		st["init"] = true
		st["vx"] = float(b.get("vx", 150))
		st["vy"] = float(b.get("vy", 150))
	var hit := move_and_collide_obj(n, Vector2(st["vx"], st["vy"]) * dt)
	var r := rect_of(n)
	if r.position.x < 0 or r.end.x > world_size.x:
		hit.x = 1
	if r.position.y < 0 or r.end.y > world_size.y:
		hit.y = 1
	_clamp_world(n)
	if hit.x != 0:
		st["vx"] = -st["vx"]
	if hit.y != 0:
		st["vy"] = -st["vy"]
	if hit != Vector2i.ZERO:
		_fire_object(n, "Bounce", [])


func _follow_mouse(n: Node, b: Dictionary, dt: float) -> void:
	var m := get_viewport().get_mouse_position()
	if not _in_ui(n):
		m += _camera.position
	var r := rect_of(n)
	var target := m - r.size / 2.0
	var speed: float = b.get("speed", 0)
	if speed <= 0:
		set_top_left(n, target)
	else:
		set_top_left(n, r.position.move_toward(target, speed * dt))


func _patrol(n: Node, b: Dictionary, dt: float) -> void:
	var st := state(n)
	var speed: float = b.get("speed", 80)
	var distance: float = b.get("distance", 160)
	var axis: String = b.get("axis", "x")
	var r := rect_of(n)
	if not st.has("dir"):
		st["dir"] = -1 if b.get("start_left", false) else 1
		st["origin"] = r.position.x if axis == "x" else r.position.y
	var d: int = st["dir"]
	var turn := false
	var pos := 0.0
	if axis == "y":
		var h := move_and_collide_obj(n, Vector2(0, d * speed * dt))
		turn = h.y != 0
		pos = rect_of(n).position.y
	else:
		if b.get("gravity", true) and float(settings.get("gravity", 900)) > 0:
			st["vy"] = min(st["vy"] + float(settings.get("gravity", 900)) * dt, 900.0)
			var hy := move_and_collide_obj(n, Vector2(0, st["vy"] * dt))
			if hy.y != 0:
				st["vy"] = 0.0
			st["on_ground"] = _standing(n)
		var hx := move_and_collide_obj(n, Vector2(d * speed * dt, 0))
		turn = hx.x != 0
		r = rect_of(n)
		pos = r.position.x
		if st["on_ground"] and b.get("turn_at_edges", true):
			var fx := r.end.x + 1 if d > 0 else r.position.x - 1
			if not is_solid_at(Vector2(fx, r.end.y + 2), n):
				turn = true
		_flip(n, d < 0)
		_anim(n, ["walk", "run"])
	if distance > 0 and abs(pos - st["origin"]) >= distance and (pos - st["origin"]) * d > 0:
		turn = true
	if turn:
		st["dir"] = -d


# ------------------------------------------------------------------ helpers for your code
func add_score(points: int = 1) -> void:
	score += points


func go_to_scene(scene_name: String) -> void:
	_pending_scene = scene_name


func restart_scene() -> void:
	_pending_scene = String(name)


func quit_game() -> void:
	_stop_sounds()
	get_tree().quit()


func _stop_sounds() -> void:
	# a sound still playing at exit would be reported by Godot as a leaked resource
	for p in get_tree().get_nodes_in_group("radgame_sound"):
		p.stop()
		p.stream = null


func play_sound(sound_id: String) -> void:
	if DisplayServer.get_name() == "headless":
		return    # no audio device; a playback still alive at exit is reported as a leak
	var path: String = settings.get("sounds", {}).get(sound_id, sound_id)
	if not ResourceLoader.exists(path):
		return
	var p := AudioStreamPlayer.new()
	p.stream = load(path)
	p.add_to_group("radgame_sound")
	add_child(p)
	p.finished.connect(p.queue_free)
	p.play()


func show_message(text: String, seconds: float = 2.0) -> void:
	_message.text = text
	_message.visible = true
	_message_until = game_time + seconds


func add_timer(timer_name: String, interval: float = 1000, enabled: bool = true) -> Dictionary:
	timers[timer_name] = {"name": timer_name, "interval": float(interval), "enabled": enabled, "acc": 0.0}
	return timers[timer_name]


func stop_timer(timer_name: String) -> void:
	if timers.has(timer_name):
		timers[timer_name]["enabled"] = false


func velocity(n: Node) -> Vector2:
	return Vector2(state(n)["vx"], state(n)["vy"])


func set_velocity(n: Node, v: Vector2) -> void:
	state(n)["vx"] = v.x
	state(n)["vy"] = v.y


# ------------------------------------------------------------------ object attributes (code translated from Python)
func getp(n, attr: String):
	# A radgame object attribute: x / y (top-left), w / h / width / height, right, bottom, center,
	# rotation (degrees), visible, group, name, text, vx, vy, alive, on_ground, props, data, z ...
	if n == null:
		return null
	if typeof(n) == TYPE_DICTIONARY:
		return n.get(attr)
	if not (n is Node) or not is_instance_valid(n):
		return null
	var r := rect_of(n)
	match attr:
		"x":
			return r.position.x
		"y":
			return r.position.y
		"w", "width":
			return r.size.x
		"h", "height":
			return r.size.y
		"right":
			return r.end.x
		"bottom":
			return r.end.y
		"center":
			return [r.get_center().x, r.get_center().y]
		"rotation":
			return n.rotation_degrees if n is Node2D else 0.0
		"visible":
			return n.visible
		"group":
			return group_of(n)
		"name":
			return String(n.name)
		"text":
			return String(n.get_meta("template", n.text)) if n is Label else ""
		"vx", "vy", "on_ground":
			if n.has_meta("rad_body") and attr != "on_ground" and n.get_meta("rad_body") is RigidBody2D:
				var lv: Vector2 = n.get_meta("rad_body").linear_velocity
				return lv.x if attr == "vx" else lv.y
			return state(n).get(attr, 0.0) if n.has_meta("rad_state") else 0.0
		"alive":
			return alive(n)
		"props":
			return n.get_meta("props", {})
		"data":
			if not n.has_meta("rad_data"):
				n.set_meta("rad_data", {})
			return n.get_meta("rad_data")
		"z":
			return n.z_index if n is CanvasItem else 0
		"flip_x":
			return n.flip_h if (n is Sprite2D or n is AnimatedSprite2D) else false
		"animation":
			return String(n.animation) if n is AnimatedSprite2D else ""
		"spawned", "template":
			return state(n).get(attr, false) if n.has_meta("rad_state") else false
		"emitting":
			var e = n.get_meta("rad_emitter", null)
			return e != null and is_instance_valid(e) and e.emitting
		"angular_velocity":
			if n.has_meta("rad_body") and n.get_meta("rad_body") is RigidBody2D:
				return rad_to_deg(n.get_meta("rad_body").angular_velocity)
			return 0.0
	if n.has_meta(attr):
		return n.get_meta(attr)
	return n.get(attr)


func setp(n, attr: String, v) -> void:
	if n == null:
		return
	if typeof(n) == TYPE_DICTIONARY:
		n[attr] = v
		if attr == "interval" and n.has("acc"):
			n["interval"] = float(v)
		return
	if not (n is Node) or not is_instance_valid(n):
		return
	var r := rect_of(n)
	match attr:
		"x":
			set_top_left(n, Vector2(float(v), r.position.y))
		"y":
			set_top_left(n, Vector2(r.position.x, float(v)))
		"w", "width", "h", "height":
			var s := r.size
			if attr in ["w", "width"]:
				s.x = max(1.0, float(v))
			else:
				s.y = max(1.0, float(v))
			if (n is Sprite2D or n is AnimatedSprite2D or n is Polygon2D) and r.size.x > 0 and r.size.y > 0:
				n.scale = Vector2(n.scale.x * s.x / r.size.x, n.scale.y * s.y / r.size.y)
			if n is Control:
				n.size = s
			n.set_meta("rad_size", s)
			set_top_left(n, r.position)
		"rotation":
			if n is Node2D:
				n.rotation_degrees = float(v)
				if n.has_meta("rad_body"):
					n.get_meta("rad_body").rotation = n.rotation
		"visible":
			n.visible = bool(v)
		"text":
			if n is Label:
				n.set_meta("template", str(v))
				n.text = str(v)
		"vx", "vy":
			if n.has_meta("rad_body") and n.get_meta("rad_body") is RigidBody2D:
				var b: RigidBody2D = n.get_meta("rad_body")
				b.linear_velocity = Vector2(float(v), b.linear_velocity.y) if attr == "vx" else Vector2(b.linear_velocity.x, float(v))
			elif n.has_meta("rad_state"):
				state(n)[attr] = float(v)
		"z":
			if n is CanvasItem:
				n.z_index = int(v)
		"flip_x":
			if n is Sprite2D or n is AnimatedSprite2D:
				n.flip_h = bool(v)
		"animation":
			play_anim(n, str(v))
		"emitting":
			var e = n.get_meta("rad_emitter", null)
			if e != null and is_instance_valid(e):
				e.emitting = bool(v)
		"angular_velocity":
			if n.has_meta("rad_body") and n.get_meta("rad_body") is RigidBody2D:
				n.get_meta("rad_body").angular_velocity = deg_to_rad(float(v))
		_:
			if n.has_meta(attr) or not (attr in n):
				n.set_meta(attr, v)
			else:
				n.set(attr, v)


func dict_pop(d: Dictionary, key, default_value = null):
	# Python's dict.pop(key, default): the value (or default) and the key is removed.
	var v = d.get(key, default_value)
	d.erase(key)
	return v


func show_obj(n) -> void:
	if n is Node and is_instance_valid(n):
		n.visible = true


func hide_obj(n) -> void:
	if n is Node and is_instance_valid(n):
		n.visible = false


func timer_start(t) -> void:
	if typeof(t) == TYPE_DICTIONARY and t.has("acc"):
		t["enabled"] = true
		t["acc"] = 0.0
	elif t is Node and t.has_meta("rad_emitter"):
		setp(t, "emitting", true)


func timer_stop(t) -> void:
	if typeof(t) == TYPE_DICTIONARY and t.has("acc"):
		t["enabled"] = false
	elif t is Node and t.has_meta("rad_emitter"):
		setp(t, "emitting", false)


func enable_behaviour_all(t: String, on: bool = true) -> void:
	# EnableBehaviour("scroll", False): switch a behaviour on / off for every object that has it.
	for n in objects.values():
		if alive(n):
			enable_behaviour(n, t, on)


func behaviour_enabled(n: Node, t: String) -> bool:
	var b := behaviour(n, t)
	return not b.is_empty() and b.get("enabled", true) != false


func move_to(n: Node, x: float, y: float) -> void:
	set_top_left(n, Vector2(x, y))


func distance_to(n: Node, other: Node) -> float:
	return rect_of(n).get_center().distance_to(rect_of(other).get_center())


func overlaps(n: Node, other: Node) -> bool:
	return alive(n) and alive(other) and hit_rect(n).intersects(hit_rect(other))


func contains(n: Node, x: float, y: float) -> bool:
	return rect_of(n).has_point(Vector2(x, y))


func play_anim(n: Node, anim_name: String, restart: bool = false) -> void:
	if n is AnimatedSprite2D and n.sprite_frames != null and n.sprite_frames.has_animation(anim_name):
		if restart or n.animation != anim_name or not n.is_playing():
			n.play(anim_name)


func has_animation(n: Node, anim_name: String) -> bool:
	return n is AnimatedSprite2D and n.sprite_frames != null and n.sprite_frames.has_animation(anim_name)


func play_music(sound_id: String, loop: bool = true) -> void:
	if DisplayServer.get_name() == "headless":
		return
	var path: String = settings.get("sounds", {}).get(sound_id, sound_id)
	if not ResourceLoader.exists(path):
		return
	stop_music()
	_music = AudioStreamPlayer.new()
	_music.stream = load(path)
	_music.add_to_group("radgame_sound")
	add_child(_music)
	if loop:
		_music.finished.connect(_music.play)
	_music.play()


func stop_music() -> void:
	if _music != null and is_instance_valid(_music):
		_music.stop()
		_music.queue_free()
	_music = null


func set_tile(layer_name: String, col: int, row: int, tile: int) -> void:
	# Change one cell of a tile layer while the game runs (-1 = empty).
	var tm = find_child(layer_name, true, false)
	if tm is TileMap:
		if tile < 0:
			tm.erase_cell(0, Vector2i(col, row))
		else:
			var src = tm.tile_set.get_source(0) if tm.tile_set != null else null
			var cols := 1
			if src is TileSetAtlasSource and src.texture != null:
				cols = max(1, int(src.texture.get_width() / src.texture_region_size.x))
			tm.set_cell(0, Vector2i(col, row), 0, Vector2i(tile % cols, tile / cols))


# ------------------------------------------------------------------ particles
func _is_pure_emitter(n: Node) -> bool:
	# An area that only emits particles does not collide (props collide=1 makes it a trigger again).
	return n.has_meta("particles") and not (n is Sprite2D or n is AnimatedSprite2D) and \
		str(n.get_meta("props", {}).get("collide", "")) == ""


func _effect(effect) -> Dictionary:
	if typeof(effect) == TYPE_DICTIONARY:
		return effect
	return settings.get("particles", {}).get(str(effect), {})


func _dot() -> Texture2D:
	# a soft round 16x16 dot for particles without a texture
	if _dot_texture == null:
		var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
		for py in range(16):
			for px in range(16):
				var d := Vector2(px + 0.5 - 8, py + 0.5 - 8).length() / 8.0
				img.set_pixel(px, py, Color(1, 1, 1, clamp(1.4 - d * 1.4, 0.0, 1.0)))
		_dot_texture = ImageTexture.create_from_image(img)
	return _dot_texture


func make_particles(effect) -> CPUParticles2D:
	# A CPUParticles2D set up from a particle effect of the scene (assets "particles").
	var e := _effect(effect)
	var p := CPUParticles2D.new()
	var life: float = max(0.05, float(e.get("lifetime", 1.0)))
	p.lifetime = life
	p.amount = int(clamp(float(e.get("rate", 30)) * life, 1.0, float(e.get("max", 500))))
	p.lifetime_randomness = clamp(float(e.get("lifetime_var", 0.0)) / life, 0.0, 1.0)
	p.direction = Vector2.from_angle(deg_to_rad(float(e.get("angle", -90))))
	p.spread = float(e.get("spread", 30))
	p.gravity = Vector2(float(e.get("gravity_x", 0)), float(e.get("gravity_y", 0)))
	var sp := float(e.get("speed", 100))
	var sv := float(e.get("speed_var", 0))
	p.initial_velocity_min = max(0.0, sp - sv)
	p.initial_velocity_max = sp + sv
	p.damping_min = float(e.get("damping", 0))
	p.damping_max = float(e.get("damping", 0))
	p.angular_velocity_min = float(e.get("spin", 0))
	p.angular_velocity_max = float(e.get("spin", 0))
	var tex: Texture2D = null
	var tid := str(e.get("texture", ""))
	var path: String = settings.get("images", {}).get(tid, "")
	if path != "" and ResourceLoader.exists(path):
		tex = load(path)
	elif str(e.get("shape", "circle")) == "circle":
		tex = _dot()
	p.texture = tex
	var base := 1.0
	if tex != null:
		base = float(max(1, tex.get_width()))
	var s0 := float(e.get("size_start", 8))
	var s1 := float(e.get("size_end", s0))
	p.scale_amount_min = s0 / base
	p.scale_amount_max = s0 / base
	if s0 > 0 and abs(s1 - s0) > 0.001:
		var c := Curve.new()
		c.max_value = max(1.0, s1 / s0)
		c.add_point(Vector2(0, 1))
		c.add_point(Vector2(1, s1 / s0))
		p.scale_amount_curve = c
	var g := Gradient.new()
	g.set_color(0, Color(str(e.get("color_start", "#FFFFFF"))))
	g.set_color(1, Color(str(e.get("color_end", e.get("color_start", "#FFFFFF")))))
	p.color_ramp = g
	var ew := float(e.get("emit_w", 0))
	var eh := float(e.get("emit_h", 0))
	if ew > 0 or eh > 0:
		p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
		p.emission_rect_extents = Vector2(ew / 2.0, eh / 2.0)
	if str(e.get("blend", "normal")) == "add":
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		p.material = m
	p.local_coords = false
	p.z_index = int(e.get("z", 0))
	return p


func _setup_emitters() -> void:
	for n in objects.values():
		if n.has_meta("particles") and not state(n).get("template", false):
			_attach_emitter(n)


func _attach_emitter(n: Node) -> void:
	var cfg = n.get_meta("particles")
	if typeof(cfg) != TYPE_DICTIONARY:
		cfg = {"effect": str(cfg)}
	var p := make_particles(cfg.get("effect", ""))
	p.emitting = bool(cfg.get("emitting", true)) and n.visible
	p.position = rect_of(n).get_center()
	n.get_parent().add_child(p)
	n.set_meta("rad_emitter", p)
	p.set_meta("rad_follow", n)
	_emitters.append(p)


func _update_emitters() -> void:
	var keep := []
	for p in _emitters:
		if not is_instance_valid(p):
			continue
		var n = p.get_meta("rad_follow", null)
		if n != null:
			if not is_instance_valid(n) or not alive(n):
				p.emitting = false
				p.remove_meta("rad_follow")
			else:
				p.position = rect_of(n).get_center()
		var until: float = p.get_meta("rad_until", -1.0)
		if until >= 0 and game_time >= until:
			p.emitting = false
			p.remove_meta("rad_until")
			get_tree().create_timer(p.lifetime + 0.2).timeout.connect(p.queue_free)
		keep.append(p)
	_emitters = keep


func emit_particles(effect, x = 0.0, y = 0.0, seconds = 0.0) -> CPUParticles2D:
	# Emit(effect, x, y, seconds): a stream of particles at (x, y) - or following an object
	# (emit_particles("smoke", Player)) - for seconds (0 = until stopped with stop_emitter).
	var p := make_particles(effect)
	var parent: Node = self
	if x is Node:
		seconds = y if typeof(y) != TYPE_NIL else 0.0
		p.position = rect_of(x).get_center()
		p.set_meta("rad_follow", x)
		parent = x.get_parent()
	else:
		p.position = Vector2(float(x), float(y))
	if float(seconds) > 0:
		p.set_meta("rad_until", game_time + float(seconds))
	parent.add_child(p)
	p.emitting = true
	_emitters.append(p)
	return p


func burst_particles(effect, x = 0.0, y = 0.0, count = 0) -> CPUParticles2D:
	# Burst(effect, x, y, n): n particles at once (an explosion, a coin sparkle).
	var e := _effect(effect)
	var p := make_particles(e)
	var where := Vector2(float(x), float(y)) if not (x is Node) else rect_of(x).get_center()
	if x is Node:
		count = y if typeof(y) != TYPE_NIL else 0
	var n := int(count) if int(count) > 0 else int(e.get("burst", 30))
	p.amount = max(1, n)
	p.one_shot = true
	p.explosiveness = 1.0
	p.position = where
	add_child(p)
	p.emitting = true
	get_tree().create_timer(p.lifetime + 0.3).timeout.connect(p.queue_free)
	return p


func emit_particles_from(n: Node, effect = "", seconds = 0.0) -> CPUParticles2D:
	if str(effect) == "" and n.has_meta("rad_emitter"):
		setp(n, "emitting", true)
		return n.get_meta("rad_emitter")
	return emit_particles(effect, n, seconds)


func burst_from(n: Node, effect = "", count = 0) -> CPUParticles2D:
	var eff = effect
	if str(eff) == "":
		var cfg = n.get_meta("particles", {})
		eff = cfg.get("effect", "") if typeof(cfg) == TYPE_DICTIONARY else str(cfg)
	return burst_particles(eff, n, count)


func stop_emitter(p) -> void:
	if p is Node and p.has_meta("rad_emitter"):
		p = p.get_meta("rad_emitter")
	if p is CPUParticles2D and is_instance_valid(p):
		p.emitting = false


# ------------------------------------------------------------------ physics (Godot's own 2D physics)
func _setup_physics() -> void:
	var ph: Dictionary = settings.get("physics", {})
	if not ph.get("enabled", false):
		return
	_physics_on = true
	var space := get_world_2d().space
	var gv := Vector2(float(ph.get("gravity_x", 0)), float(ph.get("gravity_y", settings.get("gravity", 900))))
	PhysicsServer2D.area_set_param(space, PhysicsServer2D.AREA_PARAM_GRAVITY, gv.length())
	PhysicsServer2D.area_set_param(space, PhysicsServer2D.AREA_PARAM_GRAVITY_VECTOR, gv.normalized() if gv.length() > 0 else Vector2.DOWN)
	for n in objects.values():
		if n.has_meta("physics") and not state(n).get("template", false):
			_make_body(n)
	if ph.get("tiles_static", true):
		for tm in find_children("*", "TileMap", true, false):
			if tm.get_meta("collision", false) and tm.tile_set != null:
				_tile_bodies(tm)
	for j in settings.get("joints", []):
		_make_joint(j)


func _make_body(n: Node) -> void:
	var p: Dictionary = n.get_meta("physics")
	var kind := str(p.get("body", "dynamic"))
	var body: PhysicsBody2D
	if kind == "static":
		body = StaticBody2D.new()
	elif kind == "kinematic":
		var ab := AnimatableBody2D.new()
		ab.sync_to_physics = false
		body = ab
	else:
		var rb := RigidBody2D.new()
		rb.mass = max(0.001, float(p.get("mass", 1)))
		rb.lock_rotation = bool(p.get("fixed_rotation", false))
		rb.gravity_scale = float(p.get("gravity_scale", 1))
		rb.linear_damp = float(p.get("damping", 0))
		rb.can_sleep = false
		rb.contact_monitor = false
		body = rb
	var mat := PhysicsMaterial.new()
	mat.friction = float(p.get("friction", 0.7))
	mat.bounce = float(p.get("elasticity", 0.2))
	if body is RigidBody2D or body is StaticBody2D:
		body.physics_material_override = mat
	var r := hit_rect(n)
	var cs := CollisionShape2D.new()
	var shape := str(p.get("shape", "box"))
	if shape == "circle":
		var c := CircleShape2D.new()
		c.radius = max(1.0, min(r.size.x, r.size.y) / 2.0)
		cs.shape = c
	elif shape == "poly" and p.get("points", []).size() >= 3:
		var full := rect_of(n)
		var pts := PackedVector2Array()
		for q in p["points"]:
			pts.append(Vector2(float(q[0]), float(q[1])) - full.size / 2.0)   # outline in object pixels
		var cp := ConvexPolygonShape2D.new()
		cp.set_point_cloud(pts)
		cs.shape = cp
	else:
		var rs := RectangleShape2D.new()
		rs.size = r.size
		cs.shape = rs
	if bool(p.get("sensor", false)):
		cs.disabled = false
	body.add_child(cs)
	body.position = rect_of(n).get_center()
	body.rotation = n.rotation if n is Node2D else 0.0
	body.name = "Body_" + String(n.name)
	add_child(body)
	n.set_meta("rad_body", body)
	if body is RigidBody2D:
		var st := state(n)
		body.linear_velocity = Vector2(float(p.get("vx", st.get("vx", 0.0))), float(p.get("vy", st.get("vy", 0.0))))


func _tile_bodies(tm: TileMap) -> void:
	var ts := Vector2(tm.tile_set.tile_size)
	var body := StaticBody2D.new()
	body.name = "Tiles_" + String(tm.name)
	var used: Array = tm.get_used_cells(0)
	var rows := {}
	for c in used:
		if not rows.has(c.y):
			rows[c.y] = []
		rows[c.y].append(c.x)
	for row in rows.keys():
		var xs: Array = rows[row]
		xs.sort()
		var start: int = xs[0]
		var prev: int = xs[0]
		for i in range(1, xs.size() + 1):
			if i < xs.size() and xs[i] == prev + 1:
				prev = xs[i]
				continue
			var cs := CollisionShape2D.new()
			var rs := RectangleShape2D.new()
			rs.size = Vector2((prev - start + 1) * ts.x, ts.y)
			cs.shape = rs
			cs.position = Vector2(start * ts.x + rs.size.x / 2.0, row * ts.y + ts.y / 2.0)
			body.add_child(cs)
			if i < xs.size():
				start = xs[i]
				prev = xs[i]
	add_child(body)


func _make_joint(j: Dictionary) -> void:
	var a: Node = find(str(j.get("a", "")))
	if a == null or not a.has_meta("rad_body"):
		return
	var ba: PhysicsBody2D = a.get_meta("rad_body")
	var bb: PhysicsBody2D = null
	var b: Node = find(str(j.get("b", ""))) if j.get("b", null) != null else null
	if b != null and b.has_meta("rad_body"):
		bb = b.get_meta("rad_body")
	if bb == null:
		bb = StaticBody2D.new()       # joined to the world
		bb.position = ba.position
		add_child(bb)
	var aa: Array = j.get("anchor_a", [0, 0])
	var ab: Array = j.get("anchor_b", [0, 0])
	var pa := ba.position + Vector2(float(aa[0]), float(aa[1]))
	var pb := bb.position + Vector2(float(ab[0]), float(ab[1]))
	if j.has("pivot"):
		pa = Vector2(float(j["pivot"][0]), float(j["pivot"][1]))
	var t := str(j.get("type", "pivot"))
	var joint: Joint2D
	if t == "spring" or t == "pin" or t == "rope":
		var sj := DampedSpringJoint2D.new()
		sj.position = pa
		sj.rotation = (pb - pa).angle() - PI / 2.0
		sj.length = max(1.0, pa.distance_to(pb))
		sj.rest_length = float(j.get("rest_length", pa.distance_to(pb)))
		# pymunk stiffness (force per pixel) -> Godot's 0..128 scale; pin / rope: as stiff as possible
		sj.stiffness = 128.0 if t != "spring" else clamp(float(j.get("stiffness", 200)) / 10.0, 1.0, 128.0)
		sj.damping = clamp(float(j.get("damping", 10)) / 10.0, 0.01, 16.0)
		joint = sj
	else:
		var pj := PinJoint2D.new()
		pj.position = pa
		pj.softness = float(j.get("softness", 0))
		joint = pj
	add_child(joint)
	joint.node_a = joint.get_path_to(ba)
	joint.node_b = joint.get_path_to(bb)
	joint.disable_collision = not bool(j.get("collide", false))


func _sync_bodies() -> void:
	if not _physics_on:
		return
	_syncing_bodies = true
	for n in objects.values():
		if not n.has_meta("rad_body"):
			continue
		var body = n.get_meta("rad_body")
		if not is_instance_valid(body):
			continue
		if not alive(n):
			body.queue_free()
			n.remove_meta("rad_body")
			continue
		if body is RigidBody2D:
			var s: Vector2 = n.get_meta("rad_size", Vector2(32, 32))
			set_top_left(n, body.position - s / 2.0)
			if n is Node2D:
				n.rotation = body.rotation
		else:
			_teleport_body(n)
	_syncing_bodies = false


func _teleport_body(n: Node) -> void:
	var body = n.get_meta("rad_body")
	if body == null or not is_instance_valid(body):
		return
	var c := rect_of(n).get_center()
	if body is RigidBody2D:
		PhysicsServer2D.body_set_state(body.get_rid(), PhysicsServer2D.BODY_STATE_TRANSFORM, Transform2D(body.rotation, c))
		body.position = c
	else:
		body.position = c
		if n is Node2D:
			body.rotation = n.rotation


func apply_impulse(n: Node, ix: float, iy: float) -> void:
	# ApplyImpulse(obj, ix, iy): a kick (mass x change of speed) to a dynamic body.
	var b = n.get_meta("rad_body", null) if n != null else null
	if b is RigidBody2D:
		b.apply_central_impulse(Vector2(ix, iy))


func apply_force(n: Node, fx: float, fy: float) -> void:
	var b = n.get_meta("rad_body", null) if n != null else null
	if b is RigidBody2D:
		b.apply_central_force(Vector2(fx, fy))


func set_body_velocity(n: Node, vx: float, vy: float) -> void:
	var b = n.get_meta("rad_body", null) if n != null else null
	if b is RigidBody2D:
		b.linear_velocity = Vector2(vx, vy)
	elif n != null and n.has_meta("rad_state"):
		set_velocity(n, Vector2(vx, vy))


# ------------------------------------------------------------------ auto-tiling at run time
func _tile_index(tm: TileMap, col: int, row: int) -> int:
	if tm.get_cell_source_id(0, Vector2i(col, row)) == -1:
		return -1
	var src = tm.tile_set.get_source(0)
	var cols := 1
	if src is TileSetAtlasSource and src.texture != null:
		cols = max(1, int(src.texture.get_width() / src.texture_region_size.x))
	var a := tm.get_cell_atlas_coords(0, Vector2i(col, row))
	return a.y * cols + a.x


func set_terrain(layer_name: String, col: int, row: int, terrain: String, on: bool = true) -> void:
	# SetTerrain: add / remove one cell of a terrain; it and its neighbours pick their edge tiles.
	var t: Dictionary = settings.get("terrains", {}).get(terrain, {})
	var tm = find_child(layer_name, true, false)
	if t.is_empty() or not (tm is TileMap):
		return
	var table: Dictionary = t.get("tiles", {})
	var tiles := {}
	for v in table.values():
		tiles[int(v)] = true
	var blob := str(t.get("mode", "47")) == "47"
	var full := int(table.get("255" if blob else "15", table.values()[0] if table.size() > 0 else 0))
	set_tile(layer_name, col, row, full if on else -1)
	var dirs := [[0, -1, 1], [1, -1, 2], [1, 0, 4], [1, 1, 8], [0, 1, 16], [-1, 1, 32], [-1, 0, 64], [-1, -1, 128]]
	var used: Rect2i = tm.get_used_rect()
	var edge := bool(t.get("edge", true))
	for dr in [-1, 0, 1]:
		for dc in [-1, 0, 1]:
			var c: int = col + dc
			var r: int = row + dr
			if not tiles.has(_tile_index(tm, c, r)):
				continue
			var m := 0
			for d in dirs:
				var cc: int = c + d[0]
				var rr: int = r + d[1]
				var inside := used.has_point(Vector2i(cc, rr))
				if (inside and tiles.has(_tile_index(tm, cc, rr))) or (not inside and edge):
					m |= d[2]
			var k := 0
			if blob:
				k = m & 85
				for cs in [[2, 1, 4], [8, 16, 4], [32, 16, 64], [128, 1, 64]]:
					if m & cs[0] and m & cs[1] and m & cs[2]:
						k |= cs[0]
			else:
				k = (1 if m & 1 else 0) | (2 if m & 4 else 0) | (4 if m & 16 else 0) | (8 if m & 64 else 0)
			set_tile(layer_name, c, r, int(table.get(str(k), full)))
