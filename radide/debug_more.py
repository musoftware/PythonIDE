"""More debug engines for GUI Bridge programs (used by radide/bridgedebug.py).

    ruby-bridge        "rdbg"      the debug gem (bundled with Ruby): the program runs with
                                   ``ruby -r debug/open`` (RUBY_DEBUG_PORT) and the IDE speaks DAP to that
                                   TCP port directly (no adapter process).
    lua-bridge         "luaagent"  radide/debug/raddbg_agent.lua (debug.sethook, pure Lua) - loaded before
                                   _radmain.lua; it talks to the IDE over a named pipe (QLocalServer).
    perl-bridge        "perlagent" radide/debug/perl/Devel/RadDbg.pm (``perl -d:RadDbg``) - same pipe protocol.
    powershell-bridge  "pses"      PowerShell Editor Services' debug adapter (tools\\pses, see lsp_servers.py)
                                   attaches to the running powershell.exe (processId + runspaceId 1).
    expo (web)         js-debug    ``ExpoWebDebugSession``: js-debug launches Edge/Chrome on the Expo web page
                                   (pwa-msedge / pwa-chrome) and maps breakpoints through Metro's source maps.

Agent line protocol (Lua / Perl), one message per line, fields separated by TAB
(``\\`` ``\\t`` ``\\n`` ``\\r`` escaped):
    agent -> IDE   hello <lang> <version> | stop <reason> <file> <line> + frame <name> <file> <line>* +
                   var <name> <type> <value> <ref>* + end | result <id> <value> <type> <ref> |
                   vars <id> + var* + end | out <text>
    IDE -> agent   run | c | s | n | o | e <id> <expr> | v <id> <ref> | q
Breakpoints travel in a file (RADDBG_BPFILE: ``path TAB line TAB cond TAB hit TAB log``) that the agent
re-reads when it changes, so they can be changed while the program runs (an agent blocked in a read of
stdin cannot read a pipe at the same time).
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

HERE = Path(__file__).resolve().parent
LUA_AGENT = HERE / "debug" / "raddbg_agent.lua"
PERL_AGENT_LIB = HERE / "debug" / "perl"

TRACE = bool(os.environ.get("RADIDE_DAP_TRACE"))     # print the DAP traffic of SocketDap to stderr
ENGINES = {"ruby-bridge": "rdbg", "lua-bridge": "luaagent", "perl-bridge": "perlagent",
           "powershell-bridge": "pses"}

_ENDPOINTS: dict[int, "AgentEndpoint"] = {}       # bridge debug port -> endpoint made by adjust_spec()


# ====================================================================== checks
def _ruby_has_debug(ruby: str) -> bool:
    import subprocess
    try:
        r = subprocess.run([ruby, "-e", "require 'debug/session'; print 'ok'"], capture_output=True, text=True,
                           timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                           env=dict(os.environ, RUBY_DEBUG_NO_SIGINT_HOOK="1"))
        return r.stdout.strip().endswith("ok")
    except (OSError, ValueError):
        return False


_CACHE: dict[str, str] = {}


def missing(engine: str, plugin=None) -> str | None:
    """Why *engine* cannot run ('' = ready); None = not an engine of this module."""
    if engine == "rdbg":
        ruby = plugin.tool() if plugin is not None else shutil.which("ruby")
        if not ruby:
            return "Ruby was not found"
        if ruby not in _CACHE:
            _CACHE[ruby] = "" if _ruby_has_debug(ruby) else "the debug gem is missing: gem install debug"
        return _CACHE[ruby]
    if engine == "luaagent":
        return "" if LUA_AGENT.exists() else "radide/debug/raddbg_agent.lua is missing"
    if engine == "perlagent":
        if not (PERL_AGENT_LIB / "Devel" / "RadDbg.pm").exists():
            return "Devel/RadDbg.pm is missing"
        perl = plugin.tool() if plugin is not None else ""
        if perl and os.name == "nt":
            if perl not in _CACHE:
                import subprocess
                try:
                    r = subprocess.run([perl, "-e", "print $^O"], capture_output=True, text=True, timeout=20,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    osname = r.stdout.strip()
                except (OSError, ValueError, subprocess.SubprocessError):
                    osname = ""
                _CACHE[perl] = "" if osname in ("MSWin32", "") else (
                    f"{perl} is an {osname} perl (Git for Windows) - debugging needs a native Windows perl: "
                    "Strawberry Perl in %LOCALAPPDATA%\\RADIDE\\toolchains\\strawberry")
            return _CACHE[perl]
        return ""
    if engine == "pses":
        from .lsp_servers import find_powershell, find_pses
        if not find_pses():
            return "PowerShell Editor Services is not installed (Tools > Language Servers... > PowerShell)"
        return "" if find_powershell() else "PowerShell was not found"
    return None


# ====================================================================== run spec
def adjust_run(cmd: list[str], plugin, port: int, env: dict) -> list[str]:
    """Change the program's command line / environment for debugging (called by bridgedebug.debug_spec)."""
    eng = ENGINES.get(getattr(plugin, "id", ""))
    cmd = list(cmd)
    if eng == "rdbg" and cmd:
        env["RUBY_DEBUG_PORT"] = str(port)
        env["RUBY_DEBUG_HOST"] = "127.0.0.1"
        env["RUBY_DEBUG_NO_SIGINT_HOOK"] = "1"
        env.pop("RUBY_DEBUG_OPEN_FRONTEND", None)
        # debug/open waits for the IDE before the program runs: attaching while the program is already
        # blocked in $stdin.gets leaves the gem unable to answer stackTrace (Windows pipes)
        cmd[1:1] = ["-r", "debug/open"]
    elif eng in ("luaagent", "perlagent") and cmd:
        ep = AgentEndpoint(Path(env.get("RAD_PROJECT") or os.getcwd()))
        _ENDPOINTS[port] = ep
        env["RADDBG_PIPE"] = ep.pipe_path
        env["RADDBG_BPFILE"] = str(ep.bpfile)
        if eng == "luaagent":
            # before the script name (the last argument): lua [-e setup] -e dofile(agent) _radmain.lua
            agent = str(LUA_AGENT).replace("\\", "/")
            cmd[-1:-1] = ["-e", f"dofile([[{agent}]])"]
        else:
            # -I with forward slashes: also understood by Git's MSYS perl (PERL5LIB there splits on ':')
            cmd[1:1] = ["-I" + str(PERL_AGENT_LIB).replace("\\", "/"), "-d:RadDbg"]
    return cmd


