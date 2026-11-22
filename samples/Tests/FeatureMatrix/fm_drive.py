"""Drive a published FeatureMatrix program (fm_project.build_form) on its OWN window and check every feature.

Works for every exe whose controls are top-level children of the form window: radforms programs (C, C++,
Fortran, Rust, Go, Lua, Node.js: controls found by their "radforms.name" property), FreeBASIC VB6 programs,
.NET WinForms and Java Swing are found by other means (see find_controls()).  Checks:

    load        lblTitle slides in (Left changes over frames, ends at 20); lblType types itself (after fx1)
    click       btnShake shakes and returns; btnMove moves +60 then bounces (chain); btnColor recolours pnlBox
    timer       pnlTimer changes colour every 1.5 s (PrintWindow pixels of the form)
    hover state btnHover shows "Hovered" while the mouse is over it (the cursor is put there and back)
    custom state btnAlert -> GoToState("Alert"): form caption "ALERT", lblTitle "ALERT!"
    manual      btnManual -> BeginAnimation("fx8"): lblManual moves +80
    variants    client width 380 -> pnlBox hidden, lblTitle "Small"; 760 -> btnShake Left 400; back to 480
    reduced     RADIDE_REDUCED_MOTION=1: lblTitle / lblType are at their end at once

Only the process started here is touched; no screen capture (PrintWindow of the program's window)."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes as wt
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Native"))
sys.path.insert(0, str(HERE))

import fm_project as P  # noqa: E402
import winauto as w  # noqa: E402

user32 = w.user32
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.MapWindowPoints.argtypes = [wt.HWND, wt.HWND, ctypes.POINTER(wt.POINT), wt.UINT]
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsIconic.argtypes = [wt.HWND]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.AdjustWindowRectEx.argtypes = [ctypes.POINTER(wt.RECT), wt.DWORD, wt.BOOL, wt.DWORD]
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetMenu.argtypes = [wt.HWND]
try:
    user32.GetDpiForWindow.argtypes = [wt.HWND]
except AttributeError:
    pass


def dpi(h) -> float:
    try:
        return float(user32.GetDpiForWindow(h) or 96)
    except AttributeError:
        return 96.0


def rect_in(h, parent) -> tuple[float, float, float, float]:
    """(left, top, width, height) of child h in parent's client coordinates, logical 96-DPI pixels."""
    r = wt.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    pts = (wt.POINT * 2)(wt.POINT(r.left, r.top), wt.POINT(r.right, r.bottom))
    user32.MapWindowPoints(None, parent, pts, 2)
    k = 96.0 / dpi(parent)
    return pts[0].x * k, pts[0].y * k, (pts[1].x - pts[0].x) * k, (pts[1].y - pts[0].y) * k


def client_size(h) -> tuple[float, float]:
    r = wt.RECT()
    user32.GetClientRect(h, ctypes.byref(r))
    k = 96.0 / dpi(h)
    return r.right * k, r.bottom * k


def set_client_width(h, logical_w: float):
    """Resize the program's own form so its client area is logical_w wide (height unchanged)."""
    r, c = wt.RECT(), wt.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    user32.GetClientRect(h, ctypes.byref(c))
    frame_w = (r.right - r.left) - c.right
    px = int(round(logical_w * dpi(h) / 96.0)) + frame_w
    user32.SetWindowPos(h, None, 0, 0, px, r.bottom - r.top, 0x0002 | 0x0004 | 0x0010)  # NOMOVE|NOZORDER|NOACTIVATE


def unminimize(form):
    """Parallel desktop tests (or Win+D) may minimise our window: give it its size back (our process only)."""
    if user32.IsIconic(form):
        user32.ShowWindow(form, 9)              # SW_RESTORE
        time.sleep(0.3)


def color_at(form, ctl) -> tuple[int, int, int]:
    """Colour in the middle of a control, rendered through the form (PrintWindow, client only)."""
    x, y, ww, hh = rect_in(ctl, form)
    k = dpi(form) / 96.0
    return w.grab_pixels(form, [(int((x + ww / 2) * k), int((y + hh / 2) * k))])[0]


