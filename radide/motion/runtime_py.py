"""The Python animation runtime (``_RadFx``) embedded in generated python-tk / python-qt designers.

It needs, from features/states.py and features/timeline.py: ``COMMON_RT`` (``_rad_resolve`` ...),
``_Storyboard`` (``STORYBOARD_RT``) and an ``_RadIO`` (``TK_IO`` / ``QT_IO``: get / set / rgb / later /
bind / parent_bg / release, plus the ``vis_hook`` / ``quiet`` protocol for show / hide animations), and
``PRESETS_RT`` from presets.py for ``Animate()`` from code.

User code (generated designer methods)::

    self.Animate("Button1", "shake")                     # any preset, from code
    self.Animate("Label1", "slideIn", durationMs=800, from_="right")   # params as keywords
    self.BeginAnimation("fx1"); self.StopAnimation("fx1")
    self.SetVisible("Panel1", False)                     # plays its "On hide" animation, then hides

Environment: ``RADIDE_REDUCED_MOTION=1`` (or the Windows "Show animations" setting off) makes every
animation jump to its end when the form respects reduced motion (``form.extra["motion"]``)."""
from __future__ import annotations

from . import presets as P

_DEFAULTS = {p.id: (p.duration, p.easing, bool(p.restores)) for p in P.CATALOG.values()}

