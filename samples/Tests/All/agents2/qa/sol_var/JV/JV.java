public class JV {
    public static int sum(int... xs) { int t = 0; for (int x : xs) t += x; return t; }
    public static String join(String sep, String... parts) { return String.join(sep, parts); }
}
