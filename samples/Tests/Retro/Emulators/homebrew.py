"""Tiny homebrew test programs written byte by byte for RAD IDE's emulator tests (original work, public
domain / CC0). No commercial ROM, BIOS or game data is used anywhere.

    python homebrew.py <out folder>      writes test.a26 test.nes test.gb test.gba test.prg test.xex HELLO.COM
"""
from __future__ import annotations

import sys
from pathlib import Path


def atari2600() -> bytes:
    """4 KB cartridge: a proper 262-line frame loop that scrolls background colours."""
    code = bytes([
        0x78, 0xD8, 0xA2, 0xFF, 0x9A,          # F000 sei / cld / ldx #$ff / txs
        0xA9, 0x02, 0x85, 0x00,                # F005 frame: lda #2 / sta VSYNC
        0x85, 0x02, 0x85, 0x02, 0x85, 0x02,    # F009 3 x sta WSYNC
        0xA9, 0x00, 0x85, 0x00,                # F00F lda #0 / sta VSYNC
        0xE6, 0x80, 0xA6, 0x80,                # F013 inc $80 / ldx $80
        0xA0, 0xF0,                            # F017 ldy #240
        0x86, 0x09, 0x85, 0x02, 0xE8, 0x88,    # F019 line: stx COLUBK / sta WSYNC / inx / dey
        0xD0, 0xF8,                            # F01F bne line
        0xA0, 0x13,                            # F021 ldy #19
        0x85, 0x02, 0x88, 0xD0, 0xFB,          # F023 ov: sta WSYNC / dey / bne ov
        0x4C, 0x05, 0xF0,                      # F028 jmp frame
    ])
    rom = bytearray(code + b"\xEA" * (4096 - len(code)))
    rom[0xFFC:0x1000] = bytes([0x00, 0xF0, 0x00, 0xF0])        # RESET / IRQ vectors -> $F000
    return bytes(rom)


def nes() -> bytes:
    """iNES NROM-128 (16 KB PRG + 8 KB CHR): waits for vblank and cycles the backdrop colour."""
    header = b"NES\x1a" + bytes([1, 1, 0, 0]) + bytes(8)
    code = bytes([
        0x78, 0xD8, 0xA2, 0xFF, 0x9A,                  # C000 sei cld ldx #$ff txs
        0xA9, 0x00, 0x8D, 0x00, 0x20, 0x8D, 0x01, 0x20,  # C005 lda #0 sta $2000 sta $2001
        0x2C, 0x02, 0x20, 0x10, 0xFB,                  # C00D vw: bit $2002 / bpl vw
        0x2C, 0x02, 0x20, 0x10, 0xFB,                  # C012 loop: bit $2002 / bpl loop
        0xA9, 0x3F, 0x8D, 0x06, 0x20, 0xA9, 0x00, 0x8D, 0x06, 0x20,   # C017 PPUADDR = $3F00
        0xE6, 0x00, 0xA5, 0x00, 0x4A, 0x4A, 0x4A, 0x29, 0x3F,         # C021 inc $00 / lda $00 / lsr x3 / and #$3f
        0x8D, 0x07, 0x20,                              # C02A sta $2007
        0xA9, 0x00, 0x8D, 0x06, 0x20, 0x8D, 0x06, 0x20,  # C02D PPUADDR = 0
        0x4C, 0x12, 0xC0,                              # C035 jmp loop
        0x40,                                          # C038 nmi/irq: rti
    ])
    prg = bytearray(code + b"\xEA" * (0x4000 - len(code)))
    prg[0x3FFA:0x4000] = bytes([0x38, 0xC0, 0x00, 0xC0, 0x38, 0xC0])
    return header + bytes(prg) + bytes(0x2000)


def gameboy() -> bytes:
    """32 KB ROM-only cartridge: changes the background palette in a loop (no Nintendo logo - emulators
    started without a boot ROM do not check it)."""
    rom = bytearray(0x8000)
    rom[0x100:0x104] = bytes([0x00, 0xC3, 0x50, 0x01])          # nop / jp $0150
    rom[0x134:0x13A] = b"RADIDE"
    rom[0x147], rom[0x148], rom[0x149], rom[0x14A] = 0, 0, 0, 1
    x = 0
    for i in range(0x134, 0x14D):
        x = (x - rom[i] - 1) & 0xFF
    rom[0x14D] = x
    rom[0x150:0x159] = bytes([0xF3, 0x31, 0xFE, 0xFF,          # di / ld sp,$fffe
                              0x3C, 0xE0, 0x47, 0x18, 0xFB])   # loop: inc a / ldh ($47),a / jr loop
    return bytes(rom)


