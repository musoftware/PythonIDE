"""Animations, layout sizes and TwoPane of classic Flutter forms (plan MOTION_VARIANTS_FOLDABLES, slice D).

Used by codegen_dart.DartFormGen only when a form has animations (``lib/radmotion.dart``: RadMotion /
RadSb, keyframes are F's ``RadKey`` from ``lib/radfx.dart``), layout sizes or a TwoPane (F's
``lib/radlayout.dart``: RadVariant / RadSize / RadV / RadTwoPane).  The designer is a ``part`` of the user
library, so those files are exported by ``lib/radapp.dart`` (see :func:`radapp_exports`).
"""
from __future__ import annotations

from pathlib import Path

from ..fxtargets import channels, fx_plan, trigger_of, two_panes, variant_plan, when_tuple
from .codegen_common import color_hex, font_px, form_children, to_int, truthy

DART_DIR = Path(__file__).resolve().parent / "dart"
FD_DART = Path(__file__).resolve().parent.parent / "flutterdesign" / "dart"
CURVES = {"in": "Curves.easeIn", "out": "Curves.easeOut", "inout": "Curves.easeInOut", "back": "RadEase.back",
          "elastic": "RadEase.elastic", "bounce": "RadEase.bounce", "sine": "RadEase.sine"}
VARIANT_GEOMETRY = ("Left", "Top", "Width", "Height")


def _dnum(v) -> str:
    f = float(v)
    return str(int(f)) if f.is_integer() else repr(round(f, 4))


def _dstr(s) -> str:
    s = str(s).replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$").replace("\n", "\\n")
    return f"'{s}'"


def _dcolor(v) -> str:
    h = color_hex(v)
    return f"Color(0x{h})" if h else "null"


