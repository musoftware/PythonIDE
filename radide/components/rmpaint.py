"""Design-time drawing of the RAD Modern (Rm*) controls - the same look as the native radforms modules
(radide/runtimes/native/radforms/controls/rm_*.c): theme colours (Light / Dark / Office / Metro), rounded
shapes, accent colour, the built-in glyph names. Each package's ``designer.py`` calls
``paint_control(type, painter, rect, props, ctx)``.
"""
from __future__ import annotations

import json
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPen, QPolygonF

# the radforms themes (rf_init_themes): window, window_text, face, face_text, border, hot, hot_border,
# pressed, accent, accent_text, disabled, selection, selection_text, input, input_text, radius
THEMES = {
    "Light": dict(dark=False, window="#F0F0F0", text="#000000", face="#E1E1E1", face_text="#000000", border="#ADADAD",
                  hot="#E5F1FB", hot_border="#0078D7", accent="#0078D7", disabled="#A0A0A0", input="#FFFFFF",
                  input_text="#000000", radius=3),
    "Dark": dict(dark=True, window="#202020", text="#F0F0F0", face="#333333", face_text="#F0F0F0", border="#555555",
                 hot="#454545", hot_border="#0078D7", accent="#0078D7", disabled="#787878", input="#191919",
                 input_text="#F0F0F0", radius=4),
    "Office": dict(dark=False, window="#F3F3F3", text="#262626", face="#FFFFFF", face_text="#262626", border="#ABABAB",
                   hot="#D5E1F2", hot_border="#2B579A", accent="#2B579A", disabled="#A5A5A5", input="#FFFFFF",
                   input_text="#262626", radius=2),
    "Metro": dict(dark=False, window="#FFFFFF", text="#1E1E1E", face="#E6E6E6", face_text="#1E1E1E", border="#CCCCCC",
                  hot="#DADADA", hot_border="#0078D7", accent="#0078D7", disabled="#AAAAAA", input="#FFFFFF",
                  input_text="#1E1E1E", radius=0),
}
DESIGN_THEME = "Light"          # the form's Theme while it is designed (set by the designer when known)


def theme(props) -> dict:
    name = str(props.get("Style") or "Inherit")
    if name not in THEMES:
        name = DESIGN_THEME if DESIGN_THEME in THEMES else "Light"
    return THEMES[name]


def C(v) -> QColor:
    return QColor(v) if not isinstance(v, QColor) else v


def blend(a, b, t: float) -> QColor:
    a, b = C(a), C(b)
    t = max(0.0, min(1.0, t))
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t))


