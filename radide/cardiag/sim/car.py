"""The Demo car: an original virtual vehicle for testing everything without hardware.

Five control units (engine, ABS / ESP, airbag, instrument cluster, climate) on CAN 11-bit 500k by default (29-bit,
250k, ISO 9141-2, KWP2000 fast / 5-baud variants selectable), realistic live data that changes over time (warm
up, idle with a misfire, a drive profile), stored / pending / permanent DTCs with freeze frames and snapshots,
readiness monitors that complete while "driving", warning lamps, VIN, and service routines with preconditions:
cooling system bleed, throttle adaptation reset, fuel trim reset, injector test, battery registration, oil
service reset (answers "response pending" first), brake pad service position, steering angle calibration, plus
actuator tests (fan, coolant pump, injector cut-off, ABS pump, blower, A/C clutch).

Use it through the ELM327 interpreter (sim/elm.py: Demo car in the UI, TCP server sim/server.py), the virtual
CAN bus (sim/canbus.py) or directly with ``exchange()`` (the service layer's transport shape).
"""
from __future__ import annotations

import math
import random
import threading
import time

from .ecus import (CONDITIONS_NOT_CORRECT, ENGINE_NOT_RUNNING, SPEED_TOO_HIGH, SimDtc, SimEcu, SimIo, SimRoutine,
                   wait_until)

VIN = "XRDDEM0CAR0123456"          # fictitious manufacturer code "XRD"

LAMPS = [  # bit, key, English, Arabic
    (0, "mil", "Check engine (MIL)", "لمبة فحص المحرك (MIL)"),
    (1, "abs", "ABS", "لمبة ABS"),
    (2, "airbag", "Airbag (SRS)", "لمبة الوسائد الهوائية (SRS)"),
    (3, "oil", "Oil pressure", "لمبة ضغط الزيت"),
    (4, "battery", "Battery / charging", "لمبة البطارية / الشحن"),
    (5, "coolant", "Coolant temperature", "لمبة حرارة المحرك"),
    (6, "brake", "Brake system / parking brake", "لمبة نظام الفرامل / فرامل اليد"),
    (7, "service", "Service due", "لمبة موعد الصيانة"),
    (8, "tpms", "Tyre pressure (TPMS)", "لمبة ضغط الإطارات (TPMS)"),
    (9, "esp", "ESP / traction control", "لمبة ESP / التحكم في الجر"),
]


def _u16(v) -> bytes:
    return int(max(0, min(65535, round(v)))).to_bytes(2, "big")


def _s16(v) -> bytes:
    return int(max(-32768, min(32767, round(v)))).to_bytes(2, "big", signed=True)


def _u8(v) -> bytes:
    return bytes([int(max(0, min(255, round(v))))])


def _ascii(text: str, n: int | None = None) -> bytes:
    b = text.encode("ascii")
    return b.ljust(n, b" ")[:n] if n else b


