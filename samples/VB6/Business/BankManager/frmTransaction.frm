VERSION 5.00
Begin VB.Form frmTransaction
   Caption         =   "Deposit / Withdraw"
   ClientHeight    =   3960
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   5880
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   3960
   ScaleWidth      =   5880
   Begin VB.CommandButton cmdClose
      Caption         =   "&Close"
      Height          =   375
      Left            =   4440
      TabIndex        =   13
      Top             =   3420
      Width           =   1215
   End
   Begin VB.CommandButton cmdPost
      Caption         =   "&Post"
      Default         =   -1  'True
      Enabled         =   0   'False
      Height          =   375
      Left            =   3120
      TabIndex        =   12
      Top             =   3420
      Width           =   1215
   End
   Begin VB.Frame fraKind
      Caption         =   "Transaction"
      Height          =   1815
      Left            =   120
      TabIndex        =   4
      Top             =   1440
      Width           =   5535
      Begin VB.TextBox txtReference
         Height          =   315
         Left            =   3000
         TabIndex        =   11
         Top             =   1320
         Width           =   2295
      End
      Begin VB.CheckBox chkCheque
         Caption         =   "Paid by cheque, number / reference:"
         Height          =   255
         Left            =   120
         TabIndex        =   10
         Top             =   1350
         Width           =   2895
      End
      Begin VB.TextBox txtAmount
         Alignment       =   1  'Right Justify
         Height          =   315
         Left            =   3000
         TabIndex        =   9
         Top             =   780
         Width           =   2295
      End
      Begin VB.OptionButton optKind
         Caption         =   "&Withdraw"
         Height          =   255
         Index           =   1
         Left            =   1440
         TabIndex        =   6
         Top             =   360
         Width           =   1215
      End
      Begin VB.OptionButton optKind
         Caption         =   "&Deposit"
         Height          =   255
         Index           =   0
         Left            =   120
         TabIndex        =   5
         Top             =   360
         Value           =   -1  'True
         Width           =   1215
      End
      Begin VB.Label lblAmount
         Caption         =   "Amount:"
         Height          =   255
         Left            =   120
         TabIndex        =   8
         Top             =   840
         Width           =   2775
      End
   End
   Begin VB.CommandButton cmdLookup
      Caption         =   "&Look up"
      Height          =   315
      Left            =   3000
      TabIndex        =   2
      Top             =   240
      Width           =   1095
   End
   Begin VB.TextBox txtAccNo
      Height          =   315
      Left            =   1440
      TabIndex        =   1
      Top             =   240
      Width           =   1455
   End
   Begin VB.Label lblBalance
      Caption         =   "Balance: -"
      Height          =   255
      Left            =   1440
      TabIndex        =   7
      Top             =   1020
      Width           =   4215
   End
   Begin VB.Label lblHolder
      Caption         =   "-"
      BeginProperty Font
         Name            =   "MS Sans Serif"
         Size            =   9.75
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   255
      Left            =   1440
      TabIndex        =   3
      Top             =   690
      Width           =   4215
   End
   Begin VB.Label lblAccNo
      Caption         =   "Account no:"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   285
      Width           =   1215
   End
End
Attribute VB_Name = "frmTransaction"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmTransaction - MDI child: look an account up, pick Deposit or Withdraw (an OptionButton
' control array), type the amount and post it. The rules live in clsAccount; a refused withdrawal
' comes back as a trapped run-time error.
Option Explicit

Private mAccount As clsAccount

Private Sub Form_Load()
    Set mAccount = New clsAccount
    txtReference.Enabled = False
End Sub

Private Sub cmdLookup_Click()
    If Not IsNumeric(txtAccNo.Text) Then
        MsgBox "Type an account number.", vbExclamation, APP_TITLE
        Exit Sub
    End If
    If mAccount.OpenAccount(CLng(txtAccNo.Text)) Then
        ShowAccount
        cmdPost.Enabled = True
        txtAmount.SetFocus
    Else
        lblHolder.Caption = "(no such account)"
        lblBalance.Caption = "Balance: -"
        cmdPost.Enabled = False
    End If
End Sub

Private Sub ShowAccount()
    lblHolder.Caption = mAccount.HolderName
    lblBalance.Caption = "Balance: " & Format$(mAccount.Balance, "#,##0.00") & _
                         "   (minimum " & Format$(mAccount.MinimumBalance, "#,##0.00") & ")"
End Sub

Private Sub optKind_Click(Index As Integer)
    fraKind.Caption = IIf(Index = 0, "Deposit", "Withdraw")
End Sub

Private Sub chkCheque_Click()
    txtReference.Enabled = (chkCheque.Value = vbChecked)
End Sub

Private Sub txtAccNo_KeyPress(KeyAscii As Integer)
    KeyAscii = DigitsOnly(KeyAscii)
End Sub

Private Sub txtAmount_KeyPress(KeyAscii As Integer)
    KeyAscii = DigitsOnly(KeyAscii, True)
End Sub

Private Sub cmdPost_Click()
    Dim mode As String
    If Not IsNumeric(txtAmount.Text) Then
        MsgBox "Type the amount.", vbExclamation, APP_TITLE
        Exit Sub
    End If
    mode = IIf(chkCheque.Value = vbChecked, "Cheque", "Cash")
    On Error GoTo PostFailed
    If optKind(0).Value Then
        mAccount.Deposit CCur(txtAmount.Text), mode, txtReference.Text
    Else
        mAccount.Withdraw CCur(txtAmount.Text), mode, txtReference.Text
    End If
    On Error GoTo 0
    ShowAccount
    txtAmount.Text = ""
    mdiMain.sbMain.SimpleText = "Posted. New balance of " & mAccount.AccountNo & ": " & _
                                Format$(mAccount.Balance, "#,##0.00")
    ' keep the account list up to date when it is open
    If IsFormLoaded("frmCustomers") Then frmCustomers.LoadGrid
    Exit Sub
PostFailed:
    MsgBox Err.Description, vbExclamation, APP_TITLE
End Sub

Private Function IsFormLoaded(ByVal FormName As String) As Boolean
    Dim f As Form
    For Each f In Forms
        If StrComp(f.Name, FormName, vbTextCompare) = 0 Then IsFormLoaded = True
    Next
End Function

Private Sub cmdClose_Click()
    Unload Me
End Sub
