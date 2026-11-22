Option Explicit

Private Sub Form_Load()
    ShownCount = ShownCount + 1
    Me.Caption = "Question #" & ShownCount
    txtAnswer.Text = ""
End Sub

Private Sub cmdOK_Click()
    Answer = txtAnswer.Text
    Form1.lblResult.Caption = "set by Form2"
    Unload Me
End Sub

Private Sub cmdCancel_Click()
    Answer = "(cancelled)"
    Unload Me
End Sub
