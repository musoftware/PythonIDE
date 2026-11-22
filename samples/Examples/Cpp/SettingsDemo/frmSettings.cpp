// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// frmSettings - the modal settings dialog of Greeting Cards. frmMain fills it and calls ShowDialog;
// OK validates, stores the values in `settings`, writes settings.ini and updates frmMain; Cancel only hides.
#include <string>
#include "AppSettings.hpp"
#include "radgui.hpp"

void btnOK_Click()
{
    std::string user = rad::get("txtUser", "Text");
    if (user.empty()) {
        rad::msgbox("Please type your name.");
        rad::call("txtUser", "SetFocus");
        return;
    }
    settings.user = user;
    settings.language = rad::get_num("cboLang", "ListIndex") == 1 ? "العربية" : "English";
    settings.font_size = (int)rad::get_num("nudSize", "Value");
    settings.formal = rad::get_num("chkFormal", "Value") == 1;
    if (!settings.save()) rad::msgbox("Cannot write settings.ini");
    rad::call("frmSettings", "Hide");
    applySettings();
}

void btnCancel_Click() { rad::call("frmSettings", "Hide"); }
