"""Checksum algorithms used by firmware / ECU images (pure Python, fast paths through zlib / binascii).

An algorithm is described by a small dict (stored in project files and shareable profiles):

    {"type": "crc", "width": 16, "poly": 0x1021, "init": 0xFFFF, "refin": False, "refout": False, "xorout": 0}
    {"type": "sum", "unit": 2, "unit_endian": "be", "width": 16, "complement": "none" | "ones" | "twos"}
    {"type": "xor", "unit": 1, "unit_endian": "le", "width": 8, "complement": "none" | "ones"}
    {"type": "adler32"}   {"type": "fletcher16"}   {"type": "fletcher32", "unit_endian": "le"}

or by a preset name from PRESETS ("crc32", "crc16-ccitt-false", "sum16-be", ...).  CRC parameters follow
the Rocksoft / CRC RevEng model, so any entry of the CRC catalogue can be written down.

"sum16" means "16-bit result": with unit 1 the bytes are added, with unit 2 / 4 the 16 / 32-bit words
(little- or big-endian) are added; "ones" stores ~sum (inverted), "twos" stores -sum (the whole block
then adds up to 0).  None of these presets claims to be a particular manufacturer's algorithm: users
verify a profile against their own original file (the finder helps with that).
"""
from __future__ import annotations

import binascii
import zlib
from functools import lru_cache

_REV8 = bytes(int(f"{i:08b}"[::-1], 2) for i in range(256))


def reflect(value: int, width: int) -> int:
    out = 0
    for _ in range(width):
        out = (out << 1) | (value & 1)
        value >>= 1
    return out


class AlgorithmError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------- presets
def _crc(width, poly, init=0, refin=False, refout=None, xorout=0, check=None, title=""):
    return {"type": "crc", "width": width, "poly": poly, "init": init, "refin": refin,
            "refout": refin if refout is None else refout, "xorout": xorout,
            **({"check": check} if check is not None else {}), **({"title": title} if title else {})}


def _sum(width, unit=1, endian="le", complement="none", title=""):
    return {"type": "sum", "width": width, "unit": unit, "unit_endian": endian, "complement": complement,
            **({"title": title} if title else {})}


