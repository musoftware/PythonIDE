Option Explicit

Private Sub cmdHide_Click()
    ' lblInfo has "On hide" / "On show" animations: Visible plays them
    lblInfo.Visible = Not lblInfo.Visible
End Sub

Private Sub lblTitle_Click()
    ' any preset from code: preset, duration (ms), "name=value" options
    lblTitle.Animate "slideIn", 500, "from=right"
End Sub

Private Sub pnlBox_Click()
    pnlBox.Animate "pulse"
    fx10.Begin
End Sub
