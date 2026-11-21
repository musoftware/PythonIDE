# PE / MFC Resource Workbench tests

**MiniMfc** (`src/`) is a small dialog program built with MSVC for x86 and x64 (`build.py`; the results are in
`prebuilt/MiniMfc32.pe` / `MiniMfc64.pe`; the `.pe` extension keeps them out of the `*.exe` ignore rule). It has
every resource type the workbench edits (DIALOGEX + DIALOG, MENU, accelerators, string table, VERSIONINFO, icon,
bitmaps, manifest, RCDATA, MFC `TOOLBAR` and `DLGINIT`). It re-creates MFC's message maps (the same
`AFX_MSGMAP` / `AFX_MSGMAP_ENTRY` layout, `DECLARE_MESSAGE_MAP`, a virtual `GetMessageMap`, RTTI and the
dispatcher), so editing a map entry changes what the program does, without needing the MFC libraries.

| File | What |
|---|---|
| `test_pe_core.py` | library test (radide/pe): parse, edit dialog / string / menu / version / accelerators, retarget / remove / add map entries, instruction patch limits, undo / redo, save, re-parse, `.rc` round trip, then **runs** the edited exes through `winrun.py` |
| `qa_pe_workbench_ide.py` | the workbench inside the IDE (offscreen, `RADIDE-TEST` settings, `widget.grab()` screenshots in `%TEMP%\radide-qa\shots`) |
| `winrun.py` | starts an exe, clicks buttons / sends commands through Win32, reads control text; closes only what it started |
| `build.py` | rebuilds `prebuilt/` when Visual Studio's C++ tools are installed |

    .venv\Scripts\python samples\Tests\PE\MfcResources\test_pe_core.py
    .venv\Scripts\python samples\Tests\PE\MfcResources\qa_pe_workbench_ide.py

Try it by hand: copy `prebuilt/MiniMfc32.pe` to `MiniMfc32.exe`, open it in RAD IDE (Tools > PE / MFC Resource
Workbench...), double-click *Button 1* in dialog 101, retarget its handler in MFC Events to Button 2's handler, Save
As, and run the saved program.
