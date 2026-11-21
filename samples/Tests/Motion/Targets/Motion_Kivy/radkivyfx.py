"""RAD IDE runtime for Kivy screens: animation presets, layout sizes, TwoPane (copied into the project by the
IDE - do not edit, it is replaced).

    self.BeginAnimation("fx1")   self.StopAnimation("fx1")   self.SetVisible("lblInfo", False)
    self.CurrentSizes            the layout sizes that apply now
"""
import os

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.factory import Factory
from kivy.graphics import PopMatrix, PushMatrix, Rotate, Scale, Translate
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout

EASE = {"": "linear", "linear": "linear", "in": "in_quad", "out": "out_quad", "inout": "in_out_quad",
        "back": "out_back", "elastic": "out_elastic", "bounce": "out_bounce", "sine": "in_out_sine"}
LOOK = ("tx", "ty", "sx", "sy", "rot", "reveal")
COLOR_ATTRS = ("background_color", "card_color", "bar_color", "fab_color")


class RadLook(EventDispatcher):
    """Offset (dp, y down), scale, rotation (degrees clockwise) and typewriter share of one widget."""
    tx = NumericProperty(0)
    ty = NumericProperty(0)
    sx = NumericProperty(1)
    sy = NumericProperty(1)
    rot = NumericProperty(0)
    reveal = NumericProperty(1)


def look_of(widget):
    lk = getattr(widget, "_rad_look", None)
    if lk is not None:
        return lk
    lk = RadLook()
    widget._rad_look = lk
    t, r, s = Translate(0, 0), Rotate(angle=0, origin=widget.center), Scale(1, 1, 1, origin=widget.center)
    for inst in (s, r, t, PushMatrix()):          # first in canvas.before: the background moves too
        widget.canvas.before.insert(0, inst)
    widget.canvas.after.add(PopMatrix())

    def upd(*_):
        t.x, t.y = dp(lk.tx), -dp(lk.ty)
        r.origin = s.origin = widget.center
        r.angle = -lk.rot
        s.x, s.y = lk.sx, lk.sy
    lk.bind(tx=upd, ty=upd, rot=upd, sx=upd, sy=upd)
    widget.bind(pos=upd, size=upd)
    return lk


def reduced_motion():
    """RADIDE_REDUCED_MOTION=1 / 0, else on Windows the "Show animations in Windows" setting
    (SPI_GETCLIENTAREAANIMATION, read only)."""
    v = os.environ.get("RADIDE_REDUCED_MOTION", "").strip().lower()
    if v:
        return v in ("1", "true", "yes", "on")
    if os.name == "nt":
        try:
            import ctypes
            on = ctypes.c_int(1)
            if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0):
                return not on.value
        except (AttributeError, OSError, ValueError):
            pass
    return False


