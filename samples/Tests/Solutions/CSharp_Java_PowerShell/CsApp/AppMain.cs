public static class AppMain
{
    public static string Run()
    {
        double s = PyLib.Add(2, 3);           // Python library (dynamic)
        int n = PyLib.Add(20, 22);            // whole numbers come back as int
        string g = PyLib.Greet("C#");
        var items = PyLib.Items(3);
        double m = JLib.mul(4, 2.5);          // Java library (typed: double)
        long big = JLib.big(3);
        int total = JLib.sum(1, 2, 3, 4);
        string up = JLib.shout("hey");
        dynamic sub = PsLib.Sub(10, 4);       // PowerShell library
        string u = PsLib.Get_Upper("abc");
        return $"{s}|{n}|{g}|{items.Count}|{m}|{big}|{total}|{up}|{sub}|{u}";
    }
}
