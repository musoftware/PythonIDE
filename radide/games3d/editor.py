"""The 3D scene view: a tab for ``<Scene>.scene3d`` files (Ursina and Godot 3D projects).

Left: the entity list (Hierarchy).  Centre: a perspective wireframe viewport (QPainter, no OpenGL needed):
right / middle drag orbits, wheel zooms, left click selects, left drag moves the selection on the ground
plane, arrow keys nudge it (PgUp / PgDn = up / down).  Right: the inspector - name, kind, position, rotation,
scale, colour, behaviours (and the scene's sky colour / gravity).  Saving writes the .scene3d file and
regenerates ``<Scene>_designer.py`` (Ursina) or ``<Scene>.tscn`` (Godot, when project.godot exists).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QKeySequence, QPainter, QPen
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QPushButton,
                             QScrollArea, QSplitter, QToolBar, QToolButton, QVBoxLayout, QWidget)

from .. import theme
from .model import BEHAVIOURS, KINDS, Entity, Scene3D, safe_name

# ---------------------------------------------------------------------------------------------- math helpers


def _rot(v, rx, ry, rz):
    """Rotate vector v by Euler degrees (Ursina order: z, x, y)."""
    x, y, z = v
    a = math.radians(rz)
    x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    a = math.radians(rx)
    y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
    a = math.radians(ry)
    x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
    return x, y, z


def _shape_edges(kind: str) -> tuple[list, list]:
    """Unit-size wireframe (points, edges) of a kind, centred at the origin."""
    if kind in ("cube", "empty"):
        h = 0.5
        pts = [(x, y, z) for x in (-h, h) for y in (-h, h) for z in (-h, h)]
        edges = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]
        return pts, edges
    if kind == "plane":
        pts = [(-.5, 0, -.5), (.5, 0, -.5), (.5, 0, .5), (-.5, 0, .5)]
        return pts, [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)]
    if kind in ("sphere", "capsule", "cylinder"):
        n = 16
        pts, edges = [], []
        half = 1.0 if kind == "capsule" else 0.5
        for ring, (yy, axis) in enumerate([(0, "y"), (0, "x"), (0, "z")] if kind == "sphere" else
                                          [(half - (0.5 if kind == "capsule" else 0), "y"),
                                           (-half + (0.5 if kind == "capsule" else 0), "y")]):
            base = len(pts)
            for i in range(n):
                a = 2 * math.pi * i / n
                c, s = 0.5 * math.cos(a), 0.5 * math.sin(a)
                pts.append((c, yy, s) if axis == "y" else (yy, c, s) if axis == "x" else (c, s, yy))
                edges.append((base + i, base + (i + 1) % n))
        if kind != "sphere":
            for i in range(0, n, 4):
                edges.append((i, n + i))
            if kind == "capsule":
                pts += [(0, 1.0, 0), (0, -1.0, 0)]
                for i in range(0, n, 4):
                    edges += [(i, 2 * n), (n + i, 2 * n + 1)]
        return pts, edges
    if kind == "camera":
        pts = [(0, 0, 0), (-.4, -.3, .8), (.4, -.3, .8), (.4, .3, .8), (-.4, .3, .8)]
        return pts, [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (2, 3), (3, 4), (4, 1)]
    # light: a star + direction arrow
    pts = [(-.4, 0, 0), (.4, 0, 0), (0, -.4, 0), (0, .4, 0), (0, 0, 0), (0, 0, 1.5)]
    return pts, [(0, 1), (2, 3), (4, 5)]


class Viewport(QWidget):
    """Wireframe perspective view of the scene."""
    picked = pyqtSignal(str)
    moved = pyqtSignal(str)

    def __init__(self, editor: "Scene3DEditor"):
        super().__init__(editor)
        self.ed = editor
        self.yaw, self.pitch, self.dist = -30.0, 30.0, 26.0
        self.target = [0.0, 0.0, 0.0]
        self._drag = None
        self.setMinimumSize(320, 240)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(False)
        self.setAccessibleName("3D viewport")
        self.setAccessibleDescription("Wireframe view of the scene. Click selects an entity, drag moves it on the "
                                      "ground; right drag orbits, wheel zooms; arrow keys and PgUp/PgDn nudge.")

    # ------------------------------------------------------------ projection
    def _cam(self):
        y, p = math.radians(self.yaw), math.radians(self.pitch)
        eye = (self.target[0] - self.dist * math.cos(p) * math.sin(y), self.target[1] + self.dist * math.sin(p),
               self.target[2] - self.dist * math.cos(p) * math.cos(y))
        return eye, y, p

    def project(self, v):
        eye, y, p = self._cam()
        x, yy, z = v[0] - eye[0], v[1] - eye[1], v[2] - eye[2]
        x, z = x * math.cos(-y) + z * math.sin(-y), -x * math.sin(-y) + z * math.cos(-y)
        yy, z = yy * math.cos(p) + z * math.sin(p), -yy * math.sin(p) + z * math.cos(p)
        if z <= 0.1:
            return None
        f = 0.9 * min(self.width(), self.height())
        return QPointF(self.width() / 2 + x * f / z, self.height() / 2 - yy * f / z)

    def world_points(self, e: Entity) -> tuple[list, list]:
        pts, edges = _shape_edges(e.kind)
        scale = (1, 1, 1) if e.kind in ("camera", "light") else e.scale
        out = []
        for px, py, pz in pts:
            v = _rot((px * scale[0], py * scale[1], pz * scale[2]), *e.rotation)
            out.append((v[0] + e.position[0], v[1] + e.position[1], v[2] + e.position[2]))
        return out, edges

    # ------------------------------------------------------------ painting
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(theme.color("stage")))
        grid = QPen(QColor(theme.color("mid")))
        grid.setWidthF(0.6)
        p.setPen(grid)
        for i in range(-15, 16):
            for a, b in (((i, 0, -15), (i, 0, 15)), ((-15, 0, i), (15, 0, i))):
                pa, pb = self.project(a), self.project(b)
                if pa is not None and pb is not None:
                    p.drawLine(pa, pb)
        for axis, colour in (((3, 0, 0), "#E05050"), ((0, 3, 0), "#50C050"), ((0, 0, 3), "#5080E0")):
            pa, pb = self.project((0, 0, 0)), self.project(axis)
            if pa is not None and pb is not None:
                p.setPen(QPen(QColor(colour), 2))
                p.drawLine(pa, pb)
        sel = self.ed.selected_name()
        for e in self.ed.scene.entities:
            pts, edges = self.world_points(e)
            proj = [self.project(v) for v in pts]
            is_sel = e.name == sel
            col = QColor(theme.color("highlight")) if is_sel else QColor(e.color if e.kind not in
                                                                         ("camera", "light") else "#E0E0E0")
            p.setPen(QPen(col, 2.4 if is_sel else 1.3))
            for a, b in edges:
                if proj[a] is not None and proj[b] is not None:
                    p.drawLine(proj[a], proj[b])
            c = self.project(e.position)
            if c is not None and (is_sel or e.kind in ("camera", "light")):
                p.setPen(QColor("#F0F0F0"))           # the stage is dark in every theme
                p.drawText(c + QPointF(6, -6), e.name)
        p.setPen(QColor("#C8C8C8"))
        p.drawText(8, self.height() - 8, "Right drag: orbit   Wheel: zoom   Click: select   Drag: move")
        p.end()

    # ------------------------------------------------------------ input
    def _pick(self, pos) -> str:
        best, best_d = "", 22.0
        for e in self.ed.scene.entities:
            c = self.project(e.position)
            if c is None:
                continue
            d = math.hypot(c.x() - pos.x(), c.y() - pos.y())
            if d < best_d:
                best, best_d = e.name, d
        return best

    def _ground(self, pos, height: float):
        """World point on the plane y=height under the mouse (None if parallel)."""
        eye, y, p = self._cam()
        f = 0.9 * min(self.width(), self.height())
        cx, cy = (pos.x() - self.width() / 2) / f, -(pos.y() - self.height() / 2) / f
        # camera-space ray (cx, cy, 1) -> world: inverse of project()
        yy, z = cy, 1.0
        yy, z = yy * math.cos(p) - z * math.sin(p), yy * math.sin(p) + z * math.cos(p)
        x = cx
        x, z = x * math.cos(y) + z * math.sin(y), -x * math.sin(y) + z * math.cos(y)
        if abs(yy) < 1e-6:
            return None
        t = (height - eye[1]) / yy
        if t <= 0:
            return None
        return eye[0] + x * t, eye[2] + z * t

    def mousePressEvent(self, ev):
        self.setFocus()
        if ev.button() == Qt.MouseButton.LeftButton:
            name = self._pick(ev.position())
            self.picked.emit(name)
            e = self.ed.scene.find(name) if name else None
            if e is not None:
                g = self._ground(ev.position(), e.position[1])
                self._drag = ("move", e, g, list(e.position))
            return
        self._drag = ("orbit", ev.position(), self.yaw, self.pitch)

    def mouseMoveEvent(self, ev):
        if not self._drag:
            return
        if self._drag[0] == "orbit":
            _k, start, yaw, pitch = self._drag
            self.yaw = yaw + (ev.position().x() - start.x()) * 0.4
            self.pitch = max(-85.0, min(85.0, pitch + (ev.position().y() - start.y()) * 0.4))
            self.update()
        elif self._drag[0] == "move" and self._drag[2] is not None:
            _k, e, g0, p0 = self._drag
            g = self._ground(ev.position(), p0[1])
            if g is not None:
                e.position[0] = round(p0[0] + g[0] - g0[0], 2)
                e.position[2] = round(p0[2] + g[1] - g0[1], 2)
                self.ed.entity_changed(e, record=False)

    def mouseReleaseEvent(self, ev):
        if self._drag and self._drag[0] == "move" and list(self._drag[1].position) != self._drag[3]:
            self.ed.record()
            self.moved.emit(self._drag[1].name)
        self._drag = None

    def wheelEvent(self, ev):
        self.dist = max(3.0, min(200.0, self.dist * (0.9 if ev.angleDelta().y() > 0 else 1.1)))
        self.update()

    def keyPressEvent(self, ev):
        e = self.ed.scene.find(self.ed.selected_name())
        step = {Qt.Key.Key_Left: (-.5, 0, 0), Qt.Key.Key_Right: (.5, 0, 0), Qt.Key.Key_Up: (0, 0, .5),
                Qt.Key.Key_Down: (0, 0, -.5), Qt.Key.Key_PageUp: (0, .5, 0), Qt.Key.Key_PageDown: (0, -.5, 0)}
        if e is not None and ev.key() in step:
            d = step[ev.key()]
            e.position = [round(a + b, 3) for a, b in zip(e.position, d)]
            self.ed.entity_changed(e)
            return
        super().keyPressEvent(ev)


# ---------------------------------------------------------------------------------------------- inspector


class Inspector(QScrollArea):
    """Properties of the selected entity (and of the scene)."""

    def __init__(self, editor: "Scene3DEditor"):
        super().__init__(editor)
        self.ed = editor
        self.setWidgetResizable(True)
        self.setAccessibleName("3D inspector")
        body = QWidget()
        lay = QVBoxLayout(body)
        self.box = QGroupBox("Entity")
        f = QFormLayout(self.box)
        self.name = QLineEdit()
        self.name.setAccessibleName("Entity name")
        self.name.editingFinished.connect(self._rename)
        self.kind = QComboBox()
        self.kind.addItems(KINDS)
        self.kind.setAccessibleName("Entity kind")
        self.kind.activated.connect(lambda _i: self._apply("kind", self.kind.currentText()))
        f.addRow("&Name", self.name)
        f.addRow("&Kind", self.kind)
        self.vec: dict[str, list[QDoubleSpinBox]] = {}
        for prop, label, rng, step in (("position", "&Position", 1000.0, 0.25), ("rotation", "&Rotation", 360.0, 5.0),
                                       ("scale", "&Scale", 1000.0, 0.1)):
            row = QHBoxLayout()
            spins = []
            for axis in "XYZ":
                s = QDoubleSpinBox()
                s.setRange(-rng, rng)
                s.setDecimals(2)
                s.setSingleStep(step)
                s.setAccessibleName(f"{prop.title()} {axis}")
                s.setToolTip(f"{prop.title()} {axis}")
                s.valueChanged.connect(lambda _v, prop=prop: self._vec_changed(prop))
                row.addWidget(s)
                spins.append(s)
            self.vec[prop] = spins
            w = QWidget()
            w.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            f.addRow(label, w)
        self.color = QPushButton()
        self.color.setAccessibleName("Entity colour")
        self.color.clicked.connect(self._pick_color)
        f.addRow("&Colour", self.color)
        self.fov = QDoubleSpinBox()
        self.fov.setRange(10, 170)
        self.fov.setAccessibleName("Camera field of view")
        self.fov.valueChanged.connect(lambda v: self._apply_prop("fov", v))
        f.addRow("&FOV", self.fov)
        self.behaviours: dict[str, QCheckBox] = {}
        bw = QWidget()
        bl = QVBoxLayout(bw)
        bl.setContentsMargins(0, 0, 0, 0)
        tips = {"player": "WASD / arrows move, Space jumps; the camera follows", "spin": "rotates around Y",
                "solid": "a static collider", "collectible": "removed when the player touches it (+1 score)"}
        for b in BEHAVIOURS:
            c = QCheckBox(b)
            c.setToolTip(tips[b])
            c.setAccessibleName(f"Behaviour {b}")
            c.toggled.connect(lambda on, b=b: self._behaviour(b, on))
            bl.addWidget(c)
            self.behaviours[b] = c
        f.addRow("Behaviours", bw)
        lay.addWidget(self.box)
        sbox = QGroupBox("Scene")
        sf = QFormLayout(sbox)
        self.sky = QPushButton()
        self.sky.setAccessibleName("Sky colour")
        self.sky.clicked.connect(self._pick_sky)
        self.gravity = QDoubleSpinBox()
        self.gravity.setRange(0, 100)
        self.gravity.setAccessibleName("Gravity")
        self.gravity.valueChanged.connect(self._gravity)
        sf.addRow("S&ky", self.sky)
        sf.addRow("&Gravity", self.gravity)
        lay.addWidget(sbox)
        lay.addStretch(1)
        self.setWidget(body)
        self._loading = False
        self.entity: Entity | None = None

    def load(self, e: Entity | None) -> None:
        self._loading = True
        try:
            self.entity = e
            self.box.setEnabled(e is not None)
            if e is not None:
                self.name.setText(e.name)
                self.kind.setCurrentText(e.kind)
                for prop, spins in self.vec.items():
                    for s, v in zip(spins, getattr(e, prop)):
                        s.setValue(float(v))
                self._swatch(self.color, e.color)
                self.fov.setEnabled(e.kind == "camera")
                self.fov.setValue(float(e.props.get("fov", 60)))
                for b, c in self.behaviours.items():
                    c.setChecked(b in e.behaviours)
            self._swatch(self.sky, self.ed.scene.sky)
            self.gravity.setValue(float(self.ed.scene.gravity))
        finally:
            self._loading = False

    @staticmethod
    def _swatch(btn: QPushButton, colour: str) -> None:
        btn.setText(colour)
        fg = "#000000" if QColor(colour).lightness() > 128 else "#FFFFFF"
        btn.setStyleSheet(f"background: {colour}; color: {fg};")

    def _apply(self, attr: str, value) -> None:
        if self._loading or self.entity is None:
            return
        setattr(self.entity, attr, value)
        self.ed.entity_changed(self.entity)

    def _apply_prop(self, key: str, value) -> None:
        if self._loading or self.entity is None:
            return
        self.entity.props[key] = value
        self.ed.entity_changed(self.entity)

    def _vec_changed(self, prop: str) -> None:
        if self._loading or self.entity is None:
            return
        setattr(self.entity, prop, [s.value() for s in self.vec[prop]])
        self.ed.entity_changed(self.entity)

    def _rename(self) -> None:
        if self._loading or self.entity is None:
            return
        new = safe_name(self.name.text(), self.entity.name)
        if new != self.entity.name:
            if self.ed.scene.find(new) is not None:
                new = self.ed.scene.unique_name(new)
            old = self.entity.name
            self.entity.name = new
            self.ed.entity_changed(self.entity, renamed_from=old)
        self.name.setText(self.entity.name)

    def _behaviour(self, b: str, on: bool) -> None:
        if self._loading or self.entity is None:
            return
        beh = [x for x in self.entity.behaviours if x != b] + ([b] if on else [])
        self.entity.behaviours = [x for x in BEHAVIOURS if x in beh]
        self.ed.entity_changed(self.entity)

    def _pick_color(self) -> None:
        if self.entity is None:
            return
        c = QColorDialog.getColor(QColor(self.entity.color), self, "Entity colour")
        if c.isValid():
            self._apply("color", c.name().upper())
            self._swatch(self.color, self.entity.color)

    def _pick_sky(self) -> None:
        c = QColorDialog.getColor(QColor(self.ed.scene.sky), self, "Sky colour")
        if c.isValid():
            self.ed.scene.sky = c.name().upper()
            self._swatch(self.sky, self.ed.scene.sky)
            self.ed.entity_changed(None)

    def _gravity(self, v: float) -> None:
        if not self._loading:
            self.ed.scene.gravity = float(v)
            self.ed.entity_changed(None)


# ---------------------------------------------------------------------------------------------- the tab


class Scene3DEditor(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal(str)

    def __init__(self, path: Path, parent=None, log=None):
        super().__init__(parent)
        self.path = Path(path)
        self.log = log or (lambda _t: None)
        self.scene = Scene3D.load(self.path)
        self.scene.name = self.path.stem
        self._modified = False
        self._undo: list[str] = [self._snapshot()]
        self._redo: list[str] = []
        self.setAccessibleName(f"3D scene {self.path.name}")

        self.toolbar = QToolBar("3D Scene")
        self.toolbar.setAccessibleName("3D scene toolbar")
        add = QToolButton()
        add.setText("Add")
        add.setAccessibleName("Add entity")
        add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(add)
        for k in KINDS:
            menu.addAction(k.title(), lambda k=k: self.add_entity(k))
        add.setMenu(menu)
        self.toolbar.addWidget(add)
        for text, slot, key in (("Duplicate", self.duplicate, "Ctrl+D"), ("Delete", self.delete, "Del"),
                                ("Undo", self.undo, "Ctrl+Z"), ("Redo", self.redo, "Ctrl+Y"),
                                ("Save", self.save, "Ctrl+S"), ("Frame", self.frame_selected, "F")):
            a = QAction(text, self)
            a.setShortcut(QKeySequence(key))
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            a.triggered.connect(slot)
            a.setToolTip(f"{text} ({key})")
            self.toolbar.addAction(a)
            self.addAction(a)
        self.status = QLabel()
        theme.role(self.status, "muted")

        self.list = QListWidget()
        self.list.setAccessibleName("Scene entities")
        self.list.setAccessibleDescription("The entities of the 3D scene; select one to edit it in the inspector")
        self.list.currentItemChanged.connect(lambda cur, _p: self.select(cur.text() if cur else ""))
        self.view = Viewport(self)
        self.view.picked.connect(self.select)
        self.inspector = Inspector(self)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        hdr = QLabel("Hierarchy")
        theme.role(hdr, "heading")
        hdr.setBuddy(self.list)
        ll.addWidget(hdr)
        ll.addWidget(self.list)
        split.addWidget(left)
        split.addWidget(self.view)
        split.addWidget(self.inspector)
        self.inspector.setMinimumWidth(250)
        left.setMinimumWidth(120)
        for i in range(3):
            split.setCollapsible(i, False)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([170, 600, 290])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toolbar)
        lay.addWidget(split, 1)
        lay.addWidget(self.status)
        self.setTabOrder(self.list, self.view)
        self.setTabOrder(self.view, self.inspector)
        self._fill_list()
        if self.scene.entities:
            self.select((self.scene.player() or self.scene.entities[0]).name)
        theme.changed.connect(self.view.update)

    # ------------------------------------------------------------ state
    def _snapshot(self) -> str:
        return json.dumps(self.scene.to_dict(), sort_keys=True)

    def record(self) -> None:
        snap = self._snapshot()
        if snap != self._undo[-1]:
            self._undo.append(snap)
            self._redo.clear()
            self._set_modified(True)

    def _restore(self, snap: str) -> None:
        sel = self.selected_name()
        self.scene = Scene3D.from_dict(json.loads(snap))
        self.scene.name = self.path.stem
        self._fill_list()
        self.select(sel if self.scene.find(sel) else "")
        self._set_modified(True)

    def undo(self) -> None:
        if len(self._undo) > 1:
            self._redo.append(self._undo.pop())
            self._restore(self._undo[-1])

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._redo.pop())
            self._restore(self._undo[-1])

    def is_modified(self) -> bool:
        return self._modified

    def _set_modified(self, on: bool) -> None:
        if on != self._modified:
            self._modified = on
            self.modifiedChanged.emit(on)

    # ------------------------------------------------------------ list / selection
    def _fill_list(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for e in self.scene.entities:
            it = QListWidgetItem(e.name)
            it.setToolTip(f"{e.kind} at {tuple(round(x, 2) for x in e.position)}")
            it.setData(Qt.ItemDataRole.AccessibleDescriptionRole, f"{e.kind}, behaviours: "
                       f"{', '.join(e.behaviours) or 'none'}")
            self.list.addItem(it)
        self.list.blockSignals(False)
        self._status()

    def selected_name(self) -> str:
        it = self.list.currentItem()
        return it.text() if it is not None else ""

    def select(self, name: str) -> None:
        for i in range(self.list.count()):
            if self.list.item(i).text() == name:
                if self.list.currentRow() != i:
                    self.list.setCurrentRow(i)
                break
        else:
            self.list.setCurrentRow(-1)
        self.inspector.load(self.scene.find(name) if name else None)
        self.view.update()

    def _status(self) -> None:
        probs = self.scene.problems()
        self.status.setText(f"{len(self.scene.entities)} entities" + (f"  -  {probs[0]}" if probs else ""))

    # ------------------------------------------------------------ edits
    def entity_changed(self, e: Entity | None, record: bool = True, renamed_from: str = "") -> None:
        if e is not None:
            row = next((i for i in range(self.list.count())
                        if self.list.item(i).text() in (e.name, renamed_from)), -1)
            if row >= 0:
                self.list.item(row).setText(e.name)
            if self.inspector.entity is e and not self.inspector._loading and not record:
                self.inspector.load(e)
        if record:
            self.record()
        else:
            self._set_modified(True)
        self._status()
        self.view.update()

    def add_entity(self, kind: str) -> Entity:
        y = {"plane": 0.0, "camera": 5.0, "light": 8.0, "capsule": 1.0}.get(kind, 0.5)
        e = self.scene.add(kind, position=[self.view.target[0], y, self.view.target[2]],
                           color={"sphere": "#FFD700", "capsule": "#3080FF", "light": "#FFFFFF"}.get(kind, "#C0C0C0"))
        if kind == "plane":
            e.scale = [10.0, 1.0, 10.0]
        self._fill_list()
        self.select(e.name)
        self.record()
        return e

    def duplicate(self) -> None:
        e = self.scene.duplicate(self.selected_name())
        if e is not None:
            self._fill_list()
            self.select(e.name)
            self.record()

    def delete(self) -> None:
        e = self.scene.find(self.selected_name())
        if e is None:
            return
        self.scene.entities.remove(e)
        self._fill_list()
        self.select(self.scene.entities[0].name if self.scene.entities else "")
        self.record()

    def frame_selected(self) -> None:
        e = self.scene.find(self.selected_name())
        self.view.target = list(e.position) if e is not None else [0.0, 0.0, 0.0]
        self.view.update()

    def edit_op(self, op: str) -> None:
        {"undo": self.undo, "redo": self.redo, "delete": self.delete}.get(op, lambda: None)()

    def maybe_close(self) -> bool:
        """Called by the IDE before the tab closes: ask to save changes."""
        if not self._modified:
            return True
        from PyQt6.QtWidgets import QMessageBox
        b = QMessageBox.question(self, "3D Scene", f"Save changes to {self.path.name}?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if b == QMessageBox.StandardButton.Cancel:
            return False
        if b == QMessageBox.StandardButton.Save:
            self.save()
        return True

    # ------------------------------------------------------------ save + generate
    def save(self) -> list[Path]:
        self.scene.save(self.path)
        out = [self.path]
        folder = self.path.parent
        try:
            if (folder / "project.godot").exists():
                from . import godot_gen
                godot_gen.write_runtime(folder)
                out.append(godot_gen.sync_scene(folder, self.path))
            else:
                from . import ursina_gen
                ursina_gen.write_runtime(folder)
                out.append(ursina_gen.sync_scene(folder, self.path))
        except Exception as ex:  # noqa: BLE001
            self.log(f"[3D scene] generating code for {self.path.name} failed: {ex}")
        self._set_modified(False)
        self.saved.emit(str(self.path))
        return out


__all__ = ["Inspector", "Scene3DEditor", "Viewport"]
