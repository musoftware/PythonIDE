Option Explicit
' Debugger test (VB): expandable Locals (arrays, Types, Collections), hit counts, logpoints.
Private Type PointT
    X As Integer
    Y As Integer
    Label As String
End Type

Private Sub Form_Load()
    Dim numbers(1 To 5) As Integer
    Dim p As PointT
    Dim c As New Collection
    Dim total As Integer, i As Integer
    numbers(1) = 3: numbers(2) = 1: numbers(3) = 4: numbers(4) = 1: numbers(5) = 5
    p.X = 10: p.Y = 20: p.Label = "corner"
    c.Add "first"
    c.Add 42
    For i = 1 To 5
        total = total + numbers(i) * numbers(i)
    Next i
    Debug.Print "total="; total
End Sub
