"""The Demo car for the service functions: a small UDS (ISO 14229) vehicle simulator, written for RAD IDE.

Three control units answer on CAN-style physical addresses:

* **Engine** (7E0 / 7E8) - sessions, tester present, ReadDataByIdentifier (VIN, coolant temperature, engine
  speed, battery voltage, cooling-fan duty, service counter ...), WriteDataByIdentifier (service reset,
  battery registration, a demo feature-coding byte behind security level 1), RoutineControl (cooling-system
  bleed with progress and response-pending, throttle adaptation reset), InputOutputControl (cooling fan,
  electric coolant pump), ReadDTCInformation 0x19 02, ClearDiagnosticInformation 0x14 (all or one DTC),
  OBD-II mode 03 / 04.
* **ABS / ESP** (760 / 768) - brake-pad service mode and steering-angle calibration routines, wheel-speed
  sensor fault C0035, single-DTC clear.
* **Airbag** (737 / 73F) - fault B0001 (driver frontal stage 1 deployment control); supports only "clear all"
  (answers NRC 0x31 to a single-DTC clear) so the fallback path of the clear flow can be tried.

All identifiers (RIDs / DIDs) here belong to this simulator only (see packs/demo_car.json); they are **not**
the identifiers of any real vehicle. The security-access check of the demo coding byte uses a deliberately
trivial rule of the simulated ECU (``demo_key_ok``); the tester side is the sample plug-in
samples/Tests/CarDiag/Service/demo_seedkey.py that the user selects like any licensed plug-in (RAD IDE's tester
code contains no seed/key algorithms).

Time comes from ``clock`` (``time.monotonic`` by default; tests use ``SimClock`` so a 20-second bleed routine
takes no real time).
"""
from __future__ import annotations

import os
import time

VIN = "RADDEM0CAR0000001"
S3_TIMEOUT = 5.0


class SimClock:
    """A fake clock: ``sleep(dt)`` moves the time forward instantly."""

    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def sleep(self, dt: float) -> None:
        self.t += max(0.0, float(dt))


def _dtc_bytes(code: str, ftb: int = 0) -> bytes:
    """'P0217' + failure type byte -> 3 bytes (SAE J2012 / ISO 15031-6 2-byte code + FTB)."""
    letter = "PCBU".index(code[0].upper())
    first = int(code[1], 16)
    v = (letter << 14) | (first << 12) | int(code[2:5], 16)
    return bytes([v >> 8, v & 0xFF, ftb & 0xFF])


def nrc(sid: int, code: int) -> bytes:
    return bytes([0x7F, sid, code])


