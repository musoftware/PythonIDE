"""Animations in the VB6 runtime (radide/runtimes/vbrun.py) - and so in every GUI-Bridge language.

    python samples/Tests/Motion/check_vb6.py

Runs Motion_VB6 in-process with vbrun: designed animations (click / after / hide / show / timer) run
from the Tk generator, VB code ``lblInfo.Visible = ...`` plays the hide / show animations,
``lblTitle.Animate "slideIn", 500, "from=right"``, ``fx3.Begin`` / ``Storyboard`` objects, bridge-style
``CALL cmdShake Animate shake`` arguments, ``Form1.Animate`` and Animate on a form without animations."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
os.environ["RADIDE_REDUCED_MOTION"] = "0"

FAILS: list[str] = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def main() -> int:
    import subprocess
    subprocess.run([sys.executable, str(HERE / "make_samples.py")], check=True)
    from radide.runtimes.vbrun import Runtime, VBStoryboard
    rt = Runtime(HERE / "Motion_VB6")
    rt.load()
    vf = rt.forms["form1"]
    vf.load()
    vf.vb_call("show", [])
    ui, root = vf.ui, rt.root
    root.geometry("+-2000+-2000")

    def run(ms):
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            root.update()
            time.sleep(0.005)

    def x(name):
        return int(float(getattr(ui, name).place_info().get("x", -1)))
    run(1600)
    check(ui.lblTitle.cget("text") == "Hello, motion!" and x("lblTitle") == 20, "vb: title animations on load")
    check(isinstance(vf.controls.get("fx3"), VBStoryboard), "vb: fx3 is a VB object (fx3.Begin)")
    # bridge style: CALL cmdShake Animate shake  ->  resolve_obj(...).vb_call("animate", ["shake"])
    vf.vb_get("cmdshake").vb_call("animate", ["shake"])
    run(100)
    moved = x("cmdShake")
    run(700)
    check(moved != 20 and x("cmdShake") == 20, f"vb: cmdShake.Animate \"shake\" ({moved} -> {x('cmdShake')})")
    # designed click trigger + after chain (move + bounce) through the Tk generator
    vf.controls["fx5"].vb_call("begin", [])
    run(1300)
    check(x("cmdMove") == 80, f"vb: fx5.Begin then the chained bounce ({x('cmdMove')})")
    # VB code: lblInfo.Visible = Not lblInfo.Visible  plays the hide animation, then hides
    ui.cmdHide_Click()
    run(150)
    check(ui.lblInfo.winfo_manager() == "place", "vb: lblInfo still visible while it fades out")
    run(700)
    check(ui.lblInfo.winfo_manager() == "", "vb: lblInfo hidden after the fade")
    check(vf.controls["lblinfo"].vb_get("visible") in (False, 0), "vb: lblInfo.Visible = False")
    ui.cmdHide_Click()
    run(700)
    check(ui.lblInfo.winfo_manager() == "place" and str(ui.lblInfo.cget("bg")).lower() == "#ffe08a",
          "vb: shown again (fade in), colours back")
    # VB code with options: lblTitle.Animate "slideIn", 500, "from=right"
    ui.lblTitle_Click()
    run(150)
    mid = x("lblTitle")
    run(600)
    check(mid > 20 and x("lblTitle") == 20, f"vb: slideIn from the right ({mid} -> {x('lblTitle')})")
    # Form1.Animate "Command", "preset" and BeginAnimation / StopAnimation
    vf.vb_call("animate", ["btnSpin", "slideOut", "300"])
    run(600)
    check(ui.btnSpin.winfo_manager() == "", "vb: Form1.Animate \"btnSpin\", \"slideOut\"")
    check(vf.vb_call("beginanimation", ["fx3"]) is True and vf.vb_call("stopanimation", ["fx3"]) is True,
          "vb: Form1.BeginAnimation / StopAnimation")
    try:
        vf.vb_get("cmdshake").vb_call("animate", ["nosuch"])
        check(False, "vb: unknown preset raises a VB error")
    except Exception as ex:  # noqa: BLE001
        check("Unknown animation preset" in str(ex), "vb: unknown preset raises a VB error")
    # a form without animations: Animate works too (runtime created on demand)
    from radide.languages.python_tk import PythonTkPlugin
    from radide.model import Form
    from radide.motion.runtime_py import ensure_fx
    f = Form()
    b = f.add("Button", 10, 10)
    ns: dict = {}
    exec(compile(PythonTkPlugin().generate_designer(f, ""), "<plain>", "exec"), ns)
    plain = ns["Form1Designer"](root)
    check("_fx" not in plain.__dict__, "plain form has no animation runtime in its code")
    fx = ensure_fx(plain)
    fx.Animate(b.name, "move", durationMs=200, dx=30)
    run(500)
    check(int(float(getattr(plain, b.name).place_info()["x"])) == 40, "ensure_fx: Animate on a plain form")
    plain.root.destroy()
    root.destroy()
    print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
