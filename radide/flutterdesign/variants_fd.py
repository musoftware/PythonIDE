"""Flutter designer layout variants: change a screen on one size (phone / tablet / landscape / foldable posture)
without touching the others (plan MOTION_VARIANTS_FOLDABLES.md, slice F). Plain Python (no Qt).

Schema (additive)::

    screen "variants": [{"id": "medium", "label": "Tablet", "when": {"minWidth": 600},
                         "preview": {"width": 800, "height": 1280}},
                        {"id": "tabletop", "label": "Half-open", "when": {"posture": "half-opened"},
                         "preview": {"device": "galaxy_z_fold6", "orientation": "Portrait",
                                     "posture": "HalfOpened"}}]
    node   "vprops": {"medium": {"padding": {"all": 32}, "$hidden": true}}

``when`` keys: minWidth, maxWidth, minHeight, maxHeight, orientation (portrait | landscape), posture (flat |
half-opened | folded), span (single | dual), fold (vertical | horizontal). Every matching size applies in list
order and the later one wins (like CSS). Generated code (lib/radlayout.dart)::

    static const _radSizes = [RadSize('medium', minWidth: 600), ...];
    final rv = RadVariant.of(context, _radSizes);
    padding: rv.pick(const EdgeInsets.all(16), const [RadV('medium', EdgeInsets.all(32))]),
    RadShow(hidden: rv.pick(false, const [RadV('compact', true), RadV('tabletop', false)]), child: ...)
"""
from __future__ import annotations

import copy
import re

from . import model as M

HIDDEN = "$hidden"
WHEN_KEYS = ("minWidth", "maxWidth", "minHeight", "maxHeight", "orientation", "posture", "span", "fold")
POSTURE_KEYS = ("flat", "half-opened", "folded")
_IDENT = re.compile(r"^[A-Za-z_]\w*$")
MARK_HERE, MARK_ELSEWHERE = "◆", "◇"       # ◆ overridden on this size, ◇ on another size

# ready-made size sets (Screen > Sizes > Add)
SIZE_PRESETS: dict[str, list[dict]] = {
    "Phone / Tablet / Desktop": [
        {"id": "compact", "label": "Phone", "when": {"maxWidth": 599}, "preview": {"width": 412, "height": 915}},
        {"id": "medium", "label": "Tablet", "when": {"minWidth": 600, "maxWidth": 1023},
         "preview": {"width": 800, "height": 1280}},
        {"id": "expanded", "label": "Desktop", "when": {"minWidth": 1024},
         "preview": {"width": 1280, "height": 800}}],
    "Portrait / Landscape": [
        {"id": "portrait", "label": "Portrait", "when": {"orientation": "portrait"}},
        {"id": "land", "label": "Landscape", "when": {"orientation": "landscape"}}],
    "Foldable": [
        {"id": "folded", "label": "Folded", "when": {"posture": "folded"},
         "preview": {"device": "galaxy_z_fold6", "orientation": "Portrait", "posture": "Folded"}},
        {"id": "tabletop", "label": "Half-open", "when": {"posture": "half-opened"},
         "preview": {"device": "galaxy_z_fold6", "orientation": "Portrait", "posture": "HalfOpened"}},
        {"id": "dual", "label": "Two screens", "when": {"span": "dual"},
         "preview": {"device": "surface_duo2", "orientation": "Landscape", "posture": "Flat"}}],
}


# ============================================================================================ sizes
def sizes(screen) -> list[dict]:
    data = screen.data if isinstance(screen, M.Screen) else screen
    return [s for s in (data.get("variants") or []) if isinstance(s, dict) and s.get("id")]


def size(screen, vid: str) -> dict | None:
    return next((s for s in sizes(screen) if s["id"] == vid), None)


def label(s: dict) -> str:
    return str(s.get("label") or s.get("id"))


