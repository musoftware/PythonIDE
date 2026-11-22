"""Motion, visual states and layout variants for the NATIVE runtimes (pure Python, no Qt).

The IDE's Python runtime (``runtime_py.FX_RT`` + ``features/timeline.STORYBOARD_RT`` + ``features/states.VSM_RT``
+ ``variants/runtime_py.VARIANTS_RT``) is the reference.  The native runtimes - radforms (C, C++, Fortran, Rust,
Go, Lua, JS / Node.js: ``radforms_motion.inc``), the FreeBASIC VB6 runtime (``vbrt_motion.bi``), .NET
(``RadWinForms.cs`` ``RadMotion``) and Java Swing (``RadSwing.java`` ``RadMotion``) - get the SAME data, already
expanded by :func:`radide.motion.expand` (presets -> keyframes with relative values), as a list of records.
Every runtime parses the same records and plays them with the same rules (easings, relative keys resolved
against the values at Begin, repeat / auto reverse / count, triggers, chains, reduced motion, CSS-like size
cascade, Visual State Manager precedence).

Records (lists of strings; written TAB-separated, one per line, ``\\t \\n \\r \\\\`` escaped - the radforms
description syntax - at most 10 fields):

    XR  respect                              1 = the form respects the system's reduced-motion setting
    X   fx target count forever autorev delayMs restore     a storyboard (target "" = the form)
    XT  on source intervalMs after leave     its trigger: load click hover timer show hide after manual
    K   prop ms ease kind a b c d            a key of the last X (tracks = consecutive keys of one prop)
          kind n: number a          c: colour a (#rrggbb)       b: bool a (1/0)     s: text a
               r: relative = start * a + b + d * start(c)  (c = "" | Width | Height; colours / bools /
                  texts keep their start value)
               p: the parent's background colour            v: typewriter, the start text up to fraction a
          ease: "" (linear) in out inout sine back elastic bounce
    Q   control state prop value             a visual state override (control "" = the form);
                                             states MouseOver Pressed Focused Disabled are automatic
    V   size minW maxW minH maxH orientation posture span fold   a layout size ("" = no condition)
    VL  size control "x y w h rx ry rw rh"   the place on that size, ONE field (left = x + rx * container width)
    VP  size control prop value              a property on that size (control "" = the form)

Values of Q / VP: numbers, ``True`` / ``False``, colours ``#rrggbb``, text.

Runtime API every native runtime offers (names of the Python runtime):
    form: BeginAnimation(fx | storyboard name), StopAnimation(name), GoToState(state[, control]),
          ApplySizeVariants(), CurrentSizes (comma-separated ids), CurrentState
    events: <Form>_SizeVariantChanged, <Storyboard>_Completed
    environment: RADIDE_REDUCED_MOTION=1 (or the Windows "Show animations" setting off), RADIDE_POSTURE,
                 RADIDE_SPAN (foldables simulated on the desktop)
``Animate(control, preset)`` (an ad hoc preset from code) needs the preset builders at run time: native
builds do not have it - user code calling it keeps the builder's fallback reason (design the animation
with trigger "Manual (from code)" and call BeginAnimation instead).
"""
from __future__ import annotations

from .expand import expand as _expand_form
from . import model as _model

# properties the native runtimes animate / switch (the rest is ignored with a warning in the Error List)
NUM_PROPS = ("Left", "Top", "Width", "Height", "FontSize", "Opacity", "Value")
COLOR_PROPS = ("BackColor", "ForeColor")
BOOL_PROPS = ("Visible", "FontBold", "FontItalic", "Enabled", "Checked")
TEXT_PROPS = ("Text",)
NATIVE_PROPS = NUM_PROPS + COLOR_PROPS + BOOL_PROPS + TEXT_PROPS
ANIM_PROPS = ("Left", "Top", "Width", "Height", "BackColor", "ForeColor", "Opacity", "FontSize", "Value",
              "Text", "Visible")
EASES = ("linear", "in", "out", "inout", "back", "elastic", "bounce", "sine")
AUTO_STATES = ("MouseOver", "Pressed", "Focused", "Disabled")
STATE_PROPS = ("Text", "BackColor", "ForeColor", "Left", "Top", "Width", "Height", "Visible",
               "FontSize", "FontBold", "FontItalic", "Opacity")
FORM_STATE_PROPS = ("Text", "BackColor", "Width", "Height", "Opacity")
FIELDS = 10


