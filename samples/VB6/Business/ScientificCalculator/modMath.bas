Attribute VB_Name = "modMath"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modMath - maths helpers of the calculator (VB6 has Sin, Cos, Tan, Atn, Log, Exp, Sqr built in).
Option Explicit

Public Const PI As Double = 3.14159265358979

Public Function ToRadians(ByVal Degrees As Double) As Double
    ToRadians = Degrees * PI / 180
End Function

' VB6 Log() is the natural logarithm; log base 10 = Log(x) / Log(10)
Public Function Log10(ByVal x As Double) As Double
    Log10 = Log(x) / Log(10#)
End Function

' n! for whole numbers 0..170 (a recursive function); anything else raises error 5
Public Function Factorial(ByVal n As Double) As Double
    If n < 0 Or n <> Int(n) Or n > 170 Then Err.Raise 5, "Factorial", "n! needs a whole number from 0 to 170"
    If n <= 1 Then
        Factorial = 1
    Else
        Factorial = n * Factorial(n - 1)
    End If
End Function

' Up to 12 significant digits; very large / small numbers in scientific notation
Public Function FormatResult(ByVal x As Double) As String
    If x = 0 Then
        FormatResult = "0"
    ElseIf Abs(x) >= 1E+15 Or Abs(x) < 0.000001 Then
        FormatResult = Format$(x, "0.##########E+00")
    Else
        FormatResult = CStr(CDbl(Format$(x, "0.############")))
        If Len(FormatResult) > 16 Then FormatResult = Format$(x, "0.##########E+00")
    End If
End Function
