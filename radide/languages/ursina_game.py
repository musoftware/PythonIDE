"""Python 3D (Ursina) - 3D game projects for the Ursina engine (round 7, radide/games3d/).

A thin plugin like python-arcade: the code is plain Python (main.py), the scene is ``Scene1.scene3d`` edited in
the 3D scene view (radide/games3d/editor.py) and generated into ``Scene1_designer.py`` before every run.
The id starts with "python" so the IDE treats the project as Python (.venv, debugpy).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from ..model import Form, Project
from .base import RunSpec
from .python_tk import PythonTkPlugin


class UrsinaPlugin(PythonTkPlugin):
    id = "python-ursina"
    display_name = "Python 3D (Ursina)"
    code_ext = ".py"
    supports_debug = True
    project_name_base = "Game3D"
    scene3d = True                    # .scene3d files open in the 3D scene view

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        if importlib.util.find_spec("ursina") is not None:
            return sys.executable
        return super().find_interpreter(configured)

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from ..games3d.templates import TEMPLATES
        return list(TEMPLATES[self.id])

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..games3d.templates import create_project
        return create_project(Path(folder), name, self.id, template or "playground3d")

    def module_template(self, name: str) -> str:
        return f'"""{name} - shared game code (import {name} from main.py)."""\nfrom ursina import *  # noqa: F401,F403\n'

    def add_handler(self, code: str, name: str, form: Form | None = None, args: str | None = None):
        if isinstance(form, Form) and self._find_line(code, r"^class\s+\w+") >= 0:
            return super().add_handler(code, name, form, args)
        lines = code.rstrip("\n").splitlines()
        tail = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].startswith("rad3d.run(")), len(lines))
        new = ["", "", f"def {name}({args or ''}):", "    pass", ""]
        lines[tail:tail] = new
        return "\n".join(lines) + "\n", tail + 3

    def _prepare(self, folder: Path) -> None:
        from ..games3d import ursina_gen
        ursina_gen.sync_project(Path(folder))

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        folder = Path(folder)
        self._prepare(folder)
        main = "main.py" if (folder / "main.py").exists() else self.code_file(startup_form or "main")
        return RunSpec(interpreter, ["-u", main], folder, dict(os.environ, PYTHONUNBUFFERED="1"))

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        self._prepare(Path(folder))
        return super().debug_spec(folder, "main", interpreter, breakpoints)


PLUGIN = UrsinaPlugin()
