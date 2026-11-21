"""Layout variants of classic forms: per-size overrides of the designed form (pure Python, no Qt).

Contract 1.5 of docs/plans/MOTION_VARIANTS_FOLDABLES.md.  The form keeps ONE design (the *base*); a
layout *size* says when it applies (``when``) and how it is previewed (``preview``); a control may
override a few properties on a size::

    form.extra["variants"] = {
        "sizes": [{"id": "compact", "label": "Phone", "when": {"maxWidth": 599},
                   "preview": {"width": 400, "height": 800}}, ...],
        "form":  {"compact": {"Width": 400, "Height": 800}}}       # form-level overrides
    ctrl.variants = {"compact": {"Left": 16, "Width": 368, "Visible": False}}

Matching works like the CSS cascade: every size whose ``when`` holds applies, in list order, later
sizes win.  Geometry overrides are absolute at the size's preview size; code generators turn them into
per-size Anchor / Dock specs (``layout.Place``) so controls still stretch inside the size's range.

The matching algorithm is the source text ``MATCH_RT``: the generated programs (``runtime_py``) and
the designer run exactly the same code.
"""
from __future__ import annotations

import copy
import re

from ..layout import client_size, place_specs, relayout, resize_children

# properties a size may override (the rest of a control is the same on every size)
VARIANT_PROPS = ("Left", "Top", "Width", "Height", "Anchor", "Dock", "Visible", "Text", "FontSize", "FontBold",
                 "BackColor", "ForeColor", "TextAlign", "Align", "Spacing", "Padding")
FORM_VARIANT_PROPS = ("Width", "Height", "Text", "BackColor")
GEOMETRY = ("Left", "Top", "Width", "Height", "Anchor", "Dock")
# what the generated python runtime sets through _RadIO (geometry goes through the size's Place)
RUNTIME_PROPS = ("Visible", "Text", "FontSize", "FontBold", "BackColor", "ForeColor")
FORM_RUNTIME_PROPS = ("Text", "BackColor")
_INT = {"Left", "Top", "Width", "Height", "FontSize", "Spacing"}
_BOOL = {"Visible", "FontBold"}
WHEN_KEYS = ("minWidth", "maxWidth", "minHeight", "maxHeight", "orientation", "posture", "span", "fold")

# ---------------------------------------------------------------------------------------------- matching
MATCH_RT = r'''

def _rad_vposture(v):
    """Any posture spelling -> flat | half-opened | folded ("" = unknown)."""
    s = str(v or "").strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    if s in ("halfopened", "halfopen", "half", "tabletop", "book"):
        return "half-opened"
    if s in ("folded", "closed", "fold", "cover"):
        return "folded"
    if s in ("flat", "open", "opened"):
        return "flat"
    return ""


def _rad_vmatch(when, w, h, orientation=None, posture=None, span=None, fold=None):
    """True when every condition of a layout size's "when" holds for a client area of w x h."""
    if not isinstance(when, dict):
        return False
    for k, v in when.items():
        if v is None or v == "":
            continue
        if k in ("minWidth", "maxWidth", "minHeight", "maxHeight"):
            try:
                lim = float(v)
            except (TypeError, ValueError):
                return False
            val = w if k.endswith("Width") else h
            if (val < lim) if k.startswith("min") else (val > lim):
                return False
        elif k == "orientation":
            if str(v).strip().lower()[:4] != (orientation or ("landscape" if w > h else "portrait"))[:4]:
                return False
        elif k == "posture":
            if _rad_vposture(v) != _rad_vposture(posture):
                return False
        elif k == "span":
            if str(v).strip().lower() != (span or "single"):
                return False
        elif k == "fold":
            if str(v).strip().lower() != str(fold or "").lower():
                return False
    return True


def _rad_vmatching(sizes, w, h, orientation=None, posture=None, span=None, fold=None):
    """Ids of the sizes that apply, in list order (later ones win, like CSS)."""
    return [s["id"] for s in sizes if _rad_vmatch(s.get("when"), w, h, orientation, posture, span, fold)]
'''

_NS: dict = {}
exec(compile(MATCH_RT, "<variants-match>", "exec"), _NS)        # noqa: S102 - our own constant
_vmatch = _NS["_rad_vmatch"]
normalize_posture = _NS["_rad_vposture"]


# ---------------------------------------------------------------------------------------------- presets
def _sz(vid, label, when, preview=None) -> dict:
    d = {"id": vid, "label": label, "when": dict(when)}
    if preview:
        d["preview"] = dict(preview)
    return d


