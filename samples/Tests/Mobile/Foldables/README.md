# Foldables (designer)

Foldable / dual-screen devices in the phone form designer (plan `docs/plans/MOTION_VARIANTS_FOLDABLES.md`,
slice E; contract `docs/CONTRACTS.md` 10.8).

- `FoldDemo/` - a Flutter project with two forms:
  - **MasterDetail** on a *Galaxy Z Fold6*: AppBar + a **TwoPane** (list on the left, details on the right).
    Click *Folded* in the device bar: the form becomes the cover screen and only the first pane is shown;
    *Half-open* / *Landscape*: the panes split exactly at the fold.
  - **DuoHinge** on a *Surface Duo 2* (landscape, spanned): `Button1` lies across the 26 dp hinge - the designer
    outlines it in red and the Error List shows "Controls cross the hinge: ...". Move it to one side and the
    warning goes away.
- `check_devices.py` - pure checks (no window): presets, sizes per posture, `hinge_rect`, the TwoPane rule,
  hinge conflicts, the Posture property, SuperPreview presets, Flutter / Kivy / Expo generation with a TwoPane.
- `test_hinge_ui.py` - the IDE offscreen (qh.py harness, QSettings `RADIDE-TEST`): posture buttons, form size
  per posture + undo, hinge layer, TwoPane split, `PhoneChrome.preview()`, red outline, Error List, menu item,
  Toolbox icon. Grabs of the designer per posture go to `%TEMP%\radide-qa\shots`.

```
python samples/Tests/Mobile/Foldables/check_devices.py
python samples/Tests/Mobile/Foldables/test_hinge_ui.py
```