GBA_LOOP = 0x080000D0


def gba() -> bytes:
    """Game Boy Advance ROM: sets mode 3 and spins at 0x080000D0 (a breakpoint target for the GDB test)."""
    rom = bytearray(0x200)
    rom[0:4] = (0xEA00002E).to_bytes(4, "little")              # b 0x080000C0
    rom[0xA0:0xAC] = b"RADIDE TEST\x00"
    rom[0xAC:0xB0] = b"RADE"
    rom[0xB0:0xB2] = b"00"
    rom[0xB2] = 0x96
    rom[0xBD] = (-(sum(rom[0xA0:0xBD]) + 0x19)) & 0xFF
    words = [0xE3A00301,     # C0 mov r0, #0x04000000
             0xE3A01B01,     # C4 mov r1, #0x400
             0xE2811003,     # C8 add r1, r1, #3
             0xE1C010B0,     # CC strh r1, [r0]
             0xE2822001,     # D0 loop: add r2, r2, #1
             0xEAFFFFFD]     # D4 b loop
    for i, w in enumerate(words):
        rom[0xC0 + 4 * i:0xC4 + 4 * i] = w.to_bytes(4, "little")
    return bytes(rom)


C64_LOOP = 0x080D


def c64() -> bytes:
    """C64 .prg: BASIC line 10 SYS 2061, then INC $D020 / JMP loop (border flashes)."""
    basic = bytes([0x0B, 0x08, 0x0A, 0x00, 0x9E, 0x32, 0x30, 0x36, 0x31, 0x00, 0x00, 0x00])
    code = bytes([0xEE, 0x20, 0xD0, 0x4C, 0x0D, 0x08])
    return bytes([0x01, 0x08]) + basic + code


def c64_labels() -> str:
    return "al C:080d .loop\nal C:0801 .basic\n"


def atari8() -> bytes:
    """Atari 8-bit .xex: INX / STX COLBK / JMP loop, RUNAD = $2000."""
    code = bytes([0xE8, 0x8E, 0x1A, 0xD0, 0x4C, 0x00, 0x20])
    seg = b"\xff\xff" + (0x2000).to_bytes(2, "little") + (0x2000 + len(code) - 1).to_bytes(2, "little") + code
    return seg + bytes([0xE0, 0x02, 0xE1, 0x02, 0x00, 0x20])


DOS_TEXT = "RADIDE DOS OK"


def dos_com() -> bytes:
    """HELLO.COM: prints DOS_TEXT with INT 21h / AH=09h and exits (hand-assembled 8086)."""
    msg = (DOS_TEXT + "\r\n$").encode("ascii")
    code = bytes([0xB4, 0x09, 0xBA, 0x0C, 0x01, 0xCD, 0x21, 0xB8, 0x00, 0x4C, 0xCD, 0x21])
    return code + msg


DOS_ASM = f"""; HELLO.ASM - prints a line and exits (NASM: nasm -f bin -o HELLO.COM HELLO.ASM)
        org 100h
        mov ah, 09h
        mov dx, msg
        int 21h
        mov ax, 4C00h
        int 21h
msg     db '{DOS_TEXT}', 13, 10, '$'
"""


def write_all(out) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = {"a2600": ("test.a26", atari2600()), "nes": ("test.nes", nes()), "gb": ("test.gb", gameboy()),
             "gba": ("test.gba", gba()), "c64": ("test.prg", c64()), "a8": ("test.xex", atari8()),
             "dos": ("HELLO.COM", dos_com())}
    paths = {}
    for sysid, (name, data) in files.items():
        (out / name).write_bytes(data)
        paths[sysid] = str(out / name)
    (out / "test.lbl").write_text(c64_labels(), encoding="ascii")
    (out / "HELLO.ASM").write_text(DOS_ASM, encoding="ascii")
    return paths


if __name__ == "__main__":
    for k, v in write_all(sys.argv[1] if len(sys.argv) > 1 else "homebrew_out").items():
        print(k, v)
