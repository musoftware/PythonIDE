// Debugger test (Java / JDWP): breakpoints, steps, expandable Locals, hit counts, logpoints.
public class Form1 extends Form1Designer {
    static class Point {
        int x;
        int y;
        String label;
        Point(int x, int y, String label) { this.x = x; this.y = y; this.label = label; }
    }

    static int square(int n) {
        int result = n * n;
        return result;
    }

    static void Form1_Load(RadEvent e) {
        int[] numbers = {3, 1, 4, 1, 5};
        Point p = new Point(10, 20, "corner");
        String name = "RAD";
        int total = 0;
        for (int i = 0; i < numbers.length; i++) {
            total += square(numbers[i]);
        }
        System.out.println("total=" + total + " " + name + " " + p.label);
    }
}
