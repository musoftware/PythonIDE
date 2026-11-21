import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rating_bar_flutter/main.dart';
import 'package:rating_bar_flutter/rating_bar.dart';
import 'package:rating_bar_flutter/screens/rate_screen.dart';

void main() {
  testWidgets('phone form: user code reads and sets the rating', (tester) async {
    await tester.pumpWidget(const RadMobileApp());
    await tester.pumpAndSettle();
    expect(find.byType(RatingBar), findsOneWidget);
    expect(tester.state<RatingBarState>(find.byType(RatingBar)).value, 3);
    await tester.tap(find.byKey(const ValueKey('star4')));
    await tester.pumpAndSettle();
    expect(find.text('Rating: 4'), findsOneWidget);
    await tester.tap(find.text('Set'));
    await tester.pumpAndSettle();
    expect(find.text('Set: 2 of 5'), findsOneWidget);
    expect(tester.state<RatingBarState>(find.byType(RatingBar)).value, 2);
  });

  testWidgets('designer screen: the handler reads rate2.value', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: RateScreen()));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('star5')));
    await tester.pumpAndSettle();
    final s = tester.state<RateScreenEvents>(find.byType(RateScreen));
    expect(s.lastRating, 5);
    expect(s.rate2.value, 5);
  });
}
