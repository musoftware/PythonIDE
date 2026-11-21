"""Firmware containers: open and save raw binaries (.bin .ori .mod .rom .dump ...), Intel HEX, Motorola
S-record and ELF as a :class:`~radide.firmware.formats.memmap.MemoryMap` (segments at addresses + gaps).

    from radide.firmware.formats import load, save, detect_format
    m = load("ecu.s19")              # MemoryMap
    save(m, "ecu.hex")               # format from the extension (or fmt="ihex")
    save(m, "ecu.bin", fill=0xFF)    # flat image from the lowest address, gaps filled

Pure Python, no dependencies.
"""
from __future__ import annotations

from pathlib import Path

from . import elf, ihex, srec
from .memmap import MemoryMap, Segment, Symbol

__all__ = ["MemoryMap", "Segment", "Symbol", "load", "load_bytes", "save", "dumps", "detect_format",
           "FORMATS", "RAW_EXTS", "IHEX_EXTS", "SREC_EXTS", "ELF_EXTS", "FIRMWARE_EXTS", "format_for_path"]

RAW_EXTS = {".bin", ".ori", ".mod", ".rom", ".dump", ".dmp", ".img", ".fls", ".eep", ".epr", ".e2p", ".frf"}
IHEX_EXTS = {".hex", ".ihex", ".ihx", ".h86", ".a43"}
SREC_EXTS = {".s19", ".s28", ".s37", ".mot", ".srec", ".s", ".sx", ".mhx", ".s1", ".s2", ".s3", ".exo"}
ELF_EXTS = {".elf", ".axf", ".out", ".abs"}
FIRMWARE_EXTS = RAW_EXTS | IHEX_EXTS | SREC_EXTS | ELF_EXTS

# id -> (display name, default extension)
FORMATS = {"raw": ("Raw binary", ".bin"), "ihex": ("Intel HEX", ".hex"), "srec": ("Motorola S-record", ".s19"),
           "elf": ("ELF", ".elf")}


def detect_format(head: bytes, name: str = "") -> str:
    """'elf' / 'ihex' / 'srec' / 'raw' from the content (the extension only breaks ties)."""
    if elf.looks_like(head):
        return "elf"
    if ihex.looks_like(head):
        return "ihex"
    if srec.looks_like(head):
        return "srec"
    return "raw"


def format_for_path(path) -> str:
    ext = Path(path).suffix.lower()
    if ext in IHEX_EXTS:
        return "ihex"
    if ext in SREC_EXTS:
        return "srec"
    if ext in ELF_EXTS:
        return "elf"
    return "raw"


def load_bytes(data: bytes, name: str = "", base: int = 0, fmt: str = "") -> MemoryMap:
    fmt = fmt or detect_format(data[:4096], name)
    if fmt == "elf":
        m = elf.parse(data)
    elif fmt == "ihex":
        m = ihex.parse(data.decode("latin-1"))
    elif fmt == "srec":
        m = srec.parse(data.decode("latin-1"))
    else:
        m = MemoryMap.from_bytes(data, base, Path(name).name if name else "")
        m.meta["format"] = "raw"
    m.meta.setdefault("format", fmt)
    return m


def load(path, base: int = 0, fmt: str = "") -> MemoryMap:
    """Open a firmware file. *base* is the load address of a raw binary (ignored for HEX / S-record / ELF)."""
    p = Path(path)
    m = load_bytes(p.read_bytes(), p.name, base, fmt)
    m.meta["path"] = str(p)
    return m


def dumps(m: MemoryMap, fmt: str, fill: int = 0xFF, **kw) -> bytes:
    if fmt == "ihex":
        return ihex.dumps(m, **kw).encode("ascii")
    if fmt == "srec":
        return srec.dumps(m, **kw).encode("ascii")
    if fmt == "elf":
        return elf.dumps(m, **kw)
    return m.to_flat(fill)


def save(m: MemoryMap, path, fmt: str = "", fill: int = 0xFF, **kw) -> Path:
    p = Path(path)
    fmt = fmt or format_for_path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(dumps(m, fmt, fill, **kw))
    return p
