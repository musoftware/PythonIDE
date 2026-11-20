"""Godot 3D (GDScript) - Godot 4 3D projects (round 7, radide/games3d/).

The scene is ``Scene1.scene3d`` (3D scene view); F5 regenerates ``Scene1.tscn`` and the runtime scripts in
``rad3d/`` and runs ``godot --path <project>``.  User code: ``Scene1.gd`` (extends rad3d_scene.gd) with
VB-style handlers ``Scene_Load``, ``Scene_Update(delta)``, ``Player_Collect(item)``.
"""
from __future__ import annotations

from pathlib import Path

from ..games import godot_export
from ..model import Form, Project
from .base import LanguagePlugin, RunSpec
from .godot import GD_BUILTINS, GD_KEYWORDS


class Godot3DPlugin(LanguagePlugin):
    id = "godot3d"
    display_name = "Godot 3D (GDScript)"
    code_ext = ".gd"
    scene3d = True
    supports_debug = False
    interpreter_names = list(godot_export.GODOT_NAMES)
    keywords = GD_KEYWORDS
    builtins = GD_BUILTINS + ["Vector3", "Node3D", "CharacterBody3D", "MeshInstance3D", "Camera3D", "Area3D",
                              "StaticBody3D", "move_and_slide", "is_on_floor", "deg_to_rad"]
    line_comments = ["#"]
    project_name_base = "Game3D"

    def find_interpreter(self, configured: str = "") -> str:
        return godot_export.godot_exe(configured)

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from ..games3d.templates import TEMPLATES
        return list(TEMPLATES[self.id])

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..games3d.templates import create_project
        return create_project(Path(folder), name, self.id, template or "playground3d")

    def generate_designer(self, form: Form, user_code: str) -> str:
        return f"# {form.name}: Windows Forms are not used in Godot projects - edit the 3D scene instead.\n"

    def new_code(self, form: Form, is_startup: bool) -> str:
        return 'extends "res://rad3d/rad3d_scene.gd"\n\n\nfunc Scene_Load():\n\tpass\n'

    def find_handler(self, code: str, name: str) -> int:
        return godot_export.find_gd_handler(code, name)

    def add_handler(self, code: str, name: str, form: Form | None = None, args: str | None = None):
        return godot_export.add_gd_handler(code, name)

    def module_template(self, name: str) -> str:
        return f"# {name} - shared GDScript code\nextends RefCounted\n"

    def on_file_removed(self, code: str, filename: str) -> str:
        return code

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        from ..games3d import godot_gen
        folder = Path(folder)
        godot_gen.sync_project(folder)
        exe = interpreter or godot_export.godot_exe()
        return RunSpec(exe, ["--path", str(folder)], folder)

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)


PLUGIN = Godot3DPlugin()
