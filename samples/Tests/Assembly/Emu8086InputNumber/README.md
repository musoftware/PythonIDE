# Emu8086InputNumber

An original 8086 assembly sample for the **8086 Assembly (Emulator)** project type: it runs in RAD IDE's own
8086 emulator (radide/emu8086), nothing has to be installed.

**What it shows:** Macros with parameters (PRINT_STR text, NEWLINE), reading digits with function 01h, MUL, SHL and ADC to print a number in binary. Ends with RET (COM program).

**Try it:** open `project.radproj` (File > Open Project). Step over (F10) the `int 21h` of `read_digit`: the IDE waits until you type a key on the emulator screen.

**Expected result:** Typing `1234` Enter prints `Twice  = 2468` and `Binary = 0000010011010010`.

Headless: `python -m radide.emu8086 samples/Tests/Assembly/Emu8086InputNumber/main.asm` (add `--keys "text
"` for input).
The automated checks are in `samples/Tests/Assembly/Emu8086Tests/test_samples.py`.
