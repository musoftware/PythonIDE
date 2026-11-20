# Import report - WinHello.exe

## Identification

| | |
|---|---|
| Type | .NET assembly (C# / VB.NET) |
| Format | PE32+ executable |
| CPU | x64 (64-bit) |
| Subsystem | Windows GUI |
| Compiler / packer | .NET apphost |
| .NET runtime | apphost |
| GUI framework | WinForms |
| Managed assembly | <test folder>\WinHello.dll |
| Product | WinHello |
| Version | 1.0.0.0 |
| Company | WinHello |
| Markers found | .NET apphost, .NET single-file bundle |
| Imports from | SHELL32.dll, ADVAPI32.dll, KERNEL32.dll, USER32.dll, api-ms-win-crt-runtime-l1-1-0.dll, api-ms-win-crt-heap-l1-1-0.dll, api-ms-win-crt-time-l1-1-0.dll, api-ms-win-crt-stdio-l1-1-0.dll, api-ms-win-crt-locale-l1-1-0.dll, api-ms-win-crt-string-l1-1-0.dll, api-ms-win-crt-convert-l1-1-0.dll, api-ms-win-crt-math-l1-1-0.dll |

## Result

- Target language: **python-tk**
- Project folder: `<test folder>\winforms_RAD`
- Startup form: Form1
- Form **Form1**: 6 control(s), 4 event handler(s) with recovered code

## Recovered exactly

- Decompiled WinHello.dll to a C# project with ILSpy (4 .cs files) - kept in the project's _original folder.
- Form Form1: 6 control(s), title, size, positions, fonts, colours, anchors and 4 event handler(s) from InitializeComponent.

## Translated by rules

- Form1: translated to Python by rules: exitToolStripMenuItem_Click, btnGreet_Click, lstLog_DoubleClick, Form1_Load

## Files

- `_original/` - a copy of the imported file and anything recovered that is not project code (decompiled sources, reports, strings)
- `IMPORT_REPORT.md` - this report

---

Import only programs that you wrote, that you own, or that you are allowed to analyse (for example to recover your own lost source code or for interoperability). Decompiling software may be restricted by its licence or by law in your country. Recovered code is a starting point: check it before you use it.