def describe_when(when: dict | None) -> str:
    w = when or {}
    parts = []
    if "minWidth" in w and "maxWidth" in w:
        parts.append(f"{w['minWidth']:g}-{w['maxWidth']:g} wide")
    elif "minWidth" in w:
        parts.append(f">= {w['minWidth']:g} wide")
    elif "maxWidth" in w:
        parts.append(f"<= {w['maxWidth']:g} wide")
    if "minHeight" in w:
        parts.append(f">= {w['minHeight']:g} high")
    if "maxHeight" in w:
        parts.append(f"<= {w['maxHeight']:g} high")
    for k in ("orientation", "posture", "span", "fold"):
        if k in w:
            parts.append(str(w[k]))
    return ", ".join(parts) or "always"


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def matches(when: dict | None, w: float, h: float, orientation: str | None = None, posture: str = "flat",
            span: str = "single", fold: str | None = None) -> bool:
    c = when or {}
    o = orientation or ("landscape" if w > h else "portrait")
    for k, ok in (("minWidth", lambda x: w >= x), ("maxWidth", lambda x: w <= x),
                  ("minHeight", lambda x: h >= x), ("maxHeight", lambda x: h <= x)):
        x = _num(c.get(k))
        if x is not None and not ok(x):
            return False
    if c.get("orientation") and str(c["orientation"]).lower() != o.lower():
        return False
    if c.get("posture") and _posture_key(c["posture"]) != _posture_key(posture):
        return False
    if c.get("span") and str(c["span"]).lower() != str(span).lower():
        return False
    if c.get("fold") and str(c["fold"]).lower() != str(fold or "").lower():
        return False
    return True


def _posture_key(p) -> str:
    try:
        from .. import devices as D
        return D.posture_key(p)
    except Exception:  # noqa: BLE001
        s = str(p or "").lower().replace("_", "-")
        return "half-opened" if "half" in s else "folded" if "fold" in s else "flat"


def matching(size_list: list[dict], w: float, h: float, orientation: str | None = None, posture: str = "flat",
             span: str = "single", fold: str | None = None) -> list[str]:
    """Ids of the sizes that apply, in list order (later ones win)."""
    return [s["id"] for s in size_list if matches(s.get("when"), w, h, orientation, posture, span, fold)]


def device_facts(device_id: str, orientation: str = "Portrait", posture: str = "Flat",
                 width: float | None = None, height: float | None = None) -> dict:
    """{"width", "height", "orientation", "posture", "span", "fold", "features"} of a radide.devices preset
    (the screen size the Flutter app sees: MediaQuery.size, display features)."""
    from .. import devices as D
    if width is None or height is None:
        width, height = D.screen_size(device_id, orientation, posture)
    p = D.effective_posture(device_id, posture)
    return {"width": width, "height": height,
            "orientation": "landscape" if width > height else "portrait",
            "posture": D.posture_key(p), "span": D.span(device_id, orientation, p),
            "fold": D.fold_axis(device_id, orientation, p) or None,
            "features": D.display_features(device_id, orientation, p)}


def active_for(screen, facts: dict) -> list[str]:
    return matching(sizes(screen), facts["width"], facts["height"], facts.get("orientation"),
                    facts.get("posture", "flat"), facts.get("span", "single"), facts.get("fold"))


def preview_facts(s: dict) -> dict | None:
    """Device facts of a size's ``preview`` (None when it has none)."""
    pv = s.get("preview") or {}
    if pv.get("device"):
        return device_facts(pv["device"], pv.get("orientation", "Portrait"), pv.get("posture", "Flat"))
    if _num(pv.get("width")) and _num(pv.get("height")):
        w, h = float(pv["width"]), float(pv["height"])
        return {"width": w, "height": h, "orientation": "landscape" if w > h else "portrait", "posture": "flat",
                "span": "single", "fold": None, "features": []}
    return None


# ========================================================================================== overrides
def overrides(node: dict, vid: str) -> dict:
    return dict((node.get("vprops") or {}).get(vid) or {})


def is_hidden(node: dict, vid: str) -> bool:
    return bool(overrides(node, vid).get(HIDDEN))


