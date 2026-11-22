# Changelog

All notable changes to RAD IDE. Releases are published on GitHub
(https://github.com/musoftware/PythonIDE/releases) for every tag `vX.Y.Z`; the release notes are the
section of this file whose heading starts with `## [X.Y.Z]`.

## [0.2.2] - 2026-11-22

### New
- Build > Publish of VB6 (BASIC) projects: translated to FreeBASIC with native Win32 forms - one exe of
  28-150 KB without Python (layout identical to the designer, events with their arguments, control arrays,
  classes, error handling, files, Format); untranslatable code falls back to the VB runtime with file(line) reasons.
- Tool windows: Visual Studio Auto Hide (pin button, edge tabs, slide-out over the editor, Window > Auto Hide All,
  kept across restarts).
- Build > Publish: C, C++ and Fortran GUI programs become one small native exe (C ~80 KB) on radforms, a new
  C runtime (Win32, themes Light / Dark / Office / Metro, owner-drawn control classes, stable C ABI usable from
  any language, static libradforms.a and radforms.lib); existing projects build unchanged.
- Eight complete VB6 business samples of our own (samples/VB6/Business: bank, electricity billing, finance
  ledger, scientific calculator, clinic, logic gate lab, pharmacy, online exam) and many VB runtime fixes found
  with them (MDI events, public form members, ItemData, DAO LastModified, Data control Reposition, ...).

### Fixed
- Build > Publish of Python games: Ursina exes stopped with "No graphics pipe is available!" (Panda3D's display
  library and Config.prc were missing) and then with "No module named 'Scene1_designer'" (scenes loaded with
  importlib) - fixed and checked by running the exes; pygame / Arcade / Kivy publish verified too.
- Rust WinForms projects: the toolbar's Run no longer runs `cargo run` (which shows no window - the forms are
  drawn through the IDE); it runs the project with its forms like F5. Code completion no longer comes back empty
  while rust-analyzer (or any language server) is still indexing, and the IDE's own helpers (msgbox, set, get,
  control names) are listed next to the server's items.

## [0.2.1] - 2026-11-22

### Fixed
- Running or debugging a project with a Python of another version than the IDE's own (e.g. Python 3.14)
  failed in the installed IDE with "Module use of python312.dll conflicts with this version of Python": the
  child Python got the IDE's `_internal` folder (with its compiled modules) on its path. It now imports the
  IDE's helper package through `%LOCALAPPDATA%\RADIDE\pyroot` (a junction to the package only).
- The Events tab of the Properties window was empty for VB6 projects in the installed IDE (the event names
  were read from a module that needs tkinter, which the IDE does not bundle).
- The firmware workbench (map finder / editor, checksums, entropy) needs numpy: now bundled.
- Build > Publish never stops because of a broken native builder module.
- Redesign Form with AI no longer replaces the whole form: the answer is merged into the current form (controls
  matched by name, properties the AI leaves out are kept) and every kind of change can be ticked - positions
  and sizes, texts, other properties, new controls; removing controls or changing their type only when ticked.
  "Arrange / align / sort / رتب" requests tick only positions and sizes.
- Build EXE of VB6 / GUI Bridge programs: the published exe stopped at start with KeyError: 'DataGridView' (the
  built-in control packages were not bundled).
- View menu: choosing a tool window (Properties, Toolbox, ...) always shows it and brings it to the front, like
  Visual Studio (a window covered by another tab was hidden instead); off-screen floating windows come back.
- Build > Publish: C# and PowerShell programs become native WinForms exes without Python - standalone single
  file (default), framework-dependent, or a tiny .NET Framework 4.8 exe; Java becomes Swing with a trimmed
  runtime (jlink + jpackage). Unsupported controls fall back to the previous build with the reasons listed.
- Form designer: Visual Studio parity pass (116 checks) - Format > Align to Grid, Size to Grid, Horizontal /
  Vertical Spacing, Order submenu, menu items greyed like VS; group drag/resize keep spacing; snaplines; Esc
  selects the parent / cancels a drag; Tab cycles; Ctrl/Shift+arrows; rubber band; paste into containers with
  cascade; click-drag to draw a control; Toolbox double-click; no empty undo steps; Lock Controls blocks edits.
- Format > Center in Form moves the selected controls as one group (they were each centred and ended up on
  top of each other); per container, docked controls stay.

## [0.2.0] - 2026-11-22

### Updating
- **Help > Check for Updates** now installs the update: it downloads the setup (or the portable zip),
  checks it against `SHA256SUMS.txt`, closes the IDE the normal way (unsaved work is asked about first),
  installs silently into the same folder and starts the new version. Settings, extensions and projects stay.
- **Help > Install Another Version...** lists every release: go back to an older version when a new one has
  a problem (the installer accepts a downgrade). Portable copies keep the replaced folder as
  `RADIDE_previous` and get **Help > Restore Previous Version**.
- **Check for Updates Automatically** (Help menu, on by default): once a day, a few seconds after start-up.
- The installer removes the previous version's program files before installing (no stale modules after an
  upgrade or a downgrade).

