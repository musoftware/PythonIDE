// Animations of a classic Flutter form (samples/Tests/Motion/Targets/check_targets.py runs it).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:motion_flutter/form1.dart';
import 'package:motion_flutter/radapp.dart';

Form1Code _state(WidgetTester t) => t.state<State<Form1>>(find.byType(Form1)) as Form1Code;

void main() {
  testWidgets('On load: slide in + typewriter, then the designed look', (t) async {
    await t.pumpWidget(const MaterialApp(home: Form1()));
    await t.pump();
    await t.pump(const Duration(milliseconds: 150));
    final s = _state(t);
    expect(s.lblTitle.text.length, lessThan('Hello, motion!'.length));
    expect(s.radMotion.looks['lblTitle']!.tx, lessThan(0));
    await t.pump(const Duration(seconds: 2));
    expect(s.lblTitle.text, 'Hello, motion!');
    expect(s.radMotion.looks['lblTitle']!.tx, 0);
    expect(s.radMotion.looks['lblTitle']!.opacity, 1);
  });

  testWidgets('On click: shake, rotate; After: chained bounce; flip -> pulse', (t) async {
    await t.pumpWidget(const MaterialApp(home: Form1()));
    await t.pump(const Duration(seconds: 2));
    final s = _state(t);
    await t.tap(find.text('Shake me'));
    await t.pump(const Duration(milliseconds: 100));
    expect(s.radMotion.looks['btnShake']!.tx, isNot(0));
    await t.pump(const Duration(seconds: 1));
    expect(s.radMotion.looks['btnShake']!.tx, 0);
    await t.tap(find.text('Rotate'));
    await t.pump(const Duration(milliseconds: 300));
    expect(s.radMotion.looks['btnSpin']!.rot, greaterThan(0));
    await t.pump(const Duration(seconds: 1));
    await t.tap(find.text('Move + bounce'));
    await t.pump();
    await t.pump(const Duration(milliseconds: 450));
    await t.pump(const Duration(milliseconds: 150));
    expect(s.radMotion.looks['btnMove']!.tx, 60);
    expect(s.radMotion.looks['btnMove']!.ty, lessThan(0)); // the bounce chained after the move
    await t.pump(const Duration(seconds: 1));
    await t.tap(find.text('Flip / zoom'));
    await t.pump(const Duration(milliseconds: 100));
    expect(s.radMotion.looks['btnFlip']!.sx, lessThan(0));
    await t.pump(const Duration(milliseconds: 800));
    await t.pump(const Duration(milliseconds: 300));
    expect(s.radMotion.looks['btnFlip']!.sx, greaterThan(1)); // pulse after flip
    await t.pump(const Duration(seconds: 2));
  });

  testWidgets('On hide / On show and manual animations', (t) async {
    await t.pumpWidget(const MaterialApp(home: Form1()));
    await t.pump(const Duration(seconds: 2));
    final s = _state(t);
    await t.tap(find.text('Hide / show'));
    await t.pump(const Duration(milliseconds: 200));
    expect(s.lblInfo.visible, isTrue);
    expect(s.radMotion.looks['lblInfo']!.opacity, lessThan(1));
    await t.pump(const Duration(seconds: 1));
    expect(s.lblInfo.visible, isFalse);
    s.SetVisible('lblInfo', true);
    await t.pump(const Duration(seconds: 1));
    expect(s.lblInfo.visible, isTrue);
    expect(s.radMotion.looks['lblInfo']!.opacity, 1);
    s.BeginAnimation('fx14');
    await t.pump();
    await t.pump(const Duration(seconds: 1));
    expect(s.btnHide.visible, isFalse);
    s.BeginAnimation('fx16');
    await t.pump(const Duration(seconds: 1));
    s.StopAnimation('fx10');
    await t.pump(const Duration(seconds: 3));
  });

  testWidgets('Timer: the card changes colour', (t) async {
    await t.pumpWidget(const MaterialApp(home: Form1()));
    await t.pump(const Duration(seconds: 2));
    final s = _state(t);
    final before = s.pnlBox.backColor;
    await t.pump(const Duration(milliseconds: 700));
    await t.pump(const Duration(milliseconds: 350));
    expect(s.pnlBox.backColor, isNot(before));
    await t.pump(const Duration(seconds: 3));
  });

  testWidgets('Reduced motion shows the end at once', (t) async {
    await t.pumpWidget(const MaterialApp(
      home: MediaQuery(data: MediaQueryData(disableAnimations: true), child: Form1()),
    ));
    await t.pump();
    await t.pump();
    final s = _state(t);
    expect(s.lblTitle.text, 'Hello, motion!');
    expect(s.radMotion.looks['lblTitle']!.tx, 0);
    await t.tap(find.text('Shake me'));
    await t.pump();
    expect(s.radMotion.looks['btnShake']!.tx, 0);
    expect(RadKey(0, 1).value, 1);
  });
}