def set_cwd(port: int, cwd: Path, env: dict):
    ep = _ENDPOINTS.get(port)
    if ep is not None:
        ep.cwd = Path(cwd).resolve()
        env["RADDBG_CWD"] = str(ep.cwd)


# ====================================================================== sessions
def make_dap(engine: str, bs):
    """The AttachDap-like object of *engine* for BridgeDebugSession *bs*."""
    cwd, bps = bs.cwd, bs.breakpoints
    if engine == "rdbg":
        d = make_socket_dap()(bs.port, "rdbg", {"request": "attach", "nonstop": True, "localfs": True,
                                                "cwd": str(cwd)}, cwd, bps, bs)
        d.step_out_twice = True                 # the gem's "finish" stops at the method's own return first
        return d
    if engine in ("luaagent", "perlagent"):
        ep = _ENDPOINTS.pop(bs.port, None)
        return AgentSession(ep, engine, cwd, bps, bs)
    if engine == "pses":
        from .lsp_servers import PSES_RELAY, pses_args
        argv = pses_args("-Stdio -DebugServiceOnly")
        if os.name == "nt":       # Enter-PSHostProcess needs a console: start PSES through the relay
            argv = [sys.executable, "-u", "-c", PSES_RELAY, *argv]
        d = make_pses_dap()(argv, "PowerShell",
                            {"type": "PowerShell", "request": "attach", "processId": bs.pid, "runspaceId": 1},
                            cwd, None, bps, bs)
        d.break_on_exception = False
        return d
    raise ValueError(engine)


