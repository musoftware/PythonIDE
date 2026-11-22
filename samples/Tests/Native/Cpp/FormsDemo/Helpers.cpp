// Module Helpers: RADFUNC functions can be called with rad::hub("Helpers.multiply", "[2, 3]").
#include "radgui.hpp"

RADFUNC(multiply)
{
    if (argc < 2) return rad_fail("multiply needs 2 arguments");
    return rad_json_numtext(rad::json_num(argv[0]) * rad::json_num(argv[1]));
}
