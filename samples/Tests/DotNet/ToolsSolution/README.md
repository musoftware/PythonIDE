# ToolsSolution - .NET tools sample (Test Explorer, analyzers, Code Cleanup, decompiler)

A small .NET 9 solution made with `dotnet new` for the "rest of Visual Studio 2022's .NET tooling" in RAD IDE
(docs/DOTNET.md, section *Tools*):

| Project | What it shows |
|---|---|
| `Calc` | the code under test (`Calculator`), `Patterns.cs` uses the regex **source generator** (`[GeneratedRegex]`), `Messy.cs` has unused usings, odd whitespace and CA1822 on purpose |
| `Calc.XTests` | xUnit: a `[Fact]`, a `[Theory]` with two rows and one **intentional failure** (`Add_IntentionalFailure`), coverlet for code coverage |
| `Calc.NTests` | NUnit: `[Test]`, `[TestCase]` data rows (`Add_Cases(1,1,2)` ...) |
| `Calc.MTests` | MSTest: `[TestMethod]`s |
| `.editorconfig` | `root = true`, indent settings, `dotnet_diagnostic.CA1822.severity = warning` |

Try it: open `ToolsSolution.sln` (File > Open), then

* **Test > Test Explorer** > Run All: Project > Namespace > Class > Test tree, durations, the failure message with a
  clickable stack trace (double-click the blue location), Run Failed, **Debug** a test (breakpoints work: netcoredbg).
* Solution Explorer > a project > **Dependencies > Analyzers**: analyzer assemblies, their rules with the effective
  severity (right-click > Set severity), source generators (right-click > Show Generated Files).
* **Analyze** menu: Run Code Analysis (Error List; right-click a row > Configure severity / Suppress), Code Cleanup
  (Ctrl+K, Ctrl+E), Configure Code Analysis (.editorconfig editor), Remove and Sort Usings (Ctrl+R, Ctrl+G),
  Go To Decompiled Definition (put the caret on `StringBuilder`).
* **Project > dotnet CLI**: restore / build / test / pack / publish / format / watch run / user-secrets / tools / workloads.

Never edit this folder in place in tests: they copy it to a temp folder (`../ToolsTests`).
