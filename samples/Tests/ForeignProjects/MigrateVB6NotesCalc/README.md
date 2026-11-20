# MigrateVB6NotesCalc

Hand-written Visual Basic 6 project (VB6 file formats: `.vbp`, `.frm` with CRLF line endings, `.bas`, `.cls`)
used to test **File > Migrate Project...** (radide/features/migrate_wizard.py, engine radide/migrate/).

- `frmMain.frm` - notes list (TextBox, ListBox, CheckBox, Add/Remove/Save/Load buttons), a calculator with a
  **control array** `cmdOp(0..3)`, `Select Case`, `Format`, `MsgBox`/`InputBox`, file I/O
  (`Open ... For Output/Input`, `Print #`, `Line Input #`, `EOF`), `On Error GoTo`, a `Timer`, `KeyPress`
  and `Form_Unload(Cancel)`.
- `modUtil.bas` - a public variable and functions used by the form.
- `CCounter.cls` - a class with a method and `Property Get/Let`.

Migrated by the tests to python-tk, python-qt and VB.NET (see the migration report written into each migrated
project: `MIGRATION_REPORT.md`). Do not change: the tests compare behaviour on scripted clicks.
