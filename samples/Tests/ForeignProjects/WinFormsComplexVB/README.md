# WinFormsComplexVB - foreign project test (Visual Studio VB.NET WinForms, designer round-trip)

Created with `dotnet new winforms -lang VB -n WinFormsComplexVB`; `Form1` was replaced by a hand-written
`MainForm` in the classic Visual Studio (2010-2019) VB style: `Me.` prefix, fully qualified type names,
`_` line continuations, `CType(... Or ..., AnchorStyles)` anchors, `8.25!` font sizes,
`'` / `'Name` / `'` block headers, `Friend WithEvents` fields, events wired with `Handles` clauses in
`MainForm.vb` (one method handles a button and a menu item: `Handles btnSave.Click, SaveToolStripMenuItem.Click`).
`MainForm.resx` holds the PictureBox image and the form icon plus tray locations.

Contents: MenuStrip (File > Save / separator / Exit, `ShortcutKeys`), TabControl with two pages, a docked
GroupBox with labels, TextBox (anchored, with a ToolTip), ComboBox (`Items.AddRange`, DropDownList),
CheckBox, PictureBox (resource image, `BeginInit`/`EndInit`), a ListBox docked in the second page, a Panel
docked at the bottom with an anchored button and a status label, a Timer, `AcceptButton`, the form icon.

How to test (File > Open > `WinFormsComplexVB.vbproj`):

1. Open `MainForm` in the designer, Save without changes: all files stay byte-identical.
2. Add a button, double-click it: `Private Sub Button1_Click(sender As Object, e As EventArgs) Handles
   Button1.Click` is added to `MainForm.vb` (the Designer file gets `Friend WithEvents Button1`).
3. Rename `Label2` (the Designer statements, the `'Label2` header and `Handles` clauses follow the
   rename); delete `chkVip` (its statements and field go, and - like Visual Studio - the
   `Handles chkVip.CheckedChanged` clause is removed from the method, which is kept).
4. Build / Run with the .NET SDK (`dotnet build`).
