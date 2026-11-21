"""Godot 4 (GDScript) - game projects exported to Godot (CONTRACTS 10.2).

The scenes are the same ``<Scene>.scene`` files as in pygame projects (scene designer, ``is_game``).
Their code is ``<Scene>.gd`` (extends res://radgame/radgame_scene.gd) with the same VB-style handlers:
``func Player_Collide(other):``. F5 exports every scene to ``<Scene>.tscn`` (radide/games/godot_export.py),
imports new assets with Godot once, and runs ``godot --path <project>``.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..games import codegen, godot_export
from ..model import Form, Project
from .base import Completion, LanguagePlugin, RunSpec


def _native_app(folder: Path) -> bool:
    """project.radproj says "native_app": true - an existing Godot project opened with File > Open Folder
    (radide/project_detect.py): its own project.godot / .tscn scenes are never regenerated."""
    try:
        import json
        return bool(json.loads((Path(folder) / "project.radproj").read_text(encoding="utf-8")).get("native_app"))
    except (OSError, ValueError, AttributeError):
        return False

GD_KEYWORDS = ["if", "elif", "else", "for", "while", "match", "break", "continue", "pass", "return", "class",
               "class_name", "extends", "is", "in", "as", "self", "signal", "func", "static", "const", "enum",
               "var", "await", "preload", "breakpoint", "true", "false", "null", "and", "or", "not", "super",
               "@export", "@onready", "@tool"]
GD_BUILTINS = ["print", "str", "int", "float", "len", "range", "abs", "min", "max", "clamp", "lerp", "randi",
               "randf", "randi_range", "randf_range", "load", "is_instance_valid", "Vector2", "Vector2i", "Rect2",
               "Color", "Array", "Dictionary", "String", "Node", "Node2D", "Sprite2D", "AnimatedSprite2D", "Label",
               "TileMap", "Input", "get_tree", "get_node", "queue_free"]
# helpers of radgame_scene.gd offered by IntelliSense
GD_HELPERS = {"find": "find(name) -> Node - a scene object by name", "group_of": "group_of(node) -> String",
              "find_group": "find_group(group) -> Array", "add_score": "add_score(points)",
              "go_to_scene": "go_to_scene(name)", "restart_scene": "restart_scene()", "quit_game": "quit_game()",
              "play_sound": "play_sound(id)", "show_message": "show_message(text, seconds)",
              "add_timer": "add_timer(name, ms)", "stop_timer": "stop_timer(name)", "destroy": "destroy(node)",
              "rect_of": "rect_of(node) -> Rect2", "velocity": "velocity(node) -> Vector2",
              "set_velocity": "set_velocity(node, v)", "key_down": "key_down(key) -> bool",
              "score": "score (int, kept between scenes)", "lives": "lives (int)", "vars": "vars (Dictionary)",
              "spawn": "spawn(template_name, x, y) -> Node - a copy of a spawn template (props template=1)",
              "enable_behaviour": "enable_behaviour(node, type, on)", "save_data": "save_data(key, value)",
              "load_data": "load_data(key, default) - a value kept by save_data"}


class GodotPlugin(LanguagePlugin):
    id = "godot"
    display_name = "Godot 4 (GDScript)"
    code_ext = ".gd"
    is_game = True
    scene_ext = ".scene"
    # F9 / F5: radide/features/game_runtimes.py debugs through Godot's debug adapter (radide/games/godot_dap.py)
    supports_debug = True
    interpreter_names = list(godot_export.GODOT_NAMES)
    keywords = GD_KEYWORDS
    builtins = GD_BUILTINS
    line_comments = ["#"]

    def find_interpreter(self, configured: str = "") -> str:
        return godot_export.godot_exe(configured)

    # ------------------------------------------------------------ New Project (Games group)
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from ..games.templates import templates_for
        return [(t.id, t.title + " (Godot)" if t.id != "empty" else "Empty Godot 2D", t.description, t.icon)
                for t in templates_for(self.id)]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..games.templates import create_game_project
        return create_game_project(Path(folder), name, self.id, template or "platformer")

    # ------------------------------------------------------------ forms (a Godot project has none)
    def generate_designer(self, form: Form, user_code: str) -> str:
        return (f"# {form.name}: Windows Forms are not used in Godot projects - add a scene instead.\n"
                "extends Node\n")

    def new_code(self, form: Form, is_startup: bool) -> str:
        return 'extends "res://radgame/radgame_scene.gd"\n\n\nfunc Scene_Load():\n\tpass\n'

    # ------------------------------------------------------------ scenes
    def scene_code_file(self, scene: str) -> str:
        return f"{scene}.gd"

    def scene_designer_file(self, scene: str) -> str:
        return f"{scene}.tscn"

    def new_scene_code(self, scene) -> str:
        d = codegen.scene_dict(scene)
        return godot_export.user_script(d.get("name") or "Scene1")

    def generate_scene_designer(self, scene) -> str:
        return godot_export.export_scene(Path("."), scene)

    def on_scene_saved(self, folder: Path, scene: str) -> list[Path]:
        folder = Path(folder)
        tscn = folder / f"{scene}.tscn"
        tscn.write_text(godot_export.export_scene(folder, folder / f"{scene}.scene"), encoding="utf-8")
        godot_export.write_user_scripts(folder, [scene])
        return [tscn, folder / f"{scene}.gd"]

    def scene_handler(self, obj_name: str | None, event: str) -> str:
        return codegen.handler_name(obj_name, event)

    def add_scene_handler(self, code: str, obj_name: str | None, event: str) -> tuple[str, int]:
        name = codegen.handler_name(obj_name, event)
        line = self.find_handler(code, name)
        if line >= 0:
            return code, line + 1
        return godot_export.add_gd_handler(code, name)

    # ------------------------------------------------------------ handlers
    def find_handler(self, code: str, name: str) -> int:
        return godot_export.find_gd_handler(code, name)

    def add_handler(self, code: str, name: str, form: Form | None = None, args: str | None = None):
        return godot_export.add_gd_handler(code, name)

    def module_template(self, name: str) -> str:
        return f"# {name} - shared GDScript code\nextends RefCounted\n"

    def on_file_removed(self, code: str, filename: str) -> str:
        return code

    # ------------------------------------------------------------------ run
    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        folder = Path(folder)
        if not _native_app(folder):            # an existing Godot project (File > Open Folder): its own .tscn
            godot_export.export_project(folder)
        exe = interpreter or godot_export.godot_exe()
        if godot_export.needs_import(folder):
            godot_export.import_assets(folder, exe)
        return RunSpec(exe, ["--path", str(folder)], folder)

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        """Without the IDE's Godot debug adapter session (features/game_runtimes.py) F5 just runs the game."""
        return self.run_spec(folder, startup_form, interpreter)

    # ------------------------------------------------------------ completion
    def completions(self, code, line, col, path, names=None):
        out = super().completions(code, line, col, path, names)
        if not out and re.search(r"\.\w*$", (code.splitlines()[line:line + 1] or [""])[0][:col]):
            return out
        have = {c.name for c in out}
        return [Completion(k, "function", v) for k, v in GD_HELPERS.items() if k not in have] + out

    def calltip(self, code, line, col, path, names=None):
        text = (code.splitlines()[line:line + 1] or [""])[0][:col]
        m = re.search(r"(\w+)\s*\([^()]*$", text)
        return GD_HELPERS.get(m.group(1), "") if m else ""


PLUGIN = GodotPlugin()
