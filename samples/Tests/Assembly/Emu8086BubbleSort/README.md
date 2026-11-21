# Emu8086BubbleSort

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** Nested loops with `push cx` / `pop cx`, byte array indexing `list[si]` / `list[si+1]`, `xchg` with memory, `div` by a byte.

**Try it:** open `project.radproj` (File > Open Project). Lower the speed slider in the emulator dock and press F5: the current line moves through the loops while `list` changes in the Variables tab.

**Expected result:** `Before: 64 25 12 22 11 90 03 47` then `After:  03 11 12 22 25 47 64 90`.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086BubbleSort/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
