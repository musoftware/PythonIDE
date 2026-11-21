# Emu8086Colors

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** Video mode 03h, INT 10h functions 06h (clear a window), 13h (write a string with an attribute) and 02h (cursor), and direct writes of character + attribute pairs to B800:0000 with STOSW and `es:` overrides.

**Try it:** open `project.radproj` (File > Open Project). Run with Ctrl+F5 and look at the emulator screen; in the Memory tab type `B800:0` to see the character / attribute bytes.

**Expected result:** A blue window with a yellow title and the 16 foreground colours A..P.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086Colors/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
