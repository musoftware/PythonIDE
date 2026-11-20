"""New Project > Games > "Python 3D (Ursina)" and "Godot 3D" templates."""
from __future__ import annotations

from pathlib import Path

from ..model import Project
from . import godot_gen, ursina_gen
from .model import EXT, default_scene

TEMPLATES = {
    "python-ursina": [
        ("playground3d", "Ursina 3D Playground",
         "A 3D scene for the Ursina engine: ground, crates, spinning coins and a player you move with WASD / "
         "arrows (Space jumps); the camera follows it. Edit the scene in the 3D scene view, code in main.py. "
         "F5 plays it.", "SP_MediaPlay"),
        ("empty3d", "Ursina Empty 3D Scene", "Ground, sun, camera and one box - start from scratch.",
         "SP_MediaPlay"),
    ],
    "godot3d": [
        ("playground3d", "Godot 3D Playground",
         "A Godot 4 3D scene (.tscn): Camera3D, DirectionalLight3D, meshes with materials, a CharacterBody3D "
         "player controller in GDScript (WASD / arrows, Space jumps) and collectible coins (Area3D). The scene "
         "is edited in the 3D scene view; F5 runs it with Godot.", "SP_MediaPlay"),
        ("empty3d", "Godot Empty 3D Scene", "Ground, sun, camera and one box.", "SP_MediaPlay"),
    ],
}


def create_project(folder: Path, name: str, plugin_id: str, template: str = "playground3d") -> Project:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    scene = default_scene("Scene1", "empty" if template == "empty3d" else "playground")
    scene.save(folder / f"Scene1{EXT}")
    if plugin_id == "godot3d":
        godot_gen.sync_project(folder, title=name, main_scene="Scene1")
        (folder / ".gitignore").write_text(".godot/\n", encoding="utf-8")
        modules = [f"Scene1{EXT}", "Scene1.gd"]
        startup = "Scene1"
    else:
        (folder / "main.py").write_text(ursina_gen.main_code(name, "Scene1"), encoding="utf-8")
        (folder / "requirements.txt").write_text("ursina>=8.0\n", encoding="utf-8")
        ursina_gen.sync_project(folder)
        modules = ["main.py", f"Scene1{EXT}"]
        startup = "main"
    project = Project(folder, name, plugin_id, [], startup, modules)
    project.extra["scenes3d"] = ["Scene1"]
    project.save()
    return project


__all__ = ["TEMPLATES", "create_project"]
