# Assembly QA (user flow)

`test_user_flow.py` drives the real IDE (offscreen, QSettings organisation `RADIDE-TEST`, cleared at the end) the
way a user works with the Assembly support. Screenshots are taken with `widget.grab()` only and saved to
`%TEMP%\radide-asm-qa\shots`; projects are created in `%TEMP%\radide-asm-qa\work`.

    python samples/Tests/Assembly/QA/test_user_flow.py              # every phase
    python samples/Tests/Assembly/QA/test_user_flow.py debug look   # some phases
    set ASMQA_LANG=ar & python samples/Tests/Assembly/QA/test_user_flow.py look help   # Arabic UI

| Phase | What it checks |
|---|---|
| `newproj` | File > New Project (the real dialog) for every console template (NASM x64 / x86, FASM x64 / x86, GNU as AT&T / Intel, MASM x64 / x86 when Visual Studio is installed), then Ctrl+F5, typing `7` into the Program Input bar |
| `forms` | the NASM Windows Forms template: the project opens, it builds, and `btnAdd_Click` answers in the real bridge window |
| `errors` | a broken line in `main.asm`: Ctrl+F5 fails and the Error List shows `main.asm` at that line |
| `intel` | completion, hover (instruction, `printf`) and Go to Definition of a data label |
| `debug` | F5 with an editor breakpoint: stop on the line, Registers / Disassembly / Memory windows, F10, Continue; the program's `scanf` reads `7` from the Program Input bar **under the debugger** |
| `cdebug` | regression: a C (GUI Bridge) project builds with Ctrl+F5, and F5 stops on a breakpoint in `Form1_Load` with the Registers window |
| `emu` | 8086 emulator project: F5 pauses on the first instruction, F10 steps |
| `help` | Help > Help Files (CHM) lists `RADIDE_ASSEMBLY_ar.chm`; the Tutorials view shows the Assembly course |
| `tutor` | the first lesson block that has a "جرّبه" button runs as an asm-nasm project |
| `openfolder` | File > Open Folder on `OpenFolder/NasmLoose`, `OpenFolder/GasLoose` and `NasmLooseInput` (here): opened in place, F5 stops on a breakpoint, the program ends; `NasmLooseInput` reads its number from the Program Input bar with F5 and Ctrl+F5 |
| `regress` | new C / C++ / Fortran / Rust (GUI Bridge) projects still build |
| `look` | dark theme (and Arabic UI with `ASMQA_LANG=ar`) screenshots of an assembly project with the debugger windows; in Arabic every assembly menu entry is translated |

`NasmLooseInput/input.asm` is a loose NASM program (no project file) that reads a number with `scanf`.