# check = value over b"123456789" (CRC RevEng catalogue); verified by samples/Tests/Firmware/Checksum tests
PRESETS: dict[str, dict] = {
    "crc8": _crc(8, 0x07, check=0xF4, title="CRC-8 (SMBus)"),
    "crc8-sae-j1850": _crc(8, 0x1D, 0xFF, xorout=0xFF, check=0x4B, title="CRC-8/SAE-J1850"),
    "crc8-autosar": _crc(8, 0x2F, 0xFF, xorout=0xFF, check=0xDF, title="CRC-8/AUTOSAR"),
    "crc8-maxim": _crc(8, 0x31, 0, True, check=0xA1, title="CRC-8/MAXIM-DOW (Dallas 1-Wire)"),
    "crc16-ccitt-false": _crc(16, 0x1021, 0xFFFF, check=0x29B1, title="CRC-16/CCITT-FALSE (IBM-3740)"),
    "crc16-xmodem": _crc(16, 0x1021, 0, check=0x31C3, title="CRC-16/XMODEM"),
    "crc16-kermit": _crc(16, 0x1021, 0, True, check=0x2189, title="CRC-16/KERMIT (CCITT true)"),
    "crc16-x25": _crc(16, 0x1021, 0xFFFF, True, xorout=0xFFFF, check=0x906E, title="CRC-16/X-25 (IBM-SDLC)"),
    "crc16-aug-ccitt": _crc(16, 0x1021, 0x1D0F, check=0xE5CC, title="CRC-16/AUG-CCITT (SPI-FUJITSU)"),
    "crc16-genibus": _crc(16, 0x1021, 0xFFFF, xorout=0xFFFF, check=0xD64E, title="CRC-16/GENIBUS"),
    "crc16-arc": _crc(16, 0x8005, 0, True, check=0xBB3D, title="CRC-16/ARC (IBM)"),
    "crc16-modbus": _crc(16, 0x8005, 0xFFFF, True, check=0x4B37, title="CRC-16/MODBUS"),
    "crc16-usb": _crc(16, 0x8005, 0xFFFF, True, xorout=0xFFFF, check=0xB4C8, title="CRC-16/USB"),
    "crc16-buypass": _crc(16, 0x8005, 0, check=0xFEE8, title="CRC-16/UMTS (BUYPASS)"),
    "crc32": _crc(32, 0x04C11DB7, 0xFFFFFFFF, True, xorout=0xFFFFFFFF, check=0xCBF43926,
                  title="CRC-32 (ISO-HDLC, zip / Ethernet)"),
    "crc32-bzip2": _crc(32, 0x04C11DB7, 0xFFFFFFFF, xorout=0xFFFFFFFF, check=0xFC891918, title="CRC-32/BZIP2"),
    "crc32-mpeg2": _crc(32, 0x04C11DB7, 0xFFFFFFFF, check=0x0376E6E7, title="CRC-32/MPEG-2 (STM32 CRC unit)"),
    "crc32-posix": _crc(32, 0x04C11DB7, 0, xorout=0xFFFFFFFF, check=0x765E7680, title="CRC-32/CKSUM (POSIX)"),
    "crc32-jamcrc": _crc(32, 0x04C11DB7, 0xFFFFFFFF, True, check=0x340BC6D9, title="CRC-32/JAMCRC"),
    "crc32c": _crc(32, 0x1EDC6F41, 0xFFFFFFFF, True, xorout=0xFFFFFFFF, check=0xE3069283,
                   title="CRC-32C (Castagnoli, iSCSI)"),
    "crc32-autosar": _crc(32, 0xF4ACFB13, 0xFFFFFFFF, True, xorout=0xFFFFFFFF, check=0x1697D06A,
                          title="CRC-32/AUTOSAR"),
    "sum8": _sum(8, title="Sum of bytes, 8-bit"),
    "sum8-twos": _sum(8, complement="twos", title="Sum of bytes, 8-bit, two's complement (block adds to 0)"),
    "sum8-ones": _sum(8, complement="ones", title="Sum of bytes, 8-bit, inverted"),
    "sum16-bytes": _sum(16, title="Sum of bytes, 16-bit result"),
    "sum32-bytes": _sum(32, title="Sum of bytes, 32-bit result"),
    "sum16-le": _sum(16, 2, "le", title="Sum of 16-bit little-endian words"),
    "sum16-be": _sum(16, 2, "be", title="Sum of 16-bit big-endian words"),
    "sum16-be-ones": _sum(16, 2, "be", "ones", title="Sum of 16-bit big-endian words, inverted"),
    "sum16-be-twos": _sum(16, 2, "be", "twos", title="Sum of 16-bit big-endian words, two's complement"),
    "sum16-le-ones": _sum(16, 2, "le", "ones", title="Sum of 16-bit little-endian words, inverted"),
    "sum16-le-twos": _sum(16, 2, "le", "twos", title="Sum of 16-bit little-endian words, two's complement"),
    "sum32-le": _sum(32, 4, "le", title="Sum of 32-bit little-endian words"),
    "sum32-be": _sum(32, 4, "be", title="Sum of 32-bit big-endian words"),
    "sum32-be-ones": _sum(32, 4, "be", "ones", title="Sum of 32-bit big-endian words, inverted"),
    "sum32-be-twos": _sum(32, 4, "be", "twos", title="Sum of 32-bit big-endian words, two's complement"),
    "sum32-le-ones": _sum(32, 4, "le", "ones", title="Sum of 32-bit little-endian words, inverted"),
    "sum32-le-twos": _sum(32, 4, "le", "twos", title="Sum of 32-bit little-endian words, two's complement"),
    "xor8": {"type": "xor", "width": 8, "unit": 1, "unit_endian": "le", "complement": "none", "title": "XOR of bytes"},
    "xor16-be": {"type": "xor", "width": 16, "unit": 2, "unit_endian": "be", "complement": "none",
                 "title": "XOR of 16-bit big-endian words"},
    "xor32-be": {"type": "xor", "width": 32, "unit": 4, "unit_endian": "be", "complement": "none",
                 "title": "XOR of 32-bit big-endian words"},
    "adler32": {"type": "adler32", "width": 32, "check": 0x091E01DE, "title": "Adler-32"},
    "fletcher16": {"type": "fletcher16", "width": 16, "title": "Fletcher-16 (bytes, mod 255)"},
    "fletcher32": {"type": "fletcher32", "width": 32, "unit_endian": "le",
                   "title": "Fletcher-32 (16-bit little-endian words, mod 65535)"},
}

