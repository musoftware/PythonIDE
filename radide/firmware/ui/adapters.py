"""Thin bridge between the workbench UI and the firmware sub-packages (no Qt).

Every function first asks the real module of its slice (radide/firmware/formats, cpu, disasm, maps, checksum,
project - see docs/FIRMWARE.md) and falls back to a small built-in implementation when that module is missing or
raises, so the workbench keeps working while the slices grow. ``backends()`` reports which side answered.

Data model used by the UI:

* ``Image``   - bytes + load address + format name + notes (from a .bin / .hex / .s19 / .ori / .mod file).
* ``MapDef``  - one calibration map / curve / value: address, rows x cols, cell type, axes, factor, unit.
* checksum profiles are plain dicts ``{name, algo, start, end, store, width, endian}`` (see ``verify``).
"""
from __future__ import annotations

import importlib
import json
import math
import struct
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import eeprom

_USED: dict[str, str] = {}          # area -> "slice" | "built-in" (last call)


def _mod(name: str):
    try:
        return importlib.import_module(f"radide.firmware.{name}")
    except Exception:  # noqa: BLE001 - a slice that is missing or broken falls back to the built-in code
        return None


def _call(area: str, candidates, *args, **kw):
    """Try ``module:function`` candidates in order; returns (found, result)."""
    for spec in candidates:
        modname, _, fn = spec.partition(":")
        m = _mod(modname)
        f = getattr(m, fn, None) if m is not None else None
        if callable(f):
            try:
                res = f(*args, **kw)
            except (NotImplementedError, TypeError):
                continue
            except Exception:  # noqa: BLE001 - fall back on any slice error
                continue
            _USED[area] = f"radide.firmware.{modname}.{fn}"
            return True, res
    _USED[area] = "built-in"
    return False, None


def backends() -> dict[str, str]:
    return dict(_USED)


# ============================================================================ images
@dataclass
class Image:
    data: bytearray
    base: int = 0
    fmt: str = "binary"
    path: str = ""
    notes: list[str] = field(default_factory=list)
    gaps: list[tuple[int, int]] = field(default_factory=list)    # (offset, length) filled with 0xFF

    def __len__(self) -> int:
        return len(self.data)


TEXT_FORMATS = {".hex": "ihex", ".ihex": "ihex", ".ihx": "ihex", ".s19": "srec", ".s28": "srec", ".s37": "srec",
                ".srec": "srec", ".mot": "srec", ".sx": "srec"}


def _sniff_text(head: bytes) -> str:
    s = head.lstrip()
    if s.startswith(b":") and all(c in b"0123456789ABCDEFabcdef:\r\n" for c in s[:200]):
        return "ihex"
    if s[:1] == b"S" and s[1:2] in b"0123456789" and all(c in b"0123456789ABCDEFabcdefS\r\n" for c in s[:200]):
        return "srec"
    return ""


def sniff_format(path) -> str:
    p = Path(path)
    try:
        with open(p, "rb") as f:
            head = f.read(512)
    except OSError:
        return ""
    return _sniff_text(head) or "binary"


def _parse_ihex(text: str) -> tuple[dict[int, int], list[str]]:
    mem: dict[int, int] = {}
    upper = 0
    notes = []
    for no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line.startswith(":"):
            continue
        rec = bytes.fromhex(line[1:])
        n, addr, typ = rec[0], (rec[1] << 8) | rec[2], rec[3]
        payload = rec[4:4 + n]
        if (sum(rec) & 0xFF) != 0:
            notes.append(f"line {no}: bad record checksum")
        if typ == 0:
            a = upper + addr
            for i, b in enumerate(payload):
                mem[a + i] = b
        elif typ == 1:
            break
        elif typ == 2:
            upper = int.from_bytes(payload, "big") << 4
        elif typ == 4:
            upper = int.from_bytes(payload, "big") << 16
    return mem, notes


def _parse_srec(text: str) -> tuple[dict[int, int], list[str]]:
    mem: dict[int, int] = {}
    notes = []
    alen = {"1": 2, "2": 3, "3": 4}
    for no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if len(line) < 4 or line[0] != "S":
            continue
        t = line[1]
        rec = bytes.fromhex(line[2:])
        if ((sum(rec) + 1) & 0xFF) != 0:
            notes.append(f"line {no}: bad record checksum")
        if t in alen:
            k = alen[t]
            a = int.from_bytes(rec[1:1 + k], "big")
            for i, b in enumerate(rec[1 + k:-1]):
                mem[a + i] = b
    return mem, notes


def _mem_to_image(mem: dict[int, int], fmt: str, path: str, notes: list[str]) -> Image:
    if not mem:
        return Image(bytearray(), 0, fmt, path, notes + ["no data records"])
    lo, hi = min(mem), max(mem)
    if hi - lo > 64 << 20:
        raise ValueError("the records span more than 64 MB")
    data = bytearray(b"\xFF" * (hi - lo + 1))
    for a, b in mem.items():
        data[a - lo] = b
    gaps = []
    run = None
    for i in range(len(data)):
        if (lo + i) not in mem:
            run = run if run is not None else i
        elif run is not None:
            gaps.append((run, i - run))
            run = None
    return Image(data, lo, fmt, path, notes, gaps)


