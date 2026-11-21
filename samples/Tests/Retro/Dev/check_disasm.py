"""Retro dev slice - pure tests (no Qt): decoders vs hand-assembled bytes, error parsing, TAP writer, and
round trips "disassemble -> reassemble with the real assembler -> byte-identical" on synthetic ROMs written for
this test (every byte below is our own; no commercial ROM is used).

    python samples/Tests/Retro/Dev/check_disasm.py           (downloads DASM / cc65 / RGBDS / sjasmplus once)
    python samples/Tests/Retro/Dev/check_disasm.py --offline  (round trips SKIP when a toolchain is missing)
"""
from __future__ import annotations

import random
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.retro.cpu import m6502, sm83, z80  # noqa: E402
from radide.retro.dev import errors, tapfile, toolchain  # noqa: E402

RESULTS: list[tuple[str, str]] = []
OFFLINE = "--offline" in sys.argv
WORK = Path(tempfile.mkdtemp(prefix="radide-retro-dev-"))


def check(name, cond, detail=""):
    RESULTS.append((name, "PASS" if cond else "FAIL"))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def skip(name, why):
    RESULTS.append((name, "SKIP"))
    print(f"SKIP {name}  ({why})", flush=True)


def text(mod, bs, undoc=True, addr=0x8000):
    ins = mod.decode(bytes(bs), 0, addr, undoc)
    if ins is None:
        return None
    t = ins.operand.replace("{t}", f"${ins.target:04X}" if ins.target is not None else "")
    return f"{ins.mnemonic} {t}".strip(), ins.size, ins.undocumented


