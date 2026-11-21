"""Runtime bugs found by the end-to-end QA (qa_motion_e2e.py), with their regression checks.

1. Two animations on the same control at the same time: a Slide In and a Pulse both
"On load" on one button. Both move Left (the pulse fallback grows the button around its centre), so before the
fix the pulse remembered Left at the moment it began (the slide's start, 80 px to the left), gave it back when it
ended and the button stayed off its designed place. Rule now, in every runtime with fallbacks and in the
design-time preview: the animation that started first keeps a property until it ends, and a later one starts
from where the first one ends.
2. Ring TwoPane nested in a container: RADIDE_HINGE (window coordinates) was converted with the pane's position
in its parent only, so a nested pane split at the wrong place. Now the position in the window is used.

    python samples/Tests/QA/MotionE2E/check_runtime_fixes.py

Checks: the python-tk runtime (child process), the design-time preview (FxPreview of the Animations panel), Ring
(ring.exe, offscreen), WinForms C# and VB.NET (dotnet build + RADIDE_FX_SELFTEST on temp copies). Steps whose
toolchain is missing are skipped. Exit code 0 = all passed."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Motion" / "Targets"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from target_tools import check, ring_exe, ring_run, skip, summary, winforms_case  # noqa: E402
from proj import write_project  # noqa: E402

from radide import motion  # noqa: E402
from radide.model import Form  # noqa: E402

WORK = Path(tempfile.gettempdir()) / "radide-qa" / "overlap"


def build(f: Form) -> None:
    def add(kind, name, x, y, w, h, **p):
        c = f.add(kind, x, y)
        c.props.update(Name=name, Left=x, Top=y, Width=w, Height=h, **p)
    add("Button", "btnGo", 40, 40, 120, 32, Text="Go")
    add("Button", "btnTwo", 40, 100, 120, 32, Text="Two")
    motion.add(f, "btnGo", "slideIn", id="fx1", durationMs=500)
    motion.add(f, "btnGo", "pulse", id="fx2", durationMs=600)
    motion.add(f, "btnTwo", "pulse", id="fx3", durationMs=300)       # pulse first, then the slide
    motion.add(f, "btnTwo", "slideIn", id="fx4", durationMs=500)


def form() -> Form:
    f = Form()
    f.props.update(Name="Form1", Text="Overlap", Width=400, Height=240)
    build(f)
    return f


def preview() -> None:
    from radide.features import animations_panel as A
    f = form()
    pv = A.FxPreview(f, A.segments_for(f, None, "py"))
    end = pv._values(pv.length + 50)
    mid = pv._values(250)
    check("preview: slide + pulse ends at the designed Left", end.get(("btnGo", "Left")) == 40, end.get(("btnGo", "Left")))
    check("preview: the slide is visible mid-way", mid.get(("btnGo", "Left")) not in (None, 40), mid.get(("btnGo", "Left")))
    check("preview: pulse first, slide second ends in place", end.get(("btnTwo", "Left")) == 40,
          end.get(("btnTwo", "Left")))


def tk() -> None:
    d = WORK / "tk"
    write_project(d, "python-tk", [form()], overwrite_user=True)
    code = textwrap.dedent(f"""
        import sys, time, json
        sys.path.insert(0, r"{d}")
        from Form1 import Form1
        f = Form1(); root = f.root; root.geometry("+-2000+-2000")
        def run(ms):
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                root.update(); time.sleep(0.005)
        x = lambda n: int(float(getattr(f, n).place_info().get("x", -1)))
        R = {{}}
        run(250); R["mid"] = x("btnGo")
        run(1200); R["go"] = x("btnGo"); R["two"] = x("btnTwo")
        f.BeginAnimation("fx2"); f.BeginAnimation("fx1"); run(1200); R["again"] = x("btnGo")
        print("RESULT " + json.dumps(R))
        """)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120,
                       env=dict(os.environ, RADIDE_REDUCED_MOTION="0", PYTHONPATH=str(ROOT)))
    res = next((json.loads(line[7:]) for line in r.stdout.splitlines() if line.startswith("RESULT ")),
               {"_error": (r.stdout + r.stderr)[-1200:]})
    check("tk: slide + pulse on load end at the designed Left", res.get("go") == 40 and res.get("mid") not in (None, 40),
          res)
    check("tk: pulse first, slide second end in place", res.get("two") == 40, res)
    check("tk: started again from code (pulse, then slide) ends in place", res.get("again") == 40, res)


RING_TEST = r'''load "Form1.ring"
oApp = NULL
func main
    oApp = new qApp
    Form1_Show()
    oT = new qTimer(Form1)
    oT.setInterval(1600)
    oT.setTimeoutEvent("Check()")
    oT.start()
    oApp.exec()
func Check
    see "R go " + QWidget_x(btnGo.pObject) + nl
    see "R two " + QWidget_x(btnTwo.pObject) + nl
    oApp.quit()
'''


def ring() -> None:
    if not ring_exe():
        skip("Ring", "ring.exe not found")
        return
    d = WORK / "ring"
    write_project(d, "ring-qt", [form()], overwrite_user=True)
    out = ring_run(d, RING_TEST) or ""
    r = dict(line.split(" ")[1:3] for line in out.splitlines() if line.startswith("R "))
    check("Ring: slide + pulse on load end at the designed Left", r.get("go") == "40", out[-600:])
    check("Ring: pulse first, slide second end in place", r.get("two") == "40", r)


RING_PANE = r'''load "Form1.ring"
oApp = NULL
func main
    oApp = new qApp
    Form1_Show()
    oT = new qTimer(Form1)
    oT.setInterval(400)
    oT.setTimeoutEvent("Check()")
    oT.start()
    oApp.exec()
func Check
    see "R " + QWidget_width(colA.pObject) + " " + QWidget_x(colB.pObject) + nl
    oApp.quit()
'''


def ring_twopane() -> None:
    if not ring_exe():
        skip("Ring TwoPane", "ring.exe not found")
        return
    from proj import add
    f = Form()
    f.props.update(Name="Form1", Text="Nested pane", Width=1000, Height=600)
    add(f, "Panel", "pnl", 100, 50, 800, 500)
    add(f, "TwoPane", "tp", 50, 20, 700, 400, parent="pnl", PaneMode="Auto", Ratio=0.5, SinglePane="Start",
        HingeAware=True)
    add(f, "Panel", "colA", 0, 0, 350, 400, parent="tp")
    add(f, "Panel", "colB", 350, 0, 350, 400, parent="tp")
    d = WORK / "ring_pane"
    write_project(d, "ring-qt", [f], overwrite_user=True)
    out = ring_run(d, RING_PANE, env={"RADIDE_HINGE": "590,0,20,600"}) or ""
    r = next((line.split(" ")[1:3] for line in out.splitlines() if line.startswith("R ")), None)
    # the pane is at (150, 70) in the window: hinge x 590 -> 440 in the pane, the second pane after the band
    check("Ring: nested TwoPane splits at the hinge converted to its own coordinates", r == ["440", "460"], out[-500:])
    out = ring_run(d, RING_PANE) or ""
    r = next((line.split(" ")[1:3] for line in out.splitlines() if line.startswith("R ")), None)
    check("Ring: without a hinge the Ratio split is kept", r == ["350", "350"], out[-500:])


def winforms() -> None:
    for lang in ("cs", "vb"):
        res = winforms_case(lang, build, tag="_overlap")
        if res is None:
            skip("WinForms", "dotnet not found")
            return
        ok, log, st, _report, _dst = res
        check(f"WinForms {lang}: dotnet build", ok, log)
        if not ok:
            continue
        t1 = st.get("t1", {})
        check(f"WinForms {lang}: slide + pulse on load end at the designed Left", t1.get("btnGo", {}).get("x") == 40, t1)
        check(f"WinForms {lang}: pulse first, slide second end in place", t1.get("btnTwo", {}).get("x") == 40, t1)


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    preview()
    tk()
    ring()
    ring_twopane()
    winforms()
    return summary()


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
