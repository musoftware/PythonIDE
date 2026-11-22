// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Greeting Cards - a multi-form C++ program (RAD IDE GUI Bridge, radgui.hpp; Build > Publish = native exe).
//
// frmMain makes greeting cards; frmSettings is a modal dialog (ShowDialog) for the user name, the language
// (English / Arabic), the font size and a formal style; frmAbout is a small About box. The settings are
// kept in settings.ini (AppSettings.cpp, a code module) and the Arabic texts are right-aligned.
// Shows: several forms, ShowDialog / Hide, "Form.Control" names, a menu, a module + header shared by the
// forms, a settings file, Unicode (Arabic) text in labels, combo boxes and a multi-line text box.
#include <string>
#include "AppSettings.hpp"
#include "radgui.hpp"

namespace {

struct Texts {                      // the strings of one language
    const char *hello, *formal_hello, *message, *occasion, *make, *settings, *about, *ready;
};

const Texts kEnglish = {"Hello, ", "Good day, ", "Choose an occasion and press Make card.", "Occasion:",
                        "Make card", "Settings...", "About...", "Ready"};
const Texts kArabic = {"مرحبا يا ", "أسعد الله أوقاتك يا ", "اختر مناسبة ثم اضغط اصنع بطاقة.", "المناسبة:",
                       "اصنع بطاقة", "الإعدادات...", "حول...", "جاهز"};

const Texts &texts() { return settings.arabic() ? kArabic : kEnglish; }

// the card text for occasion index i (0 Birthday, 1 New Year, 2 Eid, 3 Success)
std::string cardText(int i)
{
    static const char *en[] = {"Happy birthday! Many happy returns of the day.",
                               "Happy New Year! May the year bring you joy and health.",
                               "Eid Mubarak! Wishing you and your family a blessed Eid.",
                               "Congratulations on your success - well done!"};
    static const char *ar[] = {"عيد ميلاد سعيد! كل عام وأنت بخير.", "سنة جديدة سعيدة! أتمنى لك عاماً مليئاً بالفرح والصحة.",
                               "عيد مبارك! كل عام وأنتم بخير.", "مبروك النجاح - أحسنت!"};
    if (i < 0 || i > 3) i = 0;
    const Texts &t = texts();
    std::string greeting = (settings.formal ? t.formal_hello : t.hello) + settings.user;
    return greeting + "\r\n\r\n" + (settings.arabic() ? ar[i] : en[i]) + "\r\n\r\n" +
           (settings.arabic() ? "مع أطيب التمنيات" : "Best wishes");
}

}  // namespace

// show the settings on the main form (also called by frmSettings after OK)
void applySettings()
{
    const Texts &t = texts();
    const char *align = settings.arabic() ? "Right" : "Left";
    rad::set("frmMain.lblTitle", "Caption", (settings.formal ? t.formal_hello : t.hello) + settings.user + "!");
    rad::set("frmMain.lblMessage", "Caption", t.message);
    rad::set("frmMain.lblOccasion", "Caption", t.occasion);
    rad::set("frmMain.btnMake", "Caption", t.make);
    rad::set("frmMain.btnSettings", "Caption", t.settings);
    rad::set("frmMain.btnAbout", "Caption", t.about);
    for (const char *name : {"frmMain.lblTitle", "frmMain.lblMessage"}) rad::set(name, "TextAlign", align);
    rad::set("frmMain.txtCard", "FontSize", settings.font_size);
    rad::set("frmMain.sbStatus", "Text", t.ready);
    rad::set("frmMain", "Caption", settings.arabic() ? "بطاقات التهنئة" : "Greeting Cards");
}

void frmMain_Load()
{
    settings.load();
    rad::set("cboOccasion", "ListIndex", 0);
    applySettings();
}

void btnMake_Click()
{
    int i = (int)rad::get_num("cboOccasion", "ListIndex");
    rad::set("txtCard", "Text", cardText(i));
    rad::set("sbStatus", "Text", settings.arabic() ? "تم إنشاء البطاقة" : "Card ready");
}

void btnSettings_Click()
{
    // fill the dialog, then show it modally; its OK / Cancel handlers (frmSettings.cpp) finish the job
    rad::set("frmSettings.txtUser", "Text", settings.user);
    rad::set("frmSettings.cboLang", "ListIndex", settings.arabic() ? 1 : 0);
    rad::set("frmSettings.nudSize", "Value", settings.font_size);
    rad::set("frmSettings.chkFormal", "Value", settings.formal ? 1 : 0);
    rad::call("frmSettings", "ShowDialog");
}

void mnuSettings_Click() { btnSettings_Click(); }

void btnAbout_Click() { rad::call("frmAbout", "ShowDialog"); }
void mnuAbout_Click() { btnAbout_Click(); }
void mnuExit_Click() { rad::end(); }
