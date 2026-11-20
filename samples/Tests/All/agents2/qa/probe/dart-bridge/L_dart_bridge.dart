// Class library L_dart_bridge. Its public top-level functions (names not starting with _)
// can be called from every project that references this library, in its own language:
//   Python: import L_dart_bridge; L_dart_bridge.Add(2, 3)
//   Dart:   import 'l_dart_bridge_ref.dart' as L_dart_bridge;  await L_dart_bridge.Add(2, 3);

/// Add two numbers.
num Add(num a, num b) => a + b;

/// Greeting text for who.
String Greet(String who) => 'Hello, $who!';
