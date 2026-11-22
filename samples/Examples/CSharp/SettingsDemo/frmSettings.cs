// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// frmSettings - the modal settings dialog of Greeting Cards. frmMain fills it and calls ShowDialog;
// OK validates, stores the values in AppSettings, writes settings.ini and updates frmMain; Cancel only hides.
public static partial class frmSettings
{
    static void btnOK_Click(RadEvent e)
    {
        string user = txtUser.Text.Trim();
        if (user == "")
        {
            MsgBox("Please type your name.");
            txtUser.SetFocus();
            return;
        }
        AppSettings.User = user;
        AppSettings.Language = cboLang.ListIndex == 1 ? "العربية" : "English";
        AppSettings.FontSize = Rad.ToInt(nudSize.Value);
        AppSettings.Formal = chkFormal.Value == "1";
        if (!AppSettings.Save()) MsgBox("Cannot write settings.ini");
        Me.Call("Hide");
        frmMain.ApplySettings();
    }

    static void btnCancel_Click(RadEvent e) => Me.Call("Hide");
}
