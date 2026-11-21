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
    native: object = None                                         # formats.MemoryMap when that slice loaded it

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
    if callable(getattr(res, "to_flat", None)):                  # formats.memmap.MemoryMap
        def val(name, default=0):
            v = getattr(res, name, default)
            return v() if callable(v) else v
        flat = res.to_flat(0xFF)
        base = int(val("min_address", 0) or 0) if flat else 0
        meta = getattr(res, "meta", {}) or {}
        f = str(meta.get("format", fmt) or fmt)
        gaps = []
        try:
            for g in val("gaps", []) or []:
                a, b = int(g[0]), int(g[1])
                gaps.append((a - base, b - a if b > a else b))
        except Exception:  # noqa: BLE001
            gaps = []
        img = Image(bytearray(flat), base, "binary" if f == "raw" else f, str(path), gaps=gaps)
        img.native = res
        return img
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
    """[(arch id, title, confidence 0..1)] best first - radide/firmware/analysis/arch first."""
    m = _mod("analysis.arch")
    if m is not None and hasattr(m, "guess_arch"):
        try:
            res = m.guess_arch(bytes(data))
            out = [(g.arch, str(getattr(g, "label", g.arch)), float(g.confidence)) for g in res]
            _USED["cpu"] = "radide.firmware.analysis.arch.guess_arch"
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