TYPES = ("crc", "sum", "xor", "adler32", "fletcher16", "fletcher32")


def resolve(spec) -> dict:
    """A preset name or an algorithm dict -> a complete, validated algorithm dict (a copy)."""
    if isinstance(spec, str):
        key = spec.strip().lower()
        if key not in PRESETS:
            raise AlgorithmError(f"Unknown checksum algorithm '{spec}'")
        d = dict(PRESETS[key])
        d["name"] = key
        return d
    if not isinstance(spec, dict):
        raise AlgorithmError(f"Bad checksum algorithm: {spec!r}")
    if spec.get("name") and spec.get("type") is None:
        return resolve(spec["name"])
    d = dict(spec)
    t = d.get("type")
    if t not in TYPES:
        raise AlgorithmError(f"Unknown checksum type '{t}'")
    if t == "crc":
        w = int(d.get("width", 0))
        if not 3 <= w <= 64:
            raise AlgorithmError("CRC width must be 3..64 bits")
        mask = (1 << w) - 1
        d["width"] = w
        for k in ("poly", "init", "xorout"):
            d[k] = _int(d.get(k, 0)) & mask
        if not d["poly"] & 1:
            raise AlgorithmError("A CRC polynomial must be odd (normal form, without the top bit)")
        d["refin"] = bool(d.get("refin", False))
        d["refout"] = bool(d.get("refout", d["refin"]))
    elif t in ("sum", "xor"):
        d["width"] = int(d.get("width", 8))
        d["unit"] = int(d.get("unit", 1))
        if d["width"] not in (8, 16, 32, 64) or d["unit"] not in (1, 2, 4, 8):
            raise AlgorithmError("Sum / XOR width must be 8, 16, 32 or 64 bits and the unit 1, 2, 4 or 8 bytes")
        d["unit_endian"] = "be" if str(d.get("unit_endian", "le")).lower() == "be" else "le"
        c = str(d.get("complement", "none")).lower()
        d["complement"] = c if c in ("none", "ones", "twos") else "none"
    elif t == "adler32":
        d["width"] = 32
    elif t == "fletcher16":
        d["width"] = 16
    elif t == "fletcher32":
        d["width"] = 32
        d["unit_endian"] = "be" if str(d.get("unit_endian", "le")).lower() == "be" else "le"
    return d


def _int(v) -> int:
    if isinstance(v, str):
        return int(v.strip(), 0)
    return int(v)


def describe(spec) -> str:
    try:
        d = resolve(spec)
    except AlgorithmError as e:
        return str(e)
    if d.get("title"):
        return str(d["title"])
    t = d["type"]
    if t == "crc":
        return (f"CRC-{d['width']} poly=0x{d['poly']:X} init=0x{d['init']:X} refin={d['refin']} "
                f"refout={d['refout']} xorout=0x{d['xorout']:X}")
    if t in ("sum", "xor"):
        unit = "bytes" if d["unit"] == 1 else f"{d['unit'] * 8}-bit {d['unit_endian'].upper()} words"
        comp = {"none": "", "ones": ", inverted", "twos": ", two's complement"}[d["complement"]]
        return f"{t.upper()} of {unit}, {d['width']}-bit result{comp}"
    return t


def short_name(spec) -> str:
    """A compact label: the preset name when the dict equals a preset, else a generated one."""
    try:
        d = resolve(spec)
    except AlgorithmError:
        return "?"
    if d.get("name"):
        return d["name"]
    core = {k: v for k, v in d.items() if k not in ("title", "check", "name")}
    for name, p in PRESETS.items():
        pc = {k: v for k, v in resolve(name).items() if k not in ("title", "check", "name")}
        if pc == core:
            return name
    if d["type"] == "crc":
        return f"crc{d['width']}-0x{d['poly']:X}"
    if d["type"] in ("sum", "xor"):
        return f"{d['type']}{d['width']}-u{d['unit']}{d['unit_endian']}-{d['complement']}"
    return d["type"]


