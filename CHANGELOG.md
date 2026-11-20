# Changelog

All notable changes to RAD IDE. Releases are published on GitHub
(https://github.com/musoftware/PythonIDE/releases) for every tag `vX.Y.Z`; the release notes are the
section of this file whose heading starts with `## [X.Y.Z]`.

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
