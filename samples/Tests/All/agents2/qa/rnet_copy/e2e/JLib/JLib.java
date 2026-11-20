import java.util.*;
public class JLib {
    /** Multiplies two numbers. */
    public static double mul(double a, double b) { return a * b; }
    public static String shout(String s) { return s.toUpperCase() + "!"; }
    public static long big(int n) { return n * 1000000000L; }
    public static List<Object> pair(Object a, Object b) { return Arrays.asList(a, b); }
    public static int sum(int... xs) { int t = 0; for (int x : xs) t += x; return t; }
}
