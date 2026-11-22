Option Explicit
Private mCount As Integer

Private Sub Form_Load()
    lblResult.Caption = "Type a name and press Greet"
End Sub

Private Sub btnGreet_Click()
    Dim sName As String
    sName = txtName.Text
    If chkUpper.Value = vbChecked Then sName = UCase(sName)
    mCount = mCount + 1
    lblResult.Caption = "Hello, " & sName & "! (#" & mCount & ")"
    lstLog.AddItem sName
End Sub

Private Sub Timer1_Timer()
    lblClock.Caption = Format(Now, "hh:nn:ss")
End Sub

Private Sub mnuFileClear_Click()
    lstLog.Clear
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub mnuHelpAbout_Click()
    MsgBox "Made with RAD IDE - VB6 lives again!", vbInformation, "About"
End Sub
