"""Tests of the retro game designers' core (no Qt): encodings, generators, real toolchain builds, headless
checks of the built programs and launching them in the emulators.

Run:  .venv\\Scripts\\python.exe samples\\Tests\\Retro\\DesignGames\\test_gamedesign_core.py [--no-emu]

* unit tests: Atari 2600 playfield encoding + kernel tables, NES attribute packing / name tables / CHR / sprites,
  Game Boy OAM / tile maps, mode 13h palette / RLE / sprite data, model save / load / snapshots.
* builds (skipped when the tool is not installed - Tools > Retro installs them): DASM, ca65 + ld65, RGBDS, NASM,
  FreeBASIC (DOS fbc inside DOSBox-X), OpenWatcom.
* the built programs are checked headless: the 2600 ROM in the 6502 / TIA probe (262 / 312 lines, every kernel
  line holds the design's values), the NES ROM in the NES probe (name / attribute tables, palettes, column
  streaming while scrolling), the Game Boy ROM's data + header, the .COM in RAD IDE's 8086 emulator and the
  FreeBASIC / OpenWatcom .EXE in DOSBox-X ("/SHOT" saves the screen; it must equal the design).
* emulator smoke test (skipped with --no-emu or when not installed): Stella, Mesen, mGBA and DOSBox-X start the
  built ROM / program and keep running for a few seconds; RAD IDE stops only the processes it started.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.retro.design.game import (Design, EXTS, SYSTEMS, atari2600 as A, gameboy as G, gen_dir,  # noqa: E402
                                      load, mode13h as M, nes as N, new_design)
from radide.retro.design.game.build import build, dosbox_shot  # noqa: E402
from radide.retro.design.game.sim6502 import CPU6502, NESProbe  # noqa: E402

RESULTS: list[tuple[str, bool]] = []
SKIPPED: list[str] = []
WORK = Path(tempfile.gettempdir()) / "radide-gamedesign-test"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
NO_EMU = "--no-emu" in sys.argv


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def skip(name, why):
    SKIPPED.append(name)
    print(f"SKIP {name}  ({why})", flush=True)


# ====================================================================== Atari 2600 encoding
from radide.retro.design.game.compat import half_to_bytes  # noqa: E402

check("2600 PF: leftmost bit -> PF0 bit 4", half_to_bytes([1] + [0] * 19) == (0x10, 0, 0))
check("2600 PF: bit 3 -> PF0 bit 7", half_to_bytes([0] * 3 + [1] + [0] * 16) == (0x80, 0, 0))
check("2600 PF: bit 4 -> PF1 bit 7 (PF1 is drawn MSB first)", half_to_bytes([0] * 4 + [1] + [0] * 15) == (0, 0x80, 0))
check("2600 PF: bit 11 -> PF1 bit 0", half_to_bytes([0] * 11 + [1] + [0] * 8) == (0, 0x01, 0))
check("2600 PF: bit 12 -> PF2 bit 0 (PF2 is drawn LSB first)", half_to_bytes([0] * 12 + [1] + [0] * 7) == (0, 0, 0x01))
check("2600 PF: bit 19 -> PF2 bit 7", half_to_bytes([0] * 19 + [1]) == (0, 0, 0x80))
check("2600 PF: all on", half_to_bytes([1] * 20) == (0xF0, 0xFF, 0xFF))
row = [1, 0, 0, 1] + [0] * 16
check("2600 reflect: right half mirrors", A.full_row(row, True)[20:] == row[::-1])
check("2600 repeat: right half copies", A.full_row(row, False)[20:] == row)
check("2600 edit index (reflect): screen column 39 -> bit 0", A.edit_index(39, True) == 0)
check("2600 edit index (repeat): screen column 20 -> bit 0", A.edit_index(20, False) == 0)
check("2600 colour byte = index << 1", A.color_byte(0x42) == 0x84)

d26 = new_design("a2600", "Castle")
pf = d26.layer("Playfield")
for x in range(20):
    pf.set(x, 50, 1 if x % 2 else 0)
t = A.kernel_tables(d26)
check("2600 kernel tables have one byte per line", all(len(t[k]) == 192 for k in ("BKT", "PF0T", "G0T", "ENT")))
check("2600 kernel PF tables encode line 50", (t["PF0T"][50], t["PF1T"][50], t["PF2T"][50]) ==
      half_to_bytes([1 if x % 2 else 0 for x in range(20)]))
p0 = d26.object("Player0")
rows = A._sprite_rows(d26, p0)
check("2600 player rows on its lines", [t["G0T"][p0["y"] + i] for i in range(len(rows))] == rows)
ctrl = A.ctrlpf(d26)
check("2600 CTRLPF reflect bit", ctrl & 1 == 1)
d26.settings["priority"] = True
d26.settings["ball_size"] = "4"
check("2600 CTRLPF priority + ball size 4", A.ctrlpf(d26) == 0x01 | 0x04 | 0x20)
d26.settings["priority"] = False
early = new_design("a2600", "Early")
early.object("Player0")["x"] = 8
te = A.kernel_tables(early)
y0 = early.object("Player0")["y"]
check("2600 object left of its write pixel is generated one line early", "player0" in te["early"] and
      te["G0T"][y0 - 1] == A._sprite_rows(early, early.object("Player0"))[0])
tear = new_design("a2600", "Tear")
tear.object("Player0")["x"] = 30
check("2600 object crossing the write pixel gets a warning", any("Player0" in w for w in A.kernel_tables(tear)["warnings"]))
pal_d = new_design("a2600", "PalScr", tv="PAL")
check("2600 PAL design has 228 lines", A.lines(pal_d) == 228 and pal_d.layer("Playfield").h == 228)
A.set_tv(pal_d, "NTSC")
check("2600 switching to NTSC resizes the layers", pal_d.layer("Background colour").h == 192)
w_, h_, buf, pal = A.render_indexed(d26)
check("2600 preview is 160 x 192 with the 128-colour palette", (w_, h_, len(buf), len(pal)) == (160, 192, 160 * 192, 128))
check("2600 preview shows the playfield colour where PF bits are set",
      buf[0] == d26.layer("Playfield colour").get(0, 0) and buf[60 * 160 + 80] == d26.layer("Background colour").get(0, 60))

# ====================================================================== NES encoding
dn = new_design("nes", "Meadow", screens=3)
at = dn.layer("Attributes")
for my in range(15):
    for mx in range(48):
        at.set(mx, my, (mx + 2 * my) & 3)
tab = N.attribute_table(dn, 0)
check("NES attribute table is 64 bytes", len(tab) == 64)
b0 = (at.get(0, 0) & 3) | ((at.get(1, 0) & 3) << 2) | ((at.get(0, 1) & 3) << 4) | ((at.get(1, 1) & 3) << 6)
check("NES attribute byte: TL bits 0-1, TR 2-3, BL 4-5, BR 6-7", tab[0] == b0, (tab[0], b0))
check("NES attribute row 7 uses only the top metatiles", tab[56] == ((at.get(0, 14) & 3) | ((at.get(1, 14) & 3) << 2)))
un = N.unpack_attribute_table(tab)
check("NES attribute table unpacks back", all(un[my][mx] == at.get(mx, my) for my in range(15) for mx in range(16)))
check("NES screen 2 attributes use metatiles 32..47", N.attribute_table(dn, 2)[0] ==
      ((at.get(32, 0) & 3) | ((at.get(33, 0) & 3) << 2) | ((at.get(32, 1) & 3) << 4) | ((at.get(33, 1) & 3) << 6)))
chr_ = N.chr_bytes(dn)
check("NES CHR is 8 KB (512 tiles, 2 planes)", len(chr_) == 8192)
dn.tiles[1] = bytearray([1] * 64)
check("NES CHR planes: colour 1 = plane 0 only", N.chr_bytes(dn)[16:24] == b"\xff" * 8 and N.chr_bytes(dn)[24:32] == b"\0" * 8)
pb = N.palette_bytes(dn)
check("NES palettes: 32 bytes, colour 0 shared", len(pb) == 32 and all(pb[i * 4] == pb[0] for i in range(8)))
dn.objects = [{"name": "M", "kind": "sprite", "x": 10, "y": 20, "tile": 0, "w": 2, "h": 2, "palette": 2,
               "flip_h": True, "flip_v": False, "behind": True}]
hs = N.hw_sprites(dn)
check("NES metasprite 2x2 -> 4 hardware sprites", len(hs) == 4)
check("NES flipped metasprite swaps columns + sets attribute bits", hs[0] == (10, 20, 1, 2 | 0x20 | 0x40) and
      hs[1] == (18, 20, 0, 2 | 0x20 | 0x40) and hs[2][2] == 17)
w_, h_, buf, pal = N.render_indexed(dn)
check("NES preview is screens*256 x 240", (w_, h_) == (768, 240) and len(pal) == 64)

# ====================================================================== Game Boy
dg = new_design("gb", "Town")
oam = G.oam_bytes(dg)
hero = dg.object("Hero")
check("GB OAM: y+16, x+8, tile, flags", oam[:4] == bytes([hero["y"] + 16, hero["x"] + 8, hero["tile"], 0]))
check("GB 2x2 hero -> 4 OAM entries + enemy", len(oam) == 5 * 4)
check("GB tile data 4 KB (256 x 16 bytes)", len(G.tiles_2bpp(dg)) == 4096)
check("GB background map 32 x 32", len(G.tilemap(dg, "Background")) == 1024)
dg.tiles[3] = bytearray([2] * 64)
check("GB 2bpp interleaved: colour 2 = high plane", G.tiles_2bpp(dg)[48:50] == b"\x00\xff")
w_, h_, buf, pal = G.render_indexed(dg)
check("GB preview is the 160 x 144 LCD", (w_, h_) == (160, 144))

from radide.retro.design.game.compat import chr_offset, decode_tile, encode_tile  # noqa: E402
tile = bytearray((i * 7) % 4 for i in range(64))
check("tile codecs round trip (NES planes, GB interleaved)", decode_tile("nes", encode_tile("nes", tile)) == tile and
      decode_tile("gb", encode_tile("gb", tile)) == tile)
check("CHR offset of an iNES image", chr_offset(b"NES" + bytes([2, 1]) + bytes(10)) == 16 + 2 * 16384)

# ====================================================================== mode 13h
dm = new_design("dos13h", "Cave")
check("13h palette: 768 bytes, 6-bit", len(M.pal_bytes(dm)) == 768 and max(M.pal_bytes(dm)) <= 63)
dm.palette[5] = [63, 32, 1]
check("13h palette entry 5 stored as R G B", M.pal_bytes(dm)[15:18] == bytes([63, 32, 1]))
check("13h palette preview scales 6-bit to 8-bit", M.palette_rgb(dm)[5] == (255, 129, 4))
bg = bytes(M.compose_background(dm))
check("13h background composed to 64000 bytes", len(bg) == 64000)
rle = M.rle_encode(bg)
check("13h RLE round trip", M.rle_decode(rle) == bg and len(rle) < len(bg))
check("13h RLE runs are at most 255", all(rle[i] <= 255 and rle[i] > 0 for i in range(0, len(rle), 2)))
spr = M.spr_bytes(dm)
check("13h sprite file header + count", spr[:4] == b"RSPR" and int.from_bytes(spr[4:6], "little") == 2)
first = M.placed_sprites(dm)[0]
check("13h sprite entry: x, y, w, h, flags, key, pixels",
      int.from_bytes(spr[6:8], "little") == first["x"] and spr[14] == 1 and len(first["pixels"]) == first["w"] * first["h"])
dm.objects.append({"name": "Edge", "kind": "sprite", "x": 312, "y": -4, "sprite": "Hero", "player": False})
edge = M.placed_sprites(dm)[-1]
check("13h sprite clipped at the screen edge", (edge["x"], edge["y"], edge["w"], edge["h"]) == (312, 0, 8, 12))
scr = M.screen_after_draw(dm)
hx, hy = dm.objects[0]["x"], dm.objects[0]["y"]
hs_ = dm.sprites["Hero"]
inside = [(x, y) for y in range(hs_["h"]) for x in range(hs_["w"]) if hs_["pixels"][y * hs_["w"] + x]]
x_, y_ = inside[0]
check("13h sprite pixel drawn, transparent pixel shows the background",
      scr[(hy + y_) * 320 + hx + x_] == hs_["pixels"][y_ * hs_["w"] + x_] and scr[hy * 320 + hx] == bg[hy * 320 + hx])
check("13h 8.3 names", M.dos8("My Long Screen 1") == "MYLONGSC")

# ====================================================================== model
p = WORK / f"Meadow{N.EXT}"
dn.save(p)
back = load(p)
check("model: save / load round trip", back.to_dict() == dn.to_dict())
snap = dn.snapshot()
dn.layer("Nametable").set(0, 0, 77)
dn.restore(snap)
check("model: snapshot / restore", dn.layer("Nametable").get(0, 0) != 77 or snap["layers"][0][6][0] == 77)
lay = dn.layer("Collision")
n = lay.flood(0, 0, 3)
check("model: flood fill", n > 0 and lay.get(0, 0) == 3)
check("extensions registered", set(EXTS.values()) == set(SYSTEMS) and gen_dir(p) == p.parent / "gen" / "Meadow")
try:
    Design.from_dict({"format": "other"})
    check("model: foreign JSON refused", False)
except ValueError:
    check("model: foreign JSON refused", True)

# ====================================================================== 6502 interpreter sanity
mem = bytearray(65536)
prog = bytes([0xA9, 0x05, 0x69, 0x03, 0x8D, 0x00, 0x02, 0xA2, 0x03, 0xCA, 0xD0, 0xFD, 0x00])
mem[0x8000:0x8000 + len(prog)] = prog
cpu = CPU6502(lambda a: mem[a], lambda a, v: mem.__setitem__(a, v))
cpu.pc = 0x8000
for _ in range(10):
    cpu.step()
check("6502: LDA / ADC / STA / DEX / BNE", mem[0x200] == 8 and cpu.x == 0)


# ====================================================================== real builds
def built(system: str, design: Design, name: str, **kw) -> dict | None:
    out = WORK / name
    logs = []
    res = build(design, out, log=logs.append)
    if res.get("missing"):
        skip(f"{name} build", f"{res['missing']} not installed")
        return None
    check(f"{name}: builds with its toolchain", res["ok"], "\n".join(logs[-25:]))
    for ok, msg in res.get("checks", []):
        check(f"{name}: {msg}", ok)
    return res if res["ok"] else None


r26 = built("a2600", new_design("a2600", "Castle"), "a2600_ntsc")
if r26:
    rom = r26["rom"].read_bytes()
    check("2600 ROM is 4 KB with the reset vector in $F000-$FFFF", len(rom) == 4096 and rom[0xFFD] >= 0xF0)
d_pal = new_design("a2600", "PalCastle", tv="PAL")
for o in d_pal.objects:
    o["enabled"] = True
d_pal.object("Player0")["x"] = 10
built("a2600", d_pal, "a2600_pal")
dlong = new_design("a2600", "Positions")
for o, x in zip(dlong.objects, (159, 150, 140, 3, 120)):
    o["x"], o["enabled"] = x, True
rl = built("a2600", dlong, "a2600_positions")

dlev = new_design("nes", "Level", screens=3)
nt = dlev.layer("Nametable")
for x in range(96):
    nt.set(x, 10, x)
rn = built("nes", dlev, "nes_level")
if rn:
    pr = NESProbe(rn["rom"].read_bytes())
    pr.run(3)
    pr.pad = 0x01                      # hold Right
    pr.run(300)
    camx = pr.ram[0] | (pr.ram[1] << 8)
    row10 = [pr.vram[(s // 32) * 0x400 + 10 * 32 + s % 32] for s in range(64)]
    check("NES scrolling: camera moved right 300 px", camx == 300, camx)
    check("NES column streaming: columns 64-69 replaced slots 0-5", row10[:6] == [64, 65, 66, 67, 68, 69], row10[:8])
    pr.pad = 0x02
    pr.run(100)
    camx = pr.ram[0] | (pr.ram[1] << 8)
    check("NES scrolling back left", camx == 200, camx)
    vis = [pr.vram[(s // 32) * 0x400 + 10 * 32 + s % 32] for s in range(25, 57)]
    check("NES columns 25-56 are on screen after scrolling left", vis == list(range(25, 57)), vis[:6])
    check("NES sprites follow the camera (hero hidden at camera 200)", pr.oam[0] == 0xFF or pr.oam[3] != 40)
rs = built("nes", new_design("nes", "Single", screens=1), "nes_single")

rg = built("gb", new_design("gb", "Town"), "gb_town")

d13 = new_design("dos13h", "Cave")
r13 = built("dos13h", d13, "dos_nasm")
want13 = bytes(M.screen_after_draw(d13))
for tgt in ("freebasic", "watcom"):
    dd = new_design("dos13h", "Cave")
    dd.settings["target"] = tgt
    if tgt == "freebasic" and not shutil.which("dosbox-x"):
        pass
    res = built("dos13h", dd, f"dos_{tgt}")
    if res:
        t0 = time.time()
        got = dosbox_shot(res["rom"], 60, log=lambda m: None)
        if got is None:
            skip(f"dos_{tgt} run in DOSBox-X", "DOSBox-X not installed or no SCREEN.RAW")
        else:
            diff = sum(1 for a, b in zip(got, want13) if a != b)
            check(f"dos_{tgt}: runs in DOSBox-X and draws exactly the design ({time.time() - t0:.1f} s)", diff == 0,
                  f"{diff} pixels differ")

# ====================================================================== emulators
if NO_EMU:
    skip("emulator smoke tests", "--no-emu")
else:
    try:
        from radide.retro.emu import find_emulator, run_rom
    except Exception as e:  # noqa: BLE001
        find_emulator = None
        skip("emulator smoke tests", f"emulator manager missing: {e}")
    if find_emulator is not None:
        for sysid, res in (("a2600", r26), ("nes", rn), ("gb", rg), ("dos", r13)):
            if not res:
                continue
            emu, exe = find_emulator(sysid)
            if not exe:
                skip(f"{sysid} in emulator", "no emulator installed (Tools > Retro > Emulators...)")
                continue
            try:
                proc = run_rom(str(res["rom"]), system=sysid, minimized=True, quiet=True)
            except Exception as e:  # noqa: BLE001
                check(f"{sysid}: starts in {emu}", False, e)
                continue
            # poll the emulator RetroProcess tracks (launch.py: the process really showing the ROM - a
            # launcher's child, or an already open single-instance Mesen window that took the ROM over)
            while proc.alive() and time.time() < proc.started_at + 4:
                time.sleep(0.1)
            alive = proc.alive()
            check(f"{sysid}: {Path(res['rom']).name} runs in {emu}", alive, proc.exit_info())
            proc.stop()
            check(f"{sysid}: {emu} stopped again", not proc.alive(), proc.exit_info())

# ====================================================================== summary
ok = sum(1 for _, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; skipped {len(SKIPPED)}; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
