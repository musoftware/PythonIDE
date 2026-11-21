import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:offline_theme_app/screens/routes.dart';

/// Every designed template screen builds, plays its entrance animations and reports no framework error.
void main() {

  for (final entry in designedRoutes.entries) {
    testWidgets('template ${entry.key} builds and animates', (tester) async {
      final errors = <String>[];
      final old = FlutterError.onError;
      FlutterError.onError = (d) {
        final s = d.exceptionAsString();
        // runtime font fetching is off in tests; the test font (Ahem) is far wider than the real fonts, so
        // RenderFlex overflows are checked on the web build (real fonts) instead
        if (s.contains('overflowed') || s.contains('GoogleFonts') || s.contains('allowRuntimeFetching')) {
          return;
        }
        errors.add(s);
      };
      await tester.binding.setSurfaceSize(const Size(411, 891));
      await tester.pumpWidget(MaterialApp(routes: designedRoutes, initialRoute: entry.key));
      for (var i = 0; i < 30; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      FlutterError.onError = old;
      expect(errors, isEmpty, reason: errors.join('\n'));
      expect(find.byType(Navigator), findsOneWidget);
    });
  }
}
