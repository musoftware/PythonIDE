"""Ring Game (RingRayLib) - game projects in Ring played with raylib (CONTRACTS 10.2 / 10.4).

The scenes are the same ``<Scene>.scene`` files as the pygame / HTML5 / Godot games (scene designer, ``is_game``);
their code is ``<Scene>.ring`` with VB-style handlers (``func Player_Collide oOther``).  F5 runs ``main.ring``
(which loads radgame.ring + every scene) - with the Ring debug agent (raddbg.ring: breakpoints, stepping,
locals) like any Ring program.  RingRayLib ships with Ring (C:\\ring\\ring\\bin\\ring_raylib.dll).
"""
from __future__ import annotations

import os
from pathlib import Path

from ..games import codegen, ring_game
from ..model import Form, Project
from .base import RunSpec
from .ring_qt import AGENT, RingQtPlugin

DEBUG_MAIN = "_raddbg_game.ring"
RING_HELPERS = {"AddScore": "AddScore(points)", "RestartScene": "RestartScene()", "GoToScene": "GoToScene(name)",
                "Quit": "Quit()", "ShowMessage": "ShowMessage(text, seconds)", "PlayGameSound": "PlayGameSound(id)",
                "IsKeyHeld": 'IsKeyHeld("left") -> true/false', "FindObject": "FindObject(name) -> object",
                "FindGroup": 'FindGroup("Coin") -> list of names', "AddTimer": "AddTimer(name, ms)",
                "StopTimer": "StopTimer(name)"}


class RingGamePlugin(RingQtPlugin):
    id = "ring-game"
    display_name = "Ring Game (RingRayLib)"
    code_ext = ".ring"
    is_game = True
    scene_ext = ".scene"
    supports_debug = True
    project_name_base = "Game"

    def raylib_found(self, interpreter: str = "") -> bool:
        exe = interpreter or self.find_interpreter("")
        return bool(exe) and (Path(exe).parent / "ring_raylib.dll").exists()

    # ------------------------------------------------------------ New Project (Games group)
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from ..games.templates import templates_for
        return [(t.id, (t.title if t.id != "empty" else "Empty Game") + " (Ring)", t.description, t.icon)
                for t in templates_for("pygame")]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        first, scenes = ring_game.create_files(folder, name, template or "platformer", name)
        extra = {"scenes": scenes, "game": {"title": name, "start_scene": first}}
        project = Project(folder, name, self.id, [], "main", ["main.ring"] + [f"{s}.ring" for s in scenes],
                          extra=extra)
        project.save()
        return project

    # ------------------------------------------------------------ forms (a game project has none)
    def generate_designer(self, form: Form, user_code: str) -> str:
        return f"# {form.name}: forms are not used by Ring game projects - add a scene instead.\n"

    def new_code(self, form: Form, is_startup: bool) -> str:
        return ring_game.new_scene_code({"name": form.name})

    # ------------------------------------------------------------ scenes
    def scene_code_file(self, scene: str) -> str:
        return f"{scene}.ring"

    def scene_designer_file(self, scene: str) -> str:
        return f"{scene}_designer.ring"

    def new_scene_code(self, scene) -> str:
        return ring_game.new_scene_code(scene)

    def generate_scene_designer(self, scene) -> str:
        return ring_game.designer_code(scene)

    def on_scene_saved(self, folder: Path, scene: str) -> list[Path]:
        return ring_game.sync_project(Path(folder))

    def scene_handler(self, obj_name: str | None, event: str) -> str:
        return codegen.handler_name(obj_name, event)

    def add_scene_handler(self, code: str, obj_name: str | None, event: str) -> tuple[str, int]:
        name = codegen.handler_name(obj_name, event)
        line = ring_game.find_handler(code, name)
        if line >= 0:
            return code, line + 1
        return ring_game.add_handler(code, name)

    # ------------------------------------------------------------ handlers
    def find_handler(self, code: str, name: str) -> int:
        return ring_game.find_handler(code, name)

    def add_handler(self, code: str, name: str, form: Form | None = None, args: str | None = None):
        return ring_game.add_handler(code, name, args)

    def module_template(self, name: str) -> str:
        return (f"# {name} - shared game code (Ring). Load it from _scenes.ring's scenes or main.ring:\n"
                f'#     load "{name}.ring"\n')

    # ------------------------------------------------------------ completion
    def completions(self, code, line, col, path, names=None):
        from .base import Completion
        out = super().completions(code, line, col, path, names)
        have = {c.name.lower() for c in out}
        return [Completion(k, "function", v) for k, v in RING_HELPERS.items() if k.lower() not in have] + out

    # ------------------------------------------------------------------ run
    def _prepare(self, folder: Path) -> None:
        ring_game.sync_project(folder)

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        folder = Path(folder)
        self._prepare(folder)
        return RunSpec(interpreter, ["main.ring"], folder)

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        folder = Path(folder)
        self._prepare(folder)
        agent = str(AGENT).replace("\\", "/")
        (folder / DEBUG_MAIN).write_text(f"# generated by RAD IDE - safe to delete\nload \"{agent}\"\n"
                                         f"load \"main.ring\"\n", encoding="utf-8")
        env = dict(os.environ, RADDBG_BP=self.breakpoints_env(breakpoints))
        return RunSpec(interpreter, [DEBUG_MAIN], folder, env)


PLUGIN = RingGamePlugin()