FX_RT = r'''

_RAD_FX_DEFAULTS = __DEFAULTS__


def _rad_reduced_motion():
    """True when the system asks for less motion (RADIDE_REDUCED_MOTION=1, or Windows animations off)."""
    import os as _os
    v = _os.environ.get("RADIDE_REDUCED_MOTION", "").strip().lower()
    if v:
        return v in ("1", "true", "yes", "on")
    if _os.name == "nt":
        try:
            import ctypes
            on = ctypes.c_int(1)
            if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0):  # CLIENTAREAANIMATION
                return not on.value
        except (AttributeError, OSError, ValueError):
            pass
    return False


class _RadQuietIO:
    """Writes of the animations themselves: their Visible changes do not start show / hide animations."""

    def __init__(self, io):
        self._io = io

    def __getattr__(self, name):
        return getattr(self._io, name)

    def set(self, name, prop, v):
        self._io.quiet = getattr(self._io, "quiet", 0) + 1
        try:
            self._io.set(name, prop, v)
        finally:
            self._io.quiet -= 1


class _RadFx:
    """Animations designed in the Animations window: triggers (load, click, hover, timer, show, hide,
    after another animation, manual), chains, reduced motion and Animate() from code."""

    def __init__(self, owner, io, storyboards, triggers, reduced=True, alpha=False, transform=False):
        self._o, self._io, self._qio = owner, io, _RadQuietIO(io)
        self.Storyboards, self._meta = {}, {}
        self.Triggers = list(triggers)
        self.ReducedMotion = bool(reduced) and _rad_reduced_motion()
        self._alpha, self._transform = bool(alpha), bool(transform)
        self._timers, self._pending, self._show, self._hide = {}, {}, {}, {}
        for d in storyboards:
            sb = _Storyboard(owner, self._qio, d["name"], d["tracks"], repeat=d.get("repeat", False),
                             autoreverse=d.get("autoreverse", False), count=d.get("count", 1))
            self._add(d["fx"], sb, d.get("delayMs", 0), d.get("restore", False), d.get("target", ""))
            try:
                setattr(owner, d["name"], sb)           # self._fx_fx1.Begin() works too
            except AttributeError:
                pass
        io.vis_hook = self._visible
        for t in self.Triggers:
            self._arm(t)

    def _add(self, fx, sb, delay, restore, target):
        self.Storyboards[fx] = sb
        self._meta[fx] = {"delay": int(delay or 0), "restore": bool(restore), "target": target or "",
                          "hiding": False}
        sb.Completed.insert(0, lambda: self._done(fx))

    # ------------------------------------------------------------ triggers
    def _arm(self, t):
        fx, on, src = t.get("fx"), t.get("on"), t.get("source") or ""
        bind = getattr(self._io, "bind", None)
        try:
            if on == "click" and bind is not None:
                bind(src, "click", lambda: self.Begin(fx))
            elif on == "hover" and bind is not None:
                bind(src, "enter", lambda: self.Begin(fx))
                leave = t.get("leave", "reverse")
                if leave == "reverse":
                    bind(src, "leave", lambda: self._reverse(fx))
                elif leave == "stop":
                    bind(src, "leave", lambda: self.Stop(fx))
            elif on == "after":
                sb = self.Storyboards.get(t.get("after"))
                if sb is not None:
                    sb.Completed.append(lambda: self.Begin(fx))
            elif on == "show":
                self._show.setdefault(t.get("target") or "", []).append(fx)
            elif on == "hide":
                self._hide.setdefault(t.get("target") or "", []).append(fx)
        except (AttributeError, KeyError):
            pass                                        # a control that is not there (any more)

    def start(self):
        """After <Form>_Load: animations "On load" begin, "On timer" ones start their timers."""
        for t in self.Triggers:
            if t.get("on") == "load":
                self.Begin(t["fx"])
            elif t.get("on") == "timer" and int(t.get("intervalMs") or 0) > 0:
                tok = object()
                self._timers[t["fx"]] = tok
                ms = int(t["intervalMs"])
                self._io.later(ms, lambda fx=t["fx"], ms=ms, tok=tok: self._every(fx, ms, tok))

    def _every(self, fx, ms, tok):
        if self._timers.get(fx) is not tok:
            return
        self.Begin(fx)
        self._io.later(ms, lambda: self._every(fx, ms, tok))

    def _visible(self, name, on):
        """_RadIO.set(name, "Visible", on) hook: True = handled here (the hide plays first)."""
        if getattr(self._io, "quiet", 0):
            return False
        fxs = [fx for fx in (self._show if on else self._hide).get(name, ()) if fx in self.Storyboards]
        if not fxs or bool(self._io.get(name, "Visible")) == bool(on):
            return False
        if on:
            self._qio.set(name, "Visible", True)
            for fx in fxs:
                self.Begin(fx)
        else:
            for fx in fxs:
                self._meta[fx]["hiding"] = True
                self.Begin(fx)
        return True

    def _done(self, fx):
        m = self._meta.get(fx)
        sb = self.Storyboards.get(fx)
        if m is None or sb is None:
            return
        if m["hiding"]:
            m["hiding"] = False
            sb.Stop()                                   # designed values back, then hidden
            self._qio.set(m["target"], "Visible", False)
        elif m["restore"]:
            sb.Stop()                                   # ended where it started: Anchor / Dock take over

    def _reverse(self, fx):
        sb = self.Storyboards.get(fx)
        if sb is None:
            return
        self._pending.pop(fx, None)
        if self.ReducedMotion:
            sb.Stop()
        else:
            sb.Reverse()

    # ------------------------------------------------------------ API
    def _find(self, fx):
        fx = str(fx or "")
        if fx in self.Storyboards:
            return fx
        return next((k for k, sb in self.Storyboards.items() if sb.Name == fx), None)

    def Begin(self, fx):
        fx = self._find(fx)
        if fx is None:
            return False
        sb = self.Storyboards[fx]
        if self.ReducedMotion:
            if not sb.IsPlaying:
                sb._saved = {}
            sb.Finish()
            return True
        if not sb.IsPlaying:
            sb._saved = {}                              # start from the values the control has now
        delay = self._meta[fx]["delay"]
        if delay > 0:
            tok = object()
            self._pending[fx] = tok
            sb.Seek(0)                                  # first frame now (e.g. slid out), then wait

            def go():
                if self._pending.get(fx) is tok:
                    del self._pending[fx]
                    sb.Begin()
            self._io.later(delay, go)
        else:
            sb.Begin()
        return True

    def Stop(self, fx):
        fx = self._find(fx)
        if fx is None:
            return False
        self._timers.pop(fx, None)
        self._pending.pop(fx, None)
        self._meta[fx]["hiding"] = False
        self.Storyboards[fx].Stop()
        return True

    def SetVisible(self, target, visible):
        target = self._name(target)
        if not self._visible(target, bool(visible)):
            self._qio.set(target, "Visible", bool(visible))

    def _name(self, target):
        if target is None or isinstance(target, str):
            return target or ""
        name = getattr(target, "_rad_name", None)
        if name:
            return name
        for k, v in vars(self._o).items():
            if v is target:
                return k
        return ""

    def Animate(self, target, preset, **opts):
        """Play *preset* on *target* now; returns its storyboard (Stop() / Pause() ...)."""
        target = self._name(target)
        dur0, ease0, restores = _RAD_FX_DEFAULTS.get(preset, (500, "out", True))
        dur = opts.pop("durationMs", opts.pop("duration", dur0))
        delay = opts.pop("delayMs", opts.pop("delay", 0))
        ease = opts.pop("easing", opts.pop("ease", ease0))
        rep = int(opts.pop("repeat", 1) or 0)
        rev = bool(opts.pop("autoreverse", False))
        params = {k.rstrip("_"): v for k, v in opts.items()}      # from_="right" -> from
        tracks, _note = _rad_fx_tracks(preset, params, dur, ease, self._alpha or not target, self._transform,
                                       not target)
        if not tracks:
            raise ValueError("unknown animation preset %r" % (preset,))
        fx = "adhoc:%s:%s" % (target, preset)
        old = self.Storyboards.get(fx)
        if old is not None and old.IsPlaying:
            old.Stop()
        sb = _Storyboard(self._o, self._qio, "_fx_adhoc", [(target, p, k) for p, k in tracks],
                         repeat=rep == 0, autoreverse=rev, count=max(1, rep))
        self._add(fx, sb, delay, restores or rev, target)
        self.Begin(fx)
        return sb
'''.replace("__DEFAULTS__", repr(_DEFAULTS))

