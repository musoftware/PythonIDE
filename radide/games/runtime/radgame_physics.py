"""radgame_physics - optional real 2D physics for radgame with pymunk (copied next to radgame.py).

Switch it on in the scene (``"physics": {"enabled": true, "gravity_x": 0, "gravity_y": 900}``) and give
objects a body in the scene inspector::

    "physics": {"body": "dynamic"|"static"|"kinematic", "shape": "box"|"circle"|"poly",
                "mass": 1, "friction": 0.7, "elasticity": 0.2, "fixed_rotation": false,
                "points": [[x, y], ...],      # poly: outline in object pixels (from the sprite picture)
                "sensor": false, "gravity_scale": 1, "damping": 0, "vx": 0, "vy": 0}

The shape uses the collision box (props ``hitbox``). Collision tile layers become static walls. Joints::

    "joints": [{"type": "pivot"|"pin"|"spring"|"rope"|"motor", "a": "Door", "b": "Frame" or null (the world),
                "anchor_a": [dx, dy], "anchor_b": [dx, dy],          # from the centres
                "pivot": [x, y], "rest_length": 40, "stiffness": 200, "damping": 10, "max": 80, "rate": 2}]

Dynamic bodies move the objects (x, y, rotation); set ``obj.x`` / ``obj.y`` to teleport them, kinematic
bodies follow their object. Code: ``ApplyImpulse(obj, ix, iy)``, ``ApplyForce(obj, fx, fy)``,
``SetVelocity(obj, vx, vy)``, ``obj.body`` (the pymunk Body). Collide events still fire as usual.
"""
from __future__ import annotations

import math

import pymunk


