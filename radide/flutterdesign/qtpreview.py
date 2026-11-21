"""Fast approximate Flutter preview drawn with Qt (the designer's fallback when Flutter / the live preview host
is not available, and the instant first frame while the live preview starts).

It implements a small version of Flutter's box layout protocol (min/max constraints down, sizes up) for the
catalog widgets of ``model.CATALOG`` - Scaffold, AppBar, Container + BoxDecoration (gradients, images, borders,
radius, shadows), Padding / Center / Align, Row / Column / Flex with main / cross alignment and Expanded /
Flexible / Spacer, Stack + Positioned, SizedBox, scroll views, Text with TextStyle, Icon (the SDK's Material
icon font), Image, TextField + InputDecoration, the buttons, Card, ListTile, navigation bars, inputs ... - and
paints a Material 3 look (ColorScheme from the screen's seed colour, light / dark, text scale). It also returns
the bounds of every node (selection overlay) and plays the screen's entrance animations (``anim``).

It is an approximation: the real rendering comes from the Flutter preview host (live.py).
"""
from __future__ import annotations

import colorsys
import math
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QFontMetricsF, QImage, QLinearGradient,
                         QPainter, QPainterPath, QPen, QRadialGradient, QTextLayout, QTextOption, QTransform)

from . import iconfont
from . import model as M

INF = float("inf")


# ============================================================================== colours
_FALLBACK_COLORS = {
    "transparent": "#00000000", "black": "#FF000000", "white": "#FFFFFFFF", "black87": "#DD000000",
    "black54": "#8A000000", "black45": "#73000000", "black38": "#61000000", "black26": "#42000000",
    "black12": "#1F000000", "white70": "#B3FFFFFF", "white60": "#99FFFFFF", "white54": "#8AFFFFFF",
    "white38": "#62FFFFFF", "white30": "#4DFFFFFF", "white24": "#3DFFFFFF", "white12": "#1FFFFFFF",
    "white10": "#1AFFFFFF", "red": "#FFF44336", "pink": "#FFE91E63", "purple": "#FF9C27B0",
    "deepPurple": "#FF673AB7", "indigo": "#FF3F51B5", "blue": "#FF2196F3", "lightBlue": "#FF03A9F4",
    "cyan": "#FF00BCD4", "teal": "#FF009688", "green": "#FF4CAF50", "lightGreen": "#FF8BC34A",
    "lime": "#FFCDDC39", "yellow": "#FFFFEB3B", "amber": "#FFFFC107", "orange": "#FFFF9800",
    "deepOrange": "#FFFF5722", "brown": "#FF795548", "grey": "#FF9E9E9E", "blueGrey": "#FF607D8B",
}


@lru_cache(maxsize=1)
def flutter_colors() -> tuple[dict[str, str], dict[str, dict[int, str]]]:
    """(plain colours, swatches name -> {shade: '#AARRGGBB'}) read from the Flutter SDK's colors.dart."""
    plain = dict(_FALLBACK_COLORS)
    swatches: dict[str, dict[int, str]] = {}
    sdk = iconfont._sdk()
    if sdk is None:
        return plain, swatches
    try:
        text = (sdk / "packages" / "flutter" / "lib" / "src" / "material" / "colors.dart").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return plain, swatches
    ints = {m.group(1): m.group(2) for m in re.finditer(r"static const int (_\w+) = 0x([0-9A-Fa-f]{8});", text)}
    for m in re.finditer(r"static const Color (\w+) = Color\(0x([0-9A-Fa-f]{8})\);", text):
        plain[m.group(1)] = "#" + m.group(2).upper()
    for m in re.finditer(r"static const Material(?:Accent)?Color (\w+) = Material(?:Accent)?Color\(\s*(\w+),\s*"
                         r"<int, Color>\{(.*?)\}\);", text, re.S):
        name, prim, body = m.group(1), m.group(2), m.group(3)
        shades = {}
        for s in re.finditer(r"(\d+): Color\((0x[0-9A-Fa-f]{8}|_\w+)\)", body):
            v = s.group(2)
            hexv = v[2:] if v.startswith("0x") else ints.get(v, "")
            if hexv:
                shades[int(s.group(1))] = "#" + hexv.upper()
        pv = prim[2:] if prim.startswith("0x") else ints.get(prim, "")
        if pv:
            plain[name] = "#" + pv.upper()
        swatches[name] = shades
    return plain, swatches


def _hex_color(h: str) -> QColor:
    h = h.lstrip("#")
    if len(h) == 6:
        h = "FF" + h
    v = int(h, 16)
    return QColor((v >> 16) & 255, (v >> 8) & 255, v & 255, (v >> 24) & 255)


def named_color(name: str) -> QColor | None:
    """'Colors.white' / 'Colors.grey.shade300' / 'Colors.blue[700]' / 'CupertinoColors.activeBlue'."""
    m = re.match(r"^(?:Colors|CupertinoColors)\.(\w+)(?:\.shade(\d+)|\[(\d+)\])?$", name.strip())
    if not m:
        return None
    plain, sw = flutter_colors()
    base, shade = m.group(1), m.group(2) or m.group(3)
    if name.startswith("CupertinoColors."):
        cup = {"activeBlue": "#FF007AFF", "systemBlue": "#FF007AFF", "activeGreen": "#FF34C759",
               "systemGreen": "#FF34C759", "systemRed": "#FFFF3B30", "destructiveRed": "#FFFF3B30",
               "systemGrey": "#FF8E8E93", "systemGrey6": "#FFF2F2F7", "white": "#FFFFFFFF",
               "black": "#FF000000", "systemOrange": "#FFFF9500", "systemYellow": "#FFFFCC00",
               "systemBackground": "#FFFFFFFF", "secondaryLabel": "#993C3C43", "label": "#FF000000",
               "separator": "#493C3C43", "systemPurple": "#FFAF52DE", "systemPink": "#FFFF2D55"}
        v = cup.get(base)
        return _hex_color(v) if v else None
    if shade:
        v = sw.get(base, {}).get(int(shade))
        return _hex_color(v) if v else None
    v = plain.get(base)
    return _hex_color(v) if v else None


# ======================================================================== colour scheme
def _hsl(c: QColor, s_mul: float, light: float, s_min: float = 0.0) -> str:
    h, _l, s = colorsys.rgb_to_hls(c.redF(), c.greenF(), c.blueF())
    s = max(s_min, min(1.0, s * s_mul))
    r, g, b = colorsys.hls_to_rgb(h, light, s)
    return "#FF%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def color_scheme(seed: str | None, dark: bool) -> dict[str, QColor]:
    """An approximate Material 3 ColorScheme.fromSeed (tones by HSL lightness)."""
    sc = _hex_color(M.normalize_color(seed) if seed and str(seed).startswith("#") else "#FF6750A4")
    if seed and not str(seed).startswith("#"):
        sc = named_color(str(seed)) or sc
    if not dark:
        t = {"primary": _hsl(sc, 1.0, .40, .35), "onPrimary": "#FFFFFFFF", "primaryContainer": _hsl(sc, 1.0, .90),
             "onPrimaryContainer": _hsl(sc, 1.0, .12), "secondary": _hsl(sc, .30, .40),
             "onSecondary": "#FFFFFFFF", "secondaryContainer": _hsl(sc, .40, .90),
             "onSecondaryContainer": _hsl(sc, .40, .12), "tertiary": _hsl(sc, .5, .40),
             "surface": _hsl(sc, .25, .985), "onSurface": _hsl(sc, .12, .11),
             "onSurfaceVariant": _hsl(sc, .14, .30), "surfaceContainerLowest": "#FFFFFFFF",
             "surfaceContainerLow": _hsl(sc, .25, .965), "surfaceContainer": _hsl(sc, .25, .945),
             "surfaceContainerHigh": _hsl(sc, .22, .925), "surfaceContainerHighest": _hsl(sc, .2, .90),
             "outline": _hsl(sc, .10, .48), "outlineVariant": _hsl(sc, .12, .80), "error": "#FFB3261E",
             "onError": "#FFFFFFFF", "shadow": "#FF000000", "inverseSurface": _hsl(sc, .1, .19),
             "surfaceTint": _hsl(sc, 1.0, .40, .35)}
    else:
        t = {"primary": _hsl(sc, 1.0, .80, .35), "onPrimary": _hsl(sc, 1.0, .20), "primaryContainer": _hsl(sc, 1.0, .30),
             "onPrimaryContainer": _hsl(sc, 1.0, .90), "secondary": _hsl(sc, .30, .80),
             "onSecondary": _hsl(sc, .3, .20), "secondaryContainer": _hsl(sc, .30, .30),
             "onSecondaryContainer": _hsl(sc, .3, .90), "tertiary": _hsl(sc, .5, .80),
             "surface": _hsl(sc, .2, .07), "onSurface": _hsl(sc, .12, .90),
             "onSurfaceVariant": _hsl(sc, .12, .80), "surfaceContainerLowest": _hsl(sc, .2, .045),
             "surfaceContainerLow": _hsl(sc, .2, .10), "surfaceContainer": _hsl(sc, .2, .12),
             "surfaceContainerHigh": _hsl(sc, .2, .17), "surfaceContainerHighest": _hsl(sc, .2, .22),
             "outline": _hsl(sc, .10, .58), "outlineVariant": _hsl(sc, .12, .30), "error": "#FFF2B8B5",
             "onError": "#FF601410", "shadow": "#FF000000", "inverseSurface": _hsl(sc, .1, .90),
             "surfaceTint": _hsl(sc, 1.0, .80, .35)}
    out = {k: _hex_color(v) for k, v in t.items()}
    out["background"] = out["surface"]
    out["onBackground"] = out["onSurface"]
    return out


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


class Ctx:
    """Everything a layout pass needs."""

    def __init__(self, scheme: dict, dark: bool = False, text_scale: float = 1.0, folder: Path | None = None,
                 images=None, font_family: str = "", selected: str | None = None, screen=None):
        self.scheme = scheme
        self.dark = dark
        self.text_scale = text_scale
        self.folder = folder
        self.images = images
        self.font_family = font_family or default_font()
        self.selected = selected
        self.screen = screen
        self.anim_t: float | None = None        # ms since "play" (None = final state)
        self.show_drawer: str | None = None     # "drawer" | "endDrawer" when the selection is inside one
        self.hinge: tuple | None = None         # foldable hinge / fold (x, y, w, h) in screen coordinates
        self.screen_size: tuple = (0.0, 0.0)    # device screen (w, h) in dp


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


# ================================================================================ fonts
_fonts_loaded = False


def default_font() -> str:
    """Roboto from the Flutter SDK (Flutter's default font on Android / the web), else Segoe UI."""
    global _fonts_loaded
    from PyQt6.QtGui import QFontDatabase
    if not _fonts_loaded:
        _fonts_loaded = True
        sdk = iconfont._sdk()
        if sdk is not None:
            folder = sdk / "bin" / "cache" / "artifacts" / "material_fonts"
            for p in sorted(folder.glob("roboto-*.ttf")):
                QFontDatabase.addApplicationFont(str(p))
    fams = set(QFontDatabase.families())
    return "Roboto" if "Roboto" in fams else "Segoe UI"


_WEIGHTS = {"w100": 100, "w200": 200, "w300": 300, "w400": 400, "w500": 500, "w600": 600, "w700": 700,
            "w800": 800, "w900": 900, "normal": 400, "bold": 700}


def make_font(style: dict, ctx: Ctx) -> QFont:
    fam = style.get("googleFont") or style.get("fontFamily") or ctx.font_family
    f = QFont(str(fam))
    if fam != ctx.font_family:
        f.setFamilies([str(fam), ctx.font_family])
    size = num(style.get("fontSize"), 14.0) * ctx.text_scale
    f.setPixelSize(max(1, int(round(size))))
    w = _WEIGHTS.get(enum_val(style.get("fontWeight"), "normal"), 400)
    f.setWeight(QFont.Weight(w))
    if enum_val(style.get("fontStyle")) == "italic":
        f.setItalic(True)
    ls = num(style.get("letterSpacing"))
    if ls:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, ls)
    deco = enum_val(style.get("decoration"))
    if deco == "underline":
        f.setUnderline(True)
    elif deco == "lineThrough":
        f.setStrikeOut(True)
    elif deco == "overline":
        f.setOverline(True)
    return f


def merge_style(base: dict, extra) -> dict:
    out = dict(base)
    if isinstance(extra, dict) and not M.is_code(extra):
        for k, v in extra.items():
            if v is not None and not M.is_code(v):
                out[k] = v
    return out


# ============================================================================= painting
def rrect_path(r: QRectF, rad: tuple | None, circle: bool = False) -> QPainterPath:
    path = QPainterPath()
    if circle:
        path.addEllipse(r)
        return path
    if not rad or not any(rad):
        path.addRect(r)
        return path
    tl, tr, br, bl = (min(x, r.width() / 2, r.height() / 2) for x in rad)
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    path.moveTo(x + tl, y)
    path.lineTo(x + w - tr, y)
    path.arcTo(x + w - 2 * tr, y, 2 * tr, 2 * tr, 90, -90) if tr else path.lineTo(x + w, y)
    path.lineTo(x + w, y + h - br)
    path.arcTo(x + w - 2 * br, y + h - 2 * br, 2 * br, 2 * br, 0, -90) if br else path.lineTo(x + w, y + h)
    path.lineTo(x + bl, y + h)
    path.arcTo(x, y + h - 2 * bl, 2 * bl, 2 * bl, 270, -90) if bl else path.lineTo(x, y + h)
    path.lineTo(x, y + tl)
    path.arcTo(x, y, 2 * tl, 2 * tl, 180, -90) if tl else path.lineTo(x, y)
    path.closeSubpath()
    return path


def gradient_brush(g: dict, r: QRectF, ctx: Ctx) -> QBrush | None:
    if not isinstance(g, dict) or M.is_code(g):
        return None
    cols = [color(c, ctx) for c in g.get("colors") or []]
    cols = [c for c in cols if c is not None]
    if not cols:
        return None
    stops = g.get("stops") or []
    if len(stops) != len(cols) or not all(isinstance(s, (int, float)) for s in stops):
        stops = [i / max(1, len(cols) - 1) for i in range(len(cols))]
    t = g.get("type", "linear")
    cx, cy = r.center().x(), r.center().y()

    def pt(a):
        ax, ay = align(a, (0.0, 0.0))
        return QPointF(cx + ax * r.width() / 2, cy + ay * r.height() / 2)
    if t == "radial":
        grad = QRadialGradient(pt(g.get("center", "Alignment.center")),
                               num(g.get("radius"), 0.5) * min(r.width(), r.height()))
    elif t == "sweep":
        grad = QConicalGradient(pt(g.get("center", "Alignment.center")), 0)
    else:
        grad = QLinearGradient(pt(g.get("begin", "Alignment.centerLeft")), pt(g.get("end", "Alignment.centerRight")))
    for s, c in zip(stops, cols):
        grad.setColorAt(max(0.0, min(1.0, float(s))), c)
    return QBrush(grad)


def paint_shadows(p: QPainter, path: QPainterPath, shadows, ctx: Ctx) -> None:
    if not isinstance(shadows, list):
        return
    for s in shadows:
        if not isinstance(s, dict) or M.is_code(s):
            continue
        col = color(s.get("color"), ctx, QColor(0, 0, 0, 60))
        blur = max(0.0, num(s.get("blur"), 0.0))
        spread = num(s.get("spread"), 0.0)
        off = s.get("offset") if isinstance(s.get("offset"), list) else [0, 0]
        dx, dy = num(off[0], 0.0) if off else 0.0, num(off[1], 0.0) if len(off) > 1 else 0.0
        drop_shadow(p, path, col, blur, spread, dx, dy)


