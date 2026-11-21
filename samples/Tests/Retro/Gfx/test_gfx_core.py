"""Unit tests of the retro graphics / text core (no Qt): tile codecs, PNG round trip, Atari 2600 playfield bit
order and players, tile maps, .tbl tables, script dump / insert with pointers, Arabic shaping.

Run:  .venv\\Scripts\\python.exe samples\\Tests\\Retro\\Gfx\\test_gfx_core.py
All data is synthetic (generated here)."""
from __future__ import annotations

import dataclasses
import os
import random
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.retro.gfx import arabic, atari2600, palettes, pngio  # noqa: E402
from radide.retro.gfx.codecs import FORMATS, get_format  # noqa: E402
from radide.retro.gfx.script import PointerSpec, Script, dump_pointers, dump_ranges, insert  # noqa: E402
from radide.retro.gfx.textable import TextTable, ascii_table  # noqa: E402
from radide.retro.gfx.tilemap import TileMap  # noqa: E402
from radide.retro.gfx.tilesheet import (ByteHistory, TileSheet, flip_h, flood_fill, ines_chr_offset,  # noqa: E402
                                        line_points, rotate_ccw, rotate_cw)

RESULTS: list[tuple[str, bool]] = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"), flush=True)


rnd = random.Random(1977)

# ------------------------------------------------------------------ codecs: random round trips per format
for key, f in FORMATS.items():
    h = 12 if f.var_height else None
    n = f.data_len(h)
    ok = True
    for _ in range(20):
        data = bytes(rnd.randrange(256) for _ in range(n))
        if key in ("c64spr", "c64sprmc"):
            pass
        px = f.decode(data, h)
        ok &= len(px) == f.width * f.tile_height(h) and max(px) < f.colors
        ok &= f.encode(px, h) == data
        px2 = [rnd.randrange(f.colors) for _ in range(f.width * f.tile_height(h))]
        ok &= f.decode(f.encode(px2, h), h) == px2
    check(f"codec {key}: bytes -> pixels -> bytes and pixels -> bytes -> pixels", ok)

# known layouts
nes = get_format("nes")
check("NES planar: plane 0 = bit 0, plane 1 = bit 1",
      nes.decode(bytes([0x80] + [0] * 7 + [0x80] + [0] * 7)[:16])[0] == 3 and
      nes.decode(bytes([0x00] * 8 + [0x40] + [0] * 7))[1] == 2)
gb = get_format("gb")
check("GB 2bpp: low byte then high byte per row", gb.decode(bytes([0x80, 0x00] + [0] * 14))[0] == 1 and
      gb.decode(bytes([0x00, 0x80] + [0] * 14))[0] == 2)
s4 = get_format("snes4")
check("SNES 4bpp: planes 2+3 in the second 16 bytes", s4.decode(bytes(16) + bytes([0x80, 0x80]) + bytes(14))[0] == 12)
gen = get_format("genesis")
check("Genesis 4bpp: high nibble is the left pixel", gen.decode(bytes([0x12]) + bytes(31))[:2] == [1, 2])
gba = get_format("gba4")
check("GBA 4bpp: low nibble is the left pixel", gba.decode(bytes([0x12]) + bytes(31))[:2] == [2, 1])
mc = get_format("c64mc")
check("C64 multicolour: 2-bit pairs, MSB first, double-wide", mc.decode(bytes([0b11100100]) + bytes(7))[:4] == [3, 2, 1, 0]
      and mc.aspect == 2)
spr = get_format("c64spr")
check("C64 sprite: 24x21 = 63 data bytes in a 64-byte block", spr.data_len() == 63 and spr.stride == 64)
a26 = get_format("a2600")
check("2600 player: variable height, one byte per line", a26.size(20) == 20 and a26.decode(bytes([0x81]), 1) ==
      [1, 0, 0, 0, 0, 0, 0, 1])

# ------------------------------------------------------------------ tile sheet, padding and undo
data = bytearray(rnd.randrange(256) for _ in range(64 * 3))
sheet = TileSheet(bytearray(data), get_format("c64spr"), cols=3, rows=1)
t = sheet.get_tile(1)
t2 = flip_h(t)
ch = sheet.set_tile(1, t2)
check("C64 sprite write keeps the 64th padding byte", sheet.data[127] == data[127] and ch is not None and
      len(ch[2]) == 63)
