# RAD IDE - shared contracts (read before changing code)

Several agents work on this codebase **at the same time**. These contracts let
them build pieces that fit together without waiting for each other.

## 0. Working rules (all agents)

- Python 3.12, PyQt6. Run things with `.venv\Scripts\python.exe` from the repo root.
- **Never rewrite a whole file you do not own** (no `Write` over an existing shared file).
  Use small targeted `Edit`s. If an `Edit` fails because the file changed, re-`Read` and retry.
- New IDE features go in **new modules under `radide/features/`** exposing `install(win)`;
  they are loaded automatically (see `radide/features/__init__.py`). `win` is `radide.app.MainWindow`.
  Useful members: `win.project`, `win.plugin`, `win.docs`, `win.designers`, `win.codeviews`, `win.modviews`,
  `win.session` (running program, `radide.debugger.Session`), `win.log(text)`, `win.menuBar()`,
  `win._current_code()` (CodeView/ModuleView with `.editor`), `win._current_designer()`,
  `win._editor_for_file(name)`, `win.save_all()`, `win.open_code(form)`, `win.open_module(file)`,
  `win.dock_*` docks, `win.statusBar()`. Add docks with `win.addDockWidget` and tabify with `win.dock_output`.
- Keep `.venv\Scripts\python.exe -m pyflakes radide tools` clean.
- Tests: write them in **your own scratch folder** (given in your task). Use `QT_QPA_PLATFORM=offscreen` for Qt UI
  tests. Never leave GUI windows or processes running; never kill processes you did not start.
- **Do not run `tools/make_samples.py`** and do not touch `samples/HelloPython|HelloRing|HelloVB`.
  You may create a new sample folder `samples/Hello<YourLanguage>` (unique name).
- Do not edit `docs/CONTRACTS.md` (the coordinator owns it). Do not edit `README.md`.
- Installing toolchains: allowed only where your task says so, silently (`winget install --silent
  --accept-package-agreements --accept-source-agreements ...`). If an install fails or needs admin, skip and report.

## 1. GUI Bridge protocol (existing - `radide/runtimes/bridge.py`)

host -> program: `EVENT <object> <event> [args]` (args for mouse/key: `X Y Button KeyCode KeyChar`), `QUIT`.
program -> host (one per line, flush after each):
`SET <obj> <prop> <value>`, `GET <obj> <prop>` (host answers one line), `CALL <obj> <method> [arg\targ...]`
(answers one line), `MSGBOX <text>` (answers `1`), `INPUT <prompt>` (answers text), `SHOW <form>`, `HIDE <form>`,
`DONE` (event finished - **must** be sent after every EVENT), `END` (quit). Other lines = program output.
`<obj>` = control name, form name, or `Form.Control`. Property/method names are VB-style and case-insensitive:
`Caption Text Value Enabled Visible Left Top Width Height BackColor ForeColor ListIndex ListCount Interval` and
`AddItem RemoveItem Clear List SetFocus Move` (implemented by `VBControl` in `radide/runtimes/vbrun.py`).
Handler names are neutral: `<Control>_<Event>` (`cmdGo_Click`, `txtA_TextChanged`, `Form1_Load`), menu items
`<ItemName>_Click`. The bridge only forwards events whose handler name is listed in env `RAD_HANDLERS`.
Base class for such languages: `radide/languages/bridgebase.py` (`BridgeLanguagePlugin`).
Client libraries live in `radide/runtimes/clients/<lang>/` and are copied into the project when it runs.

## 2. Multi-language projects + RAD Hub (owner: polyglot-core)

- `project.radproj` gains `"form_languages": {"Form2": "ring-qt"}`; forms without an entry use the project
  `"language"`. Modules get their language from their file extension via
  `radide.languages.plugin_for_file(filename, default_id)` (to be added by polyglot-core; `.py` -> the project's
  python plugin, `.ring` -> ring-qt, `.bas` -> vb-basic, `.js` -> javascript, ...).
