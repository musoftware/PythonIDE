// Offline widget tests: every foldable preset of radide/devices.py in every posture (test/devices_gen.dart,
// written by check_foldable.py) is simulated with tester.view.displayFeatures and the panes must match the
// TwoPane rule computed in Python (devices.two_pane).
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:radide_foldable/main.dart';

import 'devices_gen.dart';

ui.DisplayFeature _feature(Map<String, Object> f) {
  final b = (f['bounds']! as List).cast<int>();
  return ui.DisplayFeature(
    bounds: Rect.fromLTWH(b[0].toDouble(), b[1].toDouble(), b[2].toDouble(), b[3].toDouble()),
    type: f['type'] == 'hinge' ? ui.DisplayFeatureType.hinge : ui.DisplayFeatureType.fold,
    state: f['state'] == 'postureHalfOpened'
        ? ui.DisplayFeatureState.postureHalfOpened
        : ui.DisplayFeatureState.postureFlat,
  );
}

void main() {
  for (final c in foldCases) {
    testWidgets('${c['name']}', (tester) async {
      final size = (c['size']! as List).cast<int>();
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = Size(size[0].toDouble(), size[1].toDouble());
      tester.view.displayFeatures =
          (c['features']! as List).cast<Map<String, Object>>().map(_feature).toList();
      addTearDown(tester.view.reset);
      await tester.pumpWidget(const FoldApp());
      final panes = (c['panes']! as List);
      final r1 = tester.getRect(find.byKey(const Key('pane1')));
      final p1 = (panes[0] as List).cast<int>();
      expect(r1, Rect.fromLTWH(p1[0].toDouble(), p1[1].toDouble(), p1[2].toDouble(), p1[3].toDouble()));
      if (panes[1] == null) {
        expect(find.byKey(const Key('pane2')), findsNothing);
      } else {
        final p2 = (panes[1] as List).cast<int>();
        expect(tester.getRect(find.byKey(const Key('pane2'))),
            Rect.fromLTWH(p2[0].toDouble(), p2[1].toDouble(), p2[2].toDouble(), p2[3].toDouble()));
      }
    });
  }
}
