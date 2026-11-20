# Import report - Greeter_stripped.exe

## Identification

| | |
|---|---|
| Type | Native program (C / C++ / other compiled language) |
| Format | PE32+ executable |
| CPU | x64 (64-bit) |
| Subsystem | Windows GUI |
| Compiler / packer | MinGW-w64 / MinGW / GCC |
| GUI framework | Win32 API (dialog resources) |
| Product | Greeter |
| Version | 1.2.0.0 |
| Company | RAD Test |
| Markers found | MinGW / GCC, GCC, MinGW-w64 |
| Imports from | KERNEL32.dll, api-ms-win-crt-environment-l1-1-0.dll, api-ms-win-crt-heap-l1-1-0.dll, api-ms-win-crt-locale-l1-1-0.dll, api-ms-win-crt-math-l1-1-0.dll, api-ms-win-crt-private-l1-1-0.dll, api-ms-win-crt-runtime-l1-1-0.dll, api-ms-win-crt-stdio-l1-1-0.dll, api-ms-win-crt-string-l1-1-0.dll, USER32.dll |

## Result

- Target language: **python-tk**
- Project folder: `<test folder>\greeter_dark`
- Startup form: frmGreeter
- Form **frmGreeter**: 12 control(s), 6 event handler(s) with recovered code
- Form **frmAboutGreeter**: 3 control(s), 1 event handler(s) with recovered code

## Recovered exactly

- Form frmGreeter: dialog 101 'Greeter' with 12 control(s) (DIALOGEX, font MS Shell Dlg 8, dialog units converted to pixels)
- Form frmAboutGreeter: dialog 102 'About Greeter' with 3 control(s) (DIALOG, font MS Sans Serif 8, dialog units converted to pixels)
- 2 string(s) from the STRINGTABLE (kept in strings.py / the report)
- Version information: CompanyName=RAD Test, FileDescription=Greeter test program, FileVersion=1.2.0.0, ProductName=Greeter
- 1 icon(s) extracted (.ico)
- Ghidra decompiled 56 function(s) to pseudo-C (kept in decompiled.c)

## Translated by rules

- frmGreeter.Load: 1 call(s) translated by rules (SetDlgItemTextA)
- frmGreeter.mnuHelpAbout.Click: 1 call(s) translated by rules (MessageBoxA)
- frmGreeter.btnGreet.Click: 4 call(s) translated by rules (GetDlgItemTextA, SendDlgItemMessageA, SetDlgItemTextA, sprintf)
- frmGreeter.mnuFileExit.Click: 1 call(s) translated by rules (EndDialog)
- frmGreeter.btnClose.Click: 1 call(s) translated by rules (EndDialog)
- frmGreeter.mnuFileClear.Click: 1 call(s) translated by rules (SendDlgItemMessageA)
- frmAboutGreeter.btnOK.Click: 1 call(s) translated by rules (EndDialog)

## Not recovered (missing)

- 7 program function(s) kept as documented stubs (see GreeterStripped_native.py)

## Notes

- No symbol table (stripped): functions are named sub_<address>
- sub_140001760 at 0x140001760 is the event procedure of frmGreeter (6 case(s) recovered)
- frmAboutGreeter: the WM_COMMAND code of sub_1400018C3 was given to btnOK (the id test was not a simple compare)
- sub_1400018C3 at 0x1400018C3 is the event procedure of frmAboutGreeter (1 case(s) recovered)

## Recovered event code (neutral form)

- `frmGreeter.Load: set_text(lblResult, 'Type a name and press Greet')`
- `frmGreeter.mnuHelpAbout.Click: msgbox('Greeter 1.0 - made with MinGW', 'About Greeter', info)`
- `frmGreeter.btnGreet.Click: get_text(your_name, txtYourName); assign(text, 'Hello, %s!' % (your_name,)); set_text(lblResult, text); list_add(lstItems, your_name)`
- `frmGreeter.mnuFileExit.Click: close()`
- `frmGreeter.btnClose.Click: close()`
- `frmGreeter.mnuFileClear.Click: list_clear(lstItems)`
- `frmAboutGreeter.btnOK.Click: close()`

## Files

- `_original/` - a copy of the imported file and anything recovered that is not project code (decompiled sources, reports, strings)
- `IMPORT_REPORT.md` - this report

---

Import only programs that you wrote, that you own, or that you are allowed to analyse (for example to recover your own lost source code or for interoperability). Decompiling software may be restricted by its licence or by law in your country. Recovered code is a starting point: check it before you use it.
