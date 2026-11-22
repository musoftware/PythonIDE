// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// AppSettings - the settings of the Greeting Cards example (a code module shared by the three forms),
// stored in settings.ini (key=value lines, UTF-8) next to the program.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

public static class AppSettings
{
    const string FileName = "settings.ini";
    public static string User = "Friend";
    public static string Language = "English";          // "English" or "العربية"
    public static int FontSize = 11;
    public static bool Formal;

    public static bool Arabic => Language != "English";

    public static void Load()
    {
        if (!File.Exists(FileName)) return;
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var line in File.ReadAllLines(FileName, Encoding.UTF8))
        {
            int eq = line.IndexOf('=');
            if (eq > 0 && !line.StartsWith("#") && !line.StartsWith("[")) values[line.Substring(0, eq).Trim()] = line.Substring(eq + 1);
        }
        string v;
        if (values.TryGetValue("user", out v) && v != "") User = v;
        if (values.TryGetValue("language", out v) && v != "") Language = v;
        if (values.TryGetValue("font_size", out v) && int.TryParse(v, out int size) && size >= 8 && size <= 24) FontSize = size;
        if (values.TryGetValue("formal", out v)) Formal = v == "1";
    }

    public static bool Save()
    {
        try
        {
            File.WriteAllLines(FileName, new[]
            {
                "[GreetingCards]", "user=" + User, "language=" + Language, "font_size=" + FontSize,
                "formal=" + (Formal ? "1" : "0"),
            }, new UTF8Encoding(false));
            return true;
        }
        catch (IOException)
        {
            return false;
        }
    }
}
