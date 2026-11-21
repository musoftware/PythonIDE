# LoginFromScratch - Flutter visual designer QA project

A RAD IDE "Flutter App (visual designer)" project used to QA the widget-tree designer end to end.

| Screen | How it was made |
|---|---|
| `screens/SignIn.fscreen.json` | Built **from scratch** in the designer: palette double-clicks + Properties inspector edits (no hand-written JSON). Gradient header with rounded bottom, two hanging-lamp images and a clock icon in a `Stack` / `Positioned`, white rounded card with a soft shadow, two `TextField`s with hints and prefix/suffix icons, gradient `InkWell` button with rounded corners, "Forgot password?" `TextButton`, 7 staggered entrance animations (`RadFx` fadeInDown / fadeIn / fadeInUp, 200-1400 ms). |
| `screens/Profile.fscreen.json` | Imported from the hand-written `qa/hand_profile.dart` (Add New Screen > Import from Dart...), then edited visually (avatar colour/radius, a `Divider`). Its `build()` prelude, the `_badge()` helper and the `setState` closure are kept verbatim in the regenerated `lib/screens/profile.dart`. |
| `screens/Login.fscreen.json`, `Home`, `Dash` | Created by the project template and the template gallery. |

`lib/screens/sign_in_events.dart` contains user code (`debugPrint(...)` in `onLogin`) that survived several
regenerations of `sign_in.dart`.

## Re-running the QA

`qa/qa_login.py` drives the real IDE (`python qa/qa_login.py --real`; offscreen without `--real`, but the live
Flutter canvas needs a GPU and stays blank offscreen). It creates a fresh project in its own folder, builds the
SignIn screen through the palette and inspector, checks the live canvas (widget bounds, real mouse clicks select
the widget under the cursor), runs `flutter analyze`, runs the app with `flutter run -d web-server` (the IDE's
Exact preview) and grabs it, imports `hand_profile.dart`, opens the template gallery and checks the old
absolute-form Flutter flow. Screenshots and `results*.json` go to `qa/out/`.

## Licences

- `assets/images/lamp_long.png`, `lamp_short.png`: original artwork drawn by `qa/make_art.py` (Pillow), part of
  RAD IDE's samples.
- `assets/images/login_waves.png`, `avatar_1.png`: from RAD IDE's own template gallery (abstract shapes drawn by
  `radide/flutterdesign/templates/art.py`).
- `web/` and `.metadata` come from `flutter create --platforms=web` (Flutter's default web icons, BSD licence).
- The design is an original layout inspired by common login-screen patterns; no code or images from any other
  project are included.
