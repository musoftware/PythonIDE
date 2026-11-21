"""Flutter designer UI test: This size only edits, sizes bar, foldable postures + hinge, side-by-side, motion
editors (plan MOTION_VARIANTS_FOLDABLES.md slice F). Uses the QA harness (offscreen, QSettings org RADIDE-TEST,
screenshots with widget.grab only). From the repository root:

    python samples/Tests/FlutterDesigner/ResponsiveScreens/test_designer_ui.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "QA", "Integration"))
os.environ.setdefault("QA_NAME", "fd-variants")
import qh  # noqa: E402
from qh import check, pump, shot  # noqa: E402

from radide.flutterdesign import model as M, motion_ui as MU, qtpreview as Q, variants_fd as VF  # noqa: E402
from radide.flutterdesign.designer import DEVICE_IDS, FlutterDesigner  # noqa: E402

work = os.path.join(qh.WORK, "fd_variants")
shutil.rmtree(work, ignore_errors=True)
for sub in ("ResponsiveScreens", "MotionScreens"):
    src = os.path.join(HERE, "..", sub)
    dst = os.path.join(work, sub)
    os.makedirs(os.path.join(dst, "screens"))
    for f in os.listdir(os.path.join(src, "screens")):
        shutil.copy2(os.path.join(src, "screens", f), os.path.join(dst, "screens", f))
    shutil.copy2(os.path.join(src, "pubspec.yaml"), os.path.join(dst, "pubspec.yaml"))

d = FlutterDesigner(os.path.join(work, "ResponsiveScreens", "screens", "Gallery.fscreen.json"), live=False)
d.resize(1400, 900)
d.show()
pump(1.0)
scr = d.screen
grid = next(n for n, *_ in scr.walk() if n["type"] == "GridView")
side = next(n for n, *_ in scr.walk() if (n.get("props") or {}).get("width") == 200)
check("size bar lists the sizes", d.size_bar.cbo_size.count() == len(VF.sizes(scr)))
check("phone device -> compact active", d.active_sizes() == ["compact"], d.active_sizes())
check("compact hides the sidebar in the Qt preview", d.canvas.bounds.get(side["id"]) is not None and
      d.canvas.bounds[side["id"]].width() == 0, d.canvas.bounds.get(side["id"]))
shot(d.canvas, "fd_phone")

# ---- This size only: Tablet
d.select(grid["id"])
d.set_edit_mode("size")
d.set_edit_size("medium")
pump(0.3)
check("This size only shows the size's preview size", d.device_size() == (800, 1280), d.device_size())
check("medium active on its preview", d.active_sizes() == ["medium"], d.active_sizes())
tiles = [n for n, *_ in scr.walk() if n["type"] == "Card"]
xs = sorted({round(d.canvas.bounds[t["id"]].x()) for t in tiles if t["id"] in d.canvas.bounds})
check("tablet preview: 3 grid columns", len(xs) == 3, xs)
d.set_prop(grid["id"], "mainAxisSpacing", 20)
g = scr.find(grid["id"])
check("edit stored for the size only", VF.overrides(g, "medium").get("mainAxisSpacing") == 20 and
      g["props"]["mainAxisSpacing"] == 8, g)
lab = d.inspector.labels.get("mainAxisSpacing")
check("inspector marker on the overridden property", lab is not None and lab.text().startswith(VF.MARK_HERE),
      lab.text() if lab else None)
shot(d, "fd_this_size_only")
d.undo()
pump(0.2)
check("undo removes the size override", "mainAxisSpacing" not in VF.overrides(scr.find(grid["id"]), "medium"))
d.set_hidden(side["id"], "medium", True)
check("hide on this size", VF.is_hidden(scr.find(side["id"]), "medium"))
d.undo()
d.set_edit_mode("all")
d.set_prop(grid["id"], "crossAxisSpacing", 6)
check("All sizes mode edits the base", scr.find(grid["id"])["props"]["crossAxisSpacing"] == 6)
d.undo()

# ---- foldables: Galaxy Z Fold6 postures
d.cbo_device.setCurrentIndex(DEVICE_IDS.index("galaxy_z_fold6"))
pump(0.2)
check("posture combo shown for a foldable", d.size_bar.cbo_posture.isVisibleTo(d.size_bar))
for posture in ("Flat", "HalfOpened", "Folded"):
    d.set_posture(posture)
    pump(0.2)
    shot(d.canvas, f"fd_fold_{posture}")
d.set_posture("HalfOpened")
check("half opened: crease + tabletop size", d.hinge_rect() is not None and "tabletop" in d.active_sizes(),
      (d.hinge_rect(), d.active_sizes()))
d.set_posture("Folded")
check("folded: cover screen, no hinge", d.device_size() == (360, 880) and d.hinge_rect() is None, d.device_size())
d.cbo_device.setCurrentIndex(DEVICE_IDS.index("surface_duo2"))
d._rotate()
pump(0.2)
check("dual screen: hinge band + dual size", d.hinge_rect() is not None and "dual" in d.active_sizes(),
      d.active_sizes())
shot(d.canvas, "fd_duo")
imgs = MU.render_sizes(d, 300)
check("side-by-side renders the base + every size", len(imgs) == len(VF.sizes(scr)) + 1, len(imgs))

# ---- motion editors
m = FlutterDesigner(os.path.join(work, "MotionScreens", "screens", "MotionLab.fscreen.json"), live=False)
m.resize(1300, 900)
m.show()
pump(0.8)
card = next(n for n, *_ in m.screen.walk() if (n.get("anim") or {}).get("type") == "shake")
m.select(card["id"])
pump(0.2)
ex = m.inspector.anim_extra
check("inspector shows the trigger", ex is not None and ex.trigger.currentData() == "tap",
      ex.trigger.currentData() if ex else None)
ex.changed.emit("trigger", "hover")
check("trigger edited", m.screen.find(card["id"])["anim"]["trigger"] == "hover")
ex.changed.emit("repeat", 0)
check("repeat forever", m.screen.find(card["id"])["anim"]["repeat"] == 0)
kd = MU.KeyframesDialog({"opacity": [[0, 0], [300, 1, "Curves.easeOut"]]})
check("keyframes dialog round-trips", kd.tracks() == {"opacity": [[0, 0], [300, 1, "Curves.easeOut"]]}, kd.tracks())
wd = MU.WhenDialog(m.screen, "height", "double", {"$when": {"state": "expanded", "on": 120, "off": 48}})
check("$when dialog round-trips", wd.value() == {"$when": {"state": "expanded", "on": 120, "off": 48}}, wd.value())
check("preview resolves $when / $timeline", not VF.needs_resolve(m.preview_screen()))
box = next(n for n, *_ in m.screen.walk() if n["type"] == "AnimatedContainer")
m.select(box["id"])
pump(0.2)
row = m.inspector.rows.get("height")
check("animated value shown as text", row is not None and row.code.isReadOnly() and
      row.code.text().startswith("expanded ?"), row.code.text() if row else None)
m.play_animations()
pump(0.4)
check("Qt preview plays the motion", m.canvas.anim_t is not None and Q.anim_end(m.screen.tree) > 1000,
      (m.canvas.anim_t, Q.anim_end(m.screen.tree)))
shot(m.canvas, "fd_motion_playing")
check("playback ends", qh.wait(lambda: m.canvas.anim_t is None, Q.anim_end(m.screen.tree) / 1000 + 5))
ok = m.save()
check("save regenerates the Dart code", ok and os.path.exists(os.path.join(work, "MotionScreens", "lib",
                                                                           "radfx.dart")))
d.save()
check("radlayout.dart written for a screen with sizes",
      os.path.exists(os.path.join(work, "ResponsiveScreens", "lib", "radlayout.dart")))
m.shutdown()
d.shutdown()
qh.finish()
