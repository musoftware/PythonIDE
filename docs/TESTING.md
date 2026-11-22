# Testing RAD IDE

RAD IDE is tested by about 180 test scripts under [`samples/Tests`](../samples/Tests/). Each script is a normal
Python program: it drives a part of the IDE (a library, a language plugin, a designer, the real main window, a
toolchain build), prints one `PASS <check>` / `FAIL <check>` / `SKIP <check>` line per check and a summary such as
`41/42 passed`, and **exits with the number of failed checks** (0 = all good).

One runner, [`tools/run_tests.py`](../tools/run_tests.py), **discovers** them by itself (every
`samples/Tests/**/{test_*,check_*,qa_*,smoke_*,*_test}.py`, not `All/`, not files starting with `_`) and runs any
set of them. What a script needs (tier, arguments, timeout) comes from, lowest to highest priority: a guess from
its source (a download -> `network`, a compiler -> `toolchain:<x>`, otherwise `full`; a guess is never `fast`), the `defaults` of `tests.json` files in its folder and parent folders, the central curated
[`tools/tests_registry.json`](../tools/tests_registry.json), and finally the script's own entry in its folder's
`tests.json`. So a new test is picked up the moment it exists - nothing to keep in sync - and its folder can tune it.
Two GitHub workflows use the runner: [`ci.yml`](../.github/workflows/ci.yml) (every push / PR) and
[`nightly.yml`](../.github/workflows/nightly.yml) (every night and on demand).

## Quick entry points

Double-click `run_tests.bat` at the repository root for a menu, or:

| Command | What it runs | Time |
|---|---|---|
| `python tools/run_tests.py smoke` | pyflakes + the tests marked `smoke` (the fastest check of each area, plus any crawler subset / journey a folder marks `"smoke": true`) | about 5-10 min |
| `python tools/run_tests.py changed` | pyflakes + the `fast` / `full` tests of the areas touched by your changes (working tree vs `HEAD`; `--base main` adds `main...HEAD`), the tests in changed test folders, and `smoke` when IDE code changed | depends |
| `python tools/run_tests.py area designer native` | every runnable test of those areas (`run_tests.py areas` lists them: designer, native, vsx, events, robustness, fuzz, a11y, e2e, crawler, features, examples, languages, perf, debugger, asm, dotnet, firmware, cardiag, retro, mobile, ui, collab, vb6, release, tutorials, and every top folder name) | depends |
| `python tools/run_tests.py fast` | the `fast` tier (what CI runs) | about 15 min |
| `python tools/run_tests.py full` | pyflakes + every runnable test (all tiers except manual / project / aggregate / covered), one at a time | hours |
| `python tools/run_tests.py list` / `check` | what was discovered / problems (bad tests.json, missing registry paths, duplicate ids) and the scripts whose settings are only guessed | seconds |

Every run writes `report.html` (open it with `--open`), `summary.md`, `results.json`, `junit.xml` and one log per
test. `changed` uses the path map `CHANGE_MAP` and `area` the folder map `AREAS` at the top of `tools/run_tests.py`.

## The pyramid: tiers

Every discovered script has exactly one tier.

