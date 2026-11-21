"""Mode 06: on-board monitoring test results (CAN format, ISO 15031-5 / SAE J1979).

Request ``06 MID``; the answer is ``46`` followed by 9-byte records ``MID TID UASID VAL(2) MIN(2) MAX(2)``.
MIDs 00, 20, 40 ... are bitmaps of the supported MIDs.  The unit-and-scaling id (UASID) gives unit, scale and
whether the three numbers are signed.  A test passes when MIN <= VALUE <= MAX.
"""
from __future__ import annotations

from dataclasses import dataclass

BITMAP_MIDS = tuple(range(0x00, 0x100, 0x20))


def _mid_names() -> dict[int, str]:
    n = {}
    for i in range(16):
        n[0x01 + i] = f"Oxygen sensor monitor bank {i // 4 + 1} sensor {i % 4 + 1}"
    for i in range(4):
        n[0x21 + i] = f"Catalyst monitor bank {i + 1}"
        n[0x31 + i] = f"EGR monitor bank {i + 1}"
        n[0x35 + i] = f"VVT monitor bank {i + 1}"
        n[0x61 + i] = f"Heated catalyst monitor bank {i + 1}"
        n[0x71 + i] = f"Secondary air monitor {i + 1}"
        n[0x81 + i] = f"Fuel system monitor bank {i + 1}"
        n[0x85 + i] = f"Boost pressure control monitor bank {i + 1}"
    n[0x39] = "EVAP monitor (cap off / 0.150\")"
    n[0x3A] = "EVAP monitor (0.090\")"
    n[0x3B] = "EVAP monitor (0.040\")"
    n[0x3C] = "EVAP monitor (0.020\")"
    n[0x3D] = "Purge flow monitor"
    for i in range(16):
        n[0x41 + i] = f"Oxygen sensor heater monitor bank {i // 4 + 1} sensor {i % 4 + 1}"
    n[0x90] = "NOx adsorber monitor bank 1"
    n[0x91] = "NOx adsorber monitor bank 2"
    n[0x98] = "NOx catalyst monitor bank 1"
    n[0x99] = "NOx catalyst monitor bank 2"
    n[0xA0] = "Misfire monitor general data"
    for i in range(16):
        n[0xA1 + i] = f"Misfire cylinder {i + 1} data"
    n[0xB0] = "PM filter monitor bank 1"
    n[0xB1] = "PM filter monitor bank 2"
    return n


MID_NAMES = _mid_names()

# standardised test ids (TID 0x01-0x0A: oxygen sensor tests); 0x80+ are manufacturer-defined
TID_NAMES = {0x01: "Rich to lean sensor threshold voltage", 0x02: "Lean to rich sensor threshold voltage",
             0x03: "Low sensor voltage for switch time calculation",
             0x04: "High sensor voltage for switch time calculation", 0x05: "Rich to lean sensor switch time",
             0x06: "Lean to rich sensor switch time", 0x07: "Minimum sensor voltage for test cycle",
             0x08: "Maximum sensor voltage for test cycle", 0x09: "Time between sensor transitions",
             0x0A: "Sensor period", 0x0B: "EWMA misfire counts for last 10 driving cycles",
             0x0C: "Misfire counts for last / current driving cycle"}

