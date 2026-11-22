"""Client of RAD IDE's automation channel (radide/automation) + the E2E harness helpers.

    from radauto import IDE, Desktop, Report
    with Desktop("RADIDE_E2E") as desk:                 # a hidden Win32 desktop: no window reaches the user's
        ide = IDE.launch(exe, desktop=desk.name, portable_dir=...)
        ide.call("new_project", language="vb-basic", name="Hello", location=str(tmp))
        ide.trigger("Debug/Start Debugging")
        ...
        ide.quit()

No Qt in the client: the channel is a named pipe (\\\\.\\pipe\\<name>) carrying JSON lines.
"""
from __future__ import annotations

import ctypes
import json
import os
import secrets
import subprocess
import time
import traceback
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent


class AutomationError(Exception):
    pass


# ============================================================================================ desktop
class Desktop:
    """A separate Win32 desktop in the user's window station. Processes started on it (and everything they
    start) draw there: invisible to the user, but real windows (PrintWindow / messages work)."""

    def __init__(self, name: str = "RADIDE_E2E"):
        self.name = name
        self.handle = None

    def __enter__(self):
        u = ctypes.WinDLL("user32", use_last_error=True)
        u.CreateDesktopW.restype = wintypes.HANDLE
        u.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD,
                                     wintypes.DWORD, ctypes.c_void_p]
        GENERIC_ALL = 0x10000000
        self.handle = u.CreateDesktopW(self.name, None, None, 0, GENERIC_ALL, None)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "CreateDesktopW failed")
        return self

    def __exit__(self, *exc):
        if self.handle:
            ctypes.WinDLL("user32").CloseDesktop(wintypes.HANDLE(self.handle))
            self.handle = None

    @property
    def spec(self) -> str:
        return f"WinSta0\\{self.name}"


class _STARTUPINFO(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class _PROCINFO(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD)]


class Proc:
    """A process started with CreateProcessW (optionally on another desktop)."""

    def __init__(self, pid: int, handle):
        self.pid, self.handle = pid, handle

    def poll(self):
        k = ctypes.WinDLL("kernel32")
        code = wintypes.DWORD()
        k.GetExitCodeProcess(wintypes.HANDLE(self.handle), ctypes.byref(code))
        return None if code.value == 259 else code.value

    def wait(self, timeout: float | None = None):
        end = time.monotonic() + (timeout if timeout is not None else 1e9)
        while time.monotonic() < end:
            rc = self.poll()
            if rc is not None:
                return rc
            time.sleep(0.2)
        raise TimeoutError(f"process {self.pid} still running")

    def kill(self):
        ctypes.WinDLL("kernel32").TerminateProcess(wintypes.HANDLE(self.handle), 1)


def start_process(argv: list[str], desktop: str | None = None, env: dict | None = None, cwd: str | None = None,
                  stdout_path: str | None = None) -> Proc:
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    si = _STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    if desktop:
        si.lpDesktop = desktop if "\\" in desktop else f"WinSta0\\{desktop}"
    pi = _PROCINFO()
    cmd = subprocess.list2cmdline([str(a) for a in argv])
    envblock = None
    if env is not None:
        s = "".join(f"{k_}={v}\0" for k_, v in env.items()) + "\0"
        envblock = ctypes.create_unicode_buffer(s, len(s))
    CREATE_UNICODE_ENVIRONMENT, CREATE_NO_WINDOW = 0x400, 0x08000000
    inherit = False
    if stdout_path:
        class SA(ctypes.Structure):
            _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                        ("bInheritHandle", wintypes.BOOL)]
        sa = SA(ctypes.sizeof(SA), None, True)
        k.CreateFileW.restype = wintypes.HANDLE
        k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                  wintypes.DWORD, wintypes.HANDLE]
        h = k.CreateFileW(stdout_path, 0x40000000, 3, ctypes.byref(sa), 2, 0x80, None)
        if not h or h == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), f"cannot create {stdout_path}")
        si.dwFlags |= 0x100
        si.hStdOutput = si.hStdError = h
        inherit = True
    ok = k.CreateProcessW(None, ctypes.create_unicode_buffer(cmd), None, None, inherit,
                          CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW, envblock, cwd, ctypes.byref(si),
                          ctypes.byref(pi))
    if not ok:
        raise OSError(ctypes.get_last_error(), f"CreateProcessW failed: {cmd}")
    k.CloseHandle(pi.hThread)
    return Proc(pi.dwProcessId, pi.hProcess)


