# GameMod_DABG - modding a real open-source NES game with RAD IDE

The request was "a game like Contra". Contra is a commercial ROM, so this sample does not use it. It uses a free
homebrew NES action-platformer where you shoot enemies with blasters:

| | |
|---|---|
| Game | **Double Action Blaster Guys** (DABG), (c) 2012-2014 NovaSquirrel. 1-4 players, 52 levels, 25+ enemy types |
| Licence | **zlib** (`LICENSE.txt`). You may modify and redistribute it. Altered versions must be marked as altered, and the notice must stay |
| Official source | https://github.com/NovaSquirrel/DABG (master, commit `5ecc60b6af3f726851bfeb1c2555388c5953e0c0`) |
| ROM | https://github.com/NovaSquirrel/DABG/releases/download/v2/dabg.nes (32,784 bytes, SHA-256 `eca79b9d0b546e96c1bc73099e239539fb9c7773ff10a431bb3a9cd6763208ca`) |

`original/` holds the release ROM and an unchanged copy of the source. Built with cc65, the source gives back the
release ROM byte for byte. Every changed file in `projects/` is an altered version: the changed lines say
`RAD IDE mod (altered source)`, and `pb53_py3.py` is marked as a port.

## What the mod does

* 9 lives instead of 3, and infinite lives (the `dec PlayerLives,x` is replaced with two `nop`)
* walk speed 3 instead of 2, run speed 6 instead of 4
* the player is red: the sprite palette entry changes from $01 to $16
* sunset sky: $31 becomes $27
* the menu reads "Run & Gun" instead of "Play Game"
* source version only: a red headband on the player's head tile, drawn in the Tile Editor

## Steps through the IDE (`test_gamemod_ide.py`, 88 checks)

1. **ROM Hacking Project** (New Project > Retro > ROM Hacking Project, then Patch Manager > Set Source ROM). The ROM
   Info panel shows NES 2.0, mapper 0 (NROM), 32 KB PRG and CHR RAM, plus the vectors. The source ROM opens
   read-only.
2. **Edit Working Copy** in the hex editor:
   * Hex search with wildcards (`A9 03 95 ?? BC`) finds the start-lives code. The data inspector shows
     `LDA #$03` at CPU $8D9B. Typing `09` makes it 9 lives.
   * The speed code (`ldy #2 ... ldy #4`) and the palette table / sky colour are found and edited the same way.
3. **Text through a table.** In the Text Table Editor, take the ASCII table, add `/00=<end>`, check it and save it
   as `tables/dabg.tbl`. The saved table joins the project by itself (`rom.json` `tables`, Solution Explorer >
   ROM Hacking > Tables). The Tables context menu sets it as the default table (the hex editor selects it) and
   removes / adds tables. In the hex editor:
   * Text (table) search / Replace All changes "Play Game" to "Run & Gun".
   * Find Text Strings lists the menu.
4. **Capture Edits as Patch** writes `patches/001_dabg_values.ips`. **Build** writes
   `build/DABG_RomHack_patched.nes`. **Compare Files** shows 6 difference runs. The **Emulator** toolbar chooses
   the project's emulator (`rom.json` `emulator`; Automatic = the first installed one).
5. **Disassemble ROM into Project** gives a byte-identical rebuild. The game jumps through RTS tables
   (`lda Tab+1,x / pha / lda Tab,x / pha / rts`). The tracer follows them now: 7022 instructions on the first
   pass (831 before), and the tables are written as `.word L95D0-1`. Hints are added from the editors:
   * the hex editor's context menu on `rom/dabg.nes` at file offset $747: Disassembly Hints > Mark as Code ($8737)
   * the source editor's context menu on the `MainColors` line: Mark as Data ($DCFB)
   * labels `LoseLife`, `WalkOrRun`, `ResetPlayerX` and two comments.

   Each hint goes into `hints.json` (shown in Solution Explorer) and re-disassembles.
   * Code change: `dec $76,x` becomes `nop` / `nop` (infinite lives).
   * Rebuild Check reports "different: 2 bytes at $747".
6. **Patches**:
   * The Create Patch dialog writes `patches/dabg_mod.ips` and `patches/dabg_mod.bps` (BPS with metadata and CRCs).
   * The Apply Patch dialog applies each patch to a clean copy, and both results equal the mod.
   * Compare Files shows the IPS and BPS results are the same.
7. **The game's own source as a NES (ca65) project** (`projects/DABG_Source/project.radproj`):
   * Settings: `main` `dabg.s`, `cfg` `nrom256.x`, and `prebuild` runs `{python} pb53_py3.py --raw ascii.chr ascii.pb53`.
   * The unmodified source builds byte-identical.
   * `ascii.chr` opens in the Tile Editor. Draw on sprite tile $06 (player 1's head) at offset $1000 and save.
   * Rebuild: the prebuild packs the new graphics, and the edited text, lives and palette are in the ROM.
8. **Labels from the game's build** (E): the IDE's ca65 build of the source writes `_build/game.dbg`. **Import
   Labels into Hints** merges 860 names into a copy of the disassembly. The re-disassembly is byte-identical
   and reads `ResetPlayerX:`, `dec PlayerLives,x`, `ObjectTable:`.
9. **Tile Editor on the ROM itself** (F). DABG is a CHR-RAM game: its font and sprites are PB53-compressed in the
   PRG ROM.
   * **Compressed Graphics... > Find Graphics** (PB53) finds the block at $5D17: 4811 bytes, 512 tiles.
   * The block opens in the editor and the player's head tile gets a headband.
   * **ROM Palette...** (`nes_slot` at `MainColors`, sub-palette 4, slot 2) shows the player in the ROM's colours.
     Changing the slot to $2A (green) writes the byte back.
   * Save packs the tiles again (size check against the old stream + free bytes) and writes the ROM.
10. **Emulator**:
   * The Emulator toolbar set to FCEUX: Run in Emulator starts FCEUX for that project.
   * The IDE's Run in Emulator (`radide.retro.emu.ui.start_rom`, Automatic) starts the mod in Mesen 2 for 4 s, then
     stops it.
   * The original, the ROM mod and the source mod then each run in FCEUX with `shots.lua`. The script drives the
     menus, saves screenshots with FCEUX's own `gui.savescreenshotas` and reads the lives counter from RAM: 3, 9
     and 9.
   * Mesen 2's headless test runner (`radide/retro/emu/mesenshot.py`: `--testRunner`, Lua `emu.takeScreenshot()`,
     PNG sent as hex on stdout) plays the tile-edited ROM into the game: `F_mesen_tile_rom_*.png`.

## The gaps, closed (`test_gamemod_gaps_core.py`, 54 checks, no Qt)

This test covers the codecs, ROM palettes, jump tables, hints, label importers (.dbg / .mlb / .nl / .sym), the
emulator choice and Mesen screenshots on synthetic data and on DABG. Run it with
`.venv\Scripts\python.exe samples\Tests\Retro\GameMod_DABG\test_gamemod_gaps_core.py`.

Screenshots are in `shots/`. `A_*`, `B_*`, `C_*` and the IDE `F_*` are `widget.grab()` captures. `D_<rom>_*`
(FCEUX), `E_mesen_*` and `F_mesen_*` (Mesen 2) were saved by the emulators.

Run it with `.venv\Scripts\python.exe samples\Tests\Retro\GameMod_DABG\test_gamemod_ide.py [--no-emu] [--keep]`
(add `QA_REAL=1` so the Monaco editor shows in the shots). `--keep` copies the projects and patches back into this
folder.
