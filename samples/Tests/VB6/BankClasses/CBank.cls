VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "CBank"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

' A collection class: holds CAccount objects, listens to their events.
Private mAccounts As Collection
Private WithEvents mCurrent As CAccount
Attribute mCurrent.VB_VarHelpID = -1
Public AllowOverdraft As Boolean
Public Log As String

Private Sub Class_Initialize()
    Set mAccounts = New Collection
End Sub

Private Sub Class_Terminate()
    Debug.Print "Bank closed (" & mAccounts.Count & " accounts)"
End Sub

Public Function Open_(ByVal Owner As String, Optional ByVal Initial As Currency = 0) As CAccount
    Dim a As CAccount
    Set a = New CAccount
    a.Owner = Owner
    a.Number = "AC" & Format$(mAccounts.Count + 1, "000")
    mAccounts.Add a, a.Number
    Set mCurrent = a
    If Initial > 0 Then a.Deposit Initial
    Set Open_ = a
End Function

Public Sub Use(ByVal Number As String)
    Set mCurrent = mAccounts(Number)
End Sub

Public Property Get Item(ByVal Key As Variant) As CAccount
Attribute Item.VB_UserMemId = 0
    Set Item = mAccounts(Key)
End Property

Public Property Get Count() As Long
    Count = mAccounts.Count
End Property

Public Function NewEnum() As IUnknown
Attribute NewEnum.VB_UserMemId = -4
    Set NewEnum = mAccounts.[_NewEnum]
End Function

Public Function Total() As Currency
    Dim a As CAccount
    For Each a In mAccounts
        Total = Total + a.Balance
    Next
End Function

Private Sub mCurrent_BalanceChanged(ByVal OldBalance As Currency, ByVal NewBalance As Currency)
    Log = Log & mCurrent.Number & ": " & Format$(OldBalance, "0.00") & " -> " & Format$(NewBalance, "0.00") & vbCrLf
End Sub

Private Sub mCurrent_Overdraft(ByVal Amount As Currency, Cancel As Boolean)
    Log = Log & mCurrent.Number & ": overdraft of " & Format$(Amount, "0.00") & IIf(AllowOverdraft, " allowed", " refused") & vbCrLf
    Cancel = Not AllowOverdraft
End Sub
