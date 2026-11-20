// Module Greeter. Other languages call it through the RAD Hub:
//   radcall("Greeter.greet", "Ali", 1)   (arguments and the result are JSON values)

String greet(String name, int count) =>
    count == 1 ? 'Hello, $name!' : 'Hello again, $name! (greeting #$count)';
