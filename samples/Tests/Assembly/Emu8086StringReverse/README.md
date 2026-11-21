# Emu8086StringReverse

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** Full segment definitions (`data segment` / `stack segment stack` / `code segment`, `assume`, `end start`) and buffered keyboard input (INT 21h function 0Ah).

**Try it:** open `project.radproj` (File > Open Project). Run with Ctrl+F5, click the emulator screen and type a word, then Enter. Open the Memory tab and type `buffer` in the address box to see how DOS fills the buffer.

**Expected result:** Typing `hello` prints `Reversed: olleh`.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086StringReverse/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
