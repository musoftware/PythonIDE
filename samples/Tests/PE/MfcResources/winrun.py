"""Run a MiniMfc exe for a moment and drive it through Win32 (ctypes): click buttons, send menu commands,
read the status text, close message boxes. Only processes started here are touched (and always closed)."""
from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetDlgItem.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetDlgItem.restype = wintypes.HWND
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]

WM_COMMAND, WM_CLOSE, BM_CLICK, WM_USER = 0x111, 0x10, 0xF5, 0x400


def windows_of(pid: int) -> list[int]:
    found = []

    def cb(hwnd, _l):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found


def text(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


class App:
    def __init__(self, exe, timeout: float = 10.0):
        self.proc = subprocess.Popen([str(exe)])
        self.hwnd = None
        end = time.time() + timeout
        while time.time() < end and self.proc.poll() is None:
            ws = [w for w in windows_of(self.proc.pid) if text(w)]
            if ws:
                self.hwnd = ws[0]
                break
            time.sleep(0.1)

    @property
    def ok(self) -> bool:
        return self.hwnd is not None

    def title(self) -> str:
        return text(self.hwnd)

    def item_text(self, ctrl_id: int) -> str:
        return text(user32.GetDlgItem(self.hwnd, ctrl_id))

    def click(self, ctrl_id: int) -> None:
        user32.SendMessageW(self.hwnd, WM_COMMAND, ctrl_id & 0xFFFF, user32.GetDlgItem(self.hwnd, ctrl_id) or 0)

    def command(self, cmd_id: int) -> None:
        user32.SendMessageW(self.hwnd, WM_COMMAND, cmd_id & 0xFFFF, 0)

    def send(self, msg: int, wp: int = 0, lp: int = 0) -> int:
        return user32.SendMessageW(self.hwnd, msg, wp, lp)

    def popups(self) -> list[int]:
        return [w for w in windows_of(self.proc.pid) if w != self.hwnd]

    def post_click(self, ctrl_id: int) -> None:
        user32.PostMessageW(self.hwnd, WM_COMMAND, ctrl_id & 0xFFFF, user32.GetDlgItem(self.hwnd, ctrl_id) or 0)

    def wait_popup(self, timeout: float = 5.0) -> int | None:
        end = time.time() + timeout
        while time.time() < end:
            p = self.popups()
            if p:
                return p[0]
            time.sleep(0.1)
        return None

    def close(self) -> None:
        try:
            for w in self.popups():
                user32.PostMessageW(w, WM_CLOSE, 0, 0)
            if self.hwnd:
                user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
            self.proc.wait(5)
        except Exception:  # noqa: BLE001
            pass
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(5)
