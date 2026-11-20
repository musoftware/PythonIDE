' Customer editor - hand-written to look like a Visual Studio 2019 VB.NET project.
Public Class MainForm

    Private _saved As Integer

    Private Sub MainForm_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        ' custom start-up code (must survive designer saves)
        cboCountry.SelectedIndex = 0
        lblStatus.Text = "Ready"
    End Sub

    Private Sub btnSave_Click(sender As Object, e As EventArgs) Handles btnSave.Click, SaveToolStripMenuItem.Click
        _saved += 1
        lstLog.Items.Add($"Saved {txtName.Text} ({_saved})")
        lblStatus.Text = $"{_saved} saved"
    End Sub

    Private Sub ExitToolStripMenuItem_Click(sender As Object, e As EventArgs) Handles ExitToolStripMenuItem.Click
        Close()
    End Sub

    Private Sub chkVip_CheckedChanged(sender As Object, e As EventArgs) Handles chkVip.CheckedChanged
        grpDetails.BackColor = If(chkVip.Checked, Color.LightYellow, SystemColors.Control)
    End Sub
End Class
