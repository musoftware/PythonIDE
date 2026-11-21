# Assembly samples and tests

Curated projects and test scripts of RAD IDE's assembly support (overview: [docs/ASSEMBLY.md](../../../docs/ASSEMBLY.md)).
Every folder has its own README. Open a project folder with **File > Open Project** (it has a `project.radproj`)
or **File > Open Folder** (the folders of `OpenFolder/` have none on purpose).

## Project types (New Project > Assembly)

| Sample | Plugin / dialect | Shows |
|---|---|---|
| [CoreNasmConsoleX64](CoreNasmConsoleX64/README.md) | asm-nasm, x64, gcc | puts / printf / scanf, a loop, a Win32 call |
| [CoreNasmConsoleX86](CoreNasmConsoleX86/README.md) | asm-nasm, x86, GNU ld | cdecl / stdcall, `_printf`, `_GetComputerNameA@8` |
| [CoreNasmWinApi](CoreNasmWinApi/README.md) | asm-nasm, x64 | MessageBoxA, MessageBeep, CMOVE |
| [CoreNasmForms](CoreNasmForms/README.md) | asm-nasm, x64, GUI Bridge | a designed form, `handler btnAdd_Click`, `rad_*` macros |
| [CoreFasmX64](CoreFasmX64/README.md) / [CoreFasmX86](CoreFasmX86/README.md) | asm-fasm | `format PE64 console`, no linker |
| [CoreMasmX64](CoreMasmX64/README.md) / [CoreMasmX86](CoreMasmX86/README.md) | asm-masm (Visual Studio) | ml64 / ml + link.exe, PROTO / INVOKE |
| [CoreGasAtt](CoreGasAtt/README.md) / [CoreGasIntel](CoreGasIntel/README.md) | asm-gas | AT&T and `.intel_syntax noprefix` |
| [CoreErrorList](CoreErrorList/README.md) | asm-nasm | an assembler error and a linker error in the Error List |
| (templates `nasm_forms_x86`, `fasm_forms`, `gas_forms`, `gas_forms_intel`) | NASM x86, FASM x64, GNU as AT&T / Intel + GUI Bridge | the form template in every flavor - built by `CoreTests/test_form_flavors.py` |
| (template `nasm_dll_x64`) | asm-nasm, class library | a DLL with exports, called from Python / C / C# - `CoreTests/test_class_library.py` |

## 8086 teaching emulator (New Project > Assembly > 8086 Assembly (Emulator))

| Sample | Shows |
|---|---|
| [Emu8086Hello](Emu8086Hello/README.md) | INT 21h text output |
| [Emu8086SumArray](Emu8086SumArray/README.md) | arrays and loops |
| [Emu8086StringReverse](Emu8086StringReverse/README.md) | full segments, INT 21h / 0Ah line input |
| [Emu8086InputNumber](Emu8086InputNumber/README.md) | emu8086.inc macros, binary output |
| [Emu8086Factorial](Emu8086Factorial/README.md) | recursion, `[bp+4]` |
| [Emu8086BubbleSort](Emu8086BubbleSort/README.md) | sorting in memory |
| [Emu8086Colors](Emu8086Colors/README.md) | INT 10h and the B800h text screen |
| [Emu8086KeyGame](Emu8086KeyGame/README.md) | INT 16h arrow keys |
| [Emu8086Structs](Emu8086Structs/README.md) | STRUC / ENDS, IF / IFDEF / IFB, export to a DOS .EXE |

## Open Folder, other assembly IDEs, Visual Studio + MASM

| Sample | Shows |
|---|---|
| [OpenFolder](OpenFolder/README.md) | loose NASM / MASM / FASM / GNU as / 8086 / SASM folders, RadASM `.rap`, WinAsm `.wap`, a `.vcxproj` with MASM items - all opened in place |

## The Arabic Assembly course (Help > Tutorials, `radide/tutorials/assembly`, docs/chm/RADIDE_ASSEMBLY_ar.chm)

| Sample | Shows |
|---|---|
| [CourseNumberAnalyzer](CourseNumberAnalyzer/README.md) | the final project (lesson 15): two files, scanf in a loop, sorting, primes, a chart |
| [CourseFormCalculator](CourseFormCalculator/README.md) | the GUI Bridge calculator of lesson 12 |

## Editor and debugger test material

| Folder | For |
|---|---|
| [AsmIntel](AsmIntel/README.md) | highlighting, IntelliSense, hover, outline of every dialect |
| [NativeDebug](NativeDebug/README.md) | Registers / Disassembly / Memory / Stack windows, step instruction |
| [AsmLsp](AsmLsp/README.md) | asm-lsp: install plan / GitHub release download, the LSP client, the built-in fallback |

## Test scripts

| Script | Tests |
|---|---|
| `CoreTests/run_all.py` | toolchains, templates, build, Error List, run specs, form bridge (all flavors), class library, FASM / MASM line tables, F5 in an external console, IDE ([README](CoreTests/README.md)) |
| `Emu8086Tests/test_*.py` | the emulator: assembler, CPU, samples, IDE, STRUC / conditional assembly / .COM and MZ .EXE export (`test_struc_cond_export.py`) |
| `AsmLsp/test_asm_lsp.py` | asm-lsp install / LSP client / fallback |
| `AsmIntel/tests` | editor intelligence |
| `NativeDebug/test_native_debug.py` | the native debugger windows |
| `OpenFolder/test_open_folder.py`, `OpenFolder/test_ide_open.py` | detection, in-place builds, foreign projects, exe -> NASM listing, IDE |
| `CourseTests/test_course_forms.py`, `radide/tutorials/assembly/tools/check_lessons.py` | the course ([README](CourseTests/README.md)) |
| `QA/test_user_flow.py` | the IDE as a user drives it: New Project -> Ctrl+F5 with the Program Input bar, forms, Error List, IntelliSense, F5 with Registers / Disassembly / Memory (and stdin under the debugger), C regression, emulator, CHM / Tutorials, Open Folder F5, Arabic + dark screenshots ([README](QA/README.md)) |
