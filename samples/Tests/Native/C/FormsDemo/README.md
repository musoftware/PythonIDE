# FormsDemo (C)

**c-bridge (C), native build** - two forms (menu, timer, progress bar, list, combo, check / radio buttons in a group box,
multi-line text, message box, Arabic text). The code uses the normal GUI Bridge API; Build > Publish makes a
single native exe with radforms (no Python, only Windows system DLLs) - see docs/NATIVE_BUILD.md.

**Try it:** F5 runs it through the GUI Bridge as usual; Build > Publish (Automatic) gives the native exe.
**Test:** `.venv\Scripts\python samples/Tests/Native/test_native_c.py` publishes, starts and drives it.

*Origin:* native C / C++ / Fortran builder agent (radforms).