def base_guess(data: bytes, arch: str) -> list[tuple[int, float, str]]:
    """[(load address, confidence, reason)] from radide/firmware/analysis/arch (empty when missing)."""
    m = _mod("analysis.arch")
    if m is None or not hasattr(m, "guess_base") or not arch or arch == "unknown":
        return []
    try:
        return [(int(b.base), float(b.confidence), str(b.reason)) for b in m.guess_base(bytes(data), arch)][:5]
    except Exception:  # noqa: BLE001
        return []


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
    bases = base_guess(d, cpus[0][0]) if cpus else []
    if bases:
        info["Load address (guess)"] = "; ".join(f"0x{b:08X} {c:.0%}" for b, c, _r in bases[:3])
    block = max(256, len(d) // 256 or 256)
    ent = None
    em = _mod("analysis.entropy")
    if em is not None and hasattr(em, "entropy_profile"):
        try:
            ent = [float(x) for x in em.entropy_profile(d, block)]
            if ent and max(ent) > 1.0:                 # bits per byte (0..8) -> 0..1
                ent = [x / 8.0 for x in ent]
            regions = em.summary(em.classify(d, 1024)) if hasattr(em, "classify") else {}
            if regions:
                info["Regions"] = ", ".join(f"{k} {v:,}" for k, v in regions.items())
            _USED["analysis"] = "radide.firmware.analysis"
        except Exception:  # noqa: BLE001
            ent = None
    strs = None
    sm = _mod("analysis.strings")
    if sm is not None and hasattr(sm, "find_strings"):
        try:
            found = sm.find_strings(d, 6, True, 2000)
            strs = [(f.offset, f.text) for f in found[:400]]
            ident = sm.identification(found) if hasattr(sm, "identification") else []
            if ident:
                info["Identification strings"] = " | ".join(f.text for f in ident[:6])[:300]
        except Exception:  # noqa: BLE001
            strs = None
    return {"facts": info, "entropy": ent if ent else entropy_blocks(d, block),
            "strings": strs if strs is not None else strings(d), "cpu": cpus, "eeprom": ee, "bases": bases}


# ============================================================================ disassembly
ARCHES = {"ppc": "PowerPC BE", "ppc-vle": "PowerPC VLE (Ghidra)", "arm-thumb": "ARM Thumb", "arm": "ARM",
          "arm64": "ARM64", "tricore": "TriCore", "m68k": "68000 / CPU32", "mips": "MIPS BE", "sh": "SuperH",
          "c166": "C166 / ST10 (Ghidra)", "hc12": "HC12 / S12", "sh2": "SuperH SH-2", "v850": "V850 (Ghidra)",
          "8051": "8051 (Ghidra)", "x86": "x86 (16-bit)", "6502": "6502"}


def _capstone(arch: str):
    import capstone as cs
    table = {"ppc": (cs.CS_ARCH_PPC, cs.CS_MODE_32 | cs.CS_MODE_BIG_ENDIAN),
             "arm-thumb": (cs.CS_ARCH_ARM, cs.CS_MODE_THUMB), "arm": (cs.CS_ARCH_ARM, cs.CS_MODE_ARM),
             "arm64": (cs.CS_ARCH_ARM64, cs.CS_MODE_ARM),
             "tricore": (getattr(cs, "CS_ARCH_TRICORE", None), getattr(cs, "CS_MODE_TRICORE_162", 0)),
             "m68k": (cs.CS_ARCH_M68K, cs.CS_MODE_M68K_040),
             "mips": (cs.CS_ARCH_MIPS, cs.CS_MODE_MIPS32 | cs.CS_MODE_BIG_ENDIAN),
             "sh": (getattr(cs, "CS_ARCH_SH", None), getattr(cs, "CS_MODE_SH2", 0) | cs.CS_MODE_BIG_ENDIAN),
             "sh2": (getattr(cs, "CS_ARCH_SH", None), getattr(cs, "CS_MODE_SH2", 0) | cs.CS_MODE_BIG_ENDIAN),
             "hc12": (getattr(cs, "CS_ARCH_M680X", None), getattr(cs, "CS_MODE_M680X_CPU12", 0)),
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
    found, res = _call("ghidra", ("analysis.ghidra:find_ghidra", "disasm:find_ghidra", "disasm.ghidra:find_ghidra"))
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
        score = None
        if not isinstance(m, dict) and hasattr(m, "mapdef"):          # maps.finder.Candidate
            score = float(getattr(m, "score", 0) or 0)
            m = m.mapdef
        if isinstance(m, dict) and "dtype" in m:                       # maps.model.MapDef.to_dict()
            mm = _mod("maps.model")
            if mm is not None and hasattr(mm, "MapDef"):
                try:
                    m = mm.MapDef.from_dict(m)
                except Exception:  # noqa: BLE001
                    pass
        if not isinstance(m, dict) and hasattr(m, "dtype") and hasattr(m, "x_axis"):
            out = cls._from_slice_map(m)
            if score is not None:
                out.score = round(score / 50.0, 3)         # 0..100 -> 0..2 like the built-in finder
            return out
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
        for k in ("address", "x_addr", "y_addr"):
            if isinstance(kw.get(k), str):
                kw[k] = int(kw[k], 0) if kw[k].strip() else 0
        out = cls(**kw)
        out.cell = _norm_cell(out.cell)
        out.x_cell = _norm_cell(out.x_cell) if out.x_cell else ""
        out.y_cell = _norm_cell(out.y_cell) if out.y_cell else ""
        return out

    @classmethod
    def _from_slice_map(cls, m) -> "MapDef":
        """radide.firmware.maps.model.MapDef (dtype + endian, AxisDef axes) -> the UI model."""
        def cell(dt, en):
            dt = str(dt or "u16").lower()
            return dt if dt in ("u8", "s8") else _norm_cell(f"{dt}{'le' if str(en).lower() == 'le' else 'be'}")
        x, y = m.x_axis, m.y_axis
        out = cls(name=str(m.name or f"Map_{m.address:06X}"), address=int(m.address), rows=max(1, int(m.rows)),
                  cols=max(1, int(m.cols)), cell=cell(m.dtype, m.endian), factor=float(m.factor or 1.0),
                  offset=float(m.offset or 0.0), unit=str(m.unit or ""), folder=str(getattr(m, "folder", "") or ""),
                  source=str(getattr(m, "source", "") or "finder"), comment=str(getattr(m, "description", "") or ""))
        if getattr(x, "stored", False):
            out.x_addr, out.x_cell, out.x_factor, out.x_unit = int(x.address), cell(x.dtype, x.endian), \
                float(x.factor or 1.0), str(x.unit or "")
        if getattr(y, "stored", False):
            out.y_addr, out.y_cell, out.y_factor, out.y_unit = int(y.address), cell(y.dtype, y.endian), \
                float(y.factor or 1.0), str(y.unit or "")
        if str(getattr(m, "order", "row")) == "col":
            out.comment = (out.comment + " " if out.comment else "") + "(column order: shown transposed)"
            out.rows, out.cols = out.cols, out.rows
            out.x_addr, out.y_addr, out.x_cell, out.y_cell = out.y_addr, out.x_addr, out.y_cell, out.x_cell
        return out

    def to_slice_map(self):
        """The maps slice's MapDef for this map (None when radide/firmware/maps is missing)."""
        mm = _mod("maps.model")
        if mm is None or not hasattr(mm, "MapDef"):
            return None
        def split(c):
            c = c or self.cell
            return (c, "le") if c in ("u8", "s8") else (c[:-2], c[-2:])
        dt, en = split(self.cell)
        m = mm.MapDef(self.name, self.address, cols=self.cols, rows=self.rows, dtype=dt, endian=en,
                      factor=self.factor, offset=self.offset, unit=self.unit, folder=self.folder,
                      description=self.comment, source=self.source)
        if self.x_addr:
            xd, xe = split(self.x_cell)
            m.x_axis = mm.AxisDef(address=self.x_addr, count=self.cols, dtype=xd, endian=xe, factor=self.x_factor,
                                  unit=self.x_unit)
        if self.y_addr:
            yd, ye = split(self.y_cell)
            m.y_axis = mm.AxisDef(address=self.y_addr, count=self.rows, dtype=yd, endian=ye, factor=self.y_factor,
                                  unit=self.y_unit)
        return m


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
            if 2 <= ny <= 32 and _increasing_len(vals, i + 2, nx) >= nx and \
                    _increasing_len(vals, i + 2 + nx, ny) >= ny:
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


def parse_a2l(text: str, data: bytes | None = None) -> list[MapDef]:
    """CHARACTERISTIC entries of an ASAP2 file -> MapDef (the maps slice first; built-in: address, kind and
    the dimensions of MAP / CURVE / VALUE, cell size from the record layout name)."""
    found, res = _call("a2l", ("maps.a2l:parse_a2l", "maps:parse_a2l"), text, data)
    if found and res is not None:
        try:
            items = res.get("maps", res) if isinstance(res, dict) else getattr(res, "pack", None) or \
                getattr(res, "maps", res)
            out = [MapDef.from_any(m) for m in items]
            for m in out:
                m.source = "a2l"
            return out
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
def norm_profile(p: dict) -> dict:
    """A checksum profile in the checksum slice's JSON shape (``algorithm``, ``ranges`` [start, end), ``store``,
    ``width``, ``endian`` be/le). Older built-in shapes (``algo``, ``start`` / ``end``, ``big``) are converted."""
    d = dict(p)
    if "algorithm" not in d and "algo" in d:
        a = str(d.pop("algo")).lower()
        for suf in ("be", "le"):
            if a.startswith(("sum16", "sum32", "xor16", "xor32")) and a.endswith(suf) and not a.endswith("-" + suf):
                a = a[:-2] + "-" + suf
        d["algorithm"] = a
    if "ranges" not in d and "start" in d:
        d["ranges"] = [[d.pop("start"), d.pop("end", 0)]]
    e = str(d.get("endian", "be")).lower()
    d["endian"] = "le" if e in ("le", "little") else "be"
    return d


def _ranges_of(d: dict) -> list[tuple[int, int]]:
    out = []
    for r in d.get("ranges", []) or []:
        out.append((int(str(r[0]), 0) if isinstance(r[0], str) else int(r[0]),
                    int(str(r[1]), 0) if isinstance(r[1], str) else int(r[1])))
    return out


def _int(v) -> int:
    return int(v, 0) if isinstance(v, str) else int(v or 0)


def builtin_checksum(data: bytes, p: dict) -> int:
    d = norm_profile(p)
    algo = str(d.get("algorithm", "sum16-be")).lower()
    w = _int(d.get("width", 0)) or (4 if "32" in algo else 1 if algo in ("sum8", "xor8", "crc8") else 2)
    mask = (1 << (8 * w)) - 1
    blob = b"".join(bytes(data[s:e]) for s, e in _ranges_of(d))
    if algo.startswith("crc32"):
        return zlib.crc32(blob) & 0xFFFFFFFF
    if algo.startswith("crc16"):
        crc = 0xFFFF
        for b in blob:
            crc ^= b << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
                crc &= 0xFFFF
        return crc
    if algo.startswith("xor8"):
        x = 0
        for b in blob:
            x ^= b
        return x
    if algo.startswith("sum8") or algo.endswith("bytes"):
        v = sum(blob)
    else:
        word = 4 if "sum32" in algo else 2
        n = len(blob) // word
        v = sum(struct.unpack_from(("<" if "-le" in algo else ">") + ("I" if word == 4 else "H") * n, blob, 0))
    if algo.endswith("twos"):
        v = -v
    elif algo.endswith("ones"):
        v = ~v
    return v & mask


def _slice_blocks(profiles):
    ck = _mod("checksum")
    if ck is None or not hasattr(ck, "blocks_from_json"):
        return None, None
    try:
        return ck, ck.blocks_from_json([norm_profile(p) if isinstance(p, dict) else p.to_dict() for p in profiles])
    except Exception:  # noqa: BLE001
        return None, None


def _result_dict(r) -> dict:
    if isinstance(r, dict):
        return r
    ok = getattr(r, "ok", False)
    return {"name": getattr(r, "name", "?"), "ok": bool(ok() if callable(ok) else ok),
            "stored": int(getattr(r, "stored", 0) or 0), "computed": int(getattr(r, "computed", 0) or 0),
            "store": int(getattr(r, "store", 0) or 0), "width": int(getattr(r, "width", 0) or 0),
            "error": str(getattr(r, "error", "") or ""), "corrected": bool(getattr(r, "corrected", False)),
            "line": r.line() if callable(getattr(r, "line", None)) else ""}


def verify(data: bytes, profiles: list) -> list[dict]:
    """[{name, ok, stored, computed, store, width, error}] - radide/firmware/checksum first."""
    if not profiles:
        return []
    ck, blocks = _slice_blocks(profiles)
    if ck is not None:
        try:
            res = [_result_dict(r) for r in ck.verify(bytes(data), blocks)]
            _USED["checksum"] = "radide.firmware.checksum.verify"
            return res
        except Exception:  # noqa: BLE001
            pass
    _USED["checksum"] = "built-in"
    out = []
    for p in profiles:
        d = norm_profile(p)
        w = _int(d.get("width", 0)) or 2
        st = _int(d.get("store", 0))
        name = d.get("name", "?")
        if st + w > len(data) or any(e > len(data) for _s, e in _ranges_of(d)):
            out.append({"name": name, "ok": False, "stored": 0, "computed": 0, "store": st, "width": w,
                        "error": "outside the file"})
            continue
        stored = int.from_bytes(bytes(data[st:st + w]), "little" if d["endian"] == "le" else "big")
        comp = builtin_checksum(data, d)
        out.append({"name": name, "ok": stored == comp, "stored": stored, "computed": comp, "store": st,
                    "width": w, "error": ""})
    return out


def fix(data: bytes, profiles: list) -> tuple[bytes, list[dict]]:
    """Write correct checksums (profiles in order); returns (new data, report)."""
    ck, blocks = _slice_blocks(profiles)
    if ck is not None and hasattr(ck, "correct"):
        try:
            buf = bytearray(data)
            res = [_result_dict(r) for r in ck.correct(buf, blocks)]
            _USED["checksum_fix"] = "radide.firmware.checksum.correct"
            return bytes(buf), res
        except Exception:  # noqa: BLE001
            pass
    _USED["checksum_fix"] = "built-in"
    d = bytearray(data)
    for p in profiles:
        q = norm_profile(p)
        w = _int(q.get("width", 0)) or 2
        st = _int(q.get("store", 0))
        if st + w > len(d):
            continue
        d[st:st + w] = builtin_checksum(d, q).to_bytes(w, "little" if q["endian"] == "le" else "big")
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


def _native_project():
    m = _mod("project")
    return m if m is not None and hasattr(m, "EcuProject") else None


def _rel(folder: Path, p) -> str:
    try:
        return Path(p).resolve().relative_to(Path(folder).resolve()).as_posix()
    except ValueError:
        return str(p)


class EcuProject:
    """The workbench's view of an ECU project folder (``ecu.json``).

    Delegates to radide/firmware/project (``EcuProject``: original kept read-only + SHA-256, working copy,
    versions, checksum blocks, Build with report) and keeps a minimal built-in model when that package is missing.
    Maps live in the map pack of radide/firmware/maps (``<work>.maps.json`` or ecu.json "maps")."""

    def __init__(self, folder, native=None, data: dict | None = None):
        self.folder = Path(folder)
        self._stamp = None
        self.native = native
        self.d = data if data is not None else {}

    # The native project is re-read when ecu.json changed on disk since it was loaded (another tool - the ECU
    # project menu's Build Settings, the Versions dialog ... - saved it), so a later save here never writes
    # stale settings back.
    def _disk_stamp(self):
        try:
            st = (self.folder / PROJECT_FILE).stat()
            return st.st_mtime_ns, st.st_size
        except OSError:
            return None

    @property
    def native(self):
        n = self._native
        if n is not None:
            stamp = self._disk_stamp()
            if stamp is not None and stamp != self._stamp:
                np_ = _native_project()
                if self._stamp is not None and np_ is not None:
                    try:
                        n = self._native = np_.EcuProject.load(self.folder)
                    except Exception:  # noqa: BLE001 - half-written file: keep the loaded model
                        return n
                self._stamp = stamp
        return n

    @native.setter
    def native(self, value) -> None:
        self._native = value
        self._stamp = self._disk_stamp() if value is not None else None

    # ------------------------------------------------------------------ io
    @classmethod
    def load(cls, folder) -> "EcuProject":
        folder = Path(folder)
        np_ = _native_project()
        if np_ is not None:
            _USED["project"] = "radide.firmware.project.EcuProject"
            return cls(folder, np_.EcuProject.load(folder))
        _USED["project"] = "built-in"
        return cls(folder, None, json.loads((folder / PROJECT_FILE).read_text(encoding="utf-8")))

    @classmethod
    def create(cls, folder, name: str, source=None, data: bytes | None = None, checksums=None,
               maps=None) -> "EcuProject":
        """New project from a file (*source*) or bytes (*data*, written to original/<name>.bin first)."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if source is None:
            src = folder / "original" / f"{name}.bin"
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_bytes(bytes(data or b""))
            source, copy = src, False
        else:
            copy = True
        np_ = _native_project()
        if np_ is not None:
            ep = np_.new_project(folder, name, original=source, copy=copy)
            if checksums:
                ck = _mod("checksum")
                ep.checksums = ck.blocks_from_json([norm_profile(c) for c in checksums])
            ep.work_bytes()                       # creates the working copy
            ep.save()
            p = cls(folder, ep)
        else:
            raw = Path(source).read_bytes()
            work = folder / "work" / f"{name}.bin"
            work.parent.mkdir(parents=True, exist_ok=True)
            work.write_bytes(raw)
            p = cls(folder, None, {"name": name, "original": _rel(folder, source), "work": _rel(folder, work),
                                   "checksums": [norm_profile(c) for c in checksums or []], "versions": [],
                                   "output": f"build/{name}_mod.bin"})
            p.save()
        if maps:
            p.save_maps([MapDef.from_any(m) for m in maps])
        return p

    def save(self) -> None:
        if self.native is not None:
            self.native.save()
            return
        (self.folder / PROJECT_FILE).write_text(json.dumps(self.d, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ paths
    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.folder / p

    @property
    def name(self) -> str:
        return str(self.native.name if self.native is not None else self.d.get("name", self.folder.name))

    @property
    def original_path(self) -> Path | None:
        if self.native is not None:
            return self.native.original_path
        return self.path(self.d["original"]) if self.d.get("original") else None

    @property
    def working_path(self) -> Path | None:
        if self.native is not None:
            if self.native.work_path is None or not self.native.work_path.is_file():
                try:
                    self.native.work_bytes()
                    self.native.save()
                except Exception:  # noqa: BLE001
                    pass
            return self.native.work_path
        return self.path(self.d["work"]) if self.d.get("work") else None

    @property
    def output_path(self) -> Path:
        if self.native is not None:
            return self.native.output_path
        return self.path(self.d.get("output") or f"build/{self.name}_mod.bin")

    @property
    def base(self) -> int:
        return int(getattr(self.native, "image_base", 0) or 0) if self.native is not None else 0

    def original_bytes(self) -> bytes:
        if self.native is not None:
            return self.native.original_bytes()
        p = self.original_path
        return load_image(p).data if p is not None and p.is_file() else b""

    def work_bytes(self) -> bytes:
        if self.native is not None:
            return self.native.work_bytes()
        p = self.working_path
        return p.read_bytes() if p is not None and p.is_file() else self.original_bytes()

    def write_work(self, data: bytes) -> Path:
        if self.native is not None:
            p = self.native.write_work(bytes(data))
            self.native.save()
            return p
        p = self.working_path
        p.write_bytes(bytes(data))
        return p

    # ------------------------------------------------------------------ versions
    @property
    def versions(self) -> list[dict]:
        if self.native is not None:
            return [{"id": v.id, "name": v.name, "note": v.note, "time": v.created, "file": v.file}
                    for v in self.native.versions]
        return list(self.d.get("versions", []))

    def add_version(self, data: bytes, name: str = "", note: str = "") -> Path:
        import time
        if self.native is not None:
            v = self.native.snapshot(name, note, bytes(data))
            self.native.save()
            return self.path(v.file)
        vs = self.d.setdefault("versions", [])
        vid = f"v{len(vs) + 1:03d}"
        p = self.folder / "versions" / f"{vid}.bin"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(bytes(data))
        vs.append({"id": vid, "name": name or vid, "note": note, "time": time.strftime("%Y-%m-%d %H:%M"),
                   "file": _rel(self.folder, p)})
        self.save()
        return p

    def version_bytes(self, vid: str) -> bytes:
        if self.native is not None:
            return self.native.version_bytes(vid)
        v = next((v for v in self.versions if v["id"] == vid), None)
        return self.path(v["file"]).read_bytes() if v else b""

    # ------------------------------------------------------------------ checksums
    @property
    def checksums(self) -> list[dict]:
        if self.native is not None:
            return [b.to_dict() if hasattr(b, "to_dict") else dict(b) for b in self.native.checksums]
        return list(self.d.get("checksums", []))

    def set_checksums(self, profiles: list) -> None:
        if self.native is not None:
            ck = _mod("checksum")
            self.native.checksums = ck.blocks_from_json([norm_profile(p) for p in profiles])
        else:
            self.d["checksums"] = [norm_profile(p) for p in profiles]
        self.save()

    # ------------------------------------------------------------------ maps
    def _pack_path(self) -> Path:
        if self.native is not None and self.native.maps_path is not None:
            return self.native.maps_path
        if self.d.get("maps"):
            return self.path(self.d["maps"])
        w = self.working_path or self.folder / "work" / f"{self.name}.bin"
        return w.with_name(w.name + ".maps.json")

    def map_defs(self) -> list[MapDef]:
        p = self._pack_path()
        if not p.is_file():
            return []
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        out = []
        for m in d.get("maps", []):
            try:
                out.append(MapDef.from_any(m))
            except Exception:  # noqa: BLE001
                pass
        return out

    def save_maps(self, maps: list[MapDef]) -> Path:
        p = self._pack_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        mm = _mod("maps.model")
        if mm is not None and hasattr(mm, "MapPack"):
            pack = mm.MapPack(self.name, [m.to_slice_map() for m in maps], base_address=self.base)
            pack.save(p)
        else:
            p.write_text(json.dumps({"format": "radide-mappack", "version": 1, "name": self.name,
                                     "maps": [m.to_dict() for m in maps]}, indent=2), encoding="utf-8")
        rel = _rel(self.folder, p)
        if self.native is not None:
            if self.native.maps != rel:
                self.native.maps = rel
                self.native.save()
        elif self.d.get("maps") != rel:
            self.d["maps"] = rel
            self.save()
        return p

    # ------------------------------------------------------------------ build
    def build(self, data: bytes | None = None, log=print) -> tuple[Path, list[dict]]:
        """Working copy (saved from *data* first) + corrected checksums -> output; (path, checksum report)."""
        if data is not None:
            self.write_work(data)
        if self.native is not None:
            res = self.native.build(log=log)
            self.native.save()
            return Path(res.output), [_result_dict(r) for r in res.checksums]
        src = self.work_bytes()
        new, report = fix(src, self.checksums) if self.checksums else (src, [])
        out = self.output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(new)
        log(f"Build: {_rel(self.folder, out)} ({len(new):,} bytes)")
        return out, report


def is_ecu_project(folder) -> bool:
    return folder is not None and (Path(folder) / PROJECT_FILE).is_file()


__all__ = ["Image", "MapDef", "EcuProject", "load_image", "sniff_format", "is_firmware_text", "analyze",
           "cpu_guess", "entropy_blocks", "strings", "disassemble", "ARCHES", "find_ghidra", "find_maps",
           "builtin_find_maps", "parse_a2l", "read_map", "read_cells", "pack_cell", "cell_address", "CELL",
           "CELL_TITLES", "verify", "fix", "builtin_checksum", "norm_profile", "diff_ranges",
           "is_ecu_project", "backends",
           "PROJECT_FILE", "TEXT_FORMATS"]
