// Event handlers for Form1 - GUI Bridge C++ API (radgui.hpp); the native build links radforms instead.
#include <string>
#include <vector>
#include "radgui.hpp"

static int ticks = 0;
static std::vector<std::string> history;

void Form1_Load()
{
    rad::set("lblOut", "Caption", "ready");
    rad::call("lstLog", "AddItem", "Form1 loaded");
}

void cmdAdd_Click()
{
    double a = rad::get_num("txtA", "Text");
    double b = rad::get_num("txtB", "Text");
    rad::set("lblOut", "Caption", rad::str(a + b));
    std::string line = rad::str(a) + " x " + rad::str(b) + " = " +
                       rad::hub("Helpers.multiply", "[" + rad::str(a) + ", " + rad::str(b) + "]");
    history.push_back(line);
    rad::call("lstLog", "AddItem", line);
}

void txtA_TextChanged()
{
    rad::set("lblEcho", "Caption", rad::get("txtA", "Text"));
}

void chkBig_CheckedChanged()
{
    bool on = rad::get_num("chkBig", "Value") == 1;
    rad::set("lblOut", "FontSize", on ? 14 : 9);
    rad::set("lblOut", "Caption", on ? "big" : "small");
}

void cboColor_SelectedIndexChanged()
{
    rad::set("lblOut", "Caption", rad::get("cboColor", "Text"));
}

void tmrTick_Tick()
{
    ticks++;
    rad::set("lblTicks", "Caption", ticks);
    rad::set("prgTicks", "Value", ticks % 51);
}

void cmdShow2_Click() { rad::show("Form2"); }
void mnuForm2_Click() { rad::show("Form2"); }
void mnuAbout_Click() { rad::msgbox("RAD IDE native C++ demo"); }
void mnuExit_Click() { rad::end(); }

void cmdMsg_Click()
{
    rad::msgbox("Hello from radforms");
    rad::set("lblOut", "Caption", "msg done");
}

void cmdArabic_Click()
{
    rad::set("lblOut", "Caption", std::string("مرحبا بالعالم"));
}
