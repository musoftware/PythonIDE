"""``expand(form, target) -> FxPlan`` (plan 1.3): the form's animation presets as storyboards + triggers.

FxPlan = {"storyboards": [{"name": "_fx_fx1", "fx": "fx1", "target": "Button1",
                           "tracks": [(target, prop, keys)], "repeat": bool, "count": int,
                           "autoreverse": bool, "autostart": bool, "delayMs": int, "restore": bool}],
          "triggers": [{"fx", "sb", "on", "source", "intervalMs", "after", "leave", "target"}],
          "fallbacks": [(fx, control, message)],
          "reduced_motion": bool}

``repeat`` True = forever (``repeat: 0`` in the model), ``count`` = plays (1 = once);  ``restore`` = the
animation ends where it started (entrance / attention / auto reverse), so the runtime gives the geometry
back to Anchor / Dock afterwards.  Keys are ``[ms, value, ease]`` with relative values (see presets.py).
Pure Python: used by code generation (python-tk / python-qt / vbrun / bridges, D's other targets) and by
the Animations panel preview (slice B)."""
from __future__ import annotations

import re

from . import model as M
from . import presets as P

TARGETS = tuple(P.TARGET_CAPS)
_SAFE = re.compile(r"[^A-Za-z0-9_]")


def sb_name(fx_id: str) -> str:
    return "_fx_" + _SAFE.sub("_", str(fx_id or "fx"))


def _int(v, default=0, lo=0, hi=10 ** 7) -> int:
    try:
        return max(lo, min(hi, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def expand(form, target: str = "py") -> dict:
    """Storyboards / triggers / fallbacks for code generation *target* (see TARGETS)."""
    target = target if target in P.TARGET_CAPS else "py"
    controls = {c.name: c for c in form.visual()} if hasattr(form, "visual") else {}
    plan = {"storyboards": [], "triggers": [], "fallbacks": [], "reduced_motion": M.respect_reduced_motion(form)}
    lst = [a for a in form.extra.get("animations") or [] if isinstance(a, dict) and a.get("enabled", True)]
    ids = set()
    tname = P.TARGET_NAMES.get(target, target)
    for a in lst:
        fx = str(a.get("id") or "")
        preset = P.get(a.get("preset"))
        tgt = str(a.get("target") or "")
        if not fx or fx in ids or preset is None or (tgt and tgt not in controls):
            continue                                    # validate() reports these
        ids.add(fx)
        base = form.props if not tgt else controls[tgt].props
        tracks, note = preset.build(a, base, form, target)
        if not tracks:
            continue
        if note:
            plan["fallbacks"].append((fx, tgt, f"{preset.label} on {tgt or 'the form'}: {note} on {tname}"))
        rep = _int(a.get("repeat", 1), 1, 0, 100000)
        trig = a.get("trigger") if isinstance(a.get("trigger"), dict) else {}
        on = trig.get("on", "load") if trig.get("on", "load") in P.TRIGGERS else "load"
        name = sb_name(fx)
        autorev = bool(a.get("autoreverse"))
        plan["storyboards"].append({
            "name": name, "fx": fx, "target": tgt,
            "tracks": [(tgt, prop, [list(k) for k in keys]) for prop, keys in tracks],
            "repeat": rep == 0, "count": max(1, rep), "autoreverse": autorev,
            "autostart": on == "load", "delayMs": _int(a.get("delayMs", 0)),
            "restore": bool(preset.restores or autorev), "preset": preset.id})
        src = trig.get("source") or tgt
        if on in ("click", "hover") and src and src not in controls:
            src = tgt
        leave = trig.get("leave", "reverse")
        plan["triggers"].append({
            "fx": fx, "sb": name, "on": on, "source": src if on in ("click", "hover") else (src or ""),
            "intervalMs": _int(trig.get("intervalMs", 0)) if on == "timer" else 0,
            "after": trig.get("after") if on == "after" else None,
            "leave": leave if leave in P.HOVER_LEAVE else "reverse", "target": tgt})
    # chains whose animation is missing / disabled never start: drop them (validate() reports them)
    plan["triggers"] = [t for t in plan["triggers"] if t["on"] != "after" or t["after"] in ids]
    return plan


def storyboard_dict(sb: dict) -> dict:
    """An FxPlan storyboard in the .form storyboard shape (timeline.props_at / the Timeline panel)."""
    return {"name": sb["name"], "autostart": sb.get("autostart", False), "repeat": sb.get("repeat", False),
            "autoreverse": sb.get("autoreverse", False),
            "tracks": [{"target": t, "property": p, "keys": [list(k) for k in keys]} for t, p, keys in sb["tracks"]]}
