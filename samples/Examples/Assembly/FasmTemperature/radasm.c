/* RAD IDE GUI Bridge - integer helpers for assembly programs (copied into the project when it runs).
 * Assembly code works with integers more than with doubles: these wrap the C client (radgui.c).
 *   rad_set_int("Label1", "Text", 42)    long long rad_get_int("Text1", "Text")
 *   const char *rad_str_int(42)          long long rad_int_str("42")
 */
#include <stdio.h>
#include <stdlib.h>
#include "radgui.h"

static char rad_int_ring[8][32];
static int rad_int_next = 0;

const char *rad_str_int(long long value)
{
    char *buf = rad_int_ring[rad_int_next];
    rad_int_next = (rad_int_next + 1) % 8;
    snprintf(buf, sizeof rad_int_ring[0], "%lld", value);
    return buf;
}

long long rad_int_str(const char *text)
{
    if (text == NULL)
        return 0;
    return strtoll(text, NULL, 10);
}

void rad_set_int(const char *obj, const char *prop, long long value)
{
    rad_set(obj, prop, rad_str_int(value));
}

long long rad_get_int(const char *obj, const char *prop)
{
    return rad_int_str(rad_get(obj, prop));
}