class _Ecu:
    tx = rx = 0
    supports_single_clear = True
    name = "ECU"

    def __init__(self, car: "DemoCar"):
        self.car = car
        self.session = 1
        self.last = car.clock()
        self.security = 0
        self.seed = b""
        self.attempts = 0
        self.dtcs: dict[bytes, int] = {}         # 3-byte DTC -> status byte

    # ----------------------------------------------------------------- generic services
    def tick(self) -> None:
        now = self.car.clock()
        if self.session != 1 and now - self.last > S3_TIMEOUT:
            self.session = 1
            self.security = 0
            self.on_default_session()
        self.last = now

    def on_default_session(self) -> None:
        pass

    def handle(self, req: bytes) -> bytes:
        self.tick()
        if not req:
            return b""
        sid = req[0]
        fn = getattr(self, f"sid_{sid:02x}", None)
        if fn is None:
            return nrc(sid, 0x11)
        return fn(req)

    def sid_10(self, req):
        if len(req) != 2:
            return nrc(0x10, 0x13)
        if req[1] not in (1, 3):
            return nrc(0x10, 0x12)
        self.session = req[1]
        if req[1] == 1:
            self.security = 0
            self.on_default_session()
        return bytes([0x50, req[1], 0x00, 0x32, 0x01, 0xF4])

    def sid_3e(self, req):
        if len(req) != 2:
            return nrc(0x3E, 0x13)
        return b"" if req[1] & 0x80 else b"\x7E\x00"

    def sid_27(self, req):
        if len(req) < 2:
            return nrc(0x27, 0x13)
        if self.session == 1:
            return nrc(0x27, 0x7F)
        sub = req[1]
        if sub % 2:                                   # request seed
            if self.security >= sub:
                return bytes([0x67, sub, 0, 0, 0, 0])
            self.seed = os.urandom(4) if not self.car.fixed_seed else self.car.fixed_seed
            return bytes([0x67, sub]) + self.seed
        if not self.seed:
            return nrc(0x27, 0x24)
        ok = self.car.key_check(self.seed, sub - 1, req[2:])
        self.seed = b""
        if not ok:
            self.attempts += 1
            return nrc(0x27, 0x36 if self.attempts >= 3 else 0x35)
        self.attempts = 0
        self.security = sub - 1
        return bytes([0x67, sub])

    def sid_19(self, req):
        if len(req) < 3 or req[1] != 0x02:
            return nrc(0x19, 0x12 if len(req) >= 2 else 0x13)
        mask = req[2]
        out = bytearray([0x59, 0x02, 0xFF])
        for dtc, st in self.dtcs.items():
            if st & mask:
                out += dtc + bytes([st])
        return bytes(out)

    def sid_14(self, req):
        if len(req) != 4:
            return nrc(0x14, 0x13)
        group = req[1:4]
        if group == b"\xFF\xFF\xFF":
            self.dtcs.clear()
        elif not self.supports_single_clear:
            return nrc(0x14, 0x31)
        else:
            hits = [d for d in self.dtcs if d == group or (group[2] == 0 and d[:2] == group[:2])]
            if not hits:
                return nrc(0x14, 0x31)
            for d in hits:
                del self.dtcs[d]
        self.after_clear()
        return b"\x54"

    def after_clear(self) -> None:
        pass

    def secured(self, sid: int, level: int) -> bytes | None:
        if self.session == 1:
            return nrc(sid, 0x7F)
        if level and self.security < level:
            return nrc(sid, 0x33)
        return None


