# Firmware and ECU binaries

RAD IDE opens firmware images and control-unit dumps (`.bin`, `.ori`, `.hex`, `.s19`, `.elf` ...) for analysis,
calibration-map editing, checksums and versioned builds. The tools are general-purpose. They are meant for
legitimate repair, research, education and tuning, on units you own or are authorised to service.

> **Scope.** RAD IDE has no immobiliser / anti-theft, key or PIN, emissions-system (DPF, EGR, SCR / AdBlue,
> lambda, catalyst, readiness monitors), odometer or VIN / security-access functions, templates or presets.
> Bytes that belong to such systems are treated like any other bytes. Edits to vehicle software can affect
> safety, warranty and emissions legality: keep the original and follow your local laws. The IDE shows this
> notice once per user (`radide/firmware/project/notice.py`, QSettings key `firmware/safetyNoticeAccepted`).

Packages (each slice documents its own section below):

| Package | What |
|---|---|
| `radide/firmware/formats` | containers: raw, Intel HEX, Motorola S-record, ELF -> `MemoryMap` |
| `radide/firmware/analysis` | entropy, fill, strings, CPU + base address guess, Capstone disassembly + xrefs, Ghidra headless, Firmware Analysis project |
| `radide/firmware/maps` | calibration map definitions, map finder, map packs |
| `radide/firmware/checksum` | checksum algorithms, user-defined blocks, verify / correct, finder, profiles |
| `radide/firmware/project` | ECU project: read-only original, working copy, versions, Build, report, patches |
| `radide/firmware/ui` | the ECU workbench (Qt) |

## Checksums

`radide/firmware/checksum` (pure Python; numpy speeds up word sums).

### Algorithms (`algorithms.py`)

An algorithm is a preset name or a dict (stored in project files and profiles):

```json
{"type": "crc", "width": 16, "poly": "0x1021", "init": "0xFFFF", "refin": false, "refout": false, "xorout": "0x0"}
{"type": "sum", "unit": 2, "unit_endian": "be", "width": 16, "complement": "none | ones | twos"}
{"type": "xor", "unit": 1, "unit_endian": "le", "width": 8, "complement": "none | ones"}
{"type": "adler32"}  {"type": "fletcher16"}  {"type": "fletcher32", "unit_endian": "le"}
```

* **CRC**: any width from 3 to 64 bits with Rocksoft / CRC RevEng parameters. The presets come from the
  catalogue, and each one is tested against the catalogue check value over `"123456789"`:
  * CRC-8, SAE-J1850, AUTOSAR, MAXIM;
  * CRC-16 CCITT-FALSE, XMODEM, KERMIT, X-25, AUG-CCITT, GENIBUS, ARC (IBM), MODBUS, USB, BUYPASS;
  * CRC-32 (zip), BZIP2, MPEG-2, POSIX, JAMCRC, CRC-32C, AUTOSAR.

  Polynomial 0x04C11DB7 runs through `zlib` and 0x1021 through `binascii.crc_hqx`, both reflected and
  non-reflected. Every other polynomial runs in a table-driven Python loop.
