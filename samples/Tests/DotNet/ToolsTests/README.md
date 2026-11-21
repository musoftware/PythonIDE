# ToolsTests - checks of radide/dotnet/tools

Both scripts copy `../ToolsSolution` to a temp folder first (the sample is never changed).

* `test_tools_core.py` - no IDE window: vstest discovery (xUnit / NUnit rows / MSTest), group paths, `dotnet test`
  steps + TRX + live console results, escaped `--filter`, coverlet coverage, analyzer / rule / generator listing
  (AnalyzerInfo helper built against the SDK's Roslyn), generated files, `.editorconfig` read / write, Run Code
  Analysis diagnostics, Remove and Sort Usings (CS8019), `dotnet format whitespace`, ilspycmd decompile, type
  index + light-bulb fixes, dotnet CLI submenu.  `python samples/Tests/DotNet/ToolsTests/test_tools_core.py`
* `ui_test.py` - the IDE (qh.py harness, QSettings "RADIDE-TEST", screenshots with widget.grab): Analyze menu,
  Dependencies > Analyzers + Set severity, Show Generated Files, Test Explorer Run All / Run Failed / stack links /
  Debug with a breakpoint, Code Cleanup and usings in the editor, light bulb, decompiled tab, Error List menu,
  Configure Code Analysis dialog, Project menu.  `python samples/Tests/DotNet/ToolsTests/ui_test.py`

Needs the .NET SDK 8+ (9 used here), nuget.org for the first restore, `ilspycmd` and `netcoredbg` in
`%LOCALAPPDATA%\RADIDE\tools` for the decompiler / debugger checks (they are skipped when missing).
