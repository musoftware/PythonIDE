/* Event handlers for Form2. */
#include "radgui.h"

void Form2_Load(void)
{
    rad_set("txt2", "Text", "from Form2 Load");
}

void cmdClose2_Click(void)
{
    rad_set("Form1.lblOut", "Caption", rad_get("txt2", "Text"));
    rad_hide("Form2");
}
