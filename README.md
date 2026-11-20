# RAD IDE

A Visual Basic style RAD IDE for many languages - and for **several languages in one project**.

Run: `run.bat` (or `.venv\Scripts\python -m radide [project-folder]`).
Samples: `samples/HelloPolyglot` (Python + VB6 + Ring in one project), `HelloVB`, `HelloPython`, `HelloRing`,
`HelloJavaScript`, `HelloCSharp`, `HelloFortran`, `HelloC`, `HelloDart`, `HelloPerl`, `HelloSolution`,
`HelloPHPSite` (complete PHP + SQLite web site).
Test projects: `samples/Tests` (curated projects from the IDE's own test runs, by area: languages, solutions, web, mobile,
games, exe import, Blend, AI, debugger; `samples/Tests/All` holds every other test project - see `samples/Tests/README.md`).
`tools\make_samples.py` **replaces** HelloPython/HelloRing/HelloVB.

## Languages (19)

| Group | Languages | GUI | Debugger |
| --- | --- | --- | --- |
| Visual Basic | VB6 / BASIC (bundled interpreter, runs VB code as-is) | Tkinter | built in |
| Python | Tkinter, PySide6 | native | debugpy (DAP) |
| Ring | RingQt | native | ringvm_settrace agent |
| .NET / Java | C#, PowerShell, Java | GUI Bridge | - |
| Web & script | JavaScript, TypeScript (Node), PHP | GUI Bridge | - |
| Native | C, C++, Rust, Fortran, Go | GUI Bridge | - |
| Scripting | Lua, Ruby, Perl, Dart | GUI Bridge | - |

GUI Bridge languages get their forms drawn by the IDE and talk to it over stdin/stdout
(`radide/runtimes/bridge.py`, clients in `radide/runtimes/clients/<lang>/`, protocol in `docs/CONTRACTS.md`).
A compiler/interpreter must be installed for each language; File > New Project shows which ones are.
gcc/g++/gfortran/gdb (WinLibs) live in `%LOCALAPPDATA%\RADIDE\toolchains\mingw64`.

## Solutions, projects and References (Visual Studio style)

- A **Solution** (`<Name>.radsln`) holds several **projects**; each project has **one language** and is a
  *Windows Application* or a *Class Library* (New Project > Class Library, or right-click the solution > Add).
- **Add Reference** (right-click *References* in Solution Explorer): Projects / Packages / Browse tabs.
  The IDE then generates a wrapper **in the consumer's language** for every public function of the library
  (`MathLib.py (generated)`, `MathLib.ref.cs`, ...), so the code calls it natively with IntelliSense:
  Python `import MathLib; MathLib.Add(2, 3)`, C# `MathLib.Add(2, 3)`, VB6 `MathLib.Add(2, 3)`, ...
- Tested end to end: **15 x 15 language pairs** (C#, VB6, Ring, JavaScript, TypeScript, C, C++, Rust, Fortran,
  Perl, Dart, Java, PHP, PowerShell, Python) as library and as consumer. RAD Hub (`radide/runtimes/radhub.py`)
  is the hidden transport; Build Solution refreshes wrappers; Set as StartUp Project chooses what F5 runs.
