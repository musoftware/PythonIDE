"""Animations panel for the classic form designer (plan MOTION_VARIANTS_FOLDABLES, slice B).

Presets such as Fade In, Slide In, Bounce, Shake or Typewriter are kept in the .form as
``form.extra["animations"]`` (contract 1.1) and turned into storyboards by ``radide.motion``
(slice A: presets / model / expand). This module is the user interface only:

* an "Animations" dock (tabbed next to Properties) that follows the active designer. It lists the
  animations of the selected control (or of every control) and edits the preset parameters,
  the trigger (load / click / hover / timer / show / hide / after another animation / manual),
  duration, delay, easing, repeat (0 = forever), auto reverse and enabled;
* Preview (one animation) and "Preview all on load" (load-triggered animations plus their
  "after" chains) on the design surface, without changing the model: frames are evaluated here
  and drawn through ``BlendPreview.timeline`` (the same hook as the "Objects and Timeline" dock);
* "Convert to Storyboard" bakes an animation into ``form.extra["storyboards"]`` with absolute keys;
* "Add Animation" in the designer's right-click menu;
* the Error List shows ``motion.model.validate()`` issues and the fallbacks of ``motion.expand``
  (a toolkit that cannot rotate shows a wobble, and so on) - fallbacks are never silent.
"""
from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QPushButton, QSpinBox,
                             QToolButton, QVBoxLayout, QWidget)

from .states import BlendPreview, _add_dock, compact_combo, current_view, section_label, set_note

TRIGGERS = (("load", "On load"), ("click", "On click"), ("hover", "On hover"), ("timer", "On timer"),
            ("show", "On show"), ("hide", "On hide"), ("after", "After animation"),
            ("manual", "Manual (from code)"))
EASINGS = (("linear", "Linear"), ("in", "Ease in"), ("out", "Ease out"), ("inout", "Ease in-out"),
           ("back", "Back (overshoot)"), ("elastic", "Elastic"), ("bounce", "Bounce"), ("sine", "Sine"))
LEAVES = (("reverse", "Reverse"), ("stop", "Stop"), ("none", "Keep"))
GROUPS = ("Entrance", "Exit", "Attention", "Color", "Text")
# shown until radide.motion (slice A) is importable - same ids / labels as its CATALOG
FALLBACK_CATALOG = (("fadeIn", "Fade In", "Entrance"), ("slideIn", "Slide In", "Entrance"),
                    ("scaleIn", "Zoom In", "Entrance"), ("fadeOut", "Fade Out", "Exit"),
                    ("slideOut", "Slide Out", "Exit"), ("scaleOut", "Zoom Out", "Exit"),
                    ("move", "Move", "Attention"), ("bounce", "Bounce", "Attention"),
                    ("shake", "Shake", "Attention"), ("pulse", "Pulse", "Attention"),
                    ("rotate", "Rotate", "Attention"), ("flip", "Flip", "Attention"),
                    ("zoom", "Zoom", "Attention"), ("colorTo", "Color", "Color"),
                    ("typewriter", "Typewriter", "Text"))
PREVIEW_LOOPS = 3          # a "forever" animation is previewed this many times
HOLD_MS = 500              # the last frame stays this long before the designed form comes back
ERR_TAG = "radide-animations"
# display text of preset parameter choices (the stored values stay as they are)
CHOICE_LABELS = {"left": "Left side", "right": "Right side", "top": "Top side", "bottom": "Bottom side",
                 "x": "Horizontal", "y": "Vertical"}
_COLOR_PROPS = ("BackColor", "ForeColor")
_INT_PROPS = ("Left", "Top", "Width", "Height", "FontSize", "Value")


def _tr(text: str) -> str:
    try:
        from ..i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001 - no catalog (tests)
        return text


# ====================================================================== slice A access (defensive)
def _motion():
    """(presets, model, expand) modules of radide.motion, or None while it is not available."""
    try:
        import importlib
        pkg = __name__.rsplit(".", 2)[0] + ".motion"
        # (import_module: radide.motion re-exports the expand() function under the module's name)
        return tuple(importlib.import_module(f"{pkg}.{n}") for n in ("presets", "model", "expand"))
    except Exception:  # noqa: BLE001 - slice A not installed / broken: the panel still opens
        return None


