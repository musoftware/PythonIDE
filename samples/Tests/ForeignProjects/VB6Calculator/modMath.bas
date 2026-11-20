Attribute VB_Name = "modMath"
Option Explicit

' Apply a binary operator.  Division by zero returns 0 (a calculator, not a crash).
Public Function Calculate(ByVal a As Double, ByVal b As Double, ByVal op As String) As Double
    Select Case op
        Case "+": Calculate = a + b
        Case "-": Calculate = a - b
        Case "*": Calculate = a * b
        Case "/"
            If b = 0 Then
                Calculate = 0
            Else
                Calculate = a / b
            End If
        Case Else
            Calculate = b
    End Select
End Function

Public Sub Main()
    frmCalc.Show
End Sub