# ============================================================================================ client
class IDE:
    def __init__(self, pipe: str, token: str, proc: Proc | None = None, log_path: Path | None = None):
        self.pipe, self.token, self.proc, self.log_path = pipe, token, proc, log_path
        self._f = None
        self._id = 0

    # ------------------------------------------------------------------ launching
    @classmethod
    def launch(cls, exe: str | list[str], *, desktop: str | None = None, env_extra: dict | None = None,
               args: list[str] | None = None, offscreen: bool = True, timeout: float = 180,
               log_path: Path | None = None, scratch: Path | None = None, isolate: bool = True) -> "IDE":
        """Start RADIDE.exe (or [python, -m, radide]) with the automation channel and wait until it answers."""
        token = secrets.token_hex(16)
        name = f"radide-e2e-{secrets.token_hex(4)}"
        scratch = Path(scratch or os.environ.get("RADIDE_E2E_SCRATCH") or (HERE / "_out"))
        scratch.mkdir(parents=True, exist_ok=True)
        ready = scratch / f"{name}.ready.json"
        env = dict(os.environ)
        for k in ("PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QML2_IMPORT_PATH", "VIRTUAL_ENV"):
            env.pop(k, None)
        env.update({"RADIDE_AUTOMATION": token, "RADIDE_AUTOMATION_NAME": name,
                    "RADIDE_AUTOMATION_READY": str(ready), "RADIDE_NO_BROWSER": "1",
                    "RADIDE_INSTANCE_NAME": name + "-si",
                    "QT_QPA_FONTDIR": r"C:\Windows\Fonts",
                    "QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu --disable-gpu-compositing"})
        if isolate:                      # never the user's extensions / VS Code extensions / components
            env.setdefault("RADIDE_EXTENSIONS_DIR", str(scratch / "isolated" / "extensions"))
            env.setdefault("RADIDE_VSX_ROOT", str(scratch / "isolated" / "vsx"))
            env.setdefault("RADIDE_COMPONENTS_DIR", str(scratch / "isolated" / "components"))
        if offscreen:
            env["QT_QPA_PLATFORM"] = "offscreen"
        else:
            env.pop("QT_QPA_PLATFORM", None)
        env.update(env_extra or {})
        argv = ([exe] if isinstance(exe, str) else list(exe)) + list(args or [])
        log_path = Path(log_path or scratch / f"{name}.log")
        proc = start_process(argv, desktop=desktop, env=env, cwd=str(Path(argv[0]).parent) if isinstance(exe, str)
                             else str(REPO), stdout_path=str(log_path))
        ide = cls(name, token, proc, log_path)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if proc.poll() is not None:
                raise AutomationError(f"the IDE exited with {proc.poll()} before the channel opened; log:\n"
                                      + ide.log_tail())
            if ready.is_file():
                try:
                    ide.connect()
                    ide.call("hello")
                    (scratch / f"{name}.session.json").write_text(json.dumps(   # radcli.py can attach to it
                        {"pipe": name, "token": token, "pid": proc.pid, "log": str(log_path)}), encoding="utf-8")
                    return ide
                except OSError:
                    pass
            time.sleep(0.5)
        proc.kill()
        raise AutomationError("the automation channel did not open in time; log:\n" + ide.log_tail())

    def log_tail(self, n: int = 4000) -> str:
        if not self.log_path:
            return ""
        try:
            return Path(self.log_path).read_text(encoding="utf-8", errors="replace")[-n:]
        except OSError:
            return ""

    def connect(self):
        self._f = open(rf"\\.\pipe\{self.pipe}", "r+b", buffering=0)

    def close(self):
        if self._f:
            try:
                self._f.close()
            except OSError:
                pass
            self._f = None

    # ------------------------------------------------------------------ requests
    timeout = float(os.environ.get("RADIDE_E2E_REQUEST_TIMEOUT", "600"))

    def request(self, cmd: str, args: dict | None = None, async_job: bool = False) -> dict:
        """One request; AutomationError when the IDE does not answer within self.timeout seconds (a hung GUI
        thread must fail the step, not hang the whole run)."""
        import threading
        if self._f is None:
            self.connect()
        self._id += 1
        msg = {"id": self._id, "cmd": cmd, "args": args or {}, "token": self.token}
        if async_job:
            msg["async"] = True
        f = self._f
        box: dict = {}

        def io():
            try:
                f.write((json.dumps(msg) + "\n").encode("utf-8"))
                buf = b""
                while not buf.endswith(b"\n"):
                    chunk = f.read(65536)
                    if not chunk:
                        raise AutomationError("the IDE closed the channel")
                    buf += chunk
                box["reply"] = json.loads(buf.decode("utf-8"))
            except Exception as e:  # noqa: BLE001
                box["error"] = e
        t = threading.Thread(target=io, daemon=True)
        t.start()
        t.join(self.timeout)
        if t.is_alive():
            self._f = None               # abandon this connection; the next request opens a new one
            raise AutomationError(f"{cmd}: no answer from the IDE in {self.timeout:.0f}s (GUI thread busy / hung)")
        if "error" in box:
            self._f = None
            raise box["error"]
        return box["reply"]

    def call(self, cmd: str, **args):
        r = self.request(cmd, args)
        if not r.get("ok"):
            raise AutomationError(f"{cmd}: {r.get('error')}\n{r.get('trace', '')}")
        return r.get("result")

    def try_call(self, cmd: str, **args):
        try:
            return self.call(cmd, **args)
        except (AutomationError, OSError, ValueError):
            self.close()                 # a dead pipe: reconnect on the next request
            return None

    def job(self, cmd: str, wait_s: float = 120, **args):
        """Run a (possibly long / modal) command as a job and wait for it."""
        r = self.request(cmd, args, async_job=True)
        if not r.get("ok"):
            raise AutomationError(r.get("error"))
        jid = r["result"]["job"]
        end = time.monotonic() + wait_s
        while time.monotonic() < end:
            j = self.call("job", job=jid, wait_ms=500)
            if j.get("done"):
                if not j.get("ok"):
                    raise AutomationError(f"{cmd}: {j.get('error')}\n{j.get('trace', '')}")
                return j.get("result")
        raise AutomationError(f"{cmd} did not finish in {wait_s}s")

    def py(self, code: str):
        """exec in the IDE; returns the 'result' variable."""
        return self.call("exec", code=code)["result"]

    def trigger(self, path: str, **kw):
        return self.call("trigger", path=path, **kw)

    def output(self) -> str:
        return self.call("output")

    def wait_for(self, fn, timeout: float = 60, step: float = 0.5, desc: str = ""):
        end = time.monotonic() + timeout
        last = None
        while time.monotonic() < end:
            try:
                last = fn()
                if last:
                    return last
            except (AutomationError, OSError) as e:
                last = e
            time.sleep(step)
        raise AutomationError(f"timeout waiting for {desc or fn}: last={last!r}"[:2000])

    def wait_output(self, needle: str | list, timeout: float = 120) -> str:
        needles = [needle] if isinstance(needle, str) else needle
        return self.wait_for(lambda: (lambda t: t if any(n in t for n in needles) else None)(self.output()),
                             timeout, desc=f"output {needles}")

    def wait_dialog(self, title: str = "", text: str = "", timeout: float = 30):
        def f():
            for d in self.call("dialogs"):
                if (not title or title.lower() in d["title"].lower()) and (
                        not text or text.lower() in (d.get("text", "") + " ".join(d.get("labels", []))).lower()):
                    return d
            return None
        return self.wait_for(f, timeout, desc=f"dialog {title!r} {text!r}")

    def program_windows(self, title: str = "", pid: int | None = None, all_: bool = False):
        return self.call("win32_windows", title=title, pid=pid, all_=all_)

    def wait_program_window(self, title: str = "", timeout: float = 90, pid: int | None = None):
        return self.wait_for(lambda: (self.program_windows(title, pid) or [None])[0], timeout,
                             desc=f"program window {title!r}")

    def quit(self, timeout: float = 30):
        try:
            self.call("quit", force=True)
        except Exception:  # noqa: BLE001
            pass
        self.close()
        if self.proc is not None:
            try:
                self.proc.wait(timeout)
            except TimeoutError:
                self.proc.kill()


