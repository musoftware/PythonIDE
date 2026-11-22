"""Structure widgets: Card, Material, DecoratedBox, Opacity, clips, AppBar, navigation / tab bars, Drawer,
the Cupertino scaffold widgets, Code and Scaffold."""
from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainterPath, QPen

from .. import iconfont
from .core import INF, C, Box, at, num, edge, radii, enum_val, color, props, slot
from .paint import merge_style, rrect_path, drop_shadow, paint_decoration, shape_path, shape_side
from .registry import reg, layout_node, first_child, passthrough
from .w_content import _text_box


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
