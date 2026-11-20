Attribute VB_Name = "Main"
Option Explicit

Private Type Product
    Code As String * 6
    Name As String * 20
    Price As Double
    Stock As Integer
End Type

Private WithEvents Tally As CTally
Private Ticks As Long

Sub Main()
    Dim f As Integer, i As Integer, p As Product, path As String, total As Double
    Dim c As New Collection, v As Variant

    ' --- GoSub / Return and On ... GoSub (classic BASIC)
    For i = 1 To 3
        On i GoSub Red, Green, Blue
    Next
    Debug.Print

    ' --- Static variables and named / optional arguments
    Debug.Print NextId(), NextId(), NextId()
    Debug.Print Price(100), Price(100, Discount:=0.25), Price(Amount:=80, Tax:=0)

    ' --- Format$
    Debug.Print Format$(1234567.891, "#,##0.00"), Format$(0.075, "0.0%"), Format$(-42, "0;(0)")
    Debug.Print Format$(DateSerial(2026, 1, 15), "dddd d mmmm yyyy"), Format$("abc", ">")

    ' --- Collection with keys, Before/After
    c.Add "Cairo", "EG"
    c.Add "Rome", "IT"
    c.Add "Tokyo", "JP", Before:="IT"
    For Each v In c
        Debug.Print v;
        Debug.Print " ";
    Next
    Debug.Print "| " & c("JP")

    ' --- a class with a Dictionary and an event
    Set Tally = New CTally
    Tally.AddText "the cat and the dog and THE bird"
    Debug.Print "the=" & Tally("the"), "and=" & Tally.Count("and"), "words=" & Join(Tally.Words, ","), "ticks=" & Ticks

    ' --- Type with fixed-length strings in a Random-access file
    path = App.Path & "\products.dat"
    f = FreeFile
    Open path For Random As #f Len = Len(p)
    For i = 1 To 3
        p.Code = "P" & Format$(i, "000")
        p.Name = Choose(i, "Keyboard", "Mouse", "Monitor")
        p.Price = Choose(i, 25.5, 9.99, 189)
        p.Stock = i * 4
        Put #f, i, p
    Next
    For i = 1 To LOF(f) \ Len(p)
        Get #f, i, p
        total = total + p.Price * p.Stock
        Debug.Print Trim$(p.Code), Trim$(p.Name), Format$(p.Price, "0.00")
    Next
    Close #f
    Kill path
    Debug.Print "Stock value: " & Format$(total, "Standard")

    ' --- text files and error handling
    On Error GoTo FileError
    Open App.Path & "\does-not-exist.txt" For Input As #1
    Debug.Print "not reached"
    Exit Sub

FileError:
    Debug.Print "Error " & Err.Number & ": " & Err.Description
    Exit Sub

Red:
    Debug.Print "red ";
    Return
Green:
    Debug.Print "green ";
    Return
Blue:
    Debug.Print "blue";
    Return
End Sub

Private Function NextId() As Long
    Static id As Long
    id = id + 1
    NextId = id
End Function

Private Function Price(ByVal Amount As Double, Optional ByVal Discount As Double = 0, Optional ByVal Tax As Double = 0.14) As String
    Price = Format$(Amount * (1 - Discount) * (1 + Tax), "0.00")
End Function

Private Sub Tally_Progress(ByVal Done As Long, ByVal Total As Long)
    Ticks = Ticks + 1
End Sub