# ---------------------------------------------------------------------------------------------- values
def _num(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "0"
    if f.is_integer():
        return str(int(f))
    return f"{f:.6f}".rstrip("0").rstrip(".")


def _rgb(v) -> str | None:
    s = str(v or "").strip()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) == 8:                     # #AARRGGBB
            h = h[2:]
        if len(h) == 6:
            try:
                int(h, 16)
                return "#" + h.lower()
            except ValueError:
                return None
    names = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
             "yellow": "#ffff00", "gray": "#808080", "grey": "#808080", "orange": "#ffa500", "navy": "#000080",
             "silver": "#c0c0c0", "lime": "#00ff00", "transparent": None}
    return names.get(s.lower())


def value_text(prop: str, v) -> str:
    """A Q / VP value in the neutral text form (numbers, True / False, #rrggbb, text)."""
    if prop in BOOL_PROPS:
        if isinstance(v, str):
            return "True" if v.strip().lower() in ("1", "true", "yes", "on") else "False"
        return "True" if v else "False"
    if prop in COLOR_PROPS:
        return _rgb(v) or str(v or "")
    if prop in NUM_PROPS:
        return _num(v)
    return "" if v is None else str(v)


def _key(prop: str, k) -> list[str] | None:
    """One keyframe [ms, value, ease] -> K record fields (without "K")."""
    try:
        ms = max(0, int(round(float(k[0]))))
    except (TypeError, ValueError, IndexError):
        return None
    v = k[1] if len(k) > 1 else None
    ease = str(k[2]) if len(k) > 2 and k[2] else ""
    ease = "" if ease not in EASES or ease == "linear" else ease
    head = [prop, str(ms), ease]
    if isinstance(v, str) and v == "$parent":
        return head + ["p", "", "", "", ""]
    if isinstance(v, dict):
        if "reveal" in v:
            return head + ["v", _num(v.get("reveal", 1)), "", "", ""]
        of = str(v.get("of") or "")
        of = of if of in ("Width", "Height") else ""
        return head + ["r", _num(v.get("m", 1)), _num(v.get("d", 0)), of, _num(v.get("f", 0)) if of else "0"]
    if prop in COLOR_PROPS:
        c = _rgb(v)
        return head + (["c", c, "", "", ""] if c else ["r", "1", "0", "", "0"])
    if prop in BOOL_PROPS:
        return head + ["b", "1" if (v.strip().lower() in ("1", "true", "yes", "on") if isinstance(v, str)
                                    else bool(v)) else "0", "", "", ""]
    if prop in NUM_PROPS:
        return head + ["n", _num(v), "", "", ""]
    return head + ["s", "" if v is None else str(v), "", "", ""]


# ---------------------------------------------------------------------------------------------- pieces
def _storyboards(form) -> list[dict]:
    """The form's Blend storyboards (extra["storyboards"]) in the FxPlan storyboard shape."""
    names = {c.name for c in form.visual()} if hasattr(form, "visual") else set()
    out, seen = [], set()
    for sb in form.extra.get("storyboards") or []:
        if not isinstance(sb, dict):
            continue
        name = str(sb.get("name") or "")
        if not name.isidentifier() or name in seen or name in names:
            continue
        seen.add(name)
        tracks = []
        for tr in sb.get("tracks") or []:
            if not isinstance(tr, dict):
                continue
            t, p = str(tr.get("target") or ""), str(tr.get("property") or "")
            if (t and t not in names) or p not in ANIM_PROPS:
                continue
            keys = sorted((k for k in tr.get("keys") or [] if isinstance(k, (list, tuple)) and len(k) >= 2),
                          key=lambda k: float(k[0]) if isinstance(k[0], (int, float)) else 0)
            if keys:
                tracks.append((t, p, keys))
        if tracks:
            out.append({"name": name, "fx": name, "target": "", "tracks": tracks, "repeat": bool(sb.get("repeat")),
                        "count": 1, "autoreverse": bool(sb.get("autoreverse")), "delayMs": 0, "restore": False,
                        "autostart": bool(sb.get("autostart"))})
    return out


def _sb_records(sb: dict, trig: dict) -> list[list[str]]:
    out = [["X", str(sb["fx"]), str(sb.get("target") or ""), str(max(1, int(sb.get("count", 1) or 1))),
            "1" if sb.get("repeat") else "0", "1" if sb.get("autoreverse") else "0",
            str(int(sb.get("delayMs", 0) or 0)), "1" if sb.get("restore") else "0"],
           ["XT", str(trig.get("on") or "manual"), str(trig.get("source") or ""), str(int(trig.get("intervalMs") or 0)),
            str(trig.get("after") or ""), str(trig.get("leave") or "reverse")]]
    for _t, p, keys in sb["tracks"]:            # one target per X (Blend storyboards are split by target)
        for k in keys:
            rec = _key(p, k)
            if rec is not None:
                out.append(["K"] + rec)
    return out


