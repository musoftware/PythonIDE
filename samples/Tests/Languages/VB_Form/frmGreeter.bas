Option Explicit

Private Sub Form_Load()
    lbl1003.Caption = "Type a name and press Greet"
End Sub

Private Sub mnuHelpAbout_Click()
    MsgBox "Greeter 1.0 - made with MinGW", vbInformation, "About Greeter"
End Sub

Private Sub btnGreet_Click()
    Dim your_name, text
    your_name = txtYourName.Text
    text = "Hello, " & your_name & "!"
    lbl1003.Caption = text
    lst1005.AddItem your_name
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub btnClose_Click()
    Unload Me
End Sub

Private Sub mnuFileClear_Click()
    lst1005.Clear
End Sub