def _attr(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def catalog() -> list[dict]:
    """[{id, label, group, params}] - params = {name: spec} (spec: dict with type/default/choices...)."""
    m = _motion()
    out = []
    if m is not None:
        cat = getattr(m[0], "CATALOG", None) or {}
        items = cat.values() if isinstance(cat, dict) else cat
        for p in items:
            pid = _attr(p, "id")
            if not pid:
                continue
            out.append({"id": str(pid), "label": str(_attr(p, "label") or pid),
                        "group": str(_attr(p, "group") or "Attention"),
                        "params": _norm_schema(_attr(p, "params_schema") or {})})
    if not out:
        out = [{"id": i, "label": lab, "group": g, "params": {}} for i, lab, g in FALLBACK_CATALOG]
    return out


def _norm_schema(schema) -> dict:
    """params_schema in any reasonable shape -> {name: {"type", "default", "choices", "min", "max"}}."""
    out: dict = {}
    if isinstance(schema, dict):
        items = schema.items()
    else:
        items = []
        for s in schema or []:
            if isinstance(s, dict) and s.get("name"):
                items.append((s["name"], s))
            elif isinstance(s, (list, tuple)) and s:
                items.append((s[0], {"type": s[1] if len(s) > 1 else None,
                                     "default": s[2] if len(s) > 2 else None,
                                     "choices": s[3] if len(s) > 3 else None}))
    for name, spec in items:
        if not isinstance(spec, dict):
            if isinstance(spec, (list, tuple)) and spec and all(isinstance(x, str) for x in spec):
                spec = {"type": "choice", "choices": list(spec), "default": spec[0]}
            else:
                spec = {"default": spec}
        spec = dict(spec)
        d = spec.get("default")
        t = spec.get("type")
        if isinstance(t, type):
            t = t.__name__
        if not t:
            t = ("choice" if spec.get("choices") else "bool" if isinstance(d, bool) else "int"
                 if isinstance(d, int) else "float" if isinstance(d, float) else
                 "color" if isinstance(d, str) and d.startswith("#") else "str")
        spec["type"] = str(t)
        out[str(name)] = spec
    return out


def preset_info(pid: str) -> dict | None:
    return next((p for p in catalog() if p["id"] == pid), None)


def preset_label(pid: str) -> str:
    p = preset_info(pid)
    return p["label"] if p else str(pid)


def animations(form) -> list:
    """The form's animation list (created on first use), contract 1.1."""
    lst = form.extra.get("animations")
    if not isinstance(lst, list):
        lst = []
        form.extra["animations"] = lst
    return lst


def find(form, fx_id: str) -> dict | None:
    return next((a for a in form.extra.get("animations") or [] if a.get("id") == fx_id), None)


def _new_id(form) -> str:
    taken = {str(a.get("id")) for a in form.extra.get("animations") or []}
    i = 1
    while f"fx{i}" in taken:
        i += 1
    return f"fx{i}"


def new_animation(form, target: str, preset: str) -> dict:
    """A new animation dict (preset defaults from motion.presets.make when available)."""
    m = _motion()
    anim = None
    if m is not None and callable(getattr(m[0], "make", None)):
        for call in (lambda: m[0].make(preset, target), lambda: m[0].make(preset)):
            try:
                anim = call()
                break
            except TypeError:
                continue
            except Exception:  # noqa: BLE001
                break
    anim = dict(anim) if isinstance(anim, dict) else {}
    info = preset_info(preset) or {"params": {}}
    params = {k: s.get("default") for k, s in info["params"].items() if s.get("default") is not None}
    params.update(anim.get("params") or {})
    base = {"id": _new_id(form), "target": target, "preset": preset, "params": params, "durationMs": 500,
            "delayMs": 0, "easing": "out", "repeat": 1, "autoreverse": False,
            "trigger": {"on": "load"}, "enabled": True}
    base.update({k: v for k, v in anim.items() if k not in ("id", "target", "params")})
    base["id"], base["target"], base["params"] = _new_id(form), target, params
    if not isinstance(base.get("trigger"), dict):
        base["trigger"] = {"on": "load"}
    return base


def describe(anim: dict) -> str:
    """One translated line: "Slide In - 500 ms, On click (Button2), Forever"."""
    trig = anim.get("trigger") if isinstance(anim.get("trigger"), dict) else {}
    on = trig.get("on", "load")
    t = _tr(dict(TRIGGERS).get(on, on))
    if on in ("click", "hover") and trig.get("source") and trig.get("source") != anim.get("target"):
        t += f" ({trig['source']})"
    elif on == "timer":
        t += f" ({trig.get('intervalMs', 0)} ms)"
    elif on == "after":
        t += f" ({trig.get('after') or '?'})"
    rep = anim.get("repeat", 1)
    extra = ", " + _tr("Forever") if rep == 0 else (f", x{rep}" if isinstance(rep, int) and rep > 1 else "")
    off = "" if anim.get("enabled", True) else "  [" + _tr("disabled") + "]"
    return (f"{_tr(preset_label(anim.get('preset', '')))} - {anim.get('durationMs', 500)} ms, {t}{extra}{off}")


def rename_references(form, old: str, new: str) -> None:
    m = _motion()
    if m is not None and callable(getattr(m[1], "rename_references", None)):
        try:
            m[1].rename_references(form, old, new)
            return
        except Exception:  # noqa: BLE001
            pass
    for a in form.extra.get("animations") or []:
        if a.get("target") == old:
            a["target"] = new
        trig = a.get("trigger") or {}
        if trig.get("source") == old:
            trig["source"] = new


def issues(form) -> list[tuple[str, str]]:
    """[(severity, message)] from motion.model.validate and the fallbacks of motion.expand(form, "py")."""
    m = _motion()
    out: list[tuple[str, str]] = []
    if m is None or not form.extra.get("animations"):
        return out
    try:
        for it in m[1].validate(form) or []:
            out.append(_issue(it))
    except Exception as e:  # noqa: BLE001
        out.append(("Warning", f"Animations: {e}"))
    try:
        plan = m[2].expand(form, "py") or {}
        for fb in plan.get("fallbacks") or []:
            if isinstance(fb, (list, tuple)) and len(fb) >= 3:
                out.append(("Warning", f"{fb[0]} ({fb[1] or form.name}): {fb[2]}"))
            else:
                out.append(("Warning", str(fb)))
    except Exception as e:  # noqa: BLE001
        out.append(("Warning", f"Animations: {e}"))
    return out


def _issue(it) -> tuple[str, str]:
    if isinstance(it, dict):
        sev = str(it.get("severity") or it.get("level") or "Warning").capitalize()
        msg = str(it.get("message") or it.get("text") or it)
        fx = it.get("fx") or it.get("id")
        return ("Error" if sev.startswith("E") else "Warning", f"{fx}: {msg}" if fx and str(fx) not in msg else msg)
    if isinstance(it, (list, tuple)) and len(it) == 3 and str(it[0]).lower() not in ("error", "warning"):
        fx, _tgt, msg = (str(x or "") for x in it)          # motion.model.validate: (fx id, target, message)
        msg = msg if fx in msg else f"{fx}: {msg}"
        bad = ("does not exist", "loop", "Unknown", "not a valid", "used twice")
        return ("Error" if any(b in msg for b in bad) else "Warning"), msg
    if isinstance(it, (list, tuple)):
        parts = [str(x) for x in it if x not in (None, "")]
        sev = "Warning"
        if parts and parts[0].lower() in ("error", "warning"):
            sev = parts.pop(0).capitalize()
        return sev, ": ".join(parts)
    return "Warning", str(it)


# ====================================================================== design-time evaluation
def _default_of(prop: str, props: dict):
    v = props.get(prop)
    if prop == "Opacity" and v in (None, ""):
        return 1.0
    if prop in _COLOR_PROPS and not v:
        return "#f0f0f0" if prop == "BackColor" else "#000000"
    if prop == "Visible" and v is None:
        return True
    return v


def resolve(prop: str, value, start, other=None, parent_bg: str = "#f0f0f0"):
    """Relative key values (contract 1.2, motion.presets) against the start value: {"d": delta},
    {"m": factor}, {"of": "Width", "f": 0.5} (start + f * the start value of another property),
    {"reveal": 0..1} (Text) and "$parent" (the parent's background colour).
    other(prop) -> start value of another property of the same control."""
    if value == "$parent":
        return parent_bg or "#f0f0f0"
    if not isinstance(value, dict):
        return value
    if "reveal" in value:
        s = "" if start is None else str(start)
        try:
            r = max(0.0, min(1.0, float(value["reveal"])))
        except (TypeError, ValueError):
            r = 1.0
        return s[:int(round(len(s) * r))]
    if prop in _COLOR_PROPS or isinstance(start, str) and str(start).startswith("#"):
        return start                                   # {"d": 0} on a colour = keep it
    try:
        x = float(start if start not in (None, "") else (1.0 if prop == "Opacity" else 0))
    except (TypeError, ValueError):
        return start
    try:
        if "d" in value:
            v = x + float(value["d"])
        elif "m" in value:
            v = x * float(value["m"])
        elif "of" in value:
            ref = other(str(value["of"])) if callable(other) else 0
            v = x + float(value.get("f", 1)) * float(ref or 0)
        else:
            return start
    except (TypeError, ValueError):
        return start
    if prop == "Opacity":
        v = max(0.0, min(1.0, v))
    return int(round(v)) if prop in _INT_PROPS else v


def _keys(prop: str, keys, start, other=None, parent_bg: str = "#f0f0f0") -> list[tuple]:
    out = []
    for k in keys or []:
        if not isinstance(k, (list, tuple)) or len(k) < 2:
            continue
        try:
            ms = max(0.0, float(k[0]))
        except (TypeError, ValueError):
            continue
        ease = str(k[2]) if len(k) > 2 and k[2] else ""
        out.append((ms, resolve(prop, k[1], start, other, parent_bg), "" if ease == "linear" else ease))
    out.sort(key=lambda x: x[0])
    return out


def _tracks(sb: dict) -> list[tuple]:
    out = []
    for tr in sb.get("tracks") or []:
        if isinstance(tr, dict):
            out.append((str(tr.get("target") or ""), str(tr.get("property") or ""), tr.get("keys") or []))
        elif isinstance(tr, (list, tuple)) and len(tr) >= 3:
            out.append((str(tr[0] or ""), str(tr[1]), tr[2] or []))
    return out


def sb_duration(sb: dict) -> float:
    d = 0.0
    for _t, _p, keys in _tracks(sb):
        for k in keys:
            try:
                d = max(d, float(k[0]))
            except (TypeError, ValueError, IndexError):
                pass
    return d


def sb_count(sb: dict) -> int:
    """How many cycles the preview plays (forever -> PREVIEW_LOOPS)."""
    try:
        n = int(sb.get("count", 0 if sb.get("repeat") else 1))
    except (TypeError, ValueError):
        n = 1
    if sb.get("repeat") and n <= 1:
        n = 0
    return PREVIEW_LOOPS if n <= 0 else n


def sb_span(sb: dict) -> float:
    return sb_duration(sb) * (2 if sb.get("autoreverse") else 1) * sb_count(sb)


def _local_ms(sb: dict, ms: float) -> float:
    dur = sb_duration(sb)
    cyc = dur * (2 if sb.get("autoreverse") else 1)
    if cyc <= 0:
        return 0.0
    total = cyc * sb_count(sb)
    if ms >= total:
        return 0.0 if sb.get("autoreverse") else dur        # the end of the last cycle
    ms %= cyc
    return ms if ms <= dur else cyc - ms


class FxPreview:
    """Frames of a set of fx storyboards, each starting at its own time, evaluated with the generated
    runtime's own maths (``states.DESIGN``) - relative keys resolve against the value when it starts."""

    def __init__(self, form, segments: list[tuple[float, dict]]):
        self.form = form
        self.segments = sorted(segments, key=lambda s: s[0])
        self.length = max([s + sb_span(sb) for s, sb in self.segments] or [0])
        self._starts: list[dict] = []
        for i, (s, _sb) in enumerate(self.segments):
            self._starts.append(self._values(s, upto=i))

    def _base(self, target: str, prop: str):
        if not target:
            return _default_of(prop, self.form.props)
        c = self.form.find(target)
        return _default_of(prop, c.props if c is not None else {})

    def parent_bg(self, target: str) -> str:
        """The background a Tk child fades into ("$parent"): its container's, else the form's."""
        c = self.form.find(target) if target else None
        while c is not None:
            par = self.form.find(c.parent) if c.parent else None
            if par is None:
                break
            if par.props.get("BackColor"):
                return str(par.props["BackColor"])
            c = par
        return str(self.form.props.get("BackColor") or "#f0f0f0")

    def keys_of(self, t: str, p: str, keys, starts: dict) -> tuple[list, object]:
        """(resolved keys, start value) of a track whose storyboard started with *starts*."""
        start = starts.get((t, p), self._base(t, p))
        ks = _keys(p, keys, start, lambda o: starts.get((t, o), self._base(t, o)), self.parent_bg(t))
        return ks, start

    def _values(self, ms: float, upto: int | None = None) -> dict:
        from .states import DESIGN
        from .timeline import _rgb
        vals: dict = {}
        segs = self.segments if upto is None else self.segments[:upto]
        for i, (s, sb) in enumerate(segs):
            if ms < s:
                continue
            starts = self._starts[i] if i < len(self._starts) else {}
            local = _local_ms(sb, ms - s)
            for t, p, keys in _tracks(sb):
                ks, start = self.keys_of(t, p, keys, starts)
                try:
                    vals[(t, p)] = DESIGN["_rad_value_at"](p, ks, local, start, _rgb)
                except Exception:  # noqa: BLE001 - a bad key never breaks the designer
                    pass
        return vals

    def frame(self, ms: float) -> dict:
        """A storyboard dict that BlendPreview draws as-is: one constant key per animated property."""
        return {"name": "_fx_preview",
                "tracks": [{"target": t, "property": p, "keys": [[0, v]]}
                           for (t, p), v in self._values(ms).items() if v is not None]}


def plan(form) -> dict:
    m = _motion()
    if m is None:
        return {}
    return m[2].expand(form, "py") or {}


def _sb_for(pl: dict, fx_id: str) -> dict | None:
    return next((sb for sb in pl.get("storyboards") or [] if sb.get("fx") == fx_id or
                 sb.get("name") == f"_fx_{fx_id}"), None)


def _with_delay(form, fx_id: str, sb: dict) -> float:
    """Delay before the storyboard starts (unless expand already shifted the keys: 'delayMs' on sb)."""
    if "delayMs" in sb:
        try:
            return float(sb["delayMs"])
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def segments_for(form, fx_ids: list[str] | None = None) -> list[tuple[float, dict]]:
    """fx_ids None = 'Preview all on load': load-triggered animations at their start, then the
    animations chained after them ('after' trigger), in order."""
    pl = plan(form)
    if not pl:
        return []
    if fx_ids is not None:
        out = []
        for fid in fx_ids:
            sb = _sb_for(pl, fid)
            if sb is not None:
                out.append((_with_delay(form, fid, sb), sb))
        return out
    trig = {t.get("fx"): t for t in pl.get("triggers") or []}
    starts: dict[str, float] = {}
    sbs = {sb.get("fx") or str(sb.get("name", ""))[4:]: sb for sb in pl.get("storyboards") or []}
    for fid, sb in sbs.items():
        t = trig.get(fid)
        if (t is None and sb.get("autostart")) or (t is not None and t.get("on") == "load"):
            starts[fid] = _with_delay(form, fid, sb)
    for _ in range(len(sbs)):                       # chains: after the previous one ends
        grew = False
        for fid, sb in sbs.items():
            t = trig.get(fid) or {}
            prev = t.get("after")
            if fid in starts or t.get("on") != "after" or prev not in starts:
                continue
            starts[fid] = starts[prev] + sb_span(sbs[prev]) + _with_delay(form, fid, sb)
            grew = True
        if not grew:
            break
    return [(starts[f], sbs[f]) for f in starts]


def bake(form, fx_id: str) -> dict | None:
    """Storyboard dict with absolute keys (relative values resolved against the designed values,
    repeat counts unrolled) for "Convert to Storyboard"."""
    pl = plan(form)
    sb = _sb_for(pl, fx_id) if pl else None
    if sb is None:
        return None
    anim = find(form, fx_id) or {}
    pv = FxPreview(form, [])
    delay = _with_delay(form, fx_id, sb)
    try:
        n = int(sb.get("count", 0 if sb.get("repeat") else 1))
    except (TypeError, ValueError):
        n = 1
    forever = bool(sb.get("repeat")) and n <= 1 or n <= 0
    rev = bool(sb.get("autoreverse"))
    dur = sb_duration(sb)
    cycles = 1 if forever else max(1, n)
    tracks = []
    for t, p, keys in _tracks(sb):
        ks, _start = pv.keys_of(t, p, keys, {})
        if not ks:
            continue
        one = [[k[0], k[1], k[2]] for k in ks]
        if rev and not forever:
            one += [[2 * dur - k[0], k[1], ks[i + 1][2] if i + 1 < len(ks) else ""]
                    for i, k in reversed(list(enumerate(ks))) if 2 * dur - k[0] > dur]
        cyc = dur * (2 if rev and not forever else 1)
        out = []
        for c in range(cycles):
            for k in one:
                ms = int(round(delay + c * cyc + k[0]))
                if out and out[-1][0] == ms:
                    out[-1] = [ms, k[1]] + ([k[2]] if k[2] else [])
                else:
                    out.append([ms, k[1]] + ([k[2]] if k[2] else []))
        if delay > 0 and out and out[0][0] > 0:
            out.insert(0, [0, ks[0][1]])
        tracks.append({"target": t, "property": p, "keys": out})
    trig = (anim.get("trigger") or {}).get("on", "load")
    return {"name": "", "autostart": trig == "load", "repeat": forever, "autoreverse": rev and forever,
            "tracks": tracks}


# ====================================================================== panel
class AnimationsPanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.view = None
        self._filling = False
        self._editing = False
        self._last_cp = None            # (fx id, field) of the last undo checkpoint (typing coalesces)
        self._pv: FxPreview | None = None
        self._pv_t0 = 0.0
        self._pv_name = ""
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.hold = QTimer(self)
        self.hold.setSingleShot(True)
        self.hold.timeout.connect(self.stop_preview)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setProperty("radRole", "note")
        lay.addWidget(self.note)
        self.note.hide()
        self.caption = section_label("Animations")
        lay.addWidget(self.caption)
        self.all = QCheckBox("Show all controls")
        self.all.setToolTip("List the animations of every control instead of only the selected one")
        self.all.toggled.connect(self.refresh_list)
        lay.addWidget(self.all)
        self.list = QListWidget()
        self.list.setProperty("i18n_skip_items", True)
        self.list.setMaximumHeight(150)
        self.list.currentItemChanged.connect(self._on_current)
        self.list.itemChanged.connect(self._on_item_checked)
        lay.addWidget(self.list)
        row = QHBoxLayout()
        self.btn_add = QToolButton(text="Add Animation")
        self.btn_add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.add_menu = QMenu(self.btn_add)
        self.add_menu.aboutToShow.connect(lambda: self.fill_add_menu(self.add_menu, None))
        self.btn_add.setMenu(self.add_menu)
        self.btn_del = QToolButton(text="Delete")
        self.btn_del.clicked.connect(self.delete_current)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_del)
        row.addStretch(1)
        lay.addLayout(row)

        self.editor = QWidget()
        fl = QFormLayout(self.editor)
        fl.setContentsMargins(0, 0, 0, 0)
        self.preset = compact_combo(QComboBox())
        self.preset.setToolTip("Animation preset")
        self.preset.currentIndexChanged.connect(self._on_preset)
        fl.addRow("Preset:", self.preset)
        self.params_box = QWidget()
        self.params_form = QFormLayout(self.params_box)
        self.params_form.setContentsMargins(0, 0, 0, 0)
        fl.addRow(self.params_box)
        self.trigger = compact_combo(QComboBox())
        for key, text in TRIGGERS:
            self.trigger.addItem(text, key)
        self.trigger.currentIndexChanged.connect(lambda *_: self._set_trigger("on", self.trigger.currentData()))
        fl.addRow("Trigger:", self.trigger)
        self.source = compact_combo(QComboBox())
        self.source.setToolTip("Control whose event starts the animation (default = the animated control)")
        self.source.currentIndexChanged.connect(lambda *_: self._set_trigger("source", self.source.currentData()))
        self.lab_source = QLabel("Source:")
        fl.addRow(self.lab_source, self.source)
        self.interval = QSpinBox()
        self.interval.setRange(50, 3600000)
        self.interval.setSingleStep(250)
        self.interval.setSuffix(" ms")
        self.interval.valueChanged.connect(lambda v: self._set_trigger("intervalMs", int(v)))
        self.lab_interval = QLabel("Interval:")
        fl.addRow(self.lab_interval, self.interval)
        self.after = compact_combo(QComboBox())
        self.after.currentIndexChanged.connect(lambda *_: self._set_trigger("after", self.after.currentData()))
        self.lab_after = QLabel("After:")
        fl.addRow(self.lab_after, self.after)
        self.leave = compact_combo(QComboBox())
        for key, text in LEAVES:
            self.leave.addItem(text, key)
        self.leave.setToolTip("What happens when the mouse leaves the control")
        self.leave.currentIndexChanged.connect(lambda *_: self._set_trigger("leave", self.leave.currentData()))
        self.lab_leave = QLabel("On leave:")
        fl.addRow(self.lab_leave, self.leave)
        self.duration = QSpinBox()
        self.duration.setRange(1, 600000)
        self.duration.setSingleStep(50)
        self.duration.valueChanged.connect(lambda v: self._set("durationMs", int(v)))
        fl.addRow("Duration (ms):", self.duration)
        self.delay = QSpinBox()
        self.delay.setRange(0, 600000)
        self.delay.setSingleStep(50)
        self.delay.valueChanged.connect(lambda v: self._set("delayMs", int(v)))
        fl.addRow("Delay (ms):", self.delay)
        self.easing = compact_combo(QComboBox())
        for key, text in EASINGS:
            self.easing.addItem(text, key)
        self.easing.currentIndexChanged.connect(lambda *_: self._set("easing", self.easing.currentData()))
        fl.addRow("Easing:", self.easing)
        self.repeat = QSpinBox()
        self.repeat.setRange(0, 1000)
        self.repeat.setSpecialValueText("Forever")
        self.repeat.setToolTip("How many times it plays (0 = Forever)")
        self.repeat.valueChanged.connect(lambda v: self._set("repeat", int(v)))
        fl.addRow("Repeat:", self.repeat)
        self.autoreverse = QCheckBox("Auto reverse")
        self.autoreverse.toggled.connect(lambda on: self._set("autoreverse", bool(on)))
        self.enabled = QCheckBox("Enabled")
        self.enabled.toggled.connect(lambda on: self._set("enabled", bool(on)))
        r2 = QHBoxLayout()
        r2.addWidget(self.autoreverse)
        r2.addWidget(self.enabled)
        r2.addStretch(1)
        fl.addRow(r2)
        lay.addWidget(self.editor)

        r3 = QHBoxLayout()
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setToolTip("Play the selected animation on the design surface (the form is not changed)")
        self.btn_preview.clicked.connect(self.preview_current)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop_preview)
        r3.addWidget(self.btn_preview)
        r3.addWidget(self.btn_stop)
        r3.addStretch(1)
        lay.addLayout(r3)
        self.btn_all = QPushButton("Preview all on load")
        self.btn_all.setToolTip("Play what happens when the form loads: load animations and the ones "
                                "chained after them")
        self.btn_all.clicked.connect(self.preview_all)
        lay.addWidget(self.btn_all)
        self.btn_bake = QPushButton("Convert to Storyboard")
        self.btn_bake.setToolTip("Turn the selected animation into a storyboard with keyframes "
                                 "(Objects and Timeline) that you can edit key by key")
        self.btn_bake.clicked.connect(self.convert_current)
        lay.addWidget(self.btn_bake)
        self.reduced = QCheckBox("Respect reduced motion")
        self.reduced.setToolTip("When the user turned animations off in the operating system, "
                                "animations jump to their end")
        self.reduced.toggled.connect(self._on_reduced)
        lay.addWidget(self.reduced)
        lay.addStretch(1)
        self.bind(None)

    def changeEvent(self, ev):  # noqa: N802 - Qt API
        """The IDE language changed: the list / combos hold translated text made here - rebuild them."""
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.LanguageChange:
            QTimer.singleShot(0, self.refresh_list)
        super().changeEvent(ev)

    # ------------------------------------------------------------ binding
    def bind(self, view) -> None:
        if view is self.view and view is not None:
            return
        self.stop_preview()
        if self.view is not None:
            try:
                self.view.doc.selectionChanged.disconnect(self._on_selection)
                self.view.doc.structureChanged.disconnect(self._on_structure)
                self.view.doc.undoStateChanged.disconnect(self._on_structure)
            except (TypeError, RuntimeError):
                pass
        self.view = view
        if view is not None:
            doc = view.doc
            doc.selectionChanged.connect(self._on_selection)
            doc.structureChanged.connect(self._on_structure)
            doc.undoStateChanged.connect(self._on_structure)
            if not getattr(doc, "_fx_rename_hooked", False):
                doc._fx_rename_hooked = True
                doc.renamed.connect(lambda old, new, d=doc: rename_references(d.form, old, new))
        self.refresh_list()
        self.update_errors()

    @property
    def form(self):
        return self.view.doc.form if self.view is not None else None

    def _alive(self) -> bool:
        if self.view is None:
            return False
        try:
            self.view.isVisible()
            return True
        except RuntimeError:            # the designer was closed
            self.view = None
            return False

    def _on_selection(self, *_a) -> None:
        if not self.all.isChecked():
            self.refresh_list()

    def _on_structure(self, *_a) -> None:
        if self._editing:
            return
        self._last_cp = None
        self.refresh_list()
        self.update_errors()

    # ------------------------------------------------------------ list
    def _target_name(self) -> str:
        sel = self.view.doc.selected if self.view is not None else None
        return sel.name if sel is not None else ""

    def _shown(self) -> list[dict]:
        if self.form is None:
            return []
        lst = self.form.extra.get("animations") or []
        if self.all.isChecked():
            return list(lst)
        t = self._target_name()
        return [a for a in lst if str(a.get("target") or "") == t]

    def refresh_list(self, *_a, select: str | None = None) -> None:
        self._filling = True
        try:
            cur = select or self.current_id()
            self.list.clear()
            on = self.form is not None
            for w in (self.list, self.btn_add, self.all, self.reduced, self.btn_all):
                w.setEnabled(on)
            if not on:
                set_note(self.note, "Open a form designer to add animations to its controls.")
                self.caption.setText("Animations")
                self._fill_editor(None)
                return
            if _motion() is None:
                set_note(self.note, "The animation engine (radide.motion) is not available: "
                                    "animations can be edited but not previewed.")
            else:
                set_note(self.note, "")
            t = self._target_name()
            if self.all.isChecked():
                self.caption.setText(f"Animations of {self.form.name}")      # (setText translates)
            else:
                self.caption.setText(f"Animations of {t or self.form.name + ' (form)'}")
            for a in self._shown():
                who = a.get("target") or self.form.name
                text = f"{who}: {describe(a)}" if self.all.isChecked() else describe(a)
                it = QListWidgetItem(f"{a.get('id')}  {text}")
                it.setData(Qt.ItemDataRole.UserRole, a.get("id"))
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked if a.get("enabled", True) else Qt.CheckState.Unchecked)
                it.setToolTip(_tr("Tick to enable, untick to disable"))
                self.list.addItem(it)
                if a.get("id") == cur:
                    self.list.setCurrentItem(it)
            if self.list.currentItem() is None and self.list.count():
                self.list.setCurrentRow(0)
            mo = self.form.extra.get("motion") or {}
            self.reduced.setChecked(bool(mo.get("respectReducedMotion", True)))
        finally:
            self._filling = False
        self._fill_editor(find(self.form, self.current_id()) if self.form is not None else None)

    def current_id(self) -> str | None:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else None

    def current(self) -> dict | None:
        fid = self.current_id()
        return find(self.form, fid) if fid and self.form is not None else None

    def select(self, fx_id: str) -> None:
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == fx_id:
                self.list.setCurrentRow(i)
                return

    def _on_current(self, *_a) -> None:
        if not self._filling:
            self._fill_editor(self.current())

    def _on_item_checked(self, it) -> None:
        if self._filling or self.form is None:
            return
        a = find(self.form, it.data(Qt.ItemDataRole.UserRole))
        if a is None:
            return
        on = it.checkState() == Qt.CheckState.Checked
        if bool(a.get("enabled", True)) != on:
            self._edit(lambda: a.__setitem__("enabled", on), refresh=False)
            if a is self.current():
                self._filling = True
                self.enabled.setChecked(on)
                self._filling = False

    # ------------------------------------------------------------ editor
    def _fill_editor(self, a: dict | None) -> None:
        self._filling = True
        try:
            has = a is not None
            for w in (self.editor, self.btn_del, self.btn_preview, self.btn_bake):
                w.setEnabled(has)
            self.btn_stop.setEnabled(self._pv is not None)
            for cb, items in ((self.trigger, TRIGGERS), (self.easing, EASINGS), (self.leave, LEAVES)):
                cb.clear()                      # (rebuilt: the IDE language may have changed)
                for key, text in items:
                    cb.addItem(_tr(text), key)
            self.preset.clear()
            for p in catalog():
                self.preset.addItem(f"{_tr(p['label'])}  ({_tr(p['group'])})", p["id"])
            self._clear_params()
            if not has:
                return
            i = self.preset.findData(a.get("preset"))
            if i < 0:
                self.preset.addItem(str(a.get("preset")), a.get("preset"))
                i = self.preset.count() - 1
            self.preset.setCurrentIndex(i)
            self._build_params(a)
            trig = a.get("trigger") or {}
            on = trig.get("on", "load")
            self._set_combo(self.trigger, on)
            self.source.clear()
            self.source.addItem(_tr("(the animated control)"), "")
            for c in self.form.visual():
                self.source.addItem(c.name, c.name)
            self._set_combo(self.source, trig.get("source") or "")
            self.interval.setValue(int(trig.get("intervalMs") or 3000))
            self.after.clear()
            self.after.addItem("", None)
            for o in self.form.extra.get("animations") or []:
                if o is not a:
                    self.after.addItem(f"{o.get('id')}  {o.get('target') or self.form.name}: "
                                       f"{_tr(preset_label(o.get('preset', '')))}", o.get("id"))
            self._set_combo(self.after, trig.get("after"))
            self._set_combo(self.leave, trig.get("leave") or "reverse")
            self.duration.setValue(int(a.get("durationMs") or 500))
            self.delay.setValue(int(a.get("delayMs") or 0))
            self._set_combo(self.easing, a.get("easing") or "out")
            self.repeat.setValue(int(a.get("repeat", 1) if a.get("repeat") is not None else 1))
            self.autoreverse.setChecked(bool(a.get("autoreverse")))
            self.enabled.setChecked(bool(a.get("enabled", True)))
            self._trigger_rows(on)
        finally:
            self._filling = False

    @staticmethod
    def _set_combo(cb: QComboBox, data) -> None:
        i = cb.findData(data)
        cb.setCurrentIndex(max(0, i))

    def _trigger_rows(self, on: str) -> None:
        for lab, w, show in ((self.lab_source, self.source, on in ("click", "hover")),
                             (self.lab_interval, self.interval, on == "timer"),
                             (self.lab_after, self.after, on == "after"),
                             (self.lab_leave, self.leave, on == "hover")):
            lab.setVisible(show)
            w.setVisible(show)

    def _clear_params(self) -> None:
        while self.params_form.rowCount():
            self.params_form.removeRow(0)
        self.params_box.hide()

    def _build_params(self, a: dict) -> None:
        info = preset_info(a.get("preset", "")) or {"params": {}}
        params = a.get("params") or {}
        for name, spec in info["params"].items():
            v = params.get(name, spec.get("default"))
            t = spec.get("type", "str")
            label = str(spec.get("label") or name[:1].upper() + name[1:])
            if spec.get("choices") or t == "choice":
                w = compact_combo(QComboBox())
                for ch in spec.get("choices") or []:
                    if isinstance(ch, (list, tuple)):
                        w.addItem(str(ch[1] if len(ch) > 1 else ch[0]), ch[0])
                    else:
                        w.addItem(_tr(CHOICE_LABELS.get(str(ch), str(ch))), ch)
                self._set_combo(w, v)
                w.currentIndexChanged.connect(lambda *_, n=name, w=w: self._set_param(n, w.currentData()))
            elif t in ("bool", "boolean"):
                w = QCheckBox()
                w.setChecked(bool(v))
                w.toggled.connect(lambda on, n=name: self._set_param(n, bool(on)))
            elif t in ("int", "integer"):
                w = QSpinBox()
                w.setRange(int(spec.get("min", -10000)), int(spec.get("max", 10000)))
                w.setValue(int(v or 0))
                w.valueChanged.connect(lambda x, n=name: self._set_param(n, int(x)))
            elif t in ("float", "number"):
                w = QDoubleSpinBox()
                w.setDecimals(2)
                w.setSingleStep(float(spec.get("step", 0.05)))
                w.setRange(float(spec.get("min", -10000)), float(spec.get("max", 10000)))
                w.setValue(float(v or 0))
                w.valueChanged.connect(lambda x, n=name: self._set_param(n, float(x)))
            elif t in ("color", "colour"):
                w = QPushButton(str(v or "#3399FF"))
                w.setStyleSheet(f"background:{v or '#3399FF'}")
                w.clicked.connect(lambda _c=False, n=name, w=w: self._pick_color(n, w))
            else:
                w = QLineEdit(str(v if v is not None else ""))
                w.editingFinished.connect(lambda n=name, w=w: self._set_param(n, w.text()))
            w.setObjectName(f"fxparam_{name}")
            self.params_form.addRow(label + ":", w)
        self.params_box.setVisible(self.params_form.rowCount() > 0)

    def _pick_color(self, name: str, btn) -> None:
        a = self.current()
        if a is None:
            return
        c = QColorDialog.getColor(QColor(str((a.get("params") or {}).get(name) or "#3399FF")), self, name)
        if c.isValid():
            btn.setText(c.name())
            btn.setStyleSheet(f"background:{c.name()}")
            self._set_param(name, c.name())

    # ------------------------------------------------------------ edits
    def _edit(self, fn, key=None, refresh: bool = True) -> None:
        if self.view is None:
            return
        doc = self.view.doc
        self._editing = True            # (checkpoint / set_modified signals must not rebuild the editor
        try:                            #  under the widget that is sending the edit)
            if key is None or key != self._last_cp:
                doc.checkpoint()
            self._last_cp = key
            fn()
            doc.set_modified()
        finally:
            self._editing = False
        if refresh:
            self._refresh_item_text()
        self.update_errors()

    def _refresh_item_text(self) -> None:
        a = self.current()
        it = self.list.currentItem()
        if a is None or it is None:
            return
        who = a.get("target") or self.form.name
        text = f"{who}: {describe(a)}" if self.all.isChecked() else describe(a)
        self._filling = True
        it.setText(f"{a.get('id')}  {text}")
        self._filling = False

    def _set(self, key: str, value) -> None:
        a = self.current()
        if self._filling or a is None or a.get(key) == value:
            return
        self._edit(lambda: a.__setitem__(key, value), key=(a.get("id"), key))
        if key == "enabled":
            it = self.list.currentItem()
            if it is not None:
                self._filling = True
                it.setCheckState(Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)
                self._filling = False

    def _set_param(self, name: str, value) -> None:
        a = self.current()
        if self._filling or a is None:
            return
        params = a.setdefault("params", {})
        if params.get(name) == value:
            return
        self._edit(lambda: params.__setitem__(name, value), key=(a.get("id"), "p:" + name))

    def _set_trigger(self, key: str, value) -> None:
        a = self.current()
        if self._filling or a is None:
            return
        trig = a.get("trigger")
        if not isinstance(trig, dict):
            trig = a["trigger"] = {"on": "load"}

        def do():
            if value in (None, "") and key != "on":
                trig.pop(key, None)
            else:
                trig[key] = value
        if trig.get(key) == value:
            return
        self._edit(do, key=(a.get("id"), "t:" + key))
        if key == "on":
            self._trigger_rows(str(value))

    def _on_preset(self, *_a) -> None:
        a = self.current()
        if self._filling or a is None:
            return
        pid = self.preset.currentData()
        if not pid or pid == a.get("preset"):
            return
        info = preset_info(pid) or {"params": {}}

        def do():
            a["preset"] = pid
            a["params"] = {k: s.get("default") for k, s in info["params"].items() if s.get("default") is not None}
        self._edit(do)
        self._filling = True
        self._clear_params()
        self._build_params(a)
        self._filling = False

    def _on_reduced(self, on: bool) -> None:
        if self._filling or self.form is None:
            return
        mo = self.form.extra.get("motion")
        if not isinstance(mo, dict):
            mo = {}
        if bool(mo.get("respectReducedMotion", True)) == bool(on):
            return

        def do():
            mo["respectReducedMotion"] = bool(on)
            self.form.extra["motion"] = mo
        self._edit(do, refresh=False)

    def add(self, preset: str, target: str | None = None) -> dict | None:
        """Add an animation of *preset* to *target* (None = the selected control, "" = the form)."""
        if self.form is None:
            return None
        if target is None:
            target = self._target_name()
        anim = new_animation(self.form, target, preset)
        self._edit(lambda: animations(self.form).append(anim), refresh=False)
        if not self.all.isChecked() and target != self._target_name():
            self.all.setChecked(True)
        self.refresh_list(select=anim["id"])
        return anim

    def delete_current(self) -> None:
        a = self.current()
        if a is None:
            return
        fid = a.get("id")

        def do():
            lst = animations(self.form)
            lst[:] = [x for x in lst if x is not a]
            for o in lst:                       # chains that pointed at it start on load instead
                trig = o.get("trigger") or {}
                if trig.get("on") == "after" and trig.get("after") == fid:
                    trig.pop("after", None)
        self._edit(do, refresh=False)
        self.refresh_list()

    def fill_add_menu(self, menu: QMenu, target: str | None) -> None:
        menu.clear()
        cat = catalog()
        groups = list(GROUPS) + sorted({p["group"] for p in cat} - set(GROUPS))
        for g in groups:
            items = [p for p in cat if p["group"] == g]
            if not items:
                continue
            sub = menu.addMenu(g)
            for p in items:
                sub.addAction(p["label"], lambda pid=p["id"]: self.add(pid, target))

    # ------------------------------------------------------------ Error List
    def update_errors(self) -> None:
        el = getattr(self.win, "error_list", None)
        if el is None:
            return
        try:
            from PyQt6.QtWidgets import QTreeWidgetItem
            for i in reversed(range(el.topLevelItemCount())):
                if el.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == ERR_TAG:
                    el.takeTopLevelItem(i)
            if self.form is None:
                return
            fname = f"{self.form.name}.form"
            try:
                fname = self.view.doc.path.name
            except AttributeError:
                pass
            for sev, msg in issues(self.form):
                it = QTreeWidgetItem([sev, f"{_tr('Animations')}: {msg}", fname, "1"])
                it.setData(0, Qt.ItemDataRole.UserRole, ERR_TAG)
                it.setForeground(0, Qt.GlobalColor.darkRed if sev == "Error" else Qt.GlobalColor.darkYellow)
                el.addTopLevelItem(it)
        except RuntimeError:
            pass

    # ------------------------------------------------------------ preview
    def preview_current(self) -> None:
        a = self.current()
        if a is None:
            return
        self._start(segments_for(self.form, [a["id"]]), describe(a))

    def preview_all(self) -> None:
        if self.form is None:
            return
        self._start(segments_for(self.form, None), _tr("all on load"))

    def _start(self, segs: list, name: str) -> None:
        self.stop_preview()
        if not self._alive():
            return
        if _motion() is None:
            set_note(self.note, "The animation engine (radide.motion) is not available.")
            return
        if not segs:
            set_note(self.note, "Nothing to preview: add an enabled animation (Preview all on load plays "
                                "the ones triggered on load and the ones chained after them).")
            return
        tp = getattr(self.win, "timeline_panel", None)          # one player at a time
        if tp is not None:
            try:
                if getattr(tp, "playing", False):
                    tp.stop()
                if tp.rec.isChecked():
                    tp.rec.setChecked(False)
            except (AttributeError, RuntimeError):
                pass
        self._pv = FxPreview(self.form, segs)
        self._pv_name = name
        self._pv_t0 = time.monotonic()
        bp = BlendPreview.of(self.view)
        bp.timeline_release = self.stop_preview
        self._lock(True)
        self.btn_stop.setEnabled(True)
        self.timer.start()
        self._tick()

    def _tick(self) -> None:
        if self._pv is None or not self._alive():
            self.timer.stop()
            self._pv = None
            return
        ms = (time.monotonic() - self._pv_t0) * 1000.0
        done = ms >= self._pv.length
        ms = min(ms, self._pv.length)
        self.show_frame(ms)
        if done:
            self.timer.stop()
            self.hold.start(HOLD_MS)

    def show_frame(self, ms: float) -> None:
        """Draw the preview at *ms* (also used by the tests)."""
        if self._pv is None or not self._alive():
            return
        from .timeline import RecordBanner
        bp = BlendPreview.of(self.view)
        bp.timeline = (self._pv.frame(ms), 0)
        try:
            bp.refresh()
            RecordBanner.of(self.view).set_mode(
                "play", _tr("▶ Previewing {} - Stop puts the controls back").format(self._pv_name))
        except RuntimeError:
            self.view = None

    def stop_preview(self) -> None:
        self.timer.stop()
        self.hold.stop()
        was = self._pv is not None
        self._pv = None
        self.btn_stop.setEnabled(False)
        if not was or not self._alive():
            return
        from .timeline import RecordBanner
        bp = getattr(self.view, "_blend_preview", None)
        if bp is not None:
            bp.timeline = None
            if getattr(bp, "timeline_release", None) == self.stop_preview:
                bp.timeline_release = None
            try:
                bp.refresh()
            except RuntimeError:
                pass
        b = RecordBanner.of(self.view, create=False)
        if b is not None:
            b.set_mode("")
        self._lock(False)

    @property
    def previewing(self) -> bool:
        return self._pv is not None

    def _lock(self, on: bool) -> None:
        try:
            self.view.overlay.setEnabled(not on)
        except (AttributeError, RuntimeError):
            pass
        dock = getattr(self.win, "dock_props", None)
        if dock is not None and dock.widget() is not None:
            dock.widget().setEnabled(not on)
        self.editor.setEnabled(not on and self.current() is not None)

    # ------------------------------------------------------------ bake
    def convert_current(self) -> None:
        a = self.current()
        if a is None or self.form is None:
            return
        if _motion() is None:
            set_note(self.note, "The animation engine (radide.motion) is not available.")
            return
        sb = bake(self.form, a["id"])
        if sb is None or not sb["tracks"]:
            set_note(self.note, "This animation has nothing to convert (disabled or no animated property).")
            return
        from .timeline import storyboards
        taken = {s.get("name") for s in storyboards(self.form)} | {c.name for c in self.form.controls}
        stem = "".join(ch for ch in preset_label(a.get("preset", "")).title() if ch.isalnum()) or "Fx"
        stem += str(a.get("target") or "Form")
        name, i = stem, 2
        while name in taken:
            name, i = f"{stem}{i}", i + 1
        sb["name"] = name
        fid = a.get("id")

        def do():
            self.form.extra.setdefault("storyboards", []).append(sb)
            lst = animations(self.form)
            lst[:] = [x for x in lst if x.get("id") != fid]
        self._edit(do, refresh=False)
        self.refresh_list()
        tp = getattr(self.win, "timeline_panel", None)
        if tp is not None:
            try:
                tp.rebuild()
            except Exception:  # noqa: BLE001
                pass
        set_note(self.note, f"Converted to storyboard {name} (Objects and Timeline).")


