# MigrateWinFormsVB

A Windows Forms (VB.NET, .NET 9) temperature converter created with `dotnet new winforms -lang VB` and edited the
way the Visual Studio designer writes VB forms (`Me.`, `Friend WithEvents`, handlers with `Handles X.Click`,
`Handles MyBase.Load`).

- Code (`Form1.vb`): a field with an initializer, `Double.TryParse`, `MessageBox.Show(text, title, buttons, icon)`,
  `Dim x As Double = ...`, `+=`, `&=`, `.ToString("0.0")`, `.Checked`, `Items.Add/Clear`, `Return`.

Builds with `dotnet build`. Used by the tests of **File > Migrate Project...**: migrated to vb-basic (run on the
bundled VB6 interpreter) and to python-tk / python-qt, then run with scripted clicks and compared with the VB.NET
behaviour. Do not change it.
