namespace MigrateWinFormsCS;

partial class Form1
{
    /// <summary>
    ///  Required designer variable.
    /// </summary>
    private System.ComponentModel.IContainer components = null;

    /// <summary>
    ///  Clean up any resources being used.
    /// </summary>
    /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
    protected override void Dispose(bool disposing)
    {
        if (disposing && (components != null))
        {
            components.Dispose();
        }
        base.Dispose(disposing);
    }

    #region Windows Form Designer generated code

    /// <summary>
    ///  Required method for Designer support - do not modify
    ///  the contents of this method with the code editor.
    /// </summary>
    private void InitializeComponent()
    {
        lblAmount = new Label();
        txtAmount = new TextBox();
        lblPercent = new Label();
        txtPercent = new TextBox();
        chkRound = new CheckBox();
        btnCalc = new Button();
        lblResult = new Label();
        lstHistory = new ListBox();
        btnClear = new Button();
        SuspendLayout();
        // 
        // lblAmount
        // 
        lblAmount.AutoSize = true;
        lblAmount.Location = new Point(12, 15);
        lblAmount.Name = "lblAmount";
        lblAmount.Size = new Size(54, 15);
        lblAmount.TabIndex = 0;
        lblAmount.Text = "Amount:";
        // 
        // txtAmount
        // 
        txtAmount.Location = new Point(90, 12);
        txtAmount.Name = "txtAmount";
        txtAmount.Size = new Size(120, 23);
        txtAmount.TabIndex = 1;
        txtAmount.Text = "100";
        // 
        // lblPercent
        // 
        lblPercent.AutoSize = true;
        lblPercent.Location = new Point(12, 44);
        lblPercent.Name = "lblPercent";
        lblPercent.Size = new Size(36, 15);
        lblPercent.TabIndex = 2;
        lblPercent.Text = "Tip %:";
        // 
        // txtPercent
        // 
        txtPercent.Location = new Point(90, 41);
        txtPercent.Name = "txtPercent";
        txtPercent.Size = new Size(120, 23);
        txtPercent.TabIndex = 3;
        txtPercent.Text = "15";
        // 
        // chkRound
        // 
        chkRound.AutoSize = true;
        chkRound.Location = new Point(90, 70);
        chkRound.Name = "chkRound";
        chkRound.Size = new Size(110, 19);
        chkRound.TabIndex = 4;
        chkRound.Text = "Round the total";
        chkRound.UseVisualStyleBackColor = true;
        chkRound.CheckedChanged += chkRound_CheckedChanged;
        // 
        // btnCalc
        // 
        btnCalc.Location = new Point(224, 11);
        btnCalc.Name = "btnCalc";
        btnCalc.Size = new Size(90, 25);
        btnCalc.TabIndex = 5;
        btnCalc.Text = "&Calculate";
        btnCalc.UseVisualStyleBackColor = true;
        btnCalc.Click += btnCalc_Click;
        // 
        // lblResult
        // 
        lblResult.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        lblResult.ForeColor = Color.DarkBlue;
        lblResult.Location = new Point(12, 98);
        lblResult.Name = "lblResult";
        lblResult.Size = new Size(302, 20);
        lblResult.TabIndex = 6;
        lblResult.Text = "Total:";
        // 
        // lstHistory
        // 
        lstHistory.FormattingEnabled = true;
        lstHistory.ItemHeight = 15;
        lstHistory.Location = new Point(12, 124);
        lstHistory.Name = "lstHistory";
        lstHistory.Size = new Size(302, 94);
        lstHistory.TabIndex = 7;
        // 
        // btnClear
        // 
        btnClear.Location = new Point(224, 224);
        btnClear.Name = "btnClear";
        btnClear.Size = new Size(90, 25);
        btnClear.TabIndex = 8;
        btnClear.Text = "C&lear";
        btnClear.UseVisualStyleBackColor = true;
        btnClear.Click += btnClear_Click;
        // 
        // Form1
        // 
        AcceptButton = btnCalc;
        AutoScaleDimensions = new SizeF(7F, 15F);
        AutoScaleMode = AutoScaleMode.Font;
        ClientSize = new Size(326, 261);
        Controls.Add(btnClear);
        Controls.Add(lstHistory);
        Controls.Add(lblResult);
        Controls.Add(btnCalc);
        Controls.Add(chkRound);
        Controls.Add(txtPercent);
        Controls.Add(lblPercent);
        Controls.Add(txtAmount);
        Controls.Add(lblAmount);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        Name = "Form1";
        StartPosition = FormStartPosition.CenterScreen;
        Text = "Tip Calculator";
        Load += Form1_Load;
        ResumeLayout(false);
        PerformLayout();
    }

    #endregion

    private Label lblAmount;
    private TextBox txtAmount;
    private Label lblPercent;
    private TextBox txtPercent;
    private CheckBox chkRound;
    private Button btnCalc;
    private Label lblResult;
    private ListBox lstHistory;
    private Button btnClear;
}