def _image_from_slice(res, path, fmt) -> Image | None:
    """Accept what a formats slice may return: Image-like objects, (data, base) tuples or bytes."""
    if res is None:
        return None
    if isinstance(res, (bytes, bytearray)):
        return Image(bytearray(res), 0, fmt, str(path))
    if isinstance(res, tuple) and res and isinstance(res[0], (bytes, bytearray)):
        return Image(bytearray(res[0]), int(res[1]) if len(res) > 1 else 0, fmt, str(path))
    data = None
    for attr in ("data", "flat", "image", "bytes"):
        v = getattr(res, attr, None)
        if callable(v):
            try:
                v = v()
            except TypeError:
                v = None
        if isinstance(v, (bytes, bytearray)):
            data = v
            break
    if data is None:
        for meth in ("to_bytes", "flatten", "tobinary", "as_bytes"):
            f = getattr(res, meth, None)
            if callable(f):
                try:
                    v = f()
                except TypeError:
                    continue
                if isinstance(v, tuple):
                    v = v[0]
                if isinstance(v, (bytes, bytearray)):
                    data = v
                    break
    if data is None:
        return None
    base = 0
    for attr in ("base", "start", "min_address", "load_address", "origin"):
        v = getattr(res, attr, None)
        if callable(v):
            try:
                v = v()
            except TypeError:
                v = None
        if isinstance(v, int):
            base = v
            break
    return Image(bytearray(data), base, str(getattr(res, "format", "") or fmt), str(path))


def load_image(path) -> Image:
    """Read a firmware file. Intel HEX / S-records are flattened (gaps = 0xFF) at their lowest address."""
    p = Path(path)
    fmt = sniff_format(p)
    found, res = _call("formats", ("formats:load", "formats:load_file", "formats:read_file", "formats:open_image"), p)
    img = _image_from_slice(res, p, fmt) if found else None
    if img is not None:
        return img
    _USED["formats"] = "built-in"
    if fmt in ("ihex", "srec"):
        text = p.read_text(encoding="latin-1", errors="replace")
        mem, notes = (_parse_ihex if fmt == "ihex" else _parse_srec)(text)
        return _mem_to_image(mem, fmt, str(p), notes)
    return Image(bytearray(p.read_bytes()), 0, "binary", str(p))


def is_firmware_text(path) -> bool:
    return sniff_format(path) in ("ihex", "srec")


# ============================================================================ analysis
def entropy_blocks(data: bytes, block: int = 4096) -> list[float]:
    out = []
    for i in range(0, len(data), block):
        chunk = data[i:i + block]
        if not chunk:
            break
        counts = [0] * 256
        for b in chunk:
            counts[b] += 1
        n = len(chunk)
        out.append(-sum(c / n * math.log2(c / n) for c in counts if c) / 8.0)
    return out


def strings(data: bytes, min_len: int = 6, limit: int = 400) -> list[tuple[int, str]]:
    out = []
    start = None
    for i, b in enumerate(data):
        if 32 <= b < 127:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= min_len:
                out.append((start, data[start:i].decode("ascii")))
                if len(out) >= limit:
                    return out
            start = None
    if start is not None and len(data) - start >= min_len:
        out.append((start, data[start:].decode("ascii")))
    return out


_CPU_HINTS = [
    # (arch id, title, mode for capstone, byte patterns)
    ("ppc", "PowerPC (big-endian)", (b"\x7c\x08\x02\xa6", b"\x4e\x80\x00\x20", b"\x94\x21\xff")),
    ("arm-thumb", "ARM Cortex-M / Thumb (little-endian)", (b"\x70\x47", b"\x00\xbf", b"\x10\xb5", b"\xbd\xe8")),
    ("arm", "ARM (32-bit, little-endian)", (b"\x1e\xff\x2f\xe1", b"\x04\xe0\x2d\xe5")),
    ("tricore", "Infineon TriCore (little-endian)", (b"\x00\x90", b"\x0d\x00\x00\x00")),
    ("m68k", "Motorola 68k / CPU32 (big-endian)", (b"\x4e\x75", b"\x4e\x56")),
    ("mips", "MIPS (big-endian)", (b"\x03\xe0\x00\x08",)),
    ("sh", "SuperH (big-endian)", (b"\x00\x0b\x00\x09",)),
]


def cpu_guess(data: bytes) -> list[tuple[str, str, float]]:
    """[(arch id, title, score 0..1)] best first - asks radide/firmware/cpu first."""
    found, res = _call("cpu", ("cpu:guess", "cpu:detect", "cpu:detect_cpu", "cpu.detect:detect"), bytes(data))
    if found and res:
        out = []
        try:
            for r in (res if isinstance(res, (list, tuple)) else [res]):
                if isinstance(r, (tuple, list)):
                    out.append((str(r[0]), str(r[1] if len(r) > 2 else r[0]), float(r[-1])))
                else:
                    arch = str(getattr(r, "arch", "") or getattr(r, "id", "") or r)
                    out.append((arch, str(getattr(r, "title", "") or getattr(r, "name", "") or arch),
                                float(getattr(r, "score", 0) or getattr(r, "confidence", 0) or 0.5)))
            if out:
                return out
        except Exception:  # noqa: BLE001
            pass
    _USED["cpu"] = "built-in"
    sample = bytes(data[: 2 << 20])
    scores = []
    for arch, title, pats in _CPU_HINTS:
        hits = sum(sample.count(p) for p in pats)
        scores.append((arch, title, hits))
    total = sum(s for *_x, s in scores) or 1
    return sorted(((a, t, s / total) for a, t, s in scores if s), key=lambda r: -r[2]) or \
        [("unknown", "Unknown CPU", 0.0)]


