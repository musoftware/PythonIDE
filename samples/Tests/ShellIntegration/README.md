# Windows shell integration and single instance

Tests for `radide/shell_integration.py` (file associations, "Open with", Explorer menus, shortcuts,
Uninstall entry), `radide/single_instance.py` (one IDE window, paths handed over) and the
Tools > Options > Environment > "Windows integration" group.

They never touch the real `HKCU\Software\Classes`: the registry root is redirected with
`RADIDE_SHELL_ROOT=Software\RADIDE-TEST-Shell\Classes` (and `RADIDE_SHELL_SHORTCUTS=<scratch>`), the IDE
settings use the `RADIDE-TEST` organisation and the single-instance tests use their own pipe name
(`RADIDE_INSTANCE_NAME`), so a running RAD IDE is never contacted.

| Script | What it checks |
|---|---|
| `test_shell_registry.py [scratch]` | every planned key/value is written; `.radsln` takes the default (old value restored on unregister), `.form` with another owner keeps it; source files only get `OpenWithProgids`; Start Menu shortcut; an existing shortcut is not overwritten; unregister leaves the test tree **identical** to before; a value edited by the user afterwards is kept; `python -m radide --register / --shell-status / --unregister --quiet`; partial options. |
| `test_single_instance.py [scratch]` | real processes (`si_child.py`): a 2nd launch hands a text file (`--line 3`), a project, a form, a plain folder and two files at once to the 1st and exits without a window; `--new-window` opens its own window. |
| `test_options_ui.py [scratch]` | the Options group: Register / Unregister buttons, Apply re-registers changed choices, the "Open files in the running RAD IDE window" setting, Arabic translations. |

Run with `.venv\Scripts\python samples\Tests\ShellIntegration\<script>.py`.

To try it for real (writes your own `HKCU`): `run.bat --register` (or Tools > Options > Environment >
Register), then right-click any file > "Open with RAD IDE"; `run.bat --unregister` removes everything.
