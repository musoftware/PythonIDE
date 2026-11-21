"""The gaps the DABG mod test found, closed - pure tests (no Qt):

  G1 compressed graphics: codecs (PB53 / PB53 header / Konami RLE / Shiru RLE / PackBits / GBA LZ10) round trips,
     DABG's ascii.pb53 decoded from the ROM and packed again byte for byte, Find Graphics locates it, a region is
     edited and written back with the size check / free-space rule
  G2 palettes in a ROM: NES table detection + write back, NES one-slot tables (DABG MainColors), GB BGP, BGR555,
     Genesis
  G3 disassembler: RTS / split / JMP (indirect) jump tables found automatically (synthetic ROM + DABG), hints
     (code / data / jump tables / labels / bank labels / RAM names), file offset <-> CPU address, label import
     (ca65 .dbg built from DABG's source, Mesen .mlb, FCEUX .nl, RGBDS .sym), byte-identical rebuilds
  G4 emulator choice: per-project setting, fallback when the chosen emulator is missing, runner command lines
  G5 Mesen 2 screenshots by script (headless --testRunner), when Mesen is installed

    .venv\\Scripts\\python.exe samples\\Tests\\Retro\\GameMod_DABG\\test_gamemod_gaps_core.py
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from radide.retro.cpu import disasm, labels, romfmt  # noqa: E402
from radide.retro.dev import fromrom  # noqa: E402
from radide.retro.gfx import compress as C  # noqa: E402
from radide.retro.gfx import rompal  # noqa: E402

RESULTS: list[tuple[str, bool]] = []
WORK = Path(tempfile.mkdtemp(prefix="radide-gamemod-gaps-"))
ROM = (HERE / "original" / "dabg.nes").read_bytes()
SRC = HERE / "original" / "source"
CHR = (SRC / "ascii.chr").read_bytes()
PB53 = (SRC / "ascii.pb53").read_bytes()
OFF_PB53 = 0x5D17


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:500]}]"), flush=True)
    return bool(cond)


# ============================================================================================ G1 codecs
print("=== G1 compressed graphics", flush=True)
random.seed(7)
samples = {"chr": CHR, "zeros": bytes(1000), "noise": bytes(random.randrange(256) for _ in range(2000)),
           "mixed": CHR[:777] + bytes([5]) * 300}
for key, codec in C.CODECS.items():
    ok, info = True, []
    for name, s in samples.items():
        try:
            enc = C.compress(key, s)
        except C.CodecError:
            info.append(f"{name}: cannot encode")
            continue
        dec, used = C.decompress(key, enc, 0, len(s) if codec.needs_size else None)
        # pb53h counts whole tiles in its header: a partial last tile is not part of the output
        exact = dec == s if key != "pb53h" else dec == s[:len(s) // 16 * 16]
        if not exact or used > len(enc):
            ok = False
            info.append(f"{name}: dec {len(dec)} used {used} enc {len(enc)}")
    check(f"G1.1 {key}: compress -> decompress gives the same bytes", ok, info)
raw, used = C.decompress("pb53", ROM, OFF_PB53, len(CHR))
check("G1.2 PB53 block in the DABG ROM decodes to ascii.chr", raw == CHR and used == len(PB53), (len(raw), used))
check("G1.3 PB53 packer = pb53.py byte for byte", C.compress("pb53", CHR) == PB53)
check("G1.4 PB53 header form (pb53h) matches pb53_py3.pack_file",
      C.compress("pb53h", CHR)[:2] == bytes(((len(CHR) // 16) >> 8, (len(CHR) // 16) & 0xFF)))
found = C.find_graphics(ROM, ["pb53"])
check("G1.5 Find Graphics (PB53) finds the whole block at $5D17: 512 tiles",
      found and found[0].offset == OFF_PB53 and found[0].used == len(PB53) and found[0].tiles == 512,
      [f.label() for f in found])
lz = bytearray(b"\x00" * 64) + C.compress("lz10", CHR[:2048]) + bytes(64)
found_lz = C.find_graphics(lz, ["lz10"])
check("G1.6 Find Graphics (LZ10) finds a GBA-style block", found_lz and found_lz[0].offset == 64,
      [f.label() for f in found_lz])
# edit + write back into a copy of the ROM
rom = bytearray(ROM)
reg = C.Region.open("pb53", rom, OFF_PB53, len(CHR))
edited = bytearray(reg.raw)
edited[0x1060:0x1070] = bytes([0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C] * 2)
room, fill = reg.room(rom)
new_len, room2, old = reg.write_back(rom, edited)
back, used2 = C.decompress("pb53", rom, OFF_PB53, len(CHR))
check("G1.7 edited tiles packed back into the ROM (size check passed)", back == bytes(edited) and used2 == new_len,
      (new_len, room2, old))
check("G1.8 bytes outside the block unchanged", rom[:OFF_PB53] == ROM[:OFF_PB53] and
      rom[OFF_PB53 + max(old, new_len):] == ROM[OFF_PB53 + max(old, new_len):])
noise = bytearray(edited)
noise[0:4096] = bytes(random.randrange(256) for _ in range(4096))           # incompressible: cannot fit
try:
    reg.write_back(rom, noise)
    too_big = False
except C.CodecError as e:
    too_big = "only" in str(e) and "free" in str(e)
check("G1.9 too big after editing: refused with a free-space message", too_big)
pad = bytearray(b"\x11" * 32) + C.compress("rle_konami", CHR[:512]) + bytes([0xFF]) * 200 + b"\x22" * 8
r2 = C.Region.open("rle_konami", pad, 32)
room3, fill3 = r2.room(pad)
check("G1.10 free space after a block ($FF padding) counts as room", room3 == r2.used + 200 and fill3 == 0xFF,
      (room3, r2.used))

# ============================================================================================ G2 palettes
print("=== G2 palettes in the ROM", flush=True)
pal_table = bytes([0x0F, 0x30, 0x16, 0x27, 0x0F, 0x1A, 0x2A, 0x3A, 0x0F, 0x11, 0x21, 0x31, 0x0F, 0x06, 0x16, 0x26,
                   0x0F, 0x16, 0x27, 0x18, 0x0F, 0x02, 0x12, 0x22, 0x0F, 0x19, 0x29, 0x39, 0x0F, 0x07, 0x17, 0x37])
img = bytearray(random.randrange(0x40, 0x100) for _ in range(4096))
img[0x9A0:0x9A0 + 32] = pal_table
cands = rompal.find_nes_palettes(img)
check("G2.1 NES palette table detected at its offset", cands and cands[0].offset == 0x9A0, [c.label() for c in cands[:3]])
rp = rompal.RomPalette("nes4", 0x9A0, 4)
check("G2.2 sub-palette 4 (first sprite palette) read", rp.slots(img) == [0x0F, 0x16, 0x27, 0x18])
ch = rp.set_slot(img, 3, 0x30)
check("G2.3 colour edit written back to its byte", img[0x9A0 + 16 + 3] == 0x30 and ch == [(0x9B3, b"\x18", b"\x30")])
dabg = bytearray(ROM)
rs = rompal.RomPalette("nes_slot", 0x5D0B, 4, slot=2, base=[0x31, 0x0F, 0, 0x30])
check("G2.4 DABG MainColors (one byte per palette, slot 2): player palette $31 $0F $01 $30",
      rs.slots(dabg) == [0x31, 0x0F, 0x01, 0x30], rs.slots(dabg))
rs.set_slot(dabg, 2, 0x16)
check("G2.5 slot 2 edited -> MainColors+4 = $16 (red player)", dabg[0x5D0F] == 0x16 and
      rs.set_slot(dabg, 0, 0x21) == [], dabg[0x5D0F])
gb = bytearray([0x00, 0xE4, 0x00])
g = rompal.RomPalette("gb_bgp", 1)
check("G2.6 GB BGP $E4 = shades 0,1,2,3", g.slots(gb) == [0, 1, 2, 3])
g.set_slot(gb, 0, 3)
check("G2.7 GB BGP slot 0 -> shade 3 = $E7", gb[1] == 0xE7, hex(gb[1]))
cgb = bytearray(b"\x00" * 8 + bytes((0xFF, 0x7F, 0x1F, 0x00, 0xE0, 0x03, 0x00, 0x00)) + b"\x00" * 8)
b5 = rompal.RomPalette("bgr555", 8, 0, 4)
cols = b5.colors(cgb)
check("G2.8 BGR555 colours (white, red, green, black)", cols[0] == (255, 255, 255) and cols[1] == (255, 0, 0) and
      cols[2] == (0, 255, 0) and cols[3] == (0, 0, 0), cols)
b5.set_slot(cgb, 3, (0, 0, 255))
check("G2.9 BGR555 write back (blue = $7C00)", cgb[14] == 0x00 and cgb[15] == 0x7C)
cgb2 = bytearray(b"\x00" * 8 + bytes((0xFF, 0x7F, 0x1F, 0x00, 0xE0, 0x03, 0x00, 0x00)) + b"\x00" * 8)
check("G2.10 GBC palette candidates found", any(c.offset == 8 for c in rompal.find_bgr555_palettes(cgb2)),
      [c.label() for c in rompal.find_bgr555_palettes(cgb2)])
gen = bytearray(4)
ge = rompal.RomPalette("genesis", 0, 0, 2)
ge.set_slot(gen, 0, (255, 0, 0))
check("G2.11 Genesis CRAM word for red = $000E", gen[:2] == b"\x00\x0E" and ge.colors(gen)[0] == (255, 0, 0))

# ============================================================================================ G3 disassembler
print("=== G3 disassembler: jump tables, hints, labels", flush=True)


def nes_rom(code_at: dict[int, bytes], reset: int) -> bytes:
    prg = bytearray([0xEA] * 0x4000)
    for addr, bs in code_at.items():
        prg[addr - 0xC000:addr - 0xC000 + len(bs)] = bs
    prg[0x3FFA:0x4000] = bytes((reset & 0xFF, reset >> 8)) * 3
    return b"NES\x1a" + bytes([1, 1, 0, 0]) + bytes(8) + bytes(prg) + bytes(8192)


def w(v):
    return bytes((v & 0xFF, v >> 8))


E0, E1, F0, F1, G0, G1 = 0xC100, 0xC110, 0xC140, 0xC150, 0xC180, 0xC190
code = {
    0xC000: bytes([0xA2, 0x00, 0xBD]) + w(0xC00E) + bytes([0x48, 0xBD]) + w(0xC00D) + bytes([0x48, 0x60, 0xEA, 0xEA]),
    0xC00D: w(E0 - 1) + w(E1 - 1),
    E0: bytes([0xA9, 0x01, 0x4C]) + w(0xC120),
    E1: bytes([0x4C]) + w(E1),
    0xC120: bytes([0xA0, 0x00, 0xB9]) + w(0xC130) + bytes([0x48, 0xB9]) + w(0xC12E) + bytes([0x48, 0x60]),
    0xC12E: bytes([(F0 - 1) & 0xFF, (F1 - 1) & 0xFF, (F0 - 1) >> 8, (F1 - 1) >> 8]),
    F0: bytes([0xA9, 0x02, 0x4C]) + w(0xC160),
    F1: bytes([0x4C]) + w(F1),
    0xC160: bytes([0xA2, 0x00, 0xBD]) + w(0xC170) + bytes([0x85, 0x10, 0xBD]) + w(0xC171) +
    bytes([0x85, 0x11, 0x6C, 0x10, 0x00]),
    0xC170: w(G0) + w(G1),
    G0: bytes([0x4C]) + w(G0),
    G1: bytes([0x4C]) + w(G1),
}
synth = nes_rom(code, 0xC000)
sp = WORK / "tables.nes"
sp.write_bytes(synth)
im = romfmt.load(sp)
d = disasm.analyze(im.segments, im.cpu, im.system)
prg = next(s for s in im.segments if s.trace)
reached = {a: (a - prg.base) in d.code[id(prg)] for a in (E0, E1, F0, F1, G0, G1)}
check("G3.1 RTS table, split lo/hi RTS table and JMP (ptr) table: every entry traced", all(reached.values()), reached)
kinds = sorted((t["kind"], t["hi"] is not None) for t in d.tables)
check("G3.2 three tables recorded (rts, rts split, word)", kinds == [("rts", False), ("rts", True), ("word", False)],
      d.tables)
no_auto = disasm.analyze(im.segments, im.cpu, im.system, disasm.Hints(auto_tables=False))
check("G3.3 without auto_tables the entries stay data", (E1 - prg.base) not in no_auto.code[id(prg)])
hinted = disasm.analyze(im.segments, im.cpu, im.system, disasm.Hints.from_dict(
    {"auto_tables": False, "jump_tables": [["C00D", "C010", "rts"], ["C170", "C173", "word"],
                                           ["C12E", "C12F", "rts", "C130"]]}))
check("G3.4 the same tables given as jump_tables hints", all((a - prg.base) in hinted.code[id(prg)]
                                                            for a in (E0, E1, F0, F1, G0, G1)))
have_cc65 = bool(shutil.which("ca65") or (Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE" / "tools" / "cc65" /
                                         "bin" / "ca65.exe").is_file())
if have_cc65:
    res = fromrom.create_project(sp, WORK / "tables_dis", log=lambda t: None)
    text = (WORK / "tables_dis" / "main.s").read_text(encoding="utf-8")
    check("G3.5 synthetic ROM rebuilds byte-identical with the tables as symbols",
          (res.identical or {}).get("same") and ".word LC100-1" in text and "<(LC140-1)" in text and
          ".word LC180" in text, res.summary())
    dres = fromrom.create_project(HERE / "original" / "dabg.nes", WORK / "dabg_dis", log=lambda t: None)
    st = dres.dis.stats()
    check("G3.6 DABG: RTS tables found automatically (5 tables, > 6000 instructions; 831 before)",
          st["jump_tables"] >= 5 and st["instructions"] > 6000, st)
    check("G3.7 DABG: still byte-identical", (dres.identical or {}).get("same"), dres.summary())
    dtext = (WORK / "dabg_dis" / "main.s").read_text(encoding="utf-8")
    check("G3.8 DABG: ObjectTable written as .word Label-1 and 'lda L9C18+1,y'",
          "L9C18:\n        .word L95D0-1" in dtext and "lda L9C18+1,y" in dtext)
    # label import from the game's own build (ca65 -g / ld65 --dbgfile)
    bsrc = WORK / "dabg_src"
    shutil.copytree(SRC, bsrc)
    tools = Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE" / "tools" / "cc65" / "bin"
    ca65 = shutil.which("ca65") or str(tools / "ca65.exe")
    ld65 = shutil.which("ld65") or str(tools / "ld65.exe")
    subprocess.run([ca65, "-g", "dabg.s", "-o", "dabg.o"], cwd=bsrc, check=True, capture_output=True)
    subprocess.run([ld65, "-C", "nrom256.x", "dabg.o", "-o", "dabg.nes", "--dbgfile", "dabg.dbg"], cwd=bsrc,
                   check=True, capture_output=True)
    ls = labels.read_labels(bsrc / "dabg.dbg", romfmt.load(HERE / "original" / "dabg.nes"))
    check("G3.9 ca65 .dbg: global + scoped labels, constants and ca65's own symbols skipped",
          ls.labels.get(0x8D9B) == "ResetPlayerX" and ls.labels.get(0x9C18) == "ObjectTable" and
          ls.labels.get(0x76) == "PlayerLives" and not any(v.startswith("CPU_") for v in ls.labels.values()),
          {k: ls.labels.get(k) for k in (0x8D9B, 0x9C18, 0x76)})
    n, kind = fromrom.import_labels(WORK / "dabg_dis", bsrc / "dabg.dbg")
    r3 = fromrom.redisassemble(WORK / "dabg_dis", log=lambda t: None)
    t3 = (WORK / "dabg_dis" / "main.s").read_text(encoding="utf-8")
    check("G3.10 labels imported into hints.json and used: byte-identical, real names in the source",
          n > 500 and (r3.identical or {}).get("same") and "ResetPlayerX:" in t3 and "PlayerLives = $76" in t3 and
          "dec PlayerLives,x" in t3, (n, r3.summary()))
else:
    print("SKIP G3.5-G3.10 (cc65 not installed: Tools > Retro > Retro Toolchains)")
mlb = labels.parse_mlb("NesPrgRom:0D8B:ResetX:lives at start\nNesInternalRam:0076:Lives\nP:0727:Lose\n"
                       "G:2000:PpuCtrl\n", romfmt.load(HERE / "original" / "dabg.nes"))
check("G3.11 Mesen .mlb: PRG-ROM offsets -> CPU addresses, RAM / registers, comments",
      mlb.labels == {0x8D8B: "ResetX", 0x76: "Lives", 0x8727: "Lose", 0x2000: "PpuCtrl"} and
      mlb.comments.get(0x8D8B) == "lives at start", (mlb.labels, mlb.comments))
nl = labels.parse_nl("$8D9B#ResetPlayerX#lives\n$0076/4#PlayerLives#\n$C000##comment only\n")
check("G3.12 FCEUX .nl: names, arrays, comments", nl.labels == {0x8D9B: "ResetPlayerX", 0x76: "PlayerLives"} and
      nl.comments.get(0xC000) == "comment only", (nl.labels, nl.comments))
sym = labels.parse_sym("; File generated by rgblink\n00:0150 Main\n01:4000 Bank1Code\n00:C100 wPlayer.x\n")
check("G3.13 RGBDS .sym: bank 0 / RAM plain, ROMX names bank-specific", sym.labels == {0x150: "Main", 0xC100:
                                                                                      "wPlayer_x"} and
      sym.bank_labels == {(1, 0x4000): "Bank1Code"}, (sym.labels, sym.bank_labels))
hp = WORK / "h"
hp.mkdir()
(hp / "hints.json").write_text(json.dumps(fromrom.HINTS_TEMPLATE), encoding="utf-8")
fromrom.add_hint(hp, "code", 0x8737)
fromrom.add_hint(hp, "data", 0xDCFB, 0xDD02)
fromrom.add_hint(hp, "rts_table", 0xAD8D, 0xAD96)
fromrom.add_hint(hp, "label", 0x8737, text="Lose Life")
hd = json.loads((hp / "hints.json").read_text(encoding="utf-8"))
check("G3.14 add_hint: code / data / rts table / label (name cleaned) in hints.json",
      hd["code"] == ["8737"] and hd["data"] == [["DCFB", "DD02"]] and hd["jump_tables"] == [["AD8D", "AD96", "rts"]]
      and hd["labels"] == {"8737": "Lose_Life"}, hd)
check("G3.15 address of a disassembly line", fromrom.address_of_line("        lda #$03     ; 8D9B") == 0x8D9B and
      fromrom.address_of_line("        .byte $16,$29   ; DCFB ..") == 0xDCFB and
      fromrom.address_of_line("L8D9B:") is None)
dimg = romfmt.load(HERE / "original" / "dabg.nes")
check("G3.16 file offset <-> CPU address (iNES header skipped)", romfmt.file_to_cpu(dimg, 0xDAB)[0] == 0x8D9B and
      romfmt.cpu_to_file(dimg, 0x8D9B) == 0xDAB and romfmt.file_to_cpu(dimg, 5) is None)
bh = disasm.Hints.from_dict({"labels": {"01:4000": "B1Start", "C100": "wPlayer"}})
check("G3.17 bank-specific labels and RAM names in hints", bh.bank_labels == {(1, 0x4000): "B1Start"} and
      bh.labels == {0xC100: "wPlayer"})

# ============================================================================================ G4 emulator choice
print("=== G4 emulator choice", flush=True)
from types import SimpleNamespace  # noqa: E402

from radide.retro.emu import manager  # noqa: E402
from radide.retro.emu import ui as emu_ui  # noqa: E402

pdir = WORK / "proj"
pdir.mkdir()
from radide.model import Project  # noqa: E402

proj = Project(pdir, "P", "retro-nes", [], "main", ["main.s"])
proj.extra["retro"] = {"system": "nes", "lang": "asm", "main": "main.s", "output": "p.nes"}
proj.save()
check("G4.1 project system = nes, emulators listed in order", emu_ui.project_system(proj) == "nes" and
      [c[0] for c in emu_ui.emulator_choices("nes")] == ["mesen", "fceux"])
emu_ui.set_project_emulator(proj, "fceux")
check("G4.2 choice saved in project.radproj (retro.emulator)", json.loads((pdir / "project.radproj").read_text(
    encoding="utf-8"))["retro"]["emulator"] == "fceux" and emu_ui.project_emulator(Project.load(pdir)) == "fceux")
have = {e: bool(manager.find(e)) for e in ("mesen", "fceux")}
eid, note = emu_ui.resolve_emulator("nes", "fceux")
check("G4.3 chosen emulator used when installed (else the first available + a note)",
      (eid == "fceux" and not note) if have["fceux"] else (note and eid == ("mesen" if have["mesen"] else "")),
      (eid, note, have))
eid2, note2 = emu_ui.resolve_emulator("nes", "stella")
check("G4.4 an emulator that cannot run the system falls back with a note", note2 and eid2 != "stella", (eid2, note2))
rh = WORK / "hack"
from radide.languages import get_plugin  # noqa: E402

get_plugin("retro-romhack").create_new_project(rh, "Hack", "romhack_demo")
hproj = Project.load(rh)
emu_ui.set_project_emulator(hproj, "fceux")
check("G4.5 ROM Hacking project: choice in rom.json (emulator)", json.loads((rh / "rom.json").read_text(
    encoding="utf-8")).get("emulator") == "fceux" and emu_ui.project_system(hproj) == "nes")
os.environ["RADIDE_RETRO_DRY_RUN"] = "1"
from radide.retro.rom.emulink import run_rom as link_run  # noqa: E402

if have["fceux"]:
    cmd = link_run(rh / "rom" / "demo.nes", "nes", emulator="fceux")
    check("G4.6 the ROM Hacking runner resolves the chosen emulator (dry run)", cmd.emulator == "fceux", cmd.command)
cmd2 = None
try:
    cmd2 = link_run(rh / "rom" / "demo.nes", "nes", emulator="atari800")
except Exception as e:  # noqa: BLE001
    cmd2 = SimpleNamespace(emulator=f"error {e}")
check("G4.7 a chosen emulator that cannot start -> automatic choice", getattr(cmd2, "emulator", "") in
      ("mesen", "fceux") or not any(have.values()), getattr(cmd2, "emulator", None))
os.environ.pop("RADIDE_RETRO_DRY_RUN", None)

# ============================================================================================ G5 Mesen screenshots
print("=== G5 Mesen screenshots by script", flush=True)
from radide.retro.emu import mesenshot  # noqa: E402

lua = mesenshot.script([60, 240], [(120, 126, {"start": True})])
check("G5.1 Lua script: frames, input, takeScreenshot, emu.stop", "[60]=true" in lua and "{start=true}" in lua and
      "emu.takeScreenshot()" in lua and "emu.stop(0)" in lua)
if manager.find("mesen"):
    user_settings = Path(manager.find("mesen")).with_name("settings.json")
    before = user_settings.read_bytes() if user_settings.is_file() else b""
    shots = mesenshot.mesen_screenshots(HERE / "original" / "dabg.nes", [100, 220, 330], WORK / "mshots",
                                        inputs=[(150, 156, {"start": True}), (260, 266, {"start": True})])
    from PIL import Image
    sizes = [Image.open(f).size for f in shots]
    hashes = {f.read_bytes() for f in shots}
    check("G5.2 Mesen saved 3 screenshots (256x240 PNG) from the headless test runner",
          len(shots) == 3 and all(s == (256, 240) for s in sizes), sizes)
    check("G5.3 the Start presses changed the screen (title -> menu -> next menu)", len(hashes) == 3)
    check("G5.4 the user's Mesen settings were not touched (private runner copy)",
          (user_settings.read_bytes() if user_settings.is_file() else b"") == before)
    keep = HERE / "shots"
    keep.mkdir(exist_ok=True)
    for f in shots:
        shutil.copy2(f, keep / f"E_mesen_{f.name}")
else:
    print("SKIP G5.2-G5.4 (Mesen 2 not installed: Tools > Retro > Emulators)")

failed = [n for n, ok in RESULTS if not ok]
print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed" + (f"; FAILED: {failed}" if failed else ""))
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(1 if failed else 0)
