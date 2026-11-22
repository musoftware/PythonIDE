// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// frmSettings - the modal settings dialog of Greeting Cards. frmMain fills it and calls ShowDialog;
// OK validates, stores the values in AppSettings, writes settings.properties and updates frmMain.
public class frmSettings extends frmSettingsDesigner {
    static void btnOK_Click(RadEvent e) {
        String user = txtUser.getText().trim();
        if (user.isEmpty()) {
            msgbox("Please type your name.");
            txtUser.setFocus();
            return;
        }
        AppSettings.user = user;
        AppSettings.language = cboLang.getListIndex() == 1 ? "العربية" : "English";
        AppSettings.fontSize = toInt(nudSize.getValue());
        AppSettings.formal = chkFormal.getValue().equals("1");
        if (!AppSettings.save()) msgbox("Cannot write settings.properties");
        call("frmSettings", "Hide");
        frmMain.applySettings();
    }

    static void btnCancel_Click(RadEvent e) { call("frmSettings", "Hide"); }
}
