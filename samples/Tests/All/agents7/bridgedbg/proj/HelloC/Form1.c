/* Event handlers for Form1. The IDE draws the form; rad_set / rad_get / rad_call
 * work with the controls (see radgui.h). Handlers: void <Control>_<Event>(void). */
#include <stdio.h>
#include "radgui.h"

static int clicks = 0;

void Form1_Load(void)
{
    rad_set("lblOut", "Caption", "Hello from C!");
    rad_call("lstLog", "AddItem", "Form1 loaded");
}

void cmdAdd_Click(void)
{
    char line[200];
    double a = rad_get_num("txtA", "Text");
    double b = rad_get_num("txtB", "Text");
    clicks++;
    rad_set("lblOut", "Caption", rad_str(a + b));
    snprintf(line, sizeof line, "#%d: %s + %s = %s", clicks, rad_str(a), rad_str(b), rad_str(a + b));
    rad_call("lstLog", "AddItem", line);
}

void cmdHub_Click(void)
{
    /* cross-language call through RAD Hub: Helpers.c runs as a worker */
    char args[200];
    const char *r;
    snprintf(args, sizeof args, "[%s, %s]", rad_str(rad_get_num("txtA", "Text")), rad_str(rad_get_num("txtB", "Text")));
    r = radcall("Helpers.multiply", args);
    if (*r) rad_set("lblOut", "Caption", r);
    else rad_msgbox(rad_error());
}

void txtA_TextChanged(void)
{
    rad_set("lblOut", "Caption", rad_get("txtA", "Text"));
}
