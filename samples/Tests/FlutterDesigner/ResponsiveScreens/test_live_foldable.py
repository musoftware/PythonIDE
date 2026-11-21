"""Live (real Flutter) preview of per-size overrides on foldables (plan MOTION_VARIANTS_FOLDABLES.md slice F).
Needs Flutter (the preview host is built once, a few minutes); SKIPs without it. From the repository root:

    python samples/Tests/FlutterDesigner/ResponsiveScreens/test_live_foldable.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "QA", "Integration"))
os.environ.setdefault("QA_NAME", "fd-live-fold")
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

from radide.flutterdesign import live as LV, model as M  # noqa: E402
from radide.flutterdesign.designer import DEVICE_IDS, FlutterDesigner  # noqa: E402

if not LV._flutter()[0]:
    print("SKIP: Flutter SDK not found")
    qh.finish()
if not LV.host_ready():
    print("building the preview host (once per Flutter version) ...", flush=True)
    LV.build_host_sync(log=lambda s: None)

work = os.path.join(qh.WORK, "fd_live_fold")
shutil.rmtree(work, ignore_errors=True)
shutil.copytree(os.path.join(HERE, "screens"), os.path.join(work, "screens"))
shutil.copy2(os.path.join(HERE, "pubspec.yaml"), os.path.join(work, "pubspec.yaml"))
d = FlutterDesigner(os.path.join(work, "screens", "Gallery.fscreen.json"), live=True)
d.resize(1400, 950)
d.show()
check("live preview ready", wait(lambda: d.live_ready, 180))
lv = d.live
scr = d.screen
side = next(n for n, *_ in scr.walk() if (n.get("props") or {}).get("width") == 200)
half = next(n for n, *_ in scr.walk() if str((n.get("props") or {}).get("data", "")).startswith("Half-open"))


def visible(nid):
    r = lv.rects.get(nid)
    return r is not None and r.width() > 1 and r.height() > 1


check("phone: compact hides the sidebar (live)", wait(lambda: lv.rects and not visible(side["id"]), 30),
      lv.rects.get(side["id"]))
shot(d.live_box, "fd_live_phone")
d.cbo_device.setCurrentIndex(DEVICE_IDS.index("galaxy_z_fold6"))
d.set_posture("HalfOpened")
check("device message carries the fold", lv.device.get("features") and lv.device["features"][0]["type"] == "fold",
      lv.device.get("features"))
check("half-opened fold: tabletop shows the sidebar and the half-open text (live)",
      wait(lambda: visible(side["id"]) and visible(half["id"]), 30),
      (lv.rects.get(side["id"]), lv.rects.get(half["id"])))
pump(1.0)
shot(d.live_box, "fd_live_fold_half")
d.set_edit_mode("size")
d.set_edit_size("tabletop")
pump(0.5)
check("orange frame around the live view in This size only mode",
      d.live_box.layout().contentsMargins().left() == 4)
issues = [i for i in lv.issues if i.get("level") == "error"]
check("no live runtime errors", not issues, issues[:3])
d.shutdown()
qh.finish()
