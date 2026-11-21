"""Synthetic test ROMs / images with valid headers - tiny original homebrew written for RAD IDE (an endless loop,
some text and tiles), never game data. Used by the tests, the samples and the "Demo ROM" project template.

Note: the Game Boy / GBA images leave the logo area empty, so emulators that run the real boot ROM refuse them;
they are for the header tools, not for playing.
"""
from __future__ import annotations

import struct

TITLE = "RADIDE TEST"


def _pad(data: bytes, size: int, fill: int = 0xFF) -> bytearray:
    out = bytearray(data[:size])
    out.extend(bytes([fill]) * (size - len(out)))
    return out


def tiles_2bpp_planar(count: int = 512) -> bytes:
    """NES-style 8x8 tiles: a box, a checkerboard, stripes and a ramp of patterns (original art)."""
    out = bytearray()
    for t in range(count):
        kind = t % 4
        for y in range(8):
            if kind == 0:
                lo = 0xFF if y in (0, 7) else 0x81
            elif kind == 1:
                lo = 0xAA if y % 2 == 0 else 0x55
            elif kind == 2:
                lo = 0xFF if y % 2 == 0 else 0x00
            else:
                lo = (t * 7 + y * 13) & 0xFF
            out.append(lo)
        for y in range(8):
            out.append(((t >> 2) * 0x11 + y) & 0xFF if kind == 3 else (0x3C if 2 <= y <= 5 else 0))
    return bytes(out)


def nes_rom(prg_banks: int = 1, chr_banks: int = 1, mapper: int = 0, vertical: bool = True,
            battery: bool = False, nes2: bool = False, message: str = "HELLO FROM RAD IDE") -> bytes:
    hdr = bytearray(b"NES\x1a")
    hdr += bytes([prg_banks, chr_banks,
                  (mapper & 0x0F) << 4 | (1 if vertical else 0) | (2 if battery else 0),
                  (mapper & 0xF0) | (0x08 if nes2 else 0)])
    hdr += bytes(8)
    prg_size = prg_banks * 16384
    base = 0xC000 if prg_banks == 1 else 0x8000
    # SEI / CLD / LDX #$FF / TXS / loop: JMP loop
    code = bytes([0x78, 0xD8, 0xA2, 0xFF, 0x9A, 0x4C]) + struct.pack("<H", base + 5)
    prg = _pad(code, prg_size)
    prg[0x100:0x100 + len(message)] = message.encode("ascii")
    prg[0x100 + len(message)] = 0xFF
    nmi = irq = base + 5 + 3                  # an RTI after the loop
    prg[8] = 0x40
    prg[-6:] = struct.pack("<HHH", nmi, base, irq)
    chr_ = tiles_2bpp_planar(512)[:chr_banks * 8192] * (1 if chr_banks <= 1 else chr_banks)
    return bytes(hdr) + bytes(prg) + bytes(chr_[:chr_banks * 8192])


def gb_rom(title: str = TITLE, cart_type: int = 0x00, cgb: bool = False, size_code: int = 0,
           fix: bool = True) -> bytes:
    size = 32768 << size_code
    d = bytearray(size)
    d[0x100:0x104] = b"\x00\xc3\x50\x01"      # nop / jp $0150
    t = title.encode("ascii")[:11 if cgb else 16]
    d[0x134:0x134 + len(t)] = t
    if cgb:
        d[0x143] = 0x80
    d[0x147] = cart_type
    d[0x148] = size_code
    d[0x14A] = 0x01
    d[0x150:0x153] = b"\xf3\x18\xfe"          # di / jr -2
    d[0x200:0x200 + 18] = b"HELLO FROM RAD IDE"
    if fix:
        from .detect import gb_global_checksum, gb_header_checksum
        d[0x14D] = gb_header_checksum(d)
        g = gb_global_checksum(d)
        d[0x14E:0x150] = struct.pack(">H", g)
    return bytes(d)


def gba_rom(title: str = "RADIDETEST", fix: bool = True) -> bytes:
    d = bytearray(0x400)
    d[0:4] = struct.pack("<I", 0xEA00002E)    # b $080000C0
    d[0xA0:0xA0 + len(title)] = title.encode("ascii")[:12]
    d[0xAC:0xB0] = b"RADE"
    d[0xB0:0xB2] = b"00"
    d[0xB2] = 0x96
    d[0xC0:0xC4] = struct.pack("<I", 0xEAFFFFFE)  # b . (endless loop)
    if fix:
        from .detect import gba_complement
        d[0xBD] = gba_complement(d)
    return bytes(d)


