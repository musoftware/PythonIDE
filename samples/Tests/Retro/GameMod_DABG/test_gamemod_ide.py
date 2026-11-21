"""Mod a real open-source NES game with RAD IDE, the way a user would (qh.py harness).

Game: Double Action Blaster Guys (DABG) by NovaSquirrel, zlib licence,
      https://github.com/NovaSquirrel/DABG  (ROM: release v2, source: master 5ecc60b).
The original ROM + source are in original/ (see README.md and LICENSE.txt).

Run:  .venv\\Scripts\\python.exe samples\\Tests\\Retro\\GameMod_DABG\\test_gamemod_ide.py [--no-emu] [--keep]

Steps (each one through IDE features):
  A  ROM Hacking Project: source ROM + header info, working copy in the hex editor: data inspector (6502 view)
     to find the lives / speed constants, palette bytes, the menu text through a .tbl table (Text Table Editor +
     table search / replace), Capture Edits as an IPS patch, Build, Compare Files.
  B  Disassemble ROM into Project: byte-identical rebuild, hints.json + Re-disassemble with Hints, a code change
     (infinite lives), rebuild, then IPS + BPS patches (Create Patch dialog), Apply Patch to a clean copy, compare.
  C  The game's own source as a NES (ca65) project: build with cc65 (prebuild runs the game's PB53 graphics
     packer), redraw the player sprite in the Tile Editor (ascii.chr), a source-level change, rebuild.
  D  Emulator: original and modded ROMs started from the IDE (emulator API); FCEUX's own Lua screenshot function
     saves the game screens (no desktop capture).
Every IDE screenshot is widget.grab(); QSettings org RADIDE-TEST.
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("QA_NAME", "gamemod_dabg")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait  # noqa: E402

from PyQt6.QtCore import QPoint, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

NO_EMU = "--no-emu" in sys.argv
WORK = Path(qh.WORK) / "gamemod_dabg"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)
ORIG_ROM = HERE / "original" / "dabg.nes"
ORIG_SRC = HERE / "original" / "source"
CLEAN = ORIG_ROM.read_bytes()

# file offsets in the v2 ROM (found below through the IDE; listed here only to check the results)
OFF_LIVES = 0xDAB          # ResetPlayerX: lda #3 / sta PlayerLives,x
OFF_WALK = 0x786           # ldy #2 (walk) ... ldy #4 (run, holding B)
OFF_PAL = 0x5D0B           # MainColors (.byt $16,$29,$03,$28, $01,$16,$27,$21)
OFF_SKY = 0x59E6           # lda #$31 (sky colour of every palette)
OFF_DEC = 0x747            # dec PlayerLives,x  (player lost a life)


def gshot(widget, name):
    p = SHOTS / (name + ".png")
    widget.grab().save(str(p))
    print("SHOT", p, flush=True)
    return p


def insp(doc) -> dict:
    t = doc.inspector
    return {t.item(i, 0).text(): t.item(i, 1).text() for i in range(t.rowCount()) if t.item(i, 0) and t.item(i, 1)}


def type_hex(doc, offset, digits):
    v = doc.view
    v.area = "hex"
    v.set_cursor(offset)
    v.setFocus()
    QTest.keyClicks(v, digits)
    pump(0.1)


w = qh.window()
from radide.languages import get_plugin  # noqa: E402
from radide.retro.rom.hexdoc import HexDocument  # noqa: E402

feat = w.rom_feature
gfx = w.retro_gfx

# =====================================================================================================  A
print("=== A: ROM Hacking Project", flush=True)
hack = WORK / "DABG_RomHack"
get_plugin("retro-romhack").create_new_project(hack, "DABG_RomHack", "romhack_empty")
w.open_project(hack, ask=False)
pump(1)
check("A1 ROM Hacking project opened", w.project is not None and w.project.language == "retro-romhack")
pm = feat.open_manager()
check("A2 Patch Manager: Set Source ROM (copied into rom/)", pm.choose_rom(str(ORIG_ROM), copy=True) and
      (hack / "rom" / "dabg.nes").read_bytes() == CLEAN)
src = feat.view_source()
rows = dict(src.info.rows)
check("A3 header: NES 2.0, mapper 0 NROM, 32 KB PRG, CHR RAM",
      rows.get("Mapper", "").startswith("0 - NROM") and rows.get("PRG ROM") == "32 KB" and
      "CHR RAM" in rows.get("CHR ROM", ""), rows)
check("A3b vectors listed", any(k.startswith("RESET") for k in rows), list(rows))
check("A4 source ROM is read-only", src.read_only)
gshot(w, "A_source_rom_header")

work = pm.edit_work()
pump(0.3)
wd = w.tabs.currentWidget()
check("A5 Edit Working Copy opens work/dabg.nes in the hex editor", isinstance(wd, HexDocument) and
      Path(wd.path) == work and not wd.read_only)

# -- lives: hex search for 'lda #3 / sta zp,x' and check with the 6502 inspector
wd.show_find()
fp = wd.find_panel
fp.mode.setCurrentIndex(0)
fp.find.setText("A9 03 95 ?? BC")
check("A6 hex search with wildcard finds 'lda #3 / sta PlayerLives,x'", wd.find_next() and wd.view.cursor == OFF_LIVES,
      hex(wd.view.cursor))
i = insp(wd)
check("A7 data inspector shows LDA #$03 at CPU $8D9B", i.get("6502", "").upper().startswith("LDA #$03") and
      "8D9B" in i.get("CPU address (6502)", ""), i)
type_hex(wd, OFF_LIVES + 1, "09")
check("A8 typed 09: start with 9 lives", wd.buf.data[OFF_LIVES + 1] == 9)

# -- player speed: ldy #2 / lda 0 / and #KEY_B / beq / ldy #4
fp.find.setText("A0 02 A5 00 29 40 F0 02 A0 04")
check("A9 found the walk / run speed code", wd.find_next() and wd.view.cursor == OFF_WALK, hex(wd.view.cursor))
check("A9b inspector: LDY #$02", insp(wd).get("6502", "").upper().startswith("LDY #$02"), insp(wd).get("6502"))
type_hex(wd, OFF_WALK + 1, "03")
type_hex(wd, OFF_WALK + 9, "06")
check("A10 walk speed 3, run speed 6", wd.buf.data[OFF_WALK + 1] == 3 and wd.buf.data[OFF_WALK + 9] == 6)

# -- palette: MainColors table + the sky colour
fp.find.setText("16 29 03 28 01 16 27 21")
check("A11 palette table found", wd.find_next() and wd.view.cursor == OFF_PAL, hex(wd.view.cursor))
type_hex(wd, OFF_PAL + 4, "16")           # player 1 sprite colour: dark blue $01 -> red $16
fp.find.setText("A9 31 8D 07 20")
check("A12 sky colour write found", wd.find_next() and wd.view.cursor == OFF_SKY, hex(wd.view.cursor))
type_hex(wd, OFF_SKY + 1, "27")           # sky: light blue $31 -> orange $27 (sunset)

# -- text through a table: Text Table Editor (new ASCII table + end code), then table search / replace
tbl_path = hack / "tables" / "dabg.tbl"
from radide.retro.gfx.ui_text import TableEditor  # noqa: E402
te = gfx.open_table(hack / "tables" / "ascii.tbl")
pump(0.3)
check("A13 .tbl opens in the Text Table Editor", isinstance(te, TableEditor))
te.add_row()
r = te.grid.rowCount() - 1
te.grid.item(r, 0).setText("00")
te.grid.item(r, 1).setText("<end>")
te.grid.cellWidget(r, 2).setCurrentIndex(te.grid.cellWidget(r, 2).findData("end"))
te.retro_path = tbl_path
check("A14 table check OK and saved as dabg.tbl", te.check() == [] and te.save() and tbl_path.is_file(), te.check())
te.test_hex.setText("50 6C 61 79 20 47 61 6D 65 00")
check("A15 table test box decodes the menu bytes", te.test_text_out.text().startswith("Play Game"),
      te.test_text_out.text())
gshot(te, "A_text_table_editor")
w.tabs.setCurrentWidget(wd)
wd.load_table(str(tbl_path))
fp.mode.setCurrentIndex(2)
fp.find.setText("Play Game")
fp.replace.setText("Run & Gun")
check("A16 'Play Game' found through the table", wd.find_next() and wd.view.cursor == 0x2DAD, hex(wd.view.cursor))
check("A17 replaced by 'Run & Gun' (same length)", wd.replace(True) == 1 and b"Run & Gun\x00" in bytes(wd.buf.data))
wd.dump_strings()
check("A18 Find Text Strings with the table lists the menu", any("Run & Gun" in wd.results.item(k).text()
                                                                 for k in range(wd.results.count())))
gshot(w, "A_working_copy_edits")
check("A19 save the working copy", wd.save() and work.read_bytes() != CLEAN)

pm.fmt.setCurrentText("ips")
check("A20 Capture Edits as Patch -> patches/001_dabg_values.ips", pm.capture("dabg_values") and
      pm.rp.patches[-1].file.endswith(".ips"), [p.file for p in pm.rp.patches])
built = pm.build()
check("A21 Build -> build/DABG_RomHack_patched.nes, source ROM untouched", built is not None and built.is_file() and
      (hack / "rom" / "dabg.nes").read_bytes() == CLEAN)
check("A21b the build keeps the ROM's .nes extension (empty template + Set Source ROM)",
      built is not None and built.suffix == ".nes", built)
# the new table is not registered in rom.json by the Table Editor; the user adds it (no UI for it yet)
pm.rp.tables.append("tables/dabg.tbl")
pm.rp.save()
bdata = built.read_bytes()
check("A22 built ROM has every edit", bdata[OFF_LIVES + 1] == 9 and bdata[OFF_WALK + 1] == 3 and
      bdata[OFF_PAL + 4] == 0x16 and bdata[OFF_SKY + 1] == 0x27 and b"Run & Gun" in bdata)
gshot(pm, "A_patch_manager")
cv = feat.compare(str(hack / "rom" / "dabg.nes"), str(built))
check("A23 Compare Files: 6 difference runs", cv is not None and len(cv.ranges) == 6, getattr(cv, "ranges", None))
cv.goto_diff(1)
gshot(cv, "A_compare_original_vs_mod")

# =====================================================================================================  B
print("=== B: Disassemble ROM into Project", flush=True)
from radide.features import retro_dev  # noqa: E402
dis = WORK / "DABG_Disasm"
d = retro_dev.DisassembleDialog(w, str(hack / "rom" / "dabg.nes"))
d.folder.setText(str(dis))
d.show()
d.run()
check("B1 disassembly finished", wait(lambda: d.result_obj is not None or "Could not" in d.summary.text(), 120),
      d.summary.text())
check("B2 byte-identical rebuild", "byte-identical" in d.summary.text(), d.summary.text())
check("B2b system detected as NES", d.system.currentData() == "nes", d.system.currentData())
gshot(d, "B_disassemble_dialog")
d.open_project()
pump(2)
check("B3 disassembly project opened", w.project is not None and Path(w.project.folder) == dis)
main_s = dis / "main.s"
first = main_s.read_text(encoding="utf-8")
traced_before = first.count("\n        ") - first.count(".byte")
# The game jumps through RTS tables, so the tracer does not reach the life / speed code. The user adds hints.
import json  # noqa: E402
hints = json.loads((dis / "hints.json").read_text(encoding="utf-8"))
hints["code"] = ["8737", "8776", "8D9B"]
hints["labels"] = {"8737": "LoseLife", "8776": "WalkOrRun", "8D9B": "ResetPlayerX"}
hints["comments"] = {"8737": "player fell off / died: one life less", "8D9B": "lives at the start of a game"}
(dis / "hints.json").write_text(json.dumps(hints, indent=1), encoding="utf-8")
qh.MSGS.clear()
retro_dev.redisassemble(w)
pump(0.5)
text = main_s.read_text(encoding="utf-8")
check("B4 Re-disassemble with Hints: labels in the source", "LoseLife:" in text and "ResetPlayerX:" in text,
      qh.MSGS[-1:] if qh.MSGS else "")
check("B5 still byte-identical after the hints", any("byte-identical" in str(m).lower() for m in qh.MSGS), qh.MSGS)
check("B5b .bak of the old source kept", any(p.suffix == ".bak" for p in dis.iterdir()))
lines = text.splitlines()
k = next((n for n, ln in enumerate(lines) if ln.startswith("LoseLife:")), None)
dec_line = next((n for n in range(k + 1, k + 6) if "dec" in lines[n].lower()), None) if k is not None else None
check("B6 LoseLife starts with dec $76,x", dec_line is not None, lines[k:k + 6] if k is not None else "")
if dec_line is not None:
    # the code change: infinite lives (dec zp,x = 2 bytes -> 2 x nop)
    lines[dec_line] = "        nop                                     ; RAD IDE mod: infinite lives (was dec $76,x)"
    lines.insert(dec_line + 1, "        nop")
    main_s.write_text("\n".join(lines) + "\n", encoding="utf-8")
w.open_any_file(main_s)
pump(2)
ed = w.tabs.currentWidget()
gshot(w, "B_disasm_source_in_editor")
qh.MSGS.clear()
retro_dev.rebuild_check(w)
pump(0.5)
check("B7 Rebuild Check reports the change against the original", any("Different" in str(m) for m in qh.MSGS),
      qh.MSGS)
mod_rom = dis / "dabg.nes"
mdata = mod_rom.read_bytes()
check("B8 rebuilt ROM: only the 2 bytes changed", mdata[OFF_DEC:OFF_DEC + 2] == b"\xEA\xEA" and
      sum(1 for a, b in zip(mdata, CLEAN) if a != b) == 2, sum(1 for a, b in zip(mdata, CLEAN) if a != b))

# patches with the Create Patch dialog (IPS + BPS), apply to a clean copy (Apply Patch dialog), compare
from radide.retro.rom.dialogs import ApplyPatchDialog, CreatePatchDialog  # noqa: E402
pdir = WORK / "patches"
pdir.mkdir()
# the full mod = the values of A (built ROM) + the infinite-lives code change
full = bytearray(bdata)
full[OFF_DEC:OFF_DEC + 2] = b"\xEA\xEA"
full_rom = WORK / "dabg_mod.nes"
full_rom.write_bytes(bytes(full))
made = {}
for fmt_idx, ext in ((1, "ips"), (0, "bps")):
    cd = CreatePatchDialog(w, str(hack / "rom" / "dabg.nes"), str(full_rom))
    cd.fmt.setCurrentIndex(fmt_idx)
    cd.out.setText(str(pdir / f"dabg_mod.{ext}"))
    cd.meta.setText("DABG mod made with RAD IDE: 9 lives, infinite lives, faster, red player, sunset sky")
    if ext == "bps":
        gshot(cd, "B_create_patch_dialog")
    cd.accept()
    made[ext] = pdir / f"dabg_mod.{ext}"
    check(f"B9 Create Patch dialog writes {ext.upper()}", made[ext].is_file() and made[ext].stat().st_size < 200,
          made[ext].stat().st_size if made[ext].is_file() else None)
clean_copy = WORK / "clean_copy.nes"
clean_copy.write_bytes(CLEAN)
outs = {}
for ext, p in made.items():
    ad = ApplyPatchDialog(w, str(clean_copy), str(p))
    ad.out.setText(str(WORK / f"applied_{ext}.nes"))
    if ext == "bps":
        gshot(ad, "B_apply_patch_dialog")
    ad.accept()
    outs[ext] = WORK / f"applied_{ext}.nes"
    check(f"B10 Apply Patch ({ext.upper()}) to a clean copy gives the mod",
          outs[ext].is_file() and outs[ext].read_bytes() == bytes(full))
check("B11 the clean copy is unchanged", clean_copy.read_bytes() == CLEAN)
cv2 = feat.compare(str(outs["ips"]), str(outs["bps"]))
check("B12 Compare Files: IPS result == BPS result", cv2 is not None and len(cv2.ranges) == 0,
      getattr(cv2, "ranges", None))
from radide.retro.rom.patches import bps_info  # noqa: E402
bi = bps_info(made["bps"].read_bytes(), actions=False)
check("B13 BPS metadata + CRCs", "RAD IDE" in (bi.metadata or "") and bi.source_size == len(CLEAN), vars(bi))

# =====================================================================================================  C
print("=== C: the game's source as a project", flush=True)
srcp = WORK / "DABG_Source"
shutil.copytree(ORIG_SRC, srcp)
# The game builds with ca65 dabg.s + ld65 -C nrom256.x (its mk.bat); its graphics (ascii.chr) are packed into
# ascii.pb53 by pb53.py (Python 2). pb53_py3.py is our Python 3 port (marked as altered, zlib licence).
shutil.copy2(HERE / "pb53_py3.py", srcp / "pb53_py3.py")
radproj = {"name": "DABG", "language": "retro-nes", "forms": [], "startup": "dabg", "modules": ["dabg.s"],
           "retro": {"system": "nes", "lang": "asm", "main": "dabg.s", "cfg": "nrom256.x", "output": "dabg.nes",
                     "prebuild": ["{python} pb53_py3.py --raw ascii.chr ascii.pb53"]}}
(srcp / "project.radproj").write_text(json.dumps(radproj, indent=2), encoding="utf-8")
w.open_project(srcp, ask=False)
pump(2)
check("C1 source project opened as a NES (ca65) project", w.project is not None and
      w.project.language == "retro-nes" and Path(w.project.folder) == srcp)
qh.MSGS.clear()
retro_dev.rebuild_check(w)
pump(0.5)
check("C2 the unmodified source builds byte-identical to the release ROM",
      (srcp / "dabg.nes").is_file() and (srcp / "dabg.nes").read_bytes() == CLEAN, qh.MSGS[-1:])
w.open_any_file(srcp / "player.s")
pump(2)
gshot(w, "C_source_player_s")

# graphics: redraw the player's head in the Tile Editor - a red headband (colour 2 = red after the palette mod)
from radide.retro.gfx.ui_tiles import TileEditor  # noqa: E402
te2 = w.open_any_file(srcp / "ascii.chr")
pump(0.5)
check("C3 ascii.chr opens in the Tile Editor (NES format)", isinstance(te2, TileEditor) and te2.sheet.fmt.key == "nes")
chr_before = (srcp / "ascii.chr").read_bytes()
# sprite tiles are the second pattern table ($1000, OBJ_1000); player 1's head is tile $06 (newgame.s PlayerHead)
te2.set_offset(0x1000)
pump(0.2)
gshot(w, "C_tile_editor_sprites_before")
HEAD = 0x06
te2.sheet_view.set_selection(HEAD % te2.sheet.cols, HEAD // te2.sheet.cols, 1, 1)
pump(0.2)
blk = [row[:] for row in te2.pixels.block]
check("C4 player head tile decoded (not empty)", any(v for row in blk for v in row), blk)
te2.set_tool("pencil")
te2.palette.current = 2
pv = te2.pixels
pv.resize(320, 320)
sx, sy = pv.scale()
headband_row = next((y for y in range(8) if sum(1 for v in blk[y] if v) >= 4), 2)
for x in range(8):
    if blk[headband_row][x]:
        QTest.mouseClick(pv, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(x * sx + sx // 2, headband_row * sy + sy // 2))
pump(0.2)
check("C5 pencil drew the headband (colour 2)", sum(1 for v in te2.pixels.block[headband_row] if v == 2) >= 3,
      te2.pixels.block[headband_row])
gshot(w, "C_tile_editor_headband")
check("C6 Tile Editor writes ascii.chr", te2.save() and (srcp / "ascii.chr").read_bytes() != chr_before)
# source-level change: the 'Run & Gun' text, 9 lives
p_screens = srcp / "screens.s"
p_screens.write_text(p_screens.read_text(encoding="latin-1").replace('.byt "Play Game",0',
                     '.byt "Run & Gun",0 ; RAD IDE mod (altered source)'), encoding="latin-1")
p_new = srcp / "newgame.s"
p_new.write_text(p_new.read_text(encoding="latin-1").replace("ResetPlayerX:\n  lda #3",
                 "ResetPlayerX:\n  lda #9 ; RAD IDE mod (altered source): 9 lives"), encoding="latin-1")
p_main = srcp / "dabg.s"
p_main.write_text(p_main.read_text(encoding="latin-1").replace("  .byt $01, $16, $27, $21",
                  "  .byt $16, $16, $27, $21 ; RAD IDE mod (altered source): player 1 colour 2 red"),
                  encoding="latin-1")
qh.MSGS.clear()
retro_dev.rebuild_check(w)
pump(0.5)
sdata = (srcp / "dabg.nes").read_bytes()
check("C7 rebuilt from source: new graphics packed (prebuild) + text + lives",
      sdata != CLEAN and b"Run & Gun" in sdata and sdata[OFF_LIVES + 1] == 9 and
      sdata[OFF_PAL + 4] == 0x16, qh.MSGS[-1:])
check("C8 ascii.pb53 regenerated from the edited tiles", (srcp / "ascii.pb53").read_bytes() !=
      (ORIG_SRC / "ascii.pb53").read_bytes())

# =====================================================================================================  D
SHOT_ROMS = {"original": ORIG_ROM, "rommod": full_rom, "sourcemod": srcp / "dabg.nes"}
if not NO_EMU:
    print("=== D: emulator", flush=True)
    from radide.retro.emu import ui as emu_ui  # noqa: E402
    from radide.retro.emu.launch import run_rom  # noqa: E402
    # the IDE's Run in Emulator (Mesen 2 is the first NES emulator): start, let it run, stop what we started
    proc = emu_ui.start_rom(w, str(full_rom), "nes")
    check("D1 IDE starts the modded ROM in the NES emulator", proc is not None and proc.alive(),
          getattr(proc, "command", None))
    pump(4)
    check("D2 still running after 4 s", proc is not None and proc.alive())
    if proc is not None:
        proc.stop()
    lua_tpl = (HERE / "shots.lua").read_text(encoding="utf-8")
    for tag, rom in SHOT_ROMS.items():
        outdir = WORK / f"emu_{tag}"
        outdir.mkdir()
        lua = outdir / "shots.lua"
        lua.write_text("OUTDIR = [[" + str(outdir).replace("\\", "/") + "]]\n" + lua_tpl, encoding="utf-8")
        p = run_rom(str(rom), "nes", emulator="fceux", lua=str(lua), quiet=True)
        done = outdir / "done.txt"
        t = time.time()
        while time.time() - t < 60 and not done.is_file():
            pump(0.5)
        p.stop()
        got = sorted(x.name for x in outdir.glob("*.png"))
        check(f"D3 FCEUX ran the {tag} ROM and saved {len(got)} screenshots", len(got) >= 8 and done.is_file(), got)
        if done.is_file():
            print(tag, done.read_text(), flush=True)
        for png in got:
            shutil.copy2(outdir / png, SHOTS / f"D_{tag}_{png}")
    lives = {tag: (WORK / f"emu_{tag}" / "done.txt").read_text() for tag in SHOT_ROMS
             if (WORK / f"emu_{tag}" / "done.txt").is_file()}
    check("D4 lives counter in RAM: 3 in the original, 9 in the mods", lives.get("original", "").startswith("lives=3")
          and lives.get("rommod", "").startswith("lives=9") and lives.get("sourcemod", "").startswith("lives=9"), lives)

# keep the projects as the curated sample (generated files removed)
if "--keep" in sys.argv:
    for name in ("DABG_RomHack", "DABG_Disasm", "DABG_Source"):
        dst = HERE / "projects" / name
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(WORK / name, dst, ignore=shutil.ignore_patterns("_build", "*.o", "*.lst", "*.bak", "__pycache__",
                                                                          ".radide"))
    shutil.rmtree(HERE / "patches", ignore_errors=True)
    shutil.copytree(pdir, HERE / "patches")
qh.finish(w)
