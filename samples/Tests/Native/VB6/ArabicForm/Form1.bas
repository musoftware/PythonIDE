Option Explicit

Private Sub cmdGreet_Click()
    Dim s As String
    s = txtName.Text
    lblOut.Caption = "أهلا يا " & s & " (" & Len(s) & " حروف)، أول حرف: " & Left(s, 1)
    Debug.Print lblOut.Caption
End Sub

Private Sub cmdN_Click(Index As Integer)
    lblOut.Caption = "اخترت " & cmdN(Index).Caption & " = " & (Index + 1)
    Debug.Print lblOut.Caption
End Sub
