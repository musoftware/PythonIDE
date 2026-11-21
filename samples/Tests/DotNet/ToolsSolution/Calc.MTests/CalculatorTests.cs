using Calc;

namespace Calc.MTests;

[TestClass]
public sealed class CalculatorTests
{
    [TestMethod]
    public void Subtract_Positive()
    {
        Assert.AreEqual(1, new Calculator().Subtract(3, 2));
    }

    [TestMethod]
    public void Divide_ByZero_Throws()
    {
        Assert.ThrowsException<DivideByZeroException>(() => new Calculator().Divide(1, 0));
    }
}
