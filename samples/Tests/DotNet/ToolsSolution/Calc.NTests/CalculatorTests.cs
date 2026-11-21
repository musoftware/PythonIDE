using Calc;

namespace Calc.NTests;

public class CalculatorTests
{
    private Calculator _calc = null!;

    [SetUp]
    public void Setup()
    {
        _calc = new Calculator();
    }

    [Test]
    public void Divide_Exact()
    {
        Assert.That(_calc.Divide(10, 2), Is.EqualTo(5));
    }

    [TestCase(1, 1, 2)]
    [TestCase(2, 2, 4)]
    public void Add_Cases(int a, int b, int expected)
    {
        Assert.That(_calc.Add(a, b), Is.EqualTo(expected));
    }
}
