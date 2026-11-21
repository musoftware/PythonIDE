# Emu8086Factorial

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** A recursive procedure with its argument on the stack (`[bp+4]`), `push` / `call` / `add sp, 2`, `mul word ptr [bp+4]`.

**Try it:** open `project.radproj` (File > Open Project). Step Into (F11) `call factorial` several times: the Call Stack and the emulator's Stack tab show every level. Shift+F11 steps out. Try Step Back in the emulator dock.

**Expected result:** `7! = 5040`.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086Factorial/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
