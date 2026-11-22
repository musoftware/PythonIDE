"""Java debugger for java-bridge programs: a small JDWP client (no jdb, no extra download).

The bridge host starts ``java -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:<port>``
(radide/bridgedebug.py); JdwpSession connects to that port, waits for the classes of the files with
breakpoints to load (ClassPrepare), sets the breakpoints from the method line tables and resumes the VM.

It has the AttachDap interface used by BridgeDebugSession (signals configured / output / stopped /
resumed / evalResult / failed / finished; start, cont, step_*, evaluate, set_breakpoint, stop) plus the
debug_extras API: children(ref, cb), watch(expr, cb), threads(cb), select_thread(tid).

Conditions, hit counts and logpoints are checked here (the VM only reports the hits). Expressions
(conditions, logpoints, Watch, Immediate) support variables, fields (a.b.c, this.x), array items
(a[i]), .length, literals, arithmetic, comparisons, ! && || - not method calls.

All socket work happens on one worker thread; results reach the Qt thread through a queued signal.
"""
from __future__ import annotations

import queue
import re
import socket
import struct
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from .debug_extras import format_log, hit_ok, parse_bp
from .debugger import StopInfo

# event kinds
SINGLE_STEP, BREAKPOINT, EXCEPTION, THREAD_START, CLASS_PREPARE, VM_START, VM_DEATH = 1, 2, 4, 6, 8, 90, 99
SUSPEND_NONE, SUSPEND_THREAD, SUSPEND_ALL = 0, 1, 2
STEP_EXCLUDES = ["java.*", "javax.*", "sun.*", "jdk.*", "com.sun.*"]
PRIMS = {"B": "byte", "C": "char", "D": "double", "F": "float", "I": "int", "J": "long", "S": "short",
         "Z": "boolean", "V": "void"}
BOXED = {"java.lang.Integer", "java.lang.Long", "java.lang.Double", "java.lang.Float", "java.lang.Short",
         "java.lang.Byte", "java.lang.Character", "java.lang.Boolean"}


class JdwpError(Exception):
    pass


class Obj:
    """A reference value (tag 'L', 's', '[' ...) of the debuggee."""
    __slots__ = ("tag", "id")

    def __init__(self, tag, oid):
        self.tag, self.id = tag, oid


def sig_name(sig: str) -> str:
    """'Ljava/lang/String;' -> 'java.lang.String', '[I' -> 'int[]'."""
    dims = len(sig) - len(sig.lstrip("["))
    s = sig[dims:]
    name = PRIMS.get(s, s[1:-1].replace("/", ".") if s.startswith("L") else s)
    return name + "[]" * dims


def short_name(sig: str) -> str:
    return re.sub(r"\b[\w$]+\.", "", sig_name(sig))