def on(back) -> QColor:
    c = C(back)
    return QColor("#202020") if (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000 > 150 else QColor("#FFFFFF")


def accent(props, t) -> QColor:
    return C(props.get("AccentColor") or t["accent"])


def card(t) -> QColor:
    return blend(t["window"], "#FFFFFF", 0.06) if t["dark"] else C(t["input"])


def items(value) -> list[dict]:
    """JSON array / list of dicts / "a;b;c" -> [{"Text", "Name", "Image", "Items", ...}]."""
    if isinstance(value, list):
        out = value
    else:
        s = str(value or "").strip()
        if s.startswith("["):
            try:
                out = json.loads(s)
            except ValueError:
                out = []
        else:
            out = [x for x in s.split(";") if x != ""] if s else []
    res = []
    for it in out:
        if isinstance(it, dict):
            res.append(it)
        else:
            res.append({"Text": str(it)})
    return res


def kids(it: dict) -> list[dict]:
    for k in ("Items", "Nodes", "Groups", "Pages", "Children", "Panels", "Tabs"):
        if isinstance(it.get(k), list) and it[k]:
            return [x if isinstance(x, dict) else {"Text": str(x)} for x in it[k]]
    return []


def font(p, props, scale=1.0, bold=False):
    f = QFont(props.get("FontName") or "Segoe UI")
    f.setPointSizeF(max(5.0, float(props.get("FontSize", 9) or 9) * scale))
    f.setBold(bool(bold or props.get("FontBold")))
    f.setItalic(bool(props.get("FontItalic")))
    p.setFont(f)
    return f


def rrect(p, r: QRectF, fill=None, border=None, radius=0.0, width=1.0):
    p.setPen(QPen(C(border), width) if border is not None else Qt.PenStyle.NoPen)
    p.setBrush(C(fill) if fill is not None else Qt.BrushStyle.NoBrush)
    if border is not None:
        r = r.adjusted(width / 2, width / 2, -width / 2, -width / 2)
    if radius > 0:
        p.drawRoundedRect(r, radius, radius)
    else:
        p.drawRect(r)


def text(p, r: QRectF, s, color, align=Qt.AlignmentFlag.AlignLeft, wrap=False):
    p.setPen(C(color))
    flags = align | (Qt.TextFlag.TextWordWrap if wrap else Qt.AlignmentFlag.AlignVCenter)
    if not wrap:
        s = QFontMetrics(p.font()).elidedText(str(s), Qt.TextElideMode.ElideRight, max(1, int(r.width())))
    p.drawText(r, int(flags), str(s))


def chevron(p, cx, cy, size, d, color, w=1.4):
    h, q = size / 2, size / 4
    pts = {"down": [(cx - h, cy - q), (cx, cy + q), (cx + h, cy - q)], "up": [(cx - h, cy + q), (cx, cy - q), (cx + h, cy + q)],
           "right": [(cx - q, cy - h), (cx + q, cy), (cx - q, cy + h)], "left": [(cx + q, cy - h), (cx - q, cy), (cx + q, cy + h)]}[d]
    p.setPen(QPen(C(color), w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))


def check(p, r: QRectF, color, w=1.8):
    p.setPen(QPen(C(color), w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPolyline(QPolygonF([QPointF(r.x() + r.width() * .18, r.y() + r.height() * .52),
                              QPointF(r.x() + r.width() * .42, r.y() + r.height() * .75),
                              QPointF(r.x() + r.width() * .82, r.y() + r.height() * .28)]))


# ------------------------------------------------------------------ glyphs (same paths as rm_kit.c)
GLYPHS = {
    "home": "M1 5 L5 1.5 L9 5 M2.5 4 L2.5 9 L7.5 9 L7.5 4 M4.2 9 L4.2 6 L5.8 6 L5.8 9",
    "settings": "O5 5 1.6 O5 5 3.4 M5 .6 L5 1.6 M5 8.4 L5 9.4 M.6 5 L1.6 5 M8.4 5 L9.4 5",
    "user": "O5 3.3 2 A5 9.6 3.6 180 180", "users": "O3.8 3.6 1.6 A3.8 9 3 180 180 O7.1 3.1 1.3",
    "mail": "R1 2.5 8 5.5 M1 2.7 L5 6 L9 2.7", "search": "O4.2 4.2 2.8 M6.3 6.3 L9 9",
    "save": "R1.5 1.5 7 7 M3 1.5 L3 4 L7 4 L7 1.5 R3 6 4 2.5",
    "open": "M1 3 L1 8.5 L9 8.5 L9 3.8 L4.8 3.8 L4 2.6 L1 2.6 Z", "folder": "M1 3 L1 8.5 L9 8.5 L9 3.8 L4.8 3.8 L4 2.6 L1 2.6 Z",
    "new": "M2.5 1 L6.5 1 L8 2.5 L8 9 L2.5 9 Z", "file": "M2.5 1 L6.5 1 L8 2.5 L8 9 L2.5 9 Z M3.8 5 L6.7 5 M3.8 6.8 L6.7 6.8",
    "cut": "O3 7.5 1.4 O7 7.5 1.4 M3.8 6.4 L7 1 M6.2 6.4 L3 1", "copy": "R3.5 3.5 5.5 5.5 M2 6.5 L1.5 6.5 L1.5 1.5 L6.5 1.5 L6.5 2",
    "paste": "R2 2 6 7.5 R3.6 1 2.8 1.8 M3.6 5 L6.4 5 M3.6 6.8 L6.4 6.8",
    "undo": "M2 3.5 L5.5 3.5 A5.5 6 2.5 270 180 M3.6 1.9 L2 3.5 L3.6 5.1",
    "redo": "M8 3.5 L4.5 3.5 A4.5 6 2.5 270 -180 M6.4 1.9 L8 3.5 L6.4 5.1",
    "bold": "TB", "italic": "TI", "underline": "TU", "print": "R2.5 1 5 3 R1 4 8 3.5 R2.5 6 5 3",
    "chart": "M1 9 L9 9 B2 5 1.5 4 B4.5 2.5 1.5 6.5 B7 6 1.5 3",
    "bell": "M2 7.5 L8 7.5 M2.8 7.5 L2.8 4.5 A5 4.5 2.2 180 180 M7.2 4.5 L7.2 7.5 M4.2 8.8 L5.8 8.8",
    "calendar": "R1.5 2 7 7 M1.5 4.2 L8.5 4.2 M3.5 1 L3.5 3 M6.5 1 L6.5 3", "clock": "O5 5 4 M5 2.5 L5 5 L7 6",
    "info": "O5 5 4 M5 4.5 L5 7.3 F5 3 .55", "warning": "M5 1 L9.5 9 L.5 9 Z M5 4 L5 6.3 F5 7.7 .5",
    "error": "O5 5 4 M3.4 3.4 L6.6 6.6 M6.6 3.4 L3.4 6.6", "success": "O5 5 4 M3 5.2 L4.5 6.7 L7.2 3.8",
    "help": "O5 5 4 T?", "close": "M2.5 2.5 L7.5 7.5 M7.5 2.5 L2.5 7.5", "plus": "M5 1.5 L5 8.5 M1.5 5 L8.5 5",
    "minus": "M1.5 5 L8.5 5", "menu": "M1.5 2.5 L8.5 2.5 M1.5 5 L8.5 5 M1.5 7.5 L8.5 7.5",
    "star": "M5 .8 L6.2 3.6 L9.3 3.9 L7 6 L7.7 9.1 L5 7.5 L2.3 9.1 L3 6 L.7 3.9 L3.8 3.6 Z",
    "grid": "R1.5 1.5 3 3 R5.5 1.5 3 3 R1.5 5.5 3 3 R5.5 5.5 3 3",
    "list": "M3.5 2.5 L9 2.5 M3.5 5 L9 5 M3.5 7.5 L9 7.5 F1.6 2.5 .55 F1.6 5 .55 F1.6 7.5 .55",
    "table": "R1 1.5 8 7 M1 4 L9 4 M1 6.3 L9 6.3 M4 1.5 L4 8.5", "filter": "M1 1.5 L9 1.5 L6 5.2 L6 8.8 L4 7.8 L4 5.2 Z",
    "refresh": "A5 5 3.5 300 290", "play": "M3 1.5 L8.5 5 L3 8.5 Z", "pause": "B2.5 1.5 1.8 7 B5.7 1.5 1.8 7",
    "stop": "B2 2 6 6", "lock": "R2 4.5 6 4.5 A5 4.5 2 180 180", "download": "M5 1 L5 6.5 M2.8 4.5 L5 6.7 L7.2 4.5 M1.5 8.8 L8.5 8.8",
    "upload": "M5 7 L5 1.5 M2.8 3.7 L5 1.5 L7.2 3.7 M1.5 8.8 L8.5 8.8", "edit": "M2 8 L2.3 6.3 L7 1.6 L8.4 3 L3.7 7.7 Z",
    "trash": "M1.5 2.5 L8.5 2.5 M4 2.5 L4 1.3 L6 1.3 L6 2.5 M2.5 2.5 L3 9 L7 9 L7.5 2.5", "tag": "M1.2 1.2 L5 1.2 L9 5.2 L5.2 9 L1.2 5 Z",
    "phone": "R3 1 4 8 M4.5 7.6 L5.5 7.6", "globe": "O5 5 4 M1 5 L9 5 E5 5 1.8 4", "camera": "R1 3 8 5.5 O5 5.8 1.8",
    "image": "R1 1.5 8 7 M1.5 8 L4 5 L6 7 L7 6 L8.5 7.5 F6.8 3.6 .7", "music": "M4 7.5 L4 1.8 L8.5 1 L8.5 6.5 F3 7.6 1.1 F7.5 6.6 1.1",
    "video": "R1 2.5 5.8 5 M6.8 4.3 L9 3 L9 7 L6.8 5.7 Z", "database": "E5 2.3 3.5 1.3 M1.5 2.3 L1.5 7.7 M8.5 2.3 L8.5 7.7",
    "code": "M3.5 2.5 L1 5 L3.5 7.5 M6.5 2.5 L9 5 L6.5 7.5 M5.8 1.5 L4.2 8.5", "terminal": "R1 1.5 8 7 M2.5 3.8 L4.2 5.2 L2.5 6.6 M5 6.8 L7.5 6.8",
    "bug": "E5 5.8 2.2 3 M5 3 L5 8.8", "light": "O5 5 2 M5 .8 L5 1.8 M5 8.2 L5 9.2 M.8 5 L1.8 5 M8.2 5 L9.2 5",
    "dark": "A5 5 3.8 300 300", "send": "M1 4.5 L9 1 L5.5 9 L4.5 5.5 Z M4.5 5.5 L9 1", "flag": "M2 9.5 L2 1 M2 1.5 L8.5 1.5 L7 3.8 L8.5 6 L2 6",
    "pin": "O5 3.8 2.7 M5 6.5 L5 9.5", "eye": "E5 5 4.2 2.8 O5 5 1.3", "heart": "M5 8.8 L1.5 5.3 M8.5 5.3 L5 8.8 O3.3 3.5 1.85 O6.7 3.5 1.85",
    "cloud": "A3 6.3 2 90 180 A5.3 4.8 2.6 200 160 A7.5 6.5 1.8 270 180 M3 8.3 L7.5 8.3",
    "link": "M4.2 5.8 L5.8 4.2", "attach": "M7 3 L3.5 6.5",
}


def icon(p, name, r: QRectF, color):
    name = str(name or "")
    if not name:
        return
    path = GLYPHS.get(name.lower())
    if path is None:
        p.setPen(QPen(C(color), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 2, 2)
        return
    s = min(r.width(), r.height())
    x0, y0, k = r.x() + (r.width() - s) / 2, r.y() + (r.height() - s) / 2, s / 10
    lw = max(1.2, s / 11)
    pen = QPen(C(color), lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    toks = path.replace(",", " ").split()
    i, poly = 0, []

    def flush():
        if len(poly) >= 2:
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(QPolygonF(poly))
        poly.clear()

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v
    while i < len(toks):
        t = toks[i]
        c, rest = t[0], t[1:]
        if rest:
            toks[i] = rest
        else:
            i += 1
        if c == "M":
            flush()
            poly.append(QPointF(x0 + num() * k, y0 + num() * k))
        elif c == "L":
            poly.append(QPointF(x0 + num() * k, y0 + num() * k))
        elif c == "Z":
            if poly:
                poly.append(poly[0])
            flush()
        elif c in "OF":
            flush()
            cx, cy, rr = num(), num(), num()
            p.setPen(pen if c == "O" else Qt.PenStyle.NoPen)
            p.setBrush(Qt.BrushStyle.NoBrush if c == "O" else C(color))
            p.drawEllipse(QPointF(x0 + cx * k, y0 + cy * k), rr * k, rr * k)
        elif c == "E":
            flush()
            cx, cy, rx, ry = num(), num(), num(), num()
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(x0 + cx * k, y0 + cy * k), rx * k, ry * k)
        elif c in "RB":
            flush()
            rx, ry, rw, rh = num(), num(), num(), num()
            rr = QRectF(x0 + rx * k, y0 + ry * k, rw * k, rh * k)
            if c == "R":
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(C(color))
            p.drawRect(rr)
        elif c == "A":
            flush()
            cx, cy, rr, st, sw = num(), num(), num(), num(), num()
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(x0 + (cx - rr) * k, y0 + (cy - rr) * k, 2 * rr * k, 2 * rr * k), int(-st * 16), int(-sw * 16))
        elif c == "T":
            flush()
            f = QFont("Segoe UI")
            f.setPixelSize(max(6, int(s * 0.9)))
            f.setBold(True)
            p.setFont(f)
            p.setPen(C(color))
            p.drawText(QRectF(x0, y0, s, s), int(Qt.AlignmentFlag.AlignCenter), rest or toks[i - 1][1:])
            break
        else:
            break
    flush()


# ------------------------------------------------------------------ controls
def _button(p, r, props, t):
    kind = props.get("Kind", "Default")
    ac = accent(props, t)
    rad = float(props.get("CornerRadius", -1) if props.get("CornerRadius", -1) not in ("", None) else -1)
    rad = t["radius"] + 2 if rad < 0 else rad
    fore = C(props.get("ForeColor") or t["face_text"])
    if kind == "Accent":
        rrect(p, QRectF(r), ac, None, rad)
        fg = on(ac)
    elif kind == "Outline":
        rrect(p, QRectF(r), None, ac, rad)
        fg = ac
    elif kind in ("Flat", "Link"):
        fg = ac if kind == "Link" else fore
    else:
        rrect(p, QRectF(r), props.get("BackColor") or t["face"], t["border"], rad)
        fg = fore
    if not props.get("Enabled", True):
        fg = C(t["disabled"])
    font(p, props)
    drop = bool(items(props.get("DropDownItems")))
    aw = 22 if drop else 0
    body = QRectF(r).adjusted(8, 0, -8 - aw, 0)
    img, s = props.get("Image"), str(props.get("Text", ""))
    pos = props.get("ImagePosition", "Left")
    al = Qt.AlignmentFlag.AlignLeft if kind == "Link" else Qt.AlignmentFlag.AlignHCenter
    if img and pos == "Top":
        isz = 32 if r.height() >= 56 else 16
        th = QFontMetrics(p.font()).height()
        top = r.y() + (r.height() - isz - 4 - th) / 2
        icon(p, img, QRectF(body.center().x() - isz / 2, top, isz, isz), fg)
        text(p, QRectF(body.x(), top + isz + 4, body.width(), th), s, fg, Qt.AlignmentFlag.AlignHCenter)
    elif img:
        tw = QFontMetrics(p.font()).horizontalAdvance(s) if s else 0
        total = 16 + (6 + tw if s else 0)
        x = body.x() if kind == "Link" else body.x() + max(0, (body.width() - total) / 2)
        icon(p, img, QRectF(x, r.center().y() - 8, 16, 16), fg)
        if s:
            text(p, QRectF(x + 22, r.y(), body.right() - x - 22, r.height()), s, fg)
    else:
        text(p, QRectF(body.x(), r.y(), body.width(), r.height()), s, fg, al)
    if drop:
        x = r.right() - aw
        p.setPen(QPen(blend(t["face"], fg, 0.35), 1))
        p.drawLine(QPointF(x, r.y() + 6), QPointF(x, r.bottom() - 6))
        chevron(p, x + aw / 2, r.center().y(), 8, "down", fg)


def _toggle(p, r, props, t):
    ac, checked = accent(props, t), bool(props.get("Checked"))
    tw, th = 40, 20
    ty = r.y() + (r.height() - th) / 2
    fg = C(props.get("ForeColor") or t["text"])
    if checked:
        rrect(p, QRectF(r.x(), ty, tw, th), ac, None, th / 2)
    else:
        rrect(p, QRectF(r.x(), ty, tw, th), None, blend(t["border"], t["text"], .3), th / 2, 1.2)
    k = th - 6
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(on(ac) if checked else blend(t["text"], t["window"], .35))
    p.drawEllipse(QRectF(r.x() + (tw - k - 3 if checked else 3), ty + 3, k, k))
    s = props.get("OnText") if checked and props.get("OnText") else props.get("OffText") if not checked and props.get("OffText") else props.get("Text", "")
    font(p, props)
    text(p, QRectF(r.x() + tw + 8, r.y(), r.width() - tw - 8, r.height()), s, fg)


def _checkbox(p, r, props, t, radio=False):
    ac, checked = accent(props, t), bool(props.get("Checked"))
    ind = bool(props.get("Indeterminate")) and not radio
    s, by = 16, r.y() + (r.height() - 16) / 2
    box = QRectF(r.x() + 1, by, s, s)
    fg = C(props.get("ForeColor") or t["text"])
    if radio:
        p.setPen(QPen(ac if checked else blend(t["border"], t["text"], .3), 1.4))
        p.setBrush(C(t["input"]))
        p.drawEllipse(box.adjusted(.7, .7, -.7, -.7))
        if checked:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ac)
            p.drawEllipse(box.center(), 4, 4)
    else:
        if checked or ind:
            rrect(p, box, ac, None, 3 if t["radius"] else 0)
            if ind:
                rrect(p, QRectF(box.x() + 4, box.center().y() - 1, 8, 2), on(ac))
            else:
                check(p, box, on(ac))
        else:
            rrect(p, box, t["input"], blend(t["border"], t["text"], .3), 3 if t["radius"] else 0, 1.2)
    font(p, props)
    text(p, QRectF(r.x() + s + 8, r.y(), r.width() - s - 8, r.height()), props.get("Text", ""), fg)


def _radio(p, r, props, t):
    _checkbox(p, r, props, t, True)


def _tile(p, r, props, t):
    base = C(props.get("TileColor") or accent(props, t))
    rrect(p, QRectF(r), base, None, 4 if t["radius"] else 0)
    fg = on(base)
    title = props.get("Title") or props.get("Text", "")
    if r.height() < 90:
        if props.get("Image"):
            icon(p, props.get("Image"), QRectF(r.center().x() - r.height() / 4, r.center().y() - r.height() / 4, r.height() / 2, r.height() / 2), fg)
        else:
            font(p, props)
            text(p, QRectF(r), title, fg, Qt.AlignmentFlag.AlignHCenter)
        return
    if props.get("Image"):
        s = 64 if r.height() >= 200 else 40
        icon(p, props.get("Image"), QRectF(r.center().x() - s / 2, r.center().y() - s / 2 - 8, s, s), fg)
    if props.get("Count") not in (None, ""):
        font(p, props, 2.4, True)
        text(p, QRectF(r.x() + 10, r.y() + 4, r.width() - 20, QFontMetrics(p.font()).height()), props["Count"], fg,
             Qt.AlignmentFlag.AlignRight)
    font(p, props, 1.05, True)
    h = QFontMetrics(p.font()).height()
    text(p, QRectF(r.x() + 10, r.bottom() - 10 - h, r.width() - 20, h), title, fg)


def _textbox(p, r, props, t):
    ac = accent(props, t)
    err = bool(props.get("ErrorText"))
    rrect(p, QRectF(r), props.get("BackColor") or t["input"], "#C62828" if err else t["border"], t["radius"] + 1)
    x = r.x() + 8
    if props.get("Icon"):
        icon(p, props["Icon"], QRectF(x, r.y() + (r.height() - 16) / 2 if not props.get("MultiLine") else r.y() + 6, 16, 16),
             blend(t["input_text"], t["input"], .35))
        x += 22
    font(p, props)
    s = str(props.get("Text", ""))
    if s and props.get("PasswordChar"):
        s = str(props["PasswordChar"])[0] * len(s)
    right = r.right() - 8 - (22 if props.get("ShowClear") else 0) - (22 if err else 0)
    col = t["input_text"] if s else blend(t["input_text"], t["input"], .5)
    if props.get("MultiLine"):
        text(p, QRectF(x, r.y() + 5, right - x, r.height() - 10), s, col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, True)
    else:
        text(p, QRectF(x, r.y(), right - x, r.height()), s or props.get("Watermark", ""), col)
    if props.get("ShowClear") and s:
        p.setPen(QPen(blend(t["input_text"], t["input"], .3), 1.3))
        cx, cy = r.right() - 16, r.center().y()
        p.drawLine(QPointF(cx - 3.5, cy - 3.5), QPointF(cx + 3.5, cy + 3.5))
        p.drawLine(QPointF(cx + 3.5, cy - 3.5), QPointF(cx - 3.5, cy + 3.5))
    if err:
        icon(p, "error", QRectF(r.right() - 8 - 16 - (22 if props.get("ShowClear") else 0), r.center().y() - 8, 16, 16), "#C62828")
    _ = ac


def _combobox(p, r, props, t):
    rrect(p, QRectF(r), t["input"], t["border"], t["radius"] + 1)
    its = items(props.get("Items"))
    idx = int(props.get("SelectedIndex", -1) or -1) if str(props.get("SelectedIndex", "")).lstrip("-").isdigit() else -1
    font(p, props)
    x = r.x() + 8
    if 0 <= idx < len(its):
        it = its[idx]
        if it.get("Image"):
            icon(p, it["Image"], QRectF(x, r.center().y() - 8, 16, 16), t["input_text"])
            x += 22
        text(p, QRectF(x, r.y(), r.right() - 26 - x, r.height()), it.get("Text", ""), t["input_text"])
    else:
        text(p, QRectF(x, r.y(), r.right() - 26 - x, r.height()), props.get("Text") or props.get("Watermark", ""),
             t["input_text"] if props.get("Text") else blend(t["input_text"], t["input"], .5))
    chevron(p, r.right() - 13, r.center().y(), 9, "down", blend(t["input_text"], t["input"], .2), 1.5)


def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _slider(p, r, props, t):
    ac = accent(props, t)
    lo, hi, v = _num(props.get("Minimum"), 0), _num(props.get("Maximum"), 100), _num(props.get("Value"), 0)
    f = 0 if hi <= lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
    x0, x1, ty = r.x() + 10, r.right() - 10, r.bottom() - 14 if r.height() > 30 else r.center().y()
    rrect(p, QRectF(x0, ty - 2, x1 - x0, 4), blend(t["border"], t["window"], .25), None, 2)
    rrect(p, QRectF(x0, ty - 2, (x1 - x0) * f, 4), ac, None, 2)
    tick = int(_num(props.get("TickFrequency"), 0))
    if tick > 0 and hi > lo:
        p.setPen(QPen(blend(t["border"], t["window"], .2), 1))
        val = lo
        while val <= hi:
            tx = x0 + (x1 - x0) * (val - lo) / (hi - lo)
            p.drawLine(QPointF(tx, ty + 9), QPointF(tx, ty + 12))
            val += tick
    cx = x0 + (x1 - x0) * f
    p.setPen(QPen(blend(t["border"], ac, .4), 1.2))
    p.setBrush(C(t["input"]))
    p.drawEllipse(QPointF(cx, ty), 9, 9)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ac)
    p.drawEllipse(QPointF(cx, ty), 4, 4)
    if props.get("ShowValue") and r.height() > 30:
        font(p, props)
        text(p, QRectF(cx - 20, r.y(), 40, ty - 10 - r.y()), str(int(v)), t["text"], Qt.AlignmentFlag.AlignHCenter)


def _progress(p, r, props, t):
    ac = accent(props, t)
    lo, hi, v = _num(props.get("Minimum"), 0), _num(props.get("Maximum"), 100), _num(props.get("Value"), 0)
    f = 0 if hi <= lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
    track = blend(t["window"], t["text"], .18 if t["dark"] else .12)
    kind = props.get("Kind", "Bar")
    if kind == "Circle":
        s = min(r.width(), r.height())
        lw = max(3.0, s / 10)
        rr = QRectF(r.x() + (r.width() - s) / 2 + lw / 2, r.y() + (r.height() - s) / 2 + lw / 2, s - lw, s - lw)
        p.setPen(QPen(track, lw))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rr)
        p.setPen(QPen(ac, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rr, 90 * 16, int(-360 * 16 * f))
        if s >= 40 or props.get("ShowText"):
            font(p, props, 1.6 if s >= 80 else 1.0, True)
            text(p, QRectF(r), f"{round(f * 100)}%", t["text"], Qt.AlignmentFlag.AlignHCenter)
        return
    show = bool(props.get("ShowText")) and r.height() >= 14
    bh = r.height() if show or r.height() < 14 else 6
    by = r.y() + (r.height() - bh) / 2
    rad = (t["radius"] + 1) if show else bh / 2
    rrect(p, QRectF(r.x(), by, r.width(), bh), track, None, rad)
    if kind == "Marquee":
        rrect(p, QRectF(r.x() + r.width() / 3, by, r.width() / 3, bh), ac, None, rad)
    elif f > 0:
        rrect(p, QRectF(r.x(), by, max(bh if not show else 2, r.width() * f), bh), ac, None, rad)
    if show and kind != "Marquee":
        font(p, props)
        text(p, QRectF(r), f"{round(f * 100)}%", t["text"], Qt.AlignmentFlag.AlignHCenter)


def _ranges(s):
    out = []
    for part in str(s or "").split(";"):
        try:
            rng, col = part.split(":")
            a, b = rng.split("-")
            out.append((float(a), float(b), QColor(col.strip())))
        except ValueError:
            pass
    return out


def _gauge(p, r, props, t):
    ac = accent(props, t)
    lo, hi, v = _num(props.get("Minimum"), 0), _num(props.get("Maximum"), 100), _num(props.get("Value"), 0)
    span = (hi - lo) or 1
    f = max(0.0, min(1.0, (v - lo) / span))
    rngs = _ranges(props.get("Ranges"))
    col = next((c for a, b, c in rngs if a <= v <= b), ac)
    fg = C(props.get("ForeColor") or t["text"])
    track = blend(t["window"], t["text"], .18 if t["dark"] else .1)
    unit, title = str(props.get("Unit", "")), str(props.get("Title") or "")
    val = f"{v:.{int(_num(props.get('Decimals'), 0))}f}" + (f" {unit}" if unit else "")
    if props.get("Kind") == "Linear":
        font(p, props, 1.0, True)
        th = QFontMetrics(p.font()).height()
        x0, x1, y = r.x() + 8, r.right() - 8, r.bottom() - 8 - th - 10
        rrect(p, QRectF(x0, y, x1 - x0, 10), track, None, 5)
        for a, b, c in rngs:
            ra, rb = x0 + (x1 - x0) * max(0, (a - lo) / span), x0 + (x1 - x0) * min(1, (b - lo) / span)
            rrect(p, QRectF(ra, y + 7, rb - ra, 3), c)
        rrect(p, QRectF(x0, y, (x1 - x0) * f, 7), col, None, 3)
        x = x0 + (x1 - x0) * f
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fg)
        p.drawPolygon(QPolygonF([QPointF(x - 6, y - 9), QPointF(x + 6, y - 9), QPointF(x, y - 1)]))
        text(p, QRectF(x0, y + 12, x1 - x0, th), title, fg)
        text(p, QRectF(x0, y + 12, x1 - x0, th), val, fg, Qt.AlignmentFlag.AlignRight)
        return
    s = min(r.width(), r.height() * 0.98)
    lw = max(4.0, s / 12)
    d = s - lw - 4
    x, y = r.x() + (r.width() - d) / 2, r.y() + (r.height() - d * .88) / 2 + 2
    rr = QRectF(x, y, d, d)

    def arc(rect, a0, sweep, color, w):
        p.setPen(QPen(C(color), w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(rect, int(-a0 * 16), int(-sweep * 16))
    arc(rr, 135, 270, track, lw)
    inner = rr.adjusted(lw * .85, lw * .85, -lw * .85, -lw * .85)
    for a, b, c in rngs:
        fa, fb = max(0, (a - lo) / span), min(1, (b - lo) / span)
        if fb > fa:
            arc(inner, 135 + 270 * fa, 270 * (fb - fa), c, lw * .3)
    if f > 0:
        arc(rr, 135, 270 * f, col, lw)
    cx, cy = rr.center().x(), rr.center().y()
    a = math.radians(135 + 270 * f)
    nr, nw = d / 2 - lw * 1.2, max(2.0, lw * .45)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fg)
    p.drawPolygon(QPolygonF([QPointF(cx + math.cos(a) * nr, cy + math.sin(a) * nr),
                             QPointF(cx + math.cos(a + math.pi / 2) * nw, cy + math.sin(a + math.pi / 2) * nw),
                             QPointF(cx + math.cos(a - math.pi / 2) * nw, cy + math.sin(a - math.pi / 2) * nw)]))
    p.drawEllipse(QPointF(cx, cy), nw * 1.6, nw * 1.6)
    font(p, props, 1.7 if d >= 120 else 1.15, True)
    th = QFontMetrics(p.font()).height()
    vy = cy + d * .16 + nw * 1.6
    text(p, QRectF(x, vy, d, th), val, fg, Qt.AlignmentFlag.AlignHCenter)
    if title:
        font(p, props)
        text(p, QRectF(x, vy + th, d, QFontMetrics(p.font()).height() + 2), title, blend(fg, t["window"], .3), Qt.AlignmentFlag.AlignHCenter)


def _panel(p, r, props, t):
    back = C(props.get("BackColor") or card(t))
    rad = _num(props.get("CornerRadius"), -1)
    rad = t["radius"] * 2 + 2 if rad < 0 else rad
    sh = 6 if props.get("Shadow") else 0
    body = QRectF(r).adjusted(sh, sh / 2, -sh, -sh)
    for i in range(sh, 0, -1):
        rrect(p, body.adjusted(-i + 1, -i + 1 + sh / 2, i - 1, i - 1 + sh / 2), blend(t["window"], "#000000", .035 * (sh - i + 1)), None, rad + i)
    border = C(props.get("BorderColor") or blend(t["border"], back, .35))
    if props.get("GradientTo"):
        from PyQt6.QtGui import QLinearGradient
        g = QLinearGradient(body.topLeft(), body.bottomLeft())
        g.setColorAt(0, back)
        g.setColorAt(1, C(props["GradientTo"]))
        p.setPen(QPen(border, 1))
        p.setBrush(g)
        p.drawRoundedRect(body, rad, rad)
    else:
        rrect(p, body, back, border, rad)
    if props.get("Title"):
        font(p, props, 1.05, True)
        text(p, QRectF(body.x() + 12, body.y(), body.width() - 24, 30), props["Title"], props.get("ForeColor") or t["face_text"])
        p.setPen(QPen(blend(border, back, .3), 1))
        p.drawLine(QPointF(body.x() + 1, body.y() + 30), QPointF(body.right() - 1, body.y() + 30))


def _group(p, r, props, t):
    back = C(props.get("BackColor") or card(t))
    border = blend(t["border"], back, .35)
    rrect(p, QRectF(r), back, border, t["radius"] + 2)
    rrect(p, QRectF(r.x() + 1, r.y() + 1, r.width() - 2, 29), blend(back, t["text"], .04), None, t["radius"] + 1)
    collapsed = bool(props.get("Collapsed"))
    fg = props.get("ForeColor") or t["face_text"]
    chevron(p, r.x() + 16, r.y() + 15, 9, "right" if collapsed else "down", fg, 1.6)
    font(p, props, 1.0, True)
    text(p, QRectF(r.x() + 30, r.y(), r.width() - 40, 30), props.get("Title") or props.get("Text", ""), fg)
    if not collapsed:
        p.setPen(QPen(border, 1))
        p.drawLine(QPointF(r.x() + 1, r.y() + 30), QPointF(r.right() - 1, r.y() + 30))


def tab_rects(props, r, p) -> list[QRectF]:
    """Tab rectangles of RmTabStrip (also the designer's tab click: tab_at)."""
    tabs = items(props.get("TabPages"))
    pos = props.get("TabPosition", "Top")
    out = []
    if pos == "Left":
        return [QRectF(r.x(), r.y() + i * 34, 140, 34) for i in range(len(tabs))]
    if p is not None:
        fm = QFontMetrics(p.font())
    else:                                   # the designer's tab click: the same font as the drawing
        f = QFont(props.get("FontName") or "Segoe UI")
        f.setPointSizeF(max(5.0, float(props.get("FontSize", 9) or 9)))
        fm = QFontMetrics(f)
    x = r.x()
    y = r.bottom() - 34 if pos == "Bottom" else r.y()
    for it in tabs:
        tw = fm.horizontalAdvance(str(it.get("Text", ""))) if fm else 7 * len(str(it.get("Text", "")))
        w = tw + tw // 12 + 2 + 28
        w += 20 if props.get("Closable") else 0
        w += 22 if it.get("Image") else 0
        out.append(QRectF(x, y, w, 34))
        x += w
    return out


def _tabstrip(p, r, props, t):
    ac = accent(props, t)
    back = C(props.get("BackColor") or t["window"])
    page = card(t)
    bar = blend(back, t["text"], .04 if t["dark"] else .03)
    fg = C(props.get("ForeColor") or t["text"])
    p.fillRect(QRectF(r), page)
    pos = props.get("TabPosition", "Top")
    font(p, props)
    rects = tab_rects(props, r, p)
    if pos == "Left":
        p.fillRect(QRectF(r.x(), r.y(), 140, r.height()), bar)
    elif pos == "Bottom":
        p.fillRect(QRectF(r.x(), r.bottom() - 34, r.width(), 34), bar)
    else:
        p.fillRect(QRectF(r.x(), r.y(), r.width(), 34), bar)
    sel = int(_num(props.get("SelectedIndex"), 0))
    for i, (it, tr) in enumerate(zip(items(props.get("TabPages")), rects)):
        is_sel = i == sel
        if is_sel:
            p.fillRect(tr, page)
            if pos == "Left":
                rrect(p, QRectF(tr.x(), tr.y() + 6, 3, tr.height() - 12), ac)
            else:
                rrect(p, QRectF(tr.x() + 8, tr.bottom() - 3, tr.width() - 16, 3), ac)
        c = (fg if t["dark"] else ac) if is_sel else blend(fg, back, .35)
        x = tr.x() + 14
        if it.get("Image"):
            icon(p, it["Image"], QRectF(x, tr.center().y() - 8, 16, 16), c)
            x += 22
        font(p, props, 1.0, is_sel)
        text(p, QRectF(x, tr.y(), tr.right() - x - (24 if props.get("Closable") else 6), tr.height()), it.get("Text", ""), c)
        if props.get("Closable") and is_sel:
            cx, cy = tr.right() - 16, tr.center().y()
            p.setPen(QPen(c, 1.3))
            p.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy + 4))
            p.drawLine(QPointF(cx + 4, cy - 4), QPointF(cx - 4, cy + 4))
    rrect(p, QRectF(r), None, blend(t["border"], back, .4), 0)


