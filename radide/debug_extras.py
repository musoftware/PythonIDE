"""Debugger extras shared by every engine (no Qt widgets here).

* Breakpoint settings (condition, hit count, logpoint) travel through the old "condition"
  string of a breakpoint so that every existing path (RADDBG_BP, ``set_breakpoint(f, line, on, cond)``,
  ``win.bp_conditions``) carries them unchanged:

      plain text            -> just a condition ("x > 3")
      "@@bp " + JSON        -> {"cond": "...", "hit": ">=5" | "==5" | "%5" | "", "log": "x is {x}"}

  ``;`` is written as \\u003b inside the JSON so RADDBG_BP (";"-separated) stays parseable.
* Engine look-up for Delve (Go) and the JDK (Java).
* The process list for Debug > Attach to Process.
* ``TcpDap``: a DapSession whose adapter speaks DAP over TCP (dlv dap --listen).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE"
EXE = ".exe" if os.name == "nt" else ""
BP_PREFIX = "@@bp "


# ====================================================================== breakpoint settings
def encode_bp(cond: str = "", hit: str = "", log: str = "") -> str:
    """The breakpoint 'condition' string that carries *cond*, *hit* and *log*."""
    cond, hit, log = (cond or "").strip(), (hit or "").strip(), (log or "").strip()
    if not hit and not log:
        return cond
    data = {k: v for k, v in (("cond", cond), ("hit", hit), ("log", log)) if v}
    return BP_PREFIX + json.dumps(data, ensure_ascii=True).replace(";", "\\u003b")


def parse_bp(text: str) -> dict:
    """{'cond': str, 'hit': str, 'log': str} of a breakpoint condition string."""
    text = text or ""
    if text.startswith(BP_PREFIX):
        try:
            d = json.loads(text[len(BP_PREFIX):])
            return {"cond": str(d.get("cond", "")), "hit": str(d.get("hit", "")), "log": str(d.get("log", ""))}
        except ValueError:
            pass
    return {"cond": text.strip(), "hit": "", "log": ""}


def hit_ok(hit: str, count: int) -> bool:
    """Does the *count*-th hit satisfy the hit condition ('5' / '==5' / '>=5' / '%5')?"""
    m = re.fullmatch(r"\s*(==|>=|>|%|=)?\s*(\d+)\s*", hit or "")
    if not m:
        return True
    op, n = m.group(1) or "==", int(m.group(2))
    if op in ("==", "="):
        return count == n
    if op == ">=":
        return count >= n
    if op == ">":
        return count > n
    return n > 0 and count % n == 0


def describe_bp(text: str) -> str:
    """Human description ('when x > 3, hit count >= 5, log "..."')."""
    d = parse_bp(text)
    out = []
    if d["cond"]:
        out.append(f"when {d['cond']}")
    if d["hit"]:
        h = d["hit"]
        out.append("every " + h[1:] + " hits" if h.startswith("%") else f"hit count {h}")
    if d["log"]:
        out.append(f'log "{d["log"]}"')
    return ", ".join(out) or "always"


def dap_breakpoint(line: int, text: str, adapter: str = "") -> dict:
    """A DAP SourceBreakpoint for *line* from a condition string."""
    d = parse_bp(text)
    bp = {"line": line}
    if d["cond"]:
        bp["condition"] = d["cond"]
    if d["hit"]:
        m = re.fullmatch(r"\s*(==|>=|>|%|=)?\s*(\d+)\s*", d["hit"])
        if m:
            op, n = m.group(1) or "==", m.group(2)
            if adapter in ("gdb",):
                bp["hitCondition"] = n                      # gdb: ignore the first n-1 hits
            elif adapter in ("dlv",):
                bp["hitCondition"] = {"=": "==", "==": "==", ">=": ">=", ">": ">", "%": "%"}[op] + " " + n
            else:                                           # debugpy / netcoredbg / js-debug
                bp["hitCondition"] = {"=": "==", "==": "==", ">=": ">=", ">": ">", "%": "%"}[op] + n
    if d["log"]:
        bp["logMessage"] = d["log"]
    return bp


def format_log(message: str, evaluate) -> str:
    """Logpoint text: every {expression} replaced by evaluate(expression) (errors shown inline)."""
    def rep(m):
        try:
            return str(evaluate(m.group(1)))
        except Exception as e:  # noqa: BLE001
            return f"<{type(e).__name__}: {e}>"
    return re.sub(r"\{([^{}]+)\}", rep, message)


# ====================================================================== tools
def find_dlv() -> str:
    """Delve: PATH, %LOCALAPPDATA%\\RADIDE\\tools\\dlv, then ~/go/bin."""
    p = shutil.which("dlv")
    if p:
        return p
    for d in (LOCAL / "tools" / "dlv", Path.home() / "go" / "bin"):
        if (d / ("dlv" + EXE)).exists():
            return str(d / ("dlv" + EXE))
    return ""


def find_go() -> str:
    p = shutil.which("go")
    if p:
        return p
    g = LOCAL / "toolchains" / "go" / "bin" / ("go" + EXE)
    return str(g) if g.exists() else ""


def install_dlv_command() -> list[str] | None:
    """argv that builds Delve into %LOCALAPPDATA%\\RADIDE\\tools\\dlv (needs Go), or None."""
    go = find_go()
    return [go, "install", "github.com/go-delve/delve/cmd/dlv@latest"] if go else None


def dlv_install_env() -> dict:
    env = dict(os.environ)
    env["GOBIN"] = str(LOCAL / "tools" / "dlv")
    env.setdefault("GOTOOLCHAIN", "local")
    return env


# ====================================================================== processes
def list_processes() -> list[dict]:
    """[{'pid', 'name', 'title', 'kind'}] of the running processes (kind: python / dotnet / native)."""
    out: list[dict] = []
    if os.name == "nt":
        out = _win_processes()            # Toolhelp32 + window titles (tasklist /v can hang on a hung window)
    else:
        try:
            r = subprocess.run(["ps", "-eo", "pid=,comm=,args="], capture_output=True, text=True, timeout=20)
            for line in r.stdout.splitlines():
                parts = line.split(None, 2)
                if len(parts) >= 2 and parts[0].isdigit():
                    out.append({"pid": int(parts[0]), "name": parts[1], "title": parts[2] if len(parts) > 2 else ""})
        except (OSError, subprocess.SubprocessError):
            pass
    for p in out:
        p["kind"] = process_kind(p["name"])
    return out


def _win_processes() -> list[dict]:
    import ctypes
    from ctypes import wintypes

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    out: list[dict] = []
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        snap = k32.CreateToolhelp32Snapshot(0x2, 0)
        if not snap or snap == wintypes.HANDLE(-1).value:
            return out
        try:
            e = PE32()
            e.dwSize = ctypes.sizeof(PE32)
            ok = k32.Process32FirstW(snap, ctypes.byref(e))
            while ok:
                out.append({"pid": int(e.th32ProcessID), "ppid": int(e.th32ParentProcessID),
                            "name": e.szExeFile, "title": ""})
                ok = k32.Process32NextW(snap, ctypes.byref(e))
        finally:
            k32.CloseHandle(snap)
        titles: dict[int, str] = {}
        u32 = ctypes.WinDLL("user32")
        proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def each(hwnd, _l):
            if u32.IsWindowVisible(hwnd):
                n = u32.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    u32.GetWindowTextW(hwnd, buf, n + 1)
                    pid = wintypes.DWORD()
                    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    titles.setdefault(pid.value, buf.value)
            return True
        u32.EnumWindows(proto(each), 0)
        for p in out:
            p["title"] = titles.get(p["pid"], "")
    except (OSError, AttributeError):
        pass
    return out


def python_child(pid: int) -> int:
    """A venv / py.exe launcher runs the real python.exe as its child: that child's PID (else *pid*)."""
    for p in list_processes():
        if p.get("ppid") == int(pid) and process_kind(p["name"]) == "python":
            return p["pid"]
    return int(pid)


