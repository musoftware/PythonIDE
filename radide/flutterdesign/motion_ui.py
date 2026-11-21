"""Flutter designer UI for motion, layout variants and foldables (plan MOTION_VARIANTS_FOLDABLES.md, slice F).

* ``SizeBar``      - "Edit: All sizes | This size only", the size being edited, the foldable posture, Sizes...
                     and Side-by-side (a second tool bar row of the designer)
* ``SideBySide``   - every size of the screen rendered next to each other (Qt preview)
* ``RowsDialog``   - a small table editor (state variables, timelines, sizes)
* ``KeyframesDialog`` - the keyframe tracks of a keyframes animation
* ``WhenDialog``   - animate a property with a state variable ($when) or a timeline ($timeline)
* ``paint_hinge`` / ``paint_size_frame`` - canvas decorations (hinge / crease, orange This-size frame)
"""
from __future__ import annotations

import copy
import json

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGridLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea,
                             QSpinBox, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from . import model as M
from . import motion as MO
from . import variants_fd as VF

ORANGE = QColor("#FFF7630C")


def _devices():
    from .. import devices as D
    return D


# ============================================================================================ canvas
def paint_hinge(p: QPainter, screen: QRectF, zoom: float, rect, kind: str, posture: str) -> None:
    """The hinge / crease of a foldable over the device screen (*rect* = devices.hinge_screen_rect, dp)."""
    if rect is None:
        return
    x, y, w, h = rect
    r = QRectF(screen.x() + x * zoom, screen.y() + y * zoom, max(w * zoom, 0.0), max(h * zoom, 0.0))
    vertical = h >= w
    p.save()
    if kind == "dual" and posture != "Folded":
        p.fillRect(r, QColor("#FF202124"))          # an opaque bezel band between the two screens
    else:
        line = QRectF(r.center().x() - .5, r.y(), 1, r.height()) if vertical else \
            QRectF(r.x(), r.center().y() - .5, r.width(), 1)
        if posture == "HalfOpened":
            g = QLinearGradient(QPointF(line.center().x(), 0), QPointF(screen.right(), 0)) if vertical else \
                QLinearGradient(QPointF(0, line.center().y()), QPointF(0, screen.bottom()))
            g.setColorAt(0, QColor(0, 0, 0, 70))
            g.setColorAt(1, QColor(0, 0, 0, 10))
            half = QRectF(line.center().x(), screen.y(), screen.right() - line.center().x(), screen.height()) \
                if vertical else QRectF(screen.x(), line.center().y(), screen.width(), screen.bottom() - line.center().y())
            p.fillRect(half, g)
            p.setPen(QPen(QColor(0, 0, 0, 140), 1.5))
        else:
            p.setPen(QPen(QColor(0, 0, 0, 90), 1, Qt.PenStyle.DashLine))
        if vertical:
            p.drawLine(QPointF(line.center().x(), r.y()), QPointF(line.center().x(), r.bottom()))
        else:
            p.drawLine(QPointF(r.x(), line.center().y()), QPointF(r.right(), line.center().y()))
    if posture == "HalfOpened" or kind == "dual":
        f = QFont("Segoe UI")
        f.setPixelSize(10)
        p.setFont(f)
        txt = "Hinge"
        tw = QFontMetricsF(f).horizontalAdvance(txt) + 8
        c = r.center()
        chip = QRectF(c.x() - tw / 2, c.y() - 8, tw, 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(32, 33, 36, 200))
        p.drawRoundedRect(chip, 4, 4)
        p.setPen(QColor("#FFFFFFFF"))
        p.drawText(chip, int(Qt.AlignmentFlag.AlignCenter), txt)
    p.restore()


