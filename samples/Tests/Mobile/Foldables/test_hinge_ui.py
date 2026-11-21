"""UI test of the foldable designer (plan MOTION_VARIANTS_FOLDABLES slice E), offscreen with the qh.py harness.

Opens samples/Tests/Mobile/Foldables/FoldDemo (copied to a temp folder) and checks: the DeviceBar posture
buttons (only for foldables), the form size per posture, undo, the hinge layer above the control previews,
the TwoPane split following the posture, PhoneChrome.preview() (form untouched), the red outline + Error
List warning for a control across the Surface Duo hinge, the Create Foldable Emulator menu item, the
Toolbox TwoPane tool.  A grab of the designer per posture goes to the QA shots folder.

Run:  python samples/Tests/Mobile/Foldables/test_hinge_ui.py
"""
import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "foldables_ui")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "QA", "Integration"))
from qh import ROOT, WORK, check, finish, pump, shot, window  # noqa: E402
from pathlib import Path  # noqa: E402

src = Path(ROOT) / "samples/Tests/Mobile/Foldables/FoldDemo"
d = Path(WORK) / "FoldDemo"
shutil.rmtree(d, ignore_errors=True)
shutil.copytree(src, d)

w = window()
w.open_project(d, ask=False)
pump(1.5)
w.open_designer("MasterDetail")
pump(1.0)
view = w._current_designer()
check("designer opened", view is not None)
ch = view.phone
doc = view.doc
form = doc.form
check("phone mode", ch.active)
bar = ch.bar
check("posture buttons shown for a foldable", all(b.isVisibleTo(bar) for b in bar.posture_buttons.values()))
check("Flat checked", bar.posture_buttons["Flat"].isChecked())
check("hinge layer above previews", ch.hinge_layer is not None and ch.hinge_layer.isVisibleTo(view.surface))
kids = view.surface.children()
check("hinge layer below the selection overlay",
      kids.index(ch.hinge_layer) < kids.index(view.overlay) if ch.hinge_layer in kids else False)
shot(view, "fold6_flat")
flat_size = (form.props["Width"], form.props["Height"])
check("Fold6 flat size", flat_size == (882, 1064), flat_size)

bar.posture_buttons["Folded"].click()
pump(0.6)
check("Folded: cover screen size", (form.props["Width"], form.props["Height"]) == (360, 840),
      (form.props["Width"], form.props["Height"]))
tp = form.find("TwoPane1")
c1, c2 = form.find("Column1"), form.find("Column2")
check("Folded: TwoPane shows one pane", c1.props["Width"] == tp.props["Width"] and c2.props["Left"] >
      tp.props["Width"], (c1.props, c2.props["Left"], tp.props["Width"]))
check("Folded checked", bar.posture_buttons["Folded"].isChecked())
check("surface follows the cover size", view.surface.width() == 360, view.surface.width())
shot(view, "fold6_folded")

bar.posture_buttons["HalfOpened"].click()
pump(0.6)
check("HalfOpened: inner size again", (form.props["Width"], form.props["Height"]) == flat_size)
check("HalfOpened: panes at the fold", c1.props["Width"] == 441 and c2.props["Left"] == 441,
      (c1.props["Width"], c2.props["Left"]))
shot(view, "fold6_halfopen")

doc.undo()
pump(0.6)
check("undo posture -> Folded", form.props.get("Posture") == "Folded", form.props.get("Posture"))
doc.undo()
pump(0.6)
check("undo posture -> Flat", form.props.get("Posture") == "Flat" and
      (form.props["Width"], form.props["Height"]) == flat_size, form.props.get("Posture"))

bar.buttons["Landscape"].click()
pump(0.6)
tp, c1, c2 = form.find("TwoPane1"), form.find("Column1"), form.find("Column2")     # undo replaced them
check("landscape: top/bottom panes", c1.props["Width"] == tp.props["Width"] and c2.props["Top"] > 0,
      (c1.props, c2.props))
shot(view, "fold6_landscape")
doc.undo()
pump(0.5)

# ---------------------------------------------------------------- preview() leaves the form alone
before = form.snapshot()
ch.preview("surface_duo2", "Landscape", "Flat")
pump(0.5)
check("preview draws another device", ch.previewing and view.surface.width() == 1106, view.surface.width())
check("preview: form untouched", form.snapshot() == before)
check("preview: device bar disabled", not bar.combo.isEnabled())
shot(view, "preview_duo")
ch.preview()
pump(0.5)
check("preview() ends the preview", not ch.previewing and view.surface.width() == 882 and bar.combo.isEnabled())
check("form untouched after preview", form.snapshot() == before)

# ---------------------------------------------------------------- a phone form has no posture
doc.set_prop(None, "Device", "pixel")
pump(0.5)
check("phone: posture buttons hidden", not any(b.isVisibleTo(bar) for b in bar.posture_buttons.values()))
check("phone size", (form.props["Width"], form.props["Height"]) == (412, 867))
doc.undo()
pump(0.5)
check("back to the Fold6", form.props["Device"] == "galaxy_z_fold6" and form.props["Width"] == 882)

# ---------------------------------------------------------------- Surface Duo: conflict outline + Error List
w.open_designer("DuoHinge")
pump(1.0)
v2 = w._current_designer()
check("Duo designer", v2 is not None and v2.phone.active)
check("Duo conflict detected in the designer", [n for n, _ in v2.phone.conflicts()] == ["Button1"],
      v2.phone.conflicts())
img = v2.phone.hinge_layer.grab().toImage()
bt = v2.doc.form.find("Button1")
red = img.pixelColor(int(bt.props["Left"]) - 1, int(bt.props["Top"]) + 10)
check("red dashed outline drawn", red.red() > 180 and red.green() < 90, red.name())
hx = 540 + 13
band = img.pixelColor(hx, 200)
check("opaque hinge band drawn", band.lightness() < 60, band.name())
shot(v2, "duo_conflict")
from radide.tools import run_checks  # noqa: E402
diags = run_checks(w)
hits = [dg for dg in diags if "cross the hinge" in dg.message]
check("Error List warning", len(hits) == 1 and hits[0].severity == "Warning" and "Button1" in hits[0].message,
      [dg.message for dg in diags][:5])
v2.doc.set_prop(v2.doc.form.find("Button1"), "Left", 700)
pump(0.3)
check("conflict gone after moving", v2.phone.conflicts() == [])
check("Error List clean", not [dg for dg in run_checks(w) if "cross the hinge" in dg.message])

# ---------------------------------------------------------------- menu + toolbox
acts = []
for a in w.menuBar().actions():
    m = a.menu()
    if m is not None:
        for b in m.actions():
            if b.menu() is not None:
                acts += [c.text() for c in b.menu().actions()]
check("Create Foldable Emulator menu item", any("Create Foldable Emulator" in t for t in acts))
from radide.toolbox import control_icon  # noqa: E402
check("TwoPane toolbox icon", not control_icon("TwoPane").isNull())
finish(w)