hist = ByteHistory()
hist.push([ch])
hist.undo(sheet.data)
check("undo restores the bytes", sheet.data == data)
hist.redo(sheet.data)
check("redo re-applies", sheet.get_tile(1) == t2 and hist.modified)
s2 = TileSheet(bytearray(40), get_format("a2600"), tile_h=10, bottom_up=True, cols=4, rows=1)
blk = [[1 if x == y % 8 else 0 for x in range(8)] for y in range(10)]
s2.set_tile(0, blk)
check("2600 upside-down storage: first byte is the bottom line", s2.data[0] == 0b01000000 and s2.get_tile(0) == blk)
big = TileSheet(bytearray(16 * 4), get_format("nes"), cols=2, rows=2)
b = big.get_block(0, 0, 2, 2)
b[0][0] = 3
b[15][15] = 2
big.set_block(0, 0, b)
check("block of 2x2 tiles round trip", big.get_block(0, 0, 2, 2) == b)
check("past the end is -1 (not editable)", TileSheet(bytearray(16), get_format("nes"), cols=2, rows=1)
      .get_block(0, 0, 2, 1)[0][8] == -1)
sq = [[1, 2], [3, 4]]
check("rotate right / left", rotate_cw(sq) == [[3, 1], [4, 2]] and rotate_ccw(sq) == [[2, 4], [1, 3]])
check("flood fill", flood_fill([[0, 0, 1], [0, 1, 1]], 0, 0, 2) == [[2, 2, 1], [2, 1, 1]])
check("bresenham line", line_points(0, 0, 3, 1) in ([(0, 0), (1, 0), (2, 1), (3, 1)], [(0, 0), (1, 0), (2, 0), (3, 1)]))
ines = bytearray(b"NES\x1a" + bytes([2, 1, 0, 0]) + bytes(8)) + bytes(32768 + 8192)
check("iNES: CHR-ROM offset = 16 + 2 * 16 KB", ines_chr_offset(ines) == 16 + 32768)

# ------------------------------------------------------------------ PNG export / import (quantise)
tmp = tempfile.mkdtemp(prefix="radide-gfx-")
colors = [palettes.palette("nes")[i] for i in palettes.default_slots("nes", 4)]
blk = [[(x + y) % 4 for x in range(16)] for y in range(16)]
p = pngio.export_png(os.path.join(tmp, "t.png"), blk, colors)
check("PNG export -> import is identical", pngio.import_png(p, colors, 16, 16) == blk)
p4 = pngio.export_png(os.path.join(tmp, "t4.png"), blk, colors, scale=4)
check("PNG at 4x is scaled back", pngio.import_png(p4, colors, 16, 16) == blk)
from PIL import Image  # noqa: E402
img = Image.new("RGB", (8, 8), (250, 250, 250))
img.putpixel((0, 0), (10, 5, 0))
img.putpixel((1, 0), (200, 40, 40))
q = pngio.image_to_block(img, colors, 8, 8)
check("PNG import quantises to the nearest slot", q[0][0] == 0 and q[1][1] == 3 and q[0][1] == 1, q[0][:3])
mcblk = [[x % 4 for x in range(4)] for _ in range(8)]
pm = pngio.export_png(os.path.join(tmp, "mc.png"), mcblk, palettes.C64[:4], aspect=2)
check("double-wide pixels (C64 multicolour) round trip", Image.open(pm).size == (8, 8) and
      pngio.import_png(pm, palettes.C64[:4], 4, 8, aspect=2) == mcblk)

# ------------------------------------------------------------------ Atari 2600 playfield bit order
check("PF0 bit 4 is the leftmost block", atari2600.bytes_to_half(0x10, 0, 0)[0] == 1)
check("PF0 bit 7 is block 3", atari2600.bytes_to_half(0x80, 0, 0)[3] == 1)
check("PF0 low nibble is not shown", sum(atari2600.bytes_to_half(0x0F, 0, 0)) == 0)
check("PF1 bit 7 is block 4 (left to right D7..D0)", atari2600.bytes_to_half(0, 0x80, 0)[4] == 1 and
      atari2600.bytes_to_half(0, 0x01, 0)[11] == 1)
check("PF2 bit 0 is block 12 (left to right D0..D7)", atari2600.bytes_to_half(0, 0, 0x01)[12] == 1 and
      atari2600.bytes_to_half(0, 0, 0x80)[19] == 1)
ok = True
for _ in range(200):
    v = (rnd.randrange(16) << 4, rnd.randrange(256), rnd.randrange(256))
    ok &= atari2600.half_to_bytes(atari2600.bytes_to_half(*v)) == v