class RadFx:
    """Plays the storyboards of a screen (sb = {"id", "target", "duration", "channels", "count", "forever",
    "autoreverse", "delay", "chain", "trigger", "source", "interval", "leave", "parent"})."""

    def __init__(self, screen, sbs, respect=True):
        self.screen = screen
        self.sbs = {s["id"]: s for s in sbs}
        self.order = [s["id"] for s in sbs]
        self.respect = respect
        self.runs = {}
        self.events = []
        self.started = False
        self._hover = set()
        self.last = {}

    # -------------------------------------------------------------- helpers
    def widget(self, name):
        return self.screen if not name else getattr(self.screen, name, None)

    def _color_attr(self, w, ch):
        if ch == "fg":
            return "color" if hasattr(w, "color") else None
        return next((a for a in COLOR_ATTRS if hasattr(w, a)), None)

    def _obj_prop(self, w, ch):
        if ch in LOOK:
            return look_of(w), ch
        if ch == "opacity":
            return w, "opacity"
        if ch in ("bg", "fg"):
            a = self._color_attr(w, ch)
            return (w, a) if a else (None, None)
        return None, None

    def _value(self, sb, run, ch, v):
        if ch in ("bg", "fg"):
            if v == "start":
                return list(run["start"].get(ch) or [1, 1, 1, 1])
            if v == "parent":
                return list(sb.get("parent") or [1, 1, 1, 1])
            return list(v)
        return v

    # -------------------------------------------------------------- start / triggers
    def start(self):
        if self.started:
            return
        self.started = True
        for fid in self.order:
            sb = self.sbs[fid]
            on = sb.get("trigger", "load")
            if on == "load":
                self.begin(fid)
            elif on == "timer" and sb.get("interval", 0) > 0:
                self.events.append(Clock.schedule_interval(lambda dt, f=fid: self.begin(f), sb["interval"] / 1000.0))
            elif on == "click":
                w = self.widget(sb.get("source") or sb["target"])
                if w is not None:
                    w.fbind("on_touch_up", self._touch_up, fid)
            elif on == "hover":
                Window.bind(mouse_pos=self._mouse)

    def _touch_up(self, fid, w, touch):
        if w.collide_point(*touch.pos) and not w.disabled:
            self.begin(fid)
        return False

    def _mouse(self, win, pos):
        for fid in self.order:
            sb = self.sbs[fid]
            if sb.get("trigger") != "hover":
                continue
            w = self.widget(sb.get("source") or sb["target"])
            if w is None or w.get_root_window() is None:
                continue
            inside = w.collide_point(*w.to_widget(*pos))
            if inside and fid not in self._hover:
                self._hover.add(fid)
                self.begin(fid)
            elif not inside and fid in self._hover:
                self._hover.discard(fid)
                self.leave(fid, sb.get("leave", "reverse"))

    # -------------------------------------------------------------- playing
    def begin(self, fid, hide_after=False, _again=0):
        sb = self.sbs.get(fid)
        w = self.widget(sb["target"]) if sb else None
        if sb is None or w is None:
            return
        old = self.runs.pop(fid, None)
        if old is not None:
            self._cancel(old)
        run = {"sb": sb, "anims": [], "events": [], "hide": hide_after, "left": _again or sb.get("count", 1),
               "start": old["start"] if old else {"bg": self._get(w, "bg"), "fg": self._get(w, "fg"),
                                                   "text": getattr(w, "text", "")},
               "t0": Clock.get_time()}
        self.runs[fid] = run
        if self.respect and reduced_motion():
            self._jump(sb, run, w, end=True)
            self._finish(fid, run)
            return
        delay = sb.get("delay", 0) / 1000.0
        if delay > 0 and not _again:
            run["events"].append(Clock.schedule_once(lambda dt: self._play(fid, run, w), delay))
        else:
            self._play(fid, run, w)

    def _get(self, w, ch):
        a = self._color_attr(w, ch)
        return list(getattr(w, a)) if a else None

    def _jump(self, sb, run, w, end):
        for ch, keys in sb["channels"].items():
            k = keys[-1] if end and not sb.get("autoreverse") else keys[0]
            self._set(sb, run, w, ch, k[1])

    def _set(self, sb, run, w, ch, v):
        if ch == "visible":
            w.visible = bool(v)
            return
        if ch == "reveal":
            txt = run["start"]["text"]
            w.text = txt[:int(round(len(txt) * max(0.0, min(1.0, v))))]
            return
        obj, prop = self._obj_prop(w, ch)
        if obj is not None:
            setattr(obj, prop, self._value(sb, run, ch, v))

    def _play(self, fid, run, w):
        sb = run["sb"]
        dur = max(1, sb["duration"]) / 1000.0
        run["t0"] = Clock.get_time()
        pending = []
        if "visible" in sb["channels"]:
            for ms, v, _e in sb["channels"]["visible"]:
                if ms <= 0:
                    self._set(sb, run, w, "visible", v)
                else:
                    run["events"].append(Clock.schedule_once(lambda dt, v=v: self._set(sb, run, w, "visible", v),
                                                             ms / 1000.0))
        lk = None
        for ch, keys in sb["channels"].items():
            if ch == "visible":
                continue
            if ch == "reveal":
                lk = look_of(w)
                txt = run["start"]["text"]
                run["reveal"] = lk.fbind("reveal", lambda inst, v, t=txt: setattr(
                    w, "text", t[:int(round(len(t) * max(0.0, min(1.0, v))))]))
            obj, prop = (look_of(w), "reveal") if ch == "reveal" else self._obj_prop(w, ch)
            if obj is None:
                continue
            setattr(obj, prop, self._value(sb, run, ch, keys[0][1]))
            seq, prev = None, 0
            pts = list(keys)
            if sb.get("autoreverse"):
                pts += [[2 * keys[-1][0] - k[0], k[1], keys[i + 1][2] or ""] for i, k in
                        reversed(list(enumerate(keys[:-1])))]
            for ms, v, e in pts[1:]:
                a = Animation(**{prop: self._value(sb, run, ch, v)}, d=max(0.0001, (ms - prev) / 1000.0),
                              t=EASE.get(e, "linear"))
                seq = a if seq is None else seq + a
                prev = ms
            total = dur * (2 if sb.get("autoreverse") else 1)
            if prev / 1000.0 < total:
                pad = Animation(d=total - prev / 1000.0)
                seq = pad if seq is None else seq + pad
            if seq is not None:
                pending.append((seq, obj))
        if not pending:
            total = dur * (2 if sb.get("autoreverse") else 1)
            run["events"].append(Clock.schedule_once(lambda dt: self._done(fid, run, w), total))
            return
        left = [len(pending)]

        def one_done(*_):
            left[0] -= 1
            if left[0] == 0 and self.runs.get(fid) is run:
                self._done(fid, run, w)
        for seq, obj in pending:
            seq.bind(on_complete=one_done)
            run["anims"].append((seq, obj))
            seq.start(obj)

    def _done(self, fid, run, w):
        sb = run["sb"]
        if sb.get("forever") or run["left"] > 1:
            run["left"] = 0 if sb.get("forever") else run["left"] - 1
            self._unbind(run)
            run["anims"], run["events"] = [], []
            self._play(fid, run, w)
            return
        self._finish(fid, run)

    def _finish(self, fid, run):
        self.runs.pop(fid, None)
        if run["sb"].get("trigger") == "hover":
            self.last[fid] = run
        self._unbind(run)
        w = self.widget(run["sb"]["target"])
        if "reveal" in run["sb"]["channels"] and w is not None:
            w.text = run["start"]["text"]
        if run["hide"] and w is not None:
            w.visible = False
        for nxt in run["sb"].get("chain", []):
            self.begin(nxt)

    def _unbind(self, run):
        if run.get("reveal"):
            w = self.widget(run["sb"]["target"])
            if w is not None:
                look_of(w).unbind_uid("reveal", run["reveal"])
            run["reveal"] = None

    def _cancel(self, run):
        for seq, obj in run["anims"]:
            seq.cancel(obj)
        for ev in run["events"]:
            ev.cancel()
        self._unbind(run)

    def stop(self, fid):
        run = self.runs.pop(fid, None)
        if run is not None:
            self._cancel(run)

    def leave(self, fid, mode):
        """Hover left: "reverse" goes back to the start look, "stop" stops, "none" lets it finish."""
        run = self.runs.get(fid) or self.last.pop(fid, None)
        if run is None or mode == "none":
            return
        if mode == "stop":
            self.stop(fid)
            return
        w = self.widget(run["sb"]["target"])
        self.runs.pop(fid, None)
        self._cancel(run)
        back = max(0.05, min(Clock.get_time() - run["t0"], run["sb"]["duration"] / 1000.0))
        for ch, keys in run["sb"]["channels"].items():
            obj, prop = self._obj_prop(w, ch)
            if obj is not None and ch != "reveal":
                Animation(**{prop: self._value(run["sb"], run, ch, keys[0][1])}, d=back).start(obj)

    def set_visible(self, name, on):
        w = self.widget(name)
        if w is None:
            return
        show = [f for f in self.order if self.sbs[f]["target"] == name and self.sbs[f].get("trigger") == "show"]
        hide = [f for f in self.order if self.sbs[f]["target"] == name and self.sbs[f].get("trigger") == "hide"]
        if on:
            w.visible = True
            for f in show:
                self.begin(f)
        elif not hide:
            w.visible = False
        else:
            for i, f in enumerate(hide):
                self.begin(f, hide_after=i == len(hide) - 1)

    def close(self):
        for ev in self.events:
            ev.cancel()
        for fid in list(self.runs):
            self.stop(fid)
        Window.unbind(mouse_pos=self._mouse)


