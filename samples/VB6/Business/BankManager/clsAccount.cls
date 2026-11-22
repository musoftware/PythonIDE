VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "clsAccount"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' clsAccount - the business rules of one bank account, kept out of the forms.
'   Dim acc As New clsAccount
'   If acc.OpenAccount(1001) Then acc.Deposit 250, "Cash", "counter"
' Withdraw refuses to go below the minimum balance (Settings table) and raises an error the
' caller traps with On Error.
Option Explicit

Public Enum TxnKind
    tkDeposit = 1
    tkWithdraw = 2
End Enum

Private Const ERR_LOW_BALANCE As Long = vbObjectError + 1001
Private Const ERR_BAD_AMOUNT As Long = vbObjectError + 1002

Private mAccountNo As Long
Private mName As String
Private mBalance As Currency
Private mLoaded As Boolean

Public Property Get AccountNo() As Long
    AccountNo = mAccountNo
End Property

Public Property Get HolderName() As String
    HolderName = mName
End Property

Public Property Get Balance() As Currency
    Balance = mBalance
End Property

Public Property Get IsLoaded() As Boolean
    IsLoaded = mLoaded
End Property

' Minimum balance a withdrawal must leave on the account
Public Property Get MinimumBalance() As Currency
    MinimumBalance = CCur(Val(AppSetting("MinBalance", "0")))
End Property

' Read the account from the Customers table; False when the number does not exist
Public Function OpenAccount(ByVal AccountNo As Long) As Boolean
    Dim rs As ADODB.Recordset
    Set rs = New ADODB.Recordset
    rs.Open "SELECT AccountNo, FullName, Balance FROM Customers WHERE AccountNo = " & AccountNo, _
            cn, adOpenStatic, adLockReadOnly
    mLoaded = Not rs.EOF
    If mLoaded Then
        mAccountNo = rs!AccountNo
        mName = rs!FullName & ""
        mBalance = rs!Balance
    End If
    rs.Close
    OpenAccount = mLoaded
End Function

Public Sub Deposit(ByVal Amount As Currency, ByVal Mode As String, ByVal Reference As String)
    Post tkDeposit, Amount, Mode, Reference
End Sub

Public Sub Withdraw(ByVal Amount As Currency, ByVal Mode As String, ByVal Reference As String)
    If mBalance - Amount < MinimumBalance Then
        Err.Raise ERR_LOW_BALANCE, "clsAccount", _
                  "Not enough balance: at least " & Format$(MinimumBalance, "#,##0.00") & " must stay on the account."
    End If
    Post tkWithdraw, Amount, Mode, Reference
End Sub

' Write the transaction row and the new balance in one database transaction
Private Sub Post(ByVal Kind As TxnKind, ByVal Amount As Currency, ByVal Mode As String, ByVal Reference As String)
    Dim newBalance As Currency
    If Not mLoaded Then Err.Raise ERR_BAD_AMOUNT, "clsAccount", "No account is loaded."
    If Amount <= 0 Then Err.Raise ERR_BAD_AMOUNT, "clsAccount", "The amount must be greater than zero."
    If Kind = tkDeposit Then newBalance = mBalance + Amount Else newBalance = mBalance - Amount
    cn.BeginTrans
    cn.Execute "INSERT INTO Transactions (AccountNo, TxnDate, TxnType, Amount, Mode, Reference) VALUES (" & _
               mAccountNo & ", " & D(Date) & ", " & Q(IIf(Kind = tkDeposit, "Deposit", "Withdraw")) & ", " & _
               Str$(Amount) & ", " & Q(Mode) & ", " & Q(Reference) & ")"
    cn.Execute "UPDATE Customers SET Balance = " & Str$(newBalance) & " WHERE AccountNo = " & mAccountNo
    cn.CommitTrans
    mBalance = newBalance
    LogActivity IIf(Kind = tkDeposit, "deposit ", "withdraw ") & mAccountNo & " " & Format$(Amount, "0.00")
End Sub
