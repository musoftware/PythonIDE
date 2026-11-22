// Event handlers for Form2.
#include "radgui.hpp"

void Form2_Load()
{
    rad::set("txt2", "Text", "from Form2 Load");
}

void cmdClose2_Click()
{
    rad::set("Form1.lblOut", "Caption", rad::get("txt2", "Text"));
    rad::hide("Form2");
}
