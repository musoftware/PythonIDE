"""Game blocks of the tutorials (guide "games"): pygame-ce projects made like New Project > Games, run headless.

Block kinds:

* ```` ```game run ````   the code file of a scene (``Scene1.py`` / ``Level1.py``: VB-style handlers such as
                          ``Scene_Load()``, ``Player_Collide(other)``, ``Scene_KeyDown(key)``) -> a "Python Game
                          (pygame)" project.  The two import lines the IDE writes at the top of every scene file
                          (``from radgame import *`` / ``from <Scene>_designer import *``) may be left out of the
                          block; they are added when missing.
* ``game exercise`` / ``game solution``   as for the other courses.

Hidden ``<!-- test: {...} -->`` keys (make_project and check use them):
  ``template``  platformer | topdown | empty (default) | sample:SkyHopper (a copy of samples/SkyHopper)
  ``objects``   extra objects for the scene: [{"name": "Ball", "kind": "sprite", "x": 100, "y": 50, "w": 32,
                "h": 32, "behaviours": [{"type": "bounce"}], "layer": "Sprites", ...}] (the scene designer's
                JSON, radide/games/model.py)
  ``scene``     scene keys to change, e.g. {"gravity": 0, "background": "#202040"}
  ``frames``    how many frames to run (default 60 = one second at 60 fps; fixed time step)
  ``keys``      keys held between frames, e.g. "right:5-90,space:40-44" (RADGAME_KEYS)
  ``seed``      random seed (default 1) so Random() gives the same numbers every run
  ``error``     text expected in the error output (an example that crashes on purpose)
print() output of the handlers is the block's output (```text output).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
REPO = Path(__file__).resolve().parents[2]
SCENES = {"platformer": "Level1", "topdown": "Room1", "empty": "Scene1"}
RUNNER = ("import random, runpy, sys; random.seed(int(sys.argv[1])); sys.argv = ['main.py']; "
          "runpy.run_path('main.py', run_name='__main__')")


def scene_name(spec: dict) -> str:
    t = str((spec or {}).get("template") or "empty")
    if t.startswith("sample:"):
        sample = REPO / "samples" / t[7:]
        try:
            data = json.loads((sample / "project.radproj").read_text(encoding="utf-8"))
            return data.get("game", {}).get("start_scene") or data.get("scenes", ["Scene1"])[0]
        except (OSError, ValueError):
            return "Scene1"
    return SCENES.get(t, "Scene1")


def with_imports(code: str, scene: str) -> str:
    if re.search(r"^\s*from\s+radgame\s+import", code, re.M):
        return code
    head = (f'"""{scene} - the code of the scene."""\n'
            "from radgame import *  # noqa: F401,F403 - the game helpers\n"
            f"from {scene}_designer import *  # noqa: F401,F403 - the objects of the scene\n\n")
    return head + code.lstrip("\n")


def make_project(files: dict[str, str], spec: dict | None, dest: Path, name: str = "Lesson"):
    """A pygame game project in *dest* (already empty); the block's code is the start scene's file."""
    from ..games import codegen
    from ..games.templates import create_game_project
    from ..model import Project
    spec = dict(spec or {})
    dest = Path(dest)
    template = str(spec.get("template") or "empty")
    scene = scene_name(spec)
    if template.startswith("sample:"):
        src = REPO / "samples" / template[7:]
        for p in src.iterdir():
            if p.name in ("__pycache__", "savegame.json") or p.name.startswith("_rad"):
                continue
            (shutil.copytree if p.is_dir() else shutil.copy2)(p, dest / p.name)
        project = Project.load(dest)
        project.name = name
    else:
        project = create_game_project(dest, name, "pygame", template)
    sp = dest / f"{scene}.scene"
    data = json.loads(sp.read_text(encoding="utf-8"))
    data.update(spec.get("scene") or {})
    for obj in spec.get("objects") or []:
        obj = dict(obj)
        lname = obj.pop("layer", None)
        layers = [ly for ly in data["layers"] if (ly["name"] == lname if lname else
                                                  ly["type"] == ("ui" if obj.get("kind") == "text" and
                                                                 obj.get("ui") else "sprites"))]
        layer = layers[0] if layers else data["layers"][0]
        obj.pop("ui", None)
        base = {"name": obj.get("name", "Object1"), "kind": "sprite", "x": 0, "y": 0, "w": 32, "h": 32,
                "scale": 1, "rotation": 0, "z": 0, "visible": True, "behaviours": [], "props": {}}
        base.update(obj)
        layer.setdefault("objects", []).append(base)
    sp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for fname, text in files.items():
        target = f"{scene}.py" if fname in ("Scene.py", f"{scene}.py") or len(files) == 1 else fname
        (dest / target).write_text(with_imports(text, scene) if target == f"{scene}.py" else text, encoding="utf-8")
        if target not in project.modules:
            project.modules.append(target)
    codegen.sync_project(dest)
    project.save()
    return project


def run_game(folder: Path, spec: dict | None, timeout: int = 60) -> tuple[bool, str, str]:
    """Run the game headless (SDL dummy drivers, fixed time step).  (finished, stdout, stderr)."""
    from ..games import codegen
    spec = dict(spec or {})
    folder = Path(folder)
    codegen.sync_project(folder)
    save = folder / "_radtut_save.json"
    if save.exists():
        save.unlink()
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYTHONUNBUFFERED="1",
               PYTHONIOENCODING="utf-8", RADGAME_FIXED_DT="1", RADGAME_FRAMES=str(int(spec.get("frames", 60))),
               RADGAME_KEYS=str(spec.get("keys", "")), RADGAME_SAVE=str(save), PYGAME_HIDE_SUPPORT_PROMPT="1")
    try:
        r = subprocess.run([sys.executable, "-c", RUNNER, str(int(spec.get("seed", 1)))], cwd=str(folder), env=env,
                           capture_output=True, timeout=spec.get("timeout", timeout), creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return False, "", "<<انتهت المهلة: هل في الكود حلقة لا تنتهي؟>>"
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    return r.returncode == 0, out, err


def _short_error(err: str) -> str:
    lines = [ln for ln in err.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    keep = [ln for ln in lines if ln.lstrip().startswith("File ") and "radgame" not in ln and "runpy" not in ln
            and "<string>" not in ln]
    return ((keep[-1].strip() + "\n") if keep else "") + lines[-1]


def check(block, code, folder, work: Path, norm, CheckResult):
    """The "تحقق" button / the course checker for a game block."""
    from . import _clean, block_files
    target = block.check_target()
    spec = dict(target.spec or {})
    if folder:
        work = Path(folder)
    else:
        _clean(work)
        make_project(block_files(block, code), spec, work)
    ok, out, err = run_game(work, spec)
    problems = []
    want_err = spec.get("error")
    if want_err:
        if want_err not in err:
            problems.append(f"كان متوقعًا الخطأ: {want_err}")
    elif not ok:
        problems.append("توقفت اللعبة بخطأ: " + (_short_error(err) or "(بلا رسالة)"))
    expected = target.expected
    if expected is not None and norm(out) != norm(expected):
        problems.append("المخرجات لا تطابق المطلوب")
    if expected is None and not problems:
        return CheckResult(True, out, None, [], "تعمل اللعبة بلا أخطاء. اضغط «جرّبه» لتلعبها بنفسك.")
    if want_err and err:
        out += ("\n" if out else "") + _short_error(err)
    return CheckResult(not problems, out, expected, problems)


__all__ = ["check", "make_project", "run_game", "scene_name", "with_imports"]
