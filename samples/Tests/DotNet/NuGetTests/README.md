# NuGet tests (Visual Studio 2022 NuGet experience)

Sample projects (never edited in place - the tests copy them to a temp folder):

| Folder | Package management style | Try it |
|---|---|---|
| [`../NuGetSdk`](../NuGetSdk/) | SDK-style net9.0, PackageReference (`dotnet add/remove package`) | Open `NuGetSdk.csproj`, right-click the project > Manage NuGet Packages..., install Newtonsoft.Json, uncomment the lines in Program.cs, F5. |
| [`../NuGetLegacy`](../NuGetLegacy/) | .NET Framework 4.8 old-style project, packages.config (solution `packages` folder, HintPath references, build imports) | Open `NuGetLegacy.sln`, install Newtonsoft.Json, uncomment the line in Program.cs, build (Visual Studio Build Tools MSBuild). |
| [`../NuGetCpm`](../NuGetCpm/) | Central Package Management (`Directory.Packages.props`) | Open `NuGetCpm.sln`, Manage NuGet Packages for Solution, update Newtonsoft.Json: the version changes in Directory.Packages.props. |
| [`../NuGetSolution`](../NuGetSolution/) | Two SDK projects with different Newtonsoft.Json versions | Manage NuGet Packages for Solution > Consolidate; Updates; Tools > NuGet Package Manager > Package Manager Console: `Get-Package`, `Install-Package Humanizer.Core -ProjectName ConsoleApp`. |

Tests:

* `python test_nuget_backend.py` - 48 checks (live nuget.org; `--offline` replays `fixtures/` for the search part and
  skips the project operations; `--record` re-records the fixtures; `--keep` keeps the temp folder).
* `python test_nuget_ui.py` - 40 checks in the IDE (qh.py harness, QSettings org RADIDE-TEST, screenshots via
  `widget.grab()` in `%TEMP%\radide-qa\shots\nuget_*.png`). Needs network.
