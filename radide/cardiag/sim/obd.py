"""OBD-II modes 01-0A for the Demo car's engine unit (CAN and K-line message formats)."""
from __future__ import annotations


def _enc(car, pid: int) -> bytes | None:
    """Mode 01 data bytes for *pid* from the car's live state (formulas of SAE J1979)."""
    s = car
    u16 = lambda v: int(max(0, min(65535, v))).to_bytes(2, "big")   # noqa: E731
    u8 = lambda v: bytes([int(max(0, min(255, round(v))))])          # noqa: E731
    run = s.engine_running
    table = {
        0x03: lambda: bytes([2 if run and s.coolant > 60 else (1 if run else 0), 0]),
        0x04: lambda: u8(s.load * 255 / 100),
        0x05: lambda: u8(s.coolant + 40),
        0x06: lambda: u8((s.stft + 100) * 128 / 100),
        0x07: lambda: u8((s.ltft + 100) * 128 / 100),
        0x0B: lambda: u8(s.map_kpa),
        0x0C: lambda: u16(s.rpm * 4),
        0x0D: lambda: u8(s.speed),
        0x0E: lambda: u8((s.timing + 64) * 2),
        0x0F: lambda: u8(s.iat + 40),
        0x10: lambda: u16(s.maf * 100),
        0x11: lambda: u8(s.throttle * 255 / 100),
        0x13: lambda: b"\x03",                       # O2 sensors present: bank 1 sensors 1 and 2
        0x15: lambda: u8(s.o2_b1s2 / 0.005) + b"\xFF",
        0x14: lambda: u8(s.o2_b1s1 / 0.005) + u8((s.stft + 100) * 128 / 100),
        0x1C: lambda: b"\x06",                       # EOBD (Europe)
        0x1F: lambda: u16(s.runtime),
        0x21: lambda: u16(s.distance_mil),
        0x2F: lambda: u8(s.fuel_level * 255 / 100),
        0x30: lambda: u8(s.warmups),
        0x31: lambda: u16(s.distance_since_clear),
        0x33: lambda: u8(s.baro),
        0x42: lambda: u16(s.battery * 1000),
        0x45: lambda: u8(max(0, s.throttle - 12) * 255 / 100),
        0x46: lambda: u8(s.ambient + 40),
        0x49: lambda: u8(s.pedal * 255 / 100),
        0x4D: lambda: u16(s.minutes_mil),
        0x4E: lambda: u16(s.minutes_since_clear),
        0x51: lambda: b"\x01",                       # gasoline
        0x5C: lambda: u8(s.oil_temp + 40),
        0x01: lambda: s.monitor_status(),
        0xA6: lambda: int(s.odometer * 10).to_bytes(4, "big"),
    }
    f = table.get(pid)
    return f() if f else None


SUPPORTED_01 = [0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x13, 0x14, 0x15,
                0x1C, 0x1F, 0x21, 0x2F, 0x30, 0x31, 0x33, 0x42, 0x45, 0x46, 0x49, 0x4D, 0x4E, 0x51, 0x5C, 0xA6]
FREEZE_PIDS = [0x02, 0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0D, 0x0F, 0x11]


def support_bitmap(pids, base: int) -> bytes:
    v = 0
    for p in pids:
        if base < p <= base + 32:
            v |= 1 << (32 - (p - base))
    if any(p > base + 32 for p in pids):
        v |= 1
    return v.to_bytes(4, "big")


def _dtc_messages(sid: int, codes: list[int], can: bool) -> list[bytes]:
    if can:
        body = bytes([sid, len(codes)]) + b"".join(c.to_bytes(2, "big") for c in codes)
        return [body]
    msgs = []
    for i in range(0, max(1, len(codes)), 3):
        part = codes[i:i + 3] + [0] * (3 - len(codes[i:i + 3]))
        msgs.append(bytes([sid]) + b"".join(c.to_bytes(2, "big") for c in part))
    return msgs


