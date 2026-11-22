# Quick Actions and quick fixes (Alt+Enter / Ctrl+.)

Put the caret on a name with a red squiggle (or any name) and open **Quick Actions**. You get the fixes for missing
`using` / `import` lines and missing packages, the RAD helpers, "Create method", and the language server's own
code actions, all in one list.

## Opening Quick Actions

| How | Notes |
|---|---|
| **Alt+Enter** | Works in every language. It is the ReSharper / Rider key, and Visual Studio's "Show potential fixes". While Monaco's find widget is open, Alt+Enter keeps its Monaco meaning, "Select All Occurrences of Find Match". |
| **Ctrl+.** | The Visual Studio default. |
| **Light bulb** | Shown in the glyph margin of the caret line when a fix is available there. It appears about 350 ms after the caret stops moving. Click it to open the menu. It is not shown on a line that has a breakpoint or the debugger's current-line arrow, because those use the same margin. To turn it off, set `editor/lightBulb` to `false`. |
| **Right-click > Quick Actions and Refactorings...** | Available in the Monaco editor and in the built-in editor. |
| **Edit > Refactor > Quick Actions and Refactorings...** | |

Using the menu:

* It works like Visual Studio's. Entries are grouped under **Quick Fixes**, **Refactorings** and **Source Actions**, and the preferred fix is shown in bold and selected when the menu opens. Use the arrow keys to move and Enter to apply.
* When you hover over or arrow to an entry, the lines it changes appear next to the menu, with `-` for the old line and `+` for the new one. For an install entry, the preview shows the command instead (`pip install PyYAML` and the interpreter it uses, for example).
* The edits from one fix are a single undo step.
* When a fix resolves a squiggle, the squiggle disappears right away. The language server checks the file again afterwards.
* Fixes that cannot work are shown greyed out, and the tool tip explains why. For example, `using System.Windows.Forms;` is greyed out in a RAD C# form.

### Key conflicts (checked)

* **Monaco's find widget** uses Alt+Enter for "Select All Occurrences of Find Match". The new binding has the condition `!findWidgetVisible`, so it does not apply while the find widget is open.
* **The notebook editor** (`radide/notebook/notebook.html`) uses Alt+Enter for "Run Cell and Insert Below". It is a separate Monaco page and is not affected.
* **Solution Explorer > References > Properties** uses Alt+Enter as a shortcut that works only inside that context menu. It does not conflict.
* **IDE menus and the VS / VS Code / Emacs keymaps** (`radide/features/editor_extras.py`) have no global Alt+Enter. In Vim mode, Alt+Enter still opens Quick Actions.

## Built-in providers (they work without a language server)

These live in `radide/quickfix/`. They are merged with the language server's `textDocument/codeAction` answer. When the server offers an action with the same title, or with an edit that gives the same text, the action is shown once and the server's copy is used.