def marker(node: dict | None, key: str, vid: str | None) -> str:
    """◆ overridden on *vid*, ◇ overridden on another size, '' = base everywhere."""
    if not node:
        return ""
    vp = node.get("vprops") or {}
    if vid and key in (vp.get(vid) or {}):
        return MARK_HERE
    if any(key in (o or {}) for k, o in vp.items() if k != vid):
        return MARK_ELSEWHERE
    return ""


def overridden_ids(screen: M.Screen, vid: str) -> set[str]:
    return {n["id"] for n, *_ in screen.walk() if (n.get("vprops") or {}).get(vid)}


def _set_vprops(screen: M.Screen, node_id: str, vp: dict) -> M.Patch:
    vp = {k: v for k, v in vp.items() if v}
    return M._set_field(screen, node_id, "vprops", vp or None)


def set_override(screen: M.Screen, node_id: str, vid: str, key: str, value) -> M.Patch:
    """Set *key* of a node on size *vid* only (value None removes the override). When the base has no value
    the catalog default is written to the base too, so the generated rv.pick() has a real base value."""
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    if size(screen, vid) is None:
        raise ValueError(f"unknown size {vid!r}")
    spec = M.widget_spec(node.get("type", ""), node.get("ctor"))
    if spec and key in spec.props and value is not None and key != HIDDEN:
        value = M.normalize_value(spec.props[key].kind, value)
    vp = copy.deepcopy(node.get("vprops") or {})
    o = dict(vp.get(vid) or {})
    if value is None:
        o.pop(key, None)
    else:
        o[key] = value
    vp[vid] = o
    patch: M.Patch = []
    base = (node.get("props") or {}).get(key)
    if value is not None and key != HIDDEN and base is None and spec and key in spec.props \
            and spec.props[key].default is not None:
        patch += M.set_prop(screen, node_id, key, spec.props[key].default)
    if key != HIDDEN and (node.get("props") or {}).get(key) == value:
        o.pop(key, None)                    # same as the base: no override needed
        vp[vid] = o
    return patch + _set_vprops(screen, node_id, vp)


def remove_override(screen: M.Screen, node_id: str, vid: str, key: str) -> M.Patch:
    return set_override(screen, node_id, vid, key, None)


def set_hidden(screen: M.Screen, node_id: str, vid: str, hidden: bool | None) -> M.Patch:
    """Hide (True) / show again (False: undoes the hiding of an earlier matching size) / follow the other
    sizes (None) on *vid*."""
    return set_override(screen, node_id, vid, HIDDEN, None if hidden is None else bool(hidden))


def apply_to_all(screen: M.Screen, node_id: str, vid: str, key: str) -> M.Patch:
    """The value of *key* on *vid* becomes the base value; the overrides of every size are removed."""
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    o = overrides(node, vid)
    if key not in o:
        return []
    patch = M.set_prop(screen, node_id, key, o[key])
    vp = copy.deepcopy(node.get("vprops") or {})
    for k in vp:
        (vp[k] or {}).pop(key, None)
    return patch + _set_vprops(screen, node_id, vp)


def copy_to(screen: M.Screen, node_id: str, vid: str, key: str, to_vid: str) -> M.Patch:
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    o = overrides(node, vid)
    val = o[key] if key in o else (node.get("props") or {}).get(key)
    return set_override(screen, node_id, to_vid, key, copy.deepcopy(val))


def add_size(screen: M.Screen, s: dict) -> M.Patch:
    lst = copy.deepcopy(sizes(screen))
    if not _IDENT.match(str(s.get("id", ""))):
        raise ValueError(f"size id {s.get('id')!r} must be an identifier")
    if any(x["id"] == s["id"] for x in lst):
        raise ValueError(f"the size {s['id']!r} already exists")
    lst.append(copy.deepcopy(s))
    return M.set_screen(screen, "variants", lst)


def add_preset(screen: M.Screen, preset: str) -> M.Patch:
    have = {s["id"] for s in sizes(screen)}
    lst = copy.deepcopy(sizes(screen)) + [copy.deepcopy(s) for s in SIZE_PRESETS[preset] if s["id"] not in have]
    return M.set_screen(screen, "variants", lst)


