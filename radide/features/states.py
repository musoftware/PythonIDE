"""Expression Blend for the form designer (CONTRACTS 8.7) - Visual States.

* Model: every control may carry ``"states": {"MouseOver": {"BackColor": "#..."}, ...}`` in the .form
  (built-in states MouseOver / Pressed / Focused / Disabled, plus the form's custom states); the form keeps
  its custom states in ``form.extra["states"] = {"Expanded": {<form property overrides>}}``.
* Code generation (python-tk and python-qt): :func:`python_blend` returns the runtime classes and the lines
  the plugins insert into the generated designer class (automatic MouseOver/Pressed/Focused/Disabled
  switching, ``GoToState(name)``, storyboards from timeline.py and data bindings from databinding.py).
* IDE: a "States" dock (like Blend's States panel). Selecting a state previews it on the design surface;
  "Record" turns property edits into overrides of that state.
"""
from __future__ import annotations

import json

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDockWidget,
                             QGraphicsOpacityEffect, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                             QListWidget, QListWidgetItem, QMessageBox, QTableWidget,
                             QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

AUTO_STATES = ("MouseOver", "Pressed", "Focused", "Disabled")
BASE = "Base"
# properties a state may override (controls) / the form may override
STATE_PROPS = ("Text", "BackColor", "ForeColor", "Left", "Top", "Width", "Height", "Visible",
               "FontSize", "FontBold", "FontItalic", "Opacity")
FORM_STATE_PROPS = ("Text", "BackColor", "Width", "Height", "Opacity")
INT_PROPS = {"Left", "Top", "Width", "Height", "FontSize", "Value"}
BOOL_PROPS = {"Visible", "FontBold", "FontItalic", "Checked"}
COLOR_PROPS = {"BackColor", "ForeColor"}
FLOAT_PROPS = {"Opacity"}
PYTHON_PLUGINS = ("python-tk", "python-qt")
# names a storyboard / data source cannot take (attributes of the generated form classes)
RESERVED_NAMES = {"root", "show", "hide", "close", "destroy", "after", "title", "update", "resize", "move",
                  "Refresh", "RefreshBindings", "GoToState", "setWindowTitle", "x", "y", "width", "height",
                  "Animate", "BeginAnimation", "StopAnimation", "SetVisible"}


# ====================================================================== model helpers
def coerce(prop: str, value):
    """Normalise a property value typed by the user (or read from JSON)."""
    if prop in INT_PROPS:
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return 0
    if prop in FLOAT_PROPS:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 1.0
    if prop in BOOL_PROPS:
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    return "" if value is None else str(value) if not isinstance(value, str) else value


def form_states(form) -> dict:
    """Custom states of the form: {state: {form property: value}} (stored in form.extra["states"])."""
    st = form.extra.get("states")
    if not isinstance(st, dict):
        st = {}
        form.extra["states"] = st
    return st


def custom_state_names(form) -> list[str]:
    names = list(form_states(form))
    for c in form.controls:
        for s in c.states:
            if s not in AUTO_STATES and s not in names:
                names.append(s)
    return names


def overrides(form, ctrl, state: str) -> dict:
    """Overrides of *state* for ctrl (None = the form)."""
    if not state or state == BASE:
        return {}
    if ctrl is None:
        return dict(form_states(form).get(state) or {})
    return dict(ctrl.states.get(state) or {})


def set_override(form, ctrl, state: str, prop: str, value) -> None:
    if ctrl is None:
        form_states(form).setdefault(state, {})[prop] = coerce(prop, value)
    else:
        ctrl.states.setdefault(state, {})[prop] = coerce(prop, value)


def remove_override(form, ctrl, state: str, prop: str) -> None:
    d = form_states(form).get(state) if ctrl is None else ctrl.states.get(state)
    if d is not None:
        d.pop(prop, None)
        if ctrl is not None and not d:
            ctrl.states.pop(state, None)


def rename_references(form, old: str, new: str) -> None:
    """A control was renamed: update storyboards and bindings (states live in the control itself)."""
    for sb in form.extra.get("storyboards") or []:
        for tr in sb.get("tracks", []):
            if tr.get("target") == old:
                tr["target"] = new
    for b in form.extra.get("bindings") or []:
        if b.get("control") == old:
            b["control"] = new
    from ..motion.model import rename_references as motion_rename      # Animations window (motion)
    motion_rename(form, old, new)


def uses_blend(form) -> bool:
    return bool(any(c.states for c in form.controls) or form.extra.get("states")
                or form.extra.get("storyboards") or form.extra.get("bindings") or form.extra.get("datasources")
                or form.extra.get("animations"))


