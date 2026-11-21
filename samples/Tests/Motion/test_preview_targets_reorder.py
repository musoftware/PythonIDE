"""Animations dock: design-time preview per target and reordering (offscreen, qh.py harness).

1. Reorder: Move Up / Move Down among the selected control's animations (other controls' animations keep
   their places), undo, drag in the list (rowsMoved) - all through motion.model.move.
2. Preview per target (preview_target = the language of the form):
   * python-tk project (Motion_AnimationsUI): a control fade is the tk fallback (colour fade, no opacity
     effect); a fade of the form itself is drawn on the form frame (FxEffect) and removed on Stop;
   * python-qt project (Motion_Qt_Presets): "Preview as python-qt", Fade In draws real opacity
     (FxEffect = QGraphicsOpacityEffect's look), Rotate stays a wobble (no transform on python-qt);
   * a transform target (the form's language reported as Flutter): Rotate / Zoom draw rotation / scale -
     the grab of the control differs from the designed look - and Stop puts everything back.
   * pure: the segments of each target are the storyboards of motion.expand(form, target).

Run:  python samples/Tests/Motion/test_preview_targets_reorder.py
"""
import os
import shutil
import random
import sys

os.environ.setdefault("QA_NAME", "motion_preview_targets")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "QA", "Integration"))
from qh import ROOT, WORK, check, finish, pump, shot, window  # noqa: E402
from pathlib import Path  # noqa: E402

from PyQt6.QtCore import QModelIndex  # noqa: E402

from radide import motion  # noqa: E402
from radide.features import animations_panel as AP  # noqa: E402
from radide.features.states import FxEffect  # noqa: E402

work = {}
for name in ("Motion_AnimationsUI", "Motion_Qt_Presets"):
    dst = Path(WORK) / (name + "_pv")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(Path(ROOT) / "samples/Tests/Motion" / name, dst, ignore=shutil.ignore_patterns("__pycache__"))
    work[name] = dst

w = window()
w.open_project(work["Motion_AnimationsUI"], ask=False)
pump(1.5)
w.open_designer("Form1")
pump(1.0)
view = w._current_designer()
panel = w.animations_panel
w.dock_animations.show()
w.dock_animations.raise_()
pump(0.3)
doc = view.doc
form = doc.form


def order():
    return [a["id"] for a in form.extra["animations"]]


# ---------------------------------------------------------------- 1. reorder
b1 = form.find("Button1")
doc.select(b1)
pump(0.2)
panel.add("shake", "Button1")
panel.add("pulse", "Button1")
pump(0.2)
ids0 = order()
mine = [a["id"] for a in form.extra["animations"] if a["target"] == "Button1"]
check("Button1 has 3 animations listed", panel.list.count() == 3 and mine == [panel.list.item(i).data(256)
                                                                              for i in range(3)], ids0)
others = {i: ids0.index(i) for i in ids0 if i not in mine}
panel.select(mine[2])
check("last row: Move Down disabled, Move Up enabled", panel.btn_up.isEnabled() and not panel.btn_down.isEnabled())
panel.btn_up.click()
pump(0.2)
now = [a["id"] for a in form.extra["animations"] if a["target"] == "Button1"]
check("Move Up swaps with its shown neighbour", now == [mine[0], mine[2], mine[1]], now)
check("other controls' animations keep their places", all(order().index(i) == p for i, p in others.items()),
      order())
check("list follows and keeps the selection", panel.current_id() == mine[2] and
      panel.list.item(1).data(256) == mine[2])
panel.btn_up.click()
pump(0.2)
check("Move Up again: first", [a["id"] for a in form.extra["animations"] if a["target"] == "Button1"][0] == mine[2])
check("first row: Move Up disabled", not panel.btn_up.isEnabled() and panel.btn_down.isEnabled())
panel.btn_down.click()
pump(0.2)
check("Move Down", [a["id"] for a in form.extra["animations"] if a["target"] == "Button1"]
      == [mine[0], mine[2], mine[1]])
check("modified", doc.modified)
doc.undo()
pump(0.3)
check("undo restores the order", [a["id"] for a in form.extra["animations"] if a["target"] == "Button1"]
      == [mine[2], mine[0], mine[1]], order())
