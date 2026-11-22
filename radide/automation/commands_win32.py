"""Win32 commands for the programs the IDE starts (and their published exes): list their windows and child
controls, screenshot a window with PrintWindow (works on a hidden desktop / behind other windows), click,
set / read text, send characters, close. They run inside the IDE process, so they see the windows of the
desktop the IDE runs on (a test may start the IDE on its own desktop, samples/Tests/E2E/radauto.py)."""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path

from .registry import AutomationError, command

if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                           wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.GetWindowDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.GetDlgCtrlID.argtypes = [wintypes.HWND]
    user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ChildWindowFromPointEx.argtypes = [wintypes.HWND, wintypes.POINT, wintypes.UINT]
    user32.ChildWindowFromPointEx.restype = wintypes.HWND
    user32.SetFocus.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
                                ctypes.c_void_p, wintypes.UINT]

WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_CLOSE, WM_CHAR = 0x000C, 0x000D, 0x000E, 0x0010, 0x0102
WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK, WM_MOUSEMOVE = 0x0201, 0x0202, 0x0203, 0x0200
WM_KEYDOWN, WM_KEYUP, BM_CLICK, BM_GETCHECK = 0x0100, 0x0101, 0x00F5, 0x00F0
LB_GETCOUNT, LB_GETTEXT, LB_GETTEXTLEN = 0x018B, 0x0189, 0x018A
CB_GETCOUNT, CB_GETLBTEXT, CB_GETLBTEXTLEN = 0x0146, 0x0148, 0x0149
LVM_GETITEMCOUNT = 0x1004


def _need_win():
    if sys.platform != "win32":
        raise AutomationError("Windows only")


def descendants(pid: int) -> list[int]:
    """Process ids of every descendant of *pid* (Toolhelp snapshot)."""
    _need_win()

    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = kernel32.CreateToolhelp32Snapshot(2, 0)
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    kids: dict[int, list[int]] = {}
    names: dict[int, str] = {}
    ok = kernel32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        kids.setdefault(pe.th32ParentProcessID, []).append(pe.th32ProcessID)
        names[pe.th32ProcessID] = pe.szExeFile
        ok = kernel32.Process32NextW(snap, ctypes.byref(pe))
    kernel32.CloseHandle(snap)
    out, todo = [], [int(pid)]
    while todo:
        p = todo.pop()
        for c in kids.get(p, []):
            if c not in out and c != p:
                out.append(c)
                todo.append(c)
    descendants.names = names          # type: ignore[attr-defined]
    return out


def _text(h) -> str:
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, buf, n + 1)
    t = buf.value
    if not t:                            # edits of other processes: WM_GETTEXT
        res = ctypes.c_size_t()
        if user32.SendMessageTimeoutW(h, WM_GETTEXTLENGTH, 0, 0, 2, 1000, ctypes.byref(res)) and res.value:
            buf = ctypes.create_unicode_buffer(res.value + 1)
            user32.SendMessageTimeoutW(h, WM_GETTEXT, res.value + 1, ctypes.addressof(buf), 2, 1000,
                                       ctypes.byref(res))
            t = buf.value
    return t


def _cls(h) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, buf, 256)
    return buf.value


def _rect(h) -> list[int]:
    r = wintypes.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    return [r.left, r.top, r.right - r.left, r.bottom - r.top]


def _pid_of(h) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def describe(h) -> dict:
    h = int(h.value or 0) if isinstance(h, wintypes.HWND) else int(h)
    d = {"hwnd": int(h), "cls": _cls(h), "text": _text(h), "visible": bool(user32.IsWindowVisible(h)),
         "rect": _rect(h), "pid": _pid_of(h), "id": user32.GetDlgCtrlID(h)}
    try:
        exe = getattr(descendants, "names", {}).get(d["pid"])
        if exe:
            d["exe"] = exe
    except Exception:  # noqa: BLE001
        pass
    return d