# UASID -> (unit, scale, offset, signed)
UAS = {0x01: ("", 1, 0, False), 0x02: ("", 0.1, 0, False), 0x03: ("", 0.01, 0, False), 0x04: ("", 0.001, 0, False),
       0x05: ("", 0.0000305, 0, False), 0x06: ("", 0.000305, 0, False), 0x07: ("rpm", 0.25, 0, False),
       0x08: ("km/h", 0.01, 0, False), 0x09: ("km/h", 1, 0, False), 0x0A: ("mV", 0.122, 0, False),
       0x0B: ("V", 0.001, 0, False), 0x0C: ("V", 0.01, 0, False), 0x0D: ("mA", 0.00390625, 0, False),
       0x0E: ("A", 0.001, 0, False), 0x0F: ("A", 0.01, 0, False), 0x10: ("ms", 1, 0, False),
       0x11: ("ms", 100, 0, False), 0x12: ("s", 1, 0, False), 0x13: ("mΩ", 1, 0, False), 0x14: ("Ω", 1, 0, False),
       0x15: ("kΩ", 1, 0, False), 0x16: ("°C", 0.1, -40, False), 0x17: ("kPa", 0.01, 0, False),
       0x18: ("kPa", 0.0117, 0, False), 0x19: ("kPa", 0.079, 0, False), 0x1A: ("kPa", 1, 0, False),
       0x1B: ("kPa", 10, 0, False), 0x1C: ("°", 0.01, 0, False), 0x1D: ("°", 0.5, 0, False),
       0x1E: ("λ", 0.0000305, 0, False), 0x1F: ("A/F", 0.05, 0, False), 0x20: ("ratio", 0.0039062, 0, False),
       0x21: ("mHz", 1, 0, False), 0x22: ("Hz", 1, 0, False), 0x23: ("kHz", 1, 0, False),
       0x24: ("counts", 1, 0, False), 0x25: ("km", 1, 0, False), 0x26: ("mV/ms", 0.1, 0, False),
       0x27: ("g/s", 0.01, 0, False), 0x28: ("g/s", 1, 0, False), 0x29: ("Pa/s", 0.25, 0, False),
       0x2A: ("kg/h", 0.001, 0, False), 0x2B: ("switches", 1, 0, False), 0x2C: ("g/cyl", 0.01, 0, False),
       0x2D: ("mg/stroke", 0.01, 0, False), 0x2E: ("", 1, 0, False), 0x2F: ("%", 0.01, 0, False),
       0x30: ("%", 0.001526, 0, False), 0x31: ("L", 0.001, 0, False), 0x32: ("mm", 0.0007747, 0, False),
       0x33: ("λ", 0.00024414, 0, False), 0x34: ("min", 1, 0, False), 0x35: ("s", 0.01, 0, False),
       0x36: ("g", 0.01, 0, False), 0x37: ("g", 0.1, 0, False), 0x38: ("g", 1, 0, False),
       0x39: ("%", 0.01, -327.68, False), 0x3A: ("g", 0.001, 0, False), 0x3B: ("g", 0.0001, 0, False),
       0x3C: ("µs", 0.1, 0, False), 0x3D: ("mA", 0.01, 0, False), 0x3E: ("mm²", 0.00006103516, 0, False),
       0x3F: ("L", 0.01, 0, False), 0x40: ("ppm", 1, 0, False), 0x41: ("µA", 0.01, 0, False),
       0x81: ("", 1, 0, True), 0x82: ("", 0.1, 0, True), 0x83: ("", 0.01, 0, True), 0x84: ("", 0.001, 0, True),
       0x85: ("", 0.0000305, 0, True), 0x86: ("", 0.000305, 0, True), 0x8A: ("mV", 0.122, 0, True),
       0x8B: ("V", 0.001, 0, True), 0x8C: ("V", 0.01, 0, True), 0x8D: ("mA", 0.00390625, 0, True),
       0x8E: ("A", 0.001, 0, True), 0x90: ("ms", 1, 0, True), 0x96: ("°C", 0.1, 0, True),
       0x9C: ("°", 0.01, 0, True), 0x9D: ("°", 0.5, 0, True), 0xA8: ("g/s", 1, 0, True),
       0xA9: ("Pa/s", 0.25, 0, True), 0xAD: ("mg/stroke", 0.01, 0, True), 0xAE: ("mg/stroke", 0.1, 0, True),
       0xAF: ("%", 0.01, 0, True), 0xB0: ("%", 0.003052, 0, True), 0xB1: ("mV/s", 2, 0, True),
       0xFC: ("kPa", 0.01, 0, True), 0xFD: ("kPa", 0.001, 0, True), 0xFE: ("kPa", 0.25, 0, True)}


@dataclass
class TestResult:
    mid: int
    tid: int
    uasid: int
    value: float
    minimum: float
    maximum: float
    unit: str

    @property
    def passed(self) -> bool:
        return self.minimum <= self.value <= self.maximum

    @property
    def mid_name(self) -> str:
        return MID_NAMES.get(self.mid, f"Monitor 0x{self.mid:02X}")

    @property
    def tid_name(self) -> str:
        if self.tid in TID_NAMES:
            return TID_NAMES[self.tid]
        return f"Manufacturer test 0x{self.tid:02X}" if self.tid >= 0x80 else f"Test 0x{self.tid:02X}"


def scale(uasid: int, raw: int) -> tuple[float, str]:
    unit, k, off, signed = UAS.get(uasid, ("", 1, 0, uasid >= 0x80))
    if signed and raw & 0x8000:
        raw -= 0x10000
    return round(raw * k + off, 6), unit


def parse(payload: bytes) -> list[TestResult]:
    """Answer starting with 0x46 (records of 9 bytes) -> test results (bitmap MIDs skipped)."""
    data = bytes(payload[1:]) if payload and payload[0] == 0x46 else bytes(payload)
    out = []
    if len(data) == 5 and data[0] in BITMAP_MIDS:       # 46 MID bitmap(4)
        return out
    for i in range(0, len(data) - 8, 9):
        mid, tid, uas = data[i], data[i + 1], data[i + 2]
        v, unit = scale(uas, (data[i + 3] << 8) | data[i + 4])
        lo, _ = scale(uas, (data[i + 5] << 8) | data[i + 6])
        hi, _ = scale(uas, (data[i + 7] << 8) | data[i + 8])
        out.append(TestResult(mid, tid, uas, v, lo, hi, unit))
    return out


def supported_from_bitmap(base: int, payload: bytes) -> set[int]:
    data = bytes(payload[1:]) if payload and payload[0] == 0x46 else bytes(payload)
    if len(data) < 5:
        return set()
    bits = int.from_bytes(data[1:5], "big")
    return {base + i + 1 for i in range(32) if bits & (1 << (31 - i))}
