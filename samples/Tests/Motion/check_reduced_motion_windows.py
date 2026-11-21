"""Reduced motion from the Windows setting "Show animations in Windows" (SPI_GETCLIENTAREAANIMATION).

    python samples/Tests/Motion/check_reduced_motion_windows.py

The user's setting is never changed: SystemParametersInfoW is MOCKED (ctypes.windll replaced by a fake that
answers "animations on" / "off" / "call failed" and records every call), and the only real call is a
read (SPI_GETCLIENTAREAANIMATION = 0x1042; the test fails if anything asks for SPI_SETCLIENTAREAANIMATION).

1. ``_rad_reduced_motion()`` of the Python runtime (motion/runtime_py.py FX_RT, python-tk / python-qt /
   VB / GUI-Bridge designers) and ``reduced_motion()`` of the Kivy runtime (mobile/kivy_fx.py): the mocked
   setting decides when RADIDE_REDUCED_MOTION is not set, the variable wins when it is.
2. A generated python-tk form (Motion_Tk_Presets) in a child process with the fake "animations off": the
   runtime reports ReducedMotion and a click-triggered move jumps to its end at once; with "animations on"
   it animates.
3. A real read-only call agrees with ctypes read directly (Windows only).
4. The WinForms (C# / VB.NET) runtimes read the same setting (source check).
Exit code 0 = all passed.
"""
from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
import time
import types
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
FAILS: list[str] = []
SPI_GET, SPI_SET = 0x1042, 0x1043


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


class FakeUser32:
    """SystemParametersInfoW(action, param, pvParam, winIni) answering *animations* (True / False) or
    failing (ok=False); records the calls."""

    def __init__(self, animations: bool, ok: bool = True):
        self.animations, self.ok, self.calls = animations, ok, []

    def SystemParametersInfoW(self, action, param, pv, winini):  # noqa: N802 - Win32 name
        self.calls.append((action, param, winini))
        if action != SPI_GET:
            raise AssertionError(f"SystemParametersInfoW action {action:#x}: only SPI_GETCLIENTAREAANIMATION "
                                 "may be called")
        if not self.ok:
            return 0
        pv._obj.value = 1 if self.animations else 0          # ctypes.byref(c_int) -> ._obj is the c_int
        return 1


def patched(user32):
    """ctypes.windll replaced by a fake (also on other systems: create=True)."""
    return mock.patch.object(ctypes, "windll", types.SimpleNamespace(user32=user32), create=True)


def no_env():
    env = {k: v for k, v in os.environ.items() if k != "RADIDE_REDUCED_MOTION"}
    return mock.patch.dict(os.environ, env, clear=True)


def function_from(source: str, name: str):
    """Compile only the function *name* of a runtime source text."""
    m = re.search(rf"^def {name}\(.*?(?=^\S)", source + "\nEND", re.S | re.M)
    assert m, name
    ns: dict = {}
    exec(compile("import os\n" + m.group(0), f"<{name}>", "exec"), ns)
    return ns[name]


# ------------------------------------------------------------------------------------- 1. the functions
def functions():
    from radide.motion import runtime_py
    from radide.mobile import kivy_fx
    cases = {"python FX_RT _rad_reduced_motion": function_from(runtime_py.FX_RT, "_rad_reduced_motion"),
             "kivy reduced_motion": function_from(kivy_fx.FX_RUNTIME, "reduced_motion")}
    for label, fn in cases.items():
        with mock.patch.object(os, "name", "nt"):
            for animations, want in ((False, True), (True, False)):
                u = FakeUser32(animations)
                with no_env(), patched(u):
                    got = fn()
                check(got is want, f"{label}: Windows animations {'on' if animations else 'off'} -> reduced={got}")
                check(u.calls == [(SPI_GET, 0, 0)], f"{label}: one read-only SPI_GETCLIENTAREAANIMATION call "
                                                    f"{u.calls}")
            u = FakeUser32(False, ok=False)
            with no_env(), patched(u):
                check(fn() is False, f"{label}: the call fails -> animations play")
            for env, animations, want in (("1", True, True), ("0", False, False)):
                u = FakeUser32(animations)
                with no_env(), patched(u):
                    os.environ["RADIDE_REDUCED_MOTION"] = env
                    got = fn()
                check(got is want and not u.calls,
                      f"{label}: RADIDE_REDUCED_MOTION={env} wins over the setting (no SPI call)")
            with no_env(), mock.patch.object(ctypes, "windll", None, create=True):
                check(fn() is False, f"{label}: no windll (broken ctypes) -> animations play")
        with mock.patch.object(os, "name", "posix"), no_env(), patched(FakeUser32(False)) as _p:
            check(fn() is False, f"{label}: not Windows -> the Windows setting is not asked")


