Attribute VB_Name = "modFinance"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modFinance - connection, posting and interest rules of FinanceLedger (a savings & loan society).
'
' Every money movement is one row of the Ledger table (CR = money in, DR = money out) and changes the
' single row of the Cash table: cash payments move CashInHand, cheques move BankBalance.
' Interest on a member's savings = balance x days x rate / 365 / 100, the rate is tiered by days (Rates).
Option Explicit

Public cn As ADODB.Connection
Public gUser As String

Public Const CAT_SAVINGS As String = "Savings"
Public Const CAT_SHARE As String = "Share"
Public Const CAT_LOAN_ISSUE As String = "LoanIssue"
Public Const CAT_LOAN_REPAY As String = "LoanRepay"
Public Const CAT_INTEREST As String = "Interest"
Public Const CAT_INCOME As String = "Income"
Public Const CAT_EXPENSE As String = "Expense"

Public Sub OpenDb()
    Set cn = New ADODB.Connection
    cn.CursorLocation = adUseClient
    cn.Open "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=" & App.Path & "\finance.mdb"
End Sub

Public Function SqlText(ByVal s As String) As String
    SqlText = "'" & Replace(s, "'", "''") & "'"
End Function

Public Function SqlDate(ByVal d As Date) As String
    SqlDate = Format$(d, "\#yyyy-mm-dd\#")
End Function

' First value of a query (0 when it is Null)
Public Function ScalarValue(ByVal sql As String) As Variant
    Dim rs As New ADODB.Recordset
    rs.Open sql, cn, adOpenForwardOnly, adLockReadOnly
    ScalarValue = IIf(IsNull(rs(0).Value), 0, rs(0).Value)
    rs.Close
End Function

Public Function CashInHand() As Currency
    CashInHand = ScalarValue("SELECT CashInHand FROM Cash WHERE ID = 1")
End Function

Public Function BankBalance() As Currency
    BankBalance = ScalarValue("SELECT BankBalance FROM Cash WHERE ID = 1")
End Function

' Savings balance of one member (deposits - withdrawals - interest is added as CR too)
Public Function SavingsOf(ByVal MemberID As String) As Currency
    SavingsOf = ScalarValue("SELECT SUM(IIF(Direction = 'CR', Amount, -Amount)) FROM Ledger WHERE MemberID = " & _
                            SqlText(MemberID) & " AND Category IN ('" & CAT_SAVINGS & "', '" & CAT_INTEREST & "')")
End Function

' Tiered rate: the highest Rates row whose MinDays <= days
Public Function RateForDays(ByVal Days As Long) As Double
    RateForDays = ScalarValue("SELECT MAX(RatePct) FROM Rates WHERE MinDays <= " & Days)
End Function

Public Function InterestFor(ByVal Balance As Currency, ByVal Days As Long) As Currency
    InterestFor = Round(Balance * Days * RateForDays(Days) / 365 / 100, 2)
End Function

' Post one ledger row and move the cash/bank balance; returns False (with a message) when a cheque
' payment would overdraw the bank account or a cash payment exceeds the cash in hand.
Public Function PostEntry(ByVal EntryDate As Date, ByVal MemberID As String, ByVal Category As String, _
                          ByVal Direction As String, ByVal Amount As Currency, ByVal PayMode As String, _
                          ByVal Narration As String) As Boolean
    Dim rs As ADODB.Recordset, sign As Integer
    If Amount <= 0 Then
        MsgBox "The amount must be greater than zero.", vbExclamation
        Exit Function
    End If
    sign = IIf(Direction = "CR", 1, -1)
    ' the Cash row is changed in a batch-optimistic recordset and written with UpdateBatch
    Set rs = New ADODB.Recordset
    rs.Open "SELECT * FROM Cash WHERE ID = 1", cn, adOpenStatic, adLockBatchOptimistic
    With rs
        If PayMode = "Cheque" Then
            If sign < 0 And !BankBalance < Amount Then
                MsgBox "The bank balance (" & Format$(!BankBalance, "#,##0.00") & ") is too low for this cheque.", vbExclamation
                .Close
                Exit Function
            End If
            !BankBalance = !BankBalance + sign * Amount
        Else
            If sign < 0 And !CashInHand < Amount Then
                MsgBox "Only " & Format$(!CashInHand, "#,##0.00") & " cash in hand.", vbExclamation
                .Close
                Exit Function
            End If
            !CashInHand = !CashInHand + sign * Amount
        End If
        .UpdateBatch
        .Close
    End With
    cn.Execute "INSERT INTO Ledger (EntryDate, MemberID, Category, Direction, Amount, PayMode, Narration) VALUES (" & _
               SqlDate(EntryDate) & ", " & IIf(MemberID = "", "NULL", SqlText(MemberID)) & ", " & SqlText(Category) & _
               ", " & SqlText(Direction) & ", " & Str$(Amount) & ", " & SqlText(PayMode) & ", " & SqlText(Narration) & ")"
    PostEntry = True
End Function
