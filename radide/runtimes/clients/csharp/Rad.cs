// RAD IDE - GUI Bridge client for C#.
// Copied into the project's _build folder every time the program runs: do not edit this copy.
//
// Every file of the project can use these helpers without a prefix (global using static):
//   Set(obj, prop, value)      Get(obj, prop)       Call(obj, method, args...)
//   MsgBox(text)               InputBox(prompt)     Show(form) / Hide(form)   End()
//   radcall("Module.function", args...)   - call a function of any project module (any language)
// and the typed control fields generated in <Form>_designer.cs:  lblOut.Text = "Hi"; lstLog.AddItem("x");
global using static Rad;

using System.Globalization;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

/// <summary>Arguments of a GUI event (mouse / key data when the event has them).</summary>
public class RadEvent
{
    public string Sender = "";      // control or form name
    public string Name = "";        // event name (Click, TextChanged, ...)
    public string Args = "";        // raw argument text
    public int X, Y, Button, KeyCode;
    public string KeyChar = "";

    public static RadEvent Parse(string sender, string name, string args)
    {
        var e = new RadEvent { Sender = sender, Name = name, Args = args ?? "" };
        var p = e.Args.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        int I(int i) => i < p.Length && int.TryParse(p[i], NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : 0;
        e.X = I(0); e.Y = I(1); e.Button = I(2); e.KeyCode = I(3);
        e.KeyChar = p.Length > 4 ? p[4] : "";
        return e;
    }
}

/// <summary>A control (or form) on a RAD IDE form. Property and method names are VB-style.</summary>
public class RadControl
{
    public string Path { get; }
    public RadControl(string path) { Path = path; }

    public string this[string prop] { get => Rad.Get(Path, prop); set => Rad.Set(Path, prop, value); }

    public string Text { get => Rad.Get(Path, "Text"); set => Rad.Set(Path, "Text", value); }
    public string Caption { get => Rad.Get(Path, "Caption"); set => Rad.Set(Path, "Caption", value); }
    public string Value { get => Rad.Get(Path, "Value"); set => Rad.Set(Path, "Value", value); }
    public bool Enabled { get => Rad.ToBool(Rad.Get(Path, "Enabled")); set => Rad.Set(Path, "Enabled", value); }
    public bool Visible { get => Rad.ToBool(Rad.Get(Path, "Visible")); set => Rad.Set(Path, "Visible", value); }
    public int Left { get => Rad.ToInt(Rad.Get(Path, "Left")); set => Rad.Set(Path, "Left", value); }
    public int Top { get => Rad.ToInt(Rad.Get(Path, "Top")); set => Rad.Set(Path, "Top", value); }
    public int Width { get => Rad.ToInt(Rad.Get(Path, "Width")); set => Rad.Set(Path, "Width", value); }
    public int Height { get => Rad.ToInt(Rad.Get(Path, "Height")); set => Rad.Set(Path, "Height", value); }
    public string BackColor { get => Rad.Get(Path, "BackColor"); set => Rad.Set(Path, "BackColor", value); }
    public string ForeColor { get => Rad.Get(Path, "ForeColor"); set => Rad.Set(Path, "ForeColor", value); }
    public int ListIndex { get => Rad.ToInt(Rad.Get(Path, "ListIndex")); set => Rad.Set(Path, "ListIndex", value); }
    public int ListCount => Rad.ToInt(Rad.Get(Path, "ListCount"));
    public int Interval { get => Rad.ToInt(Rad.Get(Path, "Interval")); set => Rad.Set(Path, "Interval", value); }

