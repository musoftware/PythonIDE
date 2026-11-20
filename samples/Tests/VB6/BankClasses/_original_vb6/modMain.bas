Attribute VB_Name = "modMain"
Option Explicit

Private Type Txn
    AccountNo As String * 5
    Amount As Currency
    Kind As Integer        ' 1 = deposit, 2 = withdrawal
End Type

Private Bank As CBank

Sub Main()
    Dim a As CAccount, ok As Boolean, f As Integer, i As Integer
    Dim t As Txn, path As String, line As String, n As Long

    Set Bank = New CBank
    Bank.Open_ "Mahmoud", 500
    Bank.Open_ "Sara"
    Bank.Use "AC002"
    Bank("AC002").Deposit 120.5
    ok = Bank("AC002").Withdraw(200)
    Debug.Print "Withdraw 200 from AC002: "; ok
    Bank.AllowOverdraft = True
    ok = Bank("AC002").Withdraw(200)
    Debug.Print "With overdraft allowed: "; ok

    ' validation errors handled with On Error GoTo
    On Error GoTo BadInput
    Bank.Open_ "   "
    On Error GoTo 0

    For Each a In Bank
        Debug.Print a.Number, a, Format$(a.Balance, "#,##0.00")
    Next
    Debug.Print "Total: " & Format$(Bank.Total, "Currency")
    Debug.Print Bank.Log;

    ' save the transactions to a Random-access file and read them back
    path = App.Path & "\txns.dat"
    If Dir$(path) <> "" Then Kill path
    f = FreeFile
    Open path For Random As #f Len = Len(t)
    For i = 1 To 3
        t.AccountNo = "AC00" & ((i Mod 2) + 1)
        t.Amount = i * 10.25
        t.Kind = IIf(i = 2, 2, 1)
        Put #f, i, t
    Next
    Get #f, 2, t
    Debug.Print "Record 2: "; t.AccountNo; " "; Format$(t.Amount, "0.00"); " kind "; t.Kind
    Debug.Print "Records: "; LOF(f) \ Len(t)
    Close #f
    Kill path

    ' a text report
    Open App.Path & "\report.txt" For Output As #1
    Print #1, "Bank report"; Tab(20); Format$(Date, "yyyy")
    For Each a In Bank
        Write #1, a.Number, a.Owner, CDbl(a.Balance)
    Next
    Close #1
    Open App.Path & "\report.txt" For Input As #1
    Line Input #1, line
    Do Until EOF(1)
        Dim no As String, owner As String, bal As Double
        Input #1, no, owner, bal
        n = n + 1
    Loop
    Close #1
    Debug.Print "Report lines read back: " & n
    Kill App.Path & "\report.txt"

    ' GoSub (classic BASIC) and Win32 API
    Dim k As Integer, fact As Long
    fact = 1
    For k = 1 To 5
        GoSub Multiply
    Next
    Debug.Print "5! = " & fact
    Dim st As SYSTEMTIME
    GetLocalTime st
    Debug.Print "API year ok: " & (st.wYear = Year(Now))
    Debug.Print "Computer name length > 0: " & (Len(ComputerName()) > 0)
    Debug.Print "Temp folder ends with \: " & (Right$(TempFolder(), 1) = "\")
    Set Bank = Nothing
    Debug.Print "Done"
    Exit Sub

Multiply:
    fact = fact * k
    Return

BadInput:
    Debug.Print "Error " & (Err.Number - vbObjectError) & " in " & Err.Source & ": " & Err.Description
    Resume Next
End Sub
