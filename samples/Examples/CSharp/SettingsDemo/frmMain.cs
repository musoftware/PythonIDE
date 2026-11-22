// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Greeting Cards - a multi-form C# program (RAD IDE GUI Bridge; Build > Publish = native WinForms exe).
//
// frmMain makes greeting cards, frmSettings is a modal dialog (ShowDialog) for the user name, the language
// (English / Arabic), the font size and a formal style, frmAbout is the About box. AppSettings.cs (a module)
// keeps the settings in settings.ini. Arabic text is right-aligned.
// Shows: several forms, ShowDialog / Hide, controls of another form (frmSettings.txtUser), a menu, a shared
// module, a settings file, Unicode (Arabic) text in labels, combo boxes and a multi-line text box.
using System;

public static partial class frmMain
{
    static readonly string[] OccasionsEn =
    {
        "Happy birthday! Many happy returns of the day.",
        "Happy New Year! May the year bring you joy and health.",
        "Eid Mubarak! Wishing you and your family a blessed Eid.",
        "Congratulations on your success - well done!",
    };
    static readonly string[] OccasionsAr =
    {
        "عيد ميلاد سعيد! كل عام وأنت بخير.",
        "سنة جديدة سعيدة! أتمنى لك عاماً مليئاً بالفرح والصحة.",
        "عيد مبارك! كل عام وأنتم بخير.",
        "مبروك النجاح - أحسنت!",
    };

    static string T(string en, string ar) => AppSettings.Arabic ? ar : en;

    static string Greeting() => (AppSettings.Formal ? T("Good day, ", "أسعد الله أوقاتك يا ") : T("Hello, ", "مرحبا يا "))
                                + AppSettings.User;

    /// <summary>Show the settings on the main form (frmSettings calls it after OK).</summary>
    public static void ApplySettings()
    {
        string align = AppSettings.Arabic ? "Right" : "Left";
        Me.Caption = T("Greeting Cards", "بطاقات التهنئة");
        lblTitle.Caption = Greeting() + "!";
        lblMessage.Caption = T("Choose an occasion and press Make card.", "اختر مناسبة ثم اضغط اصنع بطاقة.");
        lblOccasion.Caption = T("Occasion:", "المناسبة:");
        btnMake.Caption = T("Make card", "اصنع بطاقة");
        btnSettings.Caption = T("Settings...", "الإعدادات...");
        btnAbout.Caption = T("About...", "حول...");
        lblTitle["TextAlign"] = align;
        lblMessage["TextAlign"] = align;
        txtCard["FontSize"] = AppSettings.FontSize.ToString();
        sbStatus.Text = T("Ready", "جاهز");
    }

    static void frmMain_Load(RadEvent e)
    {
        AppSettings.Load();
        cboOccasion.ListIndex = 0;
        ApplySettings();
    }

    static void btnMake_Click(RadEvent e)
    {
        int i = Math.Max(0, Math.Min(3, cboOccasion.ListIndex));
        txtCard.Text = Greeting() + "\r\n\r\n" + (AppSettings.Arabic ? OccasionsAr[i] : OccasionsEn[i]) +
                       "\r\n\r\n" + T("Best wishes", "مع أطيب التمنيات");
        sbStatus.Text = T("Card ready", "تم إنشاء البطاقة");
    }

    static void btnSettings_Click(RadEvent e)
    {
        // fill the dialog, then show it modally; its OK / Cancel handlers (frmSettings.cs) finish the job
        frmSettings.txtUser.Text = AppSettings.User;
        frmSettings.cboLang.ListIndex = AppSettings.Arabic ? 1 : 0;
        frmSettings.nudSize.Value = AppSettings.FontSize.ToString();
        frmSettings.chkFormal.Value = AppSettings.Formal ? "1" : "0";
        frmSettings.Me.ShowDialog();
    }

    static void mnuSettings_Click(RadEvent e) => btnSettings_Click(e);
    static void btnAbout_Click(RadEvent e) => frmAbout.Me.ShowDialog();
    static void mnuAbout_Click(RadEvent e) => btnAbout_Click(e);
    static void mnuExit_Click(RadEvent e) => End();
}
