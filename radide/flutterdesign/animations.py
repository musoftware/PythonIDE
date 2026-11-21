"""Entrance-animation presets for the Flutter designer (docs/FLUTTER_DESIGNER.md section 1.4 and 7.4).

A preset is a ready-made value for a node's ``"anim"`` field (fade in, slide in from a side, scale, zoom,
bounce). ``stagger`` / ``cascade`` give a group of widgets increasing delays - the "elements fly in one after
another" effect of animated login / onboarding screens. The code generator turns ``anim`` into the bundled
``RadFx`` helper (lib/radfx.dart); ``to_flutter_animate`` gives the equivalent flutter_animate chain for people
who prefer that package. Plain Python (no Qt).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from . import model as M

# Containers whose children are staggered by default (their visual order = list order)
STAGGER_PARENTS = {"Column", "Row", "Flex", "Wrap", "ListView", "GridView", "Stack"}
# parent-data widgets: an anim set on them is generated around their child (codegen handles this)
_DIRECTIONAL = {"fadeInUp": ("offsetY", 30), "fadeInDown": ("offsetY", -30), "fadeInLeft": ("offsetX", -30),
                "fadeInRight": ("offsetX", 30), "slideUp": ("offsetY", 30), "slideDown": ("offsetY", -30),
                "slideLeft": ("offsetX", 30), "slideRight": ("offsetX", -30)}
_SCALE_DEFAULT = {"scaleIn": 0.8, "zoomIn": 0.3, "bounceIn": 0.3}


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    anim: dict
    help: str = ""
    group: str = "Entrance"


PRESETS: list[Preset] = [
    Preset("fade", "Fade in", {"type": "fadeIn", "durationMs": 500}, "Opacity 0 -> 1"),
    Preset("fade_up", "Fade in up", {"type": "fadeInUp", "durationMs": 600, "offsetY": 30},
           "Fades in while rising 30 px (the classic login-screen entrance)"),
    Preset("fade_down", "Fade in down", {"type": "fadeInDown", "durationMs": 600, "offsetY": -30},
           "Fades in while dropping from above"),
    Preset("fade_left", "Fade in from left", {"type": "fadeInLeft", "durationMs": 600, "offsetX": -40},
           "Fades in while moving right from the left"),
    Preset("fade_right", "Fade in from right", {"type": "fadeInRight", "durationMs": 600, "offsetX": 40},
           "Fades in while moving left from the right"),
    Preset("slide_up", "Slide up", {"type": "slideUp", "durationMs": 500, "offsetY": 60},
           "Moves up into place without fading", "Slide"),
    Preset("slide_down", "Slide down", {"type": "slideDown", "durationMs": 500, "offsetY": -60},
           "Moves down into place without fading", "Slide"),
    Preset("slide_left", "Slide in from right", {"type": "slideLeft", "durationMs": 500, "offsetX": 80},
           "Moves in from the right edge", "Slide"),
    Preset("slide_right", "Slide in from left", {"type": "slideRight", "durationMs": 500, "offsetX": -80},
           "Moves in from the left edge", "Slide"),
    Preset("scale", "Scale in", {"type": "scaleIn", "durationMs": 450, "scale": 0.8},
           "Grows from 80 % while fading in", "Scale"),
    Preset("zoom", "Zoom in", {"type": "zoomIn", "durationMs": 500, "scale": 0.3},
           "Grows from 30 % while fading in", "Scale"),
    Preset("pop", "Pop", {"type": "scaleIn", "durationMs": 400, "scale": 0.6, "curve": "Curves.easeOutBack"},
           "Overshoots slightly - good for buttons and badges", "Scale"),
    Preset("bounce", "Bounce in", {"type": "bounceIn", "durationMs": 800, "scale": 0.3,
                                   "curve": "Curves.elasticOut"}, "Springy zoom", "Scale"),
    Preset("hero_title", "Slow title fade", {"type": "fadeInUp", "durationMs": 1000, "offsetY": 16,
                                             "curve": "Curves.easeOutCubic"},
           "Long, soft entrance for headings"),
]
PRESET_BY_ID = {p.id: p for p in PRESETS}


def preset(preset_id: str) -> Preset:
    try:
        return PRESET_BY_ID[preset_id]
    except KeyError:
        raise KeyError(f"unknown animation preset {preset_id!r}") from None


def make_anim(preset_id: str, delay_ms: int | None = None, duration_ms: int | None = None, **extra) -> dict:
    """A fresh ``anim`` dict from a preset (delay / duration / any field overridable)."""
    a = copy.deepcopy(preset(preset_id).anim)
    if delay_ms:
        a["delayMs"] = int(delay_ms)
    if duration_ms:
        a["durationMs"] = int(duration_ms)
    a.update({k: v for k, v in extra.items() if v is not None})
    return normalize(a)


def normalize(anim: dict | None) -> dict | None:
    """Validate and canonicalise an anim dict (drops defaults that equal the model's implicit ones)."""
    if not anim:
        return None
    a = dict(anim)
    t = a.get("type")
    if t not in M.ANIM_TYPES:
        raise ValueError(f"unknown animation type {t!r} (one of {', '.join(M.ANIM_TYPES)})")
    for k in ("delayMs", "durationMs"):
        if k in a:
            a[k] = max(0, int(round(float(a[k]))))
    if a.get("delayMs") == 0:
        a.pop("delayMs")
    if a.get("durationMs") == 500:
        a.pop("durationMs")
    for k in ("offsetX", "offsetY", "scale"):
        if k in a and a[k] is not None:
            v = float(a[k])
            a[k] = int(v) if v == int(v) else v
    return a


def effective(anim: dict) -> dict:
    """The anim with every implicit default filled in (what the generated RadFx actually plays)."""
    a = {"delayMs": 0, "durationMs": 500, "offsetX": 0, "offsetY": 0, "curve": "Curves.easeOut", "scale": 1.0}
    a.update(anim or {})
    t = a.get("type")
    if t in _DIRECTIONAL:
        k, v = _DIRECTIONAL[t]
        if k not in (anim or {}):
            a[k] = v
    if t in _SCALE_DEFAULT and "scale" not in (anim or {}):
        a["scale"] = _SCALE_DEFAULT[t]
    a["fades"] = not str(t).startswith("slide")
    return a


def describe(anim: dict | None) -> str:
    """Short human description: 'Fade in up 600 ms after 300 ms'."""
    if not anim:
        return "No animation"
    e = effective(anim)
    p = next((p for p in PRESETS if p.anim.get("type") == anim.get("type")), None)
    name = p.label if p else anim.get("type")
    s = f"{name} {e['durationMs']} ms"
    if e["delayMs"]:
        s += f" after {e['delayMs']} ms"
    return s


# ------------------------------------------------------------------------------------------- edits
def apply_preset(screen: M.Screen, node_id: str, preset_id: str, delay_ms: int | None = None,
                 duration_ms: int | None = None) -> M.Patch:
    """Set a preset on one node (keeps its current delay unless one is given). Returns the applied patch."""
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    if delay_ms is None:
        delay_ms = (node.get("anim") or {}).get("delayMs")
    return M.set_anim(screen, node_id, make_anim(preset_id, delay_ms, duration_ms))


def clear(screen: M.Screen, node_id: str, recursive: bool = False) -> M.Patch:
    patch: M.Patch = []
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    targets = [n for n, *_ in M.walk_node(node)] if recursive else [node]
    for n in targets:
        if n.get("anim"):
            patch += M.set_anim(screen, n["id"], None)
    return patch


def _visual_children(node: dict) -> list[dict]:
    """Children in visual order: the children list, else the slots (body, child ...)."""
    if node.get("children"):
        return list(node["children"])
    out = []
    for v in (node.get("slots") or {}).values():
        out += v if isinstance(v, list) else [v]
    return out


def stagger(screen: M.Screen, parent_id: str, preset_id: str = "fade_up", start_ms: int = 0, step_ms: int = 120,
            duration_ms: int | None = None, skip_spacers: bool = True) -> M.Patch:
    """Animate every child of a Column / Row / ListView / Wrap / Stack one after another
    (delay = start + i * step). SizedBox / Spacer / Divider gaps are skipped so the rhythm stays even."""
    parent = screen.find(parent_id)
    if parent is None:
        raise KeyError(parent_id)
    patch: M.Patch = []
    i = 0
    for ch in _visual_children(parent):
        if skip_spacers and ch.get("type") in ("SizedBox", "Spacer", "Divider") and not ch.get("slots"):
            continue
        patch += M.set_anim(screen, ch["id"], make_anim(preset_id, start_ms + i * step_ms, duration_ms))
        i += 1
    return patch


def cascade(screen: M.Screen, root_id: str | None = None, start_ms: int = 0, step_ms: int = 150) -> M.Patch:
    """Re-time every animated node under ``root_id`` (default: the whole screen) in document order -
    top-to-bottom - keeping each node's animation type. Gives the login-page 'staircase' timing."""
    root = screen.find(root_id) if root_id else screen.tree
    if root is None:
        raise KeyError(root_id)
    patch: M.Patch = []
    i = 0
    for n, *_ in M.walk_node(root):
        a = n.get("anim")
        if not a:
            continue
        new = normalize({**a, "delayMs": start_ms + i * step_ms})
        patch += M.set_anim(screen, n["id"], new)
        i += 1
    return patch


def timeline(screen: M.Screen) -> list[tuple[str, int, int, dict]]:
    """[(node id, start ms, end ms, anim)] sorted by start - for a timeline strip / 'replay' in the preview."""
    out = []
    for n, *_ in screen.walk():
        a = n.get("anim")
        if a:
            e = effective(a)
            out.append((n["id"], e["delayMs"], e["delayMs"] + e["durationMs"], a))
    return sorted(out, key=lambda t: (t[1], t[0]))


def total_duration(screen: M.Screen) -> int:
    return max((t[2] for t in timeline(screen)), default=0)


# ------------------------------------------------------------------------------------- export helper
def to_flutter_animate(anim: dict) -> str:
    """The flutter_animate (package:flutter_animate) chain equivalent to an anim, e.g.
    ``.animate(delay: 300.ms).fadeIn(duration: 600.ms, curve: Curves.easeOut).moveY(begin: 30, end: 0, ...)``.
    RAD IDE generates RadFx (no third-party code); this is for copying into hand-written code."""
    e = effective(anim)
    d = f"duration: {e['durationMs']}.ms, curve: {e['curve']}"
    head = f".animate(delay: {e['delayMs']}.ms)" if e["delayMs"] else ".animate()"
    parts = []
    if e["fades"]:
        parts.append(f".fadeIn({d})")
    if e["offsetX"] or e["offsetY"]:
        if e["offsetX"]:
            parts.append(f".moveX(begin: {_num(e['offsetX'])}, end: 0, {d})")
        if e["offsetY"]:
            parts.append(f".moveY(begin: {_num(e['offsetY'])}, end: 0, {d})")
    if anim.get("type") in _SCALE_DEFAULT:
        s = _num(e["scale"])
        parts.append(f".scaleXY(begin: {s}, end: 1, {d})")
    return head + "".join(parts)


def _num(v) -> str:
    v = float(v)
    return str(int(v)) if v == int(v) else repr(v)
