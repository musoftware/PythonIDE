// RAD IDE - "Remove and Sort Usings" for one C# file, like Visual Studio's Edit > IntelliSense > Remove and
// Sort Usings. Input: a JSON request (file, text, sources, refs, langVersion, defines, nullable, remove, sort,
// systemFirst, separateGroups). The unnecessary directives are the compiler's own CS8019 diagnostics of a
// compilation made of the project's sources and compile references. Output: {"text", "removed", "error"}.
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

static class Usings
{
    sealed class Request
    {
        public string file { get; set; }
        public string text { get; set; }
        public List<string> sources { get; set; } = new();
        public List<string> refs { get; set; } = new();
        public string langVersion { get; set; }
        public List<string> defines { get; set; } = new();
        public string nullable { get; set; }
        public bool remove { get; set; } = true;
        public bool sort { get; set; } = true;
        public bool systemFirst { get; set; } = true;
        public bool separateGroups { get; set; }
    }

    static int Rank(UsingDirectiveSyntax u)
    {
        int r = u.GlobalKeyword.IsKind(SyntaxKind.None) ? 10 : 0;
        if (u.Alias != null) return r + 3;
        if (!u.StaticKeyword.IsKind(SyntaxKind.None)) return r + 2;
        return r + 1;
    }

    static string Key(UsingDirectiveSyntax u) =>
        u.Alias != null ? u.Alias.Name.ToString() : (u.NamespaceOrType?.ToString() ?? u.ToString());

    static int Compare(UsingDirectiveSyntax a, UsingDirectiveSyntax b, bool systemFirst)
    {
        int c = Rank(a).CompareTo(Rank(b));
        if (c != 0) return c;
        string ka = Key(a), kb = Key(b);
        if (systemFirst && a.Alias == null && b.Alias == null)
        {
            bool sa = ka == "System" || ka.StartsWith("System.", StringComparison.Ordinal);
            bool sb = kb == "System" || kb.StartsWith("System.", StringComparison.Ordinal);
            if (sa != sb) return sa ? -1 : 1;
        }
        c = string.Compare(ka, kb, StringComparison.OrdinalIgnoreCase);
        return c != 0 ? c : string.CompareOrdinal(ka, kb);
    }

    static string Group(UsingDirectiveSyntax u) => Rank(u) + ":" + Key(u).Split('.')[0];

