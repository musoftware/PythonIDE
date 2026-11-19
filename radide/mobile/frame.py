"""Phone frame, device bar and Column / Row / Stack layout for the form designer (CONTRACTS 10.1).

* `PhoneChrome` is attached to every DesignerView (radide/designer.py calls its hooks).  For a mobile
  form (plugin `is_mobile = True`, or a form with a `Device` property) it draws a phone / tablet around
  the design surface - bezel, status bar with clock / signal / battery, camera cut-out, gesture bar or
  home indicator and the safe-area outline - and shows the *device bar* (device preset + Portrait /
  Landscape).  The form's Width / Height follow the device's safe area.
* `layout_containers(form)` lays out the children of Column / Row / Stack controls (called from
  radide/layout.py:relayout, so the designer, undo and paste all keep them laid out); dragging a child
  inside its container reorders it (`place_in_flow`).
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QToolButton, QWidget

from .controls import (DEVICES, LAYOUT_TYPES, ORIENTATIONS, device, ensure_mobile_props, is_mobile_form,
                       landscape, safe_area_size, safe_insets, screen_size, supported_controls)

BAR_H = 34          # device bar height
GAP = 10


# ====================================================================== container layout
def _dragging(form) -> set:
    return form.__dict__.get("_rad_drag") or set()


def set_dragging(form, ctrls) -> None:
    """Controls being dragged by the mouse are left where the mouse puts them (their siblings close up)."""
    form.__dict__["_rad_drag"] = {id(c) for c in ctrls}


def _set(c, **values) -> bool:
    changed = False
    for k, v in values.items():
        v = int(round(v))
        if int(c.props.get(k, 0) or 0) != v:
            c.props[k] = v
            changed = True
    return changed


def layout_container(form, cont) -> list:
    """Position the children of one Column / Row / Stack. Returns the controls that moved."""
    if cont.type not in LAYOUT_TYPES:
        return []
    p = cont.props
    pad = max(0, int(p.get("Padding", 0) or 0))
    gap = int(p.get("Spacing", 0) or 0)
    align = str(p.get("Align", "Start") or "Start")
    cw, ch = int(p.get("Width", 0) or 0), int(p.get("Height", 0) or 0)
    drag = _dragging(form)
    kids = [k for k in form.children(cont.name) if id(k) not in drag]
    changed = []
    pos = pad
    if align in ("SpaceBetween", "SpaceAround") and kids and cont.type in ("Column", "Row"):
        size_key = "Height" if cont.type == "Column" else "Width"
        free = (ch if cont.type == "Column" else cw) - 2 * pad - sum(int(k.props.get(size_key, 0) or 0)
                                                                     for k in kids)
        if align == "SpaceBetween":
            gap = free / (len(kids) - 1) if len(kids) > 1 else 0
        else:
            gap = free / len(kids)
            pos = pad + gap / 2
        gap = max(0, gap)
    for k in kids:
        kw, kh = int(k.props.get("Width", 0) or 0), int(k.props.get("Height", 0) or 0)
        vals: dict = {}
        if cont.type == "Column":
            vals["Top"] = pos
            if align == "Stretch":
                vals["Left"], vals["Width"] = pad, max(8, cw - 2 * pad)
            else:
                vals["Left"] = {"Center": (cw - kw) / 2, "End": cw - pad - kw}.get(align, pad)
            pos += kh + gap
        elif cont.type == "Row":
            vals["Left"] = pos
            if align == "Stretch":
                vals["Top"], vals["Height"] = pad, max(8, ch - 2 * pad)
            else:
                vals["Top"] = {"Center": (ch - kh) / 2, "End": ch - pad - kh}.get(align, pad)
            pos += kw + gap
        else:                                   # Stack
            if align == "Center":
                vals = {"Left": (cw - kw) / 2, "Top": (ch - kh) / 2}
            elif align == "End":
                vals = {"Left": cw - pad - kw, "Top": ch - pad - kh}
            elif align == "Stretch":
                vals = {"Left": pad, "Top": pad, "Width": max(8, cw - 2 * pad), "Height": max(8, ch - 2 * pad)}
        if vals and _set(k, **vals):
            changed.append(k)
    return changed


def layout_containers(form) -> list:
    """Lay out every Column / Row / Stack of *form*, outer containers first."""
    changed = []
    for c in form.ordered():
        if c.type in LAYOUT_TYPES:
            changed += layout_container(form, c)
    return changed


def is_flow(form, ctrl) -> bool:
    parent = form.find(ctrl.parent) if ctrl.parent else None
    return parent is not None and parent.type in ("Column", "Row")


def flow_index(form, ctrl, point=None) -> int:
    """Index among its siblings where *ctrl* belongs, from its centre (or *point*, relative to the
    container's client area) along the container's axis."""
    cont = form.find(ctrl.parent)
    vertical = cont.type == "Column"
    if point is None:
        point = (int(ctrl.props["Left"]) + int(ctrl.props["Width"]) / 2,
                 int(ctrl.props["Top"]) + int(ctrl.props["Height"]) / 2)
    at = point[1] if vertical else point[0]
    idx = 0
    for k in form.children(cont.name):
        if k is ctrl:
            continue
        mid = (int(k.props["Top"]) + int(k.props["Height"]) / 2) if vertical else \
              (int(k.props["Left"]) + int(k.props["Width"]) / 2)
        if at > mid:
            idx += 1
    return idx


def place_in_flow(form, ctrl, point=None) -> bool:
    """Move *ctrl* in the z-order (= child order) of its Column / Row to where it was dropped."""
    if not is_flow(form, ctrl):
        return False
    idx = flow_index(form, ctrl, point)
    siblings = [k for k in form.children(ctrl.parent) if k is not ctrl]
    current = form.children(ctrl.parent).index(ctrl)
    if current == idx:
        return False
    form.controls.remove(ctrl)
    if idx < len(siblings):
        form.controls.insert(form.controls.index(siblings[idx]), ctrl)
    else:
        after = siblings[-1] if siblings else None
        form.controls.insert(form.controls.index(after) + 1 if after is not None else len(form.controls), ctrl)
    return True


# ====================================================================== phone geometry
def bezel(dev, orientation) -> tuple[int, int, int, int]:
    if dev.home_button:
        return (70, 14, 70, 14) if landscape(orientation) else (14, 70, 14, 70)
    b = 16 if dev.tablet else 12
    return b, b, b, b


def phone_geometry(device_id, orientation):
    """(frame size, screen rect in frame coords, safe-area rect in frame coords) for a preset."""
    dev = device(device_id)
    sw, sh = screen_size(device_id, orientation)
    bl, bt, br, bb = bezel(dev, orientation)
    il, it, ir, ib = safe_insets(device_id, orientation)
    screen = QRect(bl, bt, sw, sh)
    safe = QRect(bl + il, bt + it, sw - il - ir, sh - it - ib)
    return (sw + bl + br, sh + bt + bb), screen, safe


# ====================================================================== device bar
class DeviceBar(QWidget):
    """Device preset + Portrait / Landscape above the phone (uses the IDE theme's palette)."""

    def __init__(self, chrome: "PhoneChrome", parent: QWidget):
        super().__init__(parent)
        self.chrome = chrome
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(QLabel("Device:"))
        self.combo = QComboBox()
        for d in DEVICES.values():
            self.combo.addItem(d.name, d.id)
        self.combo.setToolTip("Phone / tablet the form is designed for (form property Device)")
        self.combo.activated.connect(lambda i: chrome.set_device(self.combo.itemData(i)))
        lay.addWidget(self.combo)
        self.buttons = {}
        for o in ORIENTATIONS:
            b = QToolButton()
            b.setText(o)
            b.setCheckable(True)
            b.setAutoRaise(True)
            b.setToolTip(f"{o} orientation (form property Orientation)")
            b.clicked.connect(lambda _=False, o=o: chrome.set_orientation(o))
            lay.addWidget(b)
            self.buttons[o] = b
        self.size_label = QLabel()
        lay.addWidget(self.size_label)
        lay.addStretch(1)
        try:
            from .. import theme
            theme.role(self.size_label, "muted")
        except Exception:  # noqa: BLE001 - theme roles are cosmetic
            pass

    def sync(self, props: dict) -> None:
        self.combo.blockSignals(True)
        i = self.combo.findData(props.get("Device"))
        self.combo.setCurrentIndex(max(0, i))
        self.combo.blockSignals(False)
        for o, b in self.buttons.items():
            b.setChecked(o == props.get("Orientation", "Portrait"))
        w, h = safe_area_size(props.get("Device"), props.get("Orientation"))
        sw, sh = screen_size(props.get("Device"), props.get("Orientation"))
        self.size_label.setText(f"{sw} x {sh} dp  (safe area {w} x {h})")


# ====================================================================== the chrome
class PhoneChrome:
    """Mobile mode of one DesignerView (see the module docstring)."""

    def __init__(self, view):
        self.view = view
        self.active = False
        self.bar: DeviceBar | None = None
        self._plugin_key = None
        self._plugin = None
        self._orig_style = view.content.styleSheet()
        self._orig_name = view.content.objectName()
        self._syncing = False
        try:
            from .. import theme
            theme.changed.connect(self._on_theme)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ state
    @property
    def doc(self):
        return self.view.doc

    def plugin(self):
        """The language plugin of the form (from the project next to the .form), or None."""
        path = getattr(self.doc, "path", None)
        key = (str(path), self.doc.form.name)
        if key != self._plugin_key:
            self._plugin_key, self._plugin = key, None
            try:
                from ..languages import get_plugin
                from ..model import Project
                folder = path.parent
                if (folder / Project.FILE).exists():
                    proj = Project.load(folder)
                    self._plugin = get_plugin(proj.form_language(self.doc.form.name))
            except Exception:  # noqa: BLE001 - no project / unknown plugin: desktop form
                self._plugin = None
        return self._plugin

    def refresh(self) -> None:
        """Called at the start of DesignerView.rebuild(): decide the mode and prepare the form."""
        try:
            self.active = is_mobile_form(self.doc.form, self.plugin())
        except Exception:  # noqa: BLE001
            self.active = False
        v = self.view
        v.surface.setProperty("rad_phone", self.active)
        if self.active:
            ensure_mobile_props(self.doc.form.props)
            from ..layout import relayout
            relayout(self.doc.form)        # docked AppBar / BottomNav and Column / Row children in place
            if self.bar is None:
                self.bar = DeviceBar(self, v.content)
            self.bar.sync(self.doc.form.props)
            self.bar.show()
        elif self.bar is not None:
            self.bar.hide()
        self._apply_canvas_style()
        self.announce()

    def _apply_canvas_style(self) -> None:
        c = self.view.content
        if self.active:
            try:
                from .. import theme
                back = theme.color("designer_back")
            except Exception:  # noqa: BLE001
                back = "#FFFFFF"
            c.setObjectName("rad_canvas")
            c.setStyleSheet(f"QWidget#rad_canvas {{ background: {back}; }}")
        elif c.objectName() == "rad_canvas":
            c.setObjectName(self._orig_name)
            c.setStyleSheet(self._orig_style)

    def _on_theme(self, *_a) -> None:
        try:
            if self.active:
                self._apply_canvas_style()
                self.view.update()
        except RuntimeError:          # the designer was closed
            pass

    def announce(self) -> None:
        """Tell the Toolbox whether the shown designer is a phone form (Mobile group, greyed Windows controls)."""
        try:
            if not self.view.isVisible():
                return
            from ..toolbox import TOOL_STATE
            if hasattr(TOOL_STATE, "set_mode"):
                TOOL_STATE.set_mode(self.active, supported_controls(self.plugin()) if self.active else None)
        except RuntimeError:
            pass

    # ------------------------------------------------------------ device changes
    def set_device(self, device_id: str) -> None:
        if device_id in DEVICES and device_id != self.doc.form.props.get("Device"):
            self.doc.set_prop(None, "Device", device_id)

    def set_orientation(self, orientation: str) -> None:
        if orientation in ORIENTATIONS and orientation != self.doc.form.props.get("Orientation"):
            self.doc.set_prop(None, "Orientation", orientation)
        elif self.bar is not None:
            self.bar.sync(self.doc.form.props)

    def _sync_size(self) -> None:
        """Width / Height follow Device + Orientation (anchored / docked controls follow the new size)."""
        if self._syncing:
            return
        fp = self.doc.form.props
        w, h = safe_area_size(fp.get("Device"), fp.get("Orientation"))
        if int(fp.get("Width", 0) or 0) == w and int(fp.get("Height", 0) or 0) == h:
            return
        self._syncing = True
        try:
            self.doc.set_prop(None, "Width", w, record=False)
            self.doc.set_prop(None, "Height", h, record=False)
        finally:
            self._syncing = False

    # ------------------------------------------------------------ designer hooks
    def layout(self) -> bool:
        """DesignerView.layout_form hook: geometry of the phone, the surface and the tray."""
        if not self.active:
            return False
        v = self.view
        fp = self.doc.form.props
        if fp.get("Device") not in DEVICES or fp.get("Orientation") not in ORIENTATIONS:
            ensure_mobile_props(fp)
        self._sync_size()
        (fw, fh), _screen, safe = phone_geometry(fp["Device"], fp["Orientation"])
        bar_w = max(fw, self.bar.sizeHint().width()) if self.bar is not None else fw
        total_w = max(bar_w + 2 * GAP, fw + 2 * GAP, v.viewport().width())
        x = max(GAP, (total_w - fw) // 2)
        top = GAP + BAR_H + GAP
        if self.bar is not None:
            self.bar.sync(fp)
            self.bar.setGeometry(max(GAP, (total_w - bar_w) // 2), GAP, bar_w, BAR_H)
        v.frame.setGeometry(x, top, fw, fh)
        v.surface.setGeometry(safe)
        v.overlay.setGeometry(0, 0, safe.width(), safe.height())
        tray_h = 40 if v.tray.isVisibleTo(v.content) else 0
        v.tray.setGeometry(0, top + fh + GAP, total_w, tray_h)
        v.content.resize(total_w, top + fh + GAP + tray_h + 4)
        v.frame.update()
        v.surface.update()
        return True

    def form_back(self) -> str:
        return self.doc.form.props.get("BackColor") or "#FEF7FF"

    def paint_surface(self, p: QPainter, surface: QWidget) -> bool:
        if not self.active:
            return False
        p.fillRect(surface.rect(), QColor(self.form_back()))
        p.setPen(QColor(0, 0, 0, 38))
        for x in range(0, surface.width(), 8):
            for y in range(0, surface.height(), 8):
                p.drawPoint(x, y)
        return True

    def _top_bar_color(self) -> QColor:
        """The status bar takes the colour of an AppBar at the top (as in Flutter), else the form's."""
        for c in self.doc.form.controls:
            if c.type == "AppBar" and not c.parent and int(c.props.get("Top", 1) or 0) == 0:
                return QColor(c.props.get("BackColor") or "#F3EDF7")
        return QColor(self.form_back())

    def paint(self, p: QPainter, frame: QWidget) -> bool:
        """FormFrame.paintEvent hook: draw the device."""
        if not self.active:
            return False
        fp = self.doc.form.props
        dev = device(fp.get("Device"))
        orient = fp.get("Orientation", "Portrait")
        land = landscape(orient)
        _size, screen, safe = phone_geometry(dev.id, orient)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(frame.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        outer_r = 36 if dev.home_button else dev.radius + 12
        p.setPen(QPen(QColor("#4A4A50"), 1.5))
        p.setBrush(QColor("#1B1B1F"))
        p.drawRoundedRect(body, outer_r, outer_r)
        p.setPen(QPen(QColor("#2E2E34"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body.adjusted(3, 3, -3, -3), outer_r - 3, outer_r - 3)
        # screen
        sr = QRectF(screen)
        path = QPainterPath()
        path.addRoundedRect(sr, dev.radius, dev.radius)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.form_back()))
        p.drawPath(path)
        p.save()
        p.setClipPath(path)
        il, it, ir, ib = safe_insets(dev.id, orient)
        if it:
            p.fillRect(QRectF(sr.left(), sr.top(), sr.width(), it), self._top_bar_color())
            self._status_bar(p, QRectF(sr.left(), sr.top(), sr.width(), it), dev)
        if il or ir:                    # landscape iPhone: hatched unsafe strips
            hatch = QBrush(QColor(0, 0, 0, 22), Qt.BrushStyle.BDiagPattern)
            if il:
                p.fillRect(QRectF(sr.left(), sr.top(), il, sr.height()), hatch)
            if ir:
                p.fillRect(QRectF(sr.right() - ir, sr.top(), ir, sr.height()), hatch)
        if ib:
            self._bottom_bar(p, QRectF(sr.left() + il, sr.bottom() - ib, sr.width() - il - ir, ib), dev)
        # camera cut-out
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#000000"))
        if dev.cutout == "island":
            if land:
                p.drawRoundedRect(QRectF(sr.left() + 11, sr.center().y() - 63, 37, 126), 18.5, 18.5)
            else:
                p.drawRoundedRect(QRectF(sr.center().x() - 63, sr.top() + 11, 126, 37), 18.5, 18.5)
        elif dev.cutout == "punch":
            c = QPointF(sr.left() + 12, sr.center().y()) if land else QPointF(sr.center().x(), sr.top() + 12)
            p.drawEllipse(c, 6, 6)
        p.restore()
        # safe-area outline
        p.setPen(QPen(QColor(103, 80, 164, 120), 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(safe).adjusted(-1, -1, 0, 0))
        if dev.home_button:            # iPhone SE chin: speaker + home button
            p.setPen(QPen(QColor("#55555C"), 2))
            if land:
                cx = body.right() - 35
                p.drawEllipse(QPointF(cx, body.center().y()), 20, 20)
                p.setBrush(QColor("#3A3A40"))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(body.left() + 32, body.center().y() - 24, 5, 48), 2.5, 2.5)
            else:
                cy = body.bottom() - 35
                p.drawEllipse(QPointF(body.center().x(), cy), 20, 20)
                p.setBrush(QColor("#3A3A40"))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(body.center().x() - 24, body.top() + 32, 48, 5), 2.5, 2.5)
        if self.doc.selected is None:   # the form is selected
            try:
                from .. import theme
                accent = theme.color("highlight")
            except Exception:  # noqa: BLE001
                accent = "#316AC5"
            p.setPen(QPen(QColor(accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(body.adjusted(1, 1, -1, -1), outer_r, outer_r)
        return True

    @staticmethod
    def _ink_for(back: QColor) -> QColor:
        return QColor("#FFFFFF") if back.lightnessF() < 0.5 else QColor("#1D1B20")

    def _status_bar(self, p: QPainter, r: QRectF, dev) -> None:
        ink = self._ink_for(self._top_bar_color())
        ios = dev.platform == "ios"
        f = QFont("Segoe UI", 9 if not ios else 10, QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(ink)
        if ios and dev.cutout == "island":
            left = QRectF(r.left(), r.top() + 10, r.width() / 2 - 63, r.height() - 10)
            p.drawText(left, int(Qt.AlignmentFlag.AlignCenter), "9:41")
        else:
            p.drawText(QRectF(r.left() + (16 if not ios else 8), r.top(), 60, r.height()),
                       int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), "9:41")
        # right side: signal, wifi, battery
        cy = r.top() + (r.height() / 2 + (5 if ios and dev.cutout == "island" else 0))
        x = r.right() - (16 if not ios else 22)
        p.setPen(QPen(ink, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x - 22, cy - 5.5, 22, 11), 3, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ink)
        p.drawRoundedRect(QRectF(x - 20, cy - 3.5, 15, 7), 1.5, 1.5)
        p.drawRect(QRectF(x + 1, cy - 2, 1.5, 4))
        x -= 30
        from .material_icons import draw_icon
        draw_icon(p, QRectF(x - 14, cy - 7, 14, 14), "wifi", ink.name())
        x -= 20
        for i in range(4):
            h = 3 + i * 2.5
            p.drawRect(QRectF(x - 14 + i * 4, cy + 5 - h, 3, h))

    def _bottom_bar(self, p: QPainter, r: QRectF, dev) -> None:
        ink = self._ink_for(QColor(self.form_back()))
        p.setPen(Qt.PenStyle.NoPen)
        if dev.platform == "ios":
            p.setBrush(ink)
            p.drawRoundedRect(QRectF(r.center().x() - 67, r.bottom() - 13, 134, 5), 2.5, 2.5)
        elif r.height() >= 40:            # 3-button navigation
            col = QColor(ink)
            col.setAlpha(170)
            p.setPen(QPen(col, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            cx, cy = r.center().x(), r.center().y()
            tri = QPainterPath()
            tri.moveTo(cx - 88, cy)
            tri.lineTo(cx - 76, cy - 8)
            tri.lineTo(cx - 76, cy + 8)
            tri.closeSubpath()
            p.drawPath(tri)
            p.drawEllipse(QPointF(cx, cy), 8, 8)
            p.drawRoundedRect(QRectF(cx + 74, cy - 7, 14, 14), 2, 2)
        else:                             # gesture navigation pill
            p.setBrush(ink)
            p.drawRoundedRect(QRectF(r.center().x() - 54, r.center().y() - 2, 108, 4), 2, 2)

    # ------------------------------------------------------------ drag & drop inside Column / Row
    def begin_drag(self, ctrls) -> None:
        set_dragging(self.doc.form, [c for c in ctrls if is_flow(self.doc.form, c)])

    def end_drag(self, moved) -> None:
        """Mouse released: dropped children of a Column / Row take the place where they were dropped."""
        form = self.doc.form
        had = bool(_dragging(form))
        set_dragging(form, [])
        reordered = False
        for c in moved:
            if c in form.controls and place_in_flow(form, c):
                reordered = True
        if reordered:
            self.doc._normalize()
        if had or reordered:
            self.doc._relayout()
            if reordered:
                self.doc.structureChanged.emit()
            self.doc.set_modified()

    def placed(self, ctrl, pos=None) -> None:
        """A new control was created at *pos* (overlay coordinates): put it at that place in a Column / Row."""
        form = self.doc.form
        if not is_flow(form, ctrl):
            return
        point = None
        if pos is not None:
            ox, oy = form.client_origin(form.find(ctrl.parent))
            point = (pos.x() - ox, pos.y() - oy)
        if place_in_flow(form, ctrl, point):
            self.doc._normalize()
            self.doc._relayout()
            self.doc.structureChanged.emit()
