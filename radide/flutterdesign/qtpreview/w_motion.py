"""Animation / motion widgets (implicit animations, transitions, Lottie / Rive) and the foldable RadTwoPane."""
from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPen, QTransform

from .. import iconfont
from .core import INF, C, Box, at, num, align, enum_val, props, slot
from .paint import merge_style
from .registry import reg, layout_node, passthrough
from .w_layout import _padding, _align, _pass


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
    src = str(pr.get("name") or "")
    if lottie and ctx.folder is not None and node.get("ctor", "asset") == "asset" and src \
            and not src.startswith(("http:", "https:")):
        from .. import lottie_thumb as LT
        f = Path(ctx.folder) / src
        meta = LT.info(f) if f.is_file() else None
        if meta is not None:
            def paint_frame(p, b, ctx2, f=f, meta=meta):
                dpr = 2
                img = LT.first_frame(f, max(1, int(b.w * dpr)), max(1, int(b.h * dpr)))
                if img is None:
                    return
                p.save()
                p.drawImage(QRectF(0, 0, b.w, b.h), img)
                fnt = QFont(ctx2.font_family)
                fnt.setPixelSize(9)
                p.setFont(fnt)
                tag = f"Lottie {meta['seconds']:.1f}s"
                tw = QFontMetricsF(fnt).horizontalAdvance(tag) + 6
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 137, 123, 170))
                p.drawRoundedRect(QRectF(b.w - tw - 2, 2, tw, 13), 3, 3)
                p.setPen(QColor("#FFFFFFFF"))
                p.drawText(QRectF(b.w - tw - 2, 2, tw, 13), int(Qt.AlignmentFlag.AlignCenter), tag)
                p.restore()
            return Box(w, h, paint=paint_frame)

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
    from ... import devices as D
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
