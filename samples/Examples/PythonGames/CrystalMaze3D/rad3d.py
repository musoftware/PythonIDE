"""rad3d.py - RAD IDE 3D scene runtime for Ursina (copied into the project by RAD IDE; do not edit).

main.py:
    import rad3d
    app = rad3d.start("My Game")          # Ursina() (+ test hooks)
    scene = rad3d.load_scene("Scene1")    # entities built by Scene1_designer.py, by name
    def Scene_Update(dt): ...             # VB-style handlers in main.py
    def Player_Collect(item): ...
    rad3d.run(globals())

Behaviours (set in the IDE's 3D scene view): player (WASD/arrows + Space, camera follows), spin, solid,
collectible.  Test hooks (environment): RAD3D_HEADLESS=1 renders into an offscreen buffer,
RAD3D_FRAMES=n quits after n frames and prints "rad3d-test: ...", RAD3D_KEYS="w:5-60,space:20-25" holds keys,
RAD3D_SCREENSHOT=file.png saves the last frame.
"""
from __future__ import annotations

import importlib
import os
import sys

from ursina import Entity, Ursina, Vec3, application, camera, color, held_keys, raycast, time

score = 0
vars = {}
entities: dict = {}
player = None
_app = None
_user: dict = {}
_frames = 0
_keys_script: list = []
_sim: set = set()
_cam_offset = Vec3(0, 0, 0)
_vel_y = 0.0
GRAVITY = 9.8
SPEED = 5.0
JUMP = 5.5


def start(title: str = "RAD 3D Game", **kw):
    """Create the Ursina app.  RAD3D_HEADLESS=1 -> offscreen window (tests)."""
    global _app
    headless = os.environ.get("RAD3D_HEADLESS") == "1"
    kw.setdefault("development_mode", False)
    kw.setdefault("borderless", False)
    if headless:
        kw["window_type"] = "offscreen"
    else:
        kw.setdefault("size", (1024, 640))
    _app = Ursina(title=title, **kw)
    try:
        from ursina.shaders import lit_with_shadows_shader
        Entity.default_shader = lit_with_shadows_shader
    except Exception:  # noqa: BLE001
        pass
    return _app


def hexcolor(value: str):
    try:
        return color.hex(str(value).lstrip("#"))
    except Exception:  # noqa: BLE001
        return color.white


def load_scene(name: str) -> dict:
    """Build the entities of ``<name>_designer.py`` (generated from <name>.scene3d)."""
    global player, _cam_offset, GRAVITY
    sys.path.insert(0, os.getcwd())
    mod = importlib.import_module(f"{name}_designer")
    built = mod.build(sys.modules[__name__])
    entities.clear()
    entities.update(built)
    GRAVITY = float(getattr(mod, "GRAVITY", 9.8))
    player = next((e for e in entities.values() if "player" in getattr(e, "rad_behaviours", ())), None)
    if player is not None:
        _cam_offset = camera.position - player.position
    return entities


def _down(*names: str) -> bool:
    return any(held_keys[n] or n in _sim for n in names)


def _solid_hit(e) -> bool:
    for other in entities.values():
        if other is e or not getattr(other, "enabled", True) or "solid" not in getattr(other, "rad_behaviours", ()):
            continue
        if getattr(other, "rad_kind", "") == "plane":
            continue                       # the ground is handled by the floor ray
        if other.collider is not None and e.intersects(other).hit:
            return True
    return False


def _update_player(dt: float) -> None:
    global _vel_y
    p = player
    d = Vec3(0, 0, 0)
    if _down("w", "up arrow"):
        d.z += 1
    if _down("s", "down arrow"):
        d.z -= 1
    if _down("a", "left arrow"):
        d.x -= 1
    if _down("d", "right arrow"):
        d.x += 1
    if d.length() > 0:
        d = d.normalized() * SPEED * dt
        for axis in ("x", "z"):
            old = getattr(p, axis)
            setattr(p, axis, old + getattr(d, axis))
            if _solid_hit(p):
                setattr(p, axis, old)
    half = p.scale_y * (1.0 if getattr(p, "rad_kind", "") == "capsule" else 0.5)
    ray = raycast(p.world_position, Vec3(0, -1, 0), distance=half + 0.05 + max(0.0, -_vel_y * dt),
                  ignore=(p,))
    on_ground = ray.hit and _vel_y <= 0
    if on_ground:
        p.y = ray.world_point.y + half
        _vel_y = JUMP if _down("space") else 0.0
    else:
        _vel_y -= GRAVITY * dt
    p.y += _vel_y * dt
    if p.y < -30:
        p.position = Vec3(0, 3, 0)
        _vel_y = 0.0
    camera.position = p.position + _cam_offset


def _tick() -> None:
    global score, _frames
    dt = min(time.dt, 1 / 20) if not _keys_script and not os.environ.get("RAD3D_FRAMES") else 1 / 60
    for k, a, b in _keys_script:
        if _frames == a:
            _sim.add(k)
        elif _frames == b:
            _sim.discard(k)
    for e in list(entities.values()):
        beh = getattr(e, "rad_behaviours", ())
        if "spin" in beh and e.enabled:
            e.rotation_y += 90 * dt
    if player is not None:
        _update_player(dt)
        for name, e in list(entities.items()):
            if "collectible" in getattr(e, "rad_behaviours", ()) and e.enabled and \
                    (e.world_position - player.world_position).length() < 0.6 + max(e.scale) / 2:
                e.enabled = False
                score += 1
                if callable(_user.get("Player_Collect")):
                    _user["Player_Collect"](e)
    if callable(_user.get("Scene_Update")):
        _user["Scene_Update"](dt)
    _frames += 1
    limit = int(os.environ.get("RAD3D_FRAMES") or 0)
    if limit and _frames >= limit:
        shot = os.environ.get("RAD3D_SCREENSHOT")
        if shot:
            try:
                from panda3d.core import Filename
                base = application.base
                base.graphicsEngine.renderFrame()
                if not base.win.saveScreenshot(Filename.fromOsSpecific(os.path.abspath(shot))):
                    print("rad3d: screenshot not saved", flush=True)
            except Exception as e:  # noqa: BLE001
                print("rad3d: screenshot failed:", e)
        p = player.position if player is not None else Vec3(0, 0, 0)
        print(f"rad3d-test: {_frames} frames score={score} player=({p.x:.2f},{p.y:.2f},{p.z:.2f})", flush=True)
        application.quit()


class _Runner(Entity):
    def update(self):
        _tick()


def run(user_globals: dict | None = None) -> None:
    """Start the game loop; *user_globals* = globals() of main.py (its handlers are called)."""
    _user.clear()
    _user.update(user_globals or {})
    for part in filter(None, os.environ.get("RAD3D_KEYS", "").split(",")):
        key, _, span = part.partition(":")
        a, _, b = span.partition("-")
        if a.isdigit() and b.isdigit():
            key = key.strip().lower()
            key = {"up": "up arrow", "down": "down arrow", "left": "left arrow", "right": "right arrow"}.get(key, key)
            _keys_script.append((key, int(a), int(b)))
    if callable(_user.get("Scene_Load")):
        _user["Scene_Load"]()
    _Runner()
    (_app or start()).run()
