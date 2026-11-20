// Class library DartLib. Its public top-level functions (names not starting with _)
// can be called from every project that references this library, in its own language:
//   Python: import DartLib; DartLib.Add(2, 3)
//   Dart:   import 'dartlib_ref.dart' as DartLib;  await DartLib.Add(2, 3);

/// Add two numbers.
num Add(num a, num b) => a + b;

/// Greeting text for who.
String Greet(String who) => 'Hello, $who!';