def snes_rom(title: str = TITLE, hirom: bool = False, size_kb: int = 128, copier: bool = False,
             fix: bool = True) -> bytes:
    size = size_kb * 1024
    d = bytearray(b"\xff" * size)
    o = 0xFFC0 if hirom else 0x7FC0
    code_at = 0x8000 if hirom else 0x0000
    d[code_at:code_at + 5] = b"\x78\x18\xfb\x80\xfe"   # sei / clc / xce / bra -2
    t = title.encode("ascii")[:21].ljust(21)
    d[o:o + 21] = t
    d[o + 0x15] = 0x21 if hirom else 0x20
    d[o + 0x16] = 0x00
    n = 0
    while (1024 << n) < size:
        n += 1
    d[o + 0x17] = n
    d[o + 0x18] = 0
    d[o + 0x19] = 1
    d[o + 0x1A] = 0x00
    d[o + 0x1B] = 0
    d[o + 0x1C:o + 0x20] = b"\xff\xff\x00\x00"
    d[o + 0x3C:o + 0x3E] = b"\x00\x80"       # reset -> $8000
    d[o + 0x2A:o + 0x2C] = b"\x00\x80"
    data = bytes(d)
    if fix:
        from .detect import snes_checksum
        c = snes_checksum(data, o)
        struct.pack_into("<HH", d, o + 0x1C, c ^ 0xFFFF, c)
        data = bytes(d)
    return (bytes(512) + data) if copier else data


def genesis_rom(title: str = TITLE, size_kb: int = 128, fix: bool = True) -> bytes:
    d = bytearray(size_kb * 1024)
    d[0:8] = struct.pack(">II", 0x00FFFE00, 0x00000200)
    d[0x100:0x110] = b"SEGA MEGA DRIVE "
    d[0x110:0x120] = b"(C)RADIDE 2026  "
    d[0x120:0x150] = title.encode("ascii").ljust(48)
    d[0x150:0x180] = title.encode("ascii").ljust(48)
    d[0x180:0x18E] = b"GM 00000000-00"
    d[0x190:0x1A0] = b"J".ljust(16)
    d[0x1A0:0x1B0] = struct.pack(">IIII", 0, len(d) - 1, 0xFF0000, 0xFFFFFF)
    d[0x1F0:0x1F3] = b"JUE"
    d[0x200:0x202] = b"\x60\xfe"             # bra.s * (endless loop)
    d[0x300:0x312] = b"HELLO FROM RAD IDE"
    if fix:
        from .detect import genesis_checksum
        struct.pack_into(">H", d, 0x18E, genesis_checksum(d))
    return bytes(d)


def a26_rom(banks: int = 1, superchip: bool = False) -> bytes:
    """4 KB per bank; every bank: SEI / CLD / loop, vectors -> $F000."""
    out = bytearray()
    for b in range(banks):
        bank = bytearray(b"\xff" * 4096)
        if superchip:
            bank[0:256] = b"\x00" * 256
            start = 256
        else:
            start = 0
        bank[start:start + 6] = b"\x78\xd8\x4c" + struct.pack("<H", 0xF000 + start + 2) + b"\xea"
        bank[start + 0x40:start + 0x40 + 6] = f"BANK{b}".encode().ljust(6)[:6]
        bank[-4:] = struct.pack("<HH", 0xF000 + start, 0xF000 + start)
        out += bank
    return bytes(out)


def a26_e0_rom() -> bytes:
    """8 KB with E0 (Parker Bros.) hotspot accesses."""
    d = bytearray(a26_rom(2))
    d[0x100:0x103] = b"\xad\xe0\x1f"          # lda $1FE0
    return bytes(d)


def a78_rom(title: str = TITLE, rom_kb: int = 16) -> bytes:
    h = bytearray(128)
    h[0] = 1
    h[1:17] = b"ATARI7800".ljust(16, b"\x00")
    h[17:49] = title.encode("ascii").ljust(32, b"\x00")
    h[49:53] = struct.pack(">I", rom_kb * 1024)
    h[53:55] = b"\x00\x00"
    h[55], h[56] = 1, 1
    h[100:128] = b"ACTUAL CART DATA STARTS HERE"
    rom = bytearray(b"\xff" * rom_kb * 1024)
    start = 0x10000 - len(rom)
    rom[0:4] = b"\x78\x4c" + struct.pack("<B", (start + 1) & 0xFF) + bytes([(start + 1) >> 8])
    rom[-4:] = struct.pack("<HH", start, start)
    return bytes(h + rom)


