/* Class library CLib.
 * Every non-static function below is public: projects that reference CLib call it as
 * code of their own language (Python: CLib.Add(2, 3), C: CLib_Add_num(2, 3), ...).
 * Supported types: int/long/double/float/bool, const char * (text); static = private. */
#include "radgui.h"

/* Add two numbers. Public (non-static) functions with number, bool or text
 * (const char *) parameters can be called by every project that references this one. */
double Add(double a, double b)
{
    return a + b;
}
