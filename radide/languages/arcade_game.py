"""Python Arcade - game projects written for the `arcade` library (CONTRACTS 10.2, "Python Arcade optional").

A thin plugin: the projects are plain Python (main.py with an ``arcade.Window``), made from the templates in
radide/games/arcade_templates.py.  There is no scene designer for them (the scene designer drives the pygame,
HTML5 and Godot runtimes); F5 debugs main.py like any Python program (debugpy / pyagent - the plugin id
starts with "python" so the IDE treats it as Python: .venv, debugpy, real python.exe).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from ..model import Form, Project
from .base import RunSpec
from .python_tk import PythonTkPlugin


class ArcadePlugin(PythonTkPlugin):
    id = "python-arcade"
    display_name = "Python Arcade (arcade library)"
    code_ext = ".py"
    supports_debug = True
    project_name_base = "Game"

    def find_interpreter(self, configured: str = "") -> str:
        """The configured Python, else the IDE's own Python when it has arcade, else python on PATH."""
        if configured and Path(configured).exists():
            return configured
        if importlib.util.find_spec("arcade") is not None:
            return sys.executable
        return super().find_interpreter(configured)

    # ------------------------------------------------------------ New Project (Games group)
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from ..games.arcade_templates import TEMPLATES
        return list(TEMPLATES)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..games.arcade_templates import create_project
        return create_project(Path(folder), name, self.id, template or "platformer")

    def module_template(self, name: str) -> str:
        return f'"""{name} - shared game code (import {name} from main.py)."""\nimport arcade  # noqa: F401\n'

    def add_handler(self, code: str, name: str, form: Form | None = None, args: str | None = None):
        if isinstance(form, Form) and self._find_line(code, r"^class\s+\w+") >= 0:
            return super().add_handler(code, name, form, args)
        lines = code.rstrip("\n").splitlines() + ["", "", f"def {name}({args or ''}):", "    pass"]
        return "\n".join(lines) + "\n", len(lines) - 1

    # ------------------------------------------------------------------ run
    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        folder = Path(folder)
        main = "main.py" if (folder / "main.py").exists() else self.code_file(startup_form or "main")
        return RunSpec(interpreter, ["-u", main], folder, dict(os.environ, PYTHONUNBUFFERED="1"))

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        return super().debug_spec(folder, startup_form or "main", interpreter, breakpoints)


PLUGIN = ArcadePlugin()
