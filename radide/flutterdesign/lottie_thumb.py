"""First-frame thumbnails of Lottie animations for the Qt preview of the Flutter designer.

A small, original renderer of the Lottie JSON format (bodymovin): shape layers (groups, rectangles, ellipses,
bezier paths, fills, strokes, linear / radial gradient fills approximated by their first colour), solid layers,
image layers (embedded data URIs or files next to the animation), precompositions, null layers and parenting,
layer / group transforms and opacity, at the first frame (``ip``). Masks, mattes, trim paths, effects, text and
expressions are ignored - it is a thumbnail, the live preview (package:lottie) plays the real animation.
"""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QTransform

_CACHE: dict[tuple, QImage | None] = {}
_INFO: dict[tuple, dict | None] = {}


def _load(path: Path) -> dict | None:
    try:
        key = (str(path), path.stat().st_mtime)
    except OSError:
        return None
    if key not in _INFO:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            _INFO[key] = d if isinstance(d, dict) and "layers" in d else None
        except (OSError, ValueError):
            _INFO[key] = None
    return _INFO[key]


def info(path) -> dict | None:
    """{"width", "height", "fps", "frames", "seconds", "layers", "name"} of a Lottie file (None = not one)."""
    d = _load(Path(path))
    if d is None:
        return None
    fr = float(d.get("fr") or 30)
    frames = float(d.get("op", 0)) - float(d.get("ip", 0))
    return {"width": int(d.get("w") or 0), "height": int(d.get("h") or 0), "fps": fr, "frames": frames,
            "seconds": frames / fr if fr else 0.0, "layers": len(d.get("layers") or []), "name": d.get("nm") or ""}


def first_frame(path, width: int, height: int) -> QImage | None:
    """The first frame of the animation scaled to fit *width* x *height* (None when it cannot be read)."""
    p = Path(path)
    d = _load(p)
    if d is None or width <= 0 or height <= 0:
        return None
    key = (str(p), p.stat().st_mtime, int(width), int(height))
    if key not in _CACHE:
        try:
            _CACHE[key] = _render(d, p.parent, int(width), int(height))
        except Exception:  # noqa: BLE001 - a broken file gives the placeholder, never an exception
            _CACHE[key] = None
        if len(_CACHE) > 64:
            _CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key]


# ============================================================================================ values
def _val(prop, default=None):
    """The value of an (animated) property at the first frame."""
    if not isinstance(prop, dict):
        return default
    if prop.get("s") is True and "x" in prop:              # split position
        return [_num(_val(prop.get("x"), 0)), _num(_val(prop.get("y"), 0))]
    k = prop.get("k", default)
    if prop.get("a") == 1 and isinstance(k, list) and k and isinstance(k[0], dict):
        s = k[0].get("s", k[0].get("e", default))
        return s
    return k


def _num(v, default=0.0) -> float:
    if isinstance(v, list):
        v = v[0] if v else default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _pt(v, default=(0.0, 0.0)) -> QPointF:
    if isinstance(v, list) and len(v) >= 2:
        return QPointF(_num(v[0]), _num(v[1]))
    return QPointF(*default)


def _color(v, opacity: float = 1.0) -> QColor:
    if not isinstance(v, list) or len(v) < 3:
        return QColor(0, 0, 0, int(255 * opacity))
    vals = [_num(x) for x in v[:4]] + [1.0] * (4 - len(v[:4]))
    if max(vals[:3]) > 1.0:                                 # very old files: 0..255
        vals = [x / 255.0 for x in vals[:3]] + [vals[3] if vals[3] <= 1 else vals[3] / 255.0]
    c = QColor.fromRgbF(*[max(0.0, min(1.0, x)) for x in vals[:3]], max(0.0, min(1.0, vals[3] * opacity)))
    return c


def _transform(ks: dict) -> tuple[QTransform, float]:
    """(QTransform, opacity 0..1) of a layer "ks" / group "tr"."""
    ks = ks or {}
    a = _pt(_val(ks.get("a"), [0, 0]))
    p = _pt(_val(ks.get("p"), [0, 0]))
    s = _val(ks.get("s"), [100, 100])
    sx = _num(s[0] if isinstance(s, list) else s, 100) / 100.0
    sy = _num(s[1] if isinstance(s, list) and len(s) > 1 else s, 100) / 100.0
    r = _num(_val(ks.get("r", ks.get("rz")), 0))
    o = _num(_val(ks.get("o"), 100), 100) / 100.0
    t = QTransform()
    t.translate(p.x(), p.y())
    t.rotate(r)
    t.scale(sx, sy)
    t.translate(-a.x(), -a.y())
    return t, max(0.0, min(1.0, o))


