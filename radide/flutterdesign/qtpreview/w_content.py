"""Content widgets: Text / RichText, Icon, Image, CircleAvatar, Divider, Placeholder, FlutterLogo and the
progress indicators."""
from __future__ import annotations

import math
from dataclasses import replace

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFontMetricsF, QPainterPath, QPen, QTextLayout, QTextOption

from .. import iconfont
from .. import model as M
from .core import INF, C, Box, at, Ctx, num, align, enum_val, color, props, slot
from .paint import make_font, merge_style, rrect_path, paint_image
from .registry import reg, layout_node


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


def _rich_box(spans, style: dict, c: C, ctx: Ctx, align_: str = "", max_lines=None, soft_wrap=True) -> Box:
    """Text.rich / RichText: the spans laid out as one paragraph with per-span fonts and colours."""
    from PyQt6.QtGui import QTextCharFormat
    text, ranges = "", []
    base_font = make_font(style, ctx)
    for sp in spans if isinstance(spans, list) else []:
        st = merge_style(style, sp.get("style")) if isinstance(sp, dict) and not M.is_code(sp) else style
        piece = "[…]" if M.is_code(sp) else str((sp or {}).get("text") or "") if isinstance(sp, dict) else ""
        if not piece:
            continue
        fr = QTextLayout.FormatRange()
        fr.start, fr.length = len(text), len(piece)
        cf = QTextCharFormat()
        cf.setFont(make_font(st, ctx))
        cf.setForeground(QBrush(color(st.get("color"), ctx, ctx.scheme["onSurface"])))
        bg = color(st.get("backgroundColor"), ctx)
        if bg is not None:
            cf.setBackground(QBrush(bg))
        deco = enum_val(st.get("decoration"))
        cf.setFontUnderline(deco == "underline")
        cf.setFontStrikeOut(deco == "lineThrough")
        cf.setFontOverline(deco == "overline")
        fr.format = cf
        ranges.append(fr)
        text += piece
    tl = QTextLayout(text, base_font)
    tl.setFormats(ranges)
    opt = QTextOption()
    opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere if soft_wrap is not False
                    else QTextOption.WrapMode.NoWrap)
    tl.setTextOption(opt)
    maxw = c.maxW if c.maxW < INF else 1e6
    tl.beginLayout()
    lines, y, widest = [], 0.0, 0.0
    while True:
        line = tl.createLine()
        if not line.isValid():
            break
        if max_lines and len(lines) >= max_lines:
            break
        line.setLineWidth(maxw)
        line.setPosition(QPointF(0, y))
        widest = max(widest, line.naturalTextWidth())
        lines.append(line)
        y += line.height()
    tl.endLayout()
    w, h = c.constrain(min(math.ceil(widest), maxw), y)
    fac = {"center": .5, "right": 1.0, "end": 1.0}.get(enum_val(align_, "start"), 0.0)

    def paint(p, b, ctx2, tl=tl, lines=lines):
        p.save()
        for ln in lines:
            ln.draw(p, QPointF((b.w - ln.naturalTextWidth()) * fac, 0))
        p.restore()
    return Box(w, h, paint=paint)


@reg("RichText")
def _richtext(node, c, env, ctx):
    pr = props(node)
    ml = num(pr.get("maxLines"))
    # RichText does not inherit DefaultTextStyle (only the root span style)
    return _rich_box(pr.get("spans"), merge_style({}, pr.get("style")), c, ctx, pr.get("textAlign", ""),
                     int(ml) if ml else None, pr.get("softWrap", True))


@reg("Text", "SelectableText")
def _text(node, c, env, ctx):
    pr = props(node)
    if node.get("ctor") == "rich":
        ml = num(pr.get("maxLines"))
        return _rich_box(pr.get("spans"), merge_style(env.style, pr.get("style")), c, ctx, pr.get("textAlign", ""),
                         int(ml) if ml else None, pr.get("softWrap", True))
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
