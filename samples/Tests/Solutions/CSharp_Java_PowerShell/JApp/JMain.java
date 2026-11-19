public class JMain {
    public static String run() {
        double a = CsLib.Add(1.5, 2);                 // C# library (typed)
        String g = CsLib.Greet("Java");
        boolean even = CsLib.IsEven(4);
        Object r = CsLib.Range(4);                    // List
        Object p = PyLib.Add(2, 3);                   // Python library (Object)
        String pg = (String) PyLib.Greet("J");
        Object s = PsLib.Sub(9, 2);
        CsLib.Log("from Java");
        return a + "|" + g + "|" + even + "|" + r + "|" + p + "|" + pg + "|" + s;
    }
}
