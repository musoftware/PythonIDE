"""radgame - the RAD IDE game runtime for pygame-ce (copied into every game project).

It loads a ``<Scene>.scene`` file (JSON made by the scene designer, RAD IDE CONTRACTS 10.4), runs the
game loop at the scene fps, draws the layers (tile maps, sprites, UI), moves the sprites with their
Behaviours and calls your VB-style event handlers from ``<Scene>.py``::

    from radgame import *

    def Scene_Load():
        game.score = 0

    def Scene_KeyDown(key):            # key names: "left", "space", "a", "enter", "escape" ...
        if key == "escape":
            Quit()

    def Player_Collide(other):         # <Sprite>_Collide(other): the sprite touched another one
        if other.group == "Enemy":
            RestartScene()

Every object of the scene is a global of ``<Scene>.py`` by its name (``Player.x += 4``,
``Score.text = "..."``).  Handlers: ``Scene_Load``, ``Scene_Update(dt)``, ``Scene_KeyDown(key)``,
``Scene_KeyUp(key)``, ``Scene_MouseDown(x, y, button)``, ``Scene_MouseUp(x, y, button)``,
``Scene_Draw(screen)``, ``<Obj>_Click()``, ``<Obj>_Collide(other)``, ``<Obj>_AnimationEnd()``,
``<Obj>_OutOfWorld()`` and ``<Timer>_Tick()`` (``Game_`` and ``<SceneName>_`` work like ``Scene_``).
Objects called Coin1, Coin2 ... also fire ``Coin_Collide(other)`` (the group handler).

Endless games: give an object props ``template=1`` (it is not drawn and never collides) and make copies
with ``Spawn("Pipe", x, y)``; ``Destroy(obj)`` / the ``scroll`` behaviour remove them again.
``SaveData("best", n)`` / ``LoadData("best", 0)`` keep values after the game closes (savegame.json),
``EnableBehaviour("scroll", False)`` or ``obj.enable("flap", False)`` pause behaviours, props
``hitbox=6`` makes the collision box 6 px smaller than the picture on every side.

Run: ``python main.py`` (main.py calls ``radgame.run("Level1")``).  Environment variables for tests:
RADGAME_FRAMES=n quits after n frames, RADGAME_SCREENSHOT=file.png saves the last frame,
RADGAME_FIXED_DT=1 uses a fixed time step of 1/fps, RADGAME_KEYS="space:30-32" holds keys between frames,
RADGAME_SHOTS="60:a.png,200:b.png" saves screenshots at those frames, RADGAME_SAVE=file for SaveData.
"""
from __future__ import annotations

import importlib
import inspect
import json
import math
import os
import random as _random
import re
import sys
from pathlib import Path

import pygame

__version__ = "1.0"

ACTOR_BEHAVIOURS = ("platformer", "keyboard_move", "top_down", "follow_mouse")
_KEY_ALIASES = {"return": "enter", "keypad enter": "enter", "left shift": "shift", "right shift": "shift",
                "left ctrl": "ctrl", "right ctrl": "ctrl", "left alt": "alt", "right alt": "alt"}
_DIRS = {"left": ("left", "a"), "right": ("right", "d"), "up": ("up", "w"), "down": ("down", "s")}
_JUMP_KEYS = ("up", "w", "space")


def _color(value, default=(255, 255, 255)):
    """'#RRGGBB' / '#RRGGBBAA' / (r, g, b) / colour name -> pygame.Color."""
    if value is None or value == "":
        return pygame.Color(*default)
    if isinstance(value, (tuple, list)):
        return pygame.Color(*value)
    try:
        return pygame.Color(str(value))
    except (ValueError, TypeError):
        return pygame.Color(*default)


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


# ====================================================================== input
class Input:
    """Keyboard and mouse state. ``held`` = keys down now, ``pressed`` = went down this frame.
    Tests (and replays) drive it with ``press(name)`` / ``release(name)``."""

    def __init__(self):
        self.held: set[str] = set()
        self.pressed: set[str] = set()
        self.released: set[str] = set()
        self.mouse = (0, 0)
        self.buttons: set[int] = set()
        self.clicked = False             # a mouse button went down this frame
        self._queue: list[tuple[str, tuple]] = []

    # scripted input
    def press(self, key: str):
        key = key.lower()
        if key not in self.held:
            self.held.add(key)
            self.pressed.add(key)
            self._queue.append(("KeyDown", (key,)))

    def release(self, key: str):
        key = key.lower()
        if key in self.held:
            self.held.discard(key)
            self.released.add(key)
            self._queue.append(("KeyUp", (key,)))

    def click(self, x: int, y: int, button: int = 1):
        self.mouse = (int(x), int(y))
        self.clicked = True
        self._queue.append(("MouseDown", (int(x), int(y), button)))
        self._queue.append(("MouseUp", (int(x), int(y), button)))

    def move_mouse(self, x: int, y: int):
        self.mouse = (int(x), int(y))

    # queries
    def down(self, *keys: str) -> bool:
        return any(k.lower() in self.held for k in keys)

    def hit(self, *keys: str) -> bool:
        return any(k.lower() in self.pressed for k in keys)

    def axis(self, neg: tuple, pos: tuple) -> int:
        return int(self.down(*pos)) - int(self.down(*neg))

    def _new_frame(self):
        self.pressed.clear()
        self.released.clear()
        self.clicked = False

    @staticmethod
    def key_name(key: int) -> str:
        name = pygame.key.name(key).lower()
        return _KEY_ALIASES.get(name, name)


