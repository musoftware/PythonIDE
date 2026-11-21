# Retro game designers - tests

Tests of `radide/retro/design/game` (Atari 2600 / NES / Game Boy / DOS mode 13h designers). See docs/RETRO.md,
"Retro game designers".

```
.venv\Scripts\python.exe samples\Tests\Retro\DesignGames\test_gamedesign_core.py   [--no-emu]
.venv\Scripts\python.exe samples\Tests\Retro\DesignGames\test_gamedesign_ui.py
```

* `test_gamedesign_core.py` (no Qt): encodings and generators, then real builds with DASM, ca65 / ld65, RGBDS,
  NASM, FreeBASIC (DOS, inside DOSBox-X) and OpenWatcom. Each build is checked headless (6502 / TIA probe, NES
  probe, 8086 emulator, DOSBox-X `/SHOT` capture compared with the design) and the result is started in Stella,
  Mesen, mGBA and DOSBox-X for a few seconds. Tools that are not installed are skipped - install them from
  Tools > Retro (development toolchains, DOS toolchains, emulators). `RADIDE_RETRO_TOOLPATH` can point at extra
  tool folders.
* `test_gamedesign_ui.py` (qh.py harness, offscreen, QSettings "RADIDE-TEST"): the designers inside the IDE.

Work files go to `%TEMP%\radide-gamedesign-test` and the QA work folder; screenshots to `%TEMP%\radide-qa\shots`.
