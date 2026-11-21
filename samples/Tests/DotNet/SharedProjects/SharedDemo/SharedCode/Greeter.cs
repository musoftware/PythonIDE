namespace SharedCode
{
    public static class Greeter
    {
        public static string Hello()
        {
#if NET8_0_OR_GREATER
            return "Hello from .NET 8+ (shared C#)";
#elif NETFRAMEWORK
            return "Hello from SDK-style .NET Framework (shared C#)";
#else
            return "Hello from .NET Framework 4.8 old-style (shared C#)";
#endif
        }

#if DEBUG
        public static string Configuration => "Debug";
#else
        public static string Configuration => "Release";
#endif
    }
}