def near(c, hexcol, tol=40) -> bool:
    t = tuple(int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    return all(abs(a - b) <= tol for a, b in zip(c, t))


def sample(fn, seconds, step=0.03):
    out, end = [], time.time() + seconds
    while time.time() < end:
        try:
            out.append(fn())
        except Exception:  # noqa: BLE001
            pass
        time.sleep(step)
    return out


class Report:
    def __init__(self, target: str):
        self.target, self.rows = target, []

    def ok(self, feature: str, cond, detail="") -> bool:
        self.rows.append((feature, bool(cond), str(detail)))
        print(f"{'PASS' if cond else 'FAIL'} [{self.target}] {feature}" + (f"  [{detail}]" if detail and not cond else ""),
              flush=True)
        return bool(cond)


def find_controls(form, names, pid=None):
    """{name: hwnd} of the FeatureMatrix controls (radforms.name / control text)."""
    found = w.children(form)
    if all(n in found for n in names):
        return found
    return found


def drive(exe: Path, rep: Report, vb: bool = False, env_extra: dict | None = None, form_name="Form1",
          find=None) -> None:
    p_ = "cmd" if vb else "btn"
    env = dict(os.environ)
    env["RADIDE_REDUCED_MOTION"] = "0"           # this machine may have Windows animations off
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent), env=env)
    form = None
    try:
        form = w.form_window(proc.pid, form_name, 20) or w.wait(lambda: (w.top_windows(proc.pid) or [None])[0], 10)
        if not rep.ok("form shown", form):
            return
        names = ["lblTitle", p_ + "Shake", p_ + "Move", "pnlBox", p_ + "Color", "lblType", "pnlTimer", p_ + "Hover",
                 p_ + "Alert", p_ + "Manual", "lblManual"]
        c = w.wait(lambda: (lambda d: d if all(n in d for n in names) else None)((find or find_controls)(form, names)),
                   10)
        if not rep.ok("controls found", c, sorted((find or find_controls)(form, names))):
            return
        if env_extra and env_extra.get("RADIDE_REDUCED_MOTION") == "1":
            time.sleep(0.4)
            rep.ok("reduced motion: slide ends at once", abs(rect_in(c["lblTitle"], form)[0] - P.TITLE_LEFT) <= 2,
                   rect_in(c["lblTitle"], form))
            rep.ok("reduced motion: typewriter complete at once", w.get_text(c["lblType"]) == P.TYPED,
                   w.get_text(c["lblType"]))
            return
        # ---- load: slide in + typewriter after it
        xs = sample(lambda: round(rect_in(c["lblTitle"], form)[0]), 1.0)
        texts = sample(lambda: w.get_text(c["lblType"]), 1.2)
        rep.ok("anim load slideIn moves over frames", len(set(xs)) >= 3 and min(xs) < P.TITLE_LEFT - 20, xs[:12])
        rep.ok("anim slideIn ends at the designed Left", abs(rect_in(c["lblTitle"], form)[0] - P.TITLE_LEFT) <= 2,
               rect_in(c["lblTitle"], form))
        partial = [t for t in texts if 0 < len(t) < len(P.TYPED)]
        rep.ok("anim chain (after) typewriter types", partial and w.wait(lambda: w.get_text(c["lblType"]) == P.TYPED, 3),
               texts[:8])
        # ---- click: shake returns
        x0 = rect_in(c[p_ + "Shake"], form)[0]
        w.click(c[p_ + "Shake"])
        xs = sample(lambda: round(rect_in(c[p_ + "Shake"], form)[0]), 0.8)
        rep.ok("anim click shake", len(set(xs)) >= 3 and abs(rect_in(c[p_ + "Shake"], form)[0] - x0) <= 1, xs[:12])
        # ---- click: move + chained bounce
        m0 = rect_in(c[p_ + "Move"], form)
        w.click(c[p_ + "Move"])
        ys = sample(lambda: round(rect_in(c[p_ + "Move"], form)[1]), 1.2)
        m1 = rect_in(c[p_ + "Move"], form)
        rep.ok("anim click move ends +dx", abs(m1[0] - (m0[0] + P.MOVE_DX)) <= 2, (m0, m1))
        rep.ok("anim chain bounce after move", min(ys) < m0[1] - 5 and abs(m1[1] - m0[1]) <= 1, ys[:20])
        # ---- click on another control: colour
        unminimize(form)
        before = color_at(form, c["pnlBox"])
        w.click(c[p_ + "Color"])
        cols = sample(lambda: color_at(form, c["pnlBox"]), 0.9)
        rep.ok("anim colorTo (click of another control)", near(before, P.BOX) and near(cols[-1], P.BOX_TO)
               and any(not near(x, P.BOX) and not near(x, P.BOX_TO, 10) for x in cols), (before, cols[::4]))
        # ---- timer trigger
        unminimize(form)
        tc = sample(lambda: color_at(form, c["pnlTimer"]), 3.2, 0.05)
        rep.ok("anim timer trigger", any(near(x, P.TIMER_TO, 60) for x in tc) and any(near(x, P.TIMER_FROM, 30) for x in tc),
               tc[::8])
        # ---- visual state MouseOver (cursor put over the button, then back)
        unminimize(form)
        old = wt.POINT()
        user32.GetCursorPos(ctypes.byref(old))
        try:
            hx, hy, hw, hh = rect_in(c[p_ + "Hover"], form)
            k = dpi(form) / 96.0
            pt = wt.POINT(int((hx + hw / 2) * k), int((hy + hh / 2) * k))
            user32.ClientToScreen(form, ctypes.byref(pt))
            user32.SetWindowPos(form, wt.HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)    # our window on top
            user32.SetCursorPos(pt.x, pt.y)
            user32.PostMessageW(c[p_ + "Hover"], 0x0200, 0, (int(hh * k / 2) << 16) | int(hw * k / 2))
            rep.ok("state MouseOver (automatic)", w.wait(lambda: w.get_text(c[p_ + "Hover"]) == "Hovered", 3),
                   w.get_text(c[p_ + "Hover"]))
            user32.SetCursorPos(old.x, old.y)
            rep.ok("state MouseOver given back", w.wait(lambda: w.get_text(c[p_ + "Hover"]) == "Hover me", 3),
                   w.get_text(c[p_ + "Hover"]))
        finally:
            user32.SetCursorPos(old.x, old.y)
            user32.SetWindowPos(form, wt.HWND(-2), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
        # ---- custom state from code
        w.click(c[p_ + "Alert"])
        rep.ok("state GoToState (form + control)", w.wait(lambda: w.get_text(form) == "ALERT"
                                                          and w.get_text(c["lblTitle"]) == "ALERT!", 4),
               (w.get_text(form), w.get_text(c["lblTitle"])))
        # ---- manual animation from code
        l0 = rect_in(c["lblManual"], form)[0]
        w.click(c[p_ + "Manual"])
        rep.ok("anim manual BeginAnimation", w.wait(lambda: abs(rect_in(c["lblManual"], form)[0] - (l0 + P.MANUAL_DX)) <= 2, 3),
               (l0, rect_in(c["lblManual"], form)))
        # ---- layout variants
        unminimize(form)
        set_client_width(form, 380)
        rep.ok("variant compact (hide + text)", w.wait(lambda: not user32.IsWindowVisible(c["pnlBox"])
                                                       and w.get_text(c["lblTitle"]) == "Small", 3),
               (client_size(form), user32.IsWindowVisible(c["pnlBox"]), w.get_text(c["lblTitle"])))
        set_client_width(form, 760)
        rep.ok("variant wide (geometry)", w.wait(lambda: abs(rect_in(c[p_ + "Shake"], form)[0] - P.WIDE_SHAKE_LEFT) <= 3
                                                 and user32.IsWindowVisible(c["pnlBox"]), 3),
               (client_size(form), rect_in(c[p_ + "Shake"], form)))
        set_client_width(form, 480)
        rep.ok("variant base restored", w.wait(lambda: abs(rect_in(c[p_ + "Shake"], form)[0] - P.SHAKE_LEFT) <= 3
                                               and user32.IsWindowVisible(c["pnlBox"])
                                               and w.get_text(c["lblTitle"]) != "Small", 3),
               (rect_in(c[p_ + "Shake"], form), w.get_text(c["lblTitle"])))
    finally:
        w.stop(proc, form)


__all__ = ["Report", "drive"]