check("PF bytes -> 20 bits -> bytes", ok)
left = [1] + [0] * 19
check("repeat vs reflect right half", atari2600.full_line(left)[20] == 1 and atari2600.full_line(left, reflect=True)[39] == 1)
pf = atari2600.Playfield(4, reflect=True)
pf.set(0, 0, 1)
pf.set(39, 1, 1)                       # right half in reflect mode edits the mirrored left bit
check("reflected playfield: drawing on the right edits the left half", pf.rows[1][0] == 1 and pf.get(39, 0) == 1)
t = pf.tables()
check("tables PF0/PF1/PF2", t["PF0"][:2] == [0x10, 0x10] and t["PF1"] == [0] * 4)
rom = bytearray(range(32))
pf2 = atari2600.Playfield(4, asymmetric=True)
pf2.set(25, 2, 1)
pf2.to_binary(rom, 4)
back = atari2600.Playfield.from_binary(rom, 4, 4, asymmetric=True)
check("asymmetric write to ROM -> read back", back.rows == pf2.rows, back.rows)
check("PF0 low nibble preserved in the ROM", rom[4] & 0x0F == 4 & 0x0F)
inter = bytearray(12)
pf.to_binary(inter, 0, "interleaved")
check("interleaved layout PF0,PF1,PF2 per row", inter[0] == 0x10 and inter[3] == 0x10)
asm = pf.export_asm("Level", "dasm")
check("DASM export uses %binary .byte", "Level_PF0:" in asm and ".byte %00010000" in asm)
check("player reflect", atari2600.reflect_byte(0b10000001) == 0b10000001 and atari2600.reflect_byte(0b11000000) == 3)
check("NUSIZ 1: two copies 16 clocks apart", atari2600.player_scanline(0x80, 1)[0] == 1 and
      atari2600.player_scanline(0x80, 1)[16] == 1)
check("NUSIZ 7: quad size", atari2600.player_scanline(0x80, 7)[:5] == [1, 1, 1, 1, 0])

# ------------------------------------------------------------------ tile maps
m = TileMap.new("nes")
m.set(0, 0, 5, 1)
m.set(2, 0, 6, 2)
m.set(0, 2, 7, 3)
m.set(2, 2, 8, 0)
m.set(4, 0, 9, 3)
attr = m.attribute_table()
check("NES attribute byte quadrants", attr[0] == (1 | 2 << 2 | 3 << 4 | 0 << 6) and attr[1] == 3)
blob = m.to_bytes()
m2 = TileMap.from_bytes(blob, "nes")
check("nametable + attributes = 1024 bytes and round trip", len(blob) == 1024 and m2.cells == m.cells and
      m2.attribute_table() == attr)
defs, mmap = m.build_metatiles()
check("metatile compression", len(mmap) == 16 * 15 and defs[mmap[0]] == [5, 0, 0, 0])
check("asm export", "Map_Attr:" in m.export_asm("Map", "ca65") and "db " in m.export_asm("Map", "rgbds"))
check("C export", "const unsigned char map[960]" in m.export_c("map"))
mp = os.path.join(tmp, "m.rtmap")
m.metatiles = [[1, 2, 3, 4]]
m.save(mp)
check(".rtmap save / load", TileMap.load(mp).cells == m.cells and TileMap.load(mp).metatiles == [[1, 2, 3, 4]])

# ------------------------------------------------------------------ text tables
tbl = TextTable.parse("# test\n41=A\n42=B\n4142=AB!\n20= \n/FF=<end>\n*FE\n$80=<name>\n")
check("tbl parse: entries / end / break", tbl.entries[b"AB"] == "AB!" and tbl.ends[b"\xff"] == "<end>" and
      b"\xfe" in tbl.breaks and not tbl.errors, tbl.errors)
txt, n, ended = tbl.decode(bytes([0x41, 0x42, 0x20, 0xFE, 0x42, 0x13, 0xFF, 0x41]))
check("decode: longest match, newline, unknown byte, end code", txt == "AB! \nB<$13><end>" and n == 7 and ended, txt)
enc, prob = tbl.encode("AB! \nB<$13><end>")
check("encode round trip", enc == bytes([0x41, 0x42, 0x20, 0xFE, 0x42, 0x13, 0xFF]) and not prob, enc.hex())
check("encode reports missing characters", tbl.encode("AZ")[1] != [])
check("tbl write / parse round trip", TextTable.parse(tbl.dumps()).entries == tbl.entries)
check("bad lines reported", TextTable.parse("4G=x\n41\n").errors.__len__() == 2)

# ------------------------------------------------------------------ script dump / insert with pointers (synthetic ROM)
asc = ascii_table()
rom = bytearray(0x400)
texts = [b"HELLO\x00", b"WORLD\x00", b"HELLO\x00", b"BYE\x00"]
base, add = 0x8000, 0x10                          # NES-like: pointer $8000 = file offset $10
pos = 0x100
for i, s in enumerate(texts):
    rom[pos:pos + len(s)] = s
    ptr = pos - add + base
    rom[0x40 + i * 2:0x42 + i * 2] = ptr.to_bytes(2, "little")
    pos += len(s)
spec = PointerSpec(0x40, 4, 2, "little", base, add)
sc = dump_pointers(bytes(rom), asc, spec)
check("dump by pointers", [e.original for e in sc.entries] == ["HELLO<end>", "WORLD<end>", "HELLO<end>", "BYE<end>"]
      and sc.entries[1].offset == 0x106, [e.original for e in sc.entries])
