"""An ELM327 command interpreter in front of the Demo car (original implementation of the documented ELM327
behaviour): AT commands, protocol search ("SEARCHING..."), K-line init ("BUS INIT: ...OK"), headers on / off,
spaces, CAN receive filter, ISO-TP multi-frame output in both header styles, "NO DATA" / "CAN ERROR" /
"UNABLE TO CONNECT", adaptive time-out and ``ATMA`` monitoring for answers that come late ("response pending").

It is a byte-stream device: ``feed(bytes)`` and ``read(timeout) -> bytes`` (link/transport.LoopbackTransport,
the TCP server in server.py). Optional STN-style identification (``STI`` / ``STDI``) for adapter tests.
"""
from __future__ import annotations

import threading
import time

from ..link import isotp
from ..link.protocols import FUNC_11, FUNC_29, PROTOCOLS, get as get_protocol

CAN_CODES = ("6", "7", "8", "9", "A")


class ElmInterpreter:
    def __init__(self, car, version: str = "ELM327 v1.5", stn: str | None = None, padding: int = 0xAA):
        self.car = car
        self.version = version
        self.stn = stn
        self.padding = padding
        self._in = bytearray()
        self._out = bytearray()
        self.cond = threading.Condition()
        self.queue: list[tuple[float, list[str]]] = []      # late answers: (real time, formatted lines)
        self.monitor = False
        self.last = ""
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        self.echo, self.linefeed, self.spaces, self.headers, self.dlc = True, False, True, False, False
        self.proto, self.auto = "0", True
        self.current: str | None = None
        self.header: int | None = None
        self.header_len = 0
        self.cra: int | None = None
        self.cp = 0x18
        self.st = 0x32
        self.caf = True
        self.kinit = False
        self.monitor = False
        self.queue.clear()

    @property
    def eol(self) -> str:
        return "\r\n" if self.linefeed else "\r"

    # ------------------------------------------------------------------ byte stream
    def feed(self, data: bytes) -> None:
        with self.cond:
            for b in data:
                if self.monitor:                       # any character stops ATMA
                    self.monitor = False
                    self._emit(self.eol + ">")
                    self._in.clear()
                    continue
                if b in (0x0D,):
                    line = self._in.decode("ascii", "replace")
                    self._in.clear()
                    self._line(line)
                elif b in (0x0A, 0x00):                # line feeds / NULs are ignored, as the ELM327 does
                    continue
                else:
                    self._in.append(b)
            self.cond.notify_all()

    def read(self, timeout: float = 0.0) -> bytes:
        end = time.monotonic() + timeout
        with self.cond:
            while True:
                self._poll()
                if self._out:
                    data, self._out = bytes(self._out), bytearray()
                    return data
                left = end - time.monotonic()
                if left <= 0:
                    return b""
                self.cond.wait(min(left, 0.02))

    def _emit(self, text: str) -> None:
        self._out += text.encode("ascii")

    def _poll(self) -> None:
        """Deliver late answers while monitoring (ATMA)."""
        if not self.monitor or not self.queue:
            return
        now = time.monotonic()
        due = [q for q in self.queue if q[0] <= now]
        if due:
            self.queue = [q for q in self.queue if q[0] > now]
            for _t, lines in due:
                for ln in lines:
                    self._emit(ln + self.eol)

    # ------------------------------------------------------------------ commands
    def _line(self, raw: str) -> None:
        text = raw.strip()
        if self.echo:
            self._emit(raw + self.eol)
        if not text:
            text = self.last
            if not text:
                self._emit(self.eol + ">")
                return
        cmd = text.replace(" ", "").upper()
        self.last = text
        if cmd.startswith("AT") or cmd.startswith("ST"):
            out = self._at(cmd)
            if out is None:                           # ATMA: no prompt until stopped
                return
        else:
            out = self._obd(cmd)
        for ln in out:
            self._emit(ln + self.eol)
        self._emit(self.eol + ">")

    def _at(self, cmd: str):
        if cmd.startswith("ST"):
            if not self.stn:
                return ["?"]
            if cmd == "STI":
                return [self.stn]
            if cmd == "STDI":
                return [f"Demo adapter {self.stn.split()[0]}"]
            return ["OK"]
        c = cmd[2:]
        if c in ("Z", "WS", "D"):
            keep = (self.echo, self.linefeed) if c == "D" else None
            self.reset()
            if keep:
                self.echo, self.linefeed = keep
                return ["OK"]
            return ["", self.version]
        if c == "I":
            return [self.version]
        if c == "@1":
            return ["OBDII to RS232 Interpreter (RAD IDE Demo car)"]
        if c == "RV":
            return [f"{self.car.state()['battery'] if self.car.ignition else 12.6:.1f}V"]
        flags = {"E": "echo", "L": "linefeed", "S": "spaces", "H": "headers", "D": "dlc"}
        if len(c) == 2 and c[0] in flags and c[1] in "01":
            setattr(self, flags[c[0]], c[1] == "1")
            return ["OK"]
        if c in ("CAF0", "CAF1"):
            self.caf = c.endswith("1")
            return ["OK"]
        if c in ("AT0", "AT1", "AT2", "M0", "M1", "CFC0", "CFC1", "R0", "R1", "V0", "V1", "AL", "NL", "BI",
                 "CSM0", "CSM1", "KW0", "KW1", "CEA", "LP", "SI", "FI"):
            return ["OK"]
        if c.startswith(("SPA", "TPA")):
            return self._set_proto(c[3:], auto=True)
        if c.startswith(("SP", "TP")):
            return self._set_proto(c[2:], auto=c[2:] == "0")
        if c == "DP":
            p = PROTOCOLS.get(self.current or "") if self.current else None
            name = p.name if p else "AUTO"
            return [("AUTO, " + name) if (self.auto and p) else name]
        if c == "DPN":
            shown = self.current or self.proto
            return [("A" + shown) if self.auto else shown]
        if c.startswith("SH"):
            h = c[2:]
            try:
                self.header, self.header_len = int(h, 16), len(h)
            except ValueError:
                return ["?"]
            return ["OK"]
        if c.startswith("CRA"):
            v = c[3:]
            try:
                self.cra = int(v, 16) if v else None
            except ValueError:
                return ["?"]
            return ["OK"]
        if c == "AR":
            self.cra = None
            return ["OK"]
        if c.startswith("CP"):
            try:
                self.cp = int(c[2:], 16)
            except ValueError:
                return ["?"]
            return ["OK"]
        if c.startswith("ST"):
            try:
                self.st = int(c[2:], 16) or 0x32
            except ValueError:
                return ["?"]
            return ["OK"]
        if c.startswith(("FCSH", "FCSD", "FCSM", "IB", "IIA", "SR", "CF", "CM", "BRD", "BRT", "SW", "WM")):
            return ["OK"]
        if c == "PC":
            self.kinit = False
            return ["OK"]
        if c == "CS":
            return ["T:00 R:00 ", "CAN OK"]
        if c == "MA":
            self.monitor = True
            return None
        return ["?"]

    def _set_proto(self, code: str, auto: bool):
        code = code.upper() or "0"
        if code != "0" and code not in PROTOCOLS:
            return ["?"]
        self.proto, self.auto = code, auto or code == "0"
        self.current = None if code == "0" else code
        self.kinit = False
        return ["OK"]

    # ------------------------------------------------------------------ requests
    def _reachable(self, code: str) -> str | None:
        """None when the car answers on *code*, else the adapter's error text."""
        car = self.car.protocol
        if code == car:
            return None
        p, c = PROTOCOLS.get(code), PROTOCOLS.get(car)
        if p is None or c is None:
            return "NO DATA"
        if p.is_can:
            if not c.is_can or p.bitrate != c.bitrate:
                return "CAN ERROR"
            return "NO DATA"
        if p.family == "kline":
            return "BUS INIT: ...ERROR" if not (c.family == "kline") else (None if {code, car} <= {"4", "5"} else
                                                                             "BUS INIT: ...ERROR")
        return "NO DATA"

    def _obd(self, cmd: str) -> list[str]:
        try:
            if len(cmd) % 2 == 1:                     # trailing response count digit (accepted, not needed here)
                cmd = cmd[:-1]
            payload = bytes.fromhex(cmd)
        except ValueError:
            return ["?"]
        if not payload:
            return ["?"]
        out: list[str] = []
        car = self.car
        if not car.ignition:
            return ["SEARCHING...", "UNABLE TO CONNECT"] if self.current is None else ["NO DATA"]
        if self.current is None:                      # automatic search
            out.append("SEARCHING...")
            self.current = car.protocol
        err = self._reachable(self.current)
        if err is not None:
            if self.auto and self.proto == "0":
                self.current = None
                return out + ["UNABLE TO CONNECT"]
            return out + [err]
        p = get_protocol(self.current)
        if p.family == "kline" and not self.kinit:
            self.kinit = True
            out.append("BUS INIT: ...OK")
        answers = self._route(p, payload)
        window = (self.st * 4) / 1000.0
        lines_now: list[str] = []
        now = time.monotonic()
        for delay, src, data in answers:
            lines = self._format(p, src, data)
            if delay / max(0.001, car.time_scale) <= window:
                lines_now += lines
            else:
                self.queue.append((now + delay / max(0.001, car.time_scale), lines))

        if not lines_now:
            return out + ["NO DATA"]
        return out + lines_now

    def _route(self, p, payload: bytes) -> list[tuple[float, int, bytes]]:
        car = self.car
        res: list[tuple[float, int, bytes]] = []
        with car.lock:
            if p.is_can:
                if p.bits29:
                    hdr = ((self.cp & 0x1F) << 24) | (self.header if self.header is not None else FUNC_29 & 0xFFFFFF)
                    if self.header is not None and self.header_len <= 6:
                        hdr = ((self.cp & 0x1F) << 24) | self.header
                    if self.header is not None and self.header_len == 8:
                        hdr = self.header
                    functional = (hdr & 0xFFFF0000) == 0x18DB0000
                    target = (hdr >> 8) & 0xFF
                    for e in car.ecus:
                        if functional or e.addr == target:
                            src = 0x18DAF100 | e.addr
                            if self.cra is not None and src != self.cra:
                                continue
                            for d, a in e.handle(payload, functional, True):
                                res.append((d, src, a))
                else:
                    hdr = self.header if self.header is not None else FUNC_11
                    functional = hdr == FUNC_11
                    for e in car.ecus:
                        if functional or e.tx == hdr:
                            if self.cra is not None and e.rx != self.cra:
                                continue
                            for d, a in e.handle(payload, functional, True):
                                res.append((d, e.rx, a))
            else:
                h = self.header
                if h is None:
                    functional, target = True, 0x33
                else:
                    hb = h.to_bytes(3, "big")
                    target = hb[1]
                    functional = target in (0x33, 0x6A)
                for e in car.ecus:
                    if not e.kline:
                        continue
                    if functional or e.addr == target:
                        for d, a in e.handle(payload, functional, False):
                            res.append((d, e.addr, a))
        return res

    def _fmt(self, bs: bytes) -> str:
        return (" " if self.spaces else "").join(f"{b:02X}" for b in bs)

    def _format(self, p, src: int, data: bytes) -> list[str]:
        sp = " " if self.spaces else ""
        if p.is_can:
            if p.bits29:
                hid = sp.join(f"{b:02X}" for b in src.to_bytes(4, "big"))
            else:
                hid = f"{src:03X}"
            frames = isotp.segment(data, 8, self.padding)
            if self.headers:
                out = []
                for f in frames:
                    dl = f"{len(f)}{sp}" if self.dlc else ""
                    out.append(f"{hid}{sp}{dl}{self._fmt(f)}")
                return out
            if len(frames) == 1:
                return [self._fmt(data)]
            out = [f"{len(data):03X}"]
            out.append(f"0:{sp}{self._fmt(data[:6])}")
            pos, i = 6, 1
            while pos < len(data):
                out.append(f"{i & 0xF:X}:{sp}{self._fmt(data[pos:pos + 7])}")
                pos += 7
                i += 1
            return out
        # K-line / J1850: one message per answer (the units keep answers short)
        if p.code in ("4", "5"):
            hdr = bytes([0x80 | len(data), 0xF1, src])
        else:
            hdr = bytes([0x48, 0x6B, src])
        msg = hdr + data
        msg += bytes([sum(msg) & 0xFF])
        return [self._fmt(msg if self.headers else data)]
