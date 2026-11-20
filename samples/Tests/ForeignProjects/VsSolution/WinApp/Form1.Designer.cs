namespace WinApp;

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
        numA = new NumericUpDown();
        numB = new NumericUpDown();
        btnAdd = new Button();
        lblResult = new Label();
        ((System.ComponentModel.ISupportInitialize)numA).BeginInit();
        ((System.ComponentModel.ISupportInitialize)numB).BeginInit();
        SuspendLayout();
        // 
        // numA
        // 
        numA.Location = new Point(24, 24);
        numA.Name = "numA";
        numA.Size = new Size(80, 23);
        numA.TabIndex = 0;
        // 
        // numB
        // 
        numB.Location = new Point(120, 24);
        numB.Name = "numB";
        numB.Size = new Size(80, 23);
        numB.TabIndex = 1;
        // 
        // btnAdd
        // 
        btnAdd.Location = new Point(216, 23);
        btnAdd.Name = "btnAdd";
        btnAdd.Size = new Size(75, 25);
        btnAdd.TabIndex = 2;
        btnAdd.Text = "Add";
        btnAdd.UseVisualStyleBackColor = true;
        btnAdd.Click += btnAdd_Click;
        // 
        // lblResult
        // 
        lblResult.AutoSize = true;
        lblResult.Location = new Point(304, 27);
        lblResult.Name = "lblResult";
        lblResult.Size = new Size(15, 15);
        lblResult.TabIndex = 3;
        lblResult.Text = "=";
        // 
        // Form1
        // 
        AutoScaleDimensions = new SizeF(7F, 15F);
        AutoScaleMode = AutoScaleMode.Font;
        ClientSize = new Size(400, 80);
        Controls.Add(lblResult);
        Controls.Add(btnAdd);
        Controls.Add(numB);
        Controls.Add(numA);
        Name = "Form1";
        Text = "Calculator (WinApp)";
        ((System.ComponentModel.ISupportInitialize)numA).EndInit();
        ((System.ComponentModel.ISupportInitialize)numB).EndInit();
        ResumeLayout(false);
        PerformLayout();
    }

    #endregion

    private NumericUpDown numA;
    private NumericUpDown numB;
    private Button btnAdd;
    private Label lblResult;
}
