Attribute VB_Name = "modSem"
Option Explicit

' Typical VB6 statements; Sub Main prints one result per line (Debug.Print)
Public Const APP_NAME As String = "Sem"
Public Enum Level
    lvLow = 1
    lvMid
    lvHigh = 10
End Enum
Public Type Point2
    X As Long
    Y As Long
End Type
Public gCount As Long

Public Function Fact(ByVal n As Long) As Double
    If n <= 1 Then
        Fact = 1
    Else
        Fact = n * Fact(n - 1)
    End If
End Function

Public Function Grade(ByVal score As Integer) As String
    Select Case score
        Case Is >= 90: Grade = "A"
        Case 80 To 89: Grade = "B"
        Case 70, 71, 72, 73, 74, 75, 76, 77, 78, 79: Grade = "C"
        Case Else: Grade = "F"
    End Select
End Function

Public Function Greet(Optional ByVal who As String = "World", Optional ByVal times As Integer = 1) As String
    Dim i As Integer, s As String
    For i = 1 To times
        s = s & "Hi " & who & IIf(i < times, ", ", "")
    Next
    Greet = s
End Function

Public Sub Bump()
    gCount = gCount + 1
End Sub

Private Function SafeDiv(ByVal a As Double, ByVal b As Double) As String
    On Error GoTo Failed
    SafeDiv = CStr(a / b)
    Exit Function
Failed:
    SafeDiv = "error " & Err.Number
End Function

Public Function Sum(ParamArray values() As Variant) As Double
    Dim v As Variant, t As Double
    For Each v In values
        t = t + v
    Next
    Sum = t
End Function

Sub Main()
    Dim i As Integer, n As Long, s As String, arr(4) As Integer, words() As String
    Dim p As Point2, total As Double, k As Integer
    Dim st As New CStack
    Dim c As New Collection, s2 As Variant

    Debug.Print APP_NAME & " " & lvMid & " " & lvHigh
    Debug.Print "fact " & Fact(10)
    Debug.Print Grade(95) & Grade(85) & Grade(72) & Grade(10)
    Debug.Print Greet() & " | " & Greet("Ann", 2)
    For i = 0 To UBound(arr)
        arr(i) = i * i
    Next i
    For i = UBound(arr) To 0 Step -2
        s = s & arr(i) & ";"
    Next
    Debug.Print "arr " & s
    ReDim words(2)
    words(0) = "alpha": words(1) = "beta": words(2) = "gamma"
    ReDim Preserve words(3)
    words(3) = "delta"
    Debug.Print Join(words, "-") & " " & UBound(words)
    s = "The quick brown fox"
    Debug.Print Left$(s, 3) & "|" & Right$(s, 3) & "|" & Mid$(s, 5, 5) & "|" & InStr(s, "brown") & "|" & UCase$(s)
    Debug.Print Len(s) & " " & Replace(s, "quick", "slow") & " " & LCase(Trim$("  X  ")) & "."
    words = Split("a,b,,c", ",")
    Debug.Print UBound(words) & " [" & words(2) & "] " & StrReverse("abc") & " " & Asc("A") & Chr$(66)
    Debug.Print Val("12.5kg") & " " & Val("abc") & " " & CInt(2.5) & " " & CInt(3.5) & " " & Int(-2.5) & " " & Fix(-2.5)
    Debug.Print 7 \ 2 & " " & 7 Mod 3 & " " & 2 ^ 10 & " " & 7 / 2
    Debug.Print Format(1234.5, "#,##0.00") & " " & Format(0.256, "0.0%") & " " & Format(3, "000")
    n = 0
    Do While n < 5
        n = n + 2
    Loop
    Do
        n = n - 1
    Loop Until n <= 3
    Debug.Print "loops " & n
    k = 0
    While k < 3
        k = k + 1
    Wend
    Debug.Print "wend " & k
    For i = 1 To 10
        If i = 4 Then Exit For
    Next
    Debug.Print "exit at " & i
    p.X = 3: p.Y = 4
    Debug.Print "dist " & Sqr(p.X ^ 2 + p.Y ^ 2)
    Call Bump: Call Bump: Call Bump
    Debug.Print "count " & gCount
    Debug.Print "div " & SafeDiv(1, 4) & " " & SafeDiv(1, 0)
    Debug.Print "sum " & Sum(1, 2, 3.5)
    st.Push 10: st.Push 20: st.Push 30
    Debug.Print "stack " & st.Pop & " " & st.Pop & " size " & st.Size
    c.Add "x": c.Add "y": c.Add "z"
    For Each s2 In c
        total = total + 1
    Next
    Debug.Print "coll " & c.Count & " " & c(2) & " " & total
    With p
        .X = .X * 10
        Debug.Print "with " & .X & "," & .Y
    End With
    If gCount > 2 And Len(s) > 0 Or False Then Debug.Print "logic ok"
    Debug.Print "bool " & (3 > 2) & " " & (Not (1 = 1)) & " " & (5 And 3) & " " & (5 Or 2) & " " & (Not 0)
End Sub
