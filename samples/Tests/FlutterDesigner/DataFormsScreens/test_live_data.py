"""Designer + live (real Flutter) preview of the data widgets, Lottie and the project theme refresh.
Needs Flutter (the preview host is built once, a few minutes); SKIPs without it. From the repository root:

    python samples/Tests/FlutterDesigner/DataFormsScreens/test_live_data.py

Catalog: the ListView.builder / GridView.builder templates are expanded in both previews, a click on a copy
selects the template; SignUp: Form / validators / RadioGroup render without errors; Pulse: the Lottie node plays
in the live host (no error issue) and the Qt canvas draws its first frame; saving a project theme
(designer.refresh_project_theme) refreshes the canvas colours and sends the theme to the live preview.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "QA", "Integration"))
os.environ.setdefault("QA_NAME", "fd-live-data")
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

from radide.flutterdesign import live as LV, themes as TH  # noqa: E402
from radide.flutterdesign.designer import FlutterDesigner, refresh_project_theme  # noqa: E402

if not LV._flutter()[0]:
    print("SKIP: Flutter SDK not found")
    qh.finish()
if not LV.host_ready():
    print("building the preview host (once per Flutter version) ...", flush=True)
    LV.build_host_sync(log=lambda s: None)

work = os.path.join(qh.WORK, "fd_live_data")
shutil.rmtree(work, ignore_errors=True)
for sub in ("screens", "assets"):
    shutil.copytree(os.path.join(HERE, sub), os.path.join(work, sub))
shutil.copy2(os.path.join(HERE, "pubspec.yaml"), os.path.join(work, "pubspec.yaml"))


def errors(lv):
    return [i for i in lv.issues if i.get("level") == "error"]


def open_screen(name):
    d = FlutterDesigner(os.path.join(work, "screens", f"{name}.fscreen.json"), live=True)
    d.resize(1400, 950)
    d.show()
    check(f"{name}: live preview ready", wait(lambda: d.live_ready, 180))
    return d


# ---- Catalog: item templates
d = open_screen("Catalog")
lv = d.live
lst = next(n for n, *_ in d.screen.walk() if n.get("type") == "ListView")
card = lst["slots"]["itemBuilder"]
check("live: template copies rendered (first copy + <id>~2)",
      wait(lambda: card["id"] in lv.rects and f"{card['id']}~2" in lv.rects, 30), sorted(lv.rects)[:8])
check("qt canvas: template copies laid out", card["id"] in d.canvas.bounds and f"{card['id']}~3" in d.canvas.bounds)
d.select(f"{card['id']}~3", source="live")
check("clicking a copy selects the template", d.selected == card["id"], d.selected)
check("Catalog: no live runtime errors", not errors(lv), errors(lv)[:3])
pump(0.5)
shot(lv.view.focusProxy() or d.live_box, "fd_live_catalog")
shot(d.canvas, "fd_qt_catalog")

# ---- project theme refresh (App Theme editor > Save calls refresh_project_theme)
before = d.scheme()["primary"].name()
TH.save(work, TH.new_theme(seedColor="#FFD32F2F"))
check("refresh_project_theme refreshed the open designer", refresh_project_theme(work) == 1)
check("canvas colours follow the saved project theme", d.scheme()["primary"].name() != before,
      (before, d.scheme()["primary"].name()))
check("live preview got the project theme", (lv.app_theme or {}).get("seedColor") == "#FFD32F2F", lv.app_theme)
pump(1.0)
shot(d.live_box, "fd_live_catalog_theme")
os.remove(os.path.join(work, TH.THEME_FILE))
d.shutdown()
d.close()

# ---- SignUp: Form, validators, RadioGroup
d = open_screen("SignUp")
lv = d.live
radios = [n["id"] for n, *_ in d.screen.walk() if n.get("type") in ("Radio", "RadioListTile")]
check("live: radios rendered", wait(lambda: all(r in lv.rects for r in radios), 30), radios)
check("SignUp: no live runtime errors", not errors(lv), errors(lv)[:3])
pump(0.5)
shot(d.live_box, "fd_live_signup")
d.shutdown()
d.close()

# ---- Pulse: Lottie + timeline values
d = open_screen("Pulse")
lv = d.live
lot = next(n for n, *_ in d.screen.walk() if n.get("type") == "Lottie")
check("live: Lottie node rendered", wait(lambda: lot["id"] in lv.rects, 30))
pump(2.0)
check("Lottie: no live issues on the node", not lv.issues_of(lot["id"]), lv.issues_of(lot["id"]))
check("Pulse: no live runtime errors", not errors(lv), errors(lv)[:3])
shot(lv.view.focusProxy() or d.live_box, "fd_live_pulse")
shot(d.canvas, "fd_qt_pulse")
print(json.dumps({"rects": len(lv.rects)}))
d.shutdown()
qh.finish()
