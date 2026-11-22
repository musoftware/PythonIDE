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
    if getattr(sys, "frozen", False):           # release build: debugpy of the real Python (radide/paths.py)
        from .paths import python_has_module
        return [sys.executable, "-m", "debugpy.adapter"] if python_has_module(sys.executable, "debugpy") else None
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
            if msg.get("command") == "initialize" and msg.get("success", True):
                self.capabilities = msg.get("body") or {}
            cb = self._callbacks.pop(msg.get("request_seq"), None)
            if not msg.get("success", True) and msg.get("command") in ("launch", "attach", "initialize"):
                self.failed.emit(msg.get("message", "debug adapter error"))
            if cb is not None:
                cb(msg.get("body") or {}, msg)
        elif t == "event":
            ev, body = msg.get("event"), msg.get("body") or {}
            if ev == "initialized":
                self._request("setExceptionBreakpoints", {"filters": self._exception_filters()})
                if self.exception_functions:          # e.g. Delve: runtime.gopanic = break on panics
                    self._request("setFunctionBreakpoints", {"breakpoints": [
                        {"name": n} for n in (self.exception_functions if self.break_on_exception else ())]})
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

    # adapters that change breakpoints only while the program is halted (Delve): set_breakpoint pauses it
    pause_for_bp_changes = False
    # count hit conditions here even if the adapter could (Delve keeps a breakpoint's hit count when it changes)
    count_hits_here = False

    def _flush_bp_queue(self, then=None):
        paths = sorted(self.__dict__.pop("_bp_queue", set()))
        self._bp_pausing = False
        if not paths:
            if then:
                then()
            return
        left = [len(paths)]

        def one(*_a):
            left[0] -= 1
            if left[0] == 0 and then:
                then()
        for path in paths:
            self._request("setBreakpoints", {"source": {"path": path},
                                             "breakpoints": self._bp_list(path, self.breakpoints.get(path, set()))},
                          one)

    def _on_stopped(self, reason):
        if getattr(self, "_bp_pausing", False):
            if reason == "pause":           # the pause asked for by set_breakpoint: change them, go on
                self._flush_bp_queue(lambda: self._request("continue", {"threadId": self.thread_id}))
                return
            self._flush_bp_queue()          # stopped for another reason meanwhile: change them, stay stopped

        def got_stack(body, _m):
            nonlocal reason
            frames = body.get("stackFrames", [])
            if not frames:
                return
            top = frames[0]
            if self.exception_functions and any(n.split(".")[-1] in (top.get("name") or "")
                                                for n in self.exception_functions):
                reason = "exception"            # runtime.gopanic / rust_panic: a panic starts
            if reason == "breakpoint" and self._hit_held_back(top):
                return
            here = ((top.get("source") or {}).get("path", ""), top.get("line", 0), len(frames))
            sf = getattr(self, "_step_from", None)
            if reason == "step" and sf and sf[0] == "stepOut" and here[0] == sf[1][0] and here[2] >= sf[1][2] \
                    and self._step_again < 3:      # stopped at the "end" of the method: out once more
                self._step_again += 1
                self._request("stepOut", {"threadId": self.thread_id})
                return
            if reason == "step" and sf and sf[0] != "stepOut" and sf[1] == here and self._step_again < 50:
                self._step_again += 1
                self._request(sf[0], {"threadId": self.thread_id})
                return
            self._step_from = None
            self._last_stop = here
            if reason == "exception":       # a panic / signal inside the runtime or a library: show the user's line
                user = next((f for f in frames if self._is_user_frame(f)), None)
                if user is not None:
                    top = user
            self.frame_id = top["id"]
            info = StopInfo(top.get("source", {}).get("path", ""), top.get("line", 0),
                            {"breakpoint": "breakpoint", "exception": "error"}.get(reason, "step"))
            info.thread_id = self.thread_id
            info.frames = [(f.get("name", ""), f.get("source", {}).get("path", ""), f.get("line", 0)) for f in frames]

            def got_scopes(sb, _m):
                # (gdb's DAP also reports a "Registers" scope: not shown in Locals)
                scopes = [s for s in sb.get("scopes", []) if not s.get("expensive")
                          and s.get("presentationHint") != "registers" and s.get("name") != "Registers"]
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
                            info.variables.append((prefix + name, v.get("type", ""),
                                                   v.get("value", "") or ("{...}" if v.get("variablesReference") else "")))
                            if v.get("variablesReference"):          # expandable (debug_extras / Locals)
                                info.refs[prefix + name] = v["variablesReference"]
                        remaining[0] -= 1
                        if remaining[0] == 0:
                            self._emit_stop(info)
                    self._request("variables", {"variablesReference": s["variablesReference"]}, got_vars)
            self._request("scopes", {"frameId": self.frame_id}, got_scopes)
        self._request("stackTrace", {"threadId": self.thread_id, "startFrame": 0, "levels": 30}, got_stack)

    # GUI Bridge client libraries (radide/runtimes/clients) are copied next to the user's code
    _CLIENT_FILES = {"radgui.c", "radgui.h", "radgui.hpp", "rad.cs", "radmain.cs", "radgui.dart", "radworker.dart",
                     "radlib.go", "rad.java", "radcontrol.java", "radevent.java", "radjson.java", "radmain.java",
                     "radgui.js", "radworker.js", "rad.lua", "radworker.lua", "radgui.pm", "radworker.pl",
                     "rad.ps1", "radmain.ps1", "rad.rb", "radworker.rb", "radgui.rs"}

    def _is_user_frame(self, frame: dict) -> bool:
        path = (frame.get("source") or {}).get("path") or ""
        if not path or not frame.get("line"):
            return False
        try:
            p = Path(path).resolve()
            return p.name.lower() not in self._CLIENT_FILES and self.cwd in p.parents
        except (OSError, ValueError):
            return False

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
    # adapters that stop at every expression of a line when stepping (Dart): a step that stays on the same line of
    # the same frame steps again, so F10 / F11 move by lines like the other languages
    line_steps = False
    # adapters whose Step Out stops at the return of the method itself (Ruby's debug gem): step out again
    step_out_twice = False

    def _resume(self, command):
        if self.paused:
            self.paused = False
            last = getattr(self, "_last_stop", None)
            self._step_from = (command, last) if last and (command in ("next", "stepIn") and self.line_steps or
                                                           command == "stepOut" and self.step_out_twice) else None
            self._step_again = 0
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
        out = [dap_breakpoint(n, self.conditions.get((path, n), ""), self.adapter) for n in sorted(lines)]
        if not self._adapter_hits():
            for bp in out:
                bp.pop("hitCondition", None)            # counted here instead (_hit_held_back)
        return out

    def _adapter_hits(self) -> bool:
        """Does the adapter count hit conditions itself? (netcoredbg does not: then this session counts)"""
        if self.count_hits_here or self.adapter == "gdb":     # gdb: hitCondition is an ignore count of its own
            return False
        caps = getattr(self, "capabilities", None)
        return caps is None or bool(caps.get("supportsHitConditionalBreakpoints"))

    def _hit_held_back(self, top: dict) -> bool:
        """A breakpoint with a hit count the adapter does not support: count the stop and go on until it is met."""
        if self._adapter_hits():
            return False
        import os

        from .debug_extras import hit_ok, parse_bp
        path = (top.get("source") or {}).get("path") or ""
        line = int(top.get("line") or 0)
        if not path:
            return False
        try:
            norm = os.path.normcase(str(Path(path).resolve()))
        except OSError:
            return False
        key = next(((p, n) for (p, n) in self.conditions if n == line and os.path.normcase(p) == norm), None)
        hit = parse_bp(self.conditions.get(key, ""))["hit"] if key else ""
        if not hit:
            return False
        hits = self.__dict__.setdefault("_hits", {})
        hits[key] = hits.get(key, 0) + 1
        if hit_ok(hit, hits[key]):
            return False
        self._request("continue", {"threadId": self.thread_id})
        return True

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
                out.append((v.get("name", ""), v.get("type", ""),
                            v.get("value", "") or ("{...}" if v.get("variablesReference") else ""),
                            v.get("variablesReference", 0)))
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
        self.__dict__.get("_hits", {}).pop((path, line), None)      # a changed breakpoint counts again
        if self.pause_for_bp_changes and not self.paused and self.running():
            # Delve answers setBreakpoints only while the program is halted: pause, change, go on
            self.__dict__.setdefault("_bp_queue", set()).add(path)
            if not getattr(self, "_bp_pausing", False):
                self._bp_pausing = True
                self._request("pause", {"threadId": self.thread_id})
            return
        self._request("setBreakpoints", {"source": {"path": path}, "breakpoints": self._bp_list(path, lines)})

    # exception filters for Debug > Break on Exceptions, in order of preference: the first ones the adapter offers
    # (initialize -> exceptionBreakpointFilters) are used. BridgeDebugSession sets its own (the bridge client
    # catches every handler error, so "uncaught" never fires there)
    exception_filter_prefs: tuple = ("uncaught", "userUnhandled", "user-unhandled", "Unhandled", "unhandled")
    # adapters without exception filters: functions whose breakpoint means "an exception" (a stop there shows the
    # user's line that raised it)
    exception_functions: tuple = ()

    def _exception_filters(self) -> list[str]:
        if not self.break_on_exception:
            return []
        offered = [f.get("filter") for f in (getattr(self, "capabilities", {}) or {}).get(
            "exceptionBreakpointFilters", []) if isinstance(f, dict)]
        if not offered:
            return ["uncaught", "userUnhandled"]
        return [f for f in offered if f in self.exception_filter_prefs]

    def set_break_on_exception(self, on: bool):
        self.break_on_exception = on
        self._request("setExceptionBreakpoints", {"filters": self._exception_filters()})
        if self.exception_functions:
            self._request("setFunctionBreakpoints",
                          {"breakpoints": [{"name": n} for n in (self.exception_functions if on else ())]})

    def stop(self):
        if self.running():
            self.user_stopped = True
            self._request("disconnect", {"terminateDebuggee": True})
            if not self.proc.waitForFinished(1500):
                self.proc.kill()
                self.proc.waitForFinished(1000)
