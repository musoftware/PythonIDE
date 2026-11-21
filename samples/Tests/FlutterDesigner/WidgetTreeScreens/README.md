# WidgetTreeScreens - Flutter designer model test project

A RAD IDE Flutter project (the *Flutter App* template) plus five screens designed as **widget trees**
(`screens/*.fscreen.json`, format in `docs/FLUTTER_DESIGNER.md`). All designs are original to RAD IDE.

| Screen | What it exercises |
|---|---|
| `Login` | gradient header with rounded bottom corners, `Stack` + `Positioned` shapes, Google font (Poppins), fade/zoom/slide-in animations (`RadFx`), text fields with icons in a shadowed card, styled `ElevatedButton`, `Checkbox` bound to a field, `nav:` route |
| `Profile` | `AppBar` with leading + actions, `Card` / `ListTile` / `CircleAvatar` with a network image, `Chip`, extended FAB with `push:Settings`, `BottomNavigationBar`, a `Code` node, screen theme (seed colour) |
| `Settings` | `SwitchListTile`, `CheckboxListTile`, `Slider`, `DropdownButton`, `Switch`, `ExpansionTile`, `Wrap`, `OutlinedButton.icon` with `replace:/login` |
| `ShopTabs` | `DefaultTabController` + `TabBar` / `TabBarView`, `Drawer`, `GridView.count`, `ClipRRect`, `Image.network`, `Hero`, `Opacity`, `PageView`, dark theme with a Google font text theme |
| `IosDemo` | Cupertino widgets, a `Code` node with a designable child (`#{slot:child}`), `$code` property values, extra import, build prelude and class members |

Generated files: `lib/screens/<screen>.dart` (rewritten from the screen file), `lib/screens/<screen>_events.dart`
(handler stubs - user code), `lib/screens/routes.dart`, `lib/radfx.dart`; `lib/main.dart` merges `designedRoutes`.

Checks (from the repository root / this folder):

```
python samples/Tests/FlutterDesigner/WidgetTreeScreens/check_roundtrip.py   # tree -> Dart -> import -> same tree
flutter pub get && flutter analyze      # no issues
flutter test                            # every screen builds and plays its animations
```

Images: `Image.network` / `NetworkImage` load placeholder photos from picsum.photos at run time (nothing is bundled).
Fonts: Poppins and Lato come from the `google_fonts` package at run time (SIL Open Font License).