# ------------------------------------------------------------------------------------------- decoders
def test_decoders():
    cases_6502 = [
        ([0xA9, 0x10], "lda #$10", 2), ([0xAD, 0x80, 0x00], "lda $0080", 3), ([0xA5, 0x80], "lda $0080", 2),
        ([0x9D, 0x00, 0x02], "sta $0200,x", 3), ([0xB1, 0x10], "lda ($0010),y", 2), ([0xA1, 0x10], "lda ($0010,x)", 2),
        ([0x6C, 0xFC, 0xFF], "jmp ($FFFC)", 3), ([0xD0, 0xFE], "bne $8000", 2), ([0x10, 0x02], "bpl $8004", 2),
        ([0x0A], "asl", 1), ([0x96, 0x10], "stx $0010,y", 2), ([0x20, 0xD2, 0xFF], "jsr $FFD2", 3),
        ([0x00], "brk", 1), ([0x60], "rts", 1), ([0x40], "rti", 1),
    ]
    for bs, want, size in cases_6502:
        got = text(m6502, bs)
        check(f"6502 decode {bytes(bs).hex()} = {want}", got and got[0] == want and got[1] == size, got)
    for bs, want in (([0x07, 0x80], "slo $0080"), ([0xA7, 0x10], "lax $0010"), ([0xCB, 0x05], "axs #$05"),
                     ([0x02], "jam"), ([0xEB, 0x01], "sbc #$01"), ([0x1A], "nop")):
        got = text(m6502, bs)
        check(f"6502 undocumented {bytes(bs).hex()} = {want}", got and got[0] == want and got[2], got)
        check(f"6502 undocumented {bytes(bs).hex()} refused when not asked", text(m6502, bs, undoc=False) is None)
    check("6502 table has 256 opcodes", len(m6502.OPCODES) == 256)
    check("6502 cycles lda abs,x = 4+", m6502.OPCODES[0xBD].cycles == "4+")
    check("6502 cycles sta abs,x = 5", m6502.OPCODES[0x9D].cycles == "5")
    check("6502 cycles inc abs,x = 7", m6502.OPCODES[0xFE].cycles == "7")

    cases_gb = [
        ([0x00], "nop"), ([0x3E, 0x12], "ld a, $12"), ([0xE0, 0x40], "ldh [$FF40], a"), ([0xF0, 0x44], "ldh a, [$FF44]"),
        ([0xFA, 0x44, 0xFF], "ld a, [$FF44]"), ([0xEA, 0x00, 0xC0], "ld [$C000], a"), ([0x22], "ld [hl+], a"),
        ([0x3A], "ld a, [hl-]"), ([0xF8, 0xFE], "ld hl, sp - $02"), ([0xE8, 0x05], "add sp, $05"),
        ([0xE9], "jp hl"), ([0xCB, 0x7C], "bit 7, h"), ([0xCB, 0x37], "swap a"), ([0xCB, 0x86], "res 0, [hl]"),
        ([0x18, 0xFE], "jr $8000"), ([0x20, 0x00], "jr nz, $8002"), ([0xC4, 0x00, 0x90], "call nz, $9000"),
        ([0xD9], "reti"), ([0xFF], "rst $38"), ([0x10, 0x00], "stop"), ([0x08, 0x00, 0xC0], "ld [$C000], sp"),
        ([0x96], "sub a, [hl]"), ([0xFE, 0x90], "cp a, $90"), ([0x76], "halt"),
    ]
    for bs, want in cases_gb:
        got = text(sm83, bs)
        check(f"SM83 decode {bytes(bs).hex()} = {want}", got and got[0] == want and got[1] == len(bs), got)
    for bad in (0xD3, 0xDB, 0xDD, 0xE3, 0xE4, 0xEB, 0xEC, 0xED, 0xF4, 0xFC, 0xFD):
        check(f"SM83 unused opcode {bad:02X} = data", sm83.decode(bytes([bad, 0, 0]), 0, 0) is None)
    check("SM83 stop with a non-zero byte = data", sm83.decode(bytes([0x10, 0x01]), 0, 0) is None)

    cases_z80 = [
        ([0x3E, 0x05], "ld a,$05", False), ([0x21, 0x00, 0x40], "ld hl,$4000", False),
        ([0xDD, 0x7E, 0x05], "ld a,(ix+$05)", False), ([0xFD, 0x36, 0xFE, 0x42], "ld (iy-$02),$42", False),
        ([0xDD, 0xE9], "jp (ix)", False), ([0xED, 0xB0], "ldir", False), ([0xED, 0x4B, 0x00, 0x50], "ld bc,($5000)", False),
        ([0x08], "ex af,af'", False), ([0xD3, 0xFE], "out ($FE),a", False), ([0xED, 0x78], "in a,(c)", False),
        ([0x10, 0xFE], "djnz $8000", False), ([0xCB, 0x46], "bit 0,(hl)", False), ([0xFD, 0xCB, 0x03, 0x46], "bit 0,(iy+$03)", False),
        ([0xED, 0x56], "im 1", False), ([0xE3], "ex (sp),hl", False), ([0xC7], "rst $00", False),
        ([0xDD, 0x26, 0x07], "ld ixh,$07", True), ([0xCB, 0x37], "sll a", True), ([0xED, 0x63, 0x00, 0x50], "ld ($5000),hl", True),
        ([0xFD, 0xCB, 0x03, 0x07], "rlc (iy+$03),a", True), ([0xED, 0x70], "in (c)", True), ([0xED, 0x71], "out (c),0", True),
        ([0xED, 0x4E], "im 0", True), ([0xDD, 0x00], "nop", True),
    ]
    for bs, want, und in cases_z80:
        got = text(z80, bs)
        check(f"Z80 decode {bytes(bs).hex()} = {want}", got and got[0] == want and got[2] == und, got)
    check("Z80 ld a,(ix+d) = 19 T-states", z80.decode(bytes([0xDD, 0x7E, 0x05]), 0, 0).cycles == "19")
    check("Z80 undocumented refused when not asked", z80.decode(bytes([0xDD, 0x26, 0x07]), 0, 0, False) is None)


