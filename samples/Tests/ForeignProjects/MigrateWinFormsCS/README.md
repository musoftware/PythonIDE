# MigrateWinFormsCS

A Windows Forms (C#, .NET 9) tip calculator created with `dotnet new winforms` and then edited the way the
Visual Studio designer writes forms (`Form1.Designer.cs` without `this.`, events wired with `Load += Form1_Load;`).

- Controls: Labels, TextBoxes, CheckBox, Buttons (with `&` mnemonics), ListBox; FixedSingle, CenterScreen.
- Code (`Form1.cs`): `double.TryParse(..., out double amount)`, `MessageBox.Show` with buttons/icon, `Math.Round`,
  `ToString("F2")`, string interpolation `$"{x:F2}"`, `Items.Add/Clear`, a field counter, `CheckedChanged`.

Builds with `dotnet build`. Used by the tests of **File > Migrate Project...** (radide/features/migrate_wizard.py):
migrated to python-qt and python-tk, then the migrated program is run with scripted clicks and compared with the
C# behaviour. Do not change it (the expected values are in the tests).
