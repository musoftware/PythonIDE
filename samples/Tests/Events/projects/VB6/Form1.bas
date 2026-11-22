Option Explicit
Private closing As Integer

Private Sub EvLog(ByVal s As String)
    Debug.Print "EVT " & s
End Sub

Private Sub Form_Initialize()
    EvLog "Form_Initialize"
End Sub

Private Sub Form_Load()
    EvLog "Form_Load"
End Sub

Private Sub Form_Activate()
    EvLog "Form_Activate"
End Sub

Private Sub Form_QueryUnload(Cancel As Integer, UnloadMode As Integer)
    closing = closing + 1
    EvLog "Form_QueryUnload mode=" & UnloadMode
    If closing = 1 Then Cancel = 1
End Sub

Private Sub Form_Unload(Cancel As Integer)
    EvLog "Form_Unload"
End Sub

Private Sub Form_Terminate()
    EvLog "Form_Terminate"
End Sub

Private Sub cmdA_MouseDown(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "cmdA_MouseDown " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub cmdA_MouseUp(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "cmdA_MouseUp " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub cmdA_Click()
    EvLog "cmdA_Click"
End Sub

Private Sub lblA_MouseDown(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "lblA_MouseDown " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub lblA_MouseUp(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "lblA_MouseUp " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub lblA_Click()
    EvLog "lblA_Click"
End Sub

Private Sub txtA_GotFocus()
    EvLog "txtA_GotFocus"
End Sub

Private Sub txtA_LostFocus()
    EvLog "txtA_LostFocus"
End Sub

Private Sub txtA_KeyDown(KeyCode As Integer, Shift As Integer)
    EvLog "txtA_KeyDown " & KeyCode & " " & Shift
End Sub

Private Sub txtA_KeyPress(KeyAscii As Integer)
    EvLog "txtA_KeyPress " & KeyAscii
    If KeyAscii = 120 Then KeyAscii = 0
    If KeyAscii = 98 Then KeyAscii = 66
End Sub

Private Sub txtA_KeyUp(KeyCode As Integer, Shift As Integer)
    EvLog "txtA_KeyUp " & KeyCode & " " & Shift
End Sub

Private Sub txtA_Change()
    EvLog "txtA_Change text=" & txtA.Text
End Sub

Private Sub txtB_GotFocus()
    EvLog "txtB_GotFocus"
End Sub

Private Sub txtB_LostFocus()
    EvLog "txtB_LostFocus"
End Sub

Private Sub txtB_Validate(Cancel As Boolean)
    EvLog "txtB_Validate text=" & txtB.Text
    If txtB.Text = "stay" Then Cancel = True
End Sub

Private Sub chkA_Click()
    EvLog "chkA_Click value=" & chkA.Value
End Sub

Private Sub lstA_Click()
    EvLog "lstA_Click index=" & lstA.ListIndex
End Sub

Private Sub cmdCode_Click()
    EvLog "cmdCode_Click begin"
    txtA.Text = "code"
    chkA.Value = 1
    lstA.ListIndex = 2
    EvLog "cmdCode_Click end"
End Sub

Private Sub cmdTmr_Click()
    EvLog "cmdTmr_Click"
    tmrA.Enabled = True
End Sub

Private Sub tmrA_Timer()
    tmrA.Enabled = False
    EvLog "tmrA_Timer"
End Sub

Private Sub cmdDoEv_Click()
    Dim t As Single
    EvLog "cmdDoEv_Click begin"
    tmrA.Enabled = True
    t = Timer
    Do While Timer - t < 0.8
        DoEvents
    Loop
    EvLog "cmdDoEv_Click end"
End Sub

Private Sub cmdMsg_Click()
    EvLog "cmdMsg_Click begin"
    tmrA.Enabled = True
    MsgBox "modal"
    EvLog "cmdMsg_Click end"
End Sub

Private Sub cmdErr_Click()
    Dim d As Integer
    EvLog "cmdErr_Click begin"
    d = 0
    d = 10 / d
    EvLog "cmdErr_Click end"
End Sub

Private Sub cmdUnload_Click()
    EvLog "cmdUnload_Click begin"
    Unload Me
    EvLog "cmdUnload_Click end"
End Sub