# ====================================================================== wire protocol
class Wire:
    """Blocking JDWP connection: requests from one thread, a reader thread for replies/events."""

    def __init__(self, sock, on_event, on_close):
        self.sock = sock
        self.on_event, self.on_close = on_event, on_close
        self._id = 0
        self._lock = threading.Lock()
        self._waits: dict[int, list] = {}
        self.sizes = dict(field=8, method=8, object=8, ref=8, frame=8)
        threading.Thread(target=self._reader, daemon=True).start()

    def _recv(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise OSError("closed")
            buf += chunk
        return buf

    def _reader(self):
        try:
            while True:
                length, pid, flags = struct.unpack(">IIB", self._recv(9))
                rest = self._recv(length - 9)
                if flags & 0x80:
                    err = struct.unpack(">H", rest[:2])[0]
                    w = self._waits.get(pid)
                    if w is not None:
                        w[1], w[2] = err, rest[2:]
                        w[0].set()
                elif rest[:2] == b"\x40\x64":                      # Event.Composite
                    self.on_event(rest[2:])
        except OSError:
            pass
        for w in list(self._waits.values()):
            w[1] = -1
            w[0].set()
        self.on_close()

    def request(self, cmdset, cmd, data=b"", timeout=15.0) -> bytes:
        with self._lock:
            self._id += 1
            pid = self._id
            w = [threading.Event(), None, b""]
            self._waits[pid] = w
            self.sock.sendall(struct.pack(">IIBBB", 11 + len(data), pid, 0, cmdset, cmd) + data)
        if not w[0].wait(timeout):
            self._waits.pop(pid, None)
            raise JdwpError("the Java VM did not answer")
        self._waits.pop(pid, None)
        if w[1] == -1:
            raise JdwpError("the Java VM closed the connection")
        if w[1]:
            raise JdwpError(f"JDWP error {w[1]}")
        return w[2]

    # ---- encoding
    def id(self, kind, value) -> bytes:
        return value.to_bytes(self.sizes[kind], "big")

    @staticmethod
    def string(s) -> bytes:
        b = s.encode("utf-8")
        return struct.pack(">I", len(b)) + b


class Reader:
    def __init__(self, wire, data):
        self.w, self.d, self.p = wire, data, 0

    def take(self, n):
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def byte(self):
        return self.take(1)[0]

    def int(self):
        return struct.unpack(">i", self.take(4))[0]

    def long(self):
        return struct.unpack(">q", self.take(8))[0]

    def id(self, kind="object"):
        return int.from_bytes(self.take(self.w.sizes[kind]), "big")

    def string(self):
        return self.take(self.int()).decode("utf-8", "replace")

    def location(self):
        return (self.byte(), self.id("ref"), self.id("method"), self.long())

    def value(self, tag=None):
        tag = chr(self.byte()) if tag is None else tag
        if tag == "B":
            return struct.unpack(">b", self.take(1))[0]
        if tag == "Z":
            return bool(self.byte())
        if tag == "C":
            return chr(struct.unpack(">H", self.take(2))[0])
        if tag == "S":
            return struct.unpack(">h", self.take(2))[0]
        if tag == "I":
            return self.int()
        if tag == "J":
            return self.long()
        if tag == "F":
            return struct.unpack(">f", self.take(4))[0]
        if tag == "D":
            return struct.unpack(">d", self.take(8))[0]
        if tag == "V":
            return None
        oid = self.id("object")
        return Obj(tag, oid) if oid else None


# ====================================================================== the session
class JdwpSession(QObject):
    configured = pyqtSignal()
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)
    _call = pyqtSignal(object)

    def __init__(self, port: int, cwd, breakpoints, parent=None):
        super().__init__(parent)
        self.adapter = "jdwp"
        self.port = port
        self.cwd = Path(cwd).resolve()
        self.paused = False
        self.ready = False
        self.user_stopped = False
        self.break_on_exception = False
        # GUI Bridge: the generated RadMain catches every handler's Throwable, so "uncaught" never fires - also ask
        # for caught exceptions and stop only for those thrown in the program's own source files
        self.break_on_caught_user = False
        self.wire: Wire | None = None
        self.bps: dict[str, dict[int, str]] = {}          # file basename (lower) -> {line: condition string}
        for bp in breakpoints:
            self.bps.setdefault(Path(bp[0]).name.lower(), {})[int(bp[1])] = bp[2] if len(bp) > 2 else ""
        self.hits: dict[tuple, int] = {}
        self._jobs: queue.Queue = queue.Queue()
        self._alive = False
        self._closed = False
        # (file, line) -> {class id: breakpoint request id}: a source file can have several loaded classes with
        # that line (a breakpoint re-added while running must go to every one, not only the first found)
        self._req_ids: dict[tuple, dict] = {}
        self._bp_of_req: dict[int, tuple] = {}
        self._classes: dict[str, list[int]] = {}           # source file (lower) -> loaded class ids
        self._step_req = 0
        self._exc_req = 0
        self._thread = 0
        self._frames: list = []                            # [(frameID, location)] of the shown thread
        self.frame_id = 0
        self.handles: dict[int, Obj] = {}
        self._cache: dict = {}
        self._call.connect(self._run_call, Qt.ConnectionType.QueuedConnection)

    # ------------------------------------------------------------ Qt-thread helpers
    @pyqtSlot(object)
    def _run_call(self, fn):
        fn()

    def _post(self, fn):
        self._call.emit(fn)

    def _emit(self, signal, *args):
        self._post(lambda: signal.emit(*args))

    def _job(self, fn):
        """Run fn() on the worker thread (all JDWP traffic goes there)."""
        if self._alive:
            self._jobs.put(fn)

    def running(self) -> bool:
        return self._alive

    # ------------------------------------------------------------ start / connect
    def start(self):
        self._alive = True
        threading.Thread(target=self._worker, daemon=True).start()

    def _connect(self):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and self._alive:
            try:
                s = socket.create_connection(("127.0.0.1", self.port), timeout=2)
                s.sendall(b"JDWP-Handshake")
                got = b""
                while len(got) < 14:
                    chunk = s.recv(14 - len(got))
                    if not chunk:
                        break
                    got += chunk
                if got == b"JDWP-Handshake":
                    s.settimeout(None)
                    return s
                s.close()
            except OSError:
                pass
            time.sleep(0.15)
        return None

    def _worker(self):
        try:
            s = self._connect()
            if s is None:
                raise JdwpError("could not connect to the Java VM (JDWP) - is the JDK's java used?")
            self.wire = Wire(s, lambda data: self._jobs.put(("event", data)), self._on_close)
            r = Reader(self.wire, self.wire.request(1, 7))                      # IDSizes
            f, m, o, t, fr = (r.int() for _ in range(5))
            self.wire.sizes = dict(field=f, method=m, object=o, ref=t, frame=fr)
            for name in self.bps:
                self._watch_class_loads(name)
            if self.break_on_exception:
                self._set_exception_request(True)
            self.wire.request(1, 9)                                            # VirtualMachine.Resume
            self.ready = True
            self._emit(self.configured)
        except Exception as e:  # noqa: BLE001
            self._fail(str(e))
            return
        while self._alive:
            job = self._jobs.get()
            if job is None:
                break
            try:
                if isinstance(job, tuple) and job[0] == "event":
                    self._on_events(job[1])
                else:
                    job()
            except JdwpError as e:
                if self._alive and not self.user_stopped:
                    self._emit(self.output, f"[debugger] {e}\n")
            except Exception as e:  # noqa: BLE001
                self._emit(self.output, f"[debugger] internal error: {type(e).__name__}: {e}\n")

    def _fail(self, msg):
        self._alive = False
        if not self.user_stopped:
            self._emit(self.failed, msg)
        self._emit(self.finished, 1)

    def _on_close(self):
        if self._closed:
            return
        self._closed = True
        self._alive = False
        self._jobs.put(None)

        def done():
            self.paused = False
            self.finished.emit(0)
        self._post(done)

    # ------------------------------------------------------------ class loading / breakpoints
    def _source_classes(self, name: str) -> list[str]:
        """Class names declared in source file *name* (patterns for ClassPrepare)."""
        path = next((p for p in self.cwd.glob("**/*.java") if p.name.lower() == name), None)
        names = {Path(name).stem}
        if path is not None:
            try:
                names |= set(re.findall(r"\b(?:class|interface|enum|record)\s+([A-Za-z_$][\w$]*)",
                                        path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                pass
        return sorted(names)

    def _watch_class_loads(self, name: str):
        w = self.wire
        for cls in self._source_classes(name):
            for pat in (cls, cls + "$*", "*." + cls, "*." + cls + "$*"):
                data = bytes([CLASS_PREPARE, SUSPEND_THREAD]) + struct.pack(">i", 1) + b"\x05" + w.string(pat)
                w.request(15, 1, data)
        # classes that are already loaded (a breakpoint added while running)
        for cid in self._classes.get(name, []):
            self._install_bps(cid, name)

    def _on_class_prepare(self, cid):
        src = self._source_file(cid).lower()
        if not src:
            return
        ids = self._classes.setdefault(src, [])
        if cid not in ids:
            ids.append(cid)
        if src in self.bps:
            self._install_bps(cid, src)

    def _install_bps(self, cid, name):
        for line, _cond in self.bps.get(name, {}).items():
            key = (name, line)
            if cid in self._req_ids.get(key, {}):
                continue
            loc = self._location_for_line(cid, line)
            if loc is None:
                continue
            w = self.wire
            data = bytes([BREAKPOINT, SUSPEND_ALL]) + struct.pack(">i", 1) + b"\x07" + self._enc_location(loc)
            rid = struct.unpack(">i", w.request(15, 1, data)[:4])[0]
            self._req_ids.setdefault(key, {})[cid] = rid
            self._bp_of_req[rid] = key

    def _clear_bp(self, key):
        for rid in self._req_ids.pop(key, {}).values():
            self._bp_of_req.pop(rid, None)
            self.wire.request(15, 2, bytes([BREAKPOINT]) + struct.pack(">i", rid))

    def _set_exception_request(self, on):
        w = self.wire
        if self._exc_req:
            w.request(15, 2, bytes([EXCEPTION]) + struct.pack(">i", self._exc_req))
            self._exc_req = 0
        if on:
            caught = b"\x01" if self.break_on_caught_user else b"\x00"
            mods = b"\x08" + w.id("ref", 0) + caught + b"\x01"           # ExceptionOnly (any type)
            excl = ("java.*", "javax.*", "sun.*", "jdk.*", "com.sun.*") if self.break_on_caught_user else ()
            for pat in excl:                     # ClassExclude: exceptions the JDK throws and catches itself
                mods += b"\x06" + w.string(pat)
            data = bytes([EXCEPTION, SUSPEND_ALL]) + struct.pack(">i", 1 + len(excl)) + mods
            self._exc_req = struct.unpack(">i", w.request(15, 1, data)[:4])[0]

    # ------------------------------------------------------------ type information (cached)
    def _cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def _signature(self, cid) -> str:
        return self._cached(("sig", cid), lambda: Reader(self.wire, self.wire.request(2, 1, self.wire.id("ref", cid))).string())

    def _source_file(self, cid) -> str:
        def get():
            try:
                return Reader(self.wire, self.wire.request(2, 7, self.wire.id("ref", cid))).string()
            except JdwpError:
                return ""
        return self._cached(("src", cid), get)

    def _methods(self, cid) -> dict:
        def get():
            r = Reader(self.wire, self.wire.request(2, 5, self.wire.id("ref", cid)))
            out = {}
            for _ in range(r.int()):
                mid, name, sig = r.id("method"), r.string(), r.string()
                r.int()
                out[mid] = (name, sig)
            return out
        return self._cached(("methods", cid), get)

    def _line_table(self, cid, mid) -> list[tuple[int, int]]:
        def get():
            try:
                r = Reader(self.wire, self.wire.request(6, 1, self.wire.id("ref", cid) + self.wire.id("method", mid)))
            except JdwpError:
                return []                        # native / abstract
            r.long(), r.long()
            return [(r.long(), r.int()) for _ in range(r.int())]
        return self._cached(("lines", cid, mid), get)

    def _location_for_line(self, cid, line):
        best = None
        for mid in self._methods(cid):
            table = self._line_table(cid, mid)
            hits = [idx for idx, ln in table if ln == line]
            if hits:
                return (1, cid, mid, min(hits))
            later = [(ln, idx) for idx, ln in table if ln > line]
            if later and min(ln for _i, ln in table) < line:
                cand = min(later)
                if best is None or cand[0] < best[0]:
                    best = (cand[0], (1, cid, mid, cand[1]))
        return best[1] if best else None

    def _enc_location(self, loc) -> bytes:
        tag, cid, mid, idx = loc
        return bytes([tag]) + self.wire.id("ref", cid) + self.wire.id("method", mid) + struct.pack(">q", idx)

    def _line_of(self, loc) -> int:
        _t, cid, mid, idx = loc
        line = 0
        for i, ln in self._line_table(cid, mid):
            if i <= idx:
                line = ln
        return line

    def _fields(self, cid) -> list[tuple[int, str, str, int]]:
        """[(fieldID, name, signature, modBits)] of class *cid* and its superclasses (instance fields)."""
        def get():
            out, c = [], cid
            while c:
                r = Reader(self.wire, self.wire.request(2, 4, self.wire.id("ref", c)))
                own = [(r.id("field"), r.string(), r.string(), r.int()) for _ in range(r.int())]
                out = [f for f in own if not f[3] & 0x8] + out
                try:
                    c = Reader(self.wire, self.wire.request(3, 1, self.wire.id("ref", c))).id("ref")
                except JdwpError:
                    break
                if c and self._signature(c) == "Ljava/lang/Object;":
                    break
            return out
        return self._cached(("fields", cid), get)

    def _type_of(self, obj: Obj) -> int:
        r = Reader(self.wire, self.wire.request(9, 1, self.wire.id("object", obj.id)))
        r.byte()
        return r.id("ref")

    # ------------------------------------------------------------ values
    def _string(self, obj: Obj) -> str:
        return Reader(self.wire, self.wire.request(10, 1, self.wire.id("object", obj.id))).string()

    def _array_len(self, obj: Obj) -> int:
        return Reader(self.wire, self.wire.request(13, 1, self.wire.id("object", obj.id))).int()

    def _array_items(self, obj: Obj, first=0, count=None) -> list:
        n = self._array_len(obj)
        count = min(n - first, 500) if count is None else count
        if count <= 0:
            return []
        r = Reader(self.wire, self.wire.request(13, 2, self.wire.id("object", obj.id) + struct.pack(">ii", first, count)))
        tag = chr(r.byte())
        n = r.int()
        prim = tag in PRIMS
        return [r.value(tag) if prim else r.value() for _ in range(n)]

    def _field_values(self, obj: Obj, fields) -> list:
        if not fields:
            return []
        data = self.wire.id("object", obj.id) + struct.pack(">i", len(fields)) + b"".join(
            self.wire.id("field", f[0]) for f in fields)
        r = Reader(self.wire, self.wire.request(9, 2, data))
        return [r.value() for _ in range(r.int())]

    def _get_field(self, obj: Obj, name: str):
        if obj.tag == "[":
            if name == "length":
                return self._array_len(obj)
            raise JdwpError(f"arrays have no field '{name}'")
        cid = self._type_of(obj)
        f = next((f for f in reversed(self._fields(cid)) if f[1] == name), None)
        if f is None:
            raise JdwpError(f"no field '{name}' in {short_name(self._signature(cid))}")
        return self._field_values(obj, [f])[0]

    def _type_name(self, value) -> str:
        if isinstance(value, Obj):
            if value.tag == "s":
                return "String"
            return short_name(self._signature(self._type_of(value)))
        return {bool: "boolean", int: "int", float: "double", str: "char"}.get(type(value), "null")

    def _show(self, value, depth=0) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return repr(value)
        if not isinstance(value, Obj):
            return str(value)
        try:
            if value.tag == "s":
                text = self._string(value)
                return '"' + (text if len(text) < 300 else text[:300] + "...") + '"'
            cid = self._type_of(value)
            name = sig_name(self._signature(cid))
            if value.tag == "[":
                n = self._array_len(value)
                head = f"{short_name(self._signature(cid))[:-2]}[{n}]"
                if depth == 0 and n:
                    items = self._array_items(value, 0, min(n, 10))
                    return head + " {" + ", ".join(self._show(v, 1) for v in items) + (", ..." if n > 10 else "") + "}"
                return head
            if name in BOXED:
                return self._show(self._get_field(value, "value"), depth + 1)
            return "{" + short_name(self._signature(cid)) + "}"
        except JdwpError as e:
            return f"<{e}>"

    def _handle(self, value) -> int:
        if not isinstance(value, Obj) or value.tag == "s":
            return 0
        try:
            if value.tag != "[" and sig_name(self._signature(self._type_of(value))) in BOXED:
                return 0
        except JdwpError:
            return 0
        h = len(self.handles) + 1
        self.handles[h] = value
        return h

    def _children_of(self, obj: Obj) -> list[tuple[str, object]]:
        if obj.tag == "[":
            return [(f"[{i}]", v) for i, v in enumerate(self._array_items(obj))]
        fields = self._fields(self._type_of(obj))[:300]
        return [(f[1], v) for f, v in zip(fields, self._field_values(obj, fields))]

    # ------------------------------------------------------------ frames / locals
    def _load_frames(self, thread):
        r = Reader(self.wire, self.wire.request(11, 6, self.wire.id("object", thread) + struct.pack(">ii", 0, -1)))
        return [(r.id("frame"), r.location()) for _ in range(r.int())]

    def _locals(self, thread, frame_id, loc) -> list[tuple[str, object]]:
        _t, cid, mid, idx = loc
        out = []
        try:
            r = Reader(self.wire, self.wire.request(6, 2, self.wire.id("ref", cid) + self.wire.id("method", mid)))
            r.int()
            slots = []
            for _ in range(r.int()):
                start, name, sig, length, slot = r.long(), r.string(), r.string(), r.int(), r.int()
                if start <= idx < start + length and name != "this":
                    slots.append((name, sig, slot))
            slots.sort(key=lambda t: t[2])                 # parameters first, then locals in order
            if slots:
                data = self.wire.id("object", thread) + self.wire.id("frame", frame_id) + struct.pack(">i", len(slots))
                data += b"".join(struct.pack(">i", s) + sig[0].encode() for _n, sig, s in slots)
                vr = Reader(self.wire, self.wire.request(16, 1, data))
                values = [vr.value() for _ in range(vr.int())]
                out = [(n, v) for (n, _s, _sl), v in zip(slots, values)]
        except JdwpError:
            pass                                      # no debug information (-g) for this method
        try:
            this = Reader(self.wire, self.wire.request(16, 3, self.wire.id("object", thread) +
                                                       self.wire.id("frame", frame_id))).value()
            if this is not None:
                out.insert(0, ("this", this))
        except JdwpError:
            pass
        return out

    _CLIENT = {"radmain.java", "rad.java", "radcontrol.java", "radevent.java", "radjson.java"}

    def _user_class(self, cid) -> bool:
        """The class is compiled from one of the program's own .java files (not the JDK, not the bridge client)."""
        def get():
            try:
                src = self._source_file(cid)
            except JdwpError:
                return False
            return bool(src) and src.lower() not in self._CLIENT and Path(self._path_of(cid)).exists()
        return self._cached(("user", cid), get)

    def _path_of(self, cid) -> str:
        src = self._source_file(cid)
        if not src:
            return ""
        p = self.cwd / src
        if p.exists():
            return str(p)
        hit = next((q for q in self.cwd.glob("**/" + src)), None)
        return str(hit) if hit else src

    def _frame_scope(self, thread, frame_index=0):
        frame_id, loc = self._frames[frame_index]
        return self._locals(thread, frame_id, loc)

    def _build_stop(self, thread, reason) -> StopInfo:
        self._thread = thread
        self.handles = {}
        self._frames = self._load_frames(thread)
        user = [(fid, loc) for fid, loc in self._frames if Path(self._path_of(loc[1])).exists()]
        top = user[0] if user else (self._frames[0] if self._frames else None)
        if top is None:
            return StopInfo("", 0, reason)
        self.frame_id, loc = top
        info = StopInfo(self._path_of(loc[1]), self._line_of(loc), reason)
        info.thread_id = thread
        for fid, fl in self._frames[:40]:
            path = self._path_of(fl[1])
            mname = self._methods(fl[1]).get(fl[2], ("?", ""))[0]
            cls = short_name(self._signature(fl[1]))
            if Path(path).exists():
                info.frames.append((f"{cls}.{mname}", path, self._line_of(fl)))
        for name, value in self._locals(thread, self.frame_id, loc):
            info.variables.append((name, self._type_name(value), self._show(value)))
            h = self._handle(value)
            if h:
                info.refs[name] = h
        return info

    # ------------------------------------------------------------ events
    def _on_events(self, data):
        r = Reader(self.wire, data)
        policy = r.byte()
        resume = policy != SUSPEND_NONE
        stop = None
        for _ in range(r.int()):
            kind, rid = r.byte(), r.int()
            if kind in (SINGLE_STEP, BREAKPOINT, 3, 40, 41):        # thread + location
                thread, loc = r.id("object"), r.location()
                if kind == SINGLE_STEP:
                    self._clear_step()
                    stop = (thread, "step")
                elif kind == BREAKPOINT and self._bp_should_stop(rid, thread, loc):
                    stop = stop or (thread, "breakpoint")
            elif kind == EXCEPTION:
                thread = r.id("object")
                where, catch = r.location(), (r.value(), r.location())[1]      # throw / (exception) / catch
                if not catch[1] or self._user_class(where[1]):
                    stop = (thread, "error")
            elif kind in (THREAD_START, 7, VM_START):
                r.id("object")
            elif kind == CLASS_PREPARE:
                r.id("object"), r.byte()
                cid = r.id("ref")
                r.string(), r.int()
                self._on_class_prepare(cid)
            elif kind == VM_DEATH:
                resume = False
            else:
                break                                   # unknown event layout: stop parsing
        if stop is not None:
            info = self._build_stop(*stop)

            def show():
                self.paused = True
                self.stopped.emit(info)
            self._post(show)
        elif resume:
            self.wire.request(1, 9)                     # VirtualMachine.Resume (class loaded / logpoint / no stop)

    def _bp_should_stop(self, rid, thread, loc) -> bool:
        key = self._bp_of_req.get(rid)
        if key is None:
            return True
        d = parse_bp(self.bps.get(key[0], {}).get(key[1], ""))
        scope = {}
        if d["cond"] or d["log"]:
            frames = self._load_frames(thread)
            scope = dict(self._locals(thread, frames[0][0], frames[0][1])) if frames else {}
        if d["cond"]:
            try:
                if not self._truthy(self._eval(d["cond"], scope)):
                    return False
            except JdwpError as e:
                self._emit(self.output, f"[debugger] condition '{d['cond']}': {e}\n")
        self.hits[key] = self.hits.get(key, 0) + 1
        if d["hit"] and not hit_ok(d["hit"], self.hits[key]):
            return False
        if d["log"]:
            text = format_log(d["log"], lambda e: self._plain(self._eval(e, scope)))
            self._emit(self.output, text + "\n")
            return False
        return True

    def _clear_step(self):
        if self._step_req:
            rid, self._step_req = self._step_req, 0
            try:
                self.wire.request(15, 2, bytes([SINGLE_STEP]) + struct.pack(">i", rid))
            except JdwpError:
                pass

    # ------------------------------------------------------------ expressions
    _TOK = re.compile(r"\s*(?:(\d+\.\d*|\d+)[LlFfDd]?|(\"(?:\\.|[^\"\\])*\")|('(?:\\.|[^'\\])')|"
                      r"([A-Za-z_$][\w$]*)|(==|!=|<=|>=|&&|\|\||[-+*/%<>!().\[\]]))")

    def _tokens(self, text):
        out, pos = [], 0
        text = text.strip()
        while pos < len(text):
            m = self._TOK.match(text, pos)
            if not m or m.end() == pos:
                raise JdwpError(f"cannot read the expression at '{text[pos:]}'")
            pos = m.end()
            num, s, ch, ident, op = m.groups()
            if num is not None:
                out.append(("v", float(num) if "." in num else int(num)))
            elif s is not None:
                out.append(("v", bytes(s[1:-1], "utf-8").decode("unicode_escape")))
            elif ch is not None:
                out.append(("v", bytes(ch[1:-1], "utf-8").decode("unicode_escape")))
            elif ident is not None:
                out.append(("id", ident))
            else:
                out.append(("op", op))
        return out

    def _eval(self, text, scope):
        toks = self._tokens(text)
        pos = [0]

        def peek():
            return toks[pos[0]] if pos[0] < len(toks) else ("end", None)

        def eat(op=None):
            t = peek()
            if op is not None and t != ("op", op):
                raise JdwpError(f"expected '{op}'")
            pos[0] += 1
            return t

        def primary():
            t = eat()
            if t[0] == "v":
                v = t[1]
            elif t == ("op", "("):
                v = binary(0)
                eat(")")
            elif t == ("op", "!"):
                return not self._truthy(primary())
            elif t == ("op", "-"):
                return -self._num(primary())
            elif t[0] == "id":
                name = t[1]
                if name in ("true", "false"):
                    v = name == "true"
                elif name == "null":
                    v = None
                elif name in scope:
                    v = scope[name]
                elif "this" in scope and isinstance(scope["this"], Obj):
                    v = self._get_field(scope["this"], name)
                else:
                    raise JdwpError(f"'{name}' is not a variable here")
            else:
                raise JdwpError("unexpected end of the expression")
            while peek() in (("op", "."), ("op", "[")):
                if eat()[1] == ".":
                    t = eat()
                    if t[0] != "id":
                        raise JdwpError("a field name must follow '.'")
                    if peek() == ("op", "("):
                        raise JdwpError("method calls are not supported by the Java debugger")
                    if not isinstance(v, Obj):
                        raise JdwpError(f"'{t[1]}': not an object")
                    v = self._get_field(v, t[1])
                else:
                    idx = int(self._num(binary(0)))
                    eat("]")
                    if not isinstance(v, Obj) or v.tag != "[":
                        raise JdwpError("not an array")
                    items = self._array_items(v, idx, 1)
                    if not items:
                        raise JdwpError("index out of range")
                    v = items[0]
            if peek() == ("op", "("):
                raise JdwpError("method calls are not supported by the Java debugger")
            return v

        levels = [("||",), ("&&",), ("==", "!="), ("<", "<=", ">", ">="), ("+", "-"), ("*", "/", "%")]

        def binary(level):
            if level == len(levels):
                return primary()
            left = binary(level + 1)
            while peek()[0] == "op" and peek()[1] in levels[level]:
                op = eat()[1]
                right = binary(level + 1)
                left = self._apply(op, left, right)
            return left

        v = binary(0)
        if pos[0] != len(toks):
            raise JdwpError("unexpected text at the end of the expression")
        return v

    def _plain(self, v):
        """Python value of a JDWP value (strings fetched, boxed numbers unboxed)."""
        if isinstance(v, Obj):
            if v.tag == "s":
                return self._string(v)
            try:
                if sig_name(self._signature(self._type_of(v))) in BOXED:
                    return self._get_field(v, "value")
            except JdwpError:
                pass
            return self._show(v)
        if isinstance(v, bool):
            return "true" if v else "false"
        return "null" if v is None else v

    def _num(self, v):
        v = self._plain(v) if isinstance(v, Obj) else v
        if isinstance(v, str) and len(v) == 1:
            return ord(v)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
        raise JdwpError("a number is needed")

    def _truthy(self, v):
        if isinstance(v, bool):
            return v
        raise JdwpError("the condition is not a boolean")

    def _apply(self, op, a, b):
        if op == "&&":
            return self._truthy(a) and self._truthy(b)
        if op == "||":
            return self._truthy(a) or self._truthy(b)
        if op in ("==", "!="):
            pa = self._plain(a) if isinstance(a, Obj) and (a.tag == "s") else a
            pb = self._plain(b) if isinstance(b, Obj) and (b.tag == "s") else b
            if isinstance(pa, Obj) and isinstance(pb, Obj):
                same = pa.id == pb.id
            elif isinstance(pa, Obj) or isinstance(pb, Obj):
                pa, pb = self._plain(pa) if isinstance(pa, Obj) else pa, self._plain(pb) if isinstance(pb, Obj) else pb
                same = pa == pb
            else:
                same = pa == pb
            return same if op == "==" else not same
        if op == "+" and (isinstance(self._plain(a), str) and not (isinstance(a, str) and len(a) == 1)
                          or isinstance(self._plain(b), str) and not (isinstance(b, str) and len(b) == 1)):
            return f"{self._plain(a)}{self._plain(b)}"
        x, y = self._num(a), self._num(b)
        if op == "+":
            return x + y
        if op == "-":
            return x - y
        if op == "*":
            return x * y
        if op == "/":
            if y == 0:
                raise JdwpError("/ by zero")
            return x / y if isinstance(x, float) or isinstance(y, float) else int(x / y)
        if op == "%":
            return x % y
        return {"<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}[op]

    def _scope(self):
        if not self._frames:
            return {}
        idx = next((i for i, (fid, _l) in enumerate(self._frames) if fid == self.frame_id), 0)
        return dict(self._frame_scope(self._thread, idx))

    # ------------------------------------------------------------ Session API (Qt thread)
    def _resume(self, step_depth=None):
        if not self.paused:
            return
        self.paused = False
        self.resumed.emit()
        thread = self._thread

        def go():
            if step_depth is not None:
                self._clear_step()
                w = self.wire
                mods = [b"\x0a" + w.id("object", thread) + struct.pack(">ii", 1, step_depth)]
                mods += [b"\x06" + w.string(p) for p in STEP_EXCLUDES]
                mods.append(b"\x01" + struct.pack(">i", 1))
                data = bytes([SINGLE_STEP, SUSPEND_ALL]) + struct.pack(">i", len(mods)) + b"".join(mods)
                self._step_req = struct.unpack(">i", w.request(15, 1, data)[:4])[0]
            self.wire.request(1, 9)
        self._job(go)

    def cont(self):
        self._resume()

    def step_into(self):
        self._resume(0)

    def step_over(self):
        self._resume(1)

    def step_out(self):
        self._resume(2)

    def evaluate(self, expr: str):
        if not self.paused:
            self.evalResult.emit("(the program must be paused at a breakpoint)")
            return

        def ev():
            try:
                v = self._eval(expr, self._scope())
                text = self._show(v) if isinstance(v, Obj) or v is None or isinstance(v, bool) else \
                    (repr(v) if isinstance(v, str) else str(v))
            except JdwpError as e:
                text = f"error: {e}"
            self._emit(self.evalResult, text)
        self._job(ev)

    def watch(self, expr: str, cb):
        if not self.paused:
            cb("(the program must be paused at a breakpoint)", "", 0)
            return

        def ev():
            try:
                v = self._eval(expr, self._scope())
                out = (self._show(v) if not isinstance(v, str) or len(v) == 1 else repr(v)), self._type_name(v), self._handle(v)
            except JdwpError as e:
                out = (f"error: {e}", "", 0)
            self._post(lambda: cb(*out))
        self._job(ev)

    def children(self, ref, cb):
        obj = self.handles.get(int(ref)) if str(ref).isdigit() else None
        if obj is None or not self.paused:
            cb([])
            return

        def ev():
            try:
                out = [(n, self._type_name(v), self._show(v), self._handle(v)) for n, v in self._children_of(obj)]
            except JdwpError as e:
                out = [("(error)", "", str(e), 0)]
            self._post(lambda: cb(out))
        self._job(ev)

    def threads(self, cb):
        if not self.running():
            cb([])
            return

        def ev():
            out = []
            try:
                r = Reader(self.wire, self.wire.request(1, 4))
                for tid in [r.id("object") for _ in range(r.int())]:
                    try:
                        out.append((tid, Reader(self.wire, self.wire.request(11, 1, self.wire.id("object", tid))).string()))
                    except JdwpError:
                        pass
            except JdwpError:
                pass
            self._post(lambda: cb(out))
        self._job(ev)

    def select_thread(self, tid):
        if not self.paused or not tid:
            return

        def ev():
            info = self._build_stop(int(tid), "step")
            self._post(lambda: self.stopped.emit(info))
        self._job(ev)

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = ""):
        name = Path(filename).name.lower()
        lines = self.bps.setdefault(name, {})
        if on:
            lines[int(line)] = cond or ""
        else:
            lines.pop(int(line), None)
        self.hits.pop((name, int(line)), None)

        def ev():
            self._clear_bp((name, int(line)))
            if on:
                self._watch_class_loads(name)
        if self.ready:
            self._job(ev)

    def set_break_on_exception(self, on: bool):
        self.break_on_exception = on
        if self.ready:
            self._job(lambda: self._set_exception_request(on))

    def stop(self):
        self.user_stopped = True
        w, self.wire = self.wire, None
        self._alive = False
        self._jobs.put(None)
        if w is not None:
            try:
                w.sock.close()
            except OSError:
                pass