# ====================================================================== generated runtime
COMMON_RT = r'''

# ------------------------------------------------------------------ Expression Blend runtime
import csv as _csv  # noqa: E402
import json as _json  # noqa: E402
import math as _math  # noqa: E402
import time as _time  # noqa: E402

_RAD_COLOR_PROPS = ("BackColor", "ForeColor")
_RAD_INT_PROPS = ("Left", "Top", "Width", "Height", "FontSize", "Value")


def _rad_rgb_hex(value):
    """'#rgb' / '#rrggbb' -> (r, g, b) or None."""
    s = str(value or "").strip()
    if not s.startswith("#"):
        return None
    s = s[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) if len(s) >= 6 else None
    except ValueError:
        return None


def _rad_ease(f, ease):
    if ease == "in":
        return f * f
    if ease == "out":
        return 1 - (1 - f) * (1 - f)
    if ease == "inout":
        return 2 * f * f if f < 0.5 else 1 - 2 * (1 - f) * (1 - f)
    if ease == "sine":
        return -(_math.cos(_math.pi * f) - 1) / 2
    if ease == "back":                              # overshoots a little, then settles
        return 1 + 2.70158 * (f - 1) ** 3 + 1.70158 * (f - 1) ** 2
    if ease == "elastic":
        if f <= 0 or f >= 1:
            return 1.0 if f >= 1 else 0.0
        return 2 ** (-10 * f) * _math.sin((f * 10 - 0.75) * (2 * _math.pi / 3)) + 1
    if ease == "bounce":
        n, d = 7.5625, 2.75
        if f < 1 / d:
            return n * f * f
        if f < 2 / d:
            f -= 1.5 / d
            return n * f * f + 0.75
        if f < 2.5 / d:
            f -= 2.25 / d
            return n * f * f + 0.9375
        f -= 2.625 / d
        return n * f * f + 0.984375
    return f


class _RadText(str):
    """Text being typed (typewriter keyframes): mixes by the length of the common prefix."""


def _rad_mix(prop, a, b, f, rgb):
    """Value of property *prop* between a (f = 0) and b (f = 1); rgb(colour) -> (r, g, b).
    Numbers follow f beyond 1 (back / elastic easings overshoot); colours and text stop at b."""
    if f <= 0:
        return a
    if prop in _RAD_COLOR_PROPS:
        if f >= 1:
            return b
        ca, cb = rgb(a), rgb(b)
        if ca is None or cb is None:
            return a
        return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(x + (y - x) * f)))) for x, y in zip(ca, cb))
    if isinstance(a, bool) or isinstance(b, bool):
        return b if f >= 1 else a
    if isinstance(a, _RadText) or isinstance(b, _RadText):
        sa, sb = str(a or ""), str(b or "")
        if sa.startswith(sb) or sb.startswith(sa):
            longer = sa if len(sa) > len(sb) else sb
            n = len(sa) + (len(sb) - len(sa)) * min(f, 1.0)
            return _RadText(longer[:max(0, int(round(n)))])
        return b if f >= 1 else a
    try:
        x, y = float(a), float(b)
    except (TypeError, ValueError):
        return b if f >= 1 else a                  # Text...: discrete keyframes
    v = x + (y - x) * f
    return int(round(v)) if prop in _RAD_INT_PROPS else v


def _rad_resolve(prop, v, start, ref=None):
    """A keyframe value made absolute against *start* (the value when the animation starts):
    {"d": n} start + n, {"m": k} start * k, {"of": "Width", "f": x} start + x * start Width,
    {"reveal": 0..1} the start text up to that fraction, "$parent" the parent's background colour;
    ref(prop) = start value of another property of the same control (ref("$parent") = parent colour)."""
    if isinstance(v, str) and v == "$parent":
        c = ref("$parent") if ref is not None else None
        return c if c else start
    if not isinstance(v, dict):
        return v
    if "reveal" in v:
        s = "" if start is None else str(start)
        try:
            f = max(0.0, min(1.0, float(v["reveal"])))
        except (TypeError, ValueError):
            f = 1.0
        return _RadText(s[:int(round(len(s) * f))])
    if isinstance(start, bool) or start is None:
        return start
    try:
        x = float(start)
    except (TypeError, ValueError):
        return start                               # colours / text: relative keys keep the start value
    try:
        val = x * float(v.get("m", 1)) + float(v.get("d", 0))
        if v.get("of"):
            other = ref(str(v["of"])) if ref is not None else None
            val += float(v.get("f", 0)) * float(other if other is not None else 0)
    except (TypeError, ValueError):
        return start
    if prop in _RAD_INT_PROPS:
        return int(round(val))
    return max(0.0, min(1.0, val)) if prop == "Opacity" else val


def _rad_resolve_keys(prop, keys, start, ref=None):
    """Keyframes [(ms, value, ease)] with relative values made absolute (see _rad_resolve)."""
    return [(k[0], _rad_resolve(prop, k[1], start, ref)) + tuple(k[2:]) for k in keys]


def _rad_has_relative(keys):
    return any(isinstance(k[1], dict) or (isinstance(k[1], str) and k[1] == "$parent") for k in keys)


def _rad_value_at(prop, keys, t, start, rgb):
    """keys = [(ms, value, ease), ...] sorted by time; start = value before the first key."""
    if not keys:
        return start
    pts = list(keys)
    if pts[0][0] > 0 and start is not None:
        pts.insert(0, (0, start, ""))
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0, _e0), (t1, v1, e1) in zip(pts, pts[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            return _rad_mix(prop, v0, v1, _rad_ease(f, e1), rgb)
    return pts[-1][1]
'''

VSM_RT = r'''

class _VisualStates:
    """Visual State Manager (Expression Blend). Controls switch automatically between Normal,
    MouseOver, Pressed, Focused and Disabled; GoToState("Name") moves the form to one of its
    custom states (GoToState("Normal") = back to the designed values); GoToState(state, "Button1")
    forces a state on one control (GoToState("Normal", "Button1") gives it back to the automatic states)."""
    AUTO = ("MouseOver", "Pressed", "Focused", "Disabled")

    def __init__(self, owner, io, controls, form_states):
        self._io = io
        self.Controls = controls            # {control: {state: {property: value}}}
        self.FormStates = form_states       # {state: {form property: value}}
        self.CurrentState = "Normal"
        self._flags, self._manual, self._saved, self._applied = {}, {}, {}, {}
        for name, states in controls.items():
            if any(s in states for s in self.AUTO):
                io.hook(name, self, "Disabled" in states)

    @property
    def States(self):
        names = list(self.FormStates)
        for states in self.Controls.values():
            names += [s for s in states if s not in self.AUTO and s not in names]
        return names

    def StateOf(self, control):
        """Automatic states active on *control* (e.g. {"MouseOver", "Pressed"})."""
        return set(self._flags.get(control, ()))

    def _wanted(self, name):
        out = {}
        cur = self.CurrentState
        if not name:
            return dict(self.FormStates.get(cur, {})) if cur != "Normal" else out
        st = self.Controls.get(name, {})
        if cur != "Normal":
            out.update(st.get(cur, {}))
        manual = self._manual.get(name)
        if manual:
            out.update(st.get(manual, {}))
            return out
        flags = self._flags.get(name, ())
        if "Disabled" in flags:
            out.update(st.get("Disabled", {}))
            return out
        for s in ("Focused", "MouseOver", "Pressed"):
            if s in flags:
                out.update(st.get(s, {}))
        return out

    def _update(self, name):
        want = self._wanted(name)
        for key in [k for k in self._applied if k[0] == name and k[1] not in want]:
            del self._applied[key]
            self._io.set(name, key[1], self._saved.pop(key, None))
            if key[1] in ("Left", "Top", "Width", "Height"):
                self._io.release(name, key[1])      # Anchor / Dock take the control back
        for prop, value in want.items():
            key = (name, prop)
            if key not in self._applied:
                self._saved[key] = self._io.get(name, prop)
            elif self._applied[key] == value:
                continue
            self._applied[key] = value
            self._io.set(name, prop, value)

    def Flag(self, name, state, on):
        flags = self._flags.setdefault(name, set())
        if (state in flags) == bool(on):
            return
        if on:
            flags.add(state)
        else:
            flags.discard(state)
        self._update(name)

    def GoToState(self, state, control=None):
        state = str(state or "Normal")
        if state == "Base":
            state = "Normal"
        if control:
            control = getattr(control, "_rad_name", control)
            if state == "Normal":
                self._manual.pop(control, None)
            else:
                self._manual[control] = state
            self._update(control)
            return True
        if state != "Normal" and state not in self.States:
            return False
        self.CurrentState = state
        for name in [""] + list(self.Controls):
            self._update(name)
        return True
'''

