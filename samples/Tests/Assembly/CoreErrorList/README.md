# CoreErrorList

**asm-nasm, x64** - Two mistakes on purpose: an invalid instruction (assembler error, line 15) and a call to a function that does not exist (linker error, line 18).

**Try it:** Open main.asm and save: the Error List shows line 15. Fix it (delete `, 6`) and press Ctrl+F5: the linker error is reported on line 18. Double-click a row to jump there.

*Origin:* Assembly core slice (toolchains / project types / build / GUI Bridge) - created from the New Project templates by the test runs in [CoreTests](../CoreTests/), build output removed.
