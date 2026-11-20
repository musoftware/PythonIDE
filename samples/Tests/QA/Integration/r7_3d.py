"""QA: Ursina + Godot 3D 'playground3d' templates created, opened in the IDE, run headless (Ctrl+F5 in the IDE for
Ursina with RAD3D_HEADLESS=1; Godot through its run_spec with --headless)."""
import os, shutil, subprocess
os.environ.setdefault("QA_NAME", "iqa_3d")
os.environ.update(RAD3D_HEADLESS="1", RAD3D_FRAMES="150", RAD3D_KEYS="w:5-120")
from qh import *  # noqa
from pathlib import Path
from radide.languages import get_plugin
w = window()
for pid in ("python-ursina", "godot3d"):
    folder = Path(WORK) / "g3d" / pid; shutil.rmtree(folder, ignore_errors=True)
    p = get_plugin(pid)
    p.create_new_project(folder, "Qa3D", "playground3d")
    w.open_project(folder, ask=False); pump(3)
    check(f"{pid}: project opened", w.project is not None and w.project.language == pid, w.project and w.project.language)
    scene = next(folder.rglob("*.scene3d"), None)
    check(f"{pid}: .scene3d present", scene is not None)
    if pid == "python-ursina":
        w.output.clear(); w.run_project(debug=False)
        ok = wait(lambda: w.session is None, 240)
        out = w.output.toPlainText()
        print("URSINA OUTPUT tail:\n" + out[-800:])
        check(f"{pid}: headless run via IDE finished", ok, out[-300:])
        check(f"{pid}: game loop ran (rad3d-test lines)", "rad3d-test" in out, out[-400:])
        check(f"{pid}: no Traceback", "Traceback" not in out, out[-600:])
    else:
        exe = p.find_interpreter("")
        check(f"{pid}: Godot found", bool(exe), exe)
        if exe:
            spec = p.run_spec(folder, "main", exe)
            args = ["--headless", "--fixed-fps", "60"] + list(spec.args)
            env = dict(spec.env or os.environ)
            r = subprocess.run([spec.program] + args, cwd=spec.cwd, env=env, capture_output=True, text=True, timeout=240)
            lines = [l for l in r.stdout.splitlines() if "rad3d-test" in l]
            print("GODOT rc", r.returncode, lines[:6], r.stderr[-400:])
            check(f"{pid}: headless Godot run exits 0 with test lines", r.returncode == 0 and lines, (r.returncode, r.stdout[-300:]))
    pump(1); shot(w, f"ide3d_{pid}")
finish(w)