TK_IO = r'''

class _RadIO:
    """Reads / writes neutral properties of the Tk widgets (visual states, storyboards, bindings)."""
    vis_hook = None         # animations: callable(name, visible) -> True when it handles the change
    quiet = 0               # > 0 while the animations write (no show / hide hooks)
    GEO = {"Left": "x", "Top": "y", "Width": "width", "Height": "height"}
    REL = {"Left": "relx", "Top": "rely", "Width": "relwidth", "Height": "relheight"}

    def __init__(self, owner):
        self.o = owner
        self._anchored = {}     # (name, prop) -> (offset, rel) of Anchor / Dock before a state / storyboard

    def release(self, name, prop=None):
        """A state / storyboard gave the geometry back: Anchor / Dock place the control again."""
        props = [prop] if prop else list(self.GEO)
        new = {}
        for p in props:
            orig = self._anchored.pop((name, p), None)
            if orig is not None:
                new[self.GEO[p]], new[self.REL[p]] = orig
        if not new:
            return
        self.o._places.setdefault(name, {}).update(new)
        try:
            w = self.w(name)
            if w.winfo_manager() == "place":
                w.place_configure(**new)
        except (tk.TclError, AttributeError):
            pass

    def w(self, name):
        return self.o.root if not name else getattr(self.o, name)

    def _var(self, name):
        try:
            return getattr(self.o, name + "_var")
        except AttributeError:
            return None

    def _font(self, w):
        import tkinter.font as tkfont
        return tkfont.Font(root=w, font=w.cget("font")).actual()

    def get(self, name, prop):
        try:
            w = self.w(name)
            if not name:
                return self._get_form(w, prop)
            if prop == "Text":
                if isinstance(w, tk.Text):
                    return w.get("1.0", "end-1c")
                if isinstance(w, (tk.Entry, ttk.Entry)):
                    return w.get()
                return str(w.cget("text"))
            if prop in self.GEO:
                info = w.place_info() or self.o._places.get(name, {})
                v = info.get(self.GEO[prop])
                if v in (None, "") or float(info.get(self.REL[prop]) or 0):   # anchored: the real value
                    w.update_idletasks()
                    return {"Left": w.winfo_x, "Top": w.winfo_y, "Width": w.winfo_width,
                            "Height": w.winfo_height}[prop]()
                return int(float(v))
            if prop == "BackColor":
                return str(w.cget("bg"))
            if prop == "ForeColor":
                return str(w.cget("fg"))
            if prop == "Visible":
                return w.winfo_manager() == "place"
            if prop in ("FontSize", "FontBold", "FontItalic"):
                a = self._font(w)
                return {"FontSize": abs(int(a["size"])), "FontBold": a["weight"] == "bold",
                        "FontItalic": a["slant"] == "italic"}[prop]
            if prop == "Opacity":
                return 1.0
            if prop == "Checked" and isinstance(w, tk.Radiobutton):
                return self.o._radio.get() == name
            if prop in ("Value", "Checked"):
                var = self._var(name)
                return var.get() if var is not None else w.cget("value")
        except (tk.TclError, AttributeError, ValueError, KeyError, TypeError):
            return None
        return None

    def _get_form(self, w, prop):
        if prop == "Text":
            return w.title()
        if prop == "BackColor":
            return str(w.cget("bg"))
        if prop == "Opacity":
            return float(w.attributes("-alpha"))
        if prop in self.GEO:
            size, _, pos = w.geometry().partition("+")
            ww, hh = (int(v) for v in size.split("x"))
            x, _, y = pos.partition("+")
            return {"Width": ww, "Height": hh, "Left": int(x or 0), "Top": int(y or 0)}[prop]
        return None

    def set(self, name, prop, v):
        if v is None:
            return
        if prop == "Visible" and name and not self.quiet and self.vis_hook is not None \
                and self.vis_hook(name, bool(v)):
            return                                  # an "On show" / "On hide" animation takes over
        try:
            w = self.w(name)
            if not name:
                return self._set_form(w, prop, v)
            if prop == "Text":
                if isinstance(w, tk.Text):
                    state = w.cget("state")
                    w.configure(state="normal")
                    w.delete("1.0", "end")
                    w.insert("1.0", str(v))
                    w.configure(state=state)
                elif isinstance(w, (tk.Entry, ttk.Entry)):
                    var = self._var(name)
                    if var is not None:
                        var.set(str(v))
                    else:
                        w.delete(0, "end")
                        w.insert(0, str(v))
                else:
                    w.configure(text=str(v))
            elif prop in self.GEO:
                key, rel = self.GEO[prop], self.REL[prop]
                opts = self.o._places.setdefault(name, {})
                new = {key: int(v)}
                if float(opts.get(rel) or 0):     # Anchor / Dock: the animated value is absolute
                    self._anchored.setdefault((name, prop), (opts.get(key, 0), opts[rel]))
                    opts.pop(rel, None)
                    new[rel] = 0
                opts[key] = int(v)
                if w.winfo_manager() == "place":
                    w.place_configure(**new)
            elif prop == "BackColor":
                w.configure(bg=v)
            elif prop == "ForeColor":
                w.configure(fg=v)
            elif prop == "Visible":
                if v:
                    w.place(**self.o._places.get(name, {}))
                else:
                    w.place_forget()
            elif prop in ("FontSize", "FontBold", "FontItalic"):
                a = self._font(w)
                size = int(v) if prop == "FontSize" else abs(int(a["size"]))
                bold = bool(v) if prop == "FontBold" else a["weight"] == "bold"
                italic = bool(v) if prop == "FontItalic" else a["slant"] == "italic"
                style = " ".join(s for s, on in (("bold", bold), ("italic", italic)) if on)
                w.configure(font=(a["family"], size, style) if style else (a["family"], size))
            elif prop == "Checked" and isinstance(w, tk.Radiobutton):
                if v:
                    self.o._radio.set(name)
                elif self.o._radio.get() == name:
                    self.o._radio.set("")
            elif prop in ("Value", "Checked"):
                var = self._var(name)
                if var is not None:
                    var.set(bool(v) if prop == "Checked" else int(v))
                else:
                    w.configure(value=int(v))
        except (tk.TclError, AttributeError, ValueError, TypeError):
            pass

    def _set_form(self, w, prop, v):
        if prop == "Text":
            w.title(str(v))
        elif prop == "BackColor":
            w.configure(bg=v)
            client = self.o.__dict__.get("_client")
            if client is not None:
                client.configure(bg=v)
        elif prop == "Opacity":
            w.attributes("-alpha", float(v))
        elif prop in ("Width", "Height"):
            ww, hh = self._get_form(w, "Width"), self._get_form(w, "Height")
            w.geometry(f"{int(v) if prop == 'Width' else ww}x{int(v) if prop == 'Height' else hh}")
        elif prop in ("Left", "Top"):
            x, y = self._get_form(w, "Left"), self._get_form(w, "Top")
            w.geometry(f"+{int(v) if prop == 'Left' else x}+{int(v) if prop == 'Top' else y}")

    def set_items(self, name, items):
        w = self.w(name)
        items = [str(i) for i in items]
        if isinstance(w, tk.Listbox):
            w.delete(0, "end")
            if items:
                w.insert("end", *items)
        elif isinstance(w, ttk.Combobox):
            w.configure(values=items)

    def set_rows(self, name, columns, rows):
        w = self.w(name)
        if hasattr(w, "SetColumns"):
            w.SetColumns(list(columns))
            w.Clear()
            for r in rows:
                w.AddRow(*r)

    def rgb(self, name, prop, value):
        c = _rad_rgb_hex(value)
        if c is None and value:
            try:
                c = tuple(x // 256 for x in self.o.root.winfo_rgb(value))
            except tk.TclError:
                return None
        return c

    def later(self, ms, fn):
        self.o.root.after(int(ms), fn)

    def bind(self, name, event, fn):
        """Animation triggers: event "click" / "enter" / "leave" of a control ("" = the form) calls fn()."""
        w = self.w(name)
        if not name:
            client = self.o.__dict__.get("_client")
            w = client if client is not None else w
        seq = {"click": "<Button-1>", "enter": "<Enter>", "leave": "<Leave>"}[event]

        def call(e):
            if not name and e.widget is not w:      # the form itself, not one of its controls
                return
            fn()
        w.bind(seq, call, add="+")

    def parent_bg(self, name):
        """Background colour of the control's container (fades without transparency blend into it)."""
        try:
            m = self.w(name).master
            try:
                return str(m.cget("bg"))
            except tk.TclError:
                return str(ttk.Style().lookup(m.winfo_class(), "background")) or None
        except (tk.TclError, AttributeError):
            return None

    def on_select(self, name, fn):
        w = self.w(name)
        if isinstance(w, tk.Listbox):
            w.bind("<<ListboxSelect>>", lambda _e: w.curselection() and fn(w.curselection()[0]), add="+")
        elif isinstance(w, ttk.Combobox):
            w.bind("<<ComboboxSelected>>", lambda _e: w.current() >= 0 and fn(w.current()), add="+")

    def hook(self, name, vsm, disabled=False):
        w = self.w(name)
        for seq, state, on in (("<Enter>", "MouseOver", True), ("<Leave>", "MouseOver", False),
                               ("<ButtonPress-1>", "Pressed", True), ("<ButtonRelease-1>", "Pressed", False),
                               ("<FocusIn>", "Focused", True), ("<FocusOut>", "Focused", False)):
            w.bind(seq, lambda _e, s=state, o=on: vsm.Flag(name, s, o), add="+")
        if disabled:            # Tk has no "state changed" event: look at the widget's state
            def poll():
                try:
                    off = str(w.cget("state")) == "disabled"
                except tk.TclError:
                    try:
                        off = bool(w.instate(["disabled"]))
                    except (tk.TclError, AttributeError):
                        off = False
                vsm.Flag(name, "Disabled", off)
                self.o.root.after(120, poll)
            poll()
'''

