# WinFormsVB - foreign project test (fresh `dotnet new winforms -lang VB`)

Unmodified output of `dotnet new winforms -lang VB -n WinFormsVB` (.NET 9 SDK): an empty `Form1`.

Test (File > Open > `WinFormsVB.vbproj`): open `Form1`, drop controls, double-click a button - the handler
`Private Sub Button1_Click(sender As Object, e As EventArgs) Handles Button1.Click` is added to `Form1.vb`
and `Friend WithEvents Button1 As System.Windows.Forms.Button` to `Form1.Designer.vb`. Save, Build / Run.
Opening and saving without changes leaves every file byte-identical.
