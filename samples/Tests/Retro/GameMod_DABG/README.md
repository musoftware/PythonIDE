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

## Steps through the IDE (`test_gamemod_ide.py`, 58 checks)

1. **ROM Hacking Project** (New Project > Retro > ROM Hacking Project, then Patch Manager > Set Source ROM). The ROM
   Info panel shows NES 2.0, mapper 0 (NROM), 32 KB PRG and CHR RAM, plus the vectors. The source ROM opens
   read-only.
2. **Edit Working Copy** in the hex editor:
   * Hex search with wildcards (`A9 03 95 ?? BC`) finds the start-lives code. The data inspector shows
     `LDA #$03` at CPU $8D9B. Typing `09` makes it 9 lives.
   * The speed code (`ldy #2 ... ldy #4`) and the palette table / sky colour are found and edited the same way.
3. **Text through a table.** In the Text Table Editor, take the ASCII table, add `/00=<end>`, check it and save it
   as `tables/dabg.tbl`. In the hex editor:
   * Text (table) search / Replace All changes "Play Game" to "Run & Gun".
   * Find Text Strings lists the menu.
4. **Capture Edits as Patch** writes `patches/001_dabg_values.ips`. **Build** writes
   `build/DABG_RomHack_patched.nes`. **Compare Files** shows 6 difference runs.
5. **Disassemble ROM into Project** gives a byte-identical rebuild. The game jumps through RTS tables, so on the
   first pass the tracer reaches only 831 instructions. Three `code` hints in `hints.json` plus **Re-disassemble with
   Hints** raise that to 4354 instructions and add the labels `LoseLife`, `WalkOrRun` and `ResetPlayerX`.
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
8. **Emulator**:
   * The IDE's Run in Emulator (`radide.retro.emu.ui.start_rom`) starts the mod in Mesen 2 for 4 s, then stops it.
   * The original, the ROM mod and the source mod then each run in FCEUX with `shots.lua`. The script drives the
     menus, saves screenshots with FCEUX's own `gui.savescreenshotas` and reads the lives counter from RAM: 3, 9
     and 9.

Screenshots are in `shots/`. `A_*`, `B_*` and `C_*` are `widget.grab()` captures of the IDE. `D_<rom>_*` were saved
by the emulator.

Run it with `.venv\Scripts\python.exe samples\Tests\Retro\GameMod_DABG\test_gamemod_ide.py [--no-emu] [--keep]`
(add `QA_REAL=1` so the Monaco editor shows in the shots). `--keep` copies the projects and patches back into this
folder.
