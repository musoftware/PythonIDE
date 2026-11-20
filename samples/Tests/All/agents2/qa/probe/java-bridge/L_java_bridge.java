// Class Library L_java_bridge. Its public static methods are the library's public functions:
// a project that references L_java_bridge (Add Reference) calls them as native code -
//     L_java_bridge.add(2, 3)   in Java, C#, Python, JavaScript ...   L_java_bridge_add(2, 3) in Ring
// Arguments and results are JSON values: numbers, strings, booleans, null, lists, maps.
public class L_java_bridge {
    /** Adds two numbers. */
    public static double add(double a, double b) {
        return a + b;
    }

    /** Returns a greeting. */
    public static String greet(String name) {
        return "Hello, " + name + "!";
    }
}
