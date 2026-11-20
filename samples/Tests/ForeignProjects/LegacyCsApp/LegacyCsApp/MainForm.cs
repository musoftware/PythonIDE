using System;
using System.Windows.Forms;

namespace LegacyCsApp
{
    public partial class MainForm : Form
    {
        public MainForm()
        {
            InitializeComponent();
        }

        private void btnHello_Click(object sender, EventArgs e)
        {
            MessageBox.Show("Hello, " + txtName.Text + "!", "Legacy .NET Framework 4.8");
        }
    }
}
