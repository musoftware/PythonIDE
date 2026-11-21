"""Which machine a ROM / program file is for (no Qt).

The ROM workbench slice (radide/retro/rom) owns the detailed header parsers; when it is present its
``detect()`` + ``emu_system()`` are used first, so both slices agree. This fallback looks at the extension and the
well-known magic bytes only.
"""
from __future__ import annotations

from pathlib import Path

EXT = {".a26": "a2600", ".nes": "nes", ".fds": "nes", ".unf": "nes", ".sfc": "snes", ".smc": "snes",
       ".gb": "gb", ".gbc": "gbc", ".cgb": "gbc", ".gba": "gba", ".agb": "gba", ".pce": "pce", ".sms": "sms",
       ".gg": "gg", ".prg": "c64", ".d64": "c64", ".t64": "c64", ".crt": "c64", ".tap": "c64", ".g64": "c64",
       ".p00": "c64", ".xex": "a8", ".atr": "a8", ".car": "a8", ".cas": "a8", ".atx": "a8", ".com": "dos",
       ".exe": "dos", ".bat": "dos"}


def _external(path: Path) -> str:
    """System id from the ROM workbench's header parsers (radide/retro/rom/detect.py) when that slice exists."""
    try:
        from ..rom.detect import detect, emu_system
    except Exception:  # noqa: BLE001 - the other slice is optional
        return ""
    try:
        if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
            return ""
        return emu_system(detect(path.read_bytes(), path.name)) or ""
    except Exception:  # noqa: BLE001
        return ""


def sniff(data: bytes, ext: str = "") -> str:
    """System of ROM bytes ("" = unknown)."""
    if data[:4] == b"NES\x1a":
        return "nes"
    if data[:16] == b"C64 CARTRIDGE   ":
        return "c64"
    if data[:2] == b"\x96\x02":
        return "a8"                                    # .ATR disk image
    if data[:4] == b"CART" and len(data) > 16:
        return "a8"                                    # .CAR cartridge image
    if data[:2] == b"\xff\xff" and len(data) > 6:
        return "a8"                                    # Atari DOS executable (.xex)
    if len(data) >= 0xC0 and data[0xB2] == 0x96 and data[3] == 0xEA:
        return "gba"                                   # fixed byte 0x96 + ARM branch at the entry point
    if len(data) >= 0x150 and data[0x100:0x101] in (b"\x00", b"\xc3") and data[0x104:0x105] == b"\xce":
        return "gbc" if data[0x143] & 0x80 else "gb"
    if data[:2] == b"MZ":
        return "dos" if not _is_windows_exe(data) else ""
    if ext in (".bin", ".rom") and len(data) in (2048, 4096, 8192, 12288, 16384, 32768, 65536):
        vec = data[-4:]
        if len(vec) == 4 and (vec[1] & 0xF0) in (0xF0, 0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0):
            return "a2600"                             # 6507 reset vector in the cartridge window
    return ""


def _is_windows_exe(data: bytes) -> bool:
    if len(data) < 0x40:
        return False
    off = int.from_bytes(data[0x3C:0x40], "little")
    return 0 < off < len(data) - 2 and data[off:off + 2] in (b"PE", b"NE", b"LE", b"LX")


def detect_system(path) -> str:
    """System id of *path* (a ROM / program file, or a folder = DOS program); "" when unknown."""
    p = Path(path)
    if p.is_dir():
        return "dos"
    ext = p.suffix.lower()
    got = _external(p)
    if got:
        return got
    try:
        with open(p, "rb") as f:
            head = f.read(0x200)
        size = p.stat().st_size
    except OSError:
        return EXT.get(ext, "")
    if ext == ".exe":
        try:
            data = p.read_bytes()[:0x10000]
        except OSError:
            data = head
        return "" if _is_windows_exe(data) else "dos"
    if ext in EXT:
        if ext == ".gb" and len(head) > 0x143 and head[0x143] & 0x80:
            return "gbc"
        return EXT[ext]
    if ext in (".bin", ".rom"):
        try:
            data = p.read_bytes() if size <= 65536 else head
        except OSError:
            data = head
        return sniff(data, ext)
    return sniff(head, ext)


__all__ = ["EXT", "detect_system", "sniff"]
