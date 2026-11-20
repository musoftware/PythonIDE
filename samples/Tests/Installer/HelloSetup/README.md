# HelloSetup - Build > Publish / Create Installer

Tests the installer feature (round 6): `radide/deploy/build.py` + `radide/deploy/inno.py` +
`radide/features/installer.py`.

- A one-form python-tk program with a ready `publish.json` (name "Hello Setup", version 1.0.0, per-user
  install, English + Arabic setup pages, a license page from `LICENSE.txt`, desktop + Start menu shortcuts).

**Try it in the IDE:** open this folder, **Build > Publish / Create Installer...** (Ctrl+Alt+F5), look at the
three tabs, press **Publish**. The Output window shows the PyInstaller build and the Inno Setup compile;
`Publish\HelloSetup-1.0.0-setup.exe` is made (Inno Setup is downloaded once if it is missing). Run the setup:
it installs without admin rights into `%LOCALAPPDATA%\Programs\Hello Setup` and is listed in
*Apps & features*, where it can be uninstalled.

**Automatic check:** `..\..\..\..\.venv\Scripts\python.exe tests\test_setup.py` builds a copy in %TEMP%,
installs it silently (`/VERYSILENT /CURRENTUSER /DIR=...`), starts the installed program, uninstalls it
silently (`unins000.exe /VERYSILENT`) and checks that the files and the Apps & features entry are gone.
Delete the `Publish` folder after trying it in the IDE to keep the sample clean.
