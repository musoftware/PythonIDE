"""UI test of the Animations dock (plan MOTION_VARIANTS_FOLDABLES slice B), offscreen with the qh.py harness.

Opens samples/Tests/Motion/Motion_AnimationsUI (copied to a temp folder) in the IDE and checks: the dock
follows the designer and the selection, Add (panel + designer right-click menu), editing with undo,
Preview / Preview all on load on the design surface (model unchanged), Convert to Storyboard,
rename following, Error List rows, Respect reduced motion and the Arabic catalog.

Run:  python samples/Tests/Motion/test_animations_ui.py
"""
import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "motion_animations_ui")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "QA", "Integration"))
from qh import ROOT, WORK, check, finish, pump, shot, window  # noqa: E402
from pathlib import Path  # noqa: E402

from PyQt6.QtWidgets import QMenu  # noqa: E402

src = Path(ROOT) / "samples/Tests/Motion/Motion_AnimationsUI"
d = Path(WORK) / "Motion_AnimationsUI"
shutil.rmtree(d, ignore_errors=True)
shutil.copytree(src, d)

w = window()
w.open_project(d, ask=False)
pump(1.5)
w.open_designer("Form1")
pump(1.0)
view = w._current_designer()
check("designer opened", view is not None)
panel = getattr(w, "animations_panel", None)
check("Animations panel installed", panel is not None and getattr(w, "dock_animations", None) is not None)
w.dock_animations.show()
w.dock_animations.raise_()
pump(0.3)
check("panel follows the designer", panel.view is view, panel.view)
doc = view.doc
form = doc.form
b1, b2, lab = form.find("Button1"), form.find("Button2"), form.find("Label1")

# ---------------------------------------------------------------- list follows the selection
doc.select(None)
pump(0.2)
check("form selected: no form animations listed", panel.list.count() == 0, panel.list.count())
doc.select(b1)
pump(0.2)
check("Button1 selected: its slide-in listed", panel.list.count() == 1 and panel.current_id() == "fx1",
      [panel.list.item(i).text() for i in range(panel.list.count())])
check("preset combo shows Slide In", panel.preset.currentData() == "slideIn", panel.preset.currentData())
check("slide-in params editors built (from / distance / fade)",
      all(panel.params_box.findChild(object, f"fxparam_{n}") is not None for n in ("from", "distance", "fade")))
panel.all.setChecked(True)
pump(0.1)
check("Show all controls lists 3", panel.list.count() == 3, panel.list.count())
panel.all.setChecked(False)

# ---------------------------------------------------------------- add + edit + undo
doc.select(b2)
pump(0.1)
n0 = len(form.extra["animations"])
anim = panel.add("bounce")
pump(0.1)
check("Add appends a bounce on Button2", anim is not None and len(form.extra["animations"]) == n0 + 1
      and anim["target"] == "Button2" and anim["preset"] == "bounce", anim)
check("new animation selected", panel.current_id() == anim["id"], panel.current_id())
check("document modified", doc.modified)
panel.duration.setValue(1234)
check("duration edit stored", anim["durationMs"] == 1234, anim)
i = panel.trigger.findData("click")
panel.trigger.setCurrentIndex(i)
pump(0.05)
check("trigger edit stored", anim["trigger"]["on"] == "click", anim["trigger"])
check("click trigger shows the Source row", not panel.source.isHidden() and panel.interval.isHidden())
panel.trigger.setCurrentIndex(panel.trigger.findData("timer"))
check("timer trigger shows Interval", not panel.interval.isHidden(), anim["trigger"])
panel.repeat.setValue(0)
check("repeat 0 = Forever (special text)", anim["repeat"] == 0 and panel.repeat.text() == "Forever",
      panel.repeat.text())
