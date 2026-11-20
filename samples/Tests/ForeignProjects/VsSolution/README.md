# VsSolution - a Visual Studio solution opened in place

Created with the real tools (`dotnet new sln`, `dotnet new winforms` (C# and VB), `dotnet new classlib`
(C# and F#), `dotnet new console`, `dotnet sln add --solution-folder Libraries`, `dotnet add reference`,
`dotnet sln migrate` for the `.slnx` copy). .NET 9 SDK-style projects.

| Project | Language | Kind | Notes |
|---|---|---|---|
| WinApp | C# | WinForms (WinExe) | Form1.cs + Form1.Designer.cs + Form1.resx, `Properties/AppInfo.cs`, references MathLib |
| VbWinApp | VB.NET | WinForms (WinExe) | Form1.vb + Form1.Designer.vb, `StartupObject` |
| ConsoleApp | C# | console (Exe) | references MathLib, prints a loop (good for breakpoints) |
| MathLib | C# | class library | in solution folder *Libraries* |
| FsLib | F# | class library | in solution folder *Libraries*, explicit `<Compile>` order |

Both `VsSolution.sln` (classic text format) and `VsSolution.slnx` (XML format) describe the same projects.

## What to try in RAD IDE

1. **File > Open Project/Solution** > `VsSolution.sln` (or `.slnx`, a `.csproj`, or this folder). Nothing is
   written into the folder: no `project.radproj`, no `.radsln` (IDE state goes to
   `%APPDATA%\RADIDE\foreign\VsSolution.sln-<hash>`).
2. Solution Explorer shows the solution folder, Dependencies (Frameworks / Packages / Projects / Assemblies),
   folders, and `Form1.cs` with `Form1.Designer.cs` and `Form1.resx` nested under it. Double-click `Form1.cs`
   for the designer; right-click > View Code.
3. Toolbar combos: **Debug/Release** and **Any CPU/x64/x86** (the solution configurations).
4. Right-click ConsoleApp > **Set as StartUp Project**, put a breakpoint in `MathLib/Calculator.cs`
   (`return sum;`), press **F5**: `dotnet build` then netcoredbg stops in the other project's file.
5. Right-click a project > **Add > New Item** (Class, Windows Form, User Control, Module ...),
   **Add > Project Reference**, **Manage NuGet Packages** (`dotnet add package`), **Properties**.
   SDK-style C#/VB projects glob their files, so adding a class does not touch the `.csproj`; F# gets an
   ordered `<Compile Include>`.
6. Open + save without changes leaves every file byte-identical; edits keep the BOM, CRLF and formatting.

Build outputs (`bin/`, `obj/`) are not part of the sample.
