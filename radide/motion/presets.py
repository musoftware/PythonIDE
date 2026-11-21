"""Animation presets for classic forms (plan MOTION_VARIANTS_FOLDABLES 1.1 / 1.4).

A preset turns one entry of ``form.extra["animations"]`` into keyframe tracks ``[(prop, keys)]`` with
keys ``[ms, value, ease]``.  Values are *relative* wherever possible (``{"d": -80}`` = start - 80,
``{"m": 1.1}`` = start * 1.1, ``{"of": "Width", "f": 0.5}`` = start + half the start Width,
``{"reveal": 0..1}`` = typewriter, ``"$parent"`` = the parent's background colour), resolved by the
generated runtime against the values the control has when the animation starts (``_rad_resolve`` in
features/states.py ``COMMON_RT``) - so a preset works at every size / layout variant.

The track builders are ONE source (``PRESETS_RT``): this module executes it for design time / expand(),
and the generated Python designers embed it so ``self.Animate("Button1", "shake")`` works from code.

Targets differ in what they can draw (fallback table 1.4):
    alpha      - child controls can be transparent (Qt, Ring Qt, Kivy, RN, Dart, CSS; not Tk / WinForms)
    transform  - Rotation / ScaleX / ScaleY exist (Kivy, RN, Dart, CSS)
Without them a preset falls back (rotate -> wobble, flip / scale -> Width/Height around the centre,
fade -> colour blend into the parent background) and says so (shown in the Error List)."""
from __future__ import annotations

from dataclasses import dataclass, field

GROUPS = ("Entrance", "Exit", "Attention", "Color", "Text")
EASINGS = ("linear", "in", "out", "inout", "back", "elastic", "bounce", "sine")
TRIGGERS = ("load", "click", "hover", "timer", "show", "hide", "after", "manual")
HOVER_LEAVE = ("reverse", "stop", "none")

# what each code generation target can draw: (child alpha, transform)
TARGET_CAPS = {
    "py": (False, False),        # python-tk, vb-basic (vbrun) and every GUI-Bridge language
    "tk": (False, False),
    "qt": (True, False),         # python-qt: QGraphicsOpacityEffect, no rotation
    "ring": (True, False),
    "winforms": (False, False),
    "kivy": (True, True),
    "rn": (True, True),
    "dart": (True, True),
    "css": (True, True),
}
TARGET_NAMES = {"py": "python-tk", "tk": "python-tk", "qt": "python-qt", "ring": "Ring", "winforms": "WinForms",
                "kivy": "Kivy", "rn": "React Native", "dart": "Flutter", "css": "the web"}


def caps(target: str, control: str = "") -> tuple[bool, bool]:
    """(alpha, transform) for a control of *target* ("" control = the form: windows can always fade)."""
    alpha, transform = TARGET_CAPS.get(target, (False, False))
    return (alpha or not control), transform


