"""Anchor / Dock geometry shared by the designer and the code generators.

Every visual control gets a *Place*: its geometry as a linear function of
the size of its container's client area (CW, CH):

    x = place.x + place.rx * CW        width  = place.w + place.rw * CW
    y = place.y + place.ry * CH        height = place.h + place.rh * CH

That is exactly what Tk's place(x=, relx=, width=, relwidth=, ...) does, and
other toolkits can evaluate it in a resize handler (Place.rect(cw, ch)).

Docking (WinForms rules): the children of a container are docked in z-order
(the back-most control first); each docked control takes a strip from the
remaining area; Fill controls take what is left. Anchors keep the distance to
the anchored edges: Left+Right stretches, Right only moves, no horizontal
anchor keeps the control centred proportionally.
"""
from __future__ import annotations

from dataclasses import dataclass

from .controls import TAB_PAGE_X, TAB_PAGE_Y, parse_anchor


@dataclass(frozen=True)
class Place:
    x: float
    y: float
    w: float
    h: float
    rx: float = 0.0
    ry: float = 0.0
    rw: float = 0.0
    rh: float = 0.0

    def rect(self, cw: float, ch: float) -> tuple[int, int, int, int]:
        return (int(round(self.x + self.rx * cw)), int(round(self.y + self.ry * ch)),
                max(0, int(round(self.w + self.rw * cw))), max(0, int(round(self.h + self.rh * ch))))

    def is_static(self) -> bool:
        return not (self.rx or self.ry or self.rw or self.rh)

    def tk_options(self) -> dict:
        """Keyword arguments for Tk's place()."""
        out = {"x": _num(self.x), "y": _num(self.y), "width": _num(self.w), "height": _num(self.h)}
        for k, v in (("relx", self.rx), ("rely", self.ry), ("relwidth", self.rw), ("relheight", self.rh)):
            if v:
                out[k] = _num(v)
        return out


def _num(v: float):
    return int(v) if float(v).is_integer() else round(float(v), 3)


def client_size(form, ctrl=None) -> tuple[int, int]:
    """Design-time size of the client area of the form (ctrl None) or a container."""
    if ctrl is None:
        return int(form.props["Width"]), int(form.props["Height"])
    w, h = int(ctrl.props["Width"]), int(ctrl.props["Height"])
    if ctrl.type == "TabControl":
        return max(0, w - 2 * TAB_PAGE_X), max(0, h - TAB_PAGE_Y - TAB_PAGE_X)
    return w, h


def client_offset(ctrl) -> tuple[int, int]:
    """Where the client area of a container starts, inside the container."""
    if ctrl is not None and ctrl.type == "TabControl":
        return TAB_PAGE_X, TAB_PAGE_Y
    return 0, 0


def dock_of(ctrl) -> str:
    d = str(ctrl.props.get("Dock", "None") or "None")
    return d if d in ("Top", "Bottom", "Left", "Right", "Fill") else "None"


def _groups(form, parent: str) -> list[list]:
    """Children of *parent* grouped by layout area (TabControl: one group per page)."""
    kids = form.children(parent)
    pc = form.find(parent) if parent else None
    if pc is None or pc.type != "TabControl":
        return [kids] if kids else []
    pages: dict[int, list] = {}
    for c in kids:
        pages.setdefault(tab_page(c), []).append(c)
    return [pages[k] for k in sorted(pages)]


def tab_page(ctrl) -> int:
    try:
        return int(ctrl.props.get("TabPage", 0) or 0)
    except (TypeError, ValueError):
        return 0


