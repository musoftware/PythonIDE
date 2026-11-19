#include "radgui.h"
#include "PyLib.ref.h"
#include <stdio.h>
const char *Test(void)
{
    static char buf[256];
    snprintf(buf, sizeof buf, "%g|%s", PyLib_Add_num(2, 3), PyLib_Greet_str("C"));
    return buf;
}
