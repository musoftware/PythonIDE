"""Demo vehicle for the OBD-II scan tool: answers SAE J1979 modes 01-0A like a real car's engine (7E8) and
transmission (7E9) computers.  Original code; no manufacturer data.  The VIN, calibration ids and CVNs are made up.

The engine warms up and drives a repeating 60-second cycle (idle - accelerate - cruise - slow down - idle).  Sim
time follows the wall clock, or only `advance(seconds)` when created with ``realtime=False`` (tests).

Faults of the demo car (a typical workshop case):
* engine: stored P0301 (cylinder 1 misfire, MIL on, freeze frame) and P0171 (system too lean bank 1, MIL on,
  long-term fuel trim +9 %), pending P0420 (catalyst efficiency), permanent P0301;
* transmission: stored P0715 (input / turbine speed sensor), freeze frame.

Mode 04 clears the stored and pending codes, the freeze frames and the mode 06 results of both computers, turns
the MIL off and resets every non-continuous readiness monitor; driving then completes the monitors one by one
(the EVAP monitor stays incomplete: it needs a cold start after a long stop, as in a real car).  The permanent
code goes away once the misfire monitor has run without a fault (after the "repair" a clear represents).
"""
from __future__ import annotations

import math
import time

from . import readiness
from .dtc import encode as dtc_bytes

VIN = "XRDSM1C25T0000417"

ECM, TCM = "7E8", "7E9"
ECM_PIDS = {0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x13, 0x14, 0x15, 0x1C,
            0x1F, 0x21, 0x2E, 0x2F, 0x30, 0x31, 0x33, 0x3C, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x49, 0x4A,
            0x4C, 0x4D, 0x4E, 0x51, 0x5C, 0xA6}
TCM_PIDS = {0x01, 0x05, 0x0C, 0x0D, 0x41, 0xA4}
FF_PIDS = {0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11}
TCM_FF_PIDS = {0x02, 0x05, 0x0C, 0x0D}

# monitor key -> seconds of driving (speed > 0) after a clear until it completes
MONITOR_TIMES = {"o2_heater": 40, "o2_sensor": 150, "egr": 210, "catalyst": 280, "evap": None}
SPARK_SUPPORTED = {"misfire": True, "fuel": True, "components": True, "catalyst": True, "evap": True,
                   "o2_sensor": True, "o2_heater": True, "egr": True}


def _pct(v):
    return max(0, min(255, round(v * 255 / 100)))


def _trim(v):
    return max(0, min(255, round((v + 100) * 128 / 100)))


def _u16(v):
    v = max(0, min(0xFFFF, int(round(v))))
    return bytes([v >> 8, v & 0xFF])


class Ecu:
    def __init__(self, name, pids, ff_pids):
        self.name, self.pids, self.ff_pids = name, set(pids), set(ff_pids)
        self.stored: list[str] = []
        self.pending: list[str] = []
        self.permanent: list[str] = []
        self.mil_codes: set[str] = set()
        self.freeze: dict | None = None              # {"dtc": "P0301", pid: data bytes}


def _bitmap(pids, base):
    bits = 0
    for p in pids:
        if base < p <= base + 32:
            bits |= 1 << (32 - (p - base))
    if any(p > base + 32 for p in pids):
        bits |= 1                                     # next range supported
    return bits.to_bytes(4, "big")


