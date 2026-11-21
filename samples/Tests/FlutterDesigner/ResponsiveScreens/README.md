# ResponsiveScreens - Flutter designer layout variants and foldables

Two screens with per-size overrides (`variants` / `vprops`, `radide/flutterdesign/variants_fd.py`, plan
`docs/plans/MOTION_VARIANTS_FOLDABLES.md`, slice F) - "change the design for one size without changing the rest".
All designs are original to RAD IDE.

| Screen | What it exercises |
|---|---|
| `Gallery` | sizes Phone (`compact`, <= 599), Tablet (`medium`, 600-1023), Desktop (`expanded`, >= 1024), Half-open (`tabletop`, posture half-opened) and Two screens (`dual`, span dual); per-size padding, title text and style, grid columns; a sidebar hidden on phones and shown again on a half-opened foldable (`$hidden` follows the size order: the later size wins) |
| `MailTwoPane` | `RadTwoPane`: one pane on a phone, ratio split on a tablet, split at the hinge of a dual-screen device |

Generated code uses `lib/radlayout.dart` (RadSize, RadVariant.of(context, sizes) from the MediaQuery size and
display features, `rv.pick`, RadShow, RadTwoPane).

Checks (from the repository root / this folder):

```
python samples/Tests/FlutterDesigner/ResponsiveScreens/check_roundtrip.py   # round trip + variants_fd API
python samples/Tests/FlutterDesigner/ResponsiveScreens/test_designer_ui.py  # designer UI (offscreen, qh.py):
        # This size only edits + undo, markers, sizes bar, foldable postures / hinge, side-by-side, motion editors
flutter pub get && flutter analyze      # no issues
flutter test                            # test/responsive_test.dart: phone / tablet / desktop window sizes, a
                                        # half-opened Galaxy Z Fold6 and a spanned Surface Duo 2
                                        # (tester.view.displayFeatures), RadTwoPane splits
```
