Attribute VB_Name = "Main"
Sub Main()
    Debug.Print "VB " & PyLib.Add(2, 3) & " " & PyLib.Greet("Ali") & " " & RingLib.Mul(6, 7) & " " & VBLib.Sum(2, 3) & " " & VBLib.Twice("ab")
    Dim a
    a = RingLib.Items(3)
    Debug.Print "VBLIST " & UBound(a) & " " & a(2)
    PyLib.Log "fromvb"
End Sub

Public Function Combined()
    Combined = RingLib.Mul(2, 5) + PyLib.Add(1, 1)
End Function
