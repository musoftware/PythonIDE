"""ROM / disk / tape / program file detection for the hex editor's info panel and the ROM Hacking project.

``detect(data, filename)`` returns a :class:`RomInfo`: the system, rows for the info panel, header fields
(offset, length, name, kind) that the hex view highlights as a structure overlay, an optional listing
(files of a disk / tape image, BASIC lines, XEX segments...) and warnings. ``fix_checksum`` repairs the header
checksum of Game Boy / Color, Game Boy Advance, SNES, Sega Genesis and Atari 8-bit CAR files.

Everything is written from the publicly documented header layouts (iNES / NES 2.0, the Game Boy cartridge
header, the SNES internal header, the Sega Genesis header, Atari CAR / ATR / XEX, Commodore D64 / T64 / PRG,
ZX Spectrum TAP / TZX / SNA, DOS MZ). No ROM data is embedded: the Nintendo logo of Game Boy carts is *not*
checked (detection uses the header checksum and the file name).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# system ids double as the ``system`` argument of the emulator API (radide/retro/rom/emulink.py)
SYSTEM_NAMES = {
    "atari2600": "Atari 2600 (VCS)", "atari7800": "Atari 7800", "atari8bit": "Atari 8-bit (400/800/XL/XE)",
    "nes": "NES / Famicom", "fds": "Famicom Disk System", "gb": "Game Boy", "gbc": "Game Boy Color",
    "gba": "Game Boy Advance", "snes": "Super Nintendo (SNES)", "genesis": "Sega Genesis / Mega Drive",
    "sms": "Sega Master System / Game Gear", "c64": "Commodore 64", "zxspectrum": "ZX Spectrum",
    "dos": "MS-DOS program", "patch": "ROM patch", "unknown": "Unknown / raw binary",
}

KIND_COLORS = {"magic": "#2AA198", "size": "#268BD2", "flags": "#6C71C4", "title": "#859900",
               "checksum": "#DC322F", "vector": "#CB4B16", "info": "#93A1A1", "region": "#B58900",
               "data": "#657B83"}


@dataclass
class Field:
    offset: int
    length: int
    name: str
    value: str = ""
    kind: str = "info"

    @property
    def color(self) -> str:
        return KIND_COLORS.get(self.kind, "#93A1A1")


@dataclass
class RomInfo:
    system: str = "unknown"
    format: str = ""                       # "iNES", "NES 2.0", "LoROM", "D64", ...
    rows: list[tuple[str, str]] = field(default_factory=list)
    fields: list[Field] = field(default_factory=list)
    listing: list[tuple[str, ...]] = field(default_factory=list)
    listing_header: tuple[str, ...] = ()
    warnings: list[str] = field(default_factory=list)
    checksum_ok: bool | None = None        # None = the format has no checksum we check
    fixable: bool = False                  # fix_checksum() can repair it
    cpu_address: Callable[[int], int | None] | None = None   # file offset -> CPU address (inspector)
    cpu: str = ""                          # "6502", "65816", "68000", "z80", "sm83", "arm7", "x86"
    title: str = ""

    @property
    def system_name(self) -> str:
        return SYSTEM_NAMES.get(self.system, self.system)

    def add(self, offset: int, length: int, name: str, value, kind: str = "info", row: bool = True) -> None:
        v = str(value)
        self.fields.append(Field(offset, length, name, v, kind))
        if row:
            self.rows.append((name, v))


def _u16(d, o) -> int:
    return d[o] | (d[o + 1] << 8)


def _b16(d, o) -> int:
    return (d[o] << 8) | d[o + 1]


def _u32(d, o) -> int:
    return struct.unpack_from("<I", d, o)[0]


def _b32(d, o) -> int:
    return struct.unpack_from(">I", d, o)[0]


def _text(raw: bytes, enc: str = "latin-1") -> str:
    s = bytes(raw).split(b"\x00")[0].decode(enc, errors="replace")
    return "".join(c if 32 <= ord(c) < 127 or ord(c) > 160 else "." for c in s).strip()


def _printable(raw: bytes, min_ratio: float = 0.85) -> bool:
    if not raw:
        return False
    good = sum(1 for c in raw if 32 <= c < 127 or c == 0)
    return good / len(raw) >= min_ratio


def _kb(n: int) -> str:
    if n >= 1 << 20 and n % (1 << 20) == 0:
        return f"{n >> 20} MB"
    if n >= 1024 and n % 1024 == 0:
        return f"{n >> 10} KB"
    return f"{n:,} bytes"


# ============================================================================ NES
NES_MAPPERS = {0: "NROM", 1: "MMC1 (SxROM)", 2: "UxROM", 3: "CNROM", 4: "MMC3 (TxROM) / MMC6", 5: "MMC5",
               7: "AxROM", 9: "MMC2 (PxROM)", 10: "MMC4 (FxROM)", 11: "Color Dreams", 13: "CPROM",
               19: "Namco 163", 21: "VRC4a/c", 22: "VRC2a", 23: "VRC2b / VRC4e", 24: "VRC6a", 25: "VRC4b/d",
               26: "VRC6b", 30: "UNROM 512", 34: "BNROM / NINA-001", 66: "GxROM", 69: "Sunsoft FME-7",
               71: "Camerica / Codemasters", 73: "VRC3", 75: "VRC1", 79: "NINA-03/06", 85: "VRC7",
               111: "GTROM (Cheapocabra)", 118: "TxSROM", 119: "TQROM", 180: "UNROM (AND)", 206: "DxROM / Namco 108",
               210: "Namco 175/340", 228: "Action 52"}


def _detect_nes(d: bytes, info: RomInfo) -> None:
    f6, f7 = d[6], d[7]
    nes2 = (f7 & 0x0C) == 0x08
    info.system, info.format, info.cpu = "nes", "NES 2.0" if nes2 else "iNES", "6502"
    info.add(0, 4, "Magic", "NES<1A>", "magic", row=False)
    mapper = (f6 >> 4) | (f7 & 0xF0)
    sub = 0
    if nes2:
        mapper |= (d[8] & 0x0F) << 8
        sub = d[8] >> 4

    def size(lsb: int, msb: int, unit: int) -> int:
        if msb == 0x0F:                      # exponent-multiplier notation
            return (1 << (lsb >> 2)) * ((lsb & 3) * 2 + 1)
        return ((msb << 8) | lsb) * unit
    prg = size(d[4], d[9] & 0x0F if nes2 else 0, 16384)
    chr_ = size(d[5], d[9] >> 4 if nes2 else 0, 8192)
    info.add(4, 1, "PRG ROM", _kb(prg), "size")
    info.add(5, 1, "CHR ROM", _kb(chr_) if chr_ else "none (CHR RAM)", "size")
    mirror = "four-screen" if f6 & 8 else ("vertical" if f6 & 1 else "horizontal")
    info.add(6, 1, "Flags 6", f"mirroring {mirror}, battery {'yes' if f6 & 2 else 'no'}, "
             f"trainer {'yes' if f6 & 4 else 'no'}, mapper low {f6 >> 4}", "flags")
    console = ("NES/Famicom", "Vs. System", "PlayChoice-10", "extended")[f7 & 3]
    info.add(7, 1, "Flags 7", f"{console}, mapper high {f7 >> 4}" + (", NES 2.0" if nes2 else ""), "flags")
    info.rows.append(("Mapper", f"{mapper} - {NES_MAPPERS.get(mapper, 'unknown')}" + (f" (submapper {sub})" if nes2 else "")))
    info.rows.append(("Mirroring", mirror))
    if nes2:
        info.add(8, 1, "Mapper MSB / submapper", f"{d[8] & 15} / {sub}", "flags", row=False)
        info.add(9, 1, "PRG / CHR size MSB", f"{d[9]:02X}", "size", row=False)
        info.add(10, 1, "PRG RAM / NVRAM", f"{d[10]:02X}", "size", row=False)
        info.add(11, 1, "CHR RAM / NVRAM", f"{d[11]:02X}", "size", row=False)
        tv = ("NTSC", "PAL", "multi-region", "Dendy")[d[12] & 3]
        info.add(12, 1, "Timing", tv, "region")
    else:
        info.add(8, 1, "PRG RAM (8 KB units)", d[8] or 1, "size", row=False)
        info.add(9, 1, "TV system", "PAL" if d[9] & 1 else "NTSC", "region")
        if any(d[11:16]) and not nes2:
            info.warnings.append("Bytes 11-15 of the iNES header are not zero (old 'DiskDude!' style header?): "
                                 "emulators may read a wrong mapper.")
    off = 16
    if f6 & 4:
        info.add(16, 512, "Trainer", "512 bytes", "data")
        off += 512
    info.add(off, prg, "PRG ROM data", f"{_kb(prg)} at 0x{off:X}", "data", row=False)
    if chr_:
        info.add(off + prg, chr_, "CHR ROM data", f"{_kb(chr_)} at 0x{off + prg:X}", "data", row=False)
    expected = off + prg + chr_
    if len(d) < expected:
        info.warnings.append(f"The file is {len(d) - expected:,} bytes shorter than the header says.")
    elif len(d) > expected:
        info.rows.append(("Extra data", f"{len(d) - expected:,} bytes after CHR (misc ROM / title?)"))
    if prg >= 6 and len(d) >= off + prg:
        v = off + prg - 6
        nmi, reset, irq = _u16(d, v), _u16(d, v + 2), _u16(d, v + 4)
        info.add(v, 2, "NMI vector", f"${nmi:04X}", "vector")
        info.add(v + 2, 2, "RESET vector", f"${reset:04X}", "vector")
        info.add(v + 4, 2, "IRQ/BRK vector", f"${irq:04X}", "vector")
    prg_start, prg_end = off, off + prg
    bank = 0x4000 if prg <= 0x4000 else 0x8000 if mapper == 0 else 0x4000

    def cpu(o: int) -> int | None:
        if not prg_start <= o < prg_end:
            return None
        rel = o - prg_start
        if mapper == 0:
            return 0x8000 + rel if prg > 0x4000 else 0xC000 + rel
        last = prg_end - 0x4000                 # the last 16 KB bank is usually fixed at $C000
        return 0xC000 + (o - last) if o >= last else 0x8000 + (rel % bank)
    info.cpu_address = cpu


def _detect_fds(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "fds", "FDS", "6502"
    if d[:4] == b"FDS\x1a":
        info.add(0, 4, "Magic", "FDS<1A>", "magic", row=False)
        info.add(4, 1, "Disk sides", d[4], "size")
        body = 16
    else:
        body = 0
    sides = (len(d) - body) // 65500
    info.rows.append(("Sides in file", str(sides)))
    if len(d) > body + 0x38 and d[body + 1:body + 15] == b"*NINTENDO-HVC*":
        info.add(body + 0x10, 3, "Game code", _text(d[body + 0x10:body + 0x13]), "title")


# ============================================================================ Game Boy / GBA
GB_CART = {0x00: "ROM only", 0x01: "MBC1", 0x02: "MBC1+RAM", 0x03: "MBC1+RAM+BATTERY", 0x05: "MBC2",
           0x06: "MBC2+BATTERY", 0x08: "ROM+RAM", 0x09: "ROM+RAM+BATTERY", 0x0B: "MMM01", 0x0C: "MMM01+RAM",
           0x0D: "MMM01+RAM+BATTERY", 0x0F: "MBC3+TIMER+BATTERY", 0x10: "MBC3+TIMER+RAM+BATTERY", 0x11: "MBC3",
           0x12: "MBC3+RAM", 0x13: "MBC3+RAM+BATTERY", 0x19: "MBC5", 0x1A: "MBC5+RAM", 0x1B: "MBC5+RAM+BATTERY",
           0x1C: "MBC5+RUMBLE", 0x1D: "MBC5+RUMBLE+RAM", 0x1E: "MBC5+RUMBLE+RAM+BATTERY", 0x20: "MBC6",
           0x22: "MBC7+SENSOR+RUMBLE+RAM+BATTERY", 0xFC: "Pocket Camera", 0xFD: "Bandai TAMA5", 0xFE: "HuC3",
           0xFF: "HuC1+RAM+BATTERY"}
GB_RAM = {0: "none", 1: "2 KB (unofficial)", 2: "8 KB", 3: "32 KB (4 banks)", 4: "128 KB (16 banks)",
          5: "64 KB (8 banks)"}


def gb_header_checksum(d) -> int:
    x = 0
    for i in range(0x134, 0x14D):
        x = (x - d[i] - 1) & 0xFF
    return x


def gb_global_checksum(d) -> int:
    return (sum(d) - d[0x14E] - d[0x14F]) & 0xFFFF


def _detect_gb(d: bytes, info: RomInfo) -> None:
    cgb = d[0x143]
    info.system = "gbc" if cgb in (0x80, 0xC0) else "gb"
    info.format, info.cpu = "GB cartridge header", "sm83"
    info.add(0x100, 4, "Entry point", " ".join(f"{b:02X}" for b in d[0x100:0x104]), "vector", row=False)
    info.add(0x104, 48, "Logo area", "48 bytes (checked by the boot ROM; not checked here)", "data", row=False)
    tlen = 11 if cgb in (0x80, 0xC0) else 16
    info.title = _text(d[0x134:0x134 + tlen])
    info.add(0x134, tlen, "Title", info.title, "title")
    if cgb in (0x80, 0xC0):
        info.add(0x13F, 4, "Manufacturer code", _text(d[0x13F:0x143]), "info", row=False)
    info.add(0x143, 1, "CGB flag", {0x80: "Color enhanced", 0xC0: "Color only"}.get(cgb, "DMG (no colour)"), "flags")
    info.add(0x144, 2, "New licensee", _text(d[0x144:0x146]), "info", row=False)
    info.add(0x146, 1, "SGB flag", "Super Game Boy" if d[0x146] == 3 else "no", "flags")
    info.add(0x147, 1, "Cartridge type", f"{d[0x147]:02X} {GB_CART.get(d[0x147], 'unknown')}", "flags")
    rs = d[0x148]
    info.add(0x148, 1, "ROM size", _kb(32768 << rs) if rs <= 8 else f"code {rs:02X}", "size")
    info.add(0x149, 1, "RAM size", GB_RAM.get(d[0x149], f"code {d[0x149]:02X}"), "size")
    info.add(0x14A, 1, "Destination", "Japan" if d[0x14A] == 0 else "Overseas", "region")
    info.add(0x14B, 1, "Old licensee", f"{d[0x14B]:02X}", "info", row=False)
    info.add(0x14C, 1, "Version", d[0x14C], "info")
    hc, gc = gb_header_checksum(d), gb_global_checksum(d)
    info.add(0x14D, 1, "Header checksum", f"{d[0x14D]:02X} ({'OK' if hc == d[0x14D] else f'should be {hc:02X}'})",
             "checksum")
    stored = _b16(d, 0x14E)
    info.add(0x14E, 2, "Global checksum", f"{stored:04X} ({'OK' if gc == stored else f'should be {gc:04X}'})",
             "checksum")
    info.checksum_ok = hc == d[0x14D] and gc == stored
    info.fixable = True
    if hc != d[0x14D]:
        info.warnings.append("Header checksum mismatch: a real Game Boy refuses to start this cartridge.")
    if rs <= 8 and len(d) != 32768 << rs:
        info.warnings.append(f"The file is {_kb(len(d))}; the header says {_kb(32768 << rs)}.")

    def cpu(o: int) -> int | None:
        if o < 0x4000:
            return o
        return 0x4000 + (o % 0x4000)
    info.cpu_address = cpu


def gba_complement(d) -> int:
    return (-(sum(d[0xA0:0xBD]) + 0x19)) & 0xFF


def _detect_gba(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "gba", "GBA cartridge header", "arm7"
    info.add(0x00, 4, "Entry (ARM branch)", f"{_u32(d, 0):08X}", "vector")
    info.add(0x04, 156, "Logo area", "156 bytes (not checked here)", "data", row=False)
    info.title = _text(d[0xA0:0xAC])
    info.add(0xA0, 12, "Title", info.title, "title")
    info.add(0xAC, 4, "Game code", _text(d[0xAC:0xB0]), "info")
    info.add(0xB0, 2, "Maker code", _text(d[0xB0:0xB2]), "info")
    info.add(0xB2, 1, "Fixed value", f"{d[0xB2]:02X} (must be 96)", "magic", row=False)
    info.add(0xBC, 1, "Version", d[0xBC], "info")
    c = gba_complement(d)
    info.add(0xBD, 1, "Complement check", f"{d[0xBD]:02X} ({'OK' if c == d[0xBD] else f'should be {c:02X}'})",
             "checksum")
    info.checksum_ok = c == d[0xBD]
    info.fixable = True
    info.cpu_address = lambda o: 0x08000000 + o


# ============================================================================ SNES
SNES_MAP = {0x20: "LoROM", 0x21: "HiROM", 0x22: "LoROM + S-DD1", 0x23: "LoROM + SA-1", 0x25: "ExHiROM",
            0x30: "LoROM (FastROM)", 0x31: "HiROM (FastROM)", 0x32: "ExLoROM", 0x35: "ExHiROM (FastROM)",
            0x3A: "HiROM + SPC7110"}
SNES_COUNTRY = {0: "Japan", 1: "USA / Canada", 2: "Europe", 3: "Sweden", 4: "Finland", 5: "Denmark",
                6: "France", 7: "Netherlands", 8: "Spain", 9: "Germany", 10: "Italy", 11: "China", 13: "Korea",
                15: "Canada", 16: "Brazil", 17: "Australia"}


def snes_copier_header(d) -> int:
    return 512 if len(d) % 1024 == 512 else 0


def _snes_score(d, base: int, kind: str) -> int:
    h = snes_copier_header(d)
    o = h + base
    if o + 0x40 > len(d):
        return -1
    mode = d[o + 0x15]
    comp, chk = _u16(d, o + 0x1C), _u16(d, o + 0x1E)
    s = 0
    if comp ^ chk == 0xFFFF:
        s += 4
    if kind == "lo" and mode & 0xEF in (0x20, 0x22, 0x23, 0x32):
        s += 2
    elif kind == "hi" and mode & 0xEF in (0x21, 0x2A):
        s += 2
    elif kind == "exhi" and mode & 0xEF == 0x25:
        s += 2
    if _printable(d[o:o + 21], 0.9):
        s += 2
    if _u16(d, o + 0x3C) >= 0x8000:
        s += 1
    if 7 <= d[o + 0x17] <= 13:
        s += 1
    if d[o + 0x1A] in (0x33, 0x01) or d[o + 0x19] <= 17:
        s += 1
    return s


def snes_header_offset(d) -> tuple[int, str] | None:
    """(file offset of the internal header, "LoROM" | "HiROM" | "ExHiROM") or None."""
    cands = [(0x7FC0, "lo"), (0xFFC0, "hi"), (0x40FFC0, "exhi")]
    best = None
    for base, kind in cands:
        s = _snes_score(d, base, kind)
        if s >= 0 and (best is None or s > best[0]):
            best = (s, base, kind)
    if best is None or best[0] < 5:
        return None
    return snes_copier_header(d) + best[1], {"lo": "LoROM", "hi": "HiROM", "exhi": "ExHiROM"}[best[2]]


def snes_checksum(d, header_off: int) -> int:
    """The SNES checksum of the ROM (copier header excluded), as if the header held a valid pair."""
    h = snes_copier_header(d)
    rom = bytearray(d[h:])
    o = header_off - h
    rom[o + 0x1C:o + 0x20] = b"\xff\xff\x00\x00"
    n = len(rom)
    if n == 0:
        return 0
    p = 1
    while p * 2 <= n:
        p *= 2
    total = sum(rom[:p])
    if n > p:                                 # the remainder is mirrored up to the next power of two
        rem = rom[p:]
        reps, extra = divmod(p, len(rem))
        total += sum(rem) * reps + sum(rem[:extra])
    return total & 0xFFFF


def _detect_snes(d: bytes, info: RomInfo, where: tuple[int, str]) -> None:
    o, layout = where
    h = snes_copier_header(d)
    info.system, info.format, info.cpu = "snes", layout, "65816"
    if h:
        info.add(0, 512, "Copier header", "512 bytes (SMC / SWC)", "data")
    info.title = _text(d[o:o + 21], "shift_jis")
    info.add(o, 21, "Title", info.title, "title")
    mode = d[o + 0x15]
    info.add(o + 0x15, 1, "Map mode", f"{mode:02X} {SNES_MAP.get(mode, '')}", "flags")
    info.add(o + 0x16, 1, "Cartridge type", f"{d[o + 0x16]:02X}", "flags")
    info.add(o + 0x17, 1, "ROM size", _kb(1024 << d[o + 0x17]) if d[o + 0x17] < 16 else d[o + 0x17], "size")
    info.add(o + 0x18, 1, "SRAM size", _kb(1024 << d[o + 0x18]) if 0 < d[o + 0x18] < 16 else "none", "size")
    info.add(o + 0x19, 1, "Country", SNES_COUNTRY.get(d[o + 0x19], f"{d[o + 0x19]:02X}"), "region")
    info.add(o + 0x1A, 1, "Developer", f"{d[o + 0x1A]:02X}" + (" (extended header)" if d[o + 0x1A] == 0x33 else ""),
             "info", row=False)
    info.add(o + 0x1B, 1, "Version", f"1.{d[o + 0x1B]}", "info")
    comp, chk = _u16(d, o + 0x1C), _u16(d, o + 0x1E)
    calc = snes_checksum(d, o)
    ok = chk == calc and comp == calc ^ 0xFFFF
    info.add(o + 0x1C, 2, "Checksum complement", f"{comp:04X}", "checksum")
    info.add(o + 0x1E, 2, "Checksum", f"{chk:04X} ({'OK' if ok else f'should be {calc:04X}'})", "checksum")
    info.add(o + 0x3C, 2, "RESET vector (emulation)", f"${_u16(d, o + 0x3C):04X}", "vector")
    info.add(o + 0x2A, 2, "NMI vector (native)", f"${_u16(d, o + 0x2A):04X}", "vector", row=False)
    info.checksum_ok = ok
    info.fixable = True
    if h:
        info.warnings.append("The file has a 512-byte copier header (most patches expect a headerless ROM; "
                             "check the patch's notes).")

    def cpu(off: int) -> int | None:
        r = off - h
        if r < 0:
            return None
        if layout == "LoROM":
            return ((r // 0x8000) << 16) | 0x8000 | (r % 0x8000)
        return 0xC00000 + r if r < 0x400000 else 0x400000 + (r - 0x400000)
    info.cpu_address = cpu


# ============================================================================ Sega
def genesis_checksum(d) -> int:
    body = bytes(d[0x200:])
    if len(body) % 2:
        body += b"\x00"
    words = struct.unpack(f">{len(body) // 2}H", body)
    return sum(words) & 0xFFFF


def _detect_genesis(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "genesis", "Mega Drive header", "68000"
    info.add(0x000, 4, "Initial SSP", f"{_b32(d, 0):08X}", "vector", row=False)
    info.add(0x004, 4, "Initial PC", f"{_b32(d, 4):08X}", "vector")
    info.add(0x100, 16, "System", _text(d[0x100:0x110]), "magic")
    info.add(0x110, 16, "Copyright", _text(d[0x110:0x120]), "info")
    dom = _text(d[0x120:0x150], "shift_jis")
    ovs = _text(d[0x150:0x180])
    info.title = ovs or dom
    info.add(0x120, 48, "Domestic title", dom, "title")
    info.add(0x150, 48, "Overseas title", ovs, "title")
    info.add(0x180, 14, "Serial / version", _text(d[0x180:0x18E]), "info")
    stored, calc = _b16(d, 0x18E), genesis_checksum(d)
    info.add(0x18E, 2, "Checksum", f"{stored:04X} ({'OK' if stored == calc else f'should be {calc:04X}'})",
             "checksum")
    info.add(0x190, 16, "I/O support", _text(d[0x190:0x1A0]), "info")
    info.add(0x1A0, 8, "ROM range", f"{_b32(d, 0x1A0):08X}-{_b32(d, 0x1A4):08X}", "size")
    info.add(0x1A8, 8, "RAM range", f"{_b32(d, 0x1A8):08X}-{_b32(d, 0x1AC):08X}", "size", row=False)
    info.add(0x1F0, 3, "Region", _text(d[0x1F0:0x1F3]), "region")
    info.checksum_ok = stored == calc
    info.fixable = True
    info.cpu_address = lambda o: o


def _detect_sms(d: bytes, info: RomInfo, o: int) -> None:
    info.system, info.format, info.cpu = "sms", "SEGA header", "z80"
    info.add(o, 8, "Signature", "TMR SEGA", "magic")
    info.add(o + 0x0A, 2, "Checksum", f"{_u16(d, o + 0x0A):04X}", "checksum")
    code = d[o + 0x0C] | (d[o + 0x0D] << 8) | ((d[o + 0x0E] >> 4) << 16)
    info.add(o + 0x0C, 3, "Product code", f"{code:X}", "info")
    rg = d[o + 0x0F] >> 4
    info.add(o + 0x0F, 1, "Region / size", {3: "SMS Japan", 4: "SMS Export", 5: "Game Gear Japan",
                                            6: "Game Gear Export", 7: "Game Gear International"}.get(rg, str(rg)),
             "region")
    info.cpu_address = lambda off: off if off < 0xC000 else None


# ============================================================================ Atari
A26_SIGS = {
    "E0": [b"\x8d\xe0\x1f", b"\x8d\xe0\x5f", b"\x8d\xe9\xff", b"\x0c\xe0\x1f", b"\xad\xe0\x1f", b"\xad\xe9\xff",
           b"\xad\xed\xff", b"\xad\xf3\xbf"],
    "E7": [b"\xad\xe2\xff", b"\xad\xe5\xff", b"\xad\xe5\x1f", b"\xad\xe7\x1f", b"\x0c\xe7\x1f", b"\x8d\xe7\xff",
           b"\x8d\xe7\x1f"],
    "FE": [b"\x20\x00\xd0\xc6\xc5", b"\x20\xc3\xf8\xa5\x82", b"\xd0\xfb\x20\x73\xfe", b"\x20\x00\xf0\x84\xd6"],
    "3F": [b"\x85\x3f"],
    "UA": [b"\x8d\x40\x02", b"\xad\x40\x02", b"\xbd\x1f\x02", b"\x2c\xc0\x02", b"\x8d\xc0\x02", b"\xad\xc0\x02"],
    "CV": [b"\x9d\xff\xf3", b"\x99\x00\xf4"],
}


def _sig_count(d: bytes, sigs: list[bytes]) -> int:
    return sum(d.count(s) for s in sigs)


def _superchip(d: bytes) -> bool:
    """SuperChip (128 bytes of extra RAM): the RAM's write and read ports leave the first 256 bytes of every
    4 KB bank unused, so they hold one repeated value in the ROM image."""
    if len(d) < 8192:
        return False
    for b in range(0, len(d), 4096):
        chunk = d[b:b + 256]
        if chunk.count(chunk[0:1]) != len(chunk):
            return False
    return True


def a26_bankswitch(d: bytes) -> tuple[str, str]:
    """(scheme, reason) - a guess from the size and typical hotspot accesses (like the guessing emulators do)."""
    n = len(d)
    sc = "SC" if _superchip(d) else ""
    if n <= 2048:
        return "2K", "2 KB image, mirrored"
    if n == 4096:
        return "4K", "4 KB, no bankswitching"
    if n in (10240, 10495, 10496):
        return "DPC", "Pitfall II style DPC chip (10 KB)"
    if n == 12288:
        return "FA", "12 KB: CBS RAM Plus"
    if n == 8192:
        for scheme in ("E0", "3F", "FE", "UA"):
            if _sig_count(d, A26_SIGS[scheme]) >= (2 if scheme == "3F" else 1):
                return scheme, f"8 KB with {scheme} hotspot accesses"
        return "F8" + sc, "8 KB: two 4 KB banks (hotspots $1FF8/$1FF9)" + (", SuperChip RAM" if sc else "")
    if n == 16384:
        if _sig_count(d, A26_SIGS["E7"]):
            return "E7", "16 KB with E7 (M-Network) hotspots"
        if _sig_count(d, A26_SIGS["3F"]) >= 2:
            return "3F", "Tigervision $3F writes"
        return "F6" + sc, "16 KB: four 4 KB banks ($1FF6-$1FF9)" + (", SuperChip RAM" if sc else "")
    if n == 32768:
        if _sig_count(d, A26_SIGS["3F"]) >= 2:
            return "3F", "Tigervision $3F writes"
        return "F4" + sc, "32 KB: eight 4 KB banks ($1FF4-$1FFB)" + (", SuperChip RAM" if sc else "")
    if n == 65536:
        if _sig_count(d, A26_SIGS["3F"]) >= 2:
            return "3F", "Tigervision $3F writes"
        return "EF" + sc, "64 KB: sixteen 4 KB banks ($1FE0-$1FEF)"
    if n % 2048 == 0 and _sig_count(d, A26_SIGS["3F"]) >= 2:
        return "3F", "Tigervision $3F writes"
    return "unknown", f"{_kb(n)} - no common scheme"


def _detect_a26(d: bytes, info: RomInfo) -> None:
    info.system, info.cpu = "atari2600", "6502"
    scheme, why = a26_bankswitch(d)
    info.format = f"Atari 2600 cart ({scheme})"
    info.rows.append(("Size", _kb(len(d))))
    info.rows.append(("Bankswitching (guess)", f"{scheme} - {why}"))
    banks = max(1, len(d) // 4096)
    info.rows.append(("4 KB banks", str(banks) if len(d) >= 4096 else "-"))
    end = len(d)
    if end >= 6:
        info.add(end - 4, 2, "RESET vector (last bank)", f"${_u16(d, end - 4):04X}", "vector")
        info.add(end - 2, 2, "IRQ/BRK vector (last bank)", f"${_u16(d, end - 2):04X}", "vector", row=False)
    size = 2048 if len(d) <= 2048 else 4096
    info.cpu_address = lambda o: 0xF000 + (o % size) if size == 4096 else 0xF800 + (o % 2048)
    if scheme.endswith("SC"):
        info.add(0, 256, "SuperChip RAM ports (bank 0)", "128 write + 128 read bytes", "data", row=False)


A78_CART_BITS = ["POKEY at $4000", "SuperGame bankswitching", "SuperGame RAM at $4000", "ROM at $4000",
                 "bank 6 at $4000", "banked RAM", "POKEY at $450", "mirror RAM at $4000"]


def _detect_a78(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "atari7800", "A78 header", "6502"
    info.add(0, 1, "Header version", d[0], "info")
    info.add(1, 16, "Magic", _text(d[1:17]), "magic", row=False)
    info.title = _text(d[17:49])
    info.add(17, 32, "Title", info.title, "title")
    size = _b32(d, 49)
    info.add(49, 4, "ROM size (without header)", _kb(size), "size")
    ct = _b16(d, 53)
    bits = [A78_CART_BITS[i] for i in range(8) if ct & (1 << i)]
    info.add(53, 2, "Cartridge type", f"{ct:04X} " + (", ".join(bits) or "plain ROM"), "flags")
    ctrl = {0: "none", 1: "joystick", 2: "light gun", 3: "paddle", 4: "trakball", 5: "2600 joystick",
            6: "2600 driving", 7: "2600 keypad", 8: "ST mouse", 9: "Amiga mouse"}
    info.add(55, 1, "Controller 1", ctrl.get(d[55], d[55]), "info")
    info.add(56, 1, "Controller 2", ctrl.get(d[56], d[56]), "info")
    info.add(57, 1, "TV", "PAL" if d[57] & 1 else "NTSC", "region")
    info.add(58, 1, "Save device", {0: "none", 1: "High Score Cart", 2: "SaveKey / AtariVox"}.get(d[58], d[58]),
             "info")
    info.add(100, 28, "Signature", _text(d[100:128]), "magic", row=False)
    if len(d) - 128 != size:
        info.warnings.append(f"The header says {_kb(size)} but the file holds {_kb(len(d) - 128)} after it.")
    if len(d) >= 128 + 6:
        info.add(len(d) - 4, 2, "RESET vector", f"${_u16(d, len(d) - 4):04X}", "vector")
    rom = len(d) - 128
    info.cpu_address = lambda o: 0x10000 - rom + (o - 128) if o >= 128 and rom <= 0xC000 else None


A8_CART_TYPES = {1: "Standard 8 KB", 2: "Standard 16 KB", 3: "OSS two-chip 16 KB (034M)", 4: "Atari 5200 32 KB",
                 5: "DB 32 KB", 6: "Atari 5200 16 KB two-chip", 7: "Atari 5200 40 KB (Bounty Bob)",
                 8: "Williams 64 KB", 9: "Express 64 KB", 10: "Diamond 64 KB", 11: "SpartaDOS X 64 KB",
                 12: "XEGS 32 KB", 13: "XEGS 64 KB", 14: "XEGS 128 KB", 15: "OSS one-chip 16 KB",
                 16: "Atari 5200 16 KB one-chip", 17: "Atrax 128 KB", 18: "Bounty Bob 40 KB", 19: "Atari 5200 8 KB",
                 20: "Atari 5200 4 KB", 21: "Right slot 8 KB", 22: "Williams 32 KB", 23: "XEGS 256 KB",
                 24: "XEGS 512 KB", 25: "XEGS 1 MB", 26: "MegaCart 16 KB", 27: "MegaCart 32 KB",
                 28: "MegaCart 64 KB", 29: "MegaCart 128 KB", 30: "MegaCart 256 KB", 31: "MegaCart 512 KB",
                 32: "MegaCart 1 MB", 33: "Switchable XEGS 32 KB", 40: "Blizzard 16 KB", 41: "Atarimax 128 KB",
                 42: "Atarimax 1 MB"}


def car_checksum(d) -> int:
    return sum(d[16:]) & 0xFFFFFFFF


def _detect_car(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "atari8bit", "CAR cartridge", "6502"
    t = _b32(d, 4)
    info.add(0, 4, "Magic", "CART", "magic", row=False)
    info.add(4, 4, "Cartridge type", f"{t} - {A8_CART_TYPES.get(t, 'unknown')}", "flags")
    stored, calc = _b32(d, 8), car_checksum(d)
    info.add(8, 4, "Checksum", f"{stored:08X} ({'OK' if stored == calc else f'should be {calc:08X}'})", "checksum")
    info.rows.append(("ROM data", _kb(len(d) - 16)))
    info.checksum_ok = stored == calc
    info.fixable = True


def atr_sector_offset(sec: int, sector_size: int) -> int:
    if sec <= 3 or sector_size == 128:
        return 16 + (sec - 1) * 128
    return 16 + 3 * 128 + (sec - 4) * sector_size


def _detect_atr(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "atari8bit", "ATR disk image", "6502"
    paras = _u16(d, 2) | (d[6] << 16)
    ssize = _u16(d, 4)
    info.add(0, 2, "Magic", "96 02 (NICKATARI)", "magic", row=False)
    info.add(2, 2, "Image size", _kb(paras * 16), "size")
    info.add(4, 2, "Sector size", f"{ssize} bytes", "size")
    sectors = 3 + max(0, (paras * 16 - 384) // max(ssize, 1)) if ssize != 128 else paras * 16 // 128
    density = {128: "single" if sectors <= 720 else "enhanced (medium)", 256: "double"}.get(ssize, "?")
    info.rows.append(("Sectors", f"{sectors} ({density} density)"))
    # Atari DOS 2.x directory: sectors 361-368, 8 entries x 16 bytes
    files = []
    for sec in range(361, 369):
        off = atr_sector_offset(sec, ssize)
        if off + 128 > len(d):
            break
        for e in range(8):
            ent = d[off + e * 16:off + e * 16 + 16]
            flag = ent[0]
            if flag == 0:
                continue
            if flag & 0x80:
                continue                       # deleted
            name = ent[5:13].decode("latin-1").rstrip()
            ext = ent[13:16].decode("latin-1").rstrip()
            files.append((f"{name}.{ext}" if ext else name, str(_u16(ent, 1)), str(_u16(ent, 3)),
                          "locked" if flag & 0x20 else ""))
    if files and all(_printable(f[0].encode("latin-1"), 0.8) for f in files):
        info.listing_header = ("File", "Sectors", "First sector", "Flags")
        info.listing = files
        info.rows.append(("DOS 2 directory", f"{len(files)} files"))
    else:
        info.rows.append(("Directory", "not an Atari DOS 2 disk (boot disk or other DOS)"))
    info.rows.append(("Boot", f"{d[16 + 1]} sectors to $" + f"{_u16(d, 16 + 2):04X}" if len(d) > 20 else "-"))


def xex_segments(d: bytes) -> list[tuple[int, int, int]] | None:
    """[(file offset of data, start address, end address)] or None when the chain does not parse."""
    pos, out = 0, []
    while pos < len(d):
        if pos + 2 <= len(d) and d[pos] == 0xFF and d[pos + 1] == 0xFF:
            pos += 2
        if pos + 4 > len(d):
            return None
        start, end = _u16(d, pos), _u16(d, pos + 2)
        if end < start:
            return None
        pos += 4
        if pos + end - start + 1 > len(d):
            return None
        out.append((pos, start, end))
        pos += end - start + 1
    return out if out else None


def _detect_xex(d: bytes, info: RomInfo, segs) -> None:
    info.system, info.format, info.cpu = "atari8bit", "XEX executable", "6502"
    info.add(0, 2, "Magic", "FF FF", "magic", row=False)
    rows = []
    run = init = None
    for off, start, end in segs:
        what = ""
        if start <= 0x2E0 <= end and 0x2E1 <= end:
            run = _u16(d, off + 0x2E0 - start)
            what = f"RUNAD = ${run:04X}"
        if start <= 0x2E2 <= end and 0x2E3 <= end:
            init = _u16(d, off + 0x2E2 - start)
            what = (what + ", " if what else "") + f"INITAD = ${init:04X}"
        rows.append((f"0x{off:X}", f"${start:04X}", f"${end:04X}", f"{end - start + 1}", what))
        info.fields.append(Field(off - 4, 4, f"Segment ${start:04X}-${end:04X}", f"{end - start + 1} bytes", "size"))
    info.listing_header = ("File offset", "Start", "End", "Bytes", "Note")
    info.listing = rows
    info.rows.append(("Segments", str(len(segs))))
    if run is not None:
        info.rows.append(("Run address", f"${run:04X}"))
    seg_map = [(off, start, end) for off, start, end in segs]

    def cpu(o: int) -> int | None:
        for off, start, end in seg_map:
            if off <= o <= off + end - start:
                return start + o - off
        return None
    info.cpu_address = cpu


# ============================================================================ Commodore
C64_TOKENS = ("END FOR NEXT DATA INPUT# INPUT DIM READ LET GOTO RUN IF RESTORE GOSUB RETURN REM STOP ON WAIT "
              "LOAD SAVE VERIFY DEF POKE PRINT# PRINT CONT LIST CLR CMD SYS OPEN CLOSE GET NEW TAB( TO FN SPC( "
              "THEN NOT STEP + - * / ^ AND OR > = < SGN INT ABS USR FRE POS SQR RND LOG EXP COS SIN TAN ATN PEEK "
              "LEN STR$ VAL ASC CHR$ LEFT$ RIGHT$ MID$ GO").split()


def petscii(raw: bytes) -> str:
    out = []
    for c in raw:
        if c == 0xA0:
            continue
        if 0x41 <= c <= 0x5A or 0x20 <= c <= 0x40 or c in (0x5B, 0x5D):
            out.append(chr(c))
        elif 0xC1 <= c <= 0xDA:
            out.append(chr(c - 0x80))
        elif 0x61 <= c <= 0x7A:
            out.append(chr(c - 0x20))
        else:
            out.append("?")
    return "".join(out)


def c64_basic_listing(d: bytes, load: int, limit: int = 40) -> list[str]:
    """Detokenised BASIC V2 lines of a PRG loaded at *load*."""
    lines = []
    pos = 2
    for _ in range(limit):
        if pos + 4 > len(d):
            break
        nxt = _u16(d, pos)
        if nxt == 0:
            break
        num = _u16(d, pos + 2)
        p = pos + 4
        txt = []
        quote = False
        while p < len(d) and d[p] != 0:
            c = d[p]
            if c == 0x22:
                quote = not quote
            if c >= 0x80 and not quote and c - 0x80 < len(C64_TOKENS):
                txt.append(C64_TOKENS[c - 0x80])
            elif c == 0xFF and not quote:
                txt.append("π")
            else:
                txt.append(petscii(bytes([c])))
            p += 1
        lines.append(f"{num} {''.join(txt)}")
        new = nxt - load + 2
        if new <= pos or new > len(d):
            break
        pos = new
    return lines


def _detect_prg(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "c64", "PRG program", "6502"
    load = _u16(d, 0)
    info.add(0, 2, "Load address", f"${load:04X}" + (" (BASIC start)" if load == 0x0801 else ""), "vector")
    info.rows.append(("Program size", f"{len(d) - 2:,} bytes (to ${load + len(d) - 3:04X})"))
    if load == 0x0801:
        basic = c64_basic_listing(d, load)
        if basic:
            info.listing_header = ("BASIC",)
            info.listing = [(line,) for line in basic]
            sys_lines = [line for line in basic if " SYS" in f" {line}" or "SYS" in line]
            if sys_lines:
                info.rows.append(("Starts with", sys_lines[0][:60]))
    info.cpu_address = lambda o: load + o - 2 if o >= 2 else None


D64_SIZES = {174848: (35, False), 175531: (35, True), 196608: (40, False), 197376: (40, True)}


def d64_sectors(track: int) -> int:
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def d64_offset(track: int, sector: int) -> int:
    return (sum(d64_sectors(t) for t in range(1, track)) + sector) * 256


def _detect_d64(d: bytes, info: RomInfo) -> None:
    tracks, errors = D64_SIZES.get(len(d), (35, False))
    info.system, info.format, info.cpu = "c64", "D64 disk image", "6502"
    bam = d64_offset(18, 0)
    info.add(bam + 0x90, 16, "Disk name", petscii(d[bam + 0x90:bam + 0xA0]), "title")
    info.add(bam + 0xA2, 2, "Disk ID", petscii(d[bam + 0xA2:bam + 0xA4]), "info")
    info.add(bam + 0xA5, 2, "DOS type", petscii(d[bam + 0xA5:bam + 0xA7]), "info", row=False)
    info.rows.append(("Tracks", f"{tracks}" + (" + error bytes" if errors else "")))
    free = sum(d[bam + 4 + 4 * (t - 1)] for t in range(1, 36) if t != 18)
    info.rows.append(("Blocks free", str(free)))
    info.title = petscii(d[bam + 0x90:bam + 0xA0])
    types = ("DEL", "SEQ", "PRG", "USR", "REL")
    files = []
    t, s = 18, 1
    seen = set()
    while t and (t, s) not in seen and len(seen) < 40 and 1 <= t <= tracks:
        seen.add((t, s))
        off = d64_offset(t, s)
        if off + 256 > len(d):
            break
        for e in range(8):
            ent = d[off + e * 32:off + e * 32 + 32]
            ft = ent[2]
            if ft == 0:
                continue
            name = petscii(ent[5:21])
            kind = types[ft & 7] if (ft & 7) < 5 else "???"
            flags = ("" if ft & 0x80 else "*") + ("<" if ft & 0x40 else "")
            files.append((str(_u16(ent, 30)), f'"{name}"', kind + flags, f"{ent[3]}/{ent[4]}"))
        t, s = d[off], d[off + 1]
    info.listing_header = ("Blocks", "Name", "Type", "Track/Sector")
    info.listing = files
    info.rows.append(("Files", str(len(files))))


def _detect_t64(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "c64", "T64 tape image", "6502"
    info.add(0, 32, "Signature", _text(d[0:32]), "magic", row=False)
    info.add(0x20, 2, "Version", f"{_u16(d, 0x20):04X}", "info")
    maxe, used = _u16(d, 0x22), _u16(d, 0x24)
    info.add(0x22, 2, "Directory entries", maxe, "size")
    info.add(0x24, 2, "Used entries", used, "size")
    info.title = petscii(d[0x28:0x40])
    info.add(0x28, 24, "Tape name", info.title, "title")
    files = []
    for i in range(min(maxe, 1000)):
        e = 0x40 + i * 32
        if e + 32 > len(d):
            break
        if d[e] == 0:
            continue
        start, end, off = _u16(d, e + 2), _u16(d, e + 4), _u32(d, e + 8)
        files.append((petscii(d[e + 16:e + 32]).rstrip(), f"${start:04X}", f"${end:04X}", f"0x{off:X}"))
        info.fields.append(Field(e, 32, f"Entry {i}", files[-1][0], "info"))
    info.listing_header = ("Name", "Start", "End", "File offset")
    info.listing = files


# ============================================================================ ZX Spectrum
ZX_TYPES = {0: "Program", 1: "Number array", 2: "Character array", 3: "Bytes (CODE)"}


def tap_blocks(d: bytes) -> list[tuple[int, int, int, bool]] | None:
    """[(offset of the length word, length, flag, checksum ok)] or None when the chain does not cover the file."""
    pos, out = 0, []
    while pos < len(d):
        if pos + 2 > len(d):
            return None
        n = _u16(d, pos)
        if n < 2 or pos + 2 + n > len(d):
            return None
        blk = d[pos + 2:pos + 2 + n]
        x = 0
        for b in blk[:-1]:
            x ^= b
        out.append((pos, n, blk[0], x == blk[-1]))
        pos += 2 + n
    return out


def _zx_header_text(blk: bytes) -> str:
    """Description of a 17-byte ZX header (blk = flag + 17 bytes + checksum)."""
    t = blk[1]
    name = blk[2:12].decode("latin-1", errors="replace").rstrip()
    length, p1 = _u16(blk, 12), _u16(blk, 14)
    extra = f" LINE {p1}" if t == 0 and p1 < 32768 else f" at {p1}" if t == 3 else ""
    return f'{ZX_TYPES.get(t, t)}: "{name}" {length} bytes{extra}'


def _detect_tap(d: bytes, info: RomInfo, blocks) -> None:
    info.system, info.format, info.cpu = "zxspectrum", "TAP tape image", "z80"
    rows = []
    for pos, n, flag, ok in blocks:
        blk = d[pos + 2:pos + 2 + n]
        desc = _zx_header_text(blk) if flag == 0 and n == 19 else f"data, {n - 2} bytes"
        rows.append((f"0x{pos:X}", "header" if flag == 0 else "data" if flag == 0xFF else f"flag {flag:02X}",
                     desc, "OK" if ok else "BAD"))
        info.fields.append(Field(pos, 3, "Block length + flag", desc, "size"))
        info.fields.append(Field(pos + 1 + n, 1, "Block checksum", "OK" if ok else "BAD", "checksum"))
    info.listing_header = ("Offset", "Block", "Content", "Checksum")
    info.listing = rows
    info.rows.append(("Blocks", str(len(blocks))))
    bad = sum(1 for b in blocks if not b[3])
    info.checksum_ok = bad == 0
    if bad:
        info.warnings.append(f"{bad} block(s) with a wrong XOR checksum.")


TZX_NAMES = {0x10: "Standard speed data", 0x11: "Turbo speed data", 0x12: "Pure tone", 0x13: "Pulse sequence",
             0x14: "Pure data", 0x15: "Direct recording", 0x18: "CSW recording", 0x19: "Generalized data",
             0x20: "Pause / stop", 0x21: "Group start", 0x22: "Group end", 0x23: "Jump", 0x24: "Loop start",
             0x25: "Loop end", 0x26: "Call sequence", 0x27: "Return", 0x28: "Select block", 0x2A: "Stop if 48K",
             0x2B: "Signal level", 0x30: "Text description", 0x31: "Message", 0x32: "Archive info",
             0x33: "Hardware type", 0x35: "Custom info", 0x5A: "Glue"}


def _tzx_len(d: bytes, p: int, bid: int) -> int | None:
    """Length of the block body (after the ID byte) at *p*."""
    def u24(o):
        return d[o] | (d[o + 1] << 8) | (d[o + 2] << 16)
    try:
        if bid == 0x10:
            return 4 + _u16(d, p + 2)
        if bid == 0x11:
            return 0x12 + u24(p + 0x0F)
        if bid == 0x12:
            return 4
        if bid == 0x13:
            return 1 + 2 * d[p]
        if bid == 0x14:
            return 10 + u24(p + 7)
        if bid == 0x15:
            return 8 + u24(p + 5)
        if bid in (0x18, 0x19):
            return 4 + _u32(d, p)
        if bid in (0x20, 0x23, 0x24):
            return 2
        if bid in (0x22, 0x25, 0x27):
            return 0
        if bid == 0x21 or bid == 0x30:
            return 1 + d[p]
        if bid == 0x26:
            return 2 + 2 * _u16(d, p)
        if bid == 0x28 or bid == 0x32:
            return 2 + _u16(d, p)
        if bid == 0x2A:
            return 4
        if bid == 0x2B:
            return 5
        if bid == 0x31:
            return 2 + d[p + 1]
        if bid == 0x33:
            return 1 + 3 * d[p]
        if bid == 0x35:
            return 0x14 + _u32(d, p + 0x10)
        if bid == 0x5A:
            return 9
    except (IndexError, struct.error):
        return None
    return None


def _detect_tzx(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "zxspectrum", "TZX tape image", "z80"
    info.add(0, 8, "Signature", "ZXTape!", "magic", row=False)
    info.add(8, 2, "Version", f"{d[8]}.{d[9]:02d}", "info")
    p, rows = 10, []
    while p < len(d) and len(rows) < 2000:
        bid = d[p]
        n = _tzx_len(d, p + 1, bid)
        if n is None:
            rows.append((f"0x{p:X}", f"{bid:02X}", "unknown block - listing stops here", ""))
            break
        desc = TZX_NAMES.get(bid, "?")
        if bid == 0x10 and n >= 4 + 19 and d[p + 5] == 0 and _u16(d, p + 3) == 19:
            desc += " - " + _zx_header_text(d[p + 5:p + 5 + 19])
        elif bid == 0x30:
            desc += ": " + d[p + 2:p + 2 + d[p + 1]].decode("latin-1", errors="replace")
        rows.append((f"0x{p:X}", f"{bid:02X}", desc, f"{n}"))
        info.fields.append(Field(p, 1, "Block ID", desc, "magic"))
        p += 1 + n
    info.listing_header = ("Offset", "ID", "Block", "Length")
    info.listing = rows
    info.rows.append(("Blocks", str(len(rows))))


def _detect_sna(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "zxspectrum", "SNA snapshot (48K)" if len(d) == 49179 else \
        "SNA snapshot (128K)", "z80"
    regs = [(0, 1, "I"), (1, 2, "HL'"), (3, 2, "DE'"), (5, 2, "BC'"), (7, 2, "AF'"), (9, 2, "HL"), (11, 2, "DE"),
            (13, 2, "BC"), (15, 2, "IY"), (17, 2, "IX"), (20, 1, "R"), (21, 2, "AF"), (23, 2, "SP")]
    for off, n, name in regs:
        v = d[off] if n == 1 else _u16(d, off)
        info.add(off, n, name, f"{v:0{n * 2}X}", "vector" if name == "SP" else "info", row=name in ("SP", "AF", "HL"))
    info.add(19, 1, "Interrupts", "enabled" if d[19] & 4 else "disabled", "flags")
    info.add(25, 1, "Interrupt mode", f"IM {d[25]}", "flags")
    info.add(26, 1, "Border colour", d[26] & 7, "info")
    sp = _u16(d, 23)
    if len(d) == 49179 and 0x4000 <= sp < 0xFFFF:
        o = 27 + sp - 0x4000
        info.rows.append(("PC (on the stack)", f"{_u16(d, o):04X}"))
    elif len(d) > 49181:
        info.add(49179, 2, "PC", f"{_u16(d, 49179):04X}", "vector")
    info.add(27, 49152, "RAM $4000-$FFFF", "48 KB", "data", row=False)
    info.cpu_address = lambda o: 0x4000 + o - 27 if 27 <= o < 27 + 49152 else None


# ============================================================================ DOS
def _detect_mz(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "dos", "MZ executable", "x86"
    cblp, cp, crlc, hdr = _u16(d, 2), _u16(d, 4), _u16(d, 6), _u16(d, 8)
    image = (cp - 1) * 512 + cblp if cblp else cp * 512
    info.add(0, 2, "Signature", "MZ", "magic", row=False)
    info.add(2, 4, "Image size", f"{image:,} bytes ({cp} pages, {cblp} in the last)", "size")
    info.add(6, 2, "Relocations", crlc, "size")
    info.add(8, 2, "Header size", f"{hdr * 16} bytes", "size")
    info.add(10, 4, "Min / max extra memory", f"{_u16(d, 10) * 16:,} / {_u16(d, 12) * 16:,} bytes", "size", row=False)
    info.add(14, 4, "Initial SS:SP", f"{_u16(d, 14):04X}:{_u16(d, 16):04X}", "vector")
    info.add(18, 2, "Checksum", f"{_u16(d, 18):04X}", "checksum", row=False)
    info.add(20, 4, "Initial CS:IP", f"{_u16(d, 22):04X}:{_u16(d, 20):04X}", "vector")
    rel = _u16(d, 24)
    info.add(24, 2, "Relocation table", f"0x{rel:X}", "info", row=False)
    if crlc and rel + crlc * 4 <= len(d):
        info.add(rel, crlc * 4, "Relocation entries", f"{crlc} x seg:off", "data", row=False)
    kind = "DOS program"
    if len(d) >= 0x40 and (rel >= 0x40 or rel == 0):
        lfa = _u32(d, 0x3C)
        if 0x40 <= lfa < len(d) - 4:
            sig = d[lfa:lfa + 2]
            names = {b"PE": "Windows PE (DOS stub only runs in DOS)", b"NE": "16-bit Windows / OS2 NE",
                     b"LE": "LE (VxD / DOS extender)", b"LX": "OS/2 LX"}
            if sig in names:
                kind = names[sig]
                info.add(0x3C, 4, "New header offset", f"0x{lfa:X} ({sig.decode()})", "info")
    info.rows.append(("Kind", kind))
    start = hdr * 16
    info.add(start, max(0, min(len(d), image) - start), "Load image", f"from 0x{start:X}", "data", row=False)
    if image > len(d):
        info.warnings.append("The header's image size is larger than the file.")
    elif len(d) > image + 16:
        info.rows.append(("Overlay data", f"{len(d) - image:,} bytes after the image"))
    info.cpu_address = lambda o: o - start if o >= start else None


def _detect_com(d: bytes, info: RomInfo) -> None:
    info.system, info.format, info.cpu = "dos", "COM program", "x86"
    info.rows.append(("Size", f"{len(d):,} bytes (loaded at CS:0100)"))
    if len(d) > 0xFF00:
        info.warnings.append("A COM program must be smaller than 65,280 bytes.")
    info.cpu_address = lambda o: 0x100 + o


# ============================================================================ patches
def _detect_patch(d: bytes, info: RomInfo) -> None:
    from .patches import describe_patch, ips_parse, patch_format, PatchError
    info.system, info.format = "patch", patch_format(d).upper()
    info.rows = describe_patch(d)
    if info.format == "IPS":
        try:
            p = ips_parse(d)
        except PatchError:
            return
        info.fields.append(Field(0, 5, "Magic", "PATCH", "magic"))
        rows = []
        for r in p.records[:5000]:
            info.fields.append(Field(r.patch_offset, 5 if not r.rle_count else 8,
                                     f"Record -> 0x{r.offset:06X}", f"{r.size} bytes" + (" RLE" if r.rle_count else ""),
                                     "size"))
            rows.append((f"0x{r.offset:06X}", str(r.size), "RLE" if r.rle_count else "data",
                         f"0x{r.patch_offset:X}"))
        info.listing_header = ("Target offset", "Bytes", "Kind", "Patch offset")
        info.listing = rows


# ============================================================================ entry point
ROM_EXTENSIONS = {".nes", ".fds", ".unf", ".gb", ".gbc", ".sgb", ".gba", ".sfc", ".smc", ".swc", ".fig", ".md",
                  ".gen", ".smd", ".sms", ".gg", ".a26", ".a78", ".a52", ".xex", ".atr", ".car", ".rom",
                  ".prg", ".d64", ".t64", ".tap", ".tzx", ".sna", ".z80", ".exe", ".com", ".ips", ".bps", ".ups",
                  ".bin", ".ch8", ".sg", ".col", ".pce", ".lnx", ".ngp", ".ws", ".vb", ".n64", ".z64", ".v64"}
# extensions the IDE opens in the hex editor by default (not .exe / .com / .bin / .tap / .rom: ambiguous)
HEX_DEFAULT_EXTENSIONS = ROM_EXTENSIONS - {".exe", ".com", ".bin", ".tap", ".rom", ".prg", ".vb", ".z80"}
A26_SIZES = {2048, 4096, 8192, 10240, 10495, 10496, 12288, 16384, 32768, 65536}


def detect(data: bytes, filename: str = "") -> RomInfo:
    d = bytes(data)
    ext = Path(filename).suffix.lower()
    info = RomInfo()
    n = len(d)
    try:
        _detect_into(d, ext, n, info)
    except (IndexError, struct.error, ValueError) as e:
        info.warnings.append(f"The header could not be read completely: {e}")
    if not info.rows:
        info.rows.append(("Size", _kb(n)))
    else:
        info.rows.insert(0, ("File size", _kb(n)))
    info.rows.insert(0, ("System", info.system_name + (f"  [{info.format}]" if info.format else "")))
    return info


def _detect_into(d: bytes, ext: str, n: int, info: RomInfo) -> None:
    if d[:5] == b"PATCH" or d[:4] in (b"UPS1", b"BPS1"):
        _detect_patch(d, info)
        return
    if n >= 16 and d[:4] == b"NES\x1a":
        _detect_nes(d, info)
        return
    if d[:4] == b"FDS\x1a" or d[1:15] == b"*NINTENDO-HVC*":
        _detect_fds(d, info)
        return
    if n >= 128 and d[1:10] == b"ATARI7800":
        _detect_a78(d, info)
        return
    if n >= 16 and d[:4] == b"CART":
        _detect_car(d, info)
        return
    if n >= 16 and d[0] == 0x96 and d[1] == 0x02:
        _detect_atr(d, info)
        return
    if n >= 0x40 and d[:3] == b"C64" and ext in (".t64", "") or d[:19] == b"C64 tape image file":
        _detect_t64(d, info)
        return
    if d[:12] == b"C64-TAPE-RAW":
        info.system, info.format = "c64", f"C64 raw tape (TAP v{d[12]})"
        info.rows.append(("Pulse data", f"{_u32(d, 16):,} bytes"))
        return
    if d[:8] == b"ZXTape!\x1a":
        _detect_tzx(d, info)
        return
    if n >= 0x1C and d[:2] in (b"MZ", b"ZM"):
        _detect_mz(d, info)
        return
    if n >= 0xC0 and d[0xB2] == 0x96 and (gba_complement(d) == d[0xBD] or ext == ".gba"):
        _detect_gba(d, info)
        return
    if n >= 0x200 and (d[0x100:0x104] == b"SEGA" or d[0x101:0x105] == b"SEGA"):
        _detect_genesis(d, info)
        return
    if ext == ".smd" and n % 16384 == 512 and d[8:10] == b"\xaa\xbb":
        info.system, info.format = "genesis", "SMD interleaved"
        info.warnings.append("Interleaved SMD dump: convert it to a plain .bin/.md before editing the header.")
        return
    if n >= 0x8000 and ext not in (".gb", ".gbc"):
        where = snes_header_offset(d)
        if where is not None and (ext in (".sfc", ".smc", ".swc", ".fig", "") or _snes_score(d, where[0] - snes_copier_header(d), "lo" if where[1] == "LoROM" else "hi") >= 9):
            _detect_snes(d, info, where)
            return
    if n >= 0x150 and (ext in (".gb", ".gbc", ".sgb") or
                       (gb_header_checksum(d) == d[0x14D] and d[0x148] <= 8 and d[0x147] in GB_CART and
                        _printable(d[0x134:0x13F], 0.9) and ext not in (".a26", ".bin", ".sms", ".gg"))):
        _detect_gb(d, info)
        return
    for o in (0x7FF0, 0x3FF0, 0x1FF0):
        if n >= o + 16 and d[o:o + 8] == b"TMR SEGA":
            _detect_sms(d, info, o)
            return
    if n in D64_SIZES or ext == ".d64":
        _detect_d64(d, info)
        return
    if ext in (".tap", ".tzx"):
        blocks = tap_blocks(d)
        if blocks:
            _detect_tap(d, info, blocks)
            return
    if ext == ".sna" or n in (49179, 131103, 147487) and ext in (".sna", ""):
        if n >= 49179:
            _detect_sna(d, info)
            return
    if ext in (".xex", ".obj", ".com") and d[:2] == b"\xff\xff":
        segs = xex_segments(d)
        if segs:
            _detect_xex(d, info, segs)
            return
    if ext == ".prg" and n >= 3:
        _detect_prg(d, info)
        return
    if ext == ".com":
        _detect_com(d, info)
        return
    if ext in (".a26",) or (ext in (".bin", "") and n in A26_SIZES):
        _detect_a26(d, info)
        return


# ============================================================================ checksum repair
def fix_checksum(data: bytes, filename: str = "") -> tuple[bytes, str]:
    """(fixed data, message). Raises ValueError when the format has no fixable checksum."""
    info = detect(data, filename)
    d = bytearray(data)
    if info.system in ("gb", "gbc"):
        d[0x14D] = gb_header_checksum(d)
        g = gb_global_checksum(d)
        d[0x14E], d[0x14F] = g >> 8, g & 0xFF
        return bytes(d), f"Game Boy header checksum {d[0x14D]:02X}, global checksum {g:04X}"
    if info.system == "gba":
        d[0xBD] = gba_complement(d)
        return bytes(d), f"GBA complement check {d[0xBD]:02X}"
    if info.system == "snes":
        where = snes_header_offset(d)
        if where is None:
            raise ValueError("SNES header not found")
        o = where[0]
        c = snes_checksum(d, o)
        struct.pack_into("<HH", d, o + 0x1C, c ^ 0xFFFF, c)
        return bytes(d), f"SNES checksum {c:04X}, complement {c ^ 0xFFFF:04X}"
    if info.system == "genesis" and info.format != "SMD interleaved":
        c = genesis_checksum(d)
        struct.pack_into(">H", d, 0x18E, c)
        return bytes(d), f"Genesis checksum {c:04X}"
    if info.format == "CAR cartridge":
        c = car_checksum(d)
        struct.pack_into(">I", d, 8, c)
        return bytes(d), f"CAR checksum {c:08X}"
    raise ValueError(f"No checksum to fix for {info.system_name}.")


__all__ = ["Field", "RomInfo", "SYSTEM_NAMES", "ROM_EXTENSIONS", "HEX_DEFAULT_EXTENSIONS", "detect",
           "fix_checksum", "a26_bankswitch", "gb_header_checksum", "gb_global_checksum", "gba_complement",
           "snes_checksum", "snes_header_offset", "genesis_checksum", "car_checksum", "xex_segments",
           "tap_blocks", "c64_basic_listing", "d64_offset", "petscii"]


# ============================================================================ emulator system ids
# ids of radide/retro/emu (catalog.SYSTEM_TITLES) for the systems detected here
EMU_SYSTEM = {"atari2600": "a2600", "atari8bit": "a8", "atari7800": "a7800", "nes": "nes", "fds": "nes",
              "snes": "snes", "gb": "gb", "gbc": "gbc", "gba": "gba", "sms": "sms", "genesis": "genesis",
              "c64": "c64", "zxspectrum": "zx", "dos": "dos"}


def emu_system(info: RomInfo) -> str:
    """The emulator slice's system id for *info* ("" = no emulator / unknown)."""
    if info.system == "sms":
        region = next((f.value for f in info.fields if f.name == "Region / size"), "")
        if "Game Gear" in region:
            return "gg"
    if info.system == "dos" and any("Windows" in v for _n, v in info.rows):
        return ""
    return EMU_SYSTEM.get(info.system, "")


def detect_system(path) -> str:
    """System id (radide/retro/emu ids: a2600, nes, snes, gb, gbc, gba, sms, gg, c64, a8, dos, ...) of a file;
    "" when unknown. radide/retro/emu/systems.py calls this first."""
    p = Path(path)
    try:
        if p.stat().st_size > 64 << 20:
            return ""
        data = p.read_bytes()
    except OSError:
        return ""
    return emu_system(detect(data, p.name))