# ------------------------------------------------------------------------------------------- errors
def test_errors():
    out = """e.asm (5): error: Unknown Mnemonic 'foo'.
--- Unresolved Symbol List
undefinedlabel           0000 ????         (R )
--- 1 Unresolved Symbol
main.s:3: Error: Symbol ‘nowhere’ is undefined
nes.cfg:3: Warning: Segment 'PRG' overflows memory area 'PRG' by 1 byte
ld65: Error: Cannot generate most of the files due to memory area overflow
main.c(7): Error: ';' expected
error: Undefined symbol `nowhere`
    at game.asm(12)
warning: Treating multi-unit string as a number [-Wnumeric-string]
    at game.asm(4) <- gb.inc(9)
z.asm(2): error: Label not found: q
z.asm(6): warning: [SAVETAP] Tape file will not contain data
Error - File main.a, line 9 (Zone <untitled>): Value not defined (foo).
"""
    rows = errors.parse(out)
    want = [("Error", "e.asm", 5), ("Error", "", 0), ("Error", "main.s", 3), ("Warning", "nes.cfg", 3),
            ("Error", "", 0), ("Error", "main.c", 7), ("Error", "game.asm", 12), ("Warning", "game.asm", 4),
            ("Error", "z.asm", 2), ("Warning", "z.asm", 6), ("Error", "main.a", 9)]
    got = [(r.severity, r.file, r.line) for r in rows]
    check("error parsing: DASM / ca65 / ld65 / cc65 / RGBDS / sjasmplus / ACME rows", got == want, got)
    check("error parsing keeps the messages", rows[0].message.startswith("Unknown Mnemonic") and
          "nowhere" in rows[6].message)


# ------------------------------------------------------------------------------------------- tap
def test_tap():
    code = bytes(range(40))
    tap = tapfile.make_tap(code, 32768, 32770, "demo")
    from radide.retro.cpu.romfmt import _usr_address, tap_blocks
    blocks = tap_blocks(tap)
    check("TAP has 4 blocks (BASIC header + data, CODE header + data)", len(blocks) == 4, len(blocks))
    ok = all((lambda b: __import__("functools").reduce(lambda x, y: x ^ y, b[:-1], 0) == b[-1])(b) for b in blocks)
    check("TAP block checksums", ok)
    check("TAP CODE header: start 32768, length 40", blocks[2][1] == 3 and int.from_bytes(blocks[2][14:16], "little")
          == 32768 and int.from_bytes(blocks[2][12:14], "little") == 40)
    check("TAP BASIC loader runs USR 32770", _usr_address(blocks[1][1:-1]) == 32770)
    check("TAP code bytes", blocks[3][1:-1] == code)


# ------------------------------------------------------------------------------------------- synthetic ROMs
def _rand(n, seed):
    r = random.Random(seed)
    return bytes(r.randrange(256) for _ in range(n))


def rom_2600_4k() -> bytes:
    rom = bytearray(_rand(4096, 26))
    code = [0x78, 0xD8, 0xA2, 0xFF, 0x9A,            # F000 sei / cld / ldx #$FF / txs
            0xAD, 0x80, 0x00,                          # F005 lda $0080   (absolute although < $100)
            0x8D, 0x02, 0x00,                          # F008 sta $0002   (absolute WSYNC)
            0x85, 0x02, 0xA5, 0x0C,                    # F00B sta WSYNC / lda INPT4
            0x20, 0x30, 0xF0,                          # F00F jsr $F030
            0x07, 0x80,                                # F012 slo $80     (undocumented)
            0xBD, 0x00, 0xF1,                          # F014 lda $F100,x (table)
            0x99, 0x80, 0x00,                          # F017 sta $0080,y (absolute,Y below $100)
            0x4C, 0x00, 0xF0]                          # F01A jmp $F000
    rom[0:len(code)] = bytes(code)
    sub = [0xA9, 0x01, 0x8D, 0x96, 0x02,              # F030 lda #1 / sta TIM64T
           0xAD, 0x84, 0x02, 0xD0, 0xFB, 0x60]         # F035 lda INTIM / bne F035 / rts
    rom[0x30:0x30 + len(sub)] = bytes(sub)
    rom[0x100:0x200] = bytes(range(256))
    rom[0xFFC:0x1000] = bytes([0x00, 0xF0, 0x30, 0xF0])
    return bytes(rom)