def update_size(screen: M.Screen, vid: str, new: dict) -> M.Patch:
    lst = copy.deepcopy(sizes(screen))
    for i, s in enumerate(lst):
        if s["id"] == vid:
            lst[i] = copy.deepcopy(new)
    if new.get("id") != vid:       # renamed: move the node overrides
        patch = M.set_screen(screen, "variants", lst)
        for n, *_ in screen.walk():
            vp = n.get("vprops") or {}
            if vid in vp:
                vp2 = copy.deepcopy(vp)
                vp2[new["id"]] = vp2.pop(vid)
                patch += _set_vprops(screen, n["id"], vp2)
        return patch
    return M.set_screen(screen, "variants", lst)


def remove_size(screen: M.Screen, vid: str) -> M.Patch:
    """Remove a size and every override made for it (one undo step)."""
    patch: M.Patch = []
    for n, *_ in screen.walk():
        vp = n.get("vprops") or {}
        if vid in vp:
            vp2 = copy.deepcopy(vp)
            vp2.pop(vid)
            patch += _set_vprops(screen, n["id"], vp2)
    lst = [s for s in copy.deepcopy(sizes(screen)) if s["id"] != vid]
    return patch + M.set_screen(screen, "variants", lst or None)


# ========================================================================================== preview
def effective(screen, active: list[str]) -> dict:
    """A deep copy of the screen dict with the overrides of the *active* sizes applied (in the order of the
    size list) and widgets hidden there replaced by an empty SizedBox (same id, so selection still works)."""
    data = copy.deepcopy(screen.data if isinstance(screen, M.Screen) else screen)
    order = [s["id"] for s in sizes(data)]
    act = [v for v in order if v in set(active or [])]

    def fix(node: dict) -> dict:
        vp = node.get("vprops") or {}
        hidden = False
        for vid in act:
            o = vp.get(vid) or {}
            for k, v in o.items():
                if k == HIDDEN:
                    hidden = bool(v)
                else:
                    node.setdefault("props", {})[k] = copy.deepcopy(v)
        for k, v in list((node.get("slots") or {}).items()):
            if isinstance(v, list):
                node["slots"][k] = [fix(c) for c in v if isinstance(c, dict)]
            elif isinstance(v, dict):
                node["slots"][k] = fix(v)
        if node.get("children"):
            node["children"] = [fix(c) for c in node["children"] if isinstance(c, dict)]
        if hidden:
            return {"id": node.get("id"), "type": "SizedBox", "props": {"width": 0, "height": 0}, "$hidden": True}
        return node
    data["tree"] = fix(data["tree"])
    return data


def needs_resolve(screen) -> bool:
    """Does the screen use anything the previews cannot show as stored ($when / $timeline / vprops)?"""
    from . import motion as MO
    data = screen.data if isinstance(screen, M.Screen) else screen
    for n, *_ in M.walk_node(data.get("tree") or {}):
        if n.get("vprops"):
            return True
        for v in (n.get("props") or {}).values():
            if MO.is_when(v) or MO.is_timeline(v):
                return True
    return False


def preview_data(screen, active: list[str] | None = None, state: dict | None = None,
                 t_ms: dict | None = None) -> dict:
    """What the previews render: the active sizes applied, $when / $timeline resolved, vprops removed."""
    from . import motion as MO
    scr = screen if isinstance(screen, M.Screen) else M.Screen(copy.deepcopy(screen))
    data = effective(scr, active or [])
    st = MO.state_values(scr)
    st.update(state or {})
    for n, *_ in M.walk_node(data["tree"]):
        n.pop("vprops", None)
        spec = M.widget_spec(n.get("type", ""), n.get("ctor"))
        pr = n.get("props") or {}
        for k, v in list(pr.items()):
            if MO.is_when(v) or MO.is_timeline(v):
                kind = spec.props[k].kind if spec and k in spec.props else ""
                pr[k] = MO.resolve_value(v, kind, st, t_ms)
    return data


