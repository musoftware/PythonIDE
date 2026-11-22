// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// frmAbout - the About box of Greeting Cards (shown with ShowDialog from frmMain).
#include "AppSettings.hpp"
#include "radgui.hpp"

void frmAbout_Load()
{
    rad::set("lblAboutTitle", "Caption", settings.arabic() ? "بطاقات التهنئة" : "Greeting Cards");
}

void btnClose_Click() { rad::call("frmAbout", "Hide"); }
