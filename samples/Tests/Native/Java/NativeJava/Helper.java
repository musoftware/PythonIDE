// Module Helper.
public class Helper {
    public static String greet(String name) {
        return "Hello, " + name + "!";
    }

    public static String shout(String name) {
        return greet(name).toUpperCase();
    }
}
