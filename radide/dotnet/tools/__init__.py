"""The rest of Visual Studio 2022's .NET tooling (docs/DOTNET.md, section "Tools"):

* testing.py      Test Explorer adapter for xUnit / NUnit / MSTest (vstest discovery, live results, TRX, debug)
* analyzers.py    Dependencies > Analyzers: analyzer assemblies, rules + effective severities, source generators
* editorconfig.py .editorconfig read/write (severities, code style, whitespace) + editor settings
* cleanup.py      Code Cleanup (dotnet format), Sort and Remove Usings
* diagnostics.py  MSBuild diagnostics -> Error List (Run Code Analysis)
* quickfix.py     light-bulb quick actions: add using, install package, add project reference
* metadata.py     a small ECMA-335 reader (type names of assemblies) + type index
* cli.py          dotnet CLI items of the dynamic Project menu
* ui.py           everything Qt: hooks into vs_ui / Test Explorer / Error List / editor
"""