def tab_at(props, x, y, w=0, h=0) -> int:
    """Tab index at (x, y) of an RmTabStrip / RmNavigationPane of size (w, h) in the designer, -1 = none."""
    if props.get("_type") == "RmNavigationPane" or "Pages" in props and "TabPages" not in props:
        n = len(items(props.get("Pages")))
        top = h - n * 34
        if y >= top and n:
            return min(n - 1, int((y - top) // 34))
        return -1
    from PyQt6.QtCore import QRect
    for i, tr in enumerate(tab_rects(props, QRect(0, 0, int(w), int(h)), None)):
        if tr.contains(QPointF(x, y)):
            return i
    return -1


def _navpane(p, r, props, t):
    ac = accent(props, t)
    back = C(props.get("BackColor") or card(t))
    fg = C(props.get("ForeColor") or t["face_text"])
    btn = blend(back, t["text"], .05 if t["dark"] else .035)
    line = blend(t["border"], back, .4)
    rrect(p, QRectF(r), back, line, 0)
    pages = items(props.get("Pages"))
    sel = int(_num(props.get("SelectedIndex"), 0))
    p.fillRect(QRectF(r.x() + 1, r.y() + 1, r.width() - 2, 33), blend(back, ac, .1))
    if 0 <= sel < len(pages):
        font(p, props, 1.15, True)
        text(p, QRectF(r.x() + 12, r.y(), r.width() - 24, 34), pages[sel].get("Text", ""), fg)
    top = r.bottom() - len(pages) * 34
    for i, it in enumerate(pages):
        y = top + i * 34
        p.fillRect(QRectF(r.x() + 1, y, r.width() - 2, 34), blend(btn, ac, .22) if i == sel else btn)
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(r.x(), y), QPointF(r.right(), y))
        if i == sel:
            p.fillRect(QRectF(r.x() + 1, y + 1, 3, 33), ac)
        x = r.x() + 12
        if it.get("Image"):
            icon(p, it["Image"], QRectF(x, y + 8, 18, 18), ac if i == sel else fg)
            x += 28
        font(p, props, 1.0, i == sel)
        text(p, QRectF(x, y, r.right() - x - 8, 34), it.get("Text", ""), fg)


def _dockpanel(p, r, props, t):
    back = blend(t["window"], t["text"], .06)
    p.fillRect(QRectF(r), back)
    p.setPen(QPen(blend(t["border"], back, .2), 1, Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(r).adjusted(0, 0, -1, -1))
    font(p, props, .9)
    text(p, QRectF(r.x() + 6, r.bottom() - 18, r.width() - 12, 16), "RmDockPanel - drop RmDockWindow controls here", blend(t["text"], back, .5))


def _dockwindow(p, r, props, t):
    back = C(props.get("BackColor") or t["window"])
    p.fillRect(QRectF(r), back)
    rrect(p, QRectF(r), None, blend(t["border"], back, .3), 0)
    head = blend(back, t["text"], .07)
    p.fillRect(QRectF(r.x() + 1, r.y() + 1, r.width() - 2, 25), head)
    font(p, props, 1.0, True)
    text(p, QRectF(r.x() + 8, r.y(), r.width() - 76, 26), props.get("Title") or props.get("Text", "") or props.get("Name", ""), t["text"])
    font(p, props, .85)
    text(p, QRectF(r.right() - 120, r.y(), 50, 26), str(props.get("DockSide", "Left")), blend(t["text"], head, .45), Qt.AlignmentFlag.AlignRight)
    cx, cy = r.right() - 11, r.y() + 13
    p.setPen(QPen(C(t["text"]), 1.3))
    p.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy + 4))
    p.drawLine(QPointF(cx + 4, cy - 4), QPointF(cx - 4, cy + 4))
    chevron(p, r.right() - 55, cy, 8, "down", t["text"], 1.3)