def drop_shadow(p: QPainter, path: QPainterPath, col: QColor, blur: float, spread: float, dx: float,
                dy: float) -> None:
    """A blurred shadow: the shape drawn small and scaled up smoothly (QPainter has no blur filter)."""
    base = path
    if spread > 0:
        st = QPainterPathStrokerCompat(spread * 2)
        base = path.united(st.createStroke(path))
    p.save()
    p.translate(dx, dy)
    p.setPen(Qt.PenStyle.NoPen)
    if blur < 1.5:
        p.setBrush(col)
        p.drawPath(base)
        p.restore()
        return
    br = base.boundingRect().adjusted(-blur * 1.5, -blur * 1.5, blur * 1.5, blur * 1.5)
    k = max(1.0, blur / 2.5)                     # downscale factor
    sw, sh = max(2, int(br.width() / k) + 2), max(2, int(br.height() / k) + 2)
    if sw * sh > 4_000_000:
        p.setBrush(col)
        p.drawPath(base)
        p.restore()
        return
    img = QImage(sw, sh, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    q = QPainter(img)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    q.scale(1 / k, 1 / k)
    q.translate(-br.x(), -br.y())
    q.setPen(Qt.PenStyle.NoPen)
    q.setBrush(col)
    q.drawPath(base)
    q.end()
    # one more smooth down/up pass softens the edge like a gaussian
    img = img.scaled(max(1, sw // 2), max(1, sh // 2), Qt.AspectRatioMode.IgnoreAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(br, img)
    p.restore()


def QPainterPathStrokerCompat(width: float):
    from PyQt6.QtGui import QPainterPathStroker
    s = QPainterPathStroker()
    s.setWidth(max(0.01, width))
    s.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    s.setCapStyle(Qt.PenCapStyle.RoundCap)
    return s


def paint_image(p: QPainter, r: QRectF, img: QImage | None, fit: str, al=(0.0, 0.0), clip_path=None,
                tint: QColor | None = None, opacity: float = 1.0) -> None:
    p.save()
    if clip_path is not None:
        p.setClipPath(clip_path, Qt.ClipOperation.IntersectClip)
    else:
        p.setClipRect(r, Qt.ClipOperation.IntersectClip)
    if opacity < 1:
        p.setOpacity(p.opacity() * opacity)
    if img is None or img.isNull():
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor("#FFB8C4D6"))
        g.setColorAt(1, QColor("#FF8A9BB5"))
        p.fillRect(r, QBrush(g))
        s = min(r.width(), r.height(), 48.0) * 0.6
        if s > 6:
            iconfont.draw(p, QRectF(r.center().x() - s / 2, r.center().y() - s / 2, s, s), "image",
                          QColor(255, 255, 255, 200))
        p.restore()
        return
    iw, ih = img.width(), img.height()
    fit = fit or "contain"
    if fit == "fill":
        dw, dh = r.width(), r.height()
    elif fit == "cover":
        k = max(r.width() / iw, r.height() / ih)
        dw, dh = iw * k, ih * k
    elif fit == "fitWidth":
        k = r.width() / iw
        dw, dh = r.width(), ih * k
    elif fit == "fitHeight":
        k = r.height() / ih
        dw, dh = iw * k, r.height()
    elif fit in ("none",):
        dw, dh = iw, ih
    elif fit == "scaleDown":
        k = min(1.0, r.width() / iw, r.height() / ih)
        dw, dh = iw * k, ih * k
    else:
        k = min(r.width() / iw, r.height() / ih)
        dw, dh = iw * k, ih * k
    x = r.x() + (r.width() - dw) * (al[0] + 1) / 2
    y = r.y() + (r.height() - dh) * (al[1] + 1) / 2
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRectF(x, y, dw, dh), img)
    if tint is not None:
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        p.fillRect(QRectF(x, y, dw, dh), tint)
    p.restore()


def paint_decoration(p: QPainter, r: QRectF, dec: dict, ctx: Ctx) -> None:
    if not isinstance(dec, dict) or M.is_code(dec):
        return
    circle = enum_val(dec.get("shape")) == "circle"
    if circle:
        d = min(r.width(), r.height())
        r = QRectF(r.center().x() - d / 2, r.center().y() - d / 2, d, d)
    path = rrect_path(r, radii(dec.get("borderRadius")), circle)
    paint_shadows(p, path, dec.get("boxShadow"), ctx)
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    c = color(dec.get("color"), ctx)
    if c is not None:
        p.setBrush(c)
        p.drawPath(path)
    gb = gradient_brush(dec.get("gradient"), r, ctx)
    if gb is not None:
        p.setBrush(gb)
        p.drawPath(path)
    img = dec.get("image")
    if isinstance(img, dict) and not M.is_code(img):
        q = ctx.images.get(img.get("source", "asset"), img.get("src", ""), ctx.folder) if ctx.images else None
        paint_image(p, r, q, enum_val(img.get("fit"), "cover") if img.get("fit") else "none",
                    align(img.get("alignment"), (0.0, 0.0)), path, opacity=num(img.get("opacity"), 1.0))
    p.restore()
    paint_border(p, r, dec.get("border"), radii(dec.get("borderRadius")), circle, ctx)


def paint_border(p: QPainter, r: QRectF, b, rad, circle: bool, ctx: Ctx) -> None:
    if not isinstance(b, dict) or M.is_code(b):
        return
    p.save()
    p.setBrush(Qt.BrushStyle.NoBrush)
    sides = [k for k in ("top", "right", "bottom", "left") if isinstance(b.get(k), dict)]
    if not sides:
        w = num(b.get("width"), 1.0)
        if w > 0:
            p.setPen(QPen(color(b.get("color"), ctx, QColor("#FF000000")), w))
            p.drawPath(rrect_path(r.adjusted(w / 2, w / 2, -w / 2, -w / 2),
                                  tuple(max(0.0, x - w / 2) for x in rad) if rad else None, circle))
        p.restore()
        return
    for k in sides:
        s = b[k]
        w = num(s.get("width"), 1.0)
        if w <= 0:
            continue
        p.setPen(QPen(color(s.get("color"), ctx, QColor("#FF000000")), w, cap=Qt.PenCapStyle.FlatCap))
        h = w / 2
        if k == "top":
            p.drawLine(QPointF(r.left(), r.top() + h), QPointF(r.right(), r.top() + h))
        elif k == "bottom":
            p.drawLine(QPointF(r.left(), r.bottom() - h), QPointF(r.right(), r.bottom() - h))
        elif k == "left":
            p.drawLine(QPointF(r.left() + h, r.top()), QPointF(r.left() + h, r.bottom()))
        else:
            p.drawLine(QPointF(r.right() - h, r.top()), QPointF(r.right() - h, r.bottom()))
    p.restore()


def shape_path(shape, r: QRectF, default_radius: float | tuple = 0.0) -> QPainterPath:
    """ShapeBorder JSON -> path."""
    if isinstance(shape, dict) and not M.is_code(shape):
        t = shape.get("type", "rounded")
        if t == "circle":
            d = min(r.width(), r.height())
            return rrect_path(QRectF(r.center().x() - d / 2, r.center().y() - d / 2, d, d), None, True)
        if t == "stadium":
            return rrect_path(r, (min(r.width(), r.height()) / 2,) * 4)
        return rrect_path(r, radii(shape.get("radius")) or (0.0,) * 4)
    rad = default_radius if isinstance(default_radius, tuple) else (float(default_radius),) * 4
    return rrect_path(r, rad)


def shape_side(shape, ctx: Ctx):
    if isinstance(shape, dict) and isinstance(shape.get("side"), dict):
        s = shape["side"]
        return color(s.get("color"), ctx, QColor("#FF000000")), num(s.get("width"), 1.0)
    return None


# =============================================================================== images
class ImageCache(QObject):
    """Asset images from the project folder and network images (downloaded once, asynchronously)."""
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache: dict[str, QImage | None] = {}
        self._nam = None
        self._pending: set[str] = set()
        self.offline = False

    def get(self, source: str, src: str, folder: Path | None) -> QImage | None:
        if not src or not isinstance(src, str):
            return None
        if source == "network" or src.startswith(("http://", "https://")):
            if src in self._cache:
                return self._cache[src]
            self._fetch(src)
            return None
        p = Path(src)
        if not p.is_absolute() and folder is not None:
            p = Path(folder) / src
        if not p.is_file() and folder is not None and (Path(folder) / p.name).is_file():
            p = Path(folder) / p.name           # template artwork kept flat next to the template
        key = str(p)
        if key not in self._cache:
            img = QImage(key) if p.is_file() else QImage()
            self._cache[key] = None if img.isNull() else img
        return self._cache[key]

    def _fetch(self, url: str) -> None:
        if self.offline or url in self._pending:
            return
        try:
            from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
        except ImportError:
            self._cache[url] = None
            return
        if self._nam is None:
            self._nam = QNetworkAccessManager(self)
        self._pending.add(url)
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        req.setTransferTimeout(15000)
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, u=url: self._done(r, u))

    def _done(self, reply, url: str) -> None:
        self._pending.discard(url)
        img = QImage()
        try:
            data = reply.readAll()
            img.loadFromData(bytes(data))
        finally:
            reply.deleteLater()
        self._cache[url] = None if img.isNull() else img
        if not img.isNull():
            self.changed.emit()

    def pending(self) -> int:
        return len(self._pending)


# ============================================================================== layout
LAYOUTS: dict = {}


def reg(*types):
    def deco(fn):
        for t in types:
            LAYOUTS[t] = fn
        return fn
    return deco


def layout_node(node, c: C, env: Env, ctx: Ctx) -> Box:
    if not isinstance(node, dict):
        return Box(*c.constrain(0, 0))
    fn = LAYOUTS.get(node.get("type"), _unknown)
    try:
        box = fn(node, c, env, ctx)
    except Exception:  # noqa: BLE001 - one broken widget must not hide the screen
        box = _error_box(node, c)
    if box.nid is not None:
        box = Box(box.w, box.h, [box])
    w, h = box.w, box.h
    if w == INF or h == INF or w != w or h != h:
        w = c.minW if w == INF or w != w else w
        h = c.minH if h == INF or h != h else h
    box.w, box.h = max(0.0, min(max(w, c.minW), c.maxW)), max(0.0, min(max(h, c.minH), c.maxH))
    box.nid = node.get("id")
    box.ntype = node.get("type", "")
    if node.get("anim"):
        box.anim = node["anim"]
    return box


