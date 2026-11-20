package hello;

public class Main {
    public static void main(String[] args) {
        String who = args.length > 0 ? args[0] : "Eclipse";
        System.out.println("Hello, " + who + "!");
    }
}