class EngineEcu(_Ecu):
    tx, rx, name = 0x7E0, 0x7E8, "Engine"
    RID_BLEED, RID_THROTTLE = 0x0203, 0x0204
    DID_FAN, DID_PUMP = 0xF0A0, 0xF0A1

    def __init__(self, car):
        super().__init__(car)
        self.dtcs = {_dtc_bytes("P0217", 0x00): 0x2F, _dtc_bytes("P0128", 0x00): 0x28}
        self.service_km = 1200            # km to next service (counts down)
        self.service_days = 20
        self.battery_ah = 70
        self.battery_type = 1             # 1 = flooded, 2 = EFB, 3 = AGM
        self.coding_drl = 0
        self.bleed = None                 # {"start": t, "aborted": bool}
        self.throttle_learned = True
        self.overrides: dict[int, int] = {}       # IO DID -> value set by the tester

    def on_default_session(self):
        self.overrides.clear()            # leaving the session returns control (ISO 14229)
        if self.bleed and self._bleed_state()[0] == 1:
            self.bleed["aborted"] = True

    # ---------------------------------------------------------------- data
    def did_value(self, did: int) -> bytes | None:
        c = self.car
        if did == 0xF190:
            return VIN.encode()
        if did == 0xF405:
            return bytes([max(0, min(255, int(round(c.coolant_c + 40))))])
        if did == 0xF40C:
            rpm = 780 if c.engine_running else 0
            return (rpm * 4).to_bytes(2, "big")
        if did == 0xF40D:
            return bytes([int(c.speed_kmh)])
        if did == 0xF442:
            return int(c.battery_v * 1000).to_bytes(2, "big")
        if did == 0xF101:
            return bytes([1 if c.engine_running else 0])
        if did == 0xF102:
            return bytes([1 if c.ignition else 0])
        if did == self.DID_FAN:
            return bytes([self.fan_duty()])
        if did == self.DID_PUMP:
            return bytes([self.pump_duty()])
        if did == 0xF1A0:
            return self.service_km.to_bytes(2, "big") + bytes([self.service_days])
        if did == 0xF1A1:
            return bytes([1 if self.throttle_learned else 0])
        if did == 0xF1A2:
            return bytes([self.battery_ah, self.battery_type])
        if did == 0xF1A3:
            return bytes([self.coding_drl])
        return None

    def fan_duty(self) -> int:
        if self.DID_FAN in self.overrides:
            return self.overrides[self.DID_FAN]
        if self.bleed and self._bleed_state()[0] == 1:
            return 30
        return 100 if self.car.coolant_c > 100 else (40 if self.car.coolant_c > 92 else 0)

    def pump_duty(self) -> int:
        if self.DID_PUMP in self.overrides:
            return self.overrides[self.DID_PUMP]
        if self.bleed and self._bleed_state()[0] == 1:
            return 80
        return 50 if self.car.engine_running else 0

    def sid_22(self, req):
        if len(req) < 3 or len(req) % 2 == 0:
            return nrc(0x22, 0x13)
        out = bytearray([0x62])
        for i in range(1, len(req), 2):
            did = int.from_bytes(req[i:i + 2], "big")
            v = self.did_value(did)
            if v is None:
                return nrc(0x22, 0x31)
            out += req[i:i + 2] + v
        return bytes(out)

    def sid_2e(self, req):
        if len(req) < 4:
            return nrc(0x2E, 0x13)
        did = int.from_bytes(req[1:3], "big")
        data = req[3:]
        if did not in (0xF1A0, 0xF1A2, 0xF1A3):
            return nrc(0x2E, 0x31)
        bad = self.secured(0x2E, 1 if did == 0xF1A3 else 0)
        if bad:
            return bad
        if did == 0xF1A0:
            if len(data) != 3:
                return nrc(0x2E, 0x13)
            if data != b"\x00\x00\x00":
                return nrc(0x2E, 0x31)        # the demo only accepts "reset" (00 00 00)
            self.service_km, self.service_days = 15000, 180
        elif did == 0xF1A2:
            if len(data) != 2:
                return nrc(0x2E, 0x13)
            if not 40 <= data[0] <= 120 or data[1] not in (1, 2, 3):
                return nrc(0x2E, 0x31)
            if self.car.engine_running:
                return nrc(0x2E, 0x22)
            self.battery_ah, self.battery_type = data[0], data[1]
        else:
            if len(data) != 1 or data[0] > 1:
                return nrc(0x2E, 0x31)
            self.coding_drl = data[0]
        return bytes([0x6E]) + req[1:3]

    # ---------------------------------------------------------------- routines
    def _bleed_state(self):
        """(status, progress %, air remaining %): status 1 running, 2 done, 3 aborted."""
        b = self.bleed
        if b is None:
            return 0, 0, 0
        if b["aborted"]:
            return 3, b.get("progress", 0), max(0, 100 - b.get("progress", 0))
        p = min(100, int((self.car.clock() - b["start"]) * 100 / self.car.bleed_seconds))
        b["progress"] = p
        if self.car.coolant_c >= 40 and p < 100:            # warmed up during the bleed -> abort
            b["aborted"] = True
            return 3, p, 100 - p
        return (2 if p >= 100 else 1), p, max(0, 100 - p)

    def sid_31(self, req):
        if len(req) < 4:
            return nrc(0x31, 0x13)
        sub, rid = req[1], int.from_bytes(req[2:4], "big")
        if sub not in (1, 2, 3):
            return nrc(0x31, 0x12)
        if rid not in (self.RID_BLEED, self.RID_THROTTLE):
            return nrc(0x31, 0x31)
        bad = self.secured(0x31, 0)
        if bad:
            return bad
        head = bytes([0x71, sub]) + req[2:4]
        if rid == self.RID_THROTTLE:
            if sub != 1:
                return nrc(0x31, 0x12)
            if self.car.engine_running:
                return nrc(0x31, 0x83)
            if not self.car.ignition:
                return nrc(0x31, 0x22)
            self.throttle_learned = True
            return head + b"\x02"
        # cooling-system bleed
        if sub == 1:
            if len(req) != 5 or req[4] not in (1, 2):
                return nrc(0x31, 0x31)
            if not self.car.ignition:
                return nrc(0x31, 0x22)
            if self.car.engine_running:
                return nrc(0x31, 0x83)
            if self.car.coolant_c >= 40:
                return nrc(0x31, 0x22)              # conditionsNotCorrect: engine too warm
            if self.car.battery_v < 12.0:
                return nrc(0x31, 0x93)
            if self.bleed and self._bleed_state()[0] == 1:
                return nrc(0x31, 0x24)
            self.bleed = {"start": self.car.clock(), "aborted": False}
            self.car.pending_once = True              # answer "response pending" first
            return head + b"\x01"
        if self.bleed is None:
            return nrc(0x31, 0x24)
        if sub == 2:
            if self._bleed_state()[0] == 1:
                self.bleed["aborted"] = True
            st, p, air = self._bleed_state()
            return head + bytes([st, p, air])
        if self.car.stall_results:                     # simulate an ECU that stops answering
            return b""
        st, p, air = self._bleed_state()
        return head + bytes([st, p, air])

    # ---------------------------------------------------------------- IO control
    def sid_2f(self, req):
        if len(req) < 4:
            return nrc(0x2F, 0x13)
        did, ctl = int.from_bytes(req[1:3], "big"), req[3]
        if did not in (self.DID_FAN, self.DID_PUMP):
            return nrc(0x2F, 0x31)
        bad = self.secured(0x2F, 0)
        if bad:
            return bad
        if ctl == 0x00:                                # returnControlToECU
            self.overrides.pop(did, None)
        elif ctl == 0x03:                              # shortTermAdjustment
            if len(req) != 5 or req[4] > 100:
                return nrc(0x2F, 0x31)
            if did == self.DID_FAN and self.car.speed_kmh > 0:
                return nrc(0x2F, 0x88)
            self.overrides[did] = req[4]
        else:
            return nrc(0x2F, 0x31)
        cur = self.fan_duty() if did == self.DID_FAN else self.pump_duty()
        return bytes([0x6F]) + req[1:4] + bytes([cur])

    # ---------------------------------------------------------------- DTC logic
    def after_clear(self):
        self.refresh_faults()

    def refresh_faults(self):
        """Faults whose cause is still present come back at once (like a real ECU)."""
        if self.car.coolant_c > 115:
            self.dtcs.setdefault(_dtc_bytes("P0217", 0x00), 0x2F)

    def sid_03(self, req):                             # OBD-II mode 03
        codes = [d[:2] for d, st in self.dtcs.items() if st & 0x08 and d[0] >> 6 == 0]
        return bytes([0x43, len(codes)]) + b"".join(codes)

    def sid_04(self, req):                             # OBD-II mode 04
        self.dtcs.clear()
        self.after_clear()
        return b"\x44"


