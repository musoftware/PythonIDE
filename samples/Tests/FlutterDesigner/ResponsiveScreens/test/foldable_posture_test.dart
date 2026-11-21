// Folded posture detection and RadTwoPane hinge in local coordinates (lib/radlayout.dart, RAD IDE).
//
// Flutter reports no "folded" display feature: a foldable shows the app on its cover screen without any
// fold. RadVariant therefore remembers that a fold / hinge was seen (the device is a foldable) and, before
// that, guesses the cover screen from its shape (very narrow and tall).
import 'dart:ui';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:responsive_screens/radlayout.dart';

const sizes = [
  RadSize('compact', maxWidth: 599),
  RadSize('folded', posture: RadPosture.folded),
  RadSize('tabletop', posture: RadPosture.halfOpened),
];

// Galaxy Z Fold6 inner screen fully open: Android reports a flat fold (vertical crease).
const flatFold = DisplayFeature(
  bounds: Rect.fromLTWH(441, 0, 0, 1104),
  type: DisplayFeatureType.fold,
  state: DisplayFeatureState.postureFlat,
);
// Surface Duo 2 spanned (landscape): a 26 dp hinge.
const hinge = DisplayFeature(
  bounds: Rect.fromLTWH(540, 0, 26, 720),
  type: DisplayFeatureType.hinge,
  state: DisplayFeatureState.unknown,
);

void main() {
  setUp(() {
    RadVariant.resetFoldMemory();
    RadVariant.coverScreenHeuristic = true;
    RadVariant.debugPosture = null;
  });

  test('cover screen shape: folded before any fold was seen', () {
    final v = RadVariant.compute(const Size(360, 880), const [], sizes); // Z Fold6 cover (~23:9)
    expect(v.posture, RadPosture.folded);
    expect(v.active, ['compact', 'folded']);
  });

  test('ordinary phones and tablets are not taken for a cover screen', () {
    for (final s in const [Size(412, 915), Size(360, 800), Size(430, 932), Size(411, 960), Size(800, 1280)]) {
      expect(RadVariant.compute(s, const [], sizes).posture, RadPosture.flat, reason: '$s');
    }
    expect(RadVariant.looksLikeCoverScreen(const Size(880, 360)), isTrue); // landscape cover screen
  });

  test('heuristic off: a narrow tall window stays flat', () {
    RadVariant.coverScreenHeuristic = false;
    expect(RadVariant.compute(const Size(360, 880), const [], sizes).posture, RadPosture.flat);
  });

  test('fold memory: inner screen open, then closed on the cover screen (any shape)', () {
    final open = RadVariant.compute(const Size(882, 1104), const [flatFold], sizes);
    expect(open.posture, RadPosture.flat);
    expect(RadVariant.foldableSeen, isTrue);
    // Pixel Fold cover screen 411 x 797 is not narrow enough for the shape guess - the memory decides
    final closed = RadVariant.compute(const Size(411, 797), const [], sizes);
    expect(closed.posture, RadPosture.folded);
    expect(closed.active, ['compact', 'folded']);
    RadVariant.resetFoldMemory();
    expect(RadVariant.compute(const Size(411, 797), const [], sizes).posture, RadPosture.flat);
  });

  test('half opened and debugPosture still win', () {
    const half = DisplayFeature(
      bounds: Rect.fromLTWH(0, 552, 882, 0),
      type: DisplayFeatureType.fold,
      state: DisplayFeatureState.postureHalfOpened,
    );
    expect(RadVariant.compute(const Size(882, 1104), const [half], sizes).posture, RadPosture.halfOpened);
    RadVariant.debugPosture = RadPosture.flat;
    expect(RadVariant.compute(const Size(360, 880), const [], sizes).posture, RadPosture.flat);
  });

  test('RadTwoPane.localHinge converts window coordinates to the pane', () {
    const h = Rect.fromLTWH(540, 0, 26, 720);
    final full = RadTwoPane.localHinge(h, Axis.vertical, Offset.zero, 1106, 720);
    expect(full, isNotNull);
    expect(full!.$1, const Rect.fromLTWH(540, 0, 26, 720));
    final inset = RadTwoPane.localHinge(h, Axis.vertical, const Offset(100, 56), 900, 600);
    expect(inset!.$1, const Rect.fromLTWH(440, 0, 26, 600));
    // the hinge does not cross a pane lying wholly on the right screen: no hinge split
    expect(RadTwoPane.localHinge(h, Axis.vertical, const Offset(600, 0), 500, 720), isNull);
    // horizontal fold (tabletop)
    final tab = RadTwoPane.localHinge(const Rect.fromLTWH(0, 552, 882, 0), Axis.horizontal, const Offset(0, 80), 882, 900);
    expect(tab!.$1, const Rect.fromLTWH(0, 472, 882, 0));
  });

  testWidgets('RadTwoPane that does not fill the window splits at the hinge (local coordinates)', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(1106, 720);
    tester.view.displayFeatures = const [hinge];
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      Directionality(
        textDirection: TextDirection.ltr,
        child: Padding(
          padding: const EdgeInsets.only(left: 100, top: 40, right: 20),
          child: RadTwoPane(
            start: Container(key: const Key('start'), color: const Color(0xFF2196F3)),
            end: Container(key: const Key('end'), color: const Color(0xFF4CAF50)),
          ),
        ),
      ),
    );
    await tester.pump(); // the post-frame measure of the pane's position
    final start = tester.getRect(find.byKey(const Key('start')));
    final end = tester.getRect(find.byKey(const Key('end')));
    expect(start.left, 100);
    expect(start.right, 540); // ends at the hinge (window x 540), not at 100 + 540
    expect(end.left, 566); // starts after the 26 dp hinge
    expect(end.right, 1086);
  });

  testWidgets('RadTwoPane right of the hinge: ratio split instead of a wrong hinge split', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(1106, 720);
    tester.view.displayFeatures = const [hinge];
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      Directionality(
        textDirection: TextDirection.ltr,
        child: Padding(
          padding: const EdgeInsets.only(left: 580),
          child: RadTwoPane(
            paneMode: RadPaneMode.horizontal,
            start: Container(key: const Key('start')),
            end: Container(key: const Key('end')),
          ),
        ),
      ),
    );
    await tester.pump();
    final start = tester.getRect(find.byKey(const Key('start')));
    expect(start.left, 580);
    expect(start.width, closeTo(263, 1)); // half of the 526 dp pane
  });
}