def motion_records(form, target: str = "py") -> tuple[list[list[str]], list[tuple[str, str, str]]]:
    """(records, fallback notes) of the form's animations + Blend storyboards."""
    recs: list[list[str]] = []
    notes: list[tuple[str, str, str]] = []
    has = bool(form.extra.get("animations")) or bool(form.extra.get("storyboards"))
    if not has:
        return recs, notes
    recs.append(["XR", "1" if _model.respect_reduced_motion(form) else "0"])
    plan = _expand_form(form, target)
    notes += plan["fallbacks"]
    trig = {t["fx"]: t for t in plan["triggers"]}
    for sb in plan["storyboards"]:
        recs += _sb_records(sb, trig.get(sb["fx"], {"on": "manual"}))
    for sb in _storyboards(form):
        # a Blend storyboard may animate several controls: one X per target (same name: Begin starts all)
        by_target: dict[str, list] = {}
        for t, p, keys in sb["tracks"]:
            by_target.setdefault(t, []).append((t, p, keys))
        for t, tracks in by_target.items():
            d = dict(sb, target=t, tracks=tracks)
            recs += _sb_records(d, {"on": "load" if sb["autostart"] else "manual"})
    return recs, notes


def state_records(form) -> list[list[str]]:
    out = []
    for c in form.controls:
        if getattr(c.ctype, "nonvisual", False) or not c.states:
            continue
        for s, ov in c.states.items():
            if isinstance(ov, dict):
                for p, v in ov.items():
                    if p in STATE_PROPS:
                        out.append(["Q", c.name, str(s), p, value_text(p, v)])
    for s, ov in (form.extra.get("states") or {}).items():
        if isinstance(ov, dict):
            for p, v in ov.items():
                if p in FORM_STATE_PROPS:
                    out.append(["Q", "", str(s), p, value_text(p, v)])
    return out


def variant_records(form) -> list[list[str]]:
    try:
        from ..variants import model as VM
        vp = VM.plan(form)
    except Exception:  # noqa: BLE001 - broken variant data must never break a build
        return []
    if vp is None:
        return []
    out = []
    for s in vp["sizes"]:
        w = s.get("when") or {}

        def g(k):
            v = w.get(k)
            return "" if v is None or v == "" else _num(v) if k[:3] in ("min", "max") else str(v).strip().lower()
        posture = VM.normalize_posture(w.get("posture")) if w.get("posture") else ""
        out.append(["V", s["id"], g("minWidth"), g("maxWidth"), g("minHeight"), g("maxHeight"),
                    "landscape" if g("orientation").startswith("land") else
                    "portrait" if g("orientation").startswith("port") else "",
                    posture, g("span"), g("fold")])
    for vid, ctls in vp["controls"].items():
        for name, e in ctls.items():
            if e.get("place") is not None:
                out.append(["VL", vid, name, " ".join(_num(x) for x in e["place"])])
            for p, v in (e.get("props") or {}).items():
                out.append(["VP", vid, name, p, value_text(p, v)])
    for vid, props in vp["form"].items():
        for p, v in props.items():
            out.append(["VP", vid, "", p, value_text(p, v)])
    return out


def records(form, target: str = "py") -> list[list[str]]:
    """Every record of *form* ([] when it uses none of motion / states / variants)."""
    recs, _notes = motion_records(form, target)
    return recs + state_records(form) + variant_records(form)


def notes(form, target: str = "py") -> list[str]:
    """How the native runtime shows what it cannot draw exactly (Error List / build log, never silent)."""
    out = [msg for _fx, _c, msg in motion_records(form, target)[1]]
    for c in form.controls:
        for s, ov in (c.states or {}).items():
            if isinstance(ov, dict) and "Opacity" in ov:
                out.append(f"{form.name}.{c.name}: state {s} sets Opacity - child controls of a native window "
                           "have no transparency (ignored)")
    return out


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")


def lines(form, target: str = "py") -> list[str]:
    """records() as TAB-separated escaped lines (the radforms description syntax)."""
    return ["\t".join(_esc(f) for f in r[:FIELDS]) for r in records(form, target)]


def text(form, target: str = "py") -> str:
    """lines() joined with "\\n" ("" when the form has none) - the string the other runtimes embed."""
    ls = lines(form, target)
    return "\n".join(ls) + "\n" if ls else ""


def uses(form) -> bool:
    return bool(form.extra.get("animations") or form.extra.get("storyboards") or form.extra.get("states")
                or any(c.states for c in form.controls) or variant_records(form))


__all__ = ["records", "lines", "text", "notes", "uses", "motion_records", "state_records", "variant_records",
           "value_text", "NATIVE_PROPS"]
