"""Animations, layout sizes and TwoPane of Kivy screens (plan MOTION_VARIANTS_FOLDABLES, slice D).

``FX_RUNTIME`` is copied into the project as ``radkivyfx.py`` when a form needs it (radkivy.py stays the same):

* ``RadFx`` plays the form's storyboards with ``kivy.animation.Animation`` sequences (one per channel, run in
  parallel); offsets / rotation / scale are canvas instructions (PushMatrix, Translate, Rotate, Scale,
  PopMatrix) around the widget, opacity is the widget's own, colours animate ``color`` /
  ``background_color`` / ``card_color``, typewriter reveals the text.  Triggers: load, click (touch up on
  the source), hover (``Window.mouse_pos``), timer, after, show / hide (``SetVisible``), manual.
  RADIDE_REDUCED_MOTION=1 shows the end at once (Kivy has no system setting for it).
* layout sizes: the screen's ``radsizes`` list (matching ids, MATCH_RT of radide/variants) is recomputed on
  every resize; positions of the KV rule use it (``x: ... if 'compact' in root.radsizes else ...``), the
  other properties are set from Python.  Posture / span / fold come from RADIDE_POSTURE / RADIDE_SPAN /
  RADIDE_HINGE (Kivy has no foldable API).
* ``RadTwoPane`` (FloatLayout): its first two children are the panes, split at RADIDE_HINGE when it crosses
  the pane, else at Ratio (Auto: one pane below 600 dp).
"""
from __future__ import annotations

from ..fxtargets import channels, fx_plan, trigger_of, two_panes, variant_plan
from .codegen_common import color_hex, font_px, truthy

FX_FILE = "radkivyfx.py"

FX_RUNTIME = r'''"""RAD IDE runtime for Kivy screens: animation presets, layout sizes, TwoPane (copied into the project by the
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
    return os.environ.get("RADIDE_REDUCED_MOTION", "") == "1"


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
'''


def _runtime() -> str:
    from ..variants.model import MATCH_RT
    return FX_RUNTIME + "\n# ------------------------------------------------------------------ size matching (radide/variants)" \
        + MATCH_RT


def kv_rgba(value) -> list | None:
    h = color_hex(value)
    if not h:
        return None
    a, r, g, b = (round(int(h[i:i + 2], 16) / 255, 3) for i in (0, 2, 4, 6))
    return [r, g, b, a]


def _r(v) -> str:
    v = round(float(v), 3)
    return str(int(v)) if v.is_integer() else str(v)


def _lin(base, rel, dim: str) -> str:
    out = f"dp({_r(base)})"
    if rel:
        out += f" + {_r(rel)} * {dim}"
    return out


