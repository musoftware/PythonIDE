# Mobile end-to-end journeys

Each journey builds a small mobile app **through the IDE** (offscreen `MainWindow`, harness
[`../e2e_lib.py`](../e2e_lib.py)): New Project dialog, designers, Properties edits, code typed in the editor, Save All,
then the toolchain (analyze, tests, builds, running programs). Every step prints `PASS` / `FAIL` / `SKIP`; screenshots
are taken from IDE widgets (`widget.grab()`), web views and the started programs' own windows (`PrintWindow`).

| Script | App | What it covers |
|---|---|---|
| `journey_flutter.py` | Tasks (Flutter, visual designer) | Mobile > Flutter App (visual designer); Project > Flutter App Theme; 4 designed screens (list with `ListView.builder` + Code item, add, detail, Arabic `Directionality(rtl)`), navigation (`nav:`, `back`, handlers), entrance animations, Phone/Tablet/Desktop sizes with a "This size only" override, device previews (phone, tablet, Galaxy Z Fold6 postures), `shared_preferences` storage written in the events files, `flutter analyze`, 4 widget tests (`flutter test`), Build > Publish engine -> Windows exe run + window screenshot, `flutter build apk --debug` (SKIPs when the Android SDK / licences are not ready). |
| `journey_expo.py` | Notes (React Native / Expo) | Mobile > React Native (Expo) App; phone-frame designer edits, foldable device, Add Form with right-aligned Arabic labels, handlers in the code editor (localStorage), F5 = the IDE's Expo session on the web shown in the Preview (DOM driven: add, reload keeps the note, details, About), `npx expo export --platform web` served from 127.0.0.1 and driven the same way. |
| `journey_kivy.py` | Notes (Kivy) | Mobile > Python Kivy App; designer, Add Form, handlers saving `notes.json`, device sizes; F5's run spec with the runtime's test hooks (`RADKIVY_EXEC`): phone-size window screenshot, add + open a note. Arabic SKIPs (Kivy has no bidi shaping). |
| `journey_mobileforms.py` | Shopping list (phone-frame forms) | Mobile > Flutter App (form designer): Toolbox controls on the phone frame, Click handler, layout sizes (Phone / Tablet / Half-open) with a This size only override, devices incl. foldable postures, generated Dart (`RadVariant` / `rv.pick`) + `flutter analyze` + widget tests, the same form through the React Native and Kivy generators. |

Run one journey or all of them (from the repository root, with the IDE's Python):

```bat
set E2E_OUT=%TEMP%\radide-e2e
.venv\Scripts\python samples\Tests\E2E\Mobile\journey_flutter.py
.venv\Scripts\python samples\Tests\E2E\Mobile\run_mobile.py            :: all four, prints the matrix
```

Results: `%E2E_OUT%\Mobile-<journey>\results.json` (steps, details, screenshot names), `shots\`, `work\` (the
created projects). Exit code = number of failed steps. The first Expo run downloads its npm packages (can take many
minutes); later runs reuse `node_modules`. Toolchains that are missing make their steps SKIP with the reason.

`Projects/` holds the apps the journeys built (TasksApp - Flutter, NotesApp - Expo, KivyNotes - Kivy, PhoneForms - phone-frame forms) without build output, `.dart_tool` or `node_modules`; open one with File > Open Project.
