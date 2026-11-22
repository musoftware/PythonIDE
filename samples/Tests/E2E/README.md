# E2E user journeys (the real frozen RADIDE.exe)

These tests drive the **release build** of RAD IDE the way a user does - menus, Toolbox, Properties window, code
editor, F5, the running program's own window, Publish, the installer - through the opt-in automation channel
(`radide/automation`, see `docs/TESTING.md` > "Automation channel"). Nothing appears on the user's screen: the IDE
and everything it starts run on a separate hidden Win32 desktop, the IDE itself offscreen.

| File | What |
|---|---|
| `radauto.py` | client: `Desktop` (hidden desktop), `IDE.launch/call/job/py/wait_for`, `Report` (PASS / FAIL / SKIP + screenshots) |
| `radcli.py` | keep one IDE running and send commands by hand (writing new journeys) |
| `e2e_common.py` | portable copy of the build, IDE start, the per-language "hello app" flow, native / installer steps |
| `run_e2e.py` | the runner + J1 / J2 |
| `journeys_more.py` | J3 existing projects, J5 debugger, J7 Arabic / dark theme, J8 designer under load, J10 two IDE processes at once |
| `journey_claude.py` | J4 Claude Code extension (cached .vsix, fake CLI; no real conversation) |
| `journey_install.py` | J6 installer: per-user install, Check for Updates -> Update Now, Install Another Version, setup while the IDE runs, uninstall |
| `journey_fullapp.py` | J9 "Customer Manager": a complete 3-form Python Tk app with menu, status bar, SQLite, validation, search, CSV export, settings; run, debug, Error List, publish, install, uninstall |

## Running

```bat
:: 1. a release build (about 15-40 minutes; --work reuses the PyInstaller folder)
python tools\build_ide_release.py --no-zip --out %TEMP%\e2e\release --work %TEMP%\e2e\build-ide
:: the same build as a higher version, for the update journey (J6): only Inno Setup runs
python tools\build_ide_release.py --reuse --version 0.2.4 --no-zip --out %TEMP%\e2e\release024 --work %TEMP%\e2e\build-ide

:: 2. the journeys (all, or --only J1,J9; --langs vb,c,csharp for J2)
python samples\Tests\E2E\run_e2e.py %TEMP%\e2e\run --onedir %TEMP%\e2e\build-ide\dist\RADIDE ^
       --setup %TEMP%\e2e\release\RADIDE-0.2.3-setup-win64.exe --next-setup %TEMP%\e2e\release024\RADIDE-0.2.4-setup-win64.exe

:: developing a journey against the source tree (fast, no build)
python samples\Tests\E2E\run_e2e.py %TEMP%\e2e\src --source --only J1
```

Reports: `<scratch>\report\summary.md`, `<scratch>\report\<J>\report.md|json` and the screenshots next to them
(IDE widgets via `grab`, the program's own windows via PrintWindow). The exit code is the number of failed steps.

Isolation: a portable copy of the build (`portable.flag`: settings, foreign-project state and extensions inside the
copy), its own single-instance name, extension / VS Code extension / component folders in scratch; J6 installs
per user into `<scratch>\inst` only (it refuses when RAD IDE is already installed for this user elsewhere), with
LOCALAPPDATA in scratch and the test settings organisation `RADIDE-TEST-E2E-J6`, and uninstalls at the end.
Programs and setups are started only by the test; nothing else is closed.
