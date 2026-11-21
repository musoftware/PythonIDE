"""Motion, layout sizes and TwoPane for the code generators that are not Python (plan
docs/plans/MOTION_VARIANTS_FOLDABLES.md, slice D): Ring (RingQt), classic Flutter, Kivy, React Native (Expo),
WinForms (C# / VB.NET partial classes) and the web pages of the GrapesJS designer.

Pure Python, shared by those generators:

* ``fx_plan(form, target)`` - ``motion.expand(form, target)`` plus each storyboard's ``duration`` and the
  ``chain`` of animations started when it completes (trigger "after").
* ``channels(sb, base_props)`` - the tracks of a storyboard for a target that draws with transforms (Kivy,
  React Native, Flutter, CSS) as *channels* relative to the control's designed look::

      {"tx": [[ms, px, ease], ...], "ty": ..., "sx": ..., "sy": ..., "rot": (degrees), "opacity": (0..1),
       "bg": [[ms, "start" | "parent" | "#rrggbb", ease]], "fg": ..., "reveal": (0..1 of the text),
       "visible": [[ms, True | False, ""]]}

  ``tx`` / ``ty`` are offsets from where the control is laid out (y grows downwards), so a slide works at
  every size / layout variant.  Keys always start at 0 (the start value is inserted, like
  ``_rad_value_at`` does).
* ``variant_plan(form)`` - ``variants.plan(form)`` (slice C) or None when the form has no sizes.
* ``two_panes(form)`` - the TwoPane controls of a mobile form with their two pane children.
* ``issues(form, target)`` - what a target shows differently / cannot do (Error List lines).

Targets: ``ring`` ``dart`` ``kivy`` ``rn`` ``winforms`` ``css`` (see motion.presets.TARGET_CAPS).
"""
from __future__ import annotations

EASE_NAMES = ("linear", "in", "out", "inout", "back", "elastic", "bounce", "sine")
TRANSFORM_TARGETS = ("kivy", "rn", "dart", "css")
TARGET_LABELS = {"ring": "Ring (RingQt)", "dart": "Flutter", "kivy": "Kivy", "rn": "React Native (Expo)",
                 "winforms": "WinForms", "css": "the web page"}
# plugin id -> fx target
PLUGIN_TARGETS = {"ring-qt": "ring", "ring-script": "ring", "ring-app": "ring", "flutter": "dart",
                  "kivy": "kivy", "expo": "rn", "winforms-cs": "winforms", "winforms-vb": "winforms"}
# where the platform has no foldable API: how size variants / TwoPane behave (shown once per form)
FOLD_FALLBACK = {
    "ring": "Ring desktop windows have no posture / hinge: layout sizes match the window size; "
            "RADIDE_POSTURE / RADIDE_SPAN / RADIDE_HINGE simulate a foldable",
    "kivy": "Kivy has no foldable API: layout sizes match the window size and orientation, the posture comes "
            "from RADIDE_POSTURE / RADIDE_SPAN and TwoPane splits at Ratio (or RADIDE_HINGE)",
    "rn": "React Native has no foldable API in Expo Go: layout sizes match the window size and orientation, "
          "TwoPane splits at Ratio (posture 'flat', one screen)",
    "winforms": "WinForms has no foldable API: layout sizes match the window size; RADIDE_POSTURE / "
                "RADIDE_SPAN simulate a foldable",
}


# ============================================================================================ motion
def has_motion(form) -> bool:
    lst = form.extra.get("animations")
    return isinstance(lst, list) and any(isinstance(a, dict) and a.get("enabled", True) for a in lst)


def _dur(tracks) -> int:
    d = 0
    for _t, _p, keys in tracks:
        for k in keys:
            try:
                d = max(d, int(k[0]))
            except (TypeError, ValueError, IndexError):
                pass
    return max(1, d)


def fx_plan(form, target: str) -> dict | None:
    """motion.expand(form, target) with "duration" and "chain" per storyboard; None without animations."""
    if not has_motion(form):
        return None
    import importlib
    plan = importlib.import_module("radide.motion.expand").expand(form, target)
    if not plan["storyboards"]:
        return None
    by_fx = {sb["fx"]: sb for sb in plan["storyboards"]}
    for sb in plan["storyboards"]:
        sb["duration"] = _dur(sb["tracks"])
        sb["chain"] = []
    for t in plan["triggers"]:
        if t["on"] == "after" and t.get("after") in by_fx:
            by_fx[t["after"]]["chain"].append(t["fx"])
    return plan


