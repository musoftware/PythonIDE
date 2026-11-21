# CoreNasmConsoleX86

**asm-nasm, x86, GNU ld (direct DLL linking)** - Template *Assembly Console (x86 Windows, NASM)*: cdecl and stdcall (`_printf`, `_GetComputerNameA@8`), entry `_main`, ExitProcess. Linked with `ld -m i386pe` straight against msvcrt.dll / kernel32.dll in SysWOW64.

**Try it:** Ctrl+F5, type 7. F5: breakpoint on line 62 (`dec ecx`) - the 64-bit gdb debugs the 32-bit program by line.

*Origin:* Assembly core slice (toolchains / project types / build / GUI Bridge) - created from the New Project templates by the test runs in [CoreTests](../CoreTests/), build output removed.
