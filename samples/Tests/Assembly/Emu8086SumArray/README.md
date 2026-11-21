# Emu8086SumArray

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** .model small EXE: a word array in .data, `count equ ($ - values) / 2`, a loop with SI as a pointer and a procedure that prints AX in decimal.

**Try it:** open `project.radproj` (File > Open Project). Put a breakpoint on `add ax, [si]` (F9), press F5 twice and watch AX grow in the Registers panel; open the Variables tab to see `values` and `total`.

**Expected result:** `Total = 2000`.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086SumArray/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
