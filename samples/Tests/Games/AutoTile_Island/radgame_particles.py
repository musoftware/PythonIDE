"""radgame_particles - particle effects for radgame (copied into game projects next to radgame.py).

An *effect* is a dict kept in the scene (``assets.particles``, edited with the Particle Editor of RAD IDE)::

    {"rate": 40, "lifetime": 1.0, "lifetime_var": 0.2, "speed": 120, "speed_var": 30,
     "angle": -90, "spread": 25,              # degrees: 0 = right, -90 = up; spread = +/- around it
     "gravity_x": 0, "gravity_y": 0, "damping": 0, "spin": 0,
     "color_start": "#FFD86B", "color_end": "#FF6B8B00",   # #RRGGBB or #RRGGBBAA (alpha 00 = fades out)
     "size_start": 8, "size_end": 2, "shape": "circle"|"square", "texture": "<image id>",
     "emit_w": 0, "emit_h": 0,                # emit from a rectangle instead of a point
     "max": 500, "blend": "normal"|"add", "burst": 30, "duration": 0}

Scene objects with ``"particles": {"effect": "fire", "emitting": true}`` emit from their centre (usually an
area); from code: ``Emit("smoke", x, y)`` / ``Emit("smoke", Player)`` (follows it), ``Burst("boom", x, y, 40)``,
``StopEmitter(e)``, ``obj.emitting = False``.

The simulation (``Emitter``) is pure Python; only drawing uses pygame - RAD IDE's particle editor previews
effects with the same code.
"""
from __future__ import annotations

import math
import random

DEFAULTS = {"rate": 40.0, "lifetime": 1.0, "lifetime_var": 0.0, "speed": 120.0, "speed_var": 30.0,
            "angle": -90.0, "spread": 25.0, "gravity_x": 0.0, "gravity_y": 0.0, "damping": 0.0, "spin": 0.0,
            "color_start": "#FFFFFF", "color_end": "#FFFFFF00", "size_start": 8.0, "size_end": 2.0,
            "shape": "circle", "texture": "", "emit_w": 0.0, "emit_h": 0.0, "max": 500, "blend": "normal",
            "burst": 30, "duration": 0.0}

PRESETS = {
    "fire": {"rate": 70, "lifetime": 0.8, "lifetime_var": 0.3, "speed": 90, "speed_var": 30, "angle": -90,
             "spread": 18, "gravity_y": -60, "color_start": "#FFE07A", "color_end": "#FF3A1A00",
             "size_start": 14, "size_end": 3, "blend": "add", "emit_w": 16},
    "smoke": {"rate": 18, "lifetime": 2.2, "lifetime_var": 0.5, "speed": 40, "speed_var": 12, "angle": -90,
              "spread": 20, "gravity_y": -15, "color_start": "#9A9AA8C0", "color_end": "#50505800",
              "size_start": 10, "size_end": 34},
    "sparkle": {"rate": 30, "lifetime": 0.6, "lifetime_var": 0.2, "speed": 70, "speed_var": 40, "angle": 0,
                "spread": 180, "color_start": "#FFFFFF", "color_end": "#FFD86B00", "size_start": 5,
                "size_end": 1, "blend": "add"},
    "explosion": {"rate": 0, "burst": 60, "lifetime": 0.9, "lifetime_var": 0.3, "speed": 220, "speed_var": 120,
                  "angle": 0, "spread": 180, "gravity_y": 240, "damping": 1.5, "color_start": "#FFF3B0",
                  "color_end": "#FF450000", "size_start": 9, "size_end": 2, "blend": "add"},
    "rain": {"rate": 120, "lifetime": 1.2, "speed": 520, "speed_var": 60, "angle": 100, "spread": 3,
             "color_start": "#9FC8FFC0", "color_end": "#9FC8FF60", "size_start": 3, "size_end": 3,
             "shape": "square", "emit_w": 800},
    "snow": {"rate": 40, "lifetime": 6, "lifetime_var": 1.5, "speed": 45, "speed_var": 15, "angle": 90,
             "spread": 25, "color_start": "#FFFFFF", "color_end": "#FFFFFF80", "size_start": 5, "size_end": 4,
             "emit_w": 800},
    "trail": {"rate": 60, "lifetime": 0.5, "speed": 10, "speed_var": 10, "angle": 180, "spread": 40,
              "color_start": "#7AF0FF", "color_end": "#3A60FF00", "size_start": 8, "size_end": 1,
              "blend": "add"},
    "coin": {"rate": 0, "burst": 24, "lifetime": 0.5, "lifetime_var": 0.15, "speed": 150, "speed_var": 50,
             "angle": -90, "spread": 180, "gravity_y": 300, "color_start": "#FFF07A", "color_end": "#FFB00000",
             "size_start": 6, "size_end": 2, "blend": "add"},
}


