"""Mode 09: vehicle information (VIN, calibration ids, CVNs, ECU name, in-use performance tracking).

CAN answers: ``49 <infotype> <number of data items> data...``.  K-line answers repeat ``49 <infotype> <seq>``
before every 4-byte chunk; `strip_kline` joins those chunks.
"""
from __future__ import annotations

INFO_NAMES = {0x00: "Supported info types", 0x01: "VIN message count", 0x02: "Vehicle identification number (VIN)",
              0x03: "Calibration ID message count", 0x04: "Calibration ID (CALID)",
              0x05: "CVN message count", 0x06: "Calibration verification number (CVN)",
              0x07: "In-use performance tracking message count", 0x08: "In-use performance tracking (spark ignition)",
              0x09: "ECU name message count", 0x0A: "ECU name", 0x0B: "In-use performance tracking (compression ignition)",
              0x0D: "Engine serial number", 0x0F: "Exhaust regulation or type approval number"}

IPT_SPARK = ["OBD monitoring conditions encountered", "Ignition cycles", "Catalyst monitor completions bank 1",
             "Catalyst monitor conditions bank 1", "Catalyst monitor completions bank 2",
             "Catalyst monitor conditions bank 2", "O2 sensor monitor completions bank 1",
             "O2 sensor monitor conditions bank 1", "O2 sensor monitor completions bank 2",
             "O2 sensor monitor conditions bank 2", "EGR / VVT monitor completions", "EGR / VVT monitor conditions",
             "Secondary air monitor completions", "Secondary air monitor conditions", "EVAP monitor completions",
             "EVAP monitor conditions", "Secondary O2 sensor monitor completions bank 1",
             "Secondary O2 sensor monitor conditions bank 1", "Secondary O2 sensor monitor completions bank 2",
             "Secondary O2 sensor monitor conditions bank 2"]
IPT_DIESEL = ["OBD monitoring conditions encountered", "Ignition cycles", "NMHC catalyst monitor completions",
              "NMHC catalyst monitor conditions", "NOx / SCR catalyst monitor completions",
              "NOx / SCR catalyst monitor conditions", "NOx adsorber monitor completions",
              "NOx adsorber monitor conditions", "PM filter monitor completions", "PM filter monitor conditions",
              "Exhaust gas sensor monitor completions", "Exhaust gas sensor monitor conditions",
              "EGR / VVT monitor completions", "EGR / VVT monitor conditions", "Boost pressure monitor completions",
              "Boost pressure monitor conditions", "Fuel monitor completions", "Fuel monitor conditions"]


def body(payload: bytes, infotype: int) -> bytes:
    """Data after ``49 <infotype> [count]`` of a CAN answer."""
    d = bytes(payload)
    if d[:1] == b"\x49":
        d = d[1:]
    if d[:1] == bytes([infotype]):
        d = d[1:]
    if infotype in (0x02, 0x04, 0x06, 0x08, 0x0A, 0x0B, 0x0D, 0x0F) and d:
        d = d[1:]                                      # number of data items
    return d


def _text(b: bytes) -> str:
    return bytes(c for c in b if 32 <= c < 127).decode("ascii", "replace").strip()


def vin(payload: bytes) -> str:
    d = body(payload, 0x02)
    return _text(d[-17:]) if len(d) >= 17 else _text(d)


def calids(payload: bytes) -> list[str]:
    d = body(payload, 0x04)
    return [t for t in (_text(d[i:i + 16]) for i in range(0, len(d), 16)) if t]


def cvns(payload: bytes) -> list[str]:
    d = body(payload, 0x06)
    return [d[i:i + 4].hex().upper() for i in range(0, len(d) - 3, 4)]


def ecu_name(payload: bytes) -> str:
    d = body(payload, 0x0A)
    raw = bytes(d[:20])
    if b"\x00" in raw:                                  # "ECM\0-EngineControl" -> "ECM - EngineControl"
        head, _, tail = raw.partition(b"\x00")
        return (_text(head) + _text(tail)).strip()
    return _text(raw)


def ipt(payload: bytes, diesel: bool = False) -> list[tuple[str, int]]:
    d = body(payload, 0x0B if diesel else 0x08)
    names = IPT_DIESEL if diesel else IPT_SPARK
    vals = [(d[i] << 8) | d[i + 1] for i in range(0, len(d) - 1, 2)]
    return [(names[i] if i < len(names) else f"Counter {i + 1}", v) for i, v in enumerate(vals)]


def ipt_ratios(counters: list[tuple[str, int]]) -> list[tuple[str, int, int, float]]:
    """Pairs (completions, conditions) -> (monitor, completions, conditions, ratio)."""
    out = []
    for i in range(2, len(counters) - 1, 2):
        name = counters[i][0].replace(" completions", "")
        comp, cond = counters[i][1], counters[i + 1][1]
        out.append((name, comp, cond, round(comp / cond, 3) if cond else 0.0))
    return out


# VIN position 10 -> model year (30-year cycle; letters I O Q U Z and digit 0 are not used)
_YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"


def vin_model_year(v: str) -> list[int]:
    """Possible model years of a VIN (the code repeats every 30 years: e.g. 'A' = 1980 or 2010)."""
    if len(v) != 17 or v[9] not in _YEAR_CODES:
        return []
    i = _YEAR_CODES.index(v[9])
    return [1980 + i, 2010 + i]


_REGIONS = [("A", "H", "Africa"), ("J", "R", "Asia"), ("S", "Z", "Europe"), ("1", "5", "North America"),
            ("6", "7", "Oceania"), ("8", "9", "South America")]


def vin_region(v: str) -> str:
    if not v:
        return ""
    c = v[0].upper()
    for a, b, name in _REGIONS:
        if a <= c <= b:
            return name
    return ""


def vin_check_digit_ok(v: str) -> bool | None:
    """North-American check digit (position 9). None when the VIN is not 17 characters."""
    if len(v) != 17:
        return None
    vals = {**{str(i): i for i in range(10)}, **dict(zip("ABCDEFGH", range(1, 9))), **dict(zip("JKLMN", range(1, 6))),
            "P": 7, "R": 9, **dict(zip("STUVWXYZ", range(2, 10)))}
    weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
    try:
        total = sum(vals[c] * w for c, w in zip(v.upper(), weights))
    except KeyError:
        return False
    check = total % 11
    return v[8].upper() == ("X" if check == 10 else str(check))
