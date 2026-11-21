# Retro / DOS follow-ups

Checks for the issues the retro and DOS testers found after the first QA round:

| Phase | What is checked |
|---|---|
| `mesen` | The portable Mesen 2 `settings.json` RAD IDE creates has NES / SNES / Game Boy port 1 = the standard controller with keyboard keys (arrows, X / Z, Enter, Right Shift / Backspace / Left Shift) and the Xbox pad, and `SingleInstance` off; an existing file is never overwritten; an old RAD-created config without a controller gets a one-time "Apply Controller Defaults" bar that changes only the unset ports; Stella's portable config has keymaps |
| `handoff` | With Mesen's "Single instance" preference a second start exits at once (code 0): `RetroProcess.alive()` follows the window that took the ROM, `stop()` does not close it (skipped when a Mesen not started by the test is open) |
| `tutorial` | DOS lesson blocks (`dos-qbasic`, `dos-pascal`, `dos-c`, `dos-asm`, `dos-batch`) are highlighted and have Try it / Check; Check builds, runs in DOSBox-X and compares the output (and rejects a changed program); Try it opens a QBasic DOS project and runs it captured, the output appears in the Output window; the lesson's Check button passes |
| `i18n` | Every row of File > New Project has an Arabic catalog entry; rows spaced for layout (`NES  (cc65 / ca65)`) use the single-spaced key |

    python samples/Tests/Retro/FollowUps/test_retro_followups.py [mesen handoff tutorial i18n]

Uses the test QSettings (`RADIDE-TEST`), `RADIDE_NO_BROWSER=1`, screenshots with `widget.grab()` only.
