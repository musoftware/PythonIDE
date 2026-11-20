namespace MathLib;

/// <summary>Small library used by ConsoleApp and WinApp (project reference).</summary>
public static class Calculator
{
    public static int Add(int a, int b)
    {
        int sum = a + b;
        return sum;
    }

    public static int Multiply(int a, int b) => a * b;
}