class DartFx:
    """What the generator needs to know about a form's motion / sizes / TwoPanes."""

    def __init__(self, form):
        self.form = form
        self.plan = fx_plan(form, "dart")
        self.vplan = variant_plan(form)
        self.panes = {tp["name"]: tp for tp in two_panes(form)}
        self.wrapped: set[str] = set()
        if self.plan:
            for sb in self.plan["storyboards"]:
                self.wrapped.add(sb["target"])
            for t in self.plan["triggers"]:
                if t["on"] in ("click", "hover"):
                    self.wrapped.add(t["source"] or t["target"])
        self._places: dict[str, dict] = {}

    @property
    def active(self) -> bool:
        return bool(self.plan or self.vplan or self.panes)

    @property
    def files(self) -> list[str]:
        out = []
        if self.plan:
            out += ["radfx.dart", "radmotion.dart"]
        if self.vplan or self.panes:
            out.append("radlayout.dart")
        return out

    # ------------------------------------------------------------------ widgets
    def wrap(self, name: str, widget: str) -> str:
        if self.plan and name in self.wrapped:
            return f"radMotion.wrap({_dstr(name)}, {widget})"
        return widget

    def pick(self, name: str, prop: str, base: str, alt_of) -> str:
        """``rv.pick<double>(base, [RadV<double>('vid', ...)])`` when a size moves control *name*."""
        if not self.vplan:
            return base
        alts = []
        for vid, places in self._variant_places().items():
            pl = places.get(name)
            if pl is None:
                continue
            alt = alt_of(pl)
            if alt != base:
                alts.append(f"RadV<double>({_dstr(vid)}, {alt})")
        if not alts:
            return base
        return f"rv.pick<double>({base}, [{', '.join(alts)}])"

    def _variant_places(self) -> dict:
        """{size id: {control: layout.Place}} of the sizes that change geometry, computed like the base."""
        if self._places or not self.vplan:
            return self._places
        from ..variants.model import effective_form, overrides, size
        from .codegen_dart import DartFormGen
        for s in self.vplan["sizes"]:
            vid = s["id"]
            if not any(any(k in ov for k in VARIANT_GEOMETRY) for c in self.form.controls
                       for ov in [overrides(self.form, c, vid)]) and \
                    not any(k in ("Width", "Height") for k in overrides(self.form, None, vid)):
                continue
            ef = effective_form(self.form, size(self.form, vid), [vid])
            self._places[vid] = DartFormGen(ef, {}, "_").places_of_form()
        return self._places

    def two_pane(self, gen, c) -> str:
        tp = self.panes.get(c.name)
        kids = [k for k in form_children(self.form, c.name)][:2]
        if tp is None or len(kids) < 2:
            return "const SizedBox.shrink()"
        mode = {"Horizontal": "horizontal", "Vertical": "vertical"}.get(tp["mode"], "auto")
        ws = [self.wrap(k.name, gen.widget(k)) for k in kids]
        return (f"Container(color: {c.name}.backColor, child: RadTwoPane(start: {ws[0]}, end: {ws[1]}, "
                f"paneMode: RadPaneMode.{mode}, ratio: {_dnum(tp['ratio'])}, "
                f"singlePane: RadPane.{'end' if tp['single'] == 'End' else 'start'}, "
                f"hingeAware: {'true' if tp['hinge_aware'] else 'false'}))")

    # ------------------------------------------------------------------ class members
    def mixins(self) -> str:
        return ", TickerProviderStateMixin" if self.plan else ""

    def members(self, n: str) -> list[str]:
        L: list[str] = []
        if self.vplan:
            L.append("  static const _radSizes = <RadSize>[" + ", ".join(self._size(s) for s in self.vplan["sizes"])
                     + "];")
            L.append("  String _radActive = '\\u0000';")
        if self.plan:
            L.append("  static const _radSbs = <RadSb>[")
            for sb in self.plan["storyboards"]:
                L.append("    " + self._sb(sb) + ",")
            L.append("  ];")
            respect = "true" if self.plan.get("reduced_motion", True) else "false"
            L += [f"  late final RadMotion radMotion = RadMotion(this, _radSbs, "
                  f"() => {{for (final c in radControls) c.name: c}}, respectReducedMotion: {respect});", "",
                  "  /// Plays animation [id] of the Animations window (e.g. 'fx1').",
                  "  void BeginAnimation(String id) => radMotion.begin(id);", "",
                  "  void StopAnimation(String id) => radMotion.stop(id);", "",
                  "  /// Visible with the On show / On hide animations of the control.",
                  "  void SetVisible(String name, bool on) => radMotion.setVisible(name, on);"]
        if self.vplan:
            L += ["", "  /// The layout sizes that apply now (Width / Height of the window, posture of a foldable).",
                  "  List<String> get CurrentSizes => RadVariant.of(context, _radSizes).active;"]
            L += self._apply_sizes()
        return L

    def _size(self, s) -> str:
        mw, xw, mh, xh, orient, posture, span, fold = when_tuple(s.get("when") or {})
        args = [_dstr(s["id"])]
        for k, v in (("minWidth", mw), ("maxWidth", xw), ("minHeight", mh), ("maxHeight", xh)):
            if v is not None:
                args.append(f"{k}: {_dnum(v)}")
        if orient:
            args.append(f"orientation: Orientation.{orient}")
        if posture:
            args.append("posture: RadPosture." + {"half-opened": "halfOpened"}.get(posture, posture))
        if span:
            args.append(f"span: RadSpan.{span}")
        if fold in ("vertical", "horizontal"):
            args.append(f"fold: Axis.{fold}")
        return f"RadSize({', '.join(args)})"

    def _sb(self, sb) -> str:
        base = self.form.props if not sb["target"] else self.form.find(sb["target"]).props
        ch = channels(sb, base)
        tracks, colors = [], []
        for name, keys in ch.items():
            if name in ("bg", "fg"):
                ks = []
                for ms, v, e in keys:
                    col = "null" if v == "start" else (self._parent_color(sb["target"]) if v == "parent" else _dcolor(v))
                    ks.append(f"RadMKey({ms}, {col}{', ' + CURVES[e] if e in CURVES else ''})")
                colors.append(f"{_dstr(name)}: [{', '.join(ks)}]")
            else:
                ks = []
                for ms, v, e in keys:
                    val = (1.0 if v else 0.0) if isinstance(v, bool) else float(v)
                    ks.append(f"RadKey({ms}, {_dnum(val)}{', ' + CURVES[e] if e in CURVES else ''})")
                tracks.append(f"{_dstr(name)}: [{', '.join(ks)}]")
        t = trigger_of(self.plan, sb["fx"])
        args = [_dstr(sb["fx"]), _dstr(sb["target"]), str(int(sb["duration"]))]
        if tracks:
            args.append("tracks: {" + ", ".join(tracks) + "}")
        if colors:
            args.append("colors: {" + ", ".join(colors) + "}")
        if sb["count"] != 1:
            args.append(f"count: {int(sb['count'])}")
        if sb["repeat"]:
            args.append("forever: true")
        if sb["autoreverse"]:
            args.append("autoreverse: true")
        if sb.get("delayMs"):
            args.append(f"delayMs: {int(sb['delayMs'])}")
        if sb["chain"]:
            args.append("chain: [" + ", ".join(_dstr(x) for x in sb["chain"]) + "]")
        if t["on"] != "load":
            args.append(f"trigger: {_dstr(t['on'])}")
        if t["on"] in ("click", "hover") and t.get("source") and t["source"] != sb["target"]:
            args.append(f"source: {_dstr(t['source'])}")
        if t["on"] == "timer":
            args.append(f"intervalMs: {int(t['intervalMs'] or 1000)}")
        if t["on"] == "hover" and t.get("leave", "reverse") != "reverse":
            args.append(f"leave: {_dstr(t['leave'])}")
        return f"RadSb({', '.join(args)})"

    def _parent_color(self, name: str) -> str:
        c = self.form.find(name) if name else None
        p = self.form.find(c.parent) if c is not None and c.parent else None
        while p is not None:
            if p.props.get("BackColor"):
                return _dcolor(p.props["BackColor"])
            p = self.form.find(p.parent) if p.parent else None
        return _dcolor(self.form.props.get("BackColor") or "#FFFFFFFF")

    def _apply_sizes(self) -> list[str]:
        """_radUseSizes(rv): the control properties of the sizes (text, visible, colours, font size)."""
        from ..variants.model import RUNTIME_PROPS
        stmts: list[str] = []
        per: dict[str, dict[str, list]] = {}
        for vid, ctl in (self.vplan.get("controls") or {}).items():
            for name, ov in ctl.items():
                for k, v in (ov.get("props") or {}).items():
                    if k in RUNTIME_PROPS and k != "FontBold":
                        per.setdefault(name, {}).setdefault(k, []).append((vid, v))
        for name, props in per.items():
            c = self.form.find(name)
            if c is None:
                continue
            refresh = False
            for k, alts in props.items():
                if k == "Text":
                    base, typ, conv = _dstr(c.props.get("Text", "")), "String", _dstr
                    field = "text"
                elif k == "Visible":
                    base, typ, conv = ("true" if truthy(c.props.get("Visible", True)) else "false"), "bool", \
                        (lambda v: "true" if truthy(v) else "false")
                    field = "visible"
                elif k in ("BackColor", "ForeColor"):
                    base, typ, conv = _dcolor(c.props.get(k)), "Color?", _dcolor
                    field = "backColor" if k == "BackColor" else "foreColor"
                    refresh = True
                elif k == "FontSize":
                    fs = font_px(c.props)
                    base, typ = (_dnum(fs) if fs else "null"), "double?"
                    conv = lambda v: _dnum(font_px({"FontSize": v}) or v)      # noqa: E731
                    field = "fontSize"
                    refresh = True
                else:
                    continue
                lst = ", ".join(f"RadV<{typ}>({_dstr(vid)}, {conv(v)})" for vid, v in alts)
                stmts.append(f"      {name}.{field} = rv.pick<{typ}>({base}, [{lst}]);")
            if refresh:
                stmts.append(f"      {name}.refresh();")
        L = ["", "  void _radUseSizes(RadVariant rv) {",
             "    final key = rv.active.join('|');",
             "    if (key == _radActive) return;",
             "    _radActive = key;"]
        if stmts:
            L += ["    WidgetsBinding.instance.addPostFrameCallback((_) {", "      if (!mounted) return;", *stmts,
                  "    });"]
        L.append("  }")
        return L

    # ------------------------------------------------------------------ build()
    def build_start(self) -> list[str]:
        if not self.vplan:
            return []
        return ["    final rv = RadVariant.of(context, _radSizes);", "    _radUseSizes(rv);"]

    def form_pick(self, prop: str, base: str) -> str:
        """Form-level Text / BackColor of the sizes."""
        if not self.vplan:
            return base
        alts = [(vid, ov[prop]) for vid, ov in (self.vplan.get("form") or {}).items() if prop in ov]
        if not alts:
            return base
        if prop == "Text":
            return f"rv.pick<String>({base}, [{', '.join(f'RadV<String>({_dstr(v)}, {_dstr(x)})' for v, x in alts)}])"
        return f"rv.pick<Color?>({base}, [{', '.join(f'RadV<Color?>({_dstr(v)}, {_dcolor(x)})' for v, x in alts)}])"

    def init_lines(self) -> list[str]:
        if not self.plan:
            return []
        return ["    WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) radMotion.start(context); });"]

    def dispose_lines(self) -> list[str]:
        return ["    radMotion.dispose();"] if self.plan else []


def to_px(v) -> int:
    return to_int(v, 0)


def dart_source(name: str) -> str:
    """Text of a Dart helper file: radmotion.dart (this folder) or F's radfx.dart / radlayout.dart."""
    p = DART_DIR / name
    if not p.is_file():
        p = FD_DART / name
    return p.read_text(encoding="utf-8")


def radapp_exports(radapp: str, files: list[str]) -> str:
    """lib/radapp.dart plus ``export`` lines of the helper files the forms use."""
    exports = [(f"export '{f}' show RadKey;" if f == "radfx.dart" else f"export '{f}';") +
               "      // RAD IDE animations / layout sizes" for f in files]
    if not exports:
        return radapp
    lines = radapp.split("\n")
    at = 0
    for i, s in enumerate(lines):
        if s.startswith(("import ", "export ", "library ")):
            at = i + 1
    return "\n".join(lines[:at] + exports + lines[at:])


__all__ = ["DartFx", "dart_source", "radapp_exports", "CURVES"]
