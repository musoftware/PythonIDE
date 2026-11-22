# All languages QA matrix

`test_all_languages.py` creates a project in **every** language / template of the New Project dialog and checks
it end to end: build, run, publish + the published exe, IntelliSense, the form designer, the debugger, and the
same IDE checks inside the frozen release build.

```
.venv\Scripts\python samples\Tests\QA\AllLanguages\test_all_languages.py                       # everything but frozen
.venv\Scripts\python samples\Tests\QA\AllLanguages\test_all_languages.py --lang rust-bridge,c-bridge
.venv\Scripts\python samples\Tests\QA\AllLanguages\test_all_languages.py --group Native --check build,run,publish
.venv\Scripts\python samples\Tests\QA\AllLanguages\test_all_languages.py --lang "asm-*,dos-*" --all-templates
.venv\Scripts\python samples\Tests\QA\AllLanguages\test_all_languages.py --lang vb-basic --check intellisense,designer,debug
.venv\Scripts\python samples\Tests\QA\AllLanguages\test_all_languages.py --lang python-tk --check frozen --frozen-exe <dist>\RADIDE\RADIDE.exe
.venv\Scripts\python samples\Tests\QA\AllLanguages\test_all_languages.py --list
```

Output: one line per step while it runs, then a summary table

```
language | template | build | run | publish kind | exe size | python? | intelli | designer | debug | frozen | result
```

and the failure details; `results.json` (in `--scratch`, default `%TEMP%\radide_qa_all_languages`) keeps every
step's full text and is merged with earlier runs, so subsets can be re-run. Exit code = number of FAIL cases.
SKIP = a toolchain the IDE cannot get by itself, or a feature the language does not offer (e.g. no hover without
a language server); `n/a` = the step does not exist for that language (web sites are not published as an exe).

## What each check family does (`checks/`)

| Module | Family | Checks |
|---|---|---|
| `common.py` | - | projects created like File > New Project (`create_website` / `plugin.create_new_project` / `workspace.create_project`); forms get Button1 + TextBox1 (`QA`) + Label1 and a `Button1_Click` that sets `Label1.Text = "Hi " + TextBox1.Text`, `Form1.Text = Label1.Text` and declares a local variable; processes started by the test (only those are closed/killed); window helpers |
| `pipeline.py` | build, run, publish | `plugin.build_command` (or `py_compile`); the IDE run spec - a form's window must appear and Button1's click must set the title to `Hi QA`; console programs must exit 0; games / emulators / servers must still be running without an error window; web sites: DevServer + HTTP GET 200. Publish = `radide.deploy.build.build()` with build kind auto (native where `radide/deploy/native` has a builder), then the published exe is run the same way; exe size, total size, whether Python is inside |
| `intellisense.py` | intellisense | in the real IDE (offscreen): the plugin's completions, the editor pipeline (`MonacoEditor._complete` = language server + plugin merge) and **typing `M` in the event handler** (Monaco's suggest widget, read from the page DOM) must offer the language's message-box helper; hover, signature help, go to definition, a deliberate error in the Error List / as a Monaco marker, Format Document. Languages without forms: completion in their main file |
| `designer.py` | designer | add a Button, rename it (`btnQa`), double-click creates the handler stub, Properties > Events lists the events with the handler, Save All + reopen |
| `debug.py` | debug | F5 with a breakpoint in `Button1_Click`, the program's window is clicked, the IDE pauses, Locals shows the variable, Step Over, Continue, Stop |
| `frozen.py` | frozen | runs `ide_child.py` (intellisense, designer, run) inside the release `RADIDE.exe` with `RADIDE_AS_PYTHON=1`, so the frozen radide package and its data are used |
| `ide.py`, `ide_child.py` | - | one offscreen `MainWindow` per child process (QSettings org `RADIDE-TEST-QA`, cleared before and after; modal dialogs are closed by a timer) |

## How the GUI is driven

Only the windows of processes the test started are touched, with Win32 messages (no real mouse, no screen
capture): the window `Form1` is found with `EnumWindows` on the process tree; Button1 is the native child window
with that text (Win32, WinForms, Tk) or the deepest child at its design position (Qt, Swing). Tk reads the real
mouse state, so for the click the form is made topmost for a moment and the test thread's input state is attached
to the program's thread with the left button marked down between the press and the release. The result is read
back from the window title.

Environment: `QT_QPA_PLATFORM=offscreen`, `QT_QPA_FONTDIR=C:\Windows\Fonts` for the test itself (removed for the
programs it starts), `RADIDE_NO_BROWSER=1`.

If another program's window covers the whole screen (for example a Windows Security / firewall prompt), Tk forms
cannot receive the click (Tk checks `WindowFromPoint`); the test first moves the program's own window to a free
corner and otherwise reports the step as SKIP ("covered by another window") instead of FAIL. Native Win32,
WinForms, Qt and Swing windows are not affected.
