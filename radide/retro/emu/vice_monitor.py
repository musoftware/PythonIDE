"""Client for VICE's binary remote monitor (VICE 3.5 and newer; no Qt in here).

VICE is started with ``-binarymonitor -binarymonitoraddress ip4://127.0.0.1:<port>``; this module speaks the
documented protocol (VICE manual, "Binary Monitor"):

    request : 0x02 STX | 0x02 API version | body length (u32 LE) | request id (u32 LE) | command (u8) | body
    response: 0x02 STX | 0x02 API version | body length (u32 LE) | type (u8) | error (u8) | request id (u32) | body

Responses with request id 0xFFFFFFFF are events (stopped 0x62, resumed 0x63, JAM 0x61, checkpoint hit 0x11,
registers 0x31). Any command stops the emulated machine; ``exit_monitor()`` (0xAA) lets it run again.

    mon = ViceMonitor(port); mon.connect()
    mon.pause(); regs = mon.registers(); data = mon.memory_get(0x0801, 0x0820)
    bp = mon.checkpoint_set(0xC000); mon.exit_monitor(); ev = mon.wait_stopped(5)
    mon.step(1); mon.autostart("game.prg")      # hot reload
"""
from __future__ import annotations

import socket
import struct
import threading
import time
from dataclasses import dataclass, field

STX = 0x02
API = 0x02
EVENT_ID = 0xFFFFFFFF

CMD_MEM_GET, CMD_MEM_SET = 0x01, 0x02
CMD_CP_GET, CMD_CP_SET, CMD_CP_DELETE, CMD_CP_LIST, CMD_CP_TOGGLE = 0x11, 0x12, 0x13, 0x14, 0x15
CMD_COND_SET = 0x22
CMD_REGS_GET, CMD_REGS_SET = 0x31, 0x32
CMD_ADVANCE, CMD_KEYBOARD, CMD_UNTIL_RETURN = 0x71, 0x72, 0x73
CMD_PING, CMD_BANKS, CMD_REGS_AVAILABLE, CMD_DISPLAY, CMD_INFO = 0x81, 0x82, 0x83, 0x84, 0x85
CMD_EXIT, CMD_QUIT, CMD_RESET, CMD_AUTOSTART = 0xAA, 0xBB, 0xCC, 0xDD

EV_JAM, EV_STOPPED, EV_RESUMED = 0x61, 0x62, 0x63

ERRORS = {0x01: "object does not exist", 0x80: "invalid length", 0x81: "invalid parameter",
          0x82: "API version not supported", 0x83: "invalid command", 0x8F: "general failure"}

MEM_MAIN = 0x00


class MonitorError(Exception):
    pass


@dataclass
class Response:
    type: int
    error: int
    request_id: int
    body: bytes = b""


@dataclass
class Checkpoint:
    number: int
    hit: bool
    start: int
    end: int
    stop: bool
    enabled: bool
    op: int
    temporary: bool
    hit_count: int = 0


@dataclass
class StopEvent:
    kind: str                # "stopped" | "jam" | "checkpoint"
    pc: int = -1
    checkpoint: int = -1
    registers: dict = field(default_factory=dict)