# ------------------------------------------------------------------ layout sizes
def rad_env():
    """(posture, span, fold) from RADIDE_POSTURE / RADIDE_SPAN / RADIDE_HINGE."""
    posture = _rad_vposture(os.environ.get("RADIDE_POSTURE", "")) or "flat"
    span = "dual" if os.environ.get("RADIDE_SPAN", "").strip().lower() in ("dual", "2", "spanned") else "single"
    if posture == "half-opened":
        span = "dual"
    fold = None
    hinge = rad_hinge()
    if hinge:
        fold = "vertical" if hinge[3] >= hinge[2] else "horizontal"
    return posture, span, fold


def rad_hinge():
    try:
        parts = [float(v) for v in os.environ.get("RADIDE_HINGE", "").split(",") if v.strip()]
    except ValueError:
        return None
    return parts if len(parts) == 4 else None


def rad_sizes(sizes, w, h):
    """Ids of the layout sizes of a w x h (dp) screen, in list order (later ones win, like CSS)."""
    posture, span, fold = rad_env()
    return _rad_vmatching(sizes, w, h, None, posture, span, fold)


# ------------------------------------------------------------------ TwoPane
class RadTwoPane(FloatLayout):
    """Two panes (its first two children): side by side / stacked, split at the hinge (RADIDE_HINGE, window
    coordinates in dp) when it crosses the box, else at ratio; Auto shows one pane below 600 dp."""
    pane_mode = StringProperty("Auto")
    ratio = NumericProperty(0.5)
    single_pane = StringProperty("Start")
    hinge_aware = BooleanProperty(True)

    def do_layout(self, *a):
        panes = list(reversed(self.children))[:2]
        if not panes:
            return
        w, h = self.width / dp(1), self.height / dp(1)
        rects = self.split(w, h)
        for i, p in enumerate(panes):
            r = rects[i] if i < len(rects) else None
            p.size_hint = (None, None)
            if r is None:
                p.opacity, p.disabled = 0, True
                p.pos = (self.right + dp(8), self.y)
                continue
            x, y, pw, ph = r
            p.opacity, p.disabled = 1, False
            p.size = (dp(pw), dp(ph))
            p.pos = (self.x + dp(x), self.top - dp(y) - dp(ph))

    def split(self, w, h):
        mode = (self.pane_mode or "Auto").capitalize()
        r = min(0.95, max(0.05, float(self.ratio or 0.5)))
        hinge = rad_hinge() if self.hinge_aware else None
        if hinge:
            wx, wy = self.to_window(self.x, self.top)
            hx, hy = hinge[0] - wx / dp(1), hinge[1] - (Window.height - wy) / dp(1)
            hw, hh = hinge[2], hinge[3]
            if hw <= hh and 0 < hx < w - hw and mode in ("Auto", "Horizontal"):
                return [(0, 0, hx, h), (hx + hw, 0, w - hx - hw, h)]
            if hw > hh and 0 < hy < h - hh and mode in ("Auto", "Vertical"):
                return [(0, 0, w, hy), (0, hy + hh, w, h - hy - hh)]
        if mode == "Auto":
            if w < 600:
                return [(0, 0, w, h), None] if self.single_pane != "End" else [None, (0, 0, w, h)]
            mode = "Horizontal"
        if mode == "Vertical":
            a = int(h * r + 0.5)
            return [(0, 0, w, a), (0, a, w, h - a)]
        a = int(w * r + 0.5)
        return [(0, 0, a, h), (a, 0, w - a, h)]