# ---------------------------------------------------------------------------------------------- CRC engine
@lru_cache(maxsize=64)
def _table(width: int, poly: int, refin: bool) -> tuple:
    mask = (1 << width) - 1
    tbl = []
    if refin:
        rpoly = reflect(poly, width)
        for i in range(256):
            c = i
            for _ in range(8):
                c = (c >> 1) ^ rpoly if c & 1 else c >> 1
            tbl.append(c & mask)
    else:
        top = 1 << (width - 1)
        if width >= 8:
            for i in range(256):
                c = i << (width - 8)
                for _ in range(8):
                    c = ((c << 1) ^ poly) if c & top else (c << 1)
                tbl.append(c & mask)
        else:                       # narrow CRCs: compute on an 8-bit-aligned register
            for i in range(256):
                c = i
                p8 = poly << (8 - width)
                for _ in range(8):
                    c = ((c << 1) ^ p8) if c & 0x80 else (c << 1)
                tbl.append((c & 0xFF) >> (8 - width))
    return tuple(tbl)


def _crc_register_generic(data, width, poly, reg, refin) -> int:
    """Run the CRC register over *data* (table driven, any width); returns the raw register."""
    tbl = _table(width, poly, refin)
    mask = (1 << width) - 1
    if refin:
        for b in data:
            reg = (reg >> 8) ^ tbl[(reg ^ b) & 0xFF]
    elif width >= 8:
        sh = width - 8
        for b in data:
            reg = ((reg << 8) & mask) ^ tbl[((reg >> sh) ^ b) & 0xFF]
    else:
        p8 = poly << (8 - width)
        r = reg << (8 - width)
        for b in data:
            r ^= b
            for _ in range(8):
                r = ((r << 1) ^ p8) & 0xFF if r & 0x80 else (r << 1) & 0xFF
        reg = r >> (8 - width)
    return reg & mask


def crc_register(data, d: dict, reg: int | None = None) -> int:
    """The raw CRC register after *data*, starting from *reg* (default: the algorithm's init, already
    reflected for refin algorithms).  Use ``crc_finish`` to get the checksum."""
    w, poly, refin = d["width"], d["poly"], d["refin"]
    if reg is None:
        reg = reflect(d["init"], w) if refin else d["init"]
    if w == 32 and poly == 0x04C11DB7:          # zlib fast path
        if refin:
            return zlib.crc32(data, reg ^ 0xFFFFFFFF) ^ 0xFFFFFFFF
        r = zlib.crc32(bytes(data).translate(_REV8), reflect(reg, 32) ^ 0xFFFFFFFF) ^ 0xFFFFFFFF
        return reflect(r, 32)
    if w == 16 and poly == 0x1021:              # binascii.crc_hqx = CRC-16 0x1021, not reflected
        if not refin:
            return binascii.crc_hqx(data, reg)
        return reflect(binascii.crc_hqx(bytes(data).translate(_REV8), reflect(reg, 16)), 16)
    return _crc_register_generic(data, w, poly, reg, refin)


def crc_finish(reg: int, d: dict) -> int:
    w = d["width"]
    if d["refin"] != d["refout"]:
        reg = reflect(reg, w)
    return (reg ^ d["xorout"]) & ((1 << w) - 1)


def crc(data, spec) -> int:
    d = resolve(spec) if not (isinstance(spec, dict) and spec.get("_resolved")) else spec
    return crc_finish(crc_register(data, d), d)


# ---------------------------------------------------------------------------------------------- others
def units(data, unit: int, endian: str):
    """Iterate the *unit*-byte words of *data* (a short tail is zero-padded)."""
    data = bytes(data)
    if unit == 1:
        return data
    rem = len(data) % unit
    if rem:
        data += b"\0" * (unit - rem)
    try:
        import numpy as np
        dt = np.dtype({2: "u2", 4: "u4", 8: "u8"}[unit]).newbyteorder(">" if endian == "be" else "<")
        return np.frombuffer(data, dtype=dt)
    except Exception:  # noqa: BLE001 - numpy is optional
        bo = "big" if endian == "be" else "little"
        return [int.from_bytes(data[i:i + unit], bo) for i in range(0, len(data), unit)]