def make_pses_dap():
    from .bridgedebug import AttachDap

    class PsesDap(AttachDap):
        """PSES attach: Debug-Runspace answers setBreakpoints only once the runspace breaks, which happens
        the next time the program runs PowerShell code (after the IDE lets the bridge send events). So
        configurationDone is sent without waiting for the breakpoint answers, and that first break (the
        attach itself, not a user breakpoint) is continued automatically."""

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._attach_break = True
            self._polls = 0

        def start(self):
            # attaching before the target has opened its PSHost.<time>.<pid>.* pipe hangs PSES' attach
            if not self._host_pipe_ready() and self._polls < 100:
                self._polls += 1
                QTimer.singleShot(150, self.start)
                return
            super().start()

        def _host_pipe_ready(self) -> bool:
            if os.name != "nt":
                return True
            pid = str(self.launch_args.get("processId", ""))
            try:
                return any(n.startswith("PSHost.") and f".{pid}." in n for n in os.listdir("\\\\.\\pipe\\"))
            except OSError:
                return True

        def _dispatch(self, msg):
            if msg.get("type") == "event" and msg.get("event") == "initialized":
                self._request("setExceptionBreakpoints", {"filters": []})
                self._bps_set = False
                self._send_breakpoints(self._bps_done)     # answered during the attach break
                self._request("configurationDone")
                return
            super()._dispatch(msg)

        def _configured(self):
            # Debug-Runspace needs a moment after configurationDone; PowerShell code that runs earlier breaks
            # into the target's own console debugger, which reads the next stdin line (the bridge event)
            if not self.ready:
                self.ready = True
                QTimer.singleShot(int(os.environ.get("RADIDE_PSES_SETTLE_MS", "3000")), self.configured.emit)

        def _bps_done(self):
            self._bps_set = True
            if self._attach_break == "stopped":           # the break waited for the breakpoints
                self._resume_attach_break()

        def _resume_attach_break(self):
            self._attach_break = False
            self._request("continue", {"threadId": self.thread_id})

        # Conditions / hit counts / logpoints do not survive Debug-Runspace (PSES builds the breakpoint action
        # in its own runspace): plain breakpoints go to PSES and the IDE checks the rest at each stop.
        def _bp_list(self, path, lines):
            return [{"line": n} for n in sorted(lines)]

        def _check_stop(self, reason):
            from .debug_extras import hit_ok, parse_bp

            def got(b, _m):
                frames = b.get("stackFrames") or []
                top = next((f for f in frames if f.get("name") != "<Breakpoint>"), frames[0] if frames else None)
                if not top:
                    super(PsesDap, self)._on_stopped(reason)
                    return
                key = (os.path.normcase(os.path.normpath(top.get("source", {}).get("path", ""))), top.get("line", 0))
                spec = next((c for (p, n), c in self.conditions.items()
                             if (os.path.normcase(os.path.normpath(p)), n) == key), "")
                d = parse_bp(spec)
                if not (d["cond"] or d["hit"] or d["log"]):
                    super(PsesDap, self)._on_stopped(reason)
                    return
                fid = top.get("id")

                def after_cond(ok):
                    if not ok:
                        self._request("continue", {"threadId": self.thread_id})
                        return
                    self._hits[key] = self._hits.get(key, 0) + 1
                    if d["hit"] and not hit_ok(d["hit"], self._hits[key]):
                        self._request("continue", {"threadId": self.thread_id})
                        return
                    if d["log"]:
                        import re
                        text = re.sub(r"\{([^{}]+)\}", r"$(\1)", d["log"]).replace('"', '`"')
                        self._request("evaluate", {"expression": f'"{text}"', "frameId": fid, "context": "watch"},
                                      lambda eb, em: (self.output.emit((eb.get("result", "") if em.get("success", True)
                                                                        else d["log"]).strip('"') + "\n"),
                                                      self._request("continue", {"threadId": self.thread_id})))
                        return
                    super(PsesDap, self)._on_stopped(reason)
                if d["cond"]:
                    self._request("evaluate", {"expression": f"[bool]({d['cond']})", "frameId": fid, "context": "watch"},
                                  lambda eb, em: after_cond(em.get("success", True) and
                                                            str(eb.get("result", "")).strip().lower() in ("$true", "true")))
                else:
                    after_cond(True)
            self._request("stackTrace", {"threadId": self.thread_id, "startFrame": 0, "levels": 3}, got)

        def _on_stopped(self, reason):
            if not hasattr(self, "_hits"):
                self._hits = {}
            if not self._attach_break and reason == "breakpoint" and self.conditions:
                self._check_stop(reason)
                return
            if self._attach_break:
                # read the stack at once (as VS Code does): PSES finishes setting the breakpoints and resumes
                # the Debug-Runspace break reliably only after that
                def got(_b, _m):
                    if getattr(self, "_bps_set", True):
                        self._resume_attach_break()
                    else:
                        self._attach_break = "stopped"
                self._request("stackTrace", {"threadId": self.thread_id}, got)
                return
            super()._on_stopped(reason)

        def set_break_on_exception(self, on: bool):
            self.break_on_exception = on
            self._request("setExceptionBreakpoints", {"filters": ["Error"] if on else []})

        def evaluate(self, expr: str):
            """Immediate: PSES runs a "repl" evaluation as a command in the attached (Debug-Runspace) runspace,
            which never answers and blocks the next step - evaluate expressions as Watch does."""
            if not self.paused:
                return super().evaluate(expr)
            self._request("evaluate", {"expression": expr, "frameId": self.frame_id, "context": "watch"},
                          lambda b, m: self.evalResult.emit(b.get("result", "") if m.get("success", True)
                                                            else m.get("message", "error")))

        # PSES changes breakpoints of an attached runspace only while it is stopped, and slowly: a resume sent
        # right after a change would overtake it. Changes made while the program runs apply at its next stop.
        def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = ""):
            path = str((self.cwd / filename).resolve())
            lines = self.breakpoints.setdefault(path, set())
            (lines.add if on else lines.discard)(line)
            if on and cond:
                self.conditions[(path, line)] = cond
            else:
                self.conditions.pop((path, line), None)
            self._bp_pending = getattr(self, "_bp_pending", 0) + 1

            def done(_b, _m):
                self._bp_pending -= 1
                if self._bp_pending == 0 and getattr(self, "_queued", None):
                    cmd, self._queued = self._queued, None
                    self._request(cmd, {"threadId": self.thread_id})
            self._request("setBreakpoints", {"source": {"path": path}, "breakpoints": self._bp_list(path, lines)}, done)

        def _resume(self, command):
            if self.paused and getattr(self, "_bp_pending", 0) > 0:
                self.paused = False
                self._queued = command
                self.resumed.emit()
                return
            super()._resume(command)

        def _emit_stop(self, info):
            # PSES scopes: Autos (the function's own variables) + Local/Script/Global full of automatic
            # variables ($MaximumAliasCount, ...). Show the Autos as the locals; drop PSES' "<Breakpoint>" frame.
            autos = [(n[5:], t, v) for n, t, v in info.variables if n.startswith("Auto.")]
            if autos:
                info.refs = {k[5:]: r for k, r in info.refs.items() if k.startswith("Auto.")}
                info.variables = autos
            else:
                keep = {"$e", "$args"}
                info.variables = [x for x in info.variables if "." not in x[0] and (x[0] in keep or not
                                  x[0].lstrip("$")[:1].isupper())]
            if info.frames and info.frames[0][0] == "<Breakpoint>" and len(info.frames) > 1:
                info.frames = info.frames[1:]
            super()._emit_stop(info)

    return PsesDap