FX_METHODS = [
    "",
    "    def Animate(self, target, preset, **opts):",
    "        \"\"\"Play an animation preset on a control (\"\" = the form): self.Animate(\"Button1\", \"shake\").\"\"\"",
    "        return self._fx.Animate(target, preset, **opts)",
    "",
    "    def BeginAnimation(self, name):",
    "        \"\"\"Start an animation of the Animations window by its id (e.g. \"fx1\").\"\"\"",
    "        return self._fx.Begin(name)",
    "",
    "    def StopAnimation(self, name):",
    "        return self._fx.Stop(name)",
    "",
    "    def SetVisible(self, control, visible):",
    "        \"\"\"Show / hide a control, playing its \"On show\" / \"On hide\" animation.\"\"\"",
    "        return self._fx.SetVisible(control, visible)",
]

METHOD_NAMES = {"Animate", "BeginAnimation", "StopAnimation", "SetVisible"}


def runtime_source(toolkit: str = "tk", with_io: bool = True) -> str:
    """Everything the FX runtime needs, for exec() outside a generated designer (vbrun / bridges)."""
    from ..features import states, timeline
    src = states.COMMON_RT + timeline.STORYBOARD_RT + P.PRESETS_RT + FX_RT
    if with_io:
        src += states.TK_IO if toolkit == "tk" else states.QT_IO
    return src


def ensure_fx(ui, toolkit: str = "tk"):
    """The form's ``_RadFx`` (created on demand for a form without designed animations, so VB
    ``Command1.Animate "shake"`` and bridge ``CALL Button1 Animate shake`` always work)."""
    fx = ui.__dict__.get("_fx")
    if fx is not None:
        return fx
    ns: dict = {"__name__": "radfx_runtime"}
    if toolkit == "tk":
        import tkinter
        from tkinter import ttk
        ns.update(tk=tkinter, ttk=ttk)
    else:                                   # PySide6 names used by QT_IO
        exec("from PySide6.QtCore import QObject, QEvent, QTimer\nfrom PySide6.QtGui import QColor\n"   # noqa: S102
             "from PySide6.QtWidgets import *", ns)
    exec(compile(runtime_source(toolkit), "<radfx-runtime>", "exec"), ns)       # noqa: S102 - our own code
    io = ui.__dict__.get("_rad")
    if io is None:
        io = ns["_RadIO"](ui)
        ui._rad = io
    fx = ns["_RadFx"](ui, io, [], [], reduced=True, alpha=toolkit != "tk")
    ui._fx = fx
    return fx
