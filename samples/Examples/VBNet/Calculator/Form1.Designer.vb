<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class Form1
    Inherits System.Windows.Forms.Form

    'Form overrides dispose to clean up the component list.
    <System.Diagnostics.DebuggerNonUserCode()>
    Protected Overrides Sub Dispose(disposing As Boolean)
        Try
            If disposing AndAlso components IsNot Nothing Then
                components.Dispose()
            End If
        Finally
            MyBase.Dispose(disposing)
        End Try
    End Sub

    'Required by the Windows Form Designer
    Private components As System.ComponentModel.IContainer

    'NOTE: The following procedure is required by the Windows Form Designer
    'It can be modified using the Windows Form Designer.  
    'Do not modify it using the code editor.
    <System.Diagnostics.DebuggerStepThrough()>
    Private Sub InitializeComponent()
        components = New System.ComponentModel.Container()
        Me.lblExpr = New System.Windows.Forms.Label()
        Me.lblDisplay = New System.Windows.Forms.Label()
        Me.lblMemory = New System.Windows.Forms.Label()
        Me.btnMC = New System.Windows.Forms.Button()
        Me.btnMR = New System.Windows.Forms.Button()
        Me.btnMPlus = New System.Windows.Forms.Button()
        Me.btnClear = New System.Windows.Forms.Button()
        Me.btn7 = New System.Windows.Forms.Button()
        Me.btn8 = New System.Windows.Forms.Button()
        Me.btn9 = New System.Windows.Forms.Button()
        Me.btnDiv = New System.Windows.Forms.Button()
        Me.btn4 = New System.Windows.Forms.Button()
        Me.btn5 = New System.Windows.Forms.Button()
        Me.btn6 = New System.Windows.Forms.Button()
        Me.btnMul = New System.Windows.Forms.Button()
        Me.btn1 = New System.Windows.Forms.Button()
        Me.btn2 = New System.Windows.Forms.Button()
        Me.btn3 = New System.Windows.Forms.Button()
        Me.btnSub = New System.Windows.Forms.Button()
        Me.btn0 = New System.Windows.Forms.Button()
        Me.btnDot = New System.Windows.Forms.Button()
        Me.btnEquals = New System.Windows.Forms.Button()
        Me.btnAdd = New System.Windows.Forms.Button()
        Me.btnSign = New System.Windows.Forms.Button()
        Me.btnSqrt = New System.Windows.Forms.Button()
        Me.btnPercent = New System.Windows.Forms.Button()
        Me.btnBack = New System.Windows.Forms.Button()
        Me.SuspendLayout()
        '
        'lblExpr
        '
        Me.lblExpr.ForeColor = System.Drawing.Color.FromArgb(96, 96, 96)
        Me.lblExpr.Location = New System.Drawing.Point(12, 8)
        Me.lblExpr.Name = "lblExpr"
        Me.lblExpr.Size = New System.Drawing.Size(260, 18)
        Me.lblExpr.TabIndex = 0
        Me.lblExpr.Text = ""
        Me.lblExpr.TextAlign = System.Drawing.ContentAlignment.TopRight
        '
        'lblDisplay
        '
        Me.lblDisplay.BackColor = System.Drawing.Color.White
        Me.lblDisplay.Font = New System.Drawing.Font("Segoe UI", 20.0!)
        Me.lblDisplay.Location = New System.Drawing.Point(12, 28)
        Me.lblDisplay.Name = "lblDisplay"
        Me.lblDisplay.Size = New System.Drawing.Size(260, 40)
        Me.lblDisplay.TabIndex = 1
        Me.lblDisplay.Text = "0"
        Me.lblDisplay.TextAlign = System.Drawing.ContentAlignment.TopRight
        '
        'lblMemory
        '
        Me.lblMemory.Font = New System.Drawing.Font("Segoe UI", 8.0!)
        Me.lblMemory.ForeColor = System.Drawing.Color.FromArgb(32, 96, 192)
        Me.lblMemory.Location = New System.Drawing.Point(12, 72)
        Me.lblMemory.Name = "lblMemory"
        Me.lblMemory.Size = New System.Drawing.Size(260, 16)
        Me.lblMemory.TabIndex = 2
        Me.lblMemory.Text = ""
        '
        'btnMC
        '
        Me.btnMC.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnMC.Location = New System.Drawing.Point(12, 96)
        Me.btnMC.Name = "btnMC"
        Me.btnMC.Size = New System.Drawing.Size(60, 38)
        Me.btnMC.TabIndex = 3
        Me.btnMC.Text = "MC"
        Me.btnMC.UseVisualStyleBackColor = True
        '
        'btnMR
        '
        Me.btnMR.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnMR.Location = New System.Drawing.Point(78, 96)
        Me.btnMR.Name = "btnMR"
        Me.btnMR.Size = New System.Drawing.Size(60, 38)
        Me.btnMR.TabIndex = 4
        Me.btnMR.Text = "MR"
        Me.btnMR.UseVisualStyleBackColor = True
        '
        'btnMPlus
        '
        Me.btnMPlus.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnMPlus.Location = New System.Drawing.Point(144, 96)
        Me.btnMPlus.Name = "btnMPlus"
        Me.btnMPlus.Size = New System.Drawing.Size(60, 38)
        Me.btnMPlus.TabIndex = 5
        Me.btnMPlus.Text = "M+"
        Me.btnMPlus.UseVisualStyleBackColor = True
        '
        'btnClear
        '
        Me.btnClear.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnClear.Location = New System.Drawing.Point(210, 96)
        Me.btnClear.Name = "btnClear"
        Me.btnClear.Size = New System.Drawing.Size(60, 38)
        Me.btnClear.TabIndex = 6
        Me.btnClear.Text = "C"
        Me.btnClear.UseVisualStyleBackColor = True
        '
        'btn7
        '
        Me.btn7.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn7.Location = New System.Drawing.Point(12, 140)
        Me.btn7.Name = "btn7"
        Me.btn7.Size = New System.Drawing.Size(60, 38)
        Me.btn7.TabIndex = 7
        Me.btn7.Text = "7"
        Me.btn7.UseVisualStyleBackColor = True
        '
        'btn8
        '
        Me.btn8.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn8.Location = New System.Drawing.Point(78, 140)
        Me.btn8.Name = "btn8"
        Me.btn8.Size = New System.Drawing.Size(60, 38)
        Me.btn8.TabIndex = 8
        Me.btn8.Text = "8"
        Me.btn8.UseVisualStyleBackColor = True
        '
        'btn9
        '
        Me.btn9.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn9.Location = New System.Drawing.Point(144, 140)
        Me.btn9.Name = "btn9"
        Me.btn9.Size = New System.Drawing.Size(60, 38)
        Me.btn9.TabIndex = 9
        Me.btn9.Text = "9"
        Me.btn9.UseVisualStyleBackColor = True
        '
        'btnDiv
        '
        Me.btnDiv.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnDiv.Location = New System.Drawing.Point(210, 140)
        Me.btnDiv.Name = "btnDiv"
        Me.btnDiv.Size = New System.Drawing.Size(60, 38)
        Me.btnDiv.TabIndex = 10
        Me.btnDiv.Text = "/"
        Me.btnDiv.UseVisualStyleBackColor = True
        '
        'btn4
        '
        Me.btn4.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn4.Location = New System.Drawing.Point(12, 184)
        Me.btn4.Name = "btn4"
        Me.btn4.Size = New System.Drawing.Size(60, 38)
        Me.btn4.TabIndex = 11
        Me.btn4.Text = "4"
        Me.btn4.UseVisualStyleBackColor = True
        '
        'btn5
        '
        Me.btn5.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn5.Location = New System.Drawing.Point(78, 184)
        Me.btn5.Name = "btn5"
        Me.btn5.Size = New System.Drawing.Size(60, 38)
        Me.btn5.TabIndex = 12
        Me.btn5.Text = "5"
        Me.btn5.UseVisualStyleBackColor = True
        '
        'btn6
        '
        Me.btn6.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn6.Location = New System.Drawing.Point(144, 184)
        Me.btn6.Name = "btn6"
        Me.btn6.Size = New System.Drawing.Size(60, 38)
        Me.btn6.TabIndex = 13
        Me.btn6.Text = "6"
        Me.btn6.UseVisualStyleBackColor = True
        '
        'btnMul
        '
        Me.btnMul.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnMul.Location = New System.Drawing.Point(210, 184)
        Me.btnMul.Name = "btnMul"
        Me.btnMul.Size = New System.Drawing.Size(60, 38)
        Me.btnMul.TabIndex = 14
        Me.btnMul.Text = "*"
        Me.btnMul.UseVisualStyleBackColor = True
        '
        'btn1
        '
        Me.btn1.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn1.Location = New System.Drawing.Point(12, 228)
        Me.btn1.Name = "btn1"
        Me.btn1.Size = New System.Drawing.Size(60, 38)
        Me.btn1.TabIndex = 15
        Me.btn1.Text = "1"
        Me.btn1.UseVisualStyleBackColor = True
        '
        'btn2
        '
        Me.btn2.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn2.Location = New System.Drawing.Point(78, 228)
        Me.btn2.Name = "btn2"
        Me.btn2.Size = New System.Drawing.Size(60, 38)
        Me.btn2.TabIndex = 16
        Me.btn2.Text = "2"
        Me.btn2.UseVisualStyleBackColor = True
        '
        'btn3
        '
        Me.btn3.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn3.Location = New System.Drawing.Point(144, 228)
        Me.btn3.Name = "btn3"
        Me.btn3.Size = New System.Drawing.Size(60, 38)
        Me.btn3.TabIndex = 17
        Me.btn3.Text = "3"
        Me.btn3.UseVisualStyleBackColor = True
        '
        'btnSub
        '
        Me.btnSub.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnSub.Location = New System.Drawing.Point(210, 228)
        Me.btnSub.Name = "btnSub"
        Me.btnSub.Size = New System.Drawing.Size(60, 38)
        Me.btnSub.TabIndex = 18
        Me.btnSub.Text = "-"
        Me.btnSub.UseVisualStyleBackColor = True
        '
        'btn0
        '
        Me.btn0.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btn0.Location = New System.Drawing.Point(12, 272)
        Me.btn0.Name = "btn0"
        Me.btn0.Size = New System.Drawing.Size(60, 38)
        Me.btn0.TabIndex = 19
        Me.btn0.Text = "0"
        Me.btn0.UseVisualStyleBackColor = True
        '
        'btnDot
        '
        Me.btnDot.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnDot.Location = New System.Drawing.Point(78, 272)
        Me.btnDot.Name = "btnDot"
        Me.btnDot.Size = New System.Drawing.Size(60, 38)
        Me.btnDot.TabIndex = 20
        Me.btnDot.Text = "."
        Me.btnDot.UseVisualStyleBackColor = True
        '
        'btnEquals
        '
        Me.btnEquals.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnEquals.Location = New System.Drawing.Point(144, 272)
        Me.btnEquals.Name = "btnEquals"
        Me.btnEquals.Size = New System.Drawing.Size(60, 38)
        Me.btnEquals.TabIndex = 21
        Me.btnEquals.Text = "="
        Me.btnEquals.UseVisualStyleBackColor = True
        '
        'btnAdd
        '
        Me.btnAdd.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnAdd.Location = New System.Drawing.Point(210, 272)
        Me.btnAdd.Name = "btnAdd"
        Me.btnAdd.Size = New System.Drawing.Size(60, 38)
        Me.btnAdd.TabIndex = 22
        Me.btnAdd.Text = "+"
        Me.btnAdd.UseVisualStyleBackColor = True
        '
        'btnSign
        '
        Me.btnSign.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnSign.Location = New System.Drawing.Point(12, 316)
        Me.btnSign.Name = "btnSign"
        Me.btnSign.Size = New System.Drawing.Size(60, 38)
        Me.btnSign.TabIndex = 23
        Me.btnSign.Text = "+/-"
        Me.btnSign.UseVisualStyleBackColor = True
        '
        'btnSqrt
        '
        Me.btnSqrt.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnSqrt.Location = New System.Drawing.Point(78, 316)
        Me.btnSqrt.Name = "btnSqrt"
        Me.btnSqrt.Size = New System.Drawing.Size(60, 38)
        Me.btnSqrt.TabIndex = 24
        Me.btnSqrt.Text = "sqrt"
        Me.btnSqrt.UseVisualStyleBackColor = True
        '
        'btnPercent
        '
        Me.btnPercent.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnPercent.Location = New System.Drawing.Point(144, 316)
        Me.btnPercent.Name = "btnPercent"
        Me.btnPercent.Size = New System.Drawing.Size(60, 38)
        Me.btnPercent.TabIndex = 25
        Me.btnPercent.Text = "%"
        Me.btnPercent.UseVisualStyleBackColor = True
        '
        'btnBack
        '
        Me.btnBack.Font = New System.Drawing.Font("Segoe UI", 12.0!)
        Me.btnBack.Location = New System.Drawing.Point(210, 316)
        Me.btnBack.Name = "btnBack"
        Me.btnBack.Size = New System.Drawing.Size(60, 38)
        Me.btnBack.TabIndex = 26
        Me.btnBack.Text = "<-"
        Me.btnBack.UseVisualStyleBackColor = True
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
        Me.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
        Me.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle
        Me.ClientSize = New System.Drawing.Size(300, 400)
        Me.Controls.Add(Me.lblExpr)
        Me.Controls.Add(Me.lblDisplay)
        Me.Controls.Add(Me.lblMemory)
        Me.Controls.Add(Me.btnMC)
        Me.Controls.Add(Me.btnMR)
        Me.Controls.Add(Me.btnMPlus)
        Me.Controls.Add(Me.btnClear)
        Me.Controls.Add(Me.btn7)
        Me.Controls.Add(Me.btn8)
        Me.Controls.Add(Me.btn9)
        Me.Controls.Add(Me.btnDiv)
        Me.Controls.Add(Me.btn4)
        Me.Controls.Add(Me.btn5)
        Me.Controls.Add(Me.btn6)
        Me.Controls.Add(Me.btnMul)
        Me.Controls.Add(Me.btn1)
        Me.Controls.Add(Me.btn2)
        Me.Controls.Add(Me.btn3)
        Me.Controls.Add(Me.btnSub)
        Me.Controls.Add(Me.btn0)
        Me.Controls.Add(Me.btnDot)
        Me.Controls.Add(Me.btnEquals)
        Me.Controls.Add(Me.btnAdd)
        Me.Controls.Add(Me.btnSign)
        Me.Controls.Add(Me.btnSqrt)
        Me.Controls.Add(Me.btnPercent)
        Me.Controls.Add(Me.btnBack)
        Me.Text = "Calculator"
        Me.ResumeLayout(False)
        Me.PerformLayout()
    End Sub

    Friend WithEvents lblExpr As System.Windows.Forms.Label
    Friend WithEvents lblDisplay As System.Windows.Forms.Label
    Friend WithEvents lblMemory As System.Windows.Forms.Label
    Friend WithEvents btnMC As System.Windows.Forms.Button
    Friend WithEvents btnMR As System.Windows.Forms.Button
    Friend WithEvents btnMPlus As System.Windows.Forms.Button
    Friend WithEvents btnClear As System.Windows.Forms.Button
    Friend WithEvents btn7 As System.Windows.Forms.Button
    Friend WithEvents btn8 As System.Windows.Forms.Button
    Friend WithEvents btn9 As System.Windows.Forms.Button
    Friend WithEvents btnDiv As System.Windows.Forms.Button
    Friend WithEvents btn4 As System.Windows.Forms.Button
    Friend WithEvents btn5 As System.Windows.Forms.Button
    Friend WithEvents btn6 As System.Windows.Forms.Button
    Friend WithEvents btnMul As System.Windows.Forms.Button
    Friend WithEvents btn1 As System.Windows.Forms.Button
    Friend WithEvents btn2 As System.Windows.Forms.Button
    Friend WithEvents btn3 As System.Windows.Forms.Button
    Friend WithEvents btnSub As System.Windows.Forms.Button
    Friend WithEvents btn0 As System.Windows.Forms.Button
    Friend WithEvents btnDot As System.Windows.Forms.Button
    Friend WithEvents btnEquals As System.Windows.Forms.Button
    Friend WithEvents btnAdd As System.Windows.Forms.Button
    Friend WithEvents btnSign As System.Windows.Forms.Button
    Friend WithEvents btnSqrt As System.Windows.Forms.Button
    Friend WithEvents btnPercent As System.Windows.Forms.Button
    Friend WithEvents btnBack As System.Windows.Forms.Button
End Class