# ---------------------------------------------------------------------- DAP over a TCP socket (debug gem)
def make_socket_dap():
    from PyQt6.QtNetwork import QAbstractSocket, QTcpSocket

    from .bridgedebug import AttachDap

    class SocketDap(AttachDap):
        """DAP spoken directly to a debuggee that listens on TCP (Ruby's debug gem) - no adapter process."""

        def __init__(self, port, adapter_id, attach_args, cwd, breakpoints, parent=None):
            super().__init__([], adapter_id, attach_args, cwd, None, breakpoints, parent)
            self.port = port
            self.sock: QTcpSocket | None = None
            self._tries = 0
            self._was_connected = False

        def start(self):
            self._connect()

        def _connect(self):
            s = QTcpSocket(self)
            self.sock = s
            s.readyRead.connect(self._sock_read)
            s.connected.connect(self._sock_connected)
            s.errorOccurred.connect(self._sock_error)
            s.disconnected.connect(self._sock_gone)
            s.connectToHost("127.0.0.1", self.port)

        def _sock_error(self, _err):
            if self._was_connected:
                return
            if self._tries < 100:
                self._tries += 1
                old, self.sock = self.sock, None
                old.deleteLater()
                QTimer.singleShot(150, self._connect)
            else:
                self.failed.emit(f"could not connect to the debug port {self.port}")
                self._finish(1)

        def _sock_gone(self):
            if self._was_connected:
                self._finish(0)

        def running(self) -> bool:
            return self.sock is not None and self.sock.state() == QAbstractSocket.SocketState.ConnectedState

        def _sock_connected(self):
            self._was_connected = True
            super(AttachDap, self)._request(
                "initialize", {"clientID": "radide", "adapterID": self.adapter, "linesStartAt1": True,
                               "columnsStartAt1": True, "pathFormat": "path",
                               "supportsRunInTerminalRequest": False, "supportsVariableType": True},
                self._on_initialize)

        def _send(self, msg):
            import json
            if self.sock is None:
                return
            body = json.dumps(msg).encode("utf-8")
            if TRACE:
                print("DAP>>", body[:300], file=sys.stderr, flush=True)
            self.sock.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

        def _sock_read(self):
            import json
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
                    msg = json.loads(body)
                except ValueError:
                    continue
                if TRACE:
                    print("DAP<<", body[:300], file=sys.stderr, flush=True)
                if msg.get("type") == "event" and msg.get("event") == "output" and \
                        "Ruby REPL" in (msg.get("body") or {}).get("output", ""):
                    continue                    # the gem's REPL banner
                self._dispatch(msg)

        def set_break_on_exception(self, on: bool):
            self.break_on_exception = on
            self._request("setExceptionBreakpoints", {"filters": ["RuntimeError"] if on else []})

        def _emit_stop(self, info):
            # the gem lists every global ($!, $", ...) as a cheap scope: keep locals only
            info.variables = [v for v in info.variables if not v[0].startswith(("Global variables.", "%self"))]
            info.refs = {k: r for k, r in info.refs.items() if not k.startswith(("Global variables.", "%self"))}
            super()._emit_stop(info)

        def _dispatch(self, msg):
            if msg.get("type") == "event" and msg.get("event") == "initialized":
                # the gem knows 'any' / 'RuntimeError' (not 'uncaught'); breakpoints, then configurationDone
                self._request("setExceptionBreakpoints",
                              {"filters": ["RuntimeError"] if self.break_on_exception else []})
                self._send_breakpoints(lambda: self._request("configurationDone"))
                return
            super()._dispatch(msg)

        def stop(self):
            if self.running():
                self.user_stopped = True
                super(AttachDap, self)._request("disconnect", {"terminateDebuggee": False})
                self.sock.flush()
                self.sock.disconnectFromHost()
            self._finish(0)

    return SocketDap


