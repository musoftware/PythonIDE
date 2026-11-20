# WinFormsCS - foreign project test (fresh `dotnet new winforms`, C#)

Unmodified output of `dotnet new winforms -n WinFormsCS` (.NET 9 SDK): an empty `Form1`.

Test (File > Open > `WinFormsCS.csproj`): open `Form1` in the designer, drop a Button, a TextBox and a
Label, change the form's Text, double-click the button (creates
`private void button1_Click(object sender, EventArgs e)` in `Form1.cs` and
`this.button1.Click += new System.EventHandler(this.button1_Click);` in `Form1.Designer.cs` - the file's
own style: `this.` and full type names), type some code, Save, Build / Run. The new controls get
Visual Studio style property blocks (`// \n // button1 \n // `, alphabetical properties,
`SuspendLayout` / `ResumeLayout(false)` / `PerformLayout()` are added because the template has none).
Opening and saving without changes leaves every file byte-identical.