def top_windows(pids: set[int] | None = None, visible_only: bool = True) -> list[dict]:
    _need_win()
    out = []

    def cb(h, _l):
        if (not visible_only or user32.IsWindowVisible(h)) and (pids is None or _pid_of(h) in pids):
            out.append(describe(h))
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def children(hwnd: int) -> list[dict]:
    out = []

    def cb(h, _l):
        d = describe(h)
        d["parent"] = int(user32.GetParent(h) or 0)
        out.append(d)
        return True
    user32.EnumChildWindows(wintypes.HWND(hwnd), WNDENUMPROC(cb), 0)
    return out


def _pids(pid: int | None, tree: bool) -> set[int] | None:
    if pid is None:
        return set(descendants(os.getpid()))           # everything the IDE started
    return {int(pid), *descendants(int(pid))} if tree else {int(pid)}


@command("win32_windows", doc="visible top-level windows of a process tree (default: every program the IDE "
                              "started); exe names included")
def _windows(ctx, pid: int | None = None, tree: bool = True, all_: bool = False, title: str = ""):
    ws = top_windows(None if all_ else _pids(pid, tree))
    if title:
        ws = [w for w in ws if title.lower() in w["text"].lower()]
    return ws


@command("win32_children", doc="child windows (controls) of a window: [{hwnd, cls, text, rect, id, visible}]")
def _children(ctx, hwnd: int):
    return children(int(hwnd))


def find_child(hwnd: int, text: str = "", cls: str = "", index: int = 0) -> int:
    hits = [c for c in children(hwnd)
            if (not text or text.lower() in c["text"].replace("&", "").lower())
            and (not cls or cls.lower() in c["cls"].lower())]
    if len(hits) <= index:
        raise AutomationError(f"no child text={text!r} cls={cls!r} in {hwnd}")
    return hits[index]["hwnd"]


@command("win32_grab", doc="screenshot of a window with PrintWindow (PW_RENDERFULLCONTENT) into a PNG")
def _grab(ctx, hwnd: int, path: str):
    _need_win()
    from PyQt6.QtGui import QImage
    h = wintypes.HWND(int(hwnd))
    x, y, w, hh = _rect(h)
    if w <= 0 or hh <= 0:
        raise AutomationError(f"window {hwnd} has no size")
    wdc = user32.GetWindowDC(h)
    mdc = gdi32.CreateCompatibleDC(wdc)
    bmp = gdi32.CreateCompatibleBitmap(wdc, w, hh)
    old = gdi32.SelectObject(mdc, bmp)
    ok = user32.PrintWindow(h, mdc, 2) or user32.PrintWindow(h, mdc, 0)

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    bih = BIH()
    bih.biSize = ctypes.sizeof(BIH)
    bih.biWidth, bih.biHeight, bih.biPlanes, bih.biBitCount = w, -hh, 1, 32
    buf = ctypes.create_string_buffer(w * hh * 4)
    gdi32.SelectObject(mdc, old)
    gdi32.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(h, wdc)
    img = QImage(buf.raw, w, hh, w * 4, QImage.Format.Format_RGB32).copy()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    blank = len(set(buf.raw[i:i + 4] for i in range(0, min(len(buf.raw), 400000), 4 * 97))) <= 2
    return {"path": path, "size": [w, hh], "printwindow": bool(ok), "blank": blank}


def _lparam(x: int, y: int) -> int:
    return (int(y) & 0xFFFF) << 16 | (int(x) & 0xFFFF)


