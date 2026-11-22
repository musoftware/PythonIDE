// Event handlers for Form1 (native build test: buttons, textbox, label, checkbox, list, timer, menu, two forms).
public static partial class Form1
{
    static int ticks;

    static void Form1_Load(RadEvent e)
    {
        lblOut.Text = "Loaded";
    }

    static void btnGreet_Click(RadEvent e)
    {
        var name = txtName.Text;
        var text = chkShout.Value == "1" ? radcall<string>("Helper.Shout", name) : Helper.Greet(name);
        lblOut.Text = text;
        lstLog.AddItem(text);
        lblCount.Text = $"{lstLog.ListCount} items";
    }

    static void txtName_TextChanged(RadEvent e)
    {
        lblEcho.Text = "echo:" + txtName.Text;
    }

    static void btnStart_Click(RadEvent e)
    {
        ticks = 0;
        tmrTick.Enabled = true;
    }

    static void tmrTick_Tick(RadEvent e)
    {
        ticks++;
        lblTicks.Text = ticks.ToString();
        if (ticks >= 5) tmrTick.Enabled = false;
    }

    static void btnForm2_Click(RadEvent e)
    {
        Show("Form2");
    }

    static void mnuFileHello_Click(RadEvent e)
    {
        lblOut.Text = "Menu clicked";
    }

    static void mnuFileExit_Click(RadEvent e)
    {
        End();
    }

    static void btnClose_Click(RadEvent e)
    {
        End();
    }
}
