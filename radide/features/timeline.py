"""Expression Blend for the form designer (CONTRACTS 8.7) - Storyboards ("Objects and Timeline").

Model, in the .form: ``"storyboards": [{"name": "Storyboard1", "autostart": false, "repeat": false,
"autoreverse": false, "tracks": [{"target": "Button1", "property": "Left",
"keys": [[0, 10], [1000, 200, "out"]]}]}]`` - keyframes are [time ms, value, optional easing
("linear" / "in" / "out" / "inout") of the segment that ends at the key]; target "" = the form.

Generated code (python-tk / python-qt): ``self.Storyboard1 = _Storyboard(...)`` with Begin(), Stop(),
Pause(), Resume(), Seek(ms), IsPlaying, Duration; AutoStart storyboards begin after <Form>_Load, and
``<Storyboard>_Completed`` on the form runs at the end.

IDE: the "Objects and Timeline" dock - storyboards, tracks, keyframes on a time ruler, a playhead to
scrub, Play / Stop in the designer and keyframe recording."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPolygonF
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout,
                             QWidget)

from .states import DESIGN, RESERVED_NAMES, BlendPreview, _add_dock, coerce, follow_designer, is_python

ANIM_PROPS = ("Left", "Top", "Width", "Height", "BackColor", "ForeColor", "Opacity", "FontSize", "Value",
              "Text", "Visible")
FORM_ANIM_PROPS = ("Width", "Height", "BackColor", "Opacity", "Text")
EASES = ("linear", "in", "out", "inout")

STORYBOARD_RT = r'''

class _Storyboard:
    """Storyboard (Expression Blend): keyframe animation of control properties.
    Begin() starts from time 0, Stop() stops and puts the animated properties back, Pause() / Resume(),
    Seek(ms); at the end the last values stay (HoldEnd) and the form's <Name>_Completed() runs.
    RepeatForever and AutoReverse can be changed before Begin()."""

    def __init__(self, owner, io, name, tracks, repeat=False, autoreverse=False):
        self._o, self._io, self.Name = owner, io, name
        self.Tracks = [(t, p, sorted(tuple(k) for k in keys)) for t, p, keys in tracks]
        self.RepeatForever, self.AutoReverse = bool(repeat), bool(autoreverse)
        self.Duration = max([k[0] for _t, _p, keys in self.Tracks for k in keys] or [0])
        self.IsPlaying, self.Position = False, 0
        self._gen, self._saved, self._t0, self._paused = 0, {}, 0.0, None

    def _remember(self):
        if not self._saved:
            self._saved = {(t, p): self._io.get(t, p) for t, p, _k in self.Tracks}

    def _apply(self, ms):
        self.Position = ms
        for t, p, keys in self.Tracks:
            v = _rad_value_at(p, keys, ms, self._saved.get((t, p)),
                              lambda c, t=t, p=p: self._io.rgb(t, p, c))
            self._io.set(t, p, v)

    def Begin(self):
        self._remember()
        self._gen += 1
        self.IsPlaying, self._paused = True, None
        self._t0 = _time.monotonic()
        self._tick(self._gen)

    def _tick(self, gen):
        if gen != self._gen or not self.IsPlaying:
            return
        ms = (_time.monotonic() - self._t0) * 1000.0
        span = self.Duration * (2 if self.AutoReverse else 1)
        done = False
        if span <= 0:
            ms, done = 0, True
        elif ms >= span:
            if self.RepeatForever:
                self._t0 += (ms // span) * span / 1000.0
                ms %= span
            else:
                ms, done = span, True
        self._apply(ms if ms <= self.Duration else span - ms)
        if done:
            self.IsPlaying = False
            fn = getattr(self._o, self.Name + "_Completed", None)
            if callable(fn):
                fn()
            return
        self._io.later(15, lambda: self._tick(gen))

    def Stop(self):
        self._gen += 1
        self.IsPlaying, self._paused, self.Position = False, None, 0
        for (t, p), v in self._saved.items():
            self._io.set(t, p, v)
            if p in ("Left", "Top", "Width", "Height"):
                self._io.release(t, p)          # Anchor / Dock take the control back
        self._saved = {}

    def Pause(self):
        if self.IsPlaying:
            self._gen += 1
            self.IsPlaying = False
            self._paused = _time.monotonic() - self._t0

    def Resume(self):
        if self._paused is not None:
            self._t0 = _time.monotonic() - self._paused
            self._paused = None
            self.IsPlaying = True
            self._gen += 1
            self._tick(self._gen)

    def Seek(self, ms):
        self._remember()
        ms = max(0, min(float(ms), self.Duration))
        self._apply(ms)
        if self.IsPlaying:
            self._t0 = _time.monotonic() - ms / 1000.0
        elif self._paused is not None:
            self._paused = ms / 1000.0
'''


# ====================================================================== model
def storyboards(form) -> list[dict]:
    sbs = form.extra.get("storyboards")
    if not isinstance(sbs, list):
        sbs = []
        form.extra["storyboards"] = sbs
    return sbs


def find_storyboard(form, name: str) -> dict | None:
    return next((s for s in storyboards(form) if s.get("name") == name), None)


def new_storyboard(form, name: str | None = None) -> dict:
    taken = {s.get("name") for s in storyboards(form)} | {n for n in form.all_names()}
    if not name:
        i = 1
        while f"Storyboard{i}" in taken or f"storyboard{i}" in taken:
            i += 1
        name = f"Storyboard{i}"
    sb = {"name": name, "autostart": False, "repeat": False, "autoreverse": False, "tracks": []}
    storyboards(form).append(sb)
    return sb


def track(sb: dict, target: str, prop: str, create: bool = True) -> dict | None:
    for tr in sb.setdefault("tracks", []):
        if tr.get("target") == target and tr.get("property") == prop:
            return tr
    if not create:
        return None
    tr = {"target": target, "property": prop, "keys": []}
    sb["tracks"].append(tr)
    return tr


def norm_keys(prop: str, keys) -> list[tuple]:
    out = []
    for k in keys or []:
        if not isinstance(k, (list, tuple)) or len(k) < 2:
            continue
        try:
            ms = max(0, int(round(float(k[0]))))
        except (TypeError, ValueError):
            continue
        ease = str(k[2]) if len(k) > 2 and str(k[2]) in EASES else ""
        out.append((ms, coerce(prop, k[1]), "" if ease == "linear" else ease))
    out.sort(key=lambda x: x[0])
    return out


def set_key(sb: dict, target: str, prop: str, ms: int, value, ease: str = "") -> None:
    tr = track(sb, target, prop)
    keys = [k for k in tr["keys"] if int(k[0]) != int(ms)]
    k = [int(ms), coerce(prop, value)]
    if ease and ease != "linear":
        k.append(ease)
    keys.append(k)
    keys.sort(key=lambda x: x[0])
    tr["keys"] = keys


def remove_key(sb: dict, target: str, prop: str, ms: int) -> None:
    tr = track(sb, target, prop, create=False)
    if tr is None:
        return
    tr["keys"] = [k for k in tr["keys"] if int(k[0]) != int(ms)]
    if not tr["keys"]:
        sb["tracks"].remove(tr)


def duration(sb: dict) -> int:
    return max([int(k[0]) for tr in sb.get("tracks", []) for k in tr.get("keys", [])] or [0])


def storyboards_for_code(form) -> list[dict]:
    """Storyboards ready for code generation (valid names, existing targets, normalised keys)."""
    names = {c.name for c in form.visual()}
    out, seen = [], set()
    for sb in form.extra.get("storyboards") or []:
        name = str(sb.get("name") or "")
        srcs = {str(d.get("name")) for d in form.extra.get("datasources") or []}
        if not name.isidentifier() or name in seen or name in names or name in srcs or name in RESERVED_NAMES:
            continue
        seen.add(name)
        tracks = []
        for tr in sb.get("tracks", []):
            t, p = str(tr.get("target") or ""), str(tr.get("property") or "")
            if (t and t not in names) or p not in ANIM_PROPS:
                continue
            keys = norm_keys(p, tr.get("keys"))
            if keys:
                tracks.append((t, p, keys))
        out.append({"name": name, "tracks": tracks, "autostart": bool(sb.get("autostart")),
                    "repeat": bool(sb.get("repeat")), "autoreverse": bool(sb.get("autoreverse"))})
    return out


def _rgb(value):
    c = DESIGN["_rad_rgb_hex"](value)
    if c is None and value:
        q = QColor(str(value))
        if q.isValid():
            c = (q.red(), q.green(), q.blue())
    return c


def props_at(sb: dict, target: str, ms: float, base: dict) -> dict:
    """Design-time values of the tracks of *target* at time *ms* (same algorithm as the generated code)."""
    out = {}
    for tr in sb.get("tracks", []):
        if tr.get("target") != target:
            continue
        p = tr.get("property")
        keys = norm_keys(p, tr.get("keys"))
        if not keys:
            continue
        start = base.get(p, 1.0 if p == "Opacity" else None)
        if p in ("BackColor", "ForeColor") and not start:
            start = "#f0f0f0" if p == "BackColor" else "#000000"
        out[p] = DESIGN["_rad_value_at"](p, keys, ms, start, _rgb)
    return out


# ====================================================================== timeline ruler
class TimelineRuler(QWidget):
    """Tracks as rows, keyframes as diamonds, a draggable playhead (click / drag to scrub)."""
    scrubbed = pyqtSignal(int)
    keyClicked = pyqtSignal(int, int)        # track row, time ms

    ROW = 22
    HEAD = 20
    LEFT = 6

    def __init__(self):
        super().__init__()
        self.tracks: list[dict] = []
        self.ms = 0
        self.span = 2000
        self.current = -1
        self.setMinimumHeight(90)
        self.setMouseTracking(False)

    def set_data(self, tracks: list[dict], ms: int, current: int) -> None:
        self.tracks = tracks
        self.ms = ms
        self.current = current
        dur = max([int(k[0]) for tr in tracks for k in tr.get("keys", [])] or [0])
        self.span = max(1000, int((max(dur, ms) + 999) // 1000 * 1000 + 500))
        self.setMinimumHeight(self.HEAD + self.ROW * max(1, len(tracks)) + 6)
        self.update()

    def x_of(self, ms: float) -> float:
        return self.LEFT + (self.width() - 2 * self.LEFT) * ms / max(1, self.span)

    def ms_of(self, x: float) -> int:
        ms = (x - self.LEFT) * self.span / max(1, self.width() - 2 * self.LEFT)
        return max(0, int(round(ms / 10.0) * 10))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#2b2b30"))
        p.setPen(QColor("#9a9aa5"))
        step = 100 if self.span <= 3000 else 500
        for t in range(0, self.span + 1, step):
            x = self.x_of(t)
            big = t % 1000 == 0
            p.drawLine(int(x), self.HEAD - (8 if big else 4), int(x), self.HEAD)
            if big:
                p.drawText(int(x) + 2, 11, f"{t // 1000}s")
        for r, tr in enumerate(self.tracks):
            y = self.HEAD + r * self.ROW
            p.fillRect(QRectF(0, y, self.width(), self.ROW - 1),
                       QColor("#3c3c48" if r == self.current else ("#323238" if r % 2 else "#2e2e34")))
            keys = sorted(int(k[0]) for k in tr.get("keys", []))
            if len(keys) > 1:
                p.setPen(QColor("#6d8fd8"))
                p.drawLine(int(self.x_of(keys[0])), y + self.ROW // 2, int(self.x_of(keys[-1])), y + self.ROW // 2)
            p.setPen(QColor("#202020"))
            p.setBrush(QColor("#f0c040"))
            for t in keys:
                cx, cy = self.x_of(t), y + self.ROW / 2
                p.drawPolygon(QPolygonF([QPointF(cx, cy - 6), QPointF(cx + 6, cy), QPointF(cx, cy + 6),
                                         QPointF(cx - 6, cy)]))
        p.setPen(QColor("#ff5050"))
        x = int(self.x_of(self.ms))
        p.drawLine(x, 0, x, self.height())
        p.end()

    def mousePressEvent(self, e):
        pos = e.position()
        row = int((pos.y() - self.HEAD) // self.ROW)
        if 0 <= row < len(self.tracks):
            for k in self.tracks[row].get("keys", []):
                if abs(self.x_of(int(k[0])) - pos.x()) <= 6:
                    self.keyClicked.emit(row, int(k[0]))
                    return
        self.scrubbed.emit(self.ms_of(pos.x()))

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self.scrubbed.emit(self.ms_of(e.position().x()))


# ====================================================================== panel
class TimelinePanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.view = None
        self.ms = 0
        self._filling = False
        self._shadow: dict = {}
        self.timer = QTimer(self)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self._tick)
        self._play_t0 = 0.0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setProperty("radRole", "note")
        lay.addWidget(self.note)
        row = QHBoxLayout()
        self.sb_combo = QComboBox()
        self.sb_combo.currentIndexChanged.connect(self._on_storyboard)
        self.btn_new = QToolButton(text="New")
        self.btn_new.setToolTip("New storyboard")
        self.btn_new.clicked.connect(self.new_storyboard)
        self.btn_ren = QToolButton(text="Rename")
        self.btn_ren.clicked.connect(self.rename_storyboard)
        self.btn_del = QToolButton(text="Delete")
        self.btn_del.clicked.connect(self.delete_storyboard)
        row.addWidget(QLabel("Storyboard:"))
        row.addWidget(self.sb_combo, 1)
        for b in (self.btn_new, self.btn_ren, self.btn_del):
            row.addWidget(b)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.chk_auto = QCheckBox("Begin on Load")
        self.chk_repeat = QCheckBox("Repeat")
        self.chk_rev = QCheckBox("AutoReverse")
        for c, key in ((self.chk_auto, "autostart"), (self.chk_repeat, "repeat"), (self.chk_rev, "autoreverse")):
            c.toggled.connect(lambda on, k=key: self._set_flag(k, on))
            row.addWidget(c)
        row.addStretch(1)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.play)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop)
        self.time = QSpinBox()
        self.time.setRange(0, 600000)
        self.time.setSingleStep(100)
        self.time.setSuffix(" ms")
        self.time.valueChanged.connect(self.seek)
        self.rec = QCheckBox("Record keyframes")
        self.rec.setToolTip("While on, property edits of controls add keyframes at the playhead time.")
        self.rec.toggled.connect(self._on_record)
        for w in (self.btn_play, self.btn_stop, QLabel("Time:"), self.time):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.rec)
        lay.addLayout(row)
        mid = QHBoxLayout()
        self.tracks = QListWidget()
        self.tracks.setMaximumWidth(170)
        self.tracks.currentRowChanged.connect(self._on_track)
        self.ruler = TimelineRuler()
        self.ruler.scrubbed.connect(self.seek)
        self.ruler.keyClicked.connect(self._on_key_clicked)
        mid.addWidget(self.tracks)
        mid.addWidget(self.ruler, 1)
        lay.addLayout(mid, 1)
        self.keys = QTableWidget(0, 3)
        self.keys.setHorizontalHeaderLabels(["Time (ms)", "Value", "Easing"])
        self.keys.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.keys.verticalHeader().hide()
        self.keys.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.keys.setMaximumHeight(130)
        self.keys.itemChanged.connect(self._on_key_edited)
        lay.addWidget(self.keys)
        row = QHBoxLayout()
        self.prop = QComboBox()
        self.value = QLineEdit()
        self.value.setPlaceholderText("value (empty = current)")
        self.btn_key = QPushButton("Add Keyframe")
        self.btn_key.setToolTip("Keyframe of the selected control's property at the playhead time")
        self.btn_key.clicked.connect(self.add_keyframe)
        self.btn_delkey = QToolButton(text="Delete Key")
        self.btn_delkey.clicked.connect(self.delete_keyframe)
        row.addWidget(self.prop)
        row.addWidget(self.value, 1)
        row.addWidget(self.btn_key)
        row.addWidget(self.btn_delkey)
        lay.addLayout(row)
        self.bind(None)

    # ------------------------------------------------------------ binding
    def bind(self, view) -> None:
        if view is self.view and view is not None:
            return
        self.stop()
        if self.view is not None:
            try:
                self.view.doc.selectionChanged.disconnect(self._fill_props)
                self.view.doc.structureChanged.disconnect(self.rebuild)
            except (TypeError, RuntimeError):
                pass
            bp = getattr(self.view, "_blend_preview", None)
            if bp is not None:
                bp.key_recorder = None
        self.view = view
        self.rec.setChecked(False)
        if view is not None:
            view.doc.selectionChanged.connect(self._fill_props)
            view.doc.structureChanged.connect(self.rebuild)
        self.rebuild()

    @property
    def bp(self):
        return BlendPreview.of(self.view) if self.view is not None else None

    def sb(self) -> dict | None:
        if self.view is None:
            return None
        return find_storyboard(self.view.doc.form, self.sb_combo.currentText())

    def rebuild(self, *_a) -> None:
        self._filling = True
        cur = self.sb_combo.currentText()
        self.sb_combo.clear()
        on = self.view is not None
        for w in (self.sb_combo, self.btn_new, self.btn_ren, self.btn_del, self.chk_auto, self.chk_repeat,
                  self.chk_rev, self.btn_play, self.btn_stop, self.time, self.rec, self.tracks, self.keys,
                  self.prop, self.value, self.btn_key, self.btn_delkey):
            w.setEnabled(on)
        if not on:
            self.note.setText("Open a form designer to animate it.")
            self.tracks.clear()
            self.ruler.set_data([], 0, -1)
            self._filling = False
            return
        self.note.setText("" if is_python(self.win, self.view) else
                          "Storyboards run in Python (Tkinter / PySide6) forms; this language ignores them.")
        names = [s.get("name", "") for s in storyboards(self.view.doc.form)]
        self.sb_combo.addItems(names)
        if cur in names:
            self.sb_combo.setCurrentText(cur)
        self._filling = False
        self._on_storyboard()

    def _on_storyboard(self, *_a) -> None:
        if self._filling:
            return
        sb = self.sb()
        self._filling = True
        for c, key in ((self.chk_auto, "autostart"), (self.chk_repeat, "repeat"), (self.chk_rev, "autoreverse")):
            c.setChecked(bool(sb and sb.get(key)))
            c.setEnabled(sb is not None)
        for w in (self.btn_play, self.btn_ren, self.btn_del, self.btn_key, self.rec):
            w.setEnabled(sb is not None)
        row = self.tracks.currentRow()
        self.tracks.clear()
        for tr in (sb or {}).get("tracks", []):
            t = tr.get("target") or (self.view.doc.form.name if self.view else "Form")
            self.tracks.addItem(QListWidgetItem(f"{t}.{tr.get('property')}"))
        if 0 <= row < self.tracks.count():
            self.tracks.setCurrentRow(row)
        self._filling = False
        self._fill_props()
        self._refresh_ruler()
        self._fill_keys()

    def _refresh_ruler(self) -> None:
        sb = self.sb()
        self.ruler.set_data((sb or {}).get("tracks", []), self.ms, self.tracks.currentRow())

    def _fill_props(self, *_a) -> None:
        if self.view is None:
            return
        ctrl = self.view.doc.selected
        cur = self.prop.currentText()
        self.prop.clear()
        if ctrl is None:
            self.prop.addItems(list(FORM_ANIM_PROPS))
        else:
            self.prop.addItems([p for p in ANIM_PROPS if p in ctrl.props or p == "Opacity"])
        if cur:
            self.prop.setCurrentText(cur)

    def _on_track(self, row: int) -> None:
        if self._filling:
            return
        sb = self.sb()
        if sb and 0 <= row < len(sb.get("tracks", [])):
            tr = sb["tracks"][row]
            form = self.view.doc.form
            c = form.find(tr.get("target")) if tr.get("target") else None
            if c is not None or not tr.get("target"):
                self.view.doc.select(c)
            self.prop.setCurrentText(tr.get("property", ""))
        self._refresh_ruler()
        self._fill_keys()

    def _current_track(self) -> dict | None:
        sb = self.sb()
        row = self.tracks.currentRow()
        if sb and 0 <= row < len(sb.get("tracks", [])):
            return sb["tracks"][row]
        return None

    def _fill_keys(self) -> None:
        self._filling = True
        tr = self._current_track()
        keys = (tr or {}).get("keys", [])
        self.keys.setRowCount(len(keys))
        for r, k in enumerate(keys):
            vals = [str(int(k[0])), str(k[1]), str(k[2]) if len(k) > 2 else "linear"]
            for c, v in enumerate(vals):
                self.keys.setItem(r, c, QTableWidgetItem(v))
        self._filling = False

    # ------------------------------------------------------------ edits
    def _edit(self, fn) -> None:
        doc = self.view.doc
        doc.checkpoint()
        fn()
        doc.set_modified()
        self._on_storyboard()
        self._preview()

    def new_storyboard(self) -> None:
        if self.view is None:
            return
        sb = {}
        self._edit(lambda: sb.update(new_storyboard(self.view.doc.form)))
        self.rebuild()
        self.sb_combo.setCurrentText(sb.get("name", ""))

    def rename_storyboard(self) -> None:
        sb = self.sb()
        if sb is None:
            return
        name, ok = QInputDialog.getText(self, "Rename Storyboard", "New name:", text=sb["name"])
        name = (name or "").strip()
        if not ok or not name or name == sb["name"]:
            return
        form = self.view.doc.form
        if not name.isidentifier() or find_storyboard(form, name) or name.lower() in form.all_names():
            QMessageBox.warning(self, "Rename Storyboard", f"'{name}' is not a valid unused name.")
            return
        self._edit(lambda: sb.update(name=name))
        self.rebuild()
        self.sb_combo.setCurrentText(name)

    def delete_storyboard(self) -> None:
        sb = self.sb()
        if sb is None:
            return
        self.stop()
        self._edit(lambda: storyboards(self.view.doc.form).remove(sb))
        self.rebuild()

    def _set_flag(self, key: str, on: bool) -> None:
        sb = self.sb()
        if self._filling or sb is None or bool(sb.get(key)) == on:
            return
        self._edit(lambda: sb.update({key: bool(on)}))

    def _target(self):
        ctrl = self.view.doc.selected if self.view is not None else None
        if ctrl is not None and ctrl.ctype.nonvisual:
            return None, None
        return ctrl, (ctrl.name if ctrl is not None else "")

    def add_keyframe(self) -> None:
        sb = self.sb()
        if sb is None:
            return
        ctrl, target = self._target()
        if target is None:
            return
        prop = self.prop.currentText()
        text = self.value.text().strip()
        if text:
            value = text
        else:
            props = self.bp.effective(ctrl) if ctrl is not None else self.view.doc.form.props
            value = props.get(prop, 1.0 if prop == "Opacity" else "")
        self._edit(lambda: set_key(sb, target, prop, self.ms, value))
        self.value.clear()
        self._select_track(target, prop)

    def _select_track(self, target: str, prop: str) -> None:
        sb = self.sb()
        for i, tr in enumerate((sb or {}).get("tracks", [])):
            if tr.get("target") == target and tr.get("property") == prop:
                self.tracks.setCurrentRow(i)
                return

    def delete_keyframe(self) -> None:
        tr = self._current_track()
        r = self.keys.currentRow()
        if tr is None or r < 0 or r >= len(tr["keys"]):
            return
        ms = int(tr["keys"][r][0])
        self._edit(lambda: remove_key(self.sb(), tr["target"], tr["property"], ms))

    def _on_key_edited(self, item) -> None:
        tr = self._current_track()
        if self._filling or tr is None or item.row() >= len(tr["keys"]):
            return
        r = item.row()
        cells = [self.keys.item(r, c).text() if self.keys.item(r, c) else "" for c in range(3)]
        try:
            ms = max(0, int(float(cells[0])))
        except ValueError:
            self._fill_keys()
            return
        ease = cells[2].strip().lower()

        def do():
            k = [ms, coerce(tr["property"], cells[1])]
            if ease in EASES and ease != "linear":
                k.append(ease)
            tr["keys"][r] = k
            tr["keys"].sort(key=lambda x: x[0])
        self._edit(do)

    def _on_key_clicked(self, row: int, ms: int) -> None:
        self.tracks.setCurrentRow(row)
        self.seek(ms)
        tr = self._current_track()
        if tr:
            for r, k in enumerate(tr["keys"]):
                if int(k[0]) == ms:
                    self.keys.selectRow(r)

    # ------------------------------------------------------------ playhead / play
    def seek(self, ms) -> None:
        ms = int(ms)
        if self.ms != ms:
            self.ms = ms
        if self.time.value() != ms:
            self.time.blockSignals(True)
            self.time.setValue(ms)
            self.time.blockSignals(False)
        self._refresh_ruler()
        self._preview()

    def _preview(self) -> None:
        sb, bp = self.sb(), self.bp
        if bp is None:
            return
        live = self.ms > 0 or self.timer.isActive() or self.rec.isChecked()   # recording at 0 ms too
        bp.timeline = (sb, self.ms) if sb is not None and live else None
        bp.refresh()

    def play(self) -> None:
        sb = self.sb()
        if sb is None:
            return
        import time
        self._play_t0 = time.monotonic()
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()
        self.ms = 0
        self.time.blockSignals(True)
        self.time.setValue(0)
        self.time.blockSignals(False)
        bp = getattr(self.view, "_blend_preview", None) if self.view is not None else None
        if bp is not None:
            bp.timeline = None
            try:
                bp.refresh()
            except RuntimeError:        # the designer was closed
                pass
        self._refresh_ruler()

    def _tick(self) -> None:
        import time
        sb = self.sb()
        if sb is None:
            self.timer.stop()
            return
        dur = duration(sb)
        span = dur * (2 if sb.get("autoreverse") else 1)
        ms = (time.monotonic() - self._play_t0) * 1000
        if span <= 0 or ms >= span:
            if sb.get("repeat") and span > 0:
                self._play_t0 = time.monotonic()
                ms = 0
            else:
                ms = span
                self.timer.stop()
        local = ms if ms <= dur else span - ms
        self.ms = int(local)
        self.time.blockSignals(True)
        self.time.setValue(self.ms)
        self.time.blockSignals(False)
        self._refresh_ruler()
        bp = self.bp
        bp.timeline = (sb, local)
        bp.refresh()

    # ------------------------------------------------------------ keyframe recording
    def _on_record(self, on: bool) -> None:
        if self.view is None:
            return
        bp = self.bp
        if on and self.sb() is not None:
            form = self.view.doc.form
            self._shadow = {id(c): {k: c.props.get(k) for k in ANIM_PROPS} for c in form.controls}
            bp.key_recorder = self._record
        else:
            bp.key_recorder = None
        self._preview()

    def _record(self, ctrl) -> None:
        sb = self.sb()
        if sb is None or ctrl is None:
            return
        shadow = self._shadow.setdefault(id(ctrl), {k: ctrl.props.get(k) for k in ANIM_PROPS})
        changed = False
        for k in ANIM_PROPS:
            if k in ctrl.props and ctrl.props.get(k) != shadow.get(k):
                if not track(sb, ctrl.name, k, create=False) and self.ms > 0:
                    set_key(sb, ctrl.name, k, 0, shadow.get(k))   # the animation starts from the old value
                set_key(sb, ctrl.name, k, self.ms, ctrl.props[k])
                ctrl.props[k] = shadow.get(k)
                changed = True
        if changed:
            self.view.doc.set_modified()
            self._on_storyboard()
            self._preview()


def install(win) -> None:
    panel = TimelinePanel(win)
    win.timeline_panel = panel
    _add_dock(win, "Objects and Timeline", panel, "dock_timeline")
    follow_designer(win, panel)
