"""Debugging GUI Bridge programs (C, C++, Fortran, Rust, C#, JavaScript/TypeScript, Dart).

A bridge program talks to the IDE's form host over stdin/stdout (runtimes/bridge.py), so it
cannot be *launched* by a debug adapter (gdb / netcoredbg use their own stdio for DAP). Instead:

  1. the bridge host is started with RAD_BRIDGE_DEBUG=1; it builds the program (with debug
     information), starts it with the usual pipes and prints "@@RADBRIDGE@@pid|<pid>";
  2. BridgeDebugSession attaches a Debug Adapter Protocol adapter to that process
     (gdb -i dap / netcoredbg --interpreter=vscode / js-debug dapDebugServer / dart debug_adapter),
     sends the breakpoints, and when configurationDone is answered writes "go" to the host;
  3. only then does the host send Form_Load and the other events.

Engines and where they are looked up:
    gdb         PATH, then %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64\\bin (WinLibs; needs PYTHONHOME)
    netcoredbg  PATH, then %LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg\\netcoredbg.exe
    js-debug    %LOCALAPPDATA%\\RADIDE\\tools\\js-debug\\js-debug\\src\\dapDebugServer.js (run with node)
    dart        dart debug_adapter (Dart SDK / Flutter)
Rust is built for the x86_64-pc-windows-gnu target when debugging (gdb cannot read MSVC PDBs).

BridgeDebugSession has the signals and methods of radide.debugger.Session, plus
``simulate(obj, event)`` that fires an event as if the user clicked (used by tests).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, pyqtSignal
from PyQt6.QtNetwork import QTcpSocket

from .dap import DapSession

BRIDGE_TAG = "@@RADBRIDGE@@"
EXE = ".exe" if os.name == "nt" else ""
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE"
TOOLS = LOCAL / "tools"
TOOLCHAINS = LOCAL / "toolchains"
RUST_GNU = "x86_64-pc-windows-gnu"
TRACE = bool(os.environ.get("RADIDE_DAP_TRACE"))       # print the js-debug DAP traffic to stderr

ENGINES = {
    "c-bridge": "gdb", "cpp-bridge": "gdb", "fortran-bridge": "gdb", "rust-bridge": "gdb",
    "csharp-bridge": "netcoredbg", "javascript": "jsdebug", "typescript": "jsdebug", "dart-bridge": "dart",
}


# ====================================================================== tools
def find_gdb() -> str:
    p = shutil.which("gdb")
    if p:
        return p
    for d in (TOOLCHAINS / "mingw64" / "bin", LOCAL / "w64devkit" / "bin", Path(r"C:\msys64\ucrt64\bin"),
              Path(r"C:\msys64\mingw64\bin")):
        if (d / ("gdb" + EXE)).exists():
            return str(d / ("gdb" + EXE))
    return ""


def gdb_env(gdb: str) -> dict:
    """WinLibs gdb embeds Python (needed for -i dap) but does not find its standard library alone."""
    root = Path(gdb).resolve().parent.parent
    if any(root.glob("lib/python3*/os.py")):
        return {"PYTHONHOME": str(root), "PYTHONPATH": ""}
    return {}


def find_netcoredbg() -> str:
    p = shutil.which("netcoredbg")
    if p:
        return p
    p = TOOLS / "netcoredbg" / ("netcoredbg" + EXE)
    return str(p) if p.exists() else ""


def find_jsdebug() -> str:
    for p in (TOOLS / "js-debug" / "js-debug" / "src" / "dapDebugServer.js",
              TOOLS / "js-debug" / "src" / "dapDebugServer.js"):
        if p.exists():
            return str(p)
    return ""


def find_node() -> str:
    return shutil.which("node") or next((h for h in (r"C:\Program Files\nodejs\node.exe",) if Path(h).exists()), "")


def rust_gnu_installed() -> bool:
    home = Path(os.environ.get("RUSTUP_HOME", str(Path.home() / ".rustup")))
    return any(home.glob(f"toolchains/*/lib/rustlib/{RUST_GNU}/lib"))


def mingw_gcc() -> str:
    """gcc that links Rust's x86_64-pc-windows-gnu target (PATH, then the RAD IDE toolchains)."""
    from .languages.c_bridge import find_native
    return find_native(["x86_64-w64-mingw32-gcc", "gcc"])


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


_KIND_CACHE: dict[str, tuple[float, str]] = {}


