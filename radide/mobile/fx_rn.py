"""Animations, layout sizes and TwoPane of React Native (Expo) screens (plan MOTION_VARIANTS_FOLDABLES, slice D).

Used by codegen_rn.RnFormGen only when a form needs it: the screen imports ``./radfx`` (rn_runtime.RADFX_JS,
written by the Expo plugin next to radapp.js), creates ``this._radFx = new RadFx(this, [...storyboards])`` and
draws animated controls inside ``<FxBox>`` (Animated.View).  Layout sizes: ``render()`` computes the
matching sizes (``radSizes``), places moved controls with ``placeV`` and sets the other properties with
``useSizes``.  TwoPane: ``<TwoPane>`` of radfx.js (Ratio / one pane below 600 dp - no foldable API in Expo Go).
"""
from __future__ import annotations

import json

from ..fxtargets import channels, fx_plan, trigger_of, two_panes, variant_plan
from .codegen_common import color_hex, font_px, truthy

FX_FILE = "radfx.js"


def _jcolor(v):
    h = color_hex(v)
    if not h:
        return None
    a, rgb = h[:2], h[2:]
    return "#" + rgb + ("" if a == "FF" else a)


def _num(v) -> str:
    f = float(v)
    return str(int(f)) if f.is_integer() else repr(round(f, 3))