QT_IO = r'''

class _RadStateEvents(QObject):
    """Feeds MouseOver / Pressed / Focused / Disabled of one widget to the visual state manager."""

    def __init__(self, widget, name, vsm):
        super().__init__(widget)
        self.w, self.name, self.vsm = widget, name, vsm
        self.map = {QEvent.Type.Enter: ("MouseOver", True), QEvent.Type.Leave: ("MouseOver", False),
                    QEvent.Type.MouseButtonPress: ("Pressed", True),
                    QEvent.Type.MouseButtonRelease: ("Pressed", False),
                    QEvent.Type.FocusIn: ("Focused", True), QEvent.Type.FocusOut: ("Focused", False)}
        widget.installEventFilter(self)
        vp = getattr(widget, "viewport", None)
        if callable(vp):
            vp().installEventFilter(self)
        if not widget.isEnabled():
            vsm.Flag(name, "Disabled", True)

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.Type.EnabledChange and obj is self.w:
            self.vsm.Flag(self.name, "Disabled", not self.w.isEnabled())
        elif t in self.map:
            state, on = self.map[t]
            self.vsm.Flag(self.name, state, on)
        return False


class _RadFxEvents(QObject):
    """Click / mouse enter / leave of one widget starts an animation (Animations window triggers)."""

    def __init__(self, widget, event, fn):
        super().__init__(widget)
        self.w, self.fn = widget, fn
        self.t = {"click": QEvent.Type.MouseButtonRelease, "enter": QEvent.Type.Enter,
                  "leave": QEvent.Type.Leave}[event]
        widget.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.w and ev.type() == self.t:
            inside = True
            if self.t == QEvent.Type.MouseButtonRelease:
                try:
                    inside = self.w.rect().contains(ev.position().toPoint())
                except AttributeError:
                    pass
            if inside:
                self.fn()
        return False


class _RadIO:
    """Reads / writes neutral properties of the Qt widgets (visual states, storyboards, bindings)."""
    vis_hook = None         # animations: callable(name, visible) -> True when it handles the change
    quiet = 0               # > 0 while the animations write (no show / hide hooks)

    def __init__(self, owner):
        self.o = owner
        self._colors, self._base_ss, self._events = {}, {}, []

    def w(self, name):
        return self.o if not name else getattr(self.o, name)

    def get(self, name, prop):
        try:
            w = self.w(name)
            if prop == "Text":
                if not name:
                    return w.windowTitle()
                if isinstance(w, QPlainTextEdit):
                    return w.toPlainText()
                if isinstance(w, QGroupBox):
                    return w.title()
                if isinstance(w, QComboBox):
                    return w.currentText()
                return w.text() if hasattr(w, "text") else ""
            if prop == "Left":
                return w.x()
            if prop == "Top":
                return w.y()
            if prop == "Width":
                return w.width()
            if prop == "Height":
                return w.height() - self._top() if not name else w.height()
            if prop in ("BackColor", "ForeColor"):
                return self._colors.get(name, {}).get(prop, "")
            if prop == "Visible":
                return not w.isHidden()
            if prop == "FontSize":
                return w.font().pointSize()
            if prop == "FontBold":
                return w.font().bold()
            if prop == "FontItalic":
                return w.font().italic()
            if prop == "Opacity":
                if not name:
                    return w.windowOpacity()
                eff = w.graphicsEffect()
                return eff.opacity() if isinstance(eff, QGraphicsOpacityEffect) else 1.0
            if prop == "Value":
                return w.value()
            if prop == "Checked":
                return w.isChecked()
        except (AttributeError, RuntimeError, TypeError):
            return None
        return None

    def _top(self):
        client = self.o.__dict__.get("_client")
        return self.o.height() - client.height() if client is not None else 0

    @staticmethod
    def _hold(name, w, prop):
        """A state / storyboard sets this geometry: Anchor / Dock leave it alone until release()."""
        if name:
            held = getattr(w, "_rad_held", None)
            if held is None:
                held = set()
                w._rad_held = held
            held.add(prop)

    def release(self, name, prop=None):
        """A state / storyboard gave the geometry back: Anchor / Dock place the control again."""
        if not name:
            return
        try:
            w = self.w(name)
            held = getattr(w, "_rad_held", None)
            if not held:
                return
            if prop is None:
                held.clear()
            else:
                held.discard(prop)
            host = w.parentWidget()
            for lay in (host.children() if host is not None else []):
                if type(lay).__name__ == "_Layout" and any(it[0] is w for it in lay.items):
                    lay.apply()
        except (AttributeError, RuntimeError):
            pass

    def set(self, name, prop, v):
        if v is None:
            return
        if prop == "Visible" and name and not self.quiet and self.vis_hook is not None \
                and self.vis_hook(name, bool(v)):
            return                                  # an "On show" / "On hide" animation takes over
        try:
            w = self.w(name)
            if prop == "Text":
                if not name:
                    w.setWindowTitle(str(v))
                elif isinstance(w, QPlainTextEdit):
                    w.setPlainText(str(v))
                elif isinstance(w, QGroupBox):
                    w.setTitle(str(v))
                elif isinstance(w, QComboBox):
                    if w.isEditable():
                        w.setEditText(str(v))
                    elif w.findText(str(v)) >= 0:
                        w.setCurrentIndex(w.findText(str(v)))
                elif hasattr(w, "setText"):
                    w.setText(str(v))
            elif prop in ("Left", "Top"):
                self._hold(name, w, prop)
                w.move(int(v) if prop == "Left" else w.x(), int(v) if prop == "Top" else w.y())
            elif prop in ("Width", "Height"):
                self._hold(name, w, prop)
                top = 0 if name else self._top()
                w.resize(int(v) if prop == "Width" else w.width(), int(v) + top if prop == "Height" else w.height())
            elif prop in ("BackColor", "ForeColor"):
                d = self._colors.setdefault(name, {})
                if v:
                    d[prop] = str(v)
                else:
                    d.pop(prop, None)
                self._restyle(name, w)
            elif prop == "Visible":
                w.setVisible(bool(v))
            elif prop in ("FontSize", "FontBold", "FontItalic"):
                f = w.font()
                if prop == "FontSize":
                    f.setPointSize(max(1, int(v)))
                elif prop == "FontBold":
                    f.setBold(bool(v))
                else:
                    f.setItalic(bool(v))
                w.setFont(f)
            elif prop == "Opacity":
                if not name:
                    w.setWindowOpacity(float(v))
                else:
                    eff = w.graphicsEffect()
                    if not isinstance(eff, QGraphicsOpacityEffect):
                        eff = QGraphicsOpacityEffect(w)
                        w.setGraphicsEffect(eff)
                    eff.setOpacity(max(0.0, min(1.0, float(v))))
            elif prop == "Value":
                w.setValue(int(float(v)))
            elif prop == "Checked":
                w.setChecked(bool(v))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _restyle(self, name, w):
        if name not in self._base_ss:
            self._base_ss[name] = w.styleSheet()
        d = self._colors.get(name, {})
        rules = ""
        if d.get("BackColor"):
            rules += f"background-color:{d['BackColor']};"
        if d.get("ForeColor"):
            rules += f"color:{d['ForeColor']};"
        if not rules:
            w.setStyleSheet(self._base_ss[name])
            return
        if not w.objectName():
            w.setObjectName(name or "rad_form")
        sel = f"#{w.objectName()}" + (", #client" if not name else "")
        w.setStyleSheet(self._base_ss[name] + f"\n{sel} {{ {rules} }}")

    def set_items(self, name, items):
        w = self.w(name)
        w.clear()
        w.addItems([str(i) for i in items])

    def set_rows(self, name, columns, rows):
        w = self.w(name)
        w.clear()
        w.setColumnCount(max(1, len(columns)))
        w.setHorizontalHeaderLabels([str(c) for c in columns])
        w.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, text in enumerate(row):
                w.setItem(r, c, QTableWidgetItem(str(text)))

    def rgb(self, name, prop, value):
        c = _rad_rgb_hex(value)
        if c is not None:
            return c
        if value:
            q = QColor(str(value))
        else:
            w = self.w(name)
            q = w.palette().color(w.backgroundRole() if prop == "BackColor" else w.foregroundRole())
        return (q.red(), q.green(), q.blue()) if q.isValid() else None

    def later(self, ms, fn):
        QTimer.singleShot(int(ms), self.o, fn)

    def bind(self, name, event, fn):
        """Animation triggers: event "click" / "enter" / "leave" of a control ("" = the form) calls fn()."""
        self._events.append(_RadFxEvents(self.w(name), event, fn))

    def parent_bg(self, name):
        try:
            w = self.w(name)
            host = w.parentWidget() or w
            return host.palette().color(host.backgroundRole()).name()
        except (AttributeError, RuntimeError):
            return None

    def on_select(self, name, fn):
        w = self.w(name)
        sig = w.currentRowChanged if isinstance(w, QListWidget) else w.currentIndexChanged
        sig.connect(lambda i: i >= 0 and fn(i))

    def hook(self, name, vsm, disabled=False):
        self._events.append(_RadStateEvents(self.w(name), name, vsm))
'''


