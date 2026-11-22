"""Layout primitives: BoxConstraints (C), the laid-out Box, inherited Env, the pass context Ctx and the
value parsers (num / edge / radii / align / enum_val / color / props / slot)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from PyQt6.QtGui import QColor, QTransform

from .. import model as M
from .colors import _hex_color, named_color


INF = float("inf")


# ============================================================================ geometry
@dataclass
class C:
    """BoxConstraints."""
    minW: float = 0.0
    maxW: float = INF
    minH: float = 0.0
    maxH: float = INF

    @staticmethod
    def tight(w: float, h: float) -> "C":
        return C(w, w, h, h)

    def loosen(self) -> "C":
        return C(0, self.maxW, 0, self.maxH)

    def constrain(self, w: float, h: float) -> tuple[float, float]:
        return (min(max(w, self.minW), self.maxW), min(max(h, self.minH), self.maxH))

    def deflate(self, l: float, t: float, r: float, b: float) -> "C":
        hz, vt = l + r, t + b
        mnw, mnh = max(0.0, self.minW - hz), max(0.0, self.minH - vt)
        return C(mnw, max(mnw, self.maxW - hz), mnh, max(mnh, self.maxH - vt))

    def enforce(self, outer: "C") -> "C":
        """These (additional) constraints clamped into *outer* (ConstrainedBox)."""
        def cl(v, lo, hi):
            return min(max(v, lo), hi)
        return C(cl(self.minW, outer.minW, outer.maxW), cl(self.maxW, outer.minW, outer.maxW),
                 cl(self.minH, outer.minH, outer.maxH), cl(self.maxH, outer.minH, outer.maxH))

    def tighten(self, w: float | None = None, h: float | None = None) -> "C":
        out = replace(self)
        if w is not None:
            w = min(max(w, self.minW), self.maxW)
            out.minW = out.maxW = w
        if h is not None:
            h = min(max(h, self.minH), self.maxH)
            out.minH = out.maxH = h
        return out

    @property
    def biggest(self) -> tuple[float, float]:
        return (self.maxW if self.maxW < INF else self.minW, self.maxH if self.maxH < INF else self.minH)


class Box:
    """A laid-out box: size, offset in its parent, children, painters."""
    __slots__ = ("w", "h", "x", "y", "kids", "paint", "post", "nid", "clip", "opacity", "xform", "anim",
                 "overflow", "ntype")

    def __init__(self, w=0.0, h=0.0, kids=None, paint=None, post=None):
        self.w, self.h = float(w), float(h)
        self.x = self.y = 0.0
        self.kids: list[Box] = kids or []
        self.paint = paint          # fn(p, Box, ctx) before the children (local coordinates)
        self.post = post            # fn(p, Box, ctx) after the children
        self.nid: str | None = None
        self.ntype = ""
        self.clip = None            # "rect" | QPainterPath (local) | None
        self.opacity = 1.0
        self.xform: QTransform | None = None
        self.anim: dict | None = None
        self.overflow: tuple[str, float] | None = None


def at(box: Box, x: float, y: float) -> Box:
    box.x, box.y = float(x), float(y)
    return box


@dataclass
class Env:
    """Inherited values (Theme / DefaultTextStyle / IconTheme / MediaQuery padding)."""
    style: dict = field(default_factory=dict)
    icon_color: QColor | None = None
    icon_size: float = 24.0
    pad_top: float = 0.0
    pad_bottom: float = 0.0
    in_flex: bool = False
    radio: object = None              # groupValue of the enclosing RadioGroup


class Ctx:
    """Everything a layout pass needs."""

    def __init__(self, scheme: dict, dark: bool = False, text_scale: float = 1.0, folder: Path | None = None,
                 images=None, font_family: str = "", selected: str | None = None, screen=None):
        self.scheme = scheme
        self.dark = dark
        self.text_scale = text_scale
        self.folder = folder
        self.images = images
        from .paint import default_font     # paint imports this module: imported at call time
        self.font_family = font_family or default_font()
        self.selected = selected
        self.screen = screen
        self.anim_t: float | None = None        # ms since "play" (None = final state)
        self.show_drawer: str | None = None     # "drawer" | "endDrawer" when the selection is inside one
        self.hinge: tuple | None = None         # foldable hinge / fold (x, y, w, h) in screen coordinates
        self.screen_size: tuple = (0.0, 0.0)    # device screen (w, h) in dp
        self.app_theme: dict | None = None      # project theme (screen-theme form) when the screen has none


# ============================================================================== values
def num(v, default=None):
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    if v == "infinity":
        return INF
    return default


def edge(v) -> tuple[float, float, float, float]:
    """EdgeInsets JSON -> (l, t, r, b)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (float(v),) * 4
    if not isinstance(v, dict) or M.is_code(v):
        return (0.0, 0.0, 0.0, 0.0)
    if "all" in v:
        a = num(v["all"], 0.0)
        return (a, a, a, a)
    if set(v) <= {"h", "v"}:
        h, vv = num(v.get("h"), 0.0), num(v.get("v"), 0.0)
        return (h, vv, h, vv)
    return (num(v.get("l"), 0.0), num(v.get("t"), 0.0), num(v.get("r"), 0.0), num(v.get("b"), 0.0))


def radii(v) -> tuple[float, float, float, float] | None:
    """border_radius JSON -> (tl, tr, br, bl)."""
    if v is None or M.is_code(v):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (float(v),) * 4
    if isinstance(v, dict):
        return (num(v.get("tl"), 0.0), num(v.get("tr"), 0.0), num(v.get("br"), 0.0), num(v.get("bl"), 0.0))
    return None


_ALIGN = {"topLeft": (-1, -1), "topCenter": (0, -1), "topRight": (1, -1), "centerLeft": (-1, 0),
          "center": (0, 0), "centerRight": (1, 0), "bottomLeft": (-1, 1), "bottomCenter": (0, 1),
          "bottomRight": (1, 1), "topStart": (-1, -1), "topEnd": (1, -1), "centerStart": (-1, 0),
          "centerEnd": (1, 0), "bottomStart": (-1, 1), "bottomEnd": (1, 1)}


def align(v, default=(0.0, 0.0)) -> tuple[float, float]:
    if isinstance(v, dict) and not M.is_code(v):
        return (num(v.get("x"), 0.0), num(v.get("y"), 0.0))
    if isinstance(v, str):
        a = _ALIGN.get(v.rsplit(".", 1)[-1])
        if a:
            return (float(a[0]), float(a[1]))
    return default


def enum_val(v, default: str = "") -> str:
    return v.rsplit(".", 1)[-1] if isinstance(v, str) else default


def color(v, ctx: Ctx, default=None) -> QColor | None:
    if v is None or M.is_code(v):
        return QColor(default) if isinstance(default, QColor) else default
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("#") or s.startswith("0x"):
            nv = M.normalize_color(s)
            if isinstance(nv, str) and re.match(r"^#[0-9A-Fa-f]{8}$", nv):
                return _hex_color(nv)
        if s.startswith("scheme."):
            c = ctx.scheme.get(s[7:])
            return QColor(c) if c is not None else default
        c = named_color(s)
        if c is not None:
            return c
    return default


def props(node: dict) -> dict:
    return node.get("props") or {}


def slot(node: dict, name: str):
    v = (node.get("slots") or {}).get(name)
    return v if isinstance(v, (dict, list)) and v else None
