// Smoke test of the app (flutter test).
import 'package:flutter_test/flutter_test.dart';
import 'package:variants_flutter/main.dart';

void main() {
  testWidgets('the start screen builds', (tester) async {
    await tester.pumpWidget(const RadMobileApp());
    await tester.pump();
    expect(find.byType(RadMobileApp), findsOneWidget);
  });
}
