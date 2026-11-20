Attribute VB_Name = "MathVB"
Option Explicit

' Called from Python and Ring with radcall("MathVB.AddNumbers", ...)
Public Function AddNumbers(a, b)
    AddNumbers = a + b
End Function

' VB6 calling back into Ring
Public Function Describe(n)
    Describe = "VB6 got " & n & " and Ring says " & RadCall("TextRing.shout", "ok")
End Function