doc.undo()
doc.undo()
pump(0.3)
check("undo x3: the original order", order() == ids0, order())
# drag: the list model moves row 0 below row 2 (what a drop does)
panel.select(mine[0])
ok = panel.list.model().moveRow(QModelIndex(), 0, QModelIndex(), 3)
pump(0.3)
now = [a["id"] for a in form.extra["animations"] if a["target"] == "Button1"]
check("drag (rowsMoved) reorders the form's list", ok and now == [mine[1], mine[2], mine[0]], (ok, now))
check("drag: other controls' animations keep their places",
      all(order().index(i) == p for i, p in others.items()), order())
check("drag: list rebuilt from the model", [panel.list.item(i).data(256) for i in range(3)] == now)
panel.all.setChecked(True)
pump(0.2)
check("Show all controls: buttons move in the whole list",
      panel.list.count() == len(order()))
last = order()[-1]
panel.select(last)
panel.move_current(-1)
check("Show all controls: Move Up moves in the whole list", order()[-2] == last, order())
panel.all.setChecked(False)
doc.undo()
doc.undo()
pump(0.3)
check("undo the move and the drag", order() == ids0, order())
# pure reorder(): random drags of a subset keep the other animations on their places
rng = random.Random(7)
okr = True
for _ in range(200):
    n = rng.randint(2, 8)
    fake = type("F", (), {})()
    fake.extra = {"animations": [{"id": f"a{i}"} for i in range(n)]}
    sub = sorted(rng.sample(range(n), rng.randint(1, n)))
    shown = [f"a{i}" for i in sub]
    new = shown[:]
    rng.shuffle(new)
    AP.reorder(fake, new)
    got = [a["id"] for a in fake.extra["animations"]]
    want = [f"a{i}" for i in range(n)]
    for pos, fid in zip(sub, new):
        want[pos] = fid
    okr = okr and got == want
check("pure reorder(): 200 random drags put the shown ones in order, others keep their places", okr)

# ---------------------------------------------------------------- 2a. python-tk preview
check("python-tk project previews as python-tk", panel.target == "py", panel.target)
check("'Preview as' label", "python-tk" in panel.lab_target.text(), panel.lab_target.text())
lab = form.find("Label1")
doc.select(lab)
pump(0.2)
panel.select("fx2")
segs = AP.segments_for(form, ["fx2"], "py")
props = {p for _s, sb in segs for _t, p, _k in sb["tracks"]}
check("tk fade = colour fallback (no Opacity track)", "Opacity" not in props, props)
panel.preview_current()
panel.show_frame(AP.sb_span(segs[0][1]) / 2)
pump(0.05)
lw = view.previews.get(id(lab))
check("tk: no opacity effect on the label", not isinstance(lw.graphicsEffect(), FxEffect), lw.graphicsEffect())
panel.stop_preview()
# a fade of the form itself (windows can always fade): drawn on the form frame
doc.select(None)
pump(0.2)
fa = panel.add("fadeIn", "")
pump(0.2)
panel.preview_current()
panel.show_frame(150)
pump(0.05)
fe = view.frame.graphicsEffect()
check("form fade drawn on the form frame", isinstance(fe, FxEffect) and 0 < fe.fx_opacity < 1,
      getattr(fe, "fx_opacity", fe))
shot(view, "preview_form_fade")
panel.stop_preview()
pump(0.1)
check("Stop removes the form frame effect", view.frame.graphicsEffect() is None)
doc.undo()
pump(0.2)
check("form animation undone", AP.find(form, fa["id"]) is None)

# ---------------------------------------------------------------- 2b. python-qt preview
w.open_project(work["Motion_Qt_Presets"], ask=False)
pump(1.5)
w.open_designer("Form1")
pump(1.0)
view = w._current_designer()
doc = view.doc
form = doc.form
pump(0.3)
check("panel follows the python-qt designer", panel.view is view)
check("python-qt project previews as python-qt", panel.target == "qt" and "python-qt" in panel.lab_target.text(),
      (panel.target, panel.lab_target.text()))
info = form.find("lblInfo")
doc.select(info)
pump(0.2)
panel.select("fx9")                    # fadeIn on show
segs = AP.segments_for(form, ["fx9"], "qt")
check("qt fade = Opacity track", any(p == "Opacity" for _s, sb in segs for _t, p, _k in sb["tracks"]))
panel.preview_current()
panel.show_frame(AP.sb_span(segs[0][1]) / 2)
pump(0.05)
iw = view.previews.get(id(info))
eff = iw.graphicsEffect()
check("qt: real opacity drawn on the control (FxEffect)", isinstance(eff, FxEffect) and 0 < eff.fx_opacity < 1,
      getattr(eff, "fx_opacity", eff))