def _sidebar(p, r, props, t):
    ac = accent(props, t)
    back = C(props.get("BackColor") or (blend(t["window"], "#000000", .25) if t["dark"] else blend(t["window"], t["text"], .035)))
    fg = C(props.get("ForeColor") or t["text"])
    dim = blend(fg, back, .4)
    p.fillRect(QRectF(r), back)
    collapsed = bool(props.get("Collapsed"))
    y = r.y()
    if props.get("ShowToggle", True):
        icon(p, "menu", QRectF((r.x() + (r.width() - 18) / 2) if collapsed else r.x() + 14, y + 11, 18, 18), fg)
        if not collapsed and props.get("Text"):
            font(p, props, 1.05, True)
            text(p, QRectF(r.x() + 44, y, r.width() - 50, 40), props["Text"], fg)
        y += 40
    else:
        y += 4
    sel = str(props.get("SelectedItem", ""))

    def row(it, depth):
        nonlocal y
        if y > r.bottom():
            return
        name = str(it.get("Name") or str(it.get("Text", "")).replace(" ", ""))
        is_sel = sel and name.lower() == sel.lower()
        if is_sel:
            rrect(p, QRectF(r.x() + 4, y + 2, r.width() - 9, 30), blend(back, ac, .35 if t["dark"] else .16), None, t["radius"] + 1)
            rrect(p, QRectF(r.x() + 4, y + 8, 3, 17), ac)
        x = (r.x() + (r.width() - 18) / 2) if collapsed else r.x() + 14 + (4 if depth else 0)
        if it.get("Image"):
            icon(p, it["Image"], QRectF(x, y + 8, 18, 18), ac if is_sel else fg)
        elif collapsed:
            font(p, props)
            text(p, QRectF(r.x(), y, r.width(), 34), str(it.get("Text", " "))[:1], fg, Qt.AlignmentFlag.AlignHCenter)
        if not collapsed:
            tx = x + (28 if it.get("Image") else 0)
            font(p, props, 1.0, bool(is_sel))
            text(p, QRectF(tx, y, r.right() - tx - 40, 34), it.get("Text", ""), fg)
        if it.get("Count"):
            font(p, props, .8, True)
            s = str(it["Count"])
            bw = QFontMetrics(p.font()).horizontalAdvance(s) + 10
            bx = r.right() - bw - 3 if collapsed else r.right() - 14 - bw
            rrect(p, QRectF(bx, y + (2 if collapsed else 9), bw, 16), ac, None, 8)
            text(p, QRectF(bx, y + (2 if collapsed else 9), bw, 16), s, on(ac), Qt.AlignmentFlag.AlignHCenter)
        y += 34
    for it in items(props.get("Items")):
        ks = kids(it)
        if ks:
            if collapsed:
                p.setPen(QPen(blend(t["border"], back, .3), 1))
                p.drawLine(QPointF(r.x() + 10, y + 4), QPointF(r.right() - 10, y + 4))
                y += 9
            else:
                font(p, props, .85, True)
                chevron(p, r.x() + 17, y + 14, 7, "down", dim, 1.3)
                text(p, QRectF(r.x() + 26, y, r.width() - 30, 28), it.get("Text", ""), dim)
                y += 28
            for k in ks:
                row(k, 1)
        else:
            row(it, 0)
    p.setPen(QPen(blend(t["border"], back, .5), 1))
    p.drawLine(QPointF(r.right(), r.y()), QPointF(r.right(), r.bottom()))