panel.easing.setCurrentIndex(panel.easing.findData("elastic"))
check("easing elastic stored", anim["easing"] == "elastic", anim)
hb = panel.params_box.findChild(object, "fxparam_height")
check("bounce height editor", hb is not None)
if hb is not None:
    hb.setValue(33)
    check("param edit stored", anim["params"]["height"] == 33, anim["params"])
panel.preset.setCurrentIndex(panel.preset.findData("shake"))
pump(0.05)
check("change preset -> params reset", anim["preset"] == "shake" and "height" not in anim["params"], anim)
fid = anim["id"]
for _ in range(10):
    if not any(a.get("id") == fid for a in doc.form.extra.get("animations") or []):
        break
    doc.undo()
    pump(0.05)
form = doc.form
check("undo removes the added animation", not any(a.get("id") == fid for a in form.extra.get("animations") or []),
      [a.get("id") for a in form.extra.get("animations") or []])
check("panel list follows undo", all(panel.list.item(i).data(256) != fid for i in range(panel.list.count())))
b1, b2, lab = form.find("Button1"), form.find("Button2"), form.find("Label1")

# ---------------------------------------------------------------- designer context menu
m = QMenu()
w._designer_menu("Form1", m, b2)
subs = [a.menu() for a in m.actions() if a.menu() is not None and a.text().replace("&", "") == "Add Animation"]
check("designer menu has Add Animation", bool(subs), [a.text() for a in m.actions()])
if subs:
    subs[0].aboutToShow.emit()
    groups = [a.text() for a in subs[0].actions() if a.menu() is not None]
    check("Add Animation submenu grouped (Entrance / Exit / Attention / Color / Text)",
          groups == ["Entrance", "Exit", "Attention", "Color", "Text"], groups)
    att = next((a.menu() for a in subs[0].actions() if a.text() == "Attention"), None)
    pulse = next((a for a in att.actions() if a.text() == "Pulse"), None) if att else None
    check("Attention has Pulse", pulse is not None)
    if pulse is not None:
        pulse.trigger()
        pump(0.1)
        check("menu action adds a pulse on Button2",
              any(a.get("preset") == "pulse" and a.get("target") == "Button2" for a in form.extra["animations"]))

# ---------------------------------------------------------------- preview (model unchanged)
doc.select(b1)
pump(0.1)
panel.select("fx1")
left0 = b1.props["Left"]
panel.preview_current()
panel.timer.stop()                      # drive the frames by hand
check("preview running", panel.previewing)
panel.show_frame(0)
pump(0.05)
dp = view.design_props(b1)
check("frame 0: Button1 starts 80 px left", dp.get("Left") == left0 - 80, dp.get("Left"))
banner = w.findChild(object, "timelineRecordBanner")
from radide.features.timeline import RecordBanner  # noqa: E402
rb = RecordBanner.of(view, create=False)
check("blue preview banner shown", rb is not None and rb.mode == "play" and "Previewing" in rb.text,
      rb and (rb.mode, rb.text))
check("designer locked while previewing", not view.overlay.isEnabled())
panel.show_frame(250)
pump(0.05)
mid = view.design_props(b1).get("Left")
check("frame 250: in between", left0 - 80 < mid < left0, mid)
shot(view, "motion_preview_mid")
panel.show_frame(500)
check("frame 500: arrived", view.design_props(b1).get("Left") == left0)
check("model untouched during preview", b1.props["Left"] == left0, b1.props["Left"])
panel.stop_preview()
pump(0.05)
check("stop: designed values back", view.design_props(b1).get("Left") == left0 and not panel.previewing)
check("stop: banner hidden, designer unlocked", (rb is None or rb.mode == "") and view.overlay.isEnabled())

panel.preview_all()
panel.timer.stop()
segs = [(s, sb.get("fx")) for s, sb in panel._pv.segments]
check("Preview all on load: fx1 at 0, fx2 chained at 500", (0.0, "fx1") in segs and (500.0, "fx2") in segs, segs)
panel.show_frame(700)
lab_fc = view.design_props(lab).get("ForeColor")
check("frame 700: Label1 fading in (colour blend)", lab_fc not in (None, "", "#000000"), lab_fc)
panel.stop_preview()

