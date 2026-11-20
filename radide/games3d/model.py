"""The 3D scene file ``<Scene>.scene3d`` (JSON) shared by the Ursina and Godot 3D generators.

    {"name": "Scene1", "sky": "#87CEEB", "gravity": 9.8,
     "entities": [{"name": "Player", "kind": "capsule", "position": [0, 1, 0], "rotation": [0, 0, 0],
                   "scale": [1, 1, 1], "color": "#3080FF", "behaviours": ["player"], "props": {}} ...]}

kind: cube | sphere | plane | capsule | cylinder | camera | light | empty.
behaviours: "player" (WASD/arrows + Space jump, the camera follows it), "spin" (rotates around Y),
"solid" (static collider), "collectible" (disappears when the player touches it, +1 score).
Units: metres, degrees, Ursina's convention: Y up, +Z forward (left-handed), rotation_x > 0 looks down,
rotation_y > 0 turns right.  godot_gen.py mirrors Z (Godot is right-handed, -Z forward).
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ["cube", "sphere", "plane", "capsule", "cylinder", "camera", "light", "empty"]
MESH_KINDS = {"cube", "sphere", "plane", "capsule", "cylinder"}
BEHAVIOURS = ["player", "spin", "solid", "collectible"]
EXT = ".scene3d"


def _vec(v, default=(0.0, 0.0, 0.0)) -> list[float]:
    try:
        out = [float(x) for x in list(v)[:3]]
    except (TypeError, ValueError):
        out = []
    return out + list(default[len(out):]) if len(out) < 3 else out


def safe_name(name: str, default: str = "Entity") -> str:
    n = re.sub(r"\W", "_", str(name or "")).strip("_") or default
    return "_" + n if n[0].isdigit() else n


@dataclass
class Entity:
    name: str
    kind: str = "cube"
    position: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    color: str = "#C0C0C0"
    behaviours: list[str] = field(default_factory=list)
    props: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Entity":
        kind = str(d.get("kind") or "cube").lower()
        return cls(name=safe_name(d.get("name") or kind.title()), kind=kind if kind in KINDS else "cube",
                   position=_vec(d.get("position")), rotation=_vec(d.get("rotation")),
                   scale=_vec(d.get("scale"), (1.0, 1.0, 1.0)), color=str(d.get("color") or "#C0C0C0"),
                   behaviours=[b for b in d.get("behaviours") or [] if b in BEHAVIOURS],
                   props=dict(d.get("props") or {}))

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "position": [round(x, 4) for x in self.position],
                "rotation": [round(x, 4) for x in self.rotation], "scale": [round(x, 4) for x in self.scale],
                "color": self.color, "behaviours": list(self.behaviours), "props": dict(self.props)}


@dataclass
class Scene3D:
    name: str = "Scene1"
    sky: str = "#87CEEB"
    gravity: float = 9.8
    entities: list[Entity] = field(default_factory=list)

    # ------------------------------------------------------------ io
    @classmethod
    def from_dict(cls, d: dict) -> "Scene3D":
        return cls(name=safe_name(d.get("name") or "Scene1", "Scene1"), sky=str(d.get("sky") or "#87CEEB"),
                   gravity=float(d.get("gravity", 9.8) or 0.0),
                   entities=[Entity.from_dict(e) for e in d.get("entities") or [] if isinstance(e, dict)])

    @classmethod
    def load(cls, path: Path) -> "Scene3D":
        path = Path(path)
        if not path.exists():
            return default_scene(path.stem)
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8") or "{}"))

    def to_dict(self) -> dict:
        return {"name": self.name, "sky": self.sky, "gravity": self.gravity,
                "entities": [e.to_dict() for e in self.entities]}

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    # ------------------------------------------------------------ helpers
    def find(self, name: str) -> Entity | None:
        return next((e for e in self.entities if e.name == name), None)

    def unique_name(self, base: str) -> str:
        base = safe_name(base)
        names = {e.name for e in self.entities}
        if base not in names:
            return base
        i = 1
        while f"{base}{i}" in names:
            i += 1
        return f"{base}{i}"

    def add(self, kind: str, **kw) -> Entity:
        e = Entity(name=self.unique_name(kw.pop("name", kind.title())), kind=kind, **kw)
        self.entities.append(e)
        return e

    def duplicate(self, name: str) -> Entity | None:
        src = self.find(name)
        if src is None:
            return None
        e = copy.deepcopy(src)
        e.name = self.unique_name(src.name)
        e.position = [src.position[0] + 1.5, src.position[1], src.position[2]]
        self.entities.append(e)
        return e

    def camera(self) -> Entity | None:
        return next((e for e in self.entities if e.kind == "camera"), None)

    def player(self) -> Entity | None:
        return next((e for e in self.entities if "player" in e.behaviours), None)

    def problems(self) -> list[str]:
        out = []
        names = [e.name for e in self.entities]
        for n in sorted({n for n in names if names.count(n) > 1}):
            out.append(f"Two entities are named {n}.")
        if sum("player" in e.behaviours for e in self.entities) > 1:
            out.append("More than one entity has the 'player' behaviour (only the first one is controlled).")
        if not any(e.kind == "light" for e in self.entities):
            out.append("The scene has no light (meshes will be dark in Godot).")
        return out


def default_scene(name: str = "Scene1", template: str = "playground") -> Scene3D:
    """The starter scene of the templates: ground, a few boxes, coins, a player, camera and sun."""
    s = Scene3D(name=safe_name(name, "Scene1"))
    s.add("plane", name="Ground", scale=[30.0, 1.0, 30.0], color="#4C9A2A", behaviours=["solid"])
    s.add("light", name="Sun", position=[4.0, 10.0, 4.0], rotation=[50.0, 30.0, 0.0], color="#FFFFFF")
    s.add("camera", name="MainCamera", position=[0.0, 8.0, -14.0], rotation=[25.0, 0.0, 0.0])
    if template == "empty":
        s.add("cube", name="Box", position=[0.0, 0.5, 0.0], color="#D08030")
        return s
    s.add("capsule", name="Player", position=[0.0, 1.0, 0.0], color="#3080FF", behaviours=["player"])
    for i, (x, z) in enumerate([(4, 3), (-5, 2), (2, -6)]):
        s.add("cube", name=f"Crate{i + 1}", position=[float(x), 0.75, float(z)], scale=[1.5, 1.5, 1.5],
              color="#B07030", behaviours=["solid"])
    for i, (x, z) in enumerate([(-3, -3), (6, -2), (-6, 6), (0, 7)]):
        s.add("sphere", name=f"Coin{i + 1}", position=[float(x), 0.8, float(z)], scale=[0.5, 0.5, 0.5],
              color="#FFD700", behaviours=["collectible", "spin"])
    return s


__all__ = ["BEHAVIOURS", "EXT", "Entity", "KINDS", "MESH_KINDS", "Scene3D", "default_scene", "safe_name"]
