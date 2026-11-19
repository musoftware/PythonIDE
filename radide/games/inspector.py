"""Scene inspector: the Properties window of the scene designer.

Nothing selected -> scene (window size, background, FPS, gravity, camera) + the active layer;
a sprite / text / area -> its properties, Behaviours (with parameters) and Events (double-click an
event opens its handler in <Scene>.py, like VB's Properties > Events)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMenu, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from .. import theme
from .model import BEHAVIOURS, EVENT_ARGS, handler_name, object_events


TEXT_KEYS = ("ForeColor", "FontSize", "color")


def _parse(text: str, like):
    t = text.strip()
    if isinstance(like, bool):
        if t not in ("0", "1"):            # a number where a flag was: keep it (scroll wrap = 800 px)
            try:
                v = float(t)
                return int(v) if v.is_integer() else v
            except ValueError:
                pass
        return t.lower() in ("1", "true", "yes", "on")
    if isinstance(like, int):
        try:
            return int(float(t))
        except ValueError:
            return like
    if isinstance(like, float):
        try:
            return float(t)
        except ValueError:
            return like
    try:
        return int(t)
    except ValueError:
        try:
            return float(t)
        except ValueError:
            return t


class Inspector(QScrollArea):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._live: dict[str, object] = {}       # numeric fields refreshed while dragging
        self.behaviour_list: QListWidget | None = None
        self.params: QTableWidget | None = None
        self.events: QListWidget | None = None
        self.rebuild()

    # ---------------------------------------------------------------- helpers
    def _spin(self, value, lo, hi, setter, decimals=0, step=1.0, suffix=""):
        s = QDoubleSpinBox() if decimals else QSpinBox()
        if decimals:
            s.setDecimals(decimals)
        s.setRange(lo, hi)
        s.setSingleStep(step if decimals else max(1, int(step)))
        s.setSuffix(suffix)
        s.setValue(value)
        s.setKeyboardTracking(False)
        s.setMinimumWidth(56)
        s.valueChanged.connect(setter)
        return s

    def _combo(self, items, current, setter, blank="(none)"):
        c = QComboBox()
        c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        c.setMinimumContentsLength(5)
        c.addItem(blank, "")
        for it in items:
            c.addItem(it, it)
        c.setCurrentIndex(max(0, c.findData(current or "")))
        c.currentIndexChanged.connect(lambda _i, cb=c: setter(cb.currentData()))
        return c

    def _color_button(self, value: str, setter):
        b = QPushButton(value)
        b.setMinimumWidth(56)
        b.setStyleSheet(f"background: {value}; color: {'#000' if QColor(value).lightness() > 128 else '#FFF'};")

        def pick():
            c = QColorDialog.getColor(QColor(value), self, "Colour")
            if c.isValid():
                setter(c.name().upper())
        b.clicked.connect(pick)
        return b

    def _change(self, text, fn):
        self.editor.change(text, fn)

    # ---------------------------------------------------------------- build
    def rebuild(self) -> None:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(4, 4, 4, 4)
        host.setMinimumWidth(10)
        host.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # follow the panel width
        self._live = {}
        self.behaviour_list = self.params = self.events = None
        objs = self.editor.selected_objects()
        if objs:
            self._build_object(lay, objs)
        else:
            self._build_scene(lay)
        lay.addStretch(1)
        old = self.takeWidget()
        if old is not None:
            old.deleteLater()
        self.setWidget(host)

    def _section(self, lay, title) -> QFormLayout:
        g = QGroupBox(title)
        f = QFormLayout(g)
        f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        lay.addWidget(g)
        return f

    def _build_scene(self, lay) -> None:
        ed, sc = self.editor, self.editor.scene
        f = self._section(lay, f"Scene  {sc.name}")
        f.addRow("Window width:", self._spin(sc.width, 16, 10000, lambda v: self._change(
            "Window size", lambda: setattr(sc, "width", int(v))), suffix=" px"))
        f.addRow("Window height:", self._spin(sc.height, 16, 10000, lambda v: self._change(
            "Window size", lambda: setattr(sc, "height", int(v))), suffix=" px"))
        f.addRow("Background:", self._color_button(sc.background, lambda c: self._change(
            "Background", lambda: setattr(sc, "background", c))))
        f.addRow("FPS:", self._spin(sc.fps, 1, 240, lambda v: self._change("FPS", lambda: setattr(sc, "fps", int(v)))))
        f.addRow("Gravity:", self._spin(float(sc.gravity), -10000, 10000, lambda v: self._change(
            "Gravity", lambda: setattr(sc, "gravity", float(v))), decimals=1, step=50, suffix=" px/s²"))
        names = [o.name for ly, o in sc.objects() if o.kind == "sprite"]
        f.addRow("Camera follows:", self._combo(names, sc.camera.get("follow"), lambda v: self._change(
            "Camera", lambda: sc.camera.__setitem__("follow", v or None))))
        ly = ed.active_layer()
        if ly is not None:
            lf = self._section(lay, f"Layer  {ly.name}  ({ly.type})")
            name = QLineEdit(ly.name)
            name.editingFinished.connect(lambda w=name, layer=ly: w.text().strip() and w.text().strip() != layer.name
                                         and ed.rename_layer(layer, w.text().strip()))
            lf.addRow("Name:", name)
            if ly.type == "tiles":
                lf.addRow("Tileset:", self._combo(sc.asset_ids("tilesets"), ly.tileset,
                                                  lambda v, layer=ly: ed.use_tileset(v, layer)))
                tw, th = sc.tile_size(ly)
                lf.addRow("Tile size:", QLabel(f"{tw} x {th} px"))
                lf.addRow("Columns:", self._spin(ly.cols, 1, 2000, lambda v, layer=ly: self._change(
                    "Map size", lambda: layer.resize(int(v), layer.rows))))
                lf.addRow("Rows:", self._spin(ly.rows, 1, 2000, lambda v, layer=ly: self._change(
                    "Map size", lambda: layer.resize(layer.cols, int(v)))))
            coll = QCheckBox("Collision (solid)")
            coll.setToolTip("Tiles of this layer are solid for platformer / top-down sprites")
            coll.setChecked(ly.collision)
            coll.toggled.connect(lambda on, layer=ly: self._change("Collision", lambda: setattr(layer, "collision", on)))
            lf.addRow("", coll)
        self._build_timers(lay)
        self._build_events(lay, None)

    def _build_timers(self, lay) -> None:
        """Timers (like VB's Timer control): name, interval (ms), enabled; Tick event in code."""
        ed = self.editor
        timers = ed.scene.extra.get("timers") or []
        g = QGroupBox("Timers")
        gl = QVBoxLayout(g)
        self.timers = QTableWidget(len(timers), 3)
        self.timers.setHorizontalHeaderLabels(["Name", "Interval (ms)", "Enabled"])
        self.timers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.timers.verticalHeader().hide()
        self.timers.setMaximumHeight(24 * (len(timers) + 1) + 8)
        for r, t in enumerate(timers):
            self.timers.setItem(r, 0, QTableWidgetItem(str(t.get("name", ""))))
            self.timers.setItem(r, 1, QTableWidgetItem(str(t.get("interval", 1000))))
            en = QTableWidgetItem("")
            en.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            en.setCheckState(Qt.CheckState.Checked if t.get("enabled", True) else Qt.CheckState.Unchecked)
            self.timers.setItem(r, 2, en)
        self.timers.itemChanged.connect(self._timer_changed)
        self.timers.cellDoubleClicked.connect(
            lambda r, c: c == 0 and r < len(ed.scene.extra.get("timers") or []) and
            ed.open_named_handler(f"{ed.scene.extra['timers'][r]['name']}_Tick", ""))
        gl.addWidget(self.timers)
        row = QHBoxLayout()
        add = QPushButton("Add timer")
        add.clicked.connect(ed.add_timer)
        rem = QPushButton("Remove")
        rem.clicked.connect(lambda: self.timers.currentRow() >= 0 and ed.remove_timer(self.timers.currentRow()))
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        gl.addLayout(row)
        gl.addWidget(theme.role(QLabel("Double-click a timer name to write its Tick code."), "muted"))
        lay.addWidget(g)

    def _timer_changed(self, item) -> None:
        ed = self.editor
        timers = ed.scene.extra.get("timers") or []
        r = item.row()
        if r >= len(timers):
            return
        t = dict(timers[r])
        if item.column() == 0:
            new = item.text().strip()
            if not new or not new.isidentifier() or new == t.get("name"):
                return
            t["name"] = new
        elif item.column() == 1:
            t["interval"] = max(1, int(_parse(item.text(), 1000) or 1000))
        else:
            t["enabled"] = item.checkState() == Qt.CheckState.Checked
        if t != timers[r]:
            ed.change("Timer", lambda: timers.__setitem__(r, t))

    def _build_object(self, lay, objs) -> None:
        ed, sc = self.editor, self.editor.scene
        o = objs[0]
        title = f"{o.name}  ({o.kind})" if len(objs) == 1 else f"{len(objs)} objects selected - editing {o.name}"
        f = self._section(lay, title)
        name = QLineEdit(o.name)
        name.editingFinished.connect(lambda w=name, ob=o: w.text().strip() != ob.name and ed.rename_object(ob, w.text().strip()))
        f.addRow("Name:", name)

        def num(label, attr, lo, hi, dec=0, step=1.0, suffix=""):
            def setter(v, a=attr):
                self._change(label, lambda: [setattr(x, a, v if dec else int(v)) for x in objs])
            s = self._spin(getattr(o, attr), lo, hi, setter, dec, step, suffix)
            self._live[attr] = s
            f.addRow(label + ":", s)
        num("X", "x", -100000, 100000, 1)
        num("Y", "y", -100000, 100000, 1)
        num("Width", "w", 1, 100000, 1)
        num("Height", "h", 1, 100000, 1)
        num("Scale", "scale", 0.01, 100, 2, 0.1)
        num("Rotation", "rotation", -360, 360, 1, 5, "°")
        num("Z order", "z", -499, 499)
        vis = QCheckBox("Visible")
        vis.setChecked(o.visible)
        vis.toggled.connect(lambda on: self._change("Visible", lambda: [setattr(x, "visible", on) for x in objs]))
        f.addRow("", vis)
        if o.kind == "sprite":
            f.addRow("Image:", self._combo(sc.asset_ids("images"), o.image, lambda v: ed.set_image(objs, v)))
            f.addRow("Sprite sheet:", self._combo(sc.asset_ids("spritesheets"), o.spritesheet,
                                                  lambda v: ed.set_spritesheet(objs, v)))
            sheet = sc.assets.get("spritesheets", {}).get(o.spritesheet) or {}
            f.addRow("Animation:", self._combo(list(sheet.get("animations", {})), o.animation, lambda v: self._change(
                "Animation", lambda: [setattr(x, "animation", v) for x in objs])))
        if o.kind == "text" or o.text:
            t = QLineEdit(o.text)
            t.editingFinished.connect(lambda w=t: w.text() != o.text and self._change(
                "Text", lambda: setattr(o, "text", w.text())))
            f.addRow("Text:", t)
        if o.kind == "text":
            f.addRow("Colour:", self._color_button(str(o.props.get("ForeColor") or o.props.get("color") or "#FFFFFF"), lambda c: self._change(
                "Colour", lambda: o.props.__setitem__("ForeColor", c))))
            f.addRow("Font size:", self._spin(int(o.props.get("FontSize") or 24), 4, 400, lambda v: self._change(
                "Font size", lambda: o.props.__setitem__("FontSize", int(v))), suffix=" px"))
        props = QLineEdit("; ".join(f"{k}={v}" for k, v in o.props.items() if o.kind != "text" or k not in TEXT_KEYS))
        props.setPlaceholderText("health=3; speed=2  (your own values: self.props in code)")

        def set_props(w=props):
            new = {k: v for k, v in o.props.items() if o.kind == "text" and k in TEXT_KEYS}
            for part in w.text().split(";"):
                k, eq, v = part.partition("=")
                if eq and k.strip():
                    new[k.strip()] = _parse(v, None)
            if new != o.props:
                self._change("Props", lambda: (o.props.clear(), o.props.update(new)))
        props.editingFinished.connect(set_props)
        f.addRow("Props:", props)

        # behaviours
        g = QGroupBox("Behaviours")
        gl = QVBoxLayout(g)
        self.behaviour_list = QListWidget()
        self.behaviour_list.setMaximumHeight(110)
        for b in o.behaviours:
            label = BEHAVIOURS.get(b.get("type"), (b.get("type"),))[0]
            it = QListWidgetItem(label)
            it.setToolTip(BEHAVIOURS.get(b.get("type"), ("", {}, ""))[2])
            self.behaviour_list.addItem(it)
        gl.addWidget(self.behaviour_list)
        row = QHBoxLayout()
        add = QPushButton("Add behaviour")
        menu = QMenu(add)
        for key, (label, _p, helptext) in BEHAVIOURS.items():
            a = menu.addAction(label, lambda k=key: ed.add_behaviour(objs, k))
            a.setToolTip(helptext)
        menu.setToolTipsVisible(True)
        add.setMenu(menu)
        rem = QPushButton("Remove")
        rem.clicked.connect(lambda: self.behaviour_list.currentRow() >= 0 and
                            ed.remove_behaviour(o, self.behaviour_list.currentRow()))
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        gl.addLayout(row)
        self.help = theme.role(QLabel(""), "muted")
        self.help.setWordWrap(True)
        gl.addWidget(self.help)
        self.params = QTableWidget(0, 2)
        self.params.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.params.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.params.verticalHeader().hide()
        self.params.setMaximumHeight(130)
        self.params.itemChanged.connect(lambda item: self._param_changed(o, item))
        gl.addWidget(self.params)
        self.behaviour_list.currentRowChanged.connect(lambda r: self._show_params(o, r))
        lay.addWidget(g)
        if o.behaviours:
            self.behaviour_list.setCurrentRow(0)
        else:
            self._show_params(o, -1)
        self._build_events(lay, o if len(objs) == 1 else None, single=len(objs) == 1)

    def _show_params(self, o, row) -> None:
        self.params.blockSignals(True)
        self.params.setRowCount(0)
        b = o.behaviours[row] if 0 <= row < len(o.behaviours) else None
        self.help.setText(BEHAVIOURS.get(b.get("type"), ("", {}, ""))[2] if b else
                          "Behaviours make sprites move and react without code (Add behaviour).")
        if b:
            for k, v in b.items():
                if k == "type":
                    continue
                r = self.params.rowCount()
                self.params.insertRow(r)
                ki = QTableWidgetItem(k)
                ki.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.params.setItem(r, 0, ki)
                self.params.setItem(r, 1, QTableWidgetItem(str(v)))
        self.params.blockSignals(False)

    def _param_changed(self, o, item) -> None:
        row = self.behaviour_list.currentRow()
        if item.column() != 1 or not (0 <= row < len(o.behaviours)):
            return
        b = o.behaviours[row]
        key = self.params.item(item.row(), 0).text()
        val = _parse(item.text(), b.get(key))
        if val != b.get(key):
            self._change(f"Behaviour {key}", lambda: b.__setitem__(key, val))

    def _build_events(self, lay, obj, single: bool = True) -> None:
        if not single:
            return
        ed = self.editor
        g = QGroupBox("Events (double-click to write code)")
        gl = QVBoxLayout(g)
        self.events = QListWidget()
        self.events.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        code = ed.code_text()
        for ev in object_events(obj):
            name = handler_name(ed.scene, obj, ev)
            args = EVENT_ARGS.get(ev, "")
            it = QListWidgetItem(f"{ev}    {name}({args})")
            it.setData(Qt.ItemDataRole.UserRole, ev)
            if ed.has_handler(code, name):
                fnt = QFont(it.font())
                fnt.setBold(True)
                it.setFont(fnt)
            self.events.addItem(it)
        self.events.setMaximumHeight(22 * max(3, self.events.count()) + 6)
        self.events.itemDoubleClicked.connect(lambda it: ed.open_handler(obj, it.data(Qt.ItemDataRole.UserRole)))
        gl.addWidget(self.events)
        lay.addWidget(g)

    # ---------------------------------------------------------------- live refresh
    def refresh_values(self) -> None:
        objs = self.editor.selected_objects()
        if not objs or not self._live:
            return
        o = objs[0]
        for attr, w in self._live.items():
            try:
                w.blockSignals(True)
                w.setValue(getattr(o, attr))
                w.blockSignals(False)
            except RuntimeError:
                pass
