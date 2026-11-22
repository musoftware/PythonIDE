"""Event semantics matrix: the same EventsDemo form in every desktop language and execution path, driven with
the same input, logs every event + its arguments; the log is compared with the expected sequence of the
language family (spec.py; differences explained in docs/EVENTS.md).

    .venv\\Scripts\\python samples\\Tests\\Events\\test_events.py [scratch folder] [--only VB6:vbrun,C:native ...]

Paths:
  VB6     vbrun (the IDE's VB runtime, F5)            Tk engine, in process (tk_driver.py)
          native (FreeBASIC exe)                        Win32 messages posted to the exe's windows
  Python  tk (Tkinter project)                          Tk engine, in process
  C, CSharp, Java, Rust, Go, Lua, JS
          native (radforms / WinForms / Swing exe)      Win32 messages posted to the exe's windows
          bridge (the IDE's GUI Bridge host + client)   Tk engine, in process, the client program as a child
Win32 input: WM_LBUTTONDOWN/UP at control coordinates, WM_KEYDOWN / WM_KEYUP (TranslateMessage makes WM_CHAR,
the program's thread is switched to the US layout with WM_INPUTLANGCHANGEREQUEST), WM_SETTEXT, WM_CLOSE - only
to the windows of the processes started here (never a screen capture, never another program). A path whose
tool chain is not installed is SKIPPED with the reason; a native build that falls back to another kind is
SKIPPED too (its reasons are printed). A failing engine run is repeated once (focus can be taken by another
program on a busy desktop); a step passes when one of the runs passed.
Exit code = number of FAILED steps.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes as wt
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "samples" / "Tests" / "Native"))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from evcore import FileLog, PipeLog, compare, run_steps  # noqa: E402
from spec import STEPS, expected  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SCRATCH = Path(args[0]) if args else Path(tempfile.gettempdir()) / "radide_events"
ONLY = None
if "--only" in sys.argv:
    ONLY = {s.strip().lower() for s in sys.argv[sys.argv.index("--only") + 1].split(",")}
PY = sys.executable

ENGINES = [  # (project, path, family, kind)
    ("VB6", "vbrun", "vb6", "tk"), ("VB6", "native", "vb6", "vb6fb"),
    ("Python", "tk", "tk", "tk"),
    ("C", "native", "neutral", "radforms"), ("C", "bridge", "neutral", "tk"),
    ("CSharp", "native", "winforms", "winforms"), ("CSharp", "bridge", "neutral", "tk"),
    ("Java", "native", "swing", "swing"), ("Java", "bridge", "neutral", "tk"),
    ("Rust", "native", "neutral", "radforms"), ("Rust", "bridge", "neutral", "tk"),
    ("Go", "native", "neutral", "radforms"), ("Go", "bridge", "neutral", "tk"),
    ("Lua", "native", "neutral", "radforms"), ("Lua", "bridge", "neutral", "tk"),
    ("JS", "native", "neutral", "radforms"), ("JS", "bridge", "neutral", "tk"),
]
EVENT_FAMILIES = ["lifecycle", "mouse", "focus", "keyboard", "code", "timer", "selection"]

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT,
                                       ctypes.POINTER(ctypes.c_size_t)]
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.MapVirtualKeyW.argtypes = [wt.UINT, wt.UINT]
user32.GetDlgCtrlID.argtypes = [wt.HWND]
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_CLOSE = 0x000C, 0x000D, 0x000E, 0x0010
WM_KEYDOWN, WM_KEYUP, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_INPUTLANGCHANGEREQUEST = 0x100, 0x101, 0x201, 0x202, 0x50
US_LAYOUT = 0x04090409


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hwndActive", wt.HWND), ("hwndFocus", wt.HWND),
                ("hwndCapture", wt.HWND), ("hwndMenuOwner", wt.HWND), ("hwndMoveSize", wt.HWND),
                ("hwndCaret", wt.HWND), ("rcCaret", wt.RECT)]


results: list[dict] = []          # {"engine", "step", "family", "status", "detail"}


def record(engine: str, step: str, family: str, status: str, detail: str = ""):
    """One result line in the runner's contract: PASS name / FAIL name  [detail] / SKIP name (reason)."""
    results.append({"engine": engine, "step": step, "family": family, "status": status, "detail": detail})
    name = f"{engine}/{step}"
    if status == "FAIL":
        print(f"FAIL {name}  [{detail}]", flush=True)
    elif status == "SKIP":
        print(f"SKIP {name}" + (f" ({detail})" if detail else ""), flush=True)
    else:
        print(f"PASS {name}", flush=True)


