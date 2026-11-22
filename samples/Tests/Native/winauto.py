"""Tiny ctypes helpers to drive a native (radforms) exe from a test: find its windows by the
"radforms.name" property (global atom of the control name), click, set / read text, menus.
Only the process the test started is touched."""
from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
user32.EnumChildWindows.argtypes = [wt.HWND, WNDENUMPROC, wt.LPARAM]
user32.GetPropW.argtypes = [wt.HWND, wt.LPCWSTR]
user32.GetPropW.restype = wt.HANDLE
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetMenu.argtypes = [wt.HWND]
user32.GetMenu.restype = wt.HMENU
user32.GetSubMenu.argtypes = [wt.HMENU, ctypes.c_int]
user32.GetSubMenu.restype = wt.HMENU
user32.GetMenuItemID.argtypes = [wt.HMENU, ctypes.c_int]
user32.GetMenuItemID.restype = wt.UINT
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
kernel32.GlobalGetAtomNameW.argtypes = [wt.ATOM, wt.LPWSTR, ctypes.c_int]

WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_CLOSE, WM_COMMAND = 0x000C, 0x000D, 0x000E, 0x0010, 0x0111
BM_CLICK, BM_GETCHECK, LB_GETCOUNT, CB_SETCURSEL, CBN_SELCHANGE = 0x00F5, 0x00F0, 0x018B, 0x014E, 1
IDOK = 1


def _pid(h) -> int:
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def class_name(h) -> str:
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, b, 256)
    return b.value


def rf_name(h) -> str:
    atom = user32.GetPropW(h, "radforms.name")
    if not atom:
        return ""
    b = ctypes.create_unicode_buffer(256)
    kernel32.GlobalGetAtomNameW(int(atom) & 0xFFFF, b, 256)
    return b.value


def top_windows(pid: int, visible_only=True) -> list:
    out = []

    def cb(h, _l):
        if _pid(h) == pid and (not visible_only or user32.IsWindowVisible(h)):
            out.append(h)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def children(h) -> dict:
    out = {}

    def cb(c, _l):
        n = rf_name(c)
        if n:
            out.setdefault(n, c)
        return True
    user32.EnumChildWindows(h, WNDENUMPROC(cb), 0)
    return out


def get_text(h) -> str:
    n = user32.SendMessageW(h, WM_GETTEXTLENGTH, 0, 0)
    b = ctypes.create_unicode_buffer(n + 2)
    user32.SendMessageW(h, WM_GETTEXT, n + 1, ctypes.cast(b, ctypes.c_void_p).value)
    return b.value


def set_text(h, s: str):
    b = ctypes.create_unicode_buffer(s)
    user32.SendMessageW(h, WM_SETTEXT, 0, ctypes.cast(b, ctypes.c_void_p).value)


def click(h):
    user32.PostMessageW(h, BM_CLICK, 0, 0)


def wait(pred, timeout=8.0, step=0.05):
    end = time.time() + timeout
    while time.time() < end:
        try:
            v = pred()
        except Exception:  # noqa: BLE001
            v = None
        if v:
            return v
        time.sleep(step)
    return None


def form_window(pid: int, name: str, timeout=10.0):
    return wait(lambda: next((h for h in top_windows(pid) if rf_name(h) == name), None), timeout)


def menu_command(form, path: tuple[int, int]):
    """Post the WM_COMMAND of menu item (top index, item index)."""
    sub = user32.GetSubMenu(user32.GetMenu(form), path[0])
    mid = user32.GetMenuItemID(sub, path[1])
    user32.PostMessageW(form, WM_COMMAND, mid, 0)


def dialog_of(pid: int, timeout=5.0):
    return wait(lambda: next((h for h in top_windows(pid) if class_name(h) == "#32770"), None), timeout)


def start(exe) -> subprocess.Popen:
    return subprocess.Popen([str(exe)], cwd=str(exe.parent))


def stop(proc: subprocess.Popen, form=None, timeout=5.0) -> bool:
    """Close the started program (WM_CLOSE to its form); kill only this process if it hangs.
    Returns True when it exited by itself."""
    if form:
        user32.PostMessageW(form, WM_CLOSE, 0, 0)
    try:
        proc.wait(timeout)
        return True
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(5)
        return False


gdi32 = ctypes.WinDLL("gdi32")
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.PrintWindow.argtypes = [wt.HWND, wt.HDC, wt.UINT]
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
gdi32.CreateCompatibleDC.restype = wt.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
gdi32.SelectObject.restype = wt.HGDIOBJ
gdi32.GetPixel.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
gdi32.GetPixel.restype = wt.DWORD
gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wt.HDC]


def grab_pixels(h, points) -> list[tuple[int, int, int]]:
    """Render one window (PrintWindow, client area only - no screen capture) and read some pixels."""
    r = wt.RECT()
    user32.GetClientRect(h, ctypes.byref(r))
    sdc = user32.GetDC(None)
    mem = gdi32.CreateCompatibleDC(sdc)
    bmp = gdi32.CreateCompatibleBitmap(sdc, max(1, r.right), max(1, r.bottom))
    old = gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(h, mem, 1)               # PW_CLIENTONLY
    out = []
    for x, y in points:
        c = gdi32.GetPixel(mem, int(x * r.right) if isinstance(x, float) else x,
                           int(y * r.bottom) if isinstance(y, float) else y)
        out.append((c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF))
    gdi32.SelectObject(mem, old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(None, sdc)
    return out


def mouse_click(h, x=8, y=8):
    user32.PostMessageW(h, 0x0201, 1, (y << 16) | x)      # WM_LBUTTONDOWN
    user32.PostMessageW(h, 0x0202, 0, (y << 16) | x)      # WM_LBUTTONUP


LB_GETTEXT, LB_GETTEXTLEN = 0x0189, 0x018A


def list_item(h, i: int) -> str:
    n = user32.SendMessageW(h, LB_GETTEXTLEN, i, 0)
    b = ctypes.create_unicode_buffer(max(0, n) + 2)
    user32.SendMessageW(h, LB_GETTEXT, i, ctypes.cast(b, ctypes.c_void_p).value)
    return b.value


def click_dialog_button(dlg):
    """Press the first button of a message box (its single OK has id IDCANCEL)."""
    found = []

    def cb(c, _l):
        if class_name(c).lower() == "button":
            found.append(c)
        return True
    user32.EnumChildWindows(dlg, WNDENUMPROC(cb), 0)
    if found:
        click(found[0])
    return bool(found)
