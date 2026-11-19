# Import report - Adder.exe

## Identification

| | |
|---|---|
| Type | Native program (C / C++ / other compiled language) |
| Format | PE32+ executable |
| CPU | x64 (64-bit) |
| Subsystem | Windows GUI |
| Compiler / packer | MinGW-w64 / MinGW / GCC |
| GUI framework | Win32 API |
| Markers found | MinGW / GCC, GCC, MinGW-w64 |
| Imports from | KERNEL32.dll, api-ms-win-crt-convert-l1-1-0.dll, api-ms-win-crt-environment-l1-1-0.dll, api-ms-win-crt-heap-l1-1-0.dll, api-ms-win-crt-locale-l1-1-0.dll, api-ms-win-crt-math-l1-1-0.dll, api-ms-win-crt-private-l1-1-0.dll, api-ms-win-crt-runtime-l1-1-0.dll, api-ms-win-crt-stdio-l1-1-0.dll, api-ms-win-crt-string-l1-1-0.dll, USER32.dll |

## Result

- Target language: **python-tk**
- Project folder: `C:\Users\Mahmo\AppData\Local\Temp\claude\a04f521f5a700edd\e4285af5-0b45-4335-a89a-d0dc219b139e\scratchpad\agents5\exe-core\out\Adder_tk`
- Startup form: frmMain
- Form **frmMain**: 6 control(s), 1 event handler(s) with recovered code

## Recovered exactly

- Form frmMain: 6 control(s) recovered from CreateWindowEx calls in sub_140001760

## Translated by rules

- frmMain.btnAdd.Click: 6 call(s) translated by rules (GetDlgItemTextA, SetDlgItemTextA, atoi, sprintf)

## Not recovered (missing)

- No DIALOG or MENU resources: the window layout is created in code and cannot be recovered from resources
- 6 program function(s) kept as documented stubs (see Adder_native.py)

## Notes

- No symbol table (stripped): functions are named sub_<address>
- sub_140001760 at 0x140001760 is the event procedure of frmMain (3 case(s) recovered)
- Ghidra is not installed: no pseudo-C (install it into %LOCALAPPDATA%\RADIDE\tools or set GHIDRA_HOME for full decompilation)

## Recovered event code (neutral form)

- `frmMain.btnAdd.Click: get_text(first_number, txtFirstNumber); get_text(second_number, txtSecondNumber); assign(text, 'Sum = %d' % (int(first_number) + int(second_number),)); set_text(lbl104, text)`

## Files

- `_original/` - a copy of the imported file and anything recovered that is not project code (decompiled sources, reports, strings)
- `IMPORT_REPORT.md` - this report

---

Import only programs that you wrote, that you own, or that you are allowed to analyse (for example to recover your own lost source code or for interoperability). Decompiling software may be restricted by its licence or by law in your country. Recovered code is a starting point: check it before you use it.