class ViceMonitor:
    def __init__(self, port: int = 6502, host: str = "127.0.0.1", timeout: float = 5.0):
        self.host, self.port, self.timeout = host, port, timeout
        self.sock: socket.socket | None = None
        self._buf = b""
        self._next_id = 1
        self._lock = threading.Lock()
        self.events: list[Response] = []
        self.reg_names: dict[int, str] = {}
        self.running = True

    # ------------------------------------------------------------------ connection
    def connect(self, retry_for: float = 0.0) -> "ViceMonitor":
        """Connect, retrying for *retry_for* seconds (VICE opens the port a moment after it starts)."""
        end = time.time() + retry_for
        while True:
            try:
                self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
                self.sock.settimeout(self.timeout)
                return self
            except OSError:
                if time.time() >= end:
                    raise
                time.sleep(0.25)

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    @property
    def connected(self) -> bool:
        return self.sock is not None

    # ------------------------------------------------------------------ framing
    @staticmethod
    def encode(request_id: int, command: int, body: bytes = b"") -> bytes:
        return struct.pack("<BBIIB", STX, API, len(body), request_id, command) + body

    @staticmethod
    def decode(buf: bytes) -> tuple[Response | None, bytes]:
        """One response from the front of *buf* -> (response or None when incomplete, rest of buf)."""
        if len(buf) < 12:
            return None, buf
        if buf[0] != STX:
            raise MonitorError(f"bad response start byte 0x{buf[0]:02X}")
        length = struct.unpack_from("<I", buf, 2)[0]
        if len(buf) < 12 + length:
            return None, buf
        rtype, err, rid = struct.unpack_from("<BBI", buf, 6)
        return Response(rtype, err, rid, bytes(buf[12:12 + length])), buf[12 + length:]

    def _recv_one(self, timeout: float | None = None) -> Response:
        if self.sock is None:
            raise MonitorError("not connected")
        deadline = time.time() + (self.timeout if timeout is None else timeout)
        while True:
            resp, self._buf = self.decode(self._buf)
            if resp is not None:
                return resp
            left = deadline - time.time()
            if left <= 0:
                raise TimeoutError("VICE monitor: no response")
            self.sock.settimeout(left)
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout as e:
                raise TimeoutError("VICE monitor: no response") from e
            if not chunk:
                self.close()
                raise MonitorError("VICE closed the monitor connection")
            self._buf += chunk

    def _note_event(self, r: Response) -> None:
        if r.type == EV_RESUMED:
            self.running = True
        elif r.type in (EV_STOPPED, EV_JAM):
            self.running = False
        self.events.append(r)
        del self.events[:-200]

    def request(self, command: int, body: bytes = b"", timeout: float | None = None) -> Response:
        """Send one command and return its response (events that arrive meanwhile are queued)."""
        with self._lock:
            rid = self._next_id
            self._next_id = (self._next_id + 1) & 0x7FFFFFFF or 1
            assert self.sock is not None, "not connected"
            if command in (CMD_EXIT, CMD_ADVANCE, CMD_UNTIL_RETURN):
                self.events.clear()          # stale stop events must not answer the next wait_stopped()
            self.sock.sendall(self.encode(rid, command, body))
            while True:
                r = self._recv_one(timeout)
                if r.request_id == rid:
                    if r.error:
                        raise MonitorError(f"VICE monitor command 0x{command:02X}: "
                                           f"{ERRORS.get(r.error, hex(r.error))}")
                    if command not in (CMD_EXIT,):
                        self.running = False if command != CMD_AUTOSTART else self.running
                    return r
                self._note_event(r)

    def poll_events(self, timeout: float = 0.0) -> list[Response]:
        """Events received so far plus those arriving within *timeout* seconds."""
        with self._lock:
            end = time.time() + timeout
            while True:
                left = end - time.time()
                try:
                    r = self._recv_one(max(left, 0.01) if timeout else 0.01)
                    self._note_event(r)
                except TimeoutError:
                    break
                if left <= 0 and not self._buf:
                    break
            out, self.events = self.events, []
            return out

    def wait_stopped(self, timeout: float = 5.0) -> StopEvent | None:
        """Wait for the machine to stop (breakpoint, step done, JAM); None on timeout."""
        end = time.time() + timeout
        ev = StopEvent("stopped")
        got = False
        pending = list(self.events)
        self.events = []
        while time.time() < end or pending:
            for r in pending or self.poll_events(min(0.25, max(0.0, end - time.time()))):
                if r.type == CMD_CP_GET and len(r.body) >= 4:
                    ev.checkpoint = struct.unpack_from("<I", r.body, 0)[0]
                    ev.kind = "checkpoint"
                elif r.type == CMD_REGS_GET:
                    ev.registers = self._parse_registers(r.body)
                elif r.type in (EV_STOPPED, EV_JAM):
                    ev.pc = struct.unpack_from("<H", r.body, 0)[0] if len(r.body) >= 2 else -1
                    if r.type == EV_JAM:
                        ev.kind = "jam"
                    got = True
            pending = []
            if got:
                return ev
        return None

    # ------------------------------------------------------------------ commands
    def ping(self) -> bool:
        return self.request(CMD_PING).type == CMD_PING

    def info(self) -> str:
        """VICE version, e.g. "3.10.0.0"."""
        b = self.request(CMD_INFO).body
        if not b:
            return ""
        n = b[0]
        ver = ".".join(str(x) for x in b[1:1 + n])
        return ver

    def pause(self) -> None:
        """Stop the machine (any command does; ping is the cheapest)."""
        self.ping()

    def exit_monitor(self) -> None:
        """Let the machine run again."""
        self.request(CMD_EXIT)
        self.running = True

    resume = exit_monitor

    def memory_get(self, start: int, end: int, side_effects: bool = False, memspace: int = MEM_MAIN,
                   bank: int = 0) -> bytes:
        """Bytes start..end (inclusive)."""
        body = struct.pack("<BHHBH", 1 if side_effects else 0, start & 0xFFFF, end & 0xFFFF, memspace, bank)
        b = self.request(CMD_MEM_GET, body).body
        n = struct.unpack_from("<H", b, 0)[0] if len(b) >= 2 else 0
        return bytes(b[2:2 + (n or (end - start + 1))])

    def memory_set(self, start: int, data: bytes, side_effects: bool = False, memspace: int = MEM_MAIN,
                   bank: int = 0) -> None:
        end = start + len(data) - 1
        body = struct.pack("<BHHBH", 1 if side_effects else 0, start & 0xFFFF, end & 0xFFFF, memspace, bank) + data
        self.request(CMD_MEM_SET, body)

    def register_names(self, memspace: int = MEM_MAIN) -> dict[int, str]:
        if self.reg_names:
            return self.reg_names
        b = self.request(CMD_REGS_AVAILABLE, bytes([memspace])).body
        count = struct.unpack_from("<H", b, 0)[0]
        pos, names = 2, {}
        for _ in range(count):
            size = b[pos]
            rid, nlen = b[pos + 1], b[pos + 3]          # b[pos + 2] = size in bits
            names[rid] = b[pos + 4:pos + 4 + nlen].decode("ascii", "replace")
            pos += size + 1
        self.reg_names = names
        return names

    def _parse_registers(self, b: bytes) -> dict[str, int]:
        if len(b) < 2:
            return {}
        count = struct.unpack_from("<H", b, 0)[0]
        pos, out = 2, {}
        for _ in range(count):
            size = b[pos]
            rid = b[pos + 1]
            val = struct.unpack_from("<H", b, pos + 2)[0] if size >= 3 else b[pos + 2]
            out[self.reg_names.get(rid, f"R{rid}")] = val
            pos += size + 1
        return out

    def registers(self, memspace: int = MEM_MAIN) -> dict[str, int]:
        """{"PC": .., "A": .., "X": .., "Y": .., "SP": .., "FL": .., ...}"""
        self.register_names(memspace)
        return self._parse_registers(self.request(CMD_REGS_GET, bytes([memspace])).body)

    def set_register(self, name: str, value: int, memspace: int = MEM_MAIN) -> None:
        names = {v.upper(): k for k, v in self.register_names(memspace).items()}
        rid = names[name.upper()]
        self.request(CMD_REGS_SET, struct.pack("<BHBBH", memspace, 1, 3, rid, value & 0xFFFF))

    def checkpoint_set(self, start: int, end: int | None = None, stop: bool = True, op: int = 4,
                       temporary: bool = False) -> int:
        """A breakpoint (op 4 = execute; 1 = load, 2 = store watchpoint). Returns its number."""
        body = struct.pack("<HHBBBB", start & 0xFFFF, (start if end is None else end) & 0xFFFF,
                           1 if stop else 0, 1, op, 1 if temporary else 0)
        b = self.request(CMD_CP_SET, body).body
        return struct.unpack_from("<I", b, 0)[0]

    def checkpoint_delete(self, number: int) -> None:
        self.request(CMD_CP_DELETE, struct.pack("<I", number))

    def step(self, count: int = 1, over: bool = False) -> None:
        """Run *count* instructions (over = step over JSR); the machine stops again afterwards."""
        self.request(CMD_ADVANCE, struct.pack("<BH", 1 if over else 0, count))
        self.running = True

    def until_return(self) -> None:
        self.request(CMD_UNTIL_RETURN)
        self.running = True

    def reset(self, hard: bool = False) -> None:
        self.request(CMD_RESET, bytes([1 if hard else 0]))

    def autostart(self, path: str, run: bool = True, index: int = 0) -> None:
        """Load and start a program / disk image (hot reload of a rebuilt .prg)."""
        name = str(path).encode("utf-8")
        self.request(CMD_AUTOSTART, struct.pack("<BHB", 1 if run else 0, index, len(name)) + name, timeout=15)

    def keyboard_feed(self, text: str) -> None:
        data = text.encode("latin-1", "replace")
        self.request(CMD_KEYBOARD, bytes([len(data)]) + data)

    def quit(self) -> None:
        try:
            self.request(CMD_QUIT, timeout=2)
        except (OSError, MonitorError, TimeoutError):
            pass
        self.close()


def load_labels(path) -> dict[int, str]:
    """address -> label from a VICE label file (``al C:0810 .loop``) or an ld65 / ACME / 64tass "name = $addr"
    listing; used to show names next to addresses."""
    import re
    out: dict[int, str] = {}
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    for line in text.splitlines():
        m = re.match(r"\s*al\s+(?:C:)?([0-9A-Fa-f]{1,4})\s+\.?(\S+)", line)
        if m:
            out[int(m.group(1), 16)] = m.group(2)
            continue
        m = re.match(r"\s*([A-Za-z_.@][\w.@]*)\s*=\s*\$([0-9A-Fa-f]{1,4})\b", line)
        if m:
            out.setdefault(int(m.group(2), 16), m.group(1))
    return out


__all__ = ["Checkpoint", "MonitorError", "Response", "StopEvent", "ViceMonitor", "load_labels"]