class KivyFx:
    def __init__(self, form):
        self.form = form
        self.plan = fx_plan(form, "kivy")
        self.vplan = variant_plan(form)
        self.panes = {tp["name"]: tp for tp in two_panes(form)}

    @property
    def active(self) -> bool:
        return bool(self.plan or self.vplan or self.panes)

    # ------------------------------------------------------------ KV
    def geometry(self, name: str, box: str, base_spec) -> dict | None:
        """{"size": ..., "x": ..., "top": ...} KV expressions that follow the layout sizes, or None."""
        if not self.vplan:
            return None
        alts = []
        for s in self.vplan["sizes"]:
            ov = (self.vplan["controls"].get(s["id"]) or {}).get(name)
            if ov and ov.get("place") is not None:
                alts.append((s["id"], ov["place"]))
        if not alts:
            return None

        def expr(f):
            out = f(base_spec)
            for vid, spec in alts:
                out = f"({f(spec)} if {vid!r} in root.radsizes else {out})"
            return out
        w = expr(lambda p: _lin(p[2], p[6], f"{box}.width"))
        h = expr(lambda p: _lin(p[3], p[7], f"{box}.height"))
        return {"size": f"{w}, {h}", "x": f"{box}.x + " + expr(lambda p: _lin(p[0], p[4], f"{box}.width")),
                "top": f"{box}.top - " + expr(lambda p: f"({_lin(p[1], p[5], f'{box}.height')})")}

    def two_pane_lines(self, gen, c, ind: str) -> list[str]:
        tp = self.panes.get(c.name) or {"mode": "Auto", "ratio": 0.5, "single": "Start", "hinge_aware": True}
        i2 = ind + "    "
        L = [f"{ind}RadTwoPane:", f"{i2}pane_mode: {tp['mode']!r}", f"{i2}ratio: {tp['ratio']}",
             f"{i2}single_pane: {tp['single']!r}", f"{i2}hinge_aware: {tp['hinge_aware']}"]
        L += gen.bg(c, i2)
        from .codegen_common import form_children
        tail: list[str] = []
        for k in form_children(self.form, c.name)[:2]:
            tail += gen.widget(k, i2)
        # KV wants the properties of a widget before its children: place_children() adds the TwoPane's
        # size / position first, then take_tail() gives the panes
        self._tail = getattr(self, "_tail", {})
        self._tail[c.name] = tail
        return L

    def take_tail(self, name: str) -> list[str]:
        return (getattr(self, "_tail", {}) or {}).pop(name, [])

    # ------------------------------------------------------------ Python class
    def imports(self) -> list[str]:
        if not self.active:
            return []
        return ["from kivy.properties import ListProperty  # noqa: F401",
                "from radkivyfx import RadFx, RadTwoPane, rad_sizes  # noqa: F401"]

    def class_lines(self) -> list[str]:
        L: list[str] = []
        if self.vplan:
            L.append("    radsizes = ListProperty([])")
            L.append(f"    _rad_sizes = {[{'id': s['id'], 'when': s['when']} for s in self.vplan['sizes']]!r}")
        if self.plan:
            L.append("    _rad_sbs = [")
            for sb in self.plan["storyboards"]:
                L.append(f"        {self._sb(sb)!r},")
            L.append("    ]")
        return L

    def _sb(self, sb) -> dict:
        base = self.form.props if not sb["target"] else self.form.find(sb["target"]).props
        ch = channels(sb, base)
        for k in ("bg", "fg"):
            if k in ch:
                ch[k] = [[ms, v if v in ("start", "parent") else (kv_rgba(v) or [1, 1, 1, 1]), e] for ms, v, e in ch[k]]
        t = trigger_of(self.plan, sb["fx"])
        d = {"id": sb["fx"], "target": sb["target"], "duration": int(sb["duration"]), "channels": ch,
             "count": int(sb["count"]), "forever": bool(sb["repeat"]), "autoreverse": bool(sb["autoreverse"]),
             "delay": int(sb.get("delayMs", 0)), "chain": list(sb["chain"]), "trigger": t["on"],
             "source": t.get("source") or "", "interval": int(t.get("intervalMs") or 0),
             "leave": t.get("leave", "reverse")}
        if "bg" in ch or "fg" in ch:
            d["parent"] = kv_rgba(self._parent_color(sb["target"])) or [1, 1, 1, 1]
        return d

    def _parent_color(self, name):
        c = self.form.find(name) if name else None
        p = self.form.find(c.parent) if c is not None and c.parent else None
        while p is not None:
            if p.props.get("BackColor"):
                return p.props["BackColor"]
            p = self.form.find(p.parent) if p.parent else None
        return self.form.props.get("BackColor") or "#ffffff"

    def init_lines(self) -> list[str]:
        L = []
        if self.plan:
            respect = bool(self.plan.get("reduced_motion", True))
            L.append(f"        self._radfx = RadFx(self, self._rad_sbs, respect={respect})")
        if self.vplan:
            L += ["        self._rad_props = {}", "        self.bind(size=self._rad_resize)"]
        return L

    def method_lines(self) -> list[str]:
        L: list[str] = []
        if self.plan:
            L += ["", "    def on_enter(self, *a):", "        super().on_enter(*a)", "        self._radfx.start()",
                  "", "    def on_leave(self, *a):", "        super().on_leave(*a)", "        self._radfx.close()",
                  "        self._radfx.started = False",
                  "", "    def BeginAnimation(self, fx_id):", "        self._radfx.begin(fx_id)",
                  "", "    def StopAnimation(self, fx_id):", "        self._radfx.stop(fx_id)",
                  "", "    def SetVisible(self, name, on):",
                  "        \"\"\"Visible with the On show / On hide animations of the control.\"\"\"",
                  "        self._radfx.set_visible(name, on)"]
        if self.vplan:
            L += ["", "    @property", "    def CurrentSizes(self):", "        return list(self.radsizes)",
                  "", "    def _rad_resize(self, *a):",
                  "        from kivy.metrics import dp",
                  "        active = rad_sizes(self._rad_sizes, self.width / dp(1), self.height / dp(1))",
                  "        if active == list(self.radsizes):",
                  "            return",
                  "        self.radsizes = active"]
            L += self._props_lines()
        return L

    def _props_lines(self) -> list[str]:
        """Text / Visible / colours / font size of the sizes (base value restored when none applies)."""
        from ..variants.model import RUNTIME_PROPS
        per: dict[str, dict[str, list]] = {}
        for vid, ctl in (self.vplan.get("controls") or {}).items():
            for name, ov in ctl.items():
                for k, v in (ov.get("props") or {}).items():
                    if k in RUNTIME_PROPS:
                        per.setdefault(name, {}).setdefault(k, []).append((vid, v))
        L = []
        for name, props in per.items():
            c = self.form.find(name)
            if c is None:
                continue
            for k, alts in props.items():
                if k == "Text":
                    attr, conv = "text", str
                elif k == "Visible":
                    attr, conv = "visible", truthy
                elif k == "ForeColor":
                    attr, conv = "color", kv_rgba
                elif k == "BackColor":
                    attr = "background_color" if c.type == "Button" else ("card_color" if c.type == "Card" else "")
                    conv = kv_rgba
                elif k == "FontSize":
                    attr = "font_size"
                    conv = lambda v: f"sp({_r(font_px({'FontSize': v}) or v)})"       # noqa: E731
                elif k == "FontBold":
                    attr, conv = "bold", truthy
                else:
                    continue
                if not attr:
                    continue
                L.append(f"        v = self._rad_props.setdefault({name + '.' + attr!r}, "
                         f"getattr(self.{name}, {attr!r}, None))")
                for vid, val in alts:
                    vv = conv(val)
                    lit = vv if isinstance(vv, str) and vv.startswith("sp(") else repr(vv)
                    if lit.startswith("sp("):
                        L.append(f"        if {vid!r} in active:")
                        L.append("            from kivy.metrics import sp")
                        L.append(f"            v = {lit}")
                    else:
                        L.append(f"        v = {lit} if {vid!r} in active else v")
                if attr in ("background_color", "card_color", "color"):
                    L.append("        if v is not None:")
                    L.append(f"            setattr(self.{name}, {attr!r}, v)")
                else:
                    L.append(f"        setattr(self.{name}, {attr!r}, v)")
        return L


def runtime_source() -> str:
    return _runtime()


__all__ = ["FX_FILE", "KivyFx", "runtime_source"]