# ------------------------------------------------------------------ Win32 driver
class Win32Driver:
    """Drives a started exe: *locate(name)* -> (hwnd, x offset, y offset) of a control."""

    # steps whose input the engine only accepts in the foreground window (see needs_foreground)
    FOREGROUND_STEPS = {"mouse_button", "mouse_label", "focus_first", "focus_a_to_b", "focus_b_to_a", "keys",
                        "list_user"}

    def __init__(self, proc, form, locate, names, needs_foreground=False, invoke=None, fg_steps=None):
        self.proc, self.form, self.locate, self.names = proc, form, locate, names
        self.needs_foreground = needs_foreground
        self.fg_steps = set(fg_steps) if fg_steps is not None else self.FOREGROUND_STEPS
        self.invoke = invoke or set()             # controls clicked with BM_CLICK when not in the foreground
        user32.PostMessageW(form, WM_INPUTLANGCHANGEREQUEST, 0, US_LAYOUT)
        if needs_foreground:
            user32.SetForegroundWindow(form)      # allowed only when Windows lets this process do it
            time.sleep(0.3)

    def foreground(self) -> bool:
        return user32.GetForegroundWindow() == self.form

    def cannot(self, step) -> str:
        """WinForms takes the mouse capture and the activation for real: a posted click on a background window
        raises MouseDown / MouseUp but no Click (ButtonBase checks capture + WindowFromPoint), a text box does
        not take the focus. Those steps need the program in the foreground (an interactive / CI desktop)."""
        if self.needs_foreground and step["name"] in self.fg_steps and not self.foreground():
            return "needs the foreground window (the desktop gave it to another program)"
        return ""

    def pump(self, sec):
        time.sleep(sec)

    def _post(self, h, msg, w, lp):
        user32.PostMessageW(h, msg, w, lp)

    def click(self, name, x, y):
        h, ox, oy = self.locate(name)
        if self.needs_foreground and name in self.invoke and not self.foreground():
            r = ctypes.c_size_t()                 # BM_CLICK: ButtonBase.WndProc -> PerformClick (no capture)
            user32.SendMessageTimeoutW(h, 0x00F5, 0, 0, 2, 100, ctypes.byref(r))
            return
        lp = ((y + oy) << 16) | ((x + ox) & 0xFFFF)
        self._post(h, WM_LBUTTONDOWN, 1, lp)
        time.sleep(0.06)
        self._post(h, WM_LBUTTONUP, 0, lp)

    def focus_hwnd(self):
        g = GUITHREADINFO()
        g.cbSize = ctypes.sizeof(g)
        tid = user32.GetWindowThreadProcessId(self.form, None)
        return g.hwndFocus if user32.GetGUIThreadInfo(tid, ctypes.byref(g)) else None

    def key(self, name, letter):
        h = self.focus_hwnd() or self.locate(name)[0]
        vk = ord(letter.upper())
        scan = user32.MapVirtualKeyW(vk, 0)
        self._post(h, WM_KEYDOWN, vk, 1 | (scan << 16))
        time.sleep(0.2)                    # the WM_CHAR made by TranslateMessage comes before the key-up
        self._post(self.focus_hwnd() or h, WM_KEYUP, vk, 1 | (scan << 16) | (1 << 30) | (1 << 31))

    def msgbox(self, name, seconds):
        from evcore import close_dialogs
        self.click(name, 5, 5)
        time.sleep(seconds)
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(self.form, ctypes.byref(pid))
        end = time.time() + 10
        while time.time() < end and not close_dialogs(pid.value):
            time.sleep(0.1)

    def text(self, name, value):
        h = self.locate(name)[0]
        b = ctypes.create_unicode_buffer(value)
        r = ctypes.c_size_t()
        user32.SendMessageTimeoutW(h, WM_SETTEXT, 0, ctypes.cast(b, ctypes.c_void_p).value, 2, 3000, ctypes.byref(r))

    def read(self, name):
        h = self.locate(name)[0]
        n = user32.SendMessageW(h, WM_GETTEXTLENGTH, 0, 0)
        b = ctypes.create_unicode_buffer(n + 2)
        user32.SendMessageW(h, WM_GETTEXT, n + 1, ctypes.cast(b, ctypes.c_void_p).value)
        return b.value

    def focus(self):
        f = self.focus_hwnd()
        for n in self.names:
            try:
                if f and self.locate(n)[0] == f:
                    return n
            except Exception:  # noqa: BLE001
                pass
        return str(f or "")

    def close(self):
        user32.PostMessageW(self.form, WM_CLOSE, 0, 0)

    def alive(self):
        return self.proc.poll() is None

    def wait_exit(self):
        try:
            self.proc.wait(6)
        except subprocess.TimeoutExpired:
            pass


