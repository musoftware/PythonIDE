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
