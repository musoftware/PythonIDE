// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Widget tests of TodoDesigner (flutter test): add a task, tick it, switch to Arabic in Settings.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:todo_designer/app_store.dart';
import 'package:todo_designer/main.dart';

void main() {
  testWidgets('add and finish a task, then switch to Arabic (RTL)', (tester) async {
    await tester.pumpWidget(const RadMobileApp());
    await tester.pumpAndSettle();
    expect(find.text('My tasks'), findsOneWidget);
    expect(find.text('2 open of 3 tasks'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'Buy milk');
    await tester.tap(find.text('Add'));
    await tester.pumpAndSettle();
    expect(find.text('Buy milk'), findsOneWidget);
    expect(find.text('3 open of 4 tasks'), findsOneWidget);

    await tester.tap(find.text('Buy milk'));
    await tester.pumpAndSettle();
    expect(store.todos.last.done, isTrue);

    await tester.tap(find.byIcon(Icons.settings));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(SwitchListTile).first);
    await tester.pumpAndSettle();
    expect(find.text('الإعدادات'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('مهامي'), findsOneWidget);
    final dir = tester.widget<Directionality>(find.byType(Directionality).last);
    expect(dir.textDirection, TextDirection.rtl);
  });
}