# ---------------------------------------------------------------------------------------------------------
# The track builders. Pure Python without imports: embedded verbatim in generated designers.
PRESETS_RT = r'''

def _rad_fx_scale(s0, s1, d, e, transform, form):
    """Scale from factor s0 to s1 (transform targets) or the Width / Height around the centre."""
    if transform:
        return [("ScaleX", [[0, {"m": s0}], [d, {"m": s1}, e]]), ("ScaleY", [[0, {"m": s0}], [d, {"m": s1}, e]])]
    out = [("Width", [[0, {"m": s0}], [d, {"m": s1}, e]]), ("Height", [[0, {"m": s0}], [d, {"m": s1}, e]])]
    if not form:
        out += [("Left", [[0, {"of": "Width", "f": (1 - s0) / 2.0}], [d, {"of": "Width", "f": (1 - s1) / 2.0}, e]]),
                ("Top", [[0, {"of": "Height", "f": (1 - s0) / 2.0}], [d, {"of": "Height", "f": (1 - s1) / 2.0}, e]]),
                ("FontSize", [[0, {"m": max(s0, 0.3)}], [d, {"m": max(s1, 0.3)}, e]])]
    return out


def _rad_fx_fade(a0, a1, d, e, alpha, form):
    """Opacity a0 -> a1 (1 = the start value), or a colour blend into the parent background."""
    if alpha or form:
        v0 = {"d": 0} if a0 >= 1 else float(a0)
        v1 = {"d": 0} if a1 >= 1 else float(a1)
        return [("Opacity", [[0, v0], [d, v1, e]])]
    c0 = {"d": 0} if a0 >= 1 else "$parent"
    c1 = {"d": 0} if a1 >= 1 else "$parent"
    return [("BackColor", [[0, c0], [d, c1, e]]), ("ForeColor", [[0, c0], [d, c1, e]])]


def _rad_fx_slide(side, dist):
    side = str(side or "left").lower()
    prop = "Top" if side in ("top", "bottom", "up", "down") else "Left"
    sign = -1 if side in ("left", "top", "up") else 1
    return prop, sign * abs(float(dist))


def _rad_fx_tracks(preset, params=None, dur=500, ease="out", alpha=False, transform=False, form=False):
    """Keyframe tracks [(prop, keys)] of *preset* plus a note ("" or how this target shows it)."""
    p = dict(params or {})
    d = max(1, int(dur or 1))
    e = str(ease or "")
    e = "" if e == "linear" else e
    show = [] if form else [("Visible", [[0, True]])]
    hide = [] if form else [("Visible", [[0, {"d": 0}], [d, False]])]
    note = ""
    if preset == "fadeIn":
        tr = show + _rad_fx_fade(0, 1, d, e, alpha, form)
        if not (alpha or form):
            note = "fades as a colour blend into the background (no transparency)"
        return tr, note
    if preset == "fadeOut":
        tr = _rad_fx_fade(1, 0, d, e, alpha, form) + hide
        if not (alpha or form):
            note = "fades as a colour blend into the background (no transparency)"
        return tr, note
    if preset == "move":
        dx, dy = float(p.get("dx", 100) or 0), float(p.get("dy", 0) or 0)
        tr = []
        if dx:
            tr.append(("Left", [[0, {"d": 0}], [d, {"d": dx}, e]]))
        if dy:
            tr.append(("Top", [[0, {"d": 0}], [d, {"d": dy}, e]]))
        return tr, note
    if preset in ("slideIn", "slideOut"):
        side = p.get("from", p.get("to", "left"))
        prop, off = _rad_fx_slide(side, p.get("distance", 80))
        fade = bool(p.get("fade", True)) and (alpha or form)
        if preset == "slideIn":
            tr = show + [(prop, [[0, {"d": off}], [d, {"d": 0}, e]])]
            if fade:
                tr += _rad_fx_fade(0, 1, d, e, True, form)
        else:
            tr = [(prop, [[0, {"d": 0}], [d, {"d": off}, e or "in"]])]
            if fade:
                tr += _rad_fx_fade(1, 0, d, e or "in", True, form)
            tr += hide
        return tr, note
    if preset == "bounce":
        h = abs(float(p.get("height", 20) or 20))
        return [("Top", [[0, {"d": 0}], [int(d * 0.3), {"d": -h}, "out"], [int(d * 0.55), {"d": 0}, "in"],
                         [int(d * 0.75), {"d": -h * 0.4}, "out"], [d, {"d": 0}, "in"]])], note
    if preset == "shake":
        a = abs(float(p.get("distance", 10) or 10))
        steps = [0, -a, a, -a, a, -a * 0.5, 0]
        n = len(steps) - 1
        return [("Left", [[int(d * i / n), {"d": v}] for i, v in enumerate(steps)])], note
    if preset == "pulse":
        s = float(p.get("scale", 1.08) or 1.08)
        a = _rad_fx_scale(1, s, d // 2, "inout", transform, form)
        b = _rad_fx_scale(s, 1, d, "inout", transform, form)
        tr = [(pa, ka + kb[1:]) for (pa, ka), (_pb, kb) in zip(a, b)]
        if not transform:
            note = "pulses by resizing (no scale transform)"
        return tr, note
    if preset == "rotate":
        ang = float(p.get("angle", 360) or 360)
        if transform:
            return [("Rotation", [[0, {"d": 0}], [d, {"d": ang}, e]])], note
        w = 6
        steps = [0, -w, w, -w, w, 0]
        n = len(steps) - 1
        return ([("Left", [[int(d * i / n), {"d": v}] for i, v in enumerate(steps)])],
                "rotation is shown as a wobble (no rotation)")
    if preset == "flip":
        axis = str(p.get("axis", "x")).lower()
        if transform:
            prop = "ScaleY" if axis == "y" else "ScaleX"
            return [(prop, [[0, {"m": -1}], [d, {"m": 1}, e]])], note
        size, pos = ("Height", "Top") if axis == "y" else ("Width", "Left")
        h = d // 2
        tr = [(size, [[0, {"m": 1}], [h, {"m": 0}, "in"], [d, {"m": 1}, "out"]])]
        if not form:
            tr.append((pos, [[0, {"d": 0}], [h, {"of": size, "f": 0.5}, "in"], [d, {"d": 0}, "out"]]))
        return tr, "flips by narrowing the control (no 3D transform)"
    if preset in ("scaleIn", "scaleOut", "zoom"):
        s = float(p.get("scale", 0.3 if preset != "zoom" else 1.2) or 0.3)
        if preset == "scaleIn":
            tr = show + _rad_fx_scale(s, 1, d, e or "out", transform, form)
            if alpha or form:
                tr += _rad_fx_fade(0, 1, d, e, True, form)
        elif preset == "scaleOut":
            tr = _rad_fx_scale(1, s, d, e or "in", transform, form)
            if alpha or form:
                tr += _rad_fx_fade(1, 0, d, e or "in", True, form)
            tr += hide
        else:
            tr = _rad_fx_scale(1, s, d, e, transform, form)
        if not transform:
            note = "scales by resizing around the centre (no scale transform)"
        return tr, note
    if preset == "colorTo":
        prop = "ForeColor" if str(p.get("prop", "BackColor")) == "ForeColor" else "BackColor"
        color = str(p.get("color") or "#3399ff")
        return [(prop, [[0, {"d": 0}], [d, color, e]])], note
    if preset == "typewriter":
        return [("Text", [[0, {"reveal": 0}], [d, {"reveal": 1}]])], note
    return [], "unknown preset '%s'" % preset
'''