# id -> size (a fresh copy is made by preset()); grouped for the Add Size dialog
PRESETS = {
    "phone": _sz("phone", "Phone", {"maxWidth": 599}, {"width": 400, "height": 760}),
    "tablet": _sz("tablet", "Tablet", {"minWidth": 600, "maxWidth": 1023}, {"width": 800, "height": 1000}),
    "small": _sz("small", "Small", {"maxWidth": 639}, {"width": 480}),
    "medium": _sz("medium", "Medium", {"minWidth": 640, "maxWidth": 1023}, {"width": 800}),
    "large": _sz("large", "Large", {"minWidth": 1024}, {"width": 1280}),
    "portrait": _sz("portrait", "Portrait", {"orientation": "portrait"}, {"width": 412, "height": 860}),
    "landscape": _sz("landscape", "Landscape", {"orientation": "landscape"}, {"width": 860, "height": 412}),
    "folded": _sz("folded", "Folded", {"posture": "folded"},
                  {"device": "galaxy_z_fold6", "orientation": "Portrait", "posture": "Folded"}),
    "halfopen": _sz("halfopen", "Half-open", {"posture": "half-opened"},
                    {"device": "galaxy_z_fold6", "orientation": "Landscape", "posture": "HalfOpened"}),
    "flat": _sz("flat", "Flat", {"posture": "flat"},
                {"device": "galaxy_z_fold6", "orientation": "Portrait", "posture": "Flat"}),
    "dual": _sz("dual", "Dual screen", {"span": "dual"},
                {"device": "surface_duo2", "orientation": "Portrait", "posture": "Flat"}),
}
PRESET_SETS = {
    "desktop": ("small", "medium", "large"),          # windows: Small < 640, Medium 640-1023, Large >= 1024
    "phone": ("portrait", "landscape"),
    "foldable": ("folded", "halfopen", "flat"),
    "responsive": ("phone", "tablet"),
}
PRESET_GROUPS = (("Window width", ("phone", "tablet", "small", "medium", "large")),
                 ("Orientation", ("portrait", "landscape")),
                 ("Foldable", ("folded", "halfopen", "flat", "dual")))


def preset(key: str) -> dict:
    return copy.deepcopy(PRESETS[key])


# ---------------------------------------------------------------------------------------------- storage
def data(form, create: bool = False) -> dict:
    """form.extra["variants"] ({} when the form has none and *create* is False)."""
    d = form.extra.get("variants")
    if not isinstance(d, dict):
        if not create:
            return {}
        d = form.extra["variants"] = {}
    if create:
        d.setdefault("sizes", [])
    return d


def sizes(form) -> list[dict]:
    """The form's layout sizes (list order = cascade order)."""
    out = []
    for s in data(form).get("sizes") or []:
        if isinstance(s, dict) and s.get("id"):
            out.append(s)
    return out


def size(form, vid) -> dict | None:
    return next((s for s in sizes(form) if s["id"] == vid), None)


def label(form_or_size, vid=None) -> str:
    s = form_or_size if isinstance(form_or_size, dict) else size(form_or_size, vid)
    if not s:
        return str(vid or "")
    return str(s.get("label") or s.get("id"))


def new_id(form, base: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_]", "", str(base or "size").replace(" ", "_")).lower() or "size"
    if base[0].isdigit():
        base = "s" + base
    taken = {s["id"] for s in sizes(form)}
    if base not in taken:
        return base
    i = 2
    while f"{base}{i}" in taken:
        i += 1
    return f"{base}{i}"


def add_size(form, sz: dict, index: int | None = None) -> dict:
    """Adds a copy of *sz* (its id made unique) and returns it."""
    sz = copy.deepcopy(sz)
    sz["id"] = new_id(form, sz.get("id") or sz.get("label"))
    lst = data(form, create=True)["sizes"]
    lst.insert(len(lst) if index is None else index, sz)
    return sz


def remove_size(form, vid) -> None:
    d = data(form)
    if not d:
        return
    d["sizes"] = [s for s in d.get("sizes") or [] if s.get("id") != vid]
    (d.get("form") or {}).pop(vid, None)
    for c in form.controls:
        if vid in (c.variants or {}):
            c.variants.pop(vid, None)
    _clean(form)


