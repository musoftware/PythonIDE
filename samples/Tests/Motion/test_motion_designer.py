"""The IDE with the motion core (offscreen, qh.py harness): the Blend docks still load, an FxPlan storyboard
previews on the design surface through BlendPreview (relative keyframes resolved, model unchanged), the
Timeline panel lists the new easings, renaming a control renames its animations, F5-style code
generation of the open form compiles.

Run:  python samples/Tests/Motion/test_motion_designer.py
"""
import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "motion_designer")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "QA", "Integration"))
from qh import ROOT, WORK, check, finish, pump, shot, window  # noqa: E402
from pathlib import Path  # noqa: E402

src = Path(ROOT) / "samples/Tests/Motion/Motion_Tk_Presets"
d = Path(WORK) / "Motion_Tk_Presets"
shutil.rmtree(d, ignore_errors=True)
shutil.copytree(src, d)

w = window()
w.open_project(d, ask=False)
pump(1.5)
w.open_designer("Form1")
pump(1.0)
view = w._current_designer()
check("designer opened", view is not None)
from radide import motion  # noqa: E402
from radide.features import timeline  # noqa: E402
from radide.features.states import BlendPreview  # noqa: E402

form = view.doc.form
check("animations loaded from the .form", len(motion.animations(form)) == 10, len(motion.animations(form)))
check("Blend docks installed", getattr(w, "dock_states", None) is not None)
check("timeline easings extended", {"back", "elastic", "bounce", "sine"} <= set(timeline.EASES))

plan = motion.expand(form, "py")
sb = next(s for s in plan["storyboards"] if s["fx"] == "fx1")         # lblTitle slideIn from left 120
bp = BlendPreview.of(view)
lbl = form.find("lblTitle")
before = dict(lbl.props)
bp.timeline = (motion.storyboard_dict(sb), 0)
bp.refresh()
pump(0.2)
dp = bp.design_props(lbl)
check("preview at 0 ms: slid out by 120 px", dp["Left"] == before["Left"] - 120, dp.get("Left"))
shot(view, "motion_preview_start")
bp.timeline = (motion.storyboard_dict(sb), 600)
bp.refresh()
pump(0.2)
check("preview at the end: designed Left", bp.design_props(lbl)["Left"] == before["Left"])
bp.timeline = None
bp.refresh()
check("model unchanged by the preview", lbl.props == before)

view.doc.set_prop(lbl, "Name", "lblHeading")
pump(0.2)
check("rename follows animations", sum(a["target"] == "lblHeading" for a in motion.animations(form)) == 2
      and all(a["target"] != "lblTitle" for a in motion.animations(form)))

code = w.plugin_for_form("Form1").generate_designer(form, (d / "Form1.py").read_text(encoding="utf-8"))
compile(code, "Form1_designer.py", "exec")
check("generated designer compiles with the animations", "self._fx = _RadFx(" in code)
finish(w)
