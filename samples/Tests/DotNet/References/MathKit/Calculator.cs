using System.Collections.Generic;

namespace MathKit
{
    /// <summary>Small arithmetic helpers used by the Reference Manager tests.</summary>
    public class Calculator
    {
        /// <summary>Adds two integers.</summary>
        /// <param name="a">The first number.</param>
        /// <param name="b">The second number.</param>
        /// <returns>The sum of <paramref name="a"/> and <paramref name="b"/>.</returns>
        public int Add(int a, int b) => a + b;

        /// <summary>The numbers added so far.</summary>
        public List<int> History { get; } = new List<int>();

        /// <summary>Raised after every calculation.</summary>
        public event System.EventHandler Calculated;

        /// <summary>Multiplies and remembers the result.</summary>
        public int Multiply(int a, int b)
        {
            int r = a * b;
            History.Add(r);
            Calculated?.Invoke(this, System.EventArgs.Empty);
            return r;
        }

        /// <summary>The greatest common divisor.</summary>
        public static int Gcd(int a, int b) => b == 0 ? a : Gcd(b, a % b);
    }

    /// <summary>Supported operations.</summary>
    public enum Operation { Add, Subtract, Multiply, Divide }

    /// <summary>A 2D point.</summary>
    public struct Vector2
    {
        /// <summary>X coordinate.</summary>
        public double X;
        /// <summary>Y coordinate.</summary>
        public double Y;
        /// <summary>Creates a point.</summary>
        public Vector2(double x, double y) { X = x; Y = y; }
        /// <summary>Adds two points.</summary>
        public static Vector2 operator +(Vector2 a, Vector2 b) => new Vector2(a.X + b.X, a.Y + b.Y);
    }
}