def _unit_sum(data, unit, endian) -> int:
    if unit == 1:
        return sum(data)
    u = units(data, unit, endian)
    try:
        return int(u.astype("uint64").sum(dtype="uint64")) if unit < 8 else sum(int(x) for x in u)
    except AttributeError:
        return sum(u)


def _unit_xor(data, unit, endian) -> int:
    u = units(data, unit, endian)
    try:
        import numpy as np
        if hasattr(u, "dtype"):
            return int(np.bitwise_xor.reduce(u)) if len(u) else 0
        if unit == 1 and len(u):
            return int(np.bitwise_xor.reduce(np.frombuffer(bytes(u), dtype=np.uint8)))
    except Exception:  # noqa: BLE001
        pass
    x = 0
    for v in u:
        x ^= int(v)
    return x


def finish_sum(total: int, d: dict) -> int:
    mask = (1 << d["width"]) - 1
    c = d.get("complement", "none")
    if c == "ones":
        total = ~total
    elif c == "twos":
        total = -total
    return total & mask


def fletcher16(data) -> int:
    s1 = s2 = 0
    for i in range(0, len(data), 5802):          # blocks small enough not to overflow (kept simple)
        for b in data[i:i + 5802]:
            s1 += b
            s2 += s1
        s1 %= 255
        s2 %= 255
    return (s2 << 8) | s1


def fletcher32(data, endian: str = "le") -> int:
    s1 = s2 = 0
    for w in units(data, 2, endian):
        s1 = (s1 + int(w)) % 65535
        s2 = (s2 + s1) % 65535
    return (s2 << 16) | s1


def compute(data, spec) -> int:
    """The checksum of *data* (bytes / bytearray / memoryview) for an algorithm name or dict."""
    d = resolve(spec)
    t = d["type"]
    if t == "crc":
        return crc_finish(crc_register(data, d), d)
    if t == "sum":
        return finish_sum(_unit_sum(data, d["unit"], d["unit_endian"]), d)
    if t == "xor":
        v = _unit_xor(data, d["unit"], d["unit_endian"])
        if d["complement"] == "ones":
            v = ~v
        return v & ((1 << d["width"]) - 1)
    if t == "adler32":
        return zlib.adler32(data) & 0xFFFFFFFF
    if t == "fletcher16":
        return fletcher16(bytes(data))
    if t == "fletcher32":
        return fletcher32(data, d["unit_endian"])
    raise AlgorithmError(t)


def compute_parts(parts, spec) -> int:
    """The checksum over several byte strings, as if they were concatenated (multi-range blocks).
    CRCs and Adler-32 run incrementally; the rest concatenate (word sums need alignment anyway)."""
    d = resolve(spec)
    if d["type"] == "crc":
        reg = None
        for p in parts:
            reg = crc_register(p, d, reg)
        if reg is None:
            reg = crc_register(b"", d)
        return crc_finish(reg, d)
    if d["type"] == "adler32":
        v = 1
        for p in parts:
            v = zlib.adler32(p, v)
        return v & 0xFFFFFFFF
    if d["type"] == "sum" and d["unit"] == 1:
        return finish_sum(sum(sum(p) for p in parts), d)
    return compute(b"".join(bytes(p) for p in parts), d)


def width_bytes(spec) -> int:
    d = resolve(spec)
    return (d["width"] + 7) // 8


def check_value(spec) -> int:
    """The algorithm's value over b"123456789" (compare with the CRC catalogue)."""
    return compute(b"123456789", spec)


def preset_names(kind: str = "") -> list[str]:
    return [n for n, p in PRESETS.items() if not kind or p["type"] == kind]


__all__ = ["PRESETS", "TYPES", "AlgorithmError", "resolve", "describe", "short_name", "compute", "compute_parts",
           "crc", "crc_register", "crc_finish", "reflect", "width_bytes", "check_value", "preset_names",
           "finish_sum", "fletcher16", "fletcher32", "units"]
