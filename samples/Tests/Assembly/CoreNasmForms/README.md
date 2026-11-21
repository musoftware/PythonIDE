# CoreNasmForms

**asm-nasm, x64, GUI Bridge** - Template *Assembly Windows Forms (NASM + GUI Bridge)*: Form1 (label, text box, two buttons) drawn by the IDE; `handler btnAdd_Click` ... `endhandler` in Form1.asm reads the text box with `rad_get_int`, adds 1, writes it back with `rad_set_int`, counts the clicks in `[clicks]`; `btnHello_Click` uses `rad_input` and `rad_msgbox`. Form1.inc (control names / IDs) and _radmain.asm (event loop + dispatch table) are generated.

**Try it:** F5 or Ctrl+F5, press *Add 1* (41 -> 42, Clicks: 1) and *Say hello*. Debug: breakpoint on line 21 of Form1.asm (`inc rax`), press Add 1, look at RAX. Double-click another control in the designer to add a handler.

*Origin:* Assembly core slice (toolchains / project types / build / GUI Bridge) - created from the New Project templates by the test runs in [CoreTests](../CoreTests/), build output removed.
