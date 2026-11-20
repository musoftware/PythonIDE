using MathLib;

Console.WriteLine("ConsoleApp started");
int total = 0;
for (int i = 1; i <= 3; i++)
{
    total = Calculator.Add(total, i);
    Console.WriteLine($"i={i} total={total}");
}
Console.WriteLine($"2*21={Calculator.Multiply(2, 21)}");