# ---------------------------------------------------------------------- agents over a named pipe
def _esc(s) -> str:
    return str(s).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _unesc(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"t": "\t", "n": "\n", "r": "\r"}.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def norm_key(path: str | Path, cwd: Path) -> str:
    """The agents' file key: absolute, lower case, forward slashes."""
    p = Path(path)
    if not p.is_absolute():
        p = cwd / p
    s = os.path.normpath(str(p)).replace("\\", "/").lower()
    return s


class AgentEndpoint(QObject):
    """QLocalServer (named pipe) + breakpoints file, created before the program starts."""
    hello = pyqtSignal()
    line = pyqtSignal(list)
    gone = pyqtSignal()

    def __init__(self, cwd: Path):
        from PyQt6.QtCore import QCoreApplication
        from PyQt6.QtNetwork import QLocalServer
        super().__init__(QCoreApplication.instance())
        self.cwd = Path(cwd).resolve()
        self.name = f"raddbg-{os.getpid()}-{uuid.uuid4().hex[:10]}"
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.listen(self.name)
        self.pipe_path = self.server.fullServerName()
        fd, name = tempfile.mkstemp(prefix="raddbg-", suffix=".bp")
        os.close(fd)
        self.bpfile = Path(name)
        self.out_sock = None          # agent writes here (first connection)
        self.in_sock = None           # agent reads here (second connection)
        self._buf = b""
        self.greeted = False
        self.server.newConnection.connect(self._new)
        QTimer.singleShot(120000, self._expire)

    def _expire(self):
        if self.out_sock is None:           # never used (no debug session attached): clean up
            self.close()

    def _new(self):
        while self.server.hasPendingConnections():
            s = self.server.nextPendingConnection()
            if self.out_sock is None:
                self.out_sock = s
                s.readyRead.connect(self._read)
                s.disconnected.connect(self.gone)
            elif self.in_sock is None:
                self.in_sock = s
            else:
                s.abort()

    def _read(self):
        self._buf += bytes(self.out_sock.readAll())
        while b"\n" in self._buf:
            raw, self._buf = self._buf.split(b"\n", 1)
            parts = [_unesc(x) for x in raw.decode("utf-8", "replace").rstrip("\r").split("\t")]
            if parts and parts[0] == "hello":
                self.greeted = True
                self.hello.emit()
            else:
                self.line.emit(parts)

    def send(self, *fields):
        if self.in_sock is not None:
            self.in_sock.write(("\t".join(_esc(f) for f in fields) + "\n").encode("utf-8"))
            self.in_sock.flush()

    def ready(self) -> bool:
        return self.greeted and self.in_sock is not None

    def close(self):
        for s in (self.in_sock, self.out_sock):
            if s is not None:
                try:
                    s.abort()
                except RuntimeError:
                    pass
        try:
            self.server.close()
        except RuntimeError:
            pass
        try:
            self.bpfile.unlink(missing_ok=True)
        except OSError:
            pass


