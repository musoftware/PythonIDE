/* Event handlers for Form1 - written for the GUI Bridge (radgui.h); the native build compiles the same
 * code against radforms. Handlers: void <Control>_<Event>(void). */
#include <stdio.h>
#include "radgui.h"

static int ticks = 0;

void Form1_Load(void)
{
    rad_set("lblOut", "Caption", "ready");
    rad_call("lstLog", "AddItem", "Form1 loaded");
}

void cmdAdd_Click(void)
{
    char args[100], line[200];
    double a = rad_get_num("txtA", "Text");
    double b = rad_get_num("txtB", "Text");
    rad_set("lblOut", "Caption", rad_str(a + b));
    snprintf(args, sizeof args, "[%s, %s]", rad_str(a), rad_str(b));
    /* Helpers.c is a module of this project: in the native exe radcall runs it in process */
    snprintf(line, sizeof line, "%s x %s = %s", rad_str(a), rad_str(b), radcall("Helpers.multiply", args));
    rad_call("lstLog", "AddItem", line);
}

void txtA_TextChanged(void)
{
    rad_set("lblEcho", "Caption", rad_get("txtA", "Text"));
}

void chkBig_CheckedChanged(void)
{
    int on = rad_get_num("chkBig", "Value") == 1;
    rad_set("lblOut", "FontSize", on ? "14" : "9");
    rad_set("lblOut", "Caption", on ? "big" : "small");
}

void optTwo_CheckedChanged(void)
{
    rad_set("lblEcho", "Caption", rad_get("optTwo", "Value"));
}

void cboColor_SelectedIndexChanged(void)
{
    rad_set("lblOut", "Caption", rad_get("cboColor", "Text"));
}

void tmrTick_Tick(void)
{
    ticks++;
    rad_set_num("lblTicks", "Caption", ticks);
    rad_set_num("prgTicks", "Value", ticks % 51);
}

void cmdShow2_Click(void)
{
    rad_show("Form2");
}

void mnuForm2_Click(void)
{
    rad_show("Form2");
}

void mnuAbout_Click(void)
{
    rad_msgbox("RAD IDE native C demo");
}

void mnuExit_Click(void)
{
    rad_end();
}

void cmdMsg_Click(void)
{
    rad_msgbox("Hello from radforms");
    rad_set("lblOut", "Caption", "msg done");
}

void cmdArabic_Click(void)
{
    rad_set("lblOut", "Caption", "مرحبا بالعالم");
}

void Form1_FormClosing(void)
{
    rad_print("Form1 closing");
}