def _num(v, d=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


class World:
    def __init__(self, scene):
        self.scene = scene
        cfg = scene.data.get("physics") or {}
        self.cfg = cfg
        self.space = pymunk.Space()
        self.space.gravity = (_num(cfg.get("gravity_x"), 0.0), _num(cfg.get("gravity_y"), scene.gravity or 900.0))
        self.space.iterations = int(_num(cfg.get("iterations"), 15))
        self.substeps = max(1, int(_num(cfg.get("substeps"), 2)))
        self.objects: list = []
        self.joints: list = []
        for o in list(scene.all_objects()):
            self.add(o)
        if cfg.get("tiles_static", True):
            for ly in scene.solid_tile_layers():
                self._tile_walls(ly)
        for j in scene.data.get("joints") or []:
            try:
                self.add_joint(j)
            except (KeyError, ValueError, TypeError) as e:
                print(f"radgame_physics: joint {j}: {e}")

    # ---- bodies
    def add(self, o):
        cfg = (getattr(o, "extra", None) or {}).get("physics")
        if not cfg or getattr(o, "template", False) or getattr(o, "body", None) is not None:
            return None
        kind = str(cfg.get("body", "dynamic"))
        r = o.hit_rect
        w, h = max(1.0, float(r.width)), max(1.0, float(r.height))
        shape_kind = str(cfg.get("shape", "box"))
        mass = max(0.001, _num(cfg.get("mass"), 1.0))
        pts = None
        if shape_kind == "poly" and len(cfg.get("points") or []) >= 3:
            cx, cy = o.width / 2, o.height / 2
            pts = [(_num(p[0]) - cx, _num(p[1]) - cy) for p in cfg["points"]]
        if kind == "static":
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
        elif kind == "kinematic":
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        else:
            if cfg.get("fixed_rotation"):
                moment = math.inf
            elif shape_kind == "circle":
                moment = pymunk.moment_for_circle(mass, 0, min(w, h) / 2)
            elif pts:
                moment = pymunk.moment_for_poly(mass, pts)
            else:
                moment = pymunk.moment_for_box(mass, (w, h))
            body = pymunk.Body(mass, moment)
        if shape_kind == "circle":
            shape = pymunk.Circle(body, min(w, h) / 2)
        elif pts:
            shape = pymunk.Poly(body, pts)
        else:
            shape = pymunk.Poly.create_box(body, (w, h))
        shape.friction = _num(cfg.get("friction"), 0.7)
        shape.elasticity = _num(cfg.get("elasticity"), 0.2)
        shape.sensor = bool(cfg.get("sensor", False))
        shape.radgame_object = o
        body.position = o.center
        body.angle = math.radians(o.rotation)
        if kind == "dynamic":
            body.velocity = (_num(cfg.get("vx"), o.vx), _num(cfg.get("vy"), o.vy))
            gs = _num(cfg.get("gravity_scale"), 1.0)
            damp = _num(cfg.get("damping"), 0.0)
            if gs != 1.0 or damp:
                def vel(b, gravity, damping, dt, gs=gs, damp=damp):
                    pymunk.Body.update_velocity(b, (gravity[0] * gs, gravity[1] * gs),
                                                damping * max(0.0, 1.0 - damp * dt), dt)
                body.velocity_func = vel
        self.space.add(body, shape)
        o.body = body
        o._body_kind = kind
        o._synced = (o.x, o.y, o.rotation)
        self.objects.append(o)
        return body

    def remove(self, o):
        body = getattr(o, "body", None)
        if body is None:
            return
        for c in list(body.constraints):
            if c in self.space.constraints:
                self.space.remove(c)
        self.space.remove(body, *body.shapes)
        o.body = None
        if o in self.objects:
            self.objects.remove(o)

    def _tile_walls(self, ly):
        """Static boxes for the solid cells of a collision tile layer (runs of cells merged per row)."""
        sb = self.space.static_body
        tw, th = ly.tile_w, ly.tile_h
        for r, row in enumerate(ly.data):
            c = 0
            while c < len(row):
                if row[c] < 0:
                    c += 1
                    continue
                start = c
                while c < len(row) and row[c] >= 0:
                    c += 1
                x0, x1, y0, y1 = start * tw, c * tw, r * th, (r + 1) * th
                s = pymunk.Poly(sb, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
                s.friction = _num(self.cfg.get("tile_friction"), 0.8)
                s.elasticity = _num(self.cfg.get("tile_elasticity"), 0.0)
                self.space.add(s)

    # ---- joints
    def add_joint(self, j: dict):
        objs = self.scene.objects
        a = objs[j["a"]].body
        b_name = j.get("b")
        b = objs[b_name].body if b_name else self.space.static_body
        if a is None or b is None:
            raise ValueError("both objects need a physics body")
        aa = tuple(_num(v) for v in (j.get("anchor_a") or (0, 0)))
        ab = tuple(_num(v) for v in (j.get("anchor_b") or (0, 0)))
        if b is self.space.static_body and not j.get("anchor_b"):
            ab = (a.position.x + aa[0], a.position.y + aa[1])        # world point where a is fixed
        t = str(j.get("type", "pivot"))
        if t == "pivot":
            p = j.get("pivot")
            c = pymunk.PivotJoint(a, b, (p[0], p[1])) if p else pymunk.PivotJoint(a, b, aa, ab)
        elif t == "pin":
            c = pymunk.PinJoint(a, b, aa, ab)
        elif t == "spring":
            pa, pb = a.local_to_world(aa), b.local_to_world(ab)
            rest = _num(j.get("rest_length"), (pa - pb).length)
            c = pymunk.DampedSpring(a, b, aa, ab, rest, _num(j.get("stiffness"), 200), _num(j.get("damping"), 10))
        elif t == "rope":
            pa, pb = a.local_to_world(aa), b.local_to_world(ab)
            c = pymunk.SlideJoint(a, b, aa, ab, 0, _num(j.get("max"), (pa - pb).length))
        elif t == "motor":
            c = pymunk.SimpleMotor(a, b, _num(j.get("rate"), 1.0))
        else:
            raise ValueError(f"unknown joint type {t}")
        c.collide_bodies = bool(j.get("collide", False))
        self.space.add(c)
        self.joints.append(c)
        return c

    # ---- stepping
    def step(self, dt: float):
        if dt <= 0:
            return
        for o in list(self.objects):
            body = o.body
            if body is None:
                continue
            if not o.alive:
                self.remove(o)
                continue
            cx, cy = o.center
            moved = (o.x, o.y, o.rotation) != o._synced
            if o._body_kind == "kinematic":
                px, py = body.position
                body.velocity = ((cx - px) / dt, (cy - py) / dt)
                body.angular_velocity = (math.radians(o.rotation) - body.angle) / dt
            elif moved:                                 # the code / a behaviour moved it: teleport
                body.position = (cx, cy)
                body.angle = math.radians(o.rotation)
                if o._body_kind == "static":
                    self.space.reindex_shapes_for_body(body)
        sub = dt / self.substeps
        for _ in range(self.substeps):
            self.space.step(sub)
        for o in self.objects:
            body = o.body
            if body is None:
                continue
            if o._body_kind == "dynamic":
                x, y = body.position
                o.x, o.y = x - o.width / 2, y - o.height / 2
                o.rotation = math.degrees(body.angle)
                o.vx, o.vy = body.velocity
            elif o._body_kind == "kinematic":
                body.position = o.center
                body.angle = math.radians(o.rotation)
            o._synced = (o.x, o.y, o.rotation)

    # ---- helpers for the code
    @staticmethod
    def impulse(o, ix: float, iy: float):
        if getattr(o, "body", None) is not None and o.body.body_type == pymunk.Body.DYNAMIC:
            o.body.apply_impulse_at_world_point((ix, iy), o.body.position)

    @staticmethod
    def force(o, fx: float, fy: float):
        if getattr(o, "body", None) is not None and o.body.body_type == pymunk.Body.DYNAMIC:
            o.body.apply_force_at_world_point((fx, fy), o.body.position)

    @staticmethod
    def velocity(o, vx: float, vy: float):
        if getattr(o, "body", None) is not None:
            o.body.velocity = (vx, vy)
        else:
            o.vx, o.vy = vx, vy


__all__ = ["World"]
