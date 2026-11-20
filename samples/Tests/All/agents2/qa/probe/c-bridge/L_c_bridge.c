/* Class library L_c_bridge.
 * Every non-static function below is public: projects that reference L_c_bridge call it as
 * code of their own language (Python: L_c_bridge.Add(2, 3), C: L_c_bridge_Add_num(2, 3), ...).
 * Supported types: int/long/double/float/bool, const char * (text); static = private. */
#include "radgui.h"

/* Add two numbers. Public (non-static) functions with number, bool or text
 * (const char *) parameters can be called by every project that references this one. */
double Add(double a, double b)
{
    return a + b;
}