# ============================================================================================ codegen
def _when_args(when: dict) -> list[str]:
    from . import codegen as CG
    out = []
    for k in ("minWidth", "maxWidth", "minHeight", "maxHeight"):
        x = _num(when.get(k))
        if x is not None:
            out.append(f"{k}: {CG.dart_num(when[k])}")
    if when.get("orientation"):
        out.append(f"orientation: Orientation.{str(when['orientation']).lower()}")
    if when.get("posture"):
        p = {"flat": "flat", "half-opened": "halfOpened", "folded": "folded"}[_posture_key(when["posture"])]
        out.append(f"posture: RadPosture.{p}")
    if when.get("span"):
        out.append(f"span: RadSpan.{'dual' if str(when['span']).lower() == 'dual' else 'single'}")
    if when.get("fold"):
        out.append(f"fold: Axis.{'horizontal' if str(when['fold']).lower() == 'horizontal' else 'vertical'}")
    return out


def sizes_member(screen: M.Screen) -> list[str]:
    """``static const _radSizes = [...]`` lines of the designer State."""
    from . import codegen as CG
    items = []
    for s in sizes(screen):
        args = [CG.dart_string(s["id"])] + _when_args(s.get("when") or {})
        items.append(f"    RadSize({', '.join(args)}),")
    if not items:
        return []
    return ["  static const _radSizes = ["] + items + ["  ];", ""]


def size_ids_in_order(screen: M.Screen, node: dict) -> list[str]:
    order = [s["id"] for s in sizes(screen)]
    vp = node.get("vprops") or {}
    return [v for v in order if v in vp] + [v for v in vp if v not in order]


def pick_x(base, values: list[tuple]):
    """rv.pick(base, [RadV('id', value), ...]) (*values* = [(id, X)])."""
    from . import codegen as CG
    items = [CG.Call("RadV", [CG.Lit(CG.dart_string(vid)), x]) for vid, x in values]
    return CG.Call("rv.pick", [base, CG.Lst(items)], const_ctor=False)


def hidden_entries(screen, node: dict) -> list[tuple[str, bool]]:
    """[(size id, hidden)] of a node, in size-list order."""
    return [(v, bool(overrides(node, v)[HIDDEN])) for v in size_ids_in_order(screen, node)
            if HIDDEN in overrides(node, v)]


def show_x(x, entries: list[tuple[str, bool]]):
    """RadShow(hidden: rv.pick(false, [RadV('compact', true), ...]), child: x)."""
    from . import codegen as CG
    vals = [(vid, CG.Lit("true" if h else "false")) for vid, h in entries]
    return CG.Call("RadShow", named=[("hidden", pick_x(CG.Lit("false"), vals)), ("child", x)])


# ========================================================================================= validation
def validate(screen: M.Screen) -> list[M.Issue]:
    issues: list[M.Issue] = []
    seen = set()
    for s in screen.data.get("variants") or []:
        vid = s.get("id") if isinstance(s, dict) else None
        if not vid or not _IDENT.match(str(vid)):
            issues.append(M.Issue("error", None, f"size id {vid!r} must be an identifier"))
            continue
        if vid in seen:
            issues.append(M.Issue("error", None, f"duplicate size id {vid!r}"))
        seen.add(vid)
        for k in (s.get("when") or {}):
            if k not in WHEN_KEYS:
                issues.append(M.Issue("error", None, f"size {vid}: unknown condition {k!r}"))
    for n, *_ in screen.walk():
        spec = M.widget_spec(n.get("type", ""), n.get("ctor"))
        for vid, o in (n.get("vprops") or {}).items():
            if vid not in seen:
                issues.append(M.Issue("warning", n.get("id"), f"overrides for an unknown size {vid!r}"))
            for k in (o or {}):
                if k == HIDDEN:
                    if n.get("type") in ("Positioned", "Expanded", "Flexible", "AnimatedPositioned") or \
                            n is screen.tree:
                        issues.append(M.Issue("warning", n.get("id"), f"a {n.get('type')} cannot be hidden per "
                                                                      "size (hide its child)"))
                elif spec is not None and k not in spec.props and not M.is_code((o or {}).get(k)):
                    issues.append(M.Issue("warning", n.get("id"), f"{n.get('type')} has no property {k!r}"))
    return issues
