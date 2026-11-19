#include <string>
#include "radgui.hpp"
#include "PyLib.ref.hpp"
std::string Test()
{
    double a = PyLib::Add(2, 3);
    return std::to_string((int)a) + "|" + PyLib::Greet("Cpp").str();
}
