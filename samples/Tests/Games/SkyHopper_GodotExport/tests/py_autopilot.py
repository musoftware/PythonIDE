"""Plays samples/SkyHopper (pygame radgame) with the same autopilot as autopilot.gd and prints the same lines.
    python tests/py_autopilot.py ../../../SkyHopper   (the best score goes to a temp file, not the sample)"""
import os, sys
sys.dont_write_bytecode = True      # leave no __pycache__ in the game folder
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
folder = sys.argv[1]
import tempfile; os.environ["RADGAME_SAVE"] = os.path.join(tempfile.gettempdir(), "skyhopper_autopilot_save.json")
sys.path.insert(0, folder)
import radgame
g = radgame.Game(folder, "t", headless=True)
g.load_scene("Scene1")
mod = g.module
goal = int(os.environ.get("AP_SCORE", "3"))
phase, release_at, f, over_at, max_score = "start", -1, 0, 0, 0
scene_obj = g.scene
print(f"PY scene loaded frame 0 state={mod.state} title_visible={g.scene.objects['TitleText'].visible}")
while f < 3000:
    f += 1
    if g.scene is not scene_obj:
        scene_obj = g.scene; mod = g.module
        print(f"PY scene reloaded frame {f} score={g.score} state={mod.state} title_visible={g.scene.objects['TitleText'].visible}")
    if release_at == f:
        g.input.release("space")
    p = g.scene.objects["Player"]
    if g.score > max_score:
        max_score = g.score; print(f"PY score {g.score} at frame {f}")
    def tap():
        global release_at
        g.input.press("space"); release_at = f + 2
    if phase == "start" and f == 20:
        tap(); phase = "play"
    elif phase == "play":
        if mod.state == "over":
            print(f"PY game over at frame {f} score={g.score} best={g.vars.get('best')} result={g.scene.objects['ResultText'].display_text()!r}")
            phase, over_at = "over", f
        else:
            target = 280.0
            if g.score < goal:
                bx = 1e9
                for gp in radgame.FindGroup("PillarBottom"):
                    r = gp.hit_rect
                    if r.right > p.x and r.left < bx:
                        bx = r.left; target = r.top - 45
            else:
                target = 1000
            if p.center[1] > target and p.vy > -50 and release_at < f:
                tap()
    elif phase == "over" and f == over_at + 90:
        tap(); phase = "restarted"
    elif phase == "restarted" and f == over_at + 130:
        print(f"PY after restart frame {f} score={g.score} state={mod.state}"); break
    g.step(1 / 60)