def _compiler_kind(plugin) -> str:
    """plugin.compiler_kind() looks gcc up on PATH: cached a few seconds (supports_debug is asked often)."""
    import time
    hit = _KIND_CACHE.get(plugin.id)
    if hit is None or time.monotonic() - hit[0] > 10:
        hit = (time.monotonic(), plugin.compiler_kind())
        _KIND_CACHE[plugin.id] = hit
    return hit[1]


def engine_for(plugin) -> str | None:
    """Debug engine of a bridge language (None = no debugger for it)."""
    eng = ENGINES.get(getattr(plugin, "id", ""))
    if eng == "gdb" and hasattr(plugin, "compiler_kind") and _compiler_kind(plugin) == "msvc":
        return None                      # cl.exe builds: PDB debug info, not readable by gdb
    return eng


def missing(engine: str, plugin=None) -> str:
    """Why *engine* cannot run here ('' = ready)."""
    if engine == "gdb":
        if not find_gdb():
            return ("gdb was not found (install WinLibs into %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64, "
                    "or MSYS2: pacman -S mingw-w64-ucrt-x86_64-gdb)")
        if plugin is not None and plugin.id == "rust-bridge" and os.name == "nt" and not rust_gnu_installed():
            return f"debugging Rust needs the GNU target: run  rustup target add {RUST_GNU}"
        if plugin is not None and plugin.id == "rust-bridge" and os.name == "nt" and not mingw_gcc():
            return "debugging Rust needs a MinGW gcc (WinLibs) to link the GNU target"
        return ""
    if engine == "netcoredbg":
        return "" if find_netcoredbg() else ("netcoredbg was not found (download netcoredbg-win64.zip from "
                                            "github.com/Samsung/netcoredbg into %LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg)")
    if engine == "jsdebug":
        if not find_node():
            return "Node.js was not found"
        return "" if find_jsdebug() else ("js-debug was not found (download js-debug-dap-*.tar.gz from "
                                         "github.com/microsoft/vscode-js-debug into %LOCALAPPDATA%\\RADIDE\\tools\\js-debug)")
    if engine == "dart":
        return "" if shutil.which("dart") else "the Dart SDK (dart) was not found"
    return f"no debugger for {engine}"


# ====================================================================== run spec changes
def _debug_build(build: str, plugin) -> str:
    if plugin.id == "rust-bridge":
        return build + f" --target {RUST_GNU}" if os.name == "nt" else build
    if ENGINES.get(plugin.id) == "gdb":          # gcc / g++ / gfortran: debug info, no optimisation
        out, n = re.subn(r"(?<=\s)-O[0-3sg]?(?=\s)", "-g -O0", build)
        return out if n else build.replace(" -o ", " -g -O0 -o ", 1)
    return build


def _debug_run(cmd: list[str], plugin, port: int) -> list[str]:
    cmd = list(cmd)
    if plugin.id == "rust-bridge" and os.name == "nt" and cmd:
        exe = Path(cmd[0])
        cmd[0] = str(exe.parent.parent / RUST_GNU / exe.parent.name / exe.name)     # _build/<target>/debug/radapp.exe
    elif ENGINES.get(plugin.id) == "jsdebug" and cmd:
        cmd.insert(1, f"--inspect-brk=127.0.0.1:{port}")      # paused at start: the program blocks in readSync later
    elif plugin.id == "dart-bridge" and cmd:
        cmd[1:1] = [f"--enable-vm-service={port}/127.0.0.1", "--disable-service-auth-codes"]
    return cmd


def debug_spec(spec, plugin, port: int):
    """The bridge run spec, changed to build with debug information and run debuggable."""
    args = list(spec.args)
    if "--build" in args:
        i = args.index("--build") + 1
        args[i] = _debug_build(args[i], plugin)
    if "--" in args:
        i = args.index("--") + 1
        args[i:] = _debug_run(args[i:], plugin, port)
    spec.args = args
    env = dict(spec.env if spec.env is not None else os.environ)
    env["RAD_BRIDGE_DEBUG"] = "1"
    if plugin.id == "rust-bridge" and os.name == "nt":
        # an MSVC-host rustup cross-links the GNU target with x86_64-w64-mingw32-gcc (WinLibs has it)
        gcc = mingw_gcc()
        if gcc:
            env.setdefault("CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER", gcc)
            env["PATH"] = str(Path(gcc).parent) + os.pathsep + env.get("PATH", "")
    spec.env = env
    return spec


