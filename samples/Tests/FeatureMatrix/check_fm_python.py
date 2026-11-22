"""FeatureMatrix on the IDE's Python runtime (Run / F5, the GUI Bridge and the Python-based Publish use it).

    .venv\\Scripts\\python samples/Tests/FeatureMatrix/check_fm_python.py            # from source
    set RADIDE_AS_PYTHON=1 & set RADIDE_FM_FROZEN=1 & RADIDE.exe samples/Tests/FeatureMatrix/check_fm_python.py
                                                                         # inside the frozen IDE (its radide)

The FeatureMatrix form (fm_project.build_form) -> the python-tk generator (python-qt as well when PySide6 is
there) -> the generated designer runs in a child process (off screen), and the same features as
fm_drive.py are checked through the widgets: slideIn over frames, typewriter chain, shake, move + bounce chain,
colorTo by another control, timer colour, MouseOver state, GoToState, BeginAnimation, layout variants by
resizing, reduced motion. Exit code = number of failures."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = os.environ.get("RADIDE_FM_FROZEN") == "1"
if FROZEN:
    os.environ["RADIDE_FM_NO_REPO"] = "1"         # fm_project must import the frozen IDE's radide
sys.path.insert(0, str(HERE))

CHILD = r'''
import os, sys, time
sys.path.insert(0, {folder!r})
from Form1 import Form1
f = Form1()
root = f.root
root.geometry("+-3000+-3000")
reduced = os.environ.get("RADIDE_REDUCED_MOTION") == "1"
fails = []

def check(c, m):
    print(("ok   " if c else "FAIL ") + m, flush=True)
    if not c:
        fails.append(m)

def run(ms):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        root.update()
        time.sleep(0.004)

def x(w):
    return int(float(w.place_info().get("x", -9999)))

def y(w):
    return int(float(w.place_info().get("y", -9999)))

def bg(w):
    return str(w.cget("background")).lower()

if reduced:
    run(250)
    check(x(f.lblTitle) == 20, "reduced motion: slide ends at once (%s)" % x(f.lblTitle))
    check(f.lblType.cget("text") == "typewriter text", "reduced motion: typewriter complete at once")
    sys.exit(len(fails))
xs, texts = [], []
end = time.monotonic() + 1.8
while time.monotonic() < end:
    root.update()
    xs.append(x(f.lblTitle))
    texts.append(f.lblType.cget("text"))
    time.sleep(0.01)
check(len(set(xs)) >= 3 and min(xs) < 0, "anim load slideIn moves over frames")
check(x(f.lblTitle) == 20, "anim slideIn ends at the designed Left (%s)" % x(f.lblTitle))
check(any(0 < len(t) < 15 for t in texts) and f.lblType.cget("text") == "typewriter text", "anim chain (after) typewriter types")
f.btnShake.event_generate("<Button-1>"); run(120); moved = x(f.btnShake); run(700)
check(moved != 20 and x(f.btnShake) == 20, "anim click shake (%s -> %s)" % (moved, x(f.btnShake)))
f.btnMove.event_generate("<Button-1>"); tops = []
end = time.monotonic() + 1.2
while time.monotonic() < end:
    root.update(); tops.append(y(f.btnMove)); time.sleep(0.01)
check(x(f.btnMove) == 210, "anim click move ends +dx (%s)" % x(f.btnMove))
check(min(tops) < 55 and y(f.btnMove) == 60, "anim chain bounce after move")
before = bg(f.pnlBox)
f.btnColor.event_generate("<Button-1>"); run(120); mid = bg(f.pnlBox); run(700)
check(before == "#3399ff" and mid not in ("#3399ff", "#ff7a59") and bg(f.pnlBox) == "#ff7a59",
      "anim colorTo (click of another control) %s %s %s" % (before, mid, bg(f.pnlBox)))
seen = set()
end = time.monotonic() + 3.5
while time.monotonic() < end:
    root.update(); seen.add(bg(f.pnlTimer)); time.sleep(0.02)
check("#aa0000" in seen and "#00aa00" in seen, "anim timer trigger")
f.btnHover.event_generate("<Enter>"); run(80)
check(f.btnHover.cget("text") == "Hovered", "state MouseOver (automatic)")
f.btnHover.event_generate("<Leave>"); run(80)
check(f.btnHover.cget("text") == "Hover me", "state MouseOver given back")
f.GoToState("Alert"); run(50)
check(root.title() == "ALERT" and f.lblTitle.cget("text") == "ALERT!", "state GoToState (form + control)")
l0 = x(f.lblManual); f.BeginAnimation("fx8"); run(700)
check(x(f.lblManual) == l0 + 80, "anim manual BeginAnimation")
root.geometry("380x320"); run(300)
check(f.pnlBox.winfo_manager() == "" and f.lblTitle.cget("text") == "Small", "variant compact (hide + text)")
root.geometry("760x320"); run(300)
check(x(f.btnShake) == 400 and f.pnlBox.winfo_manager() == "place", "variant wide (geometry) %s" % x(f.btnShake))
root.geometry("480x320"); run(300)
check(x(f.btnShake) == 20 and f.lblTitle.cget("text") != "Small", "variant base restored")
sys.exit(len(fails))
'''


def main() -> int:
    import fm_project
    from radide.languages import get_plugin
    tmp = Path(tempfile.mkdtemp(prefix="radide_fm_py_"))
    form = fm_project.build_form()
    user = ("from Form1_designer import Form1Designer\n\n\nclass Form1(Form1Designer):\n    pass\n")
    (tmp / "Form1.py").write_text(user, encoding="utf-8")
    (tmp / "Form1_designer.py").write_text(get_plugin("python-tk").generate_designer(form, user), encoding="utf-8")
    (tmp / "child.py").write_text(CHILD.format(folder=str(tmp)), encoding="utf-8")
    fails = 0
    for reduced in ("0", "1"):
        env = dict(os.environ, RADIDE_REDUCED_MOTION=reduced)
        env.pop("RADIDE_AS_PYTHON", None) if not FROZEN else None
        r = subprocess.run([sys.executable, str(tmp / "child.py")], env=env, capture_output=True, text=True,
                           timeout=120)
        print(r.stdout.strip())
        if r.returncode and "Traceback" in (r.stderr or ""):
            print(r.stderr[-1500:])
        fails += r.returncode
    where = "frozen IDE" if FROZEN else "source"
    print(f"FeatureMatrix python-tk ({where}): {'ALL OK' if not fails else f'{fails} failure(s)'}")
    return fails


if __name__ == "__main__":
    sys.exit(main())
