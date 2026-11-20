# Native_Greeter

**Exe import: native Win32 (C)** - DIALOGEX resource -> forms, menu, About dialog, handlers recovered from machine code (capstone), e.g. btnGreet_Click.

**Try it:** `build.bat` (MinGW) builds Greeter.exe; then File > Import > Program... (or `python ..\reimport.py Greeter.exe out`). `Imported_python-tk` is the project the import produced; F5 it.

*Origin:* agents5 exe-core (copied from the IDE's test runs, build output removed).

No binaries are kept in the repo: `source/` + `build.bat` rebuild the test program with the IDE's toolchains, so the import can be repeated.