class attached:
    """Share the input state with the window's thread (AttachThreadInput) for the duration of a gesture:
    toolkits such as Tk read the button / modifier state with GetKeyState(), which a plain posted message
    does not change, and SetFocus() on another thread's window is only allowed while attached. Works on a
    desktop that is not the input desktop (no SendInput, nothing reaches the user's mouse / keyboard)."""

    def __init__(self, hwnd: int):
        self.hwnd = int(hwnd)

    def __enter__(self):
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.tid = user32.GetWindowThreadProcessId(wintypes.HWND(self.hwnd), None)
        self.me = kernel32.GetCurrentThreadId()
        self.ok = bool(self.tid and self.tid != self.me and user32.AttachThreadInput(self.me, self.tid, True))
        self.state = (ctypes.c_ubyte * 256)()
        user32.GetKeyboardState(self.state)
        return self

    def keys(self, vks: dict) -> None:
        for vk, down in vks.items():
            self.state[vk] = 0x80 if down else 0
        user32.SetKeyboardState(self.state)

    def __exit__(self, *exc):
        for vk in (0x01, 0x02, 0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3):
            self.state[vk] = 0
        user32.SetKeyboardState(self.state)
        if self.ok:
            user32.AttachThreadInput(self.me, self.tid, False)


def _pump(ms: int) -> None:
    try:
        from .commands_core import pump
        pump(ms)
    except Exception:  # noqa: BLE001
        import time
        time.sleep(ms / 1000)


def _send(h, msg, wp, lp):
    res = ctypes.c_size_t()
    user32.SendMessageTimeoutW(wintypes.HWND(h), msg, wp, lp, 2, 5000, ctypes.byref(res))


def input_click(h: int, x: int, y: int, double: bool = False, right: bool = False) -> None:
    lp = _lparam(x, y)
    down, up, dbl, vk, mk = ((0x0204, 0x0205, 0x0206, 0x02, 2) if right else
                             (WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK, 0x01, 1))
    with attached(h) as a:
        _send(h, WM_MOUSEMOVE, 0, lp)
        a.keys({vk: True})
        _send(h, down, mk, lp)
        _pump(60)
        a.keys({vk: False})
        _send(h, up, 0, lp)
        _pump(60)
        if double:
            a.keys({vk: True})
            _send(h, dbl, mk, lp)
            _pump(60)
            a.keys({vk: False})
            _send(h, up, 0, lp)
            _pump(60)


VK = {"return": 0x0D, "enter": 0x0D, "tab": 0x09, "escape": 0x1B, "esc": 0x1B, "back": 0x08, "backspace": 0x08,
      "delete": 0x2E, "del": 0x2E, "home": 0x24, "end": 0x23, "left": 0x25, "up": 0x26, "right": 0x27,
      "down": 0x28, "space": 0x20, "pageup": 0x21, "pagedown": 0x22, "insert": 0x2D,
      **{f"f{i}": 0x6F + i for i in range(1, 13)}}