| Tier | What is in it | When it runs | Budget |
|---|---|---|---|
| `fast` | Pure library tests (assemblers, emulators, linters, firmware formats, car diagnostics, motion / variants models, ROM and graphics codecs, crdt) plus a few short offscreen IDE checks (startup smoke with every feature module, VS designer parity, Auto Hide, UI language). No network, no compiler beyond what the IDE ships, every optional toolchain part SKIPs. | CI, every push and PR | < 3 min each, about 15 min total |
| `full` | The offscreen IDE tests (`qh.py` harness): the real `MainWindow` driven like a user - designers, docks, workbenches, end-to-end QA scripts, Live Share over localhost, Examples (scripting), all-languages matrix. Optional toolchains SKIP. | nightly | up to 20 min each |
| `network` | Tests that download: Open VSX / VS Code extensions (VSX), asm-lsp and rusEFI from GitHub, DOS compilers, retro emulators, the DABG game. | nightly | up to 40 min each |
| `toolchain:<name>` | Tests that build with a real toolchain: `mingw` (gcc / gdb / NASM / FASM / gfortran), `dotnet`, `java`, `rust-go` (cargo, go, Lua), `flutter`, `freebasic`, `dos` (DOS compilers + DOSBox-X), `retro` (cc65 and friends), `inno` (Inno Setup), `ghidra`, `all` (every compiled language). | nightly, one job per toolchain | up to 60 min each |
| `gui-real` | The same tests on a real (non-offscreen) desktop: `QA_REAL=1` / `--onscreen` / `--real` variants, where Monaco and WebEngine really render into the screenshots. | by hand on a desktop session | - |
| `manual` | Needs inputs a plain run cannot give (Release/test_upgrade needs the old and new release files). | by hand | - |
| `project` | The sample projects' own pytest suites (PyCalc - fails on purpose for the Test Explorer demo -, Flask, FastAPI, pyproject app). Not IDE tests. | by hand | - |
| `aggregate` / `covered` | `run_all.py` scripts that call other registered scripts (`aggregate`), and the scripts that only make sense inside their `run_all.py` because later steps reuse the projects earlier ones create (`covered`, the Assembly CoreTests family). | never by `--tier all` | - |

`python tools/run_tests.py list` prints every discovered test grouped by tier with its timeout, needs and flags
(`[smoke]`, `[auto]` = settings guessed).

### What each family covers

| Folder | Covers |
|---|---|
| `Assembly/*` | Assembly IntelliSense and LSP, NASM / FASM / MASM / GNU as templates and GUI Bridge forms, line tables and the native debugger, the 8086 emulator (assembler, CPU semantics, samples, STRUC / conditionals / export), the smart linter, runtime checks, CPU view, beginner QA. |
| `CarDiag/*` | OBD-II / ELM327 / ISO-TP link layer, the fault knowledge base, service functions against the Demo car, the car tools in the IDE. |
| `Collab/*` | Live Share: OT / CRDT convergence, WebSocket sessions, two IDE windows editing at once. |
| `Components/*`, `Designer/*`, `UI/*`, `I18n/*` | Component packages, VS2005 / VS2022 designer parity, Auto Hide tool windows, the Arabic UI. |
| `DotNet/*`, `Tutorials/VisualStudioProjects` | .NET solutions (sln / slnx), references, NuGet, shared projects, tools, the VS2022-style windows, the .NET course. |
| `Examples/*`, `OpenFolder/*`, `QA/*` | Every example project opened / built / run / published, Open Folder detection, the all-languages matrix, start-up smoke, motion end-to-end QA. |
| `Firmware/*`, `PE/*` | Firmware formats, checksums, calibration maps, ECU projects, SLEIGH disassembly, Ghidra; the PE / MFC resource workbench. |
| `FlutterDesigner/*`, `Mobile/*` | The Flutter designer (round trips, data widgets, live preview, templates), foldables, Kivy. |
| `Motion/*`, `Variants/*` | Animations and layout variants: models, generated runtimes (Tk, Qt, VB6) and every target. |
| `Native/*` | Native exe builds without Python: C / C++ / Fortran radforms, .NET WinForms, Java, Rust / Go / Lua, RAD Modern controls, VB6 -> FreeBASIC. |
| `Retro/*` | AGC, DOS development, text-mode and game designers, retro dev templates and disassemblers, emulators, ROM / graphics tools, legacy Fortran. |
| `ShellIntegration/*`, `Installer/*`, `Release/*` | Windows shell integration (a TEST registry root only), single instance, the Inno Setup installer, upgrades. |
| `VB6Business/*` | The VB6 business samples running in the VB6 runtime. |
| `VSX/*` | VS Code extensions: market, declarative contributions, the extension host, webviews, workbench APIs. |

## Running tests locally

From the repository root, with the IDE's Python (`.venv\Scripts\python.exe`, which has `requirements.txt`;
`run_tests.bat` picks it automatically). Besides the commands above, the classic filters work alone or on top of
a command:

