"""``<Scene>.scene3d`` -> Godot 4 3D scene ``<Scene>.tscn`` + ``project.godot`` + runtime scripts.

Node tree: ``<Scene>`` (Node3D, script <Scene>.gd extends res://rad3d/rad3d_scene.gd) > WorldEnvironment (sky
colour), Camera3D, DirectionalLight3D, and per mesh entity:
* player       -> CharacterBody3D (script res://rad3d/rad3d_player.gd, group "player") + mesh + capsule shape
* solid        -> StaticBody3D + MeshInstance3D + CollisionShape3D sized like the mesh
* collectible  -> Area3D (group "collectible") + mesh + shape (rad3d_scene.gd connects body_entered)
* otherwise    -> MeshInstance3D
"spin" adds the group "spin".  Coordinates are mirrored on Z (the scene file uses Ursina's left-handed axes).
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

from .model import EXT, Entity, Scene3D

RUNTIME_DIR = Path(__file__).with_name("runtime")
RUNTIME_FILES = ("rad3d_scene.gd", "rad3d_player.gd")


def _f(x: float) -> str:
    s = f"{float(x):.6g}"
    return s if any(c in s for c in ".e") else s + ".0"


def _vec3(v) -> str:
    return f"Vector3({_f(v[0])}, {_f(v[1])}, {_f(v[2])})"


def _pos(e: Entity) -> list[float]:
    return [e.position[0], e.position[1], -e.position[2]]


def _rot_rad(e: Entity) -> list[float]:
    rx, ry, rz = e.rotation
    return [math.radians(-rx), math.radians(-ry), math.radians(rz)]


def _color(c: str) -> str:
    c = str(c or "#FFFFFF").lstrip("#")
    try:
        r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        r = g = b = 1.0
    return f"Color({r:.4g}, {g:.4g}, {b:.4g}, 1)"


class _Tscn:
    def __init__(self):
        self.ext: list[str] = []
        self.sub: list[str] = []
        self.nodes: list[str] = []
        self._n = 0

    def ext_res(self, kind: str, path: str) -> str:
        rid = f"{len(self.ext) + 1}_r3d"
        self.ext.append(f'[ext_resource type="{kind}" path="{path}" id="{rid}"]')
        return rid

    def sub_res(self, kind: str, props: dict) -> str:
        self._n += 1
        rid = f"{kind}_{self._n}"
        body = "".join(f"{k} = {v}\n" for k, v in props.items())
        self.sub.append(f'[sub_resource type="{kind}" id="{rid}"]\n{body}')
        return rid

    def node(self, name: str, kind: str, parent: str | None, props: dict, groups=()) -> None:
        head = f'[node name="{name}" type="{kind}"'
        if parent is not None:
            head += f' parent="{parent}"'
        if groups:
            head += " groups=[" + ", ".join(f'"{g}"' for g in groups) + "]"
        self.nodes.append(head + "]\n" + "".join(f"{k} = {v}\n" for k, v in props.items()))

    def text(self) -> str:
        steps = len(self.ext) + len(self.sub) + 1
        out = [f"[gd_scene load_steps={steps} format=3]", ""]
        out += [e for e in self.ext] + ([""] if self.ext else [])
        out += [s for s in self.sub]
        out += [n for n in self.nodes]
        return "\n".join(out)


def _mesh(t: _Tscn, e: Entity) -> str:
    mat = t.sub_res("StandardMaterial3D", {"albedo_color": _color(e.color)})
    m = f'SubResource("{mat}")'
    if e.kind == "cube":
        return t.sub_res("BoxMesh", {"material": m})
    if e.kind == "sphere":
        return t.sub_res("SphereMesh", {"material": m})
    if e.kind == "plane":
        return t.sub_res("PlaneMesh", {"material": m, "size": "Vector2(1, 1)"})
    if e.kind == "capsule":
        return t.sub_res("CapsuleMesh", {"material": m})
    return t.sub_res("CylinderMesh", {"material": m, "height": "1.0"})


def _shape(t: _Tscn, e: Entity) -> str:
    sx, sy, sz = (abs(x) for x in e.scale)
    if e.kind == "sphere":
        return t.sub_res("SphereShape3D", {"radius": _f(0.5 * max(sx, sy, sz))})
    if e.kind == "capsule":
        return t.sub_res("CapsuleShape3D", {"radius": _f(0.5 * max(sx, sz)), "height": _f(2 * sy)})
    if e.kind == "cylinder":
        return t.sub_res("CylinderShape3D", {"radius": _f(0.5 * max(sx, sz)), "height": _f(sy)})
    if e.kind == "plane":
        return t.sub_res("BoxShape3D", {"size": _vec3([sx, 0.1, sz])})
    return t.sub_res("BoxShape3D", {"size": _vec3([sx, sy, sz])})


def export_scene(scene: Scene3D, player_script: str = "res://rad3d/rad3d_player.gd") -> str:
    t = _Tscn()
    script = t.ext_res("Script", f"res://{scene.name}.gd")
    pscript = t.ext_res("Script", player_script) if scene.player() is not None else ""
    sky = t.sub_res("Environment", {"background_mode": "1", "background_color": _color(scene.sky),
                                    "ambient_light_source": "2", "ambient_light_color": "Color(0.5, 0.5, 0.55, 1)",
                                    "ambient_light_energy": "0.6"})
    t.node(scene.name, "Node3D", None, {"script": f'ExtResource("{script}")'})
    t.node("WorldEnvironment", "WorldEnvironment", ".", {"environment": f'SubResource("{sky}")'})
    for e in scene.entities:
        tr = {"position": _vec3(_pos(e)), "rotation": _vec3(_rot_rad(e))}
        groups = [g for g in ("spin",) if g in e.behaviours]
        if e.kind == "camera":
            # Ursina looks along +Z, Godot along -Z: the Z mirror of _pos() already turns the view around
            t.node(e.name, "Camera3D", ".", {"position": _vec3(_pos(e)), "rotation": _vec3(_rot_rad(e)),
                                              "fov": _f(float(e.props.get("fov", 60))), "current": "true"})
            continue
        if e.kind == "light":
            t.node(e.name, "DirectionalLight3D", ".", {"position": _vec3(_pos(e)), "rotation": _vec3(_rot_rad(e)),
                                                        "light_color": _color(e.color), "shadow_enabled": "true"})
            continue
        if e.kind == "empty":
            t.node(e.name, "Node3D", ".", tr, groups)
            continue
        mesh = _mesh(t, e)
        mprops = {"mesh": f'SubResource("{mesh}")', "scale": _vec3([abs(x) or 1 for x in e.scale])}
        if "player" in e.behaviours:
            t.node(e.name, "CharacterBody3D", ".", dict(tr, script=f'ExtResource("{pscript}")'),
                   ["player"] + groups)
        elif "collectible" in e.behaviours:
            t.node(e.name, "Area3D", ".", tr, ["collectible"] + groups)
        elif "solid" in e.behaviours:
            t.node(e.name, "StaticBody3D", ".", tr, groups)
        else:
            t.node(e.name, "MeshInstance3D", ".", dict(tr, mesh=mprops["mesh"], scale=mprops["scale"]), groups)
            continue
        t.node("Mesh", "MeshInstance3D", e.name, mprops)
        shape_props = {"shape": f'SubResource("{_shape(t, e)}")'}
        if e.kind == "plane":
            shape_props["position"] = "Vector3(0, -0.05, 0)"
        t.node("Shape", "CollisionShape3D", e.name, shape_props)
    return t.text()


def user_script(scene: str) -> str:
    return f'''# {scene}.gd - your code for the 3D scene {scene} (RAD IDE).  The scene itself is {scene}{EXT}
# (3D scene view); {scene}.tscn is generated from it.  VB-style handlers called by rad3d_scene.gd:
extends "res://rad3d/rad3d_scene.gd"


func Scene_Load():
	print("Collect the coins!")


func Scene_Update(delta):
	pass


func Player_Collect(item):
	print("Collected %s - score %d" % [item.name, score])
'''


def project_godot(title: str, main_scene: str, gravity: float = 9.8) -> str:
    return f'''; Engine configuration file (RAD IDE 3D project).
config_version=5

[application]

config/name="{title}"
run/main_scene="res://{main_scene}.tscn"
config/features=PackedStringArray("4.2", "Forward Plus")

[display]

window/size/viewport_width=1024
window/size/viewport_height=640

[physics]

3d/default_gravity={_f(gravity)}
'''


def write_runtime(folder: Path) -> None:
    dest = Path(folder) / "rad3d"
    dest.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_FILES:
        src = RUNTIME_DIR / name
        if not (dest / name).exists() or (dest / name).read_bytes() != src.read_bytes():
            shutil.copyfile(src, dest / name)


def sync_scene(folder: Path, scene_file) -> Path:
    folder = Path(folder)
    path = folder / scene_file if not Path(scene_file).is_absolute() else Path(scene_file)
    scene = Scene3D.load(path)
    scene.name = path.stem
    out = folder / f"{path.stem}.tscn"
    text = export_scene(scene)
    if not out.exists() or out.read_text(encoding="utf-8") != text:
        out.write_text(text, encoding="utf-8")
    gd = folder / f"{path.stem}.gd"
    if not gd.exists():
        gd.write_text(user_script(path.stem), encoding="utf-8")
    return out


def sync_project(folder: Path, title: str = "", main_scene: str = "") -> list[Path]:
    folder = Path(folder)
    write_runtime(folder)
    scenes = sorted(folder.glob(f"*{EXT}"))
    out = [sync_scene(folder, p) for p in scenes]
    pg = folder / "project.godot"
    if not pg.exists() and scenes:
        main = main_scene or scenes[0].stem
        grav = Scene3D.load(folder / f"{main}{EXT}").gravity
        pg.write_text(project_godot(title or folder.name, main, grav), encoding="utf-8")
    return out


__all__ = ["export_scene", "project_godot", "sync_project", "sync_scene", "user_script", "write_runtime"]