### New
- **VS Code extensions**: Webview views and panels, file system providers, `vscode.diff` tabs with the
  extension's own buttons, tab groups, URI handlers, file decorations, real terminals with shell
  integration, tasks, authentication, custom editors, notebooks and the common built-in commands -
  Claude Code for VS Code runs (sidebar, diffs with Accept / Reject). Install from Open VSX fixed for
  extensions whose `engines.vscode` is newer than the emulated API level.
- **PE / MFC Resource Workbench** (Tools): edit dialogs, menus, strings, accelerators, version info,
  icons, bitmaps and MFC toolbars inside .exe / .dll files; x86/x64 disassembly with in-place instruction
  edits; MFC message maps (classes from RTTI), control -> event handler, retarget handlers; save as a new
  file with a backup.
- **Car diagnostics** (ELM327 / STN / J2534, OBD-II, UDS / KWP, demo car), **Firmware & ECU workbench**
  with built-in SLEIGH disassembly (C166, V850 / RH850, 8051, VLE, RL78 ...).
- **Retro games and old NASA programs** (ROM workbench, Atari 2600 / NES / Game Boy / C64 / ZX projects,
  emulators, Apollo AGC), **DOS development** (FreeBASIC, FPC, Open Watcom, JWasm, DOSBox-X).
- **Assembly** projects (NASM / FASM / MASM / GNU as) with an OllyDbg-style smart editor (66 rules with
  Arabic explanations, CPU view, simulator).
- **.NET like Visual Studio 2022**: NuGet Package Manager + console, references, shared projects, solution
  merge, templates.
- **Flutter visual designer**, animations and per-size layouts (foldables) for many languages, component
  packages for all built-in controls, 35 Arabic courses with CHM help.

## [0.1.0] - 2026-11-21

First public release of RAD IDE - a Visual Basic 2005 style RAD IDE for many languages, and for several
languages in one project. (c) Musoftware (https://musoftwares.com), MIT License.

### Downloads
- `RADIDE-0.1.0-setup-win64.exe` - Windows installer. Installs for the current user by default
  (`%LOCALAPPDATA%\Programs\RADIDE`, no administrator rights) or for all users; Start Menu entry, optional
  desktop icon, optional file associations and "Open with RAD IDE" in Explorer; English and Arabic setup.
- `RADIDE-0.1.0-portable-win64.zip` - unzip and run `RADIDE\RADIDE.exe`. Settings stay in the `settings`
  folder next to the exe (nothing in the registry, nothing registered with Windows).
- `SHA256SUMS.txt` - checksums of both files.

Running Python projects, the Python language server (pylsp), the debugger (debugpy), Jupyter kernels and
Build EXE (PyInstaller) uses a Python 3 installed on the machine (the py launcher / PATH, or the
`RADIDE_PYTHON` environment variable). Other languages need their own compilers/interpreters, as in a
source checkout.

### Features
- **Forms designer** in the VB 2005 style: Toolbox, Properties, Solution Explorer, Output, Locals, Call
  Stack, Immediate; designer zoom, user controls, form localization, menu editor, layouts.
- **19 languages**: VB6 / BASIC (bundled interpreter), Python (Tkinter, PySide6), Ring, C#, PowerShell,
  Java, JavaScript, TypeScript, PHP, C, C++, Rust, Fortran, Go, Lua, Ruby, Perl, Dart - GUI Bridge
  languages get their forms drawn by the IDE.
- **Solutions and References** (Visual Studio style): several projects, one language each, with
  cross-language references through generated wrappers (15 x 15 language pairs tested).
- **Editor and IntelliSense**: Monaco editor, Language Server Protocol client, Emmet, Vim mode,
  formatting, refactoring, Git client.
- **Debugging**: breakpoints, stepping, expandable Locals/Watch, threads, hit counts, logpoints,
  debugpy / gdb / delve / Java adapters, Attach to Process, JavaScript debugging in the preview.
- **Web sites** (WebMatrix / Expression Web style): visual page designer, PHP / Laravel / CodeIgniter /
  WordPress, Django / Flask / FastAPI, front-end frameworks, REST client, database diagrams, publish over
  FTP/FTPS/SFTP.
- **Dynamic project menus** for Laravel, CodeIgniter, WordPress, Composer, Django, Flask, FastAPI,
  JavaScript, .NET, Java, Ruby, mobile, native and game projects.
- **Mobile apps and games**: Kivy apps, Flutter projects, pygame scene editor with physics and particles,
  3D scenes (Ursina), Python -> GDScript.
- **Import**: VB6 projects, Python GUI programs, Qt .ui, Delphi/Lazarus, Visual Studio solutions and
  programs from .exe / .dll.
- **Reports** (Crystal Reports style) with barcodes, QR codes, PDF / Excel export; data binding to
  databases (Data Sources window); Jupyter notebooks.
- **AI** chat and editor actions, **Live Share** style collaboration sessions, tutorials viewer and CHM
  help (Arabic courses).
- **Publish / Create Installer** for your own programs (PyInstaller + Inno Setup).
- IDE display language: **English / العربية**.
- Help > Check for Updates reads the latest GitHub release.
