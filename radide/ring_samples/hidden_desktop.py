"""Start a program on a hidden Windows desktop (CreateDesktopW + STARTUPINFO.lpDesktop).

Used by the Ring Samples test run (tools/index_ring_samples.py --test) so that hundreds of GUI / game
samples (RingQt, RayLib, LibSDL, FreeGLUT ...) can be started and killed without their windows
flashing on the user's screen. Not used by the gallery's interactive "Run" button.
Windows only; elsewhere start() falls back to a plain subprocess.Popen.
"""
from __future__ import annotations


import subprocess
import sys

_DESKTOPS: dict[int, int] = {}
DESKTOP_NAME = "RADIDE_RingSamples_Test"
# one desktop per parallel job: GUI programs started together on ONE hidden desktop exhaust its
# desktop heap and then fail to load their DLLs (seen with 8 RingQt samples at once)


class _Proc:
    """Minimal Popen-like wrapper around a CreateProcessW handle (stdout/stderr go to a file)."""

    def __init__(self, hproc, pid, out_path):
        self._h = hproc
        self.pid = pid
        self.out_path = out_path
        self.returncode = None

    def poll(self):
        import ctypes
        k32 = ctypes.windll.kernel32
        if self.returncode is not None:
            return self.returncode
        if k32.WaitForSingleObject(self._h, 0) == 0:
            code = ctypes.c_ulong()
            k32.GetExitCodeProcess(self._h, ctypes.byref(code))
            self.returncode = int(code.value)
            if self.returncode >= 0x80000000:
                self.returncode -= 0x100000000
            return self.returncode
        return None

    def wait(self, timeout=None):
        import ctypes
        ms = 0xFFFFFFFF if timeout is None else int(timeout * 1000)
        ctypes.windll.kernel32.WaitForSingleObject(self._h, ms)
        r = self.poll()
        if r is None:
            raise subprocess.TimeoutExpired("hidden", timeout)
        return r

    def kill(self):
        # the whole tree (a sample may start helpers)
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.pid)], capture_output=True)
        try:
            self.wait(5)
        except Exception:  # noqa: BLE001
            pass

    def close(self):
        import ctypes
        if self._h:
            ctypes.windll.kernel32.CloseHandle(self._h)
            self._h = None


def desktop_name(slot: int = 0) -> str:
    return f"{DESKTOP_NAME}_{slot}"


def _desktop(slot: int = 0):
    if slot not in _DESKTOPS:
        import ctypes
        GENERIC_ALL = 0x10000000
        u32 = ctypes.windll.user32
        u32.CreateDesktopW.restype = ctypes.c_void_p
        _DESKTOPS[slot] = u32.CreateDesktopW(desktop_name(slot), None, None, 0, GENERIC_ALL, None)
    return _DESKTOPS[slot]


def start(cmd: list[str], cwd: str, env: dict, out_path: str, stdin_path: str | None = None, slot: int = 0):
    """Start *cmd* on hidden desktop number *slot* with stdout+stderr redirected to *out_path*.
    Returns a Popen-like object (poll / wait / kill / close)."""
    if sys.platform != "win32" or not _desktop(slot):
        out = open(out_path, "wb")
        inp = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT, stdin=inp)
        p.out_path = out_path
        return p
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                    ("bInheritHandle", wintypes.BOOL)]

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
                    ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    k32.CreateFileW.restype = wintypes.HANDLE
    sa = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    GENERIC_WRITE, GENERIC_READ = 0x40000000, 0x80000000
    hout = k32.CreateFileW(out_path, GENERIC_WRITE, 3, ctypes.byref(sa), 2, 0x80, None)   # CREATE_ALWAYS
    hin = k32.CreateFileW(stdin_path or "NUL", GENERIC_READ, 3, ctypes.byref(sa), 3, 0x80, None)
    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    si.lpDesktop = desktop_name(slot)
    si.dwFlags = 0x100                       # STARTF_USESTDHANDLES
    si.hStdInput, si.hStdOutput, si.hStdError = hin, hout, hout
    pi = PROCESS_INFORMATION()
    block = "".join(f"{k}={v}\0" for k, v in sorted(env.items())) + "\0"
    CREATE_UNICODE_ENVIRONMENT, CREATE_NO_WINDOW = 0x400, 0x08000000
    ok = k32.CreateProcessW(None, ctypes.create_unicode_buffer(subprocess.list2cmdline(cmd)), None, None,
                            True, CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
                            ctypes.create_unicode_buffer(block), cwd, ctypes.byref(si), ctypes.byref(pi))
    k32.CloseHandle(hout)
    k32.CloseHandle(hin)
    if not ok:
        raise OSError(f"CreateProcessW failed ({ctypes.GetLastError()})")
    k32.CloseHandle(pi.hThread)
    return _Proc(pi.hProcess, pi.dwProcessId, out_path)


__all__ = ["start", "DESKTOP_NAME"]
