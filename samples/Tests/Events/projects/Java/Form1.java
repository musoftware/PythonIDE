// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)
public class Form1 extends Form1Designer {
    static int closing;

    static void evlog(String name, String rest) {
        String p = System.getenv("RADEVT_LOG");
        if (p == null || p.isEmpty()) return;
        try (java.io.Writer w = new java.io.OutputStreamWriter(new java.io.FileOutputStream(p, true), java.nio.charset.StandardCharsets.UTF_8)) {
            w.write("EVT " + name + (rest == null || rest.isEmpty() ? "" : " " + rest) + "\n");
        } catch (java.io.IOException ex) {
        }
    }

    static String raw(RadEvent e) {
        if (e == null) return "";
        if (!e.args.isEmpty()) return e.args;
        return (e.x + " " + e.y + " " + e.button + " " + e.keyCode + " " + e.keyChar).trim();
    }

    static void Form1_Load(RadEvent e) {
        evlog("Form1_Load", "");
    }

    static void Form1_Activated(RadEvent e) {
        evlog("Form1_Activated", "");
    }

    static void Form1_FormClosed(RadEvent e) {
        evlog("Form1_FormClosed", "");
    }

    static void cmdA_MouseDown(RadEvent e) {
        evlog("cmdA_MouseDown", raw(e));
    }

    static void cmdA_MouseUp(RadEvent e) {
        evlog("cmdA_MouseUp", raw(e));
    }

    static void cmdA_Click(RadEvent e) {
        evlog("cmdA_Click", "");
    }

    static void lblA_MouseDown(RadEvent e) {
        evlog("lblA_MouseDown", raw(e));
    }

    static void lblA_MouseUp(RadEvent e) {
        evlog("lblA_MouseUp", raw(e));
    }

    static void lblA_Click(RadEvent e) {
        evlog("lblA_Click", "");
    }

    static void txtA_GotFocus(RadEvent e) {
        evlog("txtA_GotFocus", "");
    }

    static void txtA_LostFocus(RadEvent e) {
        evlog("txtA_LostFocus", "");
    }

    static void txtA_KeyDown(RadEvent e) {
        evlog("txtA_KeyDown", raw(e));
    }

    static void txtA_KeyPress(RadEvent e) {
        evlog("txtA_KeyPress", raw(e));
    }

    static void txtA_KeyUp(RadEvent e) {
        evlog("txtA_KeyUp", raw(e));
    }

    static void txtA_TextChanged(RadEvent e) {
        evlog("txtA_TextChanged", "text=" + Rad.get("txtA", "Text"));
    }

    static void txtB_GotFocus(RadEvent e) {
        evlog("txtB_GotFocus", "");
    }

    static void txtB_LostFocus(RadEvent e) {
        evlog("txtB_LostFocus", "");
    }

    static void chkA_CheckedChanged(RadEvent e) {
        evlog("chkA_CheckedChanged", "value=" + Rad.get("chkA", "Value"));
    }

    static void lstA_SelectedIndexChanged(RadEvent e) {
        evlog("lstA_SelectedIndexChanged", "index=" + Rad.get("lstA", "ListIndex"));
    }

    static void Form1_FormClosing(RadEvent e) {
        closing++;
        evlog("Form1_FormClosing", "");
        if (closing == 1) e.cancel = true;
    }

    static void cmdCode_Click(RadEvent e) {
        evlog("cmdCode_Click", "begin");
        Rad.set("txtA", "Text", "code");
        Rad.set("chkA", "Value", 1);
        Rad.set("lstA", "ListIndex", 2);
        evlog("cmdCode_Click", "end");
    }

    static void cmdTmr_Click(RadEvent e) {
        evlog("cmdTmr_Click", "");
        Rad.set("tmrA", "Enabled", true);
    }

    static void tmrA_Tick(RadEvent e) {
        Rad.set("tmrA", "Enabled", false);
        evlog("tmrA_Tick", "");
    }
}
