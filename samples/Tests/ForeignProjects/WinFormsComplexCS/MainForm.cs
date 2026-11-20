namespace WinFormsComplexCS;

/// <summary>
/// A small "notes" window with menus, tool bars, split panels and layout panels.
/// Hand-written to look like a real Visual Studio 2022 project.
/// </summary>
public partial class MainForm : Form
{
    private int _counter;

    public MainForm()
    {
        InitializeComponent();
        // custom code after InitializeComponent (must survive designer saves)
        treeNotes.ExpandAll();
    }

    private void exitToolStripMenuItem_Click(object sender, EventArgs e)
    {
        Close();
    }

    private void btnAdd_Click(object sender, EventArgs e)
    {
        _counter++;
        lstNotes.Items.Add($"{txtTitle.Text} #{_counter}");
        statusLabel.Text = $"{lstNotes.Items.Count} notes";
    }

    private void newToolStripButton_Click(object sender, EventArgs e)
    {
        txtTitle.Clear();
        txtBody.Clear();
    }

    private void MainForm_Load(object sender, EventArgs e)
    {
        cboCategory.SelectedIndex = 0;
    }
}
