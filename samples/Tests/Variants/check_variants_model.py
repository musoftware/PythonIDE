"""Pure checks of the layout-variant model and code generation (radide/variants), no window needed.

    python samples/Tests/Variants/check_variants_model.py

Covers Control.variants round trips (to_dict / snapshot undo / copy), the sizes API, matching (width /
height ranges, orientation, posture, span, fold, cascade order), preview contexts (explicit sizes, devices,
foldable postures), effective_form (anchors, absolute overrides, container children, docking, hidden),
plan() and merge_variants (COMMON_RT / _RadIO exactly once, no change at all for forms without sizes,
generated python-tk / python-qt code compiles, together with visual states and storyboards)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from radide.languages import get_plugin  # noqa: E402
from radide.model import Control, Form  # noqa: E402
from radide.variants import model as vm  # noqa: E402
from radide.variants.runtime_py import merge_variants  # noqa: E402

FAILS: list[str] = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def base_form() -> Form:
    f = Form()
    f.props.update(Name="Form1", Width=600, Height=400)
    b = f.add("Button", 20, 20)
    b.props.update(Name="btnWide", Width=560, Height=30, Anchor="Top, Left, Right")
    r = f.add("Button", 480, 350)
    r.props.update(Name="btnOk", Width=100, Height=30, Anchor="Bottom, Right")
    p = f.add("Panel", 20, 80)
    p.props.update(Name="pnl", Width=300, Height=200)
    k = f.add("Label", 200, 10, "pnl")
    k.props.update(Name="lblIn", Width=80, Height=20, Anchor="Top, Right")
    t = f.add("Panel", 0, 0)
    t.props.update(Name="pnlTop", Height=40, Dock="Top")
    return f


def main() -> int:
    # ------------------------------------------------------------ data model
    f = base_form()
    wide, ok, pnl, lbl = (f.find(n) for n in ("btnWide", "btnOk", "pnl", "lblIn"))
    check(wide.variants == {} and "variants" not in wide.to_dict(), "Control.variants empty and not written")
    phone = vm.add_size(f, vm.preset("phone"))
    tablet = vm.add_size(f, vm.preset("tablet"))
    check([s["id"] for s in vm.sizes(f)] == ["phone", "tablet"], "sizes() in list order")
    again = vm.add_size(f, vm.preset("phone"))
    check(again["id"] == "phone2", f"add_size makes ids unique ({again['id']})")
    vm.remove_size(f, "phone2")
    vm.set_override(f, ok, "phone", "Left", "16")
    vm.set_override(f, ok, "phone", "Visible", "false")
    vm.set_override(f, None, "tablet", "Text", "Tablet window")
    check(ok.variants == {"phone": {"Left": 16, "Visible": False}}, f"set_override coerces values ({ok.variants})")
    check(vm.overrides(f, None, "tablet") == {"Text": "Tablet window"}, "form-level override stored")
    d = Control.from_dict(json.loads(json.dumps(ok.to_dict())))
    check(d.variants == ok.variants and d.variants is not ok.variants, "to_dict / from_dict round trip (copy)")
    snap = Form.from_dict(json.loads(f.snapshot()))
    check(snap.find("btnOk").variants == ok.variants and snap.extra["variants"]["sizes"][0]["id"] == "phone",
          "snapshot (undo / copy-paste) keeps per-control overrides and sizes")
    check(vm.overridden_in(f, ok, "Left") == ["phone"] and vm.has_overrides(f, "phone")
          and not vm.has_overrides(f, "nope"), "overridden_in / has_overrides")
    vm.rename_size(f, "phone", "compact")
    check("compact" in ok.variants and vm.size(f, "compact") is not None, "rename_size moves the overrides")
    vm.rename_size(f, "compact", "phone")
    vm.remove_override(f, ok, "phone", "Visible")
    check(ok.variants == {"phone": {"Left": 16}}, "remove_override (one property)")

    # ------------------------------------------------------------ matching
    sz = [{"id": "s", "when": {"maxWidth": 599}}, {"id": "m", "when": {"minWidth": 600, "maxWidth": 1023}},
          {"id": "land", "when": {"orientation": "landscape"}}, {"id": "tt", "when": {"posture": "half-opened"}},
          {"id": "dual", "when": {"span": "dual"}}, {"id": "hz", "when": {"fold": "horizontal"}},
          {"id": "tall", "when": {"minHeight": 900}}]
    check(vm.matching(sz, 500, 800) == ["s"], "width 500 portrait -> s")
    check(vm.matching(sz, 599, 300) == ["s", "land"], "599 x 300 -> s + landscape (list order)")
    check(vm.matching(sz, 600, 700) == ["m"], "600 -> m (boundaries inclusive)")
    check(vm.matching(sz, 1024, 700) == ["land"], "1024 x 700 -> landscape only")
    check(vm.matching(sz, 800, 1000, posture="half-opened", span="dual", fold="horizontal") ==
          ["m", "tt", "dual", "hz", "tall"], "posture / span / fold / minHeight")
    check(vm.matching(sz, 800, 1000, posture="HalfOpened") == ["m", "tt", "tall"], "posture spellings normalised")
    check(vm.matching([{"id": "x", "when": {}}], 1, 1) == ["x"], "empty when = always")

    # ------------------------------------------------------------ preview contexts
    ctx = vm.context(f, "phone")
    check((ctx["width"], ctx["height"]) == (400, 760), f"explicit preview size ({ctx})")
    f2 = Form()
    f2.props.update(Width=1200, Height=700)
    vm.add_size(f2, vm.preset("medium"))
    ctx = vm.context(f2, "medium")
    check((ctx["width"], ctx["height"]) == (800, 700), f"preview width + base height ({ctx})")
    vm.add_size(f2, {"id": "nar", "label": "Narrow", "when": {"maxWidth": 500}})
    check(vm.context(f2, "nar")["width"] == 500, "no preview: base width clamped into the range")
    vm.add_size(f2, vm.preset("folded"))
    vm.add_size(f2, vm.preset("halfopen"))
    cf, ch = vm.context(f2, "folded"), vm.context(f2, "halfopen")
    from radide import devices
    check((cf["width"], cf["height"]) == devices.safe_area_size("galaxy_z_fold6", "Portrait", "Folded")
          and cf["posture"] == "folded", f"foldable Folded preview = cover screen ({cf})")
    check(ch["posture"] == "half-opened" and ch["span"] == "dual" and ch["orientation"] == "landscape"
          and ch["fold"] == "horizontal", f"Half-open preview: span dual, fold horizontal ({ch})")
    vm.set_override(f2, None, "medium", "Width", 900)
    check(vm.context(f2, "medium")["width"] == 900, "form-level Width override changes the preview size")
    check(vm.when_text({"minWidth": 600, "maxWidth": 1023}) == "width 600-1023", "when_text")

    # ------------------------------------------------------------ effective form
    ef = vm.effective_form(f, "phone")
    e = {c.name: c.props for c in ef.controls}
    check(ef.props["Width"] == 400 and ef.props["Height"] == 760, "effective form gets the preview size")
    check(e["btnWide"]["Width"] == 360, f"Left+Right anchored button stretches (560 -> {e['btnWide']['Width']})")
    check(e["btnOk"]["Left"] == 16 and e["btnOk"]["Top"] == 710, f"override absolute, Bottom anchor follows "
          f"({e['btnOk']['Left']}, {e['btnOk']['Top']})")
    check(e["pnlTop"]["Width"] == 400, "docked panel relaid out to the new width")
    check(f.find("btnOk").props["Left"] == 480 and f.props["Width"] == 600, "effective_form never touches the model")
    vm.set_override(f, pnl, "phone", "Width", 200)
    ef = vm.effective_form(f, "phone")
    check(ef.find("lblIn").props["Left"] == 100, f"container override moves its Right-anchored child "
          f"({ef.find('lblIn').props['Left']})")
    vm.set_override(f, lbl, "phone", "Left", 5)
    check(vm.effective_form(f, "phone").find("lblIn").props["Left"] == 5, "child's own override wins")
    check(vm.effective_form(f, None).find("btnOk").props["Left"] == 480, "size None = base design copy")
    vm.set_override(f, wide, "phone", "Visible", False)
    check(vm.effective_form(f, "phone").find("btnWide").props["Visible"] is False, "hidden on the size")
    f3 = Form()
    f3.props.update(Width=1000, Height=600)
    lab = f3.add("Label", 10, 10)
    vm.add_size(f3, {"id": "a", "label": "A", "when": {"maxWidth": 900}, "preview": {"width": 800}})
    vm.add_size(f3, {"id": "b", "label": "B", "when": {"maxWidth": 700}, "preview": {"width": 600}})
    vm.set_override(f3, lab, "a", "Text", "from A")
    vm.set_override(f3, lab, "b", "FontSize", 20)
    check(vm.cascade(f3, "b") == ["a", "b"], f"cascade: earlier matching sizes, then the size ({vm.cascade(f3, 'b')})")
    eb = vm.effective_form(f3, "b").find(lab.name).props
    check(eb["Text"] == "from A" and eb["FontSize"] == 20, "cascade applies A then B")
    check(vm.cascade(f3, "a") == ["a"], "later sizes are not applied to an earlier one")

    # ------------------------------------------------------------ plan
    check(vm.plan(base_form()) is None, "plan() None without sizes")
    p = vm.plan(f)
    ph = p["controls"]["phone"]
    check(ph["btnOk"]["place"] is not None and ph["btnOk"]["place"][0] == 16 - 0 and ph["btnOk"]["place"][4] == 0,
          f"btnOk place on phone: Left override anchored Bottom ({ph['btnOk']['place']})")
    check(ph["btnWide"]["props"] == {"Visible": False}, "non-geometry props separate from the place")
    check("btnOk" in p["base"] and p["base"]["btnOk"][4] == 1, "base place kept for restoring (Right anchor)")
    check(p["form"] == {"tablet": {"Text": "Tablet window"}}, "form-level Text in the plan")
    check(p["controls"]["tablet"] == {}, "size without control overrides: empty")

    # ------------------------------------------------------------ code generation
    plain = base_form()
    res = {"runtime": "x", "init": [], "after_load": [], "methods": []}
    check(merge_variants(res, plain, "tk") is res and merge_variants(None, plain, "qt") is None,
          "merge_variants: no sizes -> result unchanged")
    code_plain = get_plugin("python-tk").generate_designer(plain, "")
    check("_RadVariants" not in code_plain and "_RadIO" not in code_plain, "no sizes: generated code unchanged")
    for pid, tk in (("python-tk", True), ("python-qt", False)):
        code = get_plugin(pid).generate_designer(f, "")
        compile(code, f"{pid}.py", "exec")
        check(code.count("class _RadIO") == 1 and code.count("def _rad_ease") == 1
              and code.count("self._rad = _RadIO(self)") == 1 and "_RadVariants(self, self._rad" in code,
              f"{pid}: COMMON_RT / _RadIO exactly once, variants wired")
        check(("class _RadVariantEvents" in code) != tk, f"{pid}: Qt resize filter only for python-qt")
    # with visual states + a storyboard (python_blend returns something)
    g = Form.from_dict(json.loads(f.snapshot()))
    g.find("btnOk").states = {"Big": {"Width": 160}}
    g.extra["storyboards"] = [{"name": "sbIntro", "autostart": False, "repeat": False, "autoreverse": False,
                               "tracks": [{"target": "btnOk", "property": "Left", "keys": [[0, 0], [300, 20]]}]}]
    for pid in ("python-tk", "python-qt"):
        code = get_plugin(pid).generate_designer(g, "")
        compile(code, f"{pid}-blend.py", "exec")
        check(code.count("class _RadIO") == 1 and code.count("self._rad = _RadIO(self)") == 1
              and "_VisualStates(" in code and "_RadVariants(" in code, f"{pid}: with states + storyboard, once")
    vb = get_plugin("vb-basic") if True else None
    check(vb is not None, "vb-basic plugin present (builds forms with the python-tk generator)")

    print(f"{'ALL OK' if not FAILS else f'{len(FAILS)} FAILED'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