| Language | Fixes |
|---|---|
| C# (`.csproj` / `.sln` projects, loose files) | **Missing `using X;`:** the namespace comes from the type index of the assemblies the project compiles against. The index is read from the installed .NET SDK's reference assemblies. Without an SDK, a static table of common BCL, WinForms, WPF, LINQ, IO, Net, Threading, Text and Collections types is used.<br>**Fully qualified name.**<br>**Add reference to project Y:** when the type is declared in another project of the solution.<br>**Install package Z:** when the type belongs to a well-known NuGet package. The install uses `dotnet add package` and shows progress.<br>**Search NuGet.org for 'T'...:** opens the NuGet Package Manager. |
| RAD C# forms (GUI Bridge) | **`MessageBox.Show("Hi")` → `MsgBox("Hi")`:** also `Interaction.InputBox` → `InputBox` and `Application.Exit` → `End()`. The RAD helpers come from `Rad.cs` (`global using static Rad`).<br>**`using System.Windows.Forms;` greyed out:** the IDE draws the form and the program runs as a console process, so WinForms and WPF are not referenced. The tool tip says this.<br>**Case fix:** `msgbox` → `MsgBox`.<br>**Missing `using`:** for BCL types. `System`, `System.Collections.Generic`, `System.IO`, `System.Linq` and the other implicit usings of `RadApp.csproj` are never suggested.<br>**NuGet packages:** they go into `_build/csharp/RadApp.csproj`, the project's NuGet manifest (the same file Project > Packages uses). Well-known types are offered directly. For other types, the IDE searches nuget.org (results are cached) and lists the packages to pick from. |
| VB.NET | The same fixes as C#, with `Imports X`. |
| Python | **Missing import:** common aliases (`np` → `import numpy as np`, `pd`, `plt` ...), standard-library names (`Path` → `from pathlib import Path`, `defaultdict` ...), standard modules (`import json`), modules installed in the interpreter, and top-level names from the project's own files (`from helpers import greet`). An existing one-line `from m import ...` is extended instead of adding a new line.<br>**Unresolved import → "Install 'PyYAML' with pip":** the import name is mapped to its distribution (`cv2` → `opencv-python`, `PIL` → `Pillow`, `yaml` → `PyYAML`, `sklearn` → `scikit-learn`, `bs4` → `beautifulsoup4` ...). It installs into the interpreter Run uses (the project's `.venv` first), shows progress, and adds the package to `requirements.txt` when the project has one. |
| JavaScript / TypeScript | **Package missing from `node_modules` → `npm install <pkg>`:** in the folder of the nearest `package.json`.<br>**TypeScript type declarations:** also offers `@types/<pkg>` as a dev dependency. For TS7016 (no declaration file), only `@types/<pkg>` is offered.<br>**Missing import:** for a name exported by another file of the project, adds `import { greet } from './util';` (`require` in CommonJS files). |
| Rust | **Missing `use`:** for std items (`HashMap` → `use std::collections::HashMap;` ...).<br>**Crate missing from `Cargo.toml`:** `cargo add <crate>`. |
| Go | **Missing standard-library import:** added to the import block (`strings`, `encoding/json` as `json` ...).<br>**Import path missing from `go.mod`:** `go get <path>`. |
| Java | **Missing `import`:** for common JDK classes (`java.util`, `java.io`, `java.nio.file`, `java.time`, streams, concurrency, Swing ...). Also offers `import pkg.*;`. |
| PHP | **`use` statement:** for a class declared in the project.<br>**Namespace with no autoload → `composer require <pkg>`:** for well-known packages and `symfony/<component>`. |
| C#, VB.NET, Python | **Create method 'X' / Create function 'X':** for a call to a function the file does not define. The arguments come from the call. When the line has no diagnostic, it is listed as a refactoring and the light bulb does not show it. |

Every install (pip, npm, cargo, go get, composer, dotnet add package) runs in a worker thread through
`radide/progress.py`. It shows as a status-bar task with Cancel, and the tool's output goes to the Output window.

## For developers

* Write a provider as `fn(ctx: quickfix.Context) -> list[quickfix.Action]` and register it with `quickfix.register(("mylang",), fn)`.
* `ctx` contains:
  * the text, the path and the language
  * the caret line and column, and the word under the caret with its range
  * the diagnostics on the caret line, so `ctx.diag_names()` gives the unresolved names
  * the project folder
  * `cheap`: True when the light bulb is asking. In that case, avoid network access, subprocesses and big project scans.
* An `Action` has `edits` (`{path: [[l1, c1, l2, c2, text]]}`) and/or `run(win, ed)`. It can also have `preferred`, a `disabled` reason, a `detail` preview text, and `fixes` (the diagnostics it resolves).
* The older `refactor.EXTRA_QUICK_ACTIONS` callables, which return `(title, callback)`, still work. Entries whose title matches a built-in one are dropped.
* Tests:
  * `samples/Tests/Editor/test_quickfix_providers.py` (fast): the registry and every provider.
  * `samples/Tests/Editor/test_quick_fixes.py` (full): the real IDE. Run it with `--network` to also do a real pip install.