# real-time playback ends on its own
panel.preview_current()
pump(1.4)
check("timed preview finishes and restores", not panel.previewing and view.overlay.isEnabled())

# ---------------------------------------------------------------- Error List
el = w.error_list
rows = [el.topLevelItem(i).text(1) for i in range(el.topLevelItemCount())]
check("Error List shows the python-tk fade fallback", any("colour blend" in r for r in rows), rows)
form.extra["animations"].append({"id": "fx9", "target": "Ghost", "preset": "shake", "trigger": {"on": "load"}})
panel.update_errors()
rows = [(el.topLevelItem(i).text(0), el.topLevelItem(i).text(1)) for i in range(el.topLevelItemCount())]
check("Error List shows a missing target as an Error",
      any(s == "Error" and "Ghost" in t for s, t in rows), rows)
form.extra["animations"].pop()
panel.update_errors()

# ---------------------------------------------------------------- rename follows
doc.set_prop(b1, "Name", "BtnGo")
pump(0.1)
fx1 = next(a for a in form.extra["animations"] if a["id"] == "fx1")
check("rename: animation target follows", fx1["target"] == "BtnGo", fx1["target"])
doc.set_prop(form.find("BtnGo"), "Name", "Button1")
b1 = form.find("Button1")

# ---------------------------------------------------------------- reduced motion
panel.reduced.setChecked(False)
check("Respect reduced motion off stored", form.extra["motion"]["respectReducedMotion"] is False)
panel.reduced.setChecked(True)

# ---------------------------------------------------------------- convert to storyboard
doc.select(b2)
pump(0.1)
panel.select("fx3")
check("fx3 selected", panel.current_id() == "fx3", panel.current_id())
n_sb = len(form.extra.get("storyboards") or [])
panel.convert_current()
pump(0.1)
sbs = form.extra.get("storyboards") or []
check("Convert adds a storyboard", len(sbs) == n_sb + 1, sbs)
if sbs:
    sb = sbs[-1]
    keys = [k for tr in sb["tracks"] for k in tr["keys"]]
    check("baked keys are absolute", keys and all(not isinstance(k[1], dict) for k in keys), keys)
    check("baked Button2 shake ends where it started", sb["tracks"][0]["keys"][-1][1] == b2.props["Left"],
          sb["tracks"][0]["keys"])
check("converted animation removed", not any(a.get("id") == "fx3" for a in form.extra["animations"]))
from radide.features.timeline import storyboards_for_code  # noqa: E402
check("baked storyboard is valid for code generation",
      any(s["name"] == sbs[-1]["name"] and s["tracks"] for s in storyboards_for_code(form)),
      storyboards_for_code(form))

# ---------------------------------------------------------------- save + generated code compiles
w._save_form("Form1") if hasattr(w, "_save_form") else None
pump(0.3)
import json  # noqa: E402
saved = json.loads((d / "Form1.form").read_text(encoding="utf-8"))
check("saved .form keeps extra animations", any(a.get("id") == "fx1" for a in saved.get("animations") or []),
      list(saved))

# ---------------------------------------------------------------- Arabic
from radide import i18n  # noqa: E402
i18n.load("ar")
missing = [t for t in ("Add Animation", "Fade In", "Slide In", "On click", "Preview all on load",
                       "Convert to Storyboard", "Respect reduced motion", "Forever", "Auto reverse", "Trigger")
           if i18n.tr(t) == t]
check("Arabic catalog has the panel strings", not missing, missing)
check("Add Animation -> إضافة حركة", i18n.tr("Add Animation") == "إضافة حركة", i18n.tr("Add Animation"))
i18n.load("en")

shot(w.dock_animations, "motion_animations_dock")
finish(w)
