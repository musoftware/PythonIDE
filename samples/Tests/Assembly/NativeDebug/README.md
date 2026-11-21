# NativeDebug

Test programs for the **native debugger windows** (Debug > Windows > Registers / Disassembly / Memory 1 /
Stack) and for debugging assembly with gdb (`radide/nativedbg.py`, `radide/features/native_debug.py`,
docs/ASSEMBLY.md "Native debugger").

| File | What |
|---|---|
| `sum.asm` | NASM, Windows x64: adds the table `values` (11, 22, 33, 44) in a loop and prints the total (110). |
| `waits.asm` | NASM: waits for Enter, then counts - for attaching gdb to a running assembly program. |
| `sum_gas.s` | The same sum in GNU as (Intel syntax); `gcc -g` gives DWARF lines. |
| `arrays.c` | C (`gcc -g -O0`): the native windows on a C program. |
| `build.bat` | Builds `sum.exe`, `sum_gas.exe` and `arrays.exe` with the WinLibs toolchain of RAD IDE. |
| `test_native_debug.py` | The automated test (37 checks, in the real IDE window). |

**Try it by hand:** put `sum.asm` in an Assembly project (File > New Project > Assembly > Assembly Console (x64 Windows, NASM), Project > Add
Existing Item), F9 on the line `add  rax, [rbx]`, F5:

1. It stops on that line. Alt+5 shows the **Registers**: rax = 0; F10 (or Ctrl+Alt+F10) - rax = 0x0B in red.
2. Alt+6, **Memory 1**, type `values` in Address: `0B 00 00 00 00 00 00 00 16 ...`; choose 8-byte columns.
3. Alt+8, **Disassembly**: the yellow arrow, the `.asm` lines between the instructions; click the left
   column of `mov QWORD PTR [rip+...],rax` (after the loop) for an address breakpoint, F5 - rax = 0x6E (110).
4. **Stack**: the slots from RSP; double-click a value to see that memory.

The same windows work for `arrays.c` (C source lines in the disassembly, `&table` in the memory window).

**Automated:** `python samples/Tests/Assembly/NativeDebug/test_native_debug.py` (QSettings "RADIDE-TEST",
cleared at the end; copies the files to a temp folder; screenshots of the windows via `widget.grab()` into
`%TEMP%\radide_native_debug`, or `RADIDE_SHOTS`). Needs `%LOCALAPPDATA%\RADIDE\toolchains\mingw64` (gcc, nasm,
gdb >= 14); the last part (F5 of a NASM project) also needs the Assembly core support (`radide/asm`).
