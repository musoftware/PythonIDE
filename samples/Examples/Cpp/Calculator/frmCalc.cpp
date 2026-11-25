// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Calculator - a pocket calculator in C++ (RAD IDE GUI Bridge, radgui.hpp; Build > Publish = native exe).
//
// The arithmetic lives in a small class (Calculator) that knows nothing about the GUI; the event handlers
// only translate buttons / keys into its methods and show its state. Errors (division by zero, square
// root of a negative number, overflow) are C++ exceptions caught in one place.
// Shows: many buttons sharing code, keyboard input on the form (KeyPress with key names), exceptions,
// std::string formatting, a memory register.
#include <cmath>
#include <stdexcept>
#include <string>
#include "radgui.hpp"

namespace {

class Calculator {
public:
    std::string display = "0";
    std::string expression;            // "12 +" shown above the display
    double memory = 0;
    bool error = false;

    void digit(const std::string &d)
    {
        if (error) clear();
        if (fresh_) { display = d == "." ? "0" : ""; fresh_ = false; }
        if (d == "." && display.find('.') != std::string::npos) return;
        if (display.size() >= 16) return;
        if (display == "0" && d != ".") display.clear();
        display += d;
    }
    void operation(char op)
    {
        if (error) return;
        if (!fresh_ || !op_) apply();
        op_ = op;
        fresh_ = true;
        expression = rad::str(acc_) + " " + op;
    }
    void equals()
    {
        if (error || !op_) return;
        apply();
        op_ = 0;
        fresh_ = true;
        expression.clear();
    }
    void clear()
    {
        display = "0";
        expression.clear();
        acc_ = 0;
        op_ = 0;
        fresh_ = true;
        error = false;
    }
    void unary(char what)                   // n = negate, s = square root, % = percent
    {
        if (error) return;
        double x = value();
        if (what == 'n') x = -x;
        else if (what == 's') {
            if (x < 0) throw std::domain_error("negative square root");
            x = std::sqrt(x);
            fresh_ = true;
        } else if (what == '%') {
            x = op_ ? acc_ * x / 100 : x / 100;
        }
        show(x);
    }
    void back()
    {
        if (error || fresh_) return;
        display.pop_back();
        if (display.empty() || display == "-") display = "0";
    }
    void memory_add() { if (!error) { memory += value(); fresh_ = true; } }
    void memory_recall() { if (!error) { show(memory); fresh_ = true; } }
    void fail(const std::string &why)
    {
        display = "Error: " + why;
        expression.clear();
        error = true;
        op_ = 0;
        fresh_ = true;
    }

private:
    double acc_ = 0;
    char op_ = 0;
    bool fresh_ = true;

    double value() const { return rad::num(display); }
    void show(double x)
    {
        if (std::isnan(x) || std::isinf(x) || std::fabs(x) > 1e15) throw std::overflow_error("overflow");
        display = rad::str(x);
    }
    void apply()
    {
        double x = value();
        switch (op_) {
        case '+': acc_ += x; break;
        case '-': acc_ -= x; break;
        case '*': acc_ *= x; break;
        case '/':
            if (x == 0) throw std::domain_error("division by zero");
            acc_ /= x;
            break;
        default: acc_ = x;
        }
        show(acc_);
    }
};

Calculator calc;

void refresh()
{
    rad::set("lblDisplay", "Caption", calc.display);
    rad::set("lblExpr", "Caption", calc.expression);
    rad::set("lblMemory", "Caption", calc.memory != 0 ? "M" : "");
}

// run one action; every error of the calculator ends up here
template <class F>
void act(F f)
{
    try {
        f();
    } catch (const std::exception &e) {
        calc.fail(e.what());
    }
    refresh();
}

}  // namespace

void frmCalc_Load() { refresh(); }

void btn0_Click() { act([] { calc.digit("0"); }); }
void btn1_Click() { act([] { calc.digit("1"); }); }
void btn2_Click() { act([] { calc.digit("2"); }); }
void btn3_Click() { act([] { calc.digit("3"); }); }
void btn4_Click() { act([] { calc.digit("4"); }); }
void btn5_Click() { act([] { calc.digit("5"); }); }
void btn6_Click() { act([] { calc.digit("6"); }); }
void btn7_Click() { act([] { calc.digit("7"); }); }
void btn8_Click() { act([] { calc.digit("8"); }); }
void btn9_Click() { act([] { calc.digit("9"); }); }
void btnDot_Click() { act([] { calc.digit("."); }); }
void btnAdd_Click() { act([] { calc.operation('+'); }); }
void btnSub_Click() { act([] { calc.operation('-'); }); }
void btnMul_Click() { act([] { calc.operation('*'); }); }
void btnDiv_Click() { act([] { calc.operation('/'); }); }
void btnEquals_Click() { act([] { calc.equals(); }); }
void btnClear_Click() { act([] { calc.clear(); }); }
void btnSign_Click() { act([] { calc.unary('n'); }); }
void btnSqrt_Click() { act([] { calc.unary('s'); }); }
void btnPercent_Click() { act([] { calc.unary('%'); }); }
void btnBack_Click() { act([] { calc.back(); }); }
void btnMC_Click() { act([] { calc.memory = 0; }); }
void btnMR_Click() { act([] { calc.memory_recall(); }); }
void btnMPlus_Click() { act([] { calc.memory_add(); }); }

// KeyPress args: "X Y Button KeyCode KeyChar" - KeyCode is the Windows key code (13 Enter, 27 Esc, 8 Backspace)
void frmCalc_KeyPress()
{
    const std::string key = rad::arg(3), ch = rad::arg(4);
    act([&] {
        if (ch.size() == 1 && ch[0] >= '0' && ch[0] <= '9') calc.digit(ch);
        else if (ch == "." || ch == ",") calc.digit(".");
        else if (ch == "+" || ch == "-" || ch == "*" || ch == "/") calc.operation(ch[0]);
        else if (ch == "=" || key == "13" || key == "Return") calc.equals();
        else if (key == "27" || key == "Escape") calc.clear();
        else if (key == "8" || key == "BackSpace") calc.back();
    });
}