def effect_of(e) -> dict:
    """A complete effect dict (missing keys from DEFAULTS)."""
    out = dict(DEFAULTS)
    out.update(e or {})
    return out


def parse_color(c, default=(255, 255, 255, 255)) -> tuple[int, int, int, int]:
    if isinstance(c, (list, tuple)) and len(c) >= 3:
        r, g, b = (int(v) for v in c[:3])
        return r, g, b, int(c[3]) if len(c) > 3 else 255
    s = str(c or "").strip().lstrip("#")
    try:
        if len(s) == 6:
            return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255
        if len(s) == 8:
            return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        if len(s) == 3:
            return tuple(int(ch * 2, 16) for ch in s) + (255,)
    except ValueError:
        pass
    return default


def _num(v, d=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "rot", "spin")

    def __init__(self, x, y, vx, vy, life, spin):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.age, self.life = 0.0, life
        self.rot, self.spin = 0.0, spin


class Emitter:
    """A source of particles at (x, y) or following an object (anything with ``center``)."""

    def __init__(self, effect: dict, x: float = 0.0, y: float = 0.0, follow=None, seconds: float = 0.0,
                 emitting: bool = True, rng: random.Random | None = None, name: str = ""):
        self.effect = effect_of(effect)
        self.name = name
        self.x, self.y = float(x), float(y)
        self.follow = follow
        self.emitting = emitting
        self.particles: list[Particle] = []
        self.rng = rng or random.Random()
        self._acc = 0.0
        self.time = 0.0
        d = _num(self.effect.get("duration"), 0.0)
        self.until = seconds if seconds and seconds > 0 else (d if d > 0 else 0.0)
        self.layer = None                 # the radgame Layer it is drawn with
        self.free_when_done = False       # Burst / timed emitters disappear when empty

    # ---- emission
    def _spawn(self, n: int):
        e, rng = self.effect, self.rng
        cap = int(_num(e.get("max"), 500))
        a0, spread = _num(e.get("angle"), -90), _num(e.get("spread"), 0)
        sp, spv = _num(e.get("speed"), 100), _num(e.get("speed_var"), 0)
        life, lifev = max(0.02, _num(e.get("lifetime"), 1)), _num(e.get("lifetime_var"), 0)
        ew, eh = _num(e.get("emit_w"), 0), _num(e.get("emit_h"), 0)
        spin = _num(e.get("spin"), 0)
        for _ in range(n):
            if len(self.particles) >= cap:
                break
            ang = math.radians(a0 + rng.uniform(-spread, spread))
            speed = max(0.0, sp + rng.uniform(-spv, spv))
            x = self.x + (rng.uniform(-ew / 2, ew / 2) if ew else 0.0)
            y = self.y + (rng.uniform(-eh / 2, eh / 2) if eh else 0.0)
            lf = max(0.02, life + rng.uniform(-lifev, lifev))
            self.particles.append(Particle(x, y, math.cos(ang) * speed, math.sin(ang) * speed, lf, spin))

    def burst(self, count: int = 0):
        self._spawn(int(count) if count and count > 0 else int(_num(self.effect.get("burst"), 30)))

    def stop(self):
        self.emitting = False

    @property
    def done(self) -> bool:
        return not self.emitting and not self.particles

    # ---- simulation
    def update(self, dt: float):
        if self.follow is not None:
            if getattr(self.follow, "alive", True) is False:
                self.follow = None
                self.emitting = False
            else:
                self.x, self.y = self.follow.center
        self.time += dt
        if self.until and self.time >= self.until:
            self.emitting = False
            self.free_when_done = True
        if self.emitting:
            rate = _num(self.effect.get("rate"), 0)
            if rate > 0:
                self._acc += rate * dt
                n = int(self._acc)
                if n:
                    self._acc -= n
                    self._spawn(n)
        e = self.effect
        gx, gy = _num(e.get("gravity_x"), 0), _num(e.get("gravity_y"), 0)
        damp = max(0.0, 1.0 - _num(e.get("damping"), 0) * dt)
        keep = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.life:
                continue
            p.vx = (p.vx + gx * dt) * damp
            p.vy = (p.vy + gy * dt) * damp
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rot += p.spin * dt
            keep.append(p)
        self.particles = keep

    # ---- look of a particle at its age
    def look(self, p: Particle) -> tuple[float, tuple[int, int, int, int]]:
        """(size in pixels, rgba) of particle *p* now."""
        e = self.effect
        t = min(1.0, p.age / p.life) if p.life else 1.0
        s0 = _num(e.get("size_start"), 8)
        s1 = _num(e.get("size_end"), s0)
        c0 = parse_color(e.get("color_start"))
        c1 = parse_color(e.get("color_end"), c0)
        col = tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
        return s0 + (s1 - s0) * t, col  # type: ignore[return-value]


