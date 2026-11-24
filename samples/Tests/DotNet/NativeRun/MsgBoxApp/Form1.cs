// Native mode test program (samples/Tests/DotNet/NativeRun/test_native_run.py): Windows Forms types are usable
// directly (implicit usings of a WinForms project) next to the RAD helpers (MsgBox, RadControl fields, End).
// With RAD_TEST_EXIT=1 the form reports what it is and closes itself; otherwise it is a normal little program.
public static partial class Form1
{
    static void Form1_Load(RadEvent e)
    {
        lblGreeting.Text = "Type a name and press Greet.";
        if (Environment.GetEnvironmentVariable("RAD_TEST_EXIT") == "1")
        {
            var f = Application.OpenForms.Count > 0 ? Application.OpenForms[0] : null;
            Console.WriteLine($"NATIVE-OK form={f?.GetType().BaseType?.Name} button={typeof(Button).Name} " +
                              $"color={Color.Red.Name} greet={Greeter.Make("Ada", false)}");
            var t = new System.Windows.Forms.Timer { Interval = 300 };
            t.Tick += (s, a) => { t.Stop(); End(); };
            t.Start();
        }
    }

    static void btnGreet_Click(RadEvent e)
    {
        MessageBox.Show(Greeter.Make(txtName.Text, chkShout.Value == "1"), "MsgBoxApp");
    }

    static void lstHistory_DoubleClick(RadEvent e) => MsgBox(lstHistory.Text);
    static void mnuFileClear_Click(RadEvent e) => lstHistory.Clear();
    static void mnuFileExit_Click(RadEvent e) => End();
    static void mnuHelpAbout_Click(RadEvent e) => MsgBox($"MsgBoxApp on .NET {Environment.Version}");
}
