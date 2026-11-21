# Open Folder / foreign assembly projects

Folders for **File > Open Folder** on assembly code that has no RAD IDE project file
(`radide/project_detect.py` `_asm`, `radide/foreign/asm_folder.py`). Each one is detected as an Assembly
program with its dialect guessed from the code, and opens **in place** (nothing is written into the folder;
builds go to the IDE state folder).

| Folder | What it shows | Dialect | Run |
|---|---|---|---|
| `NasmLoose` | `hello.asm` + `macros.inc` (an include file is a module, not a run target) | NASM x64 | nasm -f win64 + gcc |
| `MasmLoose` | MASM x64 (`.code`, `main PROC`, `END`) | MASM | ml64 via vcvars64.bat (Visual Studio only, never downloaded) |
| `FasmLoose` | `format PE64 console`, imports with win64a.inc | FASM | fasm writes the .exe |
| `GasLoose` | AT&T syntax `hello.s` | GNU as | gcc |
| `Dos8086Loose` | 16-bit `.COM` (`org 100h`, `int 21h`) | 8086 | the 8086 emulator session (F5 / Ctrl+F5) |
| `SasmProgram` | SASM style (`%include "io64.inc"`, `CMAIN`); SASM's include folder is used when SASM is installed | NASM | nasm + gcc |
| `RadAsmProject` | RadASM `Hello.rap` (INI: `[Project] Assembler=`, `[Files]`) | NASM | opens through the .rap |
| `WinAsmProject` | WinAsm Studio `Hello.wap` (INI: `[FILES]`, `[MAKE]`) | MASM 32-bit | ml (Visual Studio) |
| `VsMasmProject` | Visual Studio `.vcxproj` with the masm build customization: C++ `main.cpp` calls MASM `add3.asm` | MASM | MSBuild; without VC tools the MinGW fallback assembles the MASM items with ml64 |

Tests:

    python samples/Tests/Assembly/OpenFolder/test_open_folder.py   # headless: detection, dialects, build + run, .rap/.wap, vcxproj, Open with list, exe -> NASM listing
    python samples/Tests/Assembly/OpenFolder/test_ide_open.py      # the IDE (QSettings "RADIDE-TEST"): open in place, Ctrl+F5, RadASM, 8086 session, course