def _lit(value) -> str:
    return repr(value)


def _clean_states(form) -> tuple[dict, dict]:
    ctrl_states: dict = {}
    for c in form.controls:
        if c.ctype.nonvisual or not c.states:
            continue
        st = {}
        for s, ov in c.states.items():
            if isinstance(ov, dict):
                st[str(s)] = {p: coerce(p, v) for p, v in ov.items() if p in STATE_PROPS}
        st = {s: ov for s, ov in st.items() if ov}
        if st:
            ctrl_states[c.name] = st
    fst = {}
    for s, ov in (form.extra.get("states") or {}).items():
        fst[str(s)] = {p: coerce(p, v) for p, v in (ov or {}).items() if p in FORM_STATE_PROPS}
    return ctrl_states, fst


def python_blend(form, toolkit: str) -> dict | None:
    """Code for the Blend features of *form* in a python-tk ("tk") or python-qt ("qt") designer file.

    Returns None when the form uses none of them (the generated code then stays exactly as before),
    else {"runtime": str, "init": [lines], "after_load": [lines], "methods": [lines]}; lines are
    relative to the class body (init/after_load: 8 spaces, methods: 4 spaces)."""
    from . import databinding, timeline
    ctrl_states, fst = _clean_states(form)
    has_states = bool(ctrl_states or fst)
    sbs = timeline.storyboards_for_code(form)
    sources, binds = databinding.for_code(form)
    fx = _fx_plan(form, toolkit)
    if not (has_states or sbs or sources or fx):
        return None
    runtime = COMMON_RT
    if has_states:
        runtime += VSM_RT
    if sbs or fx:
        runtime += timeline.STORYBOARD_RT
    if fx:
        from ..motion import presets as motion_presets, runtime_py
        runtime += motion_presets.PRESETS_RT + runtime_py.FX_RT
    if sources:
        runtime += databinding.DATA_RT
    runtime += TK_IO if toolkit == "tk" else QT_IO
    I = "        "
    init = ["", I + "# Expression Blend: data sources and bindings, visual states, storyboards",
            I + "self._rad = _RadIO(self)"]
    methods = ["", "    # ---------------------------------------------------------------- Expression Blend"]
    if sources:
        init += databinding.init_lines(sources, binds, I)
        methods += databinding.METHODS
    if has_states:
        init.append(I + f"self._vsm = _VisualStates(self, self._rad, {_lit(ctrl_states)}, {_lit(fst)})")
        methods += VSM_METHODS
    after: list[str] = []
    for sb in sbs:
        init.append(I + f"self.{sb['name']} = _Storyboard(self, self._rad, {sb['name']!r}, {_lit(sb['tracks'])}, "
                        f"repeat={sb['repeat']!r}, autoreverse={sb['autoreverse']!r})")
        if sb["autostart"]:
            after.append(I + (f"self.root.after(0, self.{sb['name']}.Begin)" if toolkit == "tk"
                              else f"QTimer.singleShot(0, self.{sb['name']}.Begin)"))
    if fx:                  # Animations window (radide/motion): presets, triggers, Animate() from code
        from ..motion import runtime_py
        sbs_fx = [{k: sb[k] for k in ("name", "fx", "target", "tracks", "repeat", "count", "autoreverse",
                                      "delayMs", "restore")} for sb in fx["storyboards"]]
        init.append(I + f"self._fx = _RadFx(self, self._rad, {_lit(sbs_fx)}, {_lit(fx['triggers'])}, "
                        f"reduced={fx['reduced_motion']!r}, alpha={toolkit != 'tk'!r})")
        after.append(I + ("self.root.after(0, self._fx.start)" if toolkit == "tk"
                          else "QTimer.singleShot(0, self._fx.start)"))
        methods += runtime_py.FX_METHODS
    return {"runtime": runtime, "init": init, "after_load": after, "methods": methods}