```bat
python tools\run_tests.py --tier full                  :: one tier
python tools\run_tests.py --tier toolchain             :: every toolchain:<name> tier
python tools\run_tests.py --tier fast,full --skip VSX  :: several tiers, minus a family
python tools\run_tests.py --only CarDiag               :: by name (substring or glob, repeatable)
python tools\run_tests.py --only "Firmware/*core*" -v  :: stream the test output
python tools\run_tests.py area designer --tier fast    :: an area, only its fast tests
```

Useful options: `--report-dir DIR` (default `%TEMP%\radide-test-results\<time>`), `--retries N` (default 1),
`--timeout-scale 2` (slow machine), `--keep-scratch`, `--python PATH`, `--jobs N`. Keep `--jobs 1` (the default)
for anything with a window: offscreen IDE tests still share fonts, the clipboard and some per-user folders.

A single script can always be run directly too (`python samples\Tests\CarDiag\Obd\test_obd_core.py`); the runner
only adds isolation, timeouts, retries and reports.

### What the runner does for each test

* Runs it in its own process from the repository root, with its own scratch folder; `TEMP` / `TMP`, `QA_OUT` (the
  `qh.py` harness output) and any `{scratch}` argument in the registry point into it. Scratch folders of passed tests
  are deleted (`--keep-scratch` keeps them).
* Sets the offscreen environment unless it is already set:

  | Variable | Value | Why |
  |---|---|---|
  | `QT_QPA_PLATFORM` | `offscreen` | no window on the desktop |
  | `QT_QPA_FONTDIR` | `C:\Windows\Fonts` | the offscreen platform has no font database of its own |
  | `RADIDE_NO_BROWSER` | `1` | never open the system browser |
  | `QTWEBENGINE_CHROMIUM_FLAGS` | `--disable-gpu --disable-gpu-compositing` | WebEngine (Monaco) without a GPU |
  | `PYTHONIOENCODING` / `PYTHONUTF8` | `utf-8` / `1` | Arabic text in the output |

* Gives it unique settings: `QA_NAME=<slug>` (the `qh.py` harness uses it as the QSettings application name under
  the `RADIDE-TEST` organisation, so tests never share or touch the real `RADIDE` settings) and
  `RADIDE_TEST_ORG=RADIDE-TEST-<slug>` for tests that read it.
* Enforces the registry timeout. On Windows the test runs in a Job Object: when it ends (or times out) every process
  it started and left running - dev servers, emulators, debuggers - is ended too. Nothing else is touched.
* Writes `results.json`, `summary.md` (also appended to `GITHUB_STEP_SUMMARY` in Actions), `junit.xml` and
  `logs/<nnn>_<name>.log` (a retry gets `_r2`).

The exit code of the runner is the number of failed tests.

### Toolchains

Most toolchains are downloaded by the IDE itself into `%LOCALAPPDATA%\RADIDE\tools` the first time a test needs them
(NASM, FASM, MinGW, Lua, FreeBASIC, DOS compilers, DOSBox-X, emulators); CI caches that folder. The others come
from their official installers: the .NET SDK 8 / 9, a JDK 21 (Temurin), Go, Rust (rustup), Node.js, Flutter,
Inno Setup. The nightly workflow installs exactly what each tier needs. Tests SKIP (not FAIL) the parts whose
optional toolchain is missing, so a `fast` / `full` run on a bare machine is still meaningful.

## Flaky policy

* A failed or timed-out test is run once more. If the second run passes it is reported as **FLAKY**: it does not
  fail the build, but it is listed in the summary (with the log of the failed attempt) and marked
  `<property name="flaky" value="true"/>` in JUnit.
* A flaky test is a bug, either in the IDE (a race) or in the test (a fixed sleep, a timing threshold). Open an issue
  the first time a test is flaky; fix it or move it to a slower tier within a week. Never "fix" a flaky test by
  raising `--retries` in CI.
* Timing assertions (e.g. "re-analysed in < 200 ms") belong in `full`, not in `fast`, unless they have a generous
  margin: CI machines are slower and noisier than a developer machine.

