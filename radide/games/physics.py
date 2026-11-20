"""Physics (pymunk) in the scene designer: the scene's Physics section (on/off, gravity, joints) and the
"Physics body" section of an object (body type, shape, mass, friction, elasticity ...) in the inspector.

The settings are plain JSON in the scene (see radide/games/runtime/radgame_physics.py)::

    scene  "physics": {"enabled": true, "gravity_x": 0, "gravity_y": 900, "tiles_static": true}
           "joints": [{"type": "pivot", "a": "Plank", "b": null, "pivot": [400, 300]} ...]
    object "physics": {"body": "dynamic", "shape": "box", "mass": 1, "friction": 0.7, "elasticity": 0.2,
                       "fixed_rotation": false, "sensor": false, "points": [[x, y] ...]}

The pygame runtime runs them with pymunk (pip install pymunk); the Godot export builds RigidBody2D /
StaticBody2D / AnimatableBody2D proxies and joints from the same data (radgame_scene.gd).
"""
from __future__ import annotations

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem)

from .. import theme

BODY_TYPES = ("dynamic", "static", "kinematic")
SHAPES = ("box", "circle", "poly")
JOINT_TYPES = ("pivot", "pin", "spring", "rope", "motor")
JOINT_HELP = {"pivot": "turns around a point (seesaw, wheel, door hinge)",
              "pin": "keeps a fixed distance (pendulum on a rod)",
              "spring": "a springy link (rest_length, stiffness, damping)",
              "rope": "at most max pixels apart (rope, chain)",
              "motor": "spins b relative to a at rate (radians / s)"}
DEFAULT_BODY = {"body": "dynamic", "shape": "box", "mass": 1.0, "friction": 0.7, "elasticity": 0.2,
                "fixed_rotation": False, "sensor": False}


def pymunk_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("pymunk") is not None


# ====================================================================== outline from the picture
def convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Andrew's monotone chain (counter-clockwise, no repeated end point)."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def simplify(hull: list, max_points: int = 12) -> list:
    """Drop the hull points that change the outline least until at most *max_points* are left."""
    pts = list(hull)
    if len(pts) > 3:          # also drop nearly straight corners (pixel steps along a slanted edge)
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        tol = 0.02 * (max(xs) - min(xs)) * (max(ys) - min(ys))
    else:
        tol = 0
    while len(pts) > 3:
        best, bi = None, 0
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
            if best is None or area < best:
                best, bi = area, i
        if len(pts) <= max(3, max_points) and best >= tol:
            break
        pts.pop(bi)
    return pts


def outline_points(image: QImage, w: float, h: float, source=None, alpha: int = 40,
                   max_points: int = 12) -> list[list[float]]:
    """The convex outline of the opaque pixels of *image* (or of the *source* rect (x, y, w, h) of it - a
    sprite-sheet frame), scaled to an object of w x h pixels; [[x, y] ...] from the top-left."""
    if image.isNull():
        return []
    sx, sy, sw, sh = source or (0, 0, image.width(), image.height())
    img = image.convertToFormat(QImage.Format.Format_ARGB32)
    pts = []
    for y in range(sy, min(sy + sh, img.height())):
        row = [x for x in range(sx, min(sx + sw, img.width())) if (img.pixel(x, y) >> 24) & 0xFF > alpha]
        if row:
            pts += [(row[0] - sx, y - sy), (row[-1] + 1 - sx, y - sy), (row[0] - sx, y + 1 - sy),
                    (row[-1] + 1 - sx, y + 1 - sy)]
    hull = simplify(convex_hull(pts), max_points)
    kx, ky = w / max(1, sw), h / max(1, sh)
    return [[round(x * kx, 1), round(y * ky, 1)] for x, y in hull]


