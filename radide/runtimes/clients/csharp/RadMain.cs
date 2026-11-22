// RAD IDE - entry program for C# projects (copied into _build/<lang> when the program runs - do not edit).
//   RadApp.dll                    GUI Bridge program: runs the handler named <Object>_<Event> for each EVENT
//   RadApp.dll --worker <Module>  serves the public static methods of class <Module> to the RAD Hub (JSON lines)
using System.Reflection;
using System.Text.Json;

public static class RadMain
{
    public static int Main(string[] args)
    {
        if (args.Length >= 2 && args[0] == "--worker")
        {
            Rad.Init(worker: true);
            return RadWorker.Serve(args[1]);
        }
        Rad.Init();
        var handlers = new Dictionary<string, MethodInfo>(StringComparer.OrdinalIgnoreCase);
        foreach (var type in typeof(RadMain).Assembly.GetTypes())
        {
            if (type == typeof(RadMain) || type == typeof(Rad) || type == typeof(RadWorker)) continue;
            foreach (var m in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.DeclaredOnly))
            {
                if (m.IsSpecialName || m.Name.Contains('<') || !m.Name.Contains('_') || m.GetParameters().Length > 1) continue;
                handlers.TryAdd(m.Name, m);
            }
        }
        string line;
        while ((line = Rad.ReadLine()) != null)
        {
            if (line == "QUIT") break;
            if (!line.StartsWith("EVENT ")) continue;
            var parts = line.Substring(6).Split(' ', 3);
            var obj = parts[0];
            var ev = parts.Length > 1 ? parts[1] : "";
            try
            {
                if (handlers.TryGetValue($"{obj}_{ev}", out var m))
                {
                    var ps = m.GetParameters();
                    var e = RadEvent.Parse(obj, ev, parts.Length > 2 ? parts[2] : "");
                    object[] call = ps.Length == 0 ? Array.Empty<object>() : new object[] { e };
                    var r = m.Invoke(null, call);
                    if (r is Task t) t.GetAwaiter().GetResult();
                    if (e.Cancel) Rad.Set(obj, "Cancel", true);       // FormClosing: e.Cancel = true keeps the form
                }
            }
            catch (Exception ex)
            {
                var inner = ex is TargetInvocationException tie && tie.InnerException != null ? tie.InnerException : ex;
                Console.Error.WriteLine($"Error in {obj}_{ev}: {inner.GetType().Name}: {inner.Message}");
                foreach (var st in (inner.StackTrace ?? "").Split('\n'))
                {
                    if (st.Contains("System.RuntimeMethodHandle") || st.Contains("System.Reflection.")) break;
                    Console.Error.WriteLine(st.TrimEnd());
                }
            }
            finally
            {
                Rad.Send("DONE");
            }
        }
        return 0;
    }
}

/// <summary>RAD Hub worker: {"id":7,"func":"add","args":[2,3]} -> {"id":7,"result":5}</summary>
public static class RadWorker
{
    static readonly JsonSerializerOptions Opts = new() { IncludeFields = true };

    public static int Serve(string module)
    {
        var type = typeof(RadWorker).Assembly.GetTypes()
            .FirstOrDefault(t => string.Equals(t.Name, module, StringComparison.OrdinalIgnoreCase));
        if (type == null)
        {
            Console.Error.WriteLine($"[csharp worker] class '{module}' was not found in the project");
        }
        string line;
        while ((line = Rad.ReadLine()) != null)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            JsonElement id = default;
            string reply;
            try
            {
                using var doc = JsonDocument.Parse(line);
                var root = doc.RootElement;
                if (root.TryGetProperty("id", out var i)) id = i.Clone();
                var func = root.GetProperty("func").GetString();
                var args = root.TryGetProperty("args", out var a) && a.ValueKind == JsonValueKind.Array
                    ? a.EnumerateArray().Select(x => x.Clone()).ToArray() : Array.Empty<JsonElement>();
                if (type == null) throw new InvalidOperationException($"class '{module}' was not found");
                var result = Invoke(type, func, args);
                reply = JsonSerializer.Serialize(new Dictionary<string, object> { ["id"] = id, ["result"] = result }, Opts);
            }
            catch (Exception ex)
            {
                var inner = ex is TargetInvocationException tie && tie.InnerException != null ? tie.InnerException : ex;
                reply = JsonSerializer.Serialize(new Dictionary<string, object>
                    { ["id"] = id, ["error"] = $"{inner.GetType().Name}: {inner.Message}" });
            }
            Rad.Send(reply);
        }
        return 0;
    }

    static object Invoke(Type type, string func, JsonElement[] args)
    {
        var candidates = type.GetMethods(BindingFlags.Public | BindingFlags.Static)
            .Where(m => string.Equals(m.Name, func, StringComparison.OrdinalIgnoreCase)).ToList();
        if (candidates.Count == 0) throw new MissingMethodException($"{type.Name} has no public static method '{func}'");
        Exception last = null;
        foreach (var m in candidates.OrderBy(m => m.GetParameters().Length == args.Length ? 0 : 1))
        {
            var ps = m.GetParameters();
            bool hasParams = ps.Length > 0 && IsParams(ps[^1]);
            if ((args.Length > ps.Length && !hasParams) || args.Length < ps.Count(p => !p.IsOptional && !IsParams(p))) continue;
            try
            {
                var call = new object[ps.Length];
                for (int i = 0; i < ps.Length; i++)
                {
                    if (IsParams(ps[i]))
                    {
                        var et = ps[i].ParameterType.GetElementType();
                        var rest = Array.CreateInstance(et, Math.Max(0, args.Length - i));
                        for (int j = i; j < args.Length; j++) rest.SetValue(Convert(args[j], et), j - i);
                        call[i] = rest;
                        break;
                    }
                    call[i] = i < args.Length ? Convert(args[i], ps[i].ParameterType) : ps[i].DefaultValue;
                }
                var r = m.Invoke(null, call);
                if (r is Task t)
                {
                    t.GetAwaiter().GetResult();
                    var rp = t.GetType().GetProperty("Result");
                    r = rp != null && rp.PropertyType.Name != "VoidTaskResult" ? rp.GetValue(t) : null;
                }
                return r;
            }
            catch (Exception ex) when (ex is JsonException || ex is InvalidOperationException || ex is FormatException)
            {
                last = ex;
            }
        }
        throw last ?? new ArgumentException($"{type.Name}.{func}: wrong number of arguments ({args.Length})");
    }

    static bool IsParams(ParameterInfo p) => p.GetCustomAttribute<ParamArrayAttribute>() != null;

    static object Convert(JsonElement e, Type t)
    {
        if (t == typeof(object)) return Rad.Plain(e);
        if (t == typeof(string) && e.ValueKind != JsonValueKind.String && e.ValueKind != JsonValueKind.Null) return e.ToString();
        return e.Deserialize(t, Opts);
    }
}
