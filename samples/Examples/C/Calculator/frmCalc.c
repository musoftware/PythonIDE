/* (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * Calculator - a pocket calculator in C (RAD IDE GUI Bridge, radgui.h; Build > Publish makes a native exe).
 *
 * Shows: many buttons that share one function, keyboard input (the form gets the keys of its controls:
 * digits, + - * / . Enter = Escape = C, BackSpace), error handling (division by zero, square root of
 * a negative number, overflow), a memory register (MC / MR / M+), number <-> text with rad_num / rad_str.
 */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "radgui.h"

static char display[64] = "0";   /* what the user is typing / the last result */
static double acc = 0;           /* left operand */
static char op = 0;              /* pending operator: + - * / or 0 */
static int fresh = 1;            /* the next digit starts a new number */
static double memory = 0;
static int error = 0;

static void show(void)
{
    char expr[128] = "";
    rad_set("lblDisplay", "Caption", display);
    if (op) snprintf(expr, sizeof expr, "%s %c", rad_str(acc), op);
    rad_set("lblExpr", "Caption", expr);
    rad_set("lblMemory", "Caption", memory != 0 ? "M" : "");
}

static void fail(const char *why)
{
    snprintf(display, sizeof display, "Error: %s", why);
    error = 1;
    op = 0;
    fresh = 1;
    show();
}

static void set_number(double x)
{
    if (isnan(x) || isinf(x) || fabs(x) > 1e15) { fail("overflow"); return; }
    snprintf(display, sizeof display, "%s", rad_str(x));
}

/* apply the pending operator to acc and the display; 0 = error */
static int apply(void)
{
    double x = rad_num(display);
    switch (op) {
    case '+': acc += x; break;
    case '-': acc -= x; break;
    case '*': acc *= x; break;
    case '/':
        if (x == 0) { fail("division by zero"); return 0; }
        acc /= x;
        break;
    default: acc = x; break;
    }
    set_number(acc);
    return !error;
}

static void digit(const char *d)
{
    if (error) { error = 0; strcpy(display, "0"); }
    if (fresh) { strcpy(display, strcmp(d, ".") == 0 ? "0" : ""); fresh = 0; }
    if (strcmp(d, ".") == 0 && strchr(display, '.')) return;      /* one decimal point */
    if (strlen(display) >= 16) return;
    if (strcmp(display, "0") == 0 && strcmp(d, ".") != 0) display[0] = 0;
    strcat(display, d);
    show();
}

static void operation(char o)
{
    if (error) return;
    if (!fresh || !op) {
        if (!apply()) return;
    }
    op = o;
    fresh = 1;
    show();
}

static void equals(void)
{
    if (error || !op) return;
    if (apply()) {
        op = 0;
        fresh = 1;
        show();
    }
}

static void clear_all(void)
{
    strcpy(display, "0");
    acc = 0;
    op = 0;
    fresh = 1;
    error = 0;
    show();
}

/* ------------------------------------------------------------------ buttons */
void frmCalc_Load(void) { show(); }

void btn0_Click(void) { digit("0"); }
void btn1_Click(void) { digit("1"); }
void btn2_Click(void) { digit("2"); }
void btn3_Click(void) { digit("3"); }
void btn4_Click(void) { digit("4"); }
void btn5_Click(void) { digit("5"); }
void btn6_Click(void) { digit("6"); }
void btn7_Click(void) { digit("7"); }
void btn8_Click(void) { digit("8"); }
void btn9_Click(void) { digit("9"); }
void btnDot_Click(void) { digit("."); }
void btnAdd_Click(void) { operation('+'); }
void btnSub_Click(void) { operation('-'); }
void btnMul_Click(void) { operation('*'); }
void btnDiv_Click(void) { operation('/'); }
void btnEquals_Click(void) { equals(); }
void btnClear_Click(void) { clear_all(); }

void btnSign_Click(void)
{
    if (error) return;
    set_number(-rad_num(display));
    show();
}

void btnSqrt_Click(void)
{
    double x = rad_num(display);
    if (error) return;
    if (x < 0) { fail("negative square root"); return; }
    set_number(sqrt(x));
    fresh = 1;
    show();
}

void btnPercent_Click(void)
{
    if (error) return;
    /* 200 + 10 % = 220 (10 % of the left operand), otherwise x / 100 */
    set_number(op ? acc * rad_num(display) / 100 : rad_num(display) / 100);
    show();
}

void btnBack_Click(void)
{
    size_t n = strlen(display);
    if (error || fresh) return;
    if (n <= 1 || (n == 2 && display[0] == '-')) strcpy(display, "0");
    else display[n - 1] = 0;
    show();
}

void btnMC_Click(void) { memory = 0; show(); }
void btnMR_Click(void) { if (!error) { set_number(memory); fresh = 1; show(); } }
void btnMPlus_Click(void) { if (!error) { memory += rad_num(display); fresh = 1; show(); } }

/* ------------------------------------------------------------------ keyboard
 * KeyPress args: "X Y Button KeyCode KeyChar"; KeyCode is the key name (Return, Escape, BackSpace, 7 ...) */
void frmCalc_KeyPress(void)
{
    const char *key = rad_arg(3), *ch = rad_arg(4);
    if (*ch && strchr("0123456789", ch[0]) && !ch[1]) digit(ch);
    else if (strcmp(ch, ".") == 0 || strcmp(ch, ",") == 0) digit(".");
    else if (strcmp(ch, "+") == 0) operation('+');
    else if (strcmp(ch, "-") == 0) operation('-');
    else if (strcmp(ch, "*") == 0) operation('*');
    else if (strcmp(ch, "/") == 0) operation('/');
    else if (strcmp(ch, "=") == 0 || strcmp(key, "Return") == 0) equals();
    else if (strcmp(key, "Escape") == 0) clear_all();
    else if (strcmp(key, "BackSpace") == 0) btnBack_Click();
}
