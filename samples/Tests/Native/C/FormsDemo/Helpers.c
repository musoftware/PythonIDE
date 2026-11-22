/* Module Helpers: RADFUNC functions can be called with radcall("Helpers.multiply", "[2, 3]"). */
#include "radgui.h"

RADFUNC(multiply)
{
    if (argc < 2) return rad_fail("multiply needs 2 arguments");
    return rad_json_numtext(rad_json_num(argv[0]) * rad_json_num(argv[1]));
}
