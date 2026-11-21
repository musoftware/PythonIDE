# Flutter_Foldable

A plain Flutter app whose `TwoPane` (lib/main.dart) follows the TwoPane rule of `docs/CONTRACTS.md` 10.8: a
separating hinge / half-opened fold from `MediaQuery.displayFeatures` splits the screen at its edges, a wide
window shows both panes at the ratio, a narrow one only the first pane.

`check_foldable.py`:
1. writes `test/devices_gen.dart` from `radide/devices.py` (every foldable preset x orientation x posture, its
   display features and the panes Python computes);
2. runs `flutter pub get`, `flutter analyze` and `flutter test` - the widget tests set
   `tester.view.displayFeatures` / `physicalSize` and compare the panes (offline, no device needed);
3. if the Android SDK is installed (and `RADIDE_SKIP_EMULATOR` is not 1): creates the AVD **RADIDE_Fold** when
   missing (other AVDs are never touched), boots it headless on port 5600, switches Folded / Half-open / Flat
   with `features.mobile.set_posture`, checks the device state and the screen size, then stops that emulator.

```
python samples/Tests/Mobile/Flutter_Foldable/check_foldable.py
```
Run the app on the foldable emulator from the IDE: Build > Mobile App > Create Foldable Emulator, then choose
"Android emulator: RADIDE Fold" in the Device box and press F5.