MOD = {"shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12}


def input_key(h: int, combo: str) -> None:
    parts = [x.strip().lower() for x in combo.split("+") if x.strip()]
    mods = [MOD[x] for x in parts[:-1] if x in MOD]
    key = parts[-1]
    vk = VK.get(key) or (ord(key.upper()) if len(key) == 1 else None)
    if vk is None:
        raise AutomationError(f"unknown key {combo!r}")
    user32.MapVirtualKeyW.restype = wintypes.UINT
    sc = user32.MapVirtualKeyW(vk, 0)
    alt = 0x12 in mods
    with attached(h) as a:
        user32.SetFocus(wintypes.HWND(h))
        a.keys({m: True for m in mods})
        a.keys({vk: True})
        _send(h, 0x0104 if alt else WM_KEYDOWN, vk, 1 | (sc << 16))
        if vk in (0x0D, 0x09, 0x08, 0x1B) and not mods:
            _send(h, WM_CHAR, vk, 1 | (sc << 16))
        elif 0x11 in mods and 0x41 <= vk <= 0x5A:
            _send(h, WM_CHAR, vk - 0x40, 1 | (sc << 16))       # Ctrl+A -> 0x01 ...
        _pump(30)
        a.keys({vk: False})
        _send(h, 0x0105 if alt else WM_KEYUP, vk, 0xC0000001 | (sc << 16))
        a.keys({m: False for m in mods})
        _pump(30)


def input_text(h: int, text: str) -> None:
    with attached(h):
        user32.SetFocus(wintypes.HWND(h))
        for ch in text:
            if ch == "\n":
                input_key(h, "Return")
                continue
            _send(h, WM_CHAR, ord(ch), 1)
            _pump(5)


@command("win32_click", doc="click a window / control like a mouse (input state shared with its thread, "
                            "works for Tk / Qt / Win32): hwnd + optional child text/cls, client x/y; "
                            "how='bm_click' for BM_CLICK on a native button")
def _click(ctx, hwnd: int, text: str = "", cls: str = "", x: int | None = None, y: int | None = None,
           double: bool = False, right: bool = False, index: int = 0, how: str = "input"):
    target = find_child(int(hwnd), text, cls, index) if (text or cls) else int(hwnd)
    h = wintypes.HWND(target)
    if how == "bm_click":
        user32.PostMessageW(h, BM_CLICK, 0, 0)
        return {"hwnd": target, "how": "BM_CLICK"}
    if x is None:
        r = wintypes.RECT()
        user32.GetClientRect(h, ctypes.byref(r))
        x, y = r.right // 2, r.bottom // 2
    input_click(target, int(x), int(y), double, right)
    return {"hwnd": target, "how": "input", "x": x, "y": y}


@command("win32_set_text", doc="WM_SETTEXT on a window / child control (a native edit box)")
def _set_text(ctx, hwnd: int, value: str, text: str = "", cls: str = "", index: int = 0):
    target = find_child(int(hwnd), text, cls, index) if (text or cls) else int(hwnd)
    buf = ctypes.create_unicode_buffer(value)
    res = ctypes.c_size_t()
    user32.SendMessageTimeoutW(wintypes.HWND(target), WM_SETTEXT, 0, ctypes.addressof(buf), 2, 3000,
                               ctypes.byref(res))
    return {"hwnd": target, "text": _text(wintypes.HWND(target))}


@command("win32_type", doc="type text into a window / child (focus set while attached, WM_CHAR per character)")
def _type(ctx, hwnd: int, value: str, text: str = "", cls: str = "", index: int = 0):
    target = find_child(int(hwnd), text, cls, index) if (text or cls) else int(hwnd)
    input_text(target, value)
    return {"hwnd": target}


@command("win32_key", doc="press keys in a window: 'Return', 'Ctrl+A', 'Shift+End', 'F5', 'Alt+F4' "
                          "(comma separated for several)")
def _key(ctx, hwnd: int, keys: str, text: str = "", cls: str = "", index: int = 0):
    target = find_child(int(hwnd), text, cls, index) if (text or cls) else int(hwnd)
    for k in [x.strip() for x in keys.split(",") if x.strip()]:
        input_key(target, k)
    return {"hwnd": target}


@command("win32_text", doc="text of a window / child control (WM_GETTEXT), list box / combo items")
def _get_text(ctx, hwnd: int, text: str = "", cls: str = "", index: int = 0):
    target = find_child(int(hwnd), text, cls, index) if (text or cls) else int(hwnd)
    h = wintypes.HWND(target)
    d = describe(h)
    c = d["cls"].lower()
    if "listbox" in c or "combobox" in c:
        cnt_msg, len_msg, get_msg = ((LB_GETCOUNT, LB_GETTEXTLEN, LB_GETTEXT) if "listbox" in c
                                     else (CB_GETCOUNT, CB_GETLBTEXTLEN, CB_GETLBTEXT))
        n = user32.SendMessageW(h, cnt_msg, 0, 0)
        items = []
        for i in range(max(0, min(n, 500))):
            ln = user32.SendMessageW(h, len_msg, i, 0)
            buf = ctypes.create_unicode_buffer(max(ln, 0) + 2)
            user32.SendMessageW(h, get_msg, i, ctypes.addressof(buf))
            items.append(buf.value)
        d["items"] = items
    if c == "button":
        d["checked"] = user32.SendMessageW(h, BM_GETCHECK, 0, 0)
    return d


@command("win32_close", doc="WM_CLOSE to a window (the program's own close, like the X button)")
def _close(ctx, hwnd: int):
    user32.PostMessageW(wintypes.HWND(int(hwnd)), WM_CLOSE, 0, 0)
    return True


@command("win32_kill", doc="terminate a process the IDE started (only descendants of the IDE)")
def _kill(ctx, pid: int):
    if int(pid) not in descendants(os.getpid()):
        raise AutomationError(f"{pid} was not started by this IDE")
    h = kernel32.OpenProcess(0x0001, False, int(pid))
    if not h:
        raise AutomationError(f"cannot open process {pid}")
    kernel32.TerminateProcess(h, 1)
    kernel32.CloseHandle(h)
    return True


@command("start_process", doc="start a program (e.g. a published exe) from the IDE process, so it runs on "
                              "the IDE's desktop; returns its pid")
def _start_process(ctx, argv: list, cwd: str | None = None, env: dict | None = None):
    import subprocess
    e = dict(os.environ)
    e.update({k: str(v) for k, v in (env or {}).items()})
    p = subprocess.Popen([str(a) for a in argv], cwd=cwd, env=e, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    ctx.data.setdefault("procs", {})[p.pid] = p
    return {"pid": p.pid}


@command("process_status", doc="exit code of a process started with start_process (None while running)")
def _process_status(ctx, pid: int):
    p = ctx.data.get("procs", {}).get(int(pid))
    if p is None:
        raise AutomationError(f"{pid} was not started with start_process")
    return {"pid": p.pid, "returncode": p.poll()}


@command("win32_menu", doc="choose an item of a window's menu bar by text path ('File/Export CSV'): WM_COMMAND "
                           "with the item's id (Win32 / Tk menus); list=True returns the menu tree")
def _menu(ctx, hwnd: int, path: str = "", list_: bool = False):
    user32.GetMenu.restype = wintypes.HMENU
    user32.GetSubMenu.restype = wintypes.HMENU
    user32.GetMenu.argtypes = [wintypes.HWND]
    user32.GetSubMenu.argtypes = [wintypes.HMENU, ctypes.c_int]
    user32.GetMenuItemCount.argtypes = [wintypes.HMENU]
    user32.GetMenuItemID.argtypes = [wintypes.HMENU, ctypes.c_int]
    user32.GetMenuItemID.restype = wintypes.UINT
    user32.GetMenuStringW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.LPWSTR, ctypes.c_int, wintypes.UINT]
    h = user32.GetMenu(wintypes.HWND(int(hwnd)))
    if not h:
        raise AutomationError(f"window {hwnd} has no menu bar")

    def items(menu):
        out = []
        for i in range(user32.GetMenuItemCount(menu)):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetMenuStringW(menu, i, buf, 256, 0x400)          # MF_BYPOSITION
            sub = user32.GetSubMenu(menu, i)
            out.append((buf.value.replace("&", "").split("\t")[0].strip(), sub, user32.GetMenuItemID(menu, i)))
        return out

    def tree(menu):
        return [{"text": t, "items": tree(s)} if s else {"text": t, "id": i} for t, s, i in items(menu)]
    if list_ or not path:
        return tree(h)
    menu = h
    parts = [p.strip().lower() for p in path.split("/")]
    for n, part in enumerate(parts):
        hit = next(((t, s, i) for t, s, i in items(menu) if t.lower() == part), None) or next(
            ((t, s, i) for t, s, i in items(menu) if part in t.lower()), None)
        if hit is None:
            raise AutomationError(f"no menu item {part!r} in {[t for t, _s, _i in items(menu)]}")
        if n == len(parts) - 1:
            user32.PostMessageW(wintypes.HWND(int(hwnd)), 0x0111, hit[2] & 0xFFFF, 0)     # WM_COMMAND
            return {"item": hit[0], "id": hit[2]}
        menu = hit[1]
        if not menu:
            raise AutomationError(f"{hit[0]!r} has no submenu")
    return None
