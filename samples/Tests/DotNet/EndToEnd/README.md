# .NET end-to-end QA (VS2022 parity)

Cross-slice checks of the Visual Studio 2022 style .NET support (NuGet, references, solutions, shared projects,
tools). Every script runs in the IDE window offscreen through `samples/Tests/QA/Integration/qh.py`
(QSettings org `RADIDE-TEST`, cleared; screenshots with `widget.grab()` in `%TEMP%\radide-qa\shots`) and works
on temp copies only: the samples in this folder are never edited in place.

| Script | What it does |
|---|---|
| `test_e2e_ui.py` | One user journey over a copy of `../SolutionVS2022` + `../SolutionMerge`: New Project wizard (class library, C# shared project, xUnit, .NET Framework class library, console) -> merge `Tools.slnx`'s projects -> Reference Manager (shared project, project references, circular refusal, Browse DLL, framework assembly + COM on the old-style project) -> NuGet (Package Manager Console `Install-Package`, solution Consolidate, project Install / Uninstall) -> code that uses all of them -> Build Solution -> Configuration Manager (new `QA` configuration, build in it) -> Project Properties round trip -> launch profile + multiple startup projects (Ctrl+F5, output checked) -> Save As `.slnx`, reopen, Build Solution -> Test Explorer (pass + intentional failure) -> Object Browser + ilspycmd decompile -> Code Cleanup + Remove and Sort Usings. |
| `test_arabic_dark.py` | Arabic UI + Dark theme: opens every new .NET window (wizard, Reference Manager, NuGet project / solution documents, Package Manager Console, NuGet options, Configuration Manager, Project Dependencies, Solution Property Pages, Project Properties, Launch Profiles, Publish, Object Browser, Test Explorer, Configure Code Analysis), screenshots `ar_dark_*.png`, checks right-to-left + translated buttons, the solution context menu, and that `i18n.missing()` holds no string written in the .NET modules' source. |
| `test_regression_ui.py` | The existing `samples/Tests/ForeignProjects` .NET samples (VsSolution .sln and .slnx, LegacyCsApp, WinForms C#/VB, complex WinForms, migration samples, NativeCpp .vcxproj) open in place and build; `samples/HelloCSharp` (C# GUI Bridge) and `samples/HelloPython` build and run. |

Run:

    python samples/Tests/DotNet/EndToEnd/test_e2e_ui.py
    python samples/Tests/DotNet/EndToEnd/test_arabic_dark.py
    python samples/Tests/DotNet/EndToEnd/test_regression_ui.py

Needs the .NET SDK (8 + 9), network access to nuget.org, and Visual Studio 2022 / Build Tools MSBuild for the
COM reference project.
