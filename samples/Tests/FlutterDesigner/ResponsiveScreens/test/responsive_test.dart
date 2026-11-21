// Flutter designer layout variants (RAD IDE): per-size overrides, RadShow, foldable postures, RadTwoPane.
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:responsive_screens/radlayout.dart';
import 'package:responsive_screens/screens/routes.dart';

Future<void> show(WidgetTester tester, String route, Size size, [List<DisplayFeature> features = const []]) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = size;
  tester.view.displayFeatures = features;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(key: UniqueKey(), routes: designedRoutes, initialRoute: route));
  await tester.pumpAndSettle();
}

int columns(WidgetTester tester) {
  final g = tester.widget<GridView>(find.byType(GridView));
  return (g.gridDelegate as SliverGridDelegateWithFixedCrossAxisCount).crossAxisCount;
}

// Galaxy Z Fold6 inner screen half opened (tabletop: horizontal crease) and Surface Duo 2 spanned.
const fold = DisplayFeature(
  bounds: Rect.fromLTWH(0, 552, 882, 0),
  type: DisplayFeatureType.fold,
  state: DisplayFeatureState.postureHalfOpened,
);
const hinge = DisplayFeature(
  bounds: Rect.fromLTWH(540, 0, 26, 720),
  type: DisplayFeatureType.hinge,
  state: DisplayFeatureState.unknown,
);

void main() {
  test('RadVariant.compute matches like the designer (later sizes win)', () {
    const sizes = [
      RadSize('compact', maxWidth: 599),
      RadSize('medium', minWidth: 600, maxWidth: 1023),
      RadSize('tabletop', posture: RadPosture.halfOpened),
    ];
    final a = RadVariant.compute(const Size(400, 800), const [], sizes);
    expect(a.active, ['compact']);
    final b = RadVariant.compute(const Size(882, 1104), const [fold], sizes);
    expect(b.active, ['medium', 'tabletop']);
    expect(b.posture, RadPosture.halfOpened);
    expect(b.fold, Axis.horizontal);
    expect(b.pick(1, const [RadV('medium', 2), RadV('tabletop', 3)]), 3);
    final c = RadVariant.compute(const Size(1106, 720), const [hinge], sizes);
    expect(c.span, RadSpan.dual);
    expect(c.fold, Axis.vertical);
    expect(c.hinge, const Rect.fromLTWH(540, 0, 26, 720));
  });

  testWidgets('phone: compact overrides, sidebar hidden', (tester) async {
    await show(tester, '/', const Size(400, 800));
    expect(find.text('Phone layout'), findsOneWidget);
    expect(find.text('Sidebar'), findsNothing);
    expect(find.textContaining('Half-open'), findsNothing);
    expect(columns(tester), 2);
  });

  testWidgets('tablet: medium overrides', (tester) async {
    await show(tester, '/', const Size(800, 1280));
    expect(find.text('Tablet layout'), findsOneWidget);
    expect(find.text('Sidebar'), findsOneWidget);
    expect(columns(tester), 3);
    final pad = tester.widget<Padding>(find.ancestor(of: find.byType(Row), matching: find.byType(Padding)).first);
    expect(pad.padding, const EdgeInsets.all(24));
  });

  testWidgets('desktop: expanded overrides the title text and style', (tester) async {
    await show(tester, '/', const Size(1280, 800));
    expect(find.text('Gallery - desktop'), findsOneWidget);
    expect(tester.widget<Text>(find.text('Gallery - desktop')).style?.fontSize, 28);
    expect(columns(tester), 4);
  });

  testWidgets('foldable half opened: tabletop wins over medium and shows again what compact hid', (tester) async {
    await show(tester, '/', const Size(882, 1104), const [fold]);
    expect(find.text('Tabletop layout'), findsOneWidget);
    expect(find.textContaining('Half-open'), findsOneWidget);
    expect(find.text('Sidebar'), findsOneWidget);
  });

  testWidgets('dual screen: span dual, RadTwoPane splits at the hinge', (tester) async {
    await show(tester, '/', const Size(1106, 720), const [hinge]);
    expect(columns(tester), 2);
    await show(tester, '/mail', const Size(1106, 720), const [hinge]);
    final list = tester.getRect(find.byType(ListView));
    expect(list.width, 540);
    expect(tester.getRect(find.text('Message')).left, greaterThan(566));
  });

  testWidgets('RadTwoPane: one pane on a phone, ratio split on a tablet', (tester) async {
    await show(tester, '/mail', const Size(400, 800));
    expect(find.text('Inbox'), findsOneWidget);
    expect(find.text('Message'), findsNothing);
    await show(tester, '/mail', const Size(1000, 700));
    expect(find.text('Message'), findsOneWidget);
    expect(tester.getRect(find.byType(ListView)).width, closeTo(400, 1));
  });
}
