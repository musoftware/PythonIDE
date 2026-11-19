// Event handlers for Form1. A handler is a static method named <Control>_<Event>
// (optionally taking RadEvent e: e.X, e.Y, e.Button, e.KeyCode, e.KeyChar).
// Controls are fields generated in Form1_designer.cs:  lblOut.Text = "Hi";  lstLog.AddItem("x");
// Helpers: MsgBox(text), InputBox(prompt), Set/Get/Call(obj, ...), Show("Form2"), End(),
//          radcall("Module.function", args...) - call a function of a project module.
public static partial class Form1
{
    static int count;

    static void Form1_Load(RadEvent e)
    {
        lblGreeting.Text = "Type a name and press Greet.";
    }

    static void btnGreet_Click(RadEvent e)
    {
        var text = Greeter.Make(txtName.Text, chkShout.Value == "1");
        lblGreeting.Text = text;
        lstHistory.AddItem($"{DateTime.Now:HH:mm:ss}  {text}");
        count++;
        lblCount.Text = $"{count} greeting{(count == 1 ? "" : "s")}";
    }

    static void lstHistory_DoubleClick(RadEvent e)
    {
        if (lstHistory.ListIndex >= 0)
            MsgBox(lstHistory.List(lstHistory.ListIndex));
    }

    static void mnuFileClear_Click(RadEvent e)
    {
        lstHistory.Clear();
        count = 0;
        lblCount.Text = "0 greetings";
        lblGreeting.Text = "";
    }

    static void mnuFileExit_Click(RadEvent e)
    {
        End();
    }

    static void mnuHelpAbout_Click(RadEvent e)
    {
        MsgBox($"HelloCSharp - a RAD IDE sample running on .NET {Environment.Version}");
    }
}
