"""Layout variants in the generated python-tk / python-qt programs (and so in vb-basic and every GUI-Bridge
language, which build their forms with the python-tk generator).

``merge_variants(res, form, toolkit)`` is chained after ``states.python_blend`` and
``databinding_sql.merge_blend`` in ``PythonTkPlugin._blend``: it returns *res* unchanged when the form has
no layout sizes (the generated code then stays byte-identical), else adds

* ``VARIANTS_RT``: the size matching (``model.MATCH_RT``, the designer's own algorithm) and
  ``_RadVariants``, which watches the client area (Tk ``<Configure>`` add="+", a Qt Resize event filter),
  works out which sizes apply, restores the designed values and applies the sizes' overrides in order:
  geometry through each size's Anchor / Dock spec (Tk ``place_configure`` + ``self._places``, Qt
  ``setGeometry`` from the container size, honouring ``_rad_held`` of running storyboards), the other
  properties through ``_RadIO.set`` (states.TK_IO / QT_IO);
* ``self.CurrentSizes`` and ``ApplySizeVariants()``; ``<Form>_SizeVariantChanged()`` is called when the
  matching sizes change.

Foldables are simulated on the desktop with RADIDE_POSTURE (flat | half-opened | folded), RADIDE_SPAN
(single | dual) and RADIDE_HINGE=x,y,w,h (window coordinates; a hinge also gives the fold direction).
"""
from __future__ import annotations

from .model import MATCH_RT, plan

VARIANTS_RT = MATCH_RT + r'''

def _rad_venv():
    """Posture / span / fold of a simulated foldable (RADIDE_POSTURE, RADIDE_SPAN, RADIDE_HINGE=x,y,w,h)."""
    import os
    env = os.environ
    posture = _rad_vposture(env.get("RADIDE_POSTURE", ""))
    span = str(env.get("RADIDE_SPAN", "") or "").strip().lower()
    span = "dual" if span in ("dual", "2", "spanned") else ("single" if span else "")
    hinge, fold = None, ""
    try:
        parts = [int(float(p)) for p in str(env.get("RADIDE_HINGE", "")).split(",") if p.strip()]
        if len(parts) == 4:
            hinge = tuple(parts)
    except ValueError:
        pass
    if hinge is not None and posture != "folded":
        fold = "vertical" if hinge[2] <= hinge[3] else "horizontal"
    if not span:
        span = "dual" if posture == "half-opened" or (hinge is not None and posture != "folded"
                                                      and min(hinge[2], hinge[3]) > 0) else "single"
    return {"posture": posture, "span": span, "hinge": hinge, "fold": fold}


class _RadVariants:
    """Layout variants: the sizes designed with "This size only" follow the window (CSS-like cascade)."""

    def __init__(self, owner, io, plan, form_name, tk=True):
        self.o, self.io, self.plan, self.form_name, self.tk = owner, io, plan, form_name, tk
        self.current = None
        self.env = _rad_venv()
        self.places = {}
        self._hosts = {}
        keys = {}
        for ctl in plan["controls"].values():
            for n, e in ctl.items():
                keys.setdefault(n, set()).update(e.get("props") or {})
        # the designed values, read back from the widgets (restored when a size stops applying)
        self._base_props = {n: {k: io.get(n, k) for k in ks} for n, ks in keys.items()
                            if getattr(owner, n, None) is not None}
        fks = {k for fo in plan["form"].values() for k in fo}
        self._base_form = {k: io.get("", k) for k in fks}
        self.base = {n: tuple(s) for n, s in plan["base"].items() if getattr(owner, n, None) is not None}
        self._attach()
        self.update()

    # ------------------------------------------------------------ toolkit
    def _top(self):
        client = self.o.__dict__.get("_client")
        if client is not None:
            return client
        return self.o.root if self.tk else self.o

    def size(self):
        h = self._top()
        try:
            return (h.winfo_width(), h.winfo_height()) if self.tk else (h.width(), h.height())
        except Exception:  # noqa: BLE001 - the window is being destroyed
            return 0, 0

    def _attach(self):
        if self.tk:
            self._top().bind("<Configure>", self._configured, add="+")
        else:
            self._watch(self._top())

    def _configured(self, e):
        if e.widget is self._top():
            self.update()

    def _watch(self, host):
        if host is None or id(host) in self._hosts:
            return
        self._hosts[id(host)] = _RadVariantEvents(self, host)

    def _place(self, name, spec):
        w = getattr(self.o, name, None)
        if w is None:
            return
        self.places[name] = spec
        x, y, ww, hh, rx, ry, rw, rh = spec
        if self.tk:
            opts = {"x": x, "y": y, "width": ww, "height": hh, "relx": rx, "rely": ry, "relwidth": rw,
                    "relheight": rh}
            self.o._places.setdefault(name, {}).update(opts)
            try:
                if w.winfo_manager() == "place":
                    w.place_configure(**opts)
            except Exception:  # noqa: BLE001
                pass
            return
        host = w.parentWidget()
        self._watch(host)
        for lay in (host.children() if host is not None else []):
            items = getattr(lay, "items", None)
            if type(lay).__name__ == "_Layout" and items:      # Anchor / Dock: this control is ours now
                lay.items = [it for it in items if it[0] is not w]
        self._geo(w, spec)

    def _geo(self, w, spec):
        host = w.parentWidget()
        if host is None:
            return
        cw, ch = host.width(), host.height()
        x, y, ww, hh, rx, ry, rw, rh = spec
        g = [round(x + rx * cw), round(y + ry * ch), max(0, round(ww + rw * cw)), max(0, round(hh + rh * ch))]
        held = getattr(w, "_rad_held", None)        # geometry a visual state / storyboard is animating
        if held:
            for i, (prop, cur) in enumerate((("Left", w.x()), ("Top", w.y()), ("Width", w.width()),
                                             ("Height", w.height()))):
                if prop in held:
                    g[i] = cur
        w.setGeometry(*g)

    def relayout(self, host):
        for name, spec in self.places.items():
            w = getattr(self.o, name, None)
            if w is not None and w.parentWidget() is host:
                self._geo(w, spec)

    # ------------------------------------------------------------ sizes
    def update(self, *_a):
        """Re-checks which sizes apply; True when they changed."""
        w, h = self.size()
        if w <= 1 or h <= 1:                        # not mapped yet: the designed size
            w, h = self.plan["design"]
        e = self.env
        ids = _rad_vmatching(self.plan["sizes"], w, h, None, e["posture"], e["span"], e["fold"])
        if ids == self.current:
            return False
        first = self.current is None
        self.current = ids
        self._apply(ids)
        if not first:
            fn = getattr(self.o, self.form_name + "_SizeVariantChanged", None)
            if fn is not None:
                fn()
        return True

    def _apply(self, ids):
        p = self.plan
        props = {n: dict(v) for n, v in self._base_props.items()}
        places = dict(self.base)
        fprops = dict(self._base_form)
        for vid in ids:
            for n, e in p["controls"].get(vid, {}).items():
                if n in props:
                    props[n].update(e.get("props") or {})
                if e.get("place") is not None and n in places:
                    places[n] = tuple(e["place"])
            fprops.update(p["form"].get(vid) or {})
        io = self.io
        io.quiet = getattr(io, "quiet", 0) + 1      # no "On show" / "On hide" animations for a size change
        try:
            for k, v in fprops.items():
                io.set("", k, v)
            for n, spec in places.items():
                self._place(n, spec)
            for n, pr in props.items():
                for k, v in pr.items():
                    if k != "Visible":
                        io.set(n, k, v)
                if "Visible" in pr:
                    io.set(n, "Visible", pr["Visible"])
        finally:
            io.quiet -= 1
'''

