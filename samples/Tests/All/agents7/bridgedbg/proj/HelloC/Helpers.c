/* Module Helpers.
 * Functions written as RADFUNC(name) can be called from every language through RAD Hub:
 *     Python: radcall("Helpers.multiply", 2, 3)      C: radcall("Helpers.multiply", "[2, 3]")
 * argv[i] is the JSON text of argument i; return JSON text (rad_json_numtext,
 * rad_json_quote) or rad_fail("message"). */
#include <stdio.h>
#include "radgui.h"

RADFUNC(multiply)
{
    if (argc < 2) return rad_fail("multiply needs 2 arguments");
    return rad_json_numtext(rad_json_num(argv[0]) * rad_json_num(argv[1]));
}

RADFUNC(greet)
{
    char buf[512];
    snprintf(buf, sizeof buf, "Hello, %s!", argc > 0 ? rad_json_str(argv[0]) : "world");
    return rad_json_quote(buf);
}
