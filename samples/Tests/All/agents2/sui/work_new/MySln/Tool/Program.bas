Attribute VB_Name = "Program"
Option Explicit

' Console application: the program starts in Sub Main.
' Output (Debug.Print) appears in the Output window.

Sub Main()
    Dim i As Integer, total As Long
    Debug.Print "Hello from Program!"
    For i = 1 To 10
        total = total + i
    Next i
    Debug.Print "1 + 2 + ... + 10 = " & total
End Sub
