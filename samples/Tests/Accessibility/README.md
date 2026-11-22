# Accessibility tests

Keyboard-only use, screen readers, contrast / text size, and the accessibility of the programs RAD IDE builds.
See docs/ACCESSIBILITY.md for the keyboard map and the known limits.

| Test | What it checks |
|---|---|
| `test_keyboard_ide.py` | Alt / access keys of the menus, F6 / Shift+F6 / Ctrl+F6, Auto Hide windows with F6 + Esc, Ctrl+Tab, Toolbox (Enter adds a control, group headers), designer keys, Properties grid (no focus trap, Enter / Esc, Events), dialogs (Tab round trip, every field reached, Alt+label key, Esc), visible focus indicator in every theme |
| `test_screen_reader.py` | Accessible names of every interactive widget of the main window and the main dialogs (incl. all tab pages), designer surface (selected control), Properties rows / value editors, Arabic names; real UI Automation tree of an IDE window (Windows platform plugin, off screen) |
| `test_contrast_scaling.py` | WCAG contrast of every theme and palette, the four Windows contrast themes and "follow Windows contrast", focus ring colour, 200 % text in the main dialogs |
| `test_native_a11y.py` | `NativeForm` built into a native radforms exe: TabIndex order, Space / Enter / Alt+letter, UIA names / roles / values / states of standard and Rm controls; RadIDE.Controls (.NET) accessible objects through UIA |

`NativeForm/` is the C (GUI Bridge) program the native test builds.

```
.venv\Scripts\python samples\Tests\Accessibility\test_keyboard_ide.py
```

Each test prints PASS / FAIL lines and a summary; the exit code is the number of failures. Offscreen, own QSettings
organisation `RADIDE-TEST-A11Y` (cleared before and after), only `widget.grab()` pictures, only the processes the
tests start are touched (`A11Y_NO_UIA=1` skips the UI Automation part).
