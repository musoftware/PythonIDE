VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "CAccount"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

' A bank account with validation and events.
Public Event BalanceChanged(ByVal OldBalance As Currency, ByVal NewBalance As Currency)
Public Event Overdraft(ByVal Amount As Currency, Cancel As Boolean)

Private mNumber As String
Private mOwner As String
Private mBalance As Currency

Private Sub Class_Initialize()
    mBalance = 0
End Sub

Public Property Get Number() As String
    Number = mNumber
End Property

Public Property Let Number(ByVal Value As String)
    mNumber = Value
End Property

Public Property Get Owner() As String
Attribute Owner.VB_UserMemId = 0
    Owner = mOwner
End Property

Public Property Let Owner(ByVal Value As String)
    If Len(Trim$(Value)) = 0 Then
        Err.Raise vbObjectError + 1000, "CAccount.Owner", "Owner name is required"
    End If
    mOwner = Value
End Property

Public Property Get Balance() As Currency
    Balance = mBalance
End Property

Public Sub Deposit(ByVal Amount As Currency)
    If Amount <= 0 Then Err.Raise 5, "CAccount.Deposit", "Amount must be positive"
    SetBalance mBalance + Amount
End Sub

Public Function Withdraw(ByVal Amount As Currency) As Boolean
    Dim Cancel As Boolean
    If Amount > mBalance Then
        Cancel = True
        RaiseEvent Overdraft(Amount - mBalance, Cancel)
        If Cancel Then
            Withdraw = False
            Exit Function
        End If
    End If
    SetBalance mBalance - Amount
    Withdraw = True
End Function

Private Sub SetBalance(ByVal NewValue As Currency)
    Dim Old As Currency
    Old = mBalance
    mBalance = NewValue
    RaiseEvent BalanceChanged(Old, mBalance)
End Sub
