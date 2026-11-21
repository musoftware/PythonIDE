# Retro/RomTools - ROM workbench tests

Slice "rom" of the retro support (`radide/retro/rom`, `radide/features/retro_rom.py`,
`radide/languages/retro_romhack.py`; docs/RETRO.md "ROM workbench").

| Test | What it checks |
|------|----------------|
| `test_rom_core.py` | No Qt. IPS / UPS / BPS against hand-computed byte vectors (incl. IPS RLE, truncation, the 0x454F46 "EOF" offset; UPS reverse; BPS SourceCopy / TargetCopy / metadata; CRC32 errors), 150 random round trips per format, a 2 MB BPS with a moved block; header detection of every system on synthetic ROMs (NES / NES 2.0, GB / GBC, GBA, SNES LoROM / HiROM + copier header, Genesis, Atari 2600 bankswitch guess, 7800, CAR, ATR, XEX, C64 PRG / D64 / T64, ZX TAP / TZX / SNA, DOS MZ / COM, patch files); checksum repair (GB, GBC, GBA, SNES, Genesis, CAR); .tbl tables + relative search; hex buffer undo / redo / wildcard search / replace; ROM Hacking project build, disabled patch, capture edits, referenced ROM, original never written; the `python -m radide.retro.rom` command line. |
| `test_hex_ui.py` | The IDE (qh.py harness, offscreen, QSettings "RADIDE-TEST"): a .nes opens in the hex editor with the ROM info + structure overlay, typing / Ctrl+Z / Ctrl+Y, insert mode, Ctrl+F hex search with wildcards, text Find All, Replace All, Save All, the inspector (6502 opcode + CPU address), Fix Header Checksum on a GB ROM, Compare Files, then a ROM Hacking project: Solution Explorer nodes, read-only source ROM, Patch Manager build, Edit Working Copy + Capture Edits as Patch, rebuild. Screenshots in `%TEMP%\radide-qa\shots\retro_rom_*.png`. |

    python samples/Tests/Retro/RomTools/run_all.py

All ROMs are generated on the fly by `radide/retro/rom/synth.py` (original homebrew bytes, CC0) - no commercial
ROM or game data is used or downloaded. See also the sample project `../RomHackDemo`.