def trigger_of(plan: dict, fx: str) -> dict:
    return next((t for t in plan["triggers"] if t["fx"] == fx), {"on": "load", "source": "", "intervalMs": 0,
                                                               "leave": "reverse"})


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _rel(v, start: float, base: dict) -> float:
    """A relative keyframe value made absolute against *start* (see states.COMMON_RT _rad_resolve)."""
    if isinstance(v, dict):
        if "reveal" in v:
            return _num(v["reveal"], 1.0)
        val = start * _num(v.get("m", 1), 1.0) + _num(v.get("d", 0))
        if v.get("of"):
            val += _num(v.get("f", 0)) * _num(base.get(str(v["of"])), 0.0)
        return val
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    return _num(v, start)


def _color(v) -> str:
    if isinstance(v, str) and v == "$parent":
        return "parent"
    if isinstance(v, str) and v.startswith("#"):
        return v
    return "start"


def channels(sb: dict, base_props: dict | None = None) -> dict:
    """The tracks of FxPlan storyboard *sb* as transform channels (see the module docstring)."""
    base = dict(base_props or {})
    out: dict[str, list] = {}

    def put(ch, keys, start, conv):
        lst = []
        for k in keys:
            ms = int(_num(k[0]))
            ease = str(k[2]) if len(k) > 2 and k[2] else ""
            lst.append([ms, conv(k[1]), ease if ease in EASE_NAMES else ""])
        if not lst:
            return
        if lst[0][0] > 0:
            lst.insert(0, [0, start, ""])
        out[ch] = lst

    for _t, prop, keys in sb["tracks"]:
        if prop in ("Left", "Top"):
            b = _num(base.get(prop), 0.0)
            put("tx" if prop == "Left" else "ty", keys, 0.0, lambda v, b=b: round(_rel(v, b, base) - b, 3))
        elif prop in ("ScaleX", "ScaleY"):
            put("sx" if prop == "ScaleX" else "sy", keys, 1.0, lambda v: round(_rel(v, 1.0, base), 4))
        elif prop in ("Width", "Height"):          # only when a target without transforms asked for it
            b = max(1.0, _num(base.get(prop), 1.0))
            put("sx" if prop == "Width" else "sy", keys, 1.0, lambda v, b=b: round(_rel(v, b, base) / b, 4))
        elif prop == "Rotation":
            put("rot", keys, 0.0, lambda v: round(_rel(v, 0.0, base), 3))
        elif prop == "Opacity":
            put("opacity", keys, 1.0, lambda v: round(max(0.0, min(1.0, _rel(v, 1.0, base))), 4))
        elif prop in ("BackColor", "ForeColor"):
            put("bg" if prop == "BackColor" else "fg", keys, "start", _color)
        elif prop == "Text":
            put("reveal", keys, 1.0, lambda v: round(max(0.0, min(1.0, _rel(v, 1.0, base))), 4))
        elif prop == "Visible":
            put("visible", keys, True, lambda v: (not isinstance(v, bool)) or v)
    return out


def ease_js(name: str) -> str:
    return name if name in EASE_NAMES else "linear"


# ============================================================================================ variants
def variant_plan(form) -> dict | None:
    """variants.plan(form) of slice C (None when the form has no layout sizes or the module is missing)."""
    d = form.extra.get("variants")
    if not isinstance(d, dict) or not d.get("sizes"):
        return None
    try:
        from .variants import model as vm
    except Exception:  # noqa: BLE001 - slice C not installed
        return None
    try:
        return vm.plan(form)
    except Exception:  # noqa: BLE001 - a broken size must not break code generation
        return None


def when_tuple(when: dict) -> tuple:
    """(minW, maxW, minH, maxH, orientation, posture, span, fold) with None for missing values."""
    w = when or {}

    def n(k):
        v = w.get(k)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def s(k, norm=None):
        v = w.get(k)
        if v in (None, ""):
            return None
        v = str(v).strip().lower()
        return norm(v) if norm else v

    def posture(v):
        try:
            from .variants.model import normalize_posture
            return normalize_posture(v) or v
        except Exception:  # noqa: BLE001
            return v
    return (n("minWidth"), n("maxWidth"), n("minHeight"), n("maxHeight"),
            s("orientation", lambda v: "landscape" if v.startswith("land") else "portrait"),
            s("posture", posture), s("span"), s("fold"))


