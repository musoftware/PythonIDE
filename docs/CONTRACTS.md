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
`ESC <command>` = the same command with `\\` `\n` `\r` escaped in its values (multi-line text; the C/C++, C#,
Java, Go and Rust clients always use it) - its answer is escaped the same way; answers to commands
without `ESC` are kept on one line (newlines -> spaces). `CALL <Form> ShowDialog` shows the form modally for the
user but answers at once (handle the result in the dialog's OK / Cancel handlers).
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
manifest, search_url, env)` - argv lists with `{name}`, `{query}`, `{version}` placeholders, run in the project folder
(`env`: optional extra environment variables for every command, e.g. LuaRocks' `LUAROCKS_CONFIG`, RubyGems'
`GEM_HOME`=`vendor/gems` so gems go into the project).
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

## 8. Web workspace (WebMatrix + Expression Web) and Expression Blend features - round 3

**User request:** the user loved Microsoft **WebMatrix** and **Microsoft Expression** (Web, Blend) and asked to
"build everything that is missing" compared with them, including "a complete project in PHP". RAD IDE so far
only had desktop forms; this round adds real **web site** development plus Blend-style visual states/animation.

### 8.1 Web Site projects (owner: web-core)
- New plugins (each `LanguagePlugin`, `kind="website"` projects): `php-web` ("PHP Web Site"), `static-web`
  ("HTML / CSS / JavaScript Site"), `node-web` ("Node.js Web Site (Express)"). File: `radide/languages/<id>.py`.
- `project.radproj`: `"kind": "website"`, `"language": "<plugin id>"`, `"web": {"root": ".", "start": "index.php",
  "port": 0}` (0 = choose a free port). A website project has **no forms**; its files are the whole folder tree.
- Dev server: `radide/web_site/server.py` `DevServer(project_folder, plugin)` with `start() -> url`, `stop()`,
  `url`, Qt signal `request(dict)` (method, path, status, ms, size) parsed from the server log
  (`php -S 127.0.0.1:<port> -t <root>` for PHP, a Python static server for static-web, `node <start>` for node-web
  with PORT env). Live reload: after a save the preview reloads.
- IDE (minimal hooks in app.py / solution_ui, rest in `radide/features/web_workspace.py`):
  Solution Explorer shows the **folder tree** of website projects (folders, files, right-click New File / New
  Folder / Rename / Delete / Open in Browser / Open in Design View); `win.open_file(path)` opens any file in a
  Monaco tab (language by extension); **Run (F5/Ctrl+F5)** of a website starts the DevServer and shows the
  **Preview dock** (`win.web_preview`, QWebEngineView with address bar, back/forward/reload, device-size combo,
  "Open in external browser"); **Requests dock** lists the server requests (WebMatrix "Requests" view);
  Stop stops the server. A web project can be a solution project like any other.
- New Project dialog: a "Web" group with PHP Web Site / HTML Site / Node.js Site and their templates (see 8.5).
- **PHP version per site** (round 6, `radide/web_site/php_toolchain.py` + `radide/features/php_tools.py`):
  `"web": {"php": "auto" | "8.4" | "8.4.28" | "<path to php.exe>"}` - "auto" = newest installed PHP that satisfies
  composer.json `require.php`; missing = Tools > Options interpreter, else auto. Site Settings has a "PHP version"
  row. Installs are detected in `%LOCALAPPDATA%\RADIDE\toolchains\php\<series>` (official windows.php.net NTS
  x64 zips, SHA256 verified, generated php.ini with extension_dir + Laravel/CodeIgniter extensions),
  `C:\tools\php*`, PATH, XAMPP/Laragon/WAMP/Scoop - the real version is read from each php.exe.
  `web_workspace.server_interpreter(win, plugin, project)` resolves it for the dev server and the PHP debugger
  (Xdebug DLL matched to that PHP); intelephense gets `environment.phpVersion`; Composer
  (`toolchains\composer\composer.phar` + `composer.bat`, `php_toolchain.composer_argv(args, php)`) runs with it:
  Tools > Composer (install / update / require / remove / dump-autoload / validate / outdated), Tools > PHP
  Versions... (list + Install PHP 8.x / Composer). Framework code calls `php_toolchain.project_php(project)` and
  `win.run_composer(args, project)`.
- **PHP frameworks** (round 6). Shared: `radide/web_site/frameworks/common.py` - registry
  (`register_framework(PhpFramework(id, title, detect, router, module))`, `framework_of(folder)` = `web.framework`
  of project.radproj or detected, `framework_module(id)`), `router_for(folder, root)` (php_web.backend appends it
  to `php -S` when `web.router` is empty; a module may also define `backend_spec(server, spec)`), `run_php`,
  `StampCache` / `tree_stamp` (indexes rebuilt only when their files change), PHP string / call-context and
  config-array parsers, completion item shape. A framework module exposes `complete_items(folder, path, text,
  line, col) -> list | None` and `definition(folder, path, text, line, col) -> (file, line) | None`;
  `radide/features/php_frameworks.py` merges them into Monaco through `MonacoEditor.completion_providers`
  (fn(editor, line, col) -> items; LSP items with the same label are dropped; `"exclusive": True` = only ours) and
  a `radPhpFw` channel object (F12 / Ctrl+click via a definition provider + `registerEditorOpener`).
  **Laravel** (`frameworks/laravel.py`, owner: laravel): templates "Laravel App" / "Laravel API" (gallery ids
  `laravel`, `laravel-api`; `create_laravel()` = composer create-project, .env + key:generate, SQLite or the local
  MariaDB / PostgreSQL server, migrate, `install:api` + Sanctum, barryvdh/laravel-ide-helper); `web = {"root":
  "public", "start": "/", "framework": "laravel", "php": "8.4"}` (the newest RAD IDE toolchain PHP >= 8.3 it was
  created with, else "auto"); Blade language `radide/web/blade.js` (`*.blade.php`);
  Laravel panel (Artisan form from `artisan list --format=json`, Routes from `route:list --json`, Tinker =
  `frameworks/laravel_repl.php` persistent REPL); opening a project without vendor/ offers composer install / .env /
  key / database + migrate --seed / npm install + build (`win.prepare_laravel()`). Sample:
  `samples/Tests/Web/Laravel_Blog`.

### 8.2 Design view (owner: web-design) - Expression Web
`radide/web_site/design.py` + assets in `radide/web/grapes/` (GrapesJS, BSD licence; get it with
`npm pack grapesjs@<version>` into scratch and copy the dist files; also grapesjs-preset-webpage / blocks-basic
if useful). `DesignView(win, path)` tab for .html/.htm/.php files: **Design**, **Split** (design + Monaco code,
synced) and **Code** modes; Blocks, Layers, **Style Manager = CSS Properties panel**, Traits; saving writes the HTML
back (PHP code blocks `<?php ... ?>` must be preserved - protect them as non-editable components); CSS goes to the
page's own <style> or a linked stylesheet if the page has one. Opened from the explorer menu "Open in Design View"
and from a "Design" button when an HTML/PHP file is active.

### 8.3 Databases (owner: web-db) - WebMatrix Databases workspace
`radide/web_site/databases.py` + `radide/features/databases.py`: Databases dock/tab with connections (SQLite file,
MySQL, PostgreSQL) stored in the project (`project.radproj` "databases": [...], passwords NOT stored in plain text
- keep them in QSettings with a warning or ask each time). Native browser: tables list, table data grid (edit/insert/
delete rows), schema view, SQL query window with results; SQLite via `sqlite3`, MySQL via PyMySQL / PostgreSQL via
psycopg if installed (pip into the IDE venv is allowed: `.venv\Scripts\python.exe -m pip install pymysql`).
Also bundle **Adminer** (single PHP file, download from the official GitHub release into `radide/web/adminer/`)
and offer "Open in Adminer" served by `php -S` in the Preview dock.
**Local servers** (`radide/web_site/dbservers.py`, no Windows services): "Local Servers" in the Databases toolbar /
Tools > Databases starts MariaDB (portable zip in `%LOCALAPPDATA%\RADIDE\toolchains\mariadb`) or PostgreSQL (EDB
binaries zip, `...\toolchains\pgsql`) on demand; data in `%LOCALAPPDATA%\RADIDE\db\<mariadb|pgsql>\data`
(initialized on the first start), 127.0.0.1 only, user/database `radide`, random password DPAPI-encrypted in
`...\db\<engine>\radide-server.json`; the connection is added to the project; servers this IDE started are stopped
on exit. The PHP Data App template also runs on MySQL (`'db_driver' => 'mysql'` in app/config.php).

### 8.4 Publish, Reports, SuperPreview (owner: web-tools)
- `radide/web_site/publish.py`: publish profiles (FTP, FTPS, SFTP via paramiko if installed, local folder copy);
  upload only changed files (size+mtime or hash cache), dry-run listing, exclusions (.git, .radide_backup...),
  progress in the Output window. Profile dialog; passwords not in the project file.
- `radide/web_site/reports.py`: **SEO report** crawler over the running DevServer (title, meta description, h1,
  img alt, broken links/4xx/5xx, duplicate titles, page size, load time), results dock with click-to-open; plus
  "Lighthouse report" via `npx lighthouse <url> --output=html` when available (opens the HTML report in Preview).
- `radide/web_site/superpreview.py`: **SuperPreview** window: the same URL side by side at two sizes/engines
  (phone/tablet/desktop presets, rotate), overlay/onion-skin compare, and "Open in Chrome / Edge / Firefox" for
  installed browsers.
- Menu entries via a feature module (`radide/features/web_tools.py`).

### 8.5 App Gallery and the complete PHP project (owner: web-gallery)
`radide/web_site/gallery.py` + `radide/web_site/templates/`: templates for New Project / "App Gallery" dialog:
PHP Empty Site, **PHP Starter Site** (layout include, pages, contact form), **PHP + SQLite Data App** (login with
password_hash, session, CRUD list/add/edit/delete, PDO prepared statements, CSRF token), HTML Bootstrap site
(Bootstrap via CDN or bundled), Node Express site, Laravel (via `composer create-project` when composer exists),
WordPress (download latest zip from wordpress.org + "SQLite Database Integration" plugin so no MySQL is needed -
only if downloads work; otherwise say so). Create **samples/HelloPHPSite** = the PHP + SQLite Data App, verified by
running `php -S` and real HTTP requests (register/login/CRUD).

### 8.6 Web IntelliSense (owner: web-intellisense)
Monaco + LSP for web files: HTML/CSS/JSON via `vscode-langservers-extracted` (npm), PHP via `intelephense` (npm),
JS/TS via typescript-language-server (npm) - install into a private folder `%LOCALAPPDATA%\RADIDE\lsp\node_modules`
with `npm install --prefix` (allowed) and teach `radide/lsp.py` SERVERS to find them there; **Emmet** in Monaco
(`emmet-monaco-es` bundled into `radide/web/`), "Open as PHP" for any file, PHP/HTML snippets. Owner: radide/lsp.py,
radide/monaco_editor.py, radide/web/editor.html.

### 8.7 Expression Blend features for the form designer (owner: blend)
`radide/features/states.py`, `radide/features/timeline.py` (+ targeted edits in designer.py, document.py,
properties.py, model.py, python_tk.py, python_qt.py, vbrun.py): **Visual States** - a States panel (Normal,
MouseOver, Pressed, Disabled, Focused per control + custom form-level states) storing property overrides in the
.form (`"states": {...}` per control and form), designer shows the selected state, generated code switches states
automatically (hover/press) and exposes `GoToState(name)`; **Storyboards** - an Objects and Timeline panel with
keyframes on Left/Top/Width/Height/BackColor/ForeColor/Opacity, play in the designer, generated code runs them
(`Storyboard1.Begin()`); **Sample data / data binding** - a Data panel: a JSON/CSV data source in the project, bind
a control property (Text, Items, Value) to a field, design-time sample values. Implement fully for python-tk and
python-qt; for other languages generate nothing new (ignore states) without breaking them.

### 8.8 Round-3 ownership
| Owner | Files |
|---|---|
| web-core | radide/web_site/__init__.py, server.py, project.py; radide/languages/php_web.py, static_web.py, node_web.py; radide/features/web_workspace.py; small hooks in app.py, features/solution_ui.py, dialogs.py |
| web-design | radide/web_site/design.py, radide/web/grapes/ |
| web-db | radide/web_site/databases.py, radide/features/databases.py, radide/web/adminer/ |
| web-tools | radide/web_site/publish.py, reports.py, superpreview.py, radide/features/web_tools.py |
| web-gallery | radide/web_site/gallery.py, radide/web_site/templates/, samples/HelloPHPSite |
| web-intellisense | radide/lsp.py, radide/monaco_editor.py, radide/web/editor.html, radide/web/emmet/ |
| blend | radide/features/states.py, timeline.py, databinding.py (+ targeted edits listed in 8.7) |
| qa (after all) | integration fixes anywhere (small edits) |

## 9. Workbench layouts (Visual Studio / VS Code / Agent) and AI everywhere - round 4

The user's request: one button switches the whole IDE between a **Visual Studio** look (today's), a **VS Code**
look and an **Antigravity-style Agent** look; AI support "in all its forms", including **free AI without API keys**.

"Free without API" is done with legitimate routes only:
(a) official **CLI agents that log in with the user's own account / subscription** (Claude Code `claude`,
Gemini CLI `gemini` - free tier with a Google login, OpenAI Codex CLI `codex` - ChatGPT login, GitHub Copilot CLI
`copilot`, Qwen Code `qwen`, opencode `opencode`, Cursor `cursor-agent`), (b) **local models** (Ollama - installed
here with `gemma4:e4b`, LM Studio, llama.cpp / any OpenAI-compatible local server), (c) **embedded web chats**
(chatgpt.com, gemini.google.com, claude.ai, chat.deepseek.com, copilot.microsoft.com, perplexity.ai ...) in a
QWebEngine tab with a persistent profile - the user logs in normally, the IDE pastes context into the page and
reads code blocks back. API keys (OpenAI, Anthropic, Gemini API, OpenRouter, Groq, DeepSeek, Mistral, xAI, any
OpenAI-compatible URL) are optional extras. We do NOT use reverse-engineered/unofficial web endpoints (g4f-style).
Installed on this machine: `claude` (WinGet link), `gemini` and `opencode` (npm global), `ollama`.
Tests must keep CLI/API usage tiny (1-2 short prompts per provider) - they spend the user's quota; prefer Ollama.

### 9.1 AI core - `radide/ai/` (owner: ai-core).  Everybody else codes against THIS API.
```python
from radide import ai
ai.Message(role, content)                      # role: "system" | "user" | "assistant"
p = ai.get(provider_id)                         # ai.providers() -> list[Provider]
p.id, p.name, p.kind                            # kind: "cli" | "local" | "api" | "web"
p.available() -> tuple[bool, str]               # (ok, reason / install hint); must be fast (cache detection)
p.models() -> list[str]; p.default_model
job = p.chat(messages, model=None, system=None, temperature=None, max_tokens=None, cwd=None)
#   job: ai.ChatJob(QObject) signals delta(str), finished(str full_text), failed(str); job.cancel(); job.text
#   streaming on the Qt event loop (worker thread or QProcess) - never blocks the UI thread
p.supports_fim; p.complete(prefix, suffix, language, model=None) -> ChatJob   # inline completion (FIM or prompt)
ai.default(purpose) -> (Provider, model)        # purpose: "chat" | "complete" | "edit" | "agent" | "commit"
ai.set_default(purpose, provider_id, model)     # stored in QSettings "ai/..."
ai.run_sync(job, timeout=60) -> str             # tests / scripts only
ai.extract_code_blocks(text) -> list[(lang, code)]
```
Provider ids: `claude-cli`, `gemini-cli`, `codex-cli`, `copilot-cli`, `qwen-cli`, `opencode-cli`, `cursor-cli`,
`ollama`, `lmstudio`, `openai-compatible` (custom base URL), `openai`, `anthropic`, `gemini-api`, `openrouter`,
`groq`, `deepseek`, `mistral`, `xai`. CLI providers run non-interactive modes (`claude -p --output-format
stream-json --verbose`, `gemini -p`, `codex exec --json`, `opencode run`, ...) with the prompt on stdin where
supported; detect with shutil.which (+ `.cmd`/`.ps1` npm shims: run `.ps1`-only shims via
`powershell -NoProfile -File` or prefer the `.cmd`). Secrets: `keyring` if importable, else QSettings with a warning.
Tools > Options > **AI** page: providers table (status, install hint / "Install with npm" button for npm CLIs,
login hint e.g. "run `gemini` once in the Terminal to sign in"), API keys, base URLs, model pickers, defaults per
purpose, "Test" button per provider. `radide/ai/context.py`: `gather(win, mentions)` builds prompt context for
`@file:path`, `@selection`, `@problems` (Error List), `@form` (current .form JSON), `@project` (file tree),
`@git` (diff), `@terminal` (last output) - truncated to a token budget.

### 9.2 Workbench layouts - `radide/features/workbench.py` (owner: layouts)
- **View > Layout** + a toolbar segmented button + Ctrl+K Ctrl+L: *Visual Studio* | *VS Code* | *Agent*.
  The switch is live (no restart), remembered in QSettings `workbench/mode`; each mode keeps its own
  `saveState()`/`saveGeometry()` so the user's dock arrangement per mode survives.
- *Visual Studio*: today's menus, toolbars, docks.
- *VS Code*: **Activity Bar** (left vertical icon strip: Explorer, Search, Source Control, Run and Debug,
  Packages/Extensions, Databases, AI Chat, Agents; a click toggles one **Side Bar** that hosts the existing
  widgets - re-parent the existing dock widgets, do not duplicate logic), editor area centre (tabs, breadcrumbs
  bar above the editor), bottom **Panel** (Problems = Error List, Output, Terminal, Debug Console = Immediate,
  Requests), compact toolbar hidden, menu bar kept (VS Code style "File Edit Selection View Go Run Terminal Help"
  ordering is optional), blue status bar with language / line:col / git branch / AI provider. **Command Palette**
  Ctrl+Shift+P (fuzzy over every QAction in the menus + extra commands), **Quick Open** Ctrl+P (fuzzy files of the
  solution), Zen mode, toggle side bar Ctrl+B, toggle panel Ctrl+J.
- *Agent* (Antigravity style): the **Agent Manager** (9.5) fills the left/centre, the editor/preview on the right,
  a slim activity bar to jump back to Editor view; the chat/agent is the main surface.
- Command Palette and Quick Open work in all modes. All themes (radide/theme.py) apply to the new chrome: use
  `theme.color(token)` / `theme.role(widget, name)` and connect `theme.changed`.

### 9.3 AI Chat - `radide/features/ai_chat.py` (owner: ai-chat)
Dock "AI Chat" (also used by the VS Code side bar and the Agent mode): provider/model picker, streaming markdown
answer (QTextBrowser or a QWebEngine view; code highlighted), code blocks with **Copy / Insert at cursor /
Apply to file (diff preview, accept/reject) / New file / Run in Terminal**, `@` mention completion (9.1 context),
attach current file/selection buttons, Stop, regenerate, new chat, history saved per project in
`.radide/ai/chats/*.json`, "Ask about this" from editor/explorer right-click, Arabic text RTL-correct.

### 9.4 AI in the editor and designers - `radide/features/ai_editor.py` (owner: ai-editor)
- **Inline completions (ghost text)** in Monaco (`monaco.languages.registerInlineCompletionsProvider` in
  `radide/web/editor.html`, routed through the existing `rad` QWebChannel bridge to `ai.default("complete")`),
  debounce, Tab accept, Esc dismiss, on/off in the status bar; builtin-editor fallback optional.
- **Ctrl+I inline edit**: prompt box over the selection -> streamed replacement shown as a diff (Monaco diff
  editor or decorations) -> Accept / Reject.
- Editor right-click **AI** submenu: Explain, Fix, Refactor, Add comments, Generate tests, Generate docs,
  Translate code to another language of the IDE. Error List "Fix with AI". Git panel "Generate commit message"
  (from the staged diff). Form designer "Generate form with AI" (description -> neutral .form JSON validated with
  radide/model.py, then opened in the designer) and "Generate event handler".

### 9.5 Agent Manager - `radide/ai/agents.py` + `radide/features/ai_agents.py` (owner: ai-agent)
Antigravity-style: a list of agent **tasks** (title, status, provider, started), several running in parallel, each
with a conversation view showing the plan, every step (file read/write/edit, command run, search) and its result,
**file diffs to review** (accept/reject per file, "Undo all" via a checkpoint copy of touched files under
`.radide/ai/checkpoints/<task>`), artifacts (plan/walkthrough markdown, screenshots of the web Preview). Two
engines: (1) **CLI agent engine** - runs `claude -p --output-format stream-json --verbose` (parse its JSON events
into steps), `gemini -p ... --yolo|--approval-mode`, `codex exec --json`, `opencode run` in the project folder;
(2) **built-in agent loop** for any ai provider (Ollama/API/...) with tools read_file, list_files, search,
write_file, edit_file, run_command (approval required for writes/commands unless "auto-approve" is on), max steps.
Permission modes: Ask every time / Auto-approve edits / Auto-approve all. Inbox notifications when a task needs
approval or finishes.

### 9.6 Web chats - `radide/features/ai_web.py` (owner: ai-web)
"AI Web Chats" tab/dock with a site switcher (ChatGPT, Gemini, Claude, DeepSeek, Copilot, Perplexity, Grok, Qwen,
Mistral Le Chat, custom URL), one persistent QWebEngineProfile (`%LOCALAPPDATA%\RADIDE\webchat`, cookies kept),
"Send context" (selection/file/problems -> filled into the page's prompt box via JS, fallback: clipboard + focus),
"Grab last code block" (JS reads the last `<pre><code>` of the page) -> Insert / Apply via the same diff preview as
9.3 (import it from ai_chat if present, else a local fallback), open in external browser. Also registered as
provider kind "web" in the registry (chat() = send + wait for the answer to stop changing, best effort).

### 9.7 Ownership (round 4)
| Agent | Owns |
|---|---|
| ai-core | radide/ai/__init__.py, providers*.py, context.py, settings page module radide/features/ai_settings.py |
| layouts | radide/features/workbench.py, radide/features/command_palette.py |
| ai-chat | radide/features/ai_chat.py, radide/ai/diffview.py (shared diff accept/reject dialog) |
| ai-editor | radide/features/ai_editor.py; targeted edits in radide/web/editor.html, radide/monaco_editor.py |
| ai-agent | radide/ai/agents.py, radide/features/ai_agents.py |
| ai-web | radide/features/ai_web.py |
Until ai-core lands, other agents may stub `radide.ai` calls behind try/except but must end up using the real API.

## 10. Mobile apps, games, and importing programs from .exe - round 5

The user's requests: "now the most important part: mobile applications and games" and "the last thing: use a
source that reads the assembly from the exe and converts any program to simple Python".
Installed here: Flutter (C:\flutter, Dart), Android SDK (%LOCALAPPDATA%\Android\Sdk: adb, emulator, AVDs
`Medium_Phone_API_36`, `ZA_Screens`), JDK 17, Godot 4.2.2 (`godot`), .NET 9 SDK, Node 22. pip/npm/dotnet-tool
installs into the venv / private folders are allowed (pygame-ce, kivy, pefile, capstone, ilspycmd ...).

### 10.1 Mobile apps (owner: mobile)
- New Project > **Mobile** group: *Flutter App* (Dart, the main path), *Python Kivy App* (desktop run + Buildozer
  notes), *React Native / Expo* only when npx works (template + run on web/Android).
- The **form designer gets a phone frame**: device presets (Android phone / tablet, iPhone sizes), portrait /
  landscape, safe area, mobile-only controls in the Toolbox when the project is mobile (AppBar, BottomNavigation,
  FloatingActionButton, Card, ListView with item template, Switch, Slider, TextField, Image, Icon, Drawer,
  TabBar, Snackbar/Toast, WebView), layout by Column/Row/Stack/Padding (Flutter) besides absolute placement.
- Code generation: `.form` -> Dart widget tree (`lib/<form>_designer.dart`) + user file `lib/<form>.dart` with
  event handlers (same VB-style double-click -> handler model), several forms = screens with navigation
  (`Navigator.push`, `ShowForm` equivalent); Kivy: .form -> KV/Python.
- Run: **Device selector** in the toolbar (Windows desktop / Chrome / Android emulators from `flutter devices` and
  `emulator -list-avds`, start an AVD on demand), F5 = `flutter run -d <id>` with **hot reload on save** (send `r`
  to the process) and hot restart, logs in Output; Build menu: APK / App Bundle / Windows exe / web.
- Debugger: Dart DAP (`dart debug_adapter` / `flutter debug_adapter`) through radide/dap.py when feasible.

### 10.2 Games (owner: games)
- New Project > **Games** group: *Python Game (pygame-ce)* main path, *Python Arcade* optional, *Godot project*
  (opens/edits GDScript, runs `godot --path`), *Ring Game (RingRayLib / Allegro)* if available, *HTML5 Canvas game*.
- **Scene designer** (a designer mode for game projects): scene canvas with grid/camera, **sprites** (image,
  position, scale, rotation, z-order, visible), **tilemap editor** (tileset import, paint/erase/fill, layers,
  collision layer), **sprite sheet / animation editor** (frames, fps, loop), sounds, text/UI layers, game
  properties (window size, FPS, background), **Behaviours** (keyboard movement, gravity/platformer, top-down,
  bounce, follow mouse, collide -> event) set in the Properties window, events in code like VB:
  `Player_Collide(other)`, `Game_Update(dt)`, `Game_KeyDown(key)`, `Timer1_Tick`.
- Code generation for pygame-ce (scene loader + game loop + behaviours in a small runtime module copied into the
  project) and for Godot (`.tscn` + `.gd` export). F5 runs the game; asset browser dock (images/sounds preview).
- Samples: `samples/HelloGame` (platformer with tilemap, player sprite animation, coins, score) and
  `samples/HelloMobile` (Flutter: 2 screens, list, form, navigation). (Samples are new folders - allowed.)

### 10.3 Import a program from .exe (owner: exe-import)
File > Import > **Program (.exe / .dll)...**: a wizard that identifies the binary and uses the best open-source
tool, producing a RAD IDE project (forms + code) - for programs the user owns or may legally analyse (show that
notice in the wizard).
- Identify: `pefile` - .NET (CLR header), VB6 (MSVBVM60 import / VB5! header), PyInstaller / py2exe / cx_Freeze /
  Nuitka, Delphi, AutoIt/AHK, Electron/NW.js (app.asar), Java (jar/exe wrapper), native C/C++.
- **.NET**: `ilspycmd` (dotnet tool, install into %LOCALAPPDATA%\RADIDE\tools) -> C# project; WinForms
  `InitializeComponent` -> `.form` (controls, positions, text, events) + handler code translated to Python
  (rules for common APIs: MessageBox.Show, TextBox.Text, ..., with AI (radide.ai, CONTRACTS 9.1) as the
  translator when a provider is configured and rules otherwise leave the C# as comments).
- **VB6 exe**: forms from the embedded VB6 form structures (open-source parsers / own parser) -> `.frm` -> the
  existing VB6 importer; P-code / native code -> best effort (event names + strings) + AI translation.
- **Python exes**: pyinstxtractor-ng -> .pyc -> decompile (pycdc / decompyle3 for the matching version) -> the
  existing Python importer for forms.
- **Native**: dialogs/menus/strings from PE resources (pefile) -> `.form`; disassembly with capstone and, when
  available, Ghidra headless decompile (download Ghidra into %LOCALAPPDATA%\RADIDE\tools only if the user
  confirms - it is large) -> pseudo-C -> AI translation to simple Python; without Ghidra: resources + imports +
  strings + function list report.
- Electron (asar extract -> JS project), Java (jar -> CFR/Vineflower decompile -> Java project or AI to Python),
  AutoIt (resource script).
- Output: a new project (python-tk by default, user can choose another language) + an import report (what was
  recovered exactly, what was translated by rules, what by AI, what is missing).

### 10.4 Shared formats (agree on these - agents of the same area work in parallel)
- Mobile control types (in `.form` like any control; `props` use the usual Left/Top/Width/Height/Text/BackColor/
  ForeColor/FontSize/Visible/Enabled + the extras listed): `AppBar` (Title, Actions="a;b"), `BottomNav`
  (Items="Home;Search;Profile", SelectedIndex), `Fab` (Icon), `Card` (Elevation, container), `MListView`
  (Items, ItemTemplate="title|subtitle"), `Switch` (Checked), `MSlider` (Minimum/Maximum/Value), `MTextField`
  (Hint, Password), `MImage` (Image, Fit), `MIcon` (Icon name from Material icons), `Drawer` (Items),
  `MTabBar` (Tabs), `MWebView` (Url), `Column`/`Row`/`Stack` containers (Spacing, Align, Padding; children are
  laid out by the container in the designer preview too). Form props for mobile forms: `Device` (preset id),
  `Orientation` (Portrait|Landscape), `Route` (screen route name). Events: Click/Tap, Changed, Submitted, Load.
  Project `kind` stays "app"; plugin ids `flutter` and `kivy`. A plugin attribute `is_mobile = True` tells the
  designer to show the phone frame and the Mobile toolbox group.
- Game scene file `<Scene>.scene` (JSON): `{"name", "width", "height", "background", "fps", "gravity",
  "camera": {"follow": sprite|null}, "assets": {"images": {id: path}, "sounds": {id: path},
  "spritesheets": {id: {"image", "frame_w", "frame_h", "animations": {name: {"frames": [i...], "fps", "loop"}}}},
  "tilesets": {id: {"image", "tile_w", "tile_h"}}}, "layers": [{"name", "type": "tiles"|"sprites"|"ui",
  "tileset", "data": [[tile index or -1 ...]...], "collision": bool, "objects": [{"name", "kind":
  "sprite"|"text"|"area", "x", "y", "w", "h", "image"|"spritesheet", "animation", "scale", "rotation", "z",
  "visible", "text", "behaviours": [{"type": "keyboard_move"|"platformer"|"top_down"|"bounce"|"follow_mouse"|
  "solid"|"collectible"|"enemy_patrol"|"flap"|"scroll", ...params}], "props": {}}]}]}` (a behaviour with
  `"enabled": false` is paused; object props `template=1` = a hidden spawn template copied at run time by
  `Spawn(name, x, y)` / GDScript `spawn()`, `hitbox=n` = collide n px inside the picture). Game project: plugin ids
  `pygame` and `godot`; `is_game = True` tells the IDE to open `.scene` files in the scene designer; user code in
  `<Scene>.py` with VB-style handlers `Scene_Load`, `Scene_Update(dt)`, `Scene_KeyDown(key)`,
  `<Sprite>_Collide(other)`, `<Sprite>_Click`, `Timer` events; the runtime module `radgame.py` is copied into
  the project (like the GUI-bridge clients).
- Exe import backends: `radide/importers/exe/base.py` (owner exe-core) defines
  `identify(path) -> BinaryInfo(kind, details: dict)` and `ImportResult(forms: list[(name, form_dict)],
  modules: list[(name, code, language)], resources: dict, report: list[(level, text)], source_dir: Path|None)`;
  backends `dotnet.py`, `vb6.py`, `pyexe.py`, `java.py`, `electron.py` (owner exe-managed) and `native.py`,
  `pe_resources.py` (owner exe-core) each expose `can_handle(info) -> bool` and
  `run(path, info, workdir, progress, ai_translate: bool) -> ImportResult`. The wizard (exe-core) picks the
  backend and turns the result into a project in the chosen language (forms via the neutral model, code via
  rules + radide.ai when allowed).

### 10.5 Ownership (round 5)
| Agent | Owns |
|---|---|
| mobile-lang | radide/languages/flutter.py, kivy_app.py, radide/mobile/codegen*.py, radide/features/mobile.py (devices, run, hot reload, build), templates, samples/HelloMobile |
| mobile-designer | radide/mobile/controls.py, radide/mobile/frame.py (phone frame, device presets, container layout), mobile rendering in the designer (targeted edits in designer.py/preview.py/toolbox.py/controls.py) |
| game-designer | radide/games/model.py, radide/games/scene_editor.py, tilemap/animation/asset editors, radide/features/game_designer.py |
| game-runtime | radide/languages/pygame_game.py, godot.py, radide/games/runtime/radgame.py, codegen, Godot export, templates, samples/HelloGame |
| exe-core | radide/importers/exe/base.py, native.py, pe_resources.py, radide/features/exe_import.py (wizard + report) |
| exe-managed | radide/importers/exe/dotnet.py, vb6.py, pyexe.py, java.py, electron.py |

### 10.6 Advanced Flutter designer (widget trees, FlutterFlow style)
Screens as real widget trees in `<Screen>.fscreen.json` (Scaffold/Container/BoxDecoration/Stack/Positioned/...,
~90 catalog widgets, animations), generated to `lib/screens/<screen>.dart` + user part file
`<screen>_events.dart`, imported back from Dart with a package:analyzer CLI. Schema, catalog, value encodings,
tree-op/undo API, codegen and importer contracts: **docs/FLUTTER_DESIGNER.md** (owners: model -
radide/flutterdesign/model.py, codegen.py, importer.py, dart_tools/; ui - designer.py, inspector.py, palette.py,
radide/features/flutter_designer.py; render - preview_host/, live.py; assets - assets.py, themes.py,
animations.py, templates/).

### 10.7 Assembly (NASM, FASM, MASM, GNU as, 8086 emulator)
Plugins `asm-nasm` / `asm-fasm` / `asm-masm` (`.asm`) and `asm-gas` (`.s`): `radide/languages/asm_*.py` (base
`asm_base.py`); toolchains (NASM / FASM / GoLink downloaded from the official sites, MinGW-w64 as / ld / gcc /
gdb reused, MASM only from Visual Studio), build `python -m radide.asm.build <folder>` -> `_radapp.exe` +
`_build\diagnostics.json`, error parsing, templates, GUI Bridge forms (`Form1.inc` / `_radmain.asm` /
`radgui.inc`) and the DWARF line information gdb reads for NASM objects: `radide/asm/`. Project settings: the
`"asm"` key of project.radproj. Editor intelligence, native debugger, 8086 emulator, samples and course have
their own sections - all in **docs/ASSEMBLY.md** (owners: asm-core - radide/asm/, languages/asm_*.py,
features/asm_build_ui.py; the other parts as listed there).
Editor intelligence (owner: asm-intel - radide/asm_intel/, features/asm_ide.py; targeted edits in
radide/monaco_editor.py, radide/web/editor.html, radide/lsp.py, radide/lsp_servers.py) added generic Monaco hooks
any language may use: `MonacoEditor.plugin_overlays`, `plugin.monaco_language(path)` (full Monarch grammar via
`radRegisterMonarch`), completion items with `doc` / `insert` / `snippet` / `sort` / `edits`, and dict calltips
(docs/ASSEMBLY.md, "Editor intelligence").

### 10.8 Foldable devices and TwoPane (owner: foldables - radide/devices.py, radide/mobile/{controls,frame,render}.py, features/mobile.py AVD helpers)
- **Shared geometry** `radide/devices.py` (pure, no Qt): `Device` (+ `fold` book|flip|dual, `fold_axis` in
  portrait, `hinge` dp - 0 = seamless crease, `cover` (w, h) | None, `postures`, `avd` profile), `DEVICES`
  (the 5 original ids kept + iPhone 15 Pro Max, Galaxy S20, iPad mini, `galaxy_z_fold6`, `galaxy_z_flip6`,
  `pixel_fold`, `pixel_9_pro_fold`, `surface_duo2`; dp approximate), `screen_size / safe_insets /
  safe_area_size(device, orientation, posture="Flat")` (Folded = cover screen), `fold_axis`,
  `hinge_screen_rect` (screen coords), `hinge_rect(device, orientation, posture) -> (x, y, w, h) | None` in
  **safe-area coords** (= form client area), `is_separating` (dual hinge, or HalfOpened), `span` (single|dual),
  `segments` (CSS viewport segments), `display_features` (Flutter `MediaQuery.displayFeatures`:
  `{"type": "hinge"|"fold", "bounds": [x, y, w, h], "state": "postureFlat"|"postureHalfOpened"}`), `two_pane()`,
  `env_state()` (RADIDE_POSTURE / RADIDE_SPAN / RADIDE_HINGE), `device_rows()`. `radide.mobile.controls`
  re-exports all of it (old imports keep working).
- **Form property** `Posture` = `Flat | HalfOpened | Folded` (default Flat), written / shown only when `Device` is
  a foldable (`form_prop_defs`); `posture_key()` gives the runtime spelling `flat | half-opened | folded`
  (variant `when.posture`, RADIDE_POSTURE). Width / Height follow Device + Orientation + Posture.
- **Designer**: DeviceBar Flat / Half-open / Folded buttons; hinge drawing (dual = opaque bezel band, Flat
  fold = dashed crease, HalfOpened = crease + shaded upper / right half + "Hinge" tag); controls across a
  separating hinge get a red dashed outline and an Error List warning ("Controls cross the hinge: ...",
  `mobile.controls.hinge_conflicts(form, device=None, orientation=None, posture=None)`; AppBar / BottomNav /
  MTabBar / Drawer / TwoPane and containers are allowed to span). `PhoneChrome.preview(device, orientation,
  posture)` draws another device without touching the form (no args = back to the form's own); the form's
  Width / Height for that preview come from `DesignerView.form_props()` (layout variants, slice C).
- **TwoPane** (mobile Toolbox, container made in code): props `PaneMode` Auto|Horizontal|Vertical, `Ratio`
  0.5 (float), `SinglePane` Start|End, `HingeAware` True; event `PaneModeChanged` (e.Mode). Its **first two
  child controls** are the panes (put a Column / Stack / Panel in each). Split rule = `devices.two_pane(w, h,
  mode, ratio, single, hinge_in_box, hinge_aware)`:
  1. HingeAware and the hinge band lies inside the box: vertical band -> side by side, horizontal band ->
     top / bottom, panes end exactly at the band edges (Auto, or the matching explicit mode);
  2. else Auto: width >= 600 dp -> side by side at Ratio, narrower -> `single` (only SinglePane, full box);
  3. Horizontal / Vertical: always two panes at Ratio.
  At design time the hidden pane of single mode is parked just right of the box (clipped). **Runtimes / code
  generators** (python-tk / python-qt / vbrun / bridges = slice C; Flutter, Kivy, Expo, Ring = slice D) must use
  the same rule: desktop toolkits = two placed frames, hinge from `devices.env_state()["hinge"]` (RADIDE_HINGE
  in window coords) else Ratio; Flutter = `RadTwoPane` (DisplayFeatureSubScreen, Ratio fallback); targets
  without display features use the Ratio / single rule. The hinge is always converted to the TwoPane's own
  coordinates first (it need not fill the window): Flutter `RadTwoPane.localHinge(hinge, fold, origin, w, h)`
  with the origin measured after layout (`localToGlobal`, one extra frame), Kivy `to_window`, Ring
  `RadPane_Origin` (position in the window, also for a nested pane), the designer `frame.two_pane_split`; a
  hinge that does not cross the box from side to side -> rule 2 / 3.
- **Folded posture at runtime (Flutter)**: Flutter reports no "folded" display feature (Android reports a fold
  only on the inner screen). `RadVariant.compute` says `folded` when no fold / hinge is reported and either a
  fold was seen before in this run (`RadVariant.foldableSeen`: the app moved to the cover screen) or the window
  looks like a cover screen (`looksLikeCoverScreen`: shortest side < 400 dp and >= 2.3 times as long;
  `RadVariant.coverScreenHeuristic = false` turns the guess off). A half-opened fold = halfOpened, a flat fold /
  hinge = flat; `debugPosture` overrides; `resetFoldMemory()` for tests. Limits: an app started folded on a
  cover screen wider than 2.3:1 (Pixel Fold 411 x 797) is flat until it has been unfolded once; a window of a
  split screen that does not cross the fold reads as folded.
- **Error List**: the "Controls cross the hinge" rows of an open form are refreshed 250 ms after each designer
  change (move / resize / Device / Orientation / Posture / undo) and when the designer opens
  (`features/mobile.watch_hinge`), not only by the checks run on save / build.
- **Labels**: device names in combo boxes go through `devices.display_name(dev)` / `short_name(dev)` (ar.json;
  combo items are not translated by radide.i18n), relabelled on a language change.
- **Emulator**: `features/mobile.py` `foldable_avd(name="RADIDE_Fold")` creates (never modifies / deletes other
  AVDs) an AVD from the first available profile of `devices.FOLDABLE_AVD_PROFILES` (pixel_9_pro_fold,
  pixel_fold, 7.6in Foldable ...) and the newest installed system image for this CPU (Build > Mobile App >
  Create Foldable Emulator); `set_posture(serial, posture)` uses `cmd device_state state <id>` (ids read from
  `print-states`, they vary by image; fallback `adb emu fold|unfold`) and verifies with `print-state`.
- **SuperPreview** foldable presets (`Preset.device / posture / segments`, `preset_segments()`): Fold6 open /
  cover, Pixel Fold, Flip6 (flat, half-open dual segments), Surface Duo 2 spanned (dual segments).

### 10.9 Motion for classic forms - animation presets (owner: motion - radide/motion/*, features/states.py, features/timeline.py; small additions in runtimes/vbrun.py)
Plan: docs/plans/MOTION_VARIANTS_FOLDABLES.md (contracts 1.1-1.4, 1.7; slice A).
- **Model** `form.extra["animations"]` (list of `{id, target ("" = form), preset, params, durationMs, delayMs,
  easing, repeat (0 = forever), autoreverse, trigger: {on, source, intervalMs, after, leave}, enabled}`) and
  `form.extra["motion"] = {"respectReducedMotion": true}`. API `radide/motion/model.py`: `animations, add, remove,
  move, find, for_target, new_id, rename_references, remove_target, validate -> [(fx, control, message)]`
  (missing target / source, bad id, unknown preset / trigger, `after` without animation or in a loop, timer <= 0,
  typewriter without Text). `states.rename_references` also renames animation targets / sources.
- **Presets** `radide/motion/presets.py`: `CATALOG` (fadeIn, slideIn, scaleIn | fadeOut, slideOut, scaleOut | move,
  bounce, shake, pulse, rotate, flip, zoom | colorTo | typewriter), `GROUPS` Entrance / Exit / Attention / Color /
  Text, `Preset.params_schema` (`{name: {type: int|float|bool|choice|color, label, default, choices?, min?, max?}}`),
  `Preset.build(anim, base_props, form, target) -> (tracks, note)`, `make`, `describe`, `by_group`, `EASINGS`
  (linear in out inout back elastic bounce sine), `TRIGGERS`, `TARGET_CAPS` (child alpha, transform) per target
  `py tk qt ring winforms kivy rn dart css`. The track builders are one source, `PRESETS_RT`, embedded in generated
  Python designers.
- **Relative keyframes** (COMMON_RT `_rad_resolve`, resolved in `_Storyboard._remember` against the values at
  Begin): `{"d": n}`, `{"m": k}`, `{"of": "Width", "f": x}` (start + x * start Width), `{"reveal": 0..1}`
  (typewriter, `_RadText` mixes by prefix), `"$parent"` (container background). `timeline.norm_keys` keeps them;
  `timeline.props_at(sb, target, ms, base, parent_bg=None)` resolves them at design time and accepts dict tracks
  or `(target, prop, keys)` tuples. New easings in `_rad_ease` / `timeline.EASES`; numbers may overshoot (back /
  elastic). Old storyboards give the same values as before.
- **Fallbacks** (no transform: rotate = wobble, flip / pulse / scale / zoom = Width / Height around the centre +
  FontSize; no child alpha (tk, winforms): fade = colour blend into `$parent`, then Visible) are returned by
  `expand()` as `fallbacks` - show them in the Error List, never silently.
- **Two animations on one property at the same time** (e.g. Slide In + Pulse On load on one button: both move
  Left in the fallbacks): the one that started first keeps the property until it ends, a later one starts from
  where the first one ends (and Stop does not put back a property another animation still plays). Same rule in
  `_Storyboard` (python-tk / python-qt / vbrun / bridges), `_radfx.ring` (`RadFx_Owner` / `RadFx_RestOf`), the
  WinForms `RadFxEngine` (`Owner` / `RestOf`) and the design-time preview (`FxPreview._owner / _rest`);
  transform targets (Flutter, Kivy, RN) use separate channels. Test: `samples/Tests/QA/MotionE2E/check_runtime_fixes.py`.
- **expand** `radide/motion/expand.py` `expand(form, target) -> FxPlan` (contract 1.3) with additive keys:
  storyboards also carry `target, delayMs, restore (ends where it started), preset`; triggers carry `target`.
  `storyboard_dict(sb)` = .form storyboard shape (for `BlendPreview.timeline`). `sb_name(fx) = "_fx_" + fx`.
- **_Storyboard** (timeline.STORYBOARD_RT): `Count`, `Completed` (list of callables, run before
  `<Name>_Completed`), `Reverse()`, `Finish()` (jump to end + Completed; reduced motion), relative keys.
- **Python runtime** `radide/motion/runtime_py.py` `FX_RT` (`_RadFx`, `_RadQuietIO`, `_rad_reduced_motion`):
  `python_blend` adds it when the form has animations or `extra["motion"]` (target "py" for tk, "qt" for qt):
  `self._fx = _RadFx(self, self._rad, storyboards, triggers, reduced=..., alpha=...)`, `self._fx_<id>` storyboards,
  `self._fx.start` after `<Form>_Load`. Designer methods `Animate(target, preset, **opts)` (opts durationMs,
  delayMs, easing, repeat, autoreverse + preset params, `from_=` for `from`), `BeginAnimation(id)`,
  `StopAnimation(id)`, `SetVisible(control, on)` (plays On show / On hide). `_RadIO` gained `bind(name,
  "click"|"enter"|"leave", fn)`, `parent_bg(name)` and the `vis_hook` / `quiet` protocol (Visible changes go
  through the On show / On hide animations). Reduced motion: `RADIDE_REDUCED_MOTION=1|0`, else Windows
  `SPI_GETCLIENTAREAANIMATION` (read only; tested with a mocked SystemParametersInfoW in
  `samples/Tests/Motion/check_reduced_motion_windows.py`). `ensure_fx(ui, toolkit)` creates the runtime on
  demand (vbrun).
- **Animations panel** (features/animations_panel.py): the list order is the form's order (start / generation
  order): Move Up / Move Down and drag in the list (`move_among`, `reorder` over `motion.model.move`; with one
  control's list shown the others keep their places). Preview and Convert to Storyboard use
  `preview_target(win, form)` = the motion target of the form's language (python-qt "qt", PLUGIN_TARGETS of
  10.11, else "py"): frames come from `expand(form, target)` and `BlendPreview` draws Opacity / ScaleX /
  ScaleY / Rotation with `states.FxEffect` (a QGraphicsEffect: the control's pixmap scaled / rotated around its
  centre with opacity; the form's own fade on the form frame); the model never changes.
- **VB6 / GUI Bridge**: `Command1.Animate "slideIn", 500, "from=right"` (preset, optional duration, `name=value`
  options), `Form1.Animate "fadeIn"`, `Me.Animate "Command1", "shake"`, `Form1.BeginAnimation "fx1"` /
  `StopAnimation`, storyboards and animations as objects (`Storyboard1.Begin`, `fx1.Stop`, `.Pause`, `.Resume`,
  `.Reverse`, `.Seek ms`, `.IsPlaying`, `.Duration`, `.Position`), `lblInfo.Visible = False` plays its On hide
  animation. Bridges: `CALL Button1 Animate shake` (`CALL Button1 Animate slideIn<TAB>600<TAB>from=right`).
- Tests: `samples/Tests/Motion/check_motion_core.py`, `check_runtime.py` (tk, tk reduced motion, qt offscreen),
  `check_vb6.py`, `test_motion_designer.py` (qh.py); samples Motion_Tk_Presets, Motion_Qt_Presets, Motion_VB6
  (`make_samples.py` rebuilds them).

### 10.11 Motion, layout sizes and TwoPane on the non-Python targets (owner: slice D - radide/fxtargets.py, languages/ring_fx.py, mobile/{fx_dart,kivy_fx,fx_rn}.py + mobile/dart/radmotion.dart, rn_runtime.RADFX_JS, foreign/winforms_fx.py, web/grapes/radfx.{css,js}, features/motion_targets.py)
Plan: docs/plans/MOTION_VARIANTS_FOLDABLES.md (slice D). Every target reads the same data: `motion.expand(form,
target)` (10.9) and `variants.model.plan(form)` (contract 1.5); forms without animations / sizes / TwoPane are
generated byte-identically (checked over all 246 sample forms for ring-qt / ring-script / ring-app / flutter /
kivy / expo).
- **Shared** `radide/fxtargets.py` (pure): `fx_plan(form, target)` (= expand + `duration` + `chain` per storyboard),
  `channels(sb, base_props)` - the tracks as offsets relative to the designed look for transform targets
  (`tx` / `ty` px y-down, `sx` / `sy`, `rot` degrees, `opacity`, `bg` / `fg` = "start" | "parent" | "#hex",
  `reveal` 0..1, `visible`), `variant_plan`, `when_tuple`, `managed_controls` (moved by some size), `two_panes`,
  `issues(form, target)` (Error List lines), `PLUGIN_TARGETS` (plugin id -> ring | dart | kivy | rn | winforms).
- **Ring (ring-qt, ring-script, ring-app)**: runtime `_radfx.ring` (`ring_fx.RING_FX`, written with `_radqt.ring`;
  the designer `load`s it only when needed). 15 ms qTimer, same easings and relative keyframes as the Python
  runtime; no opacity effect in RingQt: a control fades through rgba() colours of its style sheet (the window
  uses setWindowOpacity), transforms fall back like python-tk (wobble / Bounds around the centre). Triggers:
  On load after `<Form>_Load`, click / hover = an extra qAllEvents filter that passes the event on
  (`RadFx_Pass`: qAllEvents eats every handled event unless `setEventOutput(false)` is called *while* it is
  handled), timers, chains, `<Form>_SetVisible("lbl", false)` for On show / On hide, `<Form>_BeginAnimation /
  StopAnimation("fx1")`, `<fx>_Completed` when defined. Sizes: `<Form>_VSizes` / `<Form>_VCtl` rows,
  `RadVar_Apply` on the client's resize (its filter is installed after the Anchor / Dock filters, places the
  anchored rows itself, then passes the event); moved controls leave the Anchor rows; `<Form>_CurrentSizes()`.
  Posture / span / fold: RADIDE_POSTURE / RADIDE_SPAN / RADIDE_HINGE. TwoPane (if one is pasted into a
  desktop form): qFrame + `RadPane_Place` (Ratio, RADIDE_HINGE).
- **Flutter (classic forms)**: `lib/radmotion.dart` (RadMotion / RadSb, keyframes = F's `RadKey` of
  `lib/radfx.dart`; one Ticker, works with the test clock) and F's `lib/radlayout.dart` (RadVariant / RadSize /
  RadV / RadTwoPane), copied and exported from `lib/radapp.dart` by the flutter plugin only when a form needs
  them. Designer: `with TickerProviderStateMixin`, `static const _radSbs`, `radMotion.wrap('name', widget)`
  (Transform / Opacity + Listener / MouseRegion for click / hover), `BeginAnimation / StopAnimation /
  SetVisible`; colours / text / visible go through the RadControl objects; reduced motion =
  `MediaQuery.disableAnimations`. Sizes: `final rv = RadVariant.of(context, _radSizes)` in build(), Positioned
  values `rv.pick<double>(...)` (computed from `effective_form` per size), text / visible / colours / font size
  set after the frame when the active sizes change, form BackColor / title picked; `CurrentSizes`.
  TwoPane -> `RadTwoPane` (displayFeatures hinge, Ratio fallback).
- **Kivy**: `radkivyfx.py` (only when needed): `kivy.animation.Animation` sequences per channel; offsets / rotate /
  scale are canvas instructions (PushMatrix / Translate / Rotate / Scale / PopMatrix inserted first in
  canvas.before); colours animate `color` / `background_color` / `card_color`; click = touch up on the
  source, hover = `Window.mouse_pos`; RADIDE_REDUCED_MOTION=1|0, else Windows SPI_GETCLIENTAREAANIMATION
  (Kivy has no system setting of its own). Sizes: the
  screen's `radsizes` ListProperty (MATCH_RT of radide/variants) recomputed on resize; KV positions are
  conditional expressions on `root.radsizes`, other properties set from Python. TwoPane -> `RadTwoPane`
  (FloatLayout; RADIDE_HINGE else Ratio; one pane below 600 dp). No foldable API: documented fallback.
- **React Native (Expo)**: `radfx.js` (rn_runtime.RADFX_JS, only when needed; radapp.js unchanged): `Animated`
  timing sequences (useNativeDriver on Android / iOS) for offsets / scale / rotate / opacity, a JS clock for
  colours / typewriter / Visible; `<FxBox>` (Animated.View, pointer enter / leave for hover); the designer
  overrides `hasHandler` / `fireAny` (click triggers), `componentDidMount` (start), `BeginAnimation /
  StopAnimation / SetVisible`; `AccessibilityInfo.isReduceMotionEnabled()`. Sizes: `radSizes(form, list)` (body
  width, window height) + `placeV` + `useSizes`; TwoPane -> `<TwoPane>` (Ratio, one pane below 600 dp). Expo Go
  has no foldable API: posture 'flat', one screen (documented fallback).
- **WinForms (Visual Studio C# / VB.NET projects)**: `.Designer.cs|vb` is never changed for this. Sidecar
  `Form1.radide.json` (animations, motion, variants, per-control size overrides; read back by `load_form`) and
  the generated partial class `Form1.RadFx.cs|vb` (nested RadFxEngine, Forms.Timer; fallbacks of target
  "winforms": colour blend into the parent, wobble, Bounds; exit animations give the colours back when hidden).
  `OnLoad` override calls `RadFxAttach()` unless the user's Form1.cs|vb overrides OnLoad (then Save reports
  "call RadFxAttach() in it"); sizes on the form's Layout event (moved controls get Anchor Top|Left and their
  per-size spec, menu offset respected); reduced motion = RADIDE_REDUCED_MOTION or SPI_GETCLIENTAREAANIMATION.
  `BeginAnimation / StopAnimation / SetVisible / CurrentSizes`; tests: RADIDE_FX_SELFTEST / RADIDE_FX_CLICK /
  RADIDE_FX_RESIZE. Removing every animation / size deletes both generated files.
- **Web pages (GrapesJS Design View)**: "Animate" / "Animate on" / Delay / Duration traits ->
  `class="radfx radfx-<preset>"` + `data-radfx-trigger` (load | visible | click | hover | timer | manual) /
  `-delay` / `-duration` (also `-source`, `-after`, `-repeat`, `-reverse`, `-color`, `-from` by hand); Save links
  `radfx.css` + `radfx.js` and copies them next to the page (`design.add_radfx`). radfx.css: 15 keyframe presets
  with CSS variables, `prefers-reduced-motion`; radfx.js: IntersectionObserver, click / hover / timer / after
  chains, `radfx.play(el)`. Devices: GrapesJS defaults + Fold6 open / cover, Pixel Fold, Flip6, Surface Duo 2
  spanned; a non-desktop device shows the orange 4 px frame + "This size only: <device>" (CSS edits go into the
  device's @media rule); hinge band / crease drawn for foldables. `.rad-two-pane` (viewport-segment env()
  variables under `@media (horizontal|vertical-viewport-segments: 2)`, two columns from 600 px) and
  `.rad-hide-folded` (`@media (device-posture: folded)`). SuperPreview draws the hinge / segment gap of the
  foldable presets (`preset_hinges`).
- **Error List**: `features/motion_targets.py` adds the fallbacks / notes of `fxtargets.issues` for forms of the
  targets above, and a warning for foreign form formats that cannot keep animations / sizes.
- **Not applicable** (documented, nothing generated): godot / godot3d (scenes animate with AnimationPlayer),
  rust-cargo (no designed forms), web sites without GrapesJS pages (server templates: use the Design View or
  radfx.css by hand), the VB6 `.frm` export (the VB runtime plays animations / sizes from the .form), Delphi /
  Lazarus / Qt .ui / NetBeans foreign forms (their files cannot hold them: Error List warning; the IDE keeps them
  while the form is open). Not done: ad hoc `Animate(target, preset)` from Ring / Flutter / Kivy / RN / WinForms
  code (only the designed animations by id), FontBold per size on Flutter / RN, TwoPane hinge on React Native.
- Tests: `samples/Tests/Motion/Targets/check_targets.py` (pure, Ring run, flutter analyze + test, Kivy run, RN in
  Node via esbuild + stubs, WinForms C# / VB dotnet build + self test on temp copies, web page in QtWebEngine,
  GrapesJS Design View) and `samples/Tests/Variants/Targets/check_targets.py`; samples rebuilt by
  `make_targets.py` in each folder.

## 11. Retro slices - shared file bus and menu (details: docs/RETRO.md)

- After writing into a ROM / binary, call `radide.retro.filebus.file_changed(win, path, source=self)`. Editors
  that show a file expose `retro_path` (and optionally a `retro_watch` list) plus `reload_from_disk()`; they are
  refreshed automatically (the hex editor, tile editor, tile map ...).
- Retro menus go under Tools > Retro via `radide.retro.menu.retro_menu(win)` / `section(win, title)`.
- Emulators (slice emu): `radide.retro.emu.run_rom(path, system=None, debug=False, symbols=None)` -> `RetroProcess` (`alive() / stop() / reload(rom) / monitor() / gdb()`), `detect_system(path)`, `manager.find(id) / ensure(id, download=True)`; errors are `launch.EmuError`. Rebuilt ROMs announced with `file_changed` are hot-reloaded in VICE. Details: docs/RETRO.md "Emulators".
- Apollo AGC / legacy Fortran (slice nasa): project keys `"agc": {"assembler": "auto|builtin|yayul", "run": "emulator|yaagc", "port", "alarms"}` and `"fortran": {"preset": "legacy|f66|dec|strict", "flags"}`; `radide.agc.machine.AgcMachine` (headless CPU + DSKY), `radide.agc.yaagc` (socket packets, `YaAgcLink`), `radide.agc.toolchain.find("yayul"|"yaagc")`, `radide.retro.legacy_fortran` (fields, `to_free_form`, `analyze`, `punch_rows`). Menus: Tools > Retro > Apollo AGC / Legacy Fortran. Details: docs/RETRO.md "Old NASA programs".