def _ns() -> dict:
    ns: dict = {}
    exec(compile(PRESETS_RT, "<radfx-presets>", "exec"), ns)        # noqa: S102 - our own constant
    return ns


_RT = _ns()
fx_tracks = _RT["_rad_fx_tracks"]


# ---------------------------------------------------------------------------------------------------------
def _choice(label, choices, default):
    return {"type": "choice", "label": label, "choices": list(choices), "default": default}


def _num(label, default, lo=-10000, hi=10000, kind="int"):
    return {"type": kind, "label": label, "default": default, "min": lo, "max": hi}


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    group: str
    params_schema: dict = field(default_factory=dict)
    duration: int = 500
    easing: str = "out"
    exits: bool = False        # ends hidden (Exit group)
    restores: bool = True      # ends where it started: the runtime gives the geometry back to Anchor / Dock

    def defaults(self) -> dict:
        return {k: s.get("default") for k, s in self.params_schema.items()}

    def build(self, anim: dict, base_props: dict | None, form=None, target: str = "py") -> tuple[list, str]:
        """(tracks [(prop, keys)], fallback note or "") of *anim* for code generation *target*."""
        control = str((anim or {}).get("target") or "")
        alpha, transform = caps(target, control)
        params = self.defaults()
        params.update((anim or {}).get("params") or {})
        dur = (anim or {}).get("durationMs", self.duration)
        ease = (anim or {}).get("easing", self.easing)
        if ease not in EASINGS:
            ease = self.easing
        tracks, note = fx_tracks(self.id, params, dur, ease, alpha, transform, not control)
        if base_props is not None and control:
            # a property the control does not have (e.g. Text of a PictureBox) cannot be animated
            tracks = [(p, k) for p, k in tracks
                      if p in base_props or p in ("Opacity", "Visible", "Rotation", "ScaleX", "ScaleY")]
        return tracks, note

    def tracks(self, anim: dict, base_props: dict | None, form=None, target: str = "py") -> list:
        return self.build(anim, base_props, form, target)[0]


