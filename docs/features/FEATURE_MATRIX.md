# Feature x output-target parity matrix

Question this answers: *"the IDE has many internal features (motion / animations, layout variants, visual
states ...) - do they all work when the program runs from the IDE (F5), in the frozen IDE, and in the
published exe of every target?"*

Legend: **works** = verified on the running program (test named in the cell) · **works\*** = works with a
documented visual fallback (logged in the build output / Error List, never silent) · **falls back** = the
native builder's `check()` gives a reason and Publish builds the previous kind (bridge / vbrun) instead, so
the feature still works in the published program, only the exe is bigger · **default only** = no reason is
given and the published program shows the designed default (gap) · **n.a.** = the target has no such concept.

Targets:

| Key | Output target | How it was checked |
|---|---|---|
| **F5** | Run from source in the IDE: python-tk / python-qt designers, vb-basic (vbrun) and every GUI-Bridge language (they all build forms with the python-tk generator) | `samples/Tests/Motion/check_runtime.py`, `check_vb6.py`, `samples/Tests/Variants/check_runtime.py`, `check_motion_core.py`, `check_variants_model.py` |
| **Frozen** | The same, inside the frozen `RADIDE.exe` (`tools/build_ide_release.py`) | the frozen build ships `radide/**/*.py` and the whole `radide/runtimes` tree (incl. `radforms_motion.inc`, `vbrt_motion.bi`, `RadMotion.java`, `RadWinForms.cs`); same code paths as F5 |
| **Bridge** | Publish, Python-based (GUI Bridge / vbrun / PyInstaller) | same generated Python runtime as F5 (`radide/motion/runtime_py.py` + `features/states.py` + `variants/runtime_py.py`) |
| **radforms** | Publish native exe, radforms runtime: C, C++, Fortran (`win32_c.py`), Rust (`rust_native.py`), Go (`go_native.py`), Lua (`script_embed.py`), JavaScript / Node.js SEA (`node_sea.py`) | `samples/Tests/FeatureMatrix/check_fm_radforms.py` (FeatureMatrix form, every language) |
| **VB6 FB** | Publish native exe, VB6 -> FreeBASIC (`vb6_freebasic.py`, `vb6fb/rt`) | `samples/Tests/FeatureMatrix/check_fm_vb6.py`, `samples/Tests/Native/VB6/test_native_vb6.py` (Variants_VB6) |
| **.NET** | Publish native exe, WinForms (C#, PowerShell; `dotnet_winforms.py` + `RadWinForms.cs`) | `samples/Tests/FeatureMatrix/check_fm_dotnet.py` (netfx / framework) |
| **Java** | Publish native exe, Swing + jlink (`java_native.py` + `RadSwing.java` / `RadMotion.java`) | `samples/Tests/FeatureMatrix/check_fm_java.py` (via RadTestHook) |
| **Others** | Generators with their own runtimes: Flutter (`radfx.dart` / `radlayout.dart`), Ring Qt, Kivy, Expo (React Native), Web (GrapesJS `radfx.js`), WinForms *source* export | `samples/Tests/Motion/Targets/check_targets.py`, `samples/Tests/Variants/Targets/check_targets.py`, `samples/Tests/FlutterDesigner/MotionScreens`, `ResponsiveScreens` |

## The FeatureMatrix test form

`samples/Tests/FeatureMatrix/fm_project.py` builds ONE form used for every target: `lblTitle` slides in on
load, `lblType` types itself *after* it (chain), `btnShake` shakes on click, `btnMove` moves +60 on click and
then bounces (chain), `btnColor` recolours `pnlBox` (trigger on another control), `pnlTimer` changes colour
every 1.5 s (timer, auto reverse), `btnHover` has a `MouseOver` visual state, `btnAlert` calls
`GoToState("Alert")` (form caption + `lblTitle` state), `btnManual` calls `BeginAnimation("fx8")` (manual
trigger), sizes `compact` (< 400 px: `pnlBox` hidden, title text) and `wide` (>= 700 px: `btnShake` moved),
plus a run with `RADIDE_REDUCED_MOTION=1`. `fm_drive.py` checks all of it on the running program's own
window only: control positions sampled over frames, texts by `WM_GETTEXT`, colours by `PrintWindow` of the
form (no screen capture), the cursor put over `btnHover` with our window topmost and put back, the form
resized with `SetWindowPos`. (This machine has Windows "Show animations" off, so the normal run sets
`RADIDE_REDUCED_MOTION=0`: the runtimes honour the Windows setting otherwise.)

## Matrix (after this change)

| Feature | F5 | Frozen | Bridge | radforms (7 langs) | VB6 FB | .NET | Java | Others |
|---|---|---|---|---|---|---|---|---|
| Animation presets (15) + 8 easings | works | works | works | works\* | works\* | works\* | works\* | works (real transforms) |
| Triggers load / click / hover / timer / after (chains) / show / hide / manual | works | works | works | works | works | works | works | works |
| Reduced motion (env + Windows setting) | works | works | works | works | works | works | works (env only) | works |
| `Animate(control, preset)` ad hoc from code | works | works | works | falls back | falls back | falls back | falls back | target-specific |
| Blend storyboards (`extra["storyboards"]`, `<Name>_Completed`) | works | works | works | works | works (Begin/Stop) | works | works | Ring / WinForms src |
| Visual states: automatic MouseOver / Pressed / Focused / Disabled | works | works | works | works | works | works | works | n.a. |
| Visual states: `GoToState(state[, control])` | works | works | works | works | works | works | works | n.a. |
| Layout variants (size cascade, places + props, `SizeVariantChanged`) | works | works | works | works | works | works | works | works |
| Foldable simulation (`RADIDE_POSTURE` / `SPAN` / `HINGE`) | works | works | works | works | works | works | works | Flutter: real display features |
| Form Opacity | works | works | works | works (layered) | works (layered) | works | works (if supported) | works |
| Child-control Opacity | Qt only | Qt only | Qt only | works\* (colour blend) | works\* | works\* | works\* | works |
| Data binding / data sources | works | works | works | falls back | falls back | falls back | falls back | n.a. |
| Localization (`extra["resources"]`, run-time language) | works | works | works | default only | default only | default only | default only | n.a. |
| Themes (`Theme`) | works | works | works | works | - | works (RmThemeManager) | - | - |
| Modern Rm\* controls (29) | works | works | works | works (modules) | falls back | works (RadIDE.Controls) | falls back | n.a. |
| Menus / status bar / ToolStrip | works | works | works | works (drop-down buttons fall back) | works | works | works (MenuStrip) | - |
| Timers, common dialogs, images / icons | works | works | works | works | works | works | works | - |
| Anchor / Dock | works | works | works | works | works | works | works | works |
| RightToLeft | works | works | works | works | works | works | - | - |
| Per-monitor DPI | works | works | works | works | works | works (scaled) | works | - |
| Control arrays | works (vbrun) | works | works | falls back | works | falls back | falls back | n.a. |

"works\*" for the native targets = the expand() fallback table of `radide/motion/presets.py` (target "py" /
"winforms"): child controls cannot be transparent or rotated, so fade = colour blend into the parent
background, rotate = wobble, flip / scale / pulse = resize around the centre. The same fallbacks as the
python-tk runtime; each one is logged as `Motion: ...` in the build output (and shown in the IDE's Error List).

## Before -> after (motion, visual states, layout variants on the FeatureMatrix form)

| Target | Before | After |
|---|---|---|
| radforms C / C++ / Fortran / Rust / Go / Lua / JS | falls back to the bridge build (`check()`: "states / storyboards / animations (Blend / data) are not supported natively", "visual states / layout variants are not supported natively") | native exe, 21/21 checks per language (see the run below) |
| VB6 FB | falls back to vbrun ("animations / storyboards / visual states / motion presets / layout variants are not supported by the native build yet") | native exe, FeatureMatrix 23/23 (clean run); Variants_VB6 now native |
| .NET WinForms | Visual States / storyboards / per-control states fell back; **animations and form-level variants were silently dropped** (published exe without them) | native exe plays all of it, FeatureMatrix 24/24 (C# netfx + .NET 8, PowerShell) |
| Java Swing | same as .NET (states / storyboards fell back, animations + variants silently dropped) | native exe plays all of it, FeatureMatrix 24/24 |

Counts per target column (the 21 feature rows of the matrix above; "default only" before = the feature was
silently dropped or ignored by the published exe):

| Target | works | works\* | falls back | default only | - |
|---|---|---|---|---|---|
| radforms before | 7 | 0 | 12 | 2 | 0 |
| radforms after | 15 | 2 | 3 | 1 | 0 |
| VB6 FB before | 6 | 0 | 12 | 2 | 1 |
| VB6 FB after | 14 | 2 | 3 | 1 | 1 |
| .NET before | 8 | 0 | 7 | 6 | 0 |
| .NET after | 15 | 2 | 3 | 1 | 0 |
| Java before | 4 | 0 | 8 | 7 | 2 |
| Java after | 12 | 2 | 4 | 1 | 2 |

FeatureMatrix runs (this change): python-tk from source 17/17, inside the frozen IDE 17/17 (0.2.2 build, the
program run with a real Python as Run does); radforms C 23/23, C++ 23/23, Fortran 23/23, Rust 23/23, Go 23/23,
Lua 23/23, JS 23/23 (each = check() clean + native kind + 19 runtime checks + 2 reduced-motion checks); VB6 FB
23/23; .NET C# netfx 24/24, C# .NET 8 24/24, PowerShell 24/24; Java 24/24. Timing-based checks can flake when
the machine is at 100 % CPU (PrintWindow takes 0.1 - 0.7 s then): re-run before suspecting a runtime.

Frozen-IDE findings: the frozen bundle has no `tkinter`, so when no real Python is installed RADIDE.exe cannot
stand in for python-tk programs (Run needs a Python with Tk - the IDE's Python search finds one when present);
`RADIDE.exe` used as Python (`RADIDE_AS_PYTHON=1`) does not exit after an uncaught exception in `-c` code.

## How it works (one contract, five runtimes)

`radide/motion/native_plan.py` turns a form into records (`XR`, `X`, `XT`, `K`, `Q`, `V`, `VL`, `VP`) from
`motion.expand()` (presets -> keyframes with relative values), the Blend storyboards, the visual states and
`variants.model.plan()`. Every native runtime parses the same records and plays them with the semantics of the
IDE's Python runtime (`runtime_py._RadFx`, `timeline._Storyboard`, `states._VisualStates`,
`variants.runtime_py._RadVariants`):

| Runtime | File | Embedded as |
|---|---|---|
| radforms (C core, every C-ABI language) | `radide/runtimes/native/radforms/radforms_motion.inc` (+ hooks in `radforms.c`) | lines of the form description (RCDATA `RADFORMS`) |
| FreeBASIC VB6 runtime | `radide/deploy/native/vb6fb/rt/vbrt_motion.bi` (+ hooks in `vbrt_forms.bi`) | `VBFxRec` lines in each form's setup code |
| .NET | `RadMotion` in `radide/deploy/native/dotnet/RadWinForms.cs` | `this.UseMotion("...")` in the generated form |
| Java | `radide/deploy/native/java/RadMotion.java` | `motion("...")` in `initComponents` |

Program API everywhere: `BeginAnimation(name)`, `StopAnimation(name)`, `GoToState(state[, control])`,
`ApplySizeVariants()`, `CurrentSizes`, `CurrentState`; events `<Form>_SizeVariantChanged`,
`<Storyboard>_Completed`. Forms without motion generate exactly the code they did before.

## Remaining gaps (with the builder's reason)

* `Animate(control, preset)` from user code: the preset builders exist only in the Python runtime -
  radforms: "method 'Animate' ... is not supported by the native runtime"; Java / .NET: "... calls Animate
  (ad hoc presets need the IDE runtime; design the animation with trigger Manual and call BeginAnimation)";
  VB6 FB: translator reason. Publish falls back, the program still works.
* Data binding / data sources: no native data layer ("data binding is not supported natively").
* Localization: the native builders publish the designed default language and give no reason (gap: the
  run-time language switch of `extra["resources"]` exists only in the Python runtime).
* VB6 FB: storyboard `Pause` / `Resume` / `Seek` (only `Begin` / `Stop`); Rm\* controls fall back.
* Java: reduced motion reads only `RADIDE_REDUCED_MOTION` (not the Windows setting).
* Child-control transparency is impossible for Win32 child windows / Swing components: fades are colour blends.
