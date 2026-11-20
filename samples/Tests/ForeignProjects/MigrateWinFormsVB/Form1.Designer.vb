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
        Me.lblCelsius = New System.Windows.Forms.Label()
        Me.txtCelsius = New System.Windows.Forms.TextBox()
        Me.btnConvert = New System.Windows.Forms.Button()
        Me.lblOut = New System.Windows.Forms.Label()
        Me.chkKelvin = New System.Windows.Forms.CheckBox()
        Me.lstLog = New System.Windows.Forms.ListBox()
        Me.btnClear = New System.Windows.Forms.Button()
        Me.SuspendLayout()
        '
        'lblCelsius
        '
        Me.lblCelsius.AutoSize = True
        Me.lblCelsius.Location = New System.Drawing.Point(12, 15)
        Me.lblCelsius.Name = "lblCelsius"
        Me.lblCelsius.Size = New System.Drawing.Size(57, 15)
        Me.lblCelsius.TabIndex = 0
        Me.lblCelsius.Text = "Celsius:"
        '
        'txtCelsius
        '
        Me.txtCelsius.Location = New System.Drawing.Point(80, 12)
        Me.txtCelsius.Name = "txtCelsius"
        Me.txtCelsius.Size = New System.Drawing.Size(100, 23)
        Me.txtCelsius.TabIndex = 1
        Me.txtCelsius.Text = "25"
        '
        'btnConvert
        '
        Me.btnConvert.Location = New System.Drawing.Point(190, 11)
        Me.btnConvert.Name = "btnConvert"
        Me.btnConvert.Size = New System.Drawing.Size(90, 25)
        Me.btnConvert.TabIndex = 2
        Me.btnConvert.Text = "&Convert"
        Me.btnConvert.UseVisualStyleBackColor = True
        '
        'lblOut
        '
        Me.lblOut.Location = New System.Drawing.Point(12, 45)
        Me.lblOut.Name = "lblOut"
        Me.lblOut.Size = New System.Drawing.Size(268, 20)
        Me.lblOut.TabIndex = 3
        Me.lblOut.Text = "Fahrenheit: -"
        '
        'chkKelvin
        '
        Me.chkKelvin.AutoSize = True
        Me.chkKelvin.Location = New System.Drawing.Point(12, 70)
        Me.chkKelvin.Name = "chkKelvin"
        Me.chkKelvin.Size = New System.Drawing.Size(110, 19)
        Me.chkKelvin.TabIndex = 4
        Me.chkKelvin.Text = "Also show Kelvin"
        Me.chkKelvin.UseVisualStyleBackColor = True
        '
        'lstLog
        '
        Me.lstLog.FormattingEnabled = True
        Me.lstLog.ItemHeight = 15
        Me.lstLog.Location = New System.Drawing.Point(12, 96)
        Me.lstLog.Name = "lstLog"
        Me.lstLog.Size = New System.Drawing.Size(268, 94)
        Me.lstLog.TabIndex = 5
        '
        'btnClear
        '
        Me.btnClear.Location = New System.Drawing.Point(190, 196)
        Me.btnClear.Name = "btnClear"
        Me.btnClear.Size = New System.Drawing.Size(90, 25)
        Me.btnClear.TabIndex = 6
        Me.btnClear.Text = "C&lear"
        Me.btnClear.UseVisualStyleBackColor = True
        '
        'Form1
        '
        Me.AcceptButton = Me.btnConvert
        Me.AutoScaleDimensions = New System.Drawing.SizeF(7.0!, 15.0!)
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
        Me.ClientSize = New System.Drawing.Size(292, 233)
        Me.Controls.Add(Me.btnClear)
        Me.Controls.Add(Me.lstLog)
        Me.Controls.Add(Me.chkKelvin)
        Me.Controls.Add(Me.lblOut)
        Me.Controls.Add(Me.btnConvert)
        Me.Controls.Add(Me.txtCelsius)
        Me.Controls.Add(Me.lblCelsius)
        Me.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle
        Me.MaximizeBox = False
        Me.Name = "Form1"
        Me.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
        Me.Text = "Temperature"
        Me.ResumeLayout(False)
        Me.PerformLayout()

    End Sub

    Friend WithEvents lblCelsius As Label
    Friend WithEvents txtCelsius As TextBox
    Friend WithEvents btnConvert As Button
    Friend WithEvents lblOut As Label
    Friend WithEvents chkKelvin As CheckBox
    Friend WithEvents lstLog As ListBox
    Friend WithEvents btnClear As Button
End Class
