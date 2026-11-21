"""Motion core (radide/motion + Blend runtime extensions) without a GUI.

    python samples/Tests/Motion/check_motion_core.py

expand() of every preset for every target, fallbacks, relative keyframes / easings of COMMON_RT,
validate() / rename / remove, design-time props_at, old storyboards unchanged, generated python-tk and
python-qt designers compile (with and without animations)."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from radide import motion  # noqa: E402
from radide.features import states, timeline  # noqa: E402
from radide.languages import get_plugin  # noqa: E402
from radide.model import Form  # noqa: E402
from radide.motion import presets as P  # noqa: E402
from radide.motion import runtime_py  # noqa: E402

FAILS: list[str] = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


D = states.DESIGN


def sample_form() -> Form:
    f = Form()
    for kind, x, y in (("Button", 10, 10), ("Label", 10, 50), ("Panel", 200, 10), ("PictureBox", 200, 120)):
        f.add(kind, x, y)
    return f


def main() -> int:
    f = sample_form()
    names = [c.name for c in f.visual()]
    # ------------------------------------------------------------------ catalog / expand
    check(set(P.GROUPS) == {p.group for p in P.CATALOG.values()}, "every group has presets")
    for pid in P.CATALOG:
        motion.add(f, names[0], pid)
    motion.add(f, "", "fadeIn")
    motion.add(f, names[1], "typewriter", trigger={"on": "after", "after": "fx1"})
    for target in P.TARGET_CAPS:
        plan = motion.expand(f, target)
        n = len(plan["storyboards"])
        alpha, transform = P.TARGET_CAPS[target]
        props = {p for sb in plan["storyboards"] for _t, p, _k in sb["tracks"]}
        ok = n == len(P.CATALOG) + 2 and len(plan["triggers"]) == n
        ok &= (("Rotation" in props) == transform) and (("ScaleX" in props) == transform)
        fb = {fx for fx, _c, _m in plan["fallbacks"]}
        rot = next(a["id"] for a in f.extra["animations"] if a["preset"] == "rotate")
        fade = next(a["id"] for a in f.extra["animations"] if a["preset"] == "fadeOut" and a["target"])
        ok &= (rot in fb) != transform and (fade in fb) != alpha
        check(ok, f"expand target {target}: {n} storyboards, fallbacks {len(plan['fallbacks'])}")
        for sb in plan["storyboards"]:
            if not (sb["name"].startswith("_fx_") and all(isinstance(k, list) and len(k) >= 2
                                                          for _t, _p, ks in sb["tracks"] for k in ks)):
                check(False, f"{target}: bad storyboard {sb['name']}")
    plan = motion.expand(f, "py")
    check(all("Button1 Rotate" not in m for _f, _c, m in plan["fallbacks"]) and plan["fallbacks"],
          "fallbacks are listed with a message for the Error List")
    form_fade = next(sb for sb in plan["storyboards"] if sb["target"] == "")
    check([p for _t, p, _k in form_fade["tracks"]] == ["Opacity"], "form fade = window opacity, even on tk")
    tw = next(t for t in plan["triggers"] if t["on"] == "after")
    check(tw["after"] == "fx1" and tw["target"] == names[1], "after trigger kept with its target")
    # ------------------------------------------------------------------ model
    check(motion.validate(f) == [], f"valid form: {motion.validate(f)}")
    g = sample_form()
    motion.add(g, "Nope", "shake", id="a1")
    motion.add(g, names[3], "typewriter", id="a2")              # PictureBox: no Text
    motion.add(g, names[0], "fadeIn", id="a3", trigger={"on": "after", "after": "a4"})
    motion.add(g, names[0], "fadeOut", id="a4", trigger={"on": "after", "after": "a3"})
    motion.add(g, names[0], "pulse", id="a5", trigger={"on": "timer", "intervalMs": 0})
    msgs = " | ".join(m for _f, _c, m in motion.validate(g))
    check("'Nope' does not exist" in msgs and "Typewriter needs" in msgs and "loop" in msgs
          and "interval" in msgs, f"validate finds problems: {msgs}")
    check(len(motion.expand(g, "py")["storyboards"]) == 3, "expand skips missing targets / text-less typewriter")
    motion.add(g, names[0], "shake", id="a6", trigger={"on": "click", "source": names[2]})
    check(states.rename_references(g, names[2], "pnlNew") is None
          and motion.find(g, "a6")["trigger"]["source"] == "pnlNew", "rename follows trigger sources (states hook)")
    check(motion.model.rename_references(g, names[0], "btnX") >= 3, "rename follows targets")
    motion.remove(g, "a3")
    check(motion.find(g, "a4")["trigger"]["after"] is None, "remove clears chains to it")
    check(motion.describe(motion.find(g, "a6")).startswith("Shake - 500 ms, on click of pnlNew"), "describe")
    # ------------------------------------------------------------------ runtime maths (COMMON_RT)
    R = D["_rad_resolve"]
    check(R("Left", {"d": -50}, 100) == 50 and R("Width", {"m": 1.5}, 100) == 150, "relative d / m")
    check(R("Left", {"of": "Width", "f": 0.5}, 10, lambda p: 80) == 50, "relative 'of' another property")
    check(R("Text", {"reveal": 0.5}, "abcd") == "ab" and R("BackColor", "$parent", "#fff", lambda p: "#000") == "#000",
          "reveal / $parent")
    check(R("Opacity", {"d": 0}, 1.0) == 1.0 and R("Visible", {"d": 0}, True) is True, "Opacity / bool start kept")
    for e in ("linear", "in", "out", "inout", "back", "elastic", "bounce", "sine"):
        a, b = D["_rad_ease"](0.0, e), D["_rad_ease"](1.0, e)
        if abs(a) > 1e-9 or abs(b - 1) > 1e-9:
            check(False, f"ease {e} must go 0 -> 1 ({a}, {b})")
    check(D["_rad_ease"](0.6, "back") > D["_rad_ease"](0.6, "linear"), "back overshoots")
    keys = [(0, D["_RadText"](""), ""), (1000, D["_RadText"]("Hello"), "")]
    check(D["_rad_value_at"]("Text", keys, 600, "", None) == "Hel", "typewriter mixes by prefix")
    check(D["_rad_value_at"]("Text", [(0, "a", ""), (1000, "b", "")], 600, "a", None) == "a",
          "plain Text keyframes stay discrete")
    # old storyboards: same values as the previous algorithm
    old = [(0, 10, ""), (500, 200, "out"), (1000, 50, "inout")]
    exp = {0: 10, 250: 152, 500: 200, 750: 125, 1000: 50}
    got = {t: D["_rad_value_at"]("Left", old, t, 10, None) for t in exp}
    check(got == exp, f"old storyboard values unchanged {got}")
    # ------------------------------------------------------------------ design time
    sb = motion.expand(f, "py")["storyboards"][0]                # fadeIn on tk: colour blend from parent
    base = f.find(names[0]).props
    mid = timeline.props_at(sb, names[0], 200, dict(base, BackColor="#ffffff"), "#000000")
    check(mid.get("BackColor") not in (None, "#ffffff", "#000000"), f"props_at resolves $parent ({mid.get('BackColor')})")
    sl = next(s for s in motion.expand(f, "py")["storyboards"] if s.get("preset") == "slideIn")
    check(timeline.props_at(motion.storyboard_dict(sl), names[0], 0, base)["Left"] == base["Left"] - 80,
          "props_at on storyboard_dict with relative keys")
    # ------------------------------------------------------------------ code generation
    for pl in ("python-tk", "python-qt"):
        code = get_plugin(pl).generate_designer(f, "")
        compile(code, pl, "exec")
        check("_RadFx(" in code and "def Animate(" in code and "def BeginAnimation(" in code,
              f"{pl}: designer with animations compiles, has the API")
        plain = get_plugin(pl).generate_designer(sample_form(), "")
        check("_RadFx(" not in plain and "_Storyboard" not in plain, f"{pl}: no animation runtime without animations")
        h = sample_form()
        h.extra["motion"] = {"respectReducedMotion": False}
        code = get_plugin(pl).generate_designer(h, "")
        compile(code, pl, "exec")
        check("reduced=False" in code and "def Animate(" in code, f"{pl}: extra.motion alone gives Animate()")
    check(states.python_blend(sample_form(), "tk") is None, "python_blend None without Blend features / animations")
    check(runtime_py.METHOD_NAMES <= states.RESERVED_NAMES, "API names reserved for storyboard names")
    # existing Blend samples still generate and compile
    for folder in ("Blend_Tk_StatesStoryboards", "Blend_Qt_StatesStoryboards", "Blend_Tk_DataBinding"):
        d = ROOT / "samples" / "Tests" / "Blend" / folder
        lang = "python-qt" if "_Qt_" in folder else "python-tk"
        code = get_plugin(lang).generate_designer(Form.load(d / "Form1.form"), (d / "Form1.py").read_text("utf-8"))
        compile(code, folder, "exec")
        check("self._fx = _RadFx(" not in code, f"Blend sample {folder} generates as before (no motion runtime)")
    print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