    public string Call(string method, params object[] args) => Rad.Call(Path, method, args);
    public void AddItem(object item) => Rad.Call(Path, "AddItem", item);
    public void RemoveItem(int index) => Rad.Call(Path, "RemoveItem", index);
    public void Clear() => Rad.Call(Path, "Clear");
    public string List(int index) => Rad.Call(Path, "List", index);
    public void SetFocus() => Rad.Call(Path, "SetFocus");
    public void Move(int left, int top, int width, int height) => Rad.Call(Path, "Move", left, top, width, height);
    public string ShowDialog() => Rad.Call(Path, "ShowDialog");
    public void Show() => Rad.Show(Path);
    public void Hide() => Rad.Hide(Path);
    public override string ToString() => Text;
}

/// <summary>Raised when radcall() gets an error from the RAD Hub or the called function.</summary>
public class RadCallException : Exception
{
    public RadCallException(string message) : base(message) { }
}

public static class Rad
{
    static TextReader _in = Console.In;
    static TextWriter _out = Console.Out;
    static readonly object _lock = new();

    /// <summary>Called by the generated main program. Switches stdin/stdout to UTF-8 (protocol channel).
    /// In worker mode the user's Console output goes to stderr so stdout stays JSON only.</summary>
    public static void Init(bool worker = false)
    {
        var utf8 = new UTF8Encoding(false);
        _in = new StreamReader(Console.OpenStandardInput(), utf8);
        _out = new StreamWriter(Console.OpenStandardOutput(), utf8) { AutoFlush = true, NewLine = "\n" };
        var err = new StreamWriter(Console.OpenStandardError(), utf8) { AutoFlush = true };
        Console.SetError(err);
        Console.SetOut(worker ? err : _out);
        Console.SetIn(_in);
    }

    internal static string ReadLine() => _in.ReadLine();

    internal static void Send(string line)
    {
        lock (_lock) { _out.Write(line + "\n"); _out.Flush(); }
    }

    static string Ask(string line)
    {
        lock (_lock)
        {
            Send(line);
            var answer = _in.ReadLine();
            if (answer == null) Environment.Exit(0);       // the IDE closed the program
            return Unesc(answer);                          // answers to ESC commands are escaped
        }
    }

    /// <summary>Value as bridge text: invariant culture, True/False, one line.</summary>
    public static string Str(object value) =>
        Text(value).Replace("\r\n", " ").Replace('\n', ' ').Replace('\r', ' ');

    static string Text(object value) => value switch
    {
        null => "",
        bool b => b ? "True" : "False",
        IFormattable f => f.ToString(null, CultureInfo.InvariantCulture),
        _ => value.ToString() ?? "",
    };

    /// <summary>Value for an "ESC" command: \\ newline CR escaped, so multi-line text survives the line protocol.</summary>
    static string Esc(object value) => Text(value).Replace("\\", "\\\\").Replace("\n", "\\n").Replace("\r", "\\r");

    /// <summary>Answer to an "ESC" command, unescaped.</summary>
    static string Unesc(string s)
    {
        if (s.IndexOf('\\') < 0) return s;
        var sb = new System.Text.StringBuilder(s.Length);
        for (int i = 0; i < s.Length; i++)
        {
            char c = s[i];
            if (c == '\\' && i + 1 < s.Length && (s[i + 1] == '\\' || s[i + 1] == 'n' || s[i + 1] == 'r'))
            {
                char n = s[++i];
                sb.Append(n == 'n' ? '\n' : n == 'r' ? '\r' : '\\');
            }
            else sb.Append(c);
        }
        return sb.ToString();
    }

    public static bool ToBool(string s) =>
        s != null && (s.Equals("true", StringComparison.OrdinalIgnoreCase) || s == "1" || s == "-1");

    public static int ToInt(string s) =>
        double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d) ? (int)Math.Round(d) : 0;