def rom_2600_2k() -> bytes:
    rom = bytearray(_rand(2048, 22))
    code = [0xA9, 0x84, 0x85, 0x09,                    # F800 lda #$84 / sta COLUBK
            0x4C, 0x07, 0x18,                          # F804 jmp $1807 (a mirror of $F807)
            0xE6, 0x80, 0x4C, 0x07, 0xF8]              # F807 inc $80 / jmp $F807
    rom[0:len(code)] = bytes(code)
    rom[0x7FC:0x800] = bytes([0x00, 0xF8, 0x00, 0xF8])
    return bytes(rom)


def rom_2600_f8() -> bytes:
    out = bytearray()
    for bank in range(2):
        b = bytearray(_rand(4096, 80 + bank))
        code = [0xAD, 0xF9 - bank, 0x1F,               # lda $1FF9 / $1FF8: switch bank
                0xA9, bank, 0x85, 0x09, 0x4C, 0x03, 0xF0]
        b[0:len(code)] = bytes(code)
        b[0xFFC:0x1000] = bytes([0x00, 0xF0, 0x00, 0xF0])
        out += b
    return bytes(out)


def rom_nes() -> bytes:
    hdr = b"NES\x1a" + bytes([1, 1, 0x01, 0]) + bytes(8)
    prg = bytearray(_rand(16384, 65))
    code = [0x78, 0xD8, 0xA2, 0xFF, 0x9A,             # C000
            0x2C, 0x02, 0x20, 0x10, 0xFB,              # C005 bit PPUSTATUS / bpl C005
            0xA9, 0x80, 0x8D, 0x00, 0x20,              # C00A lda #$80 / sta PPUCTRL
            0xAD, 0x12, 0x00,                          # C00F lda $0012 (absolute)
            0xB9, 0x00, 0xD0,                          # C012 lda $D000,y
            0x20, 0x40, 0xC0,                          # C015 jsr $C040
            0x4C, 0x15, 0xC0]                          # C018 jmp $C015
    prg[0:len(code)] = bytes(code)
    prg[0x40:0x47] = bytes([0xA9, 0x02, 0x8D, 0x14, 0x40, 0x60, 0x40])   # C040 lda #2 / sta OAMDMA / rts ; C046 rti
    prg[0x3FFA:0x4000] = bytes([0x46, 0xC0, 0x00, 0xC0, 0x46, 0xC0])
    return hdr + bytes(prg) + _rand(8192, 99)


def prg_c64() -> bytes:
    load = b"\x01\x08"
    basic = bytes([0x0B, 0x08, 0x0A, 0x00, 0x9E]) + b"2064" + bytes([0, 0, 0]) + bytes(3)   # 10 SYS 2064, padding
    code = bytes([0xA9, 0x01, 0x8D, 0x20, 0xD0,      # $0810 lda #1 / sta EXTCOL
                  0xA9, 0x41, 0x20, 0xD2, 0xFF,       # lda #'A' / jsr CHROUT
                  0xAD, 0x01, 0x00,                   # lda $0001 (absolute R6510)
                  0x60]) + _rand(40, 64)
    return load + basic + code


def rom_gb() -> bytes:
    rom = bytearray(_rand(32768, 0x6B))
    rom[0x40] = 0xD9                                    # VBlank: reti
    rom[0x100:0x104] = bytes([0x00, 0xC3, 0x50, 0x01])
    code = [0xF3, 0x31, 0xFE, 0xFF,                   # 0150 di / ld sp,$FFFE
            0xF0, 0x44, 0xFE, 0x90, 0x38, 0xFA,        # ldh a,[rLY] / cp $90 / jr c,-6
            0xFA, 0x44, 0xFF,                          # ld a,[$FF44]  (not ldh!)
            0xE0, 0x40, 0xE2, 0x22, 0x3A,              # ldh [rLCDC],a / ldh [c],a / ld [hl+],a / ld a,[hl-]
            0xF8, 0xFE, 0xE8, 0xFE, 0xE8, 0x05,        # ld hl,sp-2 / add sp,-2 / add sp,5
            0xCB, 0x7C, 0xCB, 0x37, 0xCB, 0xC6,        # bit 7,h / swap a / set 0,[hl]
            0x08, 0x00, 0xC0,                          # ld [$C000],sp
            0xCD, 0x80, 0x01,                          # call $0180
            0x10, 0x00,                                # stop
            0xC3, 0x50, 0x01]                          # jp $0150
    rom[0x150:0x150 + len(code)] = bytes(code)
    rom[0x180:0x186] = bytes([0x21, 0x00, 0x40, 0xE9, 0xD3, 0x10])   # ld hl,$4000 / jp hl / (data)
    return bytes(rom)