def group_places(kids: list, cw: int, ch: int) -> dict[int, Place]:
    """Place of each control of one layout area whose design client size is (cw, ch)."""
    out: dict[int, Place] = {}
    left = top = right = bottom = 0
    fills = []
    for c in kids:
        d = dock_of(c)
        w, h = int(c.props["Width"]), int(c.props["Height"])
        if d == "None":
            out[id(c)] = anchored_place(c, cw, ch)
        elif d == "Fill":
            fills.append(c)
        elif d == "Top":
            out[id(c)] = Place(left, top, -left - right, h, rw=1)
            top += h
        elif d == "Bottom":
            out[id(c)] = Place(left, -bottom - h, -left - right, h, ry=1, rw=1)
            bottom += h
        elif d == "Left":
            out[id(c)] = Place(left, top, w, -top - bottom, rh=1)
            left += w
        elif d == "Right":
            out[id(c)] = Place(-right - w, top, w, -top - bottom, rx=1, rh=1)
            right += w
    for c in fills:
        out[id(c)] = Place(left, top, -left - right, -top - bottom, rw=1, rh=1)
    return out


def anchored_place(c, cw: int, ch: int) -> Place:
    x, y = int(c.props["Left"]), int(c.props["Top"])
    w, h = int(c.props["Width"]), int(c.props["Height"])
    a = parse_anchor(c.props.get("Anchor", "Top, Left"))
    px, prx, pw, prw = _axis(x, w, cw, "Left" in a, "Right" in a)
    py, pry, ph, prh = _axis(y, h, ch, "Top" in a, "Bottom" in a)
    return Place(px, py, pw, ph, prx, pry, prw, prh)


def _axis(pos, size, total, near, far):
    if near and far:
        return pos, 0.0, size - total, 1.0
    if far:
        return pos - total, 1.0, size, 0.0
    if near:
        return pos, 0.0, size, 0.0
    return pos - total / 2, 0.5, size, 0.0     # keeps its place relative to the centre


def place_specs(form) -> dict[str, Place]:
    """Place of every visual control (by name), computed from the design geometry."""
    out: dict[str, Place] = {}
    for parent in [None, *[c for c in form.ordered() if c.ctype.container]]:
        cw, ch = client_size(form, parent)
        for group in _groups(form, parent.name if parent else ""):
            places = group_places(group, cw, ch)
            for c in group:
                out[c.name] = places[id(c)]
    return out


# ------------------------------------------------------------------ designer helpers
def relayout(form) -> list:
    """Snap docked controls to their container edges (updates Left/Top/Width/Height).
    Containers whose size changes pass the change on to their anchored children.
    Returns the controls that changed."""
    changed = []
    for parent in [None, *[c for c in form.ordered() if c.ctype.container]]:
        cw, ch = client_size(form, parent)
        for group in _groups(form, parent.name if parent else ""):
            places = group_places(group, cw, ch)
            for c in group:
                if dock_of(c) == "None":
                    continue
                new = places[id(c)].rect(cw, ch)
                old = tuple(int(c.props[k]) for k in ("Left", "Top", "Width", "Height"))
                if new != old:
                    if c.ctype.container:
                        before = client_size(form, c)
                        _set(c, new)
                        changed += resize_children(form, c, before, client_size(form, c))
                    else:
                        _set(c, new)
                    changed.append(c)
    if any(c.type in ("Column", "Row", "Stack", "TwoPane") for c in form.controls):
        from .mobile.frame import layout_containers      # mobile layout containers (CONTRACTS 10.4 / 10.8)
        changed += layout_containers(form)
    return changed


def resize_children(form, parent, old_size, new_size) -> list:
    """The client area of *parent* (None = form) changed size: move/resize its anchored
    children (recursively). Docked children are fixed later by relayout()."""
    if tuple(old_size) == tuple(new_size):
        return []
    changed = []
    ow, oh = old_size
    nw, nh = new_size
    for c in form.children(parent.name if parent else ""):
        if dock_of(c) != "None":
            continue
        new = anchored_place(c, ow, oh).rect(nw, nh)
        old = tuple(int(c.props[k]) for k in ("Left", "Top", "Width", "Height"))
        if new != old:
            before = client_size(form, c) if c.ctype.container else None
            _set(c, new)
            changed.append(c)
            if before is not None:
                changed += resize_children(form, c, before, client_size(form, c))
    return changed


def _set(c, rect):
    c.props["Left"], c.props["Top"], c.props["Width"], c.props["Height"] = (int(v) for v in rect)