def _statusbar(p, r, props, t):
    ac = accent(props, t)
    accbar = bool(props.get("AccentBar"))
    back = C(props.get("BackColor") or (ac if accbar else blend(t["window"], t["text"], .05 if t["dark"] else .04)))
    fg = C(props.get("ForeColor") or (on(ac) if accbar else t["text"]))
    p.fillRect(QRectF(r), back)
    panels = items(props.get("Panels"))
    font(p, props)
    if not panels:
        text(p, QRectF(r.x() + 8, r.y(), r.width() - 16, r.height()), props.get("Text", ""), fg)
        return
    widths = []
    for it in panels:
        w = int(_num(it.get("Width"), 0))
        if w <= 0 and it.get("Kind") == "Zoom":
            w = 160
        if w <= 0 and it.get("Kind") == "Progress":
            w = 120
        widths.append(w)
    springs = sum(1 for w in widths if w <= 0) or 1
    rest = max(0, r.width() - sum(w for w in widths if w > 0) - 4)
    x = r.x()
    for it, w in zip(panels, widths):
        w = w if w > 0 else rest / springs
        if x > r.x():
            p.setPen(QPen(blend(back, fg, .25), 1))
            p.drawLine(QPointF(x, r.y() + 5), QPointF(x, r.bottom() - 5))
        kind = it.get("Kind", "Text")
        if kind == "Progress":
            f = max(0, min(1, _num(it.get("Value"), 0) / 100))
            rrect(p, QRectF(x + 8, r.center().y() - 3, w - 16, 6), blend(back, fg, .18), None, 3)
            rrect(p, QRectF(x + 8, r.center().y() - 3, max(6, (w - 16) * f), 6), fg if accbar else ac, None, 3)
        elif kind == "Zoom":
            text(p, QRectF(x + w - 44, r.y(), 40, r.height()), f"{int(_num(it.get('Value'), 100))}%", fg, Qt.AlignmentFlag.AlignRight)
            p.setPen(QPen(blend(back, fg, .4), 1))
            p.drawLine(QPointF(x + 20, r.center().y()), QPointF(x + w - 64, r.center().y()))
        else:
            tx = x + 8
            if it.get("Image"):
                icon(p, it["Image"], QRectF(tx, r.center().y() - 7, 14, 14), fg)
                tx += 19
            text(p, QRectF(tx, r.y(), x + w - tx - 8, r.height()), it.get("Text", ""), fg)
        x += w


