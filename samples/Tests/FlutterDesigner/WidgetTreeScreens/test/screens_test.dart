import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fs_app/screens/routes.dart';

void main() {
  GoogleFonts.config.allowRuntimeFetching = false;
  for (final entry in designedRoutes.entries) {
    testWidgets('screen ${entry.key} builds and animates', (tester) async {
      final errors = <String>[];
      final old = FlutterError.onError;
      FlutterError.onError = (d) {
        final s = d.exceptionAsString();
        // network images / runtime font fetching are not available in tests
        // the test font (Ahem) is much wider than real fonts: RenderFlex overflows are not meaningful here
        if (s.contains('overflowed') || s.contains('HTTP') || s.contains('NetworkImage') || s.contains('GoogleFonts') ||
            s.contains('allowRuntimeFetching') || d.library == 'image resource service') {
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
