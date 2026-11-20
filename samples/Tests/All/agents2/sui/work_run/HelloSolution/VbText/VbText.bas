Attribute VB_Name = "VbText"
Option Explicit

' Class Library VbText (Visual Basic 6). Its Public Functions are the library's public functions:
' a project that references VbText (Add Reference) calls them as its own code - VbText.Describe(5)

' Describes a number in words (VB6 code).
Public Function Describe(ByVal n As Variant) As String
    If n < 0 Then
        Describe = "negative"
    ElseIf n = 0 Then
        Describe = "zero"
    ElseIf n < 10 Then
        Describe = "small"
    Else
        Describe = "big"
    End If
    Describe = CStr(n) & " is " & Describe
End Function

' Repeats a text n times.
Public Function Repeat(ByVal text As String, ByVal n As Integer) As String
    Dim i As Integer, s As String
    For i = 1 To n
        s = s & text
    Next i
    Repeat = s
End Function
