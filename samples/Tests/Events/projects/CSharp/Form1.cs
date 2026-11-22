// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)
using System;
using System.IO;

public static partial class Form1
{
    static int closing;

    static void EvLog(string name, string rest)
    {
        var p = Environment.GetEnvironmentVariable("RADEVT_LOG");
        if (string.IsNullOrEmpty(p)) return;
        File.AppendAllText(p, "EVT " + name + (string.IsNullOrEmpty(rest) ? "" : " " + rest) + "\n");
    }

    static string Raw(RadEvent e)
    {
        if (e == null) return "";
        if (!string.IsNullOrEmpty(e.Args)) return e.Args;
        return (e.X + " " + e.Y + " " + e.Button + " " + e.KeyCode + " " + e.KeyChar).Trim();
    }

    static void Form1_Load(RadEvent e)
    {
        EvLog("Form1_Load", "");
    }

    static void Form1_Activated(RadEvent e)
    {
        EvLog("Form1_Activated", "");
    }

    static void Form1_FormClosed(RadEvent e)
    {
        EvLog("Form1_FormClosed", "");
    }

    static void cmdA_MouseDown(RadEvent e)
    {
        EvLog("cmdA_MouseDown", Raw(e));
    }

    static void cmdA_MouseUp(RadEvent e)
    {
        EvLog("cmdA_MouseUp", Raw(e));
    }

    static void cmdA_Click(RadEvent e)
    {
        EvLog("cmdA_Click", "");
    }

    static void lblA_MouseDown(RadEvent e)
    {
        EvLog("lblA_MouseDown", Raw(e));
    }

    static void lblA_MouseUp(RadEvent e)
    {
        EvLog("lblA_MouseUp", Raw(e));
    }

    static void lblA_Click(RadEvent e)
    {
        EvLog("lblA_Click", "");
    }

    static void txtA_GotFocus(RadEvent e)
    {
        EvLog("txtA_GotFocus", "");
    }

    static void txtA_LostFocus(RadEvent e)
    {
        EvLog("txtA_LostFocus", "");
    }

    static void txtA_KeyDown(RadEvent e)
    {
        EvLog("txtA_KeyDown", Raw(e));
    }

    static void txtA_KeyPress(RadEvent e)
    {
        EvLog("txtA_KeyPress", Raw(e));
    }

    static void txtA_KeyUp(RadEvent e)
    {
        EvLog("txtA_KeyUp", Raw(e));
    }

    static void txtA_TextChanged(RadEvent e)
    {
        EvLog("txtA_TextChanged", "text=" + Rad.Get("txtA", "Text"));
    }

    static void txtB_GotFocus(RadEvent e)
    {
        EvLog("txtB_GotFocus", "");
    }

    static void txtB_LostFocus(RadEvent e)
    {
        EvLog("txtB_LostFocus", "");
    }

    static void chkA_CheckedChanged(RadEvent e)
    {
        EvLog("chkA_CheckedChanged", "value=" + Rad.Get("chkA", "Value"));
    }

    static void lstA_SelectedIndexChanged(RadEvent e)
    {
        EvLog("lstA_SelectedIndexChanged", "index=" + Rad.Get("lstA", "ListIndex"));
    }

    static void Form1_FormClosing(RadEvent e)
    {
        closing++;
        EvLog("Form1_FormClosing", "");
        if (closing == 1) e.Cancel = true;
    }

    static void cmdCode_Click(RadEvent e)
    {
        EvLog("cmdCode_Click", "begin");
        Rad.Set("txtA", "Text", "code");
        Rad.Set("chkA", "Value", 1);
        Rad.Set("lstA", "ListIndex", 2);
        EvLog("cmdCode_Click", "end");
    }

    static void cmdTmr_Click(RadEvent e)
    {
        EvLog("cmdTmr_Click", "");
        Rad.Set("tmrA", "Enabled", true);
    }

    static void tmrA_Tick(RadEvent e)
    {
        Rad.Set("tmrA", "Enabled", false);
        EvLog("tmrA_Tick", "");
    }
}