# =========================================================================================== shapes
def _bezier(sh) -> QPainterPath:
    path = QPainterPath()
    if isinstance(sh, list):
        sh = sh[0] if sh else {}
    if not isinstance(sh, dict):
        return path
    vs, ins, outs = sh.get("v") or [], sh.get("i") or [], sh.get("o") or []
    if not vs:
        return path
    path.moveTo(_pt(vs[0]))
    n = len(vs)
    for k in range(1, n + (1 if sh.get("c") else 0)):
        i0, i1 = (k - 1) % n, k % n
        v0, v1 = _pt(vs[i0]), _pt(vs[i1])
        c1 = v0 + _pt(outs[i0] if i0 < len(outs) else [0, 0])
        c2 = v1 + _pt(ins[i1] if i1 < len(ins) else [0, 0])
        path.cubicTo(c1, c2, v1)
    if sh.get("c"):
        path.closeSubpath()
    return path


def _geometry(it: dict) -> QPainterPath | None:
    ty = it.get("ty")
    if ty == "rc":
        c, s = _pt(_val(it.get("p"), [0, 0])), _pt(_val(it.get("s"), [0, 0]))
        r = _num(_val(it.get("r"), 0))
        path = QPainterPath()
        rect = QRectF(c.x() - s.x() / 2, c.y() - s.y() / 2, s.x(), s.y())
        rr = min(r, s.x() / 2, s.y() / 2)
        if rr > 0:
            path.addRoundedRect(rect, rr, rr)
        else:
            path.addRect(rect)
        return path
    if ty == "el":
        c, s = _pt(_val(it.get("p"), [0, 0])), _pt(_val(it.get("s"), [0, 0]))
        path = QPainterPath()
        path.addEllipse(c, s.x() / 2, s.y() / 2)
        return path
    if ty == "sh":
        return _bezier(_val(it.get("ks")))
    if ty == "sr":                                         # star / polygon
        c = _pt(_val(it.get("p"), [0, 0]))
        pts = max(3, int(_num(_val(it.get("pt"), 5))))
        orr = _num(_val(it.get("or"), 10))
        irr = _num(_val(it.get("ir"), orr / 2)) if it.get("sy") == 1 else orr
        rot = math.radians(_num(_val(it.get("r"), 0))) - math.pi / 2
        n = pts * (2 if it.get("sy") == 1 else 1)
        path = QPainterPath()
        for k in range(n):
            rad = orr if k % 2 == 0 or it.get("sy") != 1 else irr
            a = rot + 2 * math.pi * k / n
            q = QPointF(c.x() + rad * math.cos(a), c.y() + rad * math.sin(a))
            path.moveTo(q) if k == 0 else path.lineTo(q)
        path.closeSubpath()
        return path
    return None


def _paint_group(p: QPainter, items: list, inherited: list):
    """Paint a shape list (bottom item first): nested groups, then this list's geometry with its styles."""
    items = [i for i in items or [] if isinstance(i, dict) and not i.get("hd")]
    styles = [i for i in items if i.get("ty") in ("fl", "st", "gf", "gs")] or inherited
    geo = QPainterPath()
    for it in items:
        g = _geometry(it)
        if g is not None:
            geo.addPath(g)
    for it in reversed(items):
        if it.get("ty") == "gr":
            tr = next((x for x in it.get("it") or [] if isinstance(x, dict) and x.get("ty") == "tr"), None)
            t, o = _transform(tr) if tr else (QTransform(), 1.0)
            p.save()
            p.setTransform(t, True)
            p.setOpacity(p.opacity() * o)
            _paint_group(p, it.get("it") or [], styles)
            p.restore()
    if geo.isEmpty():
        return
    for st in reversed(styles):                            # fills under strokes
        op = _num(_val(st.get("o"), 100), 100) / 100.0
        if st.get("ty") in ("fl", "gf"):
            col = _color(_val(st.get("c"))) if st.get("ty") == "fl" else _grad_color(st)
            col.setAlphaF(col.alphaF() * op)
            geo.setFillRule(Qt.FillRule.OddEvenFill if st.get("r") == 2 else Qt.FillRule.WindingFill)
            p.fillPath(geo, QBrush(col))
        else:
            col = _color(_val(st.get("c"))) if st.get("ty") == "st" else _grad_color(st)
            col.setAlphaF(col.alphaF() * op)
            pen = QPen(col, max(0.0, _num(_val(st.get("w"), 1), 1)))
            pen.setCapStyle({1: Qt.PenCapStyle.FlatCap, 2: Qt.PenCapStyle.RoundCap}.get(
                st.get("lc"), Qt.PenCapStyle.SquareCap))
            pen.setJoinStyle({1: Qt.PenJoinStyle.MiterJoin, 2: Qt.PenJoinStyle.RoundJoin}.get(
                st.get("lj"), Qt.PenJoinStyle.BevelJoin))
            p.strokePath(geo, pen)


