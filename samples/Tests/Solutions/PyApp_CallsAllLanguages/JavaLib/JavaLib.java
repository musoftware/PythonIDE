// Class Library JavaLib. Its public static methods are the library's public functions:
// a project that references JavaLib (Add Reference) calls them as native code -
//     JavaLib.add(2, 3)   in Java, C#, Python, JavaScript ...   JavaLib_add(2, 3) in Ring
// Arguments and results are JSON values: numbers, strings, booleans, null, lists, maps.
public class JavaLib {
    /** Adds two numbers. */
    public static double add(double a, double b) {
        return a + b;
    }

    /** Returns a greeting. */
    public static String greet(String name) {
        return "Hello, " + name + "!";
    }
}
