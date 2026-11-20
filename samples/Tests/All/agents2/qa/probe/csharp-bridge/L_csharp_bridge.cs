// Class Library L_csharp_bridge. Its public static methods are the library's public functions:
// a project that references L_csharp_bridge (Add Reference) calls them as native code -
//     L_csharp_bridge.Add(2, 3)   in C#, Python, Java, JavaScript ...   L_csharp_bridge_Add(2, 3) in Ring
// Arguments and results are JSON values: numbers, strings, bools, null, lists, dictionaries.
public static class L_csharp_bridge
{
    /// <summary>Adds two numbers.</summary>
    public static double Add(double a, double b) => a + b;

    /// <summary>Returns a greeting.</summary>
    public static string Greet(string name) => $"Hello, {name}!";
}
