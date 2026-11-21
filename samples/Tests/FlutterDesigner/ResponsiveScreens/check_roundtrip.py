"""Flutter designer layout variants + foldables check (plan MOTION_VARIANTS_FOLDABLES.md, slice F). From the
repository root:

    python samples/Tests/FlutterDesigner/ResponsiveScreens/check_roundtrip.py

* every screens/*.fscreen.json: valid, generates without warnings, Dart -> import gives the same tree, vprops and
  sizes (labels / preview devices come back from the previous screen file), regenerated code identical;
* variants_fd API: matching (devices.py foldables), effective(), This-size-only edits (set_override, apply to
  all, copy to, hide / show again, remove size) and their undo, markers.
Then `flutter analyze` and `flutter test` in this folder run the generated code (test/responsive_test.dart).
"""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
sys.path.insert(0, str(HERE.parent / "MotionScreens"))
from check_roundtrip import FAILS, check, roundtrip  # noqa: E402
from radide.flutterdesign import model as M, variants_fd as VF  # noqa: E402


def api():
    scr = M.Screen.load(HERE / "screens" / "Gallery.fscreen.json")
    sz = VF.sizes(scr)
    check(VF.matching(sz, 400, 800) == ["compact"], "phone -> compact")
    check(VF.matching(sz, 800, 1280) == ["medium"], "tablet -> medium")
    fold = VF.device_facts("galaxy_z_fold6", "Portrait", "HalfOpened")
    check(fold["posture"] == "half-opened" and fold["fold"] == "vertical", f"Z Fold6 half opened facts {fold}")
    check(VF.active_for(scr, fold) == ["medium", "tabletop", "dual"],   # a half-opened fold separates: dual
          f"Z Fold6 half opened -> {VF.active_for(scr, fold)}")
    folded = VF.device_facts("galaxy_z_fold6", "Portrait", "Folded")
    check(folded["width"] == 360 and VF.active_for(scr, folded) == ["compact"], "folded = cover screen, compact")
    duo = VF.device_facts("surface_duo2", "Landscape", "Flat")
    check(duo["span"] == "dual" and "dual" in VF.active_for(scr, duo), f"Surface Duo spanned -> dual {duo}")
    grid = next(n for n, *_ in scr.walk() if n["type"] == "GridView")
    eff = VF.effective(scr, ["medium"])
    g2 = next(n for n, *_ in M.walk_node(eff["tree"]) if n["id"] == grid["id"])
    check(g2["props"]["crossAxisCount"] == 3, "effective(): medium overrides applied")
    side = next(n for n, *_ in scr.walk() if (n.get("props") or {}).get("width") == 200)
    eff = VF.effective(scr, ["compact"])
    s2 = next(n for n, *_ in M.walk_node(eff["tree"]) if n["id"] == side["id"])
    check(s2["type"] == "SizedBox" and s2.get("$hidden"), "effective(): hidden on compact, id kept")
    eff = VF.effective(scr, ["compact", "tabletop"])
    s3 = next(n for n, *_ in M.walk_node(eff["tree"]) if n["id"] == side["id"])
    check(s3["type"] == "Container", "effective(): tabletop shows it again (later size wins)")
    check(VF.marker(grid, "crossAxisCount", "medium") == VF.MARK_HERE and
          VF.marker(grid, "crossAxisCount", "compact") == VF.MARK_ELSEWHERE and
          VF.marker(grid, "mainAxisSpacing", "medium") == "", "markers")

    # This size only edits + undo
    before = copy.deepcopy(scr.to_dict())
    p1 = VF.set_override(scr, grid["id"], "compact", "mainAxisSpacing", 4)
    check(VF.overrides(scr.find(grid["id"]), "compact") == {"mainAxisSpacing": 4}, "set_override")
    check(scr.find(grid["id"])["props"]["mainAxisSpacing"] == 8, "base unchanged")
    p2 = VF.copy_to(scr, grid["id"], "compact", "mainAxisSpacing", "expanded")
    check(VF.overrides(scr.find(grid["id"]), "expanded")["mainAxisSpacing"] == 4, "copy_to")
    p3 = VF.apply_to_all(scr, grid["id"], "compact", "mainAxisSpacing")
    g = scr.find(grid["id"])
    check(g["props"]["mainAxisSpacing"] == 4 and all("mainAxisSpacing" not in (o or {})
                                                     for o in g["vprops"].values()), "apply_to_all")
    p4 = VF.set_hidden(scr, grid["id"], "dual", True)
    check(VF.is_hidden(scr.find(grid["id"]), "dual"), "hide on a size")
    p5 = VF.remove_size(scr, "dual")
    check(VF.size(scr, "dual") is None and "dual" not in (scr.find(grid["id"]).get("vprops") or {}),
          "remove_size drops its overrides")
    for p in (p5, p4, p3, p2, p1):
        M.apply_patch(scr, M.invert(p))
    check(scr.to_dict() == before, "undo restores the screen")
    p6 = VF.set_override(scr, grid["id"], "medium", "crossAxisCount", 2)   # == base: no override kept
    check("crossAxisCount" not in VF.overrides(scr.find(grid["id"]), "medium"), "override equal to base dropped")
    M.apply_patch(scr, M.invert(p6))
    pv = VF.preview_data(scr, ["expanded"])
    check(all("vprops" not in n for n, *_ in M.walk_node(pv["tree"])), "preview_data strips vprops")
    bad = M.Screen({"name": "Bad", "variants": [{"id": "x", "when": {"color": 1}}],
                    "tree": {"type": "Scaffold", "id": "w1", "vprops": {"nope": {"x": 1}}}})
    msgs = " ".join(i.message for i in bad.validate())
    check("unknown condition" in msgs and "unknown size" in msgs, "validation of sizes / vprops")


def main() -> int:
    for path in sorted((HERE / "screens").glob("*" + M.SCREEN_EXT)):
        roundtrip(path)
    api()
    print("failures:", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