NAMES = ["txtA", "txtB", "cmdA", "lblA", "chkA", "lstA", "cmdCode", "cmdTmr"]


def _pid_windows(pid: int) -> list[int]:
    import winauto as w
    return w.top_windows(pid)


class _PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


def child_pids(pid: int) -> list[int]:
    """Processes started by *pid* (the Node exe starts its radforms host)."""
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    snap = k.CreateToolhelp32Snapshot(2, 0)
    e = _PE32()
    e.dwSize = ctypes.sizeof(_PE32)
    out = []
    if k.Process32FirstW(snap, ctypes.byref(e)):
        while True:
            if e.th32ParentProcessID == pid:
                out.append(e.th32ProcessID)
            if not k.Process32NextW(snap, ctypes.byref(e)):
                break
    k.CloseHandle(snap)
    return out


def start_exe(exe: Path, logfile: Path, pipe=False):
    env = dict(os.environ, RADEVT_LOG=str(logfile))
    if pipe:
        return subprocess.Popen([str(exe)], cwd=str(exe.parent), env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return subprocess.Popen([str(exe)], cwd=str(exe.parent), env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def kill_tree(proc):
    if proc.poll() is None:
        for c in child_pids(proc.pid):
            subprocess.run(["taskkill", "/F", "/PID", str(c)], capture_output=True)
        proc.kill()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            pass


def radforms_driver(proc, lang):
    import winauto as w
    pid = proc.pid
    if lang == "JS":                        # the Node exe starts its radforms host process
        pid = w.wait(lambda: next(iter(child_pids(proc.pid)), 0), 20) or proc.pid
    form = w.form_window(pid, "Form1", 30)
    if not form:
        return None
    kids = w.wait(lambda: (lambda d: d if "lstA" in d else None)(w.children(form)), 10)
    if not kids:
        return None
    return Win32Driver(proc, form, lambda n: (kids[n], 0, 0), NAMES)


def winforms_driver(proc):
    from _win import UIA, wait
    form = wait(lambda: next(iter(_pid_windows(proc.pid)), None), 60)
    if not form:
        return None
    time.sleep(0.5)
    uia = UIA()
    root = uia.root(form)
    hw = {}
    for n in NAMES:
        h = wait(lambda n=n: uia.hwnd(root, n), 10)
        if not h:
            return None
        hw[n] = h
    return Win32Driver(proc, form, lambda n: (hw[n], 0, 0), NAMES, needs_foreground=True,
                       invoke={"cmdA", "cmdCode", "cmdTmr", "chkA"})


class SwingDriver(Win32Driver):
    """Swing draws its controls itself (no child windows) and AWT sends a mouse message to the window under the REAL
    cursor, so posted mouse messages never reach a component. The test build of the exe contains RadTestHook
    (RADIDE_NATIVE_TEST_HOOK=1 at build time, never in a release): "mouse <obj> x y" posts the AWT mouse events of a
    left click (pressed, released, clicked) to the component - the whole Swing listener chain runs. Focus and
    keyboard need the window to be the active one (Java's focus requests wait for the activation)."""

    def __init__(self, proc, form):
        import queue
        import threading
        self.replies: queue.Queue = queue.Queue()

        def reader():
            for raw in iter(proc.stdout.readline, b""):
                ln = raw.decode("utf-8", "replace").rstrip("\r\n")
                if ln.startswith("R "):
                    self.replies.put(ln[2:])
        threading.Thread(target=reader, daemon=True).start()
        super().__init__(proc, form, lambda n: (form, 0, 0), NAMES, needs_foreground=True,
                         fg_steps={"focus_first", "focus_a_to_b", "focus_b_to_a", "keys"})

    def hook(self, cmd: str) -> str:
        import queue
        try:
            self.proc.stdin.write((cmd + "\n").encode("utf-8"))
            self.proc.stdin.flush()
            return self.replies.get(timeout=10)
        except (OSError, queue.Empty):
            return ""

    def cannot(self, step) -> str:
        if step["name"] in self.fg_steps:
            return ("Swing focus / keyboard need real input in the active window (AWT retargets posted input to the "
                    "real cursor and the Java focus owner)")
        return ""

    def click(self, name, x, y):
        self.hook(f"mouse Form1.{name} {x} {y}")

    def msgbox(self, name, seconds):
        self.click(name, 5, 5)


def swing_driver(proc, project: Path):
    import winauto as w

    def frames():               # the jpackage launcher runs the Java VM in a child process
        for pid in [proc.pid, *child_pids(proc.pid)]:
            for h in _pid_windows(pid):
                if w.class_name(h).startswith("SunAwt"):
                    return h
        return None
    form = w.wait(frames, 90)
    if not form:
        return None
    time.sleep(1.0)
    d = SwingDriver(proc, form)
    if d.hook("windows") == "":
        return None
    return d


def fb_ids(gen: Path) -> dict:
    import re
    out = {}
    src = next(gen.glob("*.bas")).read_text(encoding="utf-8")
    for m in re.finditer(r"^Const (CTL|MNU|FRM)_(\w+?) = (\d+)$", src, re.M):
        out[m.group(2).lower()] = int(m.group(3))
    return out


def vb6fb_driver(proc, gen: Path):
    import winauto as w
    form = w.wait(lambda: next(iter(_pid_windows(proc.pid)), None), 20)
    if not form:
        return None
    ids = fb_ids(gen)
    found = {}

    def locate(n):
        if n not in found:
            cid = 1000 + ids[f"form1_{n}".lower()]
            for c in _children_all(form):
                if user32.GetDlgCtrlID(c) == cid and w.class_name(c) != "RADVBBox":
                    found[n] = c
                    break
        return found[n], 0, 0
    return Win32Driver(proc, form, locate, NAMES)


def _children_all(h) -> list[int]:
    import winauto as w
    out = []

    def cb(c, _l):
        out.append(c)
        return True
    w.user32.EnumChildWindows(h, w.WNDENUMPROC(cb), 0)
    return out


# ------------------------------------------------------------------ builds
def copy_project(lang: str, tag: str) -> Path:
    work = SCRATCH / f"{lang}_{tag}" / lang
    shutil.rmtree(work.parent, ignore_errors=True)
    shutil.copytree(HERE / "projects" / lang, work)
    return work


def build_native(lang: str):
    """-> (result, work folder, reason)"""
    from radide.deploy import build
    from radide.deploy.config import PublishConfig
    work = copy_project(lang, "native")
    out = work.parent / "publish"
    cfg = PublishConfig(app_name=f"Events{lang}", version="1.0.0", publisher="RAD IDE tests", output_dir=str(out))
    cfg.make_installer = False
    if lang == "Java":                      # a test build: RadTestHook drives the Swing components
        os.environ["RADIDE_NATIVE_TEST_HOOK"] = "1"
    if lang == "CSharp" and os.environ.get("RADEVT_DOTNET_TARGET"):
        cfg.dotnet_target = os.environ["RADEVT_DOTNET_TARGET"]
    log: list[str] = []
    t = time.time()
    try:
        res = build.build(work, cfg, log=log.append)
    except Exception as e:  # noqa: BLE001
        return None, work, f"build failed: {e} | " + " | ".join(log[-6:])
    finally:
        os.environ.pop("RADIDE_NATIVE_TEST_HOOK", None)
    print(f"   {lang} native: {res.kind} in {time.time() - t:.0f} s", flush=True)
    if not str(res.kind).startswith("native"):
        return None, work, f"built as '{res.kind}', not native: " + " | ".join(log[-6:])
    return res, work, ""


# ------------------------------------------------------------------ runs
def run_tk(lang: str, path: str, family: str):
    work = copy_project(lang, path)
    logf = work.parent / "events.log"
    engine = {"vbrun": "vbrun", "tk": "python"}.get(path, "bridge")
    try:
        r = subprocess.run([PY, "-u", str(HERE / "tk_driver.py"), engine, str(work), str(logf), family],
                           capture_output=True, text=True, timeout=600, errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if "BUILD FAILED" in r.stdout:
        return None, "skip: bridge build failed: " + r.stdout[-600:].replace("\n", " | ")
    if not logf.is_file():
        return None, "no log: " + (r.stdout + r.stderr)[-800:]
    (work.parent / "tk_driver.out.txt").write_text((r.stdout or "") + "\n----- stderr\n" + (r.stderr or ""),
                                                  encoding="utf-8")
    tail = (r.stderr or "").strip().splitlines()[-3:]
    return logf.read_text(encoding="utf-8", errors="replace").splitlines(), " | ".join(tail)


def run_win32(lang: str, kind: str, family: str, res, work: Path):
    exe = res.dist / res.exe
    logf = work.parent / "events.log"
    pipe = kind == "vb6fb"
    if kind == "swing":
        log = FileLog(logf)
        proc = subprocess.Popen([str(exe)], cwd=str(exe.parent), env=dict(os.environ, RADEVT_LOG=str(logf)),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    elif pipe:
        proc = start_exe(exe, logf, pipe=True)
        log = PipeLog(proc.stdout)
    else:
        log = FileLog(logf)
        proc = start_exe(exe, logf)
    try:
        if kind == "radforms":
            d = radforms_driver(proc, lang)
        elif kind == "winforms":
            d = winforms_driver(proc)
        elif kind == "swing":
            d = swing_driver(proc, work)
        else:
            d = vb6fb_driver(proc, work.parent / "publish" / "build" / "native_vb6")
        if d is None:
            return None, "the form window / its controls were not found"
        run_steps(d, log, family, startup_wait=1.5)
        return log.lines(), ""
    finally:
        kill_tree(proc)


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    natives: dict[str, tuple] = {}
    for lang, path, family, kind in ENGINES:
        eng = f"{lang}:{path}"
        if ONLY and eng.lower() not in ONLY and lang.lower() not in ONLY:
            continue
        print(f"===== {eng} ({family})", flush=True)
        runs = []
        for attempt in range(3):
            if kind == "tk":
                lines, info = run_tk(lang, path, family)
            else:
                if lang not in natives:
                    natives[lang] = build_native(lang)
                res, work, reason = natives[lang]
                if res is None:
                    lines, info = None, "skip: " + reason
                else:
                    lines, info = run_win32(lang, kind, family, res, work)
            if lines is None:
                break
            runs.append(compare(lines, family))
            (SCRATCH / f"{lang}_{path}_run{attempt + 1}.log").write_text("\n".join(lines), encoding="utf-8")
            if all(ok is not False for _s, _f, ok, _d in runs[-1]):
                break
            bad = [s for s, _f, ok, _d in runs[-1] if ok is False]
            print(f"   (attempt {attempt + 1} failed: {', '.join(bad)}{'; repeating' if attempt < 2 else ''})", flush=True)
        if not runs:
            status = "SKIP" if info.startswith("skip") else "FAIL"
            mine = [st for st in STEPS if expected(st, family) is not None]
            for step in mine:
                record(eng, step["name"], step["family"], status, info if step is mine[0] else "")
            continue
        for i, (step, fam, _ok, detail) in enumerate(runs[0]):
            if all(r[i][2] is None for r in runs):
                record(eng, step, fam, "SKIP", detail)
                continue
            good = any(r[i][2] for r in runs)
            record(eng, step, fam, "PASS" if good else "FAIL", "" if good else detail)
    # ---------------------------------------------------------------- matrix
    print("\n================ event semantics matrix (language x path x event family)", flush=True)
    engines = list(dict.fromkeys(r["engine"] for r in results))
    print(f"{'':16} " + " ".join(f"{f[:9]:>9}" for f in EVENT_FAMILIES))
    matrix = {}
    for e in engines:
        row = {}
        for f in EVENT_FAMILIES:
            st = [r["status"] for r in results if r["engine"] == e and r["family"] == f]
            row[f] = "-" if not st else "FAIL" if "FAIL" in st else "SKIP" if "SKIP" in st else "PASS"
        matrix[e] = row
        print(f"{e:16} " + " ".join(f"{row[f]:>9}" for f in EVENT_FAMILIES))
    n = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "SKIP")}
    print(f"\nsteps: {n['PASS']} passed, {n['FAIL']} failed, {n['SKIP']} skipped "
          f"({len(engines)} engine paths, {time.time() - t0:.0f} s)", flush=True)
    print(f"{n['PASS']}/{n['PASS'] + n['FAIL']} passed", flush=True)
    (SCRATCH / "events_report.json").write_text(json.dumps({"results": results, "matrix": matrix}, indent=1),
                                                encoding="utf-8")
    print("report:", SCRATCH / "events_report.json")
    return n["FAIL"]


if __name__ == "__main__":
    sys.exit(main())