## Adding a test

1. Put the script next to what it tests under `samples/Tests/<Area>/<Name>/`, named `test_*.py`, `check_*.py` or
   `qa_*.py`.
2. Follow the contract: print `PASS name` / `FAIL name  [detail]` / `SKIP name (reason)` lines, end with
   `N/M passed`, and `sys.exit(<number of failures>)`. For IDE tests use the harness
   `samples/Tests/QA/Integration/qh.py` (offscreen, test QSettings, `widget.grab()` screenshots only, `finish()`).
3. Never touch the user's environment: write only into the scratch folder (`TEMP`, `QA_OUT`, or the first
   argument), never into `samples/` or the user's settings / registry; SKIP when an optional toolchain or the
   network is missing; stop every process you start.
4. It is discovered automatically. If the guess (shown by `run_tests.py check` as `AUTO`) is wrong, add a
   `tests.json` next to it:

   ```json
   {"defaults": {"tier": "full", "area": "e2e", "timeout": 900},
    "tests": {"test_a.py": {"tier": "fast", "smoke": true},
              "test_a.py@long": {"args": ["--long"], "tier": "manual"}},
    "ignore": ["check_helper_that_is_not_a_test.py"]}
   ```

   Keys: `tier`, `args` (`{scratch}` = the per-test scratch folder), `timeout` (seconds), `env`, `needs`, `note`,
   `area` (extra areas), `smoke`, `kind`. A key `name.py@variant` adds a second run of the same script.
5. Run it through the runner: `python tools/run_tests.py --only <Name> -v`.
6. Choose the tier honestly: `fast` only when it takes well under 3 minutes on CI, needs no network and no toolchain
   the runner image lacks.

## Continuous integration

* **CI** (`.github/workflows/ci.yml`, push / PR to `main` and `feature/web-workspace`): pyflakes over `radide` and
  `tools` (must be clean), `run_tests.py check` (bad tests.json / registry problems), then the `fast` tier on `windows-latest` with Python 3.12. Reports
  are uploaded as the `test-results-fast` artifact, the summary appears on the run page and the JUnit results as a
  check.
* **Nightly** (`.github/workflows/nightly.yml`, 01:17 UTC and *Run workflow*): one job per tier (`fast`, `full`,
  `network`, every `toolchain:*`), each with its toolchain installed; a failing tier does not stop the others. The
  `Aggregate report` job merges them (`run_tests.py --merge`) into the `nightly-report` artifact. *Run workflow*
  accepts a comma separated list of tiers to run only some of them.
* **Release** (`.github/workflows/release.yml`, version tags) builds and publishes the installer; it is not a test
  workflow.

## Automation channel and end-to-end user journeys (`samples/Tests/E2E`)

The unit / offscreen tests above drive Python objects inside one test process. The bugs users actually hit were in
the seams of the **installed** build (a module missing from the frozen exe, a wrong `PYTHONPATH`, the installer
running while an old IDE was open, extensions not getting the project as workspace folder, published exes missing
data). The E2E journeys therefore run the **real frozen `RADIDE.exe`** and drive it like a user, through an opt-in
automation channel built into the IDE.

### The channel (`radide/automation`)

* **Off by default.** It starts only when the environment has `RADIDE_AUTOMATION=<token>` or the command line has
  `--automation <pipe-name>`. With a token every request must carry it, and only then are the commands that run code
  in the IDE (`exec`, `eval`, `monaco_js`) and extra command modules (`RADIDE_AUTOMATION_PLUGINS`) allowed.
* A `QLocalServer` (a named pipe `\\.\pipe\<name>`, current user only) speaking JSON lines:
  `{"id":1,"cmd":"trigger","args":{"path":"Debug/Start Debugging"},"token":"..."}` ->
  `{"id":1,"ok":true,"result":...}` or `{"ok":false,"error":"...","trace":"..."}`. Handlers run on the GUI thread.
  `"async": true` turns a request into a job (answer `{"job":N}` at once, `job` returns the result later) for
  anything that may block in a modal dialog. Requests keep being served while a modal dialog runs, so a test
  triggers File > New Project asynchronously and then fills the dialog with `dialogs` / `set_value` / `press`.