def analyze(img: Image) -> dict:
    """Facts for the Analysis tab: format, size, base, EEPROM guess, CPU guesses, entropy, strings."""
    d = bytes(img.data)
    info = {"Format": img.fmt, "Size": f"{len(d):,} bytes (0x{len(d):X})", "Load address": f"0x{img.base:08X}"}
    ee = eeprom.guess(d, img.path)
    if ee is not None:
        info["EEPROM sizes"] = ", ".join(ee.chips) or "-"
        info["Blank bytes"] = f"{ee.blank:.0%}"
    cpus = cpu_guess(d)
    info["CPU (guess)"] = "; ".join(f"{t} {s:.0%}" for _a, t, s in cpus[:3])
    ff = d.count(0xFF)
    info["0xFF bytes"] = f"{ff:,} ({ff / max(1, len(d)):.0%})"
    found, res = _call("analysis", ("formats:identify", "cpu:base_address", "cpu:guess_base"), d)
    if found and res:
        info["Identification"] = str(res)[:300]
    return {"facts": info, "entropy": entropy_blocks(d, max(256, len(d) // 256 or 256)),
            "strings": strings(d), "cpu": cpus, "eeprom": ee}


# ============================================================================ disassembly
ARCHES = {"ppc": "PowerPC BE", "ppc-vle": "PowerPC VLE (Ghidra)", "arm-thumb": "ARM Thumb", "arm": "ARM",
          "arm64": "ARM64", "tricore": "TriCore", "m68k": "68000 / CPU32", "mips": "MIPS BE", "sh": "SuperH",
          "c166": "C166 / ST10 (Ghidra)", "x86": "x86 (16-bit)", "6502": "6502", "z80": "Z80"}


def _capstone(arch: str):
    import capstone as cs
    table = {"ppc": (cs.CS_ARCH_PPC, cs.CS_MODE_32 | cs.CS_MODE_BIG_ENDIAN),
             "arm-thumb": (cs.CS_ARCH_ARM, cs.CS_MODE_THUMB), "arm": (cs.CS_ARCH_ARM, cs.CS_MODE_ARM),
             "arm64": (cs.CS_ARCH_ARM64, cs.CS_MODE_ARM),
             "tricore": (getattr(cs, "CS_ARCH_TRICORE", None), getattr(cs, "CS_MODE_TRICORE_162", 0)),
             "m68k": (cs.CS_ARCH_M68K, cs.CS_MODE_M68K_040),
             "mips": (cs.CS_ARCH_MIPS, cs.CS_MODE_MIPS32 | cs.CS_MODE_BIG_ENDIAN),
             "sh": (getattr(cs, "CS_ARCH_SH", None), getattr(cs, "CS_MODE_SH2", 0) | cs.CS_MODE_BIG_ENDIAN),
             "x86": (cs.CS_ARCH_X86, cs.CS_MODE_16),
             "6502": (getattr(cs, "CS_ARCH_MOS65XX", None), getattr(cs, "CS_MODE_MOS65XX_6502", 0))}
    a = table.get(arch)
    if a is None or a[0] is None:
        return None
    md = cs.Cs(*a)
    md.skipdata = True
    return md


def disassemble(data: bytes, base: int, arch: str, start: int, count: int = 400) -> list[tuple[int, str, str, str]]:
    """[(address, hex bytes, mnemonic, operands)] - radide/firmware/disasm first, capstone otherwise."""
    found, res = _call("disasm", ("disasm:disassemble", "disasm:listing"), bytes(data), base, arch, start, count)
    if found and res:
        out = []
        for r in res:
            if isinstance(r, (tuple, list)) and len(r) >= 3:
                out.append((int(r[0]), str(r[1]) if len(r) > 3 else "", str(r[-2]), str(r[-1])))
            else:
                out.append((int(getattr(r, "address", 0)), bytes(getattr(r, "bytes", b"")).hex(" "),
                            str(getattr(r, "mnemonic", "")), str(getattr(r, "op_str", "") or
                                                                  getattr(r, "operands", ""))))
        if out:
            return out
    _USED["disasm"] = "built-in (capstone)"
    try:
        md = _capstone(arch)
    except ImportError:
        md = None
    if md is None:
        return [(base + start, "", ";", f"no built-in disassembler for {ARCHES.get(arch, arch)} - "
                                          "use Open in Ghidra")]
    off = max(0, start - base) if start >= base else start
    out = []
    for ins in md.disasm(bytes(data[off:off + count * 6]), base + off):
        out.append((ins.address, ins.bytes.hex(" "), ins.mnemonic, ins.op_str))
        if len(out) >= count:
            break
    return out


def find_ghidra() -> str | None:
    found, res = _call("ghidra", ("disasm:find_ghidra", "disasm.ghidra:find_ghidra"))
    if found:
        return res or None
    try:
        from ...importers.exe.native import find_ghidra as fg
        return fg()
    except Exception:  # noqa: BLE001
        return None


# ============================================================================ maps
CELL = {"u8": (">B", 1), "s8": (">b", 1), "u16be": (">H", 2), "u16le": ("<H", 2), "s16be": (">h", 2),
        "s16le": ("<h", 2), "u32be": (">I", 4), "u32le": ("<I", 4), "s32be": (">i", 4), "s32le": ("<i", 4),
        "f32be": (">f", 4), "f32le": ("<f", 4)}
CELL_TITLES = {"u8": "8-bit", "s8": "8-bit signed", "u16be": "16-bit Hi-Lo", "u16le": "16-bit Lo-Hi",
               "s16be": "16-bit Hi-Lo signed", "s16le": "16-bit Lo-Hi signed", "u32be": "32-bit Hi-Lo",
               "u32le": "32-bit Lo-Hi", "s32be": "32-bit Hi-Lo signed", "s32le": "32-bit Lo-Hi signed",
               "f32be": "float Hi-Lo", "f32le": "float Lo-Hi"}


@dataclass
class MapDef:
    name: str = "Map"
    address: int = 0             # file offset of the first data cell
    rows: int = 1
    cols: int = 1
    cell: str = "u16be"
    factor: float = 1.0
    offset: float = 0.0          # physical = raw * factor + offset
    unit: str = ""
    x_addr: int = 0              # 0 = no axis (index numbers)
    y_addr: int = 0
    x_cell: str = ""
    y_cell: str = ""
    x_factor: float = 1.0
    y_factor: float = 1.0
    x_unit: str = ""
    y_unit: str = ""
    folder: str = ""
    score: float = 0.0
    source: str = "user"         # user | finder | a2l | project
    comment: str = ""

    @property
    def width(self) -> int:
        return CELL.get(self.cell, (">H", 2))[1]

    @property
    def size(self) -> int:
        return self.rows * self.cols * self.width

    @property
    def kind(self) -> str:
        return "value" if self.rows * self.cols == 1 else ("curve" if self.rows == 1 or self.cols == 1 else "map")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_any(cls, m) -> "MapDef":
        if isinstance(m, MapDef):
            return m
        d = m if isinstance(m, dict) else {k: getattr(m, k) for k in dir(m) if not k.startswith("_")}
        alias = {"addr": "address", "data_addr": "address", "offset_addr": "address", "nx": "cols", "ny": "rows",
                 "x_address": "x_addr", "y_address": "y_addr", "type": "cell", "cell_type": "cell",
                 "datatype": "cell", "x_axis_addr": "x_addr", "y_axis_addr": "y_addr", "conversion_factor": "factor"}
        kw = {}
        names = set(cls.__dataclass_fields__)
        for k, v in d.items():
            k2 = alias.get(k, k)
            if k2 in names and not callable(v):
                kw[k2] = v
        out = cls(**kw)
        out.cell = _norm_cell(out.cell)
        out.x_cell = _norm_cell(out.x_cell) if out.x_cell else ""
        out.y_cell = _norm_cell(out.y_cell) if out.y_cell else ""
        return out


def _norm_cell(c) -> str:
    s = str(c or "u16be").lower().replace("_", "").replace("-", "")
    if s in CELL:
        return s
    syn = {"uint8": "u8", "ubyte": "u8", "byte": "u8", "int8": "s8", "sbyte": "s8", "uint16": "u16be",
           "uword": "u16be", "word": "u16be", "int16": "s16be", "sword": "s16be", "uint32": "u32be",
           "ulong": "u32be", "int32": "s32be", "slong": "s32be", "float32": "f32be", "float32ieee": "f32be",
           "u16": "u16be", "s16": "s16be", "u32": "u32be", "s32": "s32be", "f32": "f32be",
           "u16hilo": "u16be", "u16lohi": "u16le"}
    return syn.get(s, "u16be")


def read_cells(data: bytes, addr: int, count: int, cell: str) -> list:
    fmt, w = CELL.get(cell, (">H", 2))
    if addr < 0 or addr + count * w > len(data):
        return []
    return list(struct.unpack_from(fmt[0] + fmt[1] * count, data, addr))


def pack_cell(value, cell: str) -> bytes:
    fmt, w = CELL.get(cell, (">H", 2))
    if fmt[1] in "f":
        return struct.pack(fmt, float(value))
    lo, hi = {1: (0, 0xFF), 2: (0, 0xFFFF), 4: (0, 0xFFFFFFFF)}[w]
    if fmt[1].islower():
        lo, hi = -(hi + 1) // 2, hi // 2
    return struct.pack(fmt, max(lo, min(hi, int(round(value)))))


def read_map(data: bytes, m: MapDef) -> tuple[list, list, list[list]]:
    """(x axis raw, y axis raw, rows of raw values)."""
    vals = read_cells(data, m.address, m.rows * m.cols, m.cell)
    rows = [vals[r * m.cols:(r + 1) * m.cols] for r in range(m.rows)] if vals else []
    xs = read_cells(data, m.x_addr, m.cols, m.x_cell or m.cell) if m.x_addr else list(range(m.cols))
    ys = read_cells(data, m.y_addr, m.rows, m.y_cell or m.cell) if m.y_addr else list(range(m.rows))
    return xs or list(range(m.cols)), ys or list(range(m.rows)), rows


def cell_address(m: MapDef, r: int, c: int) -> int:
    return m.address + (r * m.cols + c) * m.width


def _smooth(vals: list, cols: int) -> float:
    """0 = perfectly smooth, 1 = noise. Mean absolute 2nd difference along rows and columns over the range."""
    if not vals:
        return 1.0
    rng = max(vals) - min(vals)
    if rng <= 0:
        return 1.0
    rows = len(vals) // cols
    acc = n = 0
    for r in range(rows):
        row = vals[r * cols:(r + 1) * cols]
        for i in range(1, len(row) - 1):
            acc += abs(row[i - 1] - 2 * row[i] + row[i + 1])
            n += 1
    for c in range(cols):
        col = vals[c::cols]
        for i in range(1, len(col) - 1):
            acc += abs(col[i - 1] - 2 * col[i] + col[i + 1])
            n += 1
    return (acc / max(1, n)) / rng


def _increasing_len(vals, i: int, max_len: int = 64) -> int:
    j = i
    while j + 1 < len(vals) and vals[j + 1] > vals[j] and j - i + 1 < max_len:
        j += 1
    return j - i + 1


def builtin_find_maps(data: bytes, limit: int = 300) -> list[MapDef]:
    """WinOLS-style guesser (no definitions needed).

    1. Bosch-style blocks: count words ``nx, ny`` then two increasing axes then a smooth nx*ny block (or ``n``,
       one axis, n smooth values for a curve) - high score.
    2. Bare axes: an increasing run of 4..32 points, optionally a second increasing run, then a smooth block.
    Smoothness = mean absolute 2nd difference over the value range (maps are smooth, code is not)."""
    d = bytes(data)
    out: list[MapDef] = []
    taken: list[tuple[int, int]] = []

    def free(a, b):
        return all(b <= s or a >= e for s, e in taken)

    def add(m: MapDef, start: int):
        out.append(m)
        taken.append((start, m.address + m.size))

    def ascii_run(vals, i, n):
        return all(0x20 <= v < 0x7F for v in vals[i:i + n])

    for cell in ("u16be", "u16le", "u8"):
        fmt, w = CELL[cell]
        n = len(d) // w
        if n < 8:
            continue
        vals = struct.unpack_from(fmt[0] + fmt[1] * n, d, 0)
        # ---- 1. Bosch-style headers
        for i in range(n - 6):
            nx = vals[i]
            if not 2 <= nx <= 32:
                continue
            ny = vals[i + 1]
            start = i * w
            if 2 <= ny <= 32 and _increasing_len(vals, i + 2, nx) >= nx and                     _increasing_len(vals, i + 2 + nx, ny) >= ny:
                addr = (i + 2 + nx + ny) * w
                if addr + nx * ny * w <= len(d) and free(start, addr + nx * ny * w):
                    cells = vals[i + 2 + nx + ny:i + 2 + nx + ny + nx * ny]
                    if len(set(cells)) >= 3 and not (cell == "u8" and ascii_run(vals, i, nx + ny + 2)):
                        rough = _smooth(list(cells), nx)
                        if rough <= 0.35:
                            add(MapDef(f"Map {ny}x{nx} @{addr:06X}", addr, ny, nx, cell, x_addr=(i + 2) * w,
                                       y_addr=(i + 2 + nx) * w, x_cell=cell, y_cell=cell,
                                       score=round(2.0 - rough, 3), source="finder"), start)
                            continue
            if nx >= 3 and _increasing_len(vals, i + 1, nx) >= nx:
                addr = (i + 1 + nx) * w
                if addr + nx * w <= len(d) and free(start, addr + nx * w):
                    cells = vals[i + 1 + nx:i + 1 + 2 * nx]
                    if len(set(cells)) >= 3 and not (cell == "u8" and ascii_run(vals, i, 2 * nx + 1)):
                        rough = _smooth(list(cells), nx)
                        if rough <= 0.3:
                            add(MapDef(f"Curve {nx} @{addr:06X}", addr, 1, nx, cell, x_addr=(i + 1) * w,
                                       x_cell=cell, score=round(1.6 - rough, 3), source="finder"), start)
        # ---- 2. bare axes
        i = 0
        while i < n - 4 and len(out) < limit:
            ln = _increasing_len(vals, i, 32)
            if ln < 4 or (cell == "u8" and ascii_run(vals, i, ln)) or not free(i * w, (i + ln) * w):
                i += max(1, ln)
                continue
            best = None
            for trim in range(0, min(3, ln - 3)):
                xi, nx = i + trim, ln - trim
                yl = _increasing_len(vals, xi + nx, 32) if xi + nx < n else 0
                for ny in range(min(yl, 32), 1, -1):
                    a = xi + nx + ny
                    cells = vals[a:a + nx * ny]
                    if len(cells) < nx * ny or len(set(cells)) < 3:
                        continue
                    r = _smooth(list(cells), nx)
                    if r <= 0.35 and (best is None or r < best[0]):
                        best = (r, xi, nx, ny, a)
                a = xi + nx
                cells = vals[a:a + nx]
                if best is None and len(cells) == nx and len(set(cells)) >= 3:
                    r = _smooth(list(cells), nx)
                    if r <= 0.25:
                        best = (r + 0.2, xi, nx, 1, a)
            if best is not None:
                r, xi, nx, ny, a = best
                if free(xi * w, (a + nx * ny) * w):
                    add(MapDef(f"Potential {'map' if ny > 1 else 'curve'} @{a * w:06X}", a * w, ny, nx, cell,
                               x_addr=xi * w, y_addr=(xi + nx) * w if ny > 1 else 0, x_cell=cell,
                               y_cell=cell if ny > 1 else "", score=round(1.0 - r + (0.2 if ny > 1 else 0), 3),
                               source="finder"), xi * w)
                    i = a + nx * ny
                    continue
            i += ln
        if len(out) >= limit:
            break
    out.sort(key=lambda m: (-m.score, m.address))
    return out


def find_maps(data: bytes) -> list[MapDef]:
    found, res = _call("maps", ("maps:find_maps", "maps.finder:find_maps", "maps:find", "maps.finder:find"),
                       bytes(data))
    if found and res is not None:
        try:
            return [MapDef.from_any(m) for m in res]
        except Exception:  # noqa: BLE001
            pass
    _USED["maps"] = "built-in"
    return builtin_find_maps(data)


def parse_a2l(text: str) -> list[MapDef]:
    """CHARACTERISTIC entries of an ASAP2 file -> MapDef (the maps slice first; built-in: address, kind and
    the dimensions of MAP / CURVE / VALUE, cell size from the record layout name)."""
    found, res = _call("a2l", ("maps.a2l:parse", "maps.a2l:parse_a2l", "maps:parse_a2l", "a2l:parse"), text)
    if found and res is not None:
        try:
            items = res.get("maps", res) if isinstance(res, dict) else getattr(res, "maps", res)
            return [MapDef.from_any(m) for m in items]
        except Exception:  # noqa: BLE001
            pass
    _USED["a2l"] = "built-in"
    import re
    out = []
    for blk in re.finditer(r"/begin\s+CHARACTERISTIC\s+(\S+)\s+\"([^\"]*)\"\s+(\w+)\s+(0x[0-9A-Fa-f]+)\s+(\S+)"
                           r"(.*?)/end\s+CHARACTERISTIC", text, re.S):
        name, desc, kind, addr, layout, body = blk.groups()
        dims = [int(x) for x in re.findall(r"/begin\s+AXIS_DESCR\s+\w+\s+\S+\s+\S+\s+(\d+)", body)]
        lay = layout.upper()
        cell = "u8" if ("UBYTE" in lay or "_U8" in lay or "BYTE" in lay) else \
            "s16be" if ("SWORD" in lay or "S16" in lay) else "u16be"
        cols = dims[0] if dims else 1
        rows = dims[1] if len(dims) > 1 else 1
        if kind.upper() == "VALUE":
            rows = cols = 1
        out.append(MapDef(name, int(addr, 16), rows, cols, cell, comment=desc, source="a2l", folder="A2L"))
    return out


# ============================================================================ checksums
def _sum(data, start, end, width, endian):
    fmt = {1: "B", 2: "H", 4: "I"}[width]
    n = (end - start) // width
    vals = struct.unpack_from(("<" if endian == "little" else ">") + fmt * n, data, start)
    return sum(vals)


def builtin_checksum(data: bytes, p: dict) -> int:
    algo = str(p.get("algo", "sum16be")).lower()
    s, e = int(p.get("start", 0)), int(p.get("end", len(data)))
    w = int(p.get("width", 2))
    mask = (1 << (8 * w)) - 1
    if algo.startswith("crc32"):
        return zlib.crc32(bytes(data[s:e])) & 0xFFFFFFFF
    if algo.startswith("crc16"):
        crc = 0xFFFF
        for b in data[s:e]:
            crc ^= b << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
                crc &= 0xFFFF
        return crc
    if algo.startswith("xor8"):
        x = 0
        for b in data[s:e]:
            x ^= b
        return x
    if algo.startswith("sum8"):
        return sum(data[s:e]) & mask
    word = 4 if "32" in algo else 2
    endian = "little" if algo.endswith("le") else "big"
    v = _sum(data, s, e, word, endian)
    if "complement" in algo or algo.startswith("neg"):
        v = -v
    return v & mask


def verify(data: bytes, profiles: list[dict]) -> list[dict]:
    """[{name, ok, stored, computed, store, width, algo}] - radide/firmware/checksum first."""
    found, res = _call("checksum", ("checksum:verify", "checksum:verify_all", "checksum.engine:verify"),
                       bytes(data), profiles)
    if found and isinstance(res, (list, tuple)) and res:
        out = []
        for r in res:
            d = r if isinstance(r, dict) else {k: getattr(r, k) for k in dir(r) if not k.startswith("_")}
            out.append({"name": d.get("name", "?"), "ok": bool(d.get("ok", d.get("valid", False))),
                        "stored": d.get("stored", 0), "computed": d.get("computed", d.get("expected", 0)),
                        "store": d.get("store", d.get("address", 0)), "width": d.get("width", 0),
                        "algo": d.get("algo", d.get("algorithm", ""))})
        return out
    _USED["checksum"] = "built-in"
    out = []
    for p in profiles:
        w = int(p.get("width", 2))
        st = int(p.get("store", 0))
        if st + w > len(data):
            out.append({**p, "ok": False, "stored": 0, "computed": 0, "error": "outside the file"})
            continue
        stored = int.from_bytes(bytes(data[st:st + w]), "little" if p.get("endian") == "little" else "big")
        comp = builtin_checksum(data, p)
        out.append({"name": p.get("name", "?"), "ok": stored == comp, "stored": stored, "computed": comp,
                    "store": st, "width": w, "algo": p.get("algo", "")})
    return out


def fix(data: bytes, profiles: list[dict]) -> tuple[bytes, list[dict]]:
    """Write correct checksums (profiles in order); returns (new data, verify report after fixing)."""
    found, res = _call("checksum_fix", ("checksum:fix", "checksum:fix_all", "checksum.engine:fix"),
                       bytes(data), profiles)
    if found and res is not None:
        new = res[0] if isinstance(res, tuple) else res
        if isinstance(new, (bytes, bytearray)) and len(new) == len(data):
            return bytes(new), verify(new, profiles)
    _USED["checksum_fix"] = "built-in"
    d = bytearray(data)
    for p in profiles:
        w = int(p.get("width", 2))
        st = int(p.get("store", 0))
        if st + w > len(d):
            continue
        comp = builtin_checksum(d, p)
        d[st:st + w] = comp.to_bytes(w, "little" if p.get("endian") == "little" else "big")
    return bytes(d), verify(d, profiles)


# ============================================================================ differences
def diff_ranges(a: bytes, b: bytes, limit: int = 20000) -> list[tuple[int, int]]:
    out = []
    n = min(len(a), len(b))
    i = 0
    while i < n and len(out) < limit:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    if len(a) != len(b):
        out.append((n, abs(len(a) - len(b))))
    return out


# ============================================================================ ECU projects
PROJECT_FILE = "ecu.json"


@dataclass
class EcuProject:
    """Fallback ECU project (``ecu.json``) used until radide/firmware/project provides its own model:
    original (never written), working copy, versions, maps, checksum profiles and the build output."""
    folder: Path
    name: str = "ECU"
    original: str = ""
    working: str = ""
    versions: list[dict] = field(default_factory=list)          # {file, note, time}
    maps: list[dict] = field(default_factory=list)
    checksums: list[dict] = field(default_factory=list)
    output: str = ""
    base: int = 0
    arch: str = ""
    extra: dict = field(default_factory=dict)
    native: object = None                                        # the project slice object, when it answered

    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.folder / p

    def rel(self, p) -> str:
        try:
            return Path(p).resolve().relative_to(self.folder.resolve()).as_posix()
        except ValueError:
            return str(p)

    @property
    def original_path(self) -> Path | None:
        return self.path(self.original) if self.original else None

    @property
    def working_path(self) -> Path | None:
        return self.path(self.working) if self.working else None

    @property
    def output_path(self) -> Path:
        return self.path(self.output or f"build/{self.name}.bin")

    def map_defs(self) -> list[MapDef]:
        return [MapDef.from_any(m) for m in self.maps]

    def save(self) -> None:
        if self.native is not None:
            for meth in ("save",):
                f = getattr(self.native, meth, None)
                if callable(f):
                    try:
                        self._push_native()
                        f()
                        return
                    except Exception:  # noqa: BLE001
                        break
        d = {k: v for k, v in asdict(self).items() if k not in ("folder", "native")}
        (self.folder / PROJECT_FILE).write_text(json.dumps(d, indent=1), encoding="utf-8")

    def _push_native(self) -> None:
        n = self.native
        for k in ("maps", "checksums"):
            if hasattr(n, k):
                try:
                    setattr(n, k, getattr(self, k))
                except Exception:  # noqa: BLE001
                    pass

    @classmethod
    def load(cls, folder) -> "EcuProject":
        folder = Path(folder)
        found, res = _call("project", ("project:load", "project:EcuProject.load", "project:load_project"), folder)
        if not found:
            m = _mod("project")
            klass = getattr(m, "EcuProject", None) if m is not None else None
            if klass is not None and callable(getattr(klass, "load", None)):
                try:
                    res, found = klass.load(folder), True
                    _USED["project"] = "radide.firmware.project.EcuProject.load"
                except Exception:  # noqa: BLE001
                    found = False
        if found and res is not None:
            return cls._from_native(folder, res)
        _USED["project"] = "built-in"
        p = folder / PROJECT_FILE
        d = json.loads(p.read_text(encoding="utf-8"))
        names = set(cls.__dataclass_fields__) - {"folder", "native"}
        return cls(folder, **{k: v for k, v in d.items() if k in names})

    @classmethod
    def _from_native(cls, folder: Path, n) -> "EcuProject":
        def get(*names, default=None):
            for k in names:
                v = n.get(k) if isinstance(n, dict) else getattr(n, k, None)
                if callable(v) and not isinstance(v, type):
                    try:
                        v = v()
                    except TypeError:
                        v = None
                if v not in (None, ""):
                    return v
            return default
        def rel(v):
            return "" if v in (None, "") else str(v)
        vers = []
        for v in get("versions", default=[]) or []:
            if isinstance(v, dict):
                vers.append({"file": rel(v.get("file") or v.get("path")), "note": v.get("note", ""),
                             "time": v.get("time", "")})
            else:
                vers.append({"file": rel(getattr(v, "file", "") or getattr(v, "path", "")),
                             "note": str(getattr(v, "note", "") or getattr(v, "comment", "")),
                             "time": str(getattr(v, "time", "") or getattr(v, "created", ""))})
        maps = []
        for m in get("maps", default=[]) or []:
            try:
                maps.append(MapDef.from_any(m).to_dict())
            except Exception:  # noqa: BLE001
                pass
        cks = []
        for c in get("checksums", "checksum_profiles", default=[]) or []:
            cks.append(c if isinstance(c, dict) else {k: getattr(c, k) for k in dir(c) if not k.startswith("_")
                                                     and not callable(getattr(c, k))})
        return cls(folder, name=str(get("name", default=folder.name)),
                   original=rel(get("original", "original_file", "ori", default="")),
                   working=rel(get("working", "working_file", "work", "mod", default="")),
                   versions=vers, maps=maps, checksums=cks,
                   output=rel(get("output", "output_file", default="")), base=int(get("base", default=0) or 0),
                   arch=str(get("arch", "cpu", default="") or ""), native=n)

    @classmethod
    def create(cls, folder, name: str, source=None, data: bytes | None = None, checksums=None,
               maps=None) -> "EcuProject":
        """New project: copies *source* (or *data*) to original/<name>.ori (read-only use) and work/<name>.bin."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        raw = data if data is not None else Path(source).read_bytes()
        ext = Path(source).suffix if source else ".bin"
        ori = folder / "original" / f"{name}{'.ori' if ext.lower() != '.ori' else ext}"
        ori.parent.mkdir(parents=True, exist_ok=True)
        ori.write_bytes(raw)
        work = folder / "work" / f"{name}.bin"
        work.parent.mkdir(parents=True, exist_ok=True)
        work.write_bytes(raw)
        (folder / "versions").mkdir(exist_ok=True)
        p = cls(folder, name, original=f"original/{ori.name}", working=f"work/{work.name}",
                checksums=list(checksums or []), maps=[MapDef.from_any(m).to_dict() for m in (maps or [])],
                output=f"build/{name}.mod.bin")
        p.save()
        return p

    def add_version(self, data: bytes, note: str = "") -> Path:
        import time
        f = getattr(self.native, "add_version", None) if self.native is not None else None
        if callable(f):
            try:
                r = f(data, note)
                if r:
                    return Path(r)
            except Exception:  # noqa: BLE001
                pass
        n = len(self.versions) + 1
        p = self.folder / "versions" / f"{self.name}_v{n:03d}.bin"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(bytes(data))
        self.versions.append({"file": self.rel(p), "note": note, "time": time.strftime("%Y-%m-%d %H:%M")})
        self.save()
        return p

    def build(self, data: bytes | None = None, log=print) -> tuple[Path, list[dict]]:
        """Working copy (or *data*) with corrected checksums -> output file; returns (path, checksum report)."""
        f = getattr(self.native, "build", None) if self.native is not None else None
        if callable(f) and data is None:
            try:
                r = f()
                out = Path(r[0] if isinstance(r, tuple) else r) if r else self.output_path
                if out.is_file():
                    return out, verify(out.read_bytes(), self.checksums)
            except Exception as e:  # noqa: BLE001
                log(f"[ecu] project build: {e} - using the built-in build")
        src = bytes(data) if data is not None else self.working_path.read_bytes()
        new, report = fix(src, self.checksums) if self.checksums else (src, [])
        out = self.output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(new)
        log(f"Build: {self.rel(out)} ({len(new):,} bytes), checksums: "
            + (", ".join(f"{r['name']} {'OK' if r['ok'] else 'BAD'}" for r in report) or "no profiles"))
        return out, report


def is_ecu_project(folder) -> bool:
    if folder is None:
        return False
    f = Path(folder)
    if (f / PROJECT_FILE).is_file():
        return True
    m = _mod("project")
    fn = getattr(m, "is_project", None) or getattr(m, "is_ecu_project", None) if m is not None else None
    if callable(fn):
        try:
            return bool(fn(f))
        except Exception:  # noqa: BLE001
            return False
    return False


__all__ = ["Image", "MapDef", "EcuProject", "load_image", "sniff_format", "is_firmware_text", "analyze",
           "cpu_guess", "entropy_blocks", "strings", "disassemble", "ARCHES", "find_ghidra", "find_maps",
           "builtin_find_maps", "parse_a2l", "read_map", "read_cells", "pack_cell", "cell_address", "CELL",
           "CELL_TITLES", "verify", "fix", "builtin_checksum", "diff_ranges", "is_ecu_project", "backends",
           "PROJECT_FILE", "TEXT_FORMATS"]
