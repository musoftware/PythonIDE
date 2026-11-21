"""Simulated control units for the Demo car: a UDS (ISO 14229) server with sessions, S3 time-out, security access
(Demo car's own seed/key, see demo_seedkey.py), DTCs with status bytes, snapshots and extended data, data
identifiers, routines with progress and preconditions, IO control, negative responses and "response pending";
KWP2000 basics for the K-line variant; the OBD-II modes for the engine unit (obd.py in this package).

``SimEcu.handle(request, functional, can)`` returns a list of ``(delay_seconds, answer_bytes)`` (empty = no
answer). Everything here is original code written for RAD IDE; the routine / DID numbers are the Demo car's own.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

# NRCs used by the simulator
GENERAL_REJECT, SERVICE_NOT_SUPPORTED, SUBFUNCTION_NOT_SUPPORTED, BAD_LENGTH = 0x10, 0x11, 0x12, 0x13
CONDITIONS_NOT_CORRECT, SEQUENCE_ERROR, OUT_OF_RANGE, SECURITY_DENIED = 0x22, 0x24, 0x31, 0x33
INVALID_KEY, EXCEEDED_ATTEMPTS, DELAY_NOT_EXPIRED, PENDING = 0x35, 0x36, 0x37, 0x78
SERVICE_NOT_IN_SESSION, SUB_NOT_IN_SESSION = 0x7F, 0x7E
ENGINE_RUNNING, ENGINE_NOT_RUNNING, SPEED_TOO_HIGH, TEMP_TOO_LOW = 0x83, 0x84, 0x88, 0x87

S3_TIMEOUT = 5.0
AVAILABILITY = 0xAF       # status bits the Demo car supports (not the "test not completed" bits 4 and 6)


def demo_key(seed: bytes, level: int) -> bytes:
    """The Demo car's seed/key (simulator only; not any real control unit's algorithm). The test / tutorial
    plug-in radide/cardiag/sim/demo_seedkey.py implements the same thing as a user plug-in."""
    out = bytearray()
    for i, b in enumerate(seed):
        out.append(((b ^ 0x5A) + level + i * 7) & 0xFF)
    return bytes(out)


@dataclass
class SimDtc:
    code: int                         # 3-byte UDS DTC (SAE 2 bytes + failure type)
    status: int                       # ISO 14229 status byte
    emission: bool = False            # reported by OBD modes 03 / 07 (engine)
    permanent: bool = False           # OBD mode 0A / UDS 0x19 0x15
    recurs_after: float | None = None     # still faulty: comes back (pending) after this many "condition" seconds
    recur_condition: str = "running"      # "running" / "driving" / "ignition" / "always"
    snapshot: dict = field(default_factory=dict)      # did -> bytes (record 1)
    occurrences: int = 1
    aging: int = 0
    cleared_at: float | None = None
    _accum: float = 0.0
    _perm_accum: float = 0.0
    permanent_clears_after: float = 30.0    # driving seconds without the fault before a permanent DTC goes

    @property
    def sae(self) -> int:
        return self.code >> 8

    @property
    def visible(self) -> bool:
        return bool(self.status & AVAILABILITY)


@dataclass
class SimRoutine:
    rid: int
    name: str
    duration: float = 0.0             # seconds (0 = instant)
    session: int = 0x03               # required session (0 = any)
    security: int = 0                 # required security level (0 = none)
    pre: object = None                # callable(ecu, params) -> NRC or 0
    pending: float = 0.0              # answer start with 7F 31 78 then the positive answer after this delay
    on_start: object = None           # callable(ecu, params)
    on_done: object = None            # callable(ecu)
    abort_if: object = None           # callable(ecu) -> bool while running
    results: object = None            # callable(ecu, routine) -> bytes (after status + progress)
    stoppable: bool = True
    state: int = 0                    # 0 idle, 1 running, 2 completed, 3 aborted, 4 stopped
    started: float = 0.0
    params: bytes = b""

    def progress(self, now: float) -> int:
        if self.state == 2:
            return 100
        if self.state != 1 or self.duration <= 0:
            return 0
        return min(100, int((now - self.started) * 100 / self.duration))


@dataclass
class SimIo:
    did: int
    name: str
    size: int = 1
    value: bytes = b"\x00"
    default: bytes = b"\x00"
    pre: object = None                # callable(ecu, state) -> NRC or 0
    session: int = 0x03
    controlled: bool = False
    since: float = 0.0
    max_time: float = 10.0            # actuator tests stop by themselves (safety)


class SimEcu:
    def __init__(self, car, key: str, name: str, tx: int, rx: int, addr: int, *, obd: bool = False,
                 kline: bool = False, clear_specific: bool = True):
        self.car = car
        self.key, self.name = key, name
        self.tx, self.rx, self.addr = tx, rx, addr          # 11-bit ids, 29-bit / K-line address
        self.obd = obd
        self.kline = kline
        self.clear_specific = clear_specific
        self.dids: dict[int, object] = {}                   # did -> bytes | callable() -> bytes
        self.writable: dict[int, tuple[int, int]] = {}      # did -> (session, security level)
        self.dtcs: list[SimDtc] = []
        self.routines: dict[int, SimRoutine] = {}
        self.ios: dict[int, SimIo] = {}
        self.kwp_local: dict[int, object] = {}              # KWP 0x21 local id -> callable() -> bytes
        self.kwp_routines: dict[int, int] = {}              # KWP local routine id -> UDS routine id
        self.snapshot_dids: dict[int, int] = {}             # did -> length (for the client's parse)
        self.session = 0x01
        self.unlocked = 0
        self.seed: bytes = b""
        self.seed_level = 0
        self.attempts = 0
        self.locked_until = 0.0
        self.last_rx = 0.0
        self.extra_handlers: dict[int, object] = {}         # sid -> callable(ecu, req) -> answer list

    # ------------------------------------------------------------------ helpers
    def now(self) -> float:
        return self.car.now()

    @staticmethod
    def pos(req: bytes, body: bytes = b"") -> list[tuple[float, bytes]]:
        return [(0.0, bytes([(req[0] + 0x40) & 0xFF]) + body)]

    @staticmethod
    def neg(sid: int, code: int) -> list[tuple[float, bytes]]:
        return [(0.0, bytes([0x7F, sid, code]))]

    def did_value(self, did: int) -> bytes | None:
        v = self.dids.get(did)
        if v is None:
            return None
        return bytes(v()) if callable(v) else bytes(v)

    def tick(self) -> None:
        """Time-based behaviour: S3 time-out, routines finishing, actuator time limits, faults returning."""
        now = self.now()
        if self.session != 0x01 and self.last_rx and now - self.last_rx > S3_TIMEOUT:
            self.session = 0x01
            self.unlocked = 0
            self._session_ended()
        for r in self.routines.values():
            if r.state == 1:
                if r.abort_if is not None and r.abort_if(self):
                    r.state = 3
                elif r.duration <= 0 or now - r.started >= r.duration:
                    r.state = 2
                    if r.on_done is not None:
                        r.on_done(self)
        for io in self.ios.values():
            if io.controlled and now - io.since > io.max_time:
                io.controlled = False
                io.value = io.default

    def _session_ended(self) -> None:
        for r in self.routines.values():
            if r.state == 1 and r.session not in (0, 0x01):
                r.state = 3
        for io in self.ios.values():
            io.controlled = False
            io.value = io.default

    def advance_faults(self, dt: float) -> None:
        car = self.car
        for d in self.dtcs:
            if d.permanent and d.cleared_at is not None and not d.status & 0x01 and car.engine_running \
                    and car.speed > 5:
                d._perm_accum += dt                      # the monitor ran and passed: permanent DTC erased
                if d._perm_accum >= d.permanent_clears_after:
                    d.permanent = False
            if d.recurs_after is None or d.status & 0x01:
                continue
            cond = {"running": car.engine_running, "driving": car.engine_running and car.speed > 5,
                    "ignition": car.ignition, "always": True}.get(d.recur_condition, False)
            if cond and d.cleared_at is not None:
                d._accum += dt
                if d._accum >= d.recurs_after:
                    d.status |= 0x01 | 0x02 | 0x04 | 0x20      # failing again: pending this cycle
                    d.occurrences += 1
                    d._accum = 0.0

    # ------------------------------------------------------------------ dispatch
    def handle(self, req: bytes, functional: bool = False, can: bool = True) -> list[tuple[float, bytes]]:
        if not req or not self.car.ignition:
            return []
        self.tick()
        self.last_rx = self.now()
        sid = req[0]
        if sid <= 0x0A:
            if not self.obd:
                return []
            from .obd import handle_obd
            return handle_obd(self, req, can)
        if functional and (not self.obd or sid not in (0x3E, 0x10, 0x14, 0x11, 0x19, 0x22)):
            return []                        # 0x7DF / 0x18DB33F1 reach the emissions-related units only
        if self.car.kwp_mode and self.kline:
            from .kwp import handle_kwp
            got = handle_kwp(self, req)
            if got is not None:
                return got
        fn = self.extra_handlers.get(sid)
        if fn is not None:
            return fn(self, req)
        h = getattr(self, f"_s{sid:02x}", None)
        if h is None:
            return [] if functional else self.neg(sid, SERVICE_NOT_SUPPORTED)
        out = h(req)
        if functional and out and out[0][1][:1] == b"\x7F" and out[0][1][2] in (SERVICE_NOT_SUPPORTED,
                                                                                OUT_OF_RANGE,
                                                                                SUBFUNCTION_NOT_SUPPORTED):
            return []                        # no negative answers to functional requests for those codes
        return out

    # ------------------------------------------------------------------ 0x10 / 0x3E / 0x11
    def _s10(self, req):
        if len(req) != 2:
            return self.neg(0x10, BAD_LENGTH)
        sub, suppress = req[1] & 0x7F, req[1] & 0x80
        if sub not in (0x01, 0x02, 0x03):
            return self.neg(0x10, SUBFUNCTION_NOT_SUPPORTED)
        if sub == 0x02:
            return self.neg(0x10, CONDITIONS_NOT_CORRECT)       # no reprogramming in the Demo car
        if sub != self.session:
            self.unlocked = 0
            if sub == 0x01:
                self._session_ended()
        self.session = sub
        return [] if suppress else self.pos(req, bytes([sub, 0x00, 0x32, 0x01, 0xF4]))

    def _s3e(self, req):
        if len(req) != 2 or req[1] & 0x7F:
            return self.neg(0x3E, SUBFUNCTION_NOT_SUPPORTED)
        return [] if req[1] & 0x80 else self.pos(req, b"\x00")

    def _s11(self, req):
        if len(req) != 2 or (req[1] & 0x7F) not in (0x01, 0x02, 0x03):
            return self.neg(0x11, SUBFUNCTION_NOT_SUPPORTED)
        if self.car.engine_running:
            return self.neg(0x11, CONDITIONS_NOT_CORRECT)
        self.session, self.unlocked = 0x01, 0
        self._session_ended()
        return [] if req[1] & 0x80 else self.pos(req, bytes([req[1] & 0x7F]))

    # ------------------------------------------------------------------ 0x14 / 0x19
    def clear(self, group: int) -> bool:
        now = self.now()
        hit = False
        for d in self.dtcs:
            if group == 0xFFFFFF or (group == 0xFFFF33 and d.emission) or group in (d.code, d.code & 0xFFFF00):
                hit = True
                active = d.recurs_after == 0
                d.status = 0x50 if not active else 0x50 | 0x01 | 0x02 | 0x08 | 0x20
                d.cleared_at = now
                d._accum = 0.0
                d.snapshot = d.snapshot if active else {}
        return hit

    def _s14(self, req):
        if len(req) != 4:
            return self.neg(0x14, BAD_LENGTH)
        group = int.from_bytes(req[1:4], "big")
        if group not in (0xFFFFFF, 0xFFFF33):
            if not self.clear_specific:
                return self.neg(0x14, OUT_OF_RANGE)
            if not any(group in (d.code, d.code & 0xFFFF00) for d in self.dtcs):
                return self.neg(0x14, OUT_OF_RANGE)
        self.clear(group)
        self.car.on_dtcs_cleared(self)
        return self.pos(req)

    def _avail_mask(self) -> int:
        return AVAILABILITY

    def _s19(self, req):
        if len(req) < 2:
            return self.neg(0x19, BAD_LENGTH)
        sub = req[1]
        if sub in (0x01, 0x02):
            if len(req) != 3:
                return self.neg(0x19, BAD_LENGTH)
            mask = req[2]
            hits = [d for d in self.dtcs if d.status & mask & AVAILABILITY]
            if sub == 0x01:
                return self.pos(req, bytes([0x01, self._avail_mask(), 0x01]) + len(hits).to_bytes(2, "big"))
            body = bytes([0x02, self._avail_mask()])
            for d in hits:
                body += d.code.to_bytes(3, "big") + bytes([d.status])
            return self.pos(req, body)
        if sub == 0x03:
            body = b"\x03"
            for d in self.dtcs:
                if d.snapshot and d.visible:
                    body += d.code.to_bytes(3, "big") + b"\x01"
            return self.pos(req, body)
        if sub in (0x04, 0x06):
            if len(req) != 6:
                return self.neg(0x19, BAD_LENGTH)
            code, rec = int.from_bytes(req[2:5], "big"), req[5]
            d = next((x for x in self.dtcs if x.code == code), None)
            if d is None:
                return self.neg(0x19, OUT_OF_RANGE)
            body = bytes([sub]) + d.code.to_bytes(3, "big") + bytes([d.status])
            if sub == 0x04:
                if d.snapshot and rec in (0x01, 0xFF):
                    body += bytes([0x01, len(d.snapshot)])
                    for did, val in d.snapshot.items():
                        body += did.to_bytes(2, "big") + bytes(val)
                elif rec not in (0x01, 0xFF):
                    return self.neg(0x19, OUT_OF_RANGE)
            else:
                ext = {0x01: d.occurrences & 0xFF, 0x02: d.aging & 0xFF}
                if rec == 0xFF:
                    for k, v in ext.items():
                        body += bytes([k, v])
                elif rec in ext:
                    body += bytes([rec, ext[rec]])
                else:
                    return self.neg(0x19, OUT_OF_RANGE)
            return self.pos(req, body)
        if sub == 0x0A:
            body = bytes([0x0A, self._avail_mask()])
            for d in self.dtcs:
                body += d.code.to_bytes(3, "big") + bytes([d.status])
            return self.pos(req, body)
        if sub == 0x15:
            body = bytes([0x15, self._avail_mask()])
            for d in self.dtcs:
                if d.permanent:
                    body += d.code.to_bytes(3, "big") + bytes([d.status])
            return self.pos(req, body)
        return self.neg(0x19, SUBFUNCTION_NOT_SUPPORTED)

    # ------------------------------------------------------------------ 0x22 / 0x2E
    def _s22(self, req):
        if len(req) < 3 or len(req) % 2 == 0:
            return self.neg(0x22, BAD_LENGTH)
        body = b""
        for i in range(1, len(req), 2):
            did = int.from_bytes(req[i:i + 2], "big")
            v = self.did_value(did)
            if v is None:
                if len(req) == 3:
                    return self.neg(0x22, OUT_OF_RANGE)
                continue
            body += did.to_bytes(2, "big") + v
        if not body:
            return self.neg(0x22, OUT_OF_RANGE)
        return self.pos(req, body)

    def _s2e(self, req):
        if len(req) < 4:
            return self.neg(0x2E, BAD_LENGTH)
        did = int.from_bytes(req[1:3], "big")
        if did not in self.writable:
            return self.neg(0x2E, OUT_OF_RANGE)
        sess, sec = self.writable[did]
        if sess and self.session != sess:
            return self.neg(0x2E, SERVICE_NOT_IN_SESSION)
        if sec and self.unlocked != sec:
            return self.neg(0x2E, SECURITY_DENIED)
        old = self.did_value(did)
        if old is not None and len(old) != len(req) - 3:
            return self.neg(0x2E, BAD_LENGTH)
        self.dids[did] = bytes(req[3:])
        return self.pos(req, req[1:3])

    # ------------------------------------------------------------------ 0x27 (Demo car seed/key)
    def _s27(self, req):
        if len(req) < 2:
            return self.neg(0x27, BAD_LENGTH)
        sub = req[1] & 0x7F
        now = self.now()
        if sub % 2:                                          # request seed
            if self.session == 0x01:
                return self.neg(0x27, SERVICE_NOT_IN_SESSION)
            if now < self.locked_until:
                return self.neg(0x27, DELAY_NOT_EXPIRED)
            if sub != 0x01:
                return self.neg(0x27, SUBFUNCTION_NOT_SUPPORTED)
            if self.unlocked == sub:
                return self.pos(req, bytes([sub]) + b"\x00\x00\x00\x00")
            self.seed = os.urandom(4)
            if not any(self.seed):
                self.seed = b"\x12\x34\x56\x78"
            self.seed_level = sub
            return self.pos(req, bytes([sub]) + self.seed)
        if not self.seed or sub != self.seed_level + 1:
            return self.neg(0x27, SEQUENCE_ERROR)
        if bytes(req[2:]) != demo_key(self.seed, self.seed_level):
            self.attempts += 1
            self.seed = b""
            if self.attempts >= 3:
                self.attempts = 0
                self.locked_until = now + 10.0
                return self.neg(0x27, EXCEEDED_ATTEMPTS)
            return self.neg(0x27, INVALID_KEY)
        self.unlocked = self.seed_level
        self.attempts = 0
        self.seed = b""
        return self.pos(req, bytes([sub]))

    # ------------------------------------------------------------------ 0x31 routines
    def _s31(self, req):
        if len(req) < 4:
            return self.neg(0x31, BAD_LENGTH)
        sub, rid = req[1] & 0x7F, int.from_bytes(req[2:4], "big")
        r = self.routines.get(rid)
        if r is None:
            return self.neg(0x31, OUT_OF_RANGE)
        if sub not in (1, 2, 3):
            return self.neg(0x31, SUBFUNCTION_NOT_SUPPORTED)
        if r.session and self.session != r.session and not (r.session == 0x03 and self.session == 0x03):
            return self.neg(0x31, SERVICE_NOT_IN_SESSION)
        if r.security and self.unlocked != r.security:
            return self.neg(0x31, SECURITY_DENIED)
        now = self.now()
        head = bytes([sub]) + rid.to_bytes(2, "big")
        if sub == 1:
            if r.state == 1:
                return self.neg(0x31, SEQUENCE_ERROR)
            if r.pre is not None:
                code = r.pre(self, bytes(req[4:]))
                if code:
                    return self.neg(0x31, code)
            r.state, r.started, r.params = 1, now, bytes(req[4:])
            if r.on_start is not None:
                r.on_start(self, r.params)
            if r.duration <= 0:
                r.state = 2
                if r.on_done is not None:
                    r.on_done(self)
            answer = bytes([0x71]) + head + bytes([r.state])
            if r.pending:
                return [(0.0, bytes([0x7F, 0x31, PENDING])), (r.pending, answer)]
            return [(0.0, answer)]
        if sub == 2:
            if not r.stoppable:
                return self.neg(0x31, SUBFUNCTION_NOT_SUPPORTED)
            if r.state != 1:
                return self.neg(0x31, SEQUENCE_ERROR)
            r.state = 4
            return self.pos(req, head + b"\x04")
        self.tick()
        if r.state == 0:
            return self.neg(0x31, SEQUENCE_ERROR)
        extra = r.results(self, r) if r.results is not None else b""
        return self.pos(req, head + bytes([r.state, r.progress(now)]) + bytes(extra))

    # ------------------------------------------------------------------ 0x2F actuator tests
    def _s2f(self, req):
        if len(req) < 4:
            return self.neg(0x2F, BAD_LENGTH)
        did, param = int.from_bytes(req[1:3], "big"), req[3]
        io = self.ios.get(did)
        if io is None:
            return self.neg(0x2F, OUT_OF_RANGE)
        if io.session and self.session != io.session:
            return self.neg(0x2F, SERVICE_NOT_IN_SESSION)
        if param == 0x00:
            io.controlled, io.value = False, io.default
        elif param == 0x01:
            io.controlled, io.value = False, io.default
        elif param == 0x02:
            io.controlled, io.since = True, self.now()
        elif param == 0x03:
            state = bytes(req[4:4 + io.size])
            if len(state) != io.size:
                return self.neg(0x2F, BAD_LENGTH)
            if io.pre is not None:
                code = io.pre(self, state)
                if code:
                    return self.neg(0x2F, code)
            io.controlled, io.value, io.since = True, state, self.now()
        else:
            return self.neg(0x2F, OUT_OF_RANGE)
        return self.pos(req, req[1:4] + io.value)

    # ------------------------------------------------------------------ state for the UI / tests
    def summary(self) -> dict:
        return {"key": self.key, "name": self.name, "tx": self.tx, "rx": self.rx, "session": self.session,
                "dtcs": [(d.code, d.status) for d in self.dtcs if d.visible]}


def wait_until(pred, timeout: float = 5.0, step: float = 0.02) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(step)
    return pred()
