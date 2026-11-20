"""Debug Adapter Protocol client.

DapSession has the same signals and methods as radide.debugger.Session, so the
IDE can debug any language that has a ready-made debug adapter:
    python  -> debugpy        (python -m debugpy.adapter)
    c/cpp/fortran/rust -> gdb (gdb -i dap, gdb >= 14)
    go      -> delve          (dlv dap)
    dart    -> dart debug_adapter
ADAPTERS maps a name to (adapter argv builder, launch-arguments builder).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from .debugger import StopInfo


def _python_adapter():
    import importlib.util
    if importlib.util.find_spec("debugpy") is None:
        return None
    return [sys.executable, "-m", "debugpy.adapter"]


def _dlv():
    from .debug_extras import find_dlv          # PATH or %LOCALAPPDATA%\RADIDE\tools\dlv
    return find_dlv()


ADAPTERS = {
    "debugpy": (_python_adapter, lambda prog, args, cwd, env: {
        "type": "python", "request": "launch", "program": prog, "args": args, "cwd": cwd, "env": env,
        "console": "internalConsole", "justMyCode": True, "redirectOutput": True}),
    "gdb": (lambda: [shutil.which("gdb"), "-i", "dap"] if shutil.which("gdb") else None,
            lambda prog, args, cwd, env: {"program": prog, "args": args, "cwd": cwd, "stopAtBeginningOfMainSubprogram": False}),
    "dlv": (lambda: [_dlv(), "dap"] if _dlv() else None,
            lambda prog, args, cwd, env: {"mode": "debug", "program": prog, "args": args, "cwd": cwd}),
    "dart": (lambda: [shutil.which("dart") or "dart", "debug_adapter"] if shutil.which("dart") else None,
             lambda prog, args, cwd, env: {"program": prog, "args": args, "cwd": cwd}),
}


class DapSession(QObject):
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)      # StopInfo
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, adapter: str, program: str, args: list[str], cwd: Path, env: dict | None,
                 breakpoints: list[tuple[str, int]], parent=None):
        super().__init__(parent)
        self.debug = True
        cwd = Path(cwd).resolve()                 # debugpy spawns its launcher elsewhere: no relative paths
        program = str(Path(program).resolve()) if program else program
        self.paused = False
        self.user_stopped = False
        self.adapter = adapter
        build_argv, build_launch = ADAPTERS[adapter]
        self.argv = build_argv()
        self.launch_args = build_launch(program, args, str(cwd), env or {})
        self.cwd = Path(cwd)
        self.breakpoints: dict[str, set[int]] = {}
        self.conditions: dict[tuple[str, int], str] = {}
        self.break_on_exception = True
        for bp in breakpoints:
            f, line = bp[0], bp[1]
            path = str((self.cwd / f).resolve())
            self.breakpoints.setdefault(path, set()).add(line)
            if len(bp) > 2 and bp[2]:
                self.conditions[(path, line)] = bp[2]
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(cwd))
        if env:
            e = QProcessEnvironment.systemEnvironment()
            for k, v in env.items():
                e.insert(k, v)
            self.proc.setProcessEnvironment(e)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.readyReadStandardError.connect(self._read_stderr)
        self.proc.finished.connect(lambda code, _s: self._finish(code))
        self._buf = b""
        self._seq = 0
        self._callbacks: dict[int, callable] = {}
        self.thread_id = 1
        self.frame_id = None
        self._exit_code = 0
        self._done = False

    def _read_stderr(self):
        text = bytes(self.proc.readAllStandardError()).decode("utf-8", "replace")
        if getattr(self, "user_stopped", False):
            return      # the adapter's own log after Stop (debugpy: "couldn't handle disconnect ...") - noise
        self.output.emit(text)

    # ------------------------------------------------------------ protocol
    def start(self):
        if not self.argv:
            self.failed.emit(f"debug adapter '{self.adapter}' is not installed")
            self.finished.emit(1)
            return
        self.proc.start(self.argv[0], self.argv[1:])
        self._request("initialize", {"clientID": "radide", "adapterID": self.adapter, "linesStartAt1": True,
                                     "columnsStartAt1": True, "pathFormat": "path",
                                     "supportsRunInTerminalRequest": False, "supportsVariableType": True},
                      self._on_initialize)

    def running(self) -> bool:
        return self.proc.state() != QProcess.ProcessState.NotRunning

    def _send(self, msg):
        body = json.dumps(msg).encode("utf-8")
        self.proc.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

    def _request(self, command, arguments=None, cb=None):
        self._seq += 1
        if cb is not None:
            self._callbacks[self._seq] = cb
        self._send({"seq": self._seq, "type": "request", "command": command, "arguments": arguments or {}})

    def _read(self):
        self._buf += bytes(self.proc.readAllStandardOutput())
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

    def _dispatch(self, msg):
        t = msg.get("type")
        if t == "response":
            cb = self._callbacks.pop(msg.get("request_seq"), None)
            if not msg.get("success", True) and msg.get("command") in ("launch", "attach", "initialize"):
                self.failed.emit(msg.get("message", "debug adapter error"))
            if cb is not None:
                cb(msg.get("body") or {}, msg)
        elif t == "event":
            ev, body = msg.get("event"), msg.get("body") or {}
            if ev == "initialized":
                self._request("setExceptionBreakpoints",
                              {"filters": ["uncaught", "userUnhandled"] if self.break_on_exception else []})
                self._send_breakpoints(lambda: self._request("configurationDone"))
            elif ev == "output":
                if body.get("category") != "telemetry":
                    self.output.emit(body.get("output", ""))
            elif ev == "stopped":
                self.thread_id = body.get("threadId", self.thread_id)
                self._on_stopped(body.get("reason", "step"))
            elif ev == "continued":
                self.paused = False
                self.resumed.emit()
            elif ev == "exited":
                self._exit_code = body.get("exitCode", 0)
            elif ev == "terminated":
                self._request("disconnect", {"terminateDebuggee": True},
                              lambda _b, _m: self.proc.kill() if self.running() else None)
                self._finish(0)
        elif t == "request" and msg.get("command") == "runInTerminal":
            self._send({"seq": 0, "type": "response", "request_seq": msg["seq"], "success": False,
                        "command": "runInTerminal", "message": "not supported"})

    def _on_initialize(self, body, _msg):
        self._request("launch", self.launch_args)

    def _send_breakpoints(self, then=None):
        files = list(self.breakpoints.items())
        if not files:
            if then:
                then()
            return
        pending = [len(files)]

        def one_done(*_a):
            pending[0] -= 1
            if pending[0] == 0 and then:
                then()
        for path, lines in files:
            self._request("setBreakpoints", {"source": {"path": path},
                                             "breakpoints": self._bp_list(path, lines)}, one_done)

    def _on_stopped(self, reason):
        def got_stack(body, _m):
            frames = body.get("stackFrames", [])
            if not frames:
                return
            top = frames[0]
            self.frame_id = top["id"]
            info = StopInfo(top.get("source", {}).get("path", ""), top.get("line", 0),
                            {"breakpoint": "breakpoint", "exception": "error"}.get(reason, "step"))
            info.thread_id = self.thread_id
            info.frames = [(f.get("name", ""), f.get("source", {}).get("path", ""), f.get("line", 0)) for f in frames]

            def got_scopes(sb, _m):
                scopes = [s for s in sb.get("scopes", []) if not s.get("expensive")]
                if not scopes:
                    self._emit_stop(info)
                    return
                remaining = [len(scopes)]
                for s in scopes:
                    def got_vars(vb, _m, s=s):
                        for v in vb.get("variables", []):
                            name = v.get("name", "")
                            if name.startswith("__") or name in ("special variables", "function variables"):
                                continue
                            prefix = "" if s.get("name", "").lower().startswith("local") else s.get("name", "") + "."
                            info.variables.append((prefix + name, v.get("type", ""), v.get("value", "")))
                            if v.get("variablesReference"):          # expandable (debug_extras / Locals)
                                info.refs[prefix + name] = v["variablesReference"]
                        remaining[0] -= 1
                        if remaining[0] == 0:
                            self._emit_stop(info)
                    self._request("variables", {"variablesReference": s["variablesReference"]}, got_vars)
            self._request("scopes", {"frameId": self.frame_id}, got_scopes)
        self._request("stackTrace", {"threadId": self.thread_id, "startFrame": 0, "levels": 30}, got_stack)

    def _emit_stop(self, info):
        self.paused = True
        self.stopped.emit(info)

    def _finish(self, code):
        if self._done:
            return
        self._done = True
        self.paused = False
        self.finished.emit(self._exit_code if code == 0 else code)
        if self.running():
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.proc.kill() if self.running() else None)

    # ------------------------------------------------------------ Session-compatible commands
    def _resume(self, command):
        if self.paused:
            self.paused = False
            self._request(command, {"threadId": self.thread_id})
            self.resumed.emit()

    def cont(self):
        self._resume("continue")

    def step_into(self):
        self._resume("stepIn")

    def step_over(self):
        self._resume("next")

    def step_out(self):
        self._resume("stepOut")

    def evaluate(self, expr: str):
        if not self.paused:
            self.evalResult.emit("(the program must be paused at a breakpoint)")
            return
        self._request("evaluate", {"expression": expr, "frameId": self.frame_id, "context": "repl"},
                      lambda b, m: self.evalResult.emit(b.get("result", "") if m.get("success", True)
                                                        else m.get("message", "error")))

    def _bp_list(self, path, lines):
        from .debug_extras import dap_breakpoint        # condition + hitCondition + logMessage
        return [dap_breakpoint(n, self.conditions.get((path, n), ""), self.adapter) for n in sorted(lines)]

    # ------------------------------------------------------------ expandable values, threads (debug_extras)
    def children(self, ref, cb):
        """cb([(name, type, value, child_ref or 0)]) - the DAP 'variables' of *ref*."""
        if not self.paused or not ref:
            cb([])
            return

        def got(b, m):
            out = []
            for v in (b.get("variables", []) if m.get("success", True) else []):
                if v.get("name") in ("special variables", "function variables"):
                    continue
                out.append((v.get("name", ""), v.get("type", ""), v.get("value", ""), v.get("variablesReference", 0)))
            cb(out)
        self._request("variables", {"variablesReference": int(ref)}, got)

    def watch(self, expr, cb):
        """cb(value, type, ref) of a Watch expression (DAP evaluate, context 'watch')."""
        if not self.paused:
            cb("(the program must be paused at a breakpoint)", "", 0)
            return
        self._request("evaluate", {"expression": expr, "frameId": self.frame_id, "context": "watch"},
                      lambda b, m: cb(b.get("result", "") if m.get("success", True) else m.get("message", "error"),
                                      b.get("type", ""), b.get("variablesReference", 0) if m.get("success", True) else 0))

    def threads(self, cb):
        """cb([(id, name)]) of the program's threads."""
        if not self.running():
            cb([])
            return
        self._request("threads", {}, lambda b, m: cb([(t.get("id"), t.get("name", "")) for t in b.get("threads", [])]))

    def select_thread(self, tid):
        """Show the stack / locals of thread *tid* (the program stays paused)."""
        if self.paused and tid:
            self.thread_id = int(tid)
            self._on_stopped("pause")

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = ""):
        path = str((self.cwd / filename).resolve())
        lines = self.breakpoints.setdefault(path, set())
        (lines.add if on else lines.discard)(line)
        if on and cond:
            self.conditions[(path, line)] = cond
        elif not on or not cond:
            self.conditions.pop((path, line), None)
        self._request("setBreakpoints", {"source": {"path": path}, "breakpoints": self._bp_list(path, lines)})

    def set_break_on_exception(self, on: bool):
        self.break_on_exception = on
        self._request("setExceptionBreakpoints", {"filters": ["uncaught", "userUnhandled"] if on else []})

    def stop(self):
        if self.running():
            self.user_stopped = True
            self._request("disconnect", {"terminateDebuggee": True})
            if not self.proc.waitForFinished(1500):
                self.proc.kill()
                self.proc.waitForFinished(1000)
