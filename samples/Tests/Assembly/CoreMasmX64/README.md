# CoreMasmX64

**asm-masm, x64, link.exe** - Template *MASM Console (x64)*: ml64 (no INVOKE: RCX / RDX / R8 / R9 and shadow space by hand), linked with link.exe against msvcrt + legacy_stdio_definitions.

**Try it:** Needs Visual Studio with the C++ tools. Ctrl+F5, type 7: prints 7 cubed = 343. Debugging needs the Visual Studio debugger (PDB).

*Origin:* Assembly core slice (toolchains / project types / build / GUI Bridge) - created from the New Project templates by the test runs in [CoreTests](../CoreTests/), build output removed.
