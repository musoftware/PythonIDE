# PyInstaller_Tk

**Exe import: PyInstaller** - Archive extraction + the built-in bytecode decompiler (Python 3.11-3.13) rebuild tkhello.py; the Python importer turns it into a form.

**Try it:** `build.bat` (PyInstaller in the IDE's .venv) -> dist\TkHello.exe; import it.

*Origin:* agents5 exe-managed (copied from the IDE's test runs, build output removed).

No binaries are kept in the repo: `source/` + `build.bat` rebuild the test program with the IDE's toolchains, so the import can be repeated.
