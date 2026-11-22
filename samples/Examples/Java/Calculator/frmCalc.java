// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Calculator - a pocket calculator in Java (RAD IDE GUI Bridge; Build > Publish = native Swing exe).
//
// The arithmetic uses java.math.BigDecimal (exact decimal results: 0.1 + 0.2 = 0.3) inside a small engine
// class; the handlers translate buttons and keys. Errors are ArithmeticException / IllegalArgumentException
// caught in one place. Shows: many buttons, keyboard input on the form (KeyPress), exceptions, BigDecimal.
import java.math.BigDecimal;
import java.math.MathContext;

public class frmCalc extends frmCalcDesigner {
    static final Engine calc = new Engine();

    static void refresh() {
        lblDisplay.setCaption(calc.display);
        lblExpr.setCaption(calc.expression);
        lblMemory.setCaption(calc.memory.signum() != 0 ? "M" : "");
    }

    static void act(Runnable r) {
        try {
            r.run();
        } catch (ArithmeticException ex) {
            calc.fail(ex.getMessage() != null && ex.getMessage().contains("zero") ? "division by zero" : "overflow");
        } catch (IllegalArgumentException ex) {
            calc.fail(ex.getMessage());
        }
        refresh();
    }

    static void frmCalc_Load(RadEvent e) { refresh(); }

    static void btn0_Click(RadEvent e) { act(() -> calc.digit("0")); }
    static void btn1_Click(RadEvent e) { act(() -> calc.digit("1")); }
    static void btn2_Click(RadEvent e) { act(() -> calc.digit("2")); }
    static void btn3_Click(RadEvent e) { act(() -> calc.digit("3")); }
    static void btn4_Click(RadEvent e) { act(() -> calc.digit("4")); }
    static void btn5_Click(RadEvent e) { act(() -> calc.digit("5")); }
    static void btn6_Click(RadEvent e) { act(() -> calc.digit("6")); }
    static void btn7_Click(RadEvent e) { act(() -> calc.digit("7")); }
    static void btn8_Click(RadEvent e) { act(() -> calc.digit("8")); }
    static void btn9_Click(RadEvent e) { act(() -> calc.digit("9")); }
    static void btnDot_Click(RadEvent e) { act(() -> calc.digit(".")); }
    static void btnAdd_Click(RadEvent e) { act(() -> calc.operation('+')); }
    static void btnSub_Click(RadEvent e) { act(() -> calc.operation('-')); }
    static void btnMul_Click(RadEvent e) { act(() -> calc.operation('*')); }
    static void btnDiv_Click(RadEvent e) { act(() -> calc.operation('/')); }
    static void btnEquals_Click(RadEvent e) { act(calc::result); }
    static void btnClear_Click(RadEvent e) { act(calc::clear); }
    static void btnSign_Click(RadEvent e) { act(() -> calc.unary('n')); }
    static void btnSqrt_Click(RadEvent e) { act(() -> calc.unary('s')); }
    static void btnPercent_Click(RadEvent e) { act(() -> calc.unary('%')); }
    static void btnBack_Click(RadEvent e) { act(calc::back); }
    static void btnMC_Click(RadEvent e) { act(() -> calc.memory = BigDecimal.ZERO); }
    static void btnMR_Click(RadEvent e) { act(calc::memoryRecall); }
    static void btnMPlus_Click(RadEvent e) { act(calc::memoryAdd); }

    // the key name is the 4th word of e.args ("Return" in the IDE's bridge, the character code in the Swing exe)
    static void frmCalc_KeyPress(RadEvent e) {
        String ch = e.keyChar;
        String[] a = e.args.split(" ");
        String key = a.length > 3 ? a[3] : "";
        act(() -> {
            if (ch.length() == 1 && Character.isDigit(ch.charAt(0))) calc.digit(ch);
            else if (ch.equals(".") || ch.equals(",")) calc.digit(".");
            else if (ch.length() == 1 && "+-*/".indexOf(ch.charAt(0)) >= 0) calc.operation(ch.charAt(0));
            else if (ch.equals("=") || ch.equals("\n") || key.equals("Return") || key.equals("10") || key.equals("13")) calc.result();
            else if (key.equals("Escape") || key.equals("27")) calc.clear();
            else if (key.equals("BackSpace") || key.equals("8")) calc.back();
        });
    }

    /** The calculator itself - no GUI code. */
    static class Engine {
        String display = "0", expression = "";
        BigDecimal memory = BigDecimal.ZERO, acc = BigDecimal.ZERO;
        char op = 0;
        boolean fresh = true, error = false;

        BigDecimal value() { return new BigDecimal(display); }

        static String format(BigDecimal x) {
            BigDecimal r = x.round(new MathContext(15)).stripTrailingZeros();
            return r.scale() < 0 ? r.setScale(0).toPlainString() : r.toPlainString();
        }

        void show(BigDecimal x) {
            if (x.abs().compareTo(new BigDecimal("1e15")) > 0) throw new ArithmeticException("overflow");
            display = format(x);
        }

        void digit(String d) {
            if (error) clear();
            if (fresh) { display = d.equals(".") ? "0" : ""; fresh = false; }
            if (d.equals(".") && display.contains(".")) return;
            if (display.length() >= 16) return;
            if (display.equals("0") && !d.equals(".")) display = "";
            display += d;
        }

        void apply() {
            BigDecimal x = value();
            switch (op) {
                case '+': acc = acc.add(x); break;
                case '-': acc = acc.subtract(x); break;
                case '*': acc = acc.multiply(x); break;
                case '/':
                    if (x.signum() == 0) throw new ArithmeticException("division by zero");
                    acc = acc.divide(x, MathContext.DECIMAL64);
                    break;
                default: acc = x;
            }
            show(acc);
        }

        void operation(char o) {
            if (error) return;
            if (!fresh || op == 0) apply();
            op = o;
            fresh = true;
            expression = format(acc) + " " + o;
        }

        void result() {
            if (error || op == 0) return;
            apply();
            op = 0;
            fresh = true;
            expression = "";
        }

        void clear() {
            display = "0";
            expression = "";
            acc = BigDecimal.ZERO;
            op = 0;
            fresh = true;
            error = false;
        }

        void unary(char what) {
            if (error) return;
            BigDecimal x = value();
            if (what == 'n') x = x.negate();
            else if (what == 's') {
                if (x.signum() < 0) throw new IllegalArgumentException("negative square root");
                x = new BigDecimal(Math.sqrt(x.doubleValue()));
                fresh = true;
            } else if (what == '%') {
                x = op != 0 ? acc.multiply(x).divide(BigDecimal.valueOf(100)) : x.divide(BigDecimal.valueOf(100));
            }
            show(x);
        }

        void back() {
            if (error || fresh) return;
            display = display.substring(0, display.length() - 1);
            if (display.isEmpty() || display.equals("-")) display = "0";
        }

        void memoryAdd() { if (!error) { memory = memory.add(value()); fresh = true; } }
        void memoryRecall() { if (!error) { show(memory); fresh = true; } }

        void fail(String why) {
            display = "Error: " + why;
            expression = "";
            error = true;
            op = 0;
            fresh = true;
        }
    }
}