# ====================================================================== DAP sessions that attach
class AttachDap(DapSession):
    """DapSession that sends 'attach' (arguments ready-made) and tells when configuration is done."""
    configured = pyqtSignal()

    def __init__(self, argv, adapter_id, attach_args, cwd, env, breakpoints, parent=None):
        super().__init__("gdb", "", [], cwd, env, breakpoints, parent)
        self.argv = argv
        self.adapter = adapter_id
        self.launch_args = attach_args
        self.ready = False

    def _on_initialize(self, body, _msg):
        self._request(self.launch_args.get("request", "attach"), self.launch_args)

    def _dispatch(self, msg):
        if msg.get("type") == "event" and msg.get("event") == "output" \
                and (msg.get("body") or {}).get("category") in ("stdout", "stderr"):
            return          # the program's own output already comes through the bridge pipe (dart/js mirror it)
        super()._dispatch(msg)

    def _request(self, command, arguments=None, cb=None):
        if command == "configurationDone":
            orig = cb

            def cb(b, m, orig=orig):
                self._configured()
                if orig:
                    orig(b, m)
        super()._request(command, arguments, cb)

    def _configured(self):
        if not self.ready:
            self.ready = True
            self.configured.emit()

    def evaluate(self, expr: str):
        """gdb: the 'repl' context runs gdb commands - expressions use 'watch' ('-exec <cmd>' = command)."""
        if self.adapter != "gdb" or not self.paused:
            return super().evaluate(expr)
        ctx = "watch"
        if expr.startswith("-exec "):
            expr, ctx = expr[6:], "repl"
        self._request("evaluate", {"expression": expr, "frameId": self.frame_id, "context": ctx},
                      lambda b, m: self.evalResult.emit(b.get("result", "") if m.get("success", True)
                                                        else m.get("message", "error")))

    def _on_stopped(self, reason):
        if not self.ready or reason in ("entry", "attach"):        # the stop that attaching causes
            self._request("continue", {"threadId": self.thread_id})
            return
        super()._on_stopped(reason)


