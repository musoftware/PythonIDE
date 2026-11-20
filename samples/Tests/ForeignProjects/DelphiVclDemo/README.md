# DelphiVclDemo - hand-written Delphi VCL project (test fixture)

A Delphi 12-style VCL application written by hand (Delphi is not installed here):

* `CustomerApp.dproj` / `CustomerApp.dpr` - project + program (namespaced `Vcl.*` units)
* `MainForm.pas/.dfm` - panel, label, edit, button (with an action), list box, group box with check box,
  radio buttons, combo box (one item in Arabic written as `#1605...` codes) and memo, status bar,
  main menu, timer and an ActionList (a component the RAD IDE designer does not know - kept verbatim)
* `AboutBox.pas/.dfm` - classic Delphi 7 about box (`OldCreateOrder`, `IsControl`, `PixelsPerInch`)
* `CustomerData.pas` - a unit without form

Open it in RAD IDE with **File > Open Project...** (pick `CustomerApp.dproj` or `CustomerApp.dpr`).
The forms open in the designer, saving writes back to the `.dfm`/`.pas` files.
A VCL application cannot be built without Delphi; RAD IDE says so and offers
**Migrate to Lazarus** (a copy that `lazbuild` can build).