Factory.register("RadTwoPane", cls=RadTwoPane)

# ------------------------------------------------------------------ size matching (radide/variants)

def _rad_vposture(v):
    """Any posture spelling -> flat | half-opened | folded ("" = unknown)."""
    s = str(v or "").strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    if s in ("halfopened", "halfopen", "half", "tabletop", "book"):
        return "half-opened"
    if s in ("folded", "closed", "fold", "cover"):
        return "folded"
    if s in ("flat", "open", "opened"):
        return "flat"
    return ""


def _rad_vmatch(when, w, h, orientation=None, posture=None, span=None, fold=None):
    """True when every condition of a layout size's "when" holds for a client area of w x h."""
    if not isinstance(when, dict):
        return False
    for k, v in when.items():
        if v is None or v == "":
            continue
        if k in ("minWidth", "maxWidth", "minHeight", "maxHeight"):
            try:
                lim = float(v)
            except (TypeError, ValueError):
                return False
            val = w if k.endswith("Width") else h
            if (val < lim) if k.startswith("min") else (val > lim):
                return False
        elif k == "orientation":
            if str(v).strip().lower()[:4] != (orientation or ("landscape" if w > h else "portrait"))[:4]:
                return False
        elif k == "posture":
            if _rad_vposture(v) != _rad_vposture(posture):
                return False
        elif k == "span":
            if str(v).strip().lower() != (span or "single"):
                return False
        elif k == "fold":
            if str(v).strip().lower() != str(fold or "").lower():
                return False
    return True


def _rad_vmatching(sizes, w, h, orientation=None, posture=None, span=None, fold=None):
    """Ids of the sizes that apply, in list order (later ones win, like CSS)."""
    return [s["id"] for s in sizes if _rad_vmatch(s.get("when"), w, h, orientation, posture, span, fold)]
