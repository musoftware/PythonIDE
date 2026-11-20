# VB6Calculator (hand-written classic VB6 project)

Test project for opening VB6 projects **in place** in RAD IDE (`radide/foreign/vb6_project.py`).

* `Calc.vbp` - Standard EXE: 2 forms, a standard module, a class module, a COM reference (stdole2) and an
  OCX component line (`MSCOMCTL.OCX`), a related document, `[MS Transaction Server]` section.
* `frmCalc.frm` - control array `cmdDigit(0..9)` with `cmdDigit_Click(Index As Integer)`, a third-party
  OCX control (`MSComctlLib.StatusBar` with nested `BeginProperty Panels`), a ListBox whose items live in
  `frmCalc.frx` (`List = "frmCalc.frx":0002`), a form-level Font block, menus with a separator, a
  shortcut and an invisible popup menu.
* `CHistory.cls` - class module (VERSION 1.0 CLASS header), `modMath.bas` - `Calculate()`.

Open with File > Open (`Calc.vbp`).  Saving without changes leaves every file byte-identical; designer
changes touch only the edited lines.  F5 runs the native files on the bundled VB6 interpreter.