def _grad_color(st: dict) -> QColor:
    """First colour stop of a gradient fill / stroke."""
    g = st.get("g") or {}
    vals = _val(g.get("k")) if isinstance(g.get("k"), dict) else _val(g)
    if isinstance(vals, list) and len(vals) >= 4:
        return _color([vals[1], vals[2], vals[3], 1])
    return QColor(128, 128, 128)


# =========================================================================================== layers
def _layer_transform(layer: dict, by_ind: dict, depth: int = 0) -> tuple[QTransform, float]:
    t, o = _transform(layer.get("ks") or {})
    par = by_ind.get(layer.get("parent")) if "parent" in layer else None
    if par is not None and depth < 32:
        pt, _po = _layer_transform(par, by_ind, depth + 1)
        t = t * pt                                          # QTransform: child first, then parent
    return t, o


def _paint_layers(p: QPainter, layers: list, assets: dict, folder: Path, frame: float, depth: int = 0):
    layers = [la for la in layers or [] if isinstance(la, dict)]
    by_ind = {la.get("ind"): la for la in layers if "ind" in la}
    for la in reversed(layers):
        if la.get("hd") or la.get("ty") in (3, 5) or la.get("td"):
            continue                                        # null / text / matte source layers
        ip, op = _num(la.get("ip", -1e9), -1e9), _num(la.get("op", 1e9), 1e9)
        if not ip <= frame < op:
            continue
        t, o = _layer_transform(la, by_ind)
        p.save()
        p.setTransform(t, True)
        p.setOpacity(p.opacity() * o)
        ty = la.get("ty")
        if ty == 4:
            _paint_group(p, la.get("shapes") or [], [])
        elif ty == 1:
            p.fillRect(QRectF(0, 0, _num(la.get("sw")), _num(la.get("sh"))), QColor(la.get("sc") or "#000000"))
        elif ty == 2:
            img = _asset_image(assets.get(la.get("refId")) or {}, folder)
            if img is not None:
                p.drawImage(QPointF(0, 0), img)
        elif ty == 0 and depth < 8:
            a = assets.get(la.get("refId")) or {}
            st = _num(la.get("st", 0))
            sr = _num(la.get("sr", 1), 1) or 1
            if la.get("w") and la.get("h"):
                p.setClipRect(QRectF(0, 0, _num(la["w"]), _num(la["h"])), Qt.ClipOperation.IntersectClip)
            _paint_layers(p, a.get("layers") or [], assets, folder, (frame - st) / sr, depth + 1)
        p.restore()


def _asset_image(a: dict, folder: Path) -> QImage | None:
    src = str(a.get("p") or "")
    if not src:
        return None
    img = QImage()
    if src.startswith("data:") and "," in src:
        try:
            img.loadFromData(base64.b64decode(src.split(",", 1)[1]))
        except ValueError:
            return None
    else:
        f = folder / str(a.get("u") or "") / src
        if not f.is_file() or not img.load(str(f)):
            return None
    if a.get("w") and a.get("h") and (img.width(), img.height()) != (int(a["w"]), int(a["h"])):
        img = img.scaled(int(a["w"]), int(a["h"]), Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    return img


def _render(d: dict, folder: Path, width: int, height: int) -> QImage | None:
    w, h = float(d.get("w") or 0), float(d.get("h") or 0)
    if w <= 0 or h <= 0:
        return None
    img = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    k = min(width / w, height / h)                          # BoxFit.contain
    p.translate((width - w * k) / 2, (height - h * k) / 2)
    p.scale(k, k)
    p.setClipRect(QRectF(0, 0, w, h))
    assets = {a.get("id"): a for a in d.get("assets") or [] if isinstance(a, dict)}
    _paint_layers(p, d.get("layers") or [], assets, folder, _num(d.get("ip", 0)))
    p.end()
    return img
