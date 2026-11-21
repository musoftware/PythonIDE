using System.Text.RegularExpressions;

namespace Calc;

/// <summary>Uses the .NET regex source generator: Dependencies > Analyzers > System.Text.RegularExpressions.Generator
/// > RegexGenerator lists the generated RegexGenerator.g.cs after "Show Generated Files".</summary>
public static partial class Patterns
{
    [GeneratedRegex(@"^\d+$")]
    public static partial Regex Digits();
}
