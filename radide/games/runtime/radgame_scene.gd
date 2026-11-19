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
extends Node2D

static var score := 0
static var lives := 3
static var vars := {}

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


func set_top_left(n: Node, p: Vector2) -> void:
	var s: Vector2 = n.get_meta("rad_size", Vector2(32, 32))
	if n.get_meta("rad_centered", false) and not (n is Control):
		n.position = p + s / 2.0
	else:
		n.position = p


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
	var t: Node = find(template_name)
	if t == null:
		return null
	var c: Node = t.duplicate()
	_spawn_n += 1
	c.name = "%s_%d" % [template_name, _spawn_n]
	t.get_parent().add_child(c)
	var bs: Array = []
	for d in t.get_meta("behaviours", []):
		bs.append(d.duplicate())
	c.set_meta("behaviours", bs)
	c.set_meta("rad_state", {"vx": 0.0, "vy": 0.0, "on_ground": false, "alive": true, "spawned": true})
	c.set_meta("group", group_of(t))
	c.visible = true
	objects[String(c.name)] = c
	set_top_left(c, Vector2(x, y))
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
		if frame == tk[1]:
			_press(tk[0])
		elif frame == tk[2]:
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
	_collisions()
	_fire_scene("Update", [dt])
	_update_camera()
	_update_labels()
	if _message.visible and game_time > _message_until:
		_message.visible = false
	pressed.clear()
	_clicked = false
	frame += 1
	game_time += dt
	if _pending_scene != "":
		var target := _pending_scene
		_pending_scene = ""
		get_tree().change_scene_to_file("res://" + target + ".tscn")
		return
	if _test_frames > 0 and frame >= _test_frames:
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
		if alive(n) and not _in_ui(n) and not (n is Label):
			list.append(n)
	var now := {}
	for i in range(list.size()):
		var ra := rect_of(list[i])
		for j in range(i + 1, list.size()):
			if ra.intersects(rect_of(list[j])):
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


func add_timer(timer_name: String, interval: float = 1000, enabled: bool = true) -> void:
	timers[timer_name] = {"name": timer_name, "interval": float(interval), "enabled": enabled, "acc": 0.0}


func stop_timer(timer_name: String) -> void:
	if timers.has(timer_name):
		timers[timer_name]["enabled"] = false


func velocity(n: Node) -> Vector2:
	return Vector2(state(n)["vx"], state(n)["vy"])


func set_velocity(n: Node, v: Vector2) -> void:
	state(n)["vx"] = v.x
	state(n)["vy"] = v.y
