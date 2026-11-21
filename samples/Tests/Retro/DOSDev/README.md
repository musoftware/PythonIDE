# DOS development tests (`radide/retro/dos`, `radide/languages/dos_*.py`, `radide/features/dos_ide.py`)

| test | what |
|---|---|
| `test_dos_toolchains.py` | downloads FreeBASIC (DOS), Free Pascal i8086-msdos, Open Watcom v2, JWasm, CWSDPMI (official sources, SHA-256 recorded; skipped offline), finds DOSBox-X through `radide.retro.emu`, re-assembles the helper programs (`helpers_src/*.ASM`) and compares them with the embedded bytes, own-copy paths for QBasic, DOSBox-X debugger configuration |
| `test_dos_intel.py` | interrupt hovers (INT 21h/10h/16h/33h/1Ah with the function taken from `mov ah, ..`, `R.AH := ..`, `r.h.ah = ..`), QBasic / Crt / conio hovers, completions, signature help, outline, F12, every compiler's message parser |
| `test_dos_templates.py` | all 26 templates: New Project, build a real MZ / COM program, run it headless in DOSBox-X with keys stuffed (`RADKEYS`), output redirected and the screen saved (`RADSCR` / `RADCAP`), compare; mode 13h frames of the Pascal / C / assembly demos; Error List rows (file:line) for a broken source of each compiler; `run.py --capture` |
| `test_dos_compat.py` | the original old-style samples in `../DOSOldSources` (line-numbered QBasic, Turbo C with BGI + conio, Turbo Pascal with Crt / Dos, MASM / TASM `DOSSEG`): Open Folder detection, build with the free compilers, run in DOSBox-X; warnings for BGI drivers, TP units without source, PLAY / SOUND; VB6 / Delphi files are not taken |
| `test_dos_ide.py` | the IDE (qh.py, QSettings "RADIDE-TEST", `widget.grab`): New Project "DOS" group, open a project, DOS Programming menu, Build -> EXE, Error List rows, captured run + Last DOS Screen, settings / toolchains / interrupt reference dialogs, hover, F5 / Ctrl+F5 specs, Open Folder |

`python run_all.py` runs them all (about 2 minutes once the toolchains are downloaded; the first download is
about 330 MB). Work folders go to `%TEMP%\radide-dosdev` and `%TEMP%\radide-qa\work\dosdev`.
