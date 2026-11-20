"""Particle effects in the scene designer: the Particle Editor (with a live preview), emitter objects and
their section in the scene inspector.

Effects are stored in the scene (``assets.particles``: {id: effect}, the format of
radide/games/runtime/radgame_particles.py, which also runs the preview).  An *emitter object* is an area
with ``"particles": {"effect": id, "emitting": true}``; the pygame runtime (radgame_particles.py), the
Godot export (CPUParticles2D) and code (``Emit`` / ``Burst``) all use the same effects.
"""
from __future__ import annotations

import copy
import importlib.util
import random
import sys
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QListWidget, QMenu,
                             QMessageBox, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget)

from .. import theme

RUNTIME_FILE = Path(__file__).resolve().parent / "runtime" / "radgame_particles.py"
_rt = None


def runtime():
    """The radgame_particles module of the runtime folder (the simulation shared with the games)."""
    global _rt
    if _rt is None:
        spec = importlib.util.spec_from_file_location("radide_radgame_particles", RUNTIME_FILE)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _rt = mod
    return _rt


# (key, label, min, max, decimals, step, suffix, help)
NUM_FIELDS = [
    ("rate", "Rate", 0, 5000, 1, 5, " /s", "Particles per second (0 = only bursts)"),
    ("burst", "Burst count", 0, 5000, 0, 5, "", "Particles of one Burst()"),
    ("lifetime", "Lifetime", 0.02, 60, 2, 0.1, " s", "How long a particle lives"),
    ("lifetime_var", "Lifetime +/-", 0, 60, 2, 0.1, " s", "Random variation of the lifetime"),
    ("speed", "Speed", 0, 5000, 1, 10, " px/s", "Start speed"),
    ("speed_var", "Speed +/-", 0, 5000, 1, 10, " px/s", "Random variation of the speed"),
    ("angle", "Angle", -360, 360, 1, 5, "°", "Direction: 0 = right, -90 = up, 90 = down"),
    ("spread", "Spread", 0, 180, 1, 5, "°", "+/- around the angle (180 = every direction)"),
    ("gravity_x", "Gravity X", -5000, 5000, 1, 10, " px/s²", "Pull to the right (negative: left)"),
    ("gravity_y", "Gravity Y", -5000, 5000, 1, 10, " px/s²", "Pull down (negative: particles rise)"),
    ("damping", "Damping", 0, 20, 2, 0.1, "", "Slows the particles down"),
    ("size_start", "Size at birth", 0, 512, 1, 1, " px", "Size when born"),
    ("size_end", "Size at death", 0, 512, 1, 1, " px", "Size at the end of its life"),
    ("spin", "Spin", -3600, 3600, 0, 10, "°/s", "Rotation speed"),
    ("emit_w", "Emit width", 0, 10000, 0, 8, " px", "Emit from a rectangle this wide (0 = a point)"),
    ("emit_h", "Emit height", 0, 10000, 0, 8, " px", "Emit from a rectangle this high"),
    ("max", "Max particles", 1, 20000, 0, 50, "", "Cap of living particles"),
    ("duration", "Duration", 0, 3600, 1, 0.5, " s", "Stop emitting after this many seconds (0 = forever)"),
]


def unique_id(effects: dict, base: str) -> str:
    base = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in base) or "effect"
    i, out = 2, base
    while out in effects:
        out = f"{base}{i}"
        i += 1
    return out


def ensure_effect(scene, effect_id: str = "fire") -> str:
    """Make sure the scene has the effect (copying a preset of that name); returns its id."""
    effects = scene.assets.setdefault("particles", {})
    if effect_id not in effects:
        effects[effect_id] = copy.deepcopy(runtime().PRESETS.get(effect_id, runtime().PRESETS["fire"]))
    return effect_id


def add_emitter(editor, effect_id: str = "fire", pos=None):
    """Add > Particle emitter: an area that emits *effect_id* (a preset is copied into the scene)."""
    o = editor.add_object("area", pos, name=editor.scene.unique_name("Emitter"), w=32, h=32)
    if o is None:
        return None

    def do():
        ensure_effect(editor.scene, effect_id)
        o.extra["particles"] = {"effect": effect_id, "emitting": True}
    editor.change("Particle emitter", do, structural=True)
    return o


