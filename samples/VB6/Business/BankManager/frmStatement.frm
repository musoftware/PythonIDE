VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Begin VB.Form frmStatement
   Caption         =   "Account statement"
   ClientHeight    =   5400
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   8400
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   5400
   ScaleWidth      =   8400
   Begin VB.CommandButton cmdExport
      Caption         =   "&Export to text file"
      Enabled         =   0   'False
      Height          =   375
      Left            =   6360
      TabIndex        =   8
      Top             =   4920
      Width           =   1935
   End
   Begin VB.CommandButton cmdShow
      Caption         =   "&Show"
      Default         =   -1  'True
      Height          =   315
      Left            =   7080
      TabIndex        =   6
      Top             =   240
      Width           =   1215
   End
   Begin VB.TextBox txtAccNo
      Height          =   315
      Left            =   1200
      TabIndex        =   1
      Text            =   "1001"
      Top             =   240
      Width           =   1095
   End
   Begin MSComCtl2.DTPicker dtpFrom
      Height          =   315
      Left            =   2880
      TabIndex        =   3
      Top             =   240
      Width           =   1575
      _ExtentX        =   2778
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   45658
   End
   Begin MSComCtl2.DTPicker dtpTo
      Height          =   315
      Left            =   5040
      TabIndex        =   5
      Top             =   240
      Width           =   1575
      _ExtentX        =   2778
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   46387
   End
   Begin MSComctlLib.ListView lvwTxn
      Height          =   4095
      Left            =   120
      TabIndex        =   7
      Top             =   720
      Width           =   8175
      _ExtentX        =   14420
      _ExtentY        =   7223
      View            =   3
      LabelEdit       =   1
      FullRowSelect   =   -1  'True
      GridLines       =   -1  'True
      _Version        =   393217
      ForeColor       =   -2147483640
      BackColor       =   -2147483643
      BorderStyle     =   1
      Appearance      =   1
      NumItems        =   5
      BeginProperty ColumnHeader(1) {BDD1F052-858B-11D1-B16A-00C0F0283628}
         Text            =   "Date"
         Object.Width           =   2117
      EndProperty
      BeginProperty ColumnHeader(2) {BDD1F052-858B-11D1-B16A-00C0F0283628}
         SubItemIndex    =   1
         Text            =   "Type"
         Object.Width           =   1764
      EndProperty
      BeginProperty ColumnHeader(3) {BDD1F052-858B-11D1-B16A-00C0F0283628}
         Alignment       =   1
         SubItemIndex    =   2
         Text            =   "Amount"
         Object.Width           =   2117
      EndProperty
      BeginProperty ColumnHeader(4) {BDD1F052-858B-11D1-B16A-00C0F0283628}
         SubItemIndex    =   3
         Text            =   "Mode"
         Object.Width           =   1764
      EndProperty
      BeginProperty ColumnHeader(5) {BDD1F052-858B-11D1-B16A-00C0F0283628}
         SubItemIndex    =   4
         Text            =   "Reference"
         Object.Width           =   4410
      EndProperty
   End
   Begin VB.Label lblTotals
      Caption         =   "-"
      Height          =   255
      Left            =   120
      TabIndex        =   9
      Top             =   4980
      Width           =   6135
   End
   Begin VB.Label lblTo
      Caption         =   "To:"
      Height          =   255
      Left            =   4560
      TabIndex        =   4
      Top             =   285
      Width           =   435
   End
   Begin VB.Label lblFrom
      Caption         =   "From:"
      Height          =   255
      Left            =   2400
      TabIndex        =   2
      Top             =   285
      Width           =   495
   End
   Begin VB.Label lblAccNo
      Caption         =   "Account:"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   285
      Width           =   1035
   End
End
Attribute VB_Name = "frmStatement"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmStatement - MDI child: the transactions of one account between two dates (DTPicker) in a
' report-style ListView, the totals, and an export to a fixed-width text file (Open / Print #).
Option Explicit

Private mDeposits As Currency, mWithdrawals As Currency

Private Sub Form_Load()
    dtpFrom.Value = DateSerial(Year(Date) - 1, 1, 1)
    dtpTo.Value = Date
End Sub

Private Sub cmdShow_Click()
    Dim rs As ADODB.Recordset, li As ListItem
    If dtpFrom.Value > dtpTo.Value Then
        MsgBox "The start date is after the end date.", vbExclamation, APP_TITLE
        Exit Sub
    End If
    lvwTxn.ListItems.Clear
    mDeposits = 0: mWithdrawals = 0
    Set rs = New ADODB.Recordset
    rs.Open "SELECT TxnDate, TxnType, Amount, Mode, Reference FROM Transactions WHERE AccountNo = " & _
            Val(txtAccNo.Text) & " AND TxnDate BETWEEN " & D(dtpFrom.Value) & " AND " & D(dtpTo.Value) & _
            " ORDER BY TxnDate, TxnID", cn, adOpenStatic, adLockReadOnly
    Do Until rs.EOF
        Set li = lvwTxn.ListItems.Add(, , Format$(rs!TxnDate, "yyyy-mm-dd"))
        li.SubItems(1) = rs!TxnType
        li.SubItems(2) = Format$(rs!Amount, "#,##0.00")
        li.SubItems(3) = rs!Mode & ""
        li.SubItems(4) = rs!Reference & ""
        If rs!TxnType = "Deposit" Then
            mDeposits = mDeposits + rs!Amount
        Else
            mWithdrawals = mWithdrawals + rs!Amount
        End If
        rs.MoveNext
    Loop
    rs.Close
    lblTotals.Caption = lvwTxn.ListItems.Count & " transactions   deposits " & Format$(mDeposits, "#,##0.00") & _
                        "   withdrawals " & Format$(mWithdrawals, "#,##0.00") & _
                        "   net " & Format$(mDeposits - mWithdrawals, "#,##0.00")
    cmdExport.Enabled = (lvwTxn.ListItems.Count > 0)
End Sub

' Write the statement as a text file; returns its path
Public Function ExportStatement() As String
    Dim f As Integer, i As Integer, path As String
    path = App.Path & "\statement_" & Val(txtAccNo.Text) & ".txt"
    f = FreeFile
    Open path For Output As #f
    Print #f, AppSetting("BankName", APP_TITLE)
    Print #f, "Statement of account " & txtAccNo.Text & "  " & Format$(dtpFrom.Value, "yyyy-mm-dd") & _
              " to " & Format$(dtpTo.Value, "yyyy-mm-dd")
    Print #f, String$(60, "-")
    For i = 1 To lvwTxn.ListItems.Count
        With lvwTxn.ListItems(i)
            Print #f, .Text; Tab(14); .SubItems(1); Tab(26); Right$(Space$(12) & .SubItems(2), 12); _
                      Tab(42); .SubItems(4)
        End With
    Next
    Print #f, String$(60, "-")
    Print #f, lblTotals.Caption
    Close #f
    ExportStatement = path
End Function

Private Sub cmdExport_Click()
    MsgBox "Saved to " & ExportStatement(), vbInformation, APP_TITLE
End Sub
