// Event handlers for Form1 (debugger test)
#include <string>
#include "radgui.hpp"

void Form1_Load()
{
}

void cmdAdd_Click()
{
    double a = rad::get_num("txtA", "Text");
    double b = rad::get_num("txtB", "Text");
    int total = (int)(a + b);
    rad::set("lblOut", "Caption", std::to_string(total));
}