def process_kind(name: str) -> str:
    n = name.lower()
    if re.match(r"pythonw?(\d+(\.\d+)?)?(\.exe)?$", n) or n.startswith("py.exe"):
        return "python"
    if n in ("dotnet.exe", "dotnet"):
        return "dotnet"
    return "native"


# ====================================================================== DAP over TCP (Delve)
def make_tcp_dap():
    """TcpDap class (built lazily so this module imports without Qt)."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtNetwork import QTcpSocket

    from .bridgedebug import AttachDap, free_port
    from .dap import DapSession

    class TcpDap(AttachDap):
        """AttachDap for adapters that listen on TCP: ``dlv dap --listen=127.0.0.1:<port>``."""

        def __init__(self, argv, adapter_id, attach_args, cwd, env, breakpoints, parent=None):
            super().__init__(argv, adapter_id, attach_args, cwd, env, breakpoints, parent)
            self.port = free_port()
            if self.argv:
                self.argv = self.argv + [f"--listen=127.0.0.1:{self.port}"]
            self.sock: QTcpSocket | None = None
            self._log = b""
            self._tries = 0
            self.terminate_on_stop = True       # Attach to Process sets False (detach, the program goes on)

        def _dispatch(self, msg):
            # attached: the program's own output never comes through dlv, so every output event
            # (logpoints use category "stdout") is shown - only Delve's banner is dropped
            if msg.get("type") == "event" and msg.get("event") == "output":
                if (msg.get("body") or {}).get("output", "").startswith("Type 'dlv help'"):
                    return
            DapSession._dispatch(self, msg)

        def start(self):
            if not self.argv or not self.argv[0]:
                self.failed.emit(f"debug adapter '{self.adapter}' is not installed")
                self.finished.emit(1)
                return
            self.proc.start(self.argv[0], self.argv[1:])

        def _read(self):                       # adapter stdout: wait for "listening"
            data = bytes(self.proc.readAllStandardOutput())
            self._log += data
            if self.sock is None and b"listening" in self._log.lower():
                self._connect()
            elif self.sock is not None and data.strip():
                self.output.emit(data.decode("utf-8", "replace"))

        def _connect(self):
            s = QTcpSocket(self)
            self.sock = s
            s.readyRead.connect(self._sock_read)
            s.connected.connect(self._sock_connected)
            s.errorOccurred.connect(self._sock_error)
            s.connectToHost("127.0.0.1", self.port)

        def _sock_error(self, _err):
            if self.sock is not None and self._tries < 20 and not self.ready:
                self._tries += 1
                self.sock.deleteLater()
                self.sock = None
                QTimer.singleShot(150, self._connect)

        def _sock_connected(self):
            super(AttachDap, self)._request(
                "initialize", {"clientID": "radide", "adapterID": self.adapter, "linesStartAt1": True,
                               "columnsStartAt1": True, "pathFormat": "path",
                               "supportsRunInTerminalRequest": False, "supportsVariableType": True},
                self._on_initialize)

        def _send(self, msg):
            if self.sock is None:
                return
            body = json.dumps(msg).encode("utf-8")
            self.sock.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

        def _sock_read(self):
            self._buf += bytes(self.sock.readAll())
            while True:
                end = self._buf.find(b"\r\n\r\n")
                if end < 0:
                    return
                length = 0
                for line in self._buf[:end].split(b"\r\n"):
                    if line.lower().startswith(b"content-length:"):
                        length = int(line.split(b":")[1])
                if len(self._buf) < end + 4 + length:
                    return
                body, self._buf = self._buf[end + 4:end + 4 + length], self._buf[end + 4 + length:]
                try:
                    self._dispatch(json.loads(body))
                except ValueError:
                    continue

        def stop(self):
            if self.running():
                self.user_stopped = True
                if self.sock is not None:
                    super(AttachDap, self)._request("disconnect", {"terminateDebuggee": self.terminate_on_stop})
                    self.sock.flush()
                if not self.proc.waitForFinished(1500):
                    self.proc.kill()
                    self.proc.waitForFinished(1000)

    return TcpDap


# ====================================================================== Attach to Process
def process_path(pid: int) -> str:
    """Full path of the executable of process *pid* ('' when it cannot be read)."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = wintypes.HANDLE
            h = k32.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return ""
            try:
                buf = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(buf))
                if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                    return buf.value
            finally:
                k32.CloseHandle(h)
        except (OSError, AttributeError):
            pass
        return ""
    try:
        return os.readlink(f"/proc/{int(pid)}/exe")
    except OSError:
        return ""


