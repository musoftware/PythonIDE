namespace App.Tests;

public class GreeterTests
{
    [Fact]
    public void HelloFormatsTheName() => Assert.Equal("Hello, VS!", Core.Greeter.Hello("VS"));
}
