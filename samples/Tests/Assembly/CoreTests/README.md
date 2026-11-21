# CoreTests

Scripts that test the core of the Assembly support (radide/asm, radide/languages/asm_*.py). Run them all with

    python samples/Tests/Assembly/CoreTests/run_all.py

| Script | What it checks |
|---|---|
| `test_templates.py` | creates every New Project template (NASM x64 / x86 / Win32 API / Forms x64 / Forms x86 / Class Library, FASM x64 / x86 / Forms, MASM x64 / x86, GNU as AT&T / Intel / Forms AT&T / Forms Intel), builds it with `radide.asm.build.Builder` and runs the console programs with the input `7` (the class library: its `UseFromPython.py`) |
| `test_form_protocol.py <folder>` | drives the form program over the GUI Bridge protocol: `EVENT btnAdd Click` -> `GET txtNumber Text` / `SET txtNumber Text 42` / `SET lblClicks Text 1` ... `DONE` |
| `test_form_bridge.py <folder>` | runs the form in the real bridge host (radide.runtimes.bridge), clicks btnAdd and reads the label / text box back from the window |
| `test_form_flavors.py` | the Windows Forms template of every flavor (NASM x64, NASM x86, FASM x64, GNU as AT&T, GNU as Intel): build, the GUI Bridge protocol (Load, clicks, INPUT / MSGBOX, no handler), a click in the real bridge host window, a gdb breakpoint by line in the form file - 40 checks |
| `test_class_library.py` | the Assembly Class Library: build -> `<Project>.dll` + `lib<Project>.a`, export table, calls from Python (ctypes, the Ctrl+F5 command), C (gcc + import library) and C# (a .NET console project with `DllImport`) |
| `test_linetables.py` | FASM x64 / x86 and MASM x64 / x86: DWARF lines added to the exe (`_build/dwarf.ok`, `debug_info()` = dwarf, objdump), gdb breakpoint / stop / frame name by source line, F10 over the calls of a `cinvoke` / `INVOKE` line in the IDE's debug session, parser units - 43 checks |
| `test_external_console.py` | F5 with `"console": "external"`: gdb with `set new-console on`, the program's own console shows the prompt, `5` + Enter typed into that console (WriteConsoleInputW) reaches `scanf`, breakpoint, exit code 0 |
| `test_runspec.py <folders>` | the Ctrl+F5 path: `plugin.run_spec()` -> bridge runner -> `python -m radide.asm.build` -> program with stdin |
| `test_errors.py` | breaks the templates on purpose and checks the Error List rows (file + line) for NASM, GNU as, FASM, MASM, GNU ld, MS link and a form; plus the parser on sample messages |
| `test_ide.py` | the IDE (QSettings organisation RADIDE-TEST-ASM, cleared at the end): the New Project group *Assembly*, opening a form project, the Error List on save, Tools > Assembly Toolchains |

Projects are created in `%TEMP%
adide-asm-tests`. The MinGW-w64 toolchain of the C support is needed; NASM and
FASM are downloaded on the first build; MASM cases need Visual Studio with the C++ tools.
