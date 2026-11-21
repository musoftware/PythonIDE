using Calc;

namespace Calc.XTests;

public class CalculatorTests
{
    [Fact]
    public void Add_TwoNumbers_ReturnsSum()
    {
        var c = new Calculator();
        Assert.Equal(5, c.Add(2, 3));
    }

    [Theory]
    [InlineData(5, 3, 2)]
    [InlineData(10, 4, 6)]
    public void Subtract_Works(int a, int b, int expected)
    {
        Assert.Equal(expected, new Calculator().Subtract(a, b));
    }

    [Fact]
    public void Add_IntentionalFailure()
    {
        Assert.Equal(7, new Calculator().Add(2, 3));
    }
}