def _error_box(node, c: C) -> Box:
    w, h = c.constrain(min(c.maxW, 120), min(c.maxH, 40))

    def paint(p, b, ctx):
        p.fillRect(QRectF(0, 0, b.w, b.h), QColor(255, 0, 0, 40))
        p.setPen(QPen(QColor("#FFD32F2F"), 1, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(0.5, 0.5, b.w - 1, b.h - 1))
    return Box(w, h, paint=paint)


def _unknown(node, c, env, ctx) -> Box:
    kid = first_child(node)
    if kid is not None:
        return layout_node(kid, c, env, ctx)
    w, h = c.constrain(min(c.maxW, 100), min(c.maxH, 40))

    def paint(p, b, ctx):
        p.setPen(QPen(QColor("#FF9E9E9E"), 1, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(0.5, 0.5, b.w - 1, b.h - 1))
        f = QFont(ctx.font_family)
        f.setPixelSize(11)
        p.setFont(f)
        p.drawText(QRectF(0, 0, b.w, b.h), int(Qt.AlignmentFlag.AlignCenter), node.get("type", "?"))
    return Box(w, h, paint=paint)


def first_child(node: dict):
    for k in ("child", "body", "title", "label"):
        v = slot(node, k)
        if isinstance(v, dict):
            return v
    for v in (node.get("slots") or {}).values():
        if isinstance(v, dict):
            return v
    kids = node.get("children") or []
    return kids[0] if kids else None


def passthrough(child, c: C, env: Env, ctx: Ctx) -> Box:
    if child is None:
        return Box(*c.constrain(0, 0))
    b = layout_node(child, c, env, ctx)
    return Box(b.w, b.h, [at(b, 0, 0)])


def pad_box(insets, c: C, inner) -> Box:
    l, t, r, b = insets
    kid = inner(c.deflate(l, t, r, b))
    w, h = c.constrain(kid.w + l + r, kid.h + t + b)
    return Box(w, h, [at(kid, l, t)])


def align_box(al, c: C, inner, wf=None, hf=None) -> Box:
    kid = inner(c.loosen())
    w = kid.w * wf if wf is not None else (c.maxW if c.maxW < INF else kid.w)
    h = kid.h * hf if hf is not None else (c.maxH if c.maxH < INF else kid.h)
    w, h = c.constrain(w, h)
    return Box(w, h, [at(kid, (w - kid.w) * (al[0] + 1) / 2, (h - kid.h) * (al[1] + 1) / 2)])


def child_fn(node, env, ctx, name="child"):
    kid = slot(node, name)
    if isinstance(kid, dict):
        return lambda cc: layout_node(kid, cc, env, ctx)
    return None


# ---------------------------------------------------------------------------- Layout
@reg("Container", "AnimatedContainer")
def _container(node, c, env, ctx):
    pr = props(node)
    dec = pr.get("decoration") if isinstance(pr.get("decoration"), dict) and not M.is_code(pr.get("decoration")) \
        else None
    col = pr.get("color")
    margin = edge(pr.get("margin"))
    padding = list(edge(pr.get("padding")))
    if dec and isinstance(dec.get("border"), dict) and not M.is_code(dec["border"]):
        bw = dec["border"]
        if any(k in bw for k in ("top", "left", "right", "bottom")):
            ws = [num((bw.get(k) or {}).get("width"), 1.0) if isinstance(bw.get(k), dict) else 0.0
                  for k in ("left", "top", "right", "bottom")]
        else:
            ws = [num(bw.get("width"), 1.0)] * 4
        padding = [a + b for a, b in zip(padding, ws)]
    w, h = num(pr.get("width")), num(pr.get("height"))
    extra = C()
    cons = pr.get("constraints")
    if isinstance(cons, dict) and not M.is_code(cons):
        extra = C(num(cons.get("minWidth"), 0.0), num(cons.get("maxWidth"), INF), num(cons.get("minHeight"), 0.0),
                  num(cons.get("maxHeight"), INF))
    if w is not None:
        extra = extra.tighten(w=w) if extra.maxW == INF else C(w, w, extra.minH, extra.maxH)
    if h is not None:
        extra = C(extra.minW, extra.maxW, h, h)
    kid = slot(node, "child")
    al = pr.get("alignment")
    cc = c.deflate(*margin)
    cc = extra.enforce(cc)

    def inner(c2):
        if isinstance(kid, dict):
            fn = (lambda c3: layout_node(kid, c3, env, ctx))
            if al is not None:
                return pad_box(padding, c2, lambda c3: align_box(align(al), c3, fn))
            return pad_box(padding, c2, fn)
        # no child: expand when bounded (LimitedBox + ConstrainedBox.expand)
        ww = c2.maxW if c2.maxW < INF else c2.minW
        hh = c2.maxH if c2.maxH < INF else c2.minH
        return Box(*c2.constrain(ww, hh))
    body = inner(cc)
    bw, bh = cc.constrain(body.w, body.h)

    def paint(p, b, ctx2, dec=dec, col=col):
        r = QRectF(margin[0], margin[1], bw, bh)
        if col is not None:
            cq = color(col, ctx2)
            if cq is not None:
                p.fillRect(r, cq)
        if dec:
            paint_decoration(p, r, dec, ctx2)
    box = Box(bw + margin[0] + margin[2], bh + margin[1] + margin[3], [at(body, margin[0], margin[1])], paint)
    clip = enum_val(pr.get("clipBehavior"), "none")
    if clip != "none" and dec:
        box.clip = rrect_path(QRectF(margin[0], margin[1], bw, bh), radii(dec.get("borderRadius")),
                              enum_val(dec.get("shape")) == "circle")
    return box


@reg("Padding")
def _padding(node, c, env, ctx):
    fn = child_fn(node, env, ctx) or (lambda cc: Box(*cc.constrain(0, 0)))
    return pad_box(edge(props(node).get("padding", {"all": 8})), c, fn)


@reg("SafeArea")
def _safearea(node, c, env, ctx):
    pr = props(node)
    mn = edge(pr.get("minimum"))
    t = max(mn[1], env.pad_top if pr.get("top", True) is not False else 0.0)
    b = max(mn[3], env.pad_bottom if pr.get("bottom", True) is not False else 0.0)
    e2 = replace(env, pad_top=0.0, pad_bottom=0.0)
    kid = slot(node, "child")
    fn = (lambda cc: layout_node(kid, cc, e2, ctx)) if isinstance(kid, dict) else (lambda cc: Box(*cc.constrain(0, 0)))
    return pad_box((mn[0], t, mn[2], b), c, fn)


@reg("Center")
def _center(node, c, env, ctx):
    fn = child_fn(node, env, ctx) or (lambda cc: Box(0, 0))
    pr = props(node)
    return align_box((0.0, 0.0), c, fn, num(pr.get("widthFactor")), num(pr.get("heightFactor")))


@reg("Align")
def _align(node, c, env, ctx):
    fn = child_fn(node, env, ctx) or (lambda cc: Box(0, 0))
    pr = props(node)
    return align_box(align(pr.get("alignment", "Alignment.center")), c, fn, num(pr.get("widthFactor")),
                     num(pr.get("heightFactor")))


@reg("SizedBox")
def _sizedbox(node, c, env, ctx):
    pr = props(node)
    ctor = node.get("ctor")
    if ctor == "expand":
        w = h = INF
    elif ctor == "shrink":
        w = h = 0.0
    elif ctor == "square":
        w = h = num(pr.get("dimension"), 50.0)
    else:
        w, h = num(pr.get("width")), num(pr.get("height"))
    extra = C(w if w is not None else 0.0, w if w is not None else INF, h if h is not None else 0.0,
              h if h is not None else INF)
    cc = extra.enforce(c)
    kid = slot(node, "child")
    if isinstance(kid, dict):
        b = layout_node(kid, cc, env, ctx)
        return Box(*cc.constrain(b.w, b.h), [at(b, 0, 0)])
    return Box(*cc.constrain(0, 0))


@reg("ConstrainedBox")
def _constrainedbox(node, c, env, ctx):
    cons = props(node).get("constraints") or {}
    extra = C(num(cons.get("minWidth"), 0.0), num(cons.get("maxWidth"), INF), num(cons.get("minHeight"), 0.0),
              num(cons.get("maxHeight"), INF)) if isinstance(cons, dict) else C()
    cc = extra.enforce(c)
    kid = slot(node, "child")
    if isinstance(kid, dict):
        b = layout_node(kid, cc, env, ctx)
        return Box(*cc.constrain(b.w, b.h), [at(b, 0, 0)])
    return Box(*cc.constrain(0, 0))


@reg("AspectRatio")
def _aspect(node, c, env, ctx):
    ratio = num(props(node).get("aspectRatio"), 1.0) or 1.0
    w = c.maxW if c.maxW < INF else (c.maxH * ratio if c.maxH < INF else 100.0)
    h = w / ratio
    if h > c.maxH:
        h = c.maxH
        w = h * ratio
    w, h = c.constrain(w, h)
    kid = slot(node, "child")
    kids = [at(layout_node(kid, C.tight(w, h), env, ctx), 0, 0)] if isinstance(kid, dict) else []
    return Box(w, h, kids)


@reg("FractionallySizedBox")
def _fraction(node, c, env, ctx):
    pr = props(node)
    wf, hf = num(pr.get("widthFactor")), num(pr.get("heightFactor"))
    cc = replace(c)
    if wf is not None and c.maxW < INF:
        cc.minW = cc.maxW = c.maxW * wf
    if hf is not None and c.maxH < INF:
        cc.minH = cc.maxH = c.maxH * hf
    fn = child_fn(node, env, ctx) or (lambda c2: Box(*c2.constrain(0, 0)))
    return align_box(align(pr.get("alignment"), (0.0, 0.0)), c, lambda _c: fn(cc))


@reg("FittedBox")
def _fitted(node, c, env, ctx):
    kid = slot(node, "child")
    if not isinstance(kid, dict):
        return Box(*c.constrain(0, 0))
    b = layout_node(kid, C(), env, ctx)
    if b.w <= 0 or b.h <= 0:
        return Box(*c.constrain(0, 0))
    w, h = c.constrain(b.w, b.h)
    if c.maxW < INF and b.w > c.maxW or c.maxH < INF and b.h > c.maxH:
        k = min(c.maxW / b.w if c.maxW < INF else INF, c.maxH / b.h if c.maxH < INF else INF)
        w, h = c.constrain(b.w * k, b.h * k)
    k = min(w / b.w, h / b.h)
    box = Box(w, h, [at(b, (w - b.w * k) / 2 / k, (h - b.h * k) / 2 / k)])
    box.xform = QTransform().scale(k, k)
    return box


@reg("Transform")
def _transform(node, c, env, ctx):
    b = passthrough(slot(node, "child"), c, env, ctx)
    pr = props(node)
    ctor = node.get("ctor") or "rotate"
    t = QTransform()
    ax, ay = align(pr.get("alignment"), (0.0, 0.0))
    ox, oy = b.w * (ax + 1) / 2, b.h * (ay + 1) / 2
    if ctor == "translate":
        off = pr.get("offset") if isinstance(pr.get("offset"), list) else [0, 0]
        t.translate(num(off[0], 0.0), num(off[1], 0.0))
    else:
        t.translate(ox, oy)
        if ctor == "scale":
            k = num(pr.get("scale"), 1.0)
            t.scale(k, k)
        else:
            t.rotateRadians(num(pr.get("angle"), 0.0))
        t.translate(-ox, -oy)
    b.xform = t
    return b


@reg("RotatedBox")
def _rotated(node, c, env, ctx):
    q = int(num(props(node).get("quarterTurns"), 1.0)) % 4
    kid = slot(node, "child")
    if not isinstance(kid, dict):
        return Box(*c.constrain(0, 0))
    cc = c if q % 2 == 0 else C(c.minH, c.maxH, c.minW, c.maxW)
    b = layout_node(kid, cc, env, ctx)
    w, h = (b.w, b.h) if q % 2 == 0 else (b.h, b.w)
    t = QTransform()
    t.translate(w / 2, h / 2)
    t.rotate(90 * q)
    t.translate(-b.w / 2, -b.h / 2)
    inner = Box(b.w, b.h, [at(b, 0, 0)])
    inner.xform = t
    return Box(w, h, [inner])


@reg("Visibility")
def _visibility(node, c, env, ctx):
    if props(node).get("visible") is False:
        return Box(*c.constrain(0, 0))
    return passthrough(slot(node, "child"), c, env, ctx)


@reg("IntrinsicHeight", "Form", "Hero", "Tooltip", "GestureDetector", "AnimatedSwitcher", "DefaultTabController",
     "Expanded", "Flexible", "Positioned")
def _pass(node, c, env, ctx):
    return passthrough(slot(node, "child"), c, env, ctx)


@reg("InkWell")
def _inkwell(node, c, env, ctx):
    return passthrough(slot(node, "child"), c, env, ctx)


@reg("Spacer")
def _spacer(node, c, env, ctx):
    return Box(*c.constrain(0, 0))


# ------------------------------------------------------------------------------ Flex
def flex_of(node) -> tuple[int, bool]:
    """(flex factor, tight) of a Row / Column child; (0, False) = not flexible."""
    if not isinstance(node, dict):
        return 0, False
    t = node.get("type")
    if t in ("Expanded", "Spacer"):
        return max(1, int(num(props(node).get("flex"), 1.0))), True
    if t == "Flexible":
        return max(1, int(num(props(node).get("flex"), 1.0))), enum_val(props(node).get("fit"), "loose") == "tight"
    return 0, False


def flex_layout(node, c: C, env: Env, ctx: Ctx, horizontal: bool) -> Box:
    pr = props(node)
    kids = [k for k in (node.get("children") or []) if isinstance(k, dict)]
    main_al = enum_val(pr.get("mainAxisAlignment"), "start")
    cross_al = enum_val(pr.get("crossAxisAlignment"), "center")
    main_max = enum_val(pr.get("mainAxisSize"), "max") == "max"
    spacing = num(pr.get("spacing"), 0.0) or 0.0
    max_main = c.maxW if horizontal else c.maxH
    max_cross = c.maxH if horizontal else c.maxW
    stretch = cross_al == "stretch" and max_cross < INF
    e2 = replace(env, in_flex=True)

    def cc(mn, mx):
        cmin, cmax = (max_cross, max_cross) if stretch else (0.0, max_cross)
        return C(mn, mx, cmin, cmax) if horizontal else C(cmin, cmax, mn, mx)

    def main(b):
        return b.w if horizontal else b.h

    def cross(b):
        return b.h if horizontal else b.w
    boxes: list = [None] * len(kids)
    total_flex, allocated = 0, 0.0
    for i, k in enumerate(kids):
        f, _t = flex_of(k)
        if f:
            total_flex += f
            continue
        boxes[i] = layout_node(k, cc(0.0, INF), e2, ctx)
        allocated += main(boxes[i])
    gaps = spacing * max(0, len(kids) - 1)
    free = max(0.0, max_main - allocated - gaps) if max_main < INF else 0.0
    for i, k in enumerate(kids):
        f, tight = flex_of(k)
        if not f:
            continue
        share = free * f / total_flex if total_flex else 0.0
        boxes[i] = layout_node(k, cc(share if tight else 0.0, share), e2, ctx)
        allocated += main(boxes[i])
    content = allocated + gaps
    mmin = c.minW if horizontal else c.minH
    main_size = max_main if (main_max and max_main < INF) else max(mmin, min(content, max_main))
    cross_size = max([cross(b) for b in boxes] + [0.0])
    if stretch:
        cross_size = max_cross
    cmin = c.minH if horizontal else c.minW
    cross_size = max(cmin, min(cross_size, max_cross))
    remaining = main_size - content
    n = len(boxes)
    lead, between = 0.0, spacing
    if remaining > 0:
        if main_al == "end":
            lead = remaining
        elif main_al == "center":
            lead = remaining / 2
        elif main_al == "spaceBetween" and n > 1:
            between += remaining / (n - 1)
        elif main_al == "spaceAround" and n:
            between += remaining / n
            lead = remaining / n / 2
        elif main_al == "spaceEvenly" and n:
            between += remaining / (n + 1)
            lead = remaining / (n + 1)
    pos = lead
    for b in boxes:
        free_cross = cross_size - cross(b)
        co = 0.0 if cross_al in ("start", "stretch", "baseline") else (free_cross if cross_al == "end"
                                                                         else free_cross / 2)
        if horizontal:
            at(b, pos, co)
        else:
            at(b, co, pos)
        pos += main(b) + between
    w, h = (main_size, cross_size) if horizontal else (cross_size, main_size)
    box = Box(w, h, boxes)
    if remaining < -0.5:
        box.overflow = ("right" if horizontal else "bottom", -remaining)
    return box


@reg("Row")
def _row(node, c, env, ctx):
    return flex_layout(node, c, env, ctx, True)


@reg("Column")
def _column(node, c, env, ctx):
    return flex_layout(node, c, env, ctx, False)


@reg("Flex")
def _flex(node, c, env, ctx):
    return flex_layout(node, c, env, ctx, enum_val(props(node).get("direction"), "horizontal") == "horizontal")


@reg("Wrap")
def _wrap(node, c, env, ctx):
    pr = props(node)
    sp, rsp = num(pr.get("spacing"), 0.0), num(pr.get("runSpacing"), 0.0)
    maxw = c.maxW if c.maxW < INF else 1e9
    boxes = [layout_node(k, C(0, maxw), env, ctx) for k in node.get("children") or [] if isinstance(k, dict)]
    runs, cur, cw = [], [], 0.0
    for b in boxes:
        if cur and cw + sp + b.w > maxw:
            runs.append(cur)
            cur, cw = [], 0.0
        cw += (sp if cur else 0) + b.w
        cur.append(b)
    if cur:
        runs.append(cur)
    y, width = 0.0, 0.0
    al = enum_val(pr.get("alignment"), "start")
    for run in runs:
        rw = sum(b.w for b in run) + sp * (len(run) - 1)
        width = max(width, rw)
    width = c.maxW if c.maxW < INF else width
    for run in runs:
        rw = sum(b.w for b in run) + sp * (len(run) - 1)
        rh = max(b.h for b in run)
        x = {"end": width - rw, "center": (width - rw) / 2}.get(al, 0.0)
        for b in run:
            at(b, x, y + (rh - b.h) / 2 if enum_val(pr.get("crossAxisAlignment")) == "center" else y)
            x += b.w + sp
        y += rh + rsp
    h = max(0.0, y - rsp) if runs else 0.0
    return Box(*c.constrain(width, h), boxes)


@reg("Stack")
def _stack(node, c, env, ctx):
    pr = props(node)
    fit = enum_val(pr.get("fit"), "loose")
    al = align(pr.get("alignment"), (-1.0, -1.0))
    kids = [k for k in node.get("children") or [] if isinstance(k, dict)]
    nc = c.loosen() if fit == "loose" else (C.tight(*c.biggest) if fit == "expand" else c)
    boxes: list = [None] * len(kids)
    w = h = 0.0
    has_np = False
    for i, k in enumerate(kids):
        if k.get("type") in ("Positioned", "AnimatedPositioned"):
            continue
        has_np = True
        boxes[i] = layout_node(k, nc, env, ctx)
        w, h = max(w, boxes[i].w), max(h, boxes[i].h)
    if has_np:
        w, h = c.constrain(w, h)
    else:
        w, h = c.biggest
    for i, k in enumerate(kids):
        b = boxes[i]
        if b is not None:
            at(b, (w - b.w) * (al[0] + 1) / 2, (h - b.h) * (al[1] + 1) / 2)
            continue
        p = props(k)
        if k.get("ctor") == "fill":
            pw = ph = None
            l, t, r, bt = (num(p.get("left"), 0.0), num(p.get("top"), 0.0), num(p.get("right"), 0.0),
                           num(p.get("bottom"), 0.0))
        else:
            l, t, r, bt = num(p.get("left")), num(p.get("top")), num(p.get("right")), num(p.get("bottom"))
            pw, ph = num(p.get("width")), num(p.get("height"))
        cc = C()
        if l is not None and r is not None:
            cc = cc.tighten(w=max(0.0, w - l - r))
        elif pw is not None:
            cc = cc.tighten(w=pw)
        if t is not None and bt is not None:
            cc = cc.tighten(h=max(0.0, h - t - bt))
        elif ph is not None:
            cc = cc.tighten(h=ph)
        b = layout_node(k, cc, env, ctx)
        x = l if l is not None else (w - r - b.w if r is not None else (w - b.w) * (al[0] + 1) / 2)
        y = t if t is not None else (h - bt - b.h if bt is not None else (h - b.h) * (al[1] + 1) / 2)
        boxes[i] = at(b, x, y)
    box = Box(w, h, [b for b in boxes if b is not None])
    if enum_val(pr.get("clipBehavior"), "hardEdge") != "none":
        box.clip = "rect"
    return box


# ---------------------------------------------------------------------------- Scroll
def _scroll_axis(node) -> bool:
    return enum_val(props(node).get("scrollDirection"), "vertical") == "horizontal"


@reg("SingleChildScrollView")
def _scv(node, c, env, ctx):
    horiz = _scroll_axis(node)
    pad = edge(props(node).get("padding"))
    kid = slot(node, "child")
    inner_c = C(c.minW, c.maxW, 0, INF) if not horiz else C(0, INF, c.minH, c.maxH)
    inner_c = inner_c.deflate(*pad) if not horiz else inner_c.deflate(*pad)
    if not horiz:
        inner_c.maxH = INF
    else:
        inner_c.maxW = INF
    b = layout_node(kid, inner_c, env, ctx) if isinstance(kid, dict) else Box(0, 0)
    w, h = c.constrain(b.w + pad[0] + pad[2], b.h + pad[1] + pad[3])
    box = Box(w, h, [at(b, pad[0], pad[1])])
    box.clip = "rect"
    return box


@reg("ListView")
def _listview(node, c, env, ctx):
    horiz = _scroll_axis(node)
    pr = props(node)
    pad = edge(pr.get("padding"))
    ext = num(pr.get("itemExtent"))
    kids = [k for k in node.get("children") or [] if isinstance(k, dict)]
    boxes, pos = [], (pad[0] if horiz else pad[1])
    cross = (c.maxH - pad[1] - pad[3]) if horiz else (c.maxW - pad[0] - pad[2])
    for k in kids:
        if horiz:
            cc = C(0 if ext is None else ext, INF if ext is None else ext, 0, cross)
            if cross < INF:
                cc.minH = cross
        else:
            cc = C(cross if cross < INF else 0, cross, 0 if ext is None else ext, INF if ext is None else ext)
        b = layout_node(k, cc, env, ctx)
        boxes.append(at(b, pos, pad[1]) if horiz else at(b, pad[0], pos))
        pos += b.w if horiz else b.h
    content = pos + (pad[2] if horiz else pad[3])
    if pr.get("shrinkWrap") is True:
        w, h = c.constrain(content, c.maxH) if horiz else c.constrain(c.maxW, content)
    else:
        w, h = c.biggest
        if horiz and c.maxW == INF:
            w = content
        if not horiz and c.maxH == INF:
            h = content
    box = Box(w, h, boxes)
    box.clip = "rect"
    return box


@reg("GridView")
def _grid(node, c, env, ctx):
    pr = props(node)
    pad = edge(pr.get("padding"))
    ms, cs = num(pr.get("mainAxisSpacing"), 0.0), num(pr.get("crossAxisSpacing"), 0.0)
    ratio = num(pr.get("childAspectRatio"), 1.0) or 1.0
    width = (c.maxW if c.maxW < INF else 360.0) - pad[0] - pad[2]
    if node.get("ctor") == "extent":
        mx = num(pr.get("maxCrossAxisExtent"), 150.0) or 150.0
        count = max(1, math.ceil(width / (mx + cs)))
    else:
        count = max(1, int(num(pr.get("crossAxisCount"), 2.0)))
    cw = (width - cs * (count - 1)) / count
    chh = cw / ratio
    boxes = []
    for i, k in enumerate([k for k in node.get("children") or [] if isinstance(k, dict)]):
        r, col = divmod(i, count)
        b = layout_node(k, C.tight(cw, chh), env, ctx)
        boxes.append(at(b, pad[0] + col * (cw + cs), pad[1] + r * (chh + ms)))
    rows = math.ceil(len(boxes) / count) if boxes else 0
    content = pad[1] + pad[3] + rows * chh + max(0, rows - 1) * ms
    if pr.get("shrinkWrap") is True or c.maxH == INF:
        w, h = c.constrain(width + pad[0] + pad[2], content)
    else:
        w, h = c.biggest
    box = Box(w, h, boxes)
    box.clip = "rect"
    return box


@reg("PageView", "TabBarView")
def _pageview(node, c, env, ctx):
    w, h = c.biggest
    kids = [k for k in node.get("children") or [] if isinstance(k, dict)]
    boxes = [at(layout_node(kids[0], C.tight(w, h), env, ctx), 0, 0)] if kids else []
    box = Box(w, h, boxes)
    box.clip = "rect"
    return box


# ---------------------------------------------------------------------------- Content
def _text_box(text: str, style: dict, c: C, ctx: Ctx, align_: str = "", max_lines=None, overflow: str = "",
              soft_wrap=True, color_default=None) -> Box:
    font = make_font(style, ctx)
    col = color(style.get("color"), ctx, color_default or ctx.scheme["onSurface"])
    fm = QFontMetricsF(font)
    hmul = num(style.get("height"))
    lh = font.pixelSize() * hmul if hmul else fm.height()
    tl = QTextLayout(text, font)
    opt = QTextOption()
    opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere if soft_wrap is not False
                    else QTextOption.WrapMode.NoWrap)
    tl.setTextOption(opt)
    maxw = c.maxW if c.maxW < INF else 1e6
    tl.beginLayout()
    lines, y, widest = [], 0.0, 0.0
    truncated = False
    while True:
        line = tl.createLine()
        if not line.isValid():
            break
        line.setLineWidth(maxw)
        if max_lines and len(lines) >= max_lines:
            truncated = True
            break
        widest = max(widest, line.naturalTextWidth())
        line.setPosition(QPointF(0, y + (lh - fm.height()) / 2))
        lines.append(line)
        y += lh
    tl.endLayout()
    w = min(math.ceil(widest), maxw)
    w, h = c.constrain(w, y)
    al = enum_val(align_, "start")
    fac = {"center": .5, "right": 1.0, "end": 1.0}.get(al, 0.0)
    shadows = style.get("shadows") if isinstance(style.get("shadows"), list) else []
    bg = color(style.get("backgroundColor"), ctx)

    def paint(p, b, ctx2, tl=tl, lines=lines):
        p.save()
        p.setFont(font)
        for i, ln in enumerate(lines):
            dx = (b.w - ln.naturalTextWidth()) * fac
            if bg is not None:
                p.fillRect(QRectF(dx, ln.position().y(), ln.naturalTextWidth(), fm.height()), bg)
            last = truncated and i == len(lines) - 1
            for s in shadows:
                if isinstance(s, dict):
                    sc = color(s.get("color"), ctx2, QColor(0, 0, 0, 80))
                    off = s.get("offset") or [0, 0]
                    p.setPen(sc)
                    if last:
                        p.drawText(QPointF(dx + num(off[0], 0.0), ln.position().y() + fm.ascent() + num(off[1], 0.0)),
                                   fm.elidedText(text[ln.textStart():], Qt.TextElideMode.ElideRight, b.w))
                    else:
                        ln.draw(p, QPointF(dx + num(off[0], 0.0), num(off[1], 0.0)))
            p.setPen(col)
            if last and overflow != "clip":
                p.drawText(QPointF(dx, ln.position().y() + fm.ascent()),
                           fm.elidedText(text[ln.textStart():], Qt.TextElideMode.ElideRight, b.w))
            else:
                ln.draw(p, QPointF(dx, 0))
        p.restore()
    box = Box(w, h, paint=paint)
    box.clip = "rect" if overflow in ("clip", "ellipsis", "fade") else None
    return box


@reg("Text", "SelectableText")
def _text(node, c, env, ctx):
    pr = props(node)
    data = pr.get("data", "")
    text = data if isinstance(data, str) else ("${…}" if M.is_code(data) else str(data))
    style = merge_style(env.style, pr.get("style"))
    ml = num(pr.get("maxLines"))
    return _text_box(text, style, c, ctx, pr.get("textAlign", ""), int(ml) if ml else None,
                     enum_val(pr.get("overflow")), pr.get("softWrap", True))


@reg("Icon")
def _icon(node, c, env, ctx):
    pr = props(node)
    s = num(pr.get("size"), env.icon_size)
    col = color(pr.get("color"), ctx, env.icon_color or ctx.scheme["onSurfaceVariant"])
    name = pr.get("icon", "Icons.star")
    name = name if isinstance(name, str) else "Icons.code"

    def paint(p, b, ctx2):
        iconfont.draw(p, QRectF((b.w - s) / 2, (b.h - s) / 2, s, s), name, col)
    return Box(*c.constrain(s, s), paint=paint)


@reg("Image")
def _image(node, c, env, ctx):
    pr = props(node)
    src = pr.get("src", "")
    src = src if isinstance(src, str) else ""
    source = "asset" if node.get("ctor") == "asset" else "network"
    img = ctx.images.get(source, src, ctx.folder) if ctx.images else None
    w, h = num(pr.get("width")), num(pr.get("height"))
    iw, ih = (img.width(), img.height()) if img is not None else (400.0, 300.0)
    cc = c.tighten(w=w, h=h)
    if cc.minW == cc.maxW and cc.minH == cc.maxH:
        bw, bh = cc.minW, cc.minH
    else:   # constrainSizeAndAttemptToPreserveAspectRatio
        bw, bh = iw, ih
        if bw > cc.maxW:
            bh, bw = bh * cc.maxW / bw, cc.maxW
        if bh > cc.maxH:
            bw, bh = bw * cc.maxH / bh, cc.maxH
        if bw < cc.minW:
            bh, bw = bh * cc.minW / max(bw, 1), cc.minW
        if bh < cc.minH:
            bw, bh = bw * cc.minH / max(bh, 1), cc.minH
        bw, bh = cc.constrain(bw, bh)
    fit = enum_val(pr.get("fit"), "")
    al = align(pr.get("alignment"), (0.0, 0.0))
    tint = color(pr.get("color"), ctx)

    def paint(p, b, ctx2):
        im = ctx2.images.get(source, src, ctx2.folder) if ctx2.images else None
        paint_image(p, QRectF(0, 0, b.w, b.h), im, fit or "scaleDown", al, tint=tint)
    return Box(bw, bh, paint=paint)


@reg("CircleAvatar")
def _avatar(node, c, env, ctx):
    pr = props(node)
    r = num(pr.get("radius"), 20.0)
    bg = color(pr.get("backgroundColor"), ctx, ctx.scheme["primaryContainer"])
    fg = color(pr.get("foregroundColor"), ctx, ctx.scheme["onPrimaryContainer"])
    img = pr.get("backgroundImage")
    d = 2 * r
    e2 = replace(env, style=merge_style(env.style, {"fontSize": 16, "color": "#%08X" % fg.rgba(),
                                                    "fontWeight": "FontWeight.w500"}), icon_color=fg)
    kid = slot(node, "child")
    kids = []
    if isinstance(kid, dict):
        b = layout_node(kid, C(0, d, 0, d), e2, ctx)
        kids.append(at(b, (d - b.w) / 2, (d - b.h) / 2))

    def paint(p, b, ctx2):
        path = rrect_path(QRectF(0, 0, d, d), None, True)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawPath(path)
        if isinstance(img, dict) and not M.is_code(img):
            q = ctx2.images.get(img.get("source", "asset"), img.get("src", ""), ctx2.folder) if ctx2.images else None
            paint_image(p, QRectF(0, 0, d, d), q, "cover", clip_path=path)
        p.restore()
    return Box(*c.constrain(d, d), kids, paint)


@reg("Divider", "VerticalDivider")
def _divider(node, c, env, ctx):
    pr = props(node)
    vert = node.get("type") == "VerticalDivider"
    ext = num(pr.get("width" if vert else "height"), 16.0)
    th = num(pr.get("thickness"), 1.0)
    ind, end = num(pr.get("indent"), 0.0), num(pr.get("endIndent"), 0.0)
    col = color(pr.get("color"), ctx, ctx.scheme["outlineVariant"])
    if vert:
        w, h = c.constrain(ext, c.maxH if c.maxH < INF else 0)
    else:
        w, h = c.constrain(c.maxW if c.maxW < INF else 0, ext)

    def paint(p, b, ctx2):
        if vert:
            p.fillRect(QRectF((b.w - th) / 2, ind, th, b.h - ind - end), col)
        else:
            p.fillRect(QRectF(ind, (b.h - th) / 2, b.w - ind - end, th), col)
    return Box(w, h, paint=paint)


@reg("Placeholder")
def _placeholder(node, c, env, ctx):
    pr = props(node)
    w = c.maxW if c.maxW < INF else num(pr.get("fallbackWidth"), 400.0)
    h = c.maxH if c.maxH < INF else num(pr.get("fallbackHeight"), 400.0)
    col = color(pr.get("color"), ctx, QColor("#FF455A64"))
    sw = num(pr.get("strokeWidth"), 2.0)

    def paint(p, b, ctx2):
        p.setPen(QPen(col, sw))
        r = QRectF(sw / 2, sw / 2, b.w - sw, b.h - sw)
        p.drawRect(r)
        p.drawLine(r.topLeft(), r.bottomRight())
        p.drawLine(r.topRight(), r.bottomLeft())
    return Box(*c.constrain(w, h), paint=paint)


@reg("FlutterLogo")
def _flutterlogo(node, c, env, ctx):
    s = num(props(node).get("size"), 24.0)

    def paint(p, b, ctx2):
        k = s / 24.0
        p.save()
        p.translate((b.w - s) / 2, (b.h - s) / 2)
        p.scale(k, k)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FF54C5F8"))
        top = QPainterPath()
        for x, y in ((14.5, 2), (19.5, 2), (8, 13.5), (5.5, 11)):
            top.lineTo(x, y) if top.elementCount() else top.moveTo(x, y)
        top.closeSubpath()
        p.drawPath(top)
        mid = QPainterPath()
        for x, y in ((14.5, 11), (19.5, 11), (13.2, 17.3), (10.7, 14.8)):
            mid.lineTo(x, y) if mid.elementCount() else mid.moveTo(x, y)
        mid.closeSubpath()
        p.drawPath(mid)
        p.setBrush(QColor("#FF01579B"))
        low = QPainterPath()
        for x, y in ((10.7, 19.8), (13.2, 17.3), (19.5, 23), (14.5, 23)):
            low.lineTo(x, y) if low.elementCount() else low.moveTo(x, y)
        low.closeSubpath()
        p.drawPath(low)
        p.setBrush(QColor("#FF29B6F6"))
        p.drawPolygon([QPointF(10.7, 14.8), QPointF(13.2, 17.3), QPointF(10.7, 19.8), QPointF(8.2, 17.3)])
        p.restore()
    return Box(*c.constrain(s, s), paint=paint)


@reg("CircularProgressIndicator")
def _cpi(node, c, env, ctx):
    pr = props(node)
    sw = num(pr.get("strokeWidth"), 4.0)
    col = color(pr.get("color"), ctx, ctx.scheme["primary"])
    v = num(pr.get("value"))

    def paint(p, b, ctx2):
        r = QRectF(sw / 2, sw / 2, b.w - sw, b.h - sw)
        bgc = color(pr.get("backgroundColor"), ctx2)
        if bgc is not None:
            p.setPen(QPen(bgc, sw))
            p.drawEllipse(r)
        p.setPen(QPen(col, sw, cap=Qt.PenCapStyle.RoundCap))
        span = (v if v is not None else 0.7) * 360
        p.drawArc(r, 90 * 16, int(-span * 16))
    return Box(*c.constrain(36, 36), paint=paint)


@reg("LinearProgressIndicator")
def _lpi(node, c, env, ctx):
    pr = props(node)
    h = num(pr.get("minHeight"), 4.0)
    col = color(pr.get("color"), ctx, ctx.scheme["primary"])
    bgc = color(pr.get("backgroundColor"), ctx, ctx.scheme["secondaryContainer"])
    v = num(pr.get("value"), 0.45)

    def paint(p, b, ctx2):
        p.fillRect(QRectF(0, 0, b.w, b.h), bgc)
        p.fillRect(QRectF(0, 0, b.w * max(0.0, min(1.0, v)), b.h), col)
    return Box(*c.constrain(c.maxW if c.maxW < INF else 200, h), paint=paint)


def _chip_like(node, c, env, ctx, label_slot="label"):
    pr = props(node)
    bg = color(pr.get("backgroundColor"), ctx)
    pad = edge(pr.get("padding")) if pr.get("padding") else (8.0, 0.0, 8.0, 0.0)
    e2 = replace(env, style=merge_style(merge_style(env.style, {"fontSize": 14, "fontWeight": "FontWeight.w500",
                                                                "color": "#%08X" % ctx.scheme["onSurfaceVariant"].rgba()}),
                                        pr.get("labelStyle")), icon_size=18,
                 icon_color=ctx.scheme["primary"])
    kids, x = [], pad[0]
    av = slot(node, "avatar")
    if isinstance(av, dict):
        b = layout_node(av, C(0, 24, 0, 24), e2, ctx)
        kids.append(at(b, x, 0))
        x += b.w + 8
    lb = slot(node, label_slot)
    if isinstance(lb, dict):
        b = layout_node(lb, C(0, c.maxW, 0, 32), e2, ctx)
        kids.append(at(b, x, 0))
        x += b.w
    dl = slot(node, "deleteIcon")
    if isinstance(dl, dict) or (node.get("events") or {}).get("onDeleted"):
        if isinstance(dl, dict):
            b = layout_node(dl, C(0, 18, 0, 18), e2, ctx)
            kids.append(at(b, x + 8, 0))
        x += 26
    w, h = c.constrain(x + pad[2], 32)
    for k in kids:
        k.y = (h - k.h) / 2

    def paint(p, b, ctx2):
        path = rrect_path(QRectF(0.5, 0.5, b.w - 1, b.h - 1), (8.0,) * 4)
        p.save()
        if bg is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawPath(path)
        else:
            p.setPen(QPen(ctx2.scheme["outlineVariant"], 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        p.restore()
    return Box(w, h, kids, paint)


@reg("Chip")
def _chip(node, c, env, ctx):
    return _chip_like(node, c, env, ctx)


@reg("Badge")
def _badge(node, c, env, ctx):
    pr = props(node)
    kid = slot(node, "child")
    b = layout_node(kid, c, env, ctx) if isinstance(kid, dict) else Box(0, 0)
    bg = color(pr.get("backgroundColor"), ctx, ctx.scheme["error"])
    fg = color(pr.get("textColor"), ctx, ctx.scheme["onError"])
    lab = slot(node, "label")
    kids = [at(b, 0, 0)]
    lw = 6.0
    if isinstance(lab, dict):
        e2 = replace(env, style=merge_style(env.style, {"fontSize": 11, "color": "#%08X" % fg.rgba(),
                                                        "fontWeight": "FontWeight.w500"}))
        lb = layout_node(lab, C(0, 60, 0, 16), e2, ctx)
        lw = max(16.0, lb.w + 8)
        kids.append(at(lb, b.w - lw / 2 + (lw - lb.w) / 2 - 4, -6 + (16 - lb.h) / 2))
    visible = pr.get("isLabelVisible", True) is not False

    def paint_badge(p, bb, ctx2):
        if not visible:
            return
        h = 16.0 if isinstance(lab, dict) else 6.0
        r = QRectF(b.w - lw / 2 - 4, -6 if h > 6 else -2, lw, h)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, h / 2, h / 2)
        p.restore()
    box = Box(b.w, b.h, kids)
    if len(kids) > 1:          # badge circle under the label, over the child
        holder = Box(b.w, b.h, [kids[1]], paint=paint_badge)
        box.kids = [kids[0], at(holder, 0, 0)]
    else:
        box.post = paint_badge
    return box


# ------------------------------------------------------------------------------ Input
def _field_box(node, c, env, ctx, dec: dict, obscure=False, cupertino=False) -> Box:
    sch = ctx.scheme
    w = c.maxW if c.maxW < INF else 220.0
    dense = dec.get("isDense") is True
    kind = dec.get("border") or "underline"
    filled = dec.get("filled") is True
    cp = edge(dec.get("contentPadding")) if dec.get("contentPadding") is not None else None
    style = merge_style(merge_style(env.style, {"fontSize": 16, "color": "#%08X" % sch["onSurface"].rgba()}),
                        props(node).get("style"))
    hint = dec.get("hintText") or dec.get("labelText") or ""
    hint_style = merge_style(style, {"color": "#%08X" % sch["onSurfaceVariant"].rgba()})
    if dec.get("hintText") and isinstance(dec.get("hintStyle"), dict):
        hint_style = merge_style(hint_style, dec["hintStyle"])
    elif not dec.get("hintText") and isinstance(dec.get("labelStyle"), dict):
        hint_style = merge_style(hint_style, dec["labelStyle"])
    font = make_font(hint_style, ctx)
    fm = QFontMetricsF(font)
    if cp is not None:
        h = cp[1] + cp[3] + fm.height()
    else:
        h = 48.0 if dense else 56.0
        if kind == "none" and not filled:
            h = 48.0 if not dense else 40.0
    lines = int(num(props(node).get("maxLines"), 1.0) or 1)
    if lines > 1:
        h += (lines - 1) * fm.height()
    h = max(h, fm.height() + 8)
    pre, suf = dec.get("prefixIcon"), dec.get("suffixIcon")
    w, h = c.constrain(w, h)
    rad = radii(dec.get("borderRadius")) or ((4.0,) * 4 if kind == "outline" else (4.0, 4.0, 0.0, 0.0) if filled
                                             else None)
    fill = color(dec.get("fillColor"), ctx, sch["surfaceContainerHighest"]) if filled else None
    bcol = color(dec.get("borderColor"), ctx, sch["outline"] if kind == "outline" else sch["onSurfaceVariant"])

    def paint(p, b, ctx2):
        r = QRectF(0, 0, b.w, b.h)
        p.save()
        if fill is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawPath(rrect_path(r, rad))
        if kind == "outline":
            p.setPen(QPen(bcol, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(rrect_path(r.adjusted(.5, .5, -.5, -.5), rad))
        elif kind == "underline":
            p.fillRect(QRectF(0, b.h - 1, b.w, 1), bcol)
        x0 = cp[0] if cp is not None else (12.0 if (kind == "outline" or filled) else 0.0)
        x1 = b.w - (cp[2] if cp is not None else (12.0 if (kind == "outline" or filled) else 0.0))
        ic = ctx2.scheme["onSurfaceVariant"]
        if isinstance(pre, str):
            iconfont.draw(p, QRectF(12, (b.h - 24) / 2, 24, 24), pre, ic)
            x0 = 52.0
        if isinstance(suf, str):
            iconfont.draw(p, QRectF(b.w - 36, (b.h - 24) / 2, 24, 24), suf, ic)
            x1 = b.w - 48.0
        if hint:
            p.setFont(font)
            p.setPen(color(hint_style.get("color"), ctx2, ic))
            ty = (b.h - fm.height()) / 2 if lines == 1 else (cp[1] if cp is not None else 16.0)
            p.drawText(QPointF(x0, ty + fm.ascent()),
                       fm.elidedText(("•" * 8) if obscure and not dec.get("hintText") else hint,
                                     Qt.TextElideMode.ElideRight, max(0.0, x1 - x0)))
        p.restore()
    return Box(w, h, paint=paint)


@reg("TextField", "TextFormField")
def _textfield(node, c, env, ctx):
    dec = props(node).get("decoration")
    dec = dec if isinstance(dec, dict) and not M.is_code(dec) else {}
    return _field_box(node, c, env, ctx, dec, props(node).get("obscureText") is True)


@reg("CupertinoTextField")
def _cuptf(node, c, env, ctx):
    pr = props(node)
    dec = {"hintText": pr.get("placeholder") or "", "border": "outline", "borderRadius": 5,
           "borderColor": "#33000000", "contentPadding": pr.get("padding") or {"all": 7},
           "filled": True, "fillColor": "#FFFFFFFF" if not ctx.dark else "#FF1C1C1E"}
    return _field_box(node, c, env, ctx, dec, pr.get("obscureText") is True, True)


@reg("Checkbox")
def _checkbox(node, c, env, ctx):
    pr = props(node)
    on = pr.get("value") is True
    act = color(pr.get("activeColor"), ctx, ctx.scheme["primary"])
    chk = color(pr.get("checkColor"), ctx, ctx.scheme["onPrimary"])

    def paint(p, b, ctx2):
        r = QRectF((b.w - 18) / 2, (b.h - 18) / 2, 18, 18)
        p.save()
        if on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(act)
            p.drawRoundedRect(r, 2, 2)
            p.setPen(QPen(chk, 2))
            p.drawPolyline([QPointF(r.x() + 4, r.y() + 9), QPointF(r.x() + 7.5, r.y() + 12.5),
                            QPointF(r.x() + 14, r.y() + 5.5)])
        else:
            p.setPen(QPen(ctx2.scheme["onSurfaceVariant"], 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 2, 2)
        p.restore()
    return Box(*c.constrain(48, 48), paint=paint)


def _switch_paint(on, track_on, thumb_on, ctx, cupertino=False):
    def paint(p, b, ctx2):
        sch = ctx2.scheme
        tw, th = (51.0, 31.0) if cupertino else (52.0, 32.0)
        r = QRectF((b.w - tw) / 2, (b.h - th) / 2, tw, th)
        p.save()
        if cupertino:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(track_on if on else QColor("#FFE9E9EA"))
            p.drawRoundedRect(r, th / 2, th / 2)
            d = th - 4
            x = r.right() - d - 2 if on else r.x() + 2
            p.setBrush(QColor("#FFFFFFFF"))
            p.drawEllipse(QRectF(x, r.y() + 2, d, d))
        elif on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(track_on)
            p.drawRoundedRect(r, th / 2, th / 2)
            p.setBrush(thumb_on)
            p.drawEllipse(QRectF(r.right() - 28, r.y() + 4, 24, 24))
        else:
            p.setPen(QPen(sch["outline"], 2))
            p.setBrush(sch["surfaceContainerHighest"])
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), th / 2 - 1, th / 2 - 1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(sch["outline"])
            p.drawEllipse(QRectF(r.x() + 8, r.y() + 8, 16, 16))
        p.restore()
    return paint


@reg("Switch")
def _switch(node, c, env, ctx):
    pr = props(node)
    on = pr.get("value") is True
    tr = color(pr.get("activeTrackColor"), ctx, ctx.scheme["primary"])
    th = color(pr.get("activeThumbColor"), ctx, ctx.scheme["onPrimary"])
    return Box(*c.constrain(60, 48), paint=_switch_paint(on, tr, th, ctx))


@reg("CupertinoSwitch")
def _cupswitch(node, c, env, ctx):
    pr = props(node)
    tr = color(pr.get("activeTrackColor"), ctx, QColor("#FF34C759"))
    return Box(*c.constrain(59, 39), paint=_switch_paint(pr.get("value") is True, tr, None, ctx, True))


@reg("Slider", "CupertinoSlider")
def _slider(node, c, env, ctx):
    pr = props(node)
    lo, hi = num(pr.get("min"), 0.0), num(pr.get("max"), 1.0)
    v = num(pr.get("value"), 0.5)
    f = 0.0 if hi == lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
    cup = node.get("type") == "CupertinoSlider"
    act = color(pr.get("activeColor"), ctx, QColor("#FF007AFF") if cup else ctx.scheme["primary"])
    ina = color(pr.get("inactiveColor"), ctx, QColor("#FFE5E5EA") if cup else ctx.scheme["secondaryContainer"])
    w = c.maxW if c.maxW < INF else 144.0

    def paint(p, b, ctx2):
        x0, x1 = 12.0, b.w - 12.0
        cy = b.h / 2
        xv = x0 + (x1 - x0) * f
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ina)
        p.drawRoundedRect(QRectF(x0, cy - 2, x1 - x0, 4), 2, 2)
        p.setBrush(act)
        p.drawRoundedRect(QRectF(x0, cy - 2, xv - x0, 4), 2, 2)
        if cup:
            p.setBrush(QColor("#FFFFFFFF"))
            p.setPen(QPen(QColor(0, 0, 0, 40), 1))
            p.drawEllipse(QPointF(xv, cy), 13, 13)
        else:
            p.drawEllipse(QPointF(xv, cy), 10, 10)
        p.restore()
    return Box(*c.constrain(w, 48), paint=paint)


@reg("DropdownButton")
def _dropdown(node, c, env, ctx):
    pr = props(node)
    text = pr.get("value") or pr.get("hint") or ((pr.get("items") or ["Choose"])[0] if isinstance(pr.get("items"), list)
                                                  else "Choose")
    style = merge_style(env.style, {"fontSize": 16})
    tb = _text_box(str(text), style, C(0, max(0.0, c.maxW - 24)), ctx,
                   color_default=ctx.scheme["onSurfaceVariant"] if not pr.get("value") else None)
    w = (c.maxW if c.maxW < INF else tb.w + 24) if pr.get("isExpanded") else tb.w + 24
    w, h = c.constrain(w, 48)

    def post(p, b, ctx2):
        iconfont.draw(p, QRectF(b.w - 24, (b.h - 24) / 2, 24, 24), "arrow_drop_down", ctx2.scheme["onSurfaceVariant"])
        p.fillRect(QRectF(0, b.h - 9, b.w, 1), ctx2.scheme["outlineVariant"])
    return Box(w, h, [at(tb, 0, (h - tb.h) / 2)], post=post)


def _list_tile(node, c, env, ctx, trailing_control: Box | None = None, leading_control: Box | None = None) -> Box:
    pr = props(node)
    sch = ctx.scheme
    w = c.maxW if c.maxW < INF else 300.0
    cp = edge(pr.get("contentPadding")) if pr.get("contentPadding") else (16.0, 0.0, 24.0, 0.0)
    dense = pr.get("dense") is True
    sub = slot(node, "subtitle")
    h = (64.0 if dense else 72.0) if sub else (48.0 if dense else 56.0)
    e_lead = replace(env, icon_color=sch["onSurfaceVariant"], icon_size=24)
    kids = []
    x = cp[0]
    lead = slot(node, "leading") or (slot(node, "secondary") if trailing_control is not None else None)
    if leading_control is not None:
        kids.append(leading_control)
        leading_control.x = x
        x += leading_control.w + 16
    elif isinstance(lead, dict):
        b = layout_node(lead, C(0, 56, 0, h), e_lead, ctx)
        kids.append(at(b, x, 0))
        x += b.w + 16
    right = w - cp[2]
    trail = slot(node, "trailing") or (slot(node, "secondary") if leading_control is not None else None)
    if trailing_control is not None:
        right -= trailing_control.w
        trailing_control.x = right
        kids.append(trailing_control)
        right -= 16
    elif isinstance(trail, dict):
        b = layout_node(trail, C(0, w / 2, 0, h), e_lead, ctx)
        right -= b.w
        kids.append(at(b, right, 0))
        right -= 16
    tw = max(0.0, right - x)
    sel = pr.get("selected") is True
    ts = merge_style(env.style, {"fontSize": 16, "color": "#%08X" % (sch["primary"] if sel else sch["onSurface"]).rgba()})
    ss = merge_style(env.style, {"fontSize": 14, "color": "#%08X" % sch["onSurfaceVariant"].rgba()})
    tbox = sbox = None
    title = slot(node, "title")
    if isinstance(title, dict):
        tbox = layout_node(title, C(0, tw, 0, h), replace(env, style=ts), ctx)
    if isinstance(sub, dict):
        sbox = layout_node(sub, C(0, tw, 0, h), replace(env, style=ss), ctx)
    th = (tbox.h if tbox else 0) + (sbox.h if sbox else 0)
    h = max(h, th + 16)
    y = (h - th) / 2
    if tbox:
        kids.append(at(tbox, x, y))
        y += tbox.h
    if sbox:
        kids.append(at(sbox, x, y))
    for k in kids:
        if k is not tbox and k is not sbox:
            k.y = (h - k.h) / 2
    w, h = c.constrain(w, h)
    tile = color(pr.get("tileColor"), ctx)

    def paint(p, b, ctx2):
        if tile is not None:
            p.fillRect(QRectF(0, 0, b.w, b.h), tile)
    return Box(w, h, kids, paint)


@reg("ListTile", "CupertinoListTile", "ExpansionTile")
def _listtile(node, c, env, ctx):
    if node.get("type") == "ExpansionTile":
        e_kids = []
        tb = _list_tile(node, c, env, ctx, trailing_control=_icon_box("expand_more", ctx.scheme["onSurfaceVariant"]))
        if props(node).get("initiallyExpanded") is True:
            y = tb.h
            box = Box(tb.w, tb.h, [at(tb, 0, 0)])
            for k in node.get("children") or []:
                b = layout_node(k, C(0, tb.w), env, ctx)
                e_kids.append(at(b, 0, y))
                y += b.h
            box.kids += e_kids
            box.h = y
            return box
        return tb
    return _list_tile(node, c, env, ctx)


def _icon_box(name: str, col: QColor, size=24.0, box=48.0) -> Box:
    def paint(p, b, ctx2):
        iconfont.draw(p, QRectF((b.w - size) / 2, (b.h - size) / 2, size, size), name, col)
    return Box(box, box, paint=paint)


@reg("CheckboxListTile", "SwitchListTile")
def _ctrl_tile(node, c, env, ctx):
    pr = props(node)
    on = pr.get("value") is True
    sch = ctx.scheme
    if node.get("type") == "CheckboxListTile":
        ctrl = _checkbox({"props": {"value": on, "activeColor": pr.get("activeColor")}}, C(0, 48, 0, 48), env, ctx)
    else:
        th = color(pr.get("activeThumbColor"), ctx, sch["onPrimary"])
        ctrl = Box(60, 48, paint=_switch_paint(on, sch["primary"], th, ctx))
    lead = enum_val(pr.get("controlAffinity"), "trailing" if node.get("type") == "SwitchListTile" else "platform")
    if lead == "leading":
        return _list_tile(node, c, env, ctx, leading_control=ctrl)
    return _list_tile(node, c, env, ctx, trailing_control=ctrl)


# ---------------------------------------------------------------------------- Buttons
_BTN_KIND = {"ElevatedButton": "elevated", "FilledButton": "filled", "TextButton": "text",
             "OutlinedButton": "outlined"}


def _button(node, c, env, ctx) -> Box:
    t = node.get("type")
    ctor = node.get("ctor") or ""
    kind = _BTN_KIND.get(t, "elevated")
    if t == "FilledButton" and ctor.startswith("tonal"):
        kind = "tonal"
    sch = ctx.scheme
    st = props(node).get("style")
    st = st if isinstance(st, dict) and not M.is_code(st) else {}
    bg_def = {"elevated": sch["surfaceContainerLow"], "filled": sch["primary"], "tonal": sch["secondaryContainer"],
              "text": None, "outlined": None}[kind]
    fg_def = {"elevated": sch["primary"], "filled": sch["onPrimary"], "tonal": sch["onSecondaryContainer"],
              "text": sch["primary"], "outlined": sch["primary"]}[kind]
    bg = color(st.get("backgroundColor"), ctx, bg_def)
    fg = color(st.get("foregroundColor"), ctx, fg_def)
    pad = edge(st.get("padding")) if st.get("padding") is not None else \
        ((12.0, 0.0, 12.0, 0.0) if kind == "text" else (24.0, 0.0, 24.0, 0.0))
    if ctor in ("icon", "tonalIcon") and st.get("padding") is None:
        pad = (16.0, 0.0, 24.0, 0.0) if kind != "text" else (12.0, 0.0, 16.0, 0.0)
    ms = st.get("minimumSize") if isinstance(st.get("minimumSize"), list) else [64, 40]
    minw, minh = num(ms[0], 64.0), num(ms[1] if len(ms) > 1 else 40, 40.0)
    elev = num(st.get("elevation"), 1.0 if kind == "elevated" else 0.0)
    shape = st.get("shape")
    side = st.get("side") if isinstance(st.get("side"), dict) else None
    tstyle = merge_style(merge_style(env.style, {"fontSize": 14, "fontWeight": "FontWeight.w500",
                                                 "color": "#%08X" % fg.rgba()}), st.get("textStyle"))
    tstyle["color"] = "#%08X" % fg.rgba() if not (isinstance(st.get("textStyle"), dict)
                                                  and st["textStyle"].get("color")) else tstyle["color"]
    e2 = replace(env, style=tstyle, icon_color=fg, icon_size=18)
    inner_c = C(0, max(0.0, c.maxW - pad[0] - pad[2]), 0, max(0.0, c.maxH - pad[1] - pad[3]))
    parts = []
    if ctor in ("icon", "tonalIcon"):
        ic, lb = slot(node, "icon"), slot(node, "label")
        if isinstance(ic, dict):
            parts.append(layout_node(ic, inner_c, e2, ctx))
        if isinstance(lb, dict):
            parts.append(layout_node(lb, inner_c, e2, ctx))
    else:
        ch = slot(node, "child")
        if isinstance(ch, dict):
            parts.append(layout_node(ch, inner_c, e2, ctx))
    cw = sum(b.w for b in parts) + 8 * max(0, len(parts) - 1)
    chh = max([b.h for b in parts] + [0.0])
    w, h = c.constrain(max(minw, cw + pad[0] + pad[2]), max(minh, chh + pad[1] + pad[3]))
    x = (w - cw) / 2
    for b in parts:
        at(b, x, (h - b.h) / 2)
        x += b.w + 8

    def paint(p, b, ctx2):
        r = QRectF(0, 0, b.w, b.h)
        path = shape_path(shape, r, (b.h / 2,) * 4)
        p.save()
        if elev > 0 and bg is not None:
            drop_shadow(p, path, QColor(0, 0, 0, 50), elev * 1.5, 0, 0, elev * .7)
        if bg is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawPath(path)
        sd = shape_side(shape, ctx2)
        if side is not None:
            sd = (color(side.get("color"), ctx2, ctx2.scheme["outline"]), num(side.get("width"), 1.0))
        if kind == "outlined" and sd is None:
            sd = (ctx2.scheme["outline"], 1.0)
        if sd is not None:
            p.setPen(QPen(sd[0], sd[1]))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(shape_path(shape, r.adjusted(sd[1] / 2, sd[1] / 2, -sd[1] / 2, -sd[1] / 2),
                                  ((b.h - sd[1]) / 2,) * 4))
        p.restore()
    return Box(w, h, parts, paint)


reg("ElevatedButton", "FilledButton", "TextButton", "OutlinedButton")(_button)


@reg("IconButton")
def _iconbutton(node, c, env, ctx):
    pr = props(node)
    sch = ctx.scheme
    ctor = node.get("ctor") or ""
    s = num(pr.get("iconSize"), 24.0)
    fg = {"filled": sch["onPrimary"], "filledTonal": sch["onSecondaryContainer"]}.get(ctor, sch["onSurfaceVariant"])
    fg = color(pr.get("color"), ctx, fg)
    bg = {"filled": sch["primary"], "filledTonal": sch["secondaryContainer"]}.get(ctor)
    pad = edge(pr.get("padding")) if pr.get("padding") is not None else (8.0,) * 4
    e2 = replace(env, icon_color=fg, icon_size=s)
    ic = slot(node, "icon")
    b = layout_node(ic, C(0, s, 0, s), e2, ctx) if isinstance(ic, dict) else Box(s, s)
    w, h = c.constrain(max(48.0, s + pad[0] + pad[2]), max(48.0, s + pad[1] + pad[3]))
    at(b, (w - b.w) / 2, (h - b.h) / 2)

    def paint(p, bb, ctx2):
        if bg is not None or ctor == "outlined":
            d = min(40.0, bb.w, bb.h)
            r = QRectF((bb.w - d) / 2, (bb.h - d) / 2, d, d)
            p.save()
            if bg is not None:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(bg)
            else:
                p.setPen(QPen(ctx2.scheme["outline"], 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(r)
            p.restore()
    return Box(w, h, [b], paint)


@reg("MaterialButton")
def _matbutton(node, c, env, ctx):
    pr = props(node)
    bg = color(pr.get("color"), ctx)
    fg = color(pr.get("textColor"), ctx, ctx.scheme["onSurface"] if bg is None else QColor("#FF000000"))
    pad = edge(pr.get("padding")) if pr.get("padding") is not None else (16.0, 0.0, 16.0, 0.0)
    minw, hh = num(pr.get("minWidth"), 88.0), num(pr.get("height"), 36.0)
    elev = num(pr.get("elevation"), 2.0 if bg is not None else 0.0)
    shape = pr.get("shape")
    e2 = replace(env, style=merge_style(env.style, {"fontSize": 14, "fontWeight": "FontWeight.w500",
                                                    "color": "#%08X" % fg.rgba()}), icon_color=fg)
    ch = slot(node, "child")
    b = layout_node(ch, C(0, max(0.0, c.maxW - pad[0] - pad[2]), 0, c.maxH), e2, ctx) if isinstance(ch, dict) \
        else Box(0, 0)
    w, h = c.constrain(max(minw, b.w + pad[0] + pad[2]), max(hh, b.h + pad[1] + pad[3]))
    at(b, (w - b.w) / 2, (h - b.h) / 2)

    def paint(p, bb, ctx2):
        r = QRectF(0, 0, bb.w, bb.h)
        path = shape_path(shape, r, 2.0)
        p.save()
        if elev > 0 and bg is not None:
            drop_shadow(p, path, QColor(0, 0, 0, 50), elev * 1.5, 0, 0, elev * .7)
        if bg is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawPath(path)
        sd = shape_side(shape, ctx2)
        if sd is not None:
            p.setPen(QPen(sd[0], sd[1]))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        p.restore()
    return Box(w, h, [b], paint)


@reg("FloatingActionButton")
def _fab(node, c, env, ctx):
    pr = props(node)
    sch = ctx.scheme
    bg = color(pr.get("backgroundColor"), ctx, sch["primaryContainer"])
    fg = color(pr.get("foregroundColor"), ctx, sch["onPrimaryContainer"])
    e2 = replace(env, style=merge_style(env.style, {"fontSize": 14, "fontWeight": "FontWeight.w500",
                                                    "color": "#%08X" % fg.rgba()}), icon_color=fg, icon_size=24)
    shape = pr.get("shape")
    kids = []
    if node.get("ctor") == "extended":
        parts = [layout_node(slot(node, k), C(0, 300, 0, 56), e2, ctx) for k in ("icon", "label")
                 if isinstance(slot(node, k), dict)]
        cw = sum(b.w for b in parts) + 8 * max(0, len(parts) - 1)
        w, h = cw + 32, 56.0
        x = 16.0
        for b in parts:
            kids.append(at(b, x, (h - b.h) / 2))
            x += b.w + 8
    else:
        s = 40.0 if pr.get("mini") is True else 56.0
        w = h = s
        ch = slot(node, "child")
        if isinstance(ch, dict):
            b = layout_node(ch, C(0, s, 0, s), e2, ctx)
            kids.append(at(b, (s - b.w) / 2, (s - b.h) / 2))
    rad = 12.0 if pr.get("mini") is True else 16.0

    def paint(p, bb, ctx2):
        path = shape_path(shape, QRectF(0, 0, bb.w, bb.h), rad)
        p.save()
        drop_shadow(p, path, QColor(0, 0, 0, 45), 6, 0, 0, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawPath(path)
        p.restore()
    return Box(*c.constrain(w, h), kids, paint)


@reg("CupertinoButton")
def _cupbutton(node, c, env, ctx):
    pr = props(node)
    filled = node.get("ctor") == "filled"
    bg = QColor("#FF007AFF") if filled else color(pr.get("color"), ctx)
    fg = QColor("#FFFFFFFF") if (filled or bg is not None) else QColor("#FF007AFF")
    pad = edge(pr.get("padding")) if pr.get("padding") is not None else (16.0, 14.0, 16.0, 14.0)
    e2 = replace(env, style=merge_style(env.style, {"fontSize": 17, "color": "#%08X" % fg.rgba()}), icon_color=fg)
    ch = slot(node, "child")
    b = layout_node(ch, C(0, max(0.0, c.maxW - pad[0] - pad[2])), e2, ctx) if isinstance(ch, dict) else Box(0, 0)
    w, h = c.constrain(b.w + pad[0] + pad[2], max(44.0, b.h + pad[1] + pad[3]))
    at(b, (w - b.w) / 2, (h - b.h) / 2)

    def paint(p, bb, ctx2):
        if bg is not None:
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(QRectF(0, 0, bb.w, bb.h), 8, 8)
            p.restore()
    return Box(w, h, [b], paint)


# --------------------------------------------------------------------------- Material
@reg("Card")
def _card(node, c, env, ctx):
    pr = props(node)
    m = edge(pr.get("margin")) if pr.get("margin") is not None else (4.0,) * 4
    bg = color(pr.get("color"), ctx, ctx.scheme["surfaceContainerLow"])
    elev = num(pr.get("elevation"), 1.0)
    shape = pr.get("shape")
    shadow = color(pr.get("shadowColor"), ctx, QColor(0, 0, 0, 255))
    kid = slot(node, "child")
    cc = c.deflate(*m)
    b = layout_node(kid, cc, env, ctx) if isinstance(kid, dict) else Box(*cc.constrain(0, 0))
    w, h = b.w, b.h

    def paint(p, bb, ctx2):
        r = QRectF(m[0], m[1], w, h)
        path = shape_path(shape, r, 12.0)
        p.save()
        if elev > 0:
            sc = QColor(shadow)
            sc.setAlpha(min(255, int(30 + elev * 6)))
            drop_shadow(p, path, sc, elev * 2.0, 0, 0, elev * .8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawPath(path)
        sd = shape_side(shape, ctx2)
        if sd is not None:
            p.setPen(QPen(sd[0], sd[1]))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        p.restore()
    box = Box(w + m[0] + m[2], h + m[1] + m[3], [at(b, m[0], m[1])], paint)
    if enum_val(pr.get("clipBehavior"), "none") != "none":
        box.clip = shape_path(shape, QRectF(m[0], m[1], w, h), 12.0)
    return box


@reg("Material")
def _material(node, c, env, ctx):
    pr = props(node)
    b = passthrough(slot(node, "child"), c, env, ctx)
    bg = color(pr.get("color"), ctx)
    rad = radii(pr.get("borderRadius"))
    elev = num(pr.get("elevation"), 0.0)

    def paint(p, bb, ctx2):
        path = rrect_path(QRectF(0, 0, bb.w, bb.h), rad)
        p.save()
        if elev > 0:
            drop_shadow(p, path, QColor(0, 0, 0, 50), elev * 2, 0, 0, elev * .7)
        if bg is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawPath(path)
        p.restore()
    b.paint = paint
    return b


@reg("DecoratedBox")
def _decorated(node, c, env, ctx):
    b = passthrough(slot(node, "child"), c, env, ctx)
    dec = props(node).get("decoration")
    b.paint = lambda p, bb, ctx2: paint_decoration(p, QRectF(0, 0, bb.w, bb.h), dec, ctx2)
    return b


@reg("Opacity", "AnimatedOpacity")
def _opacity(node, c, env, ctx):
    b = passthrough(slot(node, "child"), c, env, ctx)
    b.opacity = max(0.0, min(1.0, num(props(node).get("opacity"), 1.0)))
    return b


@reg("ClipRRect")
def _cliprrect(node, c, env, ctx):
    b = passthrough(slot(node, "child"), c, env, ctx)
    b.clip = rrect_path(QRectF(0, 0, b.w, b.h), radii(props(node).get("borderRadius", 12)) or (0.0,) * 4)
    return b


@reg("ClipOval")
def _clipoval(node, c, env, ctx):
    b = passthrough(slot(node, "child"), c, env, ctx)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, b.w, b.h))
    b.clip = path
    return b


# ------------------------------------------------------------------------- Navigation
@reg("AppBar")
def _appbar(node, c, env, ctx):
    pr = props(node)
    sch = ctx.scheme
    th = num(pr.get("toolbarHeight"), 56.0)
    bg = color(pr.get("backgroundColor"), ctx, sch["surface"])
    fg = color(pr.get("foregroundColor"), ctx, sch["onSurface"])
    w = c.maxW if c.maxW < INF else 360.0
    top = env.pad_top
    bottom = slot(node, "bottom")
    e2 = replace(env, style=merge_style(env.style, {"fontSize": 22, "color": "#%08X" % fg.rgba()}),
                 icon_color=fg, icon_size=24, pad_top=0.0)
    kids = []
    bot_box = None
    if isinstance(bottom, dict):
        bot_box = layout_node(bottom, C(w, w, 0, 100), e2, ctx)
    h = top + th + (bot_box.h if bot_box else 0.0)
    fs = slot(node, "flexibleSpace")
    if isinstance(fs, dict):
        kids.append(at(layout_node(fs, C.tight(w, h), e2, ctx), 0, 0))
    x = 16.0
    lead = slot(node, "leading")
    if isinstance(lead, dict):
        b = layout_node(lead, C(0, 56, 0, th), e2, ctx)
        kids.append(at(b, (56 - b.w) / 2, top + (th - b.h) / 2))
        x = 72.0
    right = w - 4.0
    acts = slot(node, "actions")
    act_boxes = []
    if isinstance(acts, list):
        for a in reversed(acts):
            b = layout_node(a, C(0, w / 2, 0, th), e2, ctx)
            right -= b.w
            act_boxes.insert(0, at(b, right, top + (th - b.h) / 2))
    title = slot(node, "title")
    if isinstance(title, dict):
        tb = layout_node(title, C(0, max(0.0, right - x - 16)), e2, ctx)
        tx = (w - tb.w) / 2 if pr.get("centerTitle") is True else x
        kids.append(at(tb, tx, top + (th - tb.h) / 2))
    kids += act_boxes
    if bot_box is not None:
        kids.append(at(bot_box, 0, top + th))
    elev = num(pr.get("elevation"), 0.0)

    def paint(p, b, ctx2):
        if elev > 0:
            drop_shadow(p, rrect_path(QRectF(0, 0, b.w, b.h), None), QColor(0, 0, 0, 50), elev * 2, 0, 0, elev)
        p.fillRect(QRectF(0, 0, b.w, b.h), bg)
    return Box(w, h, kids, paint)


@reg("BottomNavigationBar", "NavigationBar")
def _bottomnav(node, c, env, ctx):
    pr = props(node)
    sch = ctx.scheme
    m3 = node.get("type") == "NavigationBar"
    items = pr.get("destinations" if m3 else "items")
    items = [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []
    cur = int(num(pr.get("selectedIndex" if m3 else "currentIndex"), 0.0))
    w = c.maxW if c.maxW < INF else 360.0
    bar_h = 80.0 if m3 else 56.0
    h = bar_h + env.pad_bottom
    bg = color(pr.get("backgroundColor"), ctx, sch["surfaceContainer"] if m3 else sch["surface"])
    sel = color(pr.get("selectedItemColor"), ctx, sch["onSecondaryContainer"] if m3 else sch["primary"])
    uns = color(pr.get("unselectedItemColor"), ctx, sch["onSurfaceVariant"])
    ind = color(pr.get("indicatorColor"), ctx, sch["secondaryContainer"])
    isz = num(pr.get("iconSize"), 24.0)
    show_uns = pr.get("showUnselectedLabels") is not False or m3
    font_family = ctx.font_family

    def paint(p, b, ctx2):
        p.fillRect(QRectF(0, 0, b.w, b.h), bg)
        if not m3:
            drop_shadow(p, rrect_path(QRectF(0, 0, b.w, 1), None), QColor(0, 0, 0, 40), 4, 0, 0, -1)
            p.fillRect(QRectF(0, 0, b.w, b.h), bg)
        n = max(1, len(items))
        cw = b.w / n
        f = QFont(font_family)
        for i, it in enumerate(items):
            on = i == cur
            cx = cw * i + cw / 2
            col = sel if on else uns
            if m3:
                if on:
                    p.save()
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(ind)
                    p.drawRoundedRect(QRectF(cx - 32, 12, 64, 32), 16, 16)
                    p.restore()
                ic = it.get("activeIcon") if on and it.get("activeIcon") else it.get("icon", "Icons.circle")
                iconfont.draw(p, QRectF(cx - 12, 16, 24, 24), ic if isinstance(ic, str) else "Icons.circle",
                              col if on else uns)
                f.setPixelSize(int(12 * ctx2.text_scale))
                f.setWeight(QFont.Weight.Medium if on else QFont.Weight.Normal)
                p.setFont(f)
                p.setPen(sch["onSurface"] if on else uns)
                p.drawText(QRectF(cw * i, 48, cw, 20), int(Qt.AlignmentFlag.AlignCenter), str(it.get("label", "")))
            else:
                ic = it.get("activeIcon") if on and it.get("activeIcon") else it.get("icon", "Icons.circle")
                lab = str(it.get("label", ""))
                iy = 8.0 if (lab and (on or show_uns)) else (bar_h - isz) / 2
                iconfont.draw(p, QRectF(cx - isz / 2, iy, isz, isz), ic if isinstance(ic, str) else "Icons.circle",
                              col)
                if lab and (on or show_uns):
                    f.setPixelSize(int((14 if on else 12) * ctx2.text_scale))
                    p.setFont(f)
                    p.setPen(col)
                    p.drawText(QRectF(cw * i, iy + isz, cw, bar_h - iy - isz - 4), int(Qt.AlignmentFlag.AlignCenter),
                               lab)
    return Box(*c.constrain(w, h), paint=paint)


@reg("TabBar")
def _tabbar(node, c, env, ctx):
    pr = props(node)
    sch = ctx.scheme
    tabs = [t for t in node.get("children") or [] if isinstance(t, dict)]
    w = c.maxW if c.maxW < INF else 360.0
    lab = color(pr.get("labelColor"), ctx, sch["primary"])
    uns = color(pr.get("unselectedLabelColor"), ctx, sch["onSurfaceVariant"])
    indc = color(pr.get("indicatorColor"), ctx, sch["primary"])
    n = max(1, len(tabs))
    has_icon = any(isinstance(slot(t, "icon"), dict) and props(t).get("text") for t in tabs)
    h = 72.0 if has_icon else 48.0
    boxes = []
    scrollable = pr.get("isScrollable") is True
    x = 0.0
    for i, t in enumerate(tabs):
        col = lab if i == 0 else uns
        e2 = replace(env, style=merge_style(env.style, {"fontSize": 14, "fontWeight": "FontWeight.w500",
                                                        "color": "#%08X" % col.rgba()}), icon_color=col)
        tw = None if scrollable else w / n
        b = layout_node(t, C(tw or 0, tw or INF, h, h), e2, ctx)
        boxes.append(at(b, x, 0))
        x += b.w
    first = boxes[0] if boxes else None
    label_size = enum_val(pr.get("indicatorSize"), "label") == "label"

    def post(p, bb, ctx2):
        p.fillRect(QRectF(0, bb.h - 1, bb.w, 1), ctx2.scheme["surfaceContainerHighest"])
        if first is not None:
            iw = first.w if not label_size else min(first.w, max(32.0, first.w * .5))
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(indc)
            p.drawRoundedRect(QRectF(first.x + (first.w - iw) / 2, bb.h - 3, iw, 3), 1.5, 1.5)
            p.restore()
    return Box(*c.constrain(w if not scrollable else x, h), boxes, post=post)


@reg("Tab")
def _tab(node, c, env, ctx):
    pr = props(node)
    parts = []
    ic = slot(node, "icon")
    if isinstance(ic, dict):
        parts.append(layout_node(ic, C(0, c.maxW, 0, 24), env, ctx))
    ch = slot(node, "child")
    if isinstance(ch, dict):
        parts.append(layout_node(ch, C(0, c.maxW, 0, c.maxH), env, ctx))
    elif pr.get("text"):
        parts.append(_text_box(str(pr.get("text")), env.style, C(0, c.maxW), ctx))
    th = sum(b.h for b in parts) + 2 * max(0, len(parts) - 1)
    cw = max([b.w for b in parts] + [0.0])
    w, h = c.constrain(cw + 32, num(pr.get("height"), th + 24))
    y = (h - th) / 2
    for b in parts:
        at(b, (w - b.w) / 2, y)
        y += b.h + 2
    return Box(w, h, parts)


@reg("Drawer")
def _drawer(node, c, env, ctx):
    pr = props(node)
    w = num(pr.get("width"), 304.0)
    h = c.maxH if c.maxH < INF else 600.0
    bg = color(pr.get("backgroundColor"), ctx, ctx.scheme["surfaceContainerLow"])
    kid = slot(node, "child")
    kids = [at(layout_node(kid, C.tight(w, h), env, ctx), 0, 0)] if isinstance(kid, dict) else []

    def paint(p, b, ctx2):
        path = rrect_path(QRectF(0, 0, b.w, b.h), (0.0, 16.0, 16.0, 0.0))
        p.save()
        drop_shadow(p, path, QColor(0, 0, 0, 60), 10, 0, 2, 0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawPath(path)
        p.restore()
    box = Box(w, h, kids, paint)
    box.clip = rrect_path(QRectF(0, 0, w, h), (0.0, 16.0, 16.0, 0.0))
    return box


@reg("DrawerHeader")
def _drawerheader(node, c, env, ctx):
    pr = props(node)
    pad = edge(pr.get("padding")) if pr.get("padding") is not None else (16.0, 16.0, 16.0, 8.0)
    mar = edge(pr.get("margin")) if pr.get("margin") is not None else (0.0, 0.0, 0.0, 8.0)
    w = c.maxW if c.maxW < INF else 304.0
    h = 160.0 + env.pad_top
    kid = slot(node, "child")
    inner = C.tight(w - pad[0] - pad[2] - mar[0] - mar[2], h - pad[1] - pad[3] - mar[1] - mar[3])
    e2 = replace(env, style=merge_style(env.style, {"fontSize": 16}))
    kids = []
    if isinstance(kid, dict):
        b = layout_node(kid, inner.loosen(), e2, ctx)
        kids.append(at(b, mar[0] + pad[0], mar[1] + pad[1] + inner.maxH - b.h))
    dec = pr.get("decoration")

    def paint(p, bb, ctx2):
        r = QRectF(mar[0], mar[1], bb.w - mar[0] - mar[2], bb.h - mar[1] - mar[3] - 1)
        if isinstance(dec, dict):
            paint_decoration(p, r, dec, ctx2)
        p.fillRect(QRectF(0, bb.h - mar[3] - 1, bb.w, 1), ctx2.scheme["outlineVariant"])
    return Box(*c.constrain(w, h + mar[1] + mar[3]), kids, paint)


# ----------------------------------------------------------------------------- Cupertino
@reg("CupertinoNavigationBar")
def _cupnav(node, c, env, ctx):
    w = c.maxW if c.maxW < INF else 360.0
    top = env.pad_top
    h = top + 44.0
    bg = color(props(node).get("backgroundColor"), ctx, QColor("#F0F9F9F9") if not ctx.dark else QColor("#F01D1D1D"))
    e2 = replace(env, style=merge_style(env.style, {"fontSize": 17, "fontWeight": "FontWeight.w600",
                                                    "color": "#FF000000" if not ctx.dark else "#FFFFFFFF"}),
                 icon_color=QColor("#FF007AFF"), pad_top=0.0)
    kids = []
    mid = slot(node, "middle")
    if isinstance(mid, dict):
        b = layout_node(mid, C(0, w * .6, 0, 44), e2, ctx)
        kids.append(at(b, (w - b.w) / 2, top + (44 - b.h) / 2))
    for k, left in (("leading", True), ("trailing", False)):
        s = slot(node, k)
        if isinstance(s, dict):
            b = layout_node(s, C(0, w * .3, 0, 44), replace(e2, style=merge_style(e2.style, {
                "fontWeight": "FontWeight.normal", "color": "#FF007AFF"})), ctx)
            kids.append(at(b, 16 if left else w - 16 - b.w, top + (44 - b.h) / 2))

    def paint(p, b, ctx2):
        p.fillRect(QRectF(0, 0, b.w, b.h), bg)
        p.fillRect(QRectF(0, b.h - .5, b.w, .5), QColor(0, 0, 0, 77))
    return Box(w, h, kids, paint)


@reg("CupertinoPageScaffold")
def _cupscaffold(node, c, env, ctx):
    w, h = c.biggest
    bg = color(props(node).get("backgroundColor"), ctx, QColor("#FFFFFFFF") if not ctx.dark else QColor("#FF000000"))
    kids = []
    top = 0.0
    nav = slot(node, "navigationBar")
    if isinstance(nav, dict):
        nb = layout_node(nav, C(w, w, 0, h), env, ctx)
        top = nb.h
        navbox = nb
    else:
        navbox = None
    ch = slot(node, "child")
    if isinstance(ch, dict):
        e2 = replace(env, pad_top=0.0 if navbox is not None else env.pad_top,
                     style=merge_style(env.style, {"fontSize": 17,
                                                   "color": "#FF000000" if not ctx.dark else "#FFFFFFFF"}))
        b = layout_node(ch, C(w, w, max(0.0, h - top), max(0.0, h - top)), e2, ctx)
        kids.append(at(b, 0, top))
    if navbox is not None:
        kids.append(at(navbox, 0, 0))

    def paint(p, b, ctx2):
        p.fillRect(QRectF(0, 0, b.w, b.h), bg)
    return Box(w, h, kids, paint)


@reg("CupertinoActivityIndicator")
def _cupspin(node, c, env, ctx):
    pr = props(node)
    r = num(pr.get("radius"), 10.0)
    col = color(pr.get("color"), ctx, QColor("#FF8E8E93"))

    def paint(p, b, ctx2):
        p.save()
        p.translate(b.w / 2, b.h / 2)
        for i in range(8):
            cc = QColor(col)
            cc.setAlphaF(0.25 + 0.75 * i / 7)
            p.setPen(QPen(cc, r * .25, cap=Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(0, -r * .5), QPointF(0, -r))
            p.rotate(45)
        p.restore()
    return Box(*c.constrain(2 * r, 2 * r), paint=paint)


# ---------------------------------------------------------------------------- Special
@reg("Code")
def _code(node, c, env, ctx):
    kid = first_child(node)
    if kid is not None:
        b = layout_node(kid, c.deflate(2, 2, 2, 2), env, ctx)
        w, h = c.constrain(b.w + 4, b.h + 4)
        kids = [at(b, 2, 2)]
    else:
        w, h = c.constrain(min(c.maxW, 160.0), min(c.maxH, 40.0))
        kids = []
    code = str(props(node).get("code", ""))

    def post(p, bb, ctx2):
        p.save()
        p.setPen(QPen(QColor("#FF8E24AA"), 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(.5, .5, bb.w - 1, bb.h - 1))
        if not kids:
            f = QFont("Consolas")
            f.setPixelSize(11)
            p.setFont(f)
            p.drawText(QRectF(4, 0, bb.w - 8, bb.h), int(Qt.AlignmentFlag.AlignVCenter),
                       QFontMetricsF(f).elidedText(code.split("\n")[0], Qt.TextElideMode.ElideRight, bb.w - 8))
        p.restore()
    return Box(w, h, kids, post=post)


# ---------------------------------------------------------------------------- Scaffold
@reg("Scaffold")
def _scaffold(node, c, env, ctx):
    pr = props(node)
    sch = ctx.scheme
    w, h = c.biggest
    theme_bg = None
    th = (ctx.screen.data.get("theme") or {}) if ctx.screen is not None else {}
    if th.get("background"):
        theme_bg = color(th.get("background"), ctx)
    bg = color(pr.get("backgroundColor"), ctx, theme_bg or sch["surface"])
    kids = []
    app = slot(node, "appBar")
    app_box = None
    if isinstance(app, dict):
        app_box = layout_node(app, C(w, w, 0, h), env, ctx)
    bot = slot(node, "bottomNavigationBar")
    bot_box = layout_node(bot, C(w, w, 0, h), env, ctx) if isinstance(bot, dict) else None
    top = app_box.h if app_box else 0.0
    bottom = bot_box.h if bot_box else 0.0
    behind = pr.get("extendBodyBehindAppBar") is True
    body = slot(node, "body")
    body_top = 0.0 if behind else top
    body_bottom = 0.0 if pr.get("extendBody") is True else bottom
    if isinstance(body, dict):
        e2 = replace(env, pad_top=env.pad_top if (app_box is None or behind) else 0.0,
                     pad_bottom=env.pad_bottom if bot_box is None else 0.0)
        bh = max(0.0, h - body_top - body_bottom)
        b = layout_node(body, C(w, w, 0, bh), e2, ctx)
        kids.append(at(b, 0, body_top))
    sheet = slot(node, "bottomSheet")
    if isinstance(sheet, dict):
        sb = layout_node(sheet, C(w, w, 0, h / 2), env, ctx)
        kids.append(at(sb, 0, h - bottom - sb.h))
    pfb = slot(node, "persistentFooterButtons")
    if isinstance(pfb, list) and pfb:
        x = w - 8
        row = []
        for f in reversed(pfb):
            fb = layout_node(f, C(0, w), env, ctx)
            x -= fb.w
            row.append(at(fb, x, h - bottom - fb.h - 8))
            x -= 8
        kids += row
    if app_box is not None:
        kids.append(at(app_box, 0, 0))
    if bot_box is not None:
        kids.append(at(bot_box, 0, h - bottom))
    fab = slot(node, "floatingActionButton")
    if isinstance(fab, dict):
        fb = layout_node(fab, C(0, w, 0, h), env, ctx)
        loc = enum_val(pr.get("floatingActionButtonLocation"), "endFloat")
        x = w - fb.w - 16 if loc.startswith("end") else ((w - fb.w) / 2 if loc.startswith("center") else 16)
        if loc.endswith("Docked"):
            y = h - bottom - fb.h / 2
        elif loc.endswith("Top"):
            y = top - fb.h / 2
        else:
            y = h - bottom - fb.h - 16 - (env.pad_bottom if bot_box is None else 0.0)
        kids.append(at(fb, x, y))
    for which in ("drawer", "endDrawer"):
        dr = slot(node, which)
        if isinstance(dr, dict) and ctx.show_drawer == which:
            scrim = Box(w, h, paint=lambda p, b, c2: p.fillRect(QRectF(0, 0, b.w, b.h), QColor(0, 0, 0, 82)))
            kids.append(at(scrim, 0, 0))
            db = layout_node(dr, C(0, w, h, h), env, ctx)
            kids.append(at(db, 0 if which == "drawer" else w - db.w, 0))

    def paint(p, b, ctx2):
        p.fillRect(QRectF(0, 0, b.w, b.h), bg)
    return Box(w, h, kids, paint)


# ---------------------------------------------------------------------------- Animation / motion widgets
reg("AnimatedPadding")(_padding)
reg("AnimatedAlign")(_align)
reg("AnimatedSize", "AnimatedPositioned")(_pass)


def _xform_box(node, c, env, ctx, scale=1.0, turns=0.0, slide=(0.0, 0.0), al_key="alignment") -> Box:
    b = passthrough(slot(node, "child"), c, env, ctx)
    ax, ay = align(props(node).get(al_key), (0.0, 0.0))
    ox, oy = b.w * (ax + 1) / 2, b.h * (ay + 1) / 2
    t = QTransform()
    t.translate(slide[0] * b.w, slide[1] * b.h)
    t.translate(ox, oy)
    if turns:
        t.rotateRadians(turns * 2 * math.pi)
    if scale != 1:
        t.scale(scale, scale)
    t.translate(-ox, -oy)
    if not t.isIdentity():
        b.xform = t
    return b


def _pair(v, default=(0.0, 0.0)):
    return (num(v[0], 0.0), num(v[1], 0.0)) if isinstance(v, (list, tuple)) and len(v) == 2 else default


@reg("AnimatedScale", "ScaleTransition")
def _anim_scale(node, c, env, ctx):
    return _xform_box(node, c, env, ctx, scale=num(props(node).get("scale"), 1.0))


@reg("AnimatedRotation", "RotationTransition")
def _anim_rotation(node, c, env, ctx):
    return _xform_box(node, c, env, ctx, turns=num(props(node).get("turns"), 0.0))


@reg("AnimatedSlide", "SlideTransition")
def _anim_slide(node, c, env, ctx):
    pr = props(node)
    return _xform_box(node, c, env, ctx, slide=_pair(pr.get("offset", pr.get("position"))))


@reg("FadeTransition")
def _fade_transition(node, c, env, ctx):
    b = passthrough(slot(node, "child"), c, env, ctx)
    b.opacity = max(0.0, min(1.0, num(props(node).get("opacity"), 1.0)))
    return b


@reg("SizeTransition")
def _size_transition(node, c, env, ctx):
    b = passthrough(slot(node, "child"), c, env, ctx)
    f = max(0.0, min(1.0, num(props(node).get("sizeFactor"), 1.0)))
    if enum_val(props(node).get("axis"), "vertical") == "horizontal":
        b.w *= f
    else:
        b.h *= f
    b.clip = "rect"
    return b


@reg("AnimatedDefaultTextStyle")
def _anim_text_style(node, c, env, ctx):
    st = props(node).get("style")
    e2 = replace(env, style=merge_style(env.style, st)) if isinstance(st, dict) else env
    return passthrough(slot(node, "child"), c, e2, ctx)


@reg("AnimatedCrossFade")
def _cross_fade(node, c, env, ctx):
    second = enum_val(props(node).get("crossFadeState"), "showFirst") == "showSecond"
    return passthrough(slot(node, "secondChild" if second else "firstChild"), c, env, ctx)


@reg("Lottie", "RiveAnimation")
def _anim_asset(node, c, env, ctx):
    pr = props(node)
    w = num(pr.get("width"), min(c.maxW, 160.0) if c.maxW < INF else 160.0)
    h = num(pr.get("height"), min(c.maxH, 160.0) if c.maxH < INF else 160.0)
    w, h = c.constrain(w, h)
    lottie = node.get("type") == "Lottie"
    name = str(pr.get("name") or "").replace("\\", "/").split("/")[-1]

    def paint(p, b, ctx2):
        r = QRectF(.5, .5, b.w - 1, b.h - 1)
        p.setPen(QPen(QColor("#FF00BFA5" if lottie else "#FF1D1D1D"), 1, Qt.PenStyle.DashLine))
        p.setBrush(QColor(0, 191, 165, 24) if lottie else QColor(29, 29, 29, 18))
        p.drawRoundedRect(r, 8, 8)
        sz = min(b.w, b.h) * .4
        iconfont.draw(p, QRectF((b.w - sz) / 2, b.h / 2 - sz * .8, sz, sz), "Icons.animation",
                      QColor("#FF00897B") if lottie else QColor("#FF424242"))
        f = QFont(ctx2.font_family)
        f.setPixelSize(11)
        p.setFont(f)
        p.setPen(QColor("#FF555555"))
        p.drawText(QRectF(4, b.h / 2 + sz * .3, b.w - 8, 28), int(Qt.AlignmentFlag.AlignHCenter),
                   f"{'Lottie' if lottie else 'Rive'}\n{name}")
    return Box(w, h, paint=paint)


@reg("RadTwoPane")
def _two_pane(node, c, env, ctx):
    from .. import devices as D
    pr = props(node)
    w, h = c.biggest
    if w == INF or h == INF:
        w, h = (c.maxW if c.maxW < INF else ctx.screen_size[0] or 400.0), (c.maxH if c.maxH < INF else 400.0)
    hinge = None
    if ctx.hinge is not None and pr.get("hingeAware", True) is not False:
        hx, hy, hw, hh = ctx.hinge
        sw, sh = ctx.screen_size
        # the pane is assumed to fill the width and to sit at the bottom of the screen (below an app bar)
        hinge = (hx - (sw - w), hy, hw, hh) if hw <= hh else (hx, hy - (sh - h), hw, hh)
    mode = enum_val(pr.get("paneMode"), "auto").capitalize()
    single = enum_val(pr.get("singlePane"), "start").capitalize()
    r = D.two_pane(w, h, mode, num(pr.get("ratio"), 0.5), single, hinge, True, int(num(pr.get("minDualWidth"),
                                                                                       600)))
    kids = []
    names = ("start", "end")
    if r["mode"] == "single":
        k = slot(node, names[r["shown"] or 0])
        if isinstance(k, dict):
            kids.append(at(layout_node(k, C.tight(w, h), env, ctx), 0, 0))
    else:
        for name, rect in zip(names, r["panes"]):
            k = slot(node, name)
            if isinstance(k, dict) and rect:
                x, y, pw, ph = rect
                kids.append(at(layout_node(k, C.tight(max(0.0, pw), max(0.0, ph)), env, ctx), x, y))
    box = Box(w, h, kids)
    box.clip = "rect"
    return box


# ============================================================================ rendering
def _curve(name: str, t: float) -> float:
    n = enum_val(name, "easeOut")
    t = max(0.0, min(1.0, t))
    if n == "linear":
        return t
    if n in ("easeIn",):
        return t * t * t
    if n in ("easeInOut", "easeInOutCubic", "ease", "fastOutSlowIn"):
        return 4 * t * t * t if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
    if n == "easeOutBack":
        k = 1.70158
        return 1 + (k + 1) * (t - 1) ** 3 + k * (t - 1) ** 2
    if n == "bounceOut":
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:
            return n1 * t * t
        if t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + .75
        if t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + .9375
        t -= 2.625 / d1
        return n1 * t * t + .984375
    if n == "elasticOut":
        return 1.0 if t == 1 else 2 ** (-10 * t) * math.sin((t * 10 - .75) * (2 * math.pi) / 3) + 1
    return 1 - (1 - t) ** 3


def anim_state(anim: dict, t_ms: float) -> tuple[float, float, float, float]:
    """(opacity, dx, dy, scale) of an entrance animation ``t_ms`` after start (docs 1.4 defaults)."""
    typ = anim.get("type", "fadeIn")
    delay, dur = num(anim.get("delayMs"), 0.0), max(1.0, num(anim.get("durationMs"), 500.0))
    e = _curve(anim.get("curve", "Curves.easeOut"), (t_ms - delay) / dur)
    raw = max(0.0, min(1.0, (t_ms - delay) / dur))
    dflt = {"fadeInUp": (0, 30), "slideUp": (0, 30), "fadeInDown": (0, -30), "slideDown": (0, -30),
            "fadeInLeft": (-30, 0), "slideLeft": (30, 0), "fadeInRight": (30, 0), "slideRight": (-30, 0)}
    dx0, dy0 = dflt.get(typ, (0, 0))
    dx0 = num(anim.get("offsetX"), dx0)
    dy0 = num(anim.get("offsetY"), dy0)
    fade = not typ.startswith("slide")
    op = raw if fade else 1.0
    op = _curve("easeOut", op) if fade else 1.0
    sc = 1.0
    if typ in ("scaleIn", "zoomIn", "bounceIn"):
        s0 = num(anim.get("scale"), 0.8 if typ == "scaleIn" else 0.3)
        e2 = _curve("bounceOut", raw) if typ == "bounceIn" else e
        sc = s0 + (1 - s0) * e2
    return op, dx0 * (1 - e), dy0 * (1 - e), sc


def anim_end(screen_tree: dict) -> float:
    """When the last animation of a tree ends (ms; repeat / reverse included, forever = 3 runs)."""
    from . import motion as MO
    end = 0.0
    for n, *_ in M.walk_node(screen_tree):
        a = n.get("anim")
        if isinstance(a, dict):
            if a.get("type") in MO.LEGACY_TYPES and not (set(a) - {"type", "delayMs", "durationMs", "offsetX",
                                                                   "offsetY", "scale", "curve", "from"}):
                end = max(end, num(a.get("delayMs"), 0.0) + num(a.get("durationMs"), 500.0))
            else:
                end = max(end, MO.play_length(a))
    return end


def paint_box(p: QPainter, box: Box, ctx: Ctx) -> None:
    p.save()
    p.translate(box.x, box.y)
    if box.xform is not None:
        p.setTransform(box.xform, True)
    if box.opacity < 1:
        p.setOpacity(p.opacity() * box.opacity)
    tint = None
    if box.anim and ctx.anim_t is not None:
        from . import motion as MO
        a = box.anim
        if a.get("type") in MO.LEGACY_TYPES and not (set(a) - {"type", "delayMs", "durationMs", "offsetX",
                                                               "offsetY", "scale", "curve", "from"}):
            op, dx, dy, sc = anim_state(a, ctx.anim_t)
            p.translate(dx, dy)
            if sc != 1:
                p.translate(box.w / 2, box.h / 2)
                p.scale(sc, sc)
                p.translate(-box.w / 2, -box.h / 2)
            p.setOpacity(p.opacity() * op)
        else:
            tint = _paint_frame(p, box, MO.frame(a, MO.value_at(a, ctx.anim_t)), ctx)
    if box.paint is not None:
        box.paint(p, box, ctx)
    if box.clip is not None:
        if box.clip == "rect":
            p.setClipRect(QRectF(0, 0, box.w, box.h), Qt.ClipOperation.IntersectClip)
        else:
            p.setClipPath(box.clip, Qt.ClipOperation.IntersectClip)
    for k in box.kids:
        paint_box(p, k, ctx)
    if box.post is not None:
        box.post(p, box, ctx)
    if box.overflow is not None:
        _paint_overflow(p, box)
    if tint is not None:
        p.setClipping(False)
        p.fillRect(QRectF(0, 0, box.w, box.h), tint)
    p.restore()


def _paint_frame(p: QPainter, box: Box, f: dict, ctx: Ctx):
    """Apply a motion.frame() to the painter; returns the tint colour to paint over the box (or None)."""
    p.translate(f["dx"], f["dy"])
    ox, oy = (box.w / 2, 0.0) if f["origin"] == "topCenter" else (box.w / 2, box.h / 2)
    sx, sy = f["sx"] * math.cos(f["ry"]), f["sy"] * math.cos(f["rx"])     # flips: a squash approximation
    if f["rotation"] or sx != 1 or sy != 1:
        p.translate(ox, oy)
        if f["rotation"]:
            p.rotate(f["rotation"] * 360)
        p.scale(sx if abs(sx) > 1e-3 else 1e-3, sy if abs(sy) > 1e-3 else 1e-3)
        p.translate(-ox, -oy)
    if f["opacity"] < 1:
        p.setOpacity(p.opacity() * max(0.0, f["opacity"]))
    if f["reveal"] < 1:
        p.setClipRect(QRectF(0, 0, box.w * max(0.0, f["reveal"]), box.h), Qt.ClipOperation.IntersectClip)
    if f["tint"] > 0 and f.get("color") is not None:
        col = f["color"]
        if isinstance(col, tuple):            # keyframe colours: (from, to, t)
            a, b2, t = (color(col[0], ctx) or QColor(0, 0, 0, 0)), (color(col[1], ctx) or QColor(0, 0, 0, 0)), col[2]
            q = QColor.fromRgbF(a.redF() + (b2.redF() - a.redF()) * t, a.greenF() + (b2.greenF() - a.greenF()) * t,
                                a.blueF() + (b2.blueF() - a.blueF()) * t, 1.0)
        else:
            q = color(col, ctx)
        if q is not None:
            q = QColor(q)
            q.setAlphaF(min(1.0, .55 * f["tint"]))
            return q
    return None


def _paint_overflow(p: QPainter, box: Box) -> None:
    """Flutter's yellow / black overflow stripe."""
    side, amount = box.overflow
    p.save()
    p.setClipping(False)
    r = QRectF(box.w - 8, 0, 8, box.h) if side == "right" else QRectF(0, box.h - 8, box.w, 8)
    p.fillRect(r, QColor("#FFFFEB3B"))
    p.setPen(QPen(QColor("#FF000000"), 3))
    p.setClipRect(r)
    step = 12
    length = int(max(r.width(), r.height()) + r.height() + r.width())
    for i in range(-length, length, step):
        p.drawLine(QPointF(r.x() + i, r.y()), QPointF(r.x() + i + r.height(), r.bottom()))
    p.setClipping(False)
    f = QFont("Segoe UI")
    f.setPixelSize(9)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#FFD32F2F"))
    msg = f"{side.upper()} OVERFLOWED BY {amount:.0f} PIXELS"
    if side == "bottom":
        p.fillRect(QRectF(4, box.h - 22, QFontMetricsF(f).horizontalAdvance(msg) + 6, 13), QColor("#FFFFEB3B"))
        p.drawText(QPointF(7, box.h - 12), msg)
    p.restore()


def bounds(root: Box) -> dict[str, QRectF]:
    """Absolute rectangle of every node (the outermost box of a node id wins)."""
    out: dict[str, QRectF] = {}

    def rec(b: Box, ox: float, oy: float, xf: QTransform | None):
        x, y = ox + b.x, oy + b.y
        r = QRectF(x, y, b.w, b.h)
        if b.xform is not None:
            t = QTransform(b.xform)
            t = t * QTransform.fromTranslate(x, y)
            r = t.mapRect(QRectF(0, 0, b.w, b.h))
        if b.nid and b.nid not in out:
            out[b.nid] = r
        if b.xform is not None:
            k = b.xform.m11()
            for kid in b.kids:      # scale only (FittedBox) - children in scaled coordinates
                sub = QTransform(b.xform) * QTransform.fromTranslate(x, y)
                kr = sub.mapRect(QRectF(kid.x, kid.y, kid.w, kid.h))
                rec_scaled(kid, sub, k)
                if kid.nid and kid.nid not in out:
                    out[kid.nid] = kr
            return
        for kid in b.kids:
            rec(kid, x, y, xf)

    def rec_scaled(b: Box, t: QTransform, _k):
        tt = QTransform.fromTranslate(b.x, b.y) * t
        for kid in b.kids:
            r = tt.mapRect(QRectF(kid.x, kid.y, kid.w, kid.h))
            if kid.nid and kid.nid not in out:
                out[kid.nid] = r
            rec_scaled(kid, tt, _k)
    rec(root, 0.0, 0.0, None)
    return out


def hit_test(root: Box, x: float, y: float) -> list[str]:
    """Node ids under a point, deepest (top-most painted) first."""
    hits: list[tuple[int, int, str]] = []
    order = [0]

    def rec(b: Box, ox: float, oy: float, depth: int):
        bx, by = ox + b.x, oy + b.y
        if b.xform is not None:
            inv, ok = b.xform.inverted()
            if ok:
                lx, ly = inv.map(x - bx, y - by)
                lx, ly = lx + bx, ly + by
            else:
                lx, ly = x, y
        else:
            lx, ly = x, y
        inside = bx <= lx <= bx + b.w and by <= ly <= by + b.h
        if inside and b.nid:
            order[0] += 1
            hits.append((depth, order[0], b.nid))
        if b.xform is not None:
            for kid in b.kids:
                _rec_local(kid, lx - bx, ly - by, depth + 1)
            return
        for kid in b.kids:
            rec(kid, bx, by, depth + 1)

    def _rec_local(b: Box, lx: float, ly: float, depth: int):
        inside = b.x <= lx <= b.x + b.w and b.y <= ly <= b.y + b.h
        if inside and b.nid:
            order[0] += 1
            hits.append((depth, order[0], b.nid))
        for kid in b.kids:
            _rec_local(kid, lx - b.x, ly - b.y, depth + 1)
    rec(root, 0.0, 0.0, 0)
    hits.sort(key=lambda h: (h[1]), reverse=True)    # last painted (deepest / top-most) first
    seen, out = set(), []
    for _d, _o, nid in hits:
        if nid not in seen:
            seen.add(nid)
            out.append(nid)
    return out


def render_tree(screen: M.Screen, width: float, height: float, ctx: Ctx, pad_top: float = 24.0,
                pad_bottom: float = 0.0) -> Box:
    """Lay out the screen's tree for a device of width x height dp."""
    ctx.screen = screen
    theme = screen.data.get("theme") or {}
    base = {"fontSize": 14, "color": "#%08X" % ctx.scheme["onSurface"].rgba(), "letterSpacing": 0.25}
    if theme.get("fontFamily"):
        base["googleFont"] = theme["fontFamily"]
    env = Env(style=base, icon_color=ctx.scheme["onSurfaceVariant"], pad_top=pad_top, pad_bottom=pad_bottom)
    root = layout_node(screen.tree, C.tight(width, height), env, ctx)
    return root


def make_ctx(screen: M.Screen, dark: bool = False, text_scale: float = 1.0, folder=None, images=None) -> Ctx:
    theme = screen.data.get("theme") or {}
    dark = dark or theme.get("brightness") == "dark"
    sch = color_scheme(theme.get("seedColor"), dark)
    return Ctx(sch, dark, text_scale, Path(folder) if folder else None, images)


def render_image(screen: M.Screen, width: int = 412, height: int = 915, dark: bool = False, scale: float = 1.0,
                 folder=None, images=None) -> QImage:
    """The whole screen as a QImage (tests, thumbnails)."""
    ctx = make_ctx(screen, dark, 1.0, folder, images)
    root = render_tree(screen, width, height, ctx)
    img = QImage(int(width * scale), int(height * scale), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor("#FFFFFFFF"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.scale(scale, scale)
    paint_box(p, root, ctx)
    p.end()
    return img
