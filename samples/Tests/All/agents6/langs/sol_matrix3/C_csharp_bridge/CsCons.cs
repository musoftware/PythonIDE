public static class CsCons {
    public static string T_GoLib() { object r = GoLib.Add(2, 3); return System.Convert.ToString(r, System.Globalization.CultureInfo.InvariantCulture); }
    public static string T_LuaLib() { object r = LuaLib.Add(2, 3); return System.Convert.ToString(r, System.Globalization.CultureInfo.InvariantCulture); }
    public static string T_RbLib() { object r = RbLib.Add(2, 3); return System.Convert.ToString(r, System.Globalization.CultureInfo.InvariantCulture); }
    public static string T_PyLib() { object r = PyLib.Add(2, 3); return System.Convert.ToString(r, System.Globalization.CultureInfo.InvariantCulture); }
    public static string T_CsLib() { object r = CsLib.Add(2, 3); return System.Convert.ToString(r, System.Globalization.CultureInfo.InvariantCulture); }
}