# ====================================================================== install
def install(win) -> None:
    panel = AnimationsPanel(win)
    win.animations_panel = panel
    _add_dock(win, "Animations", panel, "dock_animations")

    def follow(*_):
        try:
            panel.bind(current_view(win))
        except RuntimeError:
            pass
    win.tabs.currentChanged.connect(follow)
    follow()

    orig_open = win.open_designer

    def open_designer(name, *a, **kw):
        r = orig_open(name, *a, **kw)
        follow()
        return r
    win.open_designer = open_designer

    def designer_menu(form_name, m, c, _orig=win._designer_menu):
        _orig(form_name, m, c)
        try:
            if c is not None and c.ctype.nonvisual:
                return
            sub = QMenu("Add Animation", m)
            target = c.name if c is not None else ""

            def fill():
                follow()
                panel.fill_add_menu(sub, target)
                for act in sub.findChildren(QMenu):
                    for x in act.actions():
                        x.triggered.connect(lambda *_: _show_dock(win))
            sub.aboutToShow.connect(fill)
            m.addSeparator()
            m.addMenu(sub)
        except Exception as e:  # noqa: BLE001 - never break the designer menu
            win.log(f"[animations] {e}")
    win._designer_menu = designer_menu


def _show_dock(win) -> None:
    dock = getattr(win, "dock_animations", None)
    if dock is not None:
        dock.show()
        dock.raise_()


__all__ = ["AnimationsPanel", "FxPreview", "bake", "catalog", "install", "segments_for"]