def rename_size(form, old, new) -> None:
    """Changes a size's id everywhere (its overrides follow)."""
    if old == new:
        return
    s = size(form, old)
    if s is None:
        return
    s["id"] = new
    fo = data(form).get("form") or {}
    if old in fo:
        fo[new] = fo.pop(old)
    for c in form.controls:
        if old in (c.variants or {}):
            c.variants[new] = c.variants.pop(old)


def _clean(form) -> None:
    d = form.extra.get("variants")
    if not isinstance(d, dict):
        return
    fo = d.get("form")
    if isinstance(fo, dict):
        for k in [k for k, v in fo.items() if not v]:
            fo.pop(k)
        if not fo:
            d.pop("form", None)
    if not d.get("sizes") and not d.get("form"):
        form.extra.pop("variants", None)


# ---------------------------------------------------------------------------------------------- overrides
def coerce(prop: str, value):
    if prop in _INT:
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return 0
    if prop in _BOOL:
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    return value


def overrides(form, ctrl, vid) -> dict:
    """{prop: value} a size overrides for *ctrl* (None = the form itself)."""
    if ctrl is None:
        return dict((data(form).get("form") or {}).get(vid) or {})
    return dict((getattr(ctrl, "variants", None) or {}).get(vid) or {})


def set_override(form, ctrl, vid, prop, value) -> None:
    value = coerce(prop, value)
    if ctrl is None:
        data(form, create=True).setdefault("form", {}).setdefault(vid, {})[prop] = value
    else:
        ctrl.variants.setdefault(vid, {})[prop] = value


def remove_override(form, ctrl, vid, prop=None) -> None:
    """Removes one override (prop None = every override of *ctrl* on the size)."""
    if ctrl is None:
        fo = data(form).get("form") or {}
        if prop is None:
            fo.pop(vid, None)
        elif vid in fo:
            fo[vid].pop(prop, None)
        _clean(form)
        return
    ov = ctrl.variants.get(vid)
    if ov is None:
        return
    if prop is None:
        ctrl.variants.pop(vid, None)
    else:
        ov.pop(prop, None)
        if not ov:
            ctrl.variants.pop(vid, None)


def overridden_in(form, ctrl, prop) -> list[str]:
    """Ids of the sizes that override *prop* of *ctrl* (None = the form), in list order."""
    out = []
    for s in sizes(form):
        if prop in overrides(form, ctrl, s["id"]):
            out.append(s["id"])
    return out


def has_overrides(form, vid=None) -> bool:
    for c in form.controls:
        for v, ov in (getattr(c, "variants", None) or {}).items():
            if ov and (vid is None or v == vid):
                return True
    fo = data(form).get("form") or {}
    return any(ov for v, ov in fo.items() if vid is None or v == vid)


def overridden_controls(form, vid) -> list:
    return [c for c in form.controls if (getattr(c, "variants", None) or {}).get(vid)]


def rename_references(form, old: str, new: str) -> None:
    """Nothing to do: overrides live on the Control objects themselves (kept for symmetry)."""
    return None


# ---------------------------------------------------------------------------------------------- context
def is_mobile(form) -> bool:
    return "Device" in form.props


def matching(sz_list, w, h, orientation=None, posture=None, span=None, fold=None) -> list[str]:
    """Ids of the sizes of *sz_list* whose ``when`` holds (list order)."""
    return [s["id"] for s in sz_list if s.get("id") and _vmatch(s.get("when"), w, h, orientation, posture, span,
                                                               fold)]