# ====================================================================== preview
class ParticlePreview(QWidget):
    """Runs an effect with the runtime's simulation and draws it (click = Burst)."""

    def __init__(self, parent=None, images: dict | None = None):
        super().__init__(parent)
        self.setMinimumSize(240, 220)
        self.images = images or {}           # image id -> QPixmap
        self.emitter = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)
        self._cache: dict = {}
        self.setToolTip("Live preview - click to fire a Burst")

    def set_effect(self, effect: dict) -> None:
        rt = runtime()
        old = self.emitter.particles if self.emitter is not None else []
        self.emitter = rt.Emitter(effect, self.width() / 2, self.height() * 0.62, rng=random.Random(7))
        self.emitter.particles = old
        self._cache.clear()

    def burst(self) -> None:
        if self.emitter is not None:
            self.emitter.burst()

    def mousePressEvent(self, e) -> None:
        if self.emitter is not None:
            self.emitter.x, self.emitter.y = e.position().x(), e.position().y()
            self.emitter.burst()

    def resizeEvent(self, e) -> None:
        if self.emitter is not None:
            self.emitter.x, self.emitter.y = self.width() / 2, self.height() * 0.62
        super().resizeEvent(e)

    def _tick(self) -> None:
        if self.emitter is not None and self.isVisible():
            self.emitter.update(0.016)
            if self.emitter.until and not self.emitter.emitting and not self.emitter.particles:
                self.emitter.time, self.emitter.emitting = 0.0, True     # loop timed effects in the preview
            self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.color("stage")))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        em = self.emitter
        if em is None:
            return
        add = str(em.effect.get("blend")) == "add"
        if add:
            p.fillRect(self.rect(), QColor(10, 10, 18))
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        tex = self.images.get(str(em.effect.get("texture") or ""))
        square = str(em.effect.get("shape")) == "square"
        p.setPen(Qt.PenStyle.NoPen)
        for part in em.particles:
            size, col = em.look(part)
            if size <= 0.2 or col[3] <= 2:
                continue
            c = QColor(*col)
            r = QRectF(part.x - size / 2, part.y - size / 2, size, size)
            if tex is not None:
                p.setOpacity(col[3] / 255)
                p.drawPixmap(r, tex, QRectF(tex.rect()))
                p.setOpacity(1.0)
            elif square:
                p.fillRect(r, c)
            else:
                p.setBrush(c)
                p.drawEllipse(r)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setPen(QColor(theme.color("muted")))
        p.drawText(QRectF(6, 4, self.width() - 12, 18), Qt.AlignmentFlag.AlignLeft,
                   f"{len(em.particles)} particles")
        p.setPen(QColor(255, 255, 255, 60))
        p.drawEllipse(QPointF(em.x, em.y), 3, 3)


