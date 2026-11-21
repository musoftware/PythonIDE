"""ROM / program file formats -> segments for the disassembler (no Qt in here).

    system      files                  layout
    atari2600   .a26 .bin (2K-32K)     2K at $F800 / 4K at $F000; F8 / F6 / F4 bank switching: 4K banks at $F000
    nes         .nes (iNES 1 / 2.0)    16-byte header, PRG 16K banks ($C000 fixed last bank), CHR 8K banks
    gameboy     .gb .gbc               bank 0 at $0000 (entry $0100, interrupt vectors), banks 1.. at $4000
    c64         .prg                   2-byte load address + program (BASIC "SYS nnnn" stub -> entry point)
    zx          .tap / raw .bin        TAP CODE blocks at their start address (raw: the address you give)
    6502 / z80  raw .bin               one segment at the address you give

``load(path, system=None, base=None)`` -> ``RomImage``. ``detect(path, data)`` guesses the system.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .disasm import Segment

SYSTEMS = {"atari2600": ("Atari 2600", "6502", "dasm"), "nes": ("NES / Famicom", "6502", "ca65"),
           "gameboy": ("Game Boy", "sm83", "rgbds"), "c64": ("Commodore 64", "6502", "ca65"),
           "zx": ("ZX Spectrum", "z80", "sjasmplus"), "6502": ("Raw 6502 binary", "6502", "ca65"),
           "z80": ("Raw Z80 binary", "z80", "sjasmplus")}


@dataclass
class RomImage:
    system: str
    cpu: str
    dialect: str
    segments: list[Segment]
    data: bytes                                   # the whole original file
    info: dict = field(default_factory=dict)      # header fields shown to the user
    extras: dict = field(default_factory=dict)    # file name -> bytes written next to the source (chr.bin ...)
    compare: tuple[int, int] | None = None        # (start, length) of the original that a rebuild must equal
    name: str = ""

    @property
    def title(self) -> str:
        return SYSTEMS.get(self.system, (self.system,))[0]

    @property
    def sha1(self) -> str:
        return hashlib.sha1(self.data).hexdigest()


def detect(path, data: bytes) -> str:
    ext = Path(str(path)).suffix.lower()
    if data[:4] == b"NES\x1a" or ext == ".nes":
        return "nes"
    if ext in (".gb", ".gbc", ".sgb") or (len(data) >= 0x150 and data[0x104:0x108] == bytes([0xCE, 0xED, 0x66, 0x66])):
        return "gameboy"
    if ext in (".prg", ".p00"):
        return "c64"
    if ext in (".tap", ".sna", ".z80"):
        return "zx"
    if ext in (".a26",) or (ext == ".bin" and len(data) in (2048, 4096, 8192, 16384, 32768)):
        return "atari2600"
    return "6502"


def _word(data: bytes, off: int) -> int:
    return data[off] | (data[off + 1] << 8)


def load(path, system: str | None = None, base: int | None = None, entry: int | None = None) -> RomImage:
    p = Path(str(path))
    data = p.read_bytes()
    system = system or detect(p, data)
    fn = {"atari2600": _atari2600, "nes": _nes, "gameboy": _gameboy, "c64": _c64, "zx": _zx}.get(system)
    if fn is None:
        cpu = "z80" if system == "z80" else "6502"
        b = 0x8000 if base is None else base
        seg = Segment("code", b, data, entries=[(entry if entry is not None else b, "Start")])
        img = RomImage(system, cpu, SYSTEMS[system][2], [seg], data, {"Load address": f"${b:04X}"})
    elif system == "zx":
        img = _zx(p, data, base, entry)
    else:
        img = fn(data)
    img.name = p.stem
    img.info.setdefault("File size", f"{len(data)} bytes")
    img.info.setdefault("SHA-1", img.sha1)
    if img.compare is None:
        img.compare = (0, len(data))
    return img


# ---------------------------------------------------------------------------------------------- Atari 2600
def _atari2600(data: bytes) -> RomImage:
    size = len(data)
    if size <= 4096:
        base = 0x10000 - size if size in (2048, 4096) else 0xF000
        seg = Segment("code", base, data, mirror=max(size, 1) - 1 if size in (2048, 4096) else 0,
                      vectors=[(0xFFFA, "NMI"), (0xFFFC, "Reset"), (0xFFFE, "IRQ")])
        if seg.exact(0xFFFC) is None:
            seg.vectors = []
        return RomImage("atari2600", "6502", "dasm", [seg], data,
                        {"Size": f"{size // 1024}K", "Bank switching": "none", "ROM address": f"${base:04X}"})
    scheme = {8192: "F8", 16384: "F6", 32768: "F4"}.get(size, "4K banks")
    segs = []
    for i in range(0, size // 4096):
        segs.append(Segment(f"bank{i}", 0xF000, data[i * 4096:(i + 1) * 4096], bank=i, mirror=0xFFF,
                            vectors=[(0xFFFA, "NMI"), (0xFFFC, "Reset"), (0xFFFE, "IRQ")], fixed=False,
                            prefix=f"B{i}_"))
    return RomImage("atari2600", "6502", "dasm", segs, data,
                    {"Size": f"{size // 1024}K", "Bank switching": scheme, "Banks": str(len(segs))})


# ---------------------------------------------------------------------------------------------- NES
def _nes(data: bytes) -> RomImage:
    if data[:4] != b"NES\x1a":
        raise ValueError("not an iNES file (no NES<1A> header)")
    prg_n, chr_n = data[4], data[5]
    f6, f7 = data[6], data[7]
    nes2 = (f7 & 0x0C) == 0x08
    if nes2:
        prg_n |= (data[9] & 0x0F) << 8
        chr_n |= (data[9] & 0xF0) << 4
    mapper = (f6 >> 4) | (f7 & 0xF0)
    trainer = bool(f6 & 4)
    off = 16
    segs = [Segment("HEADER", 0, data[:16], trace=False)]
    if trainer:
        segs.append(Segment("TRAINER", 0x7000, data[16:16 + 512], trace=False))
        off += 512
    prg = data[off:off + prg_n * 16384]
    off += len(prg)
    chr_rom = data[off:off + chr_n * 8192]
    tail = data[off + len(chr_rom):]
    vectors = [(0xFFFA, "NMI"), (0xFFFC, "Reset"), (0xFFFE, "IRQ")]
    if len(prg) <= 32768:
        base = 0x10000 - len(prg)
        segs.append(Segment("PRG", base, prg, vectors=vectors))
    else:
        nb = len(prg) // 16384
        for i in range(nb):
            last = i == nb - 1
            segs.append(Segment(f"PRG{i}", 0xC000 if last else 0x8000, prg[i * 16384:(i + 1) * 16384], bank=i,
                                vectors=vectors if last else [], fixed=last, prefix="" if last else f"B{i}_"))
    extras = {}
    if chr_rom:
        extras["chr.bin"] = chr_rom
    if tail:
        extras["tail.bin"] = tail
    mirroring = "four-screen" if f6 & 8 else ("vertical" if f6 & 1 else "horizontal")
    info = {"Format": "NES 2.0" if nes2 else "iNES", "Mapper": str(mapper), "PRG ROM": f"{len(prg) // 1024}K",
            "CHR ROM": f"{len(chr_rom) // 1024}K" if chr_rom else "none (CHR RAM)", "Mirroring": mirroring,
            "Battery": "yes" if f6 & 2 else "no", "Trainer": "yes" if trainer else "no"}
    img = RomImage("nes", "6502", "ca65", segs, data, info, extras)
    img.info["_mapper"] = mapper
    return img


# ---------------------------------------------------------------------------------------------- Game Boy
CART_TYPES = {0x00: "ROM only", 0x01: "MBC1", 0x02: "MBC1+RAM", 0x03: "MBC1+RAM+BATTERY", 0x05: "MBC2",
              0x06: "MBC2+BATTERY", 0x0F: "MBC3+TIMER+BATTERY", 0x10: "MBC3+TIMER+RAM+BATTERY", 0x11: "MBC3",
              0x12: "MBC3+RAM", 0x13: "MBC3+RAM+BATTERY", 0x19: "MBC5", 0x1A: "MBC5+RAM", 0x1B: "MBC5+RAM+BATTERY",
              0x1C: "MBC5+RUMBLE"}


def gb_header_checksum(data: bytes) -> int:
    x = 0
    for b in data[0x134:0x14D]:
        x = (x - b - 1) & 0xFF
    return x


def gb_global_checksum(data: bytes) -> int:
    return sum(b for i, b in enumerate(data) if i not in (0x14E, 0x14F)) & 0xFFFF


def _gameboy(data: bytes) -> RomImage:
    if len(data) < 0x150:
        raise ValueError("too small for a Game Boy ROM")
    segs = []
    banks = max(1, (len(data) + 0x3FFF) // 0x4000)
    for i in range(banks):
        chunk = data[i * 0x4000:(i + 1) * 0x4000]
        if i == 0:
            entries = [(0x0100, "Start")]
            for addr, name in ((0x40, "VBlankInterrupt"), (0x48, "StatInterrupt"), (0x50, "TimerInterrupt"),
                               (0x58, "SerialInterrupt"), (0x60, "JoypadInterrupt")):
                if addr < len(chunk) and chunk[addr] not in (0x00, 0xFF):
                    entries.append((addr, name))
            segs.append(Segment("ROM0", 0x0000, chunk, entries=entries))
        else:
            segs.append(Segment(f"ROMX{i}", 0x4000, chunk, bank=i, fixed=False, prefix=f"B{i}_"))
    title = bytes(b for b in data[0x134:0x144] if 32 <= b < 127).decode("ascii", "replace").strip()
    hc = gb_header_checksum(data)
    info = {"Title": title, "Cartridge": CART_TYPES.get(data[0x147], f"${data[0x147]:02X}"),
            "ROM size": f"{32 << data[0x148]}K" if data[0x148] < 9 else f"${data[0x148]:02X}",
            "Colour (CGB)": {0x80: "supported", 0xC0: "only"}.get(data[0x143], "no"),
            "Header checksum": f"${data[0x14D]:02X} ({'OK' if hc == data[0x14D] else f'should be ${hc:02X}'})",
            "Global checksum": f"${_word(bytes([data[0x14F], data[0x14E]]), 0):04X}"}
    return RomImage("gameboy", "sm83", "rgbds", segs, data, info)


# ---------------------------------------------------------------------------------------------- C64
def basic_sys_address(prg: bytes, load: int) -> int | None:
    """The address of "SYS nnnn" in a BASIC stub at $0801 (token $9E), or None."""
    body = prg[2:2 + 64]
    i = body.find(b"\x9e")
    if i < 0:
        return None
    j = i + 1
    while j < len(body) and body[j] in b" (":
        j += 1
    digits = b""
    while j < len(body) and 48 <= body[j] <= 57:
        digits += bytes([body[j]])
        j += 1
    return int(digits) if digits else None


def _c64(data: bytes) -> RomImage:
    if len(data) < 3:
        raise ValueError("a .prg file starts with a 2-byte load address")
    load = _word(data, 0)
    body = data[2:]
    entry = basic_sys_address(data, load) if load == 0x0801 else load
    seg = Segment("CODE", load, body, entries=[(entry, "Start")] if entry is not None else [])
    info = {"Load address": f"${load:04X}", "Entry": f"${entry:04X} (SYS {entry})" if entry else "unknown",
            "Length": f"{len(body)} bytes"}
    hdr = Segment("LOADADDR", 0, data[:2], trace=False)
    return RomImage("c64", "6502", "ca65", [hdr, seg], data, info)


# ---------------------------------------------------------------------------------------------- ZX Spectrum
def tap_blocks(data: bytes) -> list[bytes]:
    """The blocks of a .tap file (flag byte + payload + checksum each)."""
    out, i = [], 0
    while i + 2 <= len(data):
        n = _word(data, i)
        out.append(data[i + 2:i + 2 + n])
        i += 2 + n
    return out


def _usr_address(basic: bytes) -> int | None:
    i = basic.find(b"\xc0")                      # USR token
    while i >= 0:
        j = i + 1
        while j < len(basic) and basic[j] in b" ":
            j += 1
        if basic[j:j + 4] == b'VAL"' or basic[j:j + 2] == b'\xb0"':          # USR VAL "nnnnn"
            j = basic.index(b'"', j) + 1
        digits = b""
        while j < len(basic) and 48 <= basic[j] <= 57:
            digits += bytes([basic[j]])
            j += 1
        if digits:
            return int(digits)
        i = basic.find(b"\xc0", i + 1)
    return None


def _zx(p: Path, data: bytes, base: int | None, entry: int | None) -> RomImage:
    if p.suffix.lower() != ".tap":
        b = 0x8000 if base is None else base
        seg = Segment("code", b, data, entries=[(entry if entry is not None else b, "Start")])
        return RomImage("zx", "z80", "sjasmplus", [seg], data, {"Load address": f"${b:04X}"})
    blocks = tap_blocks(data)
    segs, usr, pos, header = [], None, 0, None
    compare = None
    for blk in blocks:
        pos += 2
        if blk and blk[0] == 0x00 and len(blk) >= 19:
            header = blk
        elif blk and blk[0] == 0xFF and header is not None:
            payload = blk[1:-1]
            if header[1] == 0 and usr is None:                      # BASIC program
                usr = _usr_address(payload)
            elif header[1] == 3:                                      # CODE
                start = _word(header, 14)
                name = header[2:12].decode("latin-1").strip() or f"code{len(segs)}"
                segs.append(Segment(f"code{len(segs)}", start, payload, entries=[], prefix="" if not segs else
                                    f"C{len(segs)}_"))
                segs[-1].tap_name = name                              # type: ignore[attr-defined]
                if compare is None:
                    compare = (pos + 1, len(payload))
            header = None
        pos += len(blk)
    if not segs:
        raise ValueError("no CODE block in this .tap file")
    start = entry if entry is not None else (usr if usr is not None else segs[0].base)
    for s in segs:
        if s.exact(start) is not None:
            s.entries.append((start, "Start"))
    info = {"CODE blocks": ", ".join(f"{getattr(s, 'tap_name', s.name)} @ ${s.base:04X} ({len(s.data)} bytes)"
                                     for s in segs),
            "Entry (RANDOMIZE USR)": f"{start} (${start:04X})"}
    img = RomImage("zx", "z80", "sjasmplus", segs, data, info)
    img.compare = compare
    return img