# ============================================================================================ report
class Report:
    """PASS / FAIL / SKIP per step, screenshots, logs; JSON + Markdown summary."""

    def __init__(self, journey: str, out: Path):
        self.journey = journey
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.steps: list[dict] = []
        self.ide: IDE | None = None

    def shot(self, name: str, sel=None, hwnd: int | None = None) -> str | None:
        if self.ide is None:
            return None
        p = self.out / f"{len(self.steps):02d}_{''.join(c if c.isalnum() else '_' for c in name)[:50]}.png"
        try:
            if hwnd:
                self.ide.call("win32_grab", hwnd=hwnd, path=str(p))
            else:
                self.ide.call("grab", path=str(p), sel=sel)
            return str(p)
        except Exception:  # noqa: BLE001
            return None

    def step(self, name: str, fn, *, shot: bool | str = False, critical: bool = False):
        t = time.monotonic()
        rec = {"journey": self.journey, "step": name}
        try:
            res = fn()
            if isinstance(res, Skip):
                rec.update(status="SKIP", detail=res.reason)
            else:
                rec.update(status="PASS", detail=_short(res))
        except Skip as s:
            rec.update(status="SKIP", detail=s.reason)
        except Exception as e:  # noqa: BLE001
            rec.update(status="FAIL", detail=f"{type(e).__name__}: {e}"[:3000], trace=traceback.format_exc()[-3000:])
            if self.ide is not None:
                try:
                    rec["output_tail"] = self.ide.output()[-3000:]
                    rec["dialogs"] = self.ide.call("dialogs")
                except Exception:  # noqa: BLE001
                    rec["ide_log"] = self.ide.log_tail(3000)
        rec["seconds"] = round(time.monotonic() - t, 1)
        if shot or rec["status"] == "FAIL":
            rec["screenshot"] = self.shot(name, sel=shot if isinstance(shot, (dict, str)) and shot is not True else None)
        self.steps.append(rec)
        print(f"{rec['status']} [{self.journey}] {name} ({rec['seconds']}s)" +
              (f" - {rec['detail']}" if rec["status"] != "PASS" else ""), flush=True)
        if critical and rec["status"] == "FAIL":
            raise Abort(name)
        return rec["status"] == "PASS"

    def skip_rest(self, names: list[str], reason: str):
        for n in names:
            self.steps.append({"journey": self.journey, "step": n, "status": "SKIP", "detail": reason})
            print(f"SKIP [{self.journey}] {n} - {reason}", flush=True)

    def counts(self) -> dict:
        c = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for s in self.steps:
            c[s["status"]] += 1
        return c

    def save(self) -> dict:
        c = self.counts()
        (self.out / "report.json").write_text(json.dumps({"journey": self.journey, "counts": c,
                                                          "steps": self.steps}, indent=1), encoding="utf-8")
        lines = [f"# {self.journey}", "", f"PASS {c['PASS']}  FAIL {c['FAIL']}  SKIP {c['SKIP']}", "",
                 "| # | step | status | detail |", "|---|---|---|---|"]
        for i, s in enumerate(self.steps):
            d = str(s.get("detail", "")).replace("|", "/").replace("\n", " ")[:160]
            lines.append(f"| {i} | {s['step']} | {s['status']} | {d} |")
        (self.out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return c


class Skip(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class Abort(Exception):
    pass


def _short(v):
    s = json.dumps(v, default=str) if not isinstance(v, str) else v
    return s[:300]


def check(cond, msg: str = "check failed"):
    if not cond:
        raise AssertionError(msg)
    return cond
