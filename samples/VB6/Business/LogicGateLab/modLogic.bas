Attribute VB_Name = "modLogic"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modLogic - helpers shared by the forms of LogicGateLab.
Option Explicit

Public Const COLOR_ON As Long = &H0000FF00     ' green: signal 1
Public Const COLOR_OFF As Long = &H00404040    ' dark grey: signal 0

Public Function SignalColor(ByVal Signal As Boolean) As Long
    SignalColor = IIf(Signal, COLOR_ON, COLOR_OFF)
End Function

' True -> "1", False -> "0"
Public Function Bit(ByVal Signal As Boolean) As String
    Bit = IIf(Signal, "1", "0")
End Function

' Fill a grid with the truth table of a gate: inputs A, B and the output column
Public Sub FillTruthTable(grd As MSFlexGrid, g As clsGate)
    Dim a As Integer, b As Integer, r As Integer
    grd.Cols = 3
    grd.Rows = 1
    grd.TextMatrix(0, 0) = "A"
    grd.TextMatrix(0, 1) = IIf(g.Inputs = 1, "-", "B")
    grd.TextMatrix(0, 2) = g.Name
    For a = 0 To 1
        For b = 0 To 1
            If g.Inputs = 1 And b = 1 Then Exit For        ' NOT: one row per value of A
            r = grd.Rows
            grd.Rows = r + 1
            grd.TextMatrix(r, 0) = a
            grd.TextMatrix(r, 1) = IIf(g.Inputs = 1, "-", CStr(b))
            grd.TextMatrix(r, 2) = Bit(g.Evaluate(a = 1, b = 1))
        Next b
    Next a
End Sub