def _fx_plan(form, toolkit: str) -> dict | None:
    """motion.expand() of the form's animations for python-tk / python-qt, or None when it has none
    (a form with only ``extra["motion"]`` still gets the runtime, for Animate() from code)."""
    if not (form.extra.get("animations") or form.extra.get("motion")):
        return None
    try:
        from ..motion.expand import expand
        return expand(form, "py" if toolkit == "tk" else "qt")
    except Exception:  # noqa: BLE001 - a broken animation list must never break code generation
        return None


VSM_METHODS = [
    "",
    "    def GoToState(self, state, control=None):",
    "        \"\"\"Go to a visual state of the form (\"Normal\" = the designed values), or of one control.\"\"\"",
    "        return self._vsm.GoToState(state, control)",
]


def _design_ns() -> dict:
    """The generated runtime's toolkit-free helpers, for design-time previews (same algorithm)."""
    ns: dict = {}
    exec(compile(COMMON_RT, "<blend-runtime>", "exec"), ns)        # noqa: S102 - our own constant
    return ns


DESIGN = _design_ns()


# ====================================================================== design-time preview
class BlendPreview(QObject):
    """Blend features on one DesignerView, without changing the model: the selected visual state,
    the timeline position and the sample data are drawn over the designer's own previews."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.doc = view.doc
        self.state = ""                 # "" = Base
        self.recording = False
        self.timeline = None            # (storyboard dict, ms) while scrubbing / playing
        self.samples = True
        self.key_recorder = None        # timeline.py: callable(ctrl) while recording keyframes
        self._dirty: set[int] = set()
        self._shadow: dict = {}
        self._busy = False
        self.doc.structureChanged.connect(self.refresh)
        self.doc.controlChanged.connect(self._changed)
        self.doc.renamed.connect(lambda old, new: rename_references(self.doc.form, old, new))
        self.refresh()                  # sample data shows as soon as the designer opens

    @staticmethod
    def of(view) -> "BlendPreview":
        bp = getattr(view, "_blend_preview", None)
        if bp is None:
            bp = BlendPreview(view)
            view._blend_preview = bp
        return bp

    # ------------------------------------------------------------ effective props
    def effective(self, ctrl) -> dict:
        from . import databinding, timeline
        props = dict(ctrl.props)
        if self.samples:
            props.update(databinding.sample_props(self.doc, ctrl))
            try:                    # real database rows (radide/databinding_sql.py, Data Sources window)
                from ..databinding_sql import sample_props as db_sample_props
                props.update(db_sample_props(self.doc, ctrl))
            except Exception:  # noqa: BLE001 - never break the designer preview
                pass
        if self.state:
            props.update(overrides(self.doc.form, ctrl, self.state))
        if self.timeline is not None:
            sb, ms = self.timeline
            props.update(timeline.props_at(sb, ctrl.name, ms, props, self._parent_bg(ctrl)))
        return props

    def design_props(self, ctrl) -> dict:
        """Properties the designer should use for ctrl's selection outline / hit testing (the previewed
        state / timeline geometry; sample data is left out - it never changes the geometry).
        ctrl None = the form (its custom state and storyboard tracks with target "")."""
        from . import timeline
        form = self.doc.form
        base = form.props if ctrl is None else ctrl.props
        if not self.state and self.timeline is None:
            return base
        props = dict(base)
        if self.state and not (ctrl is None and self.state in AUTO_STATES):
            props.update(overrides(form, ctrl, self.state))
        if self.timeline is not None:
            sb, ms = self.timeline
            if sb is not None:
                props.update(timeline.props_at(sb, "" if ctrl is None else ctrl.name, ms, props,
                                               self._parent_bg(ctrl)))
        for k in ("Left", "Top", "Width", "Height"):
            if k in props:
                try:
                    props[k] = int(props[k])
                except (TypeError, ValueError):
                    props[k] = base.get(k, 0)
        return props

    def _parent_bg(self, ctrl):
        """Background colour of ctrl's container (design-time value of "$parent" keyframes)."""
        if ctrl is None:
            return None
        form = self.doc.form
        host = form.find(ctrl.parent) if ctrl.parent else None
        return (host.props if host is not None else form.props).get("BackColor") or None

    def apply(self, ctrl) -> None:
        from ..model import Control
        from ..preview import apply_props
        w = self.view.previews.get(id(ctrl))
        if w is None:
            return
        eff = self.effective(ctrl)
        if eff == ctrl.props:
            if id(ctrl) in self._dirty:
                self._dirty.discard(id(ctrl))
                apply_props(w, ctrl)
            return
        self._dirty.add(id(ctrl))
        try:
            apply_props(w, Control(ctrl.type, eff))
        except (TypeError, ValueError, KeyError):
            apply_props(w, ctrl)
            return
        op = eff.get("Opacity")
        if op is not None and float(op) < 1:
            e = QGraphicsOpacityEffect(w)
            e.setOpacity(max(0.0, float(op)))
            w.setGraphicsEffect(e)

    def refresh(self, *_a) -> None:
        if self.recording:
            for c in self.doc.form.controls:
                self._shadow.setdefault(id(c), {k: c.props.get(k) for k in STATE_PROPS})
        live = {id(c) for c in self.doc.form.controls}
        self._dirty &= live
        for c in self.doc.form.visual():
            self.apply(c)
        # the form's own previewed values (Text / BackColor / size) and the selection outline
        if hasattr(self.view, "layout_form"):
            self.view.layout_form()
            self.view.frame.update()
            self.view.overlay.update()

    # ------------------------------------------------------------ state recording
    def set_state(self, state: str) -> None:
        self.state = "" if state in ("", BASE) else state
        if not self.state:
            self.set_recording(False)
        self.refresh()

    def set_recording(self, on: bool) -> None:
        self.recording = bool(on) and bool(self.state)
        self._shadow = {id(c): {k: c.props.get(k) for k in STATE_PROPS} for c in self.doc.form.controls}
        self._shadow["form"] = {k: self.doc.form.props.get(k) for k in FORM_STATE_PROPS}

    def _changed(self, ctrl) -> None:
        if self._busy:
            return
        if self.recording and self.state:
            self._busy = True
            try:
                self._record(ctrl)
            finally:
                self._busy = False
        elif self.key_recorder is not None:
            self._busy = True
            try:
                self.key_recorder(ctrl)
            finally:
                self._busy = False
        if ctrl is None:
            return
        self.apply(ctrl)

    def _record(self, ctrl) -> None:
        """A property was edited while recording: it becomes an override of the state."""
        form = self.doc.form
        if ctrl is None:
            if self.state in AUTO_STATES:
                return
            shadow = self._shadow.setdefault("form", {k: form.props.get(k) for k in FORM_STATE_PROPS})
            for k in FORM_STATE_PROPS:
                if k in form.props and form.props.get(k) != shadow.get(k):
                    set_override(form, None, self.state, k, form.props[k])
                    form.props[k] = shadow.get(k)
            self.view.layout_form()
            self.doc.set_modified()
            return
        shadow = self._shadow.setdefault(id(ctrl), {k: ctrl.props.get(k) for k in STATE_PROPS})
        changed = False
        for k in STATE_PROPS:
            if k in ctrl.props and ctrl.props.get(k) != shadow.get(k):
                set_override(form, ctrl, self.state, k, ctrl.props[k])
                ctrl.props[k] = shadow.get(k)
                changed = True
        if changed:
            self.doc.set_modified()
            panel = getattr(self.view.window(), "states_panel", None)
            if panel is not None:
                panel.refresh_overrides()


