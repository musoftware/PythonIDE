"""Runs a program (optionally under a debug agent) and parses the RAD IDE
debug protocol (see languages/base.py)."""
from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from .languages import RunSpec

TAG = "@@RADDBG@@"


@dataclass
class StopInfo:
    file: str
    line: int                 # 1-based
    reason: str
    variables: list[tuple[str, str, str]] = field(default_factory=list)   # name, type, value
    frames: list[tuple[str, str, int]] = field(default_factory=list)      # func, file, line
    refs: dict = field(default_factory=dict)      # variable name -> child handle (expandable in Locals)
    thread_id: int = 0


def _unescape(s: str) -> str:
    return s.replace("\\n", "\n").replace("¦", "|")


class Session(QObject):
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)      # StopInfo
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, spec: RunSpec, debug: bool, parent=None):
        super().__init__(parent)
        self.debug = debug
        self.paused = False
        self._buf = ""
        self._pending: StopInfo | None = None
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(spec.cwd))
        if spec.env:
            env = QProcessEnvironment()
            for k, v in spec.env.items():
                env.insert(k, v)
            self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._on_finished)
        self.proc.errorOccurred.connect(self._on_error)
        self.user_stopped = False
        self._spec = spec
        self._kid_cbs: list = []          # children() callbacks waiting for "kend"
        self._kids: list = []
        self._watch_cbs: list = []        # watch() callbacks waiting for "watch"
        self.caps: set[str] = set()       # agent capabilities ("caps|children|bpx" at each stop)

    # ------------------------------------------------------------ expandable values (debug_extras)
    def children(self, ref, cb) -> None:
        """cb([(name, type, value, child_ref or 0)]) for handle *ref* (agent command 'k <ref>')."""
        if not self.paused or not self.running():
            cb([])
            return
        self._kid_cbs.append(cb)
        self.send(f"k {ref}")

    def watch(self, expr: str, cb) -> None:
        """cb(value, type, ref) for a Watch expression (agent command 'w <expr>')."""
        if not self.paused or not self.running():
            cb("(the program must be paused at a breakpoint)", "", 0)
            return
        if "children" not in self.caps:          # older agents: plain evaluate (radide/tools.py routes it)
            cb(None, "", 0)
            return
        self._watch_cbs.append(cb)
        self.send("w " + expr)

    def threads(self, cb) -> None:
        cb([(1, "Main Thread")])

    def select_thread(self, tid) -> None:
        pass

    def start(self) -> None:
        self.proc.start(self._spec.program, self._spec.args)

    def running(self) -> bool:
        return self.proc.state() != QProcess.ProcessState.NotRunning

    # ------------------------------------------------------------ commands
    def send(self, cmd: str) -> None:
        if self.running():
            self.proc.write((cmd + "\n").encode("utf-8"))

    def _resume(self, cmd: str) -> None:
        if self.paused:
            self.paused = False
            self.send(cmd)
            self.resumed.emit()

    def cont(self):
        self._resume("c")

    def step_into(self):
        self._resume("s")

    def step_over(self):
        self._resume("n")

    def step_out(self):
        self._resume("o")

    def evaluate(self, expr: str) -> None:
        if self.paused:
            self.send("e " + expr)
        else:
            self.evalResult.emit("(the program must be paused at a breakpoint)")

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = "") -> None:
        if self.debug:
            if cond.startswith("@@bp ") and "bpx" not in self.caps:
                from .debug_extras import parse_bp
                cond = parse_bp(cond)["cond"]
            self.send(f"{'b' if on else 'B'} {filename.lower()}|{line}" + (f"|{cond}" if on and cond else ""))

    def set_break_on_exception(self, on: bool) -> None:
        if self.debug:
            self.send(f"x {'on' if on else 'off'}")

    def _on_error(self, err) -> None:
        if self.user_stopped and err == QProcess.ProcessError.Crashed:
            return                       # killed by Stop: not a real crash
        self.failed.emit({"FailedToStart": "the interpreter could not be started",
                          "Crashed": "the program crashed"}.get(err.name, err.name))

    def stop(self) -> None:
        if self.running():
            self.user_stopped = True
            if self.debug:
                self.send("q")
            self.proc.kill()
            # finish now (emits finished): F5 right after Stop must not race with this session's end
            self.proc.waitForFinished(3000)

    # ------------------------------------------------------------ parsing
    def _read(self) -> None:
        self._buf += bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not self.debug:
            self.output.emit(self._buf)
            self._buf = ""
            return
        while True:
            i = self._buf.find("\n")
            if i < 0:
                # flush plain text that cannot be the start of a protocol line
                if self._buf and not TAG.startswith(self._buf[:len(TAG)]) and TAG not in self._buf:
                    self.output.emit(self._buf)
                    self._buf = ""
                return
            line, self._buf = self._buf[:i + 1], self._buf[i + 1:]
            pos = line.find(TAG)
            if pos < 0:
                self.output.emit(line)
                continue
            if pos > 0:
                self.output.emit(line[:pos])
            self._handle(line[pos + len(TAG):].rstrip("\r\n"))

    def _handle(self, msg: str) -> None:
        kind, _, rest = msg.partition("|")
        parts = [_unescape(p) for p in rest.split("|")] if rest else []
        if kind == "stop" and len(parts) >= 3:
            self._pending = StopInfo(parts[0], int(parts[1]), parts[2])
        elif kind == "var" and self._pending and len(parts) >= 3:
            self._pending.variables.append((parts[0], parts[1], "|".join(parts[2:])))
        elif kind == "frame" and self._pending and len(parts) >= 3:
            self._pending.frames.append((parts[0], parts[1], int(parts[2])))
        elif kind == "caps":
            self.caps.update(parts)
        elif kind == "ref" and self._pending and len(parts) >= 2:
            self._pending.refs[parts[0]] = parts[1]
        elif kind == "kid" and len(parts) >= 4:
            self._kids.append((parts[0], parts[1], parts[2], parts[3] if parts[3] not in ("", "0") else 0))
        elif kind == "kend":
            kids, self._kids = self._kids, []
            if self._kid_cbs:
                self._kid_cbs.pop(0)(kids)
        elif kind == "watch" and len(parts) >= 3:
            if self._watch_cbs:
                self._watch_cbs.pop(0)("|".join(parts[2:]), parts[0], parts[1] if parts[1] not in ("", "0") else 0)
        elif kind == "wait":
            self.paused = True
            if self._pending is not None:
                info, self._pending = self._pending, None
                self.stopped.emit(info)
        elif kind == "eval":
            self.evalResult.emit("|".join(parts))
        elif kind == "log":
            self.output.emit("[debugger] " + "|".join(parts) + "\n")

    def _on_finished(self, code, _status) -> None:
        if self._buf:
            self.output.emit(self._buf)
            self._buf = ""
        self.paused = False
        self.finished.emit(code)
