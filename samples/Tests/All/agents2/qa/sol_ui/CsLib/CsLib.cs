// Class Library CsLib. Its public static methods are the library's public functions:
// a project that references CsLib (Add Reference) calls them as native code -
//     CsLib.Add(2, 3)   in C#, Python, Java, JavaScript ...   CsLib_Add(2, 3) in Ring
// Arguments and results are JSON values: numbers, strings, bools, null, lists, dictionaries.
public static class CsLib
{
    /// <summary>Adds two numbers.</summary>
    public static double Add(double a, double b) => a + b;

    /// <summary>Returns a greeting.</summary>
    public static string Greet(string name) => $"Hello, {name}!";
}
