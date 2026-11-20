# Import report - notes3.12.exe

## Identification

| | |
|---|---|
| Type | Python program packed with PyInstaller |
| Format | PE32+ executable |
| CPU | x64 (64-bit) |
| Subsystem | Windows GUI |
| Compiler / packer | PyInstaller |
| Python version | 3.12 |
| Markers found | PyInstaller, PyInstaller cookie |
| Imports from | USER32.dll, COMCTL32.dll, KERNEL32.dll, ADVAPI32.dll, GDI32.dll |

## Result

- Target language: **python-tk**
- Project folder: `<test folder>\notes312`
- Startup form: Form1
- Form **Form1**: 0 control(s), 0 event handler(s) with recovered code

## Recovered exactly

- Extracted 1 entry script(s), 115 module(s) and 982 data file(s) (Python 3.12).
- 1 window(s) captured with 0 control(s); 0 event handler(s) connected to the original callbacks (Python importer, python-tk).

## Translated by rules

- notes_app.py: source rebuilt with built-in decompiler (4 part(s) kept as disassembly)

## Warnings

- functions kept as disassembly: summary, load_notes, tag_index, add
- NotImplementedError: load_notes could not be decompiled

## Files

- `_original/` - a copy of the imported file and anything recovered that is not project code (decompiled sources, reports, strings)
- `IMPORT_REPORT.md` - this report

---

Import only programs that you wrote, that you own, or that you are allowed to analyse (for example to recover your own lost source code or for interoperability). Decompiling software may be restricted by its licence or by law in your country. Recovered code is a starting point: check it before you use it.
