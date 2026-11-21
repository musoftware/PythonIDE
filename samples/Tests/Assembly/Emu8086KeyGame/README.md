# Emu8086KeyGame

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** A small game: INT 16h function 00h (wait for a key, scan codes of the arrow keys), INT 10h functions 02h / 09h, a pseudo-random generator with MUL.

**Try it:** open `project.radproj` (File > Open Project). Run with Ctrl+F5, click the emulator screen and move the @ with the arrow keys onto the star. Esc ends the game.

**Expected result:** The score at the top-left goes up each time the @ reaches the star.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086KeyGame/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