# ====================================================================== editor dialog
class ParticleEditor(QDialog):
    """Edit the particle effects of a scene: presets, every emitter setting, colours, texture, preview."""

    def __init__(self, editor, select: str = ""):
        super().__init__(editor)
        self.editor = editor
        self.setWindowTitle("Particle Editor")
        self.resize(820, 600)
        self.effects = copy.deepcopy(editor.scene.assets.get("particles") or {})
        images = {}
        for iid, rel in (editor.scene.assets.get("images") or {}).items():
            pm = editor.pixmap(rel) if hasattr(editor, "pixmap") else QPixmap(str(rel))
            if pm is not None and not pm.isNull():
                images[iid] = pm
        self.images = images
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Effects of the scene:"))
        self.list = QListWidget()
        ll.addWidget(self.list, 1)
        newb = QPushButton("New from preset")
        menu = QMenu(newb)
        for name in runtime().PRESETS:
            menu.addAction(name, lambda n=name: self.new_effect(n))
        menu.addSeparator()
        menu.addAction("Empty", lambda: self.new_effect(""))
        newb.setMenu(menu)
        ll.addWidget(newb)
        for text, slot in (("Rename...", self.rename), ("Duplicate", self.duplicate), ("Delete", self.delete)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            ll.addWidget(b)
        split.addWidget(left)
        # settings
        mid = QScrollArea()
        mid.setWidgetResizable(True)
        host = QWidget()
        self.form = QFormLayout(host)
        self.fields: dict[str, QDoubleSpinBox] = {}
        for key, label, lo, hi, dec, step, suffix, tip in NUM_FIELDS:
            s = QDoubleSpinBox()
            s.setDecimals(dec)
            s.setRange(lo, hi)
            s.setSingleStep(step)
            s.setSuffix(suffix)
            s.setToolTip(tip)
            s.setKeyboardTracking(False)
            s.valueChanged.connect(lambda v, k=key: self.set_value(k, v))
            self.fields[key] = s
            self.form.addRow(label + ":", s)
        self.col0 = QPushButton()
        self.col0.clicked.connect(lambda: self.pick_color("color_start"))
        self.col1 = QPushButton()
        self.col1.clicked.connect(lambda: self.pick_color("color_end"))
        self.form.addRow("Colour at birth:", self.col0)
        self.form.addRow("Colour at death:", self.col1)
        self.shape = QComboBox()
        self.shape.addItems(["circle", "square"])
        self.shape.currentTextChanged.connect(lambda t: self.set_value("shape", t))
        self.form.addRow("Shape:", self.shape)
        self.texture = QComboBox()
        self.texture.addItem("(none)", "")
        for iid in images:
            self.texture.addItem(iid, iid)
        self.texture.currentIndexChanged.connect(lambda _i: self.set_value("texture", self.texture.currentData() or ""))
        self.form.addRow("Texture:", self.texture)
        self.blend = QComboBox()
        self.blend.addItem("normal", "normal")
        self.blend.addItem("add (glow)", "add")
        self.blend.currentIndexChanged.connect(lambda _i: self.set_value("blend", self.blend.currentData()))
        self.form.addRow("Blend:", self.blend)
        mid.setWidget(host)
        mid.setMinimumWidth(300)
        split.addWidget(mid)
        # preview
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.preview = ParticlePreview(self, images)
        rl.addWidget(self.preview, 1)
        row = QHBoxLayout()
        bb = QPushButton("Burst")
        bb.clicked.connect(self.preview.burst)
        row.addWidget(bb)
        row.addStretch(1)
        rl.addLayout(row)
        hint = theme.role(QLabel('In code: Emit("id", x, y), Emit("id", Player), Burst("id", x, y, 40), '
                                 "StopEmitter(e); an emitter object: Add > Particle emitter."), "muted")
        hint.setWordWrap(True)
        rl.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.ok)
        buttons.rejected.connect(self.reject)
        rl.addWidget(buttons)
        split.addWidget(right)
        split.setSizes([170, 330, 320])
        self.list.currentTextChanged.connect(self.show_effect)
        self._cur = ""
        self.refresh_list(select)

    # ---- list
    def refresh_list(self, select: str = "") -> None:
        self.list.blockSignals(True)
        self.list.clear()
        self.list.addItems(list(self.effects))
        self.list.blockSignals(False)
        items = self.list.findItems(select, Qt.MatchFlag.MatchExactly) if select else []
        if items:
            self.list.setCurrentItem(items[0])
        elif self.list.count():
            self.list.setCurrentRow(0)
        else:
            self.show_effect("")

    def new_effect(self, preset: str) -> str:
        eid = unique_id(self.effects, preset or "effect")
        self.effects[eid] = copy.deepcopy(runtime().PRESETS.get(preset, {}))
        self.refresh_list(eid)
        return eid

    def rename(self) -> None:
        if self._cur not in self.effects:
            return
        new, ok = QInputDialog.getText(self, "Rename effect", "New id:", text=self._cur)
        new = (new or "").strip()
        if ok and new.isidentifier() and new not in self.effects:
            self.effects = {(new if k == self._cur else k): v for k, v in self.effects.items()}
            self.refresh_list(new)

    def duplicate(self) -> None:
        if self._cur in self.effects:
            eid = unique_id(self.effects, self._cur)
            self.effects[eid] = copy.deepcopy(self.effects[self._cur])
            self.refresh_list(eid)

    def delete(self) -> None:
        if self._cur in self.effects:
            used = [o.name for _ly, o in self.editor.scene.objects()
                    if (o.extra.get("particles") or {}).get("effect") == self._cur]
            if used and QMessageBox.question(self, "Delete effect", f"{', '.join(used)} use this effect. Delete it?") \
                    != QMessageBox.StandardButton.Yes:
                return
            del self.effects[self._cur]
            self.refresh_list()

    # ---- one effect
    def show_effect(self, eid: str) -> None:
        self._cur = eid
        e = runtime().effect_of(self.effects.get(eid, {}))
        enabled = eid in self.effects
        for key, s in self.fields.items():
            s.blockSignals(True)
            try:
                s.setValue(float(e.get(key) or 0))
            except (TypeError, ValueError):
                s.setValue(0)
            s.setEnabled(enabled)
            s.blockSignals(False)
        for w, key in ((self.col0, "color_start"), (self.col1, "color_end")):
            self._paint_button(w, str(e.get(key)))
            w.setEnabled(enabled)
        for combo, value in ((self.shape, e.get("shape")), (self.texture, e.get("texture") or ""),
                             (self.blend, e.get("blend"))):
            combo.blockSignals(True)
            i = combo.findData(value) if combo is not self.shape else combo.findText(str(value))
            combo.setCurrentIndex(max(0, i))
            combo.setEnabled(enabled)
            combo.blockSignals(False)
        if enabled:
            self.preview.set_effect(self.effects[eid])
        else:
            self.preview.emitter = None

    def _paint_button(self, b: QPushButton, value: str) -> None:
        r, g, bl, a = runtime().parse_color(value)
        b.setText(value)
        b.setStyleSheet(f"background: rgba({r},{g},{bl},{a}); color: {'#000' if (r + g + bl) / 3 > 128 else '#FFF'};")

    def set_value(self, key: str, value) -> None:
        if self._cur not in self.effects:
            return
        if isinstance(value, float) and value.is_integer() and key in ("burst", "max"):
            value = int(value)
        self.effects[self._cur][key] = value
        self.preview.set_effect(self.effects[self._cur])

    def pick_color(self, key: str) -> None:
        if self._cur not in self.effects:
            return
        e = runtime().effect_of(self.effects[self._cur])
        r, g, b, a = runtime().parse_color(e.get(key))
        c = QColorDialog.getColor(QColor(r, g, b, a), self, "Colour", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            value = f"#{c.red():02X}{c.green():02X}{c.blue():02X}" + (f"{c.alpha():02X}" if c.alpha() < 255 else "")
            self.set_value(key, value)
            self._paint_button(self.col0 if key == "color_start" else self.col1, value)

    def ok(self) -> None:
        ed = self.editor
        effects = self.effects
        ed.change("Particle effects", lambda: ed.scene.assets.__setitem__("particles", effects), structural=True)
        self.accept()


# ====================================================================== scene inspector sections
def build_scene_section(insp, lay) -> None:
    ed = insp.editor
    effects = ed.scene.assets.get("particles") or {}
    g = QGroupBox("Particle effects")
    gl = QVBoxLayout(g)
    gl.addWidget(theme.role(QLabel(f"{len(effects)} effect(s): {', '.join(effects) or '-'}"), "muted"))
    row = QHBoxLayout()
    b = QPushButton("Particle Editor...")
    b.clicked.connect(lambda: ParticleEditor(ed).exec())
    row.addWidget(b)
    a = QPushButton("Add emitter")
    a.setToolTip("An area that emits particles (fire, smoke, snow ...)")
    a.clicked.connect(lambda: add_emitter(ed, next(iter(effects), "fire")))
    row.addWidget(a)
    row.addStretch(1)
    gl.addLayout(row)
    lay.addWidget(g)


def build_object_section(insp, lay, objs) -> None:
    if len(objs) != 1:
        return
    ed, o = insp.editor, objs[0]
    cfg = o.extra.get("particles")
    effects = list((ed.scene.assets.get("particles") or {}))
    g = QGroupBox("Particles")
    f = QFormLayout(g)
    on = QCheckBox("Emit particles from this object")
    on.setChecked(bool(cfg))

    def toggle(checked):
        def do():
            if checked:
                eid = ensure_effect(ed.scene, effects[0] if effects else "fire")
                o.extra["particles"] = {"effect": eid, "emitting": True}
            else:
                o.extra.pop("particles", None)
        ed.change("Particles", do, structural=True)
    on.toggled.connect(toggle)
    f.addRow("", on)
    if cfg:
        combo = QComboBox()
        combo.addItems(effects)
        combo.setCurrentIndex(max(0, combo.findText(str(cfg.get("effect", "")))))
        combo.currentTextChanged.connect(lambda t: ed.change("Particle effect", lambda: cfg.__setitem__("effect", t)))
        f.addRow("Effect:", combo)
        em = QCheckBox("Emitting when the scene starts")
        em.setChecked(bool(cfg.get("emitting", True)))
        em.toggled.connect(lambda v: ed.change("Emitting", lambda: cfg.__setitem__("emitting", bool(v))))
        f.addRow("", em)
        b = QPushButton("Edit effect...")
        b.clicked.connect(lambda: ParticleEditor(ed, str(cfg.get("effect", ""))).exec())
        f.addRow("", b)
        f.addRow(theme.role(QLabel(f"Code: {o.name}.emitting = False / True,  Burst(\"{cfg.get('effect', '')}\", "
                                   f"{o.name})"), "muted"))
    lay.addWidget(g)


__all__ = ["ParticleEditor", "ParticlePreview", "add_emitter", "ensure_effect", "runtime", "build_scene_section",
           "build_object_section", "NUM_FIELDS"]
