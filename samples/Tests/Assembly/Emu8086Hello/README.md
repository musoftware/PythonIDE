# Emu8086Hello

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** The first program: a COM file (org 100h) that prints a $-terminated string with INT 21h function 09h and three stars with function 02h.

**Try it:** open `project.radproj` (File > Open Project). Press F5: the emulator opens paused on `mov ah, 09h`. Press F10 three times and watch AH, DX and the output on the emulator screen. Press F5 to run to the end.

**Expected result:** `Hello, 8086 world!` and `***`.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086Hello/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