    public static double ToNumber(string s) =>
        double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d) ? d : 0;

    // ------------------------------------------------------------------ GUI
    public static void Set(string obj, string prop, object value) => Send($"ESC SET {obj} {prop} {Esc(value)}");
    public static string Get(string obj, string prop) => Ask($"ESC GET {obj} {prop}");
    public static double GetNumber(string obj, string prop) => ToNumber(Get(obj, prop));

    public static string Call(string obj, string method, params object[] args)
    {
        var line = $"ESC CALL {obj} {method}";
        if (args != null && args.Length > 0) line += " " + string.Join("\t", args.Select(Esc));
        return Ask(line);
    }

    public static int MsgBox(object text) => ToInt(Ask($"ESC MSGBOX {Esc(text)}"));
    public static string InputBox(object prompt) => Ask($"ESC INPUT {Esc(prompt)}");
    public static void Show(string form) => Send($"SHOW {form}");
    public static void Hide(string form) => Send($"HIDE {form}");

    /// <summary>Close the program.</summary>
    public static void End()
    {
        Send("END");
        Environment.Exit(0);
    }

    // ------------------------------------------------------------------ RAD Hub (cross-language calls)
    static TcpClient _hub;
    static StreamReader _hubIn;
    static StreamWriter _hubOut;
    static int _hubId;

    /// <summary>Call "Module.function" of any project module (C#, Python, Ring, ...). Returns plain values:
    /// long/double, string, bool, null, List&lt;object&gt;, Dictionary&lt;string, object&gt;.</summary>
    public static object radcall(string function, params object[] args) => Plain(HubCall(function, args));

    /// <summary>Typed variant: radcall&lt;int&gt;("Helpers.add", 2, 3).</summary>
    public static T radcall<T>(string function, params object[] args) => HubCall(function, args).Deserialize<T>();

    /// <summary>Used by the generated reference proxies (&lt;Lib&gt;.ref.cs, Add Reference): a plain value as
    /// <c>dynamic</c>; whole numbers that fit are <c>int</c> so <c>int n = MathLib.Count();</c> works.</summary>
    public static dynamic RefCall(string function, params object[] args)
    {
        var r = Plain(HubCall(function, args));
        return r is long l && l >= int.MinValue && l <= int.MaxValue ? (int)l : r;
    }

    static JsonElement HubCall(string function, object[] args)
    {
        lock (_lock)
        {
            if (_hub == null)
            {
                var addr = Environment.GetEnvironmentVariable("RAD_HUB");
                if (string.IsNullOrEmpty(addr)) throw new RadCallException("RAD Hub is not running (RAD_HUB is not set)");
                var i = addr.LastIndexOf(':');
                _hub = new TcpClient(addr[..i], int.Parse(addr[(i + 1)..], CultureInfo.InvariantCulture)) { NoDelay = true };
                var s = _hub.GetStream();
                _hubIn = new StreamReader(s, new UTF8Encoding(false));
                _hubOut = new StreamWriter(s, new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };
            }
            var id = ++_hubId;
            var req = new Dictionary<string, object> { ["id"] = id, ["call"] = function, ["args"] = args ?? Array.Empty<object>() };
            _hubOut.WriteLine(JsonSerializer.Serialize(req));
            while (true)
            {
                var line = _hubIn.ReadLine() ?? throw new RadCallException("RAD Hub closed the connection");
                using var doc = JsonDocument.Parse(line);
                var root = doc.RootElement;
                if (root.TryGetProperty("id", out var rid) && rid.ValueKind == JsonValueKind.Number && rid.GetInt32() != id) continue;
                if (root.TryGetProperty("error", out var err) && err.ValueKind != JsonValueKind.Null)
                    throw new RadCallException($"{function}: {(err.ValueKind == JsonValueKind.String ? err.GetString() : err.ToString())}");
                return root.TryGetProperty("result", out var res) ? res.Clone() : default;
            }
        }
    }

    /// <summary>JsonElement -> plain .NET value.</summary>
    public static object Plain(JsonElement e) => e.ValueKind switch
    {
        JsonValueKind.String => e.GetString(),
        JsonValueKind.Number => e.TryGetInt64(out var l) ? (object)l : e.GetDouble(),   // (object): keep long
        JsonValueKind.True => true,
        JsonValueKind.False => false,
        JsonValueKind.Array => e.EnumerateArray().Select(Plain).ToList(),
        JsonValueKind.Object => e.EnumerateObject().ToDictionary(p => p.Name, p => Plain(p.Value)),
        _ => null,
    };
}
