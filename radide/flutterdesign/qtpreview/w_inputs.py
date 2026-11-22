"""Input widgets: Chip, Badge, text fields, Checkbox, Switch, Slider, DropdownButton, list tiles, Radio and
the buttons."""
from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetricsF, QPen

from .. import iconfont
from .. import model as M
from .core import INF, C, Box, at, num, edge, radii, enum_val, color, props, slot
from .paint import make_font, merge_style, rrect_path, drop_shadow, shape_path, shape_side
from .registry import reg, layout_node, passthrough
from .w_content import _text_box


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


@reg("RadioGroup")
def _radio_group(node, c, env, ctx):
    gv = props(node).get("groupValue")
    return passthrough(slot(node, "child"), c, replace(env, radio=gv if isinstance(gv, str) else None), ctx)


def _radio_paint(on: bool, act: QColor):
    def paint(p, b, ctx2):
        r = QRectF((b.w - 20) / 2, (b.h - 20) / 2, 20, 20)
        p.save()
        p.setPen(QPen(act if on else ctx2.scheme["onSurfaceVariant"], 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(r.adjusted(1, 1, -1, -1))
        if on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(act)
            p.drawEllipse(r.adjusted(5, 5, -5, -5))
        p.restore()
    return paint


@reg("Radio")
def _radio(node, c, env, ctx):
    pr = props(node)
    on = env.radio is not None and pr.get("value") == env.radio
    return Box(*c.constrain(48, 48), paint=_radio_paint(on, color(pr.get("activeColor"), ctx, ctx.scheme["primary"])))


@reg("RadioListTile")
def _radio_tile(node, c, env, ctx):
    pr = props(node)
    on = env.radio is not None and pr.get("value") == env.radio
    ctrl = Box(48, 48, paint=_radio_paint(on, color(pr.get("activeColor"), ctx, ctx.scheme["primary"])))
    if enum_val(pr.get("controlAffinity"), "platform") == "trailing":
        return _list_tile(node, c, env, ctx, trailing_control=ctrl)
    return _list_tile(node, c, env, ctx, leading_control=ctrl)


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
