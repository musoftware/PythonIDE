// Class library CppLib.
// Every non-static top-level function is public: projects that reference CppLib call it as
// code of their own language (Python: CppLib.Add(2, 3), C++: CppLib::Add(2, 3), ...).
// Supported types: int/long/double/float/bool, std::string, const char *, rad::Value.
#include <string>
#include "radgui.hpp"

// Add two numbers. Public (non-static, top-level) functions with number, bool or text
// (std::string / const char *) parameters can be called by projects that reference this one.
double Add(double a, double b)
{
    return a + b;
}
