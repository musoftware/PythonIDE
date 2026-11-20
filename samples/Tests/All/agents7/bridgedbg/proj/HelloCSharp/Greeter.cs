// Module Greeter. Its public static methods are used by Form1 (Greeter.Make(...)) and can be
// called from the other languages of a project through the RAD Hub:
//     radcall("Greeter.Make", "Ali", true)      (same syntax in C#, Python, Ring, Java, ...)
public static class Greeter
{
    static readonly string[] Words = { "Hello", "Hi", "Welcome", "Good day" };

    public static string Make(string name, bool shout)
    {
        if (string.IsNullOrWhiteSpace(name)) name = "stranger";
        var text = $"{Words[name.Length % Words.Length]}, {name.Trim()}!";
        return shout ? text.ToUpperInvariant() : text;
    }
}