def is_go_binary(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"Go build ID:" in fh.read(1 << 20) or b"Go buildinf:" in fh.read(4 << 20)
    except OSError:
        return False


ATTACH_ENGINES = {"python": "Python (debugpy)", "native": "Native C/C++/Fortran/Rust (gdb)",
                  "go": "Go (Delve)", "dotnet": ".NET (netcoredbg)"}


def attach_engine_for(proc: dict) -> str:
    """Best engine for a process dict from list_processes() (+ 'path')."""
    kind = proc.get("kind") or ""
    if kind not in ("python", "dotnet", "native"):
        kind = process_kind(Path(proc.get("path") or process_path(proc["pid"]) or "x").name)
    if kind in ("python", "dotnet"):
        return kind
    path = proc.get("path") or process_path(proc["pid"])
    return "go" if path and is_go_binary(path) else "native"


def attach_missing(engine: str) -> str:
    """Why *engine* cannot attach here ('' = ready)."""
    import importlib.util
    if engine == "python":
        return "" if importlib.util.find_spec("debugpy") else "debugpy is not installed (pip install debugpy)"
    if engine == "go":
        return "" if find_dlv() else "Delve (dlv) was not found (Debug > Install Delve)"
    from .bridgedebug import find_gdb, find_netcoredbg
    if engine == "dotnet":
        return "" if find_netcoredbg() else "netcoredbg was not found (%LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg)"
    return "" if find_gdb() else "gdb was not found (WinLibs in %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64)"


def make_attach_session(engine: str, pid: int, exe: str, cwd, breakpoints, parent=None):
    """A Session-compatible debugger attached to the running process *pid*.
    Stop detaches (the program keeps running), like Visual Studio's Detach All."""
    import sys

    from .bridgedebug import AttachDap, find_gdb, find_netcoredbg, gdb_env

    class ProcessAttach(AttachDap):
        def stop(self):
            if self.running():
                self.user_stopped = True
                self._request("disconnect", {"terminateDebuggee": False})
                if not self.proc.waitForFinished(2500):
                    self.proc.kill()
                    self.proc.waitForFinished(1000)

        def _dispatch(self, msg):
            from .dap import DapSession
            DapSession._dispatch(self, msg)           # attached: show the program's output events too

        def _emit_stop(self, info):
            skip = ("registers.", "register.", "globals.", "global.")
            info.variables = [(n, t, v if v or n not in info.refs else "{...}") for n, t, v in info.variables
                              if not n.lower().startswith(skip)]
            info.refs = {n: r for n, r in info.refs.items() if not n.lower().startswith(skip)}
            super()._emit_stop(info)

    if engine == "python":
        pid = python_child(pid)                    # venv launcher -> the real interpreter
        s = ProcessAttach([sys.executable, "-m", "debugpy.adapter"], "debugpy",
                          {"request": "attach", "processId": int(pid), "justMyCode": False}, cwd, None, breakpoints, parent)
    elif engine == "go":
        s = make_tcp_dap()([find_dlv(), "dap"], "go", {"request": "attach", "mode": "local", "processId": int(pid)},
                           cwd, None, breakpoints, parent)
        s.terminate_on_stop = False
    elif engine == "dotnet":
        s = ProcessAttach([find_netcoredbg(), "--interpreter=vscode"], "coreclr",
                          {"type": "coreclr", "request": "attach", "processId": int(pid), "justMyCode": False},
                          cwd, None, breakpoints, parent)
    else:
        gdb = find_gdb()
        args = {"pid": int(pid)}
        if exe:
            args["program"] = exe
        s = ProcessAttach([gdb, "-i", "dap"], "gdb", args, cwd, gdb_env(gdb), breakpoints, parent)
    s.attached_pid = int(pid)
    return s
