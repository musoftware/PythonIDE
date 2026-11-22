// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Greeting Cards - a multi-form Java program (RAD IDE GUI Bridge; Build > Publish = native Swing exe).
//
// frmMain makes greeting cards, frmSettings is a modal dialog (ShowDialog) for the user name, the language
// (English / Arabic), the font size and a formal style, frmAbout is the About box. AppSettings.java (a module)
// keeps the settings in settings.properties. Arabic text is right-aligned.
// Shows: several forms, ShowDialog / Hide, "Form.Control" names, a menu, a shared module, a settings file,
// Unicode (Arabic) text in labels, combo boxes and a multi-line text box.
public class frmMain extends frmMainDesigner {
    static final String[] OCCASIONS_EN = {
        "Happy birthday! Many happy returns of the day.",
        "Happy New Year! May the year bring you joy and health.",
        "Eid Mubarak! Wishing you and your family a blessed Eid.",
        "Congratulations on your success - well done!",
    };
    static final String[] OCCASIONS_AR = {
        "عيد ميلاد سعيد! كل عام وأنت بخير.",
        "سنة جديدة سعيدة! أتمنى لك عاماً مليئاً بالفرح والصحة.",
        "عيد مبارك! كل عام وأنتم بخير.",
        "مبروك النجاح - أحسنت!",
    };

    static String t(String en, String ar) { return AppSettings.arabic() ? ar : en; }

    static String greeting() {
        return (AppSettings.formal ? t("Good day, ", "أسعد الله أوقاتك يا ") : t("Hello, ", "مرحبا يا ")) + AppSettings.user;
    }

    /** Show the settings on the main form (frmSettings calls it after OK). */
    static void applySettings() {
        String align = AppSettings.arabic() ? "Right" : "Left";
        set("frmMain", "Caption", t("Greeting Cards", "بطاقات التهنئة"));
        set("frmMain.lblTitle", "Caption", greeting() + "!");
        set("frmMain.lblMessage", "Caption", t("Choose an occasion and press Make card.", "اختر مناسبة ثم اضغط اصنع بطاقة."));
        set("frmMain.lblOccasion", "Caption", t("Occasion:", "المناسبة:"));
        set("frmMain.btnMake", "Caption", t("Make card", "اصنع بطاقة"));
        set("frmMain.btnSettings", "Caption", t("Settings...", "الإعدادات..."));
        set("frmMain.btnAbout", "Caption", t("About...", "حول..."));
        set("frmMain.lblTitle", "TextAlign", align);
        set("frmMain.lblMessage", "TextAlign", align);
        set("frmMain.txtCard", "FontSize", AppSettings.fontSize);
        set("frmMain.sbStatus", "Text", t("Ready", "جاهز"));
    }

    static void frmMain_Load(RadEvent e) {
        AppSettings.load();
        cboOccasion.setListIndex(0);
        applySettings();
    }

    static void btnMake_Click(RadEvent e) {
        int i = Math.max(0, Math.min(3, cboOccasion.getListIndex()));
        txtCard.setText(greeting() + "\r\n\r\n" + (AppSettings.arabic() ? OCCASIONS_AR[i] : OCCASIONS_EN[i])
                        + "\r\n\r\n" + t("Best wishes", "مع أطيب التمنيات"));
        sbStatus.setText(t("Card ready", "تم إنشاء البطاقة"));
    }

    static void btnSettings_Click(RadEvent e) {
        // fill the dialog, then show it modally; its OK / Cancel handlers (frmSettings.java) finish the job
        set("frmSettings.txtUser", "Text", AppSettings.user);
        set("frmSettings.cboLang", "ListIndex", AppSettings.arabic() ? 1 : 0);
        set("frmSettings.nudSize", "Value", AppSettings.fontSize);
        set("frmSettings.chkFormal", "Value", AppSettings.formal ? 1 : 0);
        call("frmSettings", "ShowDialog");
    }

    static void mnuSettings_Click(RadEvent e) { btnSettings_Click(e); }
    static void btnAbout_Click(RadEvent e) { call("frmAbout", "ShowDialog"); }
    static void mnuAbout_Click(RadEvent e) { btnAbout_Click(e); }
    static void mnuExit_Click(RadEvent e) { end(); }
}
