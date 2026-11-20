// Class Library MathLib (C#). Its public static methods are the library's public functions:
// a project that references MathLib (Add Reference) calls them as its own code -
//     MathLib.Add(2, 3)   in Python, C#, Java, JavaScript ...   MathLib_Add(2, 3) in Ring
// Arguments and results are JSON values: numbers, strings, bools, null, lists, dictionaries.
public static class MathLib
{
    /// <summary>Adds two numbers.</summary>
    public static double Add(double a, double b) => a + b;

    /// <summary>Multiplies two numbers.</summary>
    public static double Multiply(double a, double b) => a * b;

    /// <summary>Returns a greeting made in C#.</summary>
    public static string Greet(string name) => $"Hello, {name}! (from C# {System.Environment.Version})";
}