def paint_size_frame(p: QPainter, screen: QRectF, text: str) -> None:
    """The orange frame (4 px, #F7630C) and its label while edits go to one size only."""
    p.save()
    p.setPen(QPen(ORANGE, 4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(screen.adjusted(-2, -2, 2, 2))
    f = QFont("Segoe UI")
    f.setPixelSize(11)
    f.setBold(True)
    p.setFont(f)
    tw = QFontMetricsF(f).horizontalAdvance(text) + 12
    chip = QRectF(screen.x() - 4, max(2.0, screen.y() - 24), tw, 18)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ORANGE)
    p.drawRoundedRect(chip, 3, 3)
    p.setPen(QColor("#FFFFFFFF"))
    p.drawText(chip, int(Qt.AlignmentFlag.AlignCenter), text)
    p.restore()


# ============================================================================================ size bar
class SizeBar(QWidget):
    """Second tool bar row: Edit mode, size, posture, Sizes..., Side-by-side."""

    def __init__(self, designer):
        super().__init__()
        self.d = designer
        self.setProperty("i18n_skip_items", True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 1, 6, 1)
        lay.setSpacing(4)
        lay.addWidget(QLabel("Edit:"))
        self.cbo_mode = QComboBox()
        self.cbo_mode.addItem("All sizes", "all")
        self.cbo_mode.addItem("This size only", "size")
        self.cbo_mode.setToolTip("All sizes: edits change the screen everywhere.\n"
                                 "This size only: edits are stored for the chosen size and leave the others alone.")
        self.cbo_mode.activated.connect(lambda _i: self.d.set_edit_mode(self.cbo_mode.currentData()))
        lay.addWidget(self.cbo_mode)
        self.cbo_size = QComboBox()
        self.cbo_size.setMinimumWidth(170)
        self.cbo_size.setToolTip("The size edited in This size only mode (its preview device is shown)")
        self.cbo_size.activated.connect(lambda _i: self.d.set_edit_size(self.cbo_size.currentData()))
        lay.addWidget(self.cbo_size)
        self.btn_sizes = QToolButton()
        self.btn_sizes.setText("Sizes")
        self.btn_sizes.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu = QMenu(self.btn_sizes)
        self.menu.aboutToShow.connect(self._fill_menu)
        self.btn_sizes.setMenu(self.menu)
        lay.addWidget(self.btn_sizes)
        self.btn_side = QToolButton()
        self.btn_side.setText("Side-by-side")
        self.btn_side.setToolTip("Every size of the screen next to each other")
        self.btn_side.clicked.connect(self.d.show_side_by_side)
        lay.addWidget(self.btn_side)
        self.lbl_posture = QLabel("Posture:")
        lay.addWidget(self.lbl_posture)
        self.cbo_posture = QComboBox()
        self.cbo_posture.addItem("Flat", "Flat")
        self.cbo_posture.addItem("Half-open", "HalfOpened")
        self.cbo_posture.addItem("Folded", "Folded")
        self.cbo_posture.setToolTip("Foldable posture of the preview device")
        self.cbo_posture.activated.connect(lambda _i: self.d.set_posture(self.cbo_posture.currentData()))
        lay.addWidget(self.cbo_posture)
        self.lbl_active = QLabel("")
        self.lbl_active.setStyleSheet("color: gray")
        lay.addWidget(self.lbl_active, 1)
        self.refresh()

    def refresh(self):
        d = self.d
        sizes = VF.sizes(d.screen)
        self.cbo_size.blockSignals(True)
        self.cbo_size.clear()
        for s in sizes:
            self.cbo_size.addItem(f"{VF.label(s)}  ({VF.describe_when(s.get('when'))})", s["id"])
        if not sizes:
            self.cbo_size.addItem("(no sizes - Sizes > Add)", None)
        i = self.cbo_size.findData(d.edit_size)
        self.cbo_size.setCurrentIndex(max(0, i))
        self.cbo_size.blockSignals(False)
        self.cbo_mode.blockSignals(True)
        self.cbo_mode.setCurrentIndex(1 if d.edit_mode == "size" else 0)
        self.cbo_mode.blockSignals(False)
        self.cbo_mode.setEnabled(bool(sizes))
        fold = _devices().is_foldable(d.device_id())
        self.lbl_posture.setVisible(fold)
        self.cbo_posture.setVisible(fold)
        self.cbo_posture.setCurrentIndex(max(0, self.cbo_posture.findData(d.posture)))
        act = d.active_sizes()
        names = [VF.label(VF.size(d.screen, v) or {"id": v}) for v in act]
        self.lbl_active.setText(("Active here: " + ", ".join(names)) if names else
                                ("No size matches this device" if sizes else ""))
        self.btn_side.setEnabled(bool(sizes))

    def _fill_menu(self):
        m = self.menu
        m.clear()
        add = m.addMenu("Add sizes")
        for name in VF.SIZE_PRESETS:
            add.addAction(name, lambda n=name: self.d.apply(VF.add_preset, n, text="Add sizes"))
        m.addAction("Add Size...", self.d.add_size_dialog)
        m.addAction("Edit Sizes...", self.d.edit_sizes_dialog)
        cur = self.d.edit_size
        rm = m.addAction("Remove this size", lambda: cur and self.d.apply(VF.remove_size, cur, text="Remove size"))
        rm.setEnabled(bool(cur))


class SideBySide(QDialog):
    """Every size of the screen rendered with the Qt preview (its preview device, else the current one)."""

    def __init__(self, designer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Side-by-side")
        self.resize(1100, 720)
        lay = QVBoxLayout(self)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        lay.addWidget(sc, 1)
        host = QWidget()
        grid = QHBoxLayout(host)
        sc.setWidget(host)
        self.labels: list[QLabel] = []
        for img, title in render_sizes(designer):
            col = QVBoxLayout()
            lab = QLabel()
            lab.setPixmap(QPixmap.fromImage(img))
            cap = QLabel(title)
            cap.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(lab)
            col.addWidget(cap)
            col.addStretch(1)
            grid.addLayout(col)
            self.labels.append(lab)
        grid.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


def render_sizes(designer, height: int = 520) -> list:
    """[(QImage, caption)] - the base screen on the current device, then every size on its preview device."""
    from . import qtpreview as Q
    out = []
    rows = [(None, designer.device_facts())]
    for s in VF.sizes(designer.screen):
        rows.append((s, VF.preview_facts(s) or designer.device_facts()))
    for s, facts in rows:
        act = VF.active_for(designer.screen, facts) if s is not None else designer.active_sizes()
        scr = M.Screen(VF.preview_data(designer.screen, act))
        w, h = int(facts["width"]), int(facts["height"])
        scale = min(1.0, height / max(1, h))
        img = Q.render_image(scr, w, h, designer.dark, scale, designer.project_folder())
        feats = facts.get("features") or []
        if feats:
            p = QPainter(img)
            b = feats[0]["bounds"]
            paint_hinge(p, QRectF(0, 0, w * scale, h * scale), scale, b, "dual" if feats[0]["type"] == "hinge"
                        else "book", "HalfOpened" if feats[0].get("state") == "postureHalfOpened" else "Flat")
            p.end()
        title = (VF.label(s) if s else "Current device") + f"  {w}x{h}"
        if s is not None:
            title += "\n" + VF.describe_when(s.get("when"))
        out.append((img, title))
    return out


# ============================================================================================ editors
class RowsDialog(QDialog):
    """Edit a list of dicts in a table. *columns* = [(key, title, kind)] kind: str | int | float | bool | json |
    "choice:a|b|c" (an empty cell = key absent)."""

    def __init__(self, title: str, columns: list[tuple], rows: list[dict], parent=None, help_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 360)
        self.columns = columns
        lay = QVBoxLayout(self)
        if help_text:
            h = QLabel(help_text)
            h.setWordWrap(True)
            h.setStyleSheet("color: gray")
            lay.addWidget(h)
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels([c[1] for c in columns])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)
        for r in rows:
            self.add_row(r)
        btns = QHBoxLayout()
        b_add = QPushButton("Add")
        b_add.clicked.connect(lambda: self.add_row({}))
        b_del = QPushButton("Remove")
        b_del.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        btns.addWidget(b_add)
        btns.addWidget(b_del)
        btns.addStretch(1)
        lay.addLayout(btns)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def add_row(self, r: dict):
        i = self.table.rowCount()
        self.table.insertRow(i)
        for j, (key, _t, kind) in enumerate(self.columns):
            v = r.get(key)
            if kind == "bool":
                cb = QCheckBox()
                cb.setChecked(bool(v))
                self.table.setCellWidget(i, j, cb)
            elif kind.startswith("choice:"):
                cbo = QComboBox()
                cbo.addItem("")
                cbo.addItems(kind[7:].split("|"))
                cbo.setCurrentText("" if v is None else str(v))
                self.table.setCellWidget(i, j, cbo)
            else:
                txt = "" if v is None else (json.dumps(v) if kind == "json" else str(v))
                self.table.setItem(i, j, QTableWidgetItem(txt))

    def rows(self) -> list[dict]:
        out = []
        for i in range(self.table.rowCount()):
            r = {}
            for j, (key, _t, kind) in enumerate(self.columns):
                if kind == "bool":
                    if self.table.cellWidget(i, j).isChecked():
                        r[key] = True
                    continue
                if kind.startswith("choice:"):
                    t = self.table.cellWidget(i, j).currentText()
                else:
                    it = self.table.item(i, j)
                    t = it.text().strip() if it else ""
                if t == "":
                    continue
                try:
                    r[key] = int(t) if kind == "int" else float(t) if kind == "float" else \
                        json.loads(t) if kind == "json" else t
                except ValueError:
                    r[key] = t
            if r:
                out.append(r)
        return out


STATE_COLUMNS = [("name", "Name", "str"), ("type", "Type", "choice:" + "|".join(MO.STATE_TYPES)),
                 ("init", "Initial value (JSON)", "json")]
TIMELINE_COLUMNS = [("name", "Name", "str"), ("durationMs", "Duration (ms)", "int"),
                    ("autostart", "Auto start", "bool"), ("repeat", "Repeat", "bool"), ("reverse", "Reverse", "bool")]
SIZE_COLUMNS = [("id", "Id", "str"), ("label", "Label", "str"), ("when", "When (JSON)", "json"),
                ("preview", "Preview (JSON)", "json")]


class KeyframesDialog(QDialog):
    """Rows of (track, ms, value, curve) for a keyframes animation."""

    def __init__(self, tracks: dict | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyframes")
        self.resize(560, 380)
        lay = QVBoxLayout(self)
        h = QLabel("One row per key: the value the track reaches at that time (ms). Rotation is in turns, offsets "
                   "in pixels, colours #AARRGGBB. The curve eases from the previous key.")
        h.setWordWrap(True)
        h.setStyleSheet("color: gray")
        lay.addWidget(h)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Track", "Time (ms)", "Value", "Curve"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)
        for tr in MO.KEY_TRACKS:
            for k in (tracks or {}).get(tr) or []:
                self.add_row(tr, k)
        row = QHBoxLayout()
        b_add = QPushButton("Add key")
        b_add.clicked.connect(lambda: self.add_row("opacity", [0, 1]))
        b_del = QPushButton("Remove")
        b_del.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        row.addWidget(b_add)
        row.addWidget(b_del)
        row.addStretch(1)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def add_row(self, track: str, key: list):
        i = self.table.rowCount()
        self.table.insertRow(i)
        cb = QComboBox()
        cb.addItems(MO.KEY_TRACKS)
        cb.setCurrentText(track)
        self.table.setCellWidget(i, 0, cb)
        sp = QSpinBox()
        sp.setRange(0, 600000)
        sp.setSingleStep(50)
        sp.setValue(int(key[0]) if key else 0)
        self.table.setCellWidget(i, 1, sp)
        self.table.setItem(i, 2, QTableWidgetItem(str(key[1]) if len(key) > 1 else "0"))
        cv = QComboBox()
        cv.addItem("")
        cv.addItems([f"Curves.{c}" for c in M.ENUMS["Curves"]])
        cv.setCurrentText(key[2] if len(key) > 2 else "")
        self.table.setCellWidget(i, 3, cv)

    def tracks(self) -> dict:
        out: dict = {}
        for i in range(self.table.rowCount()):
            tr = self.table.cellWidget(i, 0).currentText()
            ms = self.table.cellWidget(i, 1).value()
            t = (self.table.item(i, 2).text() if self.table.item(i, 2) else "").strip()
            if tr == "color":
                val = M.normalize_color(t)
            else:
                try:
                    val = float(t)
                    val = int(val) if val == int(val) else val
                except ValueError:
                    continue
            k = [ms, val]
            cv = self.table.cellWidget(i, 3).currentText()
            if cv:
                k.append(cv)
            out.setdefault(tr, []).append(k)
        for tr in out:
            out[tr].sort(key=lambda k: k[0])
        return out


class WhenDialog(QDialog):
    """Animate a property: with a state variable ($when) or, for transition properties, a timeline ($timeline)."""

    def __init__(self, screen: M.Screen, key: str, kind: str, current=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Animate {key}")
        self.kind = kind
        lay = QFormLayout(self)
        self.mode = QComboBox()
        self.mode.addItem("With a state variable (implicit)", "when")
        self.mode.addItem("With a timeline (explicit)", "timeline")
        lay.addRow("Animate", self.mode)
        self.state = QComboBox()
        self.state.setEditable(True)
        self.state.addItems([s["name"] for s in MO.state_fields(screen) if s.get("type", "bool") == "bool"])
        self.on = QLineEdit()
        self.off = QLineEdit()
        self.on.setPlaceholderText("value when true (JSON: 200, \"#FF2196F3\", {\"all\": 24})")
        self.off.setPlaceholderText("value when false")
        lay.addRow("State variable", self.state)
        lay.addRow("On (true)", self.on)
        lay.addRow("Off (false)", self.off)
        self.tl = QComboBox()
        self.tl.setEditable(True)
        self.tl.addItems([t["name"] for t in MO.timelines(screen)])
        self.frm, self.to = QLineEdit("0"), QLineEdit("1")
        self.begin, self.end = QLineEdit("0"), QLineEdit("1")
        self.curve = QComboBox()
        self.curve.addItem("")
        self.curve.addItems([f"Curves.{c}" for c in M.ENUMS["Curves"]])
        lay.addRow("Timeline", self.tl)
        lay.addRow("From", self.frm)
        lay.addRow("To", self.to)
        lay.addRow("Interval start (0..1)", self.begin)
        lay.addRow("Interval end (0..1)", self.end)
        lay.addRow("Curve", self.curve)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)
        if kind == "timeline_offset":
            self.frm.setText("[0, 1]")
            self.to.setText("[0, 0]")
        if MO.is_when(current):
            w = current["$when"]
            self.state.setCurrentText(str(w.get("state", "")))
            self.on.setText(json.dumps(w.get("on")))
            self.off.setText(json.dumps(w.get("off")))
        elif MO.is_timeline(current):
            self.mode.setCurrentIndex(1)
            self.tl.setCurrentText(current["$timeline"])
            self.frm.setText(json.dumps(current.get("from", 0)))
            self.to.setText(json.dumps(current.get("to", 1)))
            iv = current.get("interval") or [0, 1]
            self.begin.setText(str(iv[0]))
            self.end.setText(str(iv[1]))
            self.curve.setCurrentText(current.get("curve", ""))
        elif kind in MO.TIMELINE_KINDS:
            self.mode.setCurrentIndex(1)

    @staticmethod
    def _json(t: str):
        t = t.strip()
        try:
            return json.loads(t)
        except ValueError:
            return t

    def value(self) -> dict:
        if self.mode.currentData() == "when":
            return {"$when": {"state": self.state.currentText().strip(), "on": self._json(self.on.text()),
                              "off": self._json(self.off.text())}}
        v = {"$timeline": self.tl.currentText().strip(), "from": self._json(self.frm.text()),
             "to": self._json(self.to.text())}
        b, e = self._json(self.begin.text()), self._json(self.end.text())
        if (b, e) != (0, 1):
            v["interval"] = [b, e]
        if self.curve.currentText():
            v["curve"] = self.curve.currentText()
        return v


def describe_value(v) -> str:
    """Short text for a $when / $timeline value (shown in the property row)."""
    if MO.is_when(v):
        w = v["$when"]
        return f"{w.get('state')} ? {json.dumps(w.get('on'))} : {json.dumps(w.get('off'))}"
    if MO.is_timeline(v):
        s = f"timeline {v['$timeline']}: {json.dumps(v.get('from'))} -> {json.dumps(v.get('to'))}"
        if v.get("interval"):
            s += f" [{v['interval'][0]}..{v['interval'][1]}]"
        return s
    return ""


class AnimExtra(QWidget):
    """Trigger / repeat / reverse / turns / colour / controller / keyframes of the selected node's anim."""
    changed = pyqtSignal(str, object)        # anim key, value (None = remove)

    def __init__(self, designer, parent=None):
        super().__init__(parent)
        self.d = designer
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        self.trigger = QComboBox()
        self.trigger.setToolTip("What starts the animation (state: plays while a bool state variable is true)")
        self.trigger.activated.connect(lambda _i: self.changed.emit("trigger", self.trigger.currentData()))
        self.repeat = QSpinBox()
        self.repeat.setRange(0, 999)
        self.repeat.setSpecialValueText("Forever")
        self.repeat.setToolTip("Runs (0 = forever)")
        self.repeat.editingFinished.connect(lambda: self.changed.emit("repeat", None if self.repeat.value() == 1
                                                                       else self.repeat.value()))
        self.reverse = QCheckBox("Auto reverse")
        self.reverse.toggled.connect(lambda on: self.changed.emit("reverse", True if on else None))
        self.turns = QLineEdit()
        self.turns.setPlaceholderText("turns (rotate 1, swing 0.04)")
        self.turns.editingFinished.connect(self._turns)
        self.color = QLineEdit()
        self.color.setPlaceholderText("#AARRGGBB (colorTo)")
        self.color.editingFinished.connect(lambda: self.changed.emit("color", M.normalize_color(
            self.color.text().strip()) or None))
        self.controller = QLineEdit()
        self.controller.setPlaceholderText("controller field (manual: play:<name>)")
        self.controller.editingFinished.connect(lambda: self.changed.emit("controller",
                                                                          self.controller.text().strip() or None))
        self.kf = QPushButton("Keyframes...")
        self.kf.clicked.connect(self._keyframes)
        rows = [("Trigger", self.trigger), ("Repeat", self.repeat), ("", self.reverse), ("Turns", self.turns),
                ("Colour", self.color), ("Controller", self.controller), ("", self.kf)]
        for i, (t, w) in enumerate(rows):
            g.addWidget(QLabel(t), i, 0)
            g.addWidget(w, i, 1)

    def _turns(self):
        t = self.turns.text().strip()
        try:
            self.changed.emit("turns", float(t) if t else None)
        except ValueError:
            pass

    def _keyframes(self):
        node = self.d.screen.find(self.d.selected) if self.d.selected else None
        a = (node or {}).get("anim") or {}
        dlg = KeyframesDialog(a.get("tracks"), self)
        if dlg.exec():
            tr = dlg.tracks()
            self.changed.emit("tracks", tr or None)
            if tr and a.get("type") != "keyframes":
                self.changed.emit("type", "keyframes")

    def set_anim(self, a: dict | None):
        a = a or {}
        for w in (self.trigger, self.repeat, self.reverse, self.turns, self.color, self.controller):
            w.blockSignals(True)
        self.trigger.clear()
        for t in MO.TRIGGERS:
            self.trigger.addItem(t, None if t == "load" else t)
        for s in MO.state_fields(self.d.screen):
            if s.get("type", "bool") == "bool":
                self.trigger.addItem(f"state:{s['name']}", f"state:{s['name']}")
        cur = a.get("trigger")
        i = self.trigger.findData(cur)
        if i < 0 and cur:
            self.trigger.addItem(cur, cur)
            i = self.trigger.count() - 1
        self.trigger.setCurrentIndex(max(0, i))
        self.repeat.setValue(int(a.get("repeat", 1)))
        self.reverse.setChecked(bool(a.get("reverse")))
        self.turns.setText("" if a.get("turns") is None else str(a["turns"]))
        self.color.setText(str(a.get("color") or ""))
        self.controller.setText(str(a.get("controller") or ""))
        n = sum(len(v) for v in (a.get("tracks") or {}).values())
        self.kf.setText(f"Keyframes... ({n})" if n else "Keyframes...")
        for w in (self.trigger, self.repeat, self.reverse, self.turns, self.color, self.controller):
            w.blockSignals(False)


def copy_screen_list(screen: M.Screen, key: str) -> list:
    return copy.deepcopy(screen.data.get(key) or [])
