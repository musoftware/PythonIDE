# Shared Projects, project context and the VS2022 New Project wizard

`SharedDemo/SharedDemo.sln` (made by `make_and_build.py --copy-to-sample`; bin/obj removed):

| Project | Kind | Uses |
|---|---|---|
| `SharedCode` | C# Shared Project (`.shproj` + `.projitems`) | - |
| `SharedVB` | VB Shared Project | - |
| `WinApp` | .NET 8 WinForms (`dotnet new winforms`) | SharedCode + ProjectReference to MultiLib |
| `FxConsole` | .NET Framework 4.8 old-style console (RAD IDE template) | SharedCode |
| `SdkFxConsole` | SDK-style console targeting `net48` | SharedCode |
| `VbApp` | .NET 8 VB console (`dotnet new console -lang VB`) | SharedVB |
| `VbFxConsole` | .NET Framework 4.8 old-style VB console (RAD IDE template) | SharedVB |
| `MultiLib` | class library, `net8.0;netstandard2.0` (multi-targeted) | - |

`SharedCode/Greeter.cs` has `#if NET8_0_OR_GREATER / #elif NETFRAMEWORK / #else` branches and
`SharedVB/SharedGreeter.vb` `#If NET8_0_OR_GREATER / #Else`: each consumer prints its own branch.

Note on `NETFRAMEWORK`: the framework symbols (`NETFRAMEWORK`, `NET48`, `NET8_0`...) are defined by the .NET SDK,
so only SDK-style projects have them. `SdkFxConsole` (SDK-style, net48) prints the `NETFRAMEWORK` branch;
`FxConsole` (old-style, net48) has only `DEBUG;TRACE` and prints the `#else` branch. The editor greys exactly
what each project compiles.

## Try it

1. File > Open > `SharedDemo.sln`. Solution Explorer shows `SharedCode` / `SharedVB` with the shared-project icon,
   their files, and every consumer's Dependencies > Shared Projects.
2. Double-click `SharedCode > Greeter.cs`: the project-context combo above the editor lists `WinApp (net8.0-windows)`
   plus `FxConsole (net48)` and `SdkFxConsole (net48)`. Switch: the inactive `#if` branch turns grey. Change the
   solution configuration to Release and the `#if DEBUG` block greys out too.
3. Right-click `SharedCode` > Add > New Item / New Folder; Rename; Properties (root namespace). Right-click a C#
   project > Add > Shared Project Reference... (only same-language shared projects are offered).
4. Right-click the solution > Add > New Project... (the VS2022 wizard: search, language / platform / project type
   filters, Configure your new project, Additional information) or Add > New Shared Project...
   File > New Project (.NET, Visual Studio 2022)... creates a new solution.
5. Build > Build Solution: Visual Studio's MSBuild builds the old-style .NET Framework projects (dotnet alone
   builds the SDK-style ones).

## Tests

* `python make_and_build.py [folder]` - back end, no Qt: templates (dotnet new + RAD templates), shared projects,
  references, #if contexts, MSBuild build of the solution and running each program to compare its output with the un-greyed branch (67 checks).
* `python ui_test.py` - the IDE (qh.py harness): Solution Explorer nodes, menus, shared items, the reference dialog,
  the context combo and greying, renaming, and the wizard creating console / classlib / VB winforms / xunit and the
  RAD templates into the open solution.
