"""F5 with "console": "external": the program runs under gdb in its OWN console window (gdb's new-console) and
reads its input there.

The test creates the NASM x64 console template with "console": "external", builds it, starts the IDE's assembly
debug session (radide.nativedbg.asm_debug_session(new_console=True), what asm_console_session uses for such a
project) with a breakpoint on the line after scanf, finds the program's process, attaches to ITS console
(AttachConsole), checks the prompt is printed there, types "5" + Enter into that console (WriteConsoleInputW),
and waits for the breakpoint: `number` must be 5. Then it continues to the end (exit code 0).

    python samples/Tests/Assembly/CoreTests/test_external_console.py
"""
import ctypes
import shutil
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QCoreApplication                     # noqa: E402

from radide import nativedbg as nd                              # noqa: E402
from radide.asm.build import Builder                            # noqa: E402
from radide.languages import get_plugin                          # noqa: E402
from radide.model import Project                                 # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def wait(cond, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.03)
    return False


# ------------------------------------------------------------------ Win32 helpers (console of another process)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]


def processes():
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    out = []
    ok = k32.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        out.append((e.th32ProcessID, e.th32ParentProcessID, e.szExeFile))
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    return out


class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [("bKeyDown", wintypes.BOOL), ("wRepeatCount", wintypes.WORD), ("wVirtualKeyCode", wintypes.WORD),
                ("wVirtualScanCode", wintypes.WORD), ("UnicodeChar", wintypes.WCHAR),
                ("dwControlKeyState", wintypes.DWORD)]


class INPUT_RECORD(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("KeyEvent", KEY_EVENT_RECORD), ("_pad", ctypes.c_byte * 16)]
    _fields_ = [("EventType", wintypes.WORD), ("Event", _U)]


GENERIC_RW = 0x80000000 | 0x40000000
k32.CreateFileW.restype = wintypes.HANDLE


def console_of(pid):
    """(input handle, output handle) of the console of *pid* (this process attaches to it)."""
    k32.FreeConsole()
    if not k32.AttachConsole(pid):
        return None, None
    hin = k32.CreateFileW("CONIN$", GENERIC_RW, 3, None, 3, 0, None)
    hout = k32.CreateFileW("CONOUT$", GENERIC_RW, 3, None, 3, 0, None)
    return hin, hout


def screen_text(hout, rows=10, cols=120):
    buf = ctypes.create_unicode_buffer(rows * cols)
    n = wintypes.DWORD()
    k32.ReadConsoleOutputCharacterW(hout, buf, rows * cols, wintypes.DWORD(0), ctypes.byref(n))
    return buf.value[:n.value]


def type_text(hin, text):
    recs = (INPUT_RECORD * (2 * len(text)))()
    for i, ch in enumerate(text):
        vk = 0x0D if ch == "\r" else ord(ch.upper())
        for j, down in enumerate((True, False)):
            r = recs[2 * i + j]
            r.EventType = 1                                 # KEY_EVENT
            r.Event.KeyEvent.bKeyDown = down
            r.Event.KeyEvent.wRepeatCount = 1
            r.Event.KeyEvent.wVirtualKeyCode = vk
            r.Event.KeyEvent.UnicodeChar = ch
    n = wintypes.DWORD()
    return bool(k32.WriteConsoleInputW(hin, recs, len(recs), ctypes.byref(n))) and n.value == len(recs)


# ------------------------------------------------------------------ the project
folder = Path(tempfile.gettempdir()) / "radide-asm-tests" / "external_console" / "ExtConsole"
shutil.rmtree(folder, ignore_errors=True)
plugin = get_plugin("asm-nasm")
project = plugin.create_new_project(folder, "ExtConsole", "nasm_console_x64")
project.extra["asm"]["console"] = "external"
project.save()
project = Project.load(folder)
check("project console = external", plugin.settings(project).get("console") == "external")
logs = []
ok = Builder(folder, log=logs.append).build()
check("build", ok, "" if ok else "\n".join(logs[-8:]))
exe = folder / "_radapp.exe"
src = folder / "main.asm"
lines = src.read_text(encoding="utf-8").splitlines()
bp = next(i + 1 for i, l in enumerate(lines) if l.strip().startswith("imul rax, rax"))

# the session asm_console_session makes for such a project: new_console, no stdin pipe
made = {}
orig = nd.asm_debug_session


def spy(*a, **k):
    made.update(k)
    return None


nd.asm_debug_session = spy
try:
    from radide.languages.base import RunSpec
    spec = plugin.run_spec(folder, "", sys.executable)
    chain = nd.asm_console_session(None, plugin, RunSpec(spec.program, spec.args, spec.cwd, spec.env), True)
    chain.factory()
except Exception as e:  # noqa: BLE001
    made["error"] = repr(e)
finally:
    nd.asm_debug_session = orig
check("asm_console_session: new console, no Program Input pipe", made.get("new_console") is True and
      made.get("stdin_pipe") is False, str(made))

s = nd.asm_debug_session(None, exe, [], folder, None, sources=[src], breakpoints=[(str(src), bp, "")],
                         new_console=True)
check("gdb is started with 'set new-console on'", s is not None and "set new-console on" in s.argv, str(s and s.argv))
stops, outs, done = [], [], []
s.stopped.connect(stops.append)
s.output.connect(outs.append)
s.finished.connect(done.append)
s.start()
gdb_pid = s.proc.processId()
child = []
wait(lambda: child.extend(p for p in processes() if p[2].lower() == "_radapp.exe" and p[1] == gdb_pid) or child, 40)
check("the program runs as a child of gdb", bool(child), f"gdb pid {gdb_pid}")
typed = False
prompt = ""
if child:
    pid = child[0][0]
    hin = hout = None
    for _ in range(50):                          # the console needs a moment
        pump(0.2)
        hin, hout = console_of(pid)
        if hin and hin != wintypes.HANDLE(-1).value:
            prompt = screen_text(hout)
            if "Enter a number" in prompt:
                break
        k32.FreeConsole()
    check("the program has its own console with the prompt", "Enter a number" in prompt, prompt.strip()[:120])
    if hin:
        typed = type_text(hin, "5\r")
    k32.FreeConsole()
check("typed '5' + Enter into the program's console", typed)
ok = wait(lambda: stops, 30)
info = stops[-1] if stops else None
check("stops on the breakpoint after scanf", ok and Path(info.file).name == "main.asm" and info.line == bp,
      f"{info and (info.file, info.line, info.reason)}")
val = []
if ok:
    nd.gdb_command(s, "x/gd &number", lambda t, ok2: val.append(t))
    wait(lambda: val, 15)
check("number read from the console = 5", bool(val) and val[0].strip().endswith("5"), val[0].strip() if val else "")
s.cont()
wait(lambda: done, 30)
check("program ends (exit code 0)", done and done[-1] == 0, str(done))
if not done:
    s.stop()
    pump(1)

passed = sum(1 for _n, ok in results if ok)
print(f"\n{passed} / {len(results)} checks passed")
print("RESULT", "OK" if passed == len(results) else "FAIL")
sys.exit(0 if passed == len(results) else 1)
