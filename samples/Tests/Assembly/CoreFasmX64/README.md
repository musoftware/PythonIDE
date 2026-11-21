# CoreFasmX64

**asm-fasm, x64, no linker** - Template *FASM Console (x64)*: `format PE64 console`, imports with the win64a.inc macros, `cinvoke` / `invoke` (FASM writes the .exe itself; RAD IDE sets INCLUDE to FASM's INCLUDE folder).

**Try it:** Ctrl+F5, type 7: prints 7 + 7 = 14 and the computer name. FASM is downloaded from flatassembler.net on the first build.

*Origin:* Assembly core slice (toolchains / project types / build / GUI Bridge) - created from the New Project templates by the test runs in [CoreTests](../CoreTests/), build output removed.
