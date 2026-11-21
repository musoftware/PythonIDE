"""Flutter designer motion check (plan MOTION_VARIANTS_FOLDABLES.md, slice F). From the repository root:

    python samples/Tests/FlutterDesigner/MotionScreens/check_roundtrip.py

For every screens/*.fscreen.json: validate, generate the Dart code, import it back with the package:analyzer based
importer and compare the trees (ids aside) and the screen-level motion fields (state, timelines, transition).
Also checks the Python preview maths (motion.frame / value_at / resolve_value) and the event forms.
Then `flutter analyze` and `flutter test` in this folder run the generated code (test/motion_test.dart).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from radide.flutterdesign import codegen as CG, importer as I, model as M, motion as MO  # noqa: E402

FAILS = []
SCREEN_KEYS = ("state", "timelines", "transition", "variants")


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


def norm(v):
    if isinstance(v, dict):
        return {k: (re.sub(r",\s*([)\]}])", r"\1", re.sub(r"\s+", "", x)) if k in ("code", "$code") and
                    isinstance(x, str) else norm(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v


def roundtrip(path: Path):
    scr = M.Screen.load(path)
    errs = [str(i) for i in scr.validate()]
    check(not errs, f"{scr.name}: valid {errs[:3]}")
    gen = CG.generate_screen(scr, None)
    check(not gen.warnings, f"{scr.name}: no codegen warnings {gen.warnings[:3]}")
    res = I.import_dart(gen.designer_code, previous=scr.to_dict())
    back = next((s for s in res.screens if s["name"] == scr.name), None)
    check(back is not None, f"{scr.name}: imported")
    if back is None:
        return
    a, b = norm(M.strip_ids(scr.to_dict()["tree"])), norm(M.strip_ids(M.Screen(back).to_dict()["tree"]))
    check(a == b, f"{scr.name}: tree survives Dart -> import")
    if a != b:
        for x, y in zip(json.dumps(a, indent=1).splitlines(), json.dumps(b, indent=1).splitlines()):
            if x != y:
                print("   expected:", x, "\n   imported:", y)
                break
    for k in SCREEN_KEYS:
        check(norm(scr.data.get(k)) == norm(back.get(k)), f"{scr.name}: screen {k} survives")
    stats = res.stats.get(scr.name, {})
    check(not stats.get("code_nodes") and not stats.get("code_props"),
          f"{scr.name}: nothing kept as code {stats.get('code_nodes', [])[:2]} {stats.get('code_props', [])[:2]}")
    # a second generation from the imported screen is identical
    gen2 = CG.generate_screen(M.Screen(back), None)
    check(gen2.designer_code == gen.designer_code, f"{scr.name}: regenerated code identical")


def maths():
    f = MO.frame({"type": "keyframes", "tracks": {"opacity": [[0, 0], [300, 1]], "offsetY": [[0, 40], [600, 0]]}}, 0)
    check(f["opacity"] == 0 and f["dy"] == 40, "keyframes frame at 0")
    f = MO.frame({"type": "keyframes", "tracks": {"opacity": [[0, 0], [300, 1]], "offsetY": [[0, 40], [600, 0]]}}, .5)
    check(f["opacity"] == 1 and abs(f["dy"] - 20) < 1e-9, "keyframes frame at 0.5 (300 of 600 ms)")
    check(abs(MO.frame({"type": "shake"}, 1)["dx"]) < 1e-9, "shake ends where it started")
    check(abs(MO.frame({"type": "pulse", "scale": 1.2}, .5)["sx"] - 1.2) < 1e-9, "pulse peak")
    check(MO.frame({"type": "fadeInUp"}, 0)["dy"] == 30, "legacy fadeInUp offset")
    a = {"type": "shake", "repeat": 2, "reverse": True, "durationMs": 100, "delayMs": 50}
    check(MO.value_at(a, 100) == .5 and MO.value_at(a, 200) == .5 and MO.play_length(a) == 450,
          "value_at with repeat / reverse")
    check(MO.resolve_value({"$when": {"state": "x", "on": 2, "off": 1}}, "double", {"x": True}) == 2, "$when on")
    tl = {"$timeline": "t", "from": 0, "to": 10, "interval": [0, .5], "curve": "Curves.linear"}
    check(MO.resolve_value(tl, "timeline", {}, {"t": .25}) == 5, "$timeline interval")
    check(MO.event_action("toggle:x") == "() => setState(() => x = !x)", "toggle event")
    check("RadTransition.slideUp" in MO.event_action("push:Home?transition=slideUp&ms=400"), "push transition")
    bad = M.Screen({"name": "Bad", "tree": {"type": "Scaffold", "id": "w1", "anim": {"type": "shake",
                                                                                   "trigger": "state:nope"}}})
    check(any("state:nope" in i.message for i in bad.validate()), "validation: unknown state field")


def main() -> int:
    for path in sorted((HERE / "screens").glob("*" + M.SCREEN_EXT)):
        roundtrip(path)
    maths()
    print("failures:", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
