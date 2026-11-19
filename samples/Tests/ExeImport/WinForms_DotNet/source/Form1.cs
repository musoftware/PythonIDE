namespace WinHello;

public partial class Form1 : Form
{
    private int count = 0;

    public Form1()
    {
        InitializeComponent();
    }

    private void Form1_Load(object sender, EventArgs e)
    {
        lblResult.Text = "Ready";
    }

    private void btnGreet_Click(object sender, EventArgs e)
    {
        string name = txtName.Text.Trim();
        if (name == "")
        {
            MessageBox.Show("Please type a name", "Hello");
            return;
        }
        if (chkUpper.Checked)
        {
            name = name.ToUpper();
        }
        count++;
        lblResult.Text = "Hello, " + name + "! (" + count.ToString() + ")";
        lstLog.Items.Add(name);
        MessageBox.Show("Hello, " + name + "!", "Greeting");
    }

    private void lstLog_DoubleClick(object sender, EventArgs e)
    {
        if (lstLog.SelectedIndex >= 0)
        {
            txtName.Text = lstLog.SelectedItem.ToString();
        }
        for (int i = 0; i < 3; i++)
        {
            count += i;
        }
    }

    private void exitToolStripMenuItem_Click(object sender, EventArgs e)
    {
        Close();
    }
}
