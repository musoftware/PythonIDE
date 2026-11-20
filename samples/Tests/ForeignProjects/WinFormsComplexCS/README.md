# WinFormsComplexCS - foreign project test (Visual Studio C# WinForms, designer round-trip)

Created with `dotnet new winforms -n WinFormsComplexCS`; `Form1` was replaced by a hand-written
`MainForm` written the way Visual Studio 2022 (.NET 8/9 designer) serializes it: short type names, no
`this.`, single-line `AddRange` arrays, `+=` method-group event wiring. `MainForm.resx` holds two tool-bar
images, the PictureBox image and the form icon (byte-array Bitmap / Icon entries, as VS writes them).

What the form contains (everything the WinForms designer of RAD IDE has to read and keep):

* `components` container, `ComponentResourceManager`, `ImageList`, `ToolTip` (`SetToolTip`)
* `MenuStrip` (File / Edit / Help, separator, `ShortcutKeys`), `ToolStrip` (image buttons from the .resx,
  separator, `ToolStripTextBox`), `StatusStrip` with a `ToolStripStatusLabel`
* `SplitContainer` (`Panel1` / `Panel2`, `BeginInit` / `EndInit`, `SplitterDistance`)
* `TreeView` with local `TreeNode` variables, `TabControl` with two `TabPage`s
* `TableLayoutPanel` (column / row styles, `Controls.Add(ctrl, col, row)`, `SetColumnSpan`) and
  `FlowLayoutPanel` (`FlowDirection.RightToLeft`)
* anchors (`Left | Right`, all four edges, `Top | Right`), docking (`Fill`, `Bottom`), fonts, colors,
  `AcceptButton`, `MainMenuStrip`, `MinimumSize`, `StartPosition`, form `Load` event
* custom code after `InitializeComponent()` in `MainForm.cs`

How to test (File > Open > `WinFormsComplexCS.csproj`):

1. The project opens in place (no `project.radproj` is written). Double-click `MainForm` - the designer
   shows the form; TableLayoutPanel / FlowLayoutPanel / SplitContainer are shown as panels (placeholders
   that are kept unchanged), `splitContainer1.Panel1` / `.Panel2` are shown as pseudo panels.
2. Save without changing anything: `MainForm.Designer.cs`, `MainForm.cs` and `MainForm.resx` stay
   byte-identical.
3. Change a text, move a control, add a button to `grpOptions`, double-click it (creates
   `private void button1_Click(object sender, EventArgs e)` in `MainForm.cs` and the `+=` wiring), add a
   menu item, change the PictureBox image (written to `MainForm.resx`), Save, then Build / Run:
   `dotnet build` passes and the running window shows the changes. Only the statements that changed are
   rewritten; unknown statements (`ImageScalingSize`, `RowStyles`, `TreeNode`s ...) stay verbatim.

Automated checks: the scratch scripts of the winforms agent (t_roundtrip.py, t_complex.py, t_more.py,
t_gui.py) - see the agent report.
