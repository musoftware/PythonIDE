import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:phone_forms/main.dart';

void main() {
  testWidgets('phone: add an item', (tester) async {
    addTearDown(tester.view.reset);
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(412, 915);
    await tester.pumpWidget(const RadMobileApp());
    await tester.pumpAndSettle();
    expect(find.text('Items: 0'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'Milk');
    await tester.tap(find.text('Add'));
    await tester.pumpAndSettle();
    expect(find.text('Milk'), findsOneWidget);
    expect(find.text('Items: 1'), findsOneWidget);
  });

  testWidgets('tablet: the size override applies', (tester) async {
    addTearDown(tester.view.reset);
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(800, 1000);
    await tester.pumpWidget(const RadMobileApp());
    await tester.pumpAndSettle();
    expect(find.text('Items (tablet): 0'), findsOneWidget);
  });
}
