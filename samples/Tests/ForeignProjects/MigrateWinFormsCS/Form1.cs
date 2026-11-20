namespace MigrateWinFormsCS;

public partial class Form1 : Form
{
    private int calculations = 0;

    public Form1()
    {
        InitializeComponent();
    }

    private void Form1_Load(object sender, EventArgs e)
    {
        lblResult.Text = "Total: -";
    }

    private void btnCalc_Click(object sender, EventArgs e)
    {
        if (!double.TryParse(txtAmount.Text, out double amount) || amount < 0)
        {
            MessageBox.Show("Please type a valid amount.", "Tip Calculator", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            txtAmount.Focus();
            return;
        }
        double percent = double.Parse(txtPercent.Text);
        double total = amount + amount * percent / 100.0;
        if (chkRound.Checked)
        {
            total = Math.Round(total);
        }
        calculations++;
        lblResult.Text = "Total: " + total.ToString("F2");
        lstHistory.Items.Add($"{calculations}: {amount} + {percent}% = {total:F2}");
    }

    private void btnClear_Click(object sender, EventArgs e)
    {
        lstHistory.Items.Clear();
        calculations = 0;
        lblResult.Text = "Total: -";
    }

    private void chkRound_CheckedChanged(object sender, EventArgs e)
    {
        btnCalc.Text = chkRound.Checked ? "&Calculate (rounded)" : "&Calculate";
    }
}
