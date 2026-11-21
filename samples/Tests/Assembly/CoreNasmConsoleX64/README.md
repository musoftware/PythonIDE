# CoreNasmConsoleX64

**asm-nasm, x64, gcc** - Template *Assembly Console (x64 Windows, NASM)*: puts / printf / scanf / fflush from the C runtime, a loop, and the Win32 API (GetComputerNameA), with the Microsoft x64 calling convention explained in comments.

**Try it:** Ctrl+F5, type a number in the Program Input bar (e.g. 7): it prints 7 squared, 1 + 2 + ... + 7 and the computer name. F5: breakpoint on line 50 (`mov r8, rax`), F10 steps over `call printf` (gdb reads the DWARF lines RAD IDE generates for NASM).

*Origin:* Assembly core slice (toolchains / project types / build / GUI Bridge) - created from the New Project templates by the test runs in [CoreTests](../CoreTests/), build output removed.
