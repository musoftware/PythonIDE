# VB6Notes (hand-written classic VB6 project, Arabic code page 1256)

* `Notes.vbp` - files in sub-folders (`Forms\`, `Modules\`, `Classes\`), `Startup="Sub Main"`,
  version 2.0.5.
* `Forms\frmMain.frm` - Arabic captions and comments in **cp1256**, a Frame with a CheckBox and an
  OptionButton control array, a Timer, menus.  `Forms\frmEdit.frm` - modal dialog.
* `Modules\modStart.bas` - `Sub Main`, `Classes\CNote.cls` - class with public fields.

Every file must stay in cp1256 with CRLF after an open/save round trip in RAD IDE.