# ====================================================================== pygame drawing
class System:
    """The particle emitters of a running radgame scene."""

    def __init__(self, scene):
        self.scene = scene
        self.emitters: list[Emitter] = []
        self._cache: dict = {}
        self.textures: dict = {}
        for o in list(scene.all_objects()):
            self.add_object(o)

    def effect(self, eff) -> dict:
        if isinstance(eff, dict):
            return eff
        effects = (self.scene.data.get("assets") or {}).get("particles") or {}
        if eff in effects:
            return effects[eff]
        return PRESETS.get(str(eff), {})

    def add_object(self, o):
        """An emitter for a scene object with ``"particles"`` settings (spawn templates do not emit)."""
        cfg = (getattr(o, "extra", None) or {}).get("particles")
        if not cfg or getattr(o, "template", False):
            return None
        if not isinstance(cfg, dict):
            cfg = {"effect": str(cfg)}
        em = Emitter(self.effect(cfg.get("effect", "")), follow=o, emitting=bool(cfg.get("emitting", True)),
                     name=str(cfg.get("effect", "")))
        em.x, em.y = o.center
        em.layer = o.layer
        o.emitter = em
        self.emitters.append(em)
        return em

    def emit(self, eff, x=0.0, y=0.0, seconds: float = 0.0, layer=None) -> Emitter:
        follow = None
        if hasattr(x, "center"):
            follow, seconds = x, (y if isinstance(y, (int, float)) and y else seconds)
            x, y = x.center
            layer = layer or follow.layer
        em = Emitter(self.effect(eff), x, y, follow=follow, seconds=seconds, name=str(eff))
        em.layer = layer or self._top_layer()
        em.free_when_done = bool(seconds)
        self.emitters.append(em)
        return em

    def burst(self, eff, x=0.0, y=0.0, count: int = 0, layer=None) -> Emitter:
        if hasattr(x, "center"):
            layer = layer or x.layer
            count = y if isinstance(y, (int, float)) and y else count
            x, y = x.center
        em = Emitter(self.effect(eff), x, y, emitting=False, name=str(eff))
        em.layer = layer or self._top_layer()
        em.free_when_done = True
        em.burst(int(count))
        self.emitters.append(em)
        return em

    def _top_layer(self):
        layers = [ly for ly in self.scene.layers if ly.type != "ui"]
        return layers[-1] if layers else (self.scene.layers[-1] if self.scene.layers else None)

    def update(self, dt: float):
        for em in self.emitters:
            em.update(dt)
        self.emitters = [em for em in self.emitters if not (em.free_when_done and em.done)]

    def count(self) -> int:
        return sum(len(em.particles) for em in self.emitters)

    # ---- drawing
    def _texture(self, tid: str):
        if tid not in self.textures:
            self.textures[tid] = self.scene.images.get(tid)
        return self.textures[tid]

    def _sprite(self, em: Emitter, size: float, col):
        import pygame
        sz = max(1, int(round(size)))
        q = tuple(c // 8 * 8 for c in col)
        tid = str(em.effect.get("texture") or "")
        shape = str(em.effect.get("shape") or "circle")
        key = (tid, shape, sz, q)
        s = self._cache.get(key)
        if s is None:
            if len(self._cache) > 2048:
                self._cache.clear()
            tex = self._texture(tid) if tid else None
            if tex is not None:
                s = pygame.transform.smoothscale(tex, (sz, sz)).copy()
                s.fill(q, special_flags=pygame.BLEND_RGBA_MULT)
            else:
                s = pygame.Surface((sz, sz), pygame.SRCALPHA)
                if shape == "square" or sz <= 2:
                    s.fill(q)
                else:
                    pygame.draw.circle(s, q, (sz / 2, sz / 2), sz / 2)
            self._cache[key] = s
        return s

    def draw_layer(self, layer, surf, ox: float, oy: float):
        import pygame
        if getattr(layer, "screen_space", False):
            ox = oy = 0
        for em in self.emitters:
            if em.layer is not layer or not em.particles:
                continue
            add = str(em.effect.get("blend")) == "add"
            flags = pygame.BLEND_RGB_ADD if add else 0
            for p in em.particles:
                size, col = em.look(p)
                if size <= 0.2 or col[3] <= 2:
                    continue
                img = self._sprite(em, size, col)
                if add and col[3] < 255:      # additive: alpha scales the brightness
                    k = col[3] / 255
                    img = self._sprite(em, size, (int(col[0] * k), int(col[1] * k), int(col[2] * k), 255))
                w, h = img.get_size()
                surf.blit(img, (round(p.x - ox - w / 2), round(p.y - oy - h / 2)), special_flags=flags)


__all__ = ["DEFAULTS", "PRESETS", "Emitter", "Particle", "System", "effect_of", "parse_color"]
