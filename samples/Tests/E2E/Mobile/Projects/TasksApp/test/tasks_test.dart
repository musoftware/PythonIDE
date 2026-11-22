// Widget tests of the Tasks app (written in the RAD IDE editor).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:tasks_app/main.dart';

Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 25; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  testWidgets('list -> add -> list -> detail', (tester) async {
    SharedPreferences.setMockInitialValues({'tasks': <String>['Buy milk']});
    await tester.binding.setSurfaceSize(const Size(411, 891));
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    expect(find.text('My Tasks'), findsOneWidget);
    expect(find.text('Buy milk'), findsOneWidget);
    await tester.tap(find.byType(FloatingActionButton));
    await settle(tester);
    expect(find.text('New task'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'Write report');
    await tester.tap(find.text('Save'));
    await settle(tester);
    expect(find.text('Write report'), findsOneWidget);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getStringList('tasks'), ['Buy milk', 'Write report']);
    await tester.tap(find.text('Write report'));
    await settle(tester);
    expect(find.text('Task'), findsOneWidget);
    expect(find.text('Write report'), findsOneWidget);
    await tester.tap(find.text('Back'));
    await settle(tester);
    expect(find.text('My Tasks'), findsOneWidget);
  });

  testWidgets('empty title is refused', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    await tester.tap(find.byType(FloatingActionButton));
    await settle(tester);
    await tester.tap(find.text('Save'));
    await settle(tester);
    expect(find.text('Enter a title'), findsOneWidget);
  });

  testWidgets('Arabic screen is right-to-left', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    await tester.tap(find.text('عن التطبيق'));
    await settle(tester);
    final title = find.text('تطبيق المهام');
    expect(title, findsOneWidget);
    expect(Directionality.of(tester.element(title)), TextDirection.rtl);
  });

  testWidgets('tablet size uses the larger header', (tester) async {
    SharedPreferences.setMockInitialValues({});
    addTearDown(tester.view.reset);
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(800, 1280);
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    expect(tester.widget<Text>(find.text("Today's tasks")).style?.fontSize, 34);
    tester.view.physicalSize = const Size(411, 891);
    await settle(tester);
    expect(tester.widget<Text>(find.text("Today's tasks")).style?.fontSize, 22);
  });
}