class AbsEcu(_Ecu):
    tx, rx, name = 0x760, 0x768, "ABS / ESP"
    RID_PADS, RID_SAS = 0x0210, 0x0211

    def __init__(self, car):
        super().__init__(car)
        self.dtcs = {_dtc_bytes("C0035", 0x00): 0x09}
        self.pad_mode = False
        self.sas_calibrated = False

    def sid_22(self, req):
        if req[1:3] == b"\xF1\x90":
            return b"\x62\xF1\x90" + VIN.encode()
        if req[1:3] == b"\xF2\x10":
            return b"\x62\xF2\x10" + bytes([1 if self.pad_mode else 0])
        return nrc(0x22, 0x31)

    def sid_31(self, req):
        if len(req) < 4:
            return nrc(0x31, 0x13)
        sub, rid = req[1], int.from_bytes(req[2:4], "big")
        if rid not in (self.RID_PADS, self.RID_SAS):
            return nrc(0x31, 0x31)
        bad = self.secured(0x31, 0)
        if bad:
            return bad
        head = bytes([0x71, sub]) + req[2:4]
        if self.car.speed_kmh > 0:
            return nrc(0x31, 0x88)
        if rid == self.RID_PADS:
            if sub == 1:            # 01 = open (retract the electric parking brake), 02 = close
                if len(req) != 5 or req[4] not in (1, 2):
                    return nrc(0x31, 0x31)
                self.pad_mode = req[4] == 1
                return head + b"\x02"
            if sub == 3:
                return head + bytes([2, 1 if self.pad_mode else 0])
            return nrc(0x31, 0x12)
        if sub != 1:
            return nrc(0x31, 0x12)
        if self.car.engine_running is False:
            return nrc(0x31, 0x84)
        self.sas_calibrated = True
        return head + b"\x02\x00"


