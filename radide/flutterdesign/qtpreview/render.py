"""Rendering: entrance animation curves / state, painting a laid-out tree, bounds, hit testing and the
render_tree / make_ctx / render_image entry points."""
from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen, QTransform

from .. import model as M
from .colors import color_scheme
from .core import C, Box, Env, Ctx, num, enum_val, color
from .registry import layout_node


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
    from .. import motion as MO
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
        from .. import motion as MO
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
    theme = screen.data.get("theme") or getattr(ctx, "app_theme", None) or {}
    base = {"fontSize": 14, "color": "#%08X" % ctx.scheme["onSurface"].rgba(), "letterSpacing": 0.25}
    if theme.get("fontFamily"):
        base["googleFont"] = theme["fontFamily"]
    env = Env(style=base, icon_color=ctx.scheme["onSurfaceVariant"], pad_top=pad_top, pad_bottom=pad_bottom)
    root = layout_node(screen.tree, C.tight(width, height), env, ctx)
    return root


def make_ctx(screen: M.Screen, dark: bool = False, text_scale: float = 1.0, folder=None, images=None,
             app_theme: dict | None = None) -> Ctx:
    """*app_theme*: the project theme as a screen theme (themes.screen_theme), used when the screen has none."""
    theme = screen.data.get("theme") or app_theme or {}
    dark = dark or theme.get("brightness") == "dark"
    sch = color_scheme(theme.get("seedColor"), dark)
    ctx = Ctx(sch, dark, text_scale, Path(folder) if folder else None, images)
    ctx.app_theme = None if screen.data.get("theme") else app_theme
    return ctx


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
