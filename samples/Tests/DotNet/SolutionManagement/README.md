# SolutionManagement - Visual Studio 2022 solutions in RAD IDE

Two real solutions created with the .NET 9 SDK (`dotnet new sln/console/classlib/winforms/xunit`,
`dotnet sln add --solution-folder`, `dotnet add reference`):

| Solution | Projects |
|---|---|
| `Contoso/Contoso.sln` | `src/Contoso.App` (console, references Core, prints its arguments / CONTOSO_MODE / working directory), `src/Contoso.Core` (class library), `src/Contoso.Desktop` (WinForms), `tests/Contoso.Tests` (xUnit); solution folders `src` and `tests`; `Directory.Build.props` (Company, Authors) |
| `Fabrikam/Fabrikam.sln` | `libs/Fabrikam.Utils` (class library, in solution folder `libs`), `Fabrikam.Cli` (console) - to merge into Contoso |

## What to try in RAD IDE

1. Open `Contoso/Contoso.sln`. Right-click the solution: **Add > Existing Solution's Projects...** >
   `Fabrikam/Fabrikam.sln` (folder `libs` is recreated), **Add > New Solution Folder**, drag `Contoso.Desktop`
   onto the new folder.
2. **Build > Configuration Manager...**: `<New...>` configuration `Staging` copied from Release, uncheck Build for
   `Contoso.Tests`; the toolbar combo shows Staging.
3. Right-click `Contoso.App` > **Build Dependencies > Project Dependencies...**, **Unload Project** / Reload.
4. Solution > **Properties** > Startup Project > **Multiple startup projects**: Contoso.App = Start,
   Fabrikam.Cli = Start without debugging; press Ctrl+F5 / F5.
5. Contoso.App > **Properties** (the VS 2022 document): search, Build per configuration, Package, Signing > New...
   (.snk), Debug > Open debug launch profiles UI (arguments, CONTOSO_MODE, working directory) and choose the profile
   in the drop-down next to the configuration combos; **Manage User Secrets**; **Publish...** (win-x64 single file).
6. Solution > **Save Solution As .slnx...**.

## Tests

* `python test_solution_core.py` (add `--no-build` to skip dotnet build/run/publish) - model, merge, formats,
  properties, signing, secrets, launch profile, build/run/publish (46 checks).
* `python test_solution_ui.py` - the same in the IDE window (64 checks, offscreen, QSettings "RADIDE-TEST").

Both work on copies in `%TEMP%`; these folders are never changed.
