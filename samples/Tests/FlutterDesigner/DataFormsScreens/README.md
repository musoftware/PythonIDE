# DataFormsScreens - Flutter designer data widgets test project

Three designed screens (`screens/*.fscreen.json`, written by `make_screens.py`) for the data widgets of the
Flutter designer (`radide/flutterdesign/datawidgets.py`, docs/FLUTTER_DESIGNER.md section 1.7). All designs and
the Lottie animation (`assets/animations/pulse.json`) are original to RAD IDE.

| Screen | What it exercises |
|---|---|
| `Catalog` | `Text.rich` app bar title, `RichText` with styled spans (italic + text shadow), `ListView.builder` with sample `items` and a template reading `item` / `index`, `GridView.builder` (`gridDelegate`) |
| `SignUp` | named `Form` (`GlobalKey<FormState>`, autovalidate), `TextFormField` validator rules (required, email, minLength, maxLength, regex, custom messages), custom validator handlers (`checkPhone` after the rules, `checkPromo` alone), `RadioGroup` with `RadioListTile` / `Radio`, buttons `validate:form1:onSubmit` and `validate:form1` |
| `Pulse` | a repeating timeline on `Container.width`, `Opacity.opacity` and `Text.maxLines` (generated through `AnimatedBuilder`), `Lottie.asset` |

`lib/screens/sign_up_events.dart` is the hand-written user file (validator handlers, `onSubmit`).

Checks (from the repository root):

```
python samples/Tests/FlutterDesigner/DataFormsScreens/make_screens.py        # (re)writes screens + lib/
python samples/Tests/FlutterDesigner/DataFormsScreens/check_roundtrip.py     # Dart -> import -> same tree, same code;
                                                                             # hand Dart: shadows, withValues, MaterialApp(home:)
python samples/Tests/FlutterDesigner/DataFormsScreens/test_designer_data.py  # inspector editors, ctor switches, stubs
python samples/Tests/FlutterDesigner/DataFormsScreens/test_live_data.py      # live host: templates, radios, Lottie, theme refresh
python samples/Tests/FlutterDesigner/DataFormsScreens/test_exact_coldstart.py 15 --watchdog off   # exact mode cold starts
cd samples/Tests/FlutterDesigner/DataFormsScreens && flutter pub get && flutter analyze && flutter test
```
