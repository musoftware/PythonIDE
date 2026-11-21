// Layout sizes + TwoPane of a classic Flutter form (samples/Tests/Variants/Targets/check_targets.py runs it).
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:variants_flutter/form1.dart';

Form1Code _state(WidgetTester t) => t.state<State<Form1>>(find.byType(Form1)) as Form1Code;

double _left(WidgetTester t, String text) {
  final p = t.widget<Positioned>(find.ancestor(of: find.text(text), matching: find.byType(Positioned)).first);
  return p.left!;
}

Future<void> _size(WidgetTester t, double w, double h, {List<DisplayFeature> features = const []}) async {
  t.view.physicalSize = Size(w, h);
  t.view.devicePixelRatio = 1;
  t.view.displayFeatures = features;
  await t.pumpWidget(const MaterialApp(home: Form1()));
  await t.pump();
  await t.pump();
}

void main() {
  tearDown(() {
    final v = TestWidgetsFlutterBinding.instance.platformDispatcher.views.first;
    v.resetPhysicalSize();
    v.resetDevicePixelRatio();
    v.resetDisplayFeatures();
  });

  testWidgets('Phone: the designed layout, one pane', (t) async {
    await _size(t, 412, 867);
    final s = _state(t);
    expect(s.CurrentSizes, ['phone']);
    expect(s.btnGo.text, 'Go');
    expect(s.lblSide.visible, isTrue);
    expect(_left(t, 'Go'), 16);
    expect(find.text('List'), findsOneWidget);
    expect(find.text('Detail'), findsNothing);
  });

  testWidgets('Tablet: moved button, new text, hidden label', (t) async {
    await _size(t, 900, 700);
    final s = _state(t);
    expect(s.CurrentSizes, ['tablet']);
    expect(s.btnGo.text, 'Go (tablet)');
    expect(s.lblSide.visible, isFalse);
    expect(_left(t, 'Go (tablet)'), 500);
  });

  testWidgets('Half-open foldable: the tabletop size and both panes', (t) async {
    await _size(t, 882, 1104, features: const [
      DisplayFeature(bounds: Rect.fromLTWH(0, 552, 882, 0), type: DisplayFeatureType.fold,
          state: DisplayFeatureState.postureHalfOpened),
    ]);
    final s = _state(t);
    expect(s.CurrentSizes, ['tablet', 'tabletop']);
    expect(s.btnGo.text, 'Go (half-open)'); // the later size wins (CSS cascade)
    expect(find.text('List'), findsOneWidget);
    expect(find.text('Detail'), findsOneWidget);
  });
}