def context(form, sz) -> dict:
    """Where a size is previewed: {"width", "height", "orientation", "posture", "span", "fold", "device"}.

    The form-level Width / Height override of the size wins; then an explicit preview size; a preview
    device (or a phone form's own Device) gives its safe-area size for the orientation / posture; else
    the base size, clamped into the size's width / height range."""
    from .. import devices
    if isinstance(sz, str):
        sz = size(form, sz) or {"id": sz, "when": {}}
    when = sz.get("when") or {}
    pv = sz.get("preview") or {}
    fp = form.props
    base_w, base_h = int(fp.get("Width", 300) or 300), int(fp.get("Height", 300) or 300)
    w_orient = str(when.get("orientation") or "").lower()
    posture_k = normalize_posture(pv.get("posture") or when.get("posture") or "")
    dev = pv.get("device") or (fp.get("Device") if is_mobile(form) else None)
    out = {"device": None, "orientation": None, "posture": posture_k or None, "span": when.get("span") or None,
           "fold": when.get("fold") or None}
    if dev and dev in devices.DEVICES:
        orient = pv.get("orientation") or ("Landscape" if w_orient.startswith("land") else
                                           "Portrait" if w_orient.startswith("port") else
                                           fp.get("Orientation", "Portrait"))
        orient = "Landscape" if devices.landscape(orient) else "Portrait"
        pname = devices.posture_name(pv.get("posture") or when.get("posture") or fp.get("Posture") or "Flat")
        pname = devices.effective_posture(dev, pname)
        w, h = devices.safe_area_size(dev, orient, pname)
        out.update(device=dev, orientation=orient.lower(), posture=devices.posture_key(pname)
                   if devices.is_foldable(dev) else (posture_k or None),
                   span=devices.span(dev, orient, pname), fold=devices.fold_axis(dev, orient, pname) or None)
    else:
        w = int(pv.get("width") or base_w)
        h = int(pv.get("height") or base_h)
        for key, val in (("minWidth", "w"), ("maxWidth", "w"), ("minHeight", "h"), ("maxHeight", "h")):
            if when.get(key) in (None, ""):
                continue
            lim = int(float(when[key]))
            cur = w if val == "w" else h
            if (key.startswith("min") and cur < lim) or (key.startswith("max") and cur > lim):
                if val == "w":
                    w = lim
                else:
                    h = lim
        if w_orient.startswith("land") and w <= h:
            w, h = (h, w) if w < h else (w + 1, h)
        elif w_orient.startswith("port") and w > h:
            w, h = min(w, h), max(w, h)
    fo = overrides(form, None, sz.get("id"))
    if "Width" in fo:
        w = int(fo["Width"])
    if "Height" in fo:
        h = int(fo["Height"])
    out["width"], out["height"] = max(40, int(w)), max(40, int(h))
    if not out["orientation"]:
        out["orientation"] = "landscape" if out["width"] > out["height"] else "portrait"
    return out


def describe(form, sz) -> str:
    """'Tablet 800 x 1000' (label + preview size)."""
    if isinstance(sz, str):
        sz = size(form, sz) or {"id": sz}
    ctx = context(form, sz)
    return f"{label(sz)} {ctx['width']} x {ctx['height']}"


def when_text(when: dict) -> str:
    """Human description of a size's conditions ('width 600-1023', 'landscape', 'half-opened')."""
    when = when or {}
    parts = []
    lo, hi = when.get("minWidth"), when.get("maxWidth")
    if lo not in (None, "") or hi not in (None, ""):
        parts.append(f"width {lo if lo not in (None, '') else 0}-{hi if hi not in (None, '') else '...'}")
    lo, hi = when.get("minHeight"), when.get("maxHeight")
    if lo not in (None, "") or hi not in (None, ""):
        parts.append(f"height {lo if lo not in (None, '') else 0}-{hi if hi not in (None, '') else '...'}")
    for k in ("orientation", "posture", "span", "fold"):
        if when.get(k):
            parts.append(f"{k} {when[k]}" if k in ("span", "fold") else str(when[k]))
    return ", ".join(parts) or "always"


def cascade(form, vid, ctx=None) -> list[str]:
    """Sizes the designer applies when it previews *vid*: the earlier sizes that also match its preview,
    then *vid* itself last (so what is edited on the size is always what is shown)."""
    sz_list = sizes(form)
    if ctx is None:
        ctx = context(form, vid)
    ids = matching(sz_list, ctx["width"], ctx["height"], ctx["orientation"], ctx["posture"], ctx["span"],
                   ctx["fold"])
    order = [s["id"] for s in sz_list]
    if vid not in order:
        return [i for i in ids]
    pos = order.index(vid)
    return [i for i in ids if order.index(i) < pos] + [vid]


