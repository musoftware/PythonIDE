namespace WinHello;

partial class Form1
{
    private System.ComponentModel.IContainer components = null;

    protected override void Dispose(bool disposing)
    {
        if (disposing && (components != null)) components.Dispose();
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
        this.SuspendLayout();
        // menuStrip1
        this.menuStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[] { this.fileToolStripMenuItem });
        this.menuStrip1.Location = new System.Drawing.Point(0, 0);
        this.menuStrip1.Name = "menuStrip1";
        this.menuStrip1.Size = new System.Drawing.Size(384, 24);
        this.fileToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] { this.exitToolStripMenuItem });
        this.fileToolStripMenuItem.Name = "fileToolStripMenuItem";
        this.fileToolStripMenuItem.Text = "&File";
        this.exitToolStripMenuItem.Name = "exitToolStripMenuItem";
        this.exitToolStripMenuItem.Text = "E&xit";
        this.exitToolStripMenuItem.Click += new System.EventHandler(this.exitToolStripMenuItem_Click);
        // txtName
        this.txtName.Location = new System.Drawing.Point(12, 40);
        this.txtName.Name = "txtName";
        this.txtName.Size = new System.Drawing.Size(200, 23);
        this.txtName.Text = "World";
        // btnGreet
        this.btnGreet.Location = new System.Drawing.Point(224, 39);
        this.btnGreet.Name = "btnGreet";
        this.btnGreet.Size = new System.Drawing.Size(100, 27);
        this.btnGreet.Text = "Greet";
        this.btnGreet.UseVisualStyleBackColor = true;
        this.btnGreet.Click += new System.EventHandler(this.btnGreet_Click);
        // chkUpper
        this.chkUpper.Location = new System.Drawing.Point(12, 72);
        this.chkUpper.Name = "chkUpper";
        this.chkUpper.Size = new System.Drawing.Size(150, 24);
        this.chkUpper.Text = "Upper case";
        // lblResult
        this.lblResult.Font = new System.Drawing.Font("Segoe UI", 12F, System.Drawing.FontStyle.Bold);
        this.lblResult.ForeColor = System.Drawing.Color.DarkBlue;
        this.lblResult.Location = new System.Drawing.Point(12, 104);
        this.lblResult.Name = "lblResult";
        this.lblResult.Size = new System.Drawing.Size(312, 28);
        this.lblResult.Text = "Type a name";
        // lstLog
        this.lstLog.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) | System.Windows.Forms.AnchorStyles.Left) | System.Windows.Forms.AnchorStyles.Right)));
        this.lstLog.Location = new System.Drawing.Point(12, 140);
        this.lstLog.Name = "lstLog";
        this.lstLog.Size = new System.Drawing.Size(312, 100);
        this.lstLog.Items.AddRange(new object[] { "start" });
        this.lstLog.DoubleClick += new System.EventHandler(this.lstLog_DoubleClick);
        // Form1
        this.AutoScaleDimensions = new System.Drawing.SizeF(7F, 15F);
        this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
        this.ClientSize = new System.Drawing.Size(384, 261);
        this.Controls.Add(this.lstLog);
        this.Controls.Add(this.lblResult);
        this.Controls.Add(this.chkUpper);
        this.Controls.Add(this.btnGreet);
        this.Controls.Add(this.txtName);
        this.Controls.Add(this.menuStrip1);
        this.MainMenuStrip = this.menuStrip1;
        this.Name = "Form1";
        this.Text = "Hello WinForms";
        this.Load += new System.EventHandler(this.Form1_Load);
        this.menuStrip1.ResumeLayout(false);
        this.menuStrip1.PerformLayout();
        this.ResumeLayout(false);
        this.PerformLayout();
    }

    private System.Windows.Forms.Button btnGreet;
    private System.Windows.Forms.Label lblResult;
    private System.Windows.Forms.TextBox txtName;
    private System.Windows.Forms.ListBox lstLog;
    private System.Windows.Forms.CheckBox chkUpper;
    private System.Windows.Forms.MenuStrip menuStrip1;
    private System.Windows.Forms.ToolStripMenuItem fileToolStripMenuItem;
    private System.Windows.Forms.ToolStripMenuItem exitToolStripMenuItem;
}