QT_HOST = r'''

class _RadVariantEvents(QObject):
    """Layout variants: a container was resized - re-place the controls of the current sizes."""

    def __init__(self, rv, host):
        super().__init__(host)
        self.rv, self.host = rv, host
        host.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.host and ev.type() == QEvent.Type.Resize:
            if obj is self.rv._top():
                self.rv.update()
            self.rv.relayout(obj)
        return False
'''

VARIANTS_METHODS = [
    "",
    "    # ---------------------------------------------------------------- Layout variants",
    "    @property",
    "    def CurrentSizes(self):",
    "        \"\"\"Ids of the layout sizes that apply to the window now (designed with Edit: This size only).\"\"\"",
    "        return list(self._variants.current or [])",
    "",
    "    def ApplySizeVariants(self):",
    "        \"\"\"Checks again which sizes apply (e.g. after changing RADIDE_POSTURE / RADIDE_SPAN).\"\"\"",
    "        self._variants.env = _rad_venv()",
    "        return self._variants.update()",
]


def python_code(form, toolkit: str) -> dict | None:
    """{"runtime", "init", "after_load", "methods"} for the form's layout sizes, or None."""
    vp = plan(form)
    if vp is None:
        return None
    tk = toolkit == "tk"
    I = "        "
    init = ["", I + "# Layout variants: the sizes designed with \"This size only\" follow the window",
            I + f"self._variants = _RadVariants(self, self._rad, {vp!r}, {form.name!r}, tk={tk!r})"]
    return {"runtime": VARIANTS_RT + ("" if tk else QT_HOST), "init": init, "after_load": [],
            "methods": list(VARIANTS_METHODS)}


def merge_variants(res: dict | None, form, toolkit: str) -> dict | None:
    """Adds the layout-variant code to the Blend code of python_tk / python_qt (``_blend``); COMMON_RT and
    _RadIO are added exactly once, whether or not the earlier steps returned something."""
    try:
        code = python_code(form, toolkit)
    except Exception:  # noqa: BLE001 - broken variant data must never break code generation
        return res
    if code is None:
        return res
    from ..features.states import COMMON_RT, QT_IO, TK_IO
    runtime_before = res["runtime"] if res else ""
    extra = ""
    if "class _RadIO" not in runtime_before:
        if "def _rad_ease" not in runtime_before:
            extra += COMMON_RT
        extra += TK_IO if toolkit == "tk" else QT_IO
    init = list(code["init"])
    if not any("self._rad = _RadIO(self)" in line for line in (res["init"] if res else [])):
        init.insert(2, "        self._rad = _RadIO(self)")
    if res is None:
        return {"runtime": extra + code["runtime"], "init": init, "after_load": [], "methods": code["methods"]}
    return {"runtime": res["runtime"] + extra + code["runtime"], "init": res["init"] + init,
            "after_load": res["after_load"] + code["after_load"], "methods": res["methods"] + code["methods"]}


__all__ = ["VARIANTS_RT", "QT_HOST", "VARIANTS_METHODS", "python_code", "merge_variants"]
