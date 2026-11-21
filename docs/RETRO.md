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
