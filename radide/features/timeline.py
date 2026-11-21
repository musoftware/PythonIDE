"""Expression Blend for the form designer (CONTRACTS 8.7) - Storyboards ("Objects and Timeline").

Model, in the .form: ``"storyboards": [{"name": "Storyboard1", "autostart": false, "repeat": false,
"autoreverse": false, "tracks": [{"target": "Button1", "property": "Left",
"keys": [[0, 10], [1000, 200, "out"]]}]}]`` - keyframes are [time ms, value, optional easing
("linear" / "in" / "out" / "inout") of the segment that ends at the key]; target "" = the form.

Generated code (python-tk / python-qt): ``self.Storyboard1 = _Storyboard(...)`` with Begin(), Stop(),
Pause(), Resume(), Seek(ms), IsPlaying, Duration; AutoStart storyboards begin after <Form>_Load, and
``<Storyboard>_Completed`` on the form runs at the end.

IDE: the "Objects and Timeline" dock - storyboards, tracks, keyframes on a time ruler, a playhead to
scrub, Play / Stop in the designer and keyframe recording. Record on: a move / resize / Properties edit
writes ONE keyframe at the time cursor on the tracks of the properties that changed (a new track also
gets a 0 ms keyframe with the designed value); the model keeps the designed (base) values. Record off:
edits change the design (a scrubbed preview is dropped first). The designer shows the timeline only
while recording, playing or scrubbing (time > 0); a red frame says "Recording" (RecordBanner)."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPen, QPolygonF, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFrame, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QToolButton,
                             QVBoxLayout, QWidget)

from .states import (DESIGN, FLOAT_PROPS, INT_PROPS, RESERVED_NAMES, BlendPreview, _add_dock, coerce,
                     compact_combo, follow_designer, is_python, section_label, set_note)

ANIM_PROPS = ("Left", "Top", "Width", "Height", "BackColor", "ForeColor", "Opacity", "FontSize", "Value",
              "Text", "Visible")
FORM_ANIM_PROPS = ("Width", "Height", "BackColor", "Opacity", "Text")
EASES = ("linear", "in", "out", "inout", "back", "elastic", "bounce", "sine")

STORYBOARD_RT = r'''

class _Storyboard:
    """Storyboard (Expression Blend): keyframe animation of control properties.
    Begin() starts from time 0, Stop() stops and puts the animated properties back, Pause() / Resume(),
    Seek(ms), Reverse() plays back to time 0; at the end the last values stay (HoldEnd), the callables in
    Completed run and then the form's <Name>_Completed(). RepeatForever, Count (plays) and AutoReverse can
    be changed before Begin(). Keyframe values may be relative to the values at Begin ({"d": -50} ...)."""

    def __init__(self, owner, io, name, tracks, repeat=False, autoreverse=False, count=1):
        self._o, self._io, self.Name = owner, io, name
        self._raw = [(t, p, sorted(((k[0], k[1], k[2] if len(k) > 2 else "") for k in keys), key=lambda k: k[0]))
                     for t, p, keys in tracks]
        self.Tracks = self._raw
        self.RepeatForever, self.AutoReverse = bool(repeat), bool(autoreverse)
        self.Count = max(1, int(count or 1))
        self.Duration = max([k[0] for _t, _p, keys in self._raw for k in keys] or [0])
        self.IsPlaying, self.Position = False, 0
        self.Completed = []                 # callables run when the storyboard ends (chains)
        self._gen, self._saved, self._t0, self._paused, self._rev, self._last = 0, {}, 0.0, None, False, {}

    def _remember(self):
        if self._saved:
            return
        self._saved = {(t, p): self._io.get(t, p) for t, p, _k in self._raw}
        self._last = {}
        if not any(_rad_has_relative(keys) for _t, _p, keys in self._raw):
            self.Tracks = self._raw
            return

        def ref(t):
            def get(prop):
                if prop == "$parent":
                    fn = getattr(self._io, "parent_bg", None)
                    return fn(t) if fn is not None else None
                if (t, prop) not in self._saved:
                    self._saved[(t, prop)] = self._io.get(t, prop)
                return self._saved[(t, prop)]
            return get
        self.Tracks = [(t, p, _rad_resolve_keys(p, keys, self._saved.get((t, p)), ref(t)))
                       for t, p, keys in self._raw]
        self._saved = {k: v for k, v in self._saved.items() if any(k == (t, p) for t, p, _k in self._raw)}

    def _apply(self, ms):
        self.Position = ms
        for t, p, keys in self.Tracks:
            v = _rad_value_at(p, keys, ms, self._saved.get((t, p)),
                              lambda c, t=t, p=p: self._io.rgb(t, p, c))
            if self._last.get((t, p), self) == v and p == "Visible":
                continue                    # (re-showing every frame re-places the widget)
            self._last[(t, p)] = v
            self._io.set(t, p, v)

    def Begin(self):
        self._remember()
        self._gen += 1
        self.IsPlaying, self._paused, self._rev = True, None, False
        self._t0 = _time.monotonic()
        self._tick(self._gen)

    def Reverse(self):
        """Play from the current position back to time 0 (then Stop(): the values are back)."""
        if not self._saved:
            return
        self._gen += 1
        self.IsPlaying, self._paused, self._rev = True, None, True
        self._t0 = _time.monotonic() - (self.Duration - min(self.Position, self.Duration)) / 1000.0
        self._tick(self._gen)

    def _tick(self, gen):
        if gen != self._gen or not self.IsPlaying:
            return
        ms = (_time.monotonic() - self._t0) * 1000.0
        if self._rev:
            pos = self.Duration - ms
            if pos <= 0:
                self.Stop()
                return
            self._apply(pos)
            self._io.later(15, lambda: self._tick(gen))
            return
        span = self.Duration * (2 if self.AutoReverse else 1)
        total = span * self.Count
        done = False
        if span <= 0:
            ms, done = 0, True
        elif self.RepeatForever:
            if ms >= span:
                self._t0 += (ms // span) * span / 1000.0
                ms %= span
        elif ms >= total:
            ms, done = span, True
        else:
            ms %= span
        self._apply(ms if ms <= self.Duration else span - ms)
        if done:
            self._completed()
            return
        self._io.later(15, lambda: self._tick(gen))

    def _completed(self):
        self.IsPlaying = False
        for fn in list(self.Completed):
            fn()
        fn = getattr(self._o, self.Name + "_Completed", None)
        if callable(fn):
            fn()

    def Finish(self):
        """Jump to the end at once (reduced motion) and run the Completed callbacks."""
        self._remember()
        self._gen += 1
        self._paused = None
        self._apply(0 if self.AutoReverse else self.Duration)
        self._completed()

    def Stop(self):
        self._gen += 1
        self.IsPlaying, self._paused, self.Position, self._rev = False, None, 0, False
        for (t, p), v in self._saved.items():
            self._io.set(t, p, v)
            if p in ("Left", "Top", "Width", "Height"):
                self._io.release(t, p)          # Anchor / Dock take the control back
        self._saved, self._last = {}, {}

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
    if not create or not prop or prop not in ANIM_PROPS:
        return None                     # never a track without a (valid) property ("btnCalc.")
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
        v = k[1] if isinstance(k[1], dict) or k[1] == "$parent" else coerce(prop, k[1])  # relative
        out.append((ms, v, "" if ease == "linear" else ease))
    out.sort(key=lambda x: x[0])
    return out


def set_key(sb: dict, target: str, prop: str, ms: int, value, ease: str | None = None) -> bool:
    """Create / update THE keyframe of target.prop at *ms* (one per time). ease None = keep the easing of
    the keyframe already at that time. False when the property is not animatable / the value is missing."""
    if value is None or (value == "" and prop in INT_PROPS | FLOAT_PROPS):
        return False
    tr = track(sb, target, prop)
    if tr is None:
        return False
    ms = max(0, int(round(float(ms))))
    old = next((k for k in tr["keys"] if int(k[0]) == ms), None)
    if ease is None:
        ease = str(old[2]) if old is not None and len(old) > 2 else ""
    keys = [k for k in tr["keys"] if int(k[0]) != ms]
    k = [ms, coerce(prop, value)]
    if ease and ease != "linear":
        k.append(ease)
    keys.append(k)
    keys.sort(key=lambda x: x[0])
    tr["keys"] = keys
    return True


def move_key(sb: dict, tr: dict, old_ms: int, new_ms: int) -> None:
    """Move the keyframe at old_ms of *tr* to new_ms (a keyframe already there is replaced)."""
    key = next((k for k in tr.get("keys", []) if int(k[0]) == int(old_ms)), None)
    if key is None or int(old_ms) == int(new_ms):
        return
    keys = [k for k in tr["keys"] if int(k[0]) not in (int(old_ms), int(new_ms))]
    keys.append([max(0, int(new_ms))] + list(key[1:]))
    keys.sort(key=lambda x: x[0])
    tr["keys"] = keys


def repair_storyboards(form) -> int:
    """Clean storyboards saved by older versions: drop tracks without a property name (the broken
    "btnCalc." track), keyframes without a value and tracks left without keyframes; duplicate
    keyframes at one time keep the last. Returns how many tracks / keyframes were dropped."""
    dropped = 0
    sbs = form.extra.get("storyboards")
    if not isinstance(sbs, list):
        return 0
    for sb in [s for s in sbs if not isinstance(s, dict)]:
        sbs.remove(sb)
        dropped += 1
    for sb in sbs:
        tracks = sb.get("tracks")
        if not isinstance(tracks, list):
            sb["tracks"] = []
            continue
        keep = []
        for tr in tracks:
            p = tr.get("property") if isinstance(tr, dict) else None
            if not isinstance(p, str) or not p.strip():
                dropped += 1
                continue
            keys = {}
            for k in tr.get("keys") or []:
                if (not isinstance(k, (list, tuple)) or len(k) < 2 or k[1] is None
                        or (k[1] == "" and p in INT_PROPS | FLOAT_PROPS)):
                    dropped += 1
                    continue
                try:
                    ms = max(0, int(round(float(k[0]))))
                except (TypeError, ValueError):
                    dropped += 1
                    continue
                keys[ms] = [ms] + list(k[1:])
            if not keys:
                dropped += 1
                continue
            tr["keys"] = [keys[m] for m in sorted(keys)]
            keep.append(tr)
        sb["tracks"] = keep
    return dropped


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


def props_at(sb: dict, target: str, ms: float, base: dict, parent_bg: str | None = None) -> dict:
    """Design-time values of the tracks of *target* at time *ms* (same algorithm as the generated code).
    Tracks may be dicts (.form storyboards) or (target, prop, keys) tuples (motion.expand storyboards);
    relative keyframes resolve against *base*, "$parent" against *parent_bg*."""
    out = {}
    start_of = {}

    def start(p):
        if p not in start_of:
            v = base.get(p, {"Opacity": 1.0, "ScaleX": 1.0, "ScaleY": 1.0, "Rotation": 0.0}.get(p))
            if p in ("BackColor", "ForeColor") and not v:
                v = "#f0f0f0" if p == "BackColor" else "#000000"
            start_of[p] = v
        return start_of[p]

    def ref(p):
        return (parent_bg or "#f0f0f0") if p == "$parent" else start(p)
    for tr in sb.get("tracks", []):
        if isinstance(tr, dict):
            t, p, raw = tr.get("target"), tr.get("property"), tr.get("keys")
        else:
            t, p, raw = tr[0], tr[1], tr[2]
        if (t or "") != (target or ""):
            continue
        keys = norm_keys(p, raw)
        if not keys:
            continue
        s0 = start(p)
        keys = DESIGN["_rad_resolve_keys"](p, keys, s0, ref)
        out[p] = DESIGN["_rad_value_at"](p, keys, ms, s0, _rgb)
    return out


# ====================================================================== timeline ruler
HELP_TEXT = ("1. Turn on Record  2. Move the time cursor  3. Move or change a control - a keyframe is added  "
             "4. Play to preview; Begin on Load starts it when the program runs")
_STEPS = (10, 20, 50, 100, 200, 250, 500, 1000, 2000, 5000, 10000, 30000, 60000)


def _tr(text: str) -> str:
    try:
        from ..i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001 - no catalog (tests)
        return text


class TimelineRuler(QWidget):
    """Tracks as rows, keyframes as diamonds and the time cursor (playhead).
    Click / drag the ruler (or an empty part of a row) to move the time cursor; click a diamond to select
    it, drag it to change its time, Del / right-click to delete it; Ctrl+wheel zooms."""
    scrubbed = pyqtSignal(int)
    rowClicked = pyqtSignal(int)
    keySelected = pyqtSignal(int, int)         # track row, time ms
    keyMoved = pyqtSignal(int, int, int)       # track row, old ms, new ms
    deleteRequested = pyqtSignal()
    easeRequested = pyqtSignal(str)
    zoomRequested = pyqtSignal(float)

    ROW = 22
    HEAD = 24
    LEFT = 8

    def __init__(self):
        super().__init__()
        self.tracks: list[dict] = []
        self.ms = 0
        self.dur = 0
        self.span = 2000
        self.current = -1
        self.sel: tuple[int, int] | None = None    # (row, ms) of the selected keyframe
        self._drag = None                          # "head" | [row, old ms, new ms]
        self.setMinimumHeight(self.HEAD + self.ROW + 8)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setToolTip("Time cursor: click or drag on the ruler to move it (the designer shows the animation "
                        "at that time).\nKeyframes (diamonds): click to select, drag to change the time, Del or "
                        "right-click to delete.\nCtrl+wheel zooms the timeline.")
        try:
            from .. import theme
            theme.changed.connect(lambda *_: self.update())
        except Exception:  # noqa: BLE001 - no theme manager (tests): the default colours are used
            pass

    @staticmethod
    def colours() -> dict:
        """Ruler colours from the IDE theme."""
        try:
            from .. import theme
            t = theme.current()
        except Exception:  # noqa: BLE001
            t = {}
        g = lambda k, d: t.get(k) or d          # noqa: E731
        return {"back": g("base", "#ffffff"), "tick": g("muted", "#5a5a5a"), "row": g("base", "#ffffff"),
                "row_alt": g("alt_base", "#f5f5f0"), "row_cur": g("menu_sel", "#c1d2ee"),
                "span": g("accent", "#316ac5"), "key_pen": g("text", "#000000"), "head": "#d13438",
                "line": g("mid", "#b8b8b0"), "text": g("text", "#000000")}

    def set_data(self, tracks: list[dict], ms: int, current: int, sel=None) -> None:
        self.tracks = tracks
        self.ms = int(ms)
        self.current = current
        self.sel = sel
        self.dur = max([int(k[0]) for tr in tracks for k in tr.get("keys", [])] or [0])
        top = max(self.dur * 1.2, self.ms + 300, 2000)
        self.span = int((top + 499) // 500 * 500)
        self.setMinimumHeight(self.HEAD + self.ROW * max(1, len(tracks)) + 8)
        self.update()

    def x_of(self, ms: float) -> float:
        return self.LEFT + (self.width() - 2 * self.LEFT) * ms / max(1, self.span)

    def ms_of(self, x: float) -> int:
        ms = (x - self.LEFT) * self.span / max(1, self.width() - 2 * self.LEFT)
        return max(0, int(round(ms / 10.0) * 10))

    def _key_at(self, pos) -> tuple[int, int] | None:
        row = int((pos.y() - self.HEAD) // self.ROW)
        if pos.y() < self.HEAD or not 0 <= row < len(self.tracks):
            return None
        best = None
        for k in self.tracks[row].get("keys", []):
            d = abs(self.x_of(int(k[0])) - pos.x())
            if d <= 7 and (best is None or d < best[0]):
                best = (d, int(k[0]))
        return (row, best[1]) if best else None

    # ------------------------------------------------------------ paint
    def paintEvent(self, _e):
        c = self.colours()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(c["back"]))
        pps = (self.width() - 2 * self.LEFT) / max(1, self.span)
        minor = next((s for s in _STEPS if s * pps >= 7), _STEPS[-1])
        label = next((s for s in _STEPS if s * pps >= 48 and s % minor == 0), _STEPS[-1])
        p.setPen(QColor(c["tick"]))
        f = p.font()
        f.setPointSizeF(max(6.5, f.pointSizeF() - 1.5))
        p.setFont(f)
        for t in range(0, self.span + 1, minor):
            x = int(self.x_of(t))
            big = t % label == 0
            p.drawLine(x, self.HEAD - (9 if big else 4), x, self.HEAD)
            if big:
                p.drawText(x + 2, 11, f"{t / 1000:g}s")
        p.setPen(QColor(c["line"]))
        p.drawLine(0, self.HEAD, self.width(), self.HEAD)
        bottom = self.HEAD + self.ROW * max(1, len(self.tracks))
        for r, tr in enumerate(self.tracks):
            y = self.HEAD + r * self.ROW
            p.fillRect(QRectF(0, y, self.width(), self.ROW - 1),
                       QColor(c["row_cur"] if r == self.current else (c["row_alt"] if r % 2 else c["row"])))
            keys = sorted(int(k[0]) for k in tr.get("keys", []))
            if self._drag not in (None, "head") and self._drag[0] == r:
                keys = sorted([t for t in keys if t != self._drag[1]] + [self._drag[2]])
            cy = y + self.ROW / 2
            if len(keys) > 1:
                p.setPen(QPen(QColor(c["span"]), 2 if r == self.current else 1))
                p.drawLine(QPointF(self.x_of(keys[0]), cy), QPointF(self.x_of(keys[-1]), cy))
            for t in keys:
                sel = self.sel is not None and self.sel[0] == r and (
                    self.sel[1] == t or (self._drag not in (None, "head") and self._drag[2] == t))
                s = 7 if (r == self.current or sel) else 5.5
                p.setPen(QPen(QColor("#ffffff" if sel else c["key_pen"]), 1.5 if sel else 1))
                p.setBrush(QColor(c["head"] if sel else ("#f0b400" if r == self.current else "#e3c97a")))
                cx = self.x_of(t)
                p.drawPolygon(QPolygonF([QPointF(cx, cy - s), QPointF(cx + s, cy), QPointF(cx, cy + s),
                                         QPointF(cx - s, cy)]))
        if self.dur > 0:                         # end of the storyboard
            x = self.x_of(self.dur)
            p.fillRect(QRectF(x, self.HEAD, self.width() - x, bottom - self.HEAD), QColor(128, 128, 128, 40))
            pen = QPen(QColor(c["span"]))
            pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(QPointF(x, self.HEAD - 6), QPointF(x, bottom))
        # time cursor (playhead) with a handle in the ruler
        x = self.x_of(self.ms)
        p.setPen(QPen(QColor(c["head"]), 2))
        p.drawLine(QPointF(x, self.HEAD - 2), QPointF(x, self.height()))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["head"]))
        p.drawPolygon(QPolygonF([QPointF(x - 6, 12), QPointF(x + 6, 12), QPointF(x + 6, self.HEAD - 6),
                                 QPointF(x, self.HEAD), QPointF(x - 6, self.HEAD - 6)]))
        txt = f"{self.ms} ms"
        tw = p.fontMetrics().horizontalAdvance(txt) + 6
        tx = x + 8 if x + 8 + tw < self.width() else x - 8 - tw
        p.setBrush(QColor(c["head"]))
        p.drawRoundedRect(QRectF(tx, 1, tw, 13), 3, 3)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(tx, 1, tw, 13), Qt.AlignmentFlag.AlignCenter, txt)
        p.end()

    # ------------------------------------------------------------ mouse / keys
    def mousePressEvent(self, e):
        pos = e.position()
        hit = self._key_at(pos)
        if e.button() == Qt.MouseButton.RightButton:
            if hit is not None:
                self.keySelected.emit(*hit)
                self._key_menu(e.globalPosition().toPoint())
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if hit is not None:
            self.keySelected.emit(*hit)
            self._drag = [hit[0], hit[1], hit[1]]
            return
        row = int((pos.y() - self.HEAD) // self.ROW)
        if pos.y() >= self.HEAD and 0 <= row < len(self.tracks):
            self.rowClicked.emit(row)
        self._drag = "head"
        self.scrubbed.emit(self.ms_of(pos.x()))

    def mouseMoveEvent(self, e):
        if not e.buttons() & Qt.MouseButton.LeftButton or self._drag is None:
            return
        ms = self.ms_of(e.position().x())
        if self._drag == "head":
            self.scrubbed.emit(ms)
        else:
            self._drag[2] = ms
            self.update()

    def mouseReleaseEvent(self, _e):
        d, self._drag = self._drag, None
        if d not in (None, "head") and d[2] != d[1]:
            self.keyMoved.emit(d[0], d[1], d[2])
        self.update()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.sel is not None:
            self.deleteRequested.emit()
            return
        super().keyPressEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoomRequested.emit(1.25 if e.angleDelta().y() > 0 else 0.8)
            e.accept()
            return
        super().wheelEvent(e)

    def _key_menu(self, gpos) -> None:
        from PyQt6.QtWidgets import QMenu
        m = QMenu(self)
        m.addAction(_tr("Delete Keyframe"), self.deleteRequested.emit)
        sub = m.addMenu(_tr("Easing"))
        for ease in EASES:
            sub.addAction(ease, lambda e=ease: self.easeRequested.emit(e))
        m.exec(gpos)


# ====================================================================== designer banner
class RecordBanner(QWidget):
    """Red frame + "● Recording" label over the designer while keyframes are recorded (Blend's
    "Timeline recording is on"), a blue label while a storyboard plays. Mouse-transparent."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.mode = ""                  # "" | "rec" | "play"
        self.text = ""
        self.setObjectName("timelineRecordBanner")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        view.viewport().installEventFilter(self)
        self.hide()

    @staticmethod
    def of(view, create: bool = True):
        b = view.findChild(RecordBanner, "timelineRecordBanner", Qt.FindChildOption.FindDirectChildrenOnly)
        if b is None and create:
            b = RecordBanner(view)
        return b

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if ev.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show) and self.mode:
            self._place()
        return False

    def _place(self) -> None:
        self.setGeometry(self.view.viewport().geometry())
        self.raise_()

    def set_mode(self, mode: str, text: str = "") -> None:
        self.mode, self.text = mode, text
        if mode:
            self._place()
            self.show()
            self.update()
        else:
            self.hide()

    def paintEvent(self, _e):
        if not self.mode:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = QColor("#d13438") if self.mode == "rec" else QColor("#0f6cbd")
        if self.mode == "rec":
            p.setPen(QPen(col, 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(2, 2, self.width() - 4, self.height() - 4))
        f = p.font()
        f.setBold(True)
        p.setFont(f)
        tw = p.fontMetrics().horizontalAdvance(self.text) + 20
        tw = min(tw, self.width() - 20)          # top-right: the form's caption stays visible
        r = QRectF(self.width() - tw - 22, 10, tw, p.fontMetrics().height() + 8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(r, 5, 5)
        p.setPen(QColor("#ffffff"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text)
        p.end()


# ====================================================================== panel
class TimelinePanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.view = None
        self.ms = 0
        self.zoom = 1.0
        self.playing = False
        self._filling = False
        self._shadow: dict = {}             # base (designed) values while recording: {target: {prop: v}}
        self._sel: tuple[int, int] | None = None
        self.timer = QTimer(self)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self._tick)
        self._play_t0 = 0.0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.help = QLabel(HELP_TEXT)
        self.help.setWordWrap(True)
        self.help.setProperty("radRole", "note")
        self.help.setToolTip("Record: while it is on, moving / resizing a control in the designer or changing a "
                             "property in the Properties window adds a keyframe at the time cursor.\n"
                             "Play: runs the storyboard in the designer from the time cursor to the end; Stop puts "
                             "the controls back where you designed them.")
        lay.addWidget(self.help)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setProperty("radRole", "note")
        lay.addWidget(self.note)
        self.note.hide()                        # shown only when it has something to say (no empty gap)
        lay.addWidget(section_label("Storyboard"))
        row = QHBoxLayout()
        self.sb_combo = QComboBox()
        self.sb_combo.setPlaceholderText("(none - click New)")
        compact_combo(self.sb_combo, 6)
        self.sb_combo.currentIndexChanged.connect(self._on_storyboard)
        self.btn_new = QToolButton(text="New")
        self.btn_new.setToolTip("New storyboard")
        self.btn_new.clicked.connect(self.new_storyboard)
        self.btn_ren = QToolButton(text="Rename")
        self.btn_ren.clicked.connect(self.rename_storyboard)
        self.btn_del = QToolButton(text="Delete")
        self.btn_del.clicked.connect(self.delete_storyboard)
        row.addWidget(self.sb_combo, 1)
        lay.addLayout(row)
        row = QHBoxLayout()                     # (own row: the panel lives in a narrow dock column)
        for b in (self.btn_new, self.btn_ren, self.btn_del):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.chk_auto = QCheckBox("Begin on Load")
        self.chk_auto.setToolTip("The storyboard starts by itself when the program runs (after Form_Load).")
        self.chk_repeat = QCheckBox("Repeat")
        self.chk_repeat.setToolTip("Start again from the beginning at the end (forever) - in the designer too.")
        self.chk_rev = QCheckBox("AutoReverse")
        self.chk_rev.setToolTip("Play forward, then backward to the start.")
        for c, key in ((self.chk_auto, "autostart"), (self.chk_repeat, "repeat"), (self.chk_rev, "autoreverse")):
            c.toggled.connect(lambda on, k=key: self._set_flag(k, on))
            if c is self.chk_rev:              # (two rows: the panel lives in a narrow dock column)
                row.addStretch(1)
                lay.addLayout(row)
                row = QHBoxLayout()
            row.addWidget(c)
        row.addStretch(1)
        lay.addLayout(row)
        row = QHBoxLayout()                     # record: the main switch of keyframe animation
        self.rec = QCheckBox("● Record keyframes")
        self.rec.setObjectName("timelineRecord")
        self.rec.setStyleSheet("QCheckBox#timelineRecord:checked { color: #d13438; font-weight: bold; }")
        self.rec.setToolTip("Record: while it is on, moving / resizing a control in the designer or changing a "
                            "property in the Properties window adds ONE keyframe at the time cursor for the "
                            "properties that changed.\nWhile it is off, edits change the designed (base) form.")
        self.rec.toggled.connect(self._on_record)
        row.addWidget(self.rec)
        row.addStretch(1)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.btn_play = QToolButton(text="▶ Play")
        self.btn_play.setToolTip("Play: runs the storyboard in the designer from the time cursor to the end "
                                 "(honours Repeat / AutoReverse). The controls cannot be edited while it plays.")
        self.btn_play.clicked.connect(self.play)
        self.btn_stop = QToolButton(text="■ Stop")
        self.btn_stop.setToolTip("Stop: puts the controls back where you designed them and the time cursor at 0.")
        self.btn_stop.clicked.connect(self.stop)
        self.time = QSpinBox()
        self.time.setRange(0, 600000)
        self.time.setSingleStep(100)
        self.time.setSuffix(" ms")
        self.time.setToolTip("Time cursor (ms): type a time or drag the red cursor on the timeline")
        self.time.valueChanged.connect(self.seek)
        for w in (self.btn_play, self.btn_stop, self.time):
            row.addWidget(w)
        row.addStretch(1)
        lay.addLayout(row)
        self.dur_label = QLabel("")
        self.dur_label.setProperty("radRole", "note")
        lay.addWidget(self.dur_label)
        mid = QHBoxLayout()
        mid.setSpacing(0)
        self.tracks = QListWidget()
        self.tracks.setMaximumWidth(150)
        self.tracks.setFrameShape(QFrame.Shape.NoFrame)
        self.tracks.setUniformItemSizes(True)
        self.tracks.setToolTip("Animated properties (tracks). Turn on Record and move / change a control to add one.")
        self.tracks.currentRowChanged.connect(self._on_track)
        self.ruler = TimelineRuler()
        self.ruler.scrubbed.connect(self.seek)
        self.ruler.rowClicked.connect(self._on_row_clicked)
        self.ruler.keySelected.connect(self._on_key_clicked)
        self.ruler.keyMoved.connect(self._on_key_moved)
        self.ruler.deleteRequested.connect(self.delete_keyframe)
        self.ruler.easeRequested.connect(self._set_ease)
        self.ruler.zoomRequested.connect(self._zoom)
        self.ruler_area = QScrollArea()
        self.ruler_area.setFrameShape(QFrame.Shape.NoFrame)
        self.ruler_area.setWidgetResizable(True)
        self.ruler_area.setWidget(self.ruler)
        self.ruler_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(section_label("Tracks"))
        spacer = QWidget()
        spacer.setFixedHeight(TimelineRuler.HEAD)
        col.addWidget(spacer)
        col.addWidget(self.tracks, 1)
        mid.addLayout(col)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(section_label("Timeline"))
        col.addWidget(self.ruler_area, 1)
        mid.addLayout(col, 1)
        lay.addLayout(mid, 1)
        lay.addWidget(section_label("Keyframes of the selected track"))
        self.keys = QTableWidget(0, 3)
        self.keys.setHorizontalHeaderLabels(["Time (ms)", "Value", "Easing"])
        self.keys.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.keys.verticalHeader().hide()
        self.keys.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.keys.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.keys.setMaximumHeight(130)
        self.keys.setToolTip("Edit a keyframe's time or value here; Easing = how the move into this keyframe "
                             "speeds up / slows down. Del deletes the selected keyframe.")
        self.keys.itemChanged.connect(self._on_key_edited)
        self.keys.itemSelectionChanged.connect(self._on_key_row)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self.keys, self.delete_keyframe,
                  context=Qt.ShortcutContext.WidgetShortcut)
        lay.addWidget(self.keys)
        row = QHBoxLayout()
        self.prop = QComboBox()
        self.prop.setPlaceholderText("Property")
        compact_combo(self.prop, 6)
        self.prop.setToolTip("Property of the selected control to animate")
        self.value = QLineEdit()
        self.value.setPlaceholderText("value (empty = current)")
        self.value.setToolTip("Value of the keyframe; empty = the value the control shows now")
        self.btn_key = QPushButton("Add Keyframe")
        self.btn_key.setToolTip("Keyframe of the selected control's property at the time cursor")
        self.btn_key.clicked.connect(self.add_keyframe)
        self.btn_delkey = QToolButton(text="Delete Key")
        self.btn_delkey.setToolTip("Delete the selected keyframe (Del)")
        self.btn_delkey.clicked.connect(self.delete_keyframe)
        row.addWidget(self.prop)
        row.addWidget(self.value, 1)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.btn_key)
        row.addWidget(self.btn_delkey)
        lay.addLayout(row)
        self.bind(None)

    # ------------------------------------------------------------ binding
    def bind(self, view) -> None:
        if view is self.view and view is not None:
            return
        self.stop()
        old = self.view
        if old is not None:
            try:
                old.doc.selectionChanged.disconnect(self._fill_props)
                old.doc.structureChanged.disconnect(self.rebuild)
            except (TypeError, RuntimeError):
                pass
            bp = getattr(old, "_blend_preview", None)
            if bp is not None:
                bp.key_recorder = None
                bp.timeline_release = None
            try:
                b = RecordBanner.of(old, create=False)
                if b is not None:
                    b.set_mode("")
            except RuntimeError:                # the designer was closed
                pass
        self.view = None                        # (unchecking Record must not touch the new designer)
        self.rec.blockSignals(True)
        self.rec.setChecked(False)
        self.rec.blockSignals(False)
        self._shadow = {}
        self._sel = None
        self.view = view
        if view is not None:
            view.doc.selectionChanged.connect(self._fill_props)
            view.doc.structureChanged.connect(self.rebuild)
            n = repair_storyboards(view.doc.form)
            if n:                               # (saved with the form on the next Save)
                self._repaired = n
        self.rebuild()
        if view is not None and getattr(self, "_repaired", 0):
            set_note(self.note, _tr("Repaired the storyboards: removed {} broken tracks / keyframes "
                                    "(no property or no value).").format(self._repaired))
            self._repaired = 0

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
            set_note(self.note, "Open a form designer to animate it.")
            self.tracks.clear()
            self.ruler.set_data([], 0, -1)
            self.dur_label.setText("")
            self._filling = False
            return
        set_note(self.note, "" if is_python(self.win, self.view) else
                 "Storyboards run in Python (Tkinter / PySide6) forms; this language ignores them.")
        repair_storyboards(self.view.doc.form)     # (an undo can bring back old data)
        names = [s.get("name", "") for s in storyboards(self.view.doc.form)]
        self.sb_combo.addItems(names)
        if cur in names:
            self.sb_combo.setCurrentText(cur)
        elif names:                             # (the placeholder kept it at -1: tracks looked empty)
            self.sb_combo.setCurrentIndex(0)
        self._filling = False
        if self.rec.isChecked():
            self._snapshot()                   # an undo / a rename: the base values may have changed
        self._on_storyboard()
        if self.rec.isChecked() or self.playing or self.ms > 0:
            self._preview()

    def _on_storyboard(self, *_a) -> None:
        if self._filling:
            return
        sb = self.sb()
        self._filling = True
        for c, key in ((self.chk_auto, "autostart"), (self.chk_repeat, "repeat"), (self.chk_rev, "autoreverse")):
            c.setChecked(bool(sb and sb.get(key)))
            c.setEnabled(sb is not None)
        for w in (self.btn_ren, self.btn_del, self.btn_key, self.btn_play, self.btn_delkey):
            w.setEnabled(sb is not None)
        self.rec.setEnabled(self.view is not None)     # (Record with no storyboard creates Storyboard1)
        row = self.tracks.currentRow()
        self.tracks.clear()
        for tr in (sb or {}).get("tracks", []):
            t = tr.get("target") or (self.view.doc.form.name if self.view else "Form")
            it = QListWidgetItem(f"{t}.{tr.get('property')}")
            it.setSizeHint(QSize(0, TimelineRuler.ROW))
            self.tracks.addItem(it)
        if 0 <= row < self.tracks.count():
            self.tracks.setCurrentRow(row)
        self._filling = False
        self._fill_props()
        self._refresh_ruler()
        self._fill_keys()
        self._lock_playing(self.playing)

    def _refresh_ruler(self) -> None:
        sb = self.sb()
        tracks = (sb or {}).get("tracks", [])
        if self._sel is not None and not (0 <= self._sel[0] < len(tracks) and any(
                int(k[0]) == self._sel[1] for k in tracks[self._sel[0]].get("keys", []))):
            self._sel = None
        self.ruler.set_data(tracks, self.ms, self.tracks.currentRow(), self._sel)
        d = duration(sb) if sb else 0
        self.dur_label.setText(_tr("Duration: {} ms").format(d) if sb else "")
        self.tracks.setMinimumHeight(self.ruler.minimumHeight())

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
        if cur and self.prop.findText(cur) >= 0:
            self.prop.setCurrentText(cur)
        elif self.prop.count():
            self.prop.setCurrentIndex(0)

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
            if self.prop.findText(tr.get("property", "")) >= 0:
                self.prop.setCurrentText(tr.get("property", ""))
        if self._sel is not None and self._sel[0] != row:
            self._sel = None
        self._refresh_ruler()
        self._fill_keys()

    def _on_row_clicked(self, row: int) -> None:
        if row != self.tracks.currentRow():
            self.tracks.setCurrentRow(row)

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
        self.keys.setRowCount(0)                # (drops the old Easing combo boxes)
        self.keys.setRowCount(len(keys))
        sel_row = -1
        for r, k in enumerate(keys):
            for c, v in enumerate((str(int(k[0])), str(k[1]))):
                self.keys.setItem(r, c, QTableWidgetItem(v))
            ease = str(k[2]) if len(k) > 2 and str(k[2]) in EASES else "linear"
            self.keys.setItem(r, 2, QTableWidgetItem(""))
            cb = QComboBox()
            cb.addItems(list(EASES))
            cb.setCurrentText(ease)
            cb.setToolTip("linear = constant speed; in = starts slowly; out = ends slowly; inout = both")
            cb.currentTextChanged.connect(lambda e, ms=int(k[0]): self._set_ease(e, ms))
            self.keys.setCellWidget(r, 2, cb)
            if self._sel is not None and self._sel[0] == self.tracks.currentRow() and self._sel[1] == int(k[0]):
                sel_row = r
        if sel_row >= 0:
            self.keys.selectRow(sel_row)
        else:
            self.keys.clearSelection()
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
        if sb is None or self.playing:
            return
        ctrl, target = self._target()
        if target is None:
            return
        prop = self.prop.currentText()
        if prop not in (ANIM_PROPS if ctrl is not None else FORM_ANIM_PROPS):
            set_note(self.note, "Choose the property to animate first.")
            return
        text = self.value.text().strip()
        if text:
            value = text
        else:
            props = self.bp.design_props(ctrl) if ctrl is not None else self.view.doc.form.props
            value = props.get(prop, 1.0 if prop == "Opacity" else None)
            if value is None:
                set_note(self.note, "Type a value for the keyframe.")
                return
        base = (ctrl.props if ctrl is not None else self.view.doc.form.props).get(prop)

        def do():
            if track(sb, target, prop, create=False) is None and self.ms > 0 and base is not None:
                set_key(sb, target, prop, 0, base, ease="")     # the animation starts from the design
            set_key(sb, target, prop, self.ms, value)
        self._edit(do)
        self.value.clear()
        self._select_track(target, prop, self.ms)

    def _select_track(self, target: str, prop: str, ms: int | None = None) -> None:
        sb = self.sb()
        for i, tr in enumerate((sb or {}).get("tracks", [])):
            if tr.get("target") == target and tr.get("property") == prop:
                if ms is not None:
                    self._sel = (i, int(ms))
                self._filling = True        # (no doc.select: a drag may be moving a multi-selection)
                self.tracks.setCurrentRow(i)
                self._filling = False
                if self.prop.findText(prop) >= 0:
                    self.prop.setCurrentText(prop)
                self._refresh_ruler()
                self._fill_keys()
                return

    def _selected_key(self) -> tuple[dict, int] | None:
        tr = self._current_track()
        if tr is None:
            return None
        if self._sel is not None and self._sel[0] == self.tracks.currentRow():
            return tr, self._sel[1]
        r = self.keys.currentRow()
        if 0 <= r < len(tr["keys"]) and self.keys.selectionModel().hasSelection():
            return tr, int(tr["keys"][r][0])
        return None

    def delete_keyframe(self) -> None:
        sk = self._selected_key()
        if sk is None or self.playing:
            return
        tr, ms = sk
        self._sel = None
        self._edit(lambda: remove_key(self.sb(), tr["target"], tr["property"], ms))

    def _set_ease(self, ease: str, ms: int | None = None) -> None:
        if self._filling or self.playing:
            return
        tr = self._current_track()
        if ms is None:
            sk = self._selected_key()
            if sk is None:
                return
            tr, ms = sk
        if tr is None or ease not in EASES:
            return
        key = next((k for k in tr["keys"] if int(k[0]) == int(ms)), None)
        if key is None or (str(key[2]) if len(key) > 2 else "linear") == ease:
            return

        def do():
            key[2:] = [] if ease == "linear" else [ease]
        self._edit(do)

    def _on_key_edited(self, item) -> None:
        tr = self._current_track()
        if self._filling or tr is None or item.row() >= len(tr["keys"]) or item.column() > 1:
            return
        key = tr["keys"][item.row()]
        old = int(key[0])
        text = item.text().strip()
        if item.column() == 0:
            try:
                ms = max(0, int(round(float(text))))
            except ValueError:
                self._fill_keys()
                return
            self._sel = (self.tracks.currentRow(), ms)
            self._edit(lambda: move_key(self.sb(), tr, old, ms))
            return
        if text == "" and tr["property"] in INT_PROPS | FLOAT_PROPS:
            self._fill_keys()
            return

        def do():
            key[1] = coerce(tr["property"], text)
        self._sel = (self.tracks.currentRow(), old)
        self._edit(do)

    def _on_key_row(self) -> None:
        if self._filling:
            return
        tr = self._current_track()
        rows = self.keys.selectionModel().selectedRows()
        if tr is None or not rows or rows[0].row() >= len(tr["keys"]):
            return
        ms = int(tr["keys"][rows[0].row()][0])
        self._sel = (self.tracks.currentRow(), ms)
        self.seek(ms)

    def _on_key_clicked(self, row: int, ms: int) -> None:
        self._sel = (row, int(ms))
        if row != self.tracks.currentRow():
            self.tracks.setCurrentRow(row)
        self._fill_keys()
        self.seek(ms)

    def _on_key_moved(self, row: int, old: int, new: int) -> None:
        sb = self.sb()
        if sb is None or self.playing or not 0 <= row < len(sb.get("tracks", [])):
            self._refresh_ruler()
            return
        tr = sb["tracks"][row]
        self._sel = (row, int(new))
        self._edit(lambda: move_key(sb, tr, old, new))
        self.seek(new)

    def _zoom(self, factor: float) -> None:
        self.zoom = max(1.0, min(40.0, self.zoom * factor))
        vw = self.ruler_area.viewport().width()
        self.ruler.setMinimumWidth(int(vw * self.zoom) if self.zoom > 1.001 else 0)
        QTimer.singleShot(0, lambda: self.ruler_area.ensureVisible(int(self.ruler.x_of(self.ms)), 0, 60, 0))

    # ------------------------------------------------------------ time cursor / play
    def seek(self, ms) -> None:
        ms = max(0, int(ms))
        self.ms = ms
        if self.time.value() != ms:
            self.time.blockSignals(True)
            self.time.setValue(ms)
            self.time.blockSignals(False)
        if self.playing:
            import time
            self._play_t0 = time.monotonic() - ms / 1000.0
        self._refresh_ruler()
        self._preview()

    def _preview(self, ms: float | None = None) -> None:
        """Show the storyboard at the time cursor in the designer - only while recording, playing or
        scrubbing (time > 0); otherwise the designer shows the designed form (opening the panel changes
        nothing)."""
        if self.view is None:
            return
        sb = self.sb()
        live = sb is not None and (self.ms > 0 or self.playing or self.rec.isChecked())
        bp = getattr(self.view, "_blend_preview", None)
        if bp is None and not live:
            self._update_banner()
            return
        bp = self.bp
        bp.timeline_release = self._release_preview
        bp.timeline = (sb, self.ms if ms is None else ms) if live else None
        try:
            bp.refresh()
        except RuntimeError:                    # the designer was closed
            return
        self._update_banner()

    def _release_preview(self) -> None:
        """The designer starts an edit of the base design (Record off): show the designed form."""
        if self.playing or self.rec.isChecked() or self.view is None:
            return
        self.seek(0)
        set_note(self.note, "Record is off: you are changing the designed form (time cursor back to 0). "
                            "Turn on Record to add keyframes instead.")

    def _update_banner(self) -> None:
        if self.view is None:
            return
        try:
            sb = self.sb()
            name = (sb or {}).get("name", "")
            if self.playing:
                RecordBanner.of(self.view).set_mode(
                    "play", _tr("▶ Playing {} - Stop puts the controls back").format(name))
            elif self.rec.isChecked() and sb is not None:
                RecordBanner.of(self.view).set_mode(
                    "rec", _tr("● Recording {} at {} ms - moves and edits add keyframes").format(name, self.ms))
            else:
                b = RecordBanner.of(self.view, create=False)
                if b is not None:
                    b.set_mode("")
        except RuntimeError:
            pass

    def _lock_playing(self, on: bool) -> None:
        """While a storyboard plays the controls cannot be edited (designer and Properties window)."""
        if self.view is not None:
            try:
                self.view.overlay.setEnabled(not on)
            except (AttributeError, RuntimeError):
                pass
        dock = getattr(self.win, "dock_props", None)
        if dock is not None and dock.widget() is not None:
            dock.widget().setEnabled(not on)
        for w in (self.rec, self.keys, self.btn_key, self.btn_delkey, self.prop, self.value, self.btn_new,
                  self.btn_del, self.btn_ren, self.sb_combo):
            if self.view is not None and (w not in (self.btn_key, self.btn_delkey, self.btn_del, self.btn_ren)
                                          or self.sb() is not None):
                w.setEnabled(not on)
        self.btn_play.setEnabled(not on and self.sb() is not None)
        self.ruler.setEnabled(True)

    def play(self) -> None:
        sb = self.sb()
        if sb is None or self.playing or self.view is None:
            return
        dur = duration(sb)
        if dur <= 0:
            set_note(self.note, "Nothing to play yet: turn on Record, move the time cursor and move a control.")
            return
        import time
        start = self.ms if 0 <= self.ms < dur else 0
        self._play_t0 = time.monotonic() - start / 1000.0
        self.playing = True
        self._lock_playing(True)
        self.timer.start()
        self._tick()

    def _end_play(self) -> None:
        self.timer.stop()
        self.playing = False
        self._lock_playing(False)
        self._update_banner()

    def stop(self) -> None:
        was = self.playing
        self.timer.stop()
        self.playing = False
        self.ms = 0
        self.time.blockSignals(True)
        self.time.setValue(0)
        self.time.blockSignals(False)
        if self.view is not None:
            if was:
                self._lock_playing(False)
            bp = getattr(self.view, "_blend_preview", None)
            if bp is not None:
                sb = self.sb()
                bp.timeline = (sb, 0) if (sb is not None and self.rec.isChecked()) else None
                try:
                    bp.refresh()
                except RuntimeError:        # the designer was closed
                    pass
            self._update_banner()
        self._refresh_ruler()

    def _tick(self) -> None:
        """Same timing as the generated _Storyboard (Repeat / AutoReverse / hold the end)."""
        import time
        sb = self.sb()
        if sb is None or self.view is None:
            self._end_play()
            return
        dur = duration(sb)
        span = dur * (2 if sb.get("autoreverse") else 1)
        ms = (time.monotonic() - self._play_t0) * 1000.0
        done = False
        if span <= 0:
            ms, done = 0, True
        elif ms >= span:
            if sb.get("repeat"):
                self._play_t0 += (ms // span) * span / 1000.0
                ms %= span
            else:
                ms, done = span, True
        local = ms if ms <= dur else span - ms
        self.ms = int(round(local))
        self.time.blockSignals(True)
        self.time.setValue(self.ms)
        self.time.blockSignals(False)
        self._refresh_ruler()
        self._preview(local)
        if done:
            self._end_play()

    # ------------------------------------------------------------ keyframe recording
    def _snapshot(self) -> None:
        """The base (designed) values: while recording the model keeps them, the keyframes hold the rest."""
        if self.view is None:
            return
        form = self.view.doc.form
        self._shadow = {c.name: {k: c.props.get(k) for k in ANIM_PROPS if k in c.props}
                        for c in form.controls if not c.ctype.nonvisual}
        self._shadow[""] = {k: form.props.get(k) for k in FORM_ANIM_PROPS if k in form.props}

    def _on_record(self, on: bool) -> None:
        if self.view is None:
            return
        if on and self.sb() is None:            # Record needs a storyboard: make Storyboard1
            if not storyboards(self.view.doc.form):
                self.new_storyboard()
            else:
                self.sb_combo.setCurrentIndex(0)
        bp = self.bp
        if on and self.sb() is not None:
            bp.set_recording(False)             # (one recorder at a time: the States panel's is off)
            sp = getattr(self.win, "states_panel", None)
            if sp is not None and hasattr(sp, "rec") and sp.rec.isChecked():
                sp.rec.setChecked(False)
            self._snapshot()
            bp.key_recorder = self._record
        else:
            bp.key_recorder = None
            self._shadow = {}
        self._preview()

    def _record(self, ctrl) -> None:
        """A control / the form changed while recording: ONE keyframe at the time cursor for each property
        that changed on the edited (selected) controls, the model keeps the base value. Controls that
        only followed (anchored children...) go back to their base values without keyframes."""
        if self.playing or self.view is None:
            return
        sb = self.sb()
        if sb is None:
            return
        doc = self.view.doc
        if ctrl is None:
            target, props, allowed = "", doc.form.props, FORM_ANIM_PROPS
        else:
            if ctrl.ctype.nonvisual:
                return
            target, props, allowed = ctrl.name, ctrl.props, ANIM_PROPS
        base = self._shadow.get(target)
        if base is None:
            self._shadow[target] = {k: props.get(k) for k in allowed if k in props}
            return
        changed = [k for k in allowed if k in props and k in base and coerce(k, props[k]) != coerce(k, base[k])]
        if not changed:
            return
        keyed = (not doc.selection) if ctrl is None else any(c is ctrl for c in doc.selection)
        new_track, last = False, None
        for k in changed:
            if keyed:
                exists = track(sb, target, k, create=False) is not None
                if not exists and self.ms > 0:                       # starts from the designed value
                    b0 = base[k]
                    if k in ("BackColor", "ForeColor") and not b0:    # (default colour: it can fade)
                        b0 = "#f0f0f0" if k == "BackColor" else "#000000"
                    set_key(sb, target, k, 0, b0, ease="")
                if set_key(sb, target, k, self.ms, props[k]):
                    new_track |= not exists
                    last = k
            props[k] = base[k]
        if last is None:
            return
        doc.set_modified()
        if new_track:
            self._on_storyboard()
        if self.tracks.currentRow() < 0 or new_track or (self._current_track() or {}).get("target") != target:
            self._select_track(target, last, self.ms)
        else:
            row = self.tracks.currentRow()
            tr = self._current_track()
            if tr is not None and tr.get("target") == target:
                self._sel = (row, self.ms) if any(int(k[0]) == self.ms for k in tr["keys"]) else self._sel
            self._refresh_ruler()
            self._fill_keys()
        self._preview()


def install(win) -> None:
    panel = TimelinePanel(win)
    win.timeline_panel = panel
    _add_dock(win, "Objects and Timeline", panel, "dock_timeline")
    follow_designer(win, panel)