# ---------------------------------------------------------------------------------------------- effective
def effective_form(form, sz=None, active=None):
    """A deep copy of *form* as it looks on size *sz* (an id or a size dict; None = the base design):
    the form gets the size's client area, anchored / docked controls follow it (layout.resize_children
    + relayout), then the overrides of the *active* sizes (default: cascade()) are applied in order."""
    f = copy.deepcopy(form)
    if sz is None:
        return f
    if isinstance(sz, str):
        sz = size(form, sz) or {"id": sz, "when": {}}
    ctx = context(form, sz)
    if active is None:
        active = cascade(form, sz["id"], ctx)
    old = client_size(f, None)
    if is_mobile(f) and ctx.get("device"):
        from .. import devices
        f.props["Device"] = ctx["device"]
        f.props["Orientation"] = "Landscape" if ctx["orientation"] == "landscape" else "Portrait"
        if devices.is_foldable(ctx["device"]):
            f.props["Posture"] = devices.posture_name(ctx.get("posture") or "Flat")
    f.props["Width"], f.props["Height"] = ctx["width"], ctx["height"]
    resize_children(f, None, old, (ctx["width"], ctx["height"]))
    for vid in active:
        for k, v in overrides(form, None, vid).items():
            if k not in ("Width", "Height"):
                f.props[k] = coerce(k, v)
    for c in f.ordered():
        merged: dict = {}
        for vid in active:
            merged.update((c.variants or {}).get(vid) or {})
        if not merged:
            continue
        before = client_size(f, c) if c.ctype.container else None
        for k, v in merged.items():
            c.props[k] = coerce(k, v)
        if before is not None and client_size(f, c) != before:
            resize_children(f, c, before, client_size(f, c))
    try:
        relayout(f)
    except Exception:  # noqa: BLE001 - a broken mobile layout container must not break the preview
        pass
    return f


def effective_props(form, sz=None, active=None) -> tuple[dict, dict]:
    """({control name: props}, form props) of effective_form()."""
    f = effective_form(form, sz, active)
    return {c.name: c.props for c in f.controls}, f.props


# ---------------------------------------------------------------------------------------------- codegen plan
def _spec(p) -> tuple:
    def num(v):
        v = float(v)
        return int(v) if v.is_integer() else round(v, 3)
    return tuple(num(v) for v in (p.x, p.y, p.w, p.h, p.rx, p.ry, p.rw, p.rh))


def _same_place(a, b) -> bool:
    if a is None or b is None:
        return a is b
    return all(abs(x - y) < 1.01 for x, y in zip(_spec(a), _spec(b)))


def plan(form) -> dict | None:
    """What a generated program needs (None when the form has no sizes)::

        {"sizes": [{"id", "when"}], "design": (w, h),
         "form": {vid: {prop: v}},                                  # Text / BackColor of the window
         "controls": {vid: {name: {"props": {...non-geometry...}, "place": spec | None}}},
         "base": {name: spec}}                                       # designed place of every managed control
    spec = (x, y, w, h, rx, ry, rw, rh) like layout.Place: x = spec[0] + spec[4] * container width ..."""
    sz_list = sizes(form)
    if not sz_list:
        return None
    base_specs = place_specs(form)
    out = {"sizes": [{"id": s["id"], "when": dict(s.get("when") or {})} for s in sz_list],
           "design": (int(form.props.get("Width", 300)), int(form.props.get("Height", 300))),
           "form": {}, "controls": {}, "base": {}}
    visual = [c for c in form.visual()]
    for s in sz_list:
        vid = s["id"]
        fo = {k: coerce(k, v) for k, v in overrides(form, None, vid).items() if k in FORM_RUNTIME_PROPS}
        if fo:
            out["form"][vid] = fo
        if not has_overrides(form, vid):
            out["controls"][vid] = {}
            continue
        specs = place_specs(effective_form(form, s, [vid]))
        ctl = {}
        for c in visual:
            ov = (c.variants or {}).get(vid) or {}
            geo = any(k in ov for k in GEOMETRY)
            bp, vp = base_specs.get(c.name), specs.get(c.name)
            place = None
            if vp is not None and (geo or not _same_place(bp, vp)):
                place = _spec(vp)
            props = {k: coerce(k, v) for k, v in ov.items() if k in RUNTIME_PROPS}
            if place is not None or props:
                ctl[c.name] = {"props": props, "place": place}
                if place is not None and bp is not None:
                    out["base"][c.name] = _spec(bp)
        out["controls"][vid] = ctl
    return out


__all__ = ["VARIANT_PROPS", "FORM_VARIANT_PROPS", "GEOMETRY", "RUNTIME_PROPS", "MATCH_RT", "PRESETS", "PRESET_SETS",
           "PRESET_GROUPS", "preset", "data", "sizes", "size", "label", "new_id", "add_size", "remove_size",
           "rename_size", "overrides", "set_override", "remove_override", "overridden_in", "has_overrides",
           "overridden_controls", "matching", "context", "describe", "when_text", "cascade", "effective_form",
           "effective_props", "plan", "coerce", "normalize_posture", "is_mobile"]