- Sample: `samples/HelloSolution` (Python app + C# library + VB6 library).
- Lower level, still available: forms/modules of different languages inside one project and
  `radcall("Module.function", ...)`.

## Web sites (WebMatrix / Expression Web style)

- **New Project > Web**: PHP Web Site, HTML/CSS/JS Site, Node.js (Express). **App Gallery** templates include a
  complete **PHP + SQLite Data App** (register/login with password_hash, sessions, CSRF, PDO, products CRUD with
  search) - sample: `samples/HelloPHPSite`.
- **F5** starts the dev server (php -S / node / static) behind a front server with **live reload**; **Preview** dock
  (devices, rotate, open in browser) and **Requests** dock (method, path, status, time, size).
- Solution Explorer shows the site's **folder tree** (new/rename/delete/set start page/open in browser).
- **Design / Split / Code view** (GrapesJS): blocks, layers, CSS properties, devices; PHP blocks are preserved.
- **Databases** workspace: SQLite, MySQL, PostgreSQL - tables, editable data grid, schema, SQL window, CSV/SQL
  export/import, and **Adminer**.
- **Publish**: FTP / FTPS / SFTP / folder, incremental, dry run. **Reports**: SEO crawler (+ Lighthouse when npx is
  available). **SuperPreview**: side-by-side sizes, onion skin, installed browsers.
- **IntelliSense** for HTML, CSS/SCSS, JSON, PHP (intelephense), JS/TS, plus **Emmet** (`ul>li*3` + Tab).
- **Laravel** (New Project > PHP Web Site > Laravel App / Laravel API): composer create-project with the right PHP,
  SQLite or local MariaDB/PostgreSQL, F5 with Xdebug, **Laravel panel** (Artisan commands with argument forms,
  Routes, Tinker), **Blade** language, and IntelliSense read from the project as it changes: `route('`, `view('`,
  `config('`, `__('`, `env('`, model columns/relations after `->`, `Model::where('`, Blade `@directives`,
  `<x-components>` + props, view variables; F12 / Ctrl+click to the target. Sample: `samples/Tests/Web/Laravel_Blog`.

## Blend features (python-tk, python-qt forms)

**States** panel (MouseOver/Pressed/Disabled/Focused + custom states, `GoToState`), **Objects and Timeline**
(keyframe storyboards with `Begin()`/`Stop()`, AutoStart), **Data** panel (JSON/CSV sources bound to Text / Items /
Value, sample values at design time, `Refresh`).

## Layouts and AI

- **View > Layout** (or the VS | Code | Agent switch top-right): Visual Studio, VS Code (Activity Bar, Side Bar,
  Panel, Command Palette Ctrl+Shift+P, Quick Open Ctrl+P) or an Antigravity-style **Agent** layout.
- **AI** (Tools > Options > AI): free routes first - local models (Ollama, LM Studio), CLI agents signed in with
  your own account (Claude Code, Gemini CLI, Codex, Copilot, Qwen, opencode, Cursor), embedded web chats
  (ChatGPT, Gemini, Claude, DeepSeek ...); API keys optional. AI Chat with apply-as-diff, ghost-text completions,
  Ctrl+I edit, AI right-click actions, commit messages, Generate form, and the **Agent Manager** (tasks with
  approvals, diff review and undo).

## Mobile apps and games

- **Mobile**: Flutter (main) and Kivy. Phone/tablet frame in the designer, Material controls (AppBar,
  BottomNav, Card, ListView, ...), several screens with navigation, device selector (Windows, Chrome, Android
  emulators), F5 with hot reload, Build APK / App Bundle / Windows / Web, Dart debugger. Sample `samples/HelloMobile`.
- **Games**: pygame-ce and Godot. Scene designer with tilemap painting, sprites, sprite-sheet animations, assets
  and behaviours (platformer, top-down, collectibles, enemies); VB-style handlers (`Player_Collide`,
  `Scene_Update`). Sample `samples/HelloGame`; `samples/SkyHopper` (an endless "hop through the gates"
  game built entirely through the IDE: spawn templates, flap / scroll behaviours, parallax, best score
  with `SaveData`). Game > Export to Godot makes a Godot 4 project from a pygame game.

## Import a program from .exe

File > Import > Program (.exe / .dll) - for programs you own or may analyse: identifies the binary and recovers
forms and code: .NET WinForms (ILSpy) -> python-tk, PyInstaller -> Python, Java jars, Electron, VB6 forms, Win32
dialogs/menus from native programs (+ Ghidra decompile when installed, AI translation when configured). An
import report says what was recovered exactly and what is missing.

## Packages

Project > Manage Packages: NuGet (C#), pip (Python), npm (JS/TS), Maven Central (Java), cargo (Rust),
Composer (PHP), pub (Dart), RingPM (Ring), RubyGems, LuaRocks, CPAN, Go modules, PowerShell Gallery, vcpkg.

## Editor and IntelliSense

- **Monaco** (the VS Code editor, `radide/monaco_editor.py`, needs PyQt6-WebEngine): folding, minimap,
  multi-cursor, find/replace, Arabic/bidi, bracket colours. Falls back to the built-in editor otherwise
  (QSettings `editor/engine = builtin`).
- **Language servers (LSP, `radide/lsp.py`)** when installed: pylsp/pyright, typescript-language-server,
  csharp-ls, jdtls, rust-analyzer, clangd, gopls, intelephense, dart, lua-language-server, solargraph, fortls.
  Languages without a server use the plugin's IntelliSense (RingQt index, VB members, ...).
- Go to Definition (F12), Find in Files (Ctrl+Shift+F), Error List on save, TODO list, auto-save + recovery.

## Debugging

F5/Ctrl+F5, breakpoints (F9), **conditional breakpoints (Alt+F9)**, **Run to Cursor (Ctrl+F10)**,
**Break on Exceptions**, F10/F11/Shift+F11, Locals, Call Stack, **Watch**, Immediate, hover values.
Python uses **debugpy over DAP** (`radide/dap.py`); VB6 and Ring use the built-in agents.

## Designer

Toolbox with 30 controls (incl. TabControl, TreeView, ListView, DataGridView, DateTimePicker, StatusBar,
ToolStrip, file/colour/font/folder dialogs, ActiveX via PySide6 QAxWidget), Anchor/Dock, Lock Controls,
Tab Order view, Document Outline, menu editor, multi-select, align, undo/redo, right-click everywhere.

## Importing existing programs

File > Import: Python GUI programs (Tkinter / PySide6 / PyQt - runs them and reads the real windows) and
Visual Basic 6 projects (.vbp/.frm/.bas, cp1256 Arabic text, control arrays, menus, OCX placeholders).

## IDE shell

Tools > Options (font, **themes: System (follows Windows, live) / Light (VS 2005) / Blue (VS 2010) / Dark /
High Contrast** - the designed form always keeps the real light Windows look - grid, interpreters), integrated Terminal, Git panel, F1 help,
project templates (Windows, Dialog, Data Entry, Console), Build EXE (PyInstaller / ring2exe).

## Adding a language

Subclass `LanguagePlugin` (native GUI) or `BridgeLanguagePlugin` (GUI Bridge) in `radide/languages/<name>.py`
and set `PLUGIN = MyPlugin()`. See `docs/CONTRACTS.md` for the bridge, RAD Hub, package-manager and debug
protocols.

## Known limits

- No debugger yet for GUI Bridge languages (gdb/dlv DAP are available in `radide/dap.py` but not wired to
  bridge programs). Ring Immediate: runtime errors other than unknown variables stop the program.
- Lua, Ruby, Go are not installed on this machine, so their plugins are untested against real interpreters.
- VB6 interpreter: no Class modules, GoSub, or `Declare` API calls.
- Web: MySQL/PostgreSQL were tested only with mock drivers (no servers on this machine); no debugger for web sites
  yet (F5 runs the server); Firefox screenshots in SuperPreview untested (Firefox not installed).

## Git client

**Git** menu + the Git Changes window (`radide/features/git_full.py`, logic in `radide/git_ops.py`):
branches (new / switch / rename / delete, local + remote, track), Fetch / Pull / Push / Sync with a progress
bar and plain-language explanations of sign-in and network errors, merge and rebase with Continue / Abort,
a **3-way conflict resolver** (Incoming | Base | Current, take left / right / both, editable result, Accept
marks the file resolved), stashes, **commit graph** with branch lanes, **blame** (blame window + inline blame
in the editor), compare a file with any commit, tags, cherry-pick / revert / reset, amend, undo last commit,
.gitignore editor with templates, remotes and git settings, and a **GitHub** tab (pull requests / issues,
create and checkout a PR) through the GitHub CLI - downloaded on request into
`%LOCALAPPDATA%\RADIDE\tools\gh` if it is missing. Try it: `samples/Tests/Git/GitClient_Demo`.

## Reports (Crystal Reports style)

**Project > Add Report...** (wizard: data source, fields, group by, totals, chart, Arabic RTL - or blank) makes
`<Name>.rpt.json` and opens the **Report Designer**: report / page / group header and footer bands and detail;
items text (`{expressions}`), field, expression (`Sum('Amount')`, `Count()`, `Avg`, `Min`, `Max`,
`RunningSum`, `PageNumber`, `TotalPages`, `Today()` ...), line, box, image, Code 128 / EAN barcode, QR code and
bar / line / pie chart; data from an SQL query on a Databases connection (SQLite, MySQL, PostgreSQL), a CSV /
JSON file or a Data panel dataset, with parameters (`:Name`). The **Preview** tab pages, zooms, prints and exports
to PDF, HTML, CSV and Excel. Arabic and right-to-left text render correctly (mirrored layout optional).
The **ReportViewer** control (Toolbox) shows a report on python-tk / python-qt forms:
`ReportViewer1.Parameters["CustomerId"] = 3`, `Refresh()`, `SetData(rows)`, `Print()`, `ExportPdf(path)`;
the runtime `radreport.py` is copied into the project. Try it: `samples/Tests/Reports`.

## User controls, designer zoom and form localization

**Project > Add User Control...** creates a user control: a `.form` (`"kind": "usercontrol"`) designed like a form
(plain surface, no window caption) with its own code file. **Project > User Control Properties and Events...**
(also right-click on its designer) declares its properties (name, type, default, *maps to* an inner control
property such as `lblTitle.Text`, description) and its events. The Toolbox lists the project's user controls in a
**"<Project> Components"** group; they are placed on forms and inside other user controls (nested), their
properties appear in the Properties window (category Custom) and their events in the Events list. Code (python-tk,
python-qt): one class per user control in `<Name>_designer.py`, forms create
`self.Home = AddressBox(master, owner=self, name="Home")`; the user control raises `self.RaiseEvent("Changed")`
and the form handles `Home_Changed()`. Logic: `radide/usercontrols.py`, `radide/features/user_controls.py`.

**Designer zoom**: Ctrl+mouse wheel, View > Zoom or the zoom box in the status bar (25% - 400%) for forms, user
controls and phone frames (the game scene editor keeps its own zoom; the status box drives it too) -
`radide/designer_zoom.py`.

**Localization** (`radide/features/localization.py`): form properties **Localizable**, **Language**,
**RightToLeft**, **RightToLeftLayout**. Pick a Language to translate the form in the designer (Text / ToolTip /
Items / TabPages / Columns and user-control string properties go to that language's table; RightToLeftLayout
mirrors the design surface); **Format > Localization Strings...** edits all languages in one grid. Save writes
`<Form>.<lang>.resx.json`; the generated program picks the language from `RADIDE_LANG`, a `language.txt` next to
the program or the Windows UI language, mirrors the layout for Arabic and switches live with
`self.ApplyLanguage("fr")`. Try it: `samples/Tests/UserControls`, `samples/Tests/Localization`.

### Debugger: expandable Locals/Watch, Threads, hit counts, logpoints, Java/Go, Attach to Process

- **Locals and Watch are trees**: objects, lists, dicts, arrays, structs, VB Types/Collections expand (children
  are fetched when you open them) - debugpy, gdb, Delve, netcoredbg, js-debug (DAP `variablesReference`), the
  Python agent, the VB runtime and the Java debugger.
- **Debug > Breakpoint Settings...**: condition, hit count (= / multiple of / >=) and *log a message instead of
  stopping* (`total is {total}`) - logpoints and hit counts for every engine (Ring gets plain conditions).
- **Debug > Windows > Threads** (Ctrl+Alt+H): threads / goroutines; double-click shows that thread's stack and locals.
- **Java** (java-bridge): a built-in JDWP debugger (`radide/jdwp_engine.py`, only the JDK is needed).
  **Go** (go-bridge): Delve (`dlv dap`, build with `-N -l`); Debug > Install Delve builds it into
  `%LOCALAPPDATA%\RADIDE\tools\dlv`.
- **Debug > Attach to Process...** (Ctrl+Alt+P): Python (debugpy injects itself), native (gdb), Go (Delve),
  .NET (netcoredbg); Stop detaches and the program keeps running. Break All pauses a DAP session.
- Code: `radide/debug_extras.py`, `radide/features/debug_views.py`. Try it: `samples/Tests/Debugger/Debug_*_Expand`,
  `Debug_Java_JDWP`, `Debug_Go_Delve`, `Attach_Python`, `Attach_C_gdb`.

### Games: physics, particles, auto-tiling, Python -> GDScript

- **Physics (pymunk)**: scene inspector > *Physics (pymunk)* switches it on (gravity, collision tile layers
  become walls, joints: pivot / pin / spring / rope / motor); object inspector > *Physics body*: dynamic /
  static / kinematic, box / circle / poly (*Outline from picture*), mass, friction, elasticity, fixed
  rotation, sensor. Code: `ApplyImpulse(obj, ix, iy)`, `ApplyForce`, `SetVelocity`. Runtime:
  `radgame_physics.py` (copied next to radgame.py; `pip install pymunk`).
- **Particles**: *Add > Particle Editor...* (rate, lifetime, speed, angle / spread, gravity, colour and size
  over life, shape / texture, additive blend, burst, duration, live preview with presets fire, smoke,
  sparkle, explosion, rain, snow, trail, coin); *Add > Particle emitter* or the *Particles* section of any
  object; code `Emit("smoke", x, y)` / `Emit("trail", Player)` / `Burst("explosion", x, y, 40)` /
  `obj.emitting = False`. Runtime: `radgame_particles.py`.
- **Auto-tiling**: Tiles tab > *Terrain* + *Terrains...*: 16-tile (sides) and 47-tile blob terrain sets,
  a template tileset generator, then Paint / Rect / Fill / Erase choose edges and corners by themselves;
  `SetTerrain(layer, col, row, "grass")` at run time.
- **Export to Godot translates the Python handlers to GDScript** (`radide/games/gd_translate.py`, rules for
  the radgame API; the AI provider - when configured - for what the rules cannot do; the rest stays as
  `# TODO` comments). Physics bodies / joints, emitters and terrains are exported too (radgame_scene.gd).
- Code: `radide/games/physics.py`, `particles.py`, `autotile.py`, `gd_translate.py`, `runtime/radgame_physics.py`,
  `runtime/radgame_particles.py`. Try it: `samples/Tests/Games/Physics_Playground`, `Particles_Showcase`,
  `AutoTile_Island`, `SkyHopper_GodotExport` (`python tests/run_autopilot.py` plays the Godot export headless).

## IDE display language: English / العربية

- **Tools > Options > Environment > Language** (or **Tools > Language**): English or Arabic. The switch is live:
  menus, tool bars, docked windows, tabs, dialogs, message boxes and Qt's own buttons are translated, the IDE
  turns right-to-left, while code editors, the form designer, terminals and web views stay left-to-right.
  Switching back restores every English text. Help > RAD IDE Help shows `radide/features/help/index_ar.html`.
- How it works (`radide/i18n/__init__.py`): a catalog `radide/i18n/ar.json` keyed by the English text
  (`strings`, plus `patterns` such as `"Branch: {}"`), `tr(text)`, a translation pass when a widget is shown /
  an action is added, and translating setters. **Code keeps seeing English**: `QAction.text()`, `QMenu.title()`,
  `windowTitle()`, `tabText()` ... return the original English, so lookups like
  `a.text().replace("&", "") == "Tools"` and tests keep working; `i18n.shown(obj)` returns what is on screen.
  Property names, control type names and the user's own forms are never translated.
- New UI strings: `python tools/extract_ui_strings.py` (scans `radide/**/*.py` -> `radide/i18n/strings_en.json`),
  then `python tools/extract_ui_strings.py --missing ar` lists what `ar.json` still lacks.
  Test: `samples/Tests/I18n/ArabicUI`.

## Data binding to databases (Data Sources window)

**Data > Show Data Sources** (Shift+Alt+D), VB 2005 style: *Add New Data Source...* picks a connection of the
Databases workspace (SQLite, MySQL / MariaDB, PostgreSQL, or an ODBC connection string with pyodbc) and the tables /
views / a query. Drag a table onto a form for a **BindingNavigator** (first / previous / position / next / last /
add / delete / save) + **DataGridView**, or - right-click *Drop as Details* - a Label + TextBox / CheckBox per column;
drag a column for one field. The designer shows real rows. Properties (Data category): `DataSource`, `DataMember`
(column, or `Source.Column`), `DisplayMember` / `ValueMember` (ListBox / ComboBox lookups).
Generated code (python-tk, python-qt, vb-basic): `self.Customers.Fill()` / `Fill("City = ?", "Cairo")` / `Update()` /
`AddNew()` / `RemoveCurrent()` / `Position` / `MoveNext()` / `Value(col)` / `SetValue(col, v)` / `Search(text)` /
`SortBy(col)` / `HasChanges`, form `FillAll()` / `UpdateAll()`, parameterized INSERT / UPDATE / DELETE, two-way
bindings; VB code: `Customers.MoveNext`, `Customers.Fill "City = ?", "Cairo"`. Passwords are never stored in the
project (F5 passes the ones the IDE knows as `RADIDE_DB_<CONNECTION>_PASSWORD`). Code: `radide/databinding_sql.py`,
`radide/features/data_sources.py`. Samples: `samples/Tests/DataBinding`.

## Web: JavaScript debugging, front-end frameworks, REST Client, Database Diagram

- **Debug the page's JavaScript in the Preview**: F5 on a static, PHP, Node.js or Vite/Angular site attaches
  vscode-js-debug (`pwa-chrome` attach) to the IDE's own browser engine (QtWebEngine DevTools port on 127.0.0.1,
  limited to the site's URL); F9 in `.js` / `.jsx` / `.vue` / `.svelte` / `<script>` lines stops there (source
  maps), with Locals, Call Stack, Watch, Immediate, F10/F11. PHP and Node sites debug the server and the page in one
  session. Off switch: Tools > Options > Web (or `RADIDE_NO_JS_DEBUG=1`). Code: `radide/web_site/browser_debug.py`.
- **Site > New Front-end App** (also New Project > Web > Node.js): React, React + TypeScript, Vue, Svelte, vanilla
  (`npm create vite@latest`) and Angular (`ng new`; falls back to `@angular/cli@20` on older Node.js), then
  `npm install`. F5 runs the framework's dev server in the Preview (its own hot reload), **Site > Build Production**
  runs `npm run build` / `ng build`. Code: `radide/web_site/vite_templates.py`.
- **REST Client** (Tools > REST Client, Ctrl+Alt+K): method, URL, params, headers, body (JSON / form / raw / XML),
  Bearer / Basic auth, environments (`.vscode/settings.json` `rest-client.environmentVariables`, like VS Code),
  history, pretty JSON, time and size, Copy/Paste cURL; requests are saved in `.http` files (VS Code REST Client
  syntax: `###`, `@var = value`, `# @name`, `{{name.response.body.$.x}}`, `{{$guid}}` ...). In an `.http` file each
  request has a **Send Request** lens. Code: `radide/web_site/rest_client.py`.
- **Database Diagram** (Databases: right-click a connection, or the Diagram button): tables with columns, foreign
  keys as lines, Auto Layout, drag to create a relationship, New Table / Add Column / Delete - shown as SQL DDL and
  applied after OK (SQLite: safe table rebuild). Export PNG/SVG. Code: `radide/web_site/db_diagram.py`.
- Samples: `samples/Tests/Web/JsDebug_StaticSite`, `JsDebug_PhpSite`, `Frontend_React_Vite`, `Frontend_Vue_Vite`,
  `Frontend_Svelte_Vite`, `Frontend_Angular`, `RestClient_Requests`, `DbDiagram_Shop`.

## Testing, coverage, formatting and refactoring

- **Test Explorer** (Test > Test Explorer, Ctrl+E, T; VS Code layout: the flask "Testing" view): finds the tests of
  the active project by itself - Python **pytest / unittest** (the project's `.venv`, else the IDE's Python with the
  project on `PYTHONPATH`), **Jest / Vitest / node --test**, **go test**, **cargo test**, **dotnet test** (xUnit,
  NUnit, MSTest via TRX), **PHPUnit**, **dart / flutter test**, **JUnit 5** (Maven, or javac + the official console
  launcher downloaded once to `%LOCALAPPDATA%\RADIDE\tools\junit`), and simple conventions for **Ring**
  (`test_*.ring`, `func test_*`) and **VB** (`Test*.bas`, `Sub Test*()`, `AssertEqual`). Tree file > class/group >
  test with state and duration, Run All / Run Selected / Run Failed / Run tests in current file (Ctrl+R, T),
  search and state filter, failure message + output, double-click = go to the test line, **Debug** a Python test
  with debugpy (breakpoints in tests and code). Code: `radide/testing/`, `radide/features/test_explorer.py`.
- **Code coverage**: Run with Coverage (coverage.py for Python, `go test -coverprofile`, Jest/Flutter lcov) colours
  the editor gutter (green covered, red never run, amber branch not taken) and lists % per file.
- **Format Document** (Edit, Shift+Alt+F, Ctrl+K Ctrl+D) and **Format on Save**: ruff / black, Prettier (installed
  in `%LOCALAPPDATA%\RADIDE\lsp`), clang-format (C, C++, Java, C#), gofmt, rustfmt, dart format, PHP CS Fixer, or
  the language server; one Ctrl+Z undoes the whole format. Tools > Options > Formatting chooses per language.
  Code: `radide/features/formatting.py`, `radide/editkit.py`.
- **Refactor** (Edit > Refactor, editor right-click): **Rename (F2)** with a preview of every change in every file,
  **Quick Actions (Ctrl+.)** - quick fixes, refactorings, organize imports from the language server,
  **Extract Method / Variable** (pylsp-rope, typescript, rust-analyzer ...), **Find All References (Shift+F12)**
  dock. Code: `radide/features/refactor.py`.
- Samples: `samples/Tests/Testing/` (one project per framework, each with a test that fails on purpose).

## Publish / Create Installer (Build menu)

- **Build > Publish / Create Installer... (Ctrl+Alt+F5)** - one dialog (saved in the project's `publish.json`):
  name, version, publisher, icon, build kind (automatic: Python Tk/Qt via PyInstaller, VB6 via the bundled VB
  runtime, GUI Bridge languages, Ring, Flutter, or an already built folder), install for the current user (no
  admin) or all users, desktop / Start menu shortcuts, setup languages (English, Arabic, ...), license and
  read-me pages, file association, portable zip, optional code signing (signtool) and update check.
- **Publish** builds in the background (log in the Output window) and makes `<Program>-<version>-setup.exe`
  with **Inno Setup** in `<project>\Publish`. Inno Setup is downloaded once, portably, into
  `%LOCALAPPDATA%\RADIDE\tools\innosetup` when missing. The setup adds an uninstaller in Apps & features and
  supports the usual silent switches: `setup.exe /VERYSILENT /SUPPRESSMSGBOXES /CURRENTUSER [/DIR=...]`,
  `unins000.exe /VERYSILENT`.
- Code: `radide/deploy/build.py` (build), `radide/deploy/inno.py` (setup script + publish chain),
  `radide/features/installer.py` (menu + dialog).

## License

RAD IDE is free and open source under the **MIT License** - © 2026 Musoftware ([musoftwares.com](https://musoftwares.com)).
Anyone may use, copy, modify and redistribute it, provided the copyright notice crediting Musoftware (musoftwares.com) is kept in all copies. See `LICENSE`; bundled components keep their own licenses (`THIRD_PARTY_NOTICES.md`).

