"""The game scene model: load / save / validate `<Scene>.scene` files (CONTRACTS 10.4).

A scene is JSON::

    {"name", "width", "height", "background", "fps", "gravity",
     "camera": {"follow": sprite|null},
     "assets": {"images": {id: path}, "sounds": {id: path},
                "spritesheets": {id: {"image", "frame_w", "frame_h",
                                      "animations": {name: {"frames": [i...], "fps", "loop"}}}},
                "tilesets": {id: {"image", "tile_w", "tile_h"}}},
     "layers": [{"name", "type": "tiles"|"sprites"|"ui", "tileset", "data": [[tile or -1 ...] ...],
                 "collision": bool,
                 "objects": [{"name", "kind": "sprite"|"text"|"area", "x", "y", "w", "h",
                              "image"|"spritesheet", "animation", "scale", "rotation", "z", "visible",
                              "text", "behaviours": [{"type": ..., ...params}], "props": {}}]}]}

`width`/`height` are the game window (the camera view); tile layers may be larger than the window
(the level scrolls when `camera.follow` names a sprite).  Keys this module does not know are kept
when a scene is loaded and saved again.  Extra keys written by the designer: layer `visible` and
`locked` (editor state, the runtime may ignore them).

Pure Python (no Qt): the designer, the code generators and the tests all use it.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

LAYER_TYPES = ("tiles", "sprites", "ui")
OBJECT_KINDS = ("sprite", "text", "area")
DEFAULT_TILE = 32

# behaviour type -> (label, default parameters, help).  Parameters are stored flat in the
# behaviour dict next to "type" (CONTRACTS 10.4).
BEHAVIOURS: dict[str, tuple[str, dict, str]] = {
    "keyboard_move": ("Keyboard movement", {"speed": 200, "keys": "both", "axis": "both"},
                      "Arrow keys / WASD move the sprite (speed in pixels per second; keys arrows|wasd|both; "
                      "axis x|y|both)."),
    "platformer": ("Platformer (gravity + jump)", {"speed": 220, "jump": 520, "jumps": 1, "keys": "both"},
                   "Left/right to run, Up/Space to jump (jumps 2 = double jump). Falls with the scene gravity; "
                   "stands on solid sprites and on collision tile layers."),
    "top_down": ("Top-down movement", {"speed": 180, "four_way": False, "rotate": False},
                 "Arrow keys move the sprite in 8 directions (four_way = 4); rotate turns it to face the movement."),
    "bounce": ("Bounce", {"vx": 150, "vy": 150},
               "Moves with a constant velocity and bounces off the window edges and solid things."),
    "follow_mouse": ("Follow mouse", {"speed": 0, "axis": "both"},
                     "Moves towards the mouse pointer (speed 0 = stick to the pointer)."),
    "solid": ("Solid", {},
              "Other sprites cannot walk through it (platforms, walls)."),
    "collectible": ("Collectible", {"score": 1, "sound": ""},
                    "Disappears when the player touches it and adds score (plays the sound id)."),
    "enemy_patrol": ("Enemy patrol", {"speed": 80, "distance": 160, "axis": "x", "turn_at_edges": True},
                     "Walks back and forth over distance pixels along axis x or y (turns at ledges)."),
    "flap": ("Flap (tap to fly up)", {"gravity": 1100, "flap": 340, "max_fall": 600, "keys": "space,up,w",
                                      "mouse": True, "tilt": True, "ceiling": True},
             "Falls with gravity; Space / Up / W or a mouse click kicks it upwards (fires <Sprite>_Flap). "
             "tilt turns it nose-up / nose-down with its speed; ceiling stops it at the top of the window."),
    "scroll": ("Scroll (move at a constant speed)", {"speed": 120, "direction": "left", "wrap": False},
               "Moves left/right/up/down at speed pixels per second: obstacles, ground, parallax scenery. "
               "wrap = endless: copies of the same group placed side by side leapfrog each other (or a "
               "distance in pixels); without wrap the object is destroyed when it leaves the window."),
}

SCENE_EVENTS = ["Load", "Update", "KeyDown", "KeyUp", "MouseDown", "MouseUp", "Draw"]
OBJECT_EVENTS = {"sprite": ["Collide", "Click", "AnimationEnd", "OutOfWorld", "Jump", "Bounce", "Flap"],
                 "text": ["Click"],
                 "area": ["Collide", "Click"]}
# handler arguments (Python code) per event
EVENT_ARGS = {"Load": "", "Update": "dt", "KeyDown": "key", "KeyUp": "key", "MouseDown": "x, y, button",
              "MouseUp": "x, y, button", "Draw": "screen", "Collide": "other", "Click": "", "Tick": "",
              "AnimationEnd": "", "OutOfWorld": "", "Jump": "", "Bounce": "", "Flap": ""}
try:      # one list of events for the designer and the code generator (radide/games/codegen.py)
    from .codegen import EVENT_ARGS as _GEN_ARGS, OBJECT_EVENTS as _GEN_OBJ, SCENE_EVENTS as _GEN_SCENE
    EVENT_ARGS = {**EVENT_ARGS, **_GEN_ARGS}
    SCENE_EVENTS, OBJECT_EVENTS = list(_GEN_SCENE), {k: list(v) for k, v in _GEN_OBJ.items()}
except Exception:  # noqa: BLE001 - the designer works without the generator
    pass


# ====================================================================== objects
@dataclass
class SceneObject:
    name: str
    kind: str = "sprite"
    x: float = 0
    y: float = 0
    w: float = 32
    h: float = 32
    image: str = ""
    spritesheet: str = ""
    animation: str = ""
    scale: float = 1.0
    rotation: float = 0.0
    z: int = 0
    visible: bool = True
    text: str = ""
    behaviours: list = field(default_factory=list)
    props: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    _KEYS = ("name", "kind", "x", "y", "w", "h", "image", "spritesheet", "animation", "scale",
             "rotation", "z", "visible", "text", "behaviours", "props")

    @classmethod
    def from_dict(cls, d: dict) -> "SceneObject":
        o = cls(name=str(d.get("name") or "Object"))
        o.kind = d.get("kind", "sprite") if d.get("kind") in OBJECT_KINDS else "sprite"
        for k in ("x", "y", "w", "h", "scale", "rotation"):
            if k in d:
                try:
                    setattr(o, k, _num(d[k]))
                except (TypeError, ValueError):
                    pass
        o.z = int(_num(d.get("z", 0)) or 0)
        o.visible = bool(d.get("visible", True))
        for k in ("image", "spritesheet", "animation", "text"):
            o.__dict__[k] = str(d.get(k) or "")
        o.behaviours = [dict(b) for b in d.get("behaviours", []) if isinstance(b, dict) and b.get("type")]
        o.props = dict(d.get("props") or {})
        o.extra = {k: copy.deepcopy(v) for k, v in d.items() if k not in cls._KEYS}
        return o

    def to_dict(self) -> dict:
        d = {"name": self.name, "kind": self.kind, "x": _clean(self.x), "y": _clean(self.y),
             "w": _clean(self.w), "h": _clean(self.h)}
        if self.image:
            d["image"] = self.image
        if self.spritesheet:
            d["spritesheet"] = self.spritesheet
            d["animation"] = self.animation
        d.update(scale=_clean(self.scale), rotation=_clean(self.rotation), z=self.z, visible=self.visible)
        if self.kind == "text" or self.text:
            d["text"] = self.text
        d["behaviours"] = [dict(b) for b in self.behaviours]
        d["props"] = dict(self.props)
        d.update(copy.deepcopy(self.extra))
        return d

    def behaviour(self, btype: str) -> dict | None:
        return next((b for b in self.behaviours if b.get("type") == btype), None)

    def add_behaviour(self, btype: str, **params) -> dict:
        if btype not in BEHAVIOURS:
            raise KeyError(btype)
        b = {"type": btype, **BEHAVIOURS[btype][1], **params}
        self.behaviours.append(b)
        return b


# ====================================================================== layers
@dataclass
class Layer:
    name: str
    type: str = "sprites"
    tileset: str = ""
    data: list = field(default_factory=list)
    collision: bool = False
    objects: list = field(default_factory=list)
    visible: bool = True
    locked: bool = False
    extra: dict = field(default_factory=dict)

    _KEYS = ("name", "type", "tileset", "data", "collision", "objects", "visible", "locked")

    @classmethod
    def from_dict(cls, d: dict) -> "Layer":
        ly = cls(name=str(d.get("name") or "Layer"))
        ly.type = d.get("type") if d.get("type") in LAYER_TYPES else "sprites"
        ly.tileset = str(d.get("tileset") or "")
        ly.data = [[_tile(v) for v in row] for row in (d.get("data") or []) if isinstance(row, list)]
        ly.collision = bool(d.get("collision", False))
        ly.objects = [SceneObject.from_dict(o) for o in d.get("objects", []) if isinstance(o, dict)]
        ly.visible = bool(d.get("visible", True))
        ly.locked = bool(d.get("locked", False))
        ly.extra = {k: copy.deepcopy(v) for k, v in d.items() if k not in cls._KEYS}
        return ly

    def to_dict(self) -> dict:
        d = {"name": self.name, "type": self.type, "tileset": self.tileset if self.type == "tiles" else "",
             "data": [list(r) for r in self.data] if self.type == "tiles" else [],
             "collision": self.collision, "objects": [o.to_dict() for o in self.objects],
             "visible": self.visible}
        if self.locked:
            d["locked"] = True          # designer-only state
        d.update(copy.deepcopy(self.extra))
        return d

    # ---- tile map
    @property
    def cols(self) -> int:
        return max((len(r) for r in self.data), default=0)

    @property
    def rows(self) -> int:
        return len(self.data)

    def resize(self, cols: int, rows: int) -> None:
        """Grow / shrink the tile grid (new cells are empty, -1)."""
        cols, rows = max(1, int(cols)), max(1, int(rows))
        data = [list(r[:cols]) + [-1] * (cols - len(r[:cols])) for r in self.data[:rows]]
        while len(data) < rows:
            data.append([-1] * cols)
        self.data = data

    def inside(self, col: int, row: int) -> bool:
        return 0 <= row < len(self.data) and 0 <= col < len(self.data[row])

    def get(self, col: int, row: int) -> int:
        return self.data[row][col] if self.inside(col, row) else -1

    def paint(self, col: int, row: int, tile: int) -> bool:
        """Set one cell; True when it changed (tile -1 erases)."""
        if not self.inside(col, row) or self.data[row][col] == tile:
            return False
        self.data[row][col] = int(tile)
        return True

    def fill_rect(self, c0: int, r0: int, c1: int, r1: int, tile: int) -> list[tuple[int, int]]:
        """Fill the rectangle between two cells (inclusive); returns the changed cells."""
        changed = []
        for r in range(min(r0, r1), max(r0, r1) + 1):
            for c in range(min(c0, c1), max(c0, c1) + 1):
                if self.paint(c, r, tile):
                    changed.append((c, r))
        return changed

    def flood_fill(self, col: int, row: int, tile: int) -> list[tuple[int, int]]:
        """Bucket fill: replace the 4-connected region of the clicked tile; returns the changed cells."""
        if not self.inside(col, row):
            return []
        target = self.data[row][col]
        if target == tile:
            return []
        changed, stack = [], [(col, row)]
        while stack:
            c, r = stack.pop()
            if not self.inside(c, r) or self.data[r][c] != target:
                continue
            self.data[r][c] = int(tile)
            changed.append((c, r))
            stack.extend(((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)))
        return changed


# ====================================================================== scene
@dataclass
class Scene:
    name: str = "Scene1"
    width: int = 800
    height: int = 600
    background: str = "#6EC1E4"
    fps: int = 60
    gravity: float = 900
    camera: dict = field(default_factory=lambda: {"follow": None})
    assets: dict = field(default_factory=lambda: {"images": {}, "sounds": {}, "spritesheets": {}, "tilesets": {}})
    layers: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    _KEYS = ("name", "width", "height", "background", "fps", "gravity", "camera", "assets", "layers")

    # ---- construction / IO
    @classmethod
    def new(cls, name: str = "Scene1", width: int = 800, height: int = 600) -> "Scene":
        s = cls(name=name, width=width, height=height)
        bg = Layer("Background", "tiles")
        bg.resize(-(-width // DEFAULT_TILE), -(-height // DEFAULT_TILE))
        s.layers = [bg, Layer("Sprites", "sprites"), Layer("UI", "ui")]
        return s

    @classmethod
    def from_dict(cls, d: dict) -> "Scene":
        s = cls()
        s.name = str(d.get("name") or "Scene1")
        for k, conv in (("width", int), ("height", int), ("fps", int), ("gravity", float)):
            if k in d:
                try:
                    setattr(s, k, conv(_num(d[k])))
                except (TypeError, ValueError):
                    pass
        s.background = str(d.get("background") or s.background)
        cam = d.get("camera") if isinstance(d.get("camera"), dict) else {}
        s.camera = {"follow": cam.get("follow") or None, **{k: v for k, v in cam.items() if k != "follow"}}
        a = d.get("assets") if isinstance(d.get("assets"), dict) else {}
        s.assets = {k: copy.deepcopy(a.get(k) or {}) for k in ("images", "sounds", "spritesheets", "tilesets")}
        s.assets.update({k: copy.deepcopy(v) for k, v in a.items() if k not in s.assets})
        s.layers = [Layer.from_dict(ly) for ly in d.get("layers", []) if isinstance(ly, dict)]
        s.extra = {k: copy.deepcopy(v) for k, v in d.items() if k not in cls._KEYS}
        return s

    def to_dict(self) -> dict:
        d = {"name": self.name, "width": self.width, "height": self.height, "background": self.background,
             "fps": self.fps, "gravity": _clean(self.gravity), "camera": dict(self.camera),
             "assets": copy.deepcopy(self.assets), "layers": [ly.to_dict() for ly in self.layers]}
        d.update(copy.deepcopy(self.extra))
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "Scene":
        return cls.from_dict(json.loads(text))

    @classmethod
    def load(cls, path) -> "Scene":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def save(self, path) -> None:
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")

    def clone(self) -> "Scene":
        return Scene.from_dict(self.to_dict())

    # ---- queries
    def layer(self, name: str) -> Layer | None:
        return next((ly for ly in self.layers if ly.name == name), None)

    def objects(self):
        """(layer, object) for every object of every layer."""
        for ly in self.layers:
            for o in ly.objects:
                yield ly, o

    def find(self, name: str) -> tuple[Layer | None, SceneObject | None]:
        return next(((ly, o) for ly, o in self.objects() if o.name == name), (None, None))

    def names(self) -> set[str]:
        return {o.name for _ly, o in self.objects()}

    def unique_name(self, base: str) -> str:
        base = re.sub(r"\W", "", base) or "Sprite"
        if not base[0].isalpha():
            base = "S" + base
        base = re.sub(r"\d+$", "", base) or base
        taken = self.names() | {ly.name for ly in self.layers}
        i = 1
        while f"{base}{i}" in taken:
            i += 1
        return f"{base}{i}"

    def unique_layer_name(self, base: str) -> str:
        taken = {ly.name for ly in self.layers}
        if base not in taken:
            return base
        i = 2
        while f"{base} {i}" in taken:
            i += 1
        return f"{base} {i}"

    def tile_size(self, layer: Layer) -> tuple[int, int]:
        ts = self.assets.get("tilesets", {}).get(layer.tileset) if layer is not None else None
        if ts:
            return max(1, int(ts.get("tile_w") or DEFAULT_TILE)), max(1, int(ts.get("tile_h") or DEFAULT_TILE))
        return DEFAULT_TILE, DEFAULT_TILE

    def world_size(self) -> tuple[int, int]:
        """The level size: the window, or the largest tile layer / furthest object if bigger."""
        w, h = self.width, self.height
        for ly in self.layers:
            if ly.type == "tiles":
                tw, th = self.tile_size(ly)
                w, h = max(w, ly.cols * tw), max(h, ly.rows * th)
            elif ly.type == "sprites":
                for o in ly.objects:
                    w, h = max(w, int(o.x + o.w * o.scale)), max(h, int(o.y + o.h * o.scale))
        return w, h

    # ---- assets
    def asset_ids(self, kind: str) -> list[str]:
        return list(self.assets.get(kind, {}))

    def unique_asset_id(self, kind: str, base: str) -> str:
        base = re.sub(r"\W", "_", Path(base).stem).strip("_") or kind[:-1]
        taken = set().union(*(set(v) for v in self.assets.values() if isinstance(v, dict)))
        if base not in taken:
            return base
        i = 2
        while f"{base}{i}" in taken:
            i += 1
        return f"{base}{i}"


# ====================================================================== sprite sheets / animations
def sheet_grid(sheet: dict, image_w: int, image_h: int) -> tuple[int, int]:
    """Columns and rows of frames in a sprite sheet image."""
    fw, fh = max(1, int(sheet.get("frame_w") or 32)), max(1, int(sheet.get("frame_h") or 32))
    return max(1, image_w // fw), max(1, image_h // fh)


def frame_rect(sheet: dict, index: int, image_w: int) -> tuple[int, int, int, int]:
    """(x, y, w, h) of frame *index* (frames are numbered left to right, top to bottom)."""
    fw, fh = max(1, int(sheet.get("frame_w") or 32)), max(1, int(sheet.get("frame_h") or 32))
    cols = max(1, image_w // fw)
    return (index % cols) * fw, (index // cols) * fh, fw, fh


def animation_frame(anim: dict, t: float) -> int:
    """The sheet frame shown *t* seconds after an animation started (loop or stop on the last)."""
    frames = list(anim.get("frames") or [0])
    fps = float(anim.get("fps") or 8)
    step = int(t * fps) if fps > 0 else 0
    if anim.get("loop", True):
        return frames[step % len(frames)]
    return frames[min(step, len(frames) - 1)]


def first_frame(scene: Scene, obj: SceneObject) -> int:
    sheet = scene.assets.get("spritesheets", {}).get(obj.spritesheet)
    if not sheet:
        return 0
    anim = sheet.get("animations", {}).get(obj.animation) or next(iter(sheet.get("animations", {}).values()), None)
    return (anim.get("frames") or [0])[0] if anim else 0


# ====================================================================== events / handlers
def object_events(obj: SceneObject | None) -> list[str]:
    return list(SCENE_EVENTS) if obj is None else list(OBJECT_EVENTS.get(obj.kind, ["Click"]))


def default_event(obj: SceneObject | None) -> str:
    """The event a double-click opens (like VB's default event)."""
    if obj is None:
        return "Load"
    if obj.kind == "area":
        return "Collide"
    if obj.kind == "sprite" and obj.behaviours:
        return "Collide"
    return "Click"


def handler_name(scene: Scene, obj: SceneObject | None, event: str) -> str:
    return f"{'Scene' if obj is None else obj.name}_{event}"


# ====================================================================== validation
def validate(scene: Scene | dict) -> list[str]:
    """Problems of a scene (empty list = fine).  Accepts a Scene or the raw JSON dict."""
    probs: list[str] = []
    if isinstance(scene, dict):
        for k in ("name", "width", "height", "layers"):
            if k not in scene:
                probs.append(f"missing key '{k}'")
        try:
            scene = Scene.from_dict(scene)
        except Exception as e:  # noqa: BLE001
            return probs + [f"cannot read the scene: {e}"]
    if not re.match(r"^[A-Za-z_]\w*$", scene.name or ""):
        probs.append(f"scene name '{scene.name}' is not a valid identifier")
    if scene.width <= 0 or scene.height <= 0:
        probs.append("width and height must be positive")
    if scene.fps <= 0:
        probs.append("fps must be positive")
    if not re.match(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$", scene.background or ""):
        probs.append(f"background '{scene.background}' is not a #RRGGBB colour")
    seen_layers = set()
    seen = set()
    imgs, sheets = scene.assets.get("images", {}), scene.assets.get("spritesheets", {})
    tilesets, sounds = scene.assets.get("tilesets", {}), scene.assets.get("sounds", {})
    for sid, sh in sheets.items():
        if not sh.get("image"):
            probs.append(f"sprite sheet '{sid}' has no image")
        for an, a in (sh.get("animations") or {}).items():
            if not a.get("frames"):
                probs.append(f"animation '{sid}.{an}' has no frames")
    for tid, ts in tilesets.items():
        if not ts.get("image"):
            probs.append(f"tileset '{tid}' has no image")
    for ly in scene.layers:
        if ly.name in seen_layers:
            probs.append(f"duplicate layer name '{ly.name}'")
        seen_layers.add(ly.name)
        if ly.type == "tiles":
            if ly.tileset and ly.tileset not in tilesets:
                probs.append(f"layer '{ly.name}': unknown tileset '{ly.tileset}'")
            if len({len(r) for r in ly.data}) > 1:
                probs.append(f"layer '{ly.name}': rows of different length")
        for o in ly.objects:
            if not re.match(r"^[A-Za-z_]\w*$", o.name):
                probs.append(f"object name '{o.name}' is not a valid identifier")
            if o.name in seen:
                probs.append(f"duplicate object name '{o.name}'")
            seen.add(o.name)
            if o.image and o.image not in imgs:
                probs.append(f"{o.name}: unknown image '{o.image}'")
            if o.spritesheet:
                sh = sheets.get(o.spritesheet)
                if sh is None:
                    probs.append(f"{o.name}: unknown sprite sheet '{o.spritesheet}'")
                elif o.animation and o.animation not in (sh.get("animations") or {}):
                    probs.append(f"{o.name}: unknown animation '{o.animation}'")
            for b in o.behaviours:
                if b.get("type") not in BEHAVIOURS:
                    probs.append(f"{o.name}: unknown behaviour '{b.get('type')}'")
                if b.get("type") == "collectible" and b.get("sound") and b["sound"] not in sounds:
                    probs.append(f"{o.name}: unknown sound '{b['sound']}'")
    follow = scene.camera.get("follow")
    if follow and follow not in seen:
        probs.append(f"camera follows unknown sprite '{follow}'")
    return probs


# ====================================================================== helpers
def _num(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return v
    return float(v)


def _clean(v):
    """3.0 -> 3 (keeps the JSON tidy)."""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return round(v, 3) if isinstance(v, float) else v


def _tile(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return -1


def rename_in_code(code: str, old: str, new: str) -> str:
    """Rename `old_Event` handlers / references in the scene's user code."""
    return re.sub(rf"\b{re.escape(old)}(?=\b|_)", new, code)


__all__ = ["Scene", "Layer", "SceneObject", "BEHAVIOURS", "LAYER_TYPES", "OBJECT_KINDS", "SCENE_EVENTS",
           "OBJECT_EVENTS", "EVENT_ARGS", "validate", "sheet_grid", "frame_rect", "animation_frame",
           "first_frame", "object_events", "default_event", "handler_name", "rename_in_code", "DEFAULT_TILE"]