def _ribbon(p, r, props, t):
    ac = accent(props, t)
    back = C(props.get("BackColor") or (blend(t["window"], "#000000", .2) if t["dark"] else blend(t["window"], t["text"], .03)))
    body = card(t)
    fg = C(props.get("ForeColor") or t["text"])
    line = blend(t["border"], back, .45)
    p.fillRect(QRectF(r), back)
    qat = items(props.get("QuickAccess"))
    top = r.y() + (26 if qat else 0)
    def find(lst, name):
        for it in lst:
            if str(it.get("Name") or "").lower() == name.lower():
                return it
            hit = find(kids(it), name)
            if hit is not None:
                return hit
        return None
    for i, q in enumerate(qat):
        target = find(items(props.get("Tabs")), str(q.get("Name") or q.get("Text") or "")) or q
        icon(p, target.get("Image") or q.get("Text"), QRectF(r.x() + 6 + i * 26 + 4, r.y() + 5, 16, 16), fg)
    font(p, props)
    fm = QFontMetrics(p.font())
    app = str(props.get("AppButtonText", "File"))
    x = r.x()
    if app:
        aw = fm.horizontalAdvance(app) + 28
        rrect(p, QRectF(x, top + 2, aw, 28), ac, None, t["radius"])
        text(p, QRectF(x, top + 2, aw, 28), app, on(ac), Qt.AlignmentFlag.AlignHCenter)
        x += aw + 4
    tabs = items(props.get("Tabs"))
    collapsed = bool(props.get("Collapsed"))
    sel = int(_num(props.get("SelectedTab"), 0)) if str(props.get("SelectedTab", "0")).isdigit() else 0
    if not collapsed:
        p.fillRect(QRectF(r.x(), top + 30, r.width(), r.height() - (top - r.y()) - 30), body)
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(r.x(), top + 30), QPointF(r.right(), top + 30))
    for i, tab in enumerate(tabs):
        w = fm.horizontalAdvance(str(tab.get("Text", ""))) + 28
        tr = QRectF(x, top, w, 30)
        if i == sel and not collapsed:
            p.fillRect(tr.adjusted(0, 3, 0, 1), body)
            p.setPen(QPen(line, 1))
            p.drawLine(tr.topLeft() + QPointF(0, 3), tr.bottomLeft())
            p.drawLine(tr.topRight() + QPointF(0, 3), tr.bottomRight())
            p.drawLine(tr.topLeft() + QPointF(0, 3), tr.topRight() + QPointF(0, 3))
        if i == sel:
            rrect(p, QRectF(tr.x() + 10, tr.bottom() - 3, tr.width() - 20, 2), tab.get("Color") or ac)
        text(p, tr.adjusted(0, 2, 0, 0), tab.get("Text", ""), tab.get("Color") or ((fg if t["dark"] else ac) if i == sel else fg),
             Qt.AlignmentFlag.AlignHCenter)
        x += w
    chevron(p, r.right() - 15, top + 15, 8, "down" if collapsed else "up", fg, 1.3)
    if collapsed or not (0 <= sel < len(tabs)):
        return
    gx, gy, gh = r.x() + 4, top + 33, 90
    for grp in kids(tabs[sel]):
        colx = gx + 6
        row = 0
        colw = 0
        for it in kids(grp):
            if it.get("Text") == "-":
                if row:
                    colx += colw + 6
                    row, colw = 0, 0
                p.setPen(QPen(blend(line, body, .3), 1))
                p.drawLine(QPointF(colx + 3, gy + 4), QPointF(colx + 3, gy + gh - 22))
                colx += 6
                continue
            large = it.get("Large") or it.get("Size") == "Large"
            if large:
                if row:
                    colx += colw + 6
                    row, colw = 0, 0
                w = max(48, fm.horizontalAdvance(str(it.get("Text", ""))) + 12)
                icon(p, it.get("Image") or "star", QRectF(colx + (w - 32) / 2, gy + 8, 32, 32), ac)
                text(p, QRectF(colx + 2, gy + 44, w - 4, 30), it.get("Text", ""), fg,
                     Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, True)
                colx += w + 2
            else:
                w = 130 if it.get("Kind") == "Combo" else 34 + fm.horizontalAdvance(str(it.get("Text", ""))) + (12 if kids(it) else 0)
                y = gy + 3 + row * 24
                if it.get("Checked"):
                    rrect(p, QRectF(colx, y, w, 22), blend(body, ac, .2), blend(body, ac, .5), t["radius"] + 1)
                if it.get("Kind") == "Combo":
                    lw = fm.horizontalAdvance(str(it.get("Text", ""))) + 6
                    text(p, QRectF(colx, y, lw, 22), it.get("Text", ""), fg)
                    rrect(p, QRectF(colx + lw, y + 1, w - lw, 20), t["input"], t["border"], 2)
                    text(p, QRectF(colx + lw + 5, y, w - lw - 20, 22), it.get("Value", ""), t["input_text"])
                else:
                    if it.get("Image"):
                        icon(p, it["Image"], QRectF(colx + 4, y + 3, 16, 16), ac)
                    text(p, QRectF(colx + 26, y, w - 28, 22), it.get("Text", ""), fg)
                colw = max(colw, w)
                row += 1
                if row == 3:
                    colx += colw + 2
                    row, colw = 0, 0
        if row:
            colx += colw + 2
        gw = max(colx - gx + 4, fm.horizontalAdvance(str(grp.get("Text", ""))) + 16)
        text(p, QRectF(gx, gy + gh - 18, gw, 18), grp.get("Text", ""), blend(fg, body, .4), Qt.AlignmentFlag.AlignHCenter)
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(gx + gw + 1, gy + 4), QPointF(gx + gw + 1, gy + gh - 4))
        gx += gw + 3