def _info_messages(pid: int, data: bytes, items: int, can: bool) -> list[bytes]:
    if can:
        return [bytes([0x49, pid, items]) + data]
    pad = (-len(data)) % 4
    data = b"\x00" * pad + data
    return [bytes([0x49, pid, i // 4 + 1]) + data[i:i + 4] for i in range(0, len(data), 4)]


def handle_obd(ecu, req: bytes, can: bool):
    car = ecu.car
    mode = req[0]
    out: list[bytes] = []
    if mode == 0x01:
        for pid in req[1:7]:
            if pid % 0x20 == 0:
                out.append(bytes([0x41, pid]) + support_bitmap(SUPPORTED_01, pid))
                continue
            if pid not in SUPPORTED_01:
                continue
            v = _enc(car, pid)
            if v is not None:
                out.append(bytes([0x41, pid]) + v)
        if len(out) > 1 and can:                     # several PIDs in one request: one combined answer
            out = [b"\x41" + b"".join(o[1:] for o in out)]
    elif mode == 0x02:
        if len(req) < 3:
            return []
        pairs = req[1:7]                             # up to 3 (PID, frame) pairs per request (CAN)
        for k in range(0, len(pairs) - 1, 2):
            pid, frame = pairs[k], pairs[k + 1]
            ff = car.freeze_frame if frame == 0 else None
            if pid % 0x20 == 0:
                out.append(bytes([0x42, pid, frame]) + support_bitmap(FREEZE_PIDS if ff else [], pid))
            elif ff and pid in ff:
                out.append(bytes([0x42, pid, frame]) + ff[pid])
        if len(out) > 1 and can:                     # several PIDs in one request: one combined answer
            out = [b"\x42" + b"".join(o[1:] for o in out)]
    elif mode in (0x03, 0x07, 0x0A):
        if mode == 0x03:
            codes = [d.sae for d in ecu.dtcs if d.emission and d.status & 0x08]
        elif mode == 0x07:
            codes = [d.sae for d in ecu.dtcs if d.emission and d.status & 0x04]
        else:
            codes = [d.sae for d in ecu.dtcs if d.emission and d.permanent]
        out = _dtc_messages(mode + 0x40, codes, can)
    elif mode == 0x04:
        if car.engine_running:
            return [(0.0, bytes([0x7F, 0x04, 0x22]))]   # many units refuse mode 04 with the engine running
        car.obd_clear(ecu)
        out = [b"\x44"]
    elif mode == 0x06:
        mid = req[1] if len(req) > 1 else 0
        if mid == 0x00:
            out = [b"\x46\x00" + support_bitmap([0x01, 0x21], 0)]
        elif mid == 0x01:                            # oxygen sensor monitor bank 1 sensor 1
            out = [b"\x46\x01\x01\x0A" + (500).to_bytes(2, "big") + (100).to_bytes(2, "big") + (900).to_bytes(2, "big")]
        elif mid == 0x21:                            # catalyst monitor bank 1 (failing: P0420)
            out = [b"\x46\x21\x80\x24" + (40).to_bytes(2, "big") + (85).to_bytes(2, "big") + (1000).to_bytes(2, "big")]
    elif mode == 0x08:
        tid = req[1] if len(req) > 1 else 0
        if tid == 0x00:
            out = [b"\x48\x00" + support_bitmap([0x01], 0)]
        elif tid == 0x01:                            # EVAP leak test: only with the engine off
            if car.engine_running:
                return [(0.0, bytes([0x7F, 0x08, 0x22]))]
            out = [b"\x48\x01\x00\x00\x00\x00\x00"]
    elif mode == 0x09:
        pid = req[1] if len(req) > 1 else 0
        if pid == 0x00:
            out = [b"\x49\x00" + support_bitmap([0x02, 0x04, 0x06, 0x0A], 0)]
        elif pid == 0x02:
            out = _info_messages(0x02, car.vin.encode("ascii"), 1, can)
        elif pid == 0x04:
            out = _info_messages(0x04, car.calid.encode("ascii").ljust(16, b"\x00"), 1, can)
        elif pid == 0x06:
            out = _info_messages(0x06, bytes.fromhex(car.cvn), 1, can)
        elif pid == 0x0A:
            out = _info_messages(0x0A, b"ECM\x00-EngineControl".ljust(20, b"\x00"), 1, can)
    return [(0.0, o) for o in out]
