using Contoso.Core;

namespace Contoso.Tests;

public class UnitTest1
{
    [Fact]
    public void HelloGreets() => Assert.Equal("Hello, X!", Greeter.Hello("X"));
}
