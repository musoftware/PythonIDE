// Flutter designer data widgets (RAD IDE): ListView.builder / GridView.builder item templates, Text.rich and
// RichText spans, Form + validator rules + validate: events, RadioGroup, timeline values on number properties.
import 'package:data_forms_screens/radform.dart';
import 'package:data_forms_screens/screens/routes.dart';
import 'package:data_forms_screens/screens/sign_up.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget app(String route) => MaterialApp(initialRoute: route, routes: designedRoutes);

String richText(WidgetTester tester, Finder f) => tester.widget<RichText>(f).text.toPlainText();

void main() {
  test('RadRule maths', () {
    expect(const RadRule.required().check(''), 'This field is required');
    expect(const RadRule.required().check('  '), isNotNull);
    expect(const RadRule.required('x').check('a'), isNull);
    expect(const RadRule.email().check('a@b.co'), isNull);
    expect(const RadRule.email().check('a@b'), 'Enter a valid e-mail address');
    expect(const RadRule.email().check(''), isNull);
    expect(const RadRule.minLength(3).check('ab'), 'Enter at least 3 characters');
    expect(const RadRule.maxLength(2, 'too long').check('abc'), 'too long');
    expect(const RadRule.regex(r'[0-9]+').check('12a'), 'Invalid format');
    expect(const RadRule.regex(r'[0-9]+').check('123'), isNull);
    final v = radValidate(const [RadRule.required()], custom: (s) => s == 'bad' ? 'custom' : null);
    expect(v(''), 'This field is required');
    expect(v('bad'), 'custom');
    expect(v('ok'), isNull);
  });

  testWidgets('Catalog: builders and spans', (tester) async {
    await tester.binding.setSurfaceSize(const Size(400, 900));
    await tester.pumpWidget(app('/'));
    await tester.pumpAndSettle();
    expect(find.text('Apple'), findsOneWidget);
    expect(find.text('Item number 0'), findsOneWidget);
    expect(find.text('1'), findsOneWidget);
    expect(find.text('Box 0'), findsOneWidget);
    expect(find.text('Fruit Market'), findsOneWidget); // Text.rich
    final rich = find.byWidgetPredicate((w) => w is RichText && w.text.toPlainText().startsWith('Fresh '));
    expect(rich, findsOneWidget);
    expect(richText(tester, rich), 'Fresh today - tap a fruit');
    final spans = (tester.widget<RichText>(rich).text as TextSpan).children!;
    expect((spans[1] as TextSpan).style!.fontStyle, FontStyle.italic);
    expect((spans[1] as TextSpan).style!.shadows, isNotEmpty);
    await tester.binding.setSurfaceSize(null);
  });

  testWidgets('SignUp: validators, custom handlers, validate:, RadioGroup', (tester) async {
    await tester.binding.setSurfaceSize(const Size(420, 1400));
    await tester.pumpWidget(app('/sign_up'));
    await tester.pumpAndSettle();
    final state = tester.state<SignUpEvents>(find.byType(SignUp));
    await tester.tap(find.text('Sign up'));
    await tester.pumpAndSettle();
    expect(find.text('Please enter your name'), findsOneWidget);
    expect(find.text('This field is required'), findsNWidgets(2));
    expect(state.submitted, isNull);

    Finder field(String label) => find.widgetWithText(TextFormField, label);
    await tester.enterText(field('Name'), 'Mona');
    await tester.enterText(field('E-mail'), 'mona@example');
    await tester.enterText(field('Password'), 'short');
    await tester.enterText(field('Phone (digits)'), '12ab');
    await tester.enterText(field('Promo code'), 'WRONG');
    await tester.tap(find.text('Check'));
    await tester.pumpAndSettle();
    expect(find.text('Enter a valid e-mail address'), findsOneWidget);
    expect(find.text('At least 8 characters'), findsOneWidget);
    expect(find.text('7 to 15 digits'), findsOneWidget);
    expect(find.text('Unknown promo code'), findsOneWidget);

    await tester.enterText(field('Phone (digits)'), '0001234');
    await tester.pumpAndSettle();
    expect(find.text('Not a real number'), findsOneWidget); // custom checkPhone after the rules

    await tester.enterText(field('E-mail'), 'mona@example.com');
    await tester.enterText(field('Password'), 'long enough');
    await tester.enterText(field('Phone (digits)'), '01012345678');
    await tester.enterText(field('Promo code'), 'RAD2026');
    expect(state.rdoPlan, 'free');
    await tester.tap(find.text('Pro'));
    await tester.pumpAndSettle();
    expect(state.rdoPlan, 'pro');
    await tester.tap(find.byType(Radio<String>).last);
    await tester.pumpAndSettle();
    expect(state.rdoPlan, 'team');
    await tester.tap(find.text('Sign up'));
    await tester.pumpAndSettle();
    expect(state.submitted, 'Mona <mona@example.com> plan=team');
    await tester.binding.setSurfaceSize(null);
  });

  testWidgets('Pulse: timeline values on number properties animate', (tester) async {
    await tester.pumpWidget(app('/pulse'));
    await tester.pump();
    double width() => tester.getSize(find.byWidgetPredicate((w) => w is Container && w.decoration != null &&
        (w.decoration as BoxDecoration).color == const Color(0xFF6750A4))).width;
    final w0 = width();
    await tester.pump(const Duration(milliseconds: 600));
    final w1 = width();
    await tester.pump(const Duration(milliseconds: 600));
    final w2 = width();
    expect(w0, closeTo(80, 1));
    expect(w1, greaterThan(w0 + 20));
    expect(w2, closeTo(220, 1));
    final text = tester.widget<Text>(find.text('Lines follow the timeline as well'));
    expect(text.maxLines, 3);
    await tester.pump(const Duration(milliseconds: 1200)); // reverse
    expect(width(), closeTo(80, 1));
    await tester.pumpWidget(const SizedBox()); // dispose the repeating timeline
  });
}