sc.entries[1].translation = "EARTH<end>"
r = insert(bytes(rom), asc, sc, "inplace")
check("insert in place (same length)", r.ok and bytes(r.rom[0x106:0x10C]) == b"EARTH\x00")
sc.entries[0].translation = "GOOD MORNING<end>"
r = insert(bytes(rom), asc, sc, "inplace")
check("in place refuses a longer string and writes nothing", not r.ok and r.rom == rom and "too many" in r.errors[0])
r = insert(bytes(rom), asc, sc, "repack", region=(0x100, 0x140))
sc2 = dump_pointers(bytes(r.rom), asc, spec)
check("repack recalculates every pointer", r.ok and [e.original for e in sc2.entries] ==
      ["GOOD MORNING<end>", "EARTH<end>", "HELLO<end>", "BYE<end>"], r.report())
r = insert(bytes(rom), asc, sc, "repack", region=(0x100, 0x110))
check("repack overflow is reported, ROM unchanged", not r.ok and r.rom == rom and "too many" in r.errors[0])
sc.entries[0].translation = "GOOD MORNING"         # translator forgot <end>
r = insert(bytes(rom), asc, sc, "repack", region=(0x100, 0x140))
check("missing end code is added back", r.ok and dump_pointers(bytes(r.rom), asc, spec).entries[0].original
      == "GOOD MORNING<end>")
dup = Script(entries=[dataclasses.replace(e) for e in sc.entries], pointers=spec)
for e in dup.entries:
    e.translation = ""
r = insert(bytes(rom), asc, dup, "repack", region=(0x100, 0x140))
ptrs = [int.from_bytes(r.rom[0x40 + i * 2:0x42 + i * 2], "little") for i in range(4)]
check("identical strings share one copy", r.ok and ptrs[0] == ptrs[2], ptrs)
rng = dump_ranges(bytes(rom), asc, [(0x100, 0x112)])
check("dump by ranges splits at end codes", [e.original for e in rng.entries][:3] == ["HELLO<end>", "WORLD<end>",
                                                                                      "HELLO<end>"])
csv_text = sc.to_csv()
sc3 = dump_pointers(bytes(rom), asc, spec)
check("sheet CSV round trip", sc3.load_csv(csv_text) == 4 and sc3.entries[1].translation == "EARTH<end>")
check("sheet from CSV alone", Script.from_csv(csv_text).entries[1].offset == sc.entries[1].offset)

# ------------------------------------------------------------------ Arabic tables and shaping
ar = arabic.arabic_table(0x80)
check("Arabic table: every letter form has a code, no errors", not ar.errors and len(ar.entries) >= 125, ar.errors)
s = arabic.shape("سلام")
check("shaping: initial / medial / lam-alef / final",
      s == "ﺳﻼﻡ" or s == "ﺳﻼﻡ", [hex(ord(c)) for c in s])
check("shaping: isolated letter", arabic.shape("ب") == "ﺏ")
check("visual order keeps digits and control codes", arabic.prepare("بك 12<end>") ==
      "12 " + arabic.shape("بك")[::-1] + "<end>", arabic.prepare("بك 12<end>"))
rom_ar = bytearray(0x200)
rom_ar[0x40:0x42] = (0x100).to_bytes(2, "little")
rom_ar[0x100:0x107] = b"HELLO!\xff"
tab = arabic.arabic_table(0x80, base=TextTable.parse("48=H\n45=E\n4C=L\n4F=O\n21=!\n/FF=<end>\n"))
sca = dump_pointers(bytes(rom_ar), tab, PointerSpec(0x40, 1, 2))
sca.entries[0].translation = "مرحبا!<end>"
ra = insert(bytes(rom_ar), tab, sca, "repack", region=(0x100, 0x120),
            prepare=lambda t: arabic.prepare(t, True, True))
back = dump_pointers(bytes(ra.rom), tab, PointerSpec(0x40, 1, 2)).entries[0].original
check("Arabic insert: shaped + visual order, decodes to presentation forms", ra.ok and
      back == arabic.prepare("مرحبا!<end>"), (ra.report(), back))
check("Arabic bytes are in the custom range", all(b >= 0x80 or b in (0x21, 0xFF) for b in ra.rom[0x100:0x107]))

# ------------------------------------------------------------------ palettes
check("palette sizes", len(palettes.palette("a2600ntsc")) == 128 and len(palettes.palette("nes")) == 64 and
      len(palettes.palette("c64")) == 16 and len(palettes.palette("gb")) == 4)
check("2600 colour byte", palettes.a2600_color_byte(0x23) == 0x46)
check("default slots per format", palettes.default_slots("a2600ntsc", 2) == [0, 7] and
      len(palettes.default_slots("grey16", 16)) == 16)

ok = sum(1 for _, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