class TcpAttachDap(AttachDap):
    """js-debug's dapDebugServer: DAP over TCP; the real target is a child session that the
    server asks for with the 'startDebugging' reverse request (one more connection)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.port = free_port()
        self.argv = self.argv + [str(self.port), "127.0.0.1"]
        self.sock: QTcpSocket | None = None
        self._in_sock: QTcpSocket | None = None
        self._bufs: dict[int, bytes] = {}
        self._socks: list[QTcpSocket] = []
        self._log = b""

    def start(self):
        if not self.argv or not self.argv[0]:
            self.failed.emit("js-debug is not installed")
            self.finished.emit(1)
            return
        self.proc.start(self.argv[0], self.argv[1:])

    def _read(self):                                    # adapter stdout: wait for "listening"
        self._log += bytes(self.proc.readAllStandardOutput())
        if self.sock is None and b"listening" in self._log.lower():
            self.sock = self._connect(self._parent_connected)

    def _connect(self, on_connected) -> QTcpSocket:
        s = QTcpSocket(self)
        self._socks.append(s)
        self._bufs[id(s)] = b""
        s.readyRead.connect(lambda s=s: self._sock_read(s))
        s.connected.connect(lambda s=s: on_connected(s))
        s.connectToHost("127.0.0.1", self.port)
        return s

    def _initialize(self, s):
        self._in_sock = s
        try:
            super()._request("initialize", {"clientID": "radide", "adapterID": "pwa-node", "linesStartAt1": True,
                                            "columnsStartAt1": True, "pathFormat": "path",
                                            "supportsRunInTerminalRequest": False,
                                            "supportsStartDebuggingRequest": True, "supportsVariableType": True},
                                           self._on_initialize)
        finally:
            self._in_sock = None

    def _parent_connected(self, s):
        self._initialize(s)

    def _send(self, msg):
        s = self._in_sock or self.sock
        if s is None:
            return
        body = json.dumps(msg).encode("utf-8")
        if TRACE:
            print("DAP>>", self._socks.index(s), body[:300], file=sys.stderr, flush=True)
        s.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

    def _sock_read(self, s):
        buf = self._bufs[id(s)] + bytes(s.readAll())
        while True:
            end = buf.find(b"\r\n\r\n")
            if end < 0:
                break
            length = 0
            for line in buf[:end].split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
            if len(buf) < end + 4 + length:
                break
            body, buf = buf[end + 4:end + 4 + length], buf[end + 4 + length:]
            try:
                msg = json.loads(body)
            except ValueError:
                continue
            if TRACE:
                print("DAP<<", self._socks.index(s), body[:300], file=sys.stderr, flush=True)
            self._bufs[id(s)] = buf
            self._in_sock = s
            try:
                if msg.get("type") == "request" and msg.get("command") == "startDebugging":
                    self._send({"seq": 0, "type": "response", "request_seq": msg["seq"], "success": True,
                                "command": "startDebugging"})
                    cfg = (msg.get("arguments") or {}).get("configuration", {})
                    self.launch_args = dict(cfg, request=(msg.get("arguments") or {}).get("request", "attach"))
                    self.sock = self._connect(self._initialize)      # the child becomes the active connection
                else:
                    self._dispatch(msg)
            finally:
                self._in_sock = None
        self._bufs[id(s)] = buf

    def _request(self, command, arguments=None, cb=None):
        if command == "configurationDone" and (self._in_sock is None or self._in_sock is self._socks[0]):
            # the parent session's configuration does not run the program: wait for the child's
            super(AttachDap, self)._request(command, arguments, cb)
            return
        super()._request(command, arguments, cb)

    def stop(self):
        if self.running():
            self.user_stopped = True
            if self.sock is not None:
                super(AttachDap, self)._request("disconnect", {"terminateDebuggee": True})
                self.sock.flush()
            if not self.proc.waitForFinished(700):
                self.proc.kill()
                self.proc.waitForFinished(1000)


# ====================================================================== the session
class BridgeDebugSession(QObject):
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)      # StopInfo
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, spec, plugin, breakpoints, parent=None, break_on_exception: bool = False):
        super().__init__(parent)
        self.debug = True
        self.user_stopped = False
        self.plugin = plugin
        self.engine = engine_for(plugin)
        self.port = free_port()
        self._why = missing(self.engine or "", plugin)
        # no adapter here: run the program normally (a --inspect-brk node would wait forever)
        self.spec = spec if self._why else debug_spec(spec, plugin, self.port)
        self.cwd = Path(spec.cwd).resolve()
        self.breakpoints = list(breakpoints)
        self.break_on_exception = break_on_exception
        self.dap: AttachDap | None = None
        self.pid = 0
        self._go_sent = False
        self._buf = ""
        self.host = QProcess(self)
        self.host.setWorkingDirectory(str(spec.cwd))
        env = QProcessEnvironment()
        for k, v in (self.spec.env or os.environ).items():
            env.insert(k, v)
        self.host.setProcessEnvironment(env)
        self.host.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.host.readyReadStandardOutput.connect(self._read_host)
        self.host.finished.connect(self._host_finished)

    # ------------------------------------------------------------ Session API
    @property
    def paused(self) -> bool:
        return bool(self.dap is not None and self.dap.paused)

    @paused.setter
    def paused(self, value):
        if self.dap is not None:
            self.dap.paused = value

    def start(self):
        if self._why:
            self.output.emit(f"[debugger] {self._why} - running without the debugger\n")
        self._no_debugger = bool(self._why)
        self.host.start(self.spec.program, self.spec.args)

    def running(self) -> bool:
        return self.host.state() != QProcess.ProcessState.NotRunning

    def cont(self):
        if self.dap:
            self.dap.cont()

    def step_into(self):
        if self.dap:
            self.dap.step_into()

    def step_over(self):
        if self.dap:
            self.dap.step_over()

    def step_out(self):
        if self.dap:
            self.dap.step_out()

    def evaluate(self, expr: str):
        if self.dap:
            self.dap.evaluate(expr)
        else:
            self.evalResult.emit("(the debugger is not attached)")

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = ""):
        if self.dap:
            self.dap.set_breakpoint(filename, line, on, cond)

    def set_break_on_exception(self, on: bool):
        self.break_on_exception = on
        if self.dap:
            self.dap.set_break_on_exception(on)

    def simulate(self, obj: str, event: str = "Click"):
        """Fire *event* of control *obj* as if the user did it (the host runs the handler)."""
        if self.running():
            self.host.write(f"EVENT {obj} {event}\n".encode("utf-8"))

    def stop(self):
        self.user_stopped = True
        if self.dap is not None:
            try:
                self.dap.stop()
            except RuntimeError:
                pass
        if self.running():
            self.host.kill()
            self.host.waitForFinished(2000)

    # ------------------------------------------------------------ host
    def _read_host(self):
        self._buf += bytes(self.host.readAllStandardOutput()).decode("utf-8", "replace")
        while True:
            i = self._buf.find("\n")
            if i < 0:
                if self._buf and BRIDGE_TAG[:len(self._buf)] != self._buf[:len(BRIDGE_TAG)] \
                        and BRIDGE_TAG not in self._buf:
                    self.output.emit(self._buf)
                    self._buf = ""
                return
            line, self._buf = self._buf[:i + 1], self._buf[i + 1:]
            if line.startswith(BRIDGE_TAG):
                kind, _, rest = line[len(BRIDGE_TAG):].strip().partition("|")
                if kind == "pid":
                    self.pid = int(rest)
                    self._attach()
                continue
            if line.startswith(("Debugger listening on ws://", "Debugger ending on ws://", "For help, see: https://nodejs",
                                "Waiting for the debugger to disconnect")) \
                    or line.strip() == "Debugger attached.":
                continue                        # node --inspect chatter
            self.output.emit(line)

    def _go(self):
        if not self._go_sent and self.running():
            self._go_sent = True
            self.host.write(b"go\n")

    def _host_finished(self, code, _status):
        if self._buf:
            self.output.emit(self._buf)
            self._buf = ""
        if self.dap is not None and self.dap.running():
            self.dap.user_stopped = True
            QTimer.singleShot(0, self._stop_dap)
        self.finished.emit(code)

    def _stop_dap(self):
        if self.dap is not None and self.dap.running():
            self.dap.stop()

    # ------------------------------------------------------------ attach
    def _attach(self):
        if self._no_debugger:
            self._go()
            return
        if self.engine in ("jsdebug", "dart"):
            self._wait_port(self.port, 100, self._make_dap)     # the program opens its debug port
        else:
            self._make_dap()

    def _wait_port(self, port, tries, then):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                pass
            then()
        except OSError:
            if tries <= 0 or not self.running():
                self.output.emit("[debugger] the program did not open its debug port - running without the debugger\n")
                self._go()
                return
            QTimer.singleShot(150, lambda: self._wait_port(port, tries - 1, then))

    def _make_dap(self):
        cwd, bps = self.cwd, self.breakpoints
        eng = self.engine
        if eng == "gdb":
            gdb = find_gdb()
            exe = self._program_path()
            args = {"pid": self.pid}
            if exe:
                args["program"] = exe
            d = AttachDap([gdb, "-i", "dap"], "gdb", args, cwd, gdb_env(gdb), bps, self)
        elif eng == "netcoredbg":
            d = AttachDap([find_netcoredbg(), "--interpreter=vscode"], "coreclr",
                          {"type": "coreclr", "request": "attach", "processId": self.pid, "justMyCode": True},
                          cwd, None, bps, self)
        elif eng == "jsdebug":
            d = TcpAttachDap([find_node(), find_jsdebug()], "pwa-node",
                             {"type": "pwa-node", "request": "attach", "address": "127.0.0.1", "port": self.port,
                              "cwd": str(cwd), "continueOnAttach": True, "skipFiles": ["<node_internals>/**"]},
                             cwd, None, bps, self)
        else:                                   # dart
            d = AttachDap([shutil.which("dart") or "dart", "debug_adapter"], "dart",
                          {"request": "attach", "vmServiceUri": f"http://127.0.0.1:{self.port}/", "cwd": str(cwd)},
                          cwd, None, bps, self)
        d.break_on_exception = self.break_on_exception
        self.dap = d
        d.configured.connect(self._go)
        d.output.connect(self._dap_output)
        d.stopped.connect(self._on_stopped)
        d.resumed.connect(self.resumed)
        d.evalResult.connect(self.evalResult)
        d.failed.connect(self._dap_failed)
        d.finished.connect(lambda _c: self._go())       # adapter gone: let the program run anyway
        QTimer.singleShot(30000, self._attach_timeout)
        d.start()

    def _attach_timeout(self):
        if not self._go_sent and self.running():
            self.output.emit("[debugger] attaching took too long - the program runs without breakpoints\n")
            self._go()

    def _program_path(self) -> str:
        if "--" in self.spec.args:
            p = self.spec.args[self.spec.args.index("--") + 1]
            if Path(p).suffix.lower() == EXE or Path(p).exists():
                return str(Path(p).resolve())
        return ""

    def _dap_output(self, text: str):
        if self.engine == "gdb" and (not self._go_sent or re.match(r"\[(New )?Thread |\[Inferior ", text)):
            return                              # gdb banner / "Attaching to process ..." / thread noise
        if self.engine == "jsdebug" and text.startswith(("Debugger attached", "Waiting for the debugger")):
            return
        self.output.emit(text if text.startswith("[") else f"[debugger] {text}")

    def _dap_failed(self, msg: str):
        if self.user_stopped:
            return
        self.failed.emit(f"debugger: {msg}")
        self._go()

    def _on_stopped(self, info):
        info.variables = [v for v in info.variables
                          if not v[0].lower().startswith(("registers.", "register.", "globals.", "global."))]
        info.frames = [(f[:-2] if f.endswith("()") else f, p, n) for f, p, n in info.frames]     # netcoredbg: "F()"
        self.stopped.emit(info)
