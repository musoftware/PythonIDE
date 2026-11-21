using System;

namespace LegacyConsumer
{
    internal static class Program
    {
        private static void Main()
        {
            // The Reference Manager test adds: System.Numerics (Framework), MathKit.dll (Browse),
            // Microsoft Scripting Runtime (COM) and ..\Common\SharedHelper.cs (Add As Link), then defines
            // the symbols below and builds with Visual Studio's MSBuild.
#if NUMERICS
            Console.WriteLine("BigInteger: " + System.Numerics.BigInteger.Pow(2, 100));
#endif
#if MATHKIT
            Console.WriteLine("MathKit: " + new MathKit.Calculator().Add(40, 2));
#endif
#if SCRIPTING
            var fso = new Scripting.FileSystemObject();
            Console.WriteLine("Scripting: temp folder exists = " + fso.FolderExists(System.IO.Path.GetTempPath()));
#endif
#if LINKED
            Console.WriteLine(Common.SharedHelper.Greet("linked file"));
#endif
            Console.WriteLine("LegacyConsumer done");
        }
    }
}
