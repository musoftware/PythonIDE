public static class CV {
    public static int Total(params int[] xs) { int t = 0; foreach (var x in xs) t += x; return t; }
}
