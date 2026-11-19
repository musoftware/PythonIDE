Attribute VB_Name = "VBLib"
' Sum of two
Public Function Sum(ByVal a As Long, Optional ByVal b As Long = 1) As Long
    Sum = a + b
End Function

Public Function Twice(ByVal s As String) As String
    Twice = s & s
End Function

Private Function Secret()
    Secret = 42
End Function
