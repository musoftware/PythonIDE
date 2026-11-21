// RAD IDE - AnalyzerInfo: prints JSON describing the analyzers and source generators of each assembly given
// on the command line: [{ "path", "error", "rules": [{id,title,category,severity,enabled,help}], "generators": [..] }]
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.Diagnostics;

static class Program
{
    sealed class AnalyzerContext : AssemblyLoadContext
    {
        private readonly string _dir;
        public AnalyzerContext(string dir) : base(isCollectible: false) { _dir = dir; }
        protected override Assembly Load(AssemblyName name)
        {
            if (name.Name != null && name.Name.StartsWith("Microsoft.CodeAnalysis", StringComparison.Ordinal) &&
                !File.Exists(Path.Combine(_dir, name.Name + ".dll")))
                return null;                                 // the host's Roslyn
            var p = Path.Combine(_dir, name.Name + ".dll");
            return File.Exists(p) ? LoadFromAssemblyPath(p) : null;
        }
    }

    static IEnumerable<Type> SafeTypes(Assembly a)
    {
        try { return a.GetTypes(); }
        catch (ReflectionTypeLoadException e) { return e.Types.Where(t => t != null); }
    }

    static int Main(string[] args)
    {
        var all = new List<object>();
        foreach (var path in args)
        {
            var rules = new Dictionary<string, object>();
            var gens = new List<string>();
            string error = null;
            try
            {
                var full = Path.GetFullPath(path);
                var ctx = new AnalyzerContext(Path.GetDirectoryName(full));
                var asm = ctx.LoadFromAssemblyPath(full);
                foreach (var t in SafeTypes(asm))
                {
                    if (t.IsAbstract || !t.IsClass) continue;
                    try
                    {
                        if (typeof(DiagnosticAnalyzer).IsAssignableFrom(t) && t.GetConstructor(Type.EmptyTypes) != null)
                        {
                            var inst = (DiagnosticAnalyzer)Activator.CreateInstance(t);
                            foreach (var d in inst.SupportedDiagnostics)
                            {
                                if (rules.ContainsKey(d.Id)) continue;
                                rules[d.Id] = new Dictionary<string, object>
                                {
                                    ["id"] = d.Id,
                                    ["title"] = d.Title.ToString(),
                                    ["category"] = d.Category,
                                    ["severity"] = d.DefaultSeverity.ToString(),
                                    ["enabled"] = d.IsEnabledByDefault,
                                    ["help"] = d.HelpLinkUri ?? "",
                                };
                            }
                        }
                        else if (typeof(ISourceGenerator).IsAssignableFrom(t) || typeof(IIncrementalGenerator).IsAssignableFrom(t))
                        {
                            gens.Add(t.FullName);
                        }
                    }
                    catch (Exception) { }
                }
            }
            catch (Exception e) { error = e.GetType().Name + ": " + e.Message; }
            all.Add(new Dictionary<string, object>
            {
                ["path"] = path,
                ["error"] = error,
                ["rules"] = rules.Values.OrderBy(r => ((Dictionary<string, object>)r)["id"]).ToList(),
                ["generators"] = gens,
            });
        }
        Console.OutputEncoding = System.Text.Encoding.UTF8;
        Console.WriteLine(JsonSerializer.Serialize(all));
        return 0;
    }
}
