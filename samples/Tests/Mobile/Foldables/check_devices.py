"""Foldable devices - pure checks (no window): presets, sizes per posture, hinge_rect, TwoPane split,
hinge conflicts, Posture property, SuperPreview presets and mobile code generation with a TwoPane.

    python samples/Tests/Mobile/Foldables/check_devices.py
"""
import copy
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from radide import devices as D  # noqa: E402
from radide.layout import relayout  # noqa: E402
from radide.mobile import controls as M  # noqa: E402
from radide.model import Form  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"), flush=True)


# ---------------------------------------------------------------- presets
for did in ("pixel", "small_phone", "tablet", "iphone_15", "iphone_se"):
    check(f"original preset {did} kept", did in D.DEVICES and did in M.DEVICES)
check("five foldables", set(D.FOLDABLE_IDS) == {"galaxy_z_fold6", "galaxy_z_flip6", "pixel_fold",
                                                "pixel_9_pro_fold", "surface_duo2"}, D.FOLDABLE_IDS)
check("mobile.controls re-exports devices", M.device is D.device and M.safe_area_size is D.safe_area_size)
check("old signature still works", M.safe_area_size("pixel", "Portrait") == (412, 867))
check("pixel landscape unchanged", M.safe_area_size("pixel", "Landscape") == (915, 372))
for did in D.FOLDABLE_IDS:
    d = D.device(did)
    check(f"{did} portrait is taller", d.height >= d.width)
    check(f"{did} postures", D.postures(did) == D.POSTURES)
    for o in D.ORIENTATIONS:
        for p in D.POSTURES:
            w, h = D.safe_area_size(did, o, p)
            hr = D.hinge_rect(did, o, p)
            if p == "Folded":
                check(f"{did} {o} Folded = cover, no hinge", hr is None and (w, h) != D.safe_area_size(did, o))
            else:
                x, y, hw, hh = hr
                inside = (0 < x < w and y == 0 and hh == h) if D.fold_axis(did, o, p) == "vertical" else \
                         (0 < y < h and x == 0 and hw == w)
                check(f"{did} {o} {p} hinge inside safe area", inside, (hr, w, h))
check("normal phone has no posture / hinge", D.postures("pixel") == () and D.hinge_rect("pixel", "Portrait",
                                                                                           "HalfOpened") is None)
check("posture spellings", [D.posture_name(s) for s in ("half-opened", "halfOpened", "tabletop", "closed", "",
                                                         "flat")] == ["HalfOpened"] * 3 + ["Folded", "Flat", "Flat"])
check("posture_key", D.posture_key("HalfOpened") == "half-opened")
check("duo is dual when flat", D.span("surface_duo2", "Landscape", "Flat") == "dual")
check("fold is single when flat, dual half-open", D.span("galaxy_z_fold6", "Portrait", "Flat") == "single"
      and D.span("galaxy_z_fold6", "Portrait", "HalfOpened") == "dual")
check("duo hinge 26 dp", D.hinge_rect("surface_duo2", "Landscape")[2] == 26)
segs = D.segments("surface_duo2", "Landscape")
check("duo segments", segs == [(0, 0, 540, 720), (566, 0, 540, 720)], segs)
df = D.display_features("galaxy_z_flip6", "Portrait", "HalfOpened")
check("flutter display features", df and df[0]["type"] == "fold" and df[0]["state"] == "postureHalfOpened"
      and df[0]["bounds"][3] == 0, df)
env = D.env_state({"RADIDE_POSTURE": "half-opened", "RADIDE_SPAN": "dual", "RADIDE_HINGE": "400,0,20,600"})
check("env_state", env == {"posture": "half-opened", "span": "dual", "hinge": (400, 0, 20, 600)}, env)

# ---------------------------------------------------------------- TwoPane rule
r = D.two_pane(1106, 600, hinge=(540, 0, 26, 600))
check("two_pane at hinge", r["split"] == "hinge" and r["panes"] == [(0, 0, 540, 600), (566, 0, 540, 600)], r)
r = D.two_pane(400, 700, single="End")
check("two_pane narrow = single End", r["mode"] == "single" and r["shown"] == 1, r)
r = D.two_pane(800, 600, ratio=0.25)
check("two_pane wide at Ratio", r["panes"][0] == (0, 0, 200, 600), r)
r = D.two_pane(400, 700, mode="Vertical")
check("two_pane forced vertical", r["mode"] == "vertical" and r["panes"][1] == (0, 350, 400, 350), r)
r = D.two_pane(1106, 600, hinge=(540, 0, 26, 600), hinge_aware=False)
check("two_pane ignores hinge when not HingeAware", r["split"] == "ratio", r)
r = D.two_pane(720, 1000, hinge=(0, 500, 720, 0))
check("two_pane horizontal crease -> top/bottom", r["mode"] == "vertical" and r["panes"][0][3] == 500, r)

