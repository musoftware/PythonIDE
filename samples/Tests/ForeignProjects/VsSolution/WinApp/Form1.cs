using MathLib;

namespace WinApp;

public partial class Form1 : Form
{
    public Form1()
    {
        InitializeComponent();
    }

    private void btnAdd_Click(object sender, EventArgs e)
    {
        int a = (int)numA.Value, b = (int)numB.Value;
        lblResult.Text = "= " + Calculator.Add(a, b);
    }
}
