// RAD IDE sample: prints what the launch profile passed (arguments, environment, working directory)
// and a value from the Core class library.
using Core;

Console.WriteLine($"Greeting: {Greeter.Hello("RAD IDE")}");
Console.WriteLine($"Args: {string.Join(" | ", args)}");
Console.WriteLine($"RADIDE_SAMPLE={Environment.GetEnvironmentVariable("RADIDE_SAMPLE") ?? "(not set)"}");
Console.WriteLine($"Cwd: {Environment.CurrentDirectory}");
