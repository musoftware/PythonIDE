"""Drive a running native exe from a test: top-level windows of a process, UI Automation lookup by
AutomationId (= the WinForms control Name) or by name, BM_CLICK / WM_GETTEXT / WM_SETTEXT, menu items.
Only processes the test started are touched."""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT,
                                       wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_CLOSE = 0x000C, 0x000D, 0x000E, 0x0010
BM_CLICK, LB_GETCOUNT = 0x00F5, 0x018B


def top_windows(pid: int, visible_only: bool = True) -> list[int]:
    out = []

    def cb(h, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and (not visible_only or user32.IsWindowVisible(h)):
            out.append(h)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def text(hwnd: int) -> str:
    n = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
    buf = ctypes.create_unicode_buffer(n + 2)
    user32.SendMessageW(hwnd, WM_GETTEXT, n + 1, ctypes.cast(buf, ctypes.c_void_p).value)
    return buf.value


def set_text(hwnd: int, value: str) -> None:
    buf = ctypes.create_unicode_buffer(value)
    user32.SendMessageW(hwnd, WM_SETTEXT, 0, ctypes.cast(buf, ctypes.c_void_p).value)


def click(hwnd: int) -> None:
    """BM_CLICK, sent with a timeout (a handler that opens a modal dialog must not block the test)."""
    res = ctypes.c_size_t()
    user32.SendMessageTimeoutW(hwnd, BM_CLICK, 0, 0, 0x0002, 5000, ctypes.byref(res))


def list_count(hwnd: int) -> int:
    return int(user32.SendMessageW(hwnd, LB_GETCOUNT, 0, 0))


def close(hwnd: int) -> None:
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def wait(pred, timeout: float = 15.0, step: float = 0.1):
    end = time.time() + timeout
    while time.time() < end:
        try:
            v = pred()
        except Exception:  # noqa: BLE001 - window not ready yet
            v = None
        if v:
            return v
        time.sleep(step)
    return None


class UIA:
    """Minimal UI Automation (comtypes) for lookups by AutomationId / Name and menu invoke."""

    def __init__(self):
        import comtypes.client
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen import UIAutomationClient as U
        self.U = U
        self.uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=U.IUIAutomation)

    def root(self, hwnd: int):
        return self.uia.ElementFromHandle(hwnd)

    def find(self, parent, automation_id: str = "", name: str = "", pid: int = 0):
        U = self.U
        cond = (self.uia.CreatePropertyCondition(U.UIA_AutomationIdPropertyId, automation_id) if automation_id
                else self.uia.CreatePropertyCondition(U.UIA_NamePropertyId, name))
        if pid:
            cond = self.uia.CreateAndCondition(cond, self.uia.CreatePropertyCondition(U.UIA_ProcessIdPropertyId, pid))
        try:
            el = parent.FindFirst(U.TreeScope_Descendants, cond)
        except Exception:  # noqa: BLE001
            return None
        return el if el else None

    def hwnd(self, parent, automation_id: str) -> int:
        el = self.find(parent, automation_id)
        return int(el.CurrentNativeWindowHandle or 0) if el else 0

    def invoke_menu(self, window, path: list[str]) -> bool:
        """Open the menu items of *path* (by Name) and invoke the last one."""
        U = self.U
        scope = window
        pid = int(window.CurrentProcessId)
        for i, name in enumerate(path):
            el = wait(lambda: self.find(scope, name=name, pid=pid)
                      or self.find(self.uia.GetRootElement(), name=name, pid=pid), 5)
            if not el:
                return False
            if i < len(path) - 1:
                pat = el.GetCurrentPattern(U.UIA_ExpandCollapsePatternId)
                if pat:
                    pat.QueryInterface(U.IUIAutomationExpandCollapsePattern).Expand()
                else:
                    el.GetCurrentPattern(U.UIA_InvokePatternId).QueryInterface(U.IUIAutomationInvokePattern).Invoke()
                time.sleep(0.4)
                scope = self.uia.GetRootElement()
            else:
                el.GetCurrentPattern(U.UIA_InvokePatternId).QueryInterface(U.IUIAutomationInvokePattern).Invoke()
        return True