shot(view, "preview_qt_fade")
panel.stop_preview()
pump(0.1)
check("Stop: the control's effect is gone", not isinstance(iw.graphicsEffect(), FxEffect))
spin = form.find("btnSpin")
doc.select(spin)
pump(0.2)
panel.select("fx7")                    # rotate: python-qt cannot rotate a widget -> wobble
props = {p for _s, sb in AP.segments_for(form, ["fx7"], "qt") for _t, p, _k in sb["tracks"]}
check("qt rotate = wobble (no Rotation track)", "Rotation" not in props, props)

# ---------------------------------------------------------------- 2c. transform target (Flutter)
orig_pff = w.plugin_for_form


class AsFlutter:
    """The form's language plugin, reporting the Flutter plugin id (what a classic Flutter form has)."""

    def __init__(self, plugin):
        self._p = plugin

    def __getattr__(self, name):
        return "flutter" if name == "id" else getattr(self._p, name)


w.plugin_for_form = lambda name: AsFlutter(orig_pff(name))
check("form language Flutter -> previews as Flutter", panel.target == "dart", panel.target)
panel.refresh_list()
check("label says Flutter", "Flutter" in panel.lab_target.text(), panel.lab_target.text())
sw = view.previews.get(id(spin))
before = sw.grab().toImage()
segs = AP.segments_for(form, ["fx7"], "dart")
check("Flutter rotate = Rotation track", any(p == "Rotation" for _s, sb in segs for _t, p, _k in sb["tracks"]))
panel.preview_current()
panel.show_frame(AP.sb_duration(segs[0][1]) * 0.25)
pump(0.05)
eff = sw.graphicsEffect()
check("Flutter: rotation drawn (FxEffect)", isinstance(eff, FxEffect) and abs(eff.fx_rot) > 1,
      getattr(eff, "fx_rot", eff))
host = sw.parentWidget()
img = host.grab(sw.geometry().adjusted(-30, -30, 30, 30)).toImage()
shot(view, "preview_flutter_rotate")
check("model untouched while previewing", spin.props.get("Rotation") is None)
panel.stop_preview()
pump(0.1)
check("Stop: back to the designed look", not isinstance(sw.graphicsEffect(), FxEffect)
      and sw.grab().toImage() == before)
img2 = host.grab(sw.geometry().adjusted(-30, -30, 30, 30)).toImage()
check("the rotated frame (grab) differs from the designed look", img.size().width() > 0 and img != img2)
pulse = form.find("btnPulse")
doc.select(pulse)
pump(0.2)
panel.select("fx4")                    # zoom on hover
segs = AP.segments_for(form, ["fx4"], "dart")
panel.preview_current()
panel.show_frame(AP.sb_duration(segs[0][1]) * 0.5)
pump(0.05)
eff = view.previews.get(id(pulse)).graphicsEffect()
check("Flutter: zoom drawn as scale (FxEffect)", isinstance(eff, FxEffect) and abs(eff.fx_sx - 1) > 0.01,
      getattr(eff, "fx_sx", eff))
panel.stop_preview()
w.plugin_for_form = orig_pff

# ---------------------------------------------------------------- pure: segments = expand(form, target)
for t in ("py", "qt", "dart", "kivy", "rn"):
    names = sorted(sb["name"] for _s, sb in AP.segments_for(form, None, t))
    want = sorted(sb["name"] for sb in motion.expand(form, t)["storyboards"]
                  if sb["autostart"] or sb["fx"] in ("fx2",))
    check(f"{t}: Preview all on load plays expand(form, {t!r})'s load storyboards", set(want) <= set(names) or
          names == want, (names, want))
check("bake keeps opacity on python-qt", any(tr["property"] == "Opacity" for tr in AP.bake(form, "fx9", "qt")["tracks"]))
check("bake on a non-Python target falls back to the python-tk storyboard",
      not any(tr["property"] == "Rotation" for tr in AP.bake(form, "fx7", "dart")["tracks"]))

finish(w)
