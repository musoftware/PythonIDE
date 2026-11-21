# Assembly language support

RAD IDE supports x86 / x86-64 assembly on Windows the way it supports C, Fortran or Rust: project types in
File > New Project > **Assembly**, Build / Run / Debug, the Error List, IntelliSense, a visual form designer
through the GUI Bridge, samples and an Arabic course. Several parts were written in parallel; each part has
its own section below (append yours, do not rewrite the others).

| Part | Code | Section |
|---|---|---|
| Toolchains, project types, build / run, error parsing, GUI Bridge forms, debug information | `radide/asm/`, `radide/languages/asm_*.py`, `radide/features/asm_build_ui.py` | [Core](#core-toolchains-projects-build-run-forms) |
| Editor: highlighting, IntelliSense, hover, LSP | `radide/asm_intel/`, `radide/features/asm_ide.py` | [Editor intelligence](#editor-intelligence-highlighting-intellisense-hover-outline-lsp) |
| Native debugger: registers, disassembly, memory, step instruction | `radide/nativedbg.py`, `radide/features/native_debug.py` | Native debugger |
| 8086 teaching emulator | `radide/emu8086/`, `radide/languages/emu8086.py` | 8086 emulator |
| Samples, Open Folder, foreign projects, Arabic course | `samples/Tests/Assembly`, `radide/foreign/asm_folder.py`, `radide/tutorials/assembly` | Samples and course |

---

## Core: toolchains, projects, build, run, forms

### Language plugins and project types

Four language plugins (`radide/languages/asm_*.py`, shared base `asm_base.py` = `AsmIntelMixin` from the
editor part + `BridgeLanguagePlugin`). Each lists its New Project templates with `project_templates()` and
creates them with `create_new_project()` (`radide/asm/templates.py`).

| Plugin id | Display name | Ext. | Templates (template id) |
|---|---|---|---|
| `asm-nasm` | Assembly (NASM) | `.asm` | Assembly Console (x64 Windows, NASM) `nasm_console_x64` - Assembly Console (x86 Windows, NASM) `nasm_console_x86` - Win32 API (x64, NASM) `nasm_winapi_x64` - Assembly Windows Forms (NASM + GUI Bridge) `nasm_forms` - Assembly Class Library (x64 DLL, NASM) `nasm_dll_x64` - Assembly Windows Forms (x86, NASM + GUI Bridge) `nasm_forms_x86` |
| `asm-fasm` | Assembly (FASM) | `.asm` | FASM Console (x64) `fasm_console_x64` - FASM Console (x86) `fasm_console_x86` - FASM Windows Forms (x64, GUI Bridge) `fasm_forms` |
| `asm-masm` | Assembly (MASM) | `.asm` | MASM Console (x64) `masm_console_x64` - MASM Console (x86) `masm_console_x86` (only usable with Visual Studio) |
| `asm-gas` | Assembly (GNU as) | `.s` | GNU as Console (x64, AT&T syntax) `gas_console_x64` - GNU as Console (x64, Intel syntax) `gas_console_x64_intel` - GNU as Windows Forms (x64, AT&T syntax, GUI Bridge) `gas_forms` - GNU as Windows Forms (x64, Intel syntax, GUI Bridge) `gas_forms_intel` |

Every console template shows Hello World, the C runtime (`puts`, `printf`, `scanf`, `fflush`) and a Win32 API
call (`GetComputerNameA`); the Win32 API template shows `MessageBoxA` / `MessageBeep`. The class library
template writes `<Project>.asm` (exports `asm_add`, `asm_factorial`, `asm_sum_array`, `asm_strlen`, `asm_upper`,
`asm_version` with NASM's `export` directive), `<Project>.h`, `UseFromPython.py` (ctypes; Ctrl+F5 runs it),
`UseFromC.c` (`gcc UseFromC.c -L. -l<Project>`) and `UseFromCSharp.cs` (`DllImport`, for a RAD IDE C# project);
only the `.asm` is a project module. `.asm` files open with
`asm-nasm` unless the project language is another `.asm` plugin (`PREFERRED_FOR_EXT` in
`radide/languages/__init__.py`). The New Project dialog shows the group "Assembly" (`radide/dialogs.py`).

### Project settings (`project.radproj`, key `"asm"`)

```json
"asm": {"assembler": "nasm", "arch": "x64", "linker": "gcc", "entry": "main",
        "subsystem": "console", "libs": ["user32"], "debug": true, "console": "ide",
        "output": "exe", "syntax": "att"}
```

| Key | Values | Default |
|---|---|---|
| `assembler` | `nasm` `fasm` `masm` `gas` | from the plugin |
| `arch` | `x64` `x86` | `x64` |
| `linker` | `gcc` (C runtime start-up, `main`), `ld` (no C start-up: `-e entry`, direct DLL linking), `golink`, `link` (MASM), `none` (FASM writes the .exe) | nasm/gas x64: `gcc`, x86: `ld`; fasm: `none`; masm: `link` |
| `entry` | entry symbol (`main`, `_main`, `start`) | `main` (`_main` for NASM x86, `start` for FASM) |
| `subsystem` | `console` `windows` | `console` |
| `libs` | extra libraries / DLLs (`user32`, `gdi32` ...) | `[]` |
| `debug` | line debug information for gdb | `true` |
| `console` | `ide` (Output window + Program Input bar) or `external` (own console window, "Press any key"; under F5 the program gets its own console too: gdb's `new-console`) | `ide` |
| `output` | `exe` (`_radapp.exe`) or `dll` (a class library: `<Project>.dll` + `lib<Project>.a`, entry `DllMain`, linked with `gcc -shared -nostdlib` (x64) / `ld -m i386pe --dll` (x86); Ctrl+F5 runs `UseFromPython.py`) | `exe` |
| `syntax` | GNU as forms: `att` (`radgui_att.inc`) or `intel` (`radgui_intel.inc`) | `att` |

`radide.asm.build.settings_for(project)` merges them with the defaults. Tools > **Assembly Toolchains...**
edits them for the current project.

### Toolchains (`radide/asm/toolchain.py`)

| Tool | Looked up in | Missing |
|---|---|---|
| NASM | PATH, `%LOCALAPPDATA%\RADIDE\tools\nasm\nasm.exe`, `C:\Program Files\NASM` | downloaded on the first build: `https://www.nasm.us/pub/nasm/releasebuilds/3.02/win64/nasm-3.02-win64.zip` |
| FASM | PATH, `%LOCALAPPDATA%\RADIDE\tools\fasm\FASM.EXE` (+ `INCLUDE\`, given to FASM through `%INCLUDE%`) | downloaded on the first build: `https://flatassembler.net/fasmw17335.zip` |
| GoLink (optional) | PATH, `%LOCALAPPDATA%\RADIDE\tools\golink\GoLink.exe` | Tools > Assembly Toolchains > Download (`https://www.godevtool.com/Golink.zip`) |
| gcc, as, ld, gdb, objcopy | the MinGW-w64 toolchain of the C support (`c_bridge.find_native`: PATH, `%LOCALAPPDATA%\RADIDE\toolchains\mingw64\bin` (WinLibs), MSYS2 ...) | install WinLibs (as for C) |
| ml64 / ml | Visual Studio with the C++ tools (vswhere -> `VC\Tools\MSVC\*\bin\Hostx64\x64|x86`) | never downloaded |

None of the three sites publishes checksums, so `RELEASES` pins the SHA-256 measured when this was written; a
file with another hash is deleted and the user is sent to the official page. Archives are unpacked with a
path check (no absolute / `..` paths) and a `RADIDE-SOURCE.json` is written next to the tool.
API: `find(tool)`, `ensure(tool, log)` (downloads NASM / FASM / GoLink), `install(tool, log)`, `status()`,
`version(tool)`, `missing_hint(tool)`.

### Build (`python -m radide.asm.build <folder> [--release] [--check]`)

Build / Run / Debug use the GUI Bridge runner: `run_spec()` returns
`python -m radide.runtimes.bridge <folder> --build "python -m radide.asm.build <folder>" -- _radapp.exe`.
A project without forms runs as a console program (bridge console mode, stdin/stdout inherited); a project with
forms runs as a GUI Bridge program. `radide.asm.build.Builder`:

| Assembler / arch | Commands (objects in `_build\`) |
|---|---|
| NASM x64 | `nasm -f win64 -I <folder>\ -P _build\<m>.anchor.inc -l _build\<m>.lst -o _build\<m>.obj <m>.asm` (+ DWARF object, below) -> `gcc -g objs -static -o _radapp.exe` |
| NASM x86 | `nasm -f win32 ...` -> `ld -m i386pe --subsystem console -e _main --enable-stdcall-fixup objs -L C:\Windows\SysWOW64 -lmsvcrt -lkernel32 -luser32` (links straight against the system DLLs: the MinGW-w64 gcc has no 32-bit libraries) |
| GNU as | `as --64|--32 --gdwarf-3 -o _build\<m>.o <m>.s` -> gcc (x64) / ld i386pe (x86). Plain `-g` writes STABS on PE, which breaks the link. |
| FASM | `fasm -s _build\main.fas main.asm _radapp.exe` with `INCLUDE=<fasm>\INCLUDE` (`format PE` / `PE64`), then the DWARF lines from the `.fas` are added to the exe (below); a source with `format MS COFF` / `MS64 COFF` becomes an object (+ a DWARF object) linked with gcc / ld. FASM assembles one file: the file with `format` is the main file, the others are `include`d. FASM forms: every form file / module with a `format` line and `_radmain.asm` is its own object. |
| MASM | `cmd: call vcvars64.bat (vcvars32.bat) && ml64 /c /Zi /Sa /Fl_build\m.lst (ml /c /coff /Zi /Sa /Fl...) && link /DEBUG /INCREMENTAL:NO /MAP:_build\_radapp.map /SUBSYSTEM:CONSOLE objs msvcrt.lib legacy_stdio_definitions.lib ucrt.lib vcruntime.lib kernel32.lib user32.lib`, then the DWARF lines from the listing + map are added to the exe |
| NASM x86 forms | the NASM objects + `gcc -m32 -c` of radgui.c / radasm.c / radcrt32.c, `dlltool` makes a 32-bit ws2_32 import library, `ld -m i386pe -e _main ... -lucrtbase -lkernel32` (SysWOW64) |
| class library | `gcc -shared -nostdlib -Wl,--entry,DllMain -Wl,--out-implib,lib<Project>.a objs -o <Project>.dll -lkernel32 -luser32 -lmsvcrt` |
| GoLink | `GoLink /console /ni /entry <entry> [/64] objs kernel32.dll user32.dll msvcrt.dll /fo _radapp.exe` |

The builder prints every command and message (Output window), ends with `Build succeeded: _radapp.exe` or
`Build failed: <why>`, and writes `_build\diagnostics.json` = `{"ok", "exe", "diags": [{severity, message,
file, line}]}`. `Builder.check(texts)` assembles without linking (unsaved editor texts win) - the Error List on
save. `--release` turns the debug information off (and strips the exe).

### Error List (`radide/asm/errors.py`, `radide/features/asm_build_ui.py`)

`errors.parse(text, folder, line_of)` understands NASM (`f.asm:12: error: ...`), GNU as (`f.s:12: Error:`),
gcc (`f.c:10:5: error:`), MASM (`f.asm(12) : error A2008:...`), FASM (`f.asm [12]:` ... `error: ...`), GNU ld
(`x.obj:f.asm:(.text+0x11): undefined reference to ...` - the offset is turned into a line through the NASM
listing - and `f.asm:13:(.text+0x11):` when DWARF lines exist), MS link (`x.obj : error LNK2019:`) and GoLink.
`errors.locate_unresolved()` points "unresolved external symbol foo" at the first line that uses `foo`.
The feature `asm_build_ui.py` adds a `diag_providers` entry (syntax check on save + the last build's link
errors) and, after a build, replaces the Error List rows with `_build\diagnostics.json`.

### Running console programs

* `console: "ide"` (default): the program's output is in the Output window; a **Program Input** dock (Enter =
  one line, "End of input" closes stdin) appears while a Ctrl+F5 console run is active.
* `console: "external"`: `python -m radide.asm.console _radapp.exe` opens its own console window, keeps it
  open at the end ("Program exited with code N", pause) and returns the exit code. **F5** starts gdb with
  `-iex "set new-console on"` (`AsmDapSession(new_console=True)` from `asm_console_session`): the program runs
  under the debugger in its own console window and reads its input there (no Program Input bar); the window
  closes when the program ends (put a breakpoint on the last line to read it).

### Windows Forms through the GUI Bridge (NASM x64 / x86, FASM x64, GNU as x64)

Five flavors (`radide/asm/formgen.py` `flavor_for(settings)`), the same files in each assembler's syntax:

| Flavor | Template | Runtime include | Form1.inc | Main program | Linked by |
|---|---|---|---|---|---|
| `nasm64` | `nasm_forms` | `radgui.inc` | `%define btnAdd "btnAdd"` | `_radmain.asm` | gcc + radgui.c |
| `nasm32` | `nasm_forms_x86` | `radgui32.inc` (cdecl: the macros push their arguments, results in EAX) | `%define` | `_radmain.asm` (`_main`, strcpy / strcat / _stricmp, ExitProcess) | gcc -m32 -c + ld i386pe + ucrtbase.dll (`radcrt32.c`: printf / snprintf wrappers) |
| `fasm64` | `fasm_forms` | `radgui_fasm.inc` (starts the object: `format MS64 COFF`; strings with `eqtype ''`) | `btnAdd equ 'btnAdd'` | `_radmain.asm` (FASM) | gcc + radgui.c |
| `gas64` | `gas_forms` | `radgui_att.inc` | `.equ CTL_btnAdd, 1` | `_radmain.s` | gcc + radgui.c |
| `gas64i` | `gas_forms_intel` | `radgui_intel.inc` | `.equ` | `_radmain.s` | gcc + radgui.c |

GNU as removes the quotes of macro arguments, so its macros decide by the argument's role: object / property /
text arguments are a register (a char* you prepared) or anything else, taken as text (`rad_set lblOut, Text,
"Hello world"`); integer arguments are `$42` / `%rbx` / `clicks(%rip)` (AT&T) or `42` / `rbx` /
`QWORD PTR [rip + clicks]` (Intel). Strings are kept inline in the code (`jmp` over them: GNU as on PE has no
`.pushsection`). `plugin.code_flavor(code)` reads the flavor from the include a form's code names;
`prepare()` copies the flavor's files, writes the main program and rewrites an untouched new form's code that
was made before the project's flavor was known.

The NASM x64 form is designed in the normal designer; the program is linked from:

| File | Written by | What |
|---|---|---|
| `Form1.asm` | the user (template on creation) | `handler <Control>_<Event>` ... `endhandler` blocks. Never regenerated. |
| `Form1.inc` | `generate_designer()` on every form save (and `prepare()` before each run) | `%define btnAdd "btnAdd"` for the form, every control and menu item + `CTL_btnAdd equ 3` control IDs |
| `_radmain.asm` | `main_source()` before each run | `main`: `rad_init`, then `rad_next_event` -> `sprintf(key, "%s_%s", rad_obj, rad_ev)` -> `_stricmp` against the handler table -> call -> `rad_done` |
| `radgui.inc` | copied from `radide/asm/runtime/` | macros `handler / endhandler`, `rad_set`, `rad_get`, `rad_set_int`, `rad_get_int`, `rad_call`, `rad_msgbox`, `rad_input`, `rad_show`, `rad_hide`, `rad_end`, `rad_print`, `rad_arg`, `rad_str_int`, `rad_int_str`, `radcall` |
| `radgui.c`, `radgui.h` | copied from the C client (`runtimes/clients/c`) | the GUI Bridge protocol + RAD Hub |
| `radasm.c` | copied from `radide/asm/runtime/` | `rad_set_int`, `rad_get_int`, `rad_str_int`, `rad_int_str` |

Macro arguments may be string literals, `%define`d names, labels (address), registers, numbers or memory
operands (`[clicks]`); arguments go to RCX, RDX, R8, R9 in order (do not pass RCX/RDX/R8 as a later argument).
Every macro aligns the stack itself, so it works anywhere. `handler` saves RBX, RSI, RDI, R12 (free to use in
the handler) and aligns RSP; do not change RBP / RSP inside a handler. Handlers are found by
`radide.asm.formgen.handlers_in()` (`handler X_Y` blocks, or `X_Y:` labels declared `global`).
Double-clicking a control adds `handler btnAdd_Click` / `endhandler` (`add_handler`). The other flavors work
the same way (see the table above); handlers declared with `.globl` / `public` labels are found too.

### Debug information (for the native debugger)

Findings on Windows with the WinLibs gdb 16 / binutils 2.47:

* `nasm -f win64 -g` can only write **CodeView 8** (`-F cv8`) - gdb ignores it.
* `nasm -f elf64 -g -F dwarf` + `objcopy -O pe-x86-64` gives a COFF object with DWARF sections, but the
  relocations are converted wrongly (`R_X86_64_PC32` -> `IMAGE_REL_AMD64_ADDR32`, "relocation truncated to
  fit", "illegal symbol index") - not usable.
* **What RAD IDE does** (`radide/asm/dwarf.py`): NASM assembles the real win64 / win32 object with a
  pre-included anchor (`-P`: `global __radsec_<module>` at offset 0 of `.text`) and a listing (`-l`). The
  listing gives the `.text` offset of every source line (macro expansions belong to the calling line, lines
  of `%include` files are skipped, `[section]` / `__?SECT?__` inside macros are followed). A GNU as source
  `_build\<m>.dbg.s` with `.debug_abbrev` / `.debug_info` / `.debug_line` (DWARF 3, addresses =
  relocations against the anchor) is assembled to `_build\<m>.dbg.o` and linked with the program.
  Verified: `break main.asm:50`, `next` (steps over `call printf`), `info line *$pc`, `stepi`, breakpoints in a
  form handler (`break Form1.asm:21`), also for **32-bit** NASM programs debugged by the 64-bit gdb (WOW64).
* GNU as: `--gdwarf-3` (not `-g`, which writes STABS).
* **FASM** (`radide/asm/linetable.py`): the build asks FASM for its symbolic information (`fasm -s`, format
  in FASM's `TOOLS\FAS.TXT`): for every assembled line the preprocessed line (macro lines lead back to the
  line that called the macro: `cinvoke printf, ...` is one line) and the `$` address. For `format PE / PE64`
  the rows inside the code sections become a DWARF 3 compile unit + line table + one `DW_TAG_subprogram` per
  label (gdb names the frame `start`), written as raw bytes and **appended to the exe as new `.debug_abbrev` /
  `.debug_info` / `.debug_line` sections** (`pe_add_sections`: long names in a COFF string table, the header
  block grown when FASM filled it; objcopy is not used - it rewrites a FASM image and breaks it). For `format
  MS64 COFF` objects (FASM forms) the same table is a GNU as source with relocations against a public label
  of the section, assembled and linked next to the object.
* **MASM**: `/Zi` + `link /DEBUG` = PDB for the Visual Studio debugger, and for gdb: the listing (`/Fl /Sa`:
  INVOKE / .IF code is listed with `*`, macro expansions with a nesting digit - both belong to the line that
  produced them) gives each line's offset in the code segment, the map (`/MAP`, `/INCREMENTAL:NO`) the address
  of a procedure of the module, which fixes the module's base; the DWARF sections are appended to the exe as
  for FASM. gdb relocates them itself when Windows loads the program elsewhere (ASLR). Verified with ml64 and ml
  14.44: `break main.asm:32` on an `invoke` line, `info line *$pc`, frame `main`.
* The builder leaves `_build\dwarf.ok` when FASM / MASM got DWARF lines; `debug_info()` then says `"dwarf"`.
* F10 on an assembly line with DWARF (`nativedbg._AsmMixin`): gdb's line `next` needs unwind information to
  notice it entered a call, and a line that moves RSP / ESP (FASM `cinvoke`, MASM `INVOKE`) would stop inside
  the called function. The session steps by instructions (`next`, granularity instruction) until the line
  changes; when an instruction step still lands in a function without source (an import thunk, 32-bit code),
  it reads the return address from the stack, puts a temporary instruction breakpoint there and continues.
* There is no call-frame information (CFI) for assembly code: `bt` past an assembly frame is unreliable
  (frame 0 and the registers are always right).
* `plugin.debug_info(project)` returns `{"exe", "arch", "assembler", "linker", "line_info": "dwarf" |
  "codeview" | "none", "listings": "<folder>\_build"}` - the listings `_build\<m>.lst` map offsets to lines
  too (`dwarf.parse_listing`). The build command needs no change for debugging: it always produces the
  debug information unless `"debug": false`.
* `AsmPluginBase.make_session(win, spec, debug)` forwards to `nativedbg.asm_console_session` (native debugger
  part, below): F5 on a console project builds, then launches the program under gdb.

### Tests (curated projects in `samples/Tests/Assembly`)

Create + build + run of all 15 templates (input `7`; the class library through its Python client), the form
handlers of all five flavors over the GUI Bridge protocol, in the bridge host window and with a gdb breakpoint
by line (`CoreTests/test_form_flavors.py`, 40 checks), the class library from Python / C / C# (`test_class_library.py`),
FASM / MASM line tables and F10 (`test_linetables.py`, 43 checks), F5 in an external console with input typed
into the program's own console (`test_external_console.py`), the form handlers over the GUI Bridge protocol and in
the bridge host window (`btnAdd_Click` changes `txtNumber`, `lblClicks`, `lblMessage`), the Ctrl+F5 path
(`run_spec`), gdb by line for NASM x64 / x86 and GNU as, error rows (file + line) for NASM, GNU as, FASM, MASM,
ld, MS link and a form, and the IDE (New Project group, opening a form project, Error List on save,
Tools > Assembly Toolchains).

---

## Native debugger: registers, disassembly, memory, step instruction

Code: `radide/nativedbg.py` (engine helpers, the `.asm` line table, the assembly debug sessions) and
`radide/features/native_debug.py` (the tool windows). They work for **every gdb session** - C, C++, Fortran,
Rust (GNU target), Go built with gcc, assembly - launched (`DapSession("gdb")`), attached
(`bridgedebug.AttachDap`, Debug > Attach to Process) or wrapped (`BridgeDebugSession.dap`, `ChainSession.inner`).

### Windows (Debug > Windows)

| Window | Shortcut | What |
|---|---|---|
| Registers | Alt+5 | General purpose registers (hex or decimal), the flags register decoded bit by bit (CF PF AF ZF SF TF IF DF OF, double-click toggles a flag), segments; "SSE / FPU" adds xmm0-15 (128-bit hex), mxcsr and the x87 registers. Values changed by the last step are red; double-click a value to change it (`$rax = ...`). |
| Disassembly | Alt+8 | Intel syntax from the start of the current function, yellow arrow on the next instruction, source lines in between (DWARF of C / Rust / RAD IDE NASM builds, or the `.asm` line table below), optional code bytes, address / label / expression box, Step Into / Over Instruction, breakpoints on addresses (click the left column, F9, context menu). Comes up by itself when the program stops where there is no source. |
| Memory 1 | Alt+6 | Hex + ASCII, 1 / 2 / 4 / 8-byte columns (little-endian values), address box (`0x401000`, `$rsp+16`, `&buf`, a label without debug type such as `values`), "Follow" a register, re-evaluated at every stop, changed bytes red, unreadable memory `??`, double-click to write bytes (`90 90 CC` or `"text"`), page up / down. |
| Stack | - | The machine stack from RSP / ESP (a few slots above it greyed), one pointer per row, RSP / RBP marked, "Points to" = symbol + offset; double-click opens the value in the Memory window. |

Debug menu: **Step Into Instruction** (Ctrl+Alt+F11), **Step Over Instruction** (Ctrl+Alt+F10), **Go To
Disassembly**. For assembly frames without line information F10 / F11 step one instruction anyway.

### DAP requests used (gdb 14+, verified with the WinLibs gdb 18.1)

`stackTrace` (`instructionPointerReference`), `evaluate` context `repl` (`info registers [sse|float]` - fresh
after a register was changed, unlike the cached "Registers" scope; `info symbol`; `info files` for the
run-time entry point; `set disassembly-flavor intel`), `setExpression` (`$rax`, `$eflags`), `readMemory` /
`writeMemory`, `disassemble` (`resolveSymbols`; gdb ignores a negative `instructionOffset`, so the window
starts at the function start found with `info symbol`), `next` / `stepIn` with `granularity: "instruction"`,
`setInstructionBreakpoints`, launch `stopOnEntry` (= `starti`). Other adapters (Delve, netcoredbg) get the
"Registers" scope / `disassemble` / `readMemory` when they answer them; the gdb command fallbacks are gdb only.

### Assembly debugging (F5)

* **RAD IDE NASM / GNU as / FASM / MASM projects** carry DWARF lines (core section above; FASM and MASM since
  `radide/asm/linetable.py`): gdb handles the breakpoints of `.asm` lines itself; F10 steps by line over the
  calls of the line (by instructions, see "Debug information"), the windows above add the machine view.
* **Programs without DWARF lines** (`"debug": false`, Open Folder FASM / MASM folders, projects built by
  other scripts, NASM objects from elsewhere): `AsmLineMap.build(exe, sources)` assembles each `.asm` again
  into `%LOCALAPPDATA%\RADIDE\cache\asmdbg\<hash>` with a listing, takes the section offsets from `objdump -t`
  of that object and `nm` of the program, and maps `.asm` line <-> static address. ASLR is handled with the
  slide = run-time entry point (`info files`) - static entry point (`objdump -f`). Breakpoints on mapped
  `.asm` lines become instruction breakpoints (also conditions); stops are shown on the `.asm` line, the
  registers also appear in Locals; F10 / F11 = `nexti` / `stepi`; a label without type in Watch / Immediate is
  read as a 64-bit number (`*(long long*)&label`).
* **No symbols at all** (stripped, FASM `format PE`): the program stops at its entry point and is debugged
  in the Disassembly window (address breakpoints, step instruction).
* gdb's DAP prints a Python traceback when a thread starts while the target runs (gdb 18 bug, harmless) and
  its banner / thread messages come on the program's stdout: the assembly sessions filter them.

### Entry points for the language plugins (contract)

* `nativedbg.asm_debug_session(win, exe, args=(), cwd=None, env=None, sources=None, nasm_args=None,
  breakpoints=None, stop_at_entry=None)` - a ready (not started) `AsmDapSession` that *launches* the program.
* `nativedbg.asm_console_session(win, plugin, spec, debug, breakpoints=None)` - for
  `AsmPluginBase.make_session(win, spec, debug)`: F5 on a **console** project (no forms) runs the spec's
  `--build` command, then launches `debug_info()["exe"]` under gdb. **Core: please add**
  ```python
  def make_session(self, win, spec, debug):
      from ..nativedbg import asm_console_session
      return asm_console_session(win, self, spec, debug)      # None = the IDE's usual session
  ```
  because the GUI Bridge console path (`runtimes/bridge.py`, `RAD_BRIDGE_DEBUG`) starts the program first and
  gdb attaches afterwards - a short console program has finished before the breakpoints are set.
* GUI Bridge (form) projects: `bridgedebug.engine_for()` now treats a plugin with `debug_info()` (or a
  `debug_engine` attribute) as engine `gdb`; `BridgeDebugSession` then attaches with
  `nativedbg.bridge_attach_dap()` - a plain `AttachDap` when `debug_info()["line_info"] == "dwarf"`, else an
  `AsmAttachDap` with the line table above.
* `radide.features.native_debug.start_session(win, session, title)` wires a session into the IDE like F5.

### Tests

`samples/Tests/Assembly/NativeDebug/test_native_debug.py` (37 checks, in the real IDE window, settings
"RADIDE-TEST"): NASM line table + breakpoint on an `.asm` line, Step Over Instruction, Registers (rax 0 -> 11,
red, eflags bits, edit rdx), Memory of the label `values` (1- and 8-byte columns), Disassembly (arrow, Intel
syntax, `.asm` lines interleaved, address breakpoint + continue), Stack, GNU as with DWARF, C (`arrays.c`:
Registers, C source in the disassembly, Memory of `&table`, Step Into Instruction), attaching to a running
NASM program (line table, slide), a stripped program (entry point, disassembly only) and F5 of a RAD IDE NASM
project through `asm_console_session` (core build with DWARF, F10, program output).

---

## 8086 emulator

The **8086 Assembly (Emulator)** project type (plugin id `emu8086`, `radide/languages/emu8086.py`) is for the
16-bit DOS assembly that university courses teach with emu8086 or DOSBox + MASM / TASM. Programs run in RAD
IDE's own emulator, written in pure Python for this project (`radide/emu8086/`); nothing is downloaded or
installed, and it works the same on every machine.

### Package `radide/emu8086/`

| Module | Contents |
|---|---|
| `assembler.py` | Multi-pass assembler for the MASM / TASM / emu8086 dialect -> `Program` (memory chunks, entry CS:IP, SS:SP, DS/ES, source map `addr_line` / `line_addrs`, `variables`, `labels`, `listing`, `errors` / `warnings`). No Qt. |
| `cpu.py` | The 8086 CPU: every 8086 instruction (flags, string instructions with REP/REPE/REPNE, MUL/DIV with divide errors, shifts/rotates, BCD adjust, far calls, interrupts), plus the 80186 extras courses meet (push imm, pusha/popa, shifts by an immediate, imul imm, enter/leave, ins/outs). Every memory write goes through `wb` so an undo log can be kept. |
| `machine.py` | The PC around the CPU: IVT with ROM stubs (`F1 nn CF` = Python service hook + IRET, so programs can still hook vectors), PSP, BIOS data area, DOS INT 20h / 21h, BIOS INT 10h / 16h / 1Ah / 15h AH=86h, text screen 80x25 at B800:0000, mode 13h at A000:0000, keyboard queue with scan codes, virtual clock, breakpoints, step / step over / step out, reverse step (history of register snapshots + memory undo), `run_source()`. No Qt. |
| `includes.py` | Built-in `emu8086.inc` (also `rad8086.inc`) used when the file is not in the project folder: an original library with the usual names - PUTC, PRINT, PRINTN, GOTOXY, CURSOROFF, CURSORON and DEFINE_PRINT_NUM / _UNS, DEFINE_SCAN_NUM, DEFINE_PRINT_STRING, DEFINE_GET_STRING, DEFINE_CLEAR_SCREEN, DEFINE_PTHIS. |
| `messages.py` | Every diagnostic has a code (`E-UNDEF`, `E-IMM-SREG`, `W-JCC-LONG`, `R-DIV0`, ...) and an English + Arabic text; Arabic text keeps the English one in brackets. |
| `detect.py` | `is_dos16_source(text)` / `dos16_score(text)`: is a file 16-bit DOS / course code (int 21h, org 100h, @data, .model small ...) rather than 32/64-bit NASM / MASM code. For Open Folder / foreign-project detection. |
| `ui.py` | Qt: `ScreenWidget` (80x25 CGA colours, cp437, blinking cursor, keyboard -> program; mode 13h), `RegistersPanel` (AX..DX with H/L halves, SI DI BP SP, CS DS ES SS, IP, flags as check boxes, editable while paused, changed values red), `MemoryView` (seg:off, register names, variable names), `StackView` (SP / BP marks, return addresses), `VariablesView` (data labels, arrays expand, byte arrays as text), `ListingView` (machine code per line), `Emu8086Panel` (the "8086 Emulator" dock), `Emu8086Session`, `evaluate_watch()`. |
| `__main__.py` | `python -m radide.emu8086 main.asm [--keys "text\n"] [--screen] [--listing] [--lang ar]` - headless run; exit code = the program's, 2 = assembly errors, 3 = stopped otherwise. |

### Dialect accepted by the assembler

`.model tiny/small/...`, `.stack [n]`, `.data`, `.data?`, `.code`, `.startup`, `.exit [n]`, `name segment [stack]`
/ `ends`, `assume`, `org`, `even`, `align`, `db dw dd dq` (and `byte word dword` aliases) with strings, `?`,
nested `n dup(...)`, `equ` / `=` (numeric; text equates such as `arg equ [bp+4]` or `equ <...>`), `label`,
`proc [near|far]` / `endp` (RET inside a far proc = RETF), `macro` / `endm` with parameters, defaults and `local`,
`rept`, `irp`, `include`, `struc` / `ends` (fields with defaults, nested structures, instances `p Point <1, 2>`
/ `<>` / `n dup (<...>)` - an empty value keeps the default, a shorter string for a byte array is padded with
zeros; `var.field`, `[bx].field`, `(Point ptr [bx]).field` are sized memory operands, `Point.field` is the
field's offset, `size` / `type` `Point` its size, `length` / `size` of an instance array), conditional assembly
(`if` / `ife` / `ifdef` / `ifndef` / `ifb` / `ifnb` / `ifidn` / `ifidni` / `ifdif` / `ifdifi` / `if1` / `if2`, the
matching `elseif...`, `else`, `endif`, nested, also inside macros - `IF` expressions see numeric equates defined
above them, `IFDEF` the names defined so far), `end [entry]`, emu8086 lines `#make_com#` / `#make_exe#` (others ignored), `name`,
`title`, `page`, `public`, `extrn` (ignored). Expressions: decimal, `0Ah`, `0x0A`, `1010b`, `17o`, `'A'`, `$`,
`+ - * / mod shl shr and or xor not`, comparisons, `offset`, `seg`, `type`, `length` (MASM: elements of the first
initializer), `size`, `lengthof`, `sizeof`, `low`, `high`, `byte/word/dword ptr`, `short`, `near ptr`, `far ptr`,
`@data`, `@code`, segment names as values, overrides (`es:[di]`, `cs:var`, `[es:di]`), all addressing modes
(`[bx+si+4]`, `var[si]`, `[bx][di]`, `var+2`). `size`, `length`, `type`, `low`, `high` may also be variable names.
Conditional jumps out of range become an opposite jump over a near JMP (warning `W-JCC-LONG`); LOOP / JCXZ
out of range is an error. 80186 instructions assemble with a warning (`W-186`). Not supported: RECORD / UNION,
32-bit registers, the FPU (ESC opcodes are decoded and ignored).

Layout (like DOS at segment 0700h): a COM program (`org 100h`, `.model tiny`, `#make_com#` or no segment
directive at all) is one segment with the PSP below 100h and SP = FFFEh (a final RET goes to INT 20h); an EXE
program has its PSP at 0700h, DS = ES = PSP at start (so `mov ax, @data / mov ds, ax` is needed, as in DOS) and
its segments paragraph-aligned from 0710h in DOSSEG order (code, data, stack) for the simplified directives,
source order for full segment definitions. No stack segment: a 4 KB stack is given (warning `W-NOSTACK`).

### Export to DOS: .COM and MZ .EXE (`radide/emu8086/dosexe.py`)

The dock's **Export...** button (Export .COM / .EXE by the program's kind, as .COM, as MZ .EXE) writes
`<source>.com` / `<source>.exe` next to the source; they run in DOSBox / FreeDOS / MS-DOS. `com_image(prog)` is
the segment's bytes from 100h (the program must start at 100h). `mz_image(text)` assembles the program twice
(load segments 0700h and 1700h): words that differ by exactly 1000h are segment fixups (`mov ax, @data`,
`seg x`, far calls / jumps, `dd far_label`); they are stored relative to the image and listed in the MZ
relocation table. Header: size in 512-byte pages, header paragraphs, `e_minalloc` for the `?` data / stack after
the image, `e_maxalloc` FFFFh, SS:SP and CS:IP relative to the image, `e_lfarlc` 1Ch. `load_dos_file(data)` loads
a .COM / .EXE back the way DOS does (PSP, fixups applied at any segment) into a Program the emulator runs - the
tests run every exported sample that way at other load segments and compare the output with the run from source.

### DOS / BIOS services

INT 21h: 01, 02, 06, 07, 08, 09, 0A (line editing with Backspace), 0B, 0C, 0E, 19, 25, 2A, 2C, 30, 35, 3F (handle
0), 40 (handles 1/2), 48/49/4A (minimal), 4C, 00, 31. INT 20h. INT 10h: 00 (modes 03h and 13h), 01, 02, 03, 05,
06, 07, 08, 09, 0A, 0C, 0D, 0E, 0F, 10 (AX=1003h blink), 13. INT 16h: 00/10, 01/11, 02/12. INT 1Ah: 00, 02, 04.
INT 15h AH=86h (wait; paced in real time in the IDE). INT 11h, 12h; INT 33h answers "no mouse". INT 08h fires
from the virtual clock only when the program hooked INT 08h / 1Ch. Ports 60h/64h (keyboard), 61h (speaker),
40h-42h, 3DAh. Unemulated services are reported once in the Output window. Divide errors stop the program
with an explanation at the faulting line. Time is virtual (1 instruction = 1 microsecond); `run_source()` uses
a fixed clock so tests are reproducible.

### In the IDE

* New Project > Assembly > 8086 Assembly (Emulator): templates COM Program, EXE Program, Using emu8086.inc,
  Text-Mode Colours, Keyboard Game (`asm86_com`, `asm86_exe`, `asm86_inc`, `asm86_colors`, `asm86_game`).
* F5 (`make_session` hook -> `Emu8086Session`): assembles the startup file; errors / warnings go to the Error
  List (Arabic when the UI is Arabic) and the Output window. The "8086 Emulator" dock opens paused at the first
  instruction (Debug > "8086: Stop at First Instruction", setting `emu8086/stop_at_entry`, default on).
  F10 / F11 / Shift+F11, Run to Cursor, editor breakpoints (added / removed while running), Locals (registers
  with H/L halves, FLAGS, every data label; arrays expand), Call Stack (current procedure + return addresses
  found on the stack), Watch / Immediate (`ax`, `zf`, `n`, `[bx]`, `word ptr es:[di]`, `[bp+4]`, `arr`).
  Dock buttons: Run, Pause, Step, Step Over, Step Back (reverse step through the history, 200000 steps, can be
  turned off), Reload; speed slider (1 step/s .. full speed; at <= 60 steps/s the current line moves in the
  editor); the screen takes the keyboard when the program waits for input (status bar says so).
* Ctrl+F5 runs at full speed without breakpoints; a runtime error then ends the run.
* Save / Project > Check for Errors: `radide/features/emu8086_ide.py` adds a `diag_providers` entry that
  assembles the startup file (unsaved editor text included).
* IntelliSense of the plugin: instructions, directives, registers, the emu8086.inc names, the program's labels /
  procedures / variables; hover text for instructions and registers (English, plus Arabic in an Arabic UI) and
  for INT 21h; Go to Definition and the outline from labels / procs / variables.

### For the other parts

* Tutorials / course: `from radide.emu8086 import run_source` -> `run_source(text, keys="5\r")` returns
  `{ok, errors, output, screen, exit_code, reason, machine, program}`; `output` is everything printed through
  DOS / BIOS teletype (CR LF kept), `screen` the final 80x25 text. Use it to check 16-bit course examples.
* Open Folder: `radide.emu8086.detect.is_dos16_source(text)` tells 16-bit DOS sources from NASM / MASM 32/64-bit
  ones; such a folder can be opened as an `emu8086` project (`project.radproj` with `"language": "emu8086"`,
  `"startup": "main"`, `"modules": ["main.asm", ...]`).
* `.asm` files keep opening with `asm-nasm` by default (`PREFERRED_FOR_EXT`); inside an `emu8086` project the
  project language wins (`plugin_for_file(name, default_id)`).

### Samples and tests

Samples (original, each with a README and `project.radproj`): `samples/Tests/Assembly/Emu8086Hello`,
`Emu8086SumArray`, `Emu8086StringReverse` (full segments, INT 21h 0Ah), `Emu8086InputNumber` (macros, binary
output), `Emu8086Factorial` (recursion, `[bp+4]`), `Emu8086BubbleSort`, `Emu8086Colors` (INT 10h + B800h),
`Emu8086KeyGame` (INT 16h arrow keys), `Emu8086Structs` (STRUC array, `[si].field`, `size student`, `IF` /
`IFDEF` / `IFB` - and the program to export as an EXE for DOSBox).

Tests in `samples/Tests/Assembly/Emu8086Tests/`:

* `test_cpu.py` - 64 instruction cases (results and every flag: add/adc/sub/sbb/cmp/inc/dec/neg, logic, mul/imul,
  div/idiv, shifts and rotates, BCD, cbw/cwd, xchg, stack, lahf/sahf, lea, loops, signed / unsigned jumps,
  call/ret, xlat, 80186 extras), string instructions with REP prefixes, divide errors, memory / video writes,
  far call + a program-installed interrupt vector, reverse step (memory undo), keyboard services, input wait.
* `test_assembler.py` - 58 encodings checked byte by byte, jump sizing, long conditional jumps, LOOP range
  error, COM / EXE layout and source map, data definitions, macros with local labels, text equates and
  operators, the built-in emu8086.inc, error codes and lines, Arabic messages.
* `test_samples.py` - every sample headless: program output and screen text; colour attributes of Emu8086Colors;
  KeyGame played with arrow keys until two stars are caught.
* `test_struc_cond_export.py` - 12 tests: structure fields / instances / every reference form / nested
  structures, all conditional directives (also in macros) and their errors, COM bytes, MZ header and relocation
  table checks, every sample exported and run again from the file at two other load segments, a program with
  far calls / far pointers / `seg`, `export_file`, the dock's Export button.
* `test_ide.py` - the real IDE (offscreen, QSettings "RADIDE-TEST"): templates, F5 paused at entry, F10, a
  breakpoint, Locals / Call Stack / registers panel, Step Back, Step Out, Variables / Memory views, Watch, output
  in the Output window and on the emulator screen, keys typed on the screen, slow motion + Pause + Stop, an
  assembly error in the Error List (Arabic) and Check for Errors; screenshots with `widget.grab()`.

---

## Editor intelligence: highlighting, IntelliSense, hover, outline, LSP

Code: `radide/asm_intel/` (no Qt) and `radide/features/asm_ide.py` (the IDE side). Works for NASM, MASM, FASM
and GNU as (AT&T and Intel syntax), in assembly projects and for assembly files opened anywhere else.

### Modules

| Module | Contents |
|---|---|
| `isa.py` | ~875 x86 / x86-64 instructions: general purpose, x87, MMX, SSE..SSE4.2, AES/CLMUL, AVX (VEX forms), AVX2, FMA3, BMI1/2, all Jcc / SETcc / CMOVcc; registers (8 to 512 bit, ABI roles). Short original descriptions, operand forms, flags read / written / undefined, link to the Intel SDM. AT&T suffix forms (`movq`, `addl`, `movzbl`) |
| `directives.py` | directives / pseudo-instructions / macro keywords of each assembler, with a link to its manual |
| `apis.py` | ~230 Win32 API (kernel32, user32, gdi32, shell32; `A` + derived `W` + plain names) and C runtime signatures; argument locations per ABI (`arg_locations`: Win64 `rcx rdx r8 r9` / `xmm0-3` / `[rsp+20h]`..., System V, 32-bit pushes) and the calling-convention text (`convention`: Win64 shadow space, stdcall `ret n` + `_Name@n`, cdecl caller clean-up, variadic rules) |
| `index.py` | dialect detection, ABI detection, comment / string masking, the parser (`parse` -> `Module` of `Sym`: label, local, proc, macro, const, data, struct, field, section, extern, var, param; includes, externs, globals) and the project index (`parse_file` cached by mtime, `project_files`, `resolve_include`) |
| `engine.py` | `completions`, `calltip`, `hover`, `definition`, `references`, `document_symbols`, `folding_ranges` |
| `snippets.py` | snippets per dialect and ABI: procedure prologue / epilogue, counted loop, if (CMP + Jcc), while, Win64 call with shadow space, MessageBox, ExitProcess, WriteConsole, Linux `syscall` write / exit, DOS `.COM` skeleton, MASM `.if` / `.while` / `PROC FRAME`, FASM PE / ELF skeletons ... |
| `monarch.py` | the Monaco (Monarch) grammar, language configuration (comments, word pattern) and folding rules per dialect |
| `plugin.py` | `AsmIntelMixin`, `AsmPluginOverlay`, `overlay_for` |
| `lsp.py` | optional asm-lsp server |

### Dialect and ABI detection (`index.detect_dialect`, `index.abi_of`)

1. a dialect-specific extension: `.nasm`, `.fasm`, `.masm`, `.s` / `.S` (GNU as);
2. inside a project: `project.radproj` `"asm": {"assembler": ...}` (also `asm_dialect`, `assembler`, `language`
   containing nasm / fasm / masm / gas), then the plugin's `asm_dialect`;
3. a loose file: the text (`sniff`: `section .text` / `%define` -> NASM, `.model` / `PROC` / `invoke` -> MASM,
   `format PE` / `section '...'` -> FASM, `.globl` / `%rax` -> GAS), then the plugin's dialect, then NASM.

GNU as syntax: AT&T unless the file switches to `.intel_syntax`. The ABI (`win64`, `sysv`, `x86`, `dos16`) comes
from the project's `"asm": {"arch": "x86" | "x64"}`, else from the text (`bits` / `use64` / `format PE64` /
`.model flat` / 64-bit registers; Linux when `format ELF`, `int 80h`, `_start` + `syscall`, `@function`).

### What the editor does

* **Highlighting**: instructions, registers (`%rax` in AT&T), directives, preprocessor (`%define`, `#include`),
  label definitions, numbers in every notation (`0x1F`, `1Fh`, `$1F`, `1011b`, `17q`), strings (NASM back-quotes),
  comments (`;`, `#`, `//`, `/* */`). The word pattern keeps `.loop`, `%define`, `%rax` as one word.
* **Completions**: at the start of a statement - instructions (filtered by 16 / 32 / 64-bit mode), directives,
  the project's macros and snippets; after `call` / `jmp` / `Jcc` / `loop` / `invoke` - procedures, labels, local
  labels of the current procedure, externs and Win32 / CRT functions (NASM: choosing a function that is not
  declared adds `extern Name` after the last `extern` line); operands - registers, size keywords (`dword`, MASM
  `dword ptr`, `offset`, `addr`), data, constants, structures, MASM `LOCAL`s / parameters of the current
  `PROC`; `STRUC.` / `var.` - structure fields; `%include "` - project include files. Items are pre-filtered by
  the first letter typed, and the program's own names, macros and snippets come first.
* **Signature help** (`(`, `,` or Ctrl+Shift+Space): `invoke` / `stdcall` / `ccall` / `cinvoke` / `fastcall`
  arguments (Win32 API, CRT, MASM `PROC` / `PROTO`, FASM `proc` parameters); macro parameters; the **register
  set-up before a call** - on `mov r8, ...` / `lea rdx, ...` the next `call Func` is found and the parameter
  that lives in that register is highlighted (Win64 `rcx rdx r8 r9` / `xmm0-3`, System V `rdi rsi rdx rcx r8
  r9`); on `push ...` before a 32-bit call the parameter is counted from the call (right-to-left order); and the
  operand forms of the current instruction (AT&T order reversed).
* **Hover**: instruction (category, description, operand forms, flags, 64-bit availability, Intel SDM link);
  register (size, role in the ABIs, parts); directive (dialect manual link); Win32 / CRT function (C signature,
  table of parameters with the register / stack slot each one uses for the file's ABI, calling convention, DLL /
  import library, Microsoft Learn link); the program's own labels / procedures / macros / constants / data
  (definition line, comment above it, file and line); numbers (decimal, hex, binary, signed dword, character).
* **Go to Definition** (F12, Ctrl+click in the same file): local labels resolve against the enclosing label
  (`.loop` -> `main.loop`), MASM `LOCAL`s / parameters against the `PROC`; other files of the project and the
  files they `%include` / `include` / `.include` (folders: the file's, the project root, `include/`, `inc/`, the
  `INCLUDE` environment variable, `%LOCALAPPDATA%\RADIDE\tools\fasm\INCLUDE` ...). F12 on an include line opens
  the file.
* **Find All References** (Shift+F12): comments and strings skipped; NASM / FASM local labels only inside their
  parent label (plus `parent.local` anywhere); MASM locals only inside their `PROC`; case-insensitive for MASM.
* **Outline**: the Document Outline dock (via the plugin's `document_symbols`: sections > procedures / labels >
  local labels / locals, plus data, constants, macros, structures with fields) and Monaco's breadcrumbs /
  Ctrl+Shift+O (document-symbol provider answered by the `radAsm` channel object).
* **Folding**: `%macro` / `%if` / `%rep` / `struc`, MASM `PROC` / `MACRO` / `STRUCT` / `SEGMENT` / `.IF` /
  `.WHILE` / `.REPEAT`, FASM `{ }` / `proc` / `struct` / `if` / `repeat` / `virtual`, GAS `.macro` / `.rept` / `.if`
  / `.cfi_startproc`, every section, every global label's body and runs of 3+ comment lines.
* The status bar shows the dialect and ABI when an assembly file opens ("Assembly: NASM - Windows x64").

### Hooks (contract for the language plugins and the editor)

* Assembly language plugins put **`AsmIntelMixin` first** in their bases and set `asm_dialect`
  (`class AsmPluginBase(AsmIntelMixin, BridgeLanguagePlugin)`, done in `radide/languages/asm_base.py`). The
  mixin implements `completions`, `calltip` (returns a dict `{label, documentation, parameters,
  activeParameter}`), `hover`, `definition`, `references`, `document_symbols`, `folding_ranges` and
  `monaco_language(path)`, and marks the plugin with `asm_intel = True`.
* Any other plugin editing an assembly file (a `.s` in a C or Rust project, a loose file opened with File > Open)
  is wrapped for that one editor by `AsmPluginOverlay` (`.inc` only when assembly sources sit next to it or the
  text looks like assembly - otherwise it stays PHP / Pascal). Everything except the IntelliSense hooks and the
  comment settings delegates to the wrapped plugin.
* New generic Monaco hooks (`radide/monaco_editor.py`, `radide/web/editor.html`), usable by other languages:
  * `MonacoEditor.plugin_overlays: list[fn(plugin, path) -> plugin | None]` - the first non-None result becomes
    the editor's plugin;
  * `plugin.monaco_language(path) -> {"id", "aliases", "monarch", "conf", "folding", "triggers"} | None` - a full
    Monarch grammar (regexes as strings), language configuration (a string `wordPattern` is turned into a
    RegExp), folding rules (`pairs` of start / end regexes, `section`, `label`, `lineComment`) and completion
    trigger characters, registered by `radRegisterMonarch(spec)`; the editor's language id is then `spec["id"]`
    (`rad-asm-nasm`, `rad-asm-masm`, `rad-asm-fasm`, `rad-asm-gas`);
  * completion items may carry `doc`, `insert`, `snippet`, `sort` and `edits` attributes (passed to Monaco as
    documentation, insertText, snippet rules, sortText and additionalTextEdits); kind `"snippet"` exists;
  * `plugin.calltip()` may return a dict (shown with parameter highlighting) instead of a string.

### asm-lsp (optional)

[asm-lsp](https://github.com/bergercookie/asm-lsp) is used when found in
`%LOCALAPPDATA%\RADIDE\tools\asm-lsp\bin`, `~/.cargo/bin` or on PATH. Tools > Language Servers... > asm-lsp >
Install (only on request) takes the pinned GitHub release (`RELEASE` = 0.10.1 in `radide/asm_intel/lsp.py`):
on Linux x86-64 / macOS the release's prebuilt archive is downloaded from
`github.com/bergercookie/asm-lsp/releases/download/v0.10.1/` and must match the SHA-256 digest GitHub
publishes for it (pinned in `ASSETS`); the releases have **no Windows binary** (checked for v0.9.0 - v0.10.1),
so on Windows the same release tag is built from the official repository:
`cargo install --git https://github.com/bergercookie/asm-lsp --tag v0.10.1 --locked --root <tools>\asm-lsp`
(needs Rust). `samples/Tests/Assembly/AsmLsp/test_asm_lsp.py` checks the plan, the release metadata, a real
download + verification + unpack of the Linux archive, the LSP client with the server (the real asm-lsp when
installed, else a stand-in server with the same protocol) and the fallback. `radide/lsp.py` maps the four `rad-asm-*` ids to one server per project (`SERVER_GROUP`
"rad-asm", languageId `asm`). While it is attached its hover and completions are used and the built-in items are
merged into its completion list (`MonacoEditor.completion_providers`); without it (the normal case) the built-in
provider answers everything. QSettings `asm/useAsmLsp = false` turns the server off.

### Tests (`samples/Tests/Assembly/AsmIntel`)

* `tests/test_asm_intel.py` - 10 unit tests (tables, dialect / ABI detection incl. project settings, parser of
  the four dialects, completions per context, hover, signature help, definition / references, outline, folding,
  Monaco specs JSON-safe, overlay).
* `tests/test_core_templates.py` - runs every service on every line of each Assembly New Project template
  (radide/asm/templates.py): right dialect and ABI, non-empty outline, no exception.
* `tests/test_ide_asm.py` - 24 checks in the real IDE (offscreen, QSettings "RADIDE-TEST", cleared): File > Open
  of a NASM file, the Monarch grammar and rendered colours, completions (instructions, macros, snippets, APIs
  with the automatic `extern`), hover, signature help, `radAsm` symbols and Ctrl+click, the Document Outline dock,
  the MASM / FASM / GAS grammars, and the overlay on a `.S` file opened with the Python plugin.

---

## Samples and course: Open Folder, foreign projects, file associations, exe listing, Arabic course

### Open Folder (`radide/project_detect.py` `_asm`, `radide/foreign/asm_folder.py`)

* A folder with `.asm` / `.s` / `.nasm` / `.fasm` / `.masm` sources (two levels; `.inc` / `.mac` are include
  files) becomes one candidate of kind `asm`. `asm_folder.guess_dialect(text, filename)` scores each source:
  `nasm` (`section .text`, `global`, `extern`, `bits 64`, `%include`, `resb`), `masm` (`.model`, `.code`,
  `main PROC` / `ENDP`, `END main`, `includelib`, `invoke`), `fasm` (`format PE64`, `section '.text' code`,
  `entry`), `gas` (`.globl`, AT&T `%reg`, `.intel_syntax`, `.s`), `8086` (the emulator's own
  `radide.emu8086.detect.is_dos16_source`, else `org 100h` / `int 21h` / `.model small` without 64-bit registers).
  `guess_bits()` and `entry_point()` (main / start / _start / WinMain / `END label` / FASM `entry` / SASM `CMAIN`)
  complete the picture; `scan_folder()` returns the programs (sources with an entry point).
* The candidate opens **in place** by default (`inplace="loose"` -> `loose_sources.open_loose(win, folder,
  "asm")` -> `asm_folder.open_asm`), confidence 0.85 (0.9 with a RadASM / WinAsm file); it drops to 0.5 when the
  folder is also something else (a C / Rust / CMake project with a `.s` helper). "Create" writes a
  `project.radproj` for the dialect's plugin (`asm-nasm` / `asm-masm` / `asm-fasm` / `asm-gas` with an `"asm"`
  entry: assembler, arch from the bits, entry; `emu8086` for 8086 folders).
* `AsmFolderAdapter` (a `ForeignAdapter`): one run target per program (`hello.asm  [NASM 64-bit]`), modules =
  sources + includes, editor language = the dialect's plugin. Builds go to the IDE state folder (never the user's
  folder): NASM `nasm -f win64|win32 [-g -F cv8] -I<dir>` + `gcc` (entry other than main: `-nostartfiles
  -Wl,-e,<entry>`); 32-bit NASM / GNU as programs are linked with `ld -m i386pe` against the SysWOW64 DLLs like
  the x86 templates (`_ld32_step`, never `gcc -m32`: the MinGW-w64 toolchain has no 32-bit libraries), GNU as `gcc src.s`, FASM `fasm src out.exe` (INCLUDE = FASM's include folder), MASM a small
  batch file in the state folder: `call vcvars64.bat` + `ml64 /Zi ... /link` (C runtime start-up for main /
  WinMain, else `/entry:`), run from the state folder (ml writes `mllink$.lnk` into the current folder). F5 = gdb
  (`_others_base.gdb_session`) for NASM / GNU as programs. Native menu: "Disassemble <file> (objdump -d -M intel)".
  Tools: `radide/asm/toolchain.py` `find()` / `find_masm()` first, then `RADIDE_<TOOL>`, PATH and the IDE folders.
* 8086 targets (kind `emu`): `open_asm` hooks the per-project plugin's `make_session` so Run / Debug start
  `radide.emu8086.ui.Emu8086Session(win, folder, file, debug, breakpoints)` - the same session as an `emu8086`
  project.
* SASM programs (`%include "io64.inc"` + `CMAIN:`) are NASM; SASM's include folder
  (`Program Files (x86)\SASM\include`) is added with `-I` when SASM is installed.

### Other IDEs' projects (`register()` in asm_folder.py)

* RadASM `.rap` (format `radasm`) and WinAsm Studio `.wap` (format `winasm`): INI files read with
  `read_ide_project()` -> file list, main file (same name as the project, else the first source), assembler
  (`[Project] Assembler=`; WinAsm = MASM) and the other IDE's make commands (shown in the log, not run: they use
  that IDE's variables). Folder probe: a `.rap` / `.wap` next to the sources; File > Open accepts them too.
* Visual Studio `.vcxproj` with the masm build customization: `msbuild.py` lists `<MASM Include=...>` items
  (`ITEM_KINDS` has `MASM`), Open Folder titles it "C++ / MASM ...". With MSBuild + VC tools masm.targets builds
  them; the MinGW g++ fallback (`vs_ui._masm_steps`) assembles them with ml64 when Visual Studio's ml64 exists,
  else says why they were skipped.

### File associations and the exe importer

* `radide/shell_integration.py` `OPEN_WITH_BASE`: `.asm .inc .s .nasm .mac .rap .wap` ("Open with RAD IDE").
* `radide/importers/exe/asm_listing.py`: `nasm_listing(exe, analysis)` turns the capstone analysis of
  `importers/exe/native.py` into a NASM-syntax listing (functions as labels, local jump targets `.L<addr>`,
  `extern` imports, `call [rel MessageBoxA]`, strings in `.data`, the address and bytes of every instruction as a
  comment). The native importer adds it as `_original/recovered/<Program>_disasm.asm`; `export_project(exe,
  dest)` / `python -m radide.importers.exe.asm_listing Program.exe OutFolder` writes a folder that Open Folder
  opens as an Assembly folder. For study: it re-assembles with NASM (object file) but data tables and code the
  analysis did not reach are not reconstructed.

### Arabic course (`radide/tutorials/assembly`, `radide/tutorials/asm_support.py`)

16 lessons (course id `assembly`, CHM `docs/chm/RADIDE_ASSEMBLY_ar.chm`): what assembly is and the first NASM
program, number systems, registers and memory, data and sections, arithmetic and logic, flags and jumps, loops,
arrays and addressing, the stack / procedures / Windows x64 calling convention, strings, the C runtime and Win32
API, a GUI Bridge form, the 8086 emulator, debugging with the Registers / Disassembly / Memory windows, a final
two-file project, glossary.

* Blocks: `asm run` (NASM x64 console: `nasm -f win64` + gcc, stdin from `text input`), `asm form run`
  (Form1.asm with `handler ... endhandler`; "جرّبه" = `asm-nasm` template `nasm_forms` with the controls the code
  names), `asm16 run` (8086 programs checked with `radide.emu8086.run_source`; "جرّبه" = an `emu8086` project),
  `exercise` / `solution`, `; #file: name.asm` for several files, `<!-- test: {"norun": true} -->` (MessageBox).
  Wiring in `radide/tutorials/__init__.py` (`ASML`), `html.py` (Pygments `nasm` lexer) and
  `features/tutorials.py` (stdin for console blocks).
* Checks: `python radide/tutorials/assembly/tools/check_lessons.py` (all 172 blocks: run, solutions, exercises
  assemble, 8086 blocks in the emulator, quiz JSON, every "جرّبه" project) and
  `samples/Tests/Assembly/CourseTests/test_course_forms.py` (the lesson-12 forms built with
  `python -m radide.asm.build` and driven over the bridge protocol).

### Samples and tests

`samples/Tests/Assembly/README.md` is the index of every assembly sample. This part added `OpenFolder/` (NASM,
MASM, FASM, GNU as, 8086, SASM, RadASM, WinAsm and Visual Studio + MASM folders; `test_open_folder.py` headless:
43 checks incl. real builds of the NASM / GNU as / FASM / MASM folders and the exe -> NASM listing;
`test_ide_open.py`: open in place, Ctrl+F5, RadASM, 8086 session, course in the IDE), `CourseNumberAnalyzer`,
`CourseFormCalculator` and `CourseTests/`.

## QA (end-to-end pass)

`samples/Tests/Assembly/QA/test_user_flow.py` drives the IDE the way a user does (see its README). Fixes made in
that pass:

* **stdin under F5.** gdb on Windows gives the debuggee end-of-file on stdin, so a console program that reads
  input (the templates' `scanf`) could not be debugged. `AsmDapSession(stdin_pipe=True)` now listens on a named
  pipe (`QLocalServer`) and launches the program with `<\\.\pipe\radide-stdin-...`: the launch `args` are
  sent as **one string**, so gdb's own redirection handles `<` (a list would be quoted). `send(text)` /
  `end_input()` feed the pipe; `asm_console_session` turns it on unless the project's console is `external`,
  and the Program Input bar is now shown under F5 too ("End of input" closes the pipe, never gdb's stdin).
* **F5 on a loose folder (Open Folder).** `AsmFolderAdapter.debug_session` ignored the build steps (F5 debugged
  a stale or missing exe) and used plain gdb on a NASM build whose only debug info is CodeView. It now returns
  `ChainSession(pre, factory)`: build first, then `nativedbg.asm_debug_session` (the listing-based line table,
  with the folder's `-I` options and the stdin pipe) for NASM and plain gdb (DWARF from `gcc -g`) for GNU as.
* **Program Input bar** also for loose-folder console programs (Ctrl+F5 and F5), docked as a full-width row
  under the Output tabs instead of a narrow column beside them.
* Arabic: the Help > Help Files (CHM) entry of every course (`"{} (Arabic, CHM)"`) and the Assembly course title.

## CPU view (OllyDbg style) and the live assembly editor

**Debug > Windows > CPU (OllyDbg Style)** (Alt+C) is one dock with four synchronised panes. It works for every gdb
session (assembly, C, C++, Rust, Fortran: `radide/nativedbg.py`) and for RAD IDE's 8086 emulator
(`radide/emu8086`). It comes up by itself at the first stop of a native assembly program (Debug > "CPU View at
First Stop" turns that off); for the emulator it is one click away (the emulator has its own dock).

| Pane | What it shows / does |
|---|---|
| Disassembly | arrows column (every jmp / jcc / loop inside the listing; the arrow of the current conditional jump is red when it will be taken, grey and dashed when not), address + label, bytes, instruction (targets by name), comment (the user's comment, else the source line `main.asm:25  add rax, [rbx]`, else the referenced string). Current instruction highlighted, breakpoints in red. Info line under it: "Jump is taken / NOT taken" with the reason (`JNE: not equal / not zero (ZF=0). Now ZF=1.`; bilingual tooltip), the destination and the address of the memory operand. |
| Registers | General page (changed values red, a comment such as `<.next>` / `<msg>`), the flag bits as buttons (click toggles the flag in the program; tooltip explains each flag in English and Arabic), FPU and SSE pages (read only while shown). Double-click / context menu: Modify, Increment, Decrement, Zero, Follow in Dump / Disassembler / Stack. |
| Dump | 16 rows of hex + ASCII from any address; double-click a byte to edit it; changed bytes red; PgUp / PgDn; Ctrl+G; Edit Bytes. |
| Stack | from the stack pointer (SP row marked, BP marked), with `Return to show (main.asm:31)` for return addresses (the bytes before the value decode as a CALL) and `ASCII "..."` / `UNICODE "..."` for pointers to strings. Double-click follows the value in the dump. |

Keys while the CPU view has the focus (they do not steal the IDE's keys elsewhere): **F2** breakpoint, **F4** run
to cursor, **F7** step into, **F8** step over, **Ctrl+F9** execute till return (8086: stops *on* the RET like
OllyDbg; native: gdb's finish, back in the caller), **F9** run, **Ctrl+G** go to address / expression (number,
label, register, `rsp+8`, `[rbp-8]`, `CS:IP` for 8086), **Space** assemble (NASM syntax for native programs,
gdb's `QWORD PTR` / `[rip+0x..]` forms accepted; the 8086 assembler for the emulator; shorter code is padded with
NOPs, longer code asks first), **Ctrl+E** binary edit, **;** comment, **:** label, **Enter** follow, **-** back,
**\*** current instruction. Context menu: Follow, Follow in Dump, Search for > Command / Constant / All
Referenced Strings, Go to Source Line.

Comments and labels are kept per project in `<project>/.radide/cpu_notes.json` (next to the program without a
project), keyed by the program name and the *static* address (run-time address minus the ASLR slide of
`AsmDapSession`), so they survive the next debugging session.

**The assembly editor** (every Monaco editor of an assembly file, any dialect):

* jump arrows in the gutter for jmp / jcc / loop / call whose target label is in the same file (also while not
  debugging; NASM local labels resolve to their parent);
* caret on a register: every read (blue) and write (orange) of that register (al / ax / eax / rax are one
  register) in the same procedure is marked, also in the overview ruler; `xor eax, eax` counts as a write;
* while debugging: inline values after each executed line (`; rax=0x3  rbx=0x7FF7...  CF=0 ZF=0 ...` - the
  registers of the line and the flags the instruction writes / tests), the current-line arrow, the arrow of the
  current conditional jump coloured taken / not taken, and a hover on any register with its live value (hex,
  unsigned, signed, characters, and "changed by the last step (was ...)").

Modules: `radide/asm_intel/cpuview/` - `analysis.py` (pure: source jumps, register reads / writes, procedure ranges,
inline values, jcc evaluation, capstone decoding with re-synchronisation, effective addresses, return-address and
string detection, one-line assemblers), `backend.py` (`NativeBackend` over the nativedbg helpers - gdb's
disassemble decides the boundaries and symbols, capstone analyses each instruction; `EmuBackend` over
`Emu8086Session` / `Machine`), `notes.py`, `texts.py` (English / Arabic), `panes.py` (the Qt view),
`editor_live.py` (the script injected into the Monaco page + `LiveSession`); IDE glue:
`radide/features/asm_cpu_view.py` (dock, menu, stop / resume / finish hooks, editor ready hook). Nothing in
nativedbg.py, native_debug.py or radide/emu8086 was changed.

Tests: `samples/Tests/Assembly/SmartCpuView/test_cpu_analysis.py` (40 pure checks) and `test_cpu_view.py` (55 checks
in the IDE: NasmLoop under gdb and Emu8086Loop under the emulator, Arabic + dark screenshots; `QA_REAL=1` also
captures the editor with its arrows and inline values).

## Smart checks: Check by running, Explain this line, What-if (`radide/asm_sim`)

Code: `radide/asm_sim/` (no Qt) and `radide/features/asm_smart_sim.py` (the IDE side). The program runs in a
sandbox - only its own sections, a 1 MB stack, a 4 MB heap and stub slots exist; nothing touches the real system -
and every runtime mistake becomes a finding with a rule id `sim.*`, the line, and English + Arabic texts: a short
message, **what happened** (inside the CPU, for a beginner), **how to fix** (a concrete change) and a reference
(the asm_intel instruction entry / Intel SDM, or a topic page: Windows x64 convention, NASM sections ...).

### Engines

| Source | Engine |
|---|---|
| NASM, Windows x64 / x86, Linux x86-64 / i386 | NASM writes an object file (`-f win64 / win32 / elf64 / elf32`) with a listing; `objload.py` reads the COFF / ELF sections, symbols (also local labels) and relocations, links it in memory (other project modules that define a `global` the file declares `extern` are linked too, `__imp_` symbols get pointer slots) and maps addresses to lines and data labels (with sizes). `x86run.py` runs it in **Unicorn** (pip `unicorn`, official PyPI; `capstone` decodes) |
| 16-bit DOS (`abi_of` = dos16 / `emu8086.detect`) | RAD IDE's 8086 emulator (`radide/emu8086`), stepped by `emu16.py` with the same rule ids |
| MASM / FASM / GNU as | `status = "unsupported"` with a bilingual note (use F5 and the CPU view) |

Without `unicorn` the 32 / 64-bit checks answer `status = "unavailable"`; the window shows **Install Unicorn**
(`check.install_unicorn()`: `pip install unicorn capstone` from https://pypi.org/simple into the IDE's Python).
Library calls are imitated by `stubs.py` (printf / puts / scanf / gets / fgets / getchar / sprintf, string and
memory functions, malloc / calloc / free, rand / time, exit, ExitProcess, GetStdHandle / WriteConsoleA /
ReadConsoleA / WriteFile / ReadFile, MessageBoxA / W (logged, returns IDOK), GetComputerNameA, Sleep,
GetTickCount ...; Linux `syscall` / `int 80h` write / read / exit). Pointer arguments are checked; output is
collected; input comes from the window's Input box; every call is logged with its line; unknown functions
return 0 (`sim.unknown_extern`, info). 32-bit stdcall stubs end with `ret n` (`_Name@n` or the Win32 table).
Limits: 500 000 instructions / 12 s from the IDE (8086: 300 000).

### Rules

| Rule | Detected when |
|---|---|
| `sim.stack_imbalance` | at `ret` the stack pointer is not where it was right after the `call` (pushes / pops counted, cdecl caller without `add esp, n`) |
| `sim.bad_return` | the stack pointer is right but the return address there was overwritten (line of the last write) |
| `sim.callee_saved` | at `ret` a register the ABI gives to the caller changed (Win64 RBX RBP RDI RSI R12-R15, System V RBX RBP R12-R15, 32-bit EBX ESI EDI EBP; `main` included) |
| `sim.misaligned_call` / `sim.no_shadow_space` | 64-bit call of a library function with RSP not 16-aligned / (Win64) the 32-byte home area overlapping the caller's return address |
| `sim.null_deref` / `sim.mem_violation` | access below 64 KB / to unmapped memory, with the faulting instruction and the registers inside `[ ]` |
| `sim.write_readonly` / `sim.exec_data` / `sim.ran_off_end` / `sim.bad_jump` / `sim.bad_opcode` | write to `.text` / `.rdata`, running into data, past the last instruction, to nowhere, invalid bytes |
| `sim.stack_overflow` | the stack grew past 1 MB (recursion without a base case) |
| `sim.div_zero` / `sim.div_overflow` | `#DE`, explained with the divisor and EDX:EAX (missing `xor edx, edx` / `cdq`) |
| `sim.buffer_overflow` | a write outside the data label the instruction points into: from its relocation, or from the register loaded with `lea` / `mov reg, label` (copied by `mov`, kept by `add` / `inc` ...); names the variable that gets damaged |
| `sim.uninit_read` | a stack byte below the entry stack pointer read before anything was written there (`[rbp-8]`) |
| `sim.infinite_loop` | the step limit: the hottest backward jump, its condition and whether the compared registers changed |
| `sim.bad_pointer_arg` | a library function got an invalid pointer (`mov rcx, [msg]` instead of `lea rcx, [msg]`) |
| `sim.waiting_input` / `sim.unknown_extern` | info only |

### API

```python
from radide.asm_sim.check import check, explain_line, prepare
res = check(text, path, stdin="5\n")                  # whole program (main / _main / start / project entry)
res = check(text, path, proc_line=42, init_regs={"rcx": 3})   # the procedure that contains line 42
res = check(text, path, lines=(10, 20))               # only the selected lines
res.findings[i].to_dict(lang) / .issue_dict(lang) / .markdown(lang)   # rule, line, severity, texts, ref
info = explain_line(text, path, 37, iteration=-1)     # re-runs and records line 37 (all its executions)
from radide.asm_sim.explain import explain_step, condition_text, flag_table
explain_step("add eax, ebx", before_regs, after_regs, writes, reads, next_ins="jle done")   # also for debugger state
from radide.asm_sim.whatif import whatif
whatif("add eax, ebx\njc over\nover:", "eax=0xFFFFFFFF ebx=1 CF=0 [0x2000]=1,2", bits=32)
```

`explain_step` gives `what_en / what_ar` (the instruction in words with its operands), `changes` (registers and
memory before -> after, hex + decimal + signed), `flags` (every flag the instruction sets with its reason: "CF=1
because 5 < 7 as unsigned numbers: borrow") and `jump` (taken / not taken, in terms of the compared values:
"'jle .done' will NOT be taken ... 12 <= 10 is false"). The CPU view (or anything that has a debugger state) can
call it with the registers before / after a step.

**Diagnostics contract with the analyzer (radide/asm_lint).** `Finding.issue_dict(lang)` has the shape of
`asm_lint.model.Issue.to_dict` (0-based `line`, `col`, `endLine`, `endCol`, `severity`, `message`, `message_en/ar`,
`why`, `fix`, `markdown`, `url`, `mnem`, `source = "sim"`, `fixes = []`). After a run the IDE calls
`radide.asm_lint.publish_external(editor, "sim", issues)` when the analyzer defines it (it should merge them with
its own issues and show them in its hover / Problems UI); until then the findings are set as Monaco markers
with the owner `rad-asm-sim` (never replacing the analyzer's `rad` markers), plus Error List rows `sim.*` (kept by
a `win.diag_providers` entry while the checked text is unchanged).

### In the IDE (`radide/features/asm_smart_sim.py`)

* **Debug > Assembly Checks**: Check by Running (**Ctrl+Shift+F5**), Check This Procedure, Check Selection,
  Explain This Line (**Ctrl+Shift+F1**), What-If Console, Assembly Checks Window; the first three and Explain are
  also in the assembly editor's context menu. Shortcuts are only set when no other action uses them.
* The **Assembly Checks** dock: Input (program input, `\n` between lines) and Registers (start values of a
  procedure check: `rcx=10 rdx=3`); tabs **Findings** (severity / line / problem; the details pane shows the UI
  language first and the other language below, with the reference link; double-click goes to the line), **Program
  Output** (what the program printed + the call log), **Explain** (execution # of the line: 0 = the last one; the
  explanation in both languages + the flags table), **What-If** (16 / 32 / 64-bit, start values for registers /
  flags / memory, each step explained, a CF ZF SF OF PF AF DF table with their meanings). Runs happen in a worker
  thread; links open only when `RADIDE_NO_BROWSER` is not set.

### Tests (`samples/Tests/Assembly/SmartSim`)

* `buggy/*.asm` - 16 programs with one mistake each (`; EXPECT: sim.rule` on the line where it must be reported):
  stack imbalance, cdecl without clean-up, null pointer, value instead of address, divide by zero / overflow,
  buffer overflow, endless loop, misaligned call without shadow space, uninitialised local, callee-saved register,
  no `ret`, and four 8086 programs. `correct/*.asm` - four clean programs (Win64 procedures, 32-bit cdecl,
  Linux syscalls, 8086 procedure).
* `tests/test_sim.py` - headless, 82 checks: every expectation at the right line, complete bilingual texts, no
  findings for the correct programs and the IDE's own samples, procedure / selection / module-without-main /
  unsupported dialect, explain_line (x64 iterations, the jump prediction, 8086), 14 What-if explanations.
* `tests/test_ide_sim.py` - the real IDE (qh.py, QSettings "RADIDE-TEST"): menu + shortcuts, Check by Running from
  the menu action, Findings / details / Monaco markers (owner `rad-asm-sim`) / Error List / diag provider, Explain
  This Line (execution 2 of 10), What-If + flags table, context menu, buffer overflow + Program Output, an 8086
  file, the Arabic UI (findings, details right-to-left, explanation); screenshots `asm_sim_*.png`.

## Smart editor checks: mistakes explained while you type (`radide/asm_lint`)

Every assembly editor (NASM, MASM, FASM, GNU as AT&T / Intel, emu8086 / TASM-style 8086; 16 / 32 / 64-bit; Win64,
System V, 32-bit cdecl / stdcall and DOS) is analysed ~0.4 s after the last key press - without assembling. Each
finding has a rule id, a severity, a short message, **why** it is a problem, **how to fix it**, a "Learn more"
reference (Intel SDM / calling convention / DOS API, plus the instruction's own page from `radide/asm_intel`) and,
when possible, a quick fix. All texts exist in English and Arabic; the IDE language decides, and Arabic keeps the
English message so it can be searched on the web.

**In the editor** (`radide/features/asm_smart_lint.py`): squiggles (Monaco marker owner `radAsmLint`) and a red /
yellow / blue gutter dot per line; hovering a squiggle shows the full explanation; **Ctrl+.** lists the quick fixes
(and "Explain ASMxxx"); **View > Problems Explained** is a dock with the file's findings, their explanation, Fix /
Go to Line / Learn more / Open Lesson (the matching lesson of the Arabic assembly course) and **Configure
Rules...** (per project). The findings also join the **Error List** (`win.diag_providers`); a finding on the same
line as an assembler error is merged away, and the assembler's own messages (NASM, MASM, FASM, GNU as, ld, MS
link) get a friendly explanation (`asm_errors.explain`: tool tip; in Arabic the friendly text comes first, the
original message after it). The same friendly texts appear in the Problems panel.

**How it works** (no Qt in `radide/asm_lint`):

* `parse.py` splits the file into statements with typed operands (register + family + size, immediate + value,
  memory base / index / scale / segment / size, jump target) - AT&T operands are turned into Intel order. It
  reuses `asm_intel` (comment / string masking, the instruction and register tables, dialect / mode / ABI
  detection). Labels are scoped like the assemblers do (NASM / FASM `.local`, MASM labels inside PROC, `@@`,
  GNU `1f` / `1b`); MASM `LOCAL` variables and PROC parameters are typed.
* `flow.py` builds units (PROC ... ENDP, or code from an entry / global / called / address-taken label), basic
  blocks and a control-flow graph (tail jumps, `call ExitProcess`, `int 21h` with AH=4Ch, Linux exit system calls,
  procedures that never return), then runs a forward data flow to a fixed point: per register which bits were
  written, by whom (code, a call that clobbered it, a program argument), constant values; stack depth, RSP mod 16,
  the bytes reserved with `sub rsp` above the last push (shadow space), the `mov rbp, rsp` frame, pushes since the
  last call, the direction flag, DS in DOS EXE programs. Internal procedures get summaries (registers changed and
  not saved, can return, `ret N`), so `call show` followed by `loop` knows whether CX survived.
* `ops.py` (encoding), `symbols.py` (names) and `flow.py` (flow / data / ABI / DOS) produce the findings;
  `config.py` applies the project settings and suppression comments.

**Rules** (66): operands ASM101-125 (size mismatch, unknown memory size, memory to memory, immediate too big,
invalid scale / 16-bit address / mixed address sizes, register not in this mode, immediate destination, segment
register misuse, MOVZX / MOVSX sizes, LEA without memory, AH with REX, PUSH sizes, instructions removed from 64-bit
mode, operand count, MUL / DIV with a number, 80186+ instructions on an 8086, 32-bit address registers in 64-bit
code, an address loaded into a small register, segment overrides, BP addresses use SS, shift counts, useless
moves, DOS / BIOS / Linux interrupts in a Windows program); symbols ASM201-207 (undefined label with "did you
mean", missing `extern`, duplicate label, jump into data, write into a read-only / code section, NASM without
`default rel`, execution running into data); flow ASM301-310 (unreachable code, falling off the end, falling into
the next procedure, unbalanced stack at RET, different stack depths on two paths, POP without PUSH, conditional
jump after an instruction that does not set / leaves undefined the tested flags, signed / unsigned jump hints, JC
after INC); data ASM401-409 (register used before it is set, register clobbered by a call - API or internal
procedure, DIV / IDIV without EDX / RDX / AH, division by a constant 0, a certain divide overflow, LOOP / REP with a
counter never set, STD left set, string instruction without CLD in a 16-bit procedure, IDIV after `xor edx, edx`);
calling conventions ASM501-509 (Win64 shadow space, RSP not 16-byte aligned at a call, callee-saved register
changed without saving, API argument register not set - from the `asm_intel` API table, 32-bit push count, stdcall
double clean-up, cdecl without clean-up, System V variadic AL, the contents of a string passed instead of its
address); DOS ASM601-606 (DS not loaded, no DOS exit, AH not set before INT 21h, unknown INT 21h function, missing
`$` for AH=09h, DX not set for AH=09h). `python -c "from radide.asm_lint import RULES; print(len(RULES))"` lists
them; each rule's texts are in `rules.py`.

**Configuration** - `project.radproj`:

    "asm_lint": {"enabled": true, "rules": {"ASM307": "off", "register-used-before-set": "info"}}

(ids or names; `off` / `error` / `warning` / `info`; the Rules dialog writes it). Suppression comments:
`; asmlint-disable-line ASM101`, `; asmlint-disable-next-line ASM307, ASM401`, `; asmlint-disable-file ASM206`
(no id = every rule). `RADIDE_ASM_LINT=0` switches the analyzer off.

**API**:

    from radide.asm_lint import lint, apply_edits, explain
    for issue in lint(text, path):            # dialect / mode / ABI detected; dialect=, bits=, abi=, config= optional
        issue.rule, issue.severity, issue.line, issue.col, issue.message("ar"), issue.markdown("ar")
        new_text = apply_edits(text, issue.fixes[0].edits)
    explain("main.asm(9) : error A2006:undefined symbol : count").ar

Performance: the context-free part of each line, the operand typing and the instruction effects are cached, so a
5 500-line file is re-analysed after an edit in ~130 ms (the first analysis ~230 ms).

Tests: `samples/Tests/Assembly/SmartLint` - `test_lint_corpus.py` (88 bad / 14 good snippets over every dialect, all
66 rules covered, 19 quick fixes applied and re-checked, no errors / warnings on the 48 sample sources, the project
templates and the 89 runnable course blocks, assembler message translation, configuration, performance) and
`test_lint_ide.py` (the IDE in Arabic and English: squiggles, gutter icons, hover widget, Ctrl+. menu and applying a
fix, the Problems Explained panel, Error List merge, an emu8086 project). Demo projects with commented mistakes:
`SmartLint/NasmMistakes`, `SmartLint/Emu8086Mistakes`.

## Smart editor: beginner QA (samples/Tests/Assembly/SmartStudentQA)

Four beginner programs (NASM x64, MASM x86, emu8086) with the usual mistakes check the three smart-editor parts
together: the squiggle appears while the program is still being typed, the hover / Problems Explained panel say why
in Arabic and how to fix it, the quick fixes make the program build and run (NASM + gcc, ml + link, the 8086
emulator), "Check by running" finds the runtime problems of the half-fixed program and is clean on the fixed one, and
the CPU view shows "jump is taken", inline values and the jump arrows while debugging. Quick fixes added by this QA:

* ASM501 / ASM502 (Win64 call without shadow space / RSP not aligned) in a procedure that never touches RSP:
  "Reserve shadow space" inserts `sub rsp, 40` as the first instruction and `add rsp, 40` before each `ret`.
* ASM304 (stack not balanced at RET) when exactly one pushed register was never popped: "Add pop reg before RET".
* ASM302 on an explicit procedure: "Add RET". The entry procedure of a DOS program (`main proc ... main endp` +
  `end main`) that falls off its end now gets ASM602 "no DOS exit" with the `mov ah, 4Ch / int 21h` fix (it used to
  say "without RET", which is wrong for a DOS .EXE).