class RnFx:
    def __init__(self, form):
        self.form = form
        self.plan = fx_plan(form, "rn")
        self.vplan = variant_plan(form)
        self.panes = {tp["name"]: tp for tp in two_panes(form)}
        self.wrapped: set[str] = set()
        if self.plan:
            for sb in self.plan["storyboards"]:
                self.wrapped.add(sb["target"])
            for t in self.plan["triggers"]:
                if t["on"] == "hover":
                    self.wrapped.add(t["source"] or t["target"])
        self._places = None

    @property
    def active(self) -> bool:
        return bool(self.plan or self.vplan or self.panes)

    # ------------------------------------------------------------ JSX
    def place(self, gen, k, style: str) -> str:
        """The control's JSX: inside an FxBox when it is animated (the widget then fills the box)."""
        if self.plan and k.name in self.wrapped:
            return f"<FxBox fx={{this._radFx}} name={json.dumps(k.name)} style={{{style}}}>{gen.widget(k, 'FILL')}</FxBox>"
        return gen.widget(k, style)

    def style(self, name: str, base: tuple, dy: int) -> str | None:
        """placeV(...) when a layout size moves control *name* (base = (x, rx, y, ry, w, rw, h, rh))."""
        if not self.vplan:
            return None
        alts = {}
        for vid, places in self._variant_places(dy).items():
            pl = places.get(name)
            if pl is None:
                continue
            spec = (pl.x, pl.rx, pl.y, pl.ry, pl.w, pl.rw, pl.h, pl.rh)
            if any(abs(a - b) > 0.01 for a, b in zip(spec, base)):
                alts[vid] = spec
        if not alts:
            return None
        arr = lambda s: "[" + ", ".join(_num(x) for x in s) + "]"      # noqa: E731
        return (f"placeV(this, rv, {arr(base)}, {{{', '.join(f'{json.dumps(v)}: {arr(s)}' for v, s in alts.items())}}})")

    def _variant_places(self, dy) -> dict:
        if self._places is not None:
            return self._places
        self._places = {}
        from ..layout import group_places
        from ..variants.model import GEOMETRY, effective_form, overrides, size
        from .codegen_dart import _Proxy
        from .codegen_rn import RnFormGen
        for s in self.vplan["sizes"]:
            vid = s["id"]
            if not any(any(k in overrides(self.form, c, vid) for k in GEOMETRY) for c in self.form.controls) and \
                    not any(k in ("Width", "Height") for k in overrides(self.form, None, vid)):
                continue
            ef = effective_form(self.form, size(self.form, vid), [vid])
            body_kids, edy, fw, design_h = RnFormGen(ef).body_metrics()
            proxies = [_Proxy(k, edy) for k in body_kids]
            places = group_places(proxies, fw, design_h)
            self._places[vid] = {px.ctrl.name: places[id(px)] for px in proxies}
        return self._places

    def two_pane(self, gen, c, style: str) -> str:
        tp = self.panes.get(c.name)
        from .codegen_common import form_children
        kids = form_children(self.form, c.name)[:2]
        if tp is None:
            return f"<R.Unknown form={{this}} c={{this.{c.name}}} style={{{style}}} type=\"TwoPane\" />"
        bc = _jcolor(c.props.get("BackColor"))
        inner = "".join(f"{{this.{k.name}.Visible && {self.place(gen, k, 'FILL')}}}" for k in kids)
        return (f"<TwoPane style={{{style}}} mode={json.dumps(tp['mode'])} ratio={{{_num(tp['ratio'])}}} "
                f"single={json.dumps(tp['single'])}{f' backColor={json.dumps(bc)}' if bc else ''}>{inner}</TwoPane>")

    # ------------------------------------------------------------ class
    def imports(self) -> list[str]:
        if not self.active:
            return []
        names = ["FILL", "FxBox", "RadFx", "TwoPane", "placeV", "radSizes", "useSizes"]
        return ["import { " + ", ".join(names) + " } from './radfx';"]

    def constructor_lines(self) -> list[str]:
        if not self.plan:
            return []
        sbs = [self._sb(sb) for sb in self.plan["storyboards"]]
        respect = "true" if self.plan.get("reduced_motion", True) else "false"
        L = ["    this._radFx = new RadFx(this, ["]
        L += [f"      {json.dumps(s)}," for s in sbs]
        L.append(f"    ], {respect});")
        return L

    def _sb(self, sb) -> dict:
        base = self.form.props if not sb["target"] else self.form.find(sb["target"]).props
        ch = channels(sb, base)
        for k in ("bg", "fg"):
            if k in ch:
                ch[k] = [[ms, v if v in ("start", "parent") else (_jcolor(v) or "start"), e] for ms, v, e in ch[k]]
        t = trigger_of(self.plan, sb["fx"])
        d = {"id": sb["fx"], "target": sb["target"], "duration": int(sb["duration"]), "channels": ch,
             "count": int(sb["count"]), "forever": bool(sb["repeat"]), "autoreverse": bool(sb["autoreverse"]),
             "delay": int(sb.get("delayMs", 0)), "chain": list(sb["chain"]), "trigger": t["on"],
             "source": t.get("source") or "", "interval": int(t.get("intervalMs") or 0),
             "leave": t.get("leave", "reverse")}
        if "bg" in ch or "fg" in ch:
            d["parent"] = _jcolor(self._parent_color(sb["target"])) or "#ffffff"
        return d

    def _parent_color(self, name):
        c = self.form.find(name) if name else None
        p = self.form.find(c.parent) if c is not None and c.parent else None
        while p is not None:
            if p.props.get("BackColor"):
                return p.props["BackColor"]
            p = self.form.find(p.parent) if p.parent else None
        return self.form.props.get("BackColor") or "#FFFBFE"

    def method_lines(self) -> list[str]:
        L: list[str] = []
        if self.vplan:
            sizes = [{"id": s["id"], "when": s["when"]} for s in self.vplan["sizes"]]
            L += [f"  static radSizeList = {json.dumps(sizes)};", "",
                  "  /** The layout sizes that apply now (window width / height, orientation). */",
                  "  get CurrentSizes() { return radSizes(this, this.constructor.radSizeList); }", ""]
        if self.plan:
            L += ["  componentDidMount() { super.componentDidMount(); this._radFx.start(); }", "",
                  "  componentWillUnmount() { this._radFx.stopAll(); super.componentWillUnmount(); }", "",
                  "  // clicks of controls with an \"On click\" animation reach the animations too",
                  "  hasHandler(c, events) { return super.hasHandler(c, events) || this._radFx.wants(c.Name, events); }",
                  "",
                  "  fireAny(c, events, e) {",
                  "    if (events.some((ev) => ev === 'Click' || ev === 'Tap')) this._radFx.event(c.Name, 'click');",
                  "    return super.fireAny(c, events, e);",
                  "  }", "",
                  "  BeginAnimation(id) { this._radFx.begin(id); }", "",
                  "  StopAnimation(id) { this._radFx.stop(id); }", "",
                  "  /** Visible with the On show / On hide animations of the control. */",
                  "  SetVisible(name, on) { this._radFx.setVisible(name, on); }", ""]
        return L

    def render_lines(self) -> list[str]:
        if not self.vplan:
            return []
        return ["    const rv = radSizes(this, this.constructor.radSizeList);",
                f"    useSizes(this, rv, {json.dumps(self._props())});"]

    def _props(self) -> dict:
        from ..variants.model import RUNTIME_PROPS
        out: dict = {}
        for vid, ctl in (self.vplan.get("controls") or {}).items():
            for name, ov in ctl.items():
                c = self.form.find(name)
                if c is None:
                    continue
                for k, v in (ov.get("props") or {}).items():
                    if k not in RUNTIME_PROPS or k == "FontBold":
                        continue
                    conv = {"Visible": truthy, "BackColor": _jcolor, "ForeColor": _jcolor,
                            "FontSize": lambda x: font_px({"FontSize": x})}.get(k, str)
                    base = {"Visible": truthy(c.props.get("Visible", True)), "Text": str(c.props.get("Text", "")),
                            "BackColor": _jcolor(c.props.get("BackColor")), "ForeColor": _jcolor(c.props.get("ForeColor")),
                            "FontSize": font_px(c.props)}.get(k)
                    entry = out.setdefault(name, {}).setdefault(k, [base, {}])
                    entry[1][vid] = conv(v)
        return out

    def screen_back(self, base) -> str | None:
        """backColor of the screen when a size changes the form's BackColor."""
        if not self.vplan:
            return None
        alts = [(vid, _jcolor(ov["BackColor"])) for vid, ov in (self.vplan.get("form") or {}).items()
                if "BackColor" in ov]
        if not alts:
            return None
        out = base or "undefined"
        for vid, col in alts:
            out = f"(rv.includes({json.dumps(vid)}) ? {json.dumps(col)} : {out})"
        return out


__all__ = ["FX_FILE", "RnFx"]
