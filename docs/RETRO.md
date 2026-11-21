# Retro computing, old games and old NASA programs

Each slice of radide/retro (and radide/agc) documents itself in its own section below.

## Emulators (slice "emu": `radide/retro/emu`, `radide/features/retro_emu.py`, `radide/languages/retro_dos.py`)

RAD IDE never bundles an emulator, a BIOS or a game. On request (**Tools > Retro > Retro Emulators...**) it
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
`-config ...\retro\atari800\atari800.cfg -no-autosave-config`. DOSBox-X gets `<project>\.radide\dosbox-x.conf`.
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
  Retro Emulators...
* CLI: `python -m radide.retro.emu status | install <id> | run <rom> [--debug] [--symbols f] | dos <folder|program>`.

### Hot reload

**Tools > Retro > Reload ROM in Emulator** (Ctrl+Alt+F5) or the dock's **Reload ROM** button (`ui.hot_reload` /
`RetroProcess.reload`). In VICE the program is loaded again in place: the monitor runs `autostart` and the emulator
keeps running. Stella, Mesen, FCEUX, mGBA and Atari800 have no reload command on their command line or protocol, so
RAD IDE restarts them with the same options. When a GDB or monitor session was attached, the Retro Debugger attaches
to the restarted emulator again.

### DOS programs and legacy DOS development

* **New Project > Retro > DOS Program** (`retro-dos` plugin) has these templates:
  * Existing DOS Program: copy in a program or game you own.
  * DOS .COM in Assembly: NASM builds it on Windows, using the downloader of `radide/asm/toolchain.py`.
  * Turbo Pascal / Free Pascal.
  * Turbo C / Open Watcom C.
  * QBasic / QuickBASIC.
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
* Compilers: RAD IDE ships none. NASM, which is free, builds `.COM` files on the host. For Pascal, C and BASIC, the
  project's toolchain folder is searched for one of these compilers and the build runs inside DOSBox-X:
  * TPC/BPC (Turbo/Borland Pascal, your copy).
  * PPC386/FPC (Free Pascal go32v2, GPL/LGPL).
  * TCC/BCC (Turbo/Borland C, your copy).
  * WCL (Open Watcom, OWPL).
  * QB/QBASIC (Microsoft, your copy; not redistributable).
  * BC.
  * FBC (FreeBASIC DOS, GPL).

  You can also give your own `build` command with `{src}` / `{stem}` placeholders.
  RAD IDE does not download the free DOS compilers yet.

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
* `test_gfx_ui.py` - 44 IDE checks with `qh.py` (offscreen, QSettings "RADIDE-TEST", `widget.grab()` shots):
  menu, `.chr` / `.rtmap` / `.rtpf` / `.tbl` open the editors, pencil and fill by mouse, undo / redo, write back,
  file-bus refresh of the tile map and of the tile editor, PNG, 2600 player preview, playfield click + ROM
  write, table check, script dump + Arabic sheet + repack insert, Arabic UI.
* `make_sample.py` regenerates `Sample/` (original CC0 data, see the README there).

Not done yet: SNES 8bpp / mode 7 and NES 8x16 sprite ordering, palette data read from the ROM itself
(CGRAM / NES palette tables), a font-tile generator that renders Arabic glyphs into tiles automatically, DTE /
dictionary compression on insert, a tutorial course.
