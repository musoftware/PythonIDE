// Flutter designer motion (RAD IDE): triggers, keyframes, timelines, state, page transitions, reduced motion.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:motion_screens/radfx.dart';
import 'package:motion_screens/screens/routes.dart';

Widget app(String route) =>
    MaterialApp(initialRoute: route, routes: designedRoutes, onGenerateRoute: designedOnGenerateRoute);

Future<void> settle(WidgetTester tester, [int ms = 3000]) async {
  for (var t = 0; t < ms; t += 50) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

double opacityAbove(WidgetTester tester, Finder f) {
  var o = 1.0;
  for (final w in tester.widgetList(find.ancestor(of: f, matching: find.byType(Opacity)))) {
    o *= (w as Opacity).opacity;
  }
  for (final w in tester.widgetList(find.ancestor(of: f, matching: find.byType(FadeTransition)))) {
    o *= (w as FadeTransition).opacity.value;
  }
  return o;
}

void main() {
  setUp(() {});

  testWidgets('radFxFrame maths', (tester) async {
    const kf = RadKeyframes(
      opacity: [RadKey(0, 0), RadKey(300, 1)],
      offsetY: [RadKey(0, 40), RadKey(600, 0)],
    );
    final a = radFxFrame(RadFxType.keyframes, 0, keyframes: kf);
    expect(a.opacity, 0);
    expect(a.dy, 40);
    final b = radFxFrame(RadFxType.keyframes, 0.5, keyframes: kf);
    expect(b.opacity, 1);
    expect(b.dy, 20);
    expect(radFxFrame(RadFxType.keyframes, 1, keyframes: kf).dy, 0);
    expect(radFxFrame(RadFxType.shake, 0).dx, 0);
    expect(radFxFrame(RadFxType.shake, 1).dx.abs() < 1e-9, isTrue);
    expect(radFxFrame(RadFxType.pulse, 0.5, scale: 1.2).scaleX, closeTo(1.2, 1e-9));
    expect(radFxFrame(RadFxType.typewriter, 0.5, curve: Curves.linear).reveal, 0.5);
    expect(radFxFrame(RadFxType.fadeInUp, 0).dy, 30);
    expect(radFxIsEntrance(RadFxType.flipX), isTrue);
    expect(radFxIsEntrance(RadFxType.shake), isFalse);
  });

  testWidgets('every screen builds and animates', (tester) async {
    await tester.binding.setSurfaceSize(const Size(411, 1400));
    for (final route in ['/', '/details']) {
      await tester.pumpWidget(app(route));
      await settle(tester, 2500);
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('timeline intro, state toggle, manual and tap triggers', (tester) async {
    await tester.binding.setSurfaceSize(const Size(411, 1400));
    await tester.pumpWidget(app('/'));
    await tester.pump();
    expect(opacityAbove(tester, find.text('Welcome back')), lessThan(0.5));
    await settle(tester, 1500);
    expect(opacityAbove(tester, find.text('Welcome back')), closeTo(1, 1e-6));

    // $when: AnimatedContainer height 48 -> 120 after toggle:expanded
    double height() => tester.getSize(find.ancestor(of: find.text('Grows with the state'),
        matching: find.byType(AnimatedContainer)).first).height;
    expect(height(), closeTo(48, 0.5));
    expect(opacityAbove(tester, find.text('Fades in while expanded')), closeTo(0, 1e-6));
    await tester.tap(find.text('Show more'));
    await settle(tester, 800);
    expect(height(), closeTo(120, 0.5));
    expect(opacityAbove(tester, find.text('Fades in while expanded')), closeTo(1, 1e-6));

    // manual trigger: play:spinFx rotates the sync icon
    await tester.tap(find.text('Spin'));
    await tester.pump(const Duration(milliseconds: 300));
    final rot = tester.widgetList<Transform>(find.ancestor(of: find.byIcon(Icons.sync), matching: find.byType(Transform)));
    expect(rot.isNotEmpty, isTrue);
    await settle(tester, 1000);

    // tap trigger: the card shakes (a translation while running, none at the end)
    await tester.tap(find.text('Shake on tap'));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.ancestor(of: find.text('Shake on tap'), matching: find.byType(Transform)), findsWidgets);
    await settle(tester, 1000);
    expect(tester.takeException(), isNull);
  });

  testWidgets('page transition push:Details?transition=slideUp', (tester) async {
    await tester.binding.setSurfaceSize(const Size(411, 1400));
    await tester.pumpWidget(app('/'));
    await settle(tester, 1500);
    await tester.tap(find.text('Open details'));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byType(SlideTransition), findsWidgets);
    await settle(tester, 1500);
    expect(find.text('Flip X'), findsOneWidget);
  });

  testWidgets('reduced motion shows the final state at once', (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue = const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await tester.binding.setSurfaceSize(const Size(411, 1400));
    await tester.pumpWidget(app('/'));
    await tester.pump();
    await tester.pump();
    expect(opacityAbove(tester, find.text('Welcome back')), closeTo(1, 1e-6));
    expect(opacityAbove(tester, find.text('Keyframes')), closeTo(1, 1e-6));
    // the typewriter title is fully revealed (no Align with a width factor < 1)
    final aligns = tester.widgetList<Align>(find.ancestor(of: find.text('Motion lab'), matching: find.byType(Align)));
    expect(aligns.every((a) => (a.widthFactor ?? 1) >= 1), isTrue);
  });
}