class AgentSession(QObject):
    """AttachDap-compatible session for the Lua / Perl agents (see the module docstring)."""
    configured = pyqtSignal()
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, endpoint: AgentEndpoint | None, engine: str, cwd: Path, breakpoints, parent=None):
        super().__init__(parent)
        self.ep = endpoint
        self.engine = engine
        self.cwd = Path(cwd).resolve()
        self.paused = False
        self.ready = False
        self.user_stopped = False
        self.break_on_exception = False
        self.thread_id = 1
        self.bps: dict[tuple[str, int], str] = {}          # (absolute path, line) -> condition string
        for bp in breakpoints:
            self.bps[(str((self.cwd / bp[0]).resolve()), int(bp[1]))] = bp[2] if len(bp) > 2 else ""
        self._pending: list[str] | None = None             # lines of the stop being received
        self._collect: tuple[int, list] | None = None
        self._id = 0
        self._cbs: dict[int, object] = {}
        self._done = False

    # ------------------------------------------------------------ lifecycle
    def start(self):
        if self.ep is None:
            self.failed.emit("the debug agent endpoint was not prepared")
            self._finish(1)
            return
        self.ep.line.connect(self._on_line)
        self.ep.gone.connect(lambda: self._finish(0))
        self._write_bps()
        self._wait_hello(0)

    def _wait_hello(self, tries):
        if self.ep.ready():
            self.ep.send("run")
            self.ready = True
            self.configured.emit()
            return
        if tries > 200:                      # 30 s
            self.failed.emit("the debug agent did not connect")
            self.ready = True
            self.configured.emit()
            return
        QTimer.singleShot(150, lambda: self._wait_hello(tries + 1))

    def running(self) -> bool:
        return not self._done

    def stop(self):
        self.user_stopped = True
        if self.ep is not None and self.paused:
            self.ep.send("q")
        self._finish(0)

    def _finish(self, code):
        if self._done:
            return
        self._done = True
        self.paused = False
        if self.ep is not None:
            QTimer.singleShot(0, self.ep.close)
        self.finished.emit(code)

    # ------------------------------------------------------------ breakpoints
    def _write_bps(self):
        from .debug_extras import parse_bp
        lines = []
        for (path, line), cond in sorted(self.bps.items()):
            d = parse_bp(cond)
            lines.append("\t".join(_esc(x) for x in (norm_key(path, self.cwd), line, d["cond"], d["hit"], d["log"])))
        lines.append("!exc\t" + ("1" if self.break_on_exception else "0"))     # agents: break on errors
        text = "\n".join(lines) + "\n"
        if self.ep is not None:
            tmp = self.ep.bpfile.with_suffix(".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, self.ep.bpfile)

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = ""):
        key = (str((self.cwd / filename).resolve()), int(line))
        if on:
            self.bps[key] = cond or ""
        else:
            self.bps.pop(key, None)
        self._write_bps()

    def set_break_on_exception(self, on: bool):
        # the bridge runtime catches every handler error; the agents stop where it is raised (Lua: in the
        # xpcall message handler, Perl: $SIG{__DIE__})
        self.break_on_exception = on
        if self.ep is not None:
            self._write_bps()

    # ------------------------------------------------------------ commands
    def _resume(self, c):
        if self.paused:
            self.paused = False
            self.ep.send(c)
            self.resumed.emit()

    def cont(self):
        self._resume("c")

    def step_into(self):
        self._resume("s")

    def step_over(self):
        self._resume("n")

    def step_out(self):
        self._resume("o")

    def _ask(self, kind, arg, cb):
        self._id += 1
        self._cbs[self._id] = cb
        self.ep.send(kind, self._id, arg)

    def evaluate(self, expr: str):
        if not self.paused:
            self.evalResult.emit("(the program must be paused at a breakpoint)")
            return
        self._ask("e", expr, lambda v, t, r: self.evalResult.emit(v))

    def watch(self, expr, cb):
        if not self.paused:
            cb("(the program must be paused at a breakpoint)", "", 0)
            return
        self._ask("e", expr, lambda v, t, r: cb(v, t, int(r or 0)))

    def children(self, ref, cb):
        if not self.paused or not ref:
            cb([])
            return
        self._ask("v", int(ref), cb)

    def threads(self, cb):
        cb([(1, "main")] if self.running() else [])

    def select_thread(self, tid):
        pass

    # ------------------------------------------------------------ agent messages
    def _path(self, raw: str) -> str:
        p = Path(raw)
        if not p.is_absolute():
            p = self.cwd / p
        try:
            return str(p.resolve())
        except OSError:
            return str(p)

    def _on_line(self, parts: list):
        kind = parts[0] if parts else ""
        if self._pending is not None:
            if kind == "end":
                self._emit_stop(self._pending)
                self._pending = None
            else:
                self._pending.append(parts)
            return
        if self._collect is not None:
            rid, items = self._collect
            if kind == "end":
                self._collect = None
                cb = self._cbs.pop(rid, None)
                if cb:
                    cb(items)
            elif kind == "var" and len(parts) >= 5:
                items.append((parts[1], parts[2], parts[3], int(parts[4] or 0)))
            return
        if kind == "stop":
            self._pending = [parts]
        elif kind == "vars" and len(parts) >= 2:
            self._collect = (int(parts[1]), [])
        elif kind == "result" and len(parts) >= 5:
            cb = self._cbs.pop(int(parts[1]), None)
            if cb:
                cb(parts[2], parts[3], parts[4])
        elif kind == "out" and len(parts) >= 2:
            self.output.emit(parts[1] + "\n")

    def _emit_stop(self, msgs):
        from .debugger import StopInfo
        head = msgs[0]
        reason = {"breakpoint": "breakpoint", "exception": "error"}.get(head[1], "step")
        info = StopInfo(self._path(head[2]), int(head[3] or 0), reason)
        info.thread_id = 1
        for m in msgs[1:]:
            if m[0] == "frame" and len(m) >= 4:
                info.frames.append((m[1], self._path(m[2]), int(m[3] or 0)))
            elif m[0] == "var" and len(m) >= 5:
                info.variables.append((m[1], m[2], m[3]))
                if m[4] and m[4] != "0":
                    info.refs[m[1]] = int(m[4])
        self.paused = True
        self.stopped.emit(info)


