Imports System.Windows.Forms
    Module Program
        <System.STAThread>
        Sub Main()
            Application.EnableVisualStyles()
            Application.Run(New Form1())
        End Sub
    End Module

    Public Class Form1
        Inherits Form
        Friend WithEvents RmRibbon1 As RadIDE.Controls.RmRibbon
        Friend WithEvents RmToggle1 As RadIDE.Controls.RmToggle
        Friend WithEvents RmGauge1 As RadIDE.Controls.RmGauge
        Friend WithEvents lblOut As Label

        Public Sub New()
            Me.RmRibbon1 = New RadIDE.Controls.RmRibbon()
            Me.RmToggle1 = New RadIDE.Controls.RmToggle()
            Me.RmGauge1 = New RadIDE.Controls.RmGauge()
            Me.lblOut = New Label()
            Me.RmRibbon1.Name = "RmRibbon1"
            Me.RmGauge1.Name = "RmGauge1"
            Me.RmRibbon1.Tabs = "[{""Text"":""Home"",""Groups"":[{""Text"":""Go"",""Items"":[{""Text"":""Run"",""Name"":""btnRun"",""Image"":""icon:play"",""Kind"":""Large""}]}]}]"
            Me.RmToggle1.Location = New System.Drawing.Point(12, 150)
            Me.RmToggle1.Name = "RmToggle1"
            Me.RmGauge1.Location = New System.Drawing.Point(200, 140)
            Me.RmGauge1.Value = 64
            Me.RmGauge1.Kind = RadIDE.Controls.RmGaugeKind.Circular
            Me.lblOut.Location = New System.Drawing.Point(12, 190)
            Me.lblOut.Name = "lblOut"
            Me.lblOut.Text = "Ready"
            Me.Controls.Add(Me.RmGauge1)
            Me.Controls.Add(Me.RmToggle1)
            Me.Controls.Add(Me.lblOut)
            Me.Controls.Add(Me.RmRibbon1)
            Me.Text = "RmVb"
            Me.ClientSize = New System.Drawing.Size(480, 320)
        End Sub

        Private Sub RmRibbon1_ItemClick(sender As Object, e As RadIDE.Controls.RmItemEventArgs) Handles RmRibbon1.ItemClick
            lblOut.Text = "Ribbon: " & e.ItemName
        End Sub

        Private Sub RmToggle1_CheckedChanged(sender As Object, e As System.EventArgs) Handles RmToggle1.CheckedChanged
            RadIDE.Controls.RmThemeManager.SetTheme(If(RmToggle1.Checked, "Dark", "Light"))
            lblOut.Text = "Toggle: " & RmToggle1.Checked.ToString()
        End Sub
    End Class