def car_rom(cart_type: int = 1, fix: bool = True) -> bytes:
    data = bytearray(b"\xff" * (8192 if cart_type == 1 else 16384))
    data[0:4] = b"\x4c\x00\xa0\x00"
    data[-6:] = struct.pack("<HBBH", 0xA000, 0, 0x04, 0xA000)
    h = bytearray(b"CART") + struct.pack(">I", cart_type) + b"\x00" * 8
    out = h + data
    if fix:
        from .detect import car_checksum
        struct.pack_into(">I", out, 8, car_checksum(out))
    return bytes(out)


def atr_image(files=(("HELLO", "BAS", b"10 PRINT \"HELLO\"\x9b"),)) -> bytes:
    """A 720-sector single density Atari DOS 2 style disk with a directory."""
    ssize, sectors = 128, 720
    body = bytearray(ssize * sectors)
    first = 4
    for i, (name, ext, data) in enumerate(files):
        sec = 361 + i // 8
        off = (sec - 1) * 128 + (i % 8) * 16
        count = max(1, (len(data) + 124) // 125)
        body[off] = 0x42
        body[off + 1:off + 3] = struct.pack("<H", count)
        body[off + 3:off + 5] = struct.pack("<H", first)
        body[off + 5:off + 13] = name.encode().ljust(8)
        body[off + 13:off + 16] = ext.encode().ljust(3)
        so = (first - 1) * 128
        body[so:so + len(data[:125])] = data[:125]
        first += count
    paras = len(body) // 16
    h = bytearray(16)
    h[0:2] = b"\x96\x02"
    h[2:4] = struct.pack("<H", paras & 0xFFFF)
    h[4:6] = struct.pack("<H", ssize)
    h[6] = paras >> 16
    return bytes(h + body)


def xex_file() -> bytes:
    code = b"\xa9\x22\x8d\xc6\x02\x4c\x05\x20"          # lda #$22 / sta 710 / jmp *
    out = bytearray(b"\xff\xff") + struct.pack("<HH", 0x2000, 0x2000 + len(code) - 1) + code
    out += struct.pack("<HH", 0x2E0, 0x2E1) + struct.pack("<H", 0x2000)
    return bytes(out)


def c64_prg() -> bytes:
    """10 SYS 2061 + inc $d020 / jmp loop."""
    line = struct.pack("<HH", 0x080B, 10) + b"\x9e" + b"2061" + b"\x00"
    basic = line + b"\x00\x00"
    code = b"\xee\x20\xd0\x4c\x0d\x08"
    return struct.pack("<H", 0x0801) + basic + code


def d64_image(name: str = "RADIDE DISK", files=(("HELLO", b"\x01\x08" + b"\x00" * 10),)) -> bytes:
    from .detect import d64_offset
    d = bytearray(174848)
    bam = d64_offset(18, 0)
    d[bam:bam + 4] = bytes([18, 1, 0x41, 0])
    for t in range(1, 36):
        from .detect import d64_sectors
        n = d64_sectors(t)
        free = 0 if t == 18 else n
        d[bam + 4 * t:bam + 4 * t + 4] = bytes([free]) + (b"\xff\xff\x1f" if free else b"\x00\x00\x00")
    d[bam + 0x90:bam + 0xA0] = name.encode("ascii")[:16].ljust(16, b"\xa0")
    d[bam + 0xA0:bam + 0xAB] = b"\xa0\xa0RD\xa02A\xa0\xa0\xa0\xa0"
    dirs = d64_offset(18, 1)
    d[dirs:dirs + 2] = b"\x00\xff"
    for i, (fname, data) in enumerate(files):
        e = dirs + i * 32
        d[e + 2] = 0x82
        d[e + 3], d[e + 4] = 17, 0
        d[e + 5:e + 21] = fname.encode("ascii")[:16].ljust(16, b"\xa0")
        d[e + 30:e + 32] = struct.pack("<H", 1)
        so = d64_offset(17, 0)
        d[so:so + 2] = bytes([0, len(data) + 1])
        d[so + 2:so + 2 + len(data)] = data
    return bytes(d)


def t64_image() -> bytes:
    prg = c64_prg()
    h = bytearray(64)
    h[0:32] = b"C64 tape image file".ljust(32, b"\x00")
    h[0x20:0x22] = struct.pack("<H", 0x0101)
    h[0x22:0x24] = struct.pack("<H", 1)
    h[0x24:0x26] = struct.pack("<H", 1)
    h[0x28:0x40] = b"RADIDE TAPE".ljust(24, b" ")
    e = bytearray(32)
    e[0], e[1] = 1, 0x82
    start = struct.unpack("<H", prg[:2])[0]
    e[2:6] = struct.pack("<HH", start, start + len(prg) - 2)
    e[8:12] = struct.pack("<I", 96)
    e[16:32] = b"HELLO".ljust(16, b" ")
    return bytes(h + e + prg[2:])


def _tap_block(flag: int, data: bytes) -> bytes:
    blk = bytes([flag]) + data
    x = 0
    for b in blk:
        x ^= b
    blk += bytes([x])
    return struct.pack("<H", len(blk)) + blk


def zx_tap() -> bytes:
    code = b"\x3e\x02\xd3\xfe\x18\xfe"          # ld a,2 / out ($fe),a / jr $
    hdr = bytes([3]) + b"radide    " + struct.pack("<HHH", len(code), 32768, 32768)
    return _tap_block(0, hdr) + _tap_block(0xFF, code)


def zx_tzx() -> bytes:
    out = bytearray(b"ZXTape!\x1a\x01\x14")
    desc = b"RAD IDE test tape"
    out += bytes([0x30, len(desc)]) + desc
    tap = zx_tap()
    pos = 0
    while pos < len(tap):
        n = struct.unpack_from("<H", tap, pos)[0]
        out += b"\x10" + struct.pack("<HH", 1000, n) + tap[pos + 2:pos + 2 + n]
        pos += 2 + n
    return bytes(out)


def zx_sna() -> bytes:
    h = bytearray(27)
    h[23:25] = struct.pack("<H", 0xFF00)       # SP
    h[25] = 1
    h[26] = 2
    ram = bytearray(49152)
    ram[0xFF00 - 0x4000:0xFF02 - 0x4000] = struct.pack("<H", 0x8000)   # PC on the stack
    ram[0x8000 - 0x4000:0x8000 - 0x4000 + 2] = b"\x18\xfe"
    return bytes(h + ram)


def dos_mz() -> bytes:
    code = b"\xb4\x09\xba\x0d\x00\x0e\x1f\xcd\x21\xb8\x00\x4c\xcd\x21" + b"Hello$"
    hdr = bytearray(32)
    total = 32 + len(code)
    hdr[0:2] = b"MZ"
    struct.pack_into("<HHHHHHHHHHHH", hdr, 2, total % 512, (total + 511) // 512, 0, 2, 0x10, 0xFFFF,
                     0, 0x100, 0, 0, 0, 0x1C)
    return bytes(hdr + code)


def dos_com() -> bytes:
    return b"\xb4\x09\xba\x08\x01\xcd\x21\xc3Hello$"


ALL = {"nes": ("demo.nes", nes_rom), "gb": ("demo.gb", gb_rom), "gbc": ("demo.gbc", lambda: gb_rom(cgb=True)),
       "gba": ("demo.gba", gba_rom), "snes": ("demo.sfc", snes_rom), "genesis": ("demo.md", genesis_rom),
       "atari2600": ("demo.a26", a26_rom), "atari7800": ("demo.a78", a78_rom), "car": ("demo.car", car_rom),
       "atr": ("demo.atr", atr_image), "xex": ("demo.xex", xex_file), "prg": ("demo.prg", c64_prg),
       "d64": ("demo.d64", d64_image), "t64": ("demo.t64", t64_image), "tap": ("demo.tap", zx_tap),
       "tzx": ("demo.tzx", zx_tzx), "sna": ("demo.sna", zx_sna), "exe": ("demo.exe", dos_mz),
       "com": ("demo.com", dos_com)}

__all__ = ["ALL"] + [n for n in list(globals()) if n.endswith(("_rom", "_image", "_file", "_prg", "_tap", "_tzx",
                                                                "_sna", "_mz", "_com"))]