# ====================================================================== States panel
def current_view(win):
    d = win._current_designer() if hasattr(win, "_current_designer") else None
    return d


def is_python(win, view) -> bool:
    try:
        name = view.doc.form.name
        return win.plugin_for_form(name).id in PYTHON_PLUGINS
    except Exception:  # noqa: BLE001
        return True


def set_note(label, text: str) -> None:
    """Set a panel's note line and show it only when there is a note (an empty label left a gap)."""
    label.setText(text)
    label.setVisible(bool(text))


def compact_combo(cb, chars: int = 8):
    """A combo box that does not widen its dock to its longest item / placeholder (the Blend panels are
    tabbed in a narrow column and got a horizontal scroll bar)."""
    from PyQt6.QtWidgets import QComboBox as _Cb
    cb.setSizeAdjustPolicy(_Cb.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    cb.setMinimumContentsLength(chars)
    return cb


def section_label(text: str):
    """A small bold caption above a list / table of a Blend panel."""
    lab = QLabel(text)
    f = lab.font()
    f.setBold(True)
    lab.setFont(f)
    return lab


class StatesPanel(QWidget):
    """Blend's States panel: Base, the automatic control states and the form's custom states.
    The overrides table lists what the selected state changes on the selected control (or the form)."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.view = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setProperty("radRole", "note")
        lay.addWidget(self.note)
        self.note.hide()                        # shown only when it has something to say (no empty gap)
        lay.addWidget(section_label("Visual states"))
        self.list = QListWidget()
        self.list.setMaximumHeight(170)
        self.list.currentItemChanged.connect(self._on_state)
        lay.addWidget(self.list)
        row = QHBoxLayout()
        self.btn_add = QToolButton(text="Add State")
        self.btn_add.clicked.connect(self.add_state)
        self.btn_del = QToolButton(text="Delete")
        self.btn_del.clicked.connect(self.delete_state)
        self.rec = QCheckBox("Record")
        self.rec.setToolTip("While recording, edits in the Properties window / designer change the selected "
                            "state instead of the base values (like Blend's state recording).")
        self.rec.toggled.connect(self._on_record)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_del)
        row.addStretch(1)
        row.addWidget(self.rec)
        lay.addLayout(row)
        self.target = QLabel("")
        lay.addWidget(self.target)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Property", "Value in state"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self._on_value_edited)
        lay.addWidget(self.table, 1)
        row2 = QHBoxLayout()
        self.prop = QComboBox()
        self.prop.setPlaceholderText("Property to override")
        compact_combo(self.prop)
        self.prop.setToolTip("Property to override in the selected state")
        self.btn_set = QToolButton(text="Override")
        self.btn_set.setToolTip("Add an override of this property in the selected state (current value)")
        self.btn_set.clicked.connect(self.add_override)
        self.btn_color = QToolButton(text="Colour...")
        self.btn_color.clicked.connect(self.pick_color)
        self.btn_rm = QToolButton(text="Remove")
        self.btn_rm.clicked.connect(self.remove_override)
        row2.addWidget(self.prop, 1)
        row2.addWidget(self.btn_set)
        lay.addLayout(row2)
        row3 = QHBoxLayout()                    # (own row: the panel lives in a narrow dock column)
        row3.addStretch(1)
        row3.addWidget(self.btn_color)
        row3.addWidget(self.btn_rm)
        lay.addLayout(row3)
        self._filling = False
        self.bind(None)

    # ------------------------------------------------------------ binding
    def bind(self, view) -> None:
        if view is self.view and view is not None:
            return
        if self.view is not None:
            try:
                self.view.doc.selectionChanged.disconnect(self._on_selection)
                self.view.doc.structureChanged.disconnect(self.rebuild_states)
            except (TypeError, RuntimeError):
                pass
        self.view = view
        if view is not None:
            view.doc.selectionChanged.connect(self._on_selection)
            view.doc.structureChanged.connect(self.rebuild_states)
        self.rebuild_states()

    @property
    def bp(self) -> BlendPreview | None:
        return BlendPreview.of(self.view) if self.view is not None else None

    def rebuild_states(self) -> None:
        self._filling = True
        cur = self.bp.state if self.bp else ""
        self.list.clear()
        enabled = self.view is not None
        for w in (self.list, self.btn_add, self.btn_del, self.rec, self.table, self.prop, self.btn_set,
                  self.btn_rm, self.btn_color):
            w.setEnabled(enabled)
        if not enabled:
            set_note(self.note, "Open a form designer to edit its visual states.")
            self.table.setRowCount(0)
            self._filling = False
            return
        set_note(self.note, "" if is_python(self.win, self.view) else
                 "Visual states run in Python (Tkinter / PySide6) forms; this language ignores them.")
        form = self.view.doc.form
        entries = [(BASE, "Base (designed values)")]
        entries += [(s, f"{s}  (automatic)") for s in AUTO_STATES]
        entries += [(s, f"{s}  (form state - GoToState)") for s in custom_state_names(form)]
        for key, text in entries:
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, key)
            self.list.addItem(it)
            if key == (cur or BASE):
                self.list.setCurrentItem(it)
        if self.list.currentItem() is None:
            self.list.setCurrentRow(0)
        self._filling = False
        self.refresh_overrides()

    def state(self) -> str:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else BASE

    def _on_state(self, *_a) -> None:
        if self._filling or self.bp is None:
            return
        self.bp.set_state(self.state())
        if self.state() == BASE:
            self.rec.setChecked(False)
        elif self.rec.isChecked():
            self.bp.set_recording(True)
        self.refresh_overrides()

    def _on_record(self, on: bool) -> None:
        if self.bp is None:
            return
        if on and self.state() == BASE:
            self.rec.setChecked(False)
            return
        self.bp.set_recording(on)
        if self.view is not None:
            set_note(self.note, f"Recording state '{self.state()}': property edits go to this state." if on
                     else "")

    def _on_selection(self, *_a) -> None:
        self.refresh_overrides()

    # ------------------------------------------------------------ overrides table
    def _owner(self):
        return self.view.doc.selected if self.view is not None else None

    def refresh_overrides(self) -> None:
        if self.view is None:
            return
        self._filling = True
        ctrl = self._owner()
        state = self.state()
        form = self.view.doc.form
        name = ctrl.name if ctrl is not None else f"{form.name} (form)"
        self.target.setText(f"Overrides of <b>{name}</b> in state <b>{state}</b>")
        ov = overrides(form, ctrl, state)
        self.table.setRowCount(len(ov))
        for r, (k, v) in enumerate(sorted(ov.items())):
            a = QTableWidgetItem(k)
            a.setFlags(a.flags() & ~Qt.ItemFlag.ItemIsEditable)
            b = QTableWidgetItem(json.dumps(v) if not isinstance(v, str) else v)
            if k in COLOR_PROPS and v:
                b.setBackground(QColor(str(v)))
            self.table.setItem(r, 0, a)
            self.table.setItem(r, 1, b)
        props = FORM_STATE_PROPS if ctrl is None else [p for p in STATE_PROPS if p in ctrl.props or p == "Opacity"]
        self.prop.clear()
        self.prop.addItems(list(props))
        can = state != BASE and not (ctrl is None and state in AUTO_STATES)
        for w in (self.prop, self.btn_set, self.btn_rm, self.btn_color, self.table):
            w.setEnabled(can)
        self._filling = False

    def _current_value(self, ctrl, prop):
        props = ctrl.props if ctrl is not None else self.view.doc.form.props
        if prop == "Opacity":
            return 1.0
        return props.get(prop, "")

    def _edit(self, fn) -> None:
        doc = self.view.doc
        doc.checkpoint()
        fn()
        doc.set_modified()
        self.bp.refresh()
        self.refresh_overrides()

    def add_override(self) -> None:
        if self.view is None or self.state() == BASE:
            return
        ctrl, prop = self._owner(), self.prop.currentText()
        if not prop:
            return
        value = overrides(self.view.doc.form, ctrl, self.state()).get(prop, self._current_value(ctrl, prop))
        if prop in COLOR_PROPS and not value:
            value = "#3399FF"
        self._edit(lambda: set_override(self.view.doc.form, ctrl, self.state(), prop, value))

    def pick_color(self) -> None:
        if self.view is None or self.state() == BASE:
            return
        prop = self.prop.currentText()
        if prop not in COLOR_PROPS:
            prop = "BackColor"
        ctrl = self._owner()
        cur = overrides(self.view.doc.form, ctrl, self.state()).get(prop) or "#3399FF"
        c = QColorDialog.getColor(QColor(cur), self, f"{prop} in {self.state()}")
        if c.isValid():
            self._edit(lambda: set_override(self.view.doc.form, ctrl, self.state(), prop, c.name()))

    def remove_override(self) -> None:
        if self.view is None:
            return
        r = self.table.currentRow()
        if r < 0:
            return
        prop = self.table.item(r, 0).text()
        ctrl = self._owner()
        self._edit(lambda: remove_override(self.view.doc.form, ctrl, self.state(), prop))

    def _on_value_edited(self, item) -> None:
        if self._filling or self.view is None or item.column() != 1:
            return
        prop = self.table.item(item.row(), 0).text()
        text = item.text()
        try:
            value = json.loads(text) if prop not in ("Text",) + tuple(COLOR_PROPS) else text
        except ValueError:
            value = text
        ctrl = self._owner()
        self._edit(lambda: set_override(self.view.doc.form, ctrl, self.state(), prop, value))

    # ------------------------------------------------------------ custom states
    def add_state(self) -> None:
        if self.view is None:
            return
        form = self.view.doc.form
        taken = set(custom_state_names(form)) | set(AUTO_STATES) | {BASE, "Normal"}
        i = 1
        while f"State{i}" in taken:
            i += 1
        name, ok = QInputDialog.getText(self, "Add State", "Name of the new form state:", text=f"State{i}")
        name = (name or "").strip()
        if not ok or not name:
            return
        if not name.isidentifier() or name in taken:
            QMessageBox.warning(self, "Add State", f"'{name}' is not a valid new state name.")
            return
        self.view.doc.checkpoint()
        form_states(form)[name] = {}
        self.view.doc.set_modified()
        self.bp.state = name
        self.rebuild_states()
        self.bp.refresh()

    def delete_state(self) -> None:
        if self.view is None:
            return
        st = self.state()
        form = self.view.doc.form
        if st == BASE:
            return
        doc = self.view.doc
        doc.checkpoint()
        for c in form.controls:
            c.states.pop(st, None)
        if st not in AUTO_STATES:
            form_states(form).pop(st, None)
        doc.set_modified()
        self.bp.set_state(BASE)
        self.rebuild_states()


def _add_dock(win, title: str, widget, attr: str):
    dock = QDockWidget(title, win)
    dock.setObjectName(title)
    # scrollable: these panels are tall, and their minimum height must not make the main window
    # taller than the screen when they are tabbed in the right column
    from PyQt6.QtWidgets import QFrame, QScrollArea
    sa = QScrollArea()
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setWidgetResizable(True)
    sa.setWidget(widget)
    sa.setMinimumHeight(80)
    dock.setWidget(sa)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    props = getattr(win, "dock_props", None)
    if props is not None:
        win.tabifyDockWidget(props, dock)
        props.raise_()
    setattr(win, attr, dock)
    for a in win.menuBar().actions():
        if a.menu() is not None and a.text().replace("&", "").lower() == "view":
            a.menu().addAction(dock.toggleViewAction())
            break
    return dock


def follow_designer(win, panel) -> None:
    def follow(*_):
        panel.bind(current_view(win))
    win.tabs.currentChanged.connect(follow)
    follow()


def install(win) -> None:
    panel = StatesPanel(win)
    win.states_panel = panel
    _add_dock(win, "States", panel, "dock_states")
    follow_designer(win, panel)
