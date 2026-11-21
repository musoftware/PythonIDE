"""Live language switch (Tools > Options > Language) for the size / device bars that radide.i18n does not reach
(texts inside the form designer and combo-box items): the classic sizes bar ("Edit:", "Size:"), the mobile device
bar ("Device:", "Posture:", device names), the Flutter designer device combo and the Flutter live preview combo.
Real IDE, offscreen, qh.py harness (QSettings org RADIDE-TEST, widget.grab only).

    python samples/Tests/QA/MotionE2E/test_relabel.py
"""
import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "motion_relabel")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Integration"))
from qh import ROOT, WORK, app, check, finish, pump, shot, window  # noqa: E402
from pathlib import Path  # noqa: E402

from radide import i18n  # noqa: E402
from radide.i18n import shown  # noqa: E402

src = Path(ROOT) / "samples/Tests/Mobile/Foldables/FoldDemo"
d = Path(WORK) / "FoldDemo_relabel"
shutil.rmtree(d, ignore_errors=True)
shutil.copytree(src, d)
w = window()
w.open_project(d, ask=False)
pump(1.5)
w.open_designer("MasterDetail")
pump(1.0)
view = w._current_designer()
from radide.features import variants as fv  # noqa: E402
fv.attach(view) if getattr(view, "_variant_bar", None) is None else None
pump(0.3)
vbar, dbar = view._variant_bar, view.phone.bar

from radide.flutterdesign.designer import DEVICES, FlutterDesigner  # noqa: E402
from radide.flutterdesign.live import DEVICES as LIVE_DEVICES, PreviewPane  # noqa: E402
fd_src = Path(ROOT) / "samples/Tests/FlutterDesigner/ResponsiveScreens"
fdw = Path(WORK) / "fd_relabel"
shutil.rmtree(fdw, ignore_errors=True)
(fdw / "screens").mkdir(parents=True)
shutil.copy2(fd_src / "screens" / "Gallery.fscreen.json", fdw / "screens" / "Gallery.fscreen.json")
shutil.copy2(fd_src / "pubspec.yaml", fdw / "pubspec.yaml")
fd = FlutterDesigner(fdw / "screens" / "Gallery.fscreen.json", live=False)
fd.resize(1200, 800)
fd.show()
pane = PreviewPane()
pump(0.5)


def texts():
    return {"edit": shown(vbar.lbl_edit), "size": shown(vbar.lbl_size), "device": shown(dbar.device_label),
            "posture": shown(dbar.posture_label), "dev0": dbar.combo.itemText(0),
            "fd0": fd.cbo_device.itemText(0), "live": [pane.cbo_device.itemText(i) for i in range(pane.cbo_device.count())]}


en = texts()
check("English labels", en["edit"] == "Edit:" and en["size"] == "Size:" and en["device"] == "Device:"
      and en["posture"] == "Posture:", en)
i18n.set_language(app, "ar")
pump(0.6)
ar = texts()
changed = [k for k in en if ar[k] == en[k]]
check("after switching to Arabic every label / first device name changed", not changed, (changed, ar))
check("Arabic texts", not ar["edit"].isascii() and not ar["device"].isascii(), ar)
check("Flutter designer device combo relabelled", ar["fd0"] != en["fd0"] and ar["fd0"].endswith(
    f"{DEVICES[0][1]}x{DEVICES[0][2]}"), ar["fd0"])
from radide.flutterdesign.live import _tr_name  # noqa: E402
want = [f"{_tr_name(n)}  {w_}x{h_}" for n, w_, h_, _pf in LIVE_DEVICES]
check("Flutter live preview combo relabelled (generic names translated)", ar["live"] == want
      and any(not t.split("  ")[0].isascii() for t in ar["live"]), ar["live"])
shot(view, "relabel_designer_ar")
i18n.set_language(app, "en")
pump(0.6)
back = texts()
check("back to English: the same texts as before", back == en, (back, en))
fd.close()
pane.close()
finish(w)
