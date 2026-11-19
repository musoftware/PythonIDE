/// Multiply two numbers.
num Times(num a, num b) => a * b;

/// Upper-case text (async).
Future<String> Shout(String s) async => s.toUpperCase();

List<int> Range(int n, [int start = 0]) => List.generate(n, (i) => start + i);

void Log(String m) {
  print(m);
}

int _secret() => 1;

class Foo {
  int bar() => 1;
}