# ====================================================================== objects
class GameObject:
    """Anything placed in a scene: sprite, text or area. Position = top-left corner in world pixels."""

    kind = "object"

    def __init__(self, scene: "Scene", d: dict, layer: "Layer"):
        self.scene = scene
        self.layer = layer
        self.name = str(d.get("name") or "Object")
        self.x = _num(d.get("x"))
        self.y = _num(d.get("y"))
        self.w = _num(d.get("w"))
        self.h = _num(d.get("h"))
        self.scale = _num(d.get("scale", 1), 1) or 1.0
        self.rotation = _num(d.get("rotation"))
        self.z = int(_num(d.get("z")))
        self.visible = bool(d.get("visible", True))
        self.props = dict(d.get("props") or {})
        self.behaviours = [dict(b) for b in (d.get("behaviours") or []) if isinstance(b, dict)]
        self.group = str(self.props.get("group") or re.sub(r"\d+$", "", self.name) or self.name)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.alive = True
        self.flip_x = False
        self.start = (self.x, self.y)
        self.data: dict = {}             # your own values: Player.data["lives"] = 3
        self._state: dict = {}
        # props "template=1": a spawn template - not drawn, not moved, never collides; Spawn(name) copies it
        self.template = str(self.props.get("template", "")).lower() in ("1", "true", "yes", "on")
        self.spawned = False             # made at run time by Spawn / Clone (removed when destroyed)
        self.hitbox = _num(self.props.get("hitbox"), 0)    # props "hitbox=6": collide 6 px inside the edges

    # ---- geometry
    @property
    def width(self) -> float:
        return self.w * self.scale

    @property
    def height(self) -> float:
        return self.h * self.scale

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), max(1, round(self.width)), max(1, round(self.height)))

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def hit_rect(self) -> pygame.Rect:
        """The rectangle used for collisions: ``rect`` shrunk by props ``hitbox`` pixels on every side."""
        r = self.rect
        k = int(self.hitbox)
        if k > 0 and r.width > 2 * k and r.height > 2 * k:
            r = r.inflate(-2 * k, -2 * k)
        return r

    def overlaps(self, other: "GameObject") -> bool:
        return self.alive and other.alive and self.hit_rect.colliderect(other.hit_rect)

    def contains(self, x: float, y: float) -> bool:
        return self.rect.collidepoint(x, y)

    def move_to(self, x: float, y: float):
        self.x, self.y = float(x), float(y)

    def distance_to(self, other: "GameObject") -> float:
        (ax, ay), (bx, by) = self.center, other.center
        return math.hypot(ax - bx, ay - by)

    # ---- behaviours
    def has(self, behaviour: str) -> bool:
        return any(b.get("type") == behaviour for b in self.behaviours)

    def behaviour(self, behaviour: str) -> dict | None:
        return next((b for b in self.behaviours if b.get("type") == behaviour), None)

    def enable(self, behaviour: str, on: bool = True):
        """Switch a behaviour on or off (``Player.enable("flap", False)``) without removing it."""
        for b in self.behaviours:
            if b.get("type") == behaviour:
                b["enabled"] = bool(on)

    def enabled(self, behaviour: str) -> bool:
        b = self.behaviour(behaviour)
        return b is not None and b.get("enabled", True) is not False

    @property
    def solid(self) -> bool:
        return self.alive and not self.template and self.has("solid")

    def destroy(self):
        """Remove the object from the scene (a collected coin, a defeated enemy)."""
        self.alive = False
        self.visible = False

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    # ---- drawing (overridden)
    def update_animation(self, dt: float):
        pass

    def draw(self, surf: pygame.Surface, ox: float, oy: float):
        pass

    def __repr__(self):
        return f"<{type(self).__name__} {self.name} at ({self.x:.0f}, {self.y:.0f})>"


class Sprite(GameObject):
    """An image or an animated sprite sheet. ``play("run")`` switches the animation."""

    kind = "sprite"

    def __init__(self, scene, d, layer):
        super().__init__(scene, d, layer)
        self.image_id = str(d.get("image") or "")
        self.sheet_id = str(d.get("spritesheet") or "")
        self.animation = str(d.get("animation") or "")
        self.color = _color(self.props.get("color") or self.props.get("BackColor"), (230, 80, 80))
        self.anim_time = 0.0
        self.anim_done = False
        self._frames: list[pygame.Surface] = []
        self._cache: dict = {}
        sheet = scene.sheets.get(self.sheet_id)
        if sheet is not None:
            self._frames = sheet["frames"]
            if not self.animation or self.animation not in sheet["animations"]:
                self.animation = next(iter(sheet["animations"]), "")
            if not self.w or not self.h:
                self.w, self.h = sheet["frame_w"], sheet["frame_h"]
        elif self.image_id in scene.images:
            img = scene.images[self.image_id]
            self._frames = [img]
            if not self.w or not self.h:
                self.w, self.h = img.get_size()
        if not self.w or not self.h:
            self.w, self.h = self.w or 32, self.h or 32

    def play(self, animation: str, restart: bool = False):
        """Show animation *animation* of the sprite sheet (nothing happens if it does not exist)."""
        sheet = self.scene.sheets.get(self.sheet_id)
        if sheet is None or animation not in sheet["animations"]:
            return
        if animation != self.animation or restart:
            self.animation = animation
            self.anim_time = 0.0
            self.anim_done = False

    def has_animation(self, animation: str) -> bool:
        sheet = self.scene.sheets.get(self.sheet_id)
        return sheet is not None and animation in sheet["animations"]

    def set_image(self, image_id: str):
        img = self.scene.images.get(image_id)
        if img is not None:
            self.image_id, self.sheet_id = image_id, ""
            self._frames = [img]

    def _frame_index(self) -> int:
        sheet = self.scene.sheets.get(self.sheet_id)
        if sheet is None:
            return 0
        anim = sheet["animations"].get(self.animation)
        if not anim:
            return 0
        frames = list(anim.get("frames") or [0])
        fps = _num(anim.get("fps", 8), 8)
        step = int(self.anim_time * fps) if fps > 0 else 0
        if anim.get("loop", True):
            return frames[step % len(frames)]
        return frames[min(step, len(frames) - 1)]

    def update_animation(self, dt: float):
        sheet = self.scene.sheets.get(self.sheet_id)
        if sheet is None:
            return
        self.anim_time += dt
        anim = sheet["animations"].get(self.animation)
        if anim and not anim.get("loop", True) and not self.anim_done:
            fps = _num(anim.get("fps", 8), 8)
            if fps > 0 and self.anim_time * fps >= len(anim.get("frames") or [0]):
                self.anim_done = True
                self.scene.game._fire_object(self, "AnimationEnd")

    def current_surface(self) -> pygame.Surface | None:
        if not self._frames:
            return None
        idx = self._frame_index()
        base = self._frames[idx % len(self._frames)]
        size = (max(1, round(self.width)), max(1, round(self.height)))
        key = (id(base), size, self.flip_x, round(self.rotation, 1))
        surf = self._cache.get(key)
        if surf is None:
            surf = base if base.get_size() == size else pygame.transform.scale(base, size)
            if self.flip_x:
                surf = pygame.transform.flip(surf, True, False)
            if self.rotation:
                surf = pygame.transform.rotate(surf, -self.rotation)
            if len(self._cache) > 256:
                self._cache.clear()
            self._cache[key] = surf
        return surf

    def draw(self, surf, ox, oy):
        img = self.current_surface()
        if img is None:
            r = self.rect.move(-round(ox), -round(oy))
            pygame.draw.rect(surf, self.color, r)
            return
        cx, cy = self.center
        r = img.get_rect(center=(round(cx - ox), round(cy - oy)))
        surf.blit(img, r)


class TextObject(GameObject):
    """A label. ``{score}``, ``{lives}``, ``{level}`` and ``{<any game.vars key>}`` are filled in."""

    kind = "text"

    def __init__(self, scene, d, layer):
        super().__init__(scene, d, layer)
        self.text = str(d.get("text", self.props.get("Text", "")) or "")
        self.font_size = int(_num(self.props.get("FontSize", 24), 24))
        self.font_name = self.props.get("FontName") or None
        self.bold = bool(self.props.get("FontBold"))
        self.color = _color(self.props.get("ForeColor") or self.props.get("color"), (255, 255, 255))
        self.align = str(self.props.get("Align") or self.props.get("TextAlign") or "left").lower()
        self._font = None
        self._rendered = (None, None)

    def display_text(self) -> str:
        g = self.scene.game
        values = {"score": g.score, "lives": g.lives, "level": self.scene.name, **g.vars}
        try:
            return self.text.format_map(_SafeDict(values))
        except (ValueError, IndexError):
            return self.text

    def _surface(self):
        if self._font is None:
            try:
                self._font = pygame.font.SysFont(self.font_name, self.font_size, bold=self.bold) \
                    if self.font_name else pygame.font.Font(None, round(self.font_size * 1.35))
            except Exception:  # noqa: BLE001 - fall back to the default font
                self._font = pygame.font.Font(None, round(self.font_size * 1.35))
        text = self.display_text()
        key = (text, tuple(self.color))
        if self._rendered[0] != key:
            self._rendered = (key, self._font.render(text, True, self.color))
        surf = self._rendered[1]
        if not self.w or not self.h:
            self.w, self.h = surf.get_size()
        return surf

    def draw(self, surf, ox, oy):
        img = self._surface()
        x = self.x - ox
        if self.align in ("center", "middlecenter", "topcenter"):
            x += (self.width - img.get_width()) / 2
        elif self.align in ("right", "middleright", "topright"):
            x += self.width - img.get_width()
        shadow = self.props.get("Shadow")           # props "Shadow=#000000": a drop shadow (readable on any sky)
        if shadow:
            key = ("shadow", img.get_size(), self._rendered[0], str(shadow))
            if getattr(self, "_shadow", (None,))[0] != key:
                self._shadow = (key, self._font.render(self.display_text(), True, _color(shadow, (0, 0, 0))))
            d = max(1, round(self.font_size / 12))
            surf.blit(self._shadow[1], (round(x) + d, round(self.y - oy) + d))
        surf.blit(img, (round(x), round(self.y - oy)))


