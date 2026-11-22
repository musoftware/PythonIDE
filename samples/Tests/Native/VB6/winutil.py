"""ctypes helpers: find the windows of a process, read texts/rects, click, capture one window (PrintWindow)."""
import ctypes, subprocess, time
from ctypes import wintypes as W
u = ctypes.WinDLL("user32", use_last_error=True)
g = ctypes.WinDLL("gdi32")
EnumProc = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
u.SendMessageW.restype = ctypes.c_ssize_t
u.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
u.GetWindowLongPtrW.argtypes = [W.HWND, ctypes.c_int]

def text(h):
    n = u.SendMessageW(h, 0x000E, 0, 0)
    b = ctypes.create_unicode_buffer(n + 1)
    u.SendMessageW(h, 0x000D, n + 1, ctypes.addressof(b))
    return b.value

def cls(h):
    b = ctypes.create_unicode_buffer(64); u.GetClassNameW(h, b, 64); return b.value

def windows_of(pid, visible=True):
    out = []
    def cb(h, l):
        p = W.DWORD(); u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and (u.IsWindowVisible(h) or not visible): out.append(h)
        return True
    u.EnumWindows(EnumProc(cb), 0); return out

def children(h):
    out = []
    def cb(c, l):
        out.append(c); return True
    u.EnumChildWindows(h, EnumProc(cb), 0); return out

def rect(h):
    r = W.RECT(); u.GetWindowRect(h, ctypes.byref(r)); return (r.left, r.top, r.right - r.left, r.bottom - r.top)

def client_origin(h):
    p = W.POINT(0, 0); u.ClientToScreen(h, ctypes.byref(p)); return p.x, p.y

def client_size(h):
    r = W.RECT(); u.GetClientRect(h, ctypes.byref(r)); return r.right, r.bottom

def wait_window(pid, title=None, timeout=10.0):
    t = time.time()
    while time.time() - t < timeout:
        for h in windows_of(pid):
            if title is None or text(h) == title:
                return h
        time.sleep(0.05)
    return None

def find_child(top, klass=None, txt=None, ctlid=None):
    for c in children(top):
        if klass and cls(c).lower() != klass.lower():
            continue
        if txt is not None and text(c) != txt:
            continue
        if ctlid is not None and u.GetDlgCtrlID(c) != ctlid:
            continue
        return c
    return None

def click(h):
    u.SendMessageW(h, 0x00F5, 0, 0)        # BM_CLICK

def set_text(h, s):
    b = ctypes.create_unicode_buffer(s)
    u.SendMessageW(h, 0x000C, 0, ctypes.addressof(b))

def capture(h, path):
    from PIL import Image
    x, y, w, hh = rect(h)
    hdc = u.GetWindowDC(h); mdc = g.CreateCompatibleDC(hdc); bmp = g.CreateCompatibleBitmap(hdc, w, hh)
    g.SelectObject(mdc, bmp)
    u.PrintWindow(h, mdc, 2)
    class BMI(ctypes.Structure):
        _fields_ = [("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD),
                    ("biBitCount", W.WORD), ("biCompression", W.DWORD), ("biSizeImage", W.DWORD),
                    ("a", W.LONG), ("b", W.LONG), ("c", W.DWORD), ("d", W.DWORD)]
    bmi = BMI(ctypes.sizeof(BMI), w, -hh, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * hh * 4)
    g.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.byref(bmi), 0)
    img = Image.frombuffer("RGBA", (w, hh), buf, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(path)
    g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(h, hdc)
    return img

def close(p):
    if p.poll() is None:
        p.kill()
        p.wait(5)
