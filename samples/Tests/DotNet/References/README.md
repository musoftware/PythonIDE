# References (Reference Manager, reference properties, Object Browser)

A small Visual Studio solution for the references features (`radide/dotnet/refs/`, docs/DOTNET.md "References").

| Project | What it is |
|---|---|
| `MathKit` | Class library (net9.0 + netstandard2.0, XML documentation on) - the DLL that gets referenced with Browse |
| `SdkConsumer` | SDK-style console app (net9.0). `Program.cs` calls MathKit when `MATHKIT` is defined |
| `LegacyConsumer` | Old-style .NET Framework 4.8 console app. Uses System.Numerics (Framework), MathKit (Browse), Microsoft Scripting Runtime (COM) and `..\Common\SharedHelper.cs` (Add As Link) behind `NUMERICS` / `MATHKIT` / `SCRIPTING` / `LINKED` |
| `Common/SharedHelper.cs` | A file outside every project, for Add > Existing Item > **Add As Link** |

## Try it in the IDE

1. Build MathKit once (`dotnet build MathKit`), then File > Open Project > `References.sln`.
2. Right-click **SdkConsumer > Dependencies > Add Assembly Reference...** - the Reference Manager opens on
   Assemblies > Framework (the SDK note + FrameworkReference choices). Press **Browse...**, pick
   `MathKit\bin\Debug\net9.0\MathKit.dll`, OK. Dependencies > Assemblies > MathKit appears.
3. Click MathKit: the Properties window shows *MathKit Reference Properties* (Path, Version, Copy Local, Specific
   Version, Aliases...). Change Copy Local to False: the project file gets `<Private>False</Private>`.
4. Right-click MathKit > **Open in Object Browser**: MathKit > MathKit > Calculator, its members and their XML
   documentation; F12 on a type opens it decompiled (ilspycmd) or as metadata.
5. On **LegacyConsumer**: Add Reference > Assemblies > Framework (search `numerics`), COM > Type Libraries
   (*Microsoft Scripting Runtime*), Projects > Solution (MathKit). Add > Existing Item... > select
   `Common\SharedHelper.cs` > **Add As Link**. Building LegacyConsumer needs Visual Studio's MSBuild (COM).

## Automated tests

* `python samples/Tests/DotNet/References/tests/test_refs_core.py` - project-file edits + real builds (temp copy).
* `python samples/Tests/DotNet/References/tests/test_refs_ui.py` - the same through the IDE (qh.py harness).