def _columns(props) -> list[dict]:
    v = props.get("Columns")
    s = v if isinstance(v, str) else json.dumps(v or [])
    if s.strip().startswith("["):
        try:
            return [c if isinstance(c, dict) else {"Text": str(c)} for c in json.loads(s)]
        except ValueError:
            return []
    out = []
    for part in [x for x in s.split(";") if x]:
        bits = part.split(":")
        out.append({"Text": bits[0], "Type": bits[1] if len(bits) > 1 else "Text", "Width": int(_num(bits[2], 0)) if len(bits) > 2 else 0})
    return out


def _rows(props, key="Rows") -> list[list[str]]:
    v = props.get(key)
    if isinstance(v, list):
        return [[str(c) for c in (r if isinstance(r, list) else [r])] for r in v]
    s = str(v or "").strip()
    if s.startswith("["):
        try:
            data = json.loads(s)
        except ValueError:
            return []
        out = []
        for r in data:
            if isinstance(r, dict):
                out.append([str(r.get("Text", ""))] + [str(x) for x in (r.get("SubItems") or [])] + ["\x01" + str(r.get("Image", ""))])
            elif isinstance(r, list):
                out.append([str(x) for x in r])
            else:
                out.append([str(r)])
        return out
    return [row.split("|") for row in s.split(";")] if s else []


def _grid(p, r, props, t):
    ac = accent(props, t)
    back = C(props.get("BackColor") or t["input"])
    fg = C(props.get("ForeColor") or t["input_text"])
    line = blend(t["border"], back, .55)
    head = blend(back, t["text"], .08 if t["dark"] else .045)
    alt = blend(back, t["text"], .035 if t["dark"] else .022)
    p.fillRect(QRectF(r), back)
    cols = _columns(props)
    rows = _rows(props)
    hh, fh, rh = 30, 26 if props.get("AllowFilter") else 0, int(_num(props.get("RowHeight"), 0)) or 28
    p.fillRect(QRectF(r.x(), r.y(), r.width(), hh), head)
    xs, x = [], r.x()
    for c in cols:
        w = int(_num(c.get("Width"), 0)) or 110
        xs.append((x, w))
        font(p, props, 1.0, True)
        typ = c.get("Type", "Text")
        al = Qt.AlignmentFlag.AlignRight if typ == "Number" else Qt.AlignmentFlag.AlignHCenter if typ in ("Check", "Image") else Qt.AlignmentFlag.AlignLeft
        text(p, QRectF(x + 8, r.y(), w - 16, hh), c.get("Text", ""), fg, al)
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(x + w - 1, r.y() + 6), QPointF(x + w - 1, r.y() + hh - 6))
        x += w
    if fh:
        for (x, w) in xs:
            icon(p, "filter", QRectF(x + 6, r.y() + hh + 7, 12, 12), blend(fg, back, .55))
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(r.x(), r.y() + hh + fh - 1), QPointF(r.right(), r.y() + hh + fh - 1))
    y = r.y() + hh + fh
    font(p, props)
    for i, row in enumerate(rows):
        if y > r.bottom():
            break
        if props.get("AlternatingRows", True) and i % 2:
            p.fillRect(QRectF(r.x(), y, r.width(), rh), alt)
        for k, (x, w) in enumerate(xs):
            v = row[k] if k < len(row) else ""
            typ = cols[k].get("Type", "Text")
            if typ == "Check":
                box = QRectF(x + (w - 16) / 2, y + (rh - 16) / 2, 16, 16)
                if str(v).lower() in ("true", "1", "yes"):
                    rrect(p, box, ac, None, 3)
                    check(p, box, on(ac))
                else:
                    rrect(p, box, t["input"], blend(t["border"], fg, .2), 3)
            elif typ == "Progress":
                f = max(0, min(1, _num(v, 0) / 100))
                bw = w - 16 - 34
                rrect(p, QRectF(x + 8, y + rh / 2 - 4, bw, 8), blend(back, fg, .15), None, 4)
                rrect(p, QRectF(x + 8, y + rh / 2 - 4, max(8, bw * f), 8), ac, None, 4)
                text(p, QRectF(x + 8 + bw + 4, y, 30, rh), v, fg, Qt.AlignmentFlag.AlignRight)
            elif typ == "Button":
                rrect(p, QRectF(x + 5, y + 4, w - 10, rh - 8), t["face"], t["border"], t["radius"] + 1)
                text(p, QRectF(x + 5, y + 4, w - 10, rh - 8), v or cols[k].get("Text", ""), t["face_text"], Qt.AlignmentFlag.AlignHCenter)
            elif typ == "Image":
                icon(p, v, QRectF(x + (w - 18) / 2, y + (rh - 18) / 2, 18, 18), ac)
            else:
                text(p, QRectF(x + 8, y, w - 16, rh), v, fg, Qt.AlignmentFlag.AlignRight if typ == "Number" else Qt.AlignmentFlag.AlignLeft)
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(r.x(), y + rh - 1), QPointF(r.right(), y + rh - 1))
        y += rh
    rrect(p, QRectF(r), None, blend(t["border"], back, .3), 0)


