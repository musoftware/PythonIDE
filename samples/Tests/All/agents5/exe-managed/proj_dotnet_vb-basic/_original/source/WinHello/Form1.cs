using System;
using System.ComponentModel;
using System.Drawing;
using System.Windows.Forms;

namespace WinHello;

public class Form1 : Form
{
	private int count;

	private IContainer components;

	private Button btnGreet;

	private Label lblResult;

	private TextBox txtName;

	private ListBox lstLog;

	private CheckBox chkUpper;

	private MenuStrip menuStrip1;

	private ToolStripMenuItem fileToolStripMenuItem;

	private ToolStripMenuItem exitToolStripMenuItem;

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
		string text = txtName.Text.Trim();
		if (text == "")
		{
			MessageBox.Show("Please type a name", "Hello");
			return;
		}
		if (chkUpper.Checked)
		{
			text = text.ToUpper();
		}
		count++;
		lblResult.Text = "Hello, " + text + "! (" + count + ")";
		lstLog.Items.Add(text);
		MessageBox.Show("Hello, " + text + "!", "Greeting");
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

	protected override void Dispose(bool disposing)
	{
		if (disposing && components != null)
		{
			components.Dispose();
		}
		base.Dispose(disposing);
	}

	private void InitializeComponent()
	{
		this.btnGreet = new System.Windows.Forms.Button();
		this.lblResult = new System.Windows.Forms.Label();
		this.txtName = new System.Windows.Forms.TextBox();
		this.lstLog = new System.Windows.Forms.ListBox();
		this.chkUpper = new System.Windows.Forms.CheckBox();
		this.menuStrip1 = new System.Windows.Forms.MenuStrip();
		this.fileToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
		this.exitToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
		this.menuStrip1.SuspendLayout();
		base.SuspendLayout();
		this.menuStrip1.Items.AddRange(this.fileToolStripMenuItem);
		this.menuStrip1.Location = new System.Drawing.Point(0, 0);
		this.menuStrip1.Name = "menuStrip1";
		this.menuStrip1.Size = new System.Drawing.Size(384, 24);
		this.fileToolStripMenuItem.DropDownItems.AddRange(this.exitToolStripMenuItem);
		this.fileToolStripMenuItem.Name = "fileToolStripMenuItem";
		this.fileToolStripMenuItem.Text = "&File";
		this.exitToolStripMenuItem.Name = "exitToolStripMenuItem";
		this.exitToolStripMenuItem.Text = "E&xit";
		this.exitToolStripMenuItem.Click += new System.EventHandler(exitToolStripMenuItem_Click);
		this.txtName.Location = new System.Drawing.Point(12, 40);
		this.txtName.Name = "txtName";
		this.txtName.Size = new System.Drawing.Size(200, 23);
		this.txtName.Text = "World";
		this.btnGreet.Location = new System.Drawing.Point(224, 39);
		this.btnGreet.Name = "btnGreet";
		this.btnGreet.Size = new System.Drawing.Size(100, 27);
		this.btnGreet.Text = "Greet";
		this.btnGreet.UseVisualStyleBackColor = true;
		this.btnGreet.Click += new System.EventHandler(btnGreet_Click);
		this.chkUpper.Location = new System.Drawing.Point(12, 72);
		this.chkUpper.Name = "chkUpper";
		this.chkUpper.Size = new System.Drawing.Size(150, 24);
		this.chkUpper.Text = "Upper case";
		this.lblResult.Font = new System.Drawing.Font("Segoe UI", 12f, System.Drawing.FontStyle.Bold);
		this.lblResult.ForeColor = System.Drawing.Color.DarkBlue;
		this.lblResult.Location = new System.Drawing.Point(12, 104);
		this.lblResult.Name = "lblResult";
		this.lblResult.Size = new System.Drawing.Size(312, 28);
		this.lblResult.Text = "Type a name";
		this.lstLog.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right;
		this.lstLog.Location = new System.Drawing.Point(12, 140);
		this.lstLog.Name = "lstLog";
		this.lstLog.Size = new System.Drawing.Size(312, 100);
		this.lstLog.Items.AddRange("start");
		this.lstLog.DoubleClick += new System.EventHandler(lstLog_DoubleClick);
		base.AutoScaleDimensions = new System.Drawing.SizeF(7f, 15f);
		base.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
		base.ClientSize = new System.Drawing.Size(384, 261);
		base.Controls.Add(this.lstLog);
		base.Controls.Add(this.lblResult);
		base.Controls.Add(this.chkUpper);
		base.Controls.Add(this.btnGreet);
		base.Controls.Add(this.txtName);
		base.Controls.Add(this.menuStrip1);
		base.MainMenuStrip = this.menuStrip1;
		base.Name = "Form1";
		this.Text = "Hello WinForms";
		base.Load += new System.EventHandler(Form1_Load);
		this.menuStrip1.ResumeLayout(false);
		this.menuStrip1.PerformLayout();
		base.ResumeLayout(false);
		base.PerformLayout();
	}
}
