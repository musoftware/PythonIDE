import 'package:calc/calc.dart';
import 'package:test/test.dart';

void main() {
  group('add', () {
    test('adds two numbers', () {
      expect(add(2, 3), 5);
    });
    test('fails on purpose', () {
      expect(add(2, 2), 5);
    });
  });
  test('top level', () {
    expect(add(0, 0), 0);
  });
}
