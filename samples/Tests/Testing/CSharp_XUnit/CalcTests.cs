using Xunit;

namespace CalcLib.Tests;

public class CalcTests
{
    [Fact]
    public void Add_TwoNumbers()
    {
        Assert.Equal(5, Calc.Add(2, 3));
    }

    [Fact]
    public void FailsOnPurpose()
    {
        Assert.Equal(5, Calc.Add(2, 2));
    }

    [Theory]
    [InlineData(1, 1, 2)]
    [InlineData(-1, 1, 0)]
    public void Add_Cases(int a, int b, int expected)
    {
        Assert.Equal(expected, Calc.Add(a, b));
    }
}
