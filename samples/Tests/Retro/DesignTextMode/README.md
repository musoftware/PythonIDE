# DOS Text-Mode Designer tests

Tests of `radide/retro/design/textmode` (the VB-style designer for DOS text-mode screens, its code generators and
run-times, the ANSI art editor) and `radide/features/dos_designer.py`. See docs/RETRO.md, section
"DOS text-mode designer".

| file | what | needs |
|---|---|---|
| `test_core.py` | model (names, validation, containers, JSON), renderer (borders, titles, shadows, joined separators, focus colours, RLE), ANSI / BIN / TXT round trips + SAUCE, user code regions kept / orphaned code commented out in all four languages, the asm program run in RAD IDE's 8086 emulator compared cell by cell with the run-time simulator after 13 key sequences | nothing |
| `test_dosbox.py` | the sample [`../DesignTUI_Contacts`](../DesignTUI_Contacts/) built with FreeBASIC (DOS) and its user code exercised in DOSBox-X (message box, adding a contact, menus, second screen); the same screens generated for FreeBASIC, Free Pascal (i8086-msdos), OpenWatcom C and 16-bit asm, built and run in DOSBox-X; each screen is a B800 dump written by the program itself (`PROG /DUMP`, or `/DUMPKEYS` after keys typed by a generated key-stuffer .COM) and must equal the designer's rendering / the simulator. The splash screen is checked in the 8086 emulator. | the compilers and DOSBox-X (downloaded on first use; a target is SKIPPED offline) |
| `test_ui.py` | the IDE (qh.py, QSettings `RADIDE-TEST`, `widget.grab()` screenshots): New Project > DOS Text-Mode Forms App, the designer tab (drag a window with its controls, undo, draw a text box, Properties), saving regenerates MAIN.C, double-click on an event opens the handler, unsaved user code survives regeneration, Test Run, the ANSI editor (box + line joins, text, fill, undo, .ans with SAUCE, PNG), Use as Splash Screen, Add Screen | PyQt6 |

Run all: `python samples/Tests/Retro/DesignTextMode/run_all.py` (`--no-download`, `--skip-ui`).

Results on the development machine (Windows 11, FreeBASIC 1.10.1 DOS, FPC 3.2.2 i8086-msdos, OpenWatcom v2 2026-11-01, JWasm 2.21,
DOSBox-X 2026.10.01): `test_core` 48/48, `test_dosbox` 39/39, `test_ui` 34/34.
