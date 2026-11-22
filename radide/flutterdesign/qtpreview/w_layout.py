"""Layout widgets: Container, Padding, SafeArea, Center / Align, SizedBox and friends, Transform, Row / Column /
Flex, Wrap, Stack, scroll views, ListView, GridView, PageView."""
from __future__ import annotations

import math
from dataclasses import replace

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QTransform

from .. import model as M
from .core import INF, C, Box, at, Env, Ctx, num, edge, radii, align, enum_val, color, props, slot
from .paint import rrect_path, paint_decoration
from .registry import reg, layout_node, passthrough, pad_box, align_box, child_fn


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
     "Expanded", "Flexible", "Positioned", "Directionality")
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