* Environment: `RADIDE_AUTOMATION_NAME` (pipe name, default `radide-automation-<pid>`), `RADIDE_AUTOMATION_READY`
  (a file written once the pipe listens), `RADIDE_SETTINGS_ORG=RADIDE-TEST-...` (source runs only: test settings).
* Commands (`help` lists them with one line each; 80+):

  | Module | Commands |
  |---|---|
  | `commands_core` | `hello`, `help`, `job`, `wait`, `wait_idle`, `exec`, `eval`, `output`, `errors` (Error List rows), `set_env` (what programs started by the IDE inherit), `settings`, `file_dialog` (queue answers for the next `QFileDialog.get*()`), `auto_dialogs` (answer message boxes by rule), `quit` |
  | `commands_widgets` | `widgets` / `widget` / `exists` (selectors: objectName, class, text, window title, `@win_attr`), `click`, `press_button`, `type`, `key` ("F5", "Ctrl+S"), `set_value`, `select_item` (lists / trees / tables / tabs, `dclick`), `grab` (PNG of any widget or dialog), `focus`, `actions` / `trigger` (menu path "File/New Project...", toolbar, name, shortcut), `dialogs`, `press`, `close_dialog`, `menu_item` (open popup menus) |
  | `commands_ide` | `project`, `open_project`, `open_path`, `new_project` (through the real New Project dialog), `save_all`, `solution_tree`, `open_item`, `tabs`, `activate_tab`, `open_form`, `open_module`, `run_state`, `debug_state` (Locals / Call Stack), `child_pids`, `breakpoint`, `app_info` |
  | `commands_designer` | `toolbox`, `designer_place` (click the Toolbox tool, then click or drag on the form), `designer_controls`, `designer_select`, `designer_dclick` (writes the handler), `designer_drag`, `set_property` / `get_property` (types into the Properties window), `events_tab` |
  | `commands_editor` | `editor_text`, `editor_set_text`, `editor_goto`, `editor_find`, `editor_type` (Monaco's `type` command / key events), `editor_key`, `completion` (the IntelliSense list as shown), `editor_markers`, `monaco_js` |
  | `commands_win32` | windows of the programs the IDE started and of published exes: `win32_windows`, `win32_children`, `win32_grab` (PrintWindow), `win32_click` / `win32_type` / `win32_key` (input state shared with the target thread via `AttachThreadInput`: works for Tk, Qt and Win32 controls without `SendInput`), `win32_set_text`, `win32_text`, `win32_close`, `win32_kill` (only the IDE's own children), `start_process`, `process_status` |

* **Adding commands:** create `radide/automation/commands_<area>.py`, register handlers with
  `@command("name", doc="...")` from `radide.automation.registry` (`token=True` for anything that runs code), add the
  module name to `BUILTIN` in `radide/automation/__init__.py`. A test can also ship its own modules without a
  rebuild: `RADIDE_AUTOMATION_PLUGINS=<dir>` (token runs only) loads every `*.py` there. Nothing else in the IDE
  changes when the channel is off: `app.main()` only checks `requested()`.

### The client and the hidden desktop

`samples/Tests/E2E/radauto.py` (no Qt needed) has `IDE.launch()` / `call()` / `job()` / `py()` / `wait_for()`,
`Report` (PASS / FAIL / SKIP per step with screenshots, `report.json` + `report.md`) and `Desktop`: the IDE is
started on its **own Win32 desktop** (`CreateDesktopW` + `STARTUPINFO.lpDesktop`). Everything it starts - the
program under F5, compilers, published exes - draws there: real windows (PrintWindow screenshots, real Win32
messages), but nothing ever appears on the user's screen and the user's mouse and keyboard are never used. The IDE
itself still runs with `QT_QPA_PLATFORM=offscreen`; `set_env` removes it for the programs it starts when a journey
needs a real Qt window. Isolation: a portable copy of the build (`portable.flag`, settings inside the copy),
`RADIDE_INSTANCE_NAME`, `RADIDE_EXTENSIONS_DIR`, `RADIDE_VSX_ROOT` and `RADIDE_COMPONENTS_DIR` in scratch.

`samples/Tests/E2E/radcli.py launch | call <cmd> '<json>' | py "<code>" | quit` keeps one IDE running for writing
new journeys interactively. `samples/Tests/E2E/run_e2e.py` runs the journeys (see its docstring and
`samples/Tests/E2E/README.md`); tier `manual` (needs a release build).

---

## ملخص بالعربية

* **كل اختبار** في `samples/Tests` برنامج بايثون مستقل يطبع سطر `PASS` أو `FAIL` أو `SKIP` لكل فحص، ثم ملخصًا مثل
  `41/42 passed`، ويخرج بعدد الفحوص الفاشلة (صفر = نجاح).
* **مشغّل واحد** `tools/run_tests.py` يكتشف الاختبارات تلقائيًا (لا توجد قائمة يدوية تتقادم)؛ إعداداتها من تخمين
  من الكود، ثم ملفات `tests.json` في مجلداتها، ثم السجل المركزي `tools/tests_registry.json`.
* **أوامر سريعة سهلة التذكر** (أو انقر مرتين على `run_tests.bat`): `smoke` (5-10 دقائق)، `changed` (ما يخص الملفات التي
  غيّرتها)، `area designer` (مجال معيّن)، `full` (كل شيء مع تقرير HTML).
* **الطبقات (الهرم):** `fast` (سريعة بلا شبكة ولا أدوات بناء - تعمل مع كل push و PR)، `full` (اختبارات واجهة الـ IDE
  الكاملة offscreen - ليليًا)، `network` (تحتاج تنزيلات)، `toolchain:<اسم>` (تحتاج أداة بناء: mingw، dotnet، java،
  rust-go، flutter، freebasic، dos، retro، inno، ghidra، all)، `gui-real` (على سطح مكتب حقيقي)، `manual` و `project`
  (يدويًا).
* **التشغيل محليًا:** `python tools\run_tests.py list` لعرض الاختبارات، و `python tools\run_tests.py fast` للطبقة السريعة،
  و `--tier full` أو `--only CarDiag` أو `--skip VSX` للاختيار.
* **العزل:** كل اختبار في عملية مستقلة بمجلد مؤقت خاص به وإعدادات QSettings خاصة (`QA_NAME`)، ومهلة زمنية، وتُغلق
  كل العمليات التي بدأها عند انتهائه - ولا يُغلق أي شيء آخر.
* **متغيرات البيئة المطلوبة:** `QT_QPA_PLATFORM=offscreen`، `QT_QPA_FONTDIR=C:\Windows\Fonts`، `RADIDE_NO_BROWSER=1`،
  `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --disable-gpu-compositing`، `PYTHONIOENCODING=utf-8` - المشغّل يضبطها
  تلقائيًا.
* **سياسة الاختبارات المتقلبة (flaky):** الاختبار الفاشل يُعاد مرة واحدة؛ إن نجح يُعلَّم FLAKY ولا يُفشل البناء لكنه
  يظهر في التقرير، ويجب فتح مشكلة وإصلاحه أو نقله لطبقة أبطأ خلال أسبوع.
* **إضافة اختبار:** ضعه تحت `samples/Tests/<المجال>/<الاسم>/` باسم `test_*.py` أو `check_*.py`، اتبع عقد PASS/FAIL
  ورمز الخروج، اكتب فقط في مجلد الـ scratch؛ يُكتشف تلقائيًا، وإن كان التخمين خاطئًا أضف `tests.json` بجانبه.
* **التقارير:** `results.json` و `summary.md` و `junit.xml` وسجل لكل اختبار؛ في GitHub تظهر في صفحة التشغيل
  وكـ artifacts. سير العمل `ci.yml` لكل push/PR، و `nightly.yml` كل ليلة لكل الطبقات مع تثبيت الأدوات من مصادرها
  الرسمية وتقرير مجمّع.