def _listview(p, r, props, t):
    view = str(props.get("View", "Details"))
    if view in ("Details", "List", ""):
        cols = _columns(props) or [{"Text": "Name"}]
        rows = [[c for c in row if not str(c).startswith("\x01")] for row in _rows(props, "Items")]
        return _grid(p, r, {**props, "Columns": json.dumps(cols), "Rows": json.dumps(rows), "AllowFilter": False}, t)
    ac = accent(props, t)
    back = C(props.get("BackColor") or t["input"])
    fg = C(props.get("ForeColor") or t["input_text"])
    p.fillRect(QRectF(r), back)
    cards = view.startswith("Card")
    cw, ch = (236, 120) if cards else (220, 64)
    per = max(1, int(r.width() // cw))
    cols = _columns(props)
    for i, row in enumerate(_rows(props, "Items")):
        img = next((c[1:] for c in row if str(c).startswith("\x01")), "")
        cells = [c for c in row if not str(c).startswith("\x01")]
        x, y = r.x() + (i % per) * cw + 4, r.y() + (i // per) * (ch + 8) + 4
        if y > r.bottom():
            break
        rrect(p, QRectF(x, y, cw - 8, ch), card(t), blend(t["border"], card(t), .4), 6 if cards else t["radius"] + 1)
        font(p, props, 1.0, True)
        if cards:
            text(p, QRectF(x + 12, y + 12, cw - 60, 24), cells[0] if cells else "", fg)
            if img:
                icon(p, img, QRectF(x + cw - 44, y + 12, 24, 24), ac)
            font(p, props)
            for k in range(1, min(len(cols), 4)):
                text(p, QRectF(x + 12, y + 42 + (k - 1) * 19, 80, 18), cols[k].get("Text", ""), blend(fg, back, .45))
                text(p, QRectF(x + 96, y + 42 + (k - 1) * 19, cw - 116, 18), cells[k] if k < len(cells) else "", fg)
        else:
            if img:
                icon(p, img, QRectF(x + 12, y + 16, 32, 32), ac)
            tx = x + (54 if img else 12)
            text(p, QRectF(tx, y + 10, cw - tx + x - 16, 20), cells[0] if cells else "", fg)
            font(p, props)
            text(p, QRectF(tx, y + 32, cw - tx + x - 16, 20), cells[1] if len(cells) > 1 else "", blend(fg, back, .35))


def _treeview(p, r, props, t):
    ac = accent(props, t)
    back = C(props.get("BackColor") or t["input"])
    fg = C(props.get("ForeColor") or t["input_text"])
    p.fillRect(QRectF(r), back)
    font(p, props)
    y = r.y()

    def walk(nodes, depth):
        nonlocal y
        for n in nodes:
            if y > r.bottom():
                return
            ks = kids(n)
            x = r.x() + 6 + depth * 18
            if ks or n.get("Lazy"):
                chevron(p, x + 9, y + 13, 8, "down" if n.get("Expanded") else "right", blend(fg, back, .3), 1.4)
            x += 18
            if props.get("CheckBoxes"):
                box = QRectF(x, y + 5, 15, 15)
                if n.get("Checked"):
                    rrect(p, box, ac, None, 3)
                    check(p, box, on(ac))
                else:
                    rrect(p, box, t["input"], blend(t["border"], fg, .2), 3)
                x += 22
            if n.get("Image"):
                icon(p, n["Image"], QRectF(x, y + 5, 16, 16), blend(ac, fg, .3))
                x += 22
            text(p, QRectF(x, y, r.right() - x - 4, 26), n.get("Text", ""), fg)
            y += 26
            if ks and n.get("Expanded"):
                walk(ks, depth + 1)
    walk(items(props.get("Nodes")), 0)
    rrect(p, QRectF(r), None, blend(t["border"], back, .3), 0)


def _calendar(p, r, props, t):
    import datetime as dt
    ac = accent(props, t)
    back = C(props.get("BackColor") or t["input"])
    fg = C(t["text"])
    rrect(p, QRectF(r), back, blend(t["border"], back, .3), t["radius"] + 2)
    try:
        d = dt.date.fromisoformat(str(props.get("Value") or ""))
    except ValueError:
        d = dt.date.today()
    x, y, w, h = r.x() + 4, r.y() + 4, r.width() - 8, r.height() - 8
    cw, ch = w / 7, h / 8
    font(p, props, 1.1, True)
    text(p, QRectF(x + cw, y, w - 2 * cw, ch), d.strftime("%B %Y"), fg, Qt.AlignmentFlag.AlignHCenter)
    chevron(p, x + cw / 2, y + ch / 2, ch * .32, "left", fg, 1.5)
    chevron(p, x + w - cw / 2, y + ch / 2, ch * .32, "right", fg, 1.5)
    font(p, props)
    for i, n in enumerate(["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]):
        text(p, QRectF(x + i * cw, y + ch, cw, ch), n, blend(fg, back, .55), Qt.AlignmentFlag.AlignHCenter)
    first = d.replace(day=1)
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    for i in range(42):
        day = start + dt.timedelta(days=i)
        cx, cy = x + (i % 7) * cw, y + 2 * ch + (i // 7) * ch
        s = min(cw, ch) * .86
        if day == d:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ac)
            p.drawEllipse(QRectF(cx + (cw - s) / 2, cy + (ch - s) / 2, s, s))
        text(p, QRectF(cx, cy, cw, ch), str(day.day), on(ac) if day == d else (fg if day.month == d.month else blend(fg, back, .55)),
             Qt.AlignmentFlag.AlignHCenter)


def _datepicker(p, r, props, t):
    import datetime as dt
    rrect(p, QRectF(r), t["input"], t["border"], t["radius"] + 1)
    try:
        d = dt.date.fromisoformat(str(props.get("Value") or ""))
    except ValueError:
        d = dt.date.today()
    fmt = str(props.get("Format") or "Short")
    s = d.strftime("%A, %B %d, %Y") if fmt == "Long" else d.isoformat() if fmt in ("ISO", "yyyy-MM-dd") else d.strftime("%d/%m/%Y")
    font(p, props)
    text(p, QRectF(r.x() + 8, r.y(), r.width() - 38, r.height()), s, t["input_text"])
    icon(p, "calendar", QRectF(r.right() - 24, r.center().y() - 8, 16, 16), blend(t["input_text"], t["input"], .3))


def _timepicker(p, r, props, t):
    rrect(p, QRectF(r), t["input"], t["border"], t["radius"] + 1)
    v = str(props.get("Value") or "12:00:00")
    parts = (v.split(":") + ["00", "00"])[:3]
    fmt = str(props.get("Format") or "HH:mm")
    secs = "ss" in fmt or props.get("ShowSeconds")
    s = " : ".join(parts[:3] if secs else parts[:2])
    font(p, props)
    text(p, QRectF(r.x() + 10, r.y(), r.width() - 30, r.height()), s, t["input_text"])
    chevron(p, r.right() - 12, r.y() + r.height() * .32, 7, "up", blend(t["input_text"], t["input"], .3), 1.3)
    chevron(p, r.right() - 12, r.y() + r.height() * .68, 7, "down", blend(t["input_text"], t["input"], .3), 1.3)


def _component(p, r, props, t, glyph):
    """Non-visual components are shown in the component tray; this draws their icon if asked."""
    icon(p, glyph, QRectF(r).adjusted(2, 2, -2, -2), accent(props, t))


PAINTERS = {
    "RmButton": _button, "RmToggle": _toggle, "RmCheckBox": _checkbox, "RmRadioButton": _radio, "RmTile": _tile,
    "RmTextBox": _textbox, "RmComboBox": _combobox, "RmSlider": _slider, "RmProgress": _progress, "RmGauge": _gauge,
    "RmPanel": _panel, "RmGroupPanel": _group, "RmTabStrip": _tabstrip, "RmNavigationPane": _navpane,
    "RmDockPanel": _dockpanel, "RmDockWindow": _dockwindow, "RmSideBar": _sidebar, "RmStatusBar": _statusbar,
    "RmRibbon": _ribbon, "RmGrid": _grid, "RmListView": _listview, "RmTreeView": _treeview, "RmCalendar": _calendar,
    "RmDatePicker": _datepicker, "RmTimePicker": _timepicker,
    "RmToast": lambda p, r, pr, t: _component(p, r, pr, t, "bell"),
    "RmSuperTooltip": lambda p, r, pr, t: _component(p, r, pr, t, "info"),
    "RmBalloonTip": lambda p, r, pr, t: _component(p, r, pr, t, "help"),
    "RmMessageBox": lambda p, r, pr, t: _component(p, r, pr, t, "warning"),
}


def paint_control(type_name: str, painter, rect, props: dict, ctx=None) -> None:
    t = theme(props)
    painter.setRenderHint(painter.RenderHint.Antialiasing)
    painter.setRenderHint(painter.RenderHint.TextAntialiasing)
    r = QRectF(rect)
    if not props.get("Enabled", True):
        painter.setOpacity(0.55)
    PAINTERS.get(type_name, _dockpanel)(painter, r, props, t)
    painter.setOpacity(1.0)


__all__ = ["DESIGN_THEME", "GLYPHS", "PAINTERS", "THEMES", "paint_control", "tab_at"]
