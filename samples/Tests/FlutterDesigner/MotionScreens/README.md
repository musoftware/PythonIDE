# MotionScreens - Flutter designer motion test project

Two screens designed as widget trees (`screens/*.fscreen.json`) that use every motion feature of the Flutter
designer (`radide/flutterdesign/motion.py`, plan `docs/plans/MOTION_VARIANTS_FOLDABLES.md`, slice F). All designs
are original to RAD IDE.

| Screen | What it exercises |
|---|---|
| `MotionLab` | typewriter title; `FadeTransition` / `SlideTransition` driven by the `intro` timeline (`$timeline`, autostart); shake on tap, pulse on hover, swing on long press; heart beat repeated forever, a bounce run 3 times, a spin started from a button (`trigger: manual`, controller `spinFx`, event `play:spinFx`); colour tint with auto reverse; a keyframes card (opacity, offset, scale, rotation, colour tracks); a `toggle:expanded` button driving an `AnimatedContainer` and an `AnimatedCrossFade` (`$when`) and a fade with `trigger: state:expanded`; `play:intro`; `push:Details?transition=slideUp&ms=400`; screen page transition `fade` |
| `Details` | flipX / flipY / zoomIn entrances, a card that animates when scrolled into view (`trigger: visible`), page transition `scale` |

Generated files: `lib/screens/*.dart` (+ the user's `*_events.dart`), `lib/screens/routes.dart` (the transitions
go through `designedOnGenerateRoute`), `lib/radfx.dart` (RadFx, RadKeyframes, RadFxController, RadRoute,
radDrive / radPlay); `lib/main.dart` is `codegen.standalone_main`.

Checks (from the repository root / this folder):

```
python samples/Tests/FlutterDesigner/MotionScreens/check_roundtrip.py   # valid, Dart -> import -> same screen
flutter pub get && flutter analyze      # no issues
flutter test                            # test/motion_test.dart: maths, triggers, timeline, state, transitions,
                                        # reduced motion (disableAnimations shows the end state at once)
```
