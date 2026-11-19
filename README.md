# RAD IDE

A Visual Basic style RAD IDE for many languages - and for **several languages in one project**.

Run: `run.bat` (or `.venv\Scripts\python -m radide [project-folder]`).
Samples: `samples/HelloPolyglot` (Python + VB6 + Ring in one project), `HelloVB`, `HelloPython`, `HelloRing`,
`HelloJavaScript`, `HelloCSharp`, `HelloFortran`, `HelloC`, `HelloDart`, `HelloPerl`, `HelloSolution`,
`HelloPHPSite` (complete PHP + SQLite web site).
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
  `Scene_Update`). Sample `samples/HelloGame`.

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
