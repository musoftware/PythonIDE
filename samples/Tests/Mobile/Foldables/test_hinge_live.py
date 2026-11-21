"""The Error List hinge warning follows the designer, and the device labels are translated.

Offscreen with the qh.py harness (test QSettings "RADIDE-TEST", cleared at the end). Opens a temp copy of
samples/Tests/Mobile/Foldables/FoldDemo:

* DuoHinge (Surface Duo 2, Button1 across the 26 dp hinge): the "Controls cross the hinge" row appears in the
  Error List without running the checks; moving Button1 off the hinge removes it, undo brings it back,
  Posture Folded (one screen) removes it, rows are never duplicated after a full run_checks();
* the DeviceBar device combo in Arabic (radide.devices.display_name, relabel on a language change), the
  variants / Flutter designer helpers (describe_when with tr) - and back to English.

Run:  python samples/Tests/Mobile/Foldables/test_hinge_live.py
"""
import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "foldables_hinge_live")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "QA", "Integration"))
from qh import ROOT, WORK, check, finish, pump, shot, wait, window  # noqa: E402
from pathlib import Path  # noqa: E402

src = Path(ROOT) / "samples/Tests/Mobile/Foldables/FoldDemo"
d = Path(WORK) / "FoldDemoLive"
shutil.rmtree(d, ignore_errors=True)
shutil.copytree(src, d)

w = window()
w.open_project(d, ask=False)
pump(1.5)
el = w.error_list
el.clear()
w.open_designer("DuoHinge")
pump(0.3)
view = w._current_designer()
doc = view.doc
form = doc.form


def rows():
    out = []
    for i in range(el.topLevelItemCount()):
        it = el.topLevelItem(i)
        if it.text(2) == "DuoHinge.form" and "cross the hinge" in it.text(1):
            out.append(it.text(1))
    return out


check("hinge row appears when the designer opens (no build / save)", wait(lambda: len(rows()) == 1, 5),
      rows())
check("row names Button1", rows() and "Button1" in rows()[0], rows())
check("Error List title counts it", "warning" in w.dock_errors.windowTitle(), w.dock_errors.windowTitle())

b1 = form.find("Button1")
doc.checkpoint()
doc.set_prop(b1, "Left", 700)
check("moving Button1 off the hinge removes the row", wait(lambda: rows() == [], 5), rows())
doc.undo()
check("undo: the row is back", wait(lambda: len(rows()) == 1, 5), rows())

from radide.tools import run_checks  # noqa: E402
run_checks(w)
pump(0.1)
doc.set_prop(form.find("Button1"), "Width", 250)          # still across: refreshed, not duplicated
pump(0.6)
check("after run_checks + an edit: still exactly one row", len(rows()) == 1, rows())

bar = view.phone.bar
bar.posture_buttons["Folded"].click()
check("Posture Folded (one screen): no hinge, row removed", wait(lambda: rows() == [], 5), rows())
doc.undo()
check("undo the posture: row back", wait(lambda: len(rows()) == 1, 5), rows())

# another form's rows are left alone
w.open_designer("MasterDetail")
pump(0.6)
check("opening another foldable form keeps DuoHinge's row", len(rows()) == 1, rows())
w.open_designer("DuoHinge")
pump(0.3)

# ---------------------------------------------------------------- translated device labels
from radide import devices as D, i18n  # noqa: E402
from radide.flutterdesign import variants_fd as VF  # noqa: E402

i18n.load("ar")
check("display_name in Arabic", D.display_name("small_phone") == "هاتف صغير (360 x 640)",
      D.display_name("small_phone"))
check("proper names stay", D.display_name("iphone_15").startswith("iPhone 15"), D.display_name("iphone_15"))
check("short_name in Arabic", D.short_name("tablet") == "جهاز لوحي", D.short_name("tablet"))
check("every device name translated or a proper name",
      all(D.display_name(x) != x.name or x.name.split(" (")[0].split()[0] in ("iPhone", "iPad", "Galaxy")
          for x in D.DEVICES.values()), [x.name for x in D.DEVICES.values() if D.display_name(x) == x.name])
bar.relabel()
texts = [bar.combo.itemText(i) for i in range(bar.combo.count())]
check("DeviceBar combo relabelled in Arabic", "هاتف صغير (360 x 640)" in texts and
      any("شاشتان" in t for t in texts), texts)
check("combo data (device ids) unchanged", bar.combo.itemData(bar.combo.currentIndex()) == "surface_duo2")
desc = VF.describe_when({"minWidth": 600, "maxWidth": 1023, "orientation": "portrait"}, i18n.tr)
check("Flutter designer size condition in Arabic", desc.startswith("عرض 600-1023") and "عمودي" in desc, desc)
check("describe_when without tr unchanged", VF.describe_when({"maxWidth": 599}) == "<= 599 wide")
shot(bar, "devicebar_ar")
i18n.load("en")
bar.relabel()
check("back to English", bar.combo.itemText(bar.combo.findData("small_phone")) == "Small phone (360 x 640)")

finish(w)