class AirbagEcu(_Ecu):
    tx, rx, name = 0x737, 0x73F, "Airbag"
    supports_single_clear = False

    def __init__(self, car):
        super().__init__(car)
        self.dtcs = {_dtc_bytes("B0001", 0x13): 0x08}

    def sid_22(self, req):
        if req[1:3] == b"\xF1\x90":
            return b"\x62\xF1\x90" + VIN.encode()
        return nrc(0x22, 0x31)


def demo_key_ok(seed: bytes, level: int, key: bytes) -> bool:
    """The simulated ECU's own check (Demo car only, level 1): key = seed bytes XOR 0x5A, reversed. The tester
    side lives in the sample plug-in samples/Tests/CarDiag/Service/demo_seedkey.py, not in RAD IDE."""
    return level == 1 and bytes(key) == bytes(b ^ 0x5A for b in reversed(seed))


class DemoCar:
    """The whole Demo car; ``handle(tx, request)`` returns the answer of the control unit at *tx*."""

    def __init__(self, clock=time.monotonic, bleed_seconds: float = 20.0):
        self.clock = clock
        self.bleed_seconds = float(bleed_seconds)
        self.ignition = True
        self.engine_running = False
        self.coolant_c = 24.0
        self.battery_v = 12.6
        self.speed_kmh = 0.0
        self.pending_once = False
        self.stall_results = False
        self.fixed_seed = b""
        self.key_check = demo_key_ok
        self.ecus = {e.tx: e for e in (EngineEcu(self), AbsEcu(self), AirbagEcu(self))}
        self.engine: EngineEcu = self.ecus[0x7E0]
        self.abs: AbsEcu = self.ecus[0x760]
        self.airbag: AirbagEcu = self.ecus[0x737]

    def handle(self, tx: int, req: bytes) -> bytes:
        ecu = self.ecus.get(tx)
        if ecu is None or not self.ignition and req[:1] != b"\x10":
            return b""
        return ecu.handle(bytes(req))


class DemoTransport:
    """A transport (see transport.py) talking to a DemoCar, with response-pending for long requests."""

    def __init__(self, car: DemoCar | None = None):
        self.car = car or DemoCar()
        self._queued: dict[int, bytes] = {}
        self.log: list[tuple[int, bytes, bytes]] = []

    def exchange(self, req: bytes, tx: int, rx: int = 0, timeout: float = 2.0) -> bytes:
        resp = self.car.handle(tx, req)
        self.log.append((tx, bytes(req), bytes(resp)))
        if self.car.pending_once and resp and resp[0] != 0x7F:
            self.car.pending_once = False
            self._queued[tx] = resp
            return bytes([0x7F, req[0], 0x78])
        if not resp:
            raise TimeoutError("no answer")
        return resp

    def receive(self, tx: int, rx: int = 0, timeout: float = 2.0) -> bytes:
        resp = self._queued.pop(tx, b"")
        if not resp:
            raise TimeoutError("no answer")
        return resp