- Cross-language calls: `radcall("<Module>.<function>", args...)` returns the result. Values are JSON
  (number, string, bool, null, list, object). Available in every language that has a client.
- The IDE starts **RAD Hub** (`radide/runtimes/radhub.py`) when a program runs; env `RAD_HUB=127.0.0.1:<port>`,
  `RAD_PROJECT=<project folder>` are given to the program and to every worker.
- Client -> hub (TCP, UTF-8 JSON, one object per line):
  `{"id": 1, "call": "Helpers.add", "args": [2, 3]}` -> `{"id": 1, "result": 5}` or `{"id": 1, "error": "msg"}`.
- Hub -> worker (worker's stdin/stdout, JSON lines): `{"id": 7, "func": "add", "args": [2, 3]}` ->
  `{"id": 7, "result": 5}` / `{"id": 7, "error": "..."}`. Workers write logs to **stderr only**.
  Hub finds `<Module>` by file stem in the project folder, picks the plugin by extension and starts
  `plugin.worker_command(folder, module_file)` once (keeps it alive), cwd = project folder.
- Each language provides: `worker_command()` in its plugin + a worker script/template + a `radcall` client
  (in its client folder). Document the call syntax in the plugin's `module_template()` comment.

## 3. Package managers (owner of the UI: ide-shell; each language agent fills its plugin)

`radide.languages.base.PackageManager(name, tool, list_cmd, search_cmd, install_cmd, uninstall_cmd, init_cmd,
manifest, search_url)` - argv lists with `{name}`, `{query}`, `{version}` placeholders, run in the project folder.
Set `package_manager = PackageManager(...)` on your plugin class. Examples: Python pip
(`[python, -m, pip, install, {name}]`, manifest `requirements.txt`), C# NuGet (`dotnet add package {name}`),
JavaScript npm, Java Maven/Gradle (or a `libs/` jar download), Rust cargo (`cargo add`), PHP composer,
Dart `dart pub add`, Ring `ringpm install`, Ruby gem, Lua luarocks, Go `go get`, PowerShell `Install-Module`.

## 4. New controls (owners: controls-tk for catalogue/designer/Tk/VB runtime, controls-qt-ring for Qt & Ring)

Add to `radide/controls.py` exactly these names (props in brackets; all also have the common props):

| Control | Kind | Specific props | Specific events (first = default) |
|---|---|---|---|
| TabControl | container | `TabPages` (list "A;B;C"), `SelectedIndex` int | SelectedIndexChanged |
| TreeView | visual | `Nodes` (list, `/` = path: "Root;Root/Child;Root/Child2") | SelectedIndexChanged, DoubleClick |
| ListView | visual | `Columns` (list), `Items` (list of rows; cells separated by `|`), `View` enum Details/List | SelectedIndexChanged, DoubleClick |
| DataGridView | visual | `Columns` (list), `Rows` (list of rows; cells `|`), `ReadOnly` bool | SelectedIndexChanged, CellChanged |
| DateTimePicker | visual | `Value` str `YYYY-MM-DD`, `Format` enum Short/Long/Time | ValueChanged |
| LinkLabel | visual | `Text`, `LinkColor` color | Click |
| StatusBar | visual | `Text`; default Dock=Bottom, Height 22 | Click |
| ToolStrip | nonvisual (tray, like MenuStrip) | `Items` (menu kind, one level) - drawn under the menu | `<ItemName>_Click` |
| OpenFileDialog / SaveFileDialog | nonvisual | `Title`, `Filter` ("Text files|*.txt|All|*.*"), `FileName`, `InitialDirectory` | - |
| ColorDialog / FontDialog / FolderBrowserDialog | nonvisual | `Color` / `FontName`,`FontSize` / `SelectedPath` | - |
| ActiveX | visual | `ProgID` str (e.g. "Shell.Explorer.2", "MSCAL.Calendar") | Click |

Children of a TabControl get the hidden prop `TabPage` (int, page index). Dialog components expose a method
`ShowDialog()` returning `"OK"` or `"Cancel"` and fill their properties (`FileName`, `Color`, ...).
Common props added to **all visual controls**: `Anchor` (str, default `"Top, Left"`, any of Top/Bottom/Left/Right)
and `Dock` (enum `None/Top/Bottom/Left/Right/Fill`). Generators must honour them when the window is resized.
Designer must hide TabControl children that are not on the selected page.

## 5. Debugger protocol extensions (owner: debugger)

Breakpoint spec gains an optional condition: env `RADDBG_BP="file|line|cond;..."` and command
`b file|line|cond` (cond = expression in the program's language; stop only when true). New commands:
`x on|off` (break on uncaught exception / runtime error), `t file|line` (run to cursor = temporary breakpoint),
`w <expr>` (evaluate a watch expression, reply `@@RADDBG@@watch|<expr>|<value>`). Agents of each runtime
(pyagent.py, raddbg.ring, vbrun Debugger) implement what they can; unknown commands must be ignored.

## 6. File ownership (big changes) - others: targeted Edits only

| Owner | Files |
|---|---|
| polyglot-core | app.py, model.py, workspace.py, dialogs.py, languages/__init__.py, runtimes/radhub.py, runtimes/clients/python, ring, vb workers |
| lang-js-php | languages/javascript.py, typescript.py, php_bridge.py, runtimes/clients/js, php |
| lang-jvm-dotnet | languages/java_bridge.py, csharp_bridge.py, powershell_bridge.py, runtimes/clients/java, csharp, powershell |
| lang-native | languages/fortran_bridge.py, c_bridge.py, cpp_bridge.py, rust_bridge.py, pascal_bridge.py, runtimes/radgui.f90, runtimes/clients/c, rust, pascal |
| lang-scripting | languages/lua_bridge.py, ruby_bridge.py, perl_bridge.py, go_bridge.py, dart_bridge.py, runtimes/clients/lua, ruby, perl, go, dart |
| debugger | debugger.py, debug/pyagent.py, debug/raddbg.ring, features/debugtools.py (+ Debugger class in runtimes/vbrun.py) |
| editor | editor.py, features/outline.py, features/snippets.py, features/bookmarks.py |
| controls-tk | controls.py, preview.py, toolbox.py, designer.py, document.py, properties.py, menu_editor.py, languages/python_tk.py, runtimes/vbrun.py (controls part), languages/vb_basic.py |
| controls-qt-ring | languages/python_qt.py, languages/ring_qt.py |
| ide-shell | features/terminal.py, features/git_panel.py, features/settings.py, features/packages.py, features/help.py, features/templates.py, tools.py |

## 7. Solutions, projects and References (Visual Studio model) - round 2

**User request (verbatim intent):** "The IDE itself supports the other languages, and the integration between them
is like *References* in Visual Studio." So: a **Solution** contains several **Projects**; **each project has one
language**; a project uses another project through **Add Reference**, and then calls its public functions as
*native code of its own language* (with IntelliSense) - no hand-written `radcall`. RAD Hub stays the hidden
transport.

### 7.1 Files
- `<Name>.radsln` (JSON) in the solution folder:
  `{"name": "MySolution", "projects": [{"name": "App", "path": "App"}, {"name": "MathLib", "path": "MathLib"}],
  "startup": "App"}` - `path` is relative to the .radsln folder.
- Each project folder keeps `project.radproj` and gains `"kind": "app" | "library"` (default "app") and
  `"references": ["MathLib", ...]` (names of other projects in the same solution).
- Opening a bare `project.radproj` (no .radsln) = an implicit solution with that one project (old projects keep
  working unchanged). Per-form languages (`form_languages`) stay supported but the UI promotes projects+references.

### 7.2 Engine API (owner: solution-core) - `radide/solution.py`, `radide/references.py`
```python
@dataclass
class ExportedFunction:
    name: str                 # function name as written in the library
    params: list[str]         # parameter names (no types needed)
    module: str               # file stem that defines it (RAD Hub module name)
    doc: str = ""             # first doc line / comment, shown in IntelliSense
    kind: str = "function"    # "function" | "sub" (no return value)
```
- Library side (every plugin): `plugin.exported_functions(path: Path, text: str) -> list[ExportedFunction]`
  - public top-level functions only (skip `_private`, event handlers `X_Event`, and non-exported per language rules).
- Consumer side (every plugin): `plugin.reference_proxy(lib: str, functions: list[ExportedFunction]) ->
  dict[str, str]` - files to write into the **consumer** project folder so that code can call
  `lib.function(args)` naturally (e.g. Python `import MathLib; MathLib.Add(2, 3)`, C# `MathLib.Add(2, 3)`,
  JS `const MathLib = require('./MathLib.ref'); MathLib.Add(2, 3)`, Ring `MathLib_Add(2, 3)` or an object, VB
  `MathLib.Add 2, 3` / `MathLib_Add(2, 3)`). Each proxy function forwards to that language's radcall client with
  `"<module>.<name>"`. Mark generated files with an "AUTO-GENERATED by RAD IDE (reference to <lib>)" header and
  name them so they are recognisable (`<Lib>.<ext>` or `<Lib>.ref.<ext>` - choose what the language's import
  rules need). Return `{}` if the language cannot consume references yet.
- `references.update_proxies(solution, project)` regenerates proxies for all references of a project (called on
  Add Reference, on save of a library, and before Run/Build). `references.exports_of(project)` scans all code files
  of a library project with its plugin.
- RAD Hub: `RadHub(folder, ..., search_folders=[...])` also looks for modules in referenced project folders
  (consumer first, then references in order, transitively); env `RAD_PROJECT_PATH` (os.pathsep-joined folders) is
  passed to programs and workers; `worker_command(folder_of_module, filename)` uses the module's own folder.

### 7.3 UI (owner: solution-ui)
Solution Explorer: `Solution 'X' (N projects)` > projects (startup in bold) > `References` node (each reference +
right-click Remove; right-click References > Add Reference...) > forms/modules. Right-click solution: Add > New
Project / Existing Project, Set Startup Project, Build Solution, Properties. Right-click project: Set as StartUp
Project, Add > Windows Form / Module / Reference, Manage Packages, Remove from solution, Open folder, Properties.
**Add Reference dialog** with tabs: Projects (checkbox list of other projects + their language), Packages (opens
the package manager), Browse (add an existing project folder to the solution and reference it). New Project
dialog: "Create new solution" / "Add to current solution" choice, solution name; template **Class Library**
(no form, one module with an example public function) for every language. Run/Debug runs the startup project;
before running, proxies are refreshed and libraries that need building (C#, Java, C, Rust, ...) are built by
their workers. Editing works per project (each code file uses its own project's plugin).

### 7.4 Round-2 ownership
| Owner | Files |
|---|---|
| solution-core | radide/solution.py (new), radide/references.py (new), radide/model.py, radide/runtimes/radhub.py, radide/workspace.py, radide/languages/base.py (default exported_functions/reference_proxy = []/{}) |
| solution-ui | radide/app.py, radide/dialogs.py, radide/features/solution_ui.py (new), radide/features/templates.py (Class Library template) |
| refs-python-ring-vb | python_tk.py / python_qt.py / ring_qt.py / vb_basic.py: exported_functions + reference_proxy (+ VB/Ring/Python radcall client tweaks in runtimes/clients/python|ring|vb, runtimes/vbinterp.py) |
| refs-js-php | javascript.py, typescript.py, php_bridge.py (+ their clients) |
| refs-dotnet-java | csharp_bridge.py, java_bridge.py, powershell_bridge.py (+ clients) |
| refs-native | c_bridge.py, cpp_bridge.py, rust_bridge.py, fortran_bridge.py, go_bridge.py (+ clients, radgui.f90) |
| refs-scripting | lua_bridge.py, ruby_bridge.py, perl_bridge.py, dart_bridge.py (+ clients) |
