# Integration QA scripts (startup, round 7)

These are small scripts that drive the real IDE (`radide.app.MainWindow`) offscreen. They were written for the
integration QA pass. They use their own test settings (organization `RADIDE-TEST`) and clear them at the end.
Output goes to `%TEMP%\radide-qa` by default; set `QA_OUT` to put it somewhere else. Run them from the repo root:

```
.venv\Scripts\python.exe -u samples\Tests\QA\Integration\smoke_startup.py en
.venv\Scripts\python.exe -u samples\Tests\QA\Integration\smoke_startup.py ar
.venv\Scripts\python.exe -u samples\Tests\QA\Integration\r7_notebook.py
.venv\Scripts\python.exe -u samples\Tests\QA\Integration\r7_vb6class.py
.venv\Scripts\python.exe -u samples\Tests\QA\Integration\r7_3d.py
```

| Script | What it checks |
|---|---|
| `qh.py` | Shared helpers: test QSettings, `check()`, `wait()`, `shot()` (uses `widget.grab()`), `finish()`. `finish()` also fails if the Output window has a Traceback. |
| `smoke_startup.py [en\|ar]` | The IDE starts with the chosen UI language and every `radide/features` module installed. The Output window has no errors. The round 7 menu entries are there. Saves `ide_start.png` and `menus.txt`. |
| `r7_notebook.py` | Opens the Data Science starter notebook and runs every cell: an HTML table and a PNG plot come back. Also checks an error cell, interrupt, the variables list, saving and nbformat validation, restart, `# %%` export, and that closing the tab stops the kernel. |
| `r7_vb6class.py` | Runs a copy of `samples/Tests/VB6/BankClasses` (VB6 class modules, events, `Err.Raise`) with Ctrl+F5 and F5 and checks the expected output lines. |
| `r7_3d.py` | Creates the `playground3d` template for Ursina and for Godot. Ursina runs from the IDE with `RAD3D_HEADLESS=1`; Godot runs with `--headless`. Each run must print the `rad3d-test` line (150 frames, a coin collected). |

Each script prints `PASS`/`FAIL` lines and exits with 0 only when every check passed.
