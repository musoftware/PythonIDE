using Contoso.Core;

Console.WriteLine("ARGS=" + string.Join("|", args));
Console.WriteLine("ENV=" + Environment.GetEnvironmentVariable("CONTOSO_MODE"));
Console.WriteLine("CWD=" + Environment.CurrentDirectory);
Console.WriteLine("GREETING=" + Greeter.Hello("Visual Studio"));
