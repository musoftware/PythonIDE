# BankClasses - VB6 class modules, events, Types, file I/O and Win32 API

A classic VB6 project (`_original_vb6/Bank.vbp`: two standard modules and two class modules, written exactly as
VB6 saves them, with `VERSION 1.0 CLASS` headers and `Attribute` lines), imported with
**File > Import > Visual Basic 6 project** and run by the IDE's VB interpreter without changes.

What it shows:

| File | Feature |
|---|---|
| `CAccount.cls` | Class module: `Property Get/Let`, default property (`Attribute Owner.VB_UserMemId = 0`), `Event` + `RaiseEvent`, `ByRef Cancel` event argument, `Err.Raise vbObjectError + 1000`, `Class_Initialize` |
| `CBank.cls` | Collection class: `Private WithEvents mCurrent As CAccount` handlers, default `Item` property, `For Each` through `NewEnum` (`VB_UserMemId = -4`, `mAccounts.[_NewEnum]`), `Class_Terminate` (runs on `Set Bank = Nothing`) |
| `modApi.bas` | `Declare Function ... Lib "kernel32" Alias "...A"` (String buffers, `ByRef` Long, a `SYSTEMTIME` Type passed `ByRef`, `String * 260`) |
| `modMain.bas` | `Sub Main`, `New`/`Set`/`Nothing`/`Is`, `On Error GoTo` + `Resume Next`, a `Type` with `String * 5` saved to a **Random** file (`Put`/`Get`/`Len = Len(t)`), `Print #`, `Write #`, `Input #`, `Line Input #`, `EOF`, `LOF`, `Dir$`, `Kill`, `FreeFile`, `GoSub`/`Return`, `Format$` |

How to try it: open this folder (File > Open Project), press **F5**. The Output window shows:

```
Withdraw 200 from AC002: False
With overdraft allowed: True
Error 1000 in CAccount.Owner: Owner name is required
AC001   Mahmoud 500.00
AC002   Sara    -79.50
Total: 420.50
AC001: 0.00 -> 500.00
AC002: 0.00 -> 120.50
AC002: overdraft of 79.50 refused
AC002: overdraft of 79.50 allowed
AC002: 120.50 -> -79.50
Record 2: AC001 20.50 kind 2
Records: 3
Report lines read back: 2
5! = 120
API year ok: True
Computer name length > 0: True
Temp folder ends with \: True
Bank closed (2 accounts)
Done
```

From a terminal: `.venv\Scripts\python -m radide.runtimes.vbrun samples\Tests\VB6\BankClasses`.
To repeat the import: File > Import > Visual Basic 6 project > `_original_vb6\Bank.vbp`.
