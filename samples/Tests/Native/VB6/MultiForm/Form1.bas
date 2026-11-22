Option Explicit

Private Sub cmdAsk_Click()
    Form2.lblQ.Caption = "Favourite colour of " & txtName.Text & "?"
    Form2.Show vbModal
    lblResult.Caption = "answer: " & Answer & " (shown " & ShownCount & ")"
    Debug.Print lblResult.Caption
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub

Private Sub Form_QueryUnload(Cancel As Integer, UnloadMode As Integer)
    Debug.Print "queryunload " & UnloadMode
    If chkKeep.Value = vbChecked Then
        Cancel = 1
        lblResult.Caption = "refused"
    End If
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Debug.Print "unload main"
End Sub
