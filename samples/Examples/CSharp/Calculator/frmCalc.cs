// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Calculator - a pocket calculator in C# (RAD IDE GUI Bridge; Build > Publish = native WinForms exe).
//
// The arithmetic is a small engine class (CalcEngine) using decimal (no 0.1 + 0.2 rounding surprises);
// the event handlers turn buttons and keys into engine calls. Errors are exceptions caught in one place.
// Shows: many buttons, keyboard input on the form (KeyPress: the key name / code and e.KeyChar, the
// character), exception handling (DivideByZeroException, OverflowException), decimal arithmetic.
using System;
using System.Globalization;

public static partial class frmCalc
{
    static readonly CalcEngine calc = new CalcEngine();

    static void Refresh()
    {
        lblDisplay.Caption = calc.Display;
        lblExpr.Caption = calc.Expression;
        lblMemory.Caption = calc.Memory != 0 ? "M" : "";
    }

    static void Do(Action action)
    {
        try { action(); }
        catch (DivideByZeroException) { calc.Fail("division by zero"); }
        catch (OverflowException) { calc.Fail("overflow"); }
        catch (ArgumentException ex) { calc.Fail(ex.Message); }
        Refresh();
    }

    static void frmCalc_Load(RadEvent e) => Refresh();

    static void btn0_Click(RadEvent e) => Do(() => calc.Digit("0"));
    static void btn1_Click(RadEvent e) => Do(() => calc.Digit("1"));
    static void btn2_Click(RadEvent e) => Do(() => calc.Digit("2"));
    static void btn3_Click(RadEvent e) => Do(() => calc.Digit("3"));
    static void btn4_Click(RadEvent e) => Do(() => calc.Digit("4"));
    static void btn5_Click(RadEvent e) => Do(() => calc.Digit("5"));
    static void btn6_Click(RadEvent e) => Do(() => calc.Digit("6"));
    static void btn7_Click(RadEvent e) => Do(() => calc.Digit("7"));
    static void btn8_Click(RadEvent e) => Do(() => calc.Digit("8"));
    static void btn9_Click(RadEvent e) => Do(() => calc.Digit("9"));
    static void btnDot_Click(RadEvent e) => Do(() => calc.Digit("."));
    static void btnAdd_Click(RadEvent e) => Do(() => calc.Operation('+'));
    static void btnSub_Click(RadEvent e) => Do(() => calc.Operation('-'));
    static void btnMul_Click(RadEvent e) => Do(() => calc.Operation('*'));
    static void btnDiv_Click(RadEvent e) => Do(() => calc.Operation('/'));
    static void btnEquals_Click(RadEvent e) => Do(calc.Result);
    static void btnClear_Click(RadEvent e) => Do(calc.Clear);
    static void btnSign_Click(RadEvent e) => Do(() => calc.Unary('n'));
    static void btnSqrt_Click(RadEvent e) => Do(() => calc.Unary('s'));
    static void btnPercent_Click(RadEvent e) => Do(() => calc.Unary('%'));
    static void btnBack_Click(RadEvent e) => Do(calc.Back);
    static void btnMC_Click(RadEvent e) => Do(() => calc.Memory = 0);
    static void btnMR_Click(RadEvent e) => Do(calc.MemoryRecall);
    static void btnMPlus_Click(RadEvent e) => Do(calc.MemoryAdd);

    // the form gets the keys of all its controls. The key name is the 4th word of e.Args ("Return" in the IDE's
    // bridge, the key code "13" in the WinForms exe), the character is e.KeyChar.
    static void frmCalc_KeyPress(RadEvent e) => Do(() =>
    {
        string ch = e.KeyChar;
        string[] a = e.Args.Split(' ');
        string key = a.Length > 3 ? a[3] : "";
        if (ch.Length == 1 && char.IsDigit(ch[0])) calc.Digit(ch);
        else if (ch == "." || ch == ",") calc.Digit(".");
        else if (ch.Length == 1 && "+-*/".IndexOf(ch[0]) >= 0) calc.Operation(ch[0]);
        else if (ch == "=" || ch == "\r" || key == "Return" || key == "13") calc.Result();
        else if (ch == "\u001b" || key == "Escape" || key == "27") calc.Clear();
        else if (ch == "\b" || key == "BackSpace" || key == "8") calc.Back();
    });
}

/// <summary>The calculator itself - no GUI code here.</summary>
public class CalcEngine
{
    public string Display { get; private set; } = "0";
    public string Expression { get; private set; } = "";
    public decimal Memory { get; set; }
    bool error, fresh = true;
    decimal acc;
    char op;

    decimal Value => decimal.Parse(Display, CultureInfo.InvariantCulture);
    static string Format(decimal x) => x.ToString("0.############", CultureInfo.InvariantCulture);

    void Show(decimal x)
    {
        if (Math.Abs(x) > 1e15m) throw new OverflowException();
        Display = Format(x);
    }

    public void Digit(string d)
    {
        if (error) Clear();
        if (fresh) { Display = d == "." ? "0" : ""; fresh = false; }
        if (d == "." && Display.Contains(".")) return;
        if (Display.Length >= 16) return;
        if (Display == "0" && d != ".") Display = "";
        Display += d;
    }

    void Apply()
    {
        decimal x = Value;
        switch (op)
        {
            case '+': acc += x; break;
            case '-': acc -= x; break;
            case '*': acc *= x; break;
            case '/': acc /= x; break;            // DivideByZeroException for x = 0
            default: acc = x; break;
        }
        Show(acc);
    }

    public void Operation(char o)
    {
        if (error) return;
        if (!fresh || op == 0) Apply();
        op = o;
        fresh = true;
        Expression = $"{Format(acc)} {o}";
    }

    public void Result()
    {
        if (error || op == 0) return;
        Apply();
        op = '\0';
        fresh = true;
        Expression = "";
    }

    public void Clear()
    {
        Display = "0";
        Expression = "";
        acc = 0;
        op = '\0';
        fresh = true;
        error = false;
    }

    public void Unary(char what)
    {
        if (error) return;
        decimal x = Value;
        if (what == 'n') x = -x;
        else if (what == 's')
        {
            if (x < 0) throw new ArgumentException("negative square root");
            x = (decimal)Math.Sqrt((double)x);
            fresh = true;
        }
        else if (what == '%') x = op != 0 ? acc * x / 100 : x / 100;
        Show(x);
    }

    public void Back()
    {
        if (error || fresh) return;
        Display = Display.Substring(0, Display.Length - 1);
        if (Display == "" || Display == "-") Display = "0";
    }

    public void MemoryAdd() { if (!error) { Memory += Value; fresh = true; } }
    public void MemoryRecall() { if (!error) { Show(Memory); fresh = true; } }

    public void Fail(string why)
    {
        Display = "Error: " + why;
        Expression = "";
        error = true;
        op = '\0';
        fresh = true;
    }
}