_DIR = ("left", "right", "top", "bottom")
CATALOG: dict[str, Preset] = {p.id: p for p in (
    Preset("fadeIn", "Fade In", "Entrance", duration=400),
    Preset("slideIn", "Slide In", "Entrance",
           {"from": _choice("From", _DIR, "left"), "distance": _num("Distance", 80, 0, 4000),
            "fade": {"type": "bool", "label": "Fade", "default": True}}),
    Preset("scaleIn", "Zoom In", "Entrance", {"scale": _num("Start scale", 0.3, 0, 1, "float")}, easing="back"),
    Preset("fadeOut", "Fade Out", "Exit", duration=400, easing="in", exits=True, restores=False),
    Preset("slideOut", "Slide Out", "Exit",
           {"from": _choice("To", _DIR, "right"), "distance": _num("Distance", 80, 0, 4000),
            "fade": {"type": "bool", "label": "Fade", "default": True}}, easing="in", exits=True, restores=False),
    Preset("scaleOut", "Zoom Out", "Exit", {"scale": _num("End scale", 0.3, 0, 1, "float")}, easing="in",
           exits=True, restores=False),
    Preset("move", "Move", "Attention", {"dx": _num("Move X", 100), "dy": _num("Move Y", 0)}, restores=False),
    Preset("bounce", "Bounce", "Attention", {"height": _num("Height", 20, 0, 1000)}, duration=800, easing=""),
    Preset("shake", "Shake", "Attention", {"distance": _num("Distance", 10, 0, 500)}, duration=500, easing=""),
    Preset("pulse", "Pulse", "Attention", {"scale": _num("Scale", 1.08, 0.1, 5, "float")}, duration=600,
           easing="inout"),
    Preset("rotate", "Rotate", "Attention", {"angle": _num("Angle", 360, -3600, 3600)}, duration=800),
    Preset("flip", "Flip", "Attention", {"axis": _choice("Axis", ("x", "y"), "x")}, duration=600),
    Preset("zoom", "Zoom", "Attention", {"scale": _num("Scale", 1.2, 0.1, 10, "float")}, restores=False),
    Preset("colorTo", "Color", "Color",
           {"prop": _choice("Property", ("BackColor", "ForeColor"), "BackColor"),
            "color": {"type": "color", "label": "Color", "default": "#3399ff"}}, duration=600, easing="inout",
           restores=False),
    Preset("typewriter", "Typewriter", "Text", duration=1200, easing="linear"),
)}


def get(preset_id: str) -> Preset | None:
    return CATALOG.get(str(preset_id or ""))


def by_group() -> dict[str, list[Preset]]:
    out: dict[str, list[Preset]] = {g: [] for g in GROUPS}
    for p in CATALOG.values():
        out.setdefault(p.group, []).append(p)
    return out


def make(preset_id: str, target: str = "", fx_id: str = "fx1", **kw) -> dict:
    """A new animation entry (contract 1.1) with the preset's defaults; kw overrides top-level keys
    (durationMs, delayMs, easing, repeat, autoreverse, trigger, params, enabled)."""
    p = CATALOG[preset_id]
    anim = {"id": fx_id, "target": target, "preset": preset_id, "params": p.defaults(),
            "durationMs": p.duration, "delayMs": 0, "easing": p.easing or "linear", "repeat": 1,
            "autoreverse": False, "trigger": {"on": "load"}, "enabled": True}
    for k, v in kw.items():
        if k == "params" and isinstance(v, dict):
            anim["params"].update(v)
        elif k == "trigger" and isinstance(v, str):
            anim["trigger"] = {"on": v}
        else:
            anim[k] = v
    return anim


_TRIGGER_TEXT = {"load": "on load", "click": "on click", "hover": "on hover", "timer": "every {i} ms",
                 "show": "when shown", "hide": "when hidden", "after": "after {a}", "manual": "from code"}


def describe(anim: dict) -> str:
    """One line for lists: "Slide In from left - 500 ms, on click of Button2"."""
    p = CATALOG.get(str(anim.get("preset")))
    name = p.label if p else str(anim.get("preset"))
    params = anim.get("params") or {}
    if anim.get("preset") == "slideIn":
        name += f" from {params.get('from', 'left')}"
    elif anim.get("preset") == "slideOut":
        name += f" to {params.get('from', params.get('to', 'right'))}"
    elif anim.get("preset") == "colorTo":
        name += f" {params.get('color', '')}"
    trig = anim.get("trigger") or {}
    on = trig.get("on", "load")
    t = _TRIGGER_TEXT.get(on, on).format(i=trig.get("intervalMs", 1000), a=trig.get("after", "?"))
    src = trig.get("source")
    if on in ("click", "hover") and src and src != anim.get("target"):
        t += f" of {src}"
    rep = anim.get("repeat", 1)
    extra = ", forever" if rep == 0 else (f", x{rep}" if isinstance(rep, int) and rep > 1 else "")
    return f"{name} - {anim.get('durationMs', p.duration if p else 500)} ms, {t}{extra}"
