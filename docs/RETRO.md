# Retro computing, old games and old NASA programs

Each slice of radide/retro (and radide/agc) documents itself in its own section below.

## Emulators (slice "emu": `radide/retro/emu`, `radide/features/retro_emu.py`, `radide/languages/retro_dos.py`)

RAD IDE never bundles an emulator, a BIOS or a game. On request (**Tools > Retro > Emulators...**) it
downloads the pinned portable Windows build of a free emulator from the project's **official GitHub releases
page** into `%LOCALAPPDATA%\RADIDE\tools\<id>`. There is no installer, no admin and no winget. The SHA-256 is
checked (GitHub's release `digest`, or measured when this version was written) and recorded in
`tools\<id>\RADIDE-SOURCE.json`. GPL emulators run only as separate programs. The tools are meant for the user's own
ROMs, homebrew and DOS programs.

| id | Emulator | Systems | Licence | Pinned build | Debugging from RAD IDE |
|---|---|---|---|---|---|
| `stella` | Stella | Atari 2600 (`a2600`) | GPL-2.0 | 7.0c `Stella-7.0c-windows.zip` | `-debug` opens Stella's debugger. A DASM `-s` symbol file and `-l` listing are copied next to the ROM as `<rom>.sym` / `<rom>.lst`, so labels and source show. `-break <addr>` |
| `mesen` | Mesen 2 | NES, SNES, GB/GBC, PC Engine, SMS/GG | GPL-3.0 | 2.1.1 `Mesen_2.1.1_Windows.zip` (needs .NET 8 Desktop Runtime) | Mesen's debugger. ld65 `.dbg`, RGBDS `.sym`, `.mlb`, `.cdl` files next to the ROM are imported by Mesen; a `.lua` script is passed on the command line |
| `fceux` | FCEUX | NES (fallback) | GPL-2.0 | 2.7.0 `fceux-2.7.0-win64.zip` | `-lua <script>`, FCEUX debugger, `.nl` name lists |
| `mgba` | mGBA | GBA, GB, GBC | MPL-2.0 | 0.10.5 `mGBA-0.10.5-win64.7z` (unpacked with Windows' bsdtar) | `-g` starts the GDB stub on port 2345. The **Retro Debugger** dock speaks GDB RSP itself (`gdb_rsp.py`): registers r0-r15 + CPSR, memory, breakpoints, step, break, continue. With an `arm-none-eabi-gdb` you can also run `target remote :2345` |
| `vice` | VICE x64sc | Commodore 64 | GPL-2.0 | 3.10 `GTK3VICE-3.10-win64.7z` | **Binary monitor** on a free TCP port (`vice_monitor.py`): ping, info, break, continue, step / step over, registers, memory get/set, checkpoints, autostart (hot reload), reset, keyboard feed. VICE labels (`al C:xxxx .name`) or `name = $xxxx` listings are loaded with `-moncommands` |
| `atari800` | Atari800 | Atari 8-bit (`a8`) | GPL-2.0 | 7.2.1 `atari800-7.2.1-win64.zip` | `-monitor`, `-label-file`, `-bpc <addr>`. It uses its built-in free AltirraOS ROMs. Altirra is used when it is on PATH or in `tools\altirra`, but it is not downloaded automatically |
| `dosbox-x` | DOSBox-X | MS-DOS programs (`dos`) | GPL-2.0 | 2026.10.01 `dosbox-x-vsbuild-win64-...-portable.zip` | Generated `.conf`; DOSBox-X's own debugger |

Portable settings: mGBA gets `portable.ini` next to its exe. Mesen gets `settings.json` next to `Mesen.exe`, which is
Mesen's portable mode, so nothing goes to `Documents\Mesen2`. Stella uses `-basedir %LOCALAPPDATA%\RADIDE\retro\stella`.
VICE uses `-config ...\retro\vice\vice.ini -logfile ...` and `-autostartprgmode 1`, which injects programs into RAM so
no autostart disk image is written. VICE still creates `%APPDATA%\vice` for its startup log. Atari800 uses
`-config ...\retro\atari800\atari800.cfg -no-autosave-config`. DOSBox-X gets `<project>\.radide\dosbox-x.conf`. DOSBox-X still writes its default
`%LOCALAPPDATA%\DOSBox-X\dosbox-x-<version>.conf` on its first start, and there is no switch to prevent it.
You can set your own emulator paths in the manager (QSettings `retro/emu/<id>`).

### API for the other retro slices

```python
from radide.retro.emu import run_rom, detect_system, find_emulator, status
proc = run_rom(path, system=None, debug=False, symbols=None, emulator=None,
               minimized=False, quiet=False, breakpoints=[...], lua=..., initbreak=...)   # -> RetroProcess
proc.emulator, proc.command, proc.pid, proc.alive(), proc.wait(t), proc.stop()   # stop: only what RAD IDE started
proc.debug_backend            # "vice-monitor" | "gdb-rsp" | ""
proc.monitor()                # ViceMonitor (C64)      proc.gdb()  # GdbRsp (mGBA)
proc.reload(new_rom)          # VICE: autostart through the monitor (hot reload); others: restart with the same options
proc.rebuild = callable       # optional: reload() calls it to rebuild first and get the ROM path
from radide.retro.emu.launch import command_for, last_process   # command without starting / the last emulator
from radide.retro.emu.ui import start_rom, hot_reload            # IDE versions (log, Retro Debugger dock)
```

* `system` ids: `a2600 a8 nes snes gb gbc gba pce sms gg c64 dos` (`catalog.SYSTEM_TITLES`). `detect_system(path)`
  calls `radide.retro.rom.detect.detect_system(path)` (or `radide.retro.rom.detect_system`) first when the ROM
  workbench slice provides it. Otherwise it decides from the extension and magic bytes (iNES, GBA fixed byte,
  GB header, C64 CRT, ATR, XEX, MZ without PE, 2600 reset vector). A folder means `dos`.
* `symbols`: a path or a list of paths: `.sym`, `.lst`, `.dbg`, `.mlb`, `.lbl`, `.lua` or a label listing.
  `ui.start_rom` picks up `<rom>.sym/.lst/.dbg/.lbl/.mlb` automatically.
* Errors: `launch.EmuError`. When no emulator is installed, its message tells the user to open Tools > Retro >
  Emulators...
* CLI: `python -m radide.retro.emu status | install <id> | run <rom> [--debug] [--symbols f] | dos <folder|program>`.

### Hot reload

**Tools > Retro > Reload ROM in Emulator** (Ctrl+Shift+Alt+F5) or the dock's **Reload ROM** button (`ui.hot_reload` /
`RetroProcess.reload`). In VICE the program is loaded again in place: the monitor runs `autostart` and the emulator
keeps running. Stella, Mesen, FCEUX, mGBA and Atari800 have no reload command on their command line or protocol, so
RAD IDE restarts them with the same options. When a GDB or monitor session was attached, the Retro Debugger attaches
to the restarted emulator again.

### DOS programs and legacy DOS development

* **New Project > Retro > DOS Program** (`retro-dos` plugin) has two templates:
  * Existing DOS Program: copy in a program or game you own.
  * DOS .COM in Assembly: NASM builds it on Windows, using the downloader of `radide/asm/toolchain.py`.

  To write new QBasic, Pascal, C or MASM programs for DOS, use the "DOS" project family of the dosdev slice
  (`radide/retro/dos`). That slice finds DOSBox-X through `radide.retro.emu.manager`.
* **File > Open Folder** on a folder whose `.EXE` files are MZ programs without a PE/NE/LE header (or `.COM`
  files) offers "DOS program (DOSBox-X)". The detector is registered by `features/retro_emu.py` into
  `project_detect.DETECTORS`. It writes only `project.radproj` with a `"dos"` block and never touches the user's files.
* `project.radproj` `"dos"` block (`dos.DosSettings`) has these keys: `program`, `args`, `cycles` (auto / max / fixed N),
  `machine` (svga_s3, vgaonly, ega, cga, tandy, hercules, pcjr), `memsize`, `sound` (sb16, sbpro2, sb1, gus, none),
  `mounts` (`[{"drive","path","type": dir|cdrom|floppy}]`, ISO/IMG through `imgmount`), `toolchain`, `build`,
  `exit_after` and `fullscreen`. Edit them in **Project > DOS Settings...**.
* F5 runs `python -m radide.retro.emu dos <folder|file>`. It writes `.radide/dosbox-x.conf`, which mounts the folder as
  C: and the toolchain folder as T:, then starts DOSBox-X with `-conf ... -nopromptfolder -fastlaunch`. On Windows
  DOSBox-X runs inside a job object, so the IDE's Stop also closes it.
* Compilers for sources inside an existing program's folder: RAD IDE ships none. NASM, which is free, builds
  `.COM` files on the host. For Pascal, C and BASIC, the project's toolchain folder is searched for one of these compilers and the build runs inside DOSBox-X:
  * TPC/BPC (Turbo/Borland Pascal, your copy).
  * PPC386/FPC (Free Pascal go32v2, GPL/LGPL).
  * TCC/BCC (Turbo/Borland C, your copy).
  * WCL (Open Watcom, OWPL).
  * QB/QBASIC (Microsoft, your copy; not redistributable).
  * BC.
  * FBC (FreeBASIC DOS, GPL).

  You can also give your own `build` command with `{src}` / `{stem}` placeholders. The dosdev slice downloads
  the free compilers.

### Tests (`samples/Tests/Retro/Emulators`)

`homebrew.py` writes tiny original test programs byte by byte (CC0):
* a 2600 frame loop
* an NROM NES colour cycler
* a GB palette loop
* a GBA mode-3 loop
* a C64 `SYS 2061` border flasher
* an Atari 8-bit XEX
* a DOS `HELLO.COM`

`test_emu.py` covers:
* emulator detection and system detection
* command lines and config generation
* launching every installed emulator minimised for about 4 seconds (it kills only the processes it started)
* the VICE binary monitor against a real x64sc: connect, info, break, registers, memory, checkpoint hit, step,
  autostart
* the mGBA GDB stub: registers, memory, breakpoint hit, step, interrupt
* DOSBox-X running HELLO.COM with its output redirected to a file
* the DOS Program plugin and the Open Folder detection
* the IDE UI (manager dialog, Retro Debugger attached to VICE, DOS Settings), using QSettings `RADIDE-TEST`

Run it with `python samples/Tests/Retro/Emulators/test_emu.py` (`--download` installs missing emulators first).

## Graphics and game text (slice "gfx": `radide/retro/gfx`, `radide/features/retro_gfx.py`)

Tools for editing the graphics and the text **inside** old games and homebrew binaries - the user's own files.
Menu: **Tools > Retro > Graphics & Text**.  Opening a `.chr` file shows the Tile Editor, `.tbl` the Text Table
Editor, `.rtmap` the Tile Map Editor and `.rtpf` the Playfield Editor (File > Open File and Solution Explorer;
the openers are wrapped after the hex editor's, so these extensions reach these editors).  All documents join
File > Save / Save All and the "save changes?" prompt of the tab.

### Tile / sprite editor (`ui_tiles.py`, core `codecs.py`, `tilesheet.py`, `palettes.py`, `pngio.py`)

* Works directly on the bytes of any file (a ROM, a CHR bank, a .bin); "Write to File" / Ctrl+S writes the
  bytes back (the file never grows), and every other open editor of that file is refreshed.
* Formats: 1bpp (generic / ZX / C64 hires charset), NES 2bpp planar (CHR), Game Boy / SNES 2bpp, SNES / PC
  Engine 4bpp planar, Mega Drive 4bpp, GBA 4bpp, C64 multicolour charset (double-wide pixels), C64 hires and
  multicolour sprites (63 data bytes in a 64-byte block - the padding byte is kept), Atari 2600 player graphics
  (8 pixels x *height* bytes, optional "upside down" storage, preview with **Reflect (REFP)** and all 8 **NUSIZ**
  modes on a 160-clock line, and a `.byte %........` listing).
* Navigation like Tile Molester / YY-CHR (own implementation): hex offset, +/-1 byte, +/- tile, +/- row,
  page up / down, columns, rows, zoom, grid.  For iNES files the offset starts at the CHR-ROM.
* Tools: pencil, fill, line, select (block of tiles), edit 1x1 / 2x2 / 4x4 / 8x8 tiles, flip H / V, rotate,
  clear, right-click = eyedropper, undo / redo (byte-level history).
* Palettes: Atari 2600 NTSC and PAL (128, generated from a colour-signal model), NES (64, generated), Game Boy
  DMG greens / Pocket greys, C64, EGA, greyscale.  Click a slot to draw with it, double-click to pick its
  system colour (the 2600 picker shows the COLUxx value).
* PNG export (page) / import (quantised to the current colour slots, from the selected tile on; a 2x / 4x
  scaled picture is scaled back).

### Atari 2600 playfield (`ui_playfield.py`, core `atari2600.py`)

40 x N blocks; the header shows which register drives each block (PF0 bits 4-7 left to right, PF1 bits 7-0,
PF2 bits 0-7), the status bar the exact register / bit.  Repeated, reflected (CTRLPF REF) or asymmetric
(6 tables) playfields.  Export DASM / ca65 / ACME `%binary` tables or C arrays (optionally bottom row first);
read from / write into a ROM (separate tables or interleaved; PF0's undisplayed low nibble is preserved).
Saved as `.rtpf` (JSON).

### Tile maps and metatiles (`ui_tilemap.py`, core `tilemap.py`)

NES nametables (32x30 + the 64-byte attribute table computed from the per-cell palette numbers), Game Boy
BG maps (32x32) and generic byte maps.  The tile set is any file + offset + format (relative to the `.rtmap`;
the map redraws when the Tile Editor writes that file).  Paint / pick / fill, metatiles (2x2) made from the map
and stamped with the Metatile tool, "As metatiles" export (unique 2x2 definitions + metatile map).  Export
ca65 / DASM / RGBDS / NASM / ACME / WLA data or C arrays; read from / write into a ROM.

### Text tables and script dump / insert (`ui_text.py`, core `textable.py`, `script.py`, `arabic.py`)

* `.tbl` editor: `XX=text`, multi-byte keys (`8140=...`, dictionary entries), `/XX=<end>` end codes,
  `*XX` line breaks; unknown bytes are kept as `<$XX>` so a dump / insert round trip never loses data.
  Check (bad lines, duplicates, no end code), test boxes (hex -> text, text -> hex).
* **Script Dump / Insert**: strings found through a pointer table (2 / 3 / 4 bytes, little / big endian,
  `file offset = pointer - base + add`) or in hex ranges split at end codes, shown in a sheet (original,
  translation, bytes used / available, red when too long or a character is missing).  The sheet saves to /
  loads from UTF-8 CSV for translators.  Insert **in place** (each string must fit its space; padded) or
  **repack** into a region with every pointer recalculated and identical strings stored once.  Nothing is
  written when a string does not fit or a character is missing - the report lists every problem.  The result
  goes to `<name>_translated.<ext>` unless another file is chosen.
* **Arabic ROM translation**: "Add Arabic Letter Forms" gives every contextual letter form (isolated / initial /
  medial / final and the lam-alef ligatures, Unicode Presentation Forms-B, about 127 codes) its own byte from a
  chosen start code.  On insert, **Shape Arabic** picks the right form for each letter and **Right-to-left
  (visual order)** reverses each line (digits, Latin runs and `<codes>` keep their order) because the old engine
  prints tiles left to right.  Then draw the glyphs into the game's font tiles with the Tile Editor (the code of
  each form is in the table).  Diacritics are dropped by the shaper (no space for them in 8x8 fonts).

### Shared helpers for the retro slices

* `radide/retro/filebus.py` - `file_changed(win, path, source)`: every open tab / dock widget whose
  `retro_path` (or `retro_watch` list) is *path* and that has `reload_from_disk()` is reloaded, except
  *source*; `subscribe(win, callback)` for non-widgets.  The tile, playfield, map and script tools call it after
  writing into a file, so a hex editor of the ROM slice refreshes when it exposes `retro_path` +
  `reload_from_disk()`.
* `radide/retro/menu.py` - `retro_menu(win)` (Tools > Retro) and `section(win, title)` sub-menus.
* Note: `radide/retro/rom/tbl.py` (ROM slice, hex editor text view / search) reads the same `.tbl` format;
  `radide/retro/gfx/textable.py` is the editor / script-insert side.

### Tests (`samples/Tests/Retro/Gfx`)

* `test_gfx_core.py` - 79 checks, synthetic data: random round trips for every tile format, known bit layouts,
  C64 sprite padding, 2600 upside-down storage, undo / redo, flip / rotate / fill / line, iNES CHR offset, PNG
  export / import / quantise / scaled / double-wide, 2600 playfield bit order (PF0/PF1/PF2, repeat / reflect,
  asymmetric ROM write / read, interleaved, PF0 low nibble kept), NUSIZ / reflect, NES attribute table,
  metatiles, asm / C export, `.tbl` parse / decode / encode, dump / insert with pointers (in place, repack,
  overflow refused, missing end code added, duplicates shared, ranges, CSV), Arabic shaping / visual order /
  insert.
* `test_gfx_ui.py` - 46 IDE checks with `qh.py` (offscreen, QSettings "RADIDE-TEST", `widget.grab()` shots):
  menu, `.chr` / `.rtmap` / `.rtpf` / `.tbl` open the editors, pencil and fill by mouse, undo / redo, write back,
  file-bus refresh of the tile map, the tile editor and the ROM slice's hex editor, View Current File as Tiles, PNG, 2600 player preview, playfield click + ROM
  write, table check, script dump + Arabic sheet + repack insert, Arabic UI.
* `make_sample.py` regenerates `Sample/` (original CC0 data, see the README there).

Not done yet: SNES 8bpp / mode 7 and NES 8x16 sprite ordering, palette data read from the ROM itself
(CGRAM / NES palette tables), a font-tile generator that renders Arabic glyphs into tiles automatically, DTE /
dictionary compression on insert, a tutorial course.

## ROM workbench (slice "rom": `radide/retro/rom`, `radide/features/retro_rom.py`, `radide/languages/retro_romhack.py`)

Hex editor, ROM / disk / tape detection, checksum repair, IPS / BPS / UPS patches and the **ROM Hacking Project**.
The tools work on the user's own files; nothing here downloads or ships game data (tests and samples use the
original homebrew images of `synth.py`).

### Hex editor (`hexview.py`, `hexdoc.py`, core `buffer.py`, `formats.py`, `inspector.py`, `tbl.py`)

* Opens automatically for ROM / image / patch extensions (`.nes .fds .gb .gbc .gba .sfc .smc .md .gen .smd .sms .gg
  .a26 .a78 .xex .atr .car .d64 .t64 .tzx .sna .ips .bps .ups ...`) from File > Open, Solution Explorer and
  `win.open_file`; `.bin .rom .prg .tap .dat .sav` when the content is binary. It wraps `open_any_file` /
  `open_file` after editor_extras, so ROMs get this editor and other binaries keep the generic hex view.
  Tools > Retro > ROM Workbench > Open in Hex Editor... opens anything.
* Virtualised painting (only visible rows; 64 MB files scroll instantly), 8 / 16 / 32 bytes per row, overwrite /
  insert (Insert key), nibble editing, hex and text columns (Tab switches), selection by mouse / Shift, undo /
  redo where one typed byte (both nibbles) is one step, save point (the tab's `*`), atomic save.
* Copy As: hex, compact hex, C array, `db` (NASM / FASM / MASM), `.byte` (ca65 / DASM), `dc.b` (68000), `DEFB`
  (Z80), Python bytes, Base64, text. Paste takes hex text in the hex column.
* Go To (Ctrl+G: `1F0` hex default, `$1F0`, `0x1F0`, `1F0h`, `#496` decimal, `+10` / `-20` relative), bookmarks
  (Ctrl+F2 toggle, F2 / Shift+F2 next / previous, Bookmarks panel).
* Find / Replace bar (Ctrl+F, F3 / Shift+F3): hex with `??` (any byte), `A?` / `?F` (nibble) and `*` (any run)
  wildcards, text in Latin-1 / ASCII / Shift-JIS / CP437 / EBCDIC with case and `?` / `*` wildcards, or text
  through the loaded table; Find All lists hits in Results; Replace / Replace All. Searches compile to a byte
  regex (C speed).
* Data inspector: offset, binary, int8..int64 LE / BE signed / unsigned, float32 / 64 LE / BE, BCD, ASCII, the
  table character, the **6502 instruction** at the cursor (all 151 official opcodes, branch targets resolved)
  and the CPU address of the byte (NES PRG mapping, GB banks, SNES LoROM / HiROM, C64 load address, XEX
  segments, 2600 / 7800 cart window, DOS image) plus the header field under the cursor.
* Character tables (`.tbl`: `XX=text`, multi-byte `XXYY=text`, `/XX` end codes, `*XX` line breaks): the text
  column, text search / replace and typing use them. Relative search finds a word stored with an unknown
  letter encoding and builds a table from the hit; "Find Text Strings" dumps runs of table text. Tables listed
  in a ROM Hacking project are preloaded.
* Structure overlay: the detected header fields are coloured by kind (magic, size, flags, title, checksum,
  vector, region) with a tooltip; clicking a row of the ROM Info panel selects the field.
* Compare Files (`diffview.py`): two read-only views scrolling together, differing bytes in red, a list of the
  difference runs, Next / Previous Difference.
* The tab protocol of the other retro slices: `retro_path`, `reload_from_disk()`, `save()`, `is_modified()`;
  saving calls `radide.retro.filebus.file_changed` so open tile / map editors of the same file reload.

### Detection and checksums (`detect.py`)

`detect(data, filename) -> RomInfo(system, format, rows, fields, listing, warnings, checksum_ok, fixable,
cpu_address, cpu, title)`:

| System | What is read |
|--------|--------------|
| Atari 2600 | size, 4 KB banks, bankswitching guess (2K, 4K, F8 / F6 / F4 (+SC SuperChip), E0, E7, FE, 3F, UA, FA, DPC, EF) from size + hotspot access patterns, RESET / IRQ vectors |
| Atari 7800 | A78 header: title, ROM size, cartridge type bits, controllers, TV, save device |
| Atari 8-bit | XEX segments + RUNAD / INITAD, ATR geometry + Atari DOS 2 directory, CAR type + checksum |
| NES / FDS | iNES and NES 2.0: mapper (+ name, submapper), PRG / CHR sizes (incl. exponent notation), mirroring, battery, trainer, console type, timing, size check, NMI / RESET / IRQ vectors; FDS sides |
| Game Boy / Color | title, CGB / SGB flags, cartridge type, ROM / RAM size, destination, version, header + global checksum (the boot logo area is *not* compared - no Nintendo data is embedded) |
| GBA | title, game / maker code, complement check |
| SNES | copier header, LoROM / HiROM / ExHiROM scoring, title, map mode, sizes, country, version, checksum + complement (mirrored non-power-of-two sizes), vectors |
| Genesis | system, titles, serial, checksum (16-bit word sum from 0x200), ROM / RAM ranges, region; SMD interleave warning |
| Master System / Game Gear | `TMR SEGA` header, region / size, product code |
| C64 | PRG load address + detokenised BASIC V2 listing, D64 BAM + directory, T64 directory, raw TAP version |
| ZX Spectrum | TAP blocks (headers, XOR checksums), TZX block list, SNA registers (+ PC from the stack) |
| DOS | MZ header (sizes, SS:SP, CS:IP, relocations, overlay, PE / NE / LE / LX), COM |
| Patches | IPS records, UPS / BPS sizes, CRCs, actions, metadata |

`fix_checksum(data, filename) -> (data, message)` repairs Game Boy / Color (header + global), GBA (complement),
SNES (checksum + complement, copier header kept), Genesis and Atari CAR. In the editor it is one undoable edit
(ROM Tools > Fix Header Checksum). `detect_system(path)` returns the emulator slice's ids (a2600, a8, nes, snes,
gb, gbc, gba, sms, gg, c64, dos, ...); `radide/retro/emu/systems.py` calls it first.

### Patches (`patches.py`)

* IPS: create (records <= 64 KB, RLE for runs of 9+, up to 5 equal bytes kept inside a record, truncation size
  when the target is shorter, the 0x454F46 offset written from one byte earlier) and apply (grow / truncate).
* UPS: create / apply with the three CRC32 checks; applying to the target gives the source back.
* BPS: apply supports all four actions (SourceRead, TargetRead, SourceCopy, TargetCopy incl. overlapping
  copies) + metadata + CRC32 checks; create emits SourceRead for unchanged runs, TargetCopy for byte runs and
  SourceCopy for blocks found elsewhere in the source (sampled index), so moved / inserted data stays small.
* Equal runs are compared in growing blocks, so a 4 MB ROM with a few changes is diffed in well under a second.
* Tools > Retro > ROM Workbench > Create Patch / Apply Patch (the output must be a new file).

### ROM Hacking Project (`project.py`, `projectui.py`, `retro_romhack.py`)

New Project > Retro > **ROM Hacking Project** (or **(Demo ROM)**, which starts with a synthetic NES image and an
example IPS patch). `rom.json` keeps the source ROM (copied into `rom/` or referenced by absolute path) with
its CRC32, the ordered patch list (`enabled`, `note`), tables, output path, `fix_checksum` and the optional
working copy:

* Build (Project > ROM Hacking > Build Patched ROM, Build > Build Project, Patch Manager > Build, or
  `python -m radide.retro.rom build <folder>`) applies the enabled patches in order to a fresh in-memory copy,
  optionally fixes the header checksum and writes `build/<name>_patched.<ext>`. The source ROM is never written
  and always opens read-only; Build warns when its CRC32 changed.
* Run (F5 / Ctrl+F5) runs `python -m radide.retro.rom run <folder>`: build, then `emulink.run_rom`.
* Patch Manager tab: source ROM info, Set Source ROM (copy or reference), patch list with check boxes, Add /
  Remove / Move Up / Down / Note, details of the selected patch, Edit Working Copy (clean ROM + patches ->
  `work/`, opened in the hex editor) and **Capture Edits as Patch** (the diff becomes `patches/NNN_<name>.ips|bps|
  ups`), Build, Build & Run, Open Output.
* Solution Explorer shows a "ROM Hacking" node with the source ROM, the patches, the working copy and the build.

### Emulator link (`emulink.py`)

`run_rom(path, system=None, debug=False, **kw)` - translates the ids of `detect.py` (atari2600 -> a2600,
atari8bit -> a8, ...) and calls `radide.retro.emu.run_rom`; raises `emulink.RunError` with a user message when
the emulator slice or an installed emulator is missing. The CLI prints the message and keeps the built ROM.

### Command line

    python -m radide.retro.rom build|run <project folder>
    python -m radide.retro.rom info <file>
    python -m radide.retro.rom apply <rom> <patch> <output>
    python -m radide.retro.rom create <original> <modified> <patch.ips|.bps|.ups>
    python -m radide.retro.rom fixsum <file> [<output>]

### Tests (`samples/Tests/Retro/RomTools`) and sample (`samples/Tests/Retro/RomHackDemo`)

* `test_rom_core.py` (90 checks, no Qt) and `test_hex_ui.py` (34 checks in the IDE); `run_all.py` runs both.
* `RomHackDemo` - the Demo ROM project (CC0 homebrew image + IPS patch).

Not done yet: SMD de-interleaving and SMS / Game Gear checksum repair, an x86 / Z80 / 68000 / 65816
disassembler in the inspector (6502 only; the retro-dev slice owns the full disassemblers), structure templates
the user can write (only the built-in header templates), Open Folder detection of a folder of ROMs, a tutorial
course.

## Retro development (slice "dev": `radide/retro/cpu`, `radide/retro/dev`, `radide/languages/retro_*.py`, `radide/features/retro_dev.py`)

Write new games for old machines, or turn a ROM you own into a project you can edit and rebuild.

### Project types (New Project > Retro Games)

| Language plugin | Templates | Toolchain (downloaded on the first build) | Output | Runs in |
|---|---|---|---|---|
| `retro-atari2600` Atari 2600 (DASM) | Atari 2600 Game: NTSC kernel (VSYNC / VBLANK with TIM64T / 192 lines / overscan), joystick-moved sprite, RESP0 + HMOVE positioning | DASM 2.20.18 (GitHub, GPL-2.0) | 4K `.bin` | Stella |
| `retro-nes` NES (cc65 / ca65) | NES Game (ca65 assembly, own `nes.cfg`, OAM DMA, controller), NES Game (cc65 C, conio + joystick driver) | cc65 Windows snapshot (official, zlib) | `.nes` (NROM) | Mesen 2 / FCEUX |
| `retro-gameboy` Game Boy (RGBDS) | Game Boy Game: header, VRAM tiles, OAM sprite, D-pad | RGBDS 1.0.4 (GitHub, MIT) + rgbfix | `.gb` | mGBA / Mesen |
| `retro-c64` Commodore 64 (cc65 / ACME) | ca65 assembly (BASIC SYS line, KERNAL, raster loop, joystick 2), cc65 C, ACME (only when `acme` is in PATH) | cc65 | `.prg` | VICE |
| `retro-zx` ZX Spectrum (sjasmplus) | Z80 at 32768: ROM CLS / rst $10, HALT loop, border, keyboard | sjasmplus 1.24.0 (GitHub, BSD-3) | `.tap` (BASIC loader + CODE, `tapfile.py`) | Fuse / ZEsarUX / `RADIDE_ZX_EMULATOR` / file association |

GBDK-2020 (C for the Game Boy) is not offered yet.

* Toolchains: `radide/retro/dev/toolchain.py` downloads from the official release pages only, into
  `%LOCALAPPDATA%\RADIDE\tools\<tool>` (portable, no admin, no PATH change); the archive SHA-256 is checked against
  the value GitHub publishes (DASM, RGBDS, sjasmplus) and recorded in `RADIDE-SOURCE.json`. cc65 publishes only a
  rolling Windows snapshot, so its SHA-256 is measured and recorded, not pinned (the zip CRCs are verified).
  Tools > Retro > Retro Development > Retro Toolchains... shows the status and downloads with one click.
* Build: `python -m radide.retro.dev.build <folder>` (`build.py`), driven by `project.radproj` `"retro"`:
  `system`, `lang` (asm / c / acme), `main`, `cfg` (ld65 config), `output`, `fix` / `title` (rgbfix), `org` /
  `entry` (ZX .tap), `prebuild` (commands run in the project folder before assembling, e.g. a graphics packer;
  `{python}` is the IDE's Python), and for disassemblies `original` / `compare` / `compare_what`. Messages go to
  `_build/diagnostics.json`; `errors.py` understands DASM, ca65 / ld65 / cc65, RGBDS (`error: ...` + `at f(n)`),
  sjasmplus and ACME, so the Error List shows file + line (double-click opens it). Listings, symbol files,
  `labels.txt` (ld65 `-Ln`) and the ca65 `.dbg` file are written to `_build/` for the emulators / debuggers.
* Run (F5 / Ctrl+F5): `python -m radide.retro.dev.run <folder>` builds, then calls the emulator slice's API
  `radide.retro.emu.run_rom(path, system=...)` (our system ids map to `a2600`, `nes`, `gb`, `c64`) and waits for
  the emulator, so Stop ends both. `run.run_rom(path, system_id)` is the same call for other code. When no
  emulator is installed, the Output window says to use Tools > Retro > Emulators....

### Disassemblers (`radide/retro/cpu`, no Qt)

* `m6502.py` (all 256 opcodes, NMOS undocumented ones flagged), `sm83.py` (Game Boy), `z80.py` (CB / ED / DD / FD /
  DDCB / FDCB, undocumented IXH / IXL, SLL, ED duplicates, DDCB register copies, OUT (C),0 ...). Each entry has the
  addressing mode, size, cycles (T-states for SM83 / Z80) and the flags it changes; the descriptions (English +
  Arabic) are our own.
* `hwregs.py`: TIA / RIOT (read and write names differ at the same address), NES PPU / APU / controllers, Game Boy
  I/O + MBC registers, VIC-II / SID / CIA / KERNAL routines, ZX Spectrum ROM routines and system variables, ZX ports
  (hover only), with descriptions written for RAD IDE.
* `disasm.py`: recursive tracing from the reset / NMI / IRQ vectors (2600 / NES / C64), the entry point and
  interrupt vectors (Game Boy), the BASIC `SYS` / `RANDOMIZE USR` address (C64 / ZX) and the user's hints;
  everything not reached stays data. Labels (`Lxxxx`, `Bn_` per bank, `Reset` / `NMI` / `IRQ` / `Start` ...),
  hardware names as equates, 2600 zero-page RAM as `ram_XX`. Output for DASM, ca65, RGBDS and sjasmplus is written
  so the assembler picks the *same encoding*: absolute operands below $100 are forced (`lda.w` / `lda a:`),
  `ld a,[$FF44]` stays `ld` (not `ldh`), undocumented opcodes / prefix-only bytes / odd encodings become `.byte` /
  `db` with the mnemonic in a comment, labels are only placed where a line starts (a jump into the middle of an
  instruction keeps its hex address and is reported as a conflict), 2600 mirror addresses stay as written.
* `romfmt.py`: 2600 2K / 4K / F8 / F6 / F4, iNES 1 / NES 2.0 (header, trainer, PRG banks with the last one fixed at
  $C000, CHR ROM -> `chr.bin`), Game Boy (ROM0 + ROMX banks, header / checksums shown), C64 `.prg`, ZX `.tap`
  (CODE blocks + the BASIC loader's USR address) or raw code with a load address.

### Disassemble ROM into Project (Tools > Retro > Retro Development)

Choose a ROM / program file you own, the system (or let the IDE detect it), an optional load address / entry
point (raw ZX code), "follow undocumented 6502 opcodes" and a folder. `fromrom.create_project` writes the source
(`main.asm` / `main.s`, plus a generated ld65 config for ca65), the data files, a copy of the original in `rom/`
and `hints.json`, builds it and compares the result with the original: the dialog shows **byte-identical** (green)
or the first difference (red). F5 / Rebuild Check repeat the comparison after every edit.
`hints.json` (`code` addresses the tracer missed, `data` ranges, `labels`, `comments`, `undocumented`) is applied by
Re-disassemble with Hints (the old source is kept as `.bak`). Console: `python -m radide.retro.dev.fromrom <rom>
<folder> [system] [base hex]`. Multi-bank NES ROMs: only the fixed last bank is traced automatically (the other
banks need code hints); a multi-block ZX tape is compared as the concatenation of its CODE blocks.

### Editor (`radide/retro/dev/intel.py`)

Monarch grammars `rad-retro-dasm` / `-ca65` / `-rgbds` / `-sjasmplus` (mnemonics, registers, directives, hardware
names, `$hex` / `%bin` numbers, column-0 labels for DASM / sjasmplus, ca65 `@local` and `:+` labels);
completions (mnemonics with cycles, directives, registers, the system's hardware registers, labels / equates /
macros of every source in the project); hover (addressing-mode table with opcode / bytes / cycles and the flags,
hardware register text, a number in hex / decimal / binary + the register at that address, ZX ports, label
definitions); signature help (addressing modes); go to definition (across files, `.local` labels); find all
references; outline. `radide/features/retro_dev.py` puts a guard first in `MonacoEditor.plugin_overlays` so the
x86 assembly overlay never replaces a retro plugin.

### Tests (`samples/Tests/Retro/Dev`) and samples (`samples/Tests/Retro/Dev/Projects`)

* `check_disasm.py` (137 checks, no Qt): decoders vs hand-assembled bytes, error parsers, TAP writer, round trips of
  synthetic homebrew ROMs (2600 4K / 2K / F8, NES, C64, Game Boy, ZX with and without undocumented code) through
  the real assemblers -> byte-identical, hints.
* `check_templates.py` (52 checks, no Qt): every template builds without warnings, output format, a mistake -> an
  Error List row at the right file / line, the built ROM -> disassembled project -> byte-identical; editor support.
* `test_ide.py` (13 checks, IDE): New Project group, editor plugin, menus, Rebuild Check, Error List, Disassemble
  dialog end to end, toolchains dialog, Arabic strings.
* Samples: Atari2600Smiley, NesSprite, NesHelloC, GameBoySmiley, C64Ball, C64HelloC, ZxBlock and Disasm2600Smiley
  (a disassembly of our own 2600 ROM). Everything is original homebrew (CC0).

Not done yet: GBDK-2020 C template, ACME download (PATH only), automatic tracing of switchable NES / Game Boy
banks (hints needed), SNES / Genesis / 7800 / Atari 8-bit / MSX / SMS project types (the Z80 / 6502 disassemblers
already decode their code), source-level debugging inside the IDE (the emulator slice's Retro Debugger and the
emulators' own debuggers load the `.sym` / `.dbg` / `labels.txt` files), Open Folder detection of DASM / ca65 /
RGBDS source folders, a tutorial course (`radide/tutorials/retro-games/`).

## DOS program development (slice "dosdev": `radide/retro/dos`, `radide/languages/dos_*.py`, `radide/features/dos_ide.py`)

New QBasic, Pascal, C, assembly and batch programs for MS-DOS, built into **real DOS executables** with free
compilers and run in DOSBox-X (found / downloaded through `radide.retro.emu.manager`).

### Project types (New Project > DOS)

| plugin | free compiler (downloaded on the first build) | your own copy (Tools > Retro > DOS Programming > DOS Toolchains) |
|---|---|---|
| `dos-qbasic` QBasic / QuickBASIC | FreeBASIC 1.10.1 **DOS build**, `fbc -lang qb`, run inside DOSBox-X without a window (CWSDPMI copied next to the EXE) | QBASIC.EXE / QB.EXE: "Run in My QBasic" (`/RUN`); BC.EXE + LINK.EXE as compiler |
| `dos-pascal` Turbo Pascal-style | Free Pascal 3.2.2 i8086-msdos cross compiler on Windows (`-Tmsdos -Wm<model> -Mtp -XX`, Crt / Dos / Graph) | TPC.EXE inside DOSBox-X |
| `dos-c` Turbo C-style | Open Watcom v2 `wcl -bt=dos -m<s/m/c/l>`; RAD IDE's `include/` adds `tcconio.h` (clrscr, gotoxy, textcolor, cprintf in colour ...), `tcgraph.h` / `graphics.h` (BGI subset in 640x480x16, no .BGI drivers) | TCC.EXE inside DOSBox-X; DJGPP `i586-pc-msdosdjgpp-gcc` (32-bit, not downloaded: no official Windows-hosted build) |
| `dos-asm` DOS Assembly (16-bit MASM) | JWasm 2.21 `-mz` (MZ .EXE) or `-bin` (.COM); listing + symbol map in `_build` | - |
| `dos-batch` DOS Batch (.BAT) | none (the build checks GOTO / CALL targets) | - |

Templates (all original): hello, text-mode menu, mode 13h graphics, PC speaker music, mouse (INT 33h) for every
compiled language, plus line-numbered BASIC, a tiny .COM, BGI graphics (C), CHOICE menu and a launcher (batch).
Sources are written CRLF / CP437; box characters come from `CHR$()` / `#201` / `0xC9` so files stay ASCII.

Toolchains (`toolchain.py`, no Qt): official URLs, SHA-256 pinned (GitHub digests for Open Watcom and JWasm,
FreeBASIC's published SHA-1 checked too), unpacked into `%LOCALAPPDATA%\RADIDE\tools\<key>` with
`RADIDE-SOURCE.json`; the Free Pascal Inno Setup package is unpacked with innoextract (never run). Microsoft and
Borland tools are never downloaded. User paths: `%LOCALAPPDATA%\RADIDE\retro\dos\config.json` (`RADIDE_DOS_CONFIG`
overrides it).

### Build, Error List, Run, Debug

* `python -m radide.retro.dos.build <folder>` (also Build Solution through `plugin.build_command`) writes
  `_build/diags.json` (`{"ok", "exe", "tool", "map", "diags": [{severity, message, file, line, col, tool}]}`); the
  Error List shows the rows (`dos_ide.diag_provider`), with file:line for FreeBASIC, Free Pascal, Open Watcom /
  wlink, JWasm, Turbo Pascal, Turbo C, QuickBASIC BC and DJGPP gcc (`errors.py`) and compatibility notes
  (`compat.py`).
* F5 / Ctrl+F5 run `python -m radide.retro.dos.run <folder>`: build when stale, write `_build/run.conf` (project
  folder = C:, Z:\BIN on the PATH, cycles preset `xt / 286 / 386 / 486 / pentium / auto / max`, machine, memory,
  keep window, program arguments) and start DOSBox-X, tied to the runner with the emu slice's job object so Stop
  closes it. F5 adds `--debug`: DOSBox-X's built-in debugger starts the program with `DEBUGBOX` (stops at the first
  instruction) and the build's symbol map is printed (`BP seg:off`). DOS Assembly projects step in RAD IDE's own
  8086 emulator instead when it understands the code (DOS Project Settings > Debugger: auto / emu8086 / dosbox).
* `--qbasic` runs the source in your own QBASIC.EXE / QB.EXE; `--capture [--keys K] [--timeout N]` runs headless.

### Captured runs (tests and "Run with Captured Output")

`dosbox.capture_text()` starts DOSBox-X with `-silent` and three tiny original helpers (`helpers_src/*.ASM`,
embedded bytes checked against a JWasm build by the tests): `RADKEYS.COM` stuffs keys into the BIOS buffer
(`~` Enter, `` ` `` Esc, `_` Space, `^U ^D ^L ^R` arrows), the program's output is redirected to `_OUT.TXT`,
`RADSCR.COM` saves the text screen (`_SCREEN.TXT`, Crt / conio write to video memory) and the resident
`RADCAP.COM` saves the last mode 13h frame (`_SCR13.RAW`, pixels + palette) when the program switches back to
text mode. Tools > Retro > DOS Programming > Show Last DOS Screen displays both.
`dosbox.capture_clicks(run, folder, cmd, [(col, row), ...])` adds mouse clicks: the resident `RADMOUSE.COM` is a
stand-in INT 33h driver (reset / show / hide / status, and the AX=0Ch event handler Free Pascal's Mouse unit
installs) that clicks the left button over the given text cells during the program's status polls, then saves the
text screen to `_MOUSE.BIN` (char / attribute pairs) and types Esc keys so that the program can end.

### Old sources and Open Folder

`dos_ide.detect_dos_sources` is registered in `project_detect.DETECTORS`: folders of old `.BAS` (QBasic, with or
without line numbers; VB6 modules excluded), `.PAS` (Turbo Pascal; Delphi units excluded), `.C` (conio / dos.h /
graphics.h / far), `.ASM` (16-bit MASM / TASM) and `.BAT` files become a DOS project (sources untouched). The build
warns about what the free compilers cannot do: BGI `.BGI` / `.CHR` drivers (replaced by the BGI subset), Turbo
Pascal units with only a `.TPU`, `Overlay`, `inline($..)`, QBasic `PLAY` / `SOUND` / `CALL INTERRUPT` /
`ON TIMER`, Turbo C `asm` blocks and pseudo-registers, TASM IDEAL mode.

### Editor (`intel.py`, `reference.py`)

Hover / completion / signature help: INT 21h, 10h, 16h, 33h, 1Ah with every function's registers in and out
(English + Arabic), resolved from the register set just above the call in all four languages; QBasic statements,
Crt / Dos / Graph routines, conio / dos.h / i86.h / tcgraph functions, batch commands, 8086 instructions (from the
emu8086 plugin); outline and F12 (SUB / FUNCTION / labels / line numbers, procedures, C functions, asm labels /
PROCs, batch labels). Tools > Retro > DOS Programming > DOS Interrupt Reference... browses the tables.

### Tests (`samples/Tests/Retro/DOSDev`) and samples (`samples/Tests/Retro/DOSOldSources`)

`run_all.py`: toolchains (download / SHA-256 / helpers), IntelliSense and parsers, all 26 templates built and run
in DOSBox-X, the old-style samples detected / built / run, and the IDE test (qh.py).

Not done yet: FreeBASIC graphics programs are not frame-captured (its DOS graphics library does not switch modes
through the real-mode INT 10h vector RADCAP hooks; their text output is captured), the DOSBox-X debugger does not
load the symbol map itself (it is printed / opened in the IDE), DJGPP is used only when installed by the user,
QuickBASIC / Turbo Pascal / Turbo C paths were tested with configuration only (no proprietary copies available),
mode 12h (BGI) frames are not captured. Course: `radide/tutorials/dos-programming/` (see "DOS QA and course" below).

## Retro game designers (slice "gamedesign": `radide/retro/design/game`, `radide/features/retro_design.py`)

Draw a screen or level, and RAD IDE writes the data and the program for the system's toolchain (the VB idea:
draw it, generate code, run it). Tools > Retro > Game Designers > New Atari 2600 Screen / New NES Screen or
Level / New Game Boy Map / New DOS Mode 13h Screen, New Design for This Project (picks the designer from the open
retro or DOS project), Open Game Design... With a project open the design is saved in `<project>/Designs/` and
**every save regenerates** the code in `Designs/gen/<name>/`.

| system | file | layers | generated |
|---|---|---|---|
| Atari 2600 | `.a26scr` | Background colour + Playfield colour (one per scan line), Playfield (20 bits per line, mirror / repeat), Collision | DASM one-line kernel: 8 full-height tables (COLUBK, COLUPF, PF0-2, GRP0, GRP1, ENAM0/ENAM1/ENABL bits), players with NUSIZ / REFP, missiles, ball; NTSC 192 / PAL 228 lines; `<n>_collision.asm` |
| NES | `.nesscr` | Nametable (screens x 32 by 30), Attributes (palette per 16x16 metatile), Collision | ca65 data (palettes, columns, attribute columns, sprites, collision) + NROM loader (`nrom.cfg`): first 64 columns, then column + attribute streaming while the D-pad (or auto) scrolls a level of up to 8 screens; sprites at world x - camera x; `<n>.chr` |
| Game Boy | `.gbmap` | Background (32x32), Window (shown at WX/WY), Collision | `<n>.2bpp`, `_bg.tilemap`, `_win.tilemap`, `_data.inc` (OAM, BGP/OBP, SCX/SCY, WX/WY, LCDC, collision) + `<n>.asm` (RGBDS; `rgbfix -v`) |
| DOS mode 13h | `.m13scr` | Background (320x200 bitmap), Tiles (20x13 of 16x16, 255 = none), Collision | 8.3 files: `.PAL` (6-bit DAC), `.BG`, `.RLE`, `.SPR`, `.MAP`, `.COL`; programs `<N>.BAS` (QBasic / QuickBASIC dialect, FreeBASIC `-lang qb`), `<N>.C` (OpenWatcom `-ml`), `<N>.ASM` (NASM .COM with everything embedded) |

Common editor (`ui.GameDesigner`): tools Select / Pencil / Eraser / Fill / Rectangle / Pick (S P E F R K, right
button erases), Layers list (visibility + current layer, "Objects"), the colour / tile / palette picker of the
current layer (double-click edits the tile, sprite or colour), grid, zoom 1-8x (2600 pixels drawn 2:1), undo /
redo (whole-document snapshots), object list + Properties grid (object properties, or the screen settings:
TV system, mirror, score mode, priority, ball size / screens, scroll mode, speed / SCX, SCY, window, BGP, OBP0/1 /
transparent tile colour, build target), pixel editor for tiles and sprites (2600 players: height), NES palette
dialog (64-colour master palette), Import Tiles (`.chr` / `.nes` CHR ROM / `.2bpp`, read with the gfx slice's
codecs), Export PNG, Generate Code, Build && Run (a thread; then `radide.retro.emu.run_rom`: Stella, Mesen,
mGBA, DOSBox-X). Collision cells are drawn as a coloured overlay (1 solid, 2 hazard, 3 special, 4 trigger).

**Kernel timing (2600).** Every value comes from a table one byte into a 256-byte page (`TABLE-1,y` never
crosses a page) and the loop sits in one page. Stores land at cycles 3 COLUBK, 6 COLUPF, 13 PF0, 20 PF1, 27 PF2,
34 GRP0, 41 GRP1, 48/53/58 ENAM0/ENAM1/ENABL, WSYNC at 74. An object lying completely left of the pixel where its
register is written is generated one line early (and preloaded on the last VBLANK line); one that straddles it
gets a warning. VBLANK and overscan use TIM64T with the expiry padded to the middle of a line, so the frame is
exactly 262 / 312 lines whatever the positioning routine costs.

**Checks after every build (no emulator needed)** - `build.check`: the 2600 ROM runs in `sim6502.Atari2600Probe`
(cycle-counting 6502 + TIA write log + RIOT timer: lines per frame, every kernel line's PF / colour / GRP values,
PF writes before the beam); the NES ROM runs in `sim6502.NESProbe` (name / attribute tables, palettes after the
loader); the Game Boy data must be in the ROM at the `.sym` addresses with a valid header checksum; the .COM runs
in RAD IDE's 8086 emulator and video memory must equal the design. `build.dosbox_shot(exe)` runs a BASIC / C
.EXE with `/SHOT` in DOSBox-X (headless) and returns SCREEN.RAW.

### API

```python
from radide.retro.design.game import new_design, load, generate, build, gen_dir, SYSTEMS, EXTS
d = new_design("nes", "Level1", screens=3)         # a2600 (tv=) | nes (screens=) | gb | dos13h
d.layer("Nametable").set(5, 20, 4); d.save("Level1.nesscr")
info = generate(d, gen_dir("Level1.nesscr"))       # {"main", "files", "warnings", "rom", "system"}
res = build(d, "out", log=print, download=False)   # {"ok", "rom", "log", "warnings", "checks", "missing"}
from radide.retro.design.game.build import run, dosbox_shot
from radide.retro.design.game.ui import GameDesigner   # GameDesigner(design, path, log=win.log)
win.retro_designs.new_design("gb", folder=..., ask=False); win.retro_designs.open_design(path)
```

Reused from the other slices (through `compat.py`, with small fallbacks): `radide.retro.gfx` palettes, tile
codecs, playfield bit order, iNES CHR offset; `radide.retro.dev.toolchain` (DASM, ca65 / ld65, RGBDS);
`radide.asm.toolchain` (NASM); `radide.retro.dos.build.Builder` (FreeBASIC DOS inside DOSBox-X, OpenWatcom)
and `radide.retro.dos.dosbox`; `radide.retro.emu.run_rom`; `radide.retro.menu.section`; `radide.retro.filebus`;
`radide.emu8086` (mode 13h palette, .COM loader, machine). `RADIDE_RETRO_TOOLPATH` adds tool folders (tests).

### Tests (`samples/Tests/Retro/DesignGames`) and samples (`samples/Tests/Retro/DesignSamples`)

* `test_gamedesign_core.py` - 104 checks: playfield encoding, reflect / repeat, kernel tables, early objects,
  CTRLPF; NES attribute packing / unpacking, CHR planes, palettes, flipped metasprites; GB OAM / 2bpp; mode 13h
  palette, RLE, sprite file, clipping, composition; model round trip / snapshots / flood; codecs; real builds
  with DASM (NTSC, PAL, extreme x positions), ca65 + ld65 (3-screen level + scrolling and column streaming in
  the probe), RGBDS, NASM, FreeBASIC and OpenWatcom (both run in DOSBox-X and draw the design pixel for pixel);
  the ROMs / programs start in Stella, Mesen, mGBA and DOSBox-X (`--no-emu` skips). Missing tools are skipped.
* `test_gamedesign_ui.py` (qh.py) - 85 checks: menu, one designer per system, pencil / undo / redo, rectangle and
  fill on the collision layer, object drag, rename / add / delete, Export PNG, zoom, File > Save, TV / screens
  changes, mirrored playfield painting, Import Tiles, Save All, File > Open, Build && Run with checks, Arabic.
* `DesignSamples/` - `Castle.a26scr`, `Meadow.nesscr`, `Town.gbmap`, `Cave.m13scr` (original art, CC0, written by
  `make_samples.py`); all four build and pass their checks.

Not done yet: asymmetric 2600 playfields and per-line player colours (the one-line kernel has 2 cycles left),
2600 joystick movement, NES vertical scrolling / mappers beyond NROM, Game Boy Color palettes, scrolling maps
larger than 32x32 on the Game Boy, mode 13h multi-screen scrolling, a link to the gfx slice's editors for
editing tiles in place (the designer has its own pixel editor and imports `.chr` / `.2bpp`).

## Old NASA programs: Apollo AGC and legacy Fortran (slice "nasa": `radide/agc`, `radide/languages/agc_yul.py`, `radide/retro/legacy_fortran.py`, `radide/languages/retro_fortran_legacy.py`, `radide/features/retro_nasa.py`)

New Project > **Space & Science**: **Apollo AGC Program (yaYUL)** and **Fortran 66/77 (fixed form, gfortran -std=legacy)**.
File > Open Folder recognises both (`radide/agc/detect.py`, `legacy_fortran.detect_fixed_form`, hooked into
`project_detect.DETECTORS` as `_nasa`): a folder of `.agc` files with `MAIN.agc` becomes an AGC project (a flight program
with 20+ `$` includes gets `"agc": {"assembler": "yayul", "run": "yaagc"}`), fixed-form `.f/.for/.f77` sources a
`fortran-legacy` project.

### Apollo Guidance Computer

| Part | File | What it does |
|---|---|---|
| Reference data | `agc/isa.py` | Block II basic instructions, extracodes, implied-address forms (encodings + English/Arabic descriptions), pseudo-ops, ~120 interpretive opcodes, special registers, I/O channels, interrupt vectors, DSKY key and digit codes, verbs / nouns / programs (Colossus/Comanche meanings) |
| Built-in assembler | `agc/assembler.py` | original "mini-YUL" for the yaYUL syntax: labels in column 1, `#` comments, `$FILE.agc` includes, yaYUL's number rule (0-7 only = octal, 8/9 or `D` = decimal), `+n` relative operands, `SETLOC BANK BLOCK EBANK= ERASE EQUALS = OCT DEC 2DEC CADR FCADR ECADR GENADR ADRES REMADR BBCON 2CADR MM VN`, double-precision `+1` encoding (DAS DXCH DCA DCS), `NOOP` = `TCF +1` in fixed memory, EXTEND tracking (extended `INDEX`). Interpretive code is reported ("needs yaYUL"). Output: 36 x 1024-word rope, symbols, source line <-> address maps, listing, `to_bin()` in yaYUL's `.bin` order (banks 2, 3, 0, 1, 4..., words << 1, big-endian), `load_bin()`. Errors in English and Arabic. **Verified: the HelloDSKY rope is word-for-word identical to yaYUL's** (yaYUL also appends its bank "bugger" check words, which the built-in assembler does not). |
| Emulator | `agc/cpu.py`, `agc/machine.py` | original Block II CPU: 15-bit ones' complement words, 16-bit A / Q with overflow, all basic instructions and extracodes (MP / DV / MSU approximated), `TC A/L/Q` running the register as an instruction (RETURN), INDEX (also across EXTEND), banks (EB / FB / BB / superbank), edit registers CYR SR CYL EDOP, channels (L / Q as channels 1 / 2), TIME1-TIME5 with T3/T4/T5RUPT, KEYRUPT1, RESUME via ZRUPT/BRUPT, GOJAM. The **hardware alarms** restart the AGC like the real one and yaAGC: NIGHT WATCHMAN (NEWJOB, address 67, not touched within 0.64 s), RUPT LOCK / NO RUPT (140 ms), TC TRAP / NO TC (5 ms) - project `"agc": {"alarms": false}` turns them off. Not modelled: IMU, radars, parity, T6, downlink, counter cells of the flight hardware. `python -m radide.agc MAIN.agc --keys V35E` runs headless and prints the DSKY. |
| DSKY | `agc/dsky_model.py`, `agc/ui.py` | relay words of channel 10 (12 words: PROG / VERB / NOUN / R1-R3 digits and signs, lamp word 12), lamps of channel 11 and Virtual AGC's channel 163; an original painted DSKY widget (status/caution lamps, green 7-segment EL display, 19 keys + PRO, keyboard shortcuts 0-9 V N Enter C R P K + -) |
| Debugging | `agc/session.py` | F5 = `AgcSession`: the "Apollo AGC" dock (DSKY, Registers, Erasable Memory E0-E7, Channels, Variables), breakpoints on source lines in any `.agc` file, F11 / F10 (over TC) / Shift+F11, Locals = A L Q Z EB FB BB + the program's erasable variables, Call Stack (current label + Q), Watch / Immediate (symbols, registers, octal addresses), Pause / Step / Reset (GOJAM) on the dock; real-time execution (85 000 memory cycles per second) in 30 ms slices |
| Editor | `agc/intel.py` | Monarch grammar `rad-agc` (labels, opcodes, pseudo-ops, interpretive opcodes, registers, `##` annotations, `$` includes), IntelliSense with descriptions, hover (instructions, pseudo-ops, registers, I/O channels after READ/WRITE, `V16N36` / `P63` in comments), F12 and Find All References across every `.agc` file of the folder (`SymbolIndex`, mtime cache), outline by `## Page n` / log section, folding by page |
| Virtual AGC | `agc/toolchain.py` | Virtual AGC publishes no Windows binaries on GitHub, so Tools > Retro > Apollo AGC > Virtual AGC Toolchain... downloads the official `yaYUL/`, `yaAGC/` and `Tools/checkdec.c` of github.com/virtualagc/virtualagc at a pinned commit (`fdf0f05d`, 2026-10-24), checks every file against the git blob SHA-1 the GitHub API reports, records SHA-256 in `manifest.json` and builds `yaYUL.exe` / `yaAGC.exe` with the MinGW gcc into `%LOCALAPPDATA%\RADIDE\tools\virtualagc\bin` (portable, no admin). GPL v2 tools used as external programs. `python -m radide.agc.toolchain install / status`. |
| yaAGC link | `agc/yaagc.py` | the 4-byte socket protocol (channel + value, u-bit mask packets), `YaAgcLink` (QTcpSocket, retries until yaAGC listens on port 19697), key / PRO packets, parsers for the debugger console (`--fullname` stop annotations, `info registers`) |
| yaYUL / yaAGC session | `agc/session.py` `YaAgcSession` | project `"agc": {"assembler": "yayul"}` or `{"run": "yaagc"}` (or `"auto"` when the program has interpretive code): yaYUL builds (stderr `FILE:LINE: Fatal Error` -> Error List), yaAGC runs the rope (`--nodebug`, or debug mode with `break FILE:LINE` / `step` / `next` / `cont` / `info registers`) and the same DSKY dock connects to its socket |
| Apollo source | `agc/apollo_source.py` | Tools > Retro > Apollo AGC > Open Apollo Source...: Comanche055 (Apollo 11 CM) or Luminary099 (LM) from the virtualagc repository (mirror: chrislgarry/Apollo-11), on request, into a folder the user picks, blob-SHA checked, with `README_RADIDE.txt` (public-domain note, credit to Virtual AGC) and a `project.radproj` (yaYUL + yaAGC) |
| IDE glue | `features/retro_nasa.py` | Tools > Retro > Apollo AGC (Open Apollo Source, Virtual AGC Toolchain, Build with yaYUL, DSKY Panel, DSKY Verbs/Nouns/Programs, Assembly Listing); `win.diag_providers`: the built-in assembler checks the project on every save (Error List; only a hint for interpretive programs) |

Project settings (`project.radproj`): `"agc": {"assembler": "auto" | "builtin" | "yayul", "run": "emulator" | "yaagc", "port": 19697, "alarms": true, "stop_at_entry": false, "yayul_args": ""}`.

Writing programs that also run on real hardware / yaAGC: interrupt vectors at 4000 (4 words each: GOJAM, T6, T5, T3, T4, KEYRUPT1, KEYRUPT2, UPRUPT, DOWNRUPT, RADAR, HANDRUPT), save A/L with `DXCH ARUPT` and restore before `RESUME`, touch `NEWJOB` in the idle loop, keep an interrupt coming every < 140 ms (the samples reload TIME3 with 37777 for a T3RUPT every centisecond) and end idle loops with `TCF`.

### Legacy Fortran (FORTRAN IV / 66 / 77)

* `fortran-legacy` owns `.f` (the modern plugin keeps `.f90`); console programs: F5 = `python -m radide.retro.legacy_fortran run <folder>` (build into `_build/`, then run with stdin / stdout in the IDE). Project `"fortran": {"preset": ..., "flags": ...}`, presets: `legacy` (`-std=legacy -ffixed-form -ffixed-line-length-72`), `f66` (+ `-fno-automatic -finit-local-zero`, the static-variable semantics old programs rely on), `dec` (`-fdec`), `strict` (`-std=f95 -Wall -pedantic`, lists deleted / obsolescent features). Tools > Retro > Legacy Fortran > Compiler Preset...
* Editor: Monarch grammar `rad-fortran-fixed` (C / * / D comment cards by column 1, labels, Hollerith starts, dotted operators), Monaco rulers at columns 5 / 6 / 72, continuation column and label field coloured, columns 73-80 greyed (`editor_js`, a `MonacoEditor.ready_hooks` hook for every fixed-form file), hover = what the column means + an explanation of the legacy statement on that line, outline PROGRAM / SUBROUTINE / FUNCTION.
* `analyze()` (Tools > Retro > Legacy Fortran > Explain Legacy Constructs): arithmetic IF, computed / assigned GO TO, Hollerith, PAUSE, EQUIVALENCE, COMMON, ENTRY, shared DO terminals (per program unit), implicit typing - with English / Arabic notes.
* `to_free_form()` (Convert to Free Form..., diff preview + Save As .f90): `!` comments, continuations joined (strings and Hollerith kept intact), labels kept, sequence numbers dropped (or kept as comments), Hollerith -> quoted strings, `DO10` / `GOTO` blank fixes, long lines wrapped with `&`. **Verified: the converted OrbitTable compiles as free form and prints the same table.**
* Card Deck View: the current line drawn as an IBM 029 punched card (interpreted text, 12 rows, field shading 1-5 / 6 / 7-72 / 73-80, card N of M, statement number, sequence); `punch_rows`, `card_text` for text output.
* gfortran diagnostics (caret and one-line formats) -> Error List on save (`fortran_diagnostics`, `-fsyntax-only` with the project preset).

### Samples and tests

| Folder | What |
|---|---|
| `samples/Tests/Retro/AGC/HelloDSKY` | original AGC program (public domain / CC0): V16 N36 clock, V35E lamp test, OPR ERR / RSET, PUTNUM / FLUSH display buffer, KEYRUPT keyboard; same as the "Hello DSKY" template (`radide/agc/examples/hello_dsky`) |
| `samples/Tests/Retro/LegacyFortran/OrbitTable` | original Fortran 66 style program (CC0): circular orbits, Kepler's equation by Newton's method, arithmetic IF, computed GO TO, Hollerith FORMATs, sequence numbers in 73-80; `expected_output.txt` |
| `samples/Tests/Retro/AGC/test_agc_core.py` | 39 headless checks: built-in assembler + emulator + DSKY (keys, lamp test, OPR ERR, alarms, breakpoint), protocol / parsers, editor support; with Virtual AGC installed: yaYUL 0 errors and word-for-word equal rope, yaAGC + DSKY socket (clock, V35E, V16N36E); `--apollo DIR` / `--download`: Comanche055 assembles with yaYUL (0 errors) and answers V35E in yaAGC |
| `samples/Tests/Retro/LegacyFortran/test_legacy_fortran.py` | 27 checks: build + exact output with the presets, free-form conversion compiles and prints the same, analysis, fields, punch codes, plugin |
| `samples/Tests/Retro/AGC/test_ide_nasa.py` | IDE (qh harness, 35 checks): menus, templates, F5 with the DSKY dock, keys on the widget, breakpoint + Locals + F10, Error List; with Virtual AGC: the yaYUL / yaAGC session (DSKY over the socket, V35E from the widget) and yaAGC debugging (breakpoint, registers, next); Ctrl+F5 on OrbitTable, card deck and conversion windows |

Licences: the Apollo flight software is believed to be public domain (US government work); RAD IDE downloads it only on
request and writes a note crediting the Virtual AGC transcription. Virtual AGC (yaYUL, yaAGC) is GPL v2 or later, built
from the official source and used as external programs. The samples and RAD IDE's assembler, emulator and DSKY are
original code.

## DOS text-mode designer (slice "tuidesign": `radide/retro/design/textmode`, `radide/features/dos_designer.py`, `radide/languages/dos_tuiforms.py`)

A Visual Basic-style designer for DOS text-mode applications: draw the screens, RAD IDE writes the program and a small
original run-time in QBasic / FreeBASIC, Pascal, C or 16-bit assembly, builds it with the dosdev slice's free
compilers and runs it in DOSBox-X.

**New Project > DOS > DOS Text-Mode Forms App** (templates: QBasic / FreeBASIC, Pascal (Crt), C (OpenWatcom / Turbo
C), 16-bit Assembly (.COM), QuickBASIC 4.5, QBasic 1.1). The project it creates is a normal dosdev project
(`language` dos-qbasic / dos-pascal / dos-c / dos-asm, `"dos"` block), so Build, Run (F5), Project > DOS Settings
and the editor's DOS IntelliSense work unchanged; it adds `*.tform` screens and a `"tui"` block:

```json
"tui": {"target": "freebasic | quickbasic | qbasic | pascal | c | asm", "startup": "Main"}
```

Every save of a screen regenerates `MAIN.BAS` / `MAIN.PAS` / `MAIN.C` / `MAIN.ASM` (the first screen is the startup
screen). The user's code lives in `>>> USER CODE <key>` / `<<< END USER CODE` regions (`declarations`, `startup`,
`general`, one per handler) and is kept; the code of a handler whose control or event was removed is kept commented
out in the `orphaned` region. Unsaved edits of the open MAIN file are written first, then the editor reloads.

### Designer (`designer.py`, `canvas.py`, `glyphs.py`)

* Toolbox: Pointer, Window / Frame (border none / single / double / mixed / block, title left / centre / right,
  shadow), Label (alignment), Button (hotkey, focus colours, shadow, Cancel = Esc), TextBox (MaxLength, password),
  CheckBox, Option (groups), ListBox (items, border, selection colours), MenuBar (VB-style Menu Editor: captions with
  `&` hotkeys, names, shortcut texts, separators), StatusBar (`~highlighted~` text), ProgressBar (block characters),
  Separator (joins window borders: `╟─╢`, `╠═╣` ...).
* Canvas 80x25 / 80x43 / 80x50 cells, CP437 glyphs drawn pixel-exact for box drawing, blocks and shades
  (letters from Consolas / Lucida Console / Courier New), 16 foreground / 8 background colours + blink (iCE colours for
  art). Drag to draw / move / resize (snapped to cells), rubber-band and Shift / Ctrl multi-select, arrows move,
  Shift+arrows resize, moving a Window / Frame moves the controls inside it, Bring to Front / Send to Back, grid,
  zoom, undo / redo (200 steps), copy / paste, PNG export, menu drop-down preview (click a title of the menu bar).
* Properties window: object box, every property with a fitting editor (colour combos, choices, items / menus /
  character / art-file dialogs) and the events list (double-click = code). Screen properties: size, desktop fill
  character and colours, BackgroundArt (.ans / .bin / .txt), SplashArt + SplashSeconds, EscQuits.
* Events: Button Click / KeyPress, TextBox Change / KeyPress, CheckBox / Option Click / KeyPress, ListBox Click /
  Change / KeyPress, menu item Click, screen Load / KeyPress. Double-click a control, an event or an open menu's item
  -> the MAIN file opens at the handler.
* **Test Run (F5 in the designer)**: the run-time simulator (`sim.py`) runs the screens in a window (keys, mouse,
  menus, message boxes) without DOS.

### Generated programs (`codegen/*.py`, `render.py`, `sim.py`)

`render.py` is the reference: the generated run-times draw exactly the same cells. Two layers: the **static layer**
(desktop, windows, frames, separators, menu bar, list box borders, button shadows) is stored as run-length data
(count, character, attribute; a run never crosses a line) and copied to the screen; the **live controls** are drawn
from tables (type, position, attributes, text, hotkey mask, value, tab order, group, events ...) with their run-time
state. One program holds all screens (same size). Event loop: Tab / Shift+Tab / arrows move the focus (arrows move
in a list box), Enter / Space activate, typing edits a text box, Alt+letter (and the letter outside a text box)
triggers hotkeys and opens menus, F10 opens the menu bar, Esc = the Cancel button or quits, left click focuses /
activates / selects list items / opens menus. Menus and message boxes are modal loops.

| target | drawing | keys | mouse | build |
|---|---|---|---|---|
| FreeBASIC (`-lang qb`) | LOCATE / COLOR / PRINT (the bottom-right cell without scrolling) | INKEY$ | `__GETMOUSE` | dosdev Builder (FreeBASIC DOS in DOSBox-X) |
| QuickBASIC 4.5 | same | INKEY$ | INT 33h via CALL INTERRUPT (`QB /L QB.QLB`) | user's BC.EXE |
| QBasic 1.1 | same | INKEY$ | none (no COMMAND$, so no test dump either) | user's QBASIC.EXE; FreeBASIC builds it too |
| Pascal | Crt (TextAttr, GotoXY, Write); last cell / dump via `Mem[$B800:...]` (go32v2: `dosmemput`) | KeyPressed / ReadKey | FPC Mouse unit, TP: INT 33h via Dos.Intr | Free Pascal i8086-msdos (`-Mtp`), user's TPC |
| C (C89) | far pointer to B800:0000 (DJGPP: `_farpokew`) | kbhit / getch | INT 33h via int86 | OpenWatcom wcl `-bt=dos`, user's TCC, DJGPP |
| 16-bit asm (MASM / TASM / JWasm syntax, `.model tiny`, `org 100h`) | stosw to B800h | INT 16h | INT 33h | JWasm `-bin`, or RAD IDE's own 8086 assembler (no toolchain) |

Run-time API in handlers: `TuiSetText` / `TuiGetText$`, `TuiSetValue` / `TuiGetValue`, `TuiSetVisible`,
`TuiSetEnabled`, `TuiAddItem` / `TuiClearList` / `TuiGetItem$`, `TuiShowScreen`, `TuiMsgBox`, `TuiQuit`, `TuiKey`
(KeyPress: set 0 to cancel). Pascal uses the same names, C `tui_set_text` ..., asm `tui_set_text` with registers
(BX = control, SI = string, AX = value). Control and screen names are constants (`CONST btnOK = 3`, `#define`,
`equ`). Names: letters and digits only (QBasic has no `_`), so BASIC handlers are `btnOKClick`.

Test hooks every generated program has: `PROG /DUMP` writes the screen (B800 dump, `SCREEN.BIN`) right after start-up
and exits; `PROG /DUMPKEYS` first processes the keys waiting in the BIOS buffer (also inside menus and message boxes).
`project.keys_com(keys)` builds a key-stuffer .COM with RAD IDE's 8086 assembler (Tab, F10, Alt+letter ... which the
dosdev RADKEYS.COM does not cover).

### ANSI / ASCII art editor (`ansieditor.py`, `ansi.py`)

Pencil, Line (character or single / double box lines that join existing box drawing), Box (filled or not), Fill,
Text (F1..F8: block characters), Select (copy / cut / paste as a floating block / delete), Eyedropper (also right
click), character palette, colour bar (left = fore, right = back), blink, iCE colours, undo / redo. Files: `.ANS`
(SGR colours, cursor movement, clear; deferred wrap; SAUCE title / author / group / width / iCE flags / comments
read and written), `.BIN` (raw cells, SAUCE binary text width), `.TXT` / `.ASC` / `.NFO` (CP437 or UTF-8), PNG
export. **Use as Splash Screen** puts the art in front of the startup screen (seconds or until a key). ANSI cannot
carry the characters ESC, CR, LF, TAB, BS, NUL and SUB: they are saved as spaces (use `.BIN` for exact copies).

### Python API (no Qt in model / render / ansi / codegen / sim / project)

```python
from radide.retro.design.textmode.model import TScreen, new_screen, load_project_screens
from radide.retro.design.textmode.render import render            # TScreen -> CellBuffer (what DOS shows)
from radide.retro.design.textmode import project as tp
tp.create(folder, "Demo", "pascal")        # new forms project (sample screen + sample code)
tp.generate(folder)                        # .tform -> MAIN.* (regions kept)
ok, exe = tp.build(folder)                 # generate + build (dosdev Builder / built-in assembler)
buf = tp.capture(folder, exe.name, keys=[9, 13])   # run headless in DOSBox-X, the screen as a CellBuffer
from radide.retro.design.textmode.sim import Sim   # the run-time in Python (Test Run, tests)
```

CLI: `python -m radide.retro.design.textmode.project generate|build|run|capture <folder>`.

Course: `radide/tutorials/dos-programming/` (Arabic, 11 lessons; the designer, events and code, ANSI art + B800 are
lessons 6-8).
Other DOS lessons can be added to the same course.json.

### Tests (`samples/Tests/Retro/DesignTextMode`, sample `samples/Tests/Retro/DesignTUI_Contacts`)

`test_core.py` (48 checks, no toolchain: model, renderer, ANSI / BIN / TXT / SAUCE, regions in four languages, the asm
program in the 8086 emulator = simulator after 13 key sequences), `test_dosbox.py` (40: the sample and all four
targets built with FreeBASIC DOS / Free Pascal i8086 / OpenWatcom / JWasm, run in DOSBox-X, screens equal to the
designer and the simulator after keys, menus, message boxes, a second screen, 80x43 / 80x50 in C and asm; splash
in the emulator; skips offline),
`test_ui.py` (34, qh.py). Not done: the dropdown menus and message boxes have no shadow at run time (the static
windows do), list boxes have no scroll bar, there are no 40-column screens, a Pascal 80x43 program shows 50 lines on VGA
(Crt's Font8x8; the bottom 7 stay empty), Turbo Pascal / Turbo C / QuickBASIC / QBasic outputs are checked only by
reading (no proprietary copies; the QuickBASIC dialect needs QB.BI / CALL INTERRUPT, so FreeBASIC cannot build
it), DJGPP is untested (not downloadable), and the asm target has no `TuiAddItem` /
`TuiClearList` (fixed item lists).

## DOS QA and course (QA of the dosdev / tuidesign / gamedesign slices)

**End to end in the real IDE** - `samples/Tests/Retro/DOSQA/qa_dos_e2e.py` (qh.py harness, QSettings `RADIDE-TEST`,
`widget.grab()` screenshots; `QA_LANG=ar QA_THEME=dark` for Arabic + dark; phases `dos old tui ansi game i18n`):
File > New Project with the real dialog for one project of every DOS type -> Tools > Retro > DOS Programming >
Build DOS Program (real MZ / COM) -> Run with Captured Output (keys typed) -> Show Last DOS Screen, plus a windowed
DOSBox-X run that ends by itself; File > Open Folder on the old QBasic / Turbo Pascal / Turbo C samples -> build
(sources unchanged) -> run; DOS Text-Mode Forms App for FreeBASIC, Pascal, C and asm: TextBox + Button drawn with
the toolbox, handler code from a double-click, regenerate, build, keyboard (Tab, typing, Enter) and a mouse click
in DOSBox-X compared cell by cell with the simulator, Build && Run in a DOSBox-X window; the ANSI editor (box /
text / fill with mouse and keys, .ANS + SAUCE and .BIN round trips, PNG); the four game designers' Build && Run with
their checks and the emulators (Stella, Mesen, mGBA, DOSBox-X) started and stopped; the DOS / designer menus
translated in Arabic and no DOS string seen on screen missing from ar.json.

**Mouse clicks** - `samples/Tests/Retro/DesignTextMode/test_mouse.py`: OK, File > About... and an empty area clicked
in real DOSBox-X through `RADMOUSE.COM` for all four targets, each screen equal to `sim.Sim.click`. This found
that Free Pascal 3.2's DOS Mouse unit returns 1-based `GetMouseX` / `GetMouseY` (its `SysGetMouseX` adds 1), so
every click of a generated Pascal program landed one cell right and one row down; `codegen/pascal.py` now
subtracts 1.

**Course** - `radide/tutorials/dos-programming/` (11 Arabic lessons: DOS and DOSBox-X, QBasic with FreeBASIC,
Pascal and Crt, C with Open Watcom and B800, 16-bit assembly and interrupts, the text-mode designer, events and
code, ANSI art, mode 13h and the game designers, old programs and games you own, final project).
`tools/check_lessons.py` builds every ```` ```dos-qbasic / dos-pascal / dos-c / dos-asm / dos-batch run ````
block in a fresh DOS project with the free compiler and runs it headless in DOSBox-X (keys, screen, mode 13h and
compile-error specs in hidden `<!-- test: -->` comments; see the course README). CHM:
`python tools/build_chm.py dos-programming --verify` -> `docs/chm/RADIDE_DOS_PROGRAMMING_ar.chm`. The tutorial
engine has no runner for these blocks, so the viewer shows them without a "جرّبه" button.
