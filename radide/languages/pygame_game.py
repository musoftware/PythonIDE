"""Python Game (pygame-ce) - game projects with scenes (CONTRACTS 10.2 / 10.4).

A game project has no forms: its scenes (``<Scene>.scene``) are edited in the scene designer
(``is_game = True``), the code of a scene is ``<Scene>.py`` with VB-style handlers
(``Scene_Load``, ``Player_Collide(other)`` ...) and F5 runs ``main.py`` which starts
``radgame.run(<first scene>)``. Before every run the generated ``<Scene>_designer.py`` files and the
runtime ``radgame.py`` are refreshed (radide/games/codegen.py).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from ..games import codegen
from ..model import Form, Project
from .base import RunSpec
from .python_tk import PythonTkPlugin


class PygamePlugin(PythonTkPlugin):
    id = "pygame"
    display_name = "Python Game (pygame)"
    code_ext = ".py"
    is_game = True
    supports_debug = True
    uses_debugpy = True          # F5 debugs the game with debugpy like other Python projects (app._make_session)
    scene_ext = ".scene"

    # ------------------------------------------------------------ interpreter
    def find_interpreter(self, configured: str = "") -> str:
        """The configured Python, else the IDE's own Python when it has pygame, else python on PATH."""
        if configured and Path(configured).exists():
            return configured
        if importlib.util.find_spec("pygame") is not None:
            return sys.executable
        return super().find_interpreter(configured)

    # ------------------------------------------------------------ New Project (Games group)
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        """(id, title, description, icon) for the New Project dialog."""
        from ..games.templates import templates_for
        return [(t.id, t.title, t.description, t.icon) for t in templates_for(self.id)]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..games.templates import create_game_project
        return create_game_project(Path(folder), name, self.id, template or "platformer")

    # ------------------------------------------------------------ scenes
    def scene_code_file(self, scene: str) -> str:
        return f"{scene}.py"

    def scene_designer_file(self, scene: str) -> str:
        return f"{scene}_designer.py"

    def new_scene_code(self, scene) -> str:
        """User file of a new scene (*scene*: radide.games.model.Scene, dict or path)."""
        return codegen.new_scene_code(scene)

    def generate_scene_designer(self, scene) -> str:
        return codegen.designer_code(scene)

    def on_scene_saved(self, folder: Path, scene: str) -> list[Path]:
        """Call after saving ``<scene>.scene``: rewrites the designer file (object names)."""
        return codegen.sync_scene(Path(folder), scene)

    def scene_handler(self, obj_name: str | None, event: str) -> str:
        return codegen.handler_name(obj_name, event)

    def add_scene_handler(self, code: str, obj_name: str | None, event: str) -> tuple[str, int]:
        """Insert ``def <Obj>_<Event>(args):`` if missing. Returns (code, 0-based line of its body)."""
        name = codegen.handler_name(obj_name, event)
        line = codegen.find_handler(code, name)
        if line >= 0:
            return code, line + 1
        return codegen.add_handler(code, name)

    # ------------------------------------------------------------ handlers (module-level functions)
    def find_handler(self, code: str, name: str) -> int:
        line = codegen.find_handler(code, name)
        return line if line >= 0 else super().find_handler(code, name)

    def add_handler(self, code: str, name: str, form: Form | None = None, args: str | None = None):
        if isinstance(form, Form) and self._find_line(code, r"^class\s+\w+") >= 0:
            return super().add_handler(code, name, form, args)      # a Tk form inside a game project
        return codegen.add_handler(code, name, None)

    def module_template(self, name: str) -> str:
        return (f'"""{name} - shared game code (import it from a scene: import {name})."""\n'
                "from radgame import *  # noqa: F401,F403\n")

    # ------------------------------------------------------------------ run
    def _prepare(self, folder: Path) -> None:
        codegen.sync_project(folder)

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        folder = Path(folder)
        self._prepare(folder)
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        main = "main.py" if (folder / "main.py").exists() else self.code_file(startup_form or "main")
        return RunSpec(interpreter, ["-u", main], folder, env)

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        self._prepare(Path(folder))
        return super().debug_spec(folder, startup_form or "main", interpreter, breakpoints)


PLUGIN = PygamePlugin()
