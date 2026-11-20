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

import csv
import io
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
        try:
            r = subprocess.run(["tasklist", "/fo", "csv", "/nh", "/v"], capture_output=True, text=True,
                               timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                               encoding="mbcs", errors="replace")
            for row in csv.reader(io.StringIO(r.stdout)):
                if len(row) < 2 or not row[1].isdigit():
                    continue
                title = row[-1] if len(row) >= 9 else ""
                out.append({"pid": int(row[1]), "name": row[0], "title": "" if title == "N/A" else title})
        except (OSError, subprocess.SubprocessError):
            pass
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