class VirtualCar:
    def __init__(self, protocol: str = "6", *, time_scale: float = 1.0, seed: int = 7, engine_running: bool = True):
        self.lock = threading.RLock()
        self.protocol = protocol
        self.time_scale = time_scale
        self.rng = random.Random(seed)
        self.vin = VIN
        self.calid = "RADSIM-ENG-0142"
        self.cvn = "1A2B3C4D"
        self._real = time.monotonic()
        self._vt = 0.0
        # vehicle state
        self.ignition = True
        self.engine_running = engine_running
        self.driving = False
        self.overheat = False
        self.ambient = 27.0
        self.coolant = 82.0 if engine_running else 27.0
        self.oil_temp = 78.0 if engine_running else 27.0
        self.iat = 34.0
        self.runtime = 240.0 if engine_running else 0.0
        self.rpm = 780.0 if engine_running else 0.0
        self.speed = 0.0
        self.load = 22.0
        self.throttle = 14.0
        self.pedal = 0.0
        self.maf = 3.2
        self.map_kpa = 32.0
        self.timing = 8.0
        self.stft, self.ltft = 3.0, 14.0           # lean (P0171): long term trim adds fuel
        self.o2_b1s1, self.o2_b1s2 = 0.45, 0.62
        self.battery = 14.1 if engine_running else 12.5
        self.baro = 101.0
        self.fuel_level = 62.0
        self.odometer = 87412.3
        self.distance_since_clear = 1840.0
        self.minutes_since_clear = 2310.0
        self.warmups = 41
        self.distance_mil = 126.0
        self.minutes_mil = 190.0
        self.distance_to_service = -350.0          # overdue: service lamp on
        self.days_to_service = -12
        self.oil_life = 0.0
        self.steering_angle = 3.5
        self.sas_calibrated = True
        self.brake_service_mode = False
        self.tpms_fault = False
        self.battery_info = bytes([70, 0x01])      # 70 Ah, type 1 = flooded
        self.pump_duty = 0.0
        self.fan_duty = 0.0
        self.readiness = {"misfire": True, "fuel": True, "components": True, "catalyst": True, "evap": False,
                          "o2": True, "o2heater": True}
        self._drive_t = 0.0
        self._drive_ready: dict[str, float] = {}
        self.freeze_frame: dict[int, bytes] | None = None
        self.ecus: list[SimEcu] = []
        self._deferred: list[tuple[float, int, bytes]] = []     # for exchange()/receive()
        self._build()

    # ================================================================== clock / model
    def now(self) -> float:
        self.update()
        return self._vt

    def update(self) -> None:
        with self.lock:
            real = time.monotonic()
            dt = min(30.0, (real - self._real) * self.time_scale)
            self._real = real
            if dt <= 0:
                self._duties()
                return
            self._vt += dt
            self._step(dt)
            for e in self.ecus:
                e.advance_faults(dt)

    def _step(self, dt: float) -> None:
        r = self.rng
        misfire = any(d.code >> 8 == 0x0301 and d.status & 0x01 for d in self.engine.dtcs)
        if self.engine_running:
            self.runtime += dt
            if self.driving:
                self._drive_t += dt
                phase = (self._drive_t % 60.0) / 60.0
                self.speed = max(0.0, 85 * math.sin(math.pi * phase) + r.uniform(-1, 1))
                gear_ratio = 30 if self.speed < 30 else 22
                self.rpm = 850 + self.speed * gear_ratio + r.uniform(-25, 25)
                self.pedal = 10 + 25 * math.cos(math.pi * phase) ** 2
                self.throttle = 14 + self.pedal * 0.8
                self.load = 25 + self.pedal
                kmh_s = self.speed / 3600.0
                self.odometer += kmh_s * dt
                self.distance_since_clear += kmh_s * dt
                self.distance_to_service -= kmh_s * dt
                if self.engine.dtcs and any(d.status & 0x80 for d in self.engine.dtcs):
                    self.distance_mil += kmh_s * dt
                for mon, need in (("misfire", 5), ("fuel", 10), ("components", 3), ("o2heater", 8), ("o2", 20),
                                  ("catalyst", 40)):
                    if not self.readiness[mon]:
                        self._drive_ready[mon] = self._drive_ready.get(mon, 0.0) + dt
                        if self._drive_ready[mon] >= need:
                            self.readiness[mon] = True
            else:
                self.speed = 0.0
                self.pedal = 0.0
                self.rpm = 780 + r.uniform(-15, 15) + (r.uniform(-45, 45) if misfire else 0)
                self.throttle = 14 + r.uniform(-0.4, 0.4)
                self.load = 22 + r.uniform(-1, 1)
            self.maf = max(1.5, self.rpm * self.load / 5200.0)
            self.map_kpa = 28 + self.load * 0.7
            self.timing = 10 + self.speed / 10 + r.uniform(-1, 1)
            target = 118.0 if self.overheat else 90.0
            if self.fan_duty > 0:
                target -= self.fan_duty * 0.08
            self.coolant += (target - self.coolant) * min(1.0, dt / 150.0) + r.uniform(-0.05, 0.05)
            self.oil_temp += (self.coolant + 4 - self.oil_temp) * min(1.0, dt / 300.0)
            self.battery = 14.1 + r.uniform(-0.05, 0.05)
            self.fuel_level = max(0.0, self.fuel_level - dt * 0.0005)
            warm = self.coolant > 70
            self.stft = (r.uniform(-4, 6) if warm else 0.0)
            self.o2_b1s1 = (0.45 + 0.4 * math.sin(self._vt * 4.0)) if warm else 0.45
            self.o2_b1s2 = 0.62 + r.uniform(-0.03, 0.03)
            self.minutes_since_clear += dt / 60.0
            if any(d.status & 0x80 for d in self.engine.dtcs):
                self.minutes_mil += dt / 60.0
        else:
            self.rpm = self.speed = self.load = self.maf = 0.0
            self.throttle = 0.0 if not self.ignition else 12.0
            self.map_kpa = self.baro
            self.coolant += (self.ambient - self.coolant) * min(1.0, dt / 1200.0)
            if self.pump_duty > 0:                    # coolant pump test / bleed: circulates, cools a bit faster
                self.coolant += (self.ambient - self.coolant) * min(1.0, dt / 600.0)
            self.oil_temp += (self.ambient - self.oil_temp) * min(1.0, dt / 1500.0)
            self.battery = max(11.6, (12.5 if self.ignition else 12.6) - (0.002 * self.pump_duty))
        self._duties()

    def _duties(self) -> None:
        """Radiator fan / coolant pump: commanded by an actuator test, the bleed routine or the engine."""
        io = self.engine.ios
        self.fan_duty = io[0x4001].value[0] if io[0x4001].controlled else (100.0 if self.coolant > 100 else 0.0)
        bleed = self.engine.routines[0x0301]
        self.pump_duty = (io[0x4002].value[0] if io[0x4002].controlled
                          else (80.0 if bleed.state == 1 else (60.0 if self.engine_running else 0.0)))

    # ================================================================== vehicle controls (UI / tests)
    def set_ignition(self, on: bool) -> None:
        with self.lock:
            self.update()
            self.ignition = on
            if not on:
                self.engine_running = False
                self.driving = False
                for e in self.ecus:
                    e.session, e.unlocked = 0x01, 0
                    e._session_ended()

    def start_engine(self) -> None:
        with self.lock:
            self.update()
            self.ignition = True
            if not self.engine_running:
                self.engine_running = True
                self.runtime = 0.0
                if self.coolant < 50:
                    self.warmups += 1

    def stop_engine(self) -> None:
        with self.lock:
            self.update()
            self.engine_running = False
            self.driving = False

    def set_driving(self, on: bool) -> None:
        with self.lock:
            self.update()
            if on:
                self.start_engine()
            self.driving = on

    def set_overheat(self, on: bool) -> None:
        with self.lock:
            self.overheat = on

    # ================================================================== reports
    def lamps(self) -> dict[str, bool]:
        with self.lock:
            self.update()
            eng = any(d.status & 0x80 for d in self.engine.dtcs)
            abs_f = any(d.visible and d.status & 0x09 for d in self.abs.dtcs)
            bag = any(d.visible for d in self.airbag.dtcs)
            return {"mil": eng and self.ignition, "abs": abs_f and self.ignition, "airbag": bag and self.ignition,
                    "oil": self.ignition and not self.engine_running,
                    "battery": (self.ignition and not self.engine_running) or (self.engine_running and self.battery < 12.8),
                    "coolant": self.coolant > 115, "brake": self.brake_service_mode,
                    "service": self.distance_to_service <= 0 or self.days_to_service <= 0,
                    "tpms": self.tpms_fault, "esp": (abs_f or not self.sas_calibrated) and self.ignition}

    def lamp_bits(self) -> int:
        lamps = self.lamps()
        return sum(1 << bit for bit, key, _en, _ar in LAMPS if lamps.get(key))

    def monitor_status(self) -> bytes:
        confirmed = [d for d in self.engine.dtcs if d.emission and d.status & 0x08]
        mil = any(d.status & 0x80 for d in self.engine.dtcs)
        a = (0x80 if mil else 0) | min(0x7F, len(confirmed))
        rd = self.readiness
        b = 0x07                                       # misfire, fuel, components supported (spark ignition)
        for i, k in enumerate(("misfire", "fuel", "components")):
            if not rd[k]:
                b |= 1 << (i + 4)
        c = 0x01 | 0x04 | 0x20 | 0x40                  # catalyst, EVAP, O2 sensor, O2 heater
        d = 0
        for bit, k in ((0, "catalyst"), (2, "evap"), (5, "o2"), (6, "o2heater")):
            if not rd[k]:
                d |= 1 << bit
        return bytes([a, b, c, d])

    def on_dtcs_cleared(self, ecu: SimEcu) -> None:
        if ecu is self.engine:
            self.freeze_frame = None
            self.distance_since_clear = 0.0
            self.minutes_since_clear = 0.0
            self.distance_mil = 0.0
            self.minutes_mil = 0.0
            self.warmups = 0
            self.readiness = {k: False for k in self.readiness}
            self._drive_ready.clear()

    def obd_clear(self, ecu: SimEcu) -> None:
        ecu.clear(0xFFFFFF)
        self.on_dtcs_cleared(ecu)

    def state(self) -> dict:
        with self.lock:
            self.update()
            return {"ignition": self.ignition, "engine_running": self.engine_running, "driving": self.driving,
                    "rpm": round(self.rpm), "speed": round(self.speed, 1), "coolant": round(self.coolant, 1),
                    "battery": round(self.battery, 2), "protocol": self.protocol, "lamps": self.lamps(),
                    "ecus": [e.summary() for e in self.ecus]}

    def ecu(self, key: str) -> SimEcu:
        return next(e for e in self.ecus if e.key == key)

    # ================================================================== direct transport (service layer shape)
    def find_ecu(self, tx: int) -> SimEcu | None:
        for e in self.ecus:
            if tx in (e.tx, 0x18DA00F1 | (e.addr << 8)) or (tx == e.addr and not self.is_can()):
                return e
        return None

    @property
    def kwp_mode(self) -> bool:
        return self.protocol in ("4", "5")

    def is_can(self) -> bool:
        return self.protocol in ("6", "7", "8", "9")

    def exchange(self, request: bytes, tx: int = 0x7E0, rx: int | None = None, timeout: float = 2.0) -> bytes:
        """Send *request* to the unit with request id *tx*; the first answer (b"" = none). Later answers (after
        "response pending") come from ``receive()``."""
        with self.lock:
            if tx in (0x7DF, 0x18DB33F1):
                answers = []
                for e in self.ecus:
                    answers += e.handle(bytes(request), True, True)
            else:
                e = self.find_ecu(tx)
                answers = e.handle(bytes(request), False, True) if e else []
            if not answers:
                return b""
            now = time.monotonic()
            self._deferred = [(now + d / self.time_scale, tx, a) for d, a in answers[1:]] + self._deferred
            return answers[0][1]

    def receive(self, tx: int = 0x7E0, rx: int | None = None, timeout: float = 2.0) -> bytes:
        end = time.monotonic() + timeout
        while True:
            with self.lock:
                for i, (t, dtx, a) in enumerate(self._deferred):
                    if dtx == tx and t <= time.monotonic():
                        del self._deferred[i]
                        return a
                pending = any(dtx == tx for _t, dtx, _a in self._deferred)
            if not pending or time.monotonic() >= end:
                return b""
            time.sleep(0.01)

    # ================================================================== the control units
    def _build(self) -> None:
        car = self
        ident = lambda name, part, sw: {0xF187: _ascii(part), 0xF18A: _ascii("RAD IDE Demo"),       # noqa: E731
                                        0xF18C: _ascii("SN" + part[-6:]), 0xF191: _ascii("HW07"),
                                        0xF195: _ascii(sw), 0xF197: _ascii(name), 0xF189: _ascii(sw),
                                        0xF190: lambda: _ascii(car.vin)}

        # ---------------------------------------------------------- engine
        eng = SimEcu(self, "engine", "Engine control unit (ECM)", 0x7E0, 0x7E8, 0x10, obd=True, kline=True)
        eng.dids.update(ident("ENGINE", "RAD-SIM-100142", "SW0042"))
        eng.dids.update({
            0x1001: lambda: _u16(car.rpm), 0x1002: lambda: _u8(car.coolant + 40), 0x1003: lambda: _u16(car.battery * 1000),
            0x1004: lambda: _u8(car.oil_temp + 40), 0x1005: lambda: _u8(car.iat + 40),
            0x1006: lambda: _u8(car.throttle * 2.55), 0x1007: lambda: _u8(car.speed),
            0x1010: lambda: bytes([min(255, int(car.runtime / 6)) if any(
                d.code >> 8 == 0x0301 and d.status & 1 for d in car.engine.dtcs) else 0, 0, 1, 0]),
            0x1020: lambda: _u8(car.pump_duty), 0x1021: lambda: _u8(car.fan_duty),
            0x1030: lambda: _s16(car.ltft * 100), 0x3100: lambda: car.battery_info,
        })
        eng.snapshot_dids = {0x1001: 2, 0x1002: 1, 0x1007: 1, 0x1003: 2}
        snap = {0x1001: _u16(812), 0x1002: _u8(88 + 40), 0x1007: _u8(0), 0x1003: _u16(14050)}
        eng.dtcs = [
            SimDtc(0x030100, 0xAF, emission=True, permanent=True, recurs_after=10.0, snapshot=snap, occurrences=7),
            SimDtc(0x017100, 0x24, emission=True, occurrences=2),
            SimDtc(0x042000, 0xA8, emission=True, permanent=True, occurrences=3),
        ]
        self.freeze_frame = {0x02: b"\x03\x01", 0x04: _u8(24 * 2.55), 0x05: _u8(88 + 40), 0x06: _u8(131),
                             0x07: _u8(146), 0x0B: _u8(33), 0x0C: _u16(812 * 4), 0x0D: _u8(0), 0x0F: _u8(36 + 40),
                             0x11: _u8(14 * 2.55)}

        def engine_off(e, _p):
            return CONDITIONS_NOT_CORRECT if car.engine_running else 0

        def bleed_pre(e, _p):
            if car.engine_running:
                return CONDITIONS_NOT_CORRECT
            if car.coolant > 100:
                return 0x86                            # temperatureTooHigh: let the engine cool first
            return 0

        def bleed_results(e, r):
            return _u8(car.pump_duty) + _u8(car.coolant + 40) + _u8(min(100, r.progress(e.now()) * 1.1))

        eng.routines = {
            0x0301: SimRoutine(0x0301, "Cooling system bleed / coolant pump cycle", duration=8.0, pre=bleed_pre,
                               abort_if=lambda e: car.engine_running, results=bleed_results),
            0x0302: SimRoutine(0x0302, "Throttle body adaptation reset", duration=2.0, pre=engine_off),
            0x0303: SimRoutine(0x0303, "Fuel trim adaptation reset", duration=0.0, pre=engine_off,
                               on_done=lambda e: setattr(car, "ltft", 0.0)),
            0x0304: SimRoutine(0x0304, "Injector test (cylinder in parameter)", duration=3.0, pre=engine_off),
            0x0305: SimRoutine(0x0305, "Battery registration (Ah, type)", duration=0.0, pre=engine_off,
                               on_start=lambda e, p: setattr(car, "battery_info", bytes(p[:2]).ljust(2, b"\x01"))),
        }

        def needs_running(e, _s):
            return 0 if car.engine_running else ENGINE_NOT_RUNNING

        eng.ios = {0x4001: SimIo(0x4001, "Radiator fan (%)"), 0x4002: SimIo(0x4002, "Electric coolant pump (%)")}
        for cyl in range(4):
            eng.ios[0x4010 + cyl] = SimIo(0x4010 + cyl, f"Injector {cyl + 1} cut-off", pre=needs_running)
        eng.kwp_local = {0x01: lambda: _u16(car.rpm) + _u8(car.coolant + 40) + _u8(car.speed),
                         0x02: lambda: _u16(car.battery * 1000)}
        eng.kwp_routines = {0x01: 0x0301, 0x02: 0x0302}

        # ---------------------------------------------------------- ABS / ESP
        abs_ = SimEcu(self, "abs", "ABS / ESP", 0x760, 0x768, 0x28)
        abs_.dids.update(ident("ABS ESP", "RAD-SIM-200301", "SW0310"))
        abs_.dids.update({
            0x2001: lambda: _u16(0),           # front left sensor is the faulty one (C0035): reads 0
            0x2002: lambda: _u16(car.speed * 100),
            0x2003: lambda: _u16(car.speed * 100), 0x2004: lambda: _u16(car.speed * 100),
            0x2010: lambda: _s16(car.steering_angle * 10), 0x2011: lambda: _u8(0),
            0x2013: lambda: bytes([1 if car.sas_calibrated else 0]),
        })
        abs_.dtcs = [SimDtc(0x40351F, 0xAF,                # C0035-1F recurs_after=6.0, recur_condition="driving", occurrences=4,
                            snapshot={0x2002: _u16(4210), 0x2010: _s16(-12)})]
        abs_.snapshot_dids = {0x2002: 2, 0x2010: 2}

        def stopped(e, _p):
            return SPEED_TOO_HIGH if car.speed > 1 else 0

        def sas_pre(e, _p):
            if not car.engine_running:
                return ENGINE_NOT_RUNNING
            if car.speed > 1:
                return SPEED_TOO_HIGH
            if abs(car.steering_angle) > 10:
                return CONDITIONS_NOT_CORRECT
            return 0

        def sas_done(e):
            car.sas_calibrated = True
            car.steering_angle = 0.0

        abs_.routines = {
            0x0501: SimRoutine(0x0501, "Brake pads: open service position (EPB)", duration=4.0, pre=stopped,
                               on_done=lambda e: setattr(car, "brake_service_mode", True)),
            0x0502: SimRoutine(0x0502, "Brake pads: close after replacement (EPB)", duration=4.0, pre=stopped,
                               on_done=lambda e: setattr(car, "brake_service_mode", False)),
            0x0503: SimRoutine(0x0503, "Steering angle sensor calibration", duration=2.0, pre=sas_pre,
                               on_done=sas_done),
        }
        abs_.ios = {0x4501: SimIo(0x4501, "ABS pump motor", pre=lambda e, s: CONDITIONS_NOT_CORRECT
                                  if car.speed > 1 or car.engine_running else 0, max_time=3.0)}

        # ---------------------------------------------------------- airbag
        bag = SimEcu(self, "airbag", "Airbag (SRS)", 0x770, 0x778, 0x58, clear_specific=False)
        bag.dids.update(ident("AIRBAG", "RAD-SIM-300077", "SW0105"))
        bag.dids.update({0x5001: lambda: b"\x01", 0x5002: lambda: b"\x00"})
        bag.dtcs = [SimDtc(0x80011A, 0xAF, recurs_after=0.0, recur_condition="ignition", occurrences=12)]

        # ---------------------------------------------------------- instrument cluster
        clu = SimEcu(self, "cluster", "Instrument cluster", 0x720, 0x728, 0x60)
        clu.dids.update(ident("CLUSTER", "RAD-SIM-400720", "SW0221"))
        clu.dids.update({
            0x2200: lambda: int(car.odometer).to_bytes(3, "big"),            # read only
            0x2210: lambda: _s16(car.distance_to_service), 0x2211: lambda: _s16(car.days_to_service),
            0x2212: lambda: _u8(car.oil_life), 0x2220: lambda: car.lamp_bits().to_bytes(2, "big"),
            0x2230: lambda: _u8(car.fuel_level), 0x2231: lambda: _s16(car.ambient * 10),
        })
        clu.dtcs = [SimDtc(0xC12100, 0x28, occurrences=1)]

        def service_reset(e):
            car.distance_to_service, car.days_to_service, car.oil_life = 15000.0, 365, 100.0

        clu.routines = {0x0401: SimRoutine(0x0401, "Oil service interval reset", duration=0.0, pending=1.2,
                                           on_done=service_reset)}

        # ---------------------------------------------------------- climate
        cli = SimEcu(self, "climate", "Climate control", 0x744, 0x74C, 0x2C)
        cli.dids.update(ident("CLIMATE", "RAD-SIM-500744", "SW0017"))
        cli.dids.update({0x3001: lambda: _s16((car.ambient - 3) * 10), 0x3002: bytes([44]),        # 22.0 °C
                         0x3003: lambda: _s16(40 if car.engine_running else car.ambient * 10),
                         0x3004: lambda: _u8(12 if car.engine_running else 6), 0x0600: bytes([0x01, 0x00, 0x24, 0x00])})
        cli.writable = {0x3002: (0x03, 0), 0x0600: (0x03, 0x01)}
        cli.ios = {0x4101: SimIo(0x4101, "Blower motor (%)"),
                   0x4102: SimIo(0x4102, "A/C compressor clutch", pre=needs_running)}
        cli.dtcs = [SimDtc(0x942400, 0x28, occurrences=2)]          # B1424: manufacturer specific

        self.engine, self.abs, self.airbag, self.cluster, self.climate = eng, abs_, bag, clu, cli
        self.ecus = [eng, abs_, bag, clu, cli]
        if not self.engine_running:
            self.rpm = 0.0


_DEMO: VirtualCar | None = None


def demo_car() -> VirtualCar:
    """The IDE-wide Demo car (created on first use)."""
    global _DEMO
    if _DEMO is None:
        _DEMO = VirtualCar()
    return _DEMO


def reset_demo_car(**kw) -> VirtualCar:
    global _DEMO
    _DEMO = VirtualCar(**kw)
    return _DEMO


__all__ = ["VirtualCar", "demo_car", "reset_demo_car", "LAMPS", "VIN", "wait_until"]
