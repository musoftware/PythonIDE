/* Math library in C */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include "radgui.h"

static char buf[256];

static int helper(int x) { return x * 2; }

/* Add two numbers */
double Add(double a, double b)
{
    return a + b;
}

// Say hello to someone
const char *Greet(const char *who)
{
    snprintf(buf, sizeof buf, "Hello, %s!", who);
    return buf;
}

int Twice(int n) { return helper(n); }

bool IsEven(long n) { return n % 2 == 0; }

void Log(const char *msg) { fprintf(stderr, "log: %s\n", msg); }

struct point { int x, y; };
struct point Origin(void) { struct point p = {0, 0}; return p; }

RADFUNC(Sum3)
{
    return rad_json_numtext(rad_json_num(argv[0]) + rad_json_num(argv[1]) + rad_json_num(argv[2]));
}

void cmdGo_Click(void) { }
