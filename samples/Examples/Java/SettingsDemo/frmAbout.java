// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// frmAbout - the About box of Greeting Cards (shown with ShowDialog from frmMain).
public class frmAbout extends frmAboutDesigner {
    static void frmAbout_Load(RadEvent e) {
        lblAboutTitle.setCaption(AppSettings.arabic() ? "بطاقات التهنئة" : "Greeting Cards");
    }

    static void btnClose_Click(RadEvent e) { call("frmAbout", "Hide"); }
}
