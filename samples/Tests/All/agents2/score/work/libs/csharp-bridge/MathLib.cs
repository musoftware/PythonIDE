// Class Library MathLib. Its public static methods are the library's public functions:
// a project that references MathLib (Add Reference) calls them as native code -
//     MathLib.Add(2, 3)   in C#, Python, Java, JavaScript ...   MathLib_Add(2, 3) in Ring
// Arguments and results are JSON values: numbers, strings, bools, null, lists, dictionaries.
public static class MathLib
{
    /// <summary>Adds two numbers.</summary>
    public static double Add(double a, double b) => a + b;

    /// <summary>Returns a greeting.</summary>
    public static string Greet(string name) => $"Hello, {name}!";
}
