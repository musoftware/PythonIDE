# End-to-end QA: animations, layout sizes and foldables

These scripts drive the real IDE (`radide.app.MainWindow`) the way a user does. They run offscreen on a 1920 x 1080
virtual screen (`offscreen_1920.json`), use their own test settings (organization `RADIDE-TEST`), clear those
settings at the end, and take screenshots only with `widget.grab()`. The projects they create go to
`%TEMP%\radide-qa\work\motion_e2e_<lang>`, the screenshots to `%TEMP%\radide-qa\shots`.

| Script | What it checks |
|---|---|
| `qa_motion_e2e.py [phases]` | Phases: `tk qt vb js ring flutter kivy expo web fd`. For each project type it uses File > New Project (the real dialog), adds controls, and checks: Animations panel (Add, Move Up + undo, Preview frames, Preview all on load), Add Size... with This size only and Hide on this size, the Properties diamonds, the property and designer menus, the Sizes gallery, Save All and the generated code. Then it runs the result: tk / PySide6 / vbrun / the GUI Bridge host (Node) in a child process, Ctrl+F5 in the IDE for Qt and Ring, ring.exe, the Kivy app, `flutter analyze`, esbuild for Expo, the saved web page in QtWebEngine. Mobile phases use a Galaxy Z Fold6 with Folded / Half-open postures and the hinge warning. The web phase uses the GrapesJS Animate trait, the This size only frame and the hinge. The `fd` phase covers the Flutter designer: Add sizes > Foldable, This size only, the inspector marker, postures and save. Set `QA_LANG=ar QA_THEME=dark` for Arabic + dark (this also checks the Arabic bar labels), or `QA_REAL=1` to use the real display (window moved off-screen). |
| `check_runtime_fixes.py` | Runtime bugs this QA found. (1) Two animations on one property at once, e.g. Slide In + Pulse On load on one button: the button used to stay 80 px off its place. Checked in python-tk, the design-time preview, Ring, and WinForms C# / VB.NET (dotnet). (2) A Ring TwoPane nested in a container split at the wrong place for RADIDE_HINGE. |
| `test_relabel.py` | A live language switch relabels the texts that radide.i18n does not reach: the sizes bar (Edit: / Size:), the device bar (Device: / Posture: / device names), and the Flutter designer and live preview device combos. |

Each script prints PASS / FAIL lines and exits with 0 only when every check passed. Steps whose toolchain is
missing (ring.exe, flutter, node, dotnet, kivy) are skipped.
