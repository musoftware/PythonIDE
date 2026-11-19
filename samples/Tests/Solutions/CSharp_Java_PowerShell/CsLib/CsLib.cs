// C# library
using System.Collections.Generic;
public static class CsLib
{
    /// <summary>Adds two numbers.</summary>
    public static double Add(double a, double b) => a + b;
    public static string Greet(string name = "you") => $"Hello, {name}!";
    public static List<int> Range(int n) { var l = new List<int>(); for (int i = 0; i < n; i++) l.Add(i); return l; }
    public static int Count(List<object> xs) => xs.Count;
    public static void Log(string msg) => System.Console.Error.WriteLine("[CsLib] " + msg);
    public static bool IsEven(int n) => n % 2 == 0;
    static int Hidden() => 0;
}
