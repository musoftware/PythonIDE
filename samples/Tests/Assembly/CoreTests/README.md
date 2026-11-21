# CoreTests

Scripts that test the core of the Assembly support (radide/asm, radide/languages/asm_*.py). Run them all with

    python samples/Tests/Assembly/CoreTests/run_all.py

| Script | What it checks |
|---|---|
| `test_templates.py` | creates every New Project template (NASM x64 / x86 / Win32 API / Forms, FASM x64 / x86, MASM x64 / x86, GNU as AT&T / Intel), builds it with `radide.asm.build.Builder` and runs the console programs with the input `7` |
| `test_form_protocol.py <folder>` | drives the form program over the GUI Bridge protocol: `EVENT btnAdd Click` -> `GET txtNumber Text` / `SET txtNumber Text 42` / `SET lblClicks Text 1` ... `DONE` |
| `test_form_bridge.py <folder>` | runs the form in the real bridge host (radide.runtimes.bridge), clicks btnAdd and reads the label / text box back from the window |
| `test_runspec.py <folders>` | the Ctrl+F5 path: `plugin.run_spec()` -> bridge runner -> `python -m radide.asm.build` -> program with stdin |
| `test_errors.py` | breaks the templates on purpose and checks the Error List rows (file + line) for NASM, GNU as, FASM, MASM, GNU ld, MS link and a form; plus the parser on sample messages |
| `test_ide.py` | the IDE (QSettings organisation RADIDE-TEST-ASM, cleared at the end): the New Project group *Assembly*, opening a form project, the Error List on save, Tools > Assembly Toolchains |

Projects are created in `%TEMP%adide-asm-tests`. The MinGW-w64 toolchain of the C support is needed; NASM and
FASM are downloaded on the first build; MASM cases need Visual Studio with the C++ tools.