# ---------------------------------------------------------------- the sample forms
demo = HERE / "FoldDemo"
md = Form.load(demo / "MasterDetail.form")
duo = Form.load(demo / "DuoHinge.form")
check("TwoPane registered", "TwoPane" in M.MOBILE_CONTROL_TYPES and "TwoPane" in M.LAYOUT_TYPES)
check("Posture shown for foldables only",
      "Posture" in [d.name for d in M.form_prop_defs(md)]
      and "Posture" not in [d.name for d in M.form_prop_defs({"Device": "pixel"})])
check("ensure_mobile_props: no Posture for phones", "Posture" not in (lambda p: (M.ensure_mobile_props(p), p)[1])(
    {"Device": "pixel"}))


def panes(form):
    c1, c2 = form.find("Column1"), form.find("Column2")
    return [tuple(c.props[k] for k in ("Left", "Top", "Width", "Height")) for c in (c1, c2)]


check("Fold6 flat: panes split at the crease", panes(md) == [(0, 0, 441, 1008), (441, 0, 441, 1008)], panes(md))
for posture, expect in (("Folded", "single"), ("HalfOpened", "hinge"), ("Flat", "hinge")):
    f2 = copy.deepcopy(md)
    f2.props["Posture"] = posture
    M.ensure_mobile_props(f2.props)
    relayout(f2)
    res = f2.__dict__["_rad_two_pane"]["TwoPane1"]
    tp = f2.find("TwoPane1")
    ok = res["split"] == expect
    if posture == "Folded":
        p1, p2 = panes(f2)
        ok = ok and p1[0] == 0 and p1[2] == tp.props["Width"] and p2[0] > tp.props["Width"]
    check(f"Fold6 {posture}: TwoPane {expect}", ok, (res, panes(f2)))
f3 = copy.deepcopy(md)
f3.props["Orientation"] = "Landscape"
M.ensure_mobile_props(f3.props)
relayout(f3)
r3 = f3.__dict__["_rad_two_pane"]["TwoPane1"]
check("Fold6 landscape: top/bottom panes at the horizontal fold", r3["mode"] == "vertical"
      and r3["split"] == "hinge", r3)
check("no conflicts on MasterDetail", M.hinge_conflicts(md) == [])
conf = M.hinge_conflicts(duo)
check("DuoHinge: Button1 crosses the hinge (only it)", [n for n, _ in conf] == ["Button1"], conf)
check("conflicts gone when Folded", M.hinge_conflicts(duo, posture="Folded") == [])
f4 = copy.deepcopy(md)
btn = f4.add("Button", 400, 300)
btn.props.update(Width=100, Height=40)
check("half-open fold reports a control across the crease",
      [n for n, _ in M.hinge_conflicts(f4, posture="HalfOpened")] == [btn.name]
      and M.hinge_conflicts(f4) == [], M.hinge_conflicts(f4, posture="HalfOpened"))

# ---------------------------------------------------------------- SuperPreview presets
from radide.web_site.superpreview import PRESETS, preset_segments  # noqa: E402
fold = [p for p in PRESETS if p.device]
check("SuperPreview foldable presets", len(fold) >= 5, [p.name for p in fold])
duo_p = next(p for p in PRESETS if p.device == "surface_duo2")
check("SuperPreview dual segments", duo_p.segments == 2 and len(preset_segments(duo_p)) == 2)
check("SuperPreview last preset is desktop 1920", PRESETS[-1].width == 1920)

# ---------------------------------------------------------------- code generation does not break
from radide.languages import get_plugin  # noqa: E402
for lang in ("flutter", "kivy", "expo"):
    try:
        plug = get_plugin(lang)
    except Exception as e:  # noqa: BLE001
        check(f"{lang} plugin", False, e)
        continue
    try:
        out = plug.generate_designer(copy.deepcopy(md), "")
        check(f"{lang} generates a TwoPane form", isinstance(out, str) and len(out) > 50)
    except Exception as e:  # noqa: BLE001
        check(f"{lang} generates a TwoPane form", False, repr(e))

ok = sum(c for _, c in RESULTS)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
