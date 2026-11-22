Option Explicit
Private ticks As Integer

Private Sub Log(ByVal s As String)
    lstLog.AddItem s
    lstLog.ListIndex = lstLog.ListCount - 1
    Debug.Print s
End Sub

Private Sub Form_Load()
    Log "load " & Me.Caption
    Log "date " & Format(dtpWhen.Value, "yyyy-mm-dd") & " " & dtpWhen.Year
    lblStatus.Caption = "count=" & updCount.Value
End Sub

Private Sub cmdHello_Click()
    Log "Hello, " & txtName.Text & " (" & Len(txtName.Text) & ")"
    staMain.SimpleText = "said hello"
End Sub

Private Sub cmdColor_Click()
    If lblTitle.ForeColor = RGB(200, 0, 0) Then
        lblTitle.ForeColor = RGB(31, 61, 122)
    Else
        lblTitle.ForeColor = RGB(200, 0, 0)
    End If
    Log "colour " & lblTitle.ForeColor
End Sub

Private Sub chkBold_Click()
    lblTitle.FontBold = (chkBold.Value = vbChecked)
    Log "bold " & chkBold.Value
End Sub

Private Sub optSmall_Click()
    Log "small"
End Sub

Private Sub optLarge_Click()
    Log "large"
End Sub

Private Sub optRed_Click()
    pnlColors.BackColor = RGB(255, 220, 220)
    Log "red"
End Sub

Private Sub optBlue_Click()
    pnlColors.BackColor = RGB(221, 231, 245)
    Log "blue"
End Sub

Private Sub txtName_Change()
    lblStatus.Caption = "typed " & txtName.Text
End Sub

Private Sub txtName_KeyPress(KeyAscii As Integer)
    If KeyAscii >= 97 And KeyAscii <= 122 Then KeyAscii = KeyAscii - 32
End Sub

Private Sub cboFruit_Click()
    Log "fruit " & cboFruit.Text & " #" & cboFruit.ListIndex
End Sub

Private Sub lstLog_DblClick()
    Log "dbl " & lstLog.Text
End Sub

Private Sub updCount_Change()
    lblStatus.Caption = "count=" & updCount.Value
    prgDone.Value = updCount.Value * 10
End Sub

Private Sub trkLevel_Change()
    lblStatus.Caption = "level=" & trkLevel.Value
End Sub

Private Sub dtpWhen_Change()
    Log "date changed " & dtpWhen.Day
End Sub

Private Sub lnkSite_Click()
    Log "link"
End Sub

Private Sub picLogo_MouseDown(Button As Integer, Shift As Integer, X As Single, Y As Single)
    Log "mouse " & Button & " " & X & "," & Y
End Sub

Private Sub cmdNum_Click(Index As Integer)
    Log "num " & Index & " " & cmdNum(Index).Caption
    cmdNum(Index).Caption = "*" & Index
End Sub

Private Sub cmdPage2_Click()
    tabMain.Tab = 0
    Log "page2 button, tab=" & tabMain.Tab
End Sub

Private Sub tabMain_Click(PreviousTab As Integer)
    Log "tab " & PreviousTab & "->" & tabMain.Tab
End Sub

Private Sub tmrTick_Timer()
    ticks = ticks + 1
    If ticks >= 3 Then
        tmrTick.Enabled = False
        Log "ticks " & ticks
    End If
End Sub

Private Sub mnuClear_Click()
    lstLog.Clear
    Log "cleared"
    tmrTick.Enabled = True
End Sub

Private Sub mnuCheck_Click()
    mnuCheck.Checked = Not mnuCheck.Checked
    Log "checked " & mnuCheck.Checked
End Sub

Private Sub mnuExit_Click()
    Unload Me
End Sub

Private Sub Form_Resize()
    lblStatus.Caption = "size " & Me.ScaleWidth & "x" & Me.ScaleHeight
End Sub
