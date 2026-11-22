Option Explicit
' FeatureMatrix (VB6 -> FreeBASIC native exe): visual state + manual animation from code.

Private Sub cmdAlert_Click()
    GoToState "Alert"
    Debug.Print "state: " & Me.CurrentState
End Sub

Private Sub cmdManual_Click()
    Me.BeginAnimation "fx8"
End Sub

Private Sub fx8_Completed()
    Debug.Print "fx8 completed"
End Sub

Private Sub Form_SizeVariantChanged()
    Debug.Print "sizes: " & Form1.CurrentSizes
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Form1.StopAnimation "fx7"
End Sub
