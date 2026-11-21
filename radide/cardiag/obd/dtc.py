"""Diagnostic trouble codes of OBD modes 03 (stored), 07 (pending) and 0A (permanent).

* `parse(payload)`   - a mode 43 / 47 / 4A answer -> ["P0301", ...] (CAN answers carry a count byte first,
  K-line / J1850 answers come in groups of three codes padded with 00 00).
* `encode(code)`     - "P0301" -> b"\x03\x01".
* `category(code)`   - a short original description of the code's group (used when the knowledge base has no
  entry for a code), `safety_relevant(code)` - brakes / airbag / steering / overheating codes that need a warning
  before they are cleared.
"""
from __future__ import annotations

import re

from .pids import dtc_text

_RX = re.compile(r"^[PCBU][0-3][0-9A-F]{3}$")

KINDS = {"stored": 0x03, "pending": 0x07, "permanent": 0x0A}
KIND_TITLES = {"stored": "Stored (confirmed)", "pending": "Pending", "permanent": "Permanent"}


def valid(code: str) -> bool:
    return bool(_RX.match((code or "").upper()))


def encode(code: str) -> bytes:
    c = code.upper()
    if not valid(c):
        raise ValueError(f"not a DTC: {code!r}")
    a = ("PCBU".index(c[0]) << 6) | (int(c[1]) << 4) | int(c[2], 16)
    return bytes([a, int(c[3:5], 16)])


def parse(payload: bytes, can: bool | None = None) -> list[str]:
    """Answer payload starting with 0x43 / 0x47 / 0x4A -> list of codes (00 00 padding dropped)."""
    data = bytes(payload[1:]) if payload and payload[0] in (0x43, 0x47, 0x4A) else bytes(payload)
    if can is None:
        can = len(data) % 2 == 1                # CAN: count byte + pairs
    if can and data:
        n = data[0]
        data = data[1:1 + 2 * n]
    out = []
    for i in range(0, len(data) - 1, 2):
        a, b = data[i], data[i + 1]
        if a == 0 and b == 0:
            continue
        out.append(dtc_text(a, b))
    return out


SYSTEMS = {"P": "Powertrain (engine / transmission)", "C": "Chassis (brakes, steering, suspension)",
           "B": "Body (airbags, seats, lights, comfort)", "U": "Network / communication between modules"}

# (prefix, description) - checked longest prefix first; original wording
_GROUPS = [
    ("P00", "Fuel and air metering, auxiliary emission controls"), ("P01", "Fuel and air metering"),
    ("P02", "Fuel and air metering (injector circuits)"), ("P03", "Ignition system or misfire"),
    ("P04", "Auxiliary emission controls"), ("P05", "Vehicle speed, idle control and auxiliary inputs"),
    ("P06", "Computer and output circuits"), ("P07", "Transmission"), ("P08", "Transmission"),
    ("P09", "Transmission"), ("P0A", "Hybrid propulsion"), ("P0B", "Hybrid propulsion"),
    ("P0C", "Hybrid propulsion"), ("P1", "Manufacturer-specific powertrain code"),
    ("P20", "Fuel and air metering, auxiliary emission controls"), ("P21", "Fuel and air metering (throttle control)"),
    ("P22", "Fuel and air metering, auxiliary emission controls"), ("P23", "Ignition system"),
    ("P24", "Auxiliary emission controls"), ("P25", "Auxiliary inputs"), ("P26", "Computer and output circuits"),
    ("P27", "Transmission"), ("P28", "Transmission"), ("P29", "Fuel and air metering, auxiliary emission controls"),
    ("P2A", "Fuel and air metering, auxiliary emission controls"), ("P3", "Manufacturer-specific / reserved"),
    ("P34", "Cylinder deactivation"), ("C0", "Chassis (generic)"), ("C1", "Chassis (manufacturer-specific)"),
    ("C2", "Chassis (manufacturer-specific)"), ("C3", "Chassis (reserved)"), ("B0", "Body (generic)"),
    ("B1", "Body (manufacturer-specific)"), ("B2", "Body (manufacturer-specific)"), ("B3", "Body (reserved)"),
    ("U0", "Network (generic)"), ("U1", "Network (manufacturer-specific)"), ("U2", "Network (manufacturer-specific)"),
    ("U3", "Network (reserved)"),
]


def manufacturer_specific(code: str) -> bool:
    c = code.upper()
    return c[:2] in ("P1", "C1", "C2", "B1", "B2", "U1", "U2") or (c[:2] == "P3" and not c.startswith("P34"))


def category(code: str) -> str:
    c = (code or "").upper()
    best = ""
    for pre, desc in _GROUPS:
        if c.startswith(pre) and len(pre) > len(best):
            best, res = pre, desc
    return res if best else SYSTEMS.get(c[:1], "Unknown")


_COOLING = {"P0115", "P0116", "P0117", "P0118", "P0119", "P0125", "P0128", "P0217", "P0218", "P0480",
            "P0481", "P0482", "P0526", "P0597", "P0598", "P0599"}
_BRAKE_SWITCH = {"P0504", "P0571", "P0572", "P0573"}


def safety_relevant(code: str) -> str:
    """Empty string, or why clearing this code needs care (brakes / airbag / steering / overheating)."""
    c = (code or "").upper()
    if not valid(c):
        return ""
    if c.startswith("B00"):
        return "Airbag / restraint system"
    if c.startswith("C0"):
        n = int(c[2:], 16)
        if 0x450 <= n <= 0x4FF:
            return "Steering"
        return "Brakes / stability control / steering"
    if c in _COOLING:
        return "Engine cooling / overheating"
    if c in _BRAKE_SWITCH:
        return "Brake pedal switch"
    if c[:3] in ("P0A", "P0B", "P0C"):
        return "Hybrid high-voltage system"
    return ""
