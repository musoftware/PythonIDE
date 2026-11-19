# RAD IDE

A Visual Basic style IDE for scripting and classic languages: Python, Ring, VB6/BASIC, Fortran, and more via plugins.

Run: `run.bat` (or `.venv\Scripts\python -m radide [project-folder]`).
Samples: `samples/HelloPython`, `samples/HelloRing`, `samples/HelloVB` (rebuild with `tools\make_samples.py`; this
**replaces** those folders).

## Languages

| Plugin           | GUI                  | Runs with                                       | Debugger |
|------------------|----------------------|-------------------------------------------------|----------|
| `python-tk`      | Tkinter              | `python` in PATH (or the IDE's own)             | yes (bdb agent) |
| `python-qt`      | PySide6              | a Python that has PySide6                       | yes (bdb agent) |
| `ring-qt`        | RingQt               | `ring` in PATH or `C:\ring\ring\bin\ring.exe`   | yes (ringvm_settrace agent) |
| `vb-basic`       | Tkinter              | bundled VB6-compatible interpreter (no install) | yes (built in) |
| `fortran-bridge` | GUI Bridge (Tkinter) | `gfortran` (must be installed)                  | no |

The **GUI Bridge** (`radide/runtimes/bridge.py`) gives any language a form: the IDE draws it and the program
talks over stdin/stdout (`EVENT`, `SET`, `GET`, `CALL`, `MSGBOX`, `DONE`). See `radide/runtimes/radgui.f90`.

## Importing existing programs

- **File > Import > Python GUI Program**: runs the program with its event loop disabled, reads the real windows
  (Tkinter or PySide6/PyQt), and creates forms + handlers. Callback code is moved into the new form (globals become
  `self.<Name>`). The original file is kept in `_original/`.
- **File > Import > Visual Basic 6 Project** (`.vbp` / `.frm`): forms, controls (incl. control arrays, menus, fonts,
  colours, cp1256 Arabic text), modules. With the VB6 language the code runs as-is; with other languages it is
  added as commented reference code. OCX controls become placeholders.

## IDE features

- Designer: toolbox, grid/snap, multi-select, containers, component tray, menu editor, undo/redo, clipboard,
  align/size, right-click menus everywhere.
- Properties (categorized/A-Z) and Events (handlers in bold), event args (`e.X`, `KeyAscii`, ...).
- Editor: Arabic/bidi, highlighting, IntelliSense as you type + calltips (Jedi, RingQt index, VB members),
  Find/Replace (Ctrl+F/H), Find in Files (Ctrl+Shift+F), Go to Line (Ctrl+G), Go to Definition (F12),
  comment toggle (Ctrl+/), auto-indent.
- Error List (checked on save, Ctrl+Shift+B) incl. TODO/FIXME tasks; auto-save backups with recovery.
- Debugger: breakpoints (F9/margin), F10/F11/Shift+F11, Locals, Call Stack, Immediate, hover values.
- Project > Build EXE (PyInstaller for Python, ring2exe for Ring).

## Adding a language

Create `radide/languages/<name>.py` with a `LanguagePlugin` subclass and `PLUGIN = MyPlugin()`.
Implement `generate_designer`, `new_code`, `find_handler`, `add_handler`, `run_spec`; set `keywords` /
comment / string settings for highlighting. For debugging set `supports_debug = True` and implement
`debug_spec` with an agent that speaks the protocol documented in `languages/base.py`.

## Known limits

- VB6 interpreter: no `Class` modules / `New` of user classes, GoSub, `Declare` (API) calls; Line/Shape/graphics
  methods are ignored. `CreateObject` needs `pywin32`.
- Ring Immediate window: runtime errors other than unknown variables stop the program.
- Fortran needs gfortran; no debugger for bridge languages yet.
- Menu item renames in the Menu Editor don't rename their handlers.
