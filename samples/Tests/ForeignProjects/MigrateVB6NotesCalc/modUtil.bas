Attribute VB_Name = "modUtil"
Option Explicit

' Shared helpers
Public gAppTitle As String

Public Function Greeting(ByVal name As String) As String
    If name = "" Then name = "World"
    Greeting = "Hello, " & name & "!"
End Function

Public Function SumTo(ByVal n As Long) As Long
    Dim i As Long, total As Long
    For i = 1 To n
        total = total + i
    Next
    SumTo = total
End Function
