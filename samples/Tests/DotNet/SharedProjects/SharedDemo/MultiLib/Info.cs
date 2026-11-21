namespace MultiLib
{
    public static class Info
    {
#if NETSTANDARD2_0
        public const string Target = "netstandard2.0";
#else
        public const string Target = "net8.0";
#endif
    }
}