def tap_zx(undoc: bool) -> bytes:
    code = [0xF3, 0x31, 0x00, 0x00,                    # 8000 di / ld sp,$0000
            0xDD, 0x21, 0x00, 0x90, 0xDD, 0x7E, 0x05,  # ld ix,$9000 / ld a,(ix+5)
            0xFD, 0x36, 0xFE, 0x42, 0xED, 0xB0,        # ld (iy-2),$42 / ldir
            0xED, 0x4B, 0x00, 0x90, 0x08, 0xD3, 0xFE,  # ld bc,($9000) / ex af,af' / out ($FE),a
            0xCD, 0x6B, 0x0D, 0x10, 0xFE,              # call ROM_CLS / djnz $
            0x3A, 0x08, 0x5C,                          # ld a,(LAST_K)
            0xCB, 0x46, 0xFD, 0xCB, 0x03, 0x46]        # bit 0,(hl) / bit 0,(iy+3)
    if undoc:
        code += [0xDD, 0x26, 0x07, 0xCB, 0x37, 0xED, 0x63, 0x00, 0x90, 0xFD, 0xCB, 0x03, 0x07, 0xED, 0x70,
                 0xDD, 0x00, 0xED, 0x4E]
    code += [0xC9] + list(_rand(48, 0x80))
    return tapfile.make_tap(bytes(code), 0x8000, 0x8000, "synth")


def roundtrip(name, data: bytes, ext: str, needs: str, **kw):
    if not toolchain.find(needs) and (OFFLINE or not toolchain.ensure(needs, lambda t: None)):
        skip(f"round trip {name}", f"{needs} not available")
        return None
    from radide.retro.dev.fromrom import create_project
    rom = WORK / f"{name}{ext}"
    rom.write_bytes(data)
    folder = WORK / f"proj_{name}"
    shutil.rmtree(folder, ignore_errors=True)
    log: list[str] = []
    res = create_project(rom, folder, name, log=log.append, **kw)
    same = (res.identical or {}).get("same")
    check(f"round trip {name}: build OK", res.build_ok, "\n".join(log)[-1500:])
    check(f"round trip {name}: byte-identical", same, (res.identical or {}).get("reason"))
    return res


