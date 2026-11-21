# OfflineThemeApp (Flutter designer sample)

Three Flutter designer templates (Onboarding `/`, Login `/login`, SignUp `/signup`) set up to work **offline**:

- **Bundled fonts.** Poppins, Outfit and Nunito were downloaded once from Google Fonts (`radide/flutterdesign/fonts.py`,
  Project > Flutter Fonts in RAD IDE) into `assets/fonts/<Family>/` and registered under `flutter: fonts:` in
  `pubspec.yaml`. Each family's `OFL.txt` licence is copied next to it. The screens' text styles use these
  bundled families, not `google_fonts`, so nothing is downloaded at run time.
- **Project theme.** `screens/app.ftheme.json` (Project > Flutter App Theme) holds the seed colour (#FF6B8A,
  "vibrant" scheme variant), the text font, and themes for buttons, inputs, cards and the app bar. RAD IDE
  generates `lib/theme/app_theme.dart` from it and wires `theme:`, `darkTheme:` and `themeMode:` into
  `lib/main.dart`.
- **Images.** `assets/images/` contains original artwork drawn by `radide/flutterdesign/templates/art.py`.

## Build

```sh
python samples/Tests/FlutterDesigner/OfflineThemeApp/build_sample.py   # optional: regenerate (needs internet once)
cd samples/Tests/FlutterDesigner/OfflineThemeApp
flutter pub get
flutter analyze        # No issues found
flutter test
flutter build web      # the build's FontManifest.json lists Poppins, Outfit and Nunito
```

`web/` and `.metadata` were created by `flutter create --platforms=web .`, the same step RAD IDE runs the first
time you run the app on Chrome.

## Licences

- Fonts: Poppins, Outfit and Nunito are under the SIL Open Font License 1.1. The licence text is in
  `assets/fonts/<Family>/OFL.txt`.
- Artwork and screen designs: original, with the same licence as RAD IDE.
