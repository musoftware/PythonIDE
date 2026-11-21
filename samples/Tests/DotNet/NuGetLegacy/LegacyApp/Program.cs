using System;

namespace LegacyApp
{
    // NuGet test (.NET Framework 4.8, packages.config): install Newtonsoft.Json, then uncomment the line below.
    internal static class Program
    {
        private static void Main()
        {
            Console.WriteLine("LegacyApp");
            // Console.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new { Name = "RAD IDE" }));
        }
    }
}
