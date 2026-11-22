// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// frmAbout - the About box of Greeting Cards (shown with ShowDialog from frmMain).
public static partial class frmAbout
{
    static void frmAbout_Load(RadEvent e) =>
        lblAboutTitle.Caption = AppSettings.Arabic ? "بطاقات التهنئة" : "Greeting Cards";

    static void btnClose_Click(RadEvent e) => Me.Call("Hide");
}
