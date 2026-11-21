"""Run the generated animation runtime for real: python-tk, python-qt (offscreen) and reduced motion.

    python samples/Tests/Motion/check_runtime.py

Each scenario runs in its own process (the sample's Form1.py / Form1_designer.py, rebuilt first by
make_samples.py): fires clicks / hover / show / hide, lets the animations run and checks the final
geometry, colours, text and visibility. Exit code 0 = all passed."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAILS: list[str] = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


# ------------------------------------------------------------------------------------------------- tk
def tk_child(reduced: bool) -> None:
    sys.path.insert(0, str(HERE / "Motion_Tk_Presets"))
    from Form1 import Form1
    f = Form1()
    root = f.root
    root.geometry("+-2000+-2000")           # off screen: no window in the user's way

    def run(ms):
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            root.update()
            time.sleep(0.005)

    def x(w):
        return int(float(w.place_info().get("x", -1)))

    def y(w):
        return int(float(w.place_info().get("y", -1)))
    run(200 if reduced else 1800)
    check(f.lblTitle.cget("text") == "Hello, motion!", f"tk: typewriter ended with the full text ({f.lblTitle.cget('text')!r})")
    check(x(f.lblTitle) == 20, f"tk: slideIn ended at the designed Left 20 ({x(f.lblTitle)})")
    if reduced:
        check(f._fx.ReducedMotion, "tk: RADIDE_REDUCED_MOTION=1 -> ReducedMotion")
        f.btnMove.event_generate("<Button-1>")
        run(60)
        check(x(f.btnMove) == 80 and y(f.btnMove) == 110,
              f"tk reduced: move + bounce jump to the end at once ({x(f.btnMove)},{y(f.btnMove)})")
        f.SetVisible("lblInfo", False)
        run(30)
        check(f.lblInfo.winfo_manager() == "", "tk reduced: hide is immediate")
        return
    # shake on click: moves, then comes back
    f.btnShake.event_generate("<Button-1>")
    run(120)
    moved = x(f.btnShake)
    run(800)
    check(moved != 20 and x(f.btnShake) == 20, f"tk: shake moved ({moved}) and came back ({x(f.btnShake)})")
    # move then bounce (after chain)
    f.btnMove.event_generate("<Button-1>")
    run(250)
    mid_top = y(f.btnMove)
    run(1200)
    check(x(f.btnMove) == 80 and y(f.btnMove) == 110,
          f"tk: move dx=60 then bounce: at ({x(f.btnMove)},{y(f.btnMove)}), expected (80,110)")
    check(mid_top == 110, "tk: Top not touched while moving")
    # rotate falls back to a wobble that ends in place
    f.btnSpin.event_generate("<Button-1>")
    run(1100)
    check(x(f.btnSpin) == 150, f"tk: rotate (wobble fallback) ended in place ({x(f.btnSpin)})")
    # hover zoom: grows while the mouse is over it, back on leave
    f.btnPulse.event_generate("<Enter>")
    run(500)
    grown = int(float(f.btnPulse.place_info()["width"]))
    f.btnPulse.event_generate("<Leave>")
    run(500)
    back = int(float(f.btnPulse.place_info()["width"]))
    check(grown > 110 and back == 110, f"tk: hover zoom width {grown} then {back}")
    # hide: fade (colour blend fallback), then hidden with the designed colours back
    f.SetVisible("lblInfo", False)
    run(150)
    mid = str(f.lblInfo.cget("bg")).lower()
    check(f.lblInfo.winfo_manager() == "place" and mid != "#ffe08a", f"tk: fading out (bg {mid})")
    run(700)
    check(f.lblInfo.winfo_manager() == "" and str(f.lblInfo.cget("bg")).lower() == "#ffe08a",
          "tk: hidden after the fade, colours restored")
    f.SetVisible("lblInfo", True)
    run(700)
    check(f.lblInfo.winfo_manager() == "place" and str(f.lblInfo.cget("bg")).lower() == "#ffe08a",
          "tk: shown again with fade in")
    # timer colour (2.5 s, autoreverse) ran at least once by now
    f.Animate("btnSpin", "slideOut", durationMs=300)
    run(600)
    check(f.btnSpin.winfo_manager() == "", "tk: Animate('btnSpin', 'slideOut') from code hides it")
    sb = f.Animate("", "fadeOut", durationMs=200, autoreverse=True)
    run(600)
    check(abs(float(root.attributes("-alpha")) - 1.0) < 0.01 and not sb.IsPlaying, "tk: form fade with auto reverse")
    root.destroy()


# ------------------------------------------------------------------------------------------------- qt
def qt_child() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(HERE / "Motion_Qt_Presets"))
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect
    app = QApplication.instance() or QApplication(sys.argv)
    from Form1 import Form1
    f = Form1()
    f.show()

    def run(ms):
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(0.005)

    def op(w):
        e = w.graphicsEffect()
        return e.opacity() if isinstance(e, QGraphicsOpacityEffect) else 1.0
    run(1800)
    check(f.lblTitle.text() == "Hello, motion!" and f.lblTitle.x() == 20, "qt: slideIn + typewriter on load")
    QTest.mouseClick(f.btnShake, Qt.MouseButton.LeftButton)
    run(120)
    moved = f.btnShake.x()
    run(800)
    check(moved != 20 and f.btnShake.x() == 20, f"qt: shake on click ({moved} -> {f.btnShake.x()})")
    QTest.mouseClick(f.btnMove, Qt.MouseButton.LeftButton)
    run(1400)
    check((f.btnMove.x(), f.btnMove.y()) == (80, 110), f"qt: move + bounce chain -> {f.btnMove.pos().toTuple()}")
    app.sendEvent(f.btnPulse, QEvent(QEvent.Type.Enter))
    run(500)
    grown = f.btnPulse.width()
    app.sendEvent(f.btnPulse, QEvent(QEvent.Type.Leave))
    run(500)
    check(grown > 110 and f.btnPulse.width() == 110, f"qt: hover zoom {grown} -> {f.btnPulse.width()}")
    f.SetVisible("lblInfo", False)
    run(200)
    mid = op(f.lblInfo)
    check(f.lblInfo.isVisible() and 0.0 < mid < 1.0, f"qt: real opacity while fading out ({mid:.2f})")
    run(700)
    check(not f.lblInfo.isVisible() and op(f.lblInfo) == 1.0, "qt: hidden after fade, opacity restored")
    f.SetVisible("lblInfo", True)
    run(700)
    check(f.lblInfo.isVisible() and op(f.lblInfo) == 1.0, "qt: fade in on show")
    f.Animate("btnSpin", "scaleOut", durationMs=300)
    run(700)
    check(not f.btnSpin.isVisible(), "qt: Animate scaleOut from code hides it")
    f.close()


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        {"tk": lambda: tk_child(False), "tk-reduced": lambda: tk_child(True), "qt": qt_child}[sys.argv[2]]()
        return 1 if FAILS else 0
    subprocess.run([sys.executable, str(HERE / "make_samples.py")], check=True)
    rc = 0
    for name, env in (("tk", {"RADIDE_REDUCED_MOTION": "0"}), ("tk-reduced", {"RADIDE_REDUCED_MOTION": "1"}),
                      ("qt", {"RADIDE_REDUCED_MOTION": "0", "QT_QPA_PLATFORM": "offscreen"})):
        print(f"--- {name}", flush=True)
        r = subprocess.run([sys.executable, __file__, "--child", name], env={**os.environ, **env}, timeout=120)
        rc |= r.returncode
    print("ALL PASSED" if rc == 0 else "FAILED")
    return rc


if __name__ == "__main__":
    sys.exit(main())