def test_roundtrips():
    r = roundtrip("a2600_4k", rom_2600_4k(), ".bin", "dasm")
    if r:
        src = (r.folder / r.main).read_text(encoding="utf-8")
        check("2600: zero-page address used as absolute is forced (lda.w)", "lda.w ram_80" in src, src[:600])
        check("2600: hardware names (WSYNC, INPT4, TIM64T, INTIM)", all(n in src for n in ("WSYNC", "INPT4", "TIM64T",
                                                                                            "INTIM")))
        check("2600: undocumented opcode not followed by default (slo is data)", "slo" not in src.split("Reset")[1][:200]
              or ".byte $07,$80" in src)
        check("2600: vectors written as .word labels", ".word Reset" in src and ".word IRQ" in src)
    if r:                                   # hints.json: code the tracer did not reach + a label + a comment
        import json
        from radide.retro.dev.fromrom import redisassemble
        h = json.loads((r.folder / "hints.json").read_text(encoding="utf-8"))
        h.update({"code": ["F014"], "labels": {"F100": "SineTable"}, "comments": {"F030": "wait for the timer"}})
        (r.folder / "hints.json").write_text(json.dumps(h), encoding="utf-8")
        r2 = redisassemble(r.folder, log=lambda _t: None)
        src = (r2.folder / r2.main).read_text(encoding="utf-8")
        check("2600 hints: code hint traced, label and comment used, still byte-identical",
              "lda SineTable,x" in src and "; wait for the timer" in src and (r2.identical or {}).get("same") and
              (r2.folder / (r2.main + ".bak")).is_file(), src[:1500])
    r = roundtrip("a2600_4k_undoc", rom_2600_4k(), ".bin", "dasm", undocumented=True)
    if r:
        src = (r.folder / r.main).read_text(encoding="utf-8")
        check("2600 undocumented: slo written as bytes with the mnemonic in a comment",
              ".byte $07,$80" in src and "slo ram_80 (undocumented)" in src, src[:1200])
        check("2600 undocumented: tracing continues after slo, data table labelled", "lda LF100,x" in src and
              "\nLF100" in src)
        check("2600 undocumented: absolute,Y below $100 forced", "sta.w ram_80,y" in src)
    r = roundtrip("a2600_2k", rom_2600_2k(), ".bin", "dasm")
    if r:
        src = (r.folder / r.main).read_text(encoding="utf-8")
        check("2600 2K: org $F800, mirror target kept as $1807", "org $F800" in src and "jmp $1807" in src)
    r = roundtrip("a2600_f8", rom_2600_f8(), ".bin", "dasm")
    if r:
        src = (r.folder / r.main).read_text(encoding="utf-8")
        check("2600 F8: two banks with rorg $F000", src.count("rorg $F000") == 2 and "B1_Reset" in src)
    r = roundtrip("nes_nrom128", rom_nes(), ".nes", "ca65")
    if r:
        src = (r.folder / r.main).read_text(encoding="utf-8")
        check("NES: PPU / APU names, absolute forced with a:", "PPUSTATUS" in src and "OAMDMA" in src and
              "lda a:$0012" in src, src[:1500])
        check("NES: CHR ROM written to chr.bin + .incbin", (r.folder / "chr.bin").stat().st_size == 8192 and
              '.incbin "chr.bin"' in src)
        check("NES: generated linker config", (r.folder / "nes.cfg").is_file())
    r = roundtrip("c64_prg", prg_c64(), ".prg", "ca65")
    if r:
        src = (r.folder / r.main).read_text(encoding="utf-8")
        check("C64: BASIC SYS entry found, VIC / KERNAL names", "Start:" in src and "EXTCOL" in src and
              "CHROUT" in src and "lda a:R6510" in src, src[:1500])
    r = roundtrip("gb_32k", rom_gb(), ".gb", "rgbasm")
    if r:
        src = (r.folder / r.main).read_text(encoding="utf-8")
        check("Game Boy: ldh vs ld [$FF44] kept apart", "ldh a, [rLY]" in src and "ld a, [rLY]" in src, src[:2000])
        check("Game Boy: banks as ROM0 / ROMX sections", 'ROM0[$0000]' in src and "ROMX[$4000], BANK[1]" in src)
    for undoc in (False, True):
        r = roundtrip(f"zx_tap{'_undoc' if undoc else ''}", tap_zx(undoc), ".tap", "sjasmplus", undocumented=undoc)
        if r:
            src = (r.folder / r.main).read_text(encoding="utf-8")
            check(f"ZX{' undocumented' if undoc else ''}: entry from the BASIC loader, ROM names", "Start:" in src and
                  "ROM_CLS" in src and "LAST_K" in src, src[:1500])
            if undoc:
                check("ZX: undocumented Z80 forms written as db", "db $DD,$26,$07" in src and "ld ixh,$07" in src)


def main() -> int:
    test_decoders()
    test_errors()
    test_tap()
    test_roundtrips()
    shutil.rmtree(WORK, ignore_errors=True)
    p = sum(r == "PASS" for _, r in RESULTS)
    f = [n for n, r in RESULTS if r == "FAIL"]
    s = sum(r == "SKIP" for _, r in RESULTS)
    print(f"{p}/{len(RESULTS)} passed, {s} skipped; FAILED: {f or 'none'}")
    return 1 if f else 0


if __name__ == "__main__":
    raise SystemExit(main())
