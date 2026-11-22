"""Small VB6 programs (Sub Main + Debug.Print) run by the IDE's interpreter and by the native exe.

Each entry: (name, VB source).  The output of the two must be identical.
"""

SNIPPETS = [
    ("arith", """
Sub Main()
    Dim a As Integer, b As Long, c As Double, d As Single
    a = 7: b = 2: c = 2.5: d = 1.25
    Debug.Print a + b, a - b, a * b, a / b, a \\ b, a Mod b, a ^ b
    Debug.Print c * 2, c / 3, -c, d + c, 10 / 4
    Debug.Print 0.1 + 0.2, 1 / 3, 2 ^ 0.5, 1E+20, 123456789 * 1000
    Debug.Print -7 \\ 2, -7 Mod 3, 7.5 \\ 2, CInt(2.5), CInt(3.5), CLng(-2.5)
End Sub
"""),
    ("strings", """
Sub Main()
    Dim s As String
    s = "Hello, World"
    Debug.Print Len(s); Left(s, 5); "|"; Right(s, 5); "|"; Mid(s, 8); "|"; Mid(s, 8, 3)
    Debug.Print InStr(s, "o"); InStr(6, s, "o"); InStr(1, s, "WORLD", vbTextCompare); InStrRev(s, "o")
    Debug.Print UCase(s), LCase(s), Replace(s, "l", "L"), StrReverse("abc")
    Debug.Print "[" & Trim("  x  ") & "][" & LTrim("  x") & "][" & RTrim("x  ") & "]"
    Debug.Print Space(3) & "|" & String(4, "*") & String(2, 65) & Chr(66) & Asc("a")
    Debug.Print StrComp("a", "b"), StrComp("B", "a", vbTextCompare), StrConv("hello world", vbProperCase)
    Debug.Print "a" & 1 & 2.5 & True & "b"
    Debug.Print Val("12abc"), Val(" 3 4 "), Val("1.5e2"), Val("x"), Str(5), Str(-5)
    Debug.Print Hex(255), Oct(8), Hex(-1)
End Sub
"""),
    ("unicode", """
Sub Main()
    Dim s As String
    s = "مرحبا بالعالم"
    Debug.Print Len(s), Left(s, 5), Right(s, 6), Mid(s, 7, 2), InStr(s, "عا")
    Debug.Print ChrW(1576) & ChrW(65), AscW("ب"), StrReverse("أب")
End Sub
"""),
    ("conversions", """
Sub Main()
    Dim v As Variant
    Debug.Print CStr(12), CStr(1.5), CDbl("3.25") + 1, CLng("42") * 2, CBool(1), CBool(0), CBool("True")
    Debug.Print CInt("7") + CInt(True), IsNumeric("12.5"), IsNumeric("abc"), IsNumeric("")
    v = "10"
    Debug.Print v + 5, v & 5, v * 2
    v = 3
    Debug.Print TypeName(v), VarType(v)
    v = 3.5
    Debug.Print TypeName(v), v
    v = "x"
    Debug.Print TypeName(v), IsEmpty(v)
    Dim e As Variant
    Debug.Print IsEmpty(e), TypeName(e), "[" & e & "]"
End Sub
"""),
    ("booleans", """
Sub Main()
    Dim a As Boolean, b As Boolean, n As Integer
    a = True: b = False
    Debug.Print a, b, Not a, a And b, a Or b, a Xor b, a = b
    n = 5
    Debug.Print (n > 3), (n > 3) And (n < 10), 6 And 3, 6 Or 3, 6 Xor 3, Not 0
    Debug.Print CInt(a), a + 1
    If n > 3 Then Debug.Print "big" Else Debug.Print "small"
End Sub
"""),
    ("ifselect", """
Sub Main()
    Dim i As Integer, s As String
    For i = 1 To 12 Step 3
        Select Case i
            Case 1: s = "one"
            Case 2 To 5: s = "few"
            Case 6, 7: s = "six-seven"
            Case Is >= 10: s = "many"
            Case Else: s = "other"
        End Select
        Debug.Print i; s
    Next i
    Dim w As String
    w = "pear"
    Select Case w
        Case "apple", "pear": Debug.Print "fruit"
        Case Else: Debug.Print "?"
    End Select
    Dim v As Variant
    v = 15
    Select Case v
        Case 1 To 10: Debug.Print "low"
        Case Is > 10: Debug.Print "high"
    End Select
    If i = 13 Then
        Debug.Print "thirteen"
    ElseIf i = 14 Then
        Debug.Print "fourteen"
    Else
        Debug.Print "else"
    End If
End Sub
"""),
    ("loops", """
Sub Main()
    Dim i As Integer, j As Integer, total As Long
    For i = 10 To 1 Step -2
        total = total + i
    Next
    Debug.Print total
    i = 0
    Do While i < 5
        i = i + 1
    Loop
    Debug.Print i
    Do
        i = i - 1
    Loop Until i <= 2
    Debug.Print i
    Do Until i >= 4
        i = i + 1
    Loop
    Debug.Print i
    While i < 7
        i = i + 1
    Wend
    Debug.Print i
    For i = 1 To 3
        For j = 1 To 3
            If j = 2 Then Exit For
            Debug.Print i * 10 + j;
        Next j
    Next i
    Debug.Print
    Do
        i = i + 1
        If i > 20 Then Exit Do
    Loop
    Debug.Print i
    Dim d As Double
    For d = 0 To 1 Step 0.25
        Debug.Print d;
    Next
    Debug.Print
End Sub
"""),
    ("arrays", """
Sub Main()
    Dim a(5) As Integer, i As Integer
    For i = 0 To 5
        a(i) = i * i
    Next
    Debug.Print LBound(a), UBound(a), a(3), a(5)
    Dim b() As String
    ReDim b(2)
    b(0) = "x": b(1) = "y": b(2) = "z"
    ReDim Preserve b(4)
    b(4) = "w"
    Debug.Print UBound(b), b(0) & b(1) & b(2) & "[" & b(3) & "]" & b(4)
    Dim m(1 To 3, 1 To 2) As Long
    m(2, 1) = 21: m(3, 2) = 32
    Debug.Print m(2, 1) + m(3, 2), UBound(m, 1), UBound(m, 2), LBound(m, 2)
    Dim parts() As String
    parts = Split("a,b,,c", ",")
    Debug.Print UBound(parts), Join(parts, "-"), parts(3)
    Dim n As Integer
    n = 3
    Dim dyn() As Double
    ReDim dyn(1 To n)
    dyn(n) = 1.5
    Debug.Print UBound(dyn), dyn(3)
    Erase b
End Sub
"""),
    ("procs", """
Private Function Square(ByVal x As Double) As Double
    Square = x * x
End Function

Private Sub Bump(n As Integer)
    n = n + 1
End Sub

Private Sub BumpVal(ByVal n As Integer)
    n = n + 1
End Sub

Private Function Fact(ByVal n As Long) As Long
    If n <= 1 Then
        Fact = 1
    Else
        Fact = n * Fact(n - 1)
    End If
End Function

Private Function Greet(Optional ByVal who As String = "World", Optional ByVal times As Integer = 1) As String
    Dim i As Integer
    For i = 1 To times
        Greet = Greet & "Hi " & who & ";"
    Next
End Function

Private Function Sum(arr() As Integer) As Long
    Dim i As Integer
    For i = LBound(arr) To UBound(arr)
        Sum = Sum + arr(i)
    Next
End Function

Private Function Early(ByVal x As Integer) As String
    Early = "start"
    If x > 0 Then Exit Function
    Early = "end"
End Function

Sub Main()
    Dim k As Integer
    k = 1
    Bump k
    BumpVal k
    Call Bump(k)
    Debug.Print Square(1.5), k, Fact(10)
    Debug.Print Greet(), Greet("Ann"), Greet(times:=2), Greet("Bo", 2)
    Dim a(1 To 4) As Integer
    a(1) = 1: a(2) = 2: a(3) = 3: a(4) = 4
    Debug.Print Sum(a), Early(1), Early(0)
End Sub
"""),
    ("variants", """
Sub Main()
    Dim v As Variant, w As Variant
    v = 5
    w = "7"
    Debug.Print v + w, v & w, v * w, w - v, v / 2, v \\ 2, v Mod 3
    v = "abc"
    Debug.Print v + "def", v < "abd", Len(v)
    v = True
    Debug.Print v, Not v
    v = 2.5
    w = 2
    Debug.Print v > w, v = 2.5, v <> w
    Dim total
    total = 0
    Dim i
    For i = 1 To 4
        total = total + i
    Next
    Debug.Print total, i
End Sub
"""),
    ("udt", """
Private Type Person
    Name As String
    Age As Integer
    Scores(1 To 3) As Integer
End Type

Sub Main()
    Dim p As Person, q As Person
    p.Name = "Ann"
    p.Age = 30
    p.Scores(2) = 88
    q = p
    q.Name = "Bob"
    Debug.Print p.Name, q.Name, q.Age, q.Scores(2)
    Dim team(2) As Person
    team(1).Name = "Cy"
    team(1).Age = team(1).Age + 5
    Debug.Print team(1).Name, team(1).Age
    With p
        .Age = .Age + 1
        Debug.Print .Name; .Age
    End With
End Sub
"""),
    ("enums_consts", """
Private Enum Color
    Red = 1
    Green
    Blue = 10
End Enum
Private Const PI As Double = 3.14159
Private Const NAME_ As String = "Box"
Const MAXN = 3

Sub Main()
    Dim c As Color
    c = Green
    Debug.Print Red, c, Blue
    Debug.Print PI * 2, NAME_ & "!", MAXN + 1
    Const LOCAL_K = 5
    Debug.Print LOCAL_K * 2
End Sub
"""),
    ("errors", """
Private Function SafeDiv(ByVal a As Double, ByVal b As Double) As String
    On Error GoTo Fail
    SafeDiv = CStr(a / b)
    Exit Function
Fail:
    SafeDiv = "error " & Err.Number & ": " & Err.Description
End Function

Private Sub Thrower()
    Err.Raise 1234, "me", "custom problem"
End Sub

Private Sub Catcher()
    On Error GoTo H
    Thrower
    Debug.Print "not reached"
    Exit Sub
H:
    Debug.Print "caught"; Err.Number; Err.Description
End Sub

Sub Main()
    Debug.Print SafeDiv(1, 2), SafeDiv(1, 0)
    Catcher
    On Error Resume Next
    Dim x As Integer
    x = 1 / 0
    Debug.Print "after", Err.Number
    Err.Clear
    Debug.Print Err.Number
    x = CInt("abc")
    Debug.Print Err.Number, Err.Description
    On Error GoTo 0
    Dim a(2) As Integer
    On Error Resume Next
    a(5) = 1
    Debug.Print "subscript", Err.Number
End Sub
"""),
    ("resume_next", """
Sub Main()
    On Error GoTo Handler
    Dim r As Double
    r = 10 / 0
    Debug.Print "resumed", r
    r = Sqr(-1)
    Debug.Print "again"
    Exit Sub
Handler:
    Debug.Print "handler"; Err.Number
    Resume Next
End Sub
"""),
    ("gosub_goto", """
Sub Main()
    Dim i As Integer
    i = 0
Again:
    i = i + 1
    If i < 3 Then GoTo Again
    Debug.Print "i ="; i
    GoSub Sub1
    GoSub Sub1
    Debug.Print "done"
    Exit Sub
Sub1:
    Debug.Print "in gosub"
    Return
End Sub
"""),
    ("format", """
Sub Main()
    Debug.Print Format(1234.5678, "#,##0.00"), Format(0.256, "0.0%"), Format(5, "000")
    Debug.Print Format(3.14159, "0.00"), Format(2.675, "0.00"), Format(1234567, "#,##0")
    Debug.Print Format(-5.5, "0.0;(0.0)"), Format(0, "0.0;-0.0;zero"), Format(1500, "Currency")
    Debug.Print Format(12, "Fixed"), Format(1234.5, "Standard"), Format(0.5, "Percent")
    Debug.Print Format(1, "Yes/No"), Format(0, "True/False"), Format("abc", ">"), Format(123.456)
    Debug.Print Format(1.5E-07, "0.00E+00"), Format(7, "General Number")
    Dim d As Date
    d = DateSerial(2024, 3, 5) + TimeSerial(14, 7, 9)
    Debug.Print Format(d, "yyyy-mm-dd hh:nn:ss"), Format(d, "dd/mm/yy"), Format(d, "dddd, mmmm d")
    Debug.Print Format(d, "h:nn AM/PM"), Format(d, "Short Date"), Format(d, "Long Time"), Format(d, "mmm")
    Debug.Print FormatNumber(1234.567, 1), FormatPercent(0.1234)
End Sub
"""),
    ("dates", """
Sub Main()
    Dim d As Date, e As Date
    d = DateSerial(2024, 1, 31)
    e = DateAdd("m", 1, d)
    Debug.Print d, e, DateAdd("d", 30, d), DateAdd("yyyy", -1, d)
    Debug.Print DateDiff("d", d, e), DateDiff("m", d, DateSerial(2025, 6, 1)), DateDiff("yyyy", d, e)
    Debug.Print Year(d), Month(d), Day(d), Weekday(d), DatePart("q", d), DatePart("y", e)
    Debug.Print MonthName(2), MonthName(2, True), WeekdayName(1), WeekdayName(7, True)
    d = DateSerial(2023, 12, 25) + TimeSerial(8, 30, 0)
    Debug.Print d, Hour(d), Minute(d), Second(d)
    Debug.Print TimeSerial(13, 5, 7), #3/15/2024#
    Debug.Print CDate("2024-02-29") + 1
End Sub
"""),
    ("math", """
Sub Main()
    Debug.Print Abs(-3), Abs(-2.5), Int(2.7), Int(-2.7), Fix(-2.7), Sgn(-4), Sgn(0)
    Debug.Print Sqr(16), Round(2.5), Round(3.5), Round(2.567, 2), Exp(0), Log(1)
    Debug.Print Sin(0), Cos(0), Atn(1) * 4
    Debug.Print 5 Mod 3, -5 Mod 3, 17 \\ 5, 2 ^ 10, 10 / 4
    Debug.Print RGB(255, 0, 0), RGB(0, 128, 255)
    Debug.Print IIf(3 > 2, "yes", "no"), IIf(1 > 2, 1, 2.5)
End Sub
"""),
    ("collection", """
Sub Main()
    Dim c As New Collection
    c.Add "apple"
    c.Add "banana", "b"
    c.Add 42
    c.Add "first", , 1
    Debug.Print c.Count, c(1), c.Item(2), c("b"), c(4)
    c.Remove 1
    Debug.Print c.Count, c(1)
    Dim x As Variant
    For Each x In c
        Debug.Print x;
    Next
    Debug.Print
    On Error Resume Next
    c.Add "dup", "b"
    Debug.Print Err.Number
End Sub
"""),
    ("foreach_array", """
Sub Main()
    Dim a(3) As String, s As Variant, total As String
    a(0) = "w": a(1) = "x": a(2) = "y": a(3) = "z"
    For Each s In a
        total = total & s
    Next
    Debug.Print total
End Sub
"""),
    ("files", """
Sub Main()
    Dim f As Integer, line_ As String, a As String, b As Integer, c As Double
    f = FreeFile
    Open "native_test.txt" For Output As #f
    Print #f, "first line"
    Print #f, "x"; 5; "y"
    Print #f, 1, 2
    Write #f, "quoted", 42, 1.5, True
    Close #f
    Open "native_test.txt" For Append As #f
    Print #f, "appended"
    Close #f
    Open "native_test.txt" For Input As #f
    Do Until EOF(f)
        Line Input #f, line_
        Debug.Print "[" & line_ & "]"
    Loop
    Close #f
    Open "native_test.txt" For Input As #1
    Line Input #1, line_
    Line Input #1, line_
    Line Input #1, line_
    Input #1, a, b, c
    Debug.Print a; b; c
    Close #1
    Debug.Print Len(Dir("native_test.txt")) > 0, FileLen("native_test.txt") > 10
    Kill "native_test.txt"
    Debug.Print "[" & Dir("native_test.txt") & "]"
End Sub
"""),
    ("debugprint", """
Sub Main()
    Debug.Print "a", "b"; "c"
    Debug.Print "x";
    Debug.Print "y"
    Debug.Print 1; 2; -3
    Debug.Print "t"; Tab(10); "u"
    Debug.Print Spc(3); "v"
    Print "plain print"
End Sub
"""),
    ("implicit", """
Sub Main()
    x = 5
    y = x * 2
    s = "n=" & y
    Debug.Print s, x + y
End Sub
"""),
    ("withudt", """
Private Type Pt
    X As Double
    Y As Double
End Type
Private Function Dist(a As Pt, b As Pt) As Double
    Dist = Sqr((a.X - b.X) ^ 2 + (a.Y - b.Y) ^ 2)
End Function
Sub Main()
    Dim p As Pt, q As Pt
    p.X = 0: p.Y = 0
    With q
        .X = 3
        .Y = 4
    End With
    Debug.Print Dist(p, q)
End Sub
"""),
    ("module_vars", """
Private counter As Long
Public Total As Double
Dim names(1 To 3) As String

Private Sub Add(ByVal n As Long)
    counter = counter + n
    Total = Total + n / 2
End Sub

Sub Main()
    Add 3
    Add 4
    names(2) = "two"
    Debug.Print counter, Total, names(2), "[" & names(1) & "]"
End Sub
"""),
    ("like_strings", """
Sub Main()
    Debug.Print "abc" Like "a*", "abc" Like "a?c", "a1c" Like "a#c", "abc" Like "[a-c]bc", "xbc" Like "[!a]bc"
    Debug.Print "abc" Like "b*", "Hello" Like "H*o"
    Dim s As String
    s = "abcdef"
    Mid(s, 2, 3) = "XYZ"
    Debug.Print s
End Sub
"""),
    ("string_build", """
Sub Main()
    Dim i As Integer, s As String
    For i = 1 To 5
        s = s & CStr(i)
        If i < 5 Then s = s & ","
    Next
    Debug.Print s, Len(s)
    Dim parts() As String, k As Integer
    parts = Split(s, ",")
    For k = UBound(parts) To 0 Step -1
        Debug.Print parts(k);
    Next
    Debug.Print
    Debug.Print Join(parts, "+")
End Sub
"""),
    ("doloop_nested", """
Private Function IsPrime(ByVal n As Long) As Boolean
    Dim d As Long
    If n < 2 Then Exit Function
    For d = 2 To Int(Sqr(n))
        If n Mod d = 0 Then Exit Function
    Next
    IsPrime = True
End Function
Sub Main()
    Dim n As Long, out As String
    For n = 1 To 30
        If IsPrime(n) Then out = out & n & " "
    Next
    Debug.Print out
End Sub
"""),
    ("bubble", """
Sub Main()
    Dim a(1 To 6) As Integer, i As Integer, j As Integer, t As Integer
    a(1) = 5: a(2) = 3: a(3) = 9: a(4) = 1: a(5) = 7: a(6) = 2
    For i = 1 To 5
        For j = 1 To 6 - i
            If a(j) > a(j + 1) Then
                t = a(j): a(j) = a(j + 1): a(j + 1) = t
            End If
        Next
    Next
    For i = 1 To 6
        Debug.Print a(i);
    Next
    Debug.Print
End Sub
"""),
    ("static_vars", """
Private Function Counter() As Integer
    Static n As Integer
    n = n + 1
    Counter = n
End Function
Sub Main()
    Counter
    Counter
    Debug.Print Counter()
End Sub
"""),
    ("on_goto", """
Sub Main()
    Dim k As Integer
    For k = 1 To 3
        On k GoTo L1, L2, L3
L1:
        Debug.Print "one": GoTo Nxt
L2:
        Debug.Print "two": GoTo Nxt
L3:
        Debug.Print "three"
Nxt:
    Next
End Sub
"""),
    ("classes", """
Sub Main()
    Dim a As CCounter, b As CCounter
    Set a = New CCounter
    a.Name = "first"
    a.Add 5
    a.Add 7
    Debug.Print a.Name, a.Total, a.Count, a.Average
    Set b = a
    b.Add 3
    Debug.Print a.Total, (a Is b), (a Is Nothing)
    Set b = Nothing
    Debug.Print b Is Nothing, TypeName(a)
    Dim c As New CCounter
    c.Add 1
    Debug.Print c.Total, c.Describe()
    Dim col As New Collection, x As CCounter, k As Integer
    For k = 1 To 3
        Set x = New CCounter
        x.Add k * 10
        col.Add x
    Next
    For Each x In col
        Debug.Print x.Total;
    Next
    Debug.Print
    Debug.Print Biggest(a, c).Name
    On Error Resume Next
    Dim z As CCounter
    z.Add 1
    Debug.Print "err", Err.Number
End Sub

Private Function Biggest(p As CCounter, q As CCounter) As CCounter
    If p.Total >= q.Total Then Set Biggest = p Else Set Biggest = q
End Function
""", {"CCounter.cls": """
Option Explicit
Private mTotal As Double
Private mCount As Long
Private mName As String

Private Sub Class_Initialize()
    mName = "(unnamed)"
End Sub

Public Property Get Name() As String
    Name = mName
End Property

Public Property Let Name(ByVal v As String)
    mName = v
End Property

Public Property Get Total() As Double
    Total = mTotal
End Property

Public Property Get Count() As Long
    Count = mCount
End Property

Public Sub Add(ByVal n As Double)
    mTotal = mTotal + n
    mCount = mCount + 1
End Sub

Public Function Average() As Double
    If mCount = 0 Then Exit Function
    Average = mTotal / mCount
End Function

Public Function Describe() As String
    Describe = Me.Name & ": " & Total & " in " & Count
End Function
"""}),
    ("fixed_strings", """
Private Type Rec
    Code As String * 4
    Qty As Integer
End Type
Sub Main()
    Dim r As Rec, s As String * 6
    Debug.Print "[" & r.Code & "]", Len(r.Code)
    r.Code = "AB"
    Debug.Print "[" & r.Code & "]"
    r.Code = "ABCDEFG"
    Debug.Print "[" & r.Code & "]"
    s = "hi"
    Debug.Print "[" & s & "]", Len(s), "[" & Trim(s) & "]"
End Sub
"""),
]