    public static int Run(string requestPath)
    {
        Console.OutputEncoding = Encoding.UTF8;
        var result = new Dictionary<string, object>();
        try
        {
            var req = JsonSerializer.Deserialize<Request>(File.ReadAllText(requestPath));
            var text = req.text ?? File.ReadAllText(req.file);
            var lv = LanguageVersion.Latest;
            if (!string.IsNullOrEmpty(req.langVersion))
                LanguageVersionFacts.TryParse(req.langVersion, out lv);
            var po = new CSharpParseOptions(lv, preprocessorSymbols: req.defines);
            var target = CSharpSyntaxTree.ParseText(text, po, req.file ?? "file.cs");
            var trees = new List<SyntaxTree> { target };
            var full = Path.GetFullPath(req.file ?? "file.cs");
            foreach (var s in req.sources)
            {
                if (!File.Exists(s) || string.Equals(Path.GetFullPath(s), full, StringComparison.OrdinalIgnoreCase)) continue;
                trees.Add(CSharpSyntaxTree.ParseText(File.ReadAllText(s), po, s));
            }
            var refs = req.refs.Where(File.Exists).Select(p => (MetadataReference)MetadataReference.CreateFromFile(p)).ToList();
            var nullable = (req.nullable ?? "").ToLowerInvariant() switch
            {
                "enable" => NullableContextOptions.Enable,
                "warnings" => NullableContextOptions.Warnings,
                "annotations" => NullableContextOptions.Annotations,
                _ => NullableContextOptions.Disable,
            };
            var comp = CSharpCompilation.Create("RadOrganizeUsings", trees, refs,
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, nullableContextOptions: nullable,
                                             allowUnsafe: true));
            var root = target.GetCompilationUnitRoot();
            var unused = new HashSet<UsingDirectiveSyntax>();
            if (req.remove)
            {
                var model = comp.GetSemanticModel(target);
                foreach (var d in model.GetDiagnostics())
                {
                    if (d.Id != "CS8019" && d.Id != "CS0105") continue;          // unnecessary / duplicate
                    var node = root.FindNode(d.Location.SourceSpan);
                    var u = node?.FirstAncestorOrSelf<UsingDirectiveSyntax>();
                    if (u != null && u.GlobalKeyword.IsKind(SyntaxKind.None)) unused.Add(u);
                }
            }
            var removed = unused.Select(u => u.WithoutTrivia().ToString()).ToList();
            // every block of directives: the compilation unit's and each namespace's
            var blocks = new List<SyntaxList<UsingDirectiveSyntax>> { root.Usings };
            blocks.AddRange(root.DescendantNodes().OfType<BaseNamespaceDeclarationSyntax>().Select(n => n.Usings));
            var lines = text.Replace("\r\n", "\n").Split('\n').ToList();
            string nl = text.Contains("\r\n") ? "\r\n" : "\n";
            var edits = new List<(int start, int end, List<string> repl)>();
            foreach (var block in blocks)
            {
                if (block.Count == 0) continue;
                var keep = block.Where(u => !unused.Contains(u)).ToList();
                bool hasComments = block.Skip(1).Any(u => u.GetLeadingTrivia().Any(t =>
                    !t.IsKind(SyntaxKind.WhitespaceTrivia) && !t.IsKind(SyntaxKind.EndOfLineTrivia)));
                if (req.sort && !hasComments)
                    keep.Sort((a, b) => Compare(a, b, req.systemFirst));
                if (!req.sort || hasComments)
                {
                    if (keep.Count == block.Count) continue;
                }
                int first = target.GetLineSpan(block.First().Span).StartLinePosition.Line;
                int last = target.GetLineSpan(block.Last().Span).EndLinePosition.Line;
                string indent = new string(lines[first].TakeWhile(char.IsWhiteSpace).ToArray());
                var repl = new List<string>();
                string prev = null;
                foreach (var u in keep)
                {
                    if (req.separateGroups && prev != null && Group(u) != prev) repl.Add("");
                    repl.Add(indent + u.WithoutTrivia().ToString());
                    prev = Group(u);
                }
                if (hasComments)
                {
                    // keep the original order and comments: only drop the unused lines
                    repl = new List<string>();
                    for (int i = first; i <= last; i++)
                    {
                        bool drop = unused.Any(u => target.GetLineSpan(u.Span).StartLinePosition.Line == i &&
                                                    target.GetLineSpan(u.Span).EndLinePosition.Line == i);
                        if (!drop) repl.Add(lines[i]);
                    }
                }
                edits.Add((first, last, repl));
            }
            foreach (var e in edits.OrderByDescending(e => e.start))
            {
                lines.RemoveRange(e.start, e.end - e.start + 1);
                lines.InsertRange(e.start, e.repl);
                // an emptied block leaves a double blank line: collapse it
                if (e.repl.Count == 0 && e.start < lines.Count && e.start > 0 &&
                    lines[e.start].Trim().Length == 0 && lines[e.start - 1].Trim().Length == 0)
                    lines.RemoveAt(e.start);
                else if (e.repl.Count == 0 && e.start == 0 && lines.Count > 0 && lines[0].Trim().Length == 0)
                    lines.RemoveAt(0);
            }
            result["text"] = string.Join(nl, lines);
            result["removed"] = removed;
            result["error"] = null;
        }
        catch (Exception e)
        {
            result["text"] = null;
            result["removed"] = new List<string>();
            result["error"] = e.GetType().Name + ": " + e.Message;
        }
        Console.WriteLine(JsonSerializer.Serialize(result));
        return 0;
    }
}
