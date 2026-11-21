# Small screens audit

Checks that RAD IDE fits small screens: 1024x600 netbooks, 1280x720 / 1366x768 laptops and
1920x1080 monitors with Windows display scaling of 150 % / 175 %, in English and Arabic (RTL),
Light and Dark.

The fixes live in `radide/screenfit.py`, an application-wide event filter that is installed when
the main window is created:

- a window or dialog that is larger than its screen is shrunk to the available area (taskbar
  excluded, window frame included) and moved fully on-screen; this also repairs a geometry that
  was saved on a big monitor and restored on a small one;
- a dialog whose content cannot shrink that far gets its content in a scroll area (the OK /
  Cancel row stays visible below it); a wizard gets scrollable pages;
- the main window opens maximized when 1280x800 does not fit;
- on a small screen the docked tool windows may be made as low as ~4 text lines, and on a screen
  lower than 700 px the Solution Explorer group joins the Properties tab group on first run.

Screens that are big enough are not touched. `RADIDE_NO_SCREENFIT=1` turns all of it off (used
for the "before" runs).

## Run

```
python samples/Tests/QA/SmallScreens/run_audit.py            # every configuration, every command
python samples/Tests/QA/SmallScreens/run_audit.py --quick    # main window only (~30 s)
python samples/Tests/QA/SmallScreens/run_audit.py --shots --only 1280x720-en,1366x768-ar
```

Options: `--out DIR` (default `%TEMP%\radide-smallscreens`), `--parallel N`, `--theme Dark`,
`--shots` (widget.grab() screenshots of the main window and of large dialogs, never full-screen
captures).

Each configuration runs `audit.py` in its own process with the Qt `offscreen` platform plugin and
a screen of the given size (`offscreen:configfile=screen.json`; the path must be relative because
`C:` would split the platform options), `QT_SCALE_FACTOR` for display scaling, and its own
`RADIDE-TEST-ss-<config>` QSettings, which are cleared at the end. The audit:

1. records the main window's minimum size, frame, toolbars (actions cut off / chevron) and every
   dock's minimum size;
2. opens a copy of `samples/HelloPython`, triggers every menu command (commands that quit, run,
   build, delete, save or go online are skipped; modal `exec()` is replaced by a non-blocking
   show + measure + reject; file / input / message boxes return "cancel");
3. builds every QDialog / QWizard subclass under `radide/` that the walk did not reach;
4. writes `<config>.json` and prints a table: main window minimum vs. screen, windows whose
   minimum is larger than the screen (`min>scr`) and windows shown larger than the screen or
   partly off it (`shown>scr`).

A clean result: `main>scr` = no, `main off` = no, `min>scr` = 0 and `shown>scr` = 0 for every
configuration.