def place_rect(spec, cw, ch) -> tuple[int, int, int, int]:
    x, y, w, h, rx, ry, rw, rh = spec
    return (int(round(x + rx * cw)), int(round(y + ry * ch)), max(0, int(round(w + rw * cw))),
            max(0, int(round(h + rh * ch))))


def managed_controls(vplan: dict | None) -> set:
    """Controls whose geometry some size changes (their place comes from the size runtime)."""
    out = set()
    if not vplan:
        return out
    for ctl in (vplan.get("controls") or {}).values():
        for name, ov in ctl.items():
            if ov.get("place") is not None:
                out.add(name)
    return out


# ============================================================================================ TwoPane
def _truth(v, default=True) -> bool:
    if isinstance(v, str):
        return v.strip().lower() not in ("false", "0", "no", "")
    return default if v is None else bool(v)


def two_panes(form) -> list[dict]:
    """[{"name", "panes": [start, end | None], "mode", "ratio", "single", "hinge_aware"}] of the TwoPane
    controls of *form* (the first two child controls are the panes, CONTRACTS 10.8)."""
    out = []
    for c in form.controls:
        if c.type != "TwoPane":
            continue
        kids = [k for k in form.children(c.name) if not k.ctype.nonvisual][:2]
        p = c.props
        try:
            ratio = min(0.95, max(0.05, float(p.get("Ratio", 0.5))))
        except (TypeError, ValueError):
            ratio = 0.5
        out.append({"name": c.name, "panes": [k.name for k in kids] + [None] * (2 - len(kids)),
                    "mode": str(p.get("PaneMode") or "Auto").capitalize(), "ratio": ratio,
                    "single": "End" if str(p.get("SinglePane") or "Start").lower() == "end" else "Start",
                    "hinge_aware": _truth(p.get("HingeAware", True))})
    return out


# ============================================================================================ Error List
def issues(form, target: str) -> list[tuple[str, str]]:
    """[(severity, message)]: fallbacks of the animation presets on *target* and what the target cannot do."""
    out: list[tuple[str, str]] = []
    label = TARGET_LABELS.get(target, target)
    if has_motion(form):
        try:
            plan = fx_plan(form, target) or {"fallbacks": [], "triggers": []}
        except Exception as e:  # noqa: BLE001
            return [("Warning", f"Animations: {e}")]
        for fx, ctl, msg in plan.get("fallbacks") or []:
            out.append(("Warning", f"{fx} ({ctl or form.name}): {msg}"))
        if target == "ring":
            for sb in plan.get("storyboards") or []:
                if sb.get("target") and any(p == "Opacity" for _t, p, _k in sb["tracks"]):
                    out.append(("Warning", f"{sb['fx']} ({sb['target']}): fades the text and background colours "
                                           f"on {label} (RingQt has no opacity effect)"))
        if target in ("rn", "dart", "kivy"):
            for t in plan.get("triggers") or []:
                if t["on"] == "hover":
                    out.append(("Info", f"{t['fx']}: 'On hover' needs a mouse (web / desktop); "
                                        f"touch screens never fire it on {label}"))
    if variant_plan(form) and target in FOLD_FALLBACK:
        if any(s.get("when", {}).get(k) for s in form.extra["variants"].get("sizes") or [] if isinstance(s, dict)
               for k in ("posture", "span", "fold")):
            out.append(("Info", f"Layout sizes: {FOLD_FALLBACK[target]}"))
    if two_panes(form) and target in ("rn",):
        out.append(("Info", f"TwoPane: {FOLD_FALLBACK[target]}"))
    return out


NOT_APPLICABLE = {
    "godot": "Godot scenes animate with Godot's AnimationPlayer; RAD IDE animation presets are not generated",
    "godot3d": "Godot scenes animate with Godot's AnimationPlayer; RAD IDE animation presets are not generated",
    "rust-cargo": "Rust (Cargo) projects have no designed forms",
}


__all__ = ["EASE_NAMES", "TRANSFORM_TARGETS", "PLUGIN_TARGETS", "TARGET_LABELS", "FOLD_FALLBACK", "NOT_APPLICABLE",
           "has_motion", "fx_plan", "trigger_of", "channels", "ease_js", "variant_plan", "when_tuple", "place_rect",
           "managed_controls", "two_panes", "issues"]