def object_outline(editor, o) -> list[list[float]]:
    """Outline of a scene object's picture (image or first frame of its sprite sheet), in object pixels."""
    sc = editor.scene
    w, h = o.w * o.scale, o.h * o.scale
    if o.spritesheet:
        sh = sc.assets.get("spritesheets", {}).get(o.spritesheet) or {}
        img = QImage(str(editor.resolve(sh.get("image", ""))))
        fw, fh = int(sh.get("frame_w") or 32), int(sh.get("frame_h") or 32)
        anim = (sh.get("animations") or {}).get(o.animation) or {}
        fi = int((anim.get("frames") or [0])[0])
        cols = max(1, img.width() // fw) if not img.isNull() else 1
        return outline_points(img, w, h, ((fi % cols) * fw, (fi // cols) * fh, fw, fh))
    if o.image:
        img = QImage(str(editor.resolve(sc.assets.get("images", {}).get(o.image, ""))))
        return outline_points(img, w, h)
    return [[0, 0], [w, 0], [w, h], [0, h]]


# ====================================================================== inspector sections
def _dspin(value, lo, hi, setter, dec=2, step=0.1, suffix=""):
    s = QDoubleSpinBox()
    s.setDecimals(dec)
    s.setRange(lo, hi)
    s.setSingleStep(step)
    s.setSuffix(suffix)
    s.setValue(float(value))
    s.setKeyboardTracking(False)
    s.valueChanged.connect(setter)
    return s


def build_scene_section(insp, lay) -> None:
    ed, sc = insp.editor, insp.editor.scene
    ph = sc.extra.get("physics") or {}
    g = QGroupBox("Physics (pymunk)")
    f = QFormLayout(g)
    on = QCheckBox("Real physics (bodies, joints)")
    on.setToolTip("Objects with a Physics body fall, collide, bounce and roll (pygame: pymunk, Godot: its 2D physics)")
    on.setChecked(bool(ph.get("enabled")))

    def toggle(v):
        def do():
            cfg = sc.extra.setdefault("physics", {"gravity_x": 0, "gravity_y": float(sc.gravity or 900),
                                                  "tiles_static": True})
            cfg["enabled"] = bool(v)
        ed.change("Physics", do, structural=True)
    on.toggled.connect(toggle)
    f.addRow("", on)
    if not pymunk_available():
        f.addRow(theme.role(QLabel("pymunk is not installed: pip install pymunk (the pygame game needs it)."),
                            "muted"))
    if ph.get("enabled"):
        def setter(key):
            return lambda v: ed.change("Physics", lambda: sc.extra["physics"].__setitem__(key, float(v)))
        f.addRow("Gravity X:", _dspin(ph.get("gravity_x", 0), -10000, 10000, setter("gravity_x"), 1, 50, " px/s²"))
        f.addRow("Gravity Y:", _dspin(ph.get("gravity_y", sc.gravity or 900), -10000, 10000, setter("gravity_y"),
                                      1, 50, " px/s²"))
        walls = QCheckBox("Collision tile layers are walls")
        walls.setChecked(bool(ph.get("tiles_static", True)))
        walls.toggled.connect(lambda v: ed.change("Physics", lambda: sc.extra["physics"].__setitem__("tiles_static",
                                                                                                    bool(v))))
        f.addRow("", walls)
        _build_joints(insp, f)
    lay.addWidget(g)


def _build_joints(insp, f) -> None:
    ed, sc = insp.editor, insp.editor.scene
    joints = sc.extra.get("joints") or []
    names = [o.name for _ly, o in sc.objects() if o.extra.get("physics")]
    t = QTableWidget(len(joints), 4)
    t.setHorizontalHeaderLabels(["Type", "A", "B (empty = world)", "Settings"])
    t.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().hide()
    t.setMaximumHeight(24 * (len(joints) + 1) + 8)
    t.setToolTip("\n".join(f"{k}: {v}" for k, v in JOINT_HELP.items()) +
                 "\nSettings: anchor_a=dx,dy; anchor_b=dx,dy; pivot=x,y; rest_length=40; stiffness=200; "
                 "damping=10; max=80; rate=2")
    for r, j in enumerate(joints):
        t.setItem(r, 0, QTableWidgetItem(str(j.get("type", "pivot"))))
        t.setItem(r, 1, QTableWidgetItem(str(j.get("a") or "")))
        t.setItem(r, 2, QTableWidgetItem(str(j.get("b") or "")))
        extra = {k: v for k, v in j.items() if k not in ("type", "a", "b")}
        t.setItem(r, 3, QTableWidgetItem("; ".join(
            f"{k}={','.join(str(x) for x in v) if isinstance(v, list) else v}" for k, v in extra.items())))

    def changed(item):
        r = item.row()
        js = sc.extra.get("joints") or []
        if r >= len(js):
            return
        j = {"type": (t.item(r, 0).text().strip() if t.item(r, 0) else "pivot") or "pivot"}
        if j["type"] not in JOINT_TYPES:
            return
        j["a"] = t.item(r, 1).text().strip() if t.item(r, 1) else ""
        b = t.item(r, 2).text().strip() if t.item(r, 2) else ""
        j["b"] = b or None
        for part in (t.item(r, 3).text() if t.item(r, 3) else "").split(";"):
            k, eq, v = part.partition("=")
            if not eq or not k.strip():
                continue
            vals = [x.strip() for x in v.split(",")]
            try:
                nums = [float(x) for x in vals]
                j[k.strip()] = nums if len(nums) > 1 else nums[0]
            except ValueError:
                j[k.strip()] = v.strip()
        if j != js[r]:
            ed.change("Joint", lambda: js.__setitem__(r, j))
    t.itemChanged.connect(changed)
    f.addRow(QLabel("Joints:"))
    f.addRow(t)
    row = QHBoxLayout()
    add = QPushButton("Add joint")

    def add_joint():
        a = names[0] if names else ""
        ed.change("Add joint", lambda: sc.extra.setdefault("joints", []).append(
            {"type": "pivot", "a": a, "b": None, "anchor_a": [0, 0]}), structural=True)
    add.clicked.connect(add_joint)
    rem = QPushButton("Remove")
    rem.clicked.connect(lambda: t.currentRow() >= 0 and ed.change(
        "Remove joint", lambda r=t.currentRow(): sc.extra["joints"].pop(r), structural=True))
    row.addWidget(add)
    row.addWidget(rem)
    row.addStretch(1)
    f.addRow(row)


def build_object_section(insp, lay, objs) -> None:
    ed = insp.editor
    o = objs[0]
    if o.kind == "text":
        return
    cfg = o.extra.get("physics")
    g = QGroupBox("Physics body")
    f = QFormLayout(g)
    body = QComboBox()
    body.addItem("(none)", "")
    for b in BODY_TYPES:
        body.addItem(b, b)
    body.setToolTip("dynamic: falls and bounces;  static: never moves (floor, wall);\n"
                    "kinematic: moved by your code or a behaviour, pushes dynamic bodies")
    body.setCurrentIndex(max(0, body.findData(cfg.get("body", "dynamic") if cfg else "")))

    def set_body(_i):
        v = body.currentData()

        def do():
            for x in objs:
                if not v:
                    x.extra.pop("physics", None)
                else:
                    x.extra.setdefault("physics", dict(DEFAULT_BODY))["body"] = v
            if v and not (ed.scene.extra.get("physics") or {}).get("enabled"):
                ed.scene.extra.setdefault("physics", {"gravity_x": 0, "gravity_y": float(ed.scene.gravity or 900),
                                                      "tiles_static": True})["enabled"] = True
        ed.change("Physics body", do, structural=True)
    body.currentIndexChanged.connect(set_body)
    f.addRow("Body:", body)
    if cfg:
        def setter(key, conv=float):
            return lambda v: ed.change(f"Physics {key}", lambda: [x.extra.setdefault("physics", dict(DEFAULT_BODY))
                                                                  .__setitem__(key, conv(v)) for x in objs])
        shape = QComboBox()
        shape.addItems(SHAPES)
        shape.setCurrentText(str(cfg.get("shape", "box")))
        shape.setToolTip("box / circle use the collision box (props hitbox); poly uses the outline points")
        shape.currentTextChanged.connect(setter("shape", str))
        f.addRow("Shape:", shape)
        f.addRow("Mass:", _dspin(cfg.get("mass", 1), 0.001, 100000, setter("mass"), 3, 0.5))
        f.addRow("Friction:", _dspin(cfg.get("friction", 0.7), 0, 10, setter("friction"), 2, 0.1))
        f.addRow("Elasticity:", _dspin(cfg.get("elasticity", 0.2), 0, 2, setter("elasticity"), 2, 0.1))
        fixed = QCheckBox("Fixed rotation (never tips over)")
        fixed.setChecked(bool(cfg.get("fixed_rotation")))
        fixed.toggled.connect(setter("fixed_rotation", bool))
        f.addRow("", fixed)
        sensor = QCheckBox("Sensor (detects, does not block)")
        sensor.setChecked(bool(cfg.get("sensor")))
        sensor.toggled.connect(setter("sensor", bool))
        f.addRow("", sensor)
        out = QPushButton("Outline from picture")
        out.setToolTip("Shape = poly: the convex outline of the opaque pixels of the sprite")

        def outline():
            pts = object_outline(ed, o)

            def do():
                c = o.extra.setdefault("physics", dict(DEFAULT_BODY))
                c["shape"], c["points"] = "poly", pts
            ed.change("Physics outline", do)
        out.clicked.connect(outline)
        f.addRow("", out)
        if cfg.get("points") and cfg.get("shape") == "poly":
            f.addRow(theme.role(QLabel(f"Outline: {len(cfg['points'])} points"), "muted"))
        f.addRow(theme.role(QLabel(f"Code: ApplyImpulse({o.name}, 0, -300), SetVelocity({o.name}, 100, 0)"),
                            "muted"))
    lay.addWidget(g)


__all__ = ["build_scene_section", "build_object_section", "outline_points", "object_outline", "convex_hull",
           "simplify", "pymunk_available", "BODY_TYPES", "SHAPES", "JOINT_TYPES"]