# ------------------------------------------------------------------------------------- 2. a real form
def tk_child(mode: str) -> None:
    os.environ.pop("RADIDE_REDUCED_MOTION", None)
    u = FakeUser32(animations=(mode == "on"))
    with mock.patch.object(os, "name", "nt"), patched(u):
        sys.path.insert(0, str(HERE / "Motion_Tk_Presets"))
        from Form1 import Form1
        f = Form1()
    root = f.root
    root.geometry("+-2000+-2000")           # off screen

    def run(ms):
        end = time.monotonic() + ms / 1000.0
        while time.monotonic() < end:
            root.update()
            time.sleep(0.005)

    def x(w):
        return int(float(w.place_info().get("x", -1)))
    run(100)
    if mode == "off":
        check(f._fx.ReducedMotion is True, "tk form: Windows animations off -> ReducedMotion")
        check(u.calls and all(c[0] == SPI_GET for c in u.calls), f"tk form: only read calls {u.calls}")
        f.btnMove.event_generate("<Button-1>")
        run(60)
        check(x(f.btnMove) == 80, f"tk form: the click move jumped to its end at once (x={x(f.btnMove)})")
    else:
        check(f._fx.ReducedMotion is False, "tk form: Windows animations on -> animations play")
        x0 = x(f.btnMove)
        f.btnMove.event_generate("<Button-1>")
        run(60)
        check(x(f.btnMove) != 80 or x0 == 80, f"tk form: the click move is still running after 60 ms "
                                              f"(x={x(f.btnMove)})")
    root.destroy()


def forms():
    subprocess.run([sys.executable, str(HERE / "make_samples.py")], check=True, stdout=subprocess.DEVNULL)
    env = {k: v for k, v in os.environ.items() if k != "RADIDE_REDUCED_MOTION"}
    for mode in ("off", "on"):
        r = subprocess.run([sys.executable, __file__, "--child", mode], env=env, timeout=120,
                           capture_output=True, text=True)
        for line in (r.stdout or "").splitlines():
            print("   " + line)
        check(r.returncode == 0, f"tk form child ({mode}) passed" + ("" if r.returncode == 0 else
                                                                      (r.stderr or "")[-800:]))


# ------------------------------------------------------------------------------------- 3. real read
def real_read():
    if os.name != "nt":
        print("SKIP real SPI read (not Windows)")
        return
    from radide.motion import runtime_py
    fn = function_from(runtime_py.FX_RT, "_rad_reduced_motion")
    on = ctypes.c_int(1)
    ok = ctypes.windll.user32.SystemParametersInfoW(SPI_GET, 0, ctypes.byref(on), 0)
    with no_env():
        got = fn()
    check(bool(ok) and got is (not on.value),
          f"real read-only call: Windows animations {'on' if on.value else 'off'} -> reduced={got}")


# ------------------------------------------------------------------------------------- 4. WinForms
def winforms_source():
    src = (ROOT / "radide" / "foreign" / "winforms_fx.py").read_text(encoding="utf-8")
    check("SystemParametersInfo(0x1042" in src, "WinForms C# runtime reads SPI_GETCLIENTAREAANIMATION")
    check("0x1043" not in src, "WinForms runtimes never set the setting")


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        tk_child(sys.argv[2])
        return 1 if FAILS else 0
    functions()
    forms()
    real_read()
    winforms_source()
    print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