# ====================================================================== React Native / Expo (web)
def find_browser() -> tuple[str, str]:
    """(js-debug type, executable) of Edge or Chrome for pwa-msedge / pwa-chrome launches."""
    cands = [("pwa-msedge", Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft" /
              "Edge" / "Application" / "msedge.exe"),
             ("pwa-msedge", Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft" / "Edge" /
              "Application" / "msedge.exe"),
             ("pwa-chrome", Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Google" / "Chrome" /
              "Application" / "chrome.exe"),
             ("pwa-chrome", Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" /
              "chrome.exe")]
    for kind, p in cands:
        if p.is_file():
            return kind, str(p)
    return "", ""


def expo_web_debug_session(url: str, folder: Path, breakpoints, parent=None, headless: bool = False):
    """A js-debug session that opens the Expo web page (``npx expo start --web``) in Edge / Chrome and stops
    at breakpoints in the project's .jsx/.js files (Metro serves source maps). Same API as DapSession."""
    from .bridgedebug import TcpAttachDap, find_jsdebug, find_node
    kind, exe = find_browser()
    if not (find_node() and find_jsdebug() and exe):
        return None
    folder = Path(folder).resolve()
    profile = Path(tempfile.gettempdir()) / f"radide-expo-debug-{os.getpid()}"
    args = {"type": kind, "request": "launch", "url": url, "webRoot": str(folder), "runtimeExecutable": exe,
            "userDataDir": str(profile), "sourceMaps": True, "resolveSourceMapLocations": None,
            "skipFiles": ["**/node_modules/**", "<node_internals>/**"],
            "pathMapping": {"/": str(folder) + os.sep}}
    if headless:
        args["runtimeArgs"] = ["--headless=new", "--disable-gpu"]

    class ExpoWebDap(TcpAttachDap):
        def _on_stopped(self, reason):              # no 'attach' stop to skip: a launched page
            self.ready = True
            super()._on_stopped(reason)

    d = ExpoWebDap([find_node(), find_jsdebug()], kind, args, folder, None, breakpoints, parent)
    d.break_on_exception = False
    return d
