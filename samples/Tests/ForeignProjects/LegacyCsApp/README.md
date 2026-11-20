# LegacyCsApp - a classic (non-SDK) .NET Framework 4.8 WinForms project

Hand-written exactly like Visual Studio 2017-2022 writes old-style projects: `ToolsVersion="15.0"`,
`xmlns=".../msbuild/2003"`, `<Configuration Condition=...>` defaults, per-configuration `PropertyGroup`s,
`<Reference Include="System.Windows.Forms" />`, explicit `<Compile Include>` with `<SubType>Form</SubType>`
and `<DependentUpon>`, `EmbeddedResource` for the `.resx`, `Properties\AssemblyInfo.cs`, `App.config`.

It builds with Visual Studio's MSBuild (found through `vswhere`), not with `dotnet build`:

    "%ProgramFiles%\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" LegacyCsApp.sln

## In RAD IDE

* Open `LegacyCsApp.sln`: the tree shows **References** (legacy projects) and `MainForm.cs` > `MainForm.Designer.cs`
  + `MainForm.resx`; the form opens in the designer.
* **Add > New Item > Class / Windows Form** writes the files *and* the `<Compile Include>` entries
  (with `SubType` / `DependentUpon`) into the `.csproj`, next to the other Compile items, in the file's own
  indentation and newlines.
* **Add > Assembly Reference** adds `<Reference Include="..."/>`; NuGet packages are written as
  `<PackageReference>` (restored by `MSBuild -restore`).
* Build / F5 use MSBuild. .NET Framework programs run without the netcoredbg debugger (it only debugs
  .NET Core / .NET 5+); right-click the solution > *Open in Visual Studio* to debug them there.