class Area(GameObject):
    """An invisible rectangle: a goal, a trigger, a kill zone (its Collide event fires)."""

    kind = "area"

    def draw(self, surf, ox, oy):
        if self.scene.game.debug:
            pygame.draw.rect(surf, (255, 255, 0), self.rect.move(-round(ox), -round(oy)), 1)


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


# ====================================================================== layers
class Layer:
    def __init__(self, scene: "Scene", d: dict):
        self.scene = scene
        self.name = str(d.get("name") or "Layer")
        self.type = str(d.get("type") or "sprites")
        self.visible = bool(d.get("visible", True))
        self.collision = bool(d.get("collision", False))
        self.tileset_id = str(d.get("tileset") or "")
        self.data = [[int(_num(v, -1)) for v in row] for row in (d.get("data") or [])]
        ts = scene.tilesets.get(self.tileset_id)
        self.tile_w = ts["tile_w"] if ts else 32
        self.tile_h = ts["tile_h"] if ts else 32
        self.objects: list[GameObject] = []
        self._cache = None

    @property
    def screen_space(self) -> bool:
        return self.type == "ui"

    @property
    def cols(self) -> int:
        return max((len(r) for r in self.data), default=0)

    @property
    def rows(self) -> int:
        return len(self.data)

    def tile_at(self, col: int, row: int) -> int:
        if 0 <= row < len(self.data) and 0 <= col < len(self.data[row]):
            return self.data[row][col]
        return -1

    def set_tile(self, col: int, row: int, tile: int):
        """Change one cell while the game runs (break a block, open a door)."""
        if 0 <= row < len(self.data) and 0 <= col < len(self.data[row]):
            self.data[row][col] = int(tile)
            self._cache = None

    def tile_at_point(self, x: float, y: float) -> int:
        return self.tile_at(int(x // self.tile_w), int(y // self.tile_h))

    def solid_rects(self, rect: pygame.Rect) -> list[pygame.Rect]:
        """Rectangles of the non-empty cells this rect touches (collision layers only)."""
        if not self.collision or self.type != "tiles":
            return []
        out = []
        c0, c1 = max(0, rect.left // self.tile_w), (rect.right - 1) // self.tile_w
        r0, r1 = max(0, rect.top // self.tile_h), (rect.bottom - 1) // self.tile_h
        for r in range(r0, min(r1, self.rows - 1) + 1):
            row = self.data[r]
            for c in range(c0, min(c1, len(row) - 1) + 1):
                if row[c] >= 0:
                    out.append(pygame.Rect(c * self.tile_w, r * self.tile_h, self.tile_w, self.tile_h))
        return out

    def _render(self) -> pygame.Surface | None:
        ts = self.scene.tilesets.get(self.tileset_id)
        surf = pygame.Surface((max(1, self.cols * self.tile_w), max(1, self.rows * self.tile_h)), pygame.SRCALPHA)
        for r, row in enumerate(self.data):
            for c, t in enumerate(row):
                if t < 0:
                    continue
                pos = (c * self.tile_w, r * self.tile_h)
                if ts and t < len(ts["tiles"]):
                    surf.blit(ts["tiles"][t], pos)
                else:
                    pygame.draw.rect(surf, (120, 90, 60), (*pos, self.tile_w, self.tile_h))
        return surf

    def draw(self, surf, ox, oy):
        if not self.visible:
            return
        if self.type == "tiles":
            if self._cache is None:
                self._cache = self._render()
            sw, sh = surf.get_size()
            area = pygame.Rect(round(ox), round(oy), sw, sh)
            surf.blit(self._cache, (0, 0), area)
            return
        if self.screen_space:
            ox = oy = 0
        for o in sorted(self.objects, key=lambda o: o.z):
            if o.visible and o.alive and not o.template:
                o.draw(surf, ox, oy)


# ====================================================================== camera
class Camera:
    def __init__(self, scene: "Scene", d: dict):
        self.scene = scene
        self.follow: str | None = d.get("follow") or None
        self.x = _num(d.get("x"))
        self.y = _num(d.get("y"))

    def update(self):
        target = self.scene.objects.get(self.follow) if self.follow else None
        vw, vh = self.scene.view_size
        if target is not None:
            cx, cy = target.center
            self.x, self.y = cx - vw / 2, cy - vh / 2
        ww, wh = self.scene.world_size
        self.x = max(0.0, min(self.x, ww - vw))
        self.y = max(0.0, min(self.y, wh - vh))

    def to_world(self, x: float, y: float) -> tuple[float, float]:
        return x + self.x, y + self.y

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return x - self.x, y - self.y


# ====================================================================== timers
class Timer:
    """``<Name>_Tick()`` fires every *interval* milliseconds while *enabled*."""

    def __init__(self, name: str, interval: float = 1000, enabled: bool = True):
        self.name = name
        self.interval = float(interval)
        self.enabled = bool(enabled)
        self._acc = 0.0

    def start(self):
        self.enabled = True
        self._acc = 0.0

    def stop(self):
        self.enabled = False


# ====================================================================== scene
class Scene:
    def __init__(self, game: "Game", name: str, data: dict):
        self.game = game
        self.data = data
        self.name = str(data.get("name") or name)
        self.width = int(_num(data.get("width", 800), 800))
        self.height = int(_num(data.get("height", 600), 600))
        self.fps = max(1, int(_num(data.get("fps", 60), 60)))
        self.gravity = _num(data.get("gravity", 900), 900)
        self.background = data.get("background") or "#6EC1E4"
        self.images: dict[str, pygame.Surface] = {}
        self.sounds: dict[str, str] = {}
        self.sheets: dict[str, dict] = {}
        self.tilesets: dict[str, dict] = {}
        self._load_assets(data.get("assets") or {})
        self.layers = [Layer(self, ld) for ld in (data.get("layers") or []) if isinstance(ld, dict)]
        self.objects: dict[str, GameObject] = {}
        for ly, ld in zip(self.layers, [d for d in (data.get("layers") or []) if isinstance(d, dict)]):
            for od in ld.get("objects") or []:
                self.add_object(od, ly)
        self.camera = Camera(self, data.get("camera") or {})
        self.timers: dict[str, Timer] = {}
        for td in data.get("timers") or []:
            t = Timer(str(td.get("name") or "Timer1"), _num(td.get("interval", 1000), 1000),
                      bool(td.get("enabled", True)))
            self.timers[t.name] = t
        self.view_size = (self.width, self.height)
        self.world_size = self._world_size()
        self.camera.update()

    # ---- assets
    def _path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.game.folder / p

    def _image(self, rel: str) -> pygame.Surface | None:
        try:
            img = pygame.image.load(str(self._path(rel)))
            return img.convert_alpha() if pygame.display.get_surface() is not None else img
        except (pygame.error, FileNotFoundError) as e:
            print(f"radgame: cannot load image {rel}: {e}", file=sys.stderr)
            return None

    def _load_assets(self, a: dict):
        for iid, rel in (a.get("images") or {}).items():
            img = self._image(rel)
            if img is not None:
                self.images[iid] = img
        for sid, rel in (a.get("sounds") or {}).items():
            self.sounds[sid] = str(self._path(rel))
        for sid, sh in (a.get("spritesheets") or {}).items():
            img = self._image(sh.get("image", ""))
            fw, fh = int(_num(sh.get("frame_w", 32), 32)), int(_num(sh.get("frame_h", 32), 32))
            frames = _slice(img, fw, fh) if img is not None else []
            anims = dict(sh.get("animations") or {})
            if not anims and frames:
                anims = {"default": {"frames": list(range(len(frames))), "fps": 8, "loop": True}}
            self.sheets[sid] = {"frames": frames, "frame_w": fw, "frame_h": fh, "animations": anims}
        for tid, ts in (a.get("tilesets") or {}).items():
            img = self._image(ts.get("image", ""))
            tw, th = int(_num(ts.get("tile_w", 32), 32)), int(_num(ts.get("tile_h", 32), 32))
            self.tilesets[tid] = {"tiles": _slice(img, tw, th) if img is not None else [], "tile_w": tw, "tile_h": th}

    def _world_size(self) -> tuple[int, int]:
        w, h = self.width, self.height
        world = self.data.get("world") or {}
        w, h = max(w, int(_num(world.get("width"), 0))), max(h, int(_num(world.get("height"), 0)))
        for ly in self.layers:
            if ly.type == "tiles":
                w, h = max(w, ly.cols * ly.tile_w), max(h, ly.rows * ly.tile_h)
        return w, h

    # ---- objects
    def add_object(self, d: dict, layer: Layer) -> GameObject:
        kind = d.get("kind", "sprite")
        cls = {"text": TextObject, "area": Area}.get(kind, Sprite)
        obj = cls(self, d, layer)
        base, i = obj.name, 2
        while obj.name in self.objects:
            obj.name = f"{base}_{i}"
            i += 1
        layer.objects.append(obj)
        self.objects[obj.name] = obj
        return obj

    def all_objects(self):
        for ly in self.layers:
            yield from ly.objects

    def live_objects(self):
        """Objects taking part in the game (not destroyed, not spawn templates)."""
        return [o for o in self.all_objects() if o.alive and not o.template]

    def remove_object(self, obj: GameObject):
        """Take *obj* out of the scene for good (spawned objects are removed like this when destroyed)."""
        obj.alive = obj.visible = False
        if obj in obj.layer.objects:
            obj.layer.objects.remove(obj)
        if self.objects.get(obj.name) is obj:
            del self.objects[obj.name]

    def purge(self):
        """Remove destroyed run-time objects (Spawn / Clone) so endless games do not slow down."""
        for ly in self.layers:
            if any(o.spawned and not o.alive for o in ly.objects):
                for o in [o for o in ly.objects if o.spawned and not o.alive]:
                    self.remove_object(o)

    def solid_tile_layers(self) -> list[Layer]:
        return [ly for ly in self.layers if ly.type == "tiles" and ly.collision]

    def blockers(self, rect: pygame.Rect, ignore: GameObject | None = None) -> list[pygame.Rect]:
        out = []
        for ly in self.solid_tile_layers():
            out += ly.solid_rects(rect)
        for o in self.all_objects():
            if o is not ignore and o.solid and not o.layer.screen_space:
                r = o.rect
                if r.colliderect(rect):
                    out.append(r)
        return out

    def is_solid_at(self, x: float, y: float, ignore: GameObject | None = None) -> bool:
        return bool(self.blockers(pygame.Rect(int(x), int(y), 1, 1), ignore))


def _slice(img: pygame.Surface, fw: int, fh: int) -> list[pygame.Surface]:
    fw, fh = max(1, fw), max(1, fh)
    cols, rows = max(1, img.get_width() // fw), max(1, img.get_height() // fh)
    return [img.subsurface(pygame.Rect(c * fw, r * fh, min(fw, img.get_width()), min(fh, img.get_height())))
            for r in range(rows) for c in range(cols)]


# ====================================================================== movement
def move_and_collide(obj: GameObject, dx: float, dy: float) -> tuple[bool, bool]:
    """Move *obj* by (dx, dy), stopping at solid tiles and solid sprites.
    Returns (hit_x, hit_y). Moves in small steps so fast objects do not tunnel."""
    scene = obj.scene
    hit_x = hit_y = False
    steps = max(1, int(max(abs(dx), abs(dy)) // 8) + 1)
    sx, sy = dx / steps, dy / steps
    for _ in range(steps):
        if sx and not hit_x:
            obj.x += sx
            r = obj.rect
            for b in scene.blockers(r, obj):
                if r.colliderect(b):
                    obj.x = (b.left - obj.width) if sx > 0 else float(b.right)
                    hit_x = True
                    r = obj.rect
        if sy and not hit_y:
            obj.y += sy
            r = obj.rect
            for b in scene.blockers(r, obj):
                if r.colliderect(b):
                    obj.y = (b.top - obj.height) if sy > 0 else float(b.bottom)
                    hit_y = True
                    r = obj.rect
    return hit_x, hit_y


def _standing(obj: GameObject) -> bool:
    r = obj.rect
    probe = pygame.Rect(r.left + 1, r.bottom, max(1, r.width - 2), 1)
    return bool(obj.scene.blockers(probe, obj))


def _keys(b: dict, direction: str) -> tuple:
    which = str(b.get("keys", "both")).lower()
    arrows, wasd = _DIRS[direction]
    return {"arrows": (arrows,), "wasd": (wasd,)}.get(which, (arrows, wasd))


def _auto_anim(o: GameObject, *names: str):
    if isinstance(o, Sprite):
        for n in names:
            if o.has_animation(n):
                o.play(n)
                return


class Behaviours:
    """The built-in behaviours of CONTRACTS 10.4. Each is a function (game, obj, params, dt)."""

    @staticmethod
    def keyboard_move(g: "Game", o: GameObject, b: dict, dt: float):
        speed = _num(b.get("speed", 200), 200)
        ix = g.input.axis(_keys(b, "left"), _keys(b, "right"))
        iy = g.input.axis(_keys(b, "up"), _keys(b, "down"))
        axis = str(b.get("axis", "both")).lower()
        if axis == "x":
            iy = 0
        elif axis == "y":
            ix = 0
        if ix and iy:
            ix, iy = ix * 0.7071, iy * 0.7071
        o.vx, o.vy = ix * speed, iy * speed
        if ix:
            o.flip_x = ix < 0
        move_and_collide(o, o.vx * dt, o.vy * dt)
        g._clamp_to_world(o)

    @staticmethod
    def top_down(g: "Game", o: GameObject, b: dict, dt: float):
        speed = _num(b.get("speed", 180), 180)
        ix = g.input.axis(_keys(b, "left"), _keys(b, "right"))
        iy = g.input.axis(_keys(b, "up"), _keys(b, "down"))
        if b.get("four_way") and ix and iy:
            iy = 0
        n = math.hypot(ix, iy) or 1.0
        o.vx, o.vy = ix / n * speed, iy / n * speed
        move_and_collide(o, o.vx * dt, o.vy * dt)
        g._clamp_to_world(o)
        if ix or iy:
            if b.get("rotate"):
                o.rotation = math.degrees(math.atan2(iy, ix))
            d = ("right" if ix > 0 else "left") if abs(ix) >= abs(iy) else ("down" if iy > 0 else "up")
            o._state["facing"] = d
            if not b.get("rotate"):
                if ix:
                    o.flip_x = ix < 0 and not (isinstance(o, Sprite) and o.has_animation("walk_left"))
            _auto_anim(o, f"walk_{d}", d, "walk", "run")
        else:
            _auto_anim(o, f"idle_{o._state.get('facing', 'down')}", "idle")

    @staticmethod
    def platformer(g: "Game", o: GameObject, b: dict, dt: float):
        speed = _num(b.get("speed", 220), 220)
        jump = _num(b.get("jump", 520), 520)
        gravity = _num(b.get("gravity", g.scene.gravity or 900), 900)
        max_fall = _num(b.get("max_fall", 900), 900)
        jumps = int(_num(b.get("jumps", 1), 1))
        st = o._state
        ix = g.input.axis(_keys(b, "left"), _keys(b, "right"))
        o.vx = ix * speed
        if ix:
            o.flip_x = ix < 0
        st["coyote"] = 0.1 if o.on_ground else max(0.0, st.get("coyote", 0.0) - dt)
        if o.on_ground:
            st["jumps_left"] = jumps
        jump_keys = tuple(k for k in _JUMP_KEYS if k in _keys(b, "up") or k == "space")
        if g.input.hit(*jump_keys):
            st["buffer"] = 0.12
        else:
            st["buffer"] = max(0.0, st.get("buffer", 0.0) - dt)
        if st["buffer"] > 0 and (st["coyote"] > 0 or st.get("jumps_left", 0) > 0):
            o.vy = -jump
            st["buffer"] = 0.0
            st["coyote"] = 0.0
            st["jumps_left"] = st.get("jumps_left", jumps) - 1
            o.on_ground = False
            g._fire_object(o, "Jump")
        if o.vy < 0 and not g.input.down(*jump_keys):
            o.vy += gravity * dt * 1.5          # short hop when the key is released early
        o.vy = min(o.vy + gravity * dt, max_fall)
        hit_x, hit_y = move_and_collide(o, o.vx * dt, o.vy * dt)
        if hit_y:
            o.vy = 0.0
        o.on_ground = _standing(o) and o.vy >= 0
        o.x = max(0.0, min(o.x, g.scene.world_size[0] - o.width))
        if o.on_ground:
            _auto_anim(o, "run", "walk") if ix else _auto_anim(o, "idle")
        else:
            _auto_anim(o, "jump", "fall") if o.vy < 0 else _auto_anim(o, "fall", "jump")

    @staticmethod
    def bounce(g: "Game", o: GameObject, b: dict, dt: float):
        st = o._state
        if "init" not in st:
            st["init"] = True
            if "speed" in b and "vx" not in b:
                ang = math.radians(_num(b.get("angle", 45), 45))
                sp = _num(b.get("speed"), 200)
                o.vx, o.vy = math.cos(ang) * sp, math.sin(ang) * sp
            else:
                o.vx, o.vy = _num(b.get("vx", 150), 150), _num(b.get("vy", 150), 150)
        hit_x, hit_y = move_and_collide(o, o.vx * dt, o.vy * dt)
        ww, wh = g.scene.world_size
        if o.x < 0 or o.right > ww:
            o.x = max(0.0, min(o.x, ww - o.width))
            hit_x = True
        if o.y < 0 or o.bottom > wh:
            o.y = max(0.0, min(o.y, wh - o.height))
            hit_y = True
        if hit_x:
            o.vx = -o.vx
        if hit_y:
            o.vy = -o.vy
        if hit_x or hit_y:
            g._fire_object(o, "Bounce")

    @staticmethod
    def follow_mouse(g: "Game", o: GameObject, b: dict, dt: float):
        mx, my = g.input.mouse
        if not o.layer.screen_space:
            mx, my = g.scene.camera.to_world(mx, my)
        tx, ty = mx - o.width / 2, my - o.height / 2
        axis = str(b.get("axis", "both")).lower()
        if axis == "x":
            ty = o.y
        elif axis == "y":
            tx = o.x
        speed = _num(b.get("speed", 0), 0)
        if speed <= 0:
            o.x, o.y = tx, ty
            return
        dx, dy = tx - o.x, ty - o.y
        dist = math.hypot(dx, dy)
        if dist > 0.5:
            step = min(dist, speed * dt)
            o.x += dx / dist * step
            o.y += dy / dist * step

    @staticmethod
    def enemy_patrol(g: "Game", o: GameObject, b: dict, dt: float):
        st = o._state
        speed = _num(b.get("speed", 80), 80)
        distance = _num(b.get("distance", 160), 160)
        axis = str(b.get("axis", "x")).lower()
        if "dir" not in st:
            st["dir"] = -1 if b.get("start_left") else 1
            st["origin"] = o.x if axis == "x" else o.y
        d = st["dir"]
        if axis == "y":
            _hx, hy = move_and_collide(o, 0, d * speed * dt)
            pos = o.y
            turn = hy
        else:
            gravity = g.scene.gravity if b.get("gravity", True) else 0
            if gravity:
                o.vy = min(o.vy + gravity * dt, 900)
                _hx0, hit_y = move_and_collide(o, 0, o.vy * dt)
                if hit_y:
                    o.vy = 0.0
                o.on_ground = _standing(o)
            hx, _hy = move_and_collide(o, d * speed * dt, 0)
            pos = o.x
            turn = hx
            if o.on_ground and b.get("turn_at_edges", True):       # do not walk off a ledge
                fx = o.right + 1 if d > 0 else o.x - 1
                if not g.scene.is_solid_at(fx, o.bottom + 2, o):
                    turn = True
            o.flip_x = d < 0 if not b.get("flip_reverse") else d > 0
            _auto_anim(o, "walk", "run")
        if distance > 0 and abs(pos - st["origin"]) >= distance and (pos - st["origin"]) * d > 0:
            turn = True
        if turn:
            st["dir"] = -d
        o.vx = st["dir"] * speed if axis == "x" else 0.0

    @staticmethod
    def flap(g: "Game", o: GameObject, b: dict, dt: float):
        """Falls with gravity; a key (default Space / Up / W) or a mouse click gives an upward kick
        (fires ``<Obj>_Flap()``). ``tilt`` turns the sprite with its speed (nose up / nose down)."""
        gravity = _num(b.get("gravity", g.scene.gravity or 900), 900)
        kick = _num(b.get("flap", 320), 320)
        max_fall = _num(b.get("max_fall", 600), 600)
        keys = tuple(k.strip().lower() for k in str(b.get("keys", "space,up,w")).split(",") if k.strip())
        if g.input.hit(*keys) or (b.get("mouse", True) and g.input.clicked):
            o.vy = -kick
            g._fire_object(o, "Flap")
        o.vy = min(o.vy + gravity * dt, max_fall)
        o.y += o.vy * dt
        if b.get("ceiling", True) and o.y < 0:
            o.y, o.vy = 0.0, max(0.0, o.vy)
        if b.get("tilt", True):
            target = max(-25.0, min(80.0, o.vy * 0.15))
            o.rotation += (target - o.rotation) * min(1.0, dt * 12)

    @staticmethod
    def scroll(g: "Game", o: GameObject, b: dict, dt: float):
        """Moves at a constant speed (default to the left) - obstacles, ground strips, parallax scenery.
        ``wrap``: when it has left the window it jumps ahead by the width of all the objects of its group
        (put 2 or more copies side by side for an endless strip); otherwise it is destroyed off screen."""
        speed = _num(b.get("speed", 120), 120)
        direction = str(b.get("direction", "left")).lower()
        dx, dy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}.get(direction, (-1, 0))
        o.x += dx * speed * dt
        o.y += dy * speed * dt
        cam = g.scene.camera
        vw, vh = g.scene.view_size
        if o.layer.screen_space:
            left, top = 0.0, 0.0
        else:
            left, top = cam.x, cam.y
        gone = (dx < 0 and o.right < left) or (dx > 0 and o.x > left + vw) or \
            (dy < 0 and o.bottom < top) or (dy > 0 and o.y > top + vh)
        if not gone:
            return
        wrap = b.get("wrap")
        if wrap:
            if not isinstance(wrap, bool) and _num(wrap, 0) > 1:      # wrap = a distance in pixels
                dist = _num(wrap)
            else:
                mates = [m for m in o.layer.objects if m.alive and not m.template and m.group == o.group]
                dist = sum(m.width if dx else m.height for m in mates)
            o.x -= dx * dist
            o.y -= dy * dist
        elif b.get("destroy", True):
            o.destroy()

    @staticmethod
    def solid(g, o, b, dt):          # blocking is handled by Scene.blockers
        pass

    @staticmethod
    def collectible(g, o, b, dt):    # handled in Game._collisions
        pass


# ====================================================================== game
class Game:
    """The running game: ``game.score``, ``game.lives``, ``game.vars``, ``game.scene``, ``game.input``."""

    def __init__(self, folder=None, title: str = "", size: tuple[int, int] | None = None,
                 headless: bool | None = None):
        self.folder = Path(folder) if folder else _main_folder()
        self.title = title
        self.size = size
        self.score = 0
        self.lives = 3
        self.vars: dict = {}
        self.debug = bool(os.environ.get("RADGAME_DEBUG"))
        self.input = Input()
        self.scene: Scene | None = None
        self.module = None
        self.screen: pygame.Surface | None = None
        self.frame = 0
        self.time = 0.0
        self.running = False
        self.events: list[tuple] = []          # (frame, handler, args) of every fired event (tests)
        self._pending_scene: str | None = None
        self._touching: set[tuple[str, str]] = set()
        self._sig_cache: dict = {}
        self._message = ("", 0.0)
        self._music = None
        self._sounds: dict[str, object] = {}
        self._audio = False
        if headless is None:
            headless = os.environ.get("SDL_VIDEODRIVER") == "dummy"
        self.headless = headless
        global _current
        _current = self

    # ---- setup
    def _init_pygame(self, w: int, h: int):
        if not pygame.get_init():
            pygame.init()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._audio = True
        except pygame.error:
            self._audio = False
        if self.screen is None or self.screen.get_size() != (w, h):
            self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption(self.title or (self.scene.name if self.scene else "Game"))

    def load_scene(self, name: str):
        """Load ``<name>.scene`` and its code ``<name>.py`` and call Scene_Load."""
        path = self.folder / f"{name}.scene"
        data = json.loads(path.read_text(encoding="utf-8"))
        w = int(_num(data.get("width", 800), 800))
        h = int(_num(data.get("height", 600), 600))
        self._init_pygame(*(self.size or (w, h)))
        self.scene = Scene(self, name, data)
        if self.size:
            self.scene.view_size = self.size
            self.scene.world_size = tuple(max(a, b) for a, b in zip(self.scene.world_size, self.size))
        self._touching = set()
        self._sig_cache = {}
        self.module = self._load_module(name)
        self._inject()
        self.scene.camera.update()
        self._fire_scene("Load")
        return self.scene

    def _load_module(self, name: str):
        if not (self.folder / f"{name}.py").exists():
            return None
        if str(self.folder) not in sys.path:
            sys.path.insert(0, str(self.folder))
        if name in sys.modules:
            return sys.modules[name]
        return importlib.import_module(name)

    def _inject(self):
        """Scene objects become globals of the scene module (VB: controls are names in the form code)."""
        if self.module is None:
            return
        g = self.module.__dict__
        for obj in self.scene.all_objects():
            g[obj.name] = obj
        for t in self.scene.timers.values():
            g[t.name] = t

    # ---- events
    def _handler(self, name: str):
        if self.module is None:
            return None
        fn = getattr(self.module, name, None)
        return fn if callable(fn) else None

    def _call(self, fn, name: str, *args):
        n = self._sig_cache.get(name)
        if n is None:
            try:
                params = inspect.signature(fn).parameters.values()
                if any(p.kind == p.VAR_POSITIONAL for p in params):
                    n = len(args)
                else:
                    n = sum(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in params)
            except (TypeError, ValueError):
                n = len(args)
            self._sig_cache[name] = n
        self.events.append((self.frame, name, args))
        return fn(*args[:n])

    def _fire_scene(self, event: str, *args) -> bool:
        done = False
        for owner in ("Scene", self.scene.name if self.scene else "", "Game"):
            fn = self._handler(f"{owner}_{event}") if owner else None
            if fn is not None:
                self._call(fn, f"{owner}_{event}", *args)
                done = True
                break
        return done

    def _fire_object(self, obj: GameObject, event: str, *args) -> bool:
        done = False
        for owner in dict.fromkeys((obj.name, obj.group)):
            fn = self._handler(f"{owner}_{event}")
            if fn is not None:
                self._call(fn, f"{owner}_{event}", *args)
                done = True
        return done

    def fired(self, handler: str) -> int:
        """How many times a handler ran (tests)."""
        return sum(1 for _f, n, _a in self.events if n == handler)

    # ---- loop
    def step(self, dt: float | None = None):
        """One frame: events, timers, behaviours, collisions, Scene_Update, camera, drawing."""
        if self.scene is None:
            return
        if dt is None:
            dt = 1.0 / self.scene.fps
        self._process_events()
        scene = self.scene
        for t in list(scene.timers.values()):
            if t.enabled and t.interval > 0:
                t._acc += dt * 1000
                while t._acc >= t.interval - 1e-6 and t.enabled:
                    t._acc -= t.interval
                    self._fire_object_name(t.name, "Tick")
        for o in scene.live_objects():
            for b in o.behaviours:
                if b.get("enabled", True) is False:
                    continue
                fn = getattr(Behaviours, str(b.get("type", "")), None)
                if fn is not None and o.alive:
                    fn(self, o, b, dt)
            o.update_animation(dt)
            if o.y > scene.world_size[1] + 200 and o.alive and not o.layer.screen_space:
                if not self._fire_object(o, "OutOfWorld"):
                    if any(o.has(a) for a in ACTOR_BEHAVIOURS):
                        self.restart_scene()
                    else:
                        o.destroy()
        self._collisions()
        self._fire_scene("Update", dt)
        scene.purge()
        if self._pending_scene is not None:
            name, self._pending_scene = self._pending_scene, None
            self.load_scene(name)
        self.scene.camera.update()
        self.draw()
        self.input._new_frame()
        self.frame += 1
        self.time += dt

    def _fire_object_name(self, name: str, event: str, *args):
        fn = self._handler(f"{name}_{event}")
        if fn is not None:
            self._call(fn, f"{name}_{event}", *args)

    def _process_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                self.input.press(Input.key_name(ev.key))
            elif ev.type == pygame.KEYUP:
                self.input.release(Input.key_name(ev.key))
            elif ev.type == pygame.MOUSEMOTION:
                self.input.mouse = ev.pos
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                self.input.mouse = ev.pos
                self.input.buttons.add(ev.button)
                self.input.clicked = True
                self.input._queue.append(("MouseDown", (ev.pos[0], ev.pos[1], ev.button)))
            elif ev.type == pygame.MOUSEBUTTONUP:
                self.input.buttons.discard(ev.button)
                self.input._queue.append(("MouseUp", (ev.pos[0], ev.pos[1], ev.button)))
        queue, self.input._queue = self.input._queue, []
        for kind, args in queue:
            if kind in ("KeyDown", "KeyUp"):
                self._fire_scene(kind, *args)
            elif kind == "MouseDown":
                x, y, button = args
                self._fire_scene("MouseDown", x, y, button)
                wx, wy = self.scene.camera.to_world(x, y)
                for o in sorted(self.scene.live_objects(), key=lambda o: -o.z):
                    px, py = (x, y) if o.layer.screen_space else (wx, wy)
                    if o.visible and o.contains(px, py):
                        self._fire_object(o, "Click")
                        break
            elif kind == "MouseUp":
                self._fire_scene("MouseUp", *args)

    def _collisions(self):
        objs = [o for o in self.scene.live_objects() if not o.layer.screen_space and
                (o.kind != "text")]
        now: set[tuple[str, str]] = set()
        rects = [o.hit_rect for o in objs]
        for i, a in enumerate(objs):
            ra = rects[i]
            for j in range(i + 1, len(objs)):
                b = objs[j]
                if ra.colliderect(rects[j]):
                    now.add((a.name, b.name))
        objects = self.scene.objects
        for pair in sorted(now - self._touching):
            a, b = objects.get(pair[0]), objects.get(pair[1])
            if a is None or b is None or not a.alive or not b.alive:
                continue
            for actor, item in ((a, b), (b, a)):
                coll = item.behaviour("collectible")
                if coll is not None and any(actor.has(x) for x in ACTOR_BEHAVIOURS) and item.alive:
                    self.score += int(_num(coll.get("score", 1), 1))
                    if coll.get("sound"):
                        self.play_sound(coll["sound"])
            self._fire_object(a, "Collide", b)
            self._fire_object(b, "Collide", a)
            for actor, item in ((a, b), (b, a)):
                if item.has("collectible") and any(actor.has(x) for x in ACTOR_BEHAVIOURS):
                    item.destroy()
        self._touching = {p for p in now if objects.get(p[0]) is not None and objects[p[0]].alive
                          and objects.get(p[1]) is not None and objects[p[1]].alive}

    def _clamp_to_world(self, o: GameObject):
        ww, wh = self.scene.world_size
        o.x = max(0.0, min(o.x, ww - o.width))
        o.y = max(0.0, min(o.y, wh - o.height))

    def draw(self):
        if self.screen is None:
            return
        scene = self.scene
        bg = scene.background
        if isinstance(bg, str) and bg in scene.images:
            self.screen.blit(pygame.transform.scale(scene.images[bg], self.screen.get_size()), (0, 0))
        else:
            self.screen.fill(_color(bg, (110, 193, 228)))
        ox, oy = scene.camera.x, scene.camera.y
        for ly in scene.layers:
            ly.draw(self.screen, ox, oy)
        self._fire_scene("Draw", self.screen)
        text, until = self._message
        if text and self.time < until:
            font = pygame.font.Font(None, 48)
            img = font.render(text, True, (255, 255, 255))
            box = img.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
            pygame.draw.rect(self.screen, (0, 0, 0), box.inflate(32, 20))
            self.screen.blit(img, box)
        if not self.headless:
            pygame.display.flip()

    def run(self, scene: str):
        """Load *scene* and run until the window closes (or RADGAME_FRAMES frames)."""
        self.load_scene(scene)
        self.running = True
        clock = pygame.time.Clock()
        frames = int(os.environ.get("RADGAME_FRAMES") or 0)
        fixed = bool(os.environ.get("RADGAME_FIXED_DT"))
        shot = os.environ.get("RADGAME_SCREENSHOT")
        script = []                     # RADGAME_KEYS="right:5-90,space:40-50" (key held between frames)
        for part in filter(None, os.environ.get("RADGAME_KEYS", "").split(",")):
            key, _, span = part.partition(":")
            a, _, b = span.partition("-")
            if a.isdigit() and b.isdigit():
                script.append((key.strip().lower(), int(a), int(b)))
        shots = {}                      # RADGAME_SHOTS="60:start.png,200:play.png" (screenshots at frames)
        for part in filter(None, os.environ.get("RADGAME_SHOTS", "").split(",")):
            n, _, f = part.partition(":")
            if n.strip().isdigit() and f.strip():
                shots[int(n)] = f.strip()
        while self.running:
            ms = clock.tick(self.scene.fps)
            dt = 1.0 / self.scene.fps if fixed else min(ms / 1000.0, 0.05)
            for key, a, b in script:
                if self.frame == a:
                    self.input.press(key)
                elif self.frame == b:
                    self.input.release(key)
            self.step(dt)
            if self.frame in shots and self.screen is not None:
                pygame.image.save(self.screen, shots[self.frame])
            if frames and self.frame >= frames:
                break
        if shot and self.screen is not None:
            pygame.image.save(self.screen, shot)
        pygame.quit()

    # ---- helpers used by the user code
    def go_to_scene(self, name: str):
        self._pending_scene = name

    def restart_scene(self):
        self._pending_scene = self.scene.name

    def quit(self):
        self.running = False

    def play_sound(self, sound_id: str):
        if not self._audio or self.scene is None:
            return
        path = self.scene.sounds.get(sound_id, sound_id)
        snd = self._sounds.get(path)
        try:
            if snd is None:
                snd = self._sounds[path] = pygame.mixer.Sound(path)
            snd.play()
        except (pygame.error, FileNotFoundError):
            pass

    def play_music(self, sound_id: str, loop: bool = True):
        if not self._audio or self.scene is None:
            return
        try:
            pygame.mixer.music.load(self.scene.sounds.get(sound_id, sound_id))
            pygame.mixer.music.play(-1 if loop else 0)
        except (pygame.error, FileNotFoundError):
            pass

    def show_message(self, text: str, seconds: float = 2.0):
        self._message = (str(text), self.time + seconds)

    # ---- saved values (best score, settings): savegame.json next to main.py (RADGAME_SAVE = another file)
    @property
    def save_file(self) -> Path:
        return Path(os.environ.get("RADGAME_SAVE") or (self.folder / "savegame.json"))

    def _saved(self) -> dict:
        try:
            data = json.loads(self.save_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_value(self, key: str, value):
        data = self._saved()
        data[str(key)] = value
        try:
            self.save_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            print(f"radgame: cannot save {self.save_file}: {e}", file=sys.stderr)

    def load_value(self, key: str, default=None):
        return self._saved().get(str(key), default)


def _main_folder() -> Path:
    """The folder of the started script (main.py), also under a debugger that runs it with exec."""
    for f in (sys.argv[0] if sys.argv else "", getattr(sys.modules.get("__main__"), "__file__", None)):
        if f and Path(f).suffix.lower() in (".py", ".pyw") and Path(f).exists():
            return Path(f).resolve().parent
    return Path.cwd()


# ====================================================================== VB-style helpers
_current: Game | None = None


class _GameRef:
    """``game`` in your code: the running Game (``game.score``, ``game.lives``, ``game.vars`` ...)."""

    def __getattr__(self, item):
        if _current is None:
            raise RuntimeError("the game is not running")
        return getattr(_current, item)

    def __setattr__(self, item, value):
        setattr(_current, item, value)

    def __repr__(self):
        return f"<game {_current!r}>"


game: Game = _GameRef()  # type: ignore[assignment]


def GoToScene(name: str):
    """Switch to another scene (``<name>.scene`` + ``<name>.py``) after this frame."""
    game.go_to_scene(name)


def RestartScene():
    game.restart_scene()


def Quit():
    game.quit()


def AddScore(points: int = 1):
    game.score += int(points)


def PlaySound(sound_id: str):
    game.play_sound(sound_id)


def PlayMusic(sound_id: str, loop: bool = True):
    game.play_music(sound_id, loop)


def StopMusic():
    try:
        pygame.mixer.music.stop()
    except pygame.error:
        pass


def ShowMessage(text: str, seconds: float = 2.0):
    """Big centred text for a few seconds ("You win!")."""
    game.show_message(text, seconds)


def IsKeyDown(key: str) -> bool:
    return game.input.down(key)


def Find(name: str) -> GameObject | None:
    return game.scene.objects.get(name)


def FindGroup(group: str) -> list[GameObject]:
    return [o for o in game.scene.live_objects() if o.group == group]


def Clone(obj: GameObject, x: float | None = None, y: float | None = None) -> GameObject:
    """A copy of a scene object (spawn bullets, enemies ...). The copy is a normal, visible object even
    when *obj* is a hidden spawn template; destroy() removes it from the scene for good."""
    props = {k: v for k, v in obj.props.items() if k != "template"}
    d = {"name": obj.name, "kind": obj.kind, "x": obj.x if x is None else x, "y": obj.y if y is None else y,
         "w": obj.w, "h": obj.h, "scale": obj.scale, "rotation": obj.rotation, "z": obj.z,
         "props": props, "behaviours": [dict(b) for b in obj.behaviours]}
    if isinstance(obj, Sprite):
        d.update(image=obj.image_id, spritesheet=obj.sheet_id, animation=obj.animation)
    if isinstance(obj, TextObject):
        d["text"] = obj.text
    new = game.scene.add_object(d, obj.layer)
    new.group = obj.group
    new.spawned = True
    if not obj.template:
        new.visible = obj.visible
    return new


def Spawn(template, x: float | None = None, y: float | None = None) -> GameObject:
    """A new object made from a scene object (usually a spawn template: props ``template=1``) by name
    or by object: ``gate = Spawn("PillarTop", 420, -200)``."""
    obj = Find(template) if isinstance(template, str) else template
    if isinstance(obj, ObjRef):
        obj = obj._obj()
    if obj is None:
        raise NameError(f"no object named {template!r} to spawn")
    return Clone(obj, x, y)


def Destroy(obj: GameObject):
    """Remove an object from the game (spawned objects are deleted, scene objects are hidden)."""
    (obj._obj() if isinstance(obj, ObjRef) else obj).destroy()


def EnableBehaviour(behaviour: str, on: bool = True, objects=None):
    """Switch a behaviour on/off for every object that has it (or only *objects*):
    ``EnableBehaviour("scroll", False)`` stops all scrolling scenery at game over."""
    for o in (objects if objects is not None else game.scene.live_objects()):
        o.enable(behaviour, on)


def SaveData(key: str, value):
    """Keep a value after the game closes (best score, settings): ``SaveData("best", 12)``."""
    game.save_value(key, value)


def LoadData(key: str, default=None):
    """A value kept by SaveData (``best = LoadData("best", 0)``)."""
    return game.load_value(key, default)


def AddTimer(name: str, interval: float = 1000, enabled: bool = True) -> Timer:
    """A timer created from code; ``<name>_Tick()`` fires every *interval* ms."""
    t = game.scene.timers[name] = Timer(name, interval, enabled)
    if game.module is not None:
        game.module.__dict__[name] = t
    return t


def Random(a: int, b: int) -> int:
    return _random.randint(a, b)


class ObjRef:
    """Stands for a scene object by name (used by the generated ``<Scene>_designer.py`` so the editor
    knows the names); the real object of the running scene answers."""

    __slots__ = ("_name",)

    def __init__(self, name: str):
        object.__setattr__(self, "_name", name)

    def _obj(self):
        if _current is None or _current.scene is None or self._name not in _current.scene.objects:
            raise NameError(f"no object named {self._name!r} in the running scene")
        return _current.scene.objects[self._name]

    def __getattr__(self, item):
        return getattr(self._obj(), item)

    def __setattr__(self, item, value):
        setattr(self._obj(), item, value)

    def __eq__(self, other):
        other = other._obj() if isinstance(other, ObjRef) else other
        return self._obj() is other

    def __hash__(self):
        return hash(self._name)

    def __repr__(self):
        return f"<ObjRef {self._name}>"


def objref(name: str):
    return ObjRef(name)


def run(scene: str, title: str = "", width: int | None = None, height: int | None = None, folder=None):
    """Start the game at *scene* (main.py calls this)."""
    g = Game(folder, title, (width, height) if width and height else None)
    g.run(scene)
    return g


__all__ = ["game", "Game", "Scene", "Sprite", "TextObject", "Area", "GameObject", "Layer", "Timer", "Input",
           "GoToScene", "RestartScene", "Quit", "AddScore", "PlaySound", "PlayMusic", "StopMusic", "ShowMessage",
           "IsKeyDown", "Find", "FindGroup", "Clone", "Spawn", "Destroy", "EnableBehaviour", "SaveData", "LoadData",
           "AddTimer", "Random", "objref", "run", "move_and_collide"]
