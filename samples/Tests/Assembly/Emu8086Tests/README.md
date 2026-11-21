# Emu8086Tests

Automated checks of RAD IDE's 8086 teaching emulator (`radide/emu8086`) and of the
**8086 Assembly (Emulator)** project type (`radide/languages/emu8086.py`). See docs/ASSEMBLY.md, section
"8086 emulator".

| Script | What it checks | Needs |
|---|---|---|
| `test_cpu.py` | 64 instruction cases (results and flags), REP string instructions, divide errors, video memory, far call + a program-installed interrupt vector, reverse step, keyboard services, input wait | Python only |
| `test_assembler.py` | 58 encodings byte by byte, jump sizing, long conditional jumps, COM / EXE layout, source map, data definitions, macros, equates and operators, the built-in emu8086.inc, error codes, Arabic messages | Python only |
| `test_samples.py` | the eight `Emu8086*` samples headless: program output, screen text, colours; KeyGame played with arrow keys | Python only |
| `test_plugin.py` | the language plugin: templates, run spec, completions, hover, outline, Go to Definition, the 16-bit source detector | Python only |
| `test_ide.py` | the real IDE offscreen (QSettings "RADIDE-TEST", cleared afterwards): F5 paused at entry, stepping, breakpoints, Locals / Call Stack / registers, Step Back / Step Out, views, Watch, keyboard input, slow motion, Pause / Stop, Error List in Arabic, screenshots with `widget.grab()` | PyQt6 |

Run each one with `python samples/Tests/Assembly/Emu8086Tests/<script>.py` (or `pytest` on the folder).
Screenshots of `test_ide.py` go to `%TEMP%\radide_emu8086` (or `$RADIDE_SHOTS`).
