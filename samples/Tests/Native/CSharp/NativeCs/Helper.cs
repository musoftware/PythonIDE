// Module Helper: plain C# used by the forms (directly and through radcall).
public static class Helper
{
    public static string Greet(string name) => $"Hello, {name}!";

    public static string Shout(string name) => Greet(name).ToUpperInvariant();
}
