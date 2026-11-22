"""The widget-type -> layout function registry (@reg), layout_node dispatch, the unknown / error boxes and
the small helpers shared by the widget modules."""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

from .core import INF, C, Box, at, Env, Ctx, slot


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
    try:                                     # a component package widget: drawn by its designer.py
        from ...components import dart as _comp_dart
        size = _comp_dart.preview_size(node.get("type", ""))
    except Exception:  # noqa: BLE001
        size = None
    if size:
        return Box(*c.constrain(min(c.maxW, size[0]), min(c.maxH, size[1])),
                   paint=lambda p, b, _ctx: _comp_dart.paint_preview(p, b.w, b.h, node))
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
