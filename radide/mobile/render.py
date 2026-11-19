"""Design-time rendering of the mobile controls (Material 3 look) for the form designer.

`make_mobile_preview()` / `apply_mobile_props()` are called by radide/preview.py for every mobile control
type (and, inside a phone frame, for the classic Button / Label / TextBox / CheckBox / RadioButton so a
phone form looks like a phone app).  The previews paint themselves with QPainter - no real widgets -
and are transparent for the mouse (the designer's overlay owns the input).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

from ..controls import split_items, split_rows
from .controls import LAYOUT_TYPES, MOBILE_CONTROL_TYPES
from .material_icons import draw_icon, resolve

# Material 3 baseline colour scheme (Flutter's default light ColorScheme, seed deep purple)
M3 = {
    "primary": "#6750A4", "on_primary": "#FFFFFF", "primary_container": "#EADDFF",
    "on_primary_container": "#21005D", "secondary_container": "#E8DEF8", "surface": "#FEF7FF",
    "surface_low": "#F7F2FA", "surface_container": "#F3EDF7", "surface_high": "#ECE6F0",
    "surface_variant": "#E7E0EC", "on_surface": "#1D1B20", "on_surface_variant": "#49454F",
    "outline": "#79747E", "outline_variant": "#CAC4D0", "shadow": "#000000", "inverse_primary": "#D0BCFF",
}
# classic controls drawn the Material way when they sit on a phone form
MATERIAL_CLASSIC = ("Button", "Label", "TextBox", "CheckBox", "RadioButton", "LinkLabel")
LAYOUT_TAG = {"Column": "Column ↓", "Row": "Row →", "Stack": "Stack ⧉"}


def in_phone(widget: QWidget | None) -> bool:
    """True when *widget* is (inside) the design surface of a phone form."""
    while widget is not None:
        v = widget.property("rad_phone")
        if v is not None:
            return bool(v)
        widget = widget.parentWidget()
    return False


def wants_mobile_preview(type_name: str, parent: QWidget | None) -> bool:
    return type_name in MOBILE_CONTROL_TYPES or (type_name in MATERIAL_CLASSIC and in_phone(parent))


class MobilePreview(QWidget):
    """A self-painting Material preview of one control."""
    rad_mobile = True

    def __init__(self, type_name: str, parent: QWidget | None, root: Path | None = None):
        super().__init__(parent)
        self.type = type_name
        self.props: dict = {}
        self.root = Path(root) if root else None
        self._pix_key = None
        self._pix = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ------------------------------------------------------------ helpers
    def c(self, prop: str, default: str) -> QColor:
        v = self.props.get(prop) or ""
        return QColor(v) if v and QColor(v).isValid() else QColor(default)

    def _font(self, size_delta: float = 0, bold: bool | None = None) -> QFont:
        p = self.props
        f = QFont(p.get("FontName") or "Segoe UI")
        f.setPointSizeF(max(1.0, float(p.get("FontSize", 11) or 11) + size_delta))
        f.setBold(bool(p.get("FontBold")) if bold is None else bold)
        f.setItalic(bool(p.get("FontItalic")))
        return f

    def form(self):
        w = self.parentWidget()
        while w is not None:
            view = getattr(w, "view", None)
            if view is not None and hasattr(view, "doc"):
                return view.doc.form
            w = w.parentWidget()
        return None

    def image(self, path: str) -> QPixmap:
        key = (path, str(self.root))
        if key != self._pix_key:
            self._pix_key = key
            pm = QPixmap()
            if path:
                full = Path(path) if Path(path).is_absolute() else (self.root or Path(".")) / path
                pm = QPixmap(str(full))
            self._pix = pm
        return self._pix

    # ------------------------------------------------------------ paint
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fn = getattr(self, "_paint_" + self.type, None)
        r = QRectF(0, 0, self.width(), self.height())
        if fn is not None:
            fn(p, r)
        elif self.type in LAYOUT_TYPES:
            self._paint_layout(p, r)
        p.end()

    def _shadow(self, p: QPainter, r: QRectF, radius: float, depth: int) -> None:
        for i in range(max(0, min(8, depth)), 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 14))
            p.drawRoundedRect(r.adjusted(-i * 0.3, i * 0.5, i * 0.3, i * 0.9), radius + i * 0.5, radius + i * 0.5)

    def _text(self, p, rect, text, color, font, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
        p.setFont(font)
        p.setPen(QColor(color))
        fm = QFontMetrics(font)
        p.drawText(rect, int(align), fm.elidedText(str(text), Qt.TextElideMode.ElideRight, int(max(1, rect.width()))))

    # --- mobile controls ------------------------------------------------
    def _paint_AppBar(self, p, r):
        back = self.c("BackColor", M3["surface_container"])
        fore = self.c("ForeColor", M3["on_surface"]).name()
        p.fillRect(r, back)
        p.fillRect(QRectF(r.left(), r.bottom() - 1, r.width(), 1), QColor(0, 0, 0, 28))
        x = 4.0
        form = self.form()
        if form is not None and any(c.type == "Drawer" for c in form.controls):
            draw_icon(p, QRectF(x + 12, r.center().y() - 12, 24, 24), "menu", fore)
            x += 48
        else:
            x += 12
        actions = split_items(self.props.get("Actions", ""))
        right = r.right() - 4
        for a in reversed(actions):
            name = resolve(a)
            if name:
                right -= 48
                draw_icon(p, QRectF(right + 12, r.center().y() - 12, 24, 24), name, fore)
            else:
                f = self._font(-2, bold=True)
                w = QFontMetrics(f).horizontalAdvance(a) + 24
                right -= w
                self._text(p, QRectF(right, r.top(), w, r.height()), a, M3["primary"], f, Qt.AlignmentFlag.AlignCenter)
        self._text(p, QRectF(x, r.top(), max(1.0, right - x), r.height()), self.props.get("Title", ""), fore,
                   self._font())

    def _paint_BottomNav(self, p, r):
        p.fillRect(r, self.c("BackColor", M3["surface_container"]))
        items = split_items(self.props.get("Items", "")) or ["Home"]
        sel = int(self.props.get("SelectedIndex", 0) or 0)
        w = r.width() / len(items)
        fore = self.c("ForeColor", M3["on_surface_variant"]).name()
        top = r.top() + max(6.0, (r.height() - 56) / 2)
        for i, text in enumerate(items):
            cx = r.left() + w * i + w / 2
            if i == sel:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(M3["secondary_container"]))
                p.drawRoundedRect(QRectF(cx - 32, top, 64, 32), 16, 16)
            draw_icon(p, QRectF(cx - 12, top + 4, 24, 24), resolve(text, "circle"),
                      M3["on_primary_container"] if i == sel else fore)
            self._text(p, QRectF(cx - w / 2, top + 34, w, 18), text,
                       M3["on_surface"] if i == sel else fore, self._font(0, bold=i == sel),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    def _paint_Fab(self, p, r):
        body = r.adjusted(1, 1, -2, -3)
        self._shadow(p, body, 16, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.c("BackColor", M3["primary_container"]))
        p.drawRoundedRect(body, min(16.0, body.height() / 3.5), min(16.0, body.height() / 3.5))
        s = min(24.0, body.width() * 0.45)
        draw_icon(p, QRectF(body.center().x() - s / 2, body.center().y() - s / 2, s, s),
                  self.props.get("Icon") or "add", self.c("ForeColor", M3["on_primary_container"]).name())

    def _paint_Card(self, p, r):
        elev = int(self.props.get("Elevation", 1) or 0)
        body = r.adjusted(1, 1, -2, -3)
        self._shadow(p, body, 12, elev * 2)
        p.setPen(QPen(QColor(M3["outline_variant"]), 1) if elev == 0 else Qt.PenStyle.NoPen)
        p.setBrush(self.c("BackColor", M3["surface_low"]))
        p.drawRoundedRect(body, 12, 12)

    def _paint_MListView(self, p, r):
        p.fillRect(r, self.c("BackColor", M3["surface"]))
        fields = [f.strip().lower() for f in str(self.props.get("ItemTemplate", "title") or "title").split("|")]
        rows = split_rows(self.props.get("Items", "")) or [["Item"]]
        two = "subtitle" in fields
        h = 72.0 if two else 56.0
        fore = self.c("ForeColor", M3["on_surface"]).name()
        y = r.top()
        p.save()
        p.setClipRect(r)
        for row in rows:
            if y > r.bottom():
                break
            vals = {f: (row[i] if i < len(row) else "") for i, f in enumerate(fields)}
            x = r.left() + 16
            if "icon" in fields:
                name = resolve(vals.get("icon", ""))
                cy = y + h / 2
                if name:
                    draw_icon(p, QRectF(x, cy - 12, 24, 24), name, M3["on_surface_variant"])
                else:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(M3["primary_container"]))
                    p.drawEllipse(QRectF(x, cy - 20, 40, 40))
                    initial = (vals.get("title") or vals.get("icon") or "?")[:1].upper()
                    self._text(p, QRectF(x, cy - 20, 40, 40), initial, M3["on_primary_container"],
                               self._font(1), Qt.AlignmentFlag.AlignCenter)
                x += 56
            right = r.right() - 16
            if "trailing" in fields:
                t = vals.get("trailing", "")
                if resolve(t) or not t:
                    draw_icon(p, QRectF(right - 24, y + h / 2 - 12, 24, 24), resolve(t, "chevron_right"),
                              M3["on_surface_variant"])
                    right -= 32
                else:
                    f = self._font(-1)
                    tw = QFontMetrics(f).horizontalAdvance(t) + 8
                    self._text(p, QRectF(right - tw, y, tw, h), t, M3["on_surface_variant"], f,
                               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    right -= tw + 8
            title = vals.get("title", row[0] if row else "")
            tw = max(1.0, right - x)
            if two:
                self._text(p, QRectF(x, y + 12, tw, 24), title, fore, self._font(1))
                self._text(p, QRectF(x, y + 36, tw, 22), vals.get("subtitle", ""), M3["on_surface_variant"],
                           self._font(-1))
            else:
                self._text(p, QRectF(x, y, tw, h), title, fore, self._font(1))
            y += h
            p.fillRect(QRectF(r.left() + 16, y - 1, r.width() - 32, 1), QColor(M3["outline_variant"]))
        p.restore()

    def _paint_Switch(self, p, r):
        on = bool(self.props.get("Checked"))
        tw, th = min(52.0, r.width()), min(32.0, r.height())
        track = QRectF(r.left(), r.center().y() - th / 2, tw, th)
        p.setPen(Qt.PenStyle.NoPen if on else QPen(QColor(M3["outline"]), 2))
        p.setBrush(self.c("BackColor", M3["primary"]) if on else QColor(M3["surface_high"]))
        p.drawRoundedRect(track.adjusted(1, 1, -1, -1), th / 2 - 1, th / 2 - 1)
        p.setPen(Qt.PenStyle.NoPen)
        if on:
            d = th - 8
            p.setBrush(QColor(M3["on_primary"]))
            p.drawEllipse(QRectF(track.right() - 4 - d, track.top() + 4, d, d))
        else:
            d = th / 2
            p.setBrush(QColor(M3["outline"]))
            p.drawEllipse(QRectF(track.left() + th / 2 - d / 2, track.center().y() - d / 2, d, d))

    def _paint_MSlider(self, p, r):
        lo, hi = int(self.props.get("Minimum", 0) or 0), int(self.props.get("Maximum", 100) or 0)
        v = int(self.props.get("Value", 0) or 0)
        frac = 0.0 if hi <= lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
        left, right = r.left() + 10, r.right() - 10
        cy = r.center().y()
        x = left + (right - left) * frac
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(M3["secondary_container"]))
        p.drawRoundedRect(QRectF(left, cy - 3, right - left, 6), 3, 3)
        primary = self.c("ForeColor", M3["primary"])
        p.setBrush(primary)
        p.drawRoundedRect(QRectF(left, cy - 3, x - left, 6), 3, 3)
        p.drawEllipse(QPointF(x, cy), 10, 10)

    def _paint_MTextField(self, p, r):
        self._outlined_field(p, r, str(self.props.get("Text", "") or ""), str(self.props.get("Hint", "") or ""),
                             bool(self.props.get("Password")))

    def _outlined_field(self, p, r, text, hint, password):
        box = r.adjusted(1, 7 if text else 1, -1, -1)
        p.setPen(QPen(QColor(M3["outline"]), 1))
        p.setBrush(self.c("BackColor", "#00000000"))
        p.drawRoundedRect(box, 4, 4)
        fore = self.c("ForeColor", M3["on_surface"]).name()
        inner = box.adjusted(16, 0, -16, 0)
        if text:
            shown = "•" * len(text) if password else text
            self._text(p, inner, shown, fore, self._font(1))
            if hint:
                f = self._font(-2)
                w = QFontMetrics(f).horizontalAdvance(hint) + 8
                lab = QRectF(box.left() + 12, r.top(), w, 14)
                back = self.props.get("BackColor") or M3["surface"]
                p.fillRect(lab, QColor(back))
                self._text(p, lab, hint, M3["on_surface_variant"], f, Qt.AlignmentFlag.AlignCenter)
        else:
            self._text(p, inner, hint, M3["on_surface_variant"], self._font(1))

    def _paint_MImage(self, p, r):
        pm = self.image(str(self.props.get("Image", "") or ""))
        if pm.isNull():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(M3["surface_variant"]))
            p.drawRoundedRect(r, 8, 8)
            s = min(48.0, r.width() * 0.4, r.height() * 0.4)
            draw_icon(p, QRectF(r.center().x() - s / 2, r.center().y() - s / 2, s, s), "image",
                      M3["on_surface_variant"])
            return
        fit = self.props.get("Fit", "Cover")
        pw, ph = pm.width(), pm.height()
        if fit == "Fill":
            target = r
        elif fit == "None":
            target = QRectF(r.center().x() - pw / 2, r.center().y() - ph / 2, pw, ph)
        else:
            sx, sy = r.width() / pw, r.height() / ph
            s = {"Cover": max(sx, sy), "Contain": min(sx, sy), "FitWidth": sx, "FitHeight": sy}.get(fit, max(sx, sy))
            target = QRectF(r.center().x() - pw * s / 2, r.center().y() - ph * s / 2, pw * s, ph * s)
        p.save()
        p.setClipRect(r)
        p.drawPixmap(target, pm, QRectF(0, 0, pw, ph))
        p.restore()

    def _paint_MIcon(self, p, r):
        s = min(r.width(), r.height())
        draw_icon(p, QRectF(r.center().x() - s / 2, r.center().y() - s / 2, s, s),
                  self.props.get("Icon") or "star", self.c("ForeColor", M3["on_surface_variant"]).name())

    def _paint_Drawer(self, p, r):
        path = QPainterPath()
        path.addRoundedRect(r.adjusted(-20, 0, -1, 0), 16, 16)
        clip = QPainterPath()
        clip.addRect(r)
        p.fillRect(QRectF(r.right() - 2, r.top(), 2, r.height()), QColor(0, 0, 0, 30))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.c("BackColor", M3["surface_low"]))
        p.drawPath(path.intersected(clip))
        fore = self.c("ForeColor", M3["on_surface_variant"]).name()
        form = self.form()
        title = str(form.props.get("Text", "")) if form is not None else "Menu"
        self._text(p, QRectF(r.left() + 28, r.top() + 12, r.width() - 40, 44), title or "Menu",
                   M3["on_surface_variant"], self._font(0, bold=True))
        y = r.top() + 60
        for i, text in enumerate(split_items(self.props.get("Items", ""))):
            if y + 56 > r.bottom() + 1:
                break
            item = QRectF(r.left() + 12, y, r.width() - 24, 56)
            if i == 0:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(M3["secondary_container"]))
                p.drawRoundedRect(item, 28, 28)
            draw_icon(p, QRectF(item.left() + 16, item.center().y() - 12, 24, 24), resolve(text, "circle"),
                      M3["on_primary_container"] if i == 0 else fore)
            self._text(p, item.adjusted(56, 0, -12, 0), text, M3["on_surface"] if i == 0 else fore,
                       self._font(0, bold=i == 0))
            y += 56

    def _paint_MTabBar(self, p, r):
        p.fillRect(r, self.c("BackColor", M3["surface"]))
        tabs = split_items(self.props.get("Tabs", "")) or ["Tab 1"]
        sel = int(self.props.get("SelectedIndex", 0) or 0)
        w = r.width() / len(tabs)
        primary = self.c("ForeColor", M3["primary"]).name()
        p.fillRect(QRectF(r.left(), r.bottom() - 1, r.width(), 1), QColor(M3["surface_variant"]))
        for i, text in enumerate(tabs):
            tr = QRectF(r.left() + w * i, r.top(), w, r.height())
            f = self._font(0, bold=True)
            self._text(p, tr, text, primary if i == sel else M3["on_surface_variant"], f, Qt.AlignmentFlag.AlignCenter)
            if i == sel:
                tw = min(w - 8, QFontMetrics(f).horizontalAdvance(text) + 8)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(primary))
                p.drawRoundedRect(QRectF(tr.center().x() - tw / 2, r.bottom() - 3, tw, 3), 1.5, 1.5)

    def _paint_MWebView(self, p, r):
        p.fillRect(r, QColor("#FFFFFF"))
        p.setPen(QPen(QColor(M3["outline_variant"]), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(r.adjusted(0, 0, -1, -1))
        bar = QRectF(r.left() + 8, r.top() + 8, r.width() - 16, 28)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(M3["surface_high"]))
        p.drawRoundedRect(bar, 14, 14)
        draw_icon(p, QRectF(bar.left() + 8, bar.center().y() - 8, 16, 16), "lock", M3["on_surface_variant"])
        self._text(p, bar.adjusted(30, 0, -10, 0), self.props.get("Url", ""), M3["on_surface_variant"], self._font(-2))
        s = min(56.0, r.width() * 0.3, max(8.0, r.height() - 60))
        body = QRectF(r.left(), bar.bottom(), r.width(), r.bottom() - bar.bottom())
        draw_icon(p, QRectF(body.center().x() - s / 2, body.center().y() - s / 2 - 8, s, s), "public",
                  M3["outline_variant"])
        self._text(p, QRectF(body.left(), body.center().y() + s / 2 - 4, body.width(), 20), "WebView",
                   M3["outline"], self._font(-2), Qt.AlignmentFlag.AlignCenter)

    def _paint_layout(self, p, r):
        if self.props.get("BackColor"):
            p.fillRect(r, QColor(self.props["BackColor"]))
        p.setPen(QPen(QColor(103, 80, 164, 150), 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(r.adjusted(0, 0, -1, -1))
        pad = int(self.props.get("Padding", 0) or 0)
        if pad > 0 and r.width() > 2 * pad and r.height() > 2 * pad:
            p.setPen(QPen(QColor(103, 80, 164, 60), 1, Qt.PenStyle.DotLine))
            p.drawRect(r.adjusted(pad, pad, -pad - 1, -pad - 1))
        f = QFont("Segoe UI", 7)
        tag = LAYOUT_TAG.get(self.type, self.type)
        tw = QFontMetrics(f).horizontalAdvance(tag) + 8
        # tag corner by kind, so the tags of nested Column / Row / Stack do not cover each other
        x = r.right() - tw if self.type == "Row" else r.left()
        y = r.bottom() - 13 if self.type == "Stack" else r.top()
        box = QRectF(x, y, tw, 13)
        p.fillRect(box, QColor(103, 80, 164, 200))
        self._text(p, box, tag, "#FFFFFF", f, Qt.AlignmentFlag.AlignCenter)

    # --- classic controls on a phone form --------------------------------
    def _paint_Button(self, p, r):
        body = r.adjusted(0.5, 0.5, -0.5, -0.5)
        rad = min(20.0, body.height() / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.c("BackColor", M3["primary"]))
        p.drawRoundedRect(body, rad, rad)
        align = {"Left": Qt.AlignmentFlag.AlignLeft, "Right": Qt.AlignmentFlag.AlignRight}.get(
            self.props.get("TextAlign", "Center"), Qt.AlignmentFlag.AlignHCenter)
        self._text(p, body.adjusted(16, 0, -16, 0), self.props.get("Text", ""),
                   self.c("ForeColor", M3["on_primary"]).name(), self._font(0, bold=True),
                   align | Qt.AlignmentFlag.AlignVCenter)

    def _paint_Label(self, p, r):
        if self.props.get("BackColor"):
            p.fillRect(r, QColor(self.props["BackColor"]))
        align = {"Center": Qt.AlignmentFlag.AlignHCenter, "Right": Qt.AlignmentFlag.AlignRight}.get(
            self.props.get("TextAlign", "Left"), Qt.AlignmentFlag.AlignLeft)
        self._text(p, r, self.props.get("Text", ""), self.c("ForeColor", M3["on_surface"]).name(), self._font(),
                   align | Qt.AlignmentFlag.AlignVCenter)

    def _paint_LinkLabel(self, p, r):
        f = self._font()
        f.setUnderline(True)
        self._text(p, r, self.props.get("Text", ""), self.props.get("LinkColor") or M3["primary"], f)

    def _paint_TextBox(self, p, r):
        self._outlined_field(p, r, str(self.props.get("Text", "") or ""), "", bool(self.props.get("PasswordChar")))

    def _paint_CheckBox(self, p, r):
        on = bool(self.props.get("Checked"))
        box = QRectF(r.left() + 3, r.center().y() - 9, 18, 18)
        p.setPen(Qt.PenStyle.NoPen if on else QPen(QColor(M3["on_surface_variant"]), 2))
        p.setBrush(QColor(M3["primary"]) if on else Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(box.adjusted(1, 1, -1, -1), 2, 2)
        if on:
            draw_icon(p, box.adjusted(1, 1, -1, -1), "check", M3["on_primary"])
        self._text(p, r.adjusted(30, 0, 0, 0), self.props.get("Text", ""),
                   self.c("ForeColor", M3["on_surface"]).name(), self._font())

    def _paint_RadioButton(self, p, r):
        on = bool(self.props.get("Checked"))
        c = QPointF(r.left() + 12, r.center().y())
        p.setPen(QPen(QColor(M3["primary"] if on else M3["on_surface_variant"]), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, 9, 9)
        if on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(M3["primary"]))
            p.drawEllipse(c, 5, 5)
        self._text(p, r.adjusted(30, 0, 0, 0), self.props.get("Text", ""),
                   self.c("ForeColor", M3["on_surface"]).name(), self._font())


# ------------------------------------------------------------------ preview.py hooks
def make_mobile_preview(ctrl, parent: QWidget, root: Path | None = None) -> MobilePreview:
    w = MobilePreview(ctrl.type, parent, root)
    apply_mobile_props(w, ctrl)
    w.show()
    return w


def apply_mobile_props(w: MobilePreview, ctrl) -> None:
    p = ctrl.props
    w.setObjectName(f"rad_{ctrl.name}")
    w.props = dict(p)
    w.setGeometry(int(p["Left"]), int(p["Top"]), max(4, int(p["Width"])), max(4, int(p["Height"])))
    w.setToolTip(str(p.get("ToolTip", "")))
    w.setGraphicsEffect(None)
    faded = not p.get("Visible", True) or not p.get("Enabled", True)
    if faded:                      # invisible / disabled controls stay visible at design time, faded
        eff = QGraphicsOpacityEffect(w)
        eff.setOpacity(0.4)
        w.setGraphicsEffect(eff)
    w.update()


# ------------------------------------------------------------------ toolbox icons
_TOOL_ICON = {"AppBar": "web", "BottomNav": "home", "Fab": "add", "Card": "tab", "MListView": "list",
              "Switch": "toggle_on", "MSlider": "tune", "MTextField": "text_fields", "MImage": "image",
              "MIcon": "star", "Drawer": "menu", "MTabBar": "tab", "MWebView": "public"}


def mobile_tool_icon(type_name: str, color: str = "#7A62C9") -> QIcon:
    """20x20 Toolbox icon of a mobile control."""
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    purple = QColor(M3["primary"])
    if type_name == "Fab":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(M3["primary_container"]))
        p.drawRoundedRect(QRectF(1, 1, 18, 18), 5, 5)
        draw_icon(p, QRectF(4, 4, 12, 12), "add", M3["on_primary_container"])
    elif type_name == "AppBar":
        p.setPen(QPen(QColor(color), 1))
        p.setBrush(QColor("#ffffff"))
        p.drawRect(QRectF(1.5, 2.5, 17, 15))
        p.fillRect(QRectF(2, 3, 16, 5), purple)
    elif type_name == "BottomNav":
        p.setPen(QPen(QColor(color), 1))
        p.setBrush(QColor("#ffffff"))
        p.drawRect(QRectF(1.5, 2.5, 17, 15))
        p.fillRect(QRectF(2, 12, 16, 5), purple)
        for x in (4, 9, 14):
            p.fillRect(QRectF(x, 14, 2, 2), QColor("#ffffff"))
    elif type_name == "Card":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawRoundedRect(QRectF(2, 5, 17, 13), 3, 3)
        p.setBrush(QColor("#ffffff"))
        p.setPen(QPen(QColor(color), 1))
        p.drawRoundedRect(QRectF(1.5, 3.5, 16, 12), 3, 3)
    elif type_name in LAYOUT_TYPES:
        p.setPen(QPen(QColor(color), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(1.5, 1.5, 17, 17))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(purple)
        if type_name == "Column":
            for y in (4, 8.5, 13):
                p.drawRect(QRectF(4, y, 12, 3))
        elif type_name == "Row":
            for x in (4, 8.5, 13):
                p.drawRect(QRectF(x, 4, 3, 12))
        else:
            p.setBrush(QColor(103, 80, 164, 120))
            p.drawRect(QRectF(4, 4, 9, 9))
            p.setBrush(purple)
            p.drawRect(QRectF(8, 8, 8, 8))
    else:
        draw_icon(p, QRectF(1, 1, 18, 18), _TOOL_ICON.get(type_name, "circle"),
                  color)
    p.end()
    return QIcon(pm)
