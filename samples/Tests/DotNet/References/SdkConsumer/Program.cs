// The Reference Manager test adds MathKit.dll (Browse) to this project; the test then builds and runs it.
#if MATHKIT
var calc = new MathKit.Calculator();
Console.WriteLine($"2 + 3 = {calc.Add(2, 3)}; gcd(12, 18) = {MathKit.Calculator.Gcd(12, 18)}");
#else
Console.WriteLine("MathKit is not referenced yet (Add > Assembly Reference... > Browse).");
#endif
