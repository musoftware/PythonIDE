""".NET tooling like Visual Studio 2022 (docs/DOTNET.md, "Tools"): Test Explorer for xUnit / NUnit / MSTest
(discover, run, debug, live results), Dependencies > Analyzers with rule severities and source generators,
.editorconfig (editor settings + Configure Code Analysis), Code Cleanup (dotnet format), Remove and Sort Usings,
Run Code Analysis into the Error List (Configure severity / Suppress), light-bulb quick actions, decompiled
Go To Definition (ilspycmd) and the dotnet CLI submenu of the Project menu. The work is in radide/dotnet/tools."""
from __future__ import annotations


def install(win) -> None:
    from ..dotnet.tools import ui
    ui.install(win)