* **Sums**: `sum8 / sum16 / sum32`. The result width is separate from the unit that is added: bytes, or
  16-bit / 32-bit words in LE or BE order. The stored value can be plain, `ones` (inverted, `~sum`) or `twos`
  (two's complement, so the whole block adds up to 0).
* **Others**: XOR of bytes or words, Adler-32, Fletcher-16 and Fletcher-32.

The presets are **generic algorithms, never claimed to be a manufacturer's algorithm**. Users must verify every
profile against their own original file.

### Blocks (`blocks.py`)

```json
{"name": "Calibration CRC", "algorithm": "crc32",
 "ranges": [["0x8000", "0xFFFC"]], "skip": [["0xC000", "0xD000"]],
 "store": "0xFFFC", "width": 4, "endian": "be", "complement_at": "0xFFF8",
 "store_mode": "skip | fill00 | fillFF", "repeat": {"count": 8, "stride": "0x100"},
 "enabled": true, "verified": false, "note": ""}
```

* **Ranges** are `[start, end)`. You can give several of them (multi-region). **Skip** ranges are holes left
  out of the ranges.
* The stored value, and its optional **complement copy**, are left out of the computation automatically.
  `fill00` / `fillFF` count those bytes as 00 / FF instead.
* **`repeat`** expands one definition into a multipoint list of equal blocks.
* `verify(data, blocks)` and `correct(bytearray, blocks)` return `BlockResult`s:
  * stored / computed value, complement check, `corrected` with old -> new;
  * `report()` prints them. The report says which blocks were recalculated.
* Blocks are processed **in list order**. Put a block whose ranges cover another block's stored value after
  that block.
* **Profiles**: `save_profile` / `load_profile` write a shareable JSON file. It uses
  `"format": "radide-checksum-profile"` and includes a disclaimer and the file size it was made for.

### Finder (`finder.py`)

`find(original, algorithms=None, granularity=None, starts=, ends=, holes=, search_holes=False, window=16,
confirm_with=[other originals])` tries the algorithms over candidate ranges and looks for a matching value
stored next to them.

**Boundaries.** These are 0, the file end, every multiple of the granularity, and the start / end hints. The
default granularity gives at most 64 blocks.

**Search patterns:**

| Pattern | Meaning |
|---|---|
| after | `[s, p)` stored at `p`, also with a complement copy right before or after the value |
| before | value at `p`, then `[p+w, e)` (a header checksum) |
| hole | `[s, h0) + [h1, p)`, using the given holes or, with `search_holes`, every boundary block |

**Speed:**

* Word sums and XOR use prefix arrays and are vectorised with numpy.
* CRC / Adler checks run incrementally from each start.
* Pure-Python CRCs and Fletcher run under a byte budget. Skipped work is listed in `FindResult.notes`.

**Noise filter:**

* 8-bit algorithms are off by default.
* Values made of one repeated byte (00 00, FF FF) are ignored.
* Candidates are ranked by these signals:
  * exact boundary;
  * complement copy;
  * 32-bit width;
  * range length;
  * range entropy.

  XOR and constant ranges are ranked down.

**Cross-check.** `confirm_with` keeps only the candidates that also hold for other originals of the same
layout. This is the reliable way to remove chance matches of 16-bit values.

Every candidate turns into a block with `Candidate.to_block()`. That block is unverified until the user
confirms it.

## ECU projects

`radide/firmware/project` (pure Python), language plugin `firmware-ecu` (New Project > Firmware), IDE feature
`radide/features/firmware_project.py`.

### ecu.json

| Key | Meaning |
|---|---|
| `original`, `original_sha256`, `original_size`, `original_format` | The original file is copied into `original/` and **made read-only** on disk. Its SHA-256 is checked before every build, and the build stops if the file changed. The project never writes it (`EcuProjectError`). HEX, S-record and ELF originals are loaded through `radide/firmware/formats` into a flat image (gaps filled with 0xFF). |
| `image_base` | Address of offset 0, used for HEX / S19 output. |
| `work` | The working copy: a flat binary, edited in the hex editor or map editor. |
| `checksums` | Checksum blocks (see above). |
| `correct_on_save`, `correct_on_build` | When the working copy is saved in the hex editor (filebus), the blocks are recalculated and the Output window names each recalculated block. |
| `container` | `bin` / `hex` / `s19` / `same`. |
| `output` | `build/<name>_mod.<ext>`. |
| `maps` | A map pack path, or inline map definitions (`radide/firmware/maps`), used for **map-level diffs**. |
| `versions` | `[{id, name, note, created, file, sha256}]`. Each version is a full copy in `versions/vNNN.bin`. |

### Project API

```python
from radide.firmware.project import EcuProject, new_project
ep = new_project(folder, "MyEcu", "stock.bin")       # original/ (read-only) + work/
ep.checksums = [...]; ep.save()
ep.snapshot("Map tweak", "why"); ep.restore("original")   # the unsaved working copy is saved as a version first
d = ep.diff("original", "v001")                       # byte ranges, changed maps (cells, largest change), checksum spans
r = ep.build()                                        # work + corrected checksums -> output + build/<name>_mod.report.txt
ep.export_patch("mod.bps"); ep.import_patch("mod.ips")    # radide/retro/rom/patches.py (IPS / BPS / UPS)
```

* `report.py` writes the modification report as text, or as self-contained HTML. It lists:
  * header: original and output SHA-256;
  * changed maps;
  * checksum results;
  * changed byte ranges with old and new bytes;
  * versions.
* Command line: `python -m radide.firmware.project build|verify|correct|diff|report|find ...`. This is also the
  project's Build / F5.

### In the IDE

**Project > ECU Project:**

* Set Original..., View Original (read-only), Edit Working Copy.
* Checksums...: the block table, the block editor (custom CRC / sum), Verify / Correct, import / export
  profile, and the Checksum Finder tab, which runs in a thread with progress and Cancel and has a cross-check
  field.
* Verify Checksums, Versions... (save / restore / delete, a diff against any version, Hex Compare), Compare with
  Original.
* Build ECU Project, Open Build Output, Export Modification Report..., Export / Import Patch, Build Settings...
* Checksum Toolkit (any file)..., which works without a project and is read-only.

**Solution Explorer** has an "ECU Project" node with these entries:

* Original (read-only);
* Working copy;
* Versions;
* Checksums (n blocks, n verified);
* Build output.

The **"ECU Project (Demo Firmware)"** template writes a synthetic 64 KB image (`synth.py`). It contains no
vehicle data, three checksum blocks and three calibration maps (`maps/demo_ecu.maps.json`). The template also
writes the checksum profile `profiles/demo_ecu.ecuprofile.json`.

**Tests:**

* `samples/Tests/Firmware/Checksum/test_checksum_core.py`;
* `samples/Tests/Firmware/EcuProject/test_ecu_project_core.py`;
* `samples/Tests/Firmware/EcuProject/qa_ecu_project_ide.py` (IDE).

## Formats and analysis

Slice "formats": `radide/firmware/formats` (containers, pure Python), `radide/firmware/analysis` (analysis, pure
Python + numpy; `view.py` and `convert_dialog.py` are the Qt parts), `radide/firmware/disasm` (short entry points
for other slices), `radide/features/firmware_analysis.py`, `radide/languages/firmware_analysis.py`.

### Containers and the memory map

`load(path, base=0)` returns a `MemoryMap`: ordered `Segment(address, data, name, flags)` objects with gaps
between them, `start` (entry point), `symbols`, `sections` (ELF), `header` (S0 text / ELF machine) and `meta`
(`format`, `arch` from ELF `e_machine`, `vle` for PowerPC VLE sections ...). `save(m, path, fmt="")` picks the
format from the extension. `MemoryMap.to_flat(fill=0xFF)` gives one block from the lowest address,
`relocate(delta)` moves a raw image to its real base, and `read` / `write` work on addresses.

| Format | Read | Write | Notes |
|---|---|---|---|
| raw `.bin .ori .mod .rom .dump .dmp .img .fls .eep ...` | yes | yes (gaps filled) | load address = `base` argument or the detected base |
| Intel HEX `.hex .ihex .ihx` | 00 / 01 / 02 / 03 / 04 / 05 | 00 / 01 / 04 / 05 (03 kept) | records never cross 64 KB; checksum errors raise `ValueError` |
| Motorola S-record `.s19 .s28 .s37 .mot .srec .sx` | S0-S3, S5-S9 | S19 / S28 / S37 (smallest that fits), S5/S6 count | S0 header text kept |
| ELF `.elf .axf` | ELF32 / ELF64, LE / BE, PT_LOAD at physical addresses, sections, `.symtab` | minimal executable ELF (PT_LOAD + section per segment + symbols) | Ghidra and objcopy read the written files |

Split / merge (`formats/split.py`): `deinterleave(data, ways=2, width=1)` / `interleave(chips)` (two 8-bit EPROMs
on a 16-bit bus, 16-bit words, 4 chips), `byteswap(data, 2|4|8)`, `wordswap` (ABCD -> CDAB),
`split_sizes` / `split_equal` / `concat`, `merge_maps([(map, offset), ...])` (internal + external flash with a gap,
later maps win) and `overlaps(...)`.

### Analysis

| Module | What |
|---|---|
| `entropy.py` | Shannon entropy per block (numpy) and regions: empty / fill, text, calibration-like (neighbouring 8/16-bit values change slowly - axes, curves, maps), code-like, data, compressed / encrypted-like. Hints, not facts. |
| `fill.py` | runs of one byte (0xFF erased flash, 0x00 ...) and short repeating patterns |
| `strings.py` | ASCII + UTF-16 LE / BE strings; tags for *shapes* that look like part / software numbers, versions, dates and build tags. There is no manufacturer database and nothing is decoded. |
| `arch.py` | CPU guess with confidence + evidence: ARM Cortex-M (Thumb / Thumb-2), ARM A32, PowerPC (Book E / e200 / MPC5xx), PowerPC e200 VLE, Infineon TriCore, Infineon C166 / ST10 / XC16x, Freescale HC12 / S12(X), Renesas SH-2 / SH-4 (BE), V850 / RH850, 68K / CPU32, 8051. Instruction-pattern statistics at the right alignment (minus what random bytes would give), vector tables / boot headers (Cortex-M vectors, MPC5xxx RCHW 0x5A + VLE bit / 0x5AA5 header, AURIX BMHD 0xB359, C166 JMPS traps, HC12 vectors at the end, SH / 68K reset vectors, V850 JR table, 8051 LJMP) and, for byte-coded CPUs, absolute calls that land after a return. Base address: candidates from the vector table, the usual flash start and the pages that many words point into, scored by how many words point exactly at string starts and vector entries (basefind method). |
| `disasm.py` | Capstone listing: ARM / Thumb (M-class), PowerPC 32 BE, TriCore 1.6.2, M68K, SuperH (SH-2A BE, SH-4 LE), HC12 (M680X CPU12), MIPS, x86, ARM64. Labels (`sub_` / `loc_` + ELF symbols + project labels), branch targets, data references (absolute / immediate operands inside the image, ARM / Thumb literal pools with the pointed-to word, SH PC-relative MOV.L, PowerPC LIS + ADDI / ORI / loads, TriCore MOVH.A + LEA / LD). `build_xrefs` indexes calls, jumps and data references over the code regions ("which instructions use the table at 0x0800A1C0"). C166 / V850 / RH850 / 8051 / VLE / RL78 / M16C / M32C / MCS-96 / HCS08 / HCS12X are decoded by the built-in SLEIGH backend (pypcode; see "Built-in SLEIGH disassembly" below), with the same labels and data references. |
| `ghidra.py` | **Analyze in Ghidra**: `analyzeHeadless` with `-processor <language> -loader BinaryLoader -loader-baseAddr <base>` (raw / HEX / S-record) or Ghidra's ELF loader, a post-script that creates functions at the vector entries, then exports the function list and decompiled C (shown read-only). Uses the Ghidra + JDK the EXE importer finds (`GHIDRA_HOME`, `%LOCALAPPDATA%\RADIDE\tools\ghidra*`, `tools\jdk*`). Languages: `ARM:LE:32:Cortex`, `ARM:LE:32:v7`, `PowerPC:BE:32:e500`, `PowerPC:BE:64:VLE-32addr`, `tricore:LE:32:default`, `HCS12:BE:24:default`, `SuperH:BE:32:SH-2A`, `V850:LE:32:default`, `68000:BE:32:CPU32`, `8051:BE:16:default`. |
| `report.py` | `analyze(memory_map)` -> `Analysis` (all of the above + `entry_points()` + `text()` report) |
| `project.py` | Firmware / ECU Analysis project (below) |
| `synth.py` | synthetic test images for the 10 CPU families, generated by RAD IDE: vector table / boot header, functions in the real instruction set with calls and literal pools, pointer table, identification strings, calibration axes / curves / maps whose addresses the code references, 0xFF fill. Every placed address is recorded for the tests. |

Command line: `python -m radide.firmware.analysis info | convert | deinterleave | interleave | byteswap | split |
merge | disasm | xrefs | ghidra | synth | build` (`--help`).

### Built-in SLEIGH disassembly (no Java, no Ghidra install)

CPUs that Capstone does not decode go through Ghidra's SLEIGH engine via **pypcode** (BSD-2-Clause,
<https://github.com/angr/pypcode>; it bundles Ghidra's C++ SLEIGH library and compiled processor specs, Apache-2.0).
`radide/firmware/analysis/sleigh.py` holds the language table, the sweep and a p-code constant propagation;
`disasm.backend(arch)` says `capstone`, `sleigh` or `""`. Listing, labels, branch targets, the reference index, the
analysis view's Disassembly tab and the workbench Disassembly tab use it transparently; "Analyze in Ghidra" stays for
decompilation.

| arch id | CPU | SLEIGH language | source |
|---|---|---|---|
| `8051` | Intel 8051 / MCS-51 | `8051:BE:16:default` | Ghidra (pypcode) |
| `v850` / `rh850` | Renesas V850 / RH850 (V850E3v5) | `V850:LE:32:default` / `V850:LE:32:v850e3v5` | Ghidra (pypcode) |
| `ppc-vle` | PowerPC e200 VLE | `PowerPC:BE:64:VLE-32addr` (context `vle=1`) | Ghidra (pypcode) |
| `c166` (`st10`, `xc16x`) | Infineon C166 / C167 / ST10 | `C166:LE:16:default` | `third_party/ghidra-processors/C166` (MIT, keyhana/c166-ghidra-module) |
| `rl78` | Renesas RL78 | `RL78:LE:16:default` | `third_party/ghidra-processors/RL78` (MIT, xyzz/ghidra-rl78) |
| `m16c` (`r8c`) / `m32c` | Renesas M16C/60, R8C / M16C/80, M32C | `M16C/60:LE:16:default` / `M16C/80:LE:16:default` | Ghidra (pypcode) |
| `mcs96` | Intel MCS-96 (80C196) | `MCS96:LE:16:default` | Ghidra (pypcode) |
| `hcs08` / `hc08` | Freescale HCS08 / HC08 | `HCS08:BE:16:default` / `HC08:BE:16:default` | Ghidra (pypcode) |
| `hcs12x` | Freescale HCS12X (24-bit global addresses: load paged flash at its global address) | `HCS12:BE:24:default` | Ghidra (pypcode) |

Without Capstone, TriCore, SH-2A, 68K / CPU32, HC12 and PowerPC Book E fall back to their SLEIGH languages. Without
pypcode those CPUs show "pip install pypcode" and the Ghidra tab. The vendored modules (`third_party/ghidra-processors`,
upstream files unchanged + LICENSE + README with source URL and commit) are compiled on first use with the SLEIGH
compiler inside the pypcode wheel into `%LOCALAPPDATA%\RADIDE\sleigh\<name>-<hash>` (`sleigh_build.py`; the C166
spec needs one mechanical fix for the C++ compiler: `export` moved to the end of eight `[Rw+]` constructors).

Analysis on the p-code: BRANCH / CBRANCH / CALL / RETURN give targets, calls and returns; LOAD / STORE addresses and
direct code-space operands give data references, with values propagated through registers inside a straight-line run
(V850 `MOVHI` + `LD`, VLE `E_LIS` + `E_LHZ`, C166 `MOV Rw,#tbl` + `MOV Rx,[Rw]`, 8051 `MOV DPTR,#tbl` ... `MOVC A,@A+DPTR`
with an unknown index -> the table base). The reference goes on the instruction that uses the address and on the one
that loaded the constant. C166: `mem` operands are DPP-paged (DPP0-3 reset values 0/1/2/3, `MOV DPPn,#x` tracked),
`EXTP` / `EXTPR` / `EXTS` / `EXTSR` prefixes apply to the next n instructions, SFR / IRAM (0xF000-0xFFFF) are not
reported as data references. The analysis view's **Show P-code** check box prints the p-code under each instruction;
`python -m radide.firmware.analysis disasm FILE --arch c166 --pcode` does the same on the command line. The view's
reference index also starts at the entry points that precede the first entropy "code" region.

Tests: `samples/Tests/Firmware/Sleigh/test_sleigh_core.py` (synthetic 8051 / V850 / VLE / C166 images: prologues,
every call at a function entry, every calibration-table reference; C166 DPP / EXTP / EXTS; hand-assembled RH850,
RL78, M16C, MCS-96, HCS08, HCS12X; p-code, CLI, fallbacks, threads) and `test_sleigh_ide.py` (analysis view and
workbench Disassembly tabs for 8051, V850, C166, VLE).

### Firmware / ECU Analysis project

New Project > Firmware > **Firmware / ECU Analysis** (language `firmware-analysis`, `firmware.json`), or the
**Synthetic ARM Image** template. The original is copied into `original/`, set read-only and its SHA-256 is
recorded; Build (F5) verifies it and writes `build/analysis.txt`. `work/` holds a flat working copy for your own
experiments, `labels.json` names addresses, `notes.md` is yours. This project is for studying a file; the ECU
project (`firmware-ecu`, above) is the one that edits, checksums and builds.

### In the IDE

* **Tools > Firmware & ECU > Analyze Firmware File...**, **Firmware Converter...** (convert, even / odd split,
  byte swap, cut, merge at addresses, interleave), **Create Synthetic Test Firmware...**
* **Project > Firmware Analysis**: Set Original..., Analyze, Verify Original, Make Working Copy, Open Notes /
  Labels; a "Firmware Analysis" node in Solution Explorer; "Analyze Firmware" in the context menu of firmware
  files. `win.firmware_analysis.open_analysis(path, base=None, arch="")` opens the view from other features.
* The analysis view: Overview (CPU / base guesses - double-click to use one, report), Entropy (graph coloured by
  region; double-click opens the hex editor there), Strings (identification-like filter), Disassembly (address /
  entry points, double-click follows a branch or opens the referenced data in hex, References to ...), Ghidra
  (function list + decompiled C, read-only), Memory Map (segments, gaps, ELF sections, symbols). A one-time bar
  shows the safety notice (shared acceptance with the ECU tools).

### Test data and licences

Tests use synthetic images only, plus open-source **rusEFI** firmware (GPL-3.0 with rusEFI's additional terms,
<https://github.com/rusefi/rusefi>) downloaded from its official GitHub releases into `%TEMP%\radide-fw-data`
(`samples/Tests/Firmware/Formats/download_rusefi.py`); nothing large is committed. No manufacturer firmware is
downloaded or included.

## Workbench (UI)

`radide/firmware/ui` (Qt) and `radide/features/firmware_ide.py`: one WinOLS-like layout for a firmware file or
an ECU project. It is a document tab of the IDE, so Save, Save All, the "modified" star and Edit > Undo / Redo
all work on it.

```
+-----------+---------------------------------------------------+------------+
| Project   | Getting Started | Hex | Map Editor | 2D View |    | Properties |
|  original | Disassembly | Analysis | (EEPROM)                 |            |
|  working  |                                                   |            |
|  versions |   hex view = radide/retro/rom/hexdoc.HexDocument  |            |
|  maps     |   (one buffer, one undo stack for hex + map edits)|            |
|  checksums|                                                   |            |
+-----------+---------------------------------------------------+------------+
| Potential Maps | Differences | Checksum Report | Output                     |
+----------------------------------------------------------------------------+
```

The **toolbar** has Build (F7), Verify Checksums (Ctrl+Shift+V), Compare (Ctrl+D), Find Maps (Ctrl+M), Analyze
(Ctrl+Shift+A), Map from Selection and Save Version. Its **More** menu has:

* Correct Checksums, Load Checksum Profile..., Find Checksums (from the original)...;
* Import A2L..., Save Working Copy As (binary)..., Open Original (read-only hex editor), Open in Ghidra;
* Calibration Map Editor (full) and Detailed Firmware Analysis, which open the views of `firmware_maps.py` and
  `firmware_analysis.py`.

A one-time **safety notice** bar is shown at the top. It uses the same QSettings key as
`radide/firmware/project/notice.py`. The **Getting Started** tab explains the workflow in Arabic and English and
lists the keys.

### Modules

| Module | What |
|---|---|
| `adapters.py` | No Qt. A bridge to the other slices: `load_image` (formats), `cpu_guess` / `base_guess` / `analyze` (analysis), `find_maps` / `parse_a2l` (maps), `verify` / `fix` (checksum), `EcuProject` (project), `disassemble` (capstone, or a `disasm` package when one exists). Each call falls back to a small built-in implementation while a slice is missing or raises. `backends()` tells which side answered. |
| `eeprom.py` | No Qt. Generic serial-EEPROM sizes (24Cxx I2C, 93Cxx Microwire, 95xxx SPI, 128 B .. 512 KB) -> chip names, and `swap16` / `swap32` views. There is no field decoding of any kind. |
| `demo.py` | No Qt. A synthetic 256 KB big-endian "PowerPC-style" image with four tables, one value and two checksums (sum16 over the calibration area, CRC32 over the image). It returns the true addresses for tests. It contains no vehicle data. |
| `mapview.py` | `MapEditor`: a heat-coloured table with the axes in the headers. It has Text, 2D and 3D views, and shows raw, physical (factor / offset), hex or diff values. Changed cells are bold red and show the original value in their tooltip. Also `WaveView`, the whole file as a curve. |
| `workbench.py` | `FirmwareWorkbench(path=... \| project_folder=..., eeprom=None, read_only=None)`, the layout above. |

The UI map model is `adapters.MapDef`: address, rows x cols, cell (`u8` `u16be` `u16le` `s16be` ... `f32le`),
factor, offset, unit, and axis addresses and types. `MapDef.from_any()` accepts `maps.model.MapDef`,
`maps.finder.Candidate` and dicts. `to_slice_map()` converts back. Project maps are saved as a `maps` map pack:
ecu.json "maps", or `<work>.maps.json` next to the working copy. Maps of a stand-alone file are saved in
`<file>.maps.json`.

### File associations

* `.s19 .s28 .s37 .srec .mot .ori .eep .e2p` always open in the workbench.
* `.mod` opens in the workbench when it is binary, so Go's `go.mod` stays text.
* `.hex` opens in the workbench when it is Intel HEX and no project of another language is active.
* `.a2l` is imported into the active workbench when one is open; otherwise it opens as text.
* `.bin` opens in the workbench only inside the active ECU project. It opens that project's workbench and
  compares the file with the working copy. Every other `.bin` keeps the ROM workbench or the generic hex view.
* Solution Explorer adds Open With > Firmware & ECU Workbench (and an EEPROM, read-only variant) to every file.
  The project node gets "Open Firmware & ECU Workbench".
* Small files with an EEPROM size (8 KB or less) open in **EEPROM mode**. This mode is read-only and has an
  EEPROM tab with the chip list and the byte order: as read, 16-bit swap or 32-bit swap. Larger stand-alone files
  with an EEPROM size (up to 512 KB) get the EEPROM tab too, but they stay editable.
* HEX and S-record files open read-only at their load address. Save Working Copy As writes a flat binary.

### Menus

* **Tools > Firmware & ECU** (shared with the other firmware features): Open Firmware in Workbench..., Open
  EEPROM Dump (read-only)..., New ECU Project..., New ECU Project (Demo Firmware)..., Compare Firmware Files...,
  Getting Started.
* **Project > ECU Project** (the submenu of `firmware_project.py`): Open Workbench, Find Maps / Verify
  Checksums / Compare with Original / Analyze (workbench), Build in Workbench.
* Opening an ECU project opens its workbench once per session.

### Keyboard

These keys work while the focus is inside the workbench, ahead of the IDE's shortcuts. Text fields keep their own
Ctrl keys.

| Key | Where | Action |
|---|---|---|
| F7 | workbench | Build: the working copy with corrected checksums -> `build/` and a report |
| Ctrl+Shift+V | workbench | Verify checksums |
| Ctrl+D | workbench | Compare with the original (or another file / version) |
| Ctrl+M | workbench | Find potential maps |
| Ctrl+Shift+A | workbench | Analyze: format, CPU and base guess, entropy, regions, identification strings |
| Ctrl+Z / Ctrl+Y | workbench | Undo / redo hex and map edits (one stack) |
| K | hex view | New map from the selected bytes (as in WinOLS) |
| Ctrl+G / Ctrl+F / F3 | hex view | Go to offset, find, find next (from the ROM hex editor) |
| + / - | map table | Raise / lower the selected cells by one raw step |
| Page Up / Page Down | map table | Raise / lower the selected cells by ten steps |
| = / % | map table | Set a value / change by a percentage |
| T / 2 / 3 | map table | Text / 2D / 3D view |

### Tests

* `samples/Tests/Firmware/Workbench/test_workbench_core.py` (no Qt);
* `samples/Tests/Firmware/Workbench/test_workbench_ide.py`: the real IDE through qh.py, with `QA_LANG=ar QA_THEME=dark`
  for the Arabic + dark run. The screenshots go to `%TEMP%\radide-qa\shots\fw_*.png`.

## Calibration maps

`radide/firmware/maps` (pure Python + numpy) and `radide/features/firmware_maps.py` (the full map editor). The
workbench uses the same package through `adapters.find_maps` / `parse_a2l`, and its "Calibration Map Editor
(full)" opens the editor below with the project's original.

### Model (`model.py`)

* `MapDef`: name, file offset `address`, `cols` x `rows`, `dtype` (`u8 s8 u16 s16 u32 s32 f32 f64`), `endian`
  (`le` / `be`), `order` (`row`: X fastest, `col`: Y fastest), `factor` / `offset` (physical = raw x factor +
  offset), `unit`, `folder`, `description`, `lower` / `upper` / `digits`, and two `AxisDef` axes. An axis is
  stored in the file (`address`, `count`, own type / byte order / factor / offset / unit), a list of fixed
  `values`, or the cell index.
* `MapPack`: the maps of one binary + `base_address` (ECU address of file offset 0, for A2L). JSON format
  `radide-mappack` v1, saved as `<file>.maps.json` next to the binary (the ECU project uses the same name for its
  working copy). CSV import / export of the map list (`pack_to_csv` / `pack_from_csv`), Excel text of one map
  (`map_to_tsv`, `parse_tsv` with decimal commas).

### Map finder (`finder.py`)

`find_maps(data)` returns `Candidate` objects (score 0..100, `layout`, ready `mapdef`), best first and
non-overlapping. It reads the file as 8-bit, 16-bit LE / BE (unsigned and signed, both alignments) and float32 LE /
BE (all alignments), takes every strictly increasing run of 4..64 cells as a possible axis, and tries:

| Layout | Bytes |
|---|---|
| `header` | Bosch style `[nx][ny][X axis][Y axis][values]` (also `[ny][nx]`), size cells of the axis type |
| `header-curve` | `[n][axis][values]` |
| `axes` | `[X axis][Y axis][values]` (the Y run may have swallowed the first values: every length is tried) |
| `curve` | `[axis][values]` |
| `axisless` | blocks whose rows look alike at a fixed width (tables with axes elsewhere), lower scores |

The value block is read unsigned and signed, in row and column order; the smoothest reading wins (monotony of the
lines, small steps, small curvature; penalties for jumps across the range, two-valued blocks and fill). A fast
cumulative-sum pre-check skips noise, so a 1 MB file takes a few seconds. Square maps cannot tell row from column
order (a transposed smooth surface is smooth too). `value_profile` gives the min / max per pixel for the 2D view.

### Editing (`ops.py`)

`set_value`, `add`, `add_percent`, `multiply`, `interpolate` (horizontal, vertical, bilinear from the corners),
`smooth` (3x3), `paste` (Excel grid; blanks keep), `copy_text`; `apply(buf, map, phys)` writes a map back as **one
undo step** of a `HexBuffer` (values rounded to the raw resolution and clamped to the type). Differences:
`changed_maps(pack, ori, mod)` (cells, min / max %, axis changed), `cell_diff`, `unmapped_changes`, `diff_ranges`.
Between versions: `locate_in(map, a, b)` (same address, or where B has the same axis bytes) and `copy_map`.

### ASAP2 / A2L (`a2l.py`)

`load_a2l(path, data=None, base=None)` / `parse_a2l(text, ...)` -> `A2LResult(pack, segments, warnings, ...)`.
Common subset: `MOD_COMMON` (`BYTE_ORDER`, `ALIGNMENT_*`), `MOD_PAR` / `MEMORY_SEGMENT`, `CHARACTERISTIC` VALUE /
CURVE / MAP / VAL_BLK (`NUMBER`, `MATRIX_DIM`), `AXIS_DESCR` STD_AXIS / COM_AXIS (`AXIS_PTS_REF`) / FIX_AXIS
(`FIX_AXIS_PAR`, `_DIST`, `_LIST`), `AXIS_PTS`, `RECORD_LAYOUT` (`FNC_VALUES` ROW_DIR / COLUMN_DIR,
`AXIS_PTS_X/Y`, `NO_AXIS_PTS_X/Y` read from the binary for dynamic layouts, `FIX_NO_AXIS_PTS_*`, `RESERVED`,
`SRC_ADDR_*`, alignment), `COMPU_METHOD` IDENTICAL / LINEAR / linear RAT_FUNC (others: raw values + a warning),
`FUNCTION` / `GROUP` -> folders, `FORMAT` -> decimals. `IF_DATA` and `A2ML` are skipped. `MSB_FIRST` = big endian,
`MSB_LAST` = little endian. The base address is the lowest FLASH / ROM memory segment unless given (the import
dialog shows it). `export_a2l(pack)` writes a self-contained A2L (record layouts per type, COMPU_METHODs,
AXIS_PTS for stored axes, FIX_AXIS_PAR_LIST, VAL_BLK, FUNCTION folders) that imports back unchanged.

### TunerStudio ini / msq (`tsini.py`)

For the open-source ECUs **rusEFI** and **Speeduino** (GPL): `load_ini(path)` reads `[Constants]` (pages,
`endianness`, `array` / `scalar` fields, `#if` / `#else`), `[TableEditor]` and `[CurveEditor]` into a map pack whose
addresses are offsets in the *pages image* (page 1 first). Shapes are `[cols x rows]`; TunerStudio's
`phys = (raw + translate) x scale` becomes factor / offset; scales written as expressions import as 1 with a note.
`msq_values(msq)` + `msq_to_image(ini, values)` turn a tune into that image (wrong-sized or unknown values are
skipped).

### The map editor (Tools > Firmware & ECU > Calibration Maps)

`document.MapsDocument` - one binary in a tab:

* left: **Map Pack** (folders, changed maps marked with `*`), **Potential Maps** (Find Maps runs in the
  background; double-click previews, Add to Map Pack keeps), **Differences** (changed maps with cell counts and
  % range, changes outside the maps);
* centre: **Map** (`editor.MapEditor`: table with physical axes in the headers, heat-map / differences-vs-original
  colouring, bold changed cells with the original in the tooltip, 3D surface - drag to rotate - and 2D chart;
  Set Value `=`, +/- % `%`, Add `+`, Multiply `*`, Interpolate `I`, Smooth `S`, Copy / Copy with Axes / Paste
  with Excel, Reset to Original, Properties), **2D View** (`views.FileGraph`: the whole file as a value graph,
  maps as bands, click to jump), **Hex** (the ROM workbench's `HexView` on the same buffer);
* toolbar: Save (binary + map pack; the first save of a file opened without an original keeps
  `<name>.original<ext>`), Undo / Redo (also Edit > Undo / Redo), Find Maps, New Map (at the hex cursor), Import
  (A2L, TunerStudio ini, CSV, map pack), Export (A2L, CSV, map pack), Set Original, Compare With.

`document.CompareDocument` - file A (editable) against file B: the maps that differ (found at the same address or by
their axis bytes), both versions side by side coloured against each other, Copy Map from B to A, Copy All
Different Maps, Hex Compare (the ROM workbench's compare view).

`win.firmware_maps` (API): `open_maps(path, original=None, pack=None, goto=None)`, `compare_maps(a, b, pack=None)`,
`open_tune(ini, msq)`. The hex editor's context menu has "Open in Map Editor".

### Tests and data

* `samples/Tests/Firmware/Maps/test_maps_core.py` (no Qt): the finder ranks the 7 embedded maps of synthetic
  images first (Bosch 8 / 16-bit headers LE / BE, headerless BE column order, float32, curves, signed values), 1 MB
  speed, editing numbers, undo, diffs, copy between shifted versions, JSON / CSV, the A2L sample + round trip, the
  synthetic ini + msq and the real rusEFI ini.
* `samples/Tests/Firmware/Maps/qa_maps_ide.py`: the real IDE (qh.py), screenshots `%TEMP%\radide-qa\shots\maps_*.png`
  (3D view, differences, compare, Arabic).
* `sample_ecu.a2l` + `sample_ecu.py`: an original A2L and the 64 KB image it describes (no vehicle data).
* `download_rusefi.py`: the rusEFI ini and two msq tunes from github.com/rusefi/rusefi (GPL-3.0) into
  `%TEMP%\radide-qa\rusefi`; nothing downloaded is committed. No manufacturer firmware is used anywhere.

## Course and end-to-end QA

- Arabic course `radide/tutorials/firmware-ecu/` (8 lessons: ECU files and the legal / safety side, raw / Intel HEX /
  S-record, memory maps and CPU detection, disassembly and Ghidra, calibration maps and the finder, physical units and
  A2L, checksums, a full project with versions / report / IPS). Every runnable block is checked by
  `radide/tutorials/firmware-ecu/tools/check_lessons.py` (`python run` blocks are standard-library Python the lesson
  viewer runs; `fwpy run` blocks use `radide.firmware.*`). CHM: `python tools/build_chm.py firmware-ecu --verify`.
- `samples/Tests/Firmware/QA/qa_firmware_e2e.py` drives all four firmware features together in the real IDE.
- Cross-feature rules found by that test:
  - the safety notice is one notice: `radide.firmware.project.notice.on_accepted(widget)` hides every notice bar
    (workbench, analysis view, map document) as soon as it is accepted anywhere, including the project's modal dialog;
  - the workbench's project model (`radide/firmware/ui/adapters.EcuProject.native`) re-reads `ecu.json` when another
    tool saved it, so Build Settings chosen in Project > ECU Project are not overwritten by the workbench;
  - a project whose original is Intel HEX or S-record builds to the same container at its addresses by default
    (`container: "same"`).