class DemoVehicle:
    def __init__(self, realtime: bool = True, start_temp: float = 22.0):
        self.realtime = realtime
        self.t = 0.0
        self._wall = time.monotonic()
        self.start_temp = start_temp
        self.odometer_km = 48213.4
        self.fuel_pct = 62.0
        self.ecus = {ECM: Ecu(ECM, ECM_PIDS, FF_PIDS), TCM: Ecu(TCM, TCM_PIDS, TCM_FF_PIDS)}
        e, tc = self.ecus[ECM], self.ecus[TCM]
        e.stored, e.pending, e.permanent = ["P0301", "P0171"], ["P0420"], ["P0301"]
        e.mil_codes = {"P0301", "P0171"}
        e.freeze = {"dtc": "P0301", 0x03: bytes([2, 0]), 0x04: bytes([_pct(46)]), 0x05: bytes([88 + 40]),
                    0x06: bytes([_trim(3.1)]), 0x07: bytes([_trim(9.4)]), 0x0B: bytes([54]),
                    0x0C: _u16(2150 * 4), 0x0D: bytes([72]), 0x0E: bytes([int((18 + 64) * 2)]),
                    0x0F: bytes([31 + 40]), 0x10: _u16(1450), 0x11: bytes([_pct(21)])}
        tc.stored, tc.mil_codes = ["P0715"], {"P0715"}
        tc.freeze = {"dtc": "P0715", 0x05: bytes([84 + 40]), 0x0C: _u16(1900 * 4), 0x0D: bytes([64])}
        self.cleared = False
        self.since_clear_drive = 0.0                  # seconds driven since the last clear
        self.since_clear_time = 3 * 3600.0 + 1800     # seconds (PID 4E) - the codes were cleared long ago
        self.dist_since_clear = 1873.0
        self.warmups = 41
        self.mil_dist = 112.0
        self.mil_time = 154.0 * 60
        self.complete = {k: True for k in SPARK_SUPPORTED}
        self.drive_complete = {k: False for k in SPARK_SUPPORTED}   # this drive cycle (PID 41)
        self.drive_complete.update(misfire=True, fuel=True, components=True)
        self.requests = 0

    # ------------------------------------------------------------------ time
    def _sync(self) -> None:
        if self.realtime:
            now = time.monotonic()
            self.advance(now - self._wall)
            self._wall = now

    def advance(self, seconds: float) -> None:
        """Move sim time forward (drives the car: distance, fuel, readiness monitors)."""
        step = 0.5
        left = max(0.0, float(seconds))
        while left > 0:
            dt = min(step, left)
            left -= dt
            self.t += dt
            v = self.speed()
            km = v * dt / 3600.0
            self.odometer_km += km
            self.fuel_pct = max(5.0, self.fuel_pct - km * 0.06)
            self.since_clear_time += dt
            self.dist_since_clear += km
            if v > 0:
                self.since_clear_drive += dt
                for key, need in MONITOR_TIMES.items():
                    if need is not None and self.since_clear_drive >= need:
                        if not self.complete.get(key):
                            self.complete[key] = True
                        self.drive_complete[key] = True
            if self.cleared and self.since_clear_drive >= 90:
                e = self.ecus[ECM]
                if "P0301" in e.permanent:                 # the misfire monitor ran clean after the repair
                    e.permanent.remove("P0301")
            if any(e.mil_codes for e in self.ecus.values()):
                self.mil_dist += km
                self.mil_time += dt

    # ------------------------------------------------------------------ engine model
    def phase(self) -> tuple[str, float]:
        c = self.t % 60.0
        if c < 10:
            return "idle", c / 10
        if c < 25:
            return "accelerate", (c - 10) / 15
        if c < 45:
            return "cruise", (c - 25) / 20
        if c < 55:
            return "decelerate", (c - 45) / 10
        return "idle", (c - 55) / 5

    def speed(self) -> float:
        ph, f = self.phase()
        return {"idle": 0.0, "accelerate": 80.0 * f, "cruise": 80.0 + 4 * math.sin(self.t / 3),
                "decelerate": 80.0 * (1 - f)}[ph]

    def rpm(self) -> float:
        ph, f = self.phase()
        v = self.speed()
        if ph == "idle" or v < 3:
            base = 780 + (150 if self.coolant() < 50 else 0)
            return base + 15 * math.sin(self.t * 2.1)        # small idle wobble (the misfire)
        gear_ratio = 45 if v < 20 else 30 if v < 40 else 26 if v < 60 else 23
        r = v * gear_ratio + (400 if ph == "accelerate" else 0)
        return max(800.0, min(6500.0, r))

    def throttle(self) -> float:
        ph, f = self.phase()
        return {"idle": 3.5, "accelerate": 18 + 22 * math.sin(f * math.pi), "cruise": 16.0,
                "decelerate": 0.0}[ph] + 0.3 * math.sin(self.t)

    def load(self) -> float:
        ph, _ = self.phase()
        return max(8.0, min(100.0, {"idle": 22.0, "accelerate": 62.0, "cruise": 38.0, "decelerate": 12.0}[ph]
                            + 2 * math.sin(self.t * 0.7)))

    def coolant(self) -> float:
        return 90.0 - (90.0 - self.start_temp) * math.exp(-self.t / 150.0) + 0.6 * math.sin(self.t / 9)

    def maf(self) -> float:
        return self.rpm() * self.load() / 100.0 * 1.6 / 120.0 * 1.18 * 0.95

    def map_kpa(self) -> float:
        return 25 + self.load() * 0.75

    def stft(self) -> float:
        return 2.5 * math.sin(self.t * 1.3) + (1.5 if not self.cleared else 0.0)

    def ltft(self) -> float:
        return 9.4 if not self.cleared else 3.9

    def o2_voltage(self, downstream=False) -> float:
        if downstream:
            return 0.62 + 0.05 * math.sin(self.t * 0.4)
        return 0.45 + 0.4 * math.sin(self.t * 6.3)

    def closed_loop(self) -> bool:
        return self.coolant() > 45 and self.phase()[0] != "decelerate"

    # ------------------------------------------------------------------ PIDs
    def pid_data(self, ecu: Ecu, pid: int) -> bytes | None:
        if pid % 0x20 == 0 and pid <= 0xC0:
            if pid and not any(p > pid for p in ecu.pids):
                return None
            return _bitmap(ecu.pids, pid)
        if pid not in ecu.pids:
            return None
        rpm, v = self.rpm(), self.speed()
        if pid in (0x01, 0x41):
            if ecu.name == TCM:
                sup = {"components": True}
                comp = {"components": True}
            else:
                sup = SPARK_SUPPORTED
                comp = self.complete if pid == 0x01 else self.drive_complete
            st = readiness.encode_status(bool(ecu.mil_codes), len(ecu.stored), False, sup, comp)
            return (b"\x00" + st[1:]) if pid == 0x41 else st
        f = {
            0x03: lambda: bytes([2 if self.closed_loop() else (1 if self.coolant() <= 45 else 4), 0]),
            0x04: lambda: bytes([_pct(self.load())]),
            0x05: lambda: bytes([int(round(self.coolant())) + 40]),
            0x06: lambda: bytes([_trim(self.stft())]),
            0x07: lambda: bytes([_trim(self.ltft())]),
            0x0B: lambda: bytes([int(self.map_kpa())]),
            0x0C: lambda: _u16(rpm * 4),
            0x0D: lambda: bytes([int(round(v))]),
            0x0E: lambda: bytes([int((10 + self.load() / 8 + 64) * 2)]),
            0x0F: lambda: bytes([31 + 40]),
            0x10: lambda: _u16(self.maf() * 100),
            0x11: lambda: bytes([_pct(self.throttle() + 12)]),
            0x13: lambda: bytes([0x03]),
            0x14: lambda: bytes([int(self.o2_voltage() * 200), _trim(self.stft())]),
            0x15: lambda: bytes([int(self.o2_voltage(True) * 200), 0xFF]),
            0x1C: lambda: bytes([7]),
            0x1F: lambda: _u16(self.t),
            0x21: lambda: _u16(self.mil_dist if ecu.mil_codes else 0),
            0x2E: lambda: bytes([_pct(12 if self.closed_loop() else 0)]),
            0x2F: lambda: bytes([_pct(self.fuel_pct)]),
            0x30: lambda: bytes([min(255, self.warmups)]),
            0x31: lambda: _u16(self.dist_since_clear),
            0x33: lambda: bytes([101]),
            0x3C: lambda: _u16((420 + self.load() * 3 + 40) * 10 if self.t > 30 else (self.coolant() + 40) * 10),
            0x42: lambda: _u16(14150 + 60 * math.sin(self.t / 5)),
            0x43: lambda: _u16(self.load() * 0.9 * 255 / 100),
            0x44: lambda: _u16((1.0 if self.closed_loop() else 0.92) * 32768),
            0x45: lambda: bytes([_pct(self.throttle())]),
            0x46: lambda: bytes([28 + 40]),
            0x47: lambda: bytes([_pct(self.throttle() + 14)]),
            0x49: lambda: bytes([_pct(self.throttle() * 1.4 + 15)]),
            0x4A: lambda: bytes([_pct(self.throttle() * 0.7 + 7)]),
            0x4C: lambda: bytes([_pct(self.throttle())]),
            0x4D: lambda: _u16(self.mil_time / 60 if ecu.mil_codes else 0),
            0x4E: lambda: _u16(self.since_clear_time / 60),
            0x51: lambda: bytes([1]),
            0x5C: lambda: bytes([int(self.coolant() - 4) + 40]),
            0xA4: lambda: bytes([0x03, self._gear() << 4, *_u16(self._gear_ratio() * 1000)]),
            0xA6: lambda: int(self.odometer_km * 10).to_bytes(4, "big"),
        }.get(pid)
        if pid == 0x05 and ecu.name == TCM:
            return bytes([int(round(self.coolant() - 6)) + 40])          # transmission oil temperature sensor
        return f() if f else None

    def _gear(self) -> int:
        v = self.speed()
        return 0 if v < 1 else 1 if v < 20 else 2 if v < 40 else 3 if v < 60 else 4 if v < 75 else 5

    def _gear_ratio(self) -> float:
        return {0: 0.0, 1: 3.45, 2: 2.05, 3: 1.37, 4: 1.03, 5: 0.84}[self._gear()]

    # ------------------------------------------------------------------ requests
    def handle(self, data: bytes) -> list[tuple[str, bytes]]:
        """One functional OBD request -> [(ecu, answer)] (no answer from computers that do not support it)."""
        self._sync()
        self.requests += 1
        data = bytes(data)
        if not data:
            return []
        mode, args = data[0], data[1:]
        out = []
        for name, ecu in self.ecus.items():
            r = self._answer(ecu, mode, args)
            if r is not None:
                out.append((name, r))
        return out

    def _answer(self, ecu: Ecu, mode: int, args: bytes) -> bytes | None:
        if mode == 0x01:
            body = b""
            for pid in args[:6]:
                d = self.pid_data(ecu, pid)
                if d is not None:
                    body += bytes([pid]) + d
            return b"\x41" + body if body else None
        if mode == 0x02:
            body = b""
            for i in range(0, len(args) - 1, 2):
                pid, frame = args[i], args[i + 1]
                d = self._freeze(ecu, pid, frame)
                if d is not None:
                    body += bytes([pid, frame]) + d
            return b"\x42" + body if body else None
        if mode in (0x03, 0x07, 0x0A):
            codes = {0x03: ecu.stored, 0x07: ecu.pending, 0x0A: ecu.permanent}[mode]
            return bytes([mode + 0x40, len(codes)]) + b"".join(dtc_bytes(c) for c in codes)
        if mode == 0x04:
            self._clear(ecu)
            return b"\x44"
        if mode == 0x06:
            return self._mode06(ecu, args[0] if args else 0)
        if mode == 0x09:
            return self._mode09(ecu, args[0] if args else 0)
        return None

    def _freeze(self, ecu: Ecu, pid: int, frame: int) -> bytes | None:
        if frame != 0:
            return None
        if pid % 0x20 == 0:
            if ecu.freeze is None:
                return None
            return _bitmap(ecu.ff_pids, pid) if pid == 0 else None
        if ecu.freeze is None or pid not in ecu.ff_pids:
            return None
        if pid == 0x02:
            return dtc_bytes(ecu.freeze["dtc"])
        return ecu.freeze.get(pid)

    def _clear(self, ecu: Ecu) -> None:
        ecu.stored, ecu.pending, ecu.mil_codes, ecu.freeze = [], [], set(), None
        if ecu.name == ECM:
            self.cleared = True
            self.since_clear_drive = 0.0
            self.since_clear_time = 0.0
            self.dist_since_clear = 0.0
            self.warmups = 0
            self.mil_dist = self.mil_time = 0.0
            for k in SPARK_SUPPORTED:
                if k not in ("misfire", "fuel", "components"):
                    self.complete[k] = False
                    self.drive_complete[k] = False

    # ------------------------------------------------------------------ mode 06
    def _tests(self, ecu: Ecu) -> dict[int, list[tuple[int, int, int, int, int]]]:
        """MID -> [(TID, UASID, value, min, max)] raw 16-bit numbers."""
        if ecu.name != ECM:
            return {}
        done = self.complete
        cyl1 = 0 if self.cleared else 38
        t = {}
        if done.get("o2_sensor"):
            t[0x01] = [(0x01, 0x0A, 3770, 3000, 4500), (0x02, 0x0A, 2210, 1500, 2800),
                       (0x05, 0x10, 72, 0, 160), (0x06, 0x10, 64, 0, 160)]
            t[0x02] = [(0x07, 0x0A, 410, 0, 1230), (0x08, 0x0A, 6550, 4900, 8200)]
        if done.get("catalyst"):
            t[0x21] = [(0x80, 0x20, 0x00A8 if not self.cleared else 0x0051, 0x0000, 0x0099)]   # pending P0420
        if done.get("egr"):
            t[0x31] = [(0x80, 0x17, 1450, 800, 6000)]
        if done.get("o2_heater"):
            t[0x41] = [(0x81, 0x14, 7, 3, 15)]
        if done.get("evap"):
            t[0x3C] = [(0x80, 0x29, 52, 0, 200)]
        t[0xA1] = [(0x0B, 0x24, cyl1, 0, 25), (0x0C, 0x24, cyl1 // 3, 0, 65535)]       # cylinder 1
        for c in range(1, 4):                                                        # cylinders 2-4
            t[0xA1 + c] = [(0x0B, 0x24, 1 if not self.cleared else 0, 0, 25), (0x0C, 0x24, 0, 0, 65535)]
        return t

    def _mode06(self, ecu: Ecu, mid: int) -> bytes | None:
        tests = self._tests(ecu)
        if not tests:
            return None
        mids = set(tests) | {0x01, 0x02, 0x21, 0x31, 0x41, 0x3C} if ecu.name == ECM else set(tests)
        if mid % 0x20 == 0:
            if mid and not any(m > mid for m in mids):
                return None
            return bytes([0x46, mid]) + _bitmap(mids, mid)
        if mid not in mids:
            return None
        rows = tests.get(mid) or [(0x80 if mid != 0x01 else 0x01, 0x01, 0, 0, 0)]    # not run since the clear
        out = b"\x46"
        for tid, uas, val, lo, hi in rows:
            out += bytes([mid, tid, uas]) + _u16(val) + _u16(lo) + _u16(hi)
        return out

    # ------------------------------------------------------------------ mode 09
    def _mode09(self, ecu: Ecu, info: int) -> bytes | None:
        ecm = ecu.name == ECM
        if info == 0x00:
            sup = {0x02, 0x04, 0x06, 0x0A} | ({0x08} if ecm else set())
            return b"\x49\x00" + _bitmap(sup, 0)
        if info == 0x02:
            return b"\x49\x02\x01" + VIN.encode() if ecm else None
        if info == 0x04:
            cal = (b"RADDEMO-ECM-0102", b"RADDEMO-ECM-OBD1") if ecm else (b"RADDEMO-TCM-0007",)
            return bytes([0x49, 0x04, len(cal)]) + b"".join(c.ljust(16, b"\x00") for c in cal)
        if info == 0x06:
            cvn = (bytes.fromhex("1A2B3C4D"), bytes.fromhex("00C0FFEE")) if ecm else (bytes.fromhex("5E6F7081"),)
            return bytes([0x49, 0x06, len(cvn)]) + b"".join(cvn)
        if info == 0x08 and ecm:
            ign = 1240 + int(self.t // 600)
            cond = 980 + int(self.t // 600)
            vals = [cond, ign, 312, 980, 0, 0, 645, 980, 0, 0, 455, 980, 0, 0, 98, 980, 501, 980, 0, 0]
            return bytes([0x49, 0x08, len(vals)]) + b"".join(_u16(v) for v in vals)
        if info == 0x0A:
            name = b"ECM\x00-EngineControl" if ecm else b"TCM\x00-TransmissionCtl"
            return b"\x49\x0a\x01" + name[:20].ljust(20, b"\x00")
        return None

    # ------------------------------------------------------------------ test helpers
    def inject(self, ecu: str, code: str, kind: str = "stored", mil: bool = True) -> None:
        e = self.ecus[ecu]
        getattr(e, kind).append(code)
        if mil and kind == "stored":
            e.mil_codes.add(code)
