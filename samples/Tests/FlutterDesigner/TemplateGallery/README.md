# TemplateGallery (Flutter designer sample)

A RAD IDE Flutter project built from the nine screen templates of the Flutter visual designer
(`radide/flutterdesign/templates`), plus a gallery home screen (route `/`) that opens each one.

| Screen | Route | Notes |
| --- | --- | --- |
| Gallery | `/` | list of the templates, gradient header, staggered fade-up |
| Login | `/login` | wave artwork, shadowed input card, gradient button |
| SignUp | `/signup` | gradient with blobs, rounded sheet, outline inputs |
| Onboarding | `/onboarding` | three illustrated pages with page dots |
| Profile | `/profile` | cover image, avatar, stats, photo grid |
| Dashboard | `/dashboard` | balance card, quick actions, transactions |
| Shop | `/shop` | search, category chips, product grid |
| ProductDetails | `/product` | hero image, colour/size pickers, add-to-cart bar |
| Settings | `/settings` | grouped list tiles, switches |
| Chat | `/chat` | message bubbles, input bar |

Buttons are linked with navigation events (`nav:/route`) so you can click through the app.

## Files

- `screens/*.fscreen.json`: the designed screens. Open them in RAD IDE to edit them visually.
- `lib/screens/<screen>.dart`: generated code. It is regenerated each time you save.
- `lib/screens/<screen>_events.dart`: your handler code. Saving never overwrites it.
- `lib/radfx.dart`: the entrance animation helper (RAD IDE's own code, no third-party package).
- `build_sample.py`: rebuilds `screens/`, `assets/` and `lib/` from the templates.
- `check_templates.py`: checks the templates, assets, fonts, themes and animations. With `--analyze` it also runs
  `flutter analyze` on a fresh project made from every template.
- `web/`, `.metadata`: created by `flutter create --platforms=web .`, which is what RAD IDE runs the first time
  you run the app on Chrome.

## Build

```sh
python samples/Tests/FlutterDesigner/TemplateGallery/build_sample.py   # optional: regenerate
cd samples/Tests/FlutterDesigner/TemplateGallery
flutter pub get
flutter analyze        # No issues found
flutter test           # every screen builds and plays its animations
flutter build web      # tested with Flutter 3.41.9
```

## Licences

- Artwork in `assets/images/` was drawn by `radide/flutterdesign/templates/art.py` (abstract shapes made with
  Pillow, fixed seed). It is original and has the same licence as RAD IDE.
- Fonts (Poppins and the other template fonts) load at run time through the `google_fonts` package. They are
  open source, mostly under the SIL Open Font License 1.1. No font files are included here (see
  `OfflineThemeApp` for bundled fonts).
- All screen designs are original. No code or images come from third-party UI kits.
