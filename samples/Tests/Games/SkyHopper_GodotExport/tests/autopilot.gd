# Test-only autoload: plays SkyHopper (taps when Glim sinks below the next gap), then crashes on purpose,
# restarts and reports. Prints AUTOPILOT lines.
extends Node

var f := 0
var phase := "start"
var release_at := -1
var crash_after := 0
var loads := 0
var last_scene: Node = null
var max_score := 0

func _ready() -> void:
	crash_after = int(OS.get_environment("AP_SCORE")) if OS.get_environment("AP_SCORE") != "" else 3

func tap(sc) -> void:
	sc._press("space")
	release_at = f + 2

func _physics_process(_dt: float) -> void:
	f += 1
	var sc = get_tree().current_scene
	if sc == null or not sc.has_method("getp"):
		return
	if sc != last_scene:
		last_scene = sc
		loads += 1
		print("AUTOPILOT scene loaded #%d frame %d score=%d state=%s title_visible=%s" % [loads, f, sc.score, sc.state_, sc.find("TitleText").visible])
	if release_at == f:
		sc._release("space")
	var p = sc.find("Player")
	if p == null:
		return
	if sc.score > max_score:
		max_score = sc.score
		print("AUTOPILOT score %d at frame %d (gates alive %d)" % [sc.score, f, sc.find_group("PillarTop").size()])
	if phase == "start" and f == 20:
		tap(sc)
		phase = "play"
		return
	if phase == "play":
		if sc.state_ == "over":
			print("AUTOPILOT game over at frame %d score=%d best=%s gameover_visible=%s result='%s'" % [f, sc.score, str(sc.vars.get("best")), sc.find("GameOverText").visible, sc.find("ResultText").text])
			phase = "over"
			crash_after = f
			return
		var target := 280.0
		if sc.score < int(OS.get_environment("AP_SCORE") if OS.get_environment("AP_SCORE") != "" else "3"):
			var best_x := 99999.0
			for g in sc.find_group("PillarBottom"):
				var r: Rect2 = sc.hit_rect(g)
				if r.end.x > sc.getp(p, "x") and r.position.x < best_x:
					best_x = r.position.x
					target = r.position.y - 45
		else:
			target = 1000.0     # stop flapping: fall and crash
		var cy: float = sc.rect_of(p).get_center().y
		if cy > target and sc.state(p)["vy"] > -50 and release_at < f:
			tap(sc)
	elif phase == "over" and f == crash_after + 90:
		tap(sc)
		phase = "restarted"
	elif phase == "restarted" and f == crash_after + 130:
		print("AUTOPILOT after restart frame %d score=%d state=%s title_visible=%s loads=%d" % [f, sc.score, sc.state_, sc.find("TitleText").visible, loads])
		get_tree().quit()
