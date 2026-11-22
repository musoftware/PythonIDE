"""FeatureMatrix for the native Java Swing exe (radide/deploy/native/java_native.py + java/RadMotion.java).

    .venv\\Scripts\\python samples/Tests/FeatureMatrix/check_fm_java.py

Publishes fm_java.write_project() with radide.deploy.build.build() (test build: RADIDE_NATIVE_TEST_HOOK=1),
asserts the native Java kind (no fallback) and checks the same features as fm_drive.py through RadTestHook
(Swing has no child HWNDs: commands on stdin, "R <result>" on stdout):

    load        lblTitle slides in (Left changes over frames, ends at 20); lblType types itself (after fx1)
    click       btnShake shakes and returns; btnMove moves +60 then bounces (chain); btnColor recolours pnlBox
    timer       pnlTimer changes colour every 1.5 s
    hover state btnHover shows "Hovered" while the mouse is over it (synthetic enter / exit)
    custom state btnAlert -> GoToState("Alert"): form caption "ALERT", lblTitle "ALERT!"
    manual      btnManual -> BeginAnimation("fx8"): lblManual moves +80
    variants    client width 380 -> pnlBox hidden, lblTitle "Small"; 760 -> btnShake Left 400; back to 480
    reduced     RADIDE_REDUCED_MOTION=1: lblTitle / lblType are at their end at once
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

import fm_java  # noqa: E402
import fm_project as P  # noqa: E402
from radide.deploy import build as B  # noqa: E402
from radide.deploy import config as C  # noqa: E402
from radide.deploy.native import java_native as J  # noqa: E402
from radide.model import Project  # noqa: E402

RESULTS: list[tuple[str, bool]] = []


def ok(name, cond, detail="") -> bool:
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} [java] {name}" + ("" if cond else f"  [{str(detail)[:400]}]"), flush=True)
    return bool(cond)


class Hook:
    def __init__(self, exe: Path, env: dict):
        self.p = subprocess.Popen([str(exe)], cwd=str(exe.parent), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8", env=env)

    def q(self, cmd: str) -> str:
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline().strip()
        return line[2:] if line.startswith("R ") else "" if line == "R" else line

    def wait(self, fn, timeout: float = 5.0, step: float = 0.05):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if fn():
                    return True
            except Exception:  # noqa: BLE001
                pass
            time.sleep(step)
        return False

    def left(self, n: str) -> int:
        return int(self.q(f"bounds {n}").split()[0])

    def top(self, n: str) -> int:
        return int(self.q(f"bounds {n}").split()[1])

    def color(self, n: str) -> tuple[int, int, int]:
        h = self.q(f"color {n}")
        return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)

    def close(self):
        try:
            if self.p.poll() is None:
                self.p.kill()
                self.p.wait(5)
        except Exception:  # noqa: BLE001
            pass


def sample(fn, seconds, step=0.03):
    out, end = [], time.time() + seconds
    while time.time() < end:
        try:
            out.append(fn())
        except Exception:  # noqa: BLE001
            pass
        time.sleep(step)
    return out


def near(c, hexcol, tol=40) -> bool:
    t = tuple(int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    return all(abs(a - b) <= tol for a, b in zip(c, t))


NAMES = ["lblTitle", "btnShake", "btnMove", "pnlBox", "btnColor", "lblType", "pnlTimer", "btnHover", "btnAlert",
         "btnManual", "lblManual"]


def start(exe: Path, reduced: str) -> Hook | None:
    env = dict(os.environ, RADIDE_REDUCED_MOTION=reduced)     # this machine may have Windows animations off
    h = Hook(exe, env)
    shown = h.wait(lambda: h.q("windows") == "Feature matrix", 30, 0.02)
    if not ok(f"form shown (reduced={reduced})", shown, h.q("windows") if h.p.poll() is None else "exited"):
        h.close()
        return None
    found = all(not h.q(f"bounds {n}").startswith("ERROR") for n in NAMES)
    if not ok(f"controls found (reduced={reduced})", found, [h.q(f"bounds {n}") for n in NAMES]):
        h.close()
        return None
    return h


def drive(exe: Path) -> None:
    h = start(exe, "0")
    if h is None:
        return
    try:
        # ---- load: slide in + typewriter after it
        xs = sample(lambda: h.left("lblTitle"), 1.0)
        texts = sample(lambda: h.q("get lblType Text"), 1.2)
        ok("anim load slideIn moves over frames", len(set(xs)) >= 3 and min(xs) < P.TITLE_LEFT - 20, xs[:16])
        ok("anim slideIn ends at the designed Left", abs(h.left("lblTitle") - P.TITLE_LEFT) <= 2, h.left("lblTitle"))
        partial = [t for t in texts if 0 < len(t) < len(P.TYPED)]
        ok("anim chain (after) typewriter types",
           partial and h.wait(lambda: h.q("get lblType Text") == P.TYPED, 3), texts[:10])
        # ---- click: shake returns
        x0 = h.left("btnShake")
        h.q("click btnShake")
        xs = sample(lambda: h.left("btnShake"), 0.8)
        ok("anim click shake", len(set(xs)) >= 3 and abs(h.left("btnShake") - x0) <= 1, (x0, xs[:16]))
        # ---- click: move + chained bounce
        m0 = (h.left("btnMove"), h.top("btnMove"))
        h.q("click btnMove")
        ys = sample(lambda: h.top("btnMove"), 1.2)
        m1 = (h.left("btnMove"), h.top("btnMove"))
        ok("anim click move ends +dx", abs(m1[0] - (m0[0] + P.MOVE_DX)) <= 2, (m0, m1))
        ok("anim chain bounce after move", ys and min(ys) < m0[1] - 5 and abs(m1[1] - m0[1]) <= 1, ys[:24])
        # ---- click on another control: colour
        before = h.color("pnlBox")
        h.q("click btnColor")
        cols = sample(lambda: h.color("pnlBox"), 0.9)
        ok("anim colorTo (click of another control)", near(before, P.BOX) and cols and near(cols[-1], P.BOX_TO)
           and any(not near(x, P.BOX) and not near(x, P.BOX_TO, 10) for x in cols), (before, cols[::4]))
        # ---- timer trigger
        tc = sample(lambda: h.color("pnlTimer"), 3.2, 0.05)
        ok("anim timer trigger", any(near(x, P.TIMER_TO, 60) for x in tc) and any(near(x, P.TIMER_FROM, 30) for x in tc),
           tc[::8])
        # ---- visual state MouseOver (synthetic mouse enter / exit on the Swing button)
        h.q("hover btnHover 1")
        ok("state MouseOver (automatic)", h.wait(lambda: h.q("get btnHover Text") == "Hovered", 3),
           h.q("get btnHover Text"))
        h.q("hover btnHover 0")
        ok("state MouseOver given back", h.wait(lambda: h.q("get btnHover Text") == "Hover me", 3),
           h.q("get btnHover Text"))
        # ---- custom state from code
        h.q("click btnAlert")
        ok("state GoToState (form + control)", h.wait(lambda: h.q("get Form1 Text") == "ALERT"
                                                      and h.q("get lblTitle Text") == "ALERT!", 4),
           (h.q("get Form1 Text"), h.q("get lblTitle Text"), h.q("get Form1 CurrentState")))
        # ---- manual animation from code
        l0 = h.left("lblManual")
        h.q("click btnManual")
        ok("anim manual BeginAnimation", h.wait(lambda: abs(h.left("lblManual") - (l0 + P.MANUAL_DX)) <= 2, 3),
           (l0, h.left("lblManual")))
        # ---- layout variants (the form's client area resized)
        h.q("resize Form1 380 320")
        ok("variant compact (hide + text)", h.wait(lambda: h.q("get pnlBox Visible") == "False"
                                                   and h.q("showing pnlBox") == "False"
                                                   and h.q("get lblTitle Text") == "Small", 3),
           (h.q("get Form1 Width"), h.q("get Form1 CurrentSizes"), h.q("get pnlBox Visible"), h.q("get lblTitle Text")))
        h.q("resize Form1 760 320")
        ok("variant wide (geometry)", h.wait(lambda: abs(h.left("btnShake") - P.WIDE_SHAKE_LEFT) <= 3
                                             and h.q("showing pnlBox") == "True", 3),
           (h.q("get Form1 Width"), h.q("get Form1 CurrentSizes"), h.q("bounds btnShake")))
        h.q("resize Form1 480 320")
        ok("variant base restored", h.wait(lambda: abs(h.left("btnShake") - P.SHAKE_LEFT) <= 3
                                           and h.q("showing pnlBox") == "True"
                                           and h.q("get lblTitle Text") != "Small"
                                           and h.q("get Form1 CurrentSizes") == "", 3),
           (h.q("bounds btnShake"), h.q("get lblTitle Text"), h.q("get Form1 CurrentSizes")))
    finally:
        h.close()
    # ---- reduced motion: every Begin jumps to the end
    h = start(exe, "1")
    if h is None:
        return
    try:
        time.sleep(0.4)
        ok("reduced motion: slide ends at once", abs(h.left("lblTitle") - P.TITLE_LEFT) <= 2, h.left("lblTitle"))
        ok("reduced motion: typewriter complete at once", h.q("get lblType Text") == P.TYPED, h.q("get lblType Text"))
    finally:
        h.close()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="radfm_java_"))
    try:
        folder = fm_java.write_project(tmp / "FeatureMatrix")
        cfg = C.load(folder, folder.name)
        reasons = J.check(folder, Project.load(folder), cfg)
        ok("check(): no reasons (animations / states / variants are native)", not reasons, reasons)
        lines: list[str] = []
        os.environ[J.TEST_HOOK_ENV] = "1"
        try:
            res = B.build(folder, cfg, log=lines.append)
        finally:
            os.environ.pop(J.TEST_HOOK_ENV, None)
        if not ok(f"build kind is native Java ({res.kind}, no fallback)", res.kind == "native-jlink",
                  "\n".join(lines[-15:])):
            return 1
        gen = res.dist.parents[1].rglob("RadForms_g.java")      # <work>/dist/<exe> -> <work>/native-java/src
        code = next((p.read_text(encoding="utf-8") for p in gen), "")
        ok("generated form starts RadMotion with the native plan", "motion(" in code and "fx8" in code)
        drive(res.dist / res.exe)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    passed = sum(1 for _, k in RESULTS if k)
    failed = [n for n, k in RESULTS if not k]
    print(f"\nFeatureMatrix java: {passed}/{len(RESULTS)} passed" + (f"  failing: {failed}" if failed else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
