VERSION 5.00
Object = "{BDC217C8-ED16-11CD-956C-0000C04E4C0A}#1.1#0"; "TABCTL32.OCX"
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Begin VB.Form frmLedger
   Caption         =   "FinanceLedger"
   ClientHeight    =   6600
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   9600
   LinkTopic       =   "Form1"
   ScaleHeight     =   6600
   ScaleWidth      =   9600
   StartUpPosition =   2  'CenterScreen
   Begin TabDlg.SSTab tabMain
      Height          =   6015
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   9375
      _ExtentX        =   16536
      _ExtentY        =   10610
      _Version        =   393216
      Tabs            =   6
      Tab             =   0
      TabsPerRow      =   6
      TabHeight       =   520
      TabCaption(0)   =   "Members"
      TabPicture(0)   =   ""
      Tab(0).ControlEnabled=   -1  'True
      Tab(0).Control(0)=   "lstMembers"
      Tab(0).Control(1)=   "lblMemberInfo"
      Tab(0).Control(2)=   "cmdAddMember"
      Tab(0).Control(3)=   "cmdToggleMember"
      Tab(0).ControlCount=   4
      TabCaption(1)   =   "Vouchers"
      TabPicture(1)   =   ""
      Tab(1).ControlEnabled=   0   'False
      Tab(1).Control(0)=   "fraVoucher"
      Tab(1).Control(1)=   "lblCash"
      Tab(1).ControlCount=   2
      TabCaption(2)   =   "Loans"
      TabPicture(2)   =   ""
      Tab(2).ControlEnabled=   0   'False
      Tab(2).Control(0)=   "grdLoans"
      Tab(2).Control(1)=   "fraLoan"
      Tab(2).Control(2)=   "cmdRepay"
      Tab(2).ControlCount=   3
      TabCaption(3)   =   "Interest"
      TabPicture(3)   =   ""
      Tab(3).ControlEnabled=   0   'False
      Tab(3).Control(0)=   "fraInterest"
      Tab(3).ControlCount=   1
      TabCaption(4)   =   "Day book"
      TabPicture(4)   =   ""
      Tab(4).ControlEnabled=   0   'False
      Tab(4).Control(0)=   "dtpDay"
      Tab(4).Control(1)=   "cmdDayBook"
      Tab(4).Control(2)=   "grdDayBook"
      Tab(4).Control(3)=   "lblDayTotals"
      Tab(4).Control(4)=   "chkAllDays"
      Tab(4).ControlCount=   5
      TabCaption(5)   =   "Profit && loss"
      TabPicture(5)   =   ""
      Tab(5).ControlEnabled=   0   'False
      Tab(5).Control(0)=   "lblPL(0)"
      Tab(5).Control(1)=   "lblPL(1)"
      Tab(5).Control(2)=   "lblPL(2)"
      Tab(5).Control(3)=   "lblPL(3)"
      Tab(5).Control(4)=   "shpNet"
      Tab(5).ControlCount=   5
      Begin VB.ListBox lstMembers
         Height          =   4740
         Left            =   240
         TabIndex        =   1
         Top             =   600
         Width           =   4215
      End
      Begin VB.CommandButton cmdAddMember
         Caption         =   "&Add member..."
         Height          =   375
         Left            =   4680
         TabIndex        =   2
         Top             =   4920
         Width           =   1695
      End
      Begin VB.CommandButton cmdToggleMember
         Caption         =   "Activate / deactivate"
         Height          =   375
         Left            =   6480
         TabIndex        =   3
         Top             =   4920
         Width           =   2535
      End
      Begin VB.Frame fraVoucher
         Caption         =   "New voucher"
         Height          =   3975
         Left            =   -74760
         TabIndex        =   4
         Top             =   600
         Width           =   8775
         Begin VB.CommandButton cmdPost
            Caption         =   "&Post voucher"
            Height          =   375
            Left            =   6960
            TabIndex        =   18
            Top             =   3360
            Width           =   1575
         End
         Begin VB.TextBox txtNarration
            Height          =   315
            Left            =   1680
            TabIndex        =   17
            Top             =   2880
            Width           =   6855
         End
         Begin VB.TextBox txtAmount
            Alignment       =   1  'Right Justify
            Height          =   315
            Left            =   1680
            TabIndex        =   15
            Top             =   2400
            Width           =   1695
         End
         Begin VB.OptionButton optMode
            Caption         =   "Cheque (bank)"
            Height          =   255
            Index           =   1
            Left            =   3240
            TabIndex        =   13
            Top             =   1980
            Width           =   1695
         End
         Begin VB.OptionButton optMode
            Caption         =   "Cash"
            Height          =   255
            Index           =   0
            Left            =   1680
            TabIndex        =   12
            Top             =   1980
            Value           =   -1  'True
            Width           =   1335
         End
         Begin VB.ComboBox cboCategory
            Height          =   315
            Left            =   1680
            Style           =   2  'Dropdown List
            TabIndex        =   10
            Top             =   1440
            Width           =   3135
         End
         Begin VB.ComboBox cboMember
            Height          =   315
            Left            =   1680
            Style           =   2  'Dropdown List
            TabIndex        =   8
            Top             =   900
            Width           =   4335
         End
         Begin MSComCtl2.DTPicker dtpEntry
            Height          =   315
            Left            =   1680
            TabIndex        =   6
            Top             =   360
            Width           =   1815
            _ExtentX        =   3201
            _ExtentY        =   556
            _Version        =   393216
            Format          =   20512769
            CurrentDate     =   46023
         End
         Begin VB.Label lblNarration
            Caption         =   "Narration:"
            Height          =   255
            Left            =   240
            TabIndex        =   16
            Top             =   2940
            Width           =   1335
         End
         Begin VB.Label lblAmount
            Caption         =   "Amount:"
            Height          =   255
            Left            =   240
            TabIndex        =   14
            Top             =   2460
            Width           =   1335
         End
         Begin VB.Label lblMode
            Caption         =   "Paid by:"
            Height          =   255
            Left            =   240
            TabIndex        =   11
            Top             =   1980
            Width           =   1335
         End
         Begin VB.Label lblCategory
            Caption         =   "Kind:"
            Height          =   255
            Left            =   240
            TabIndex        =   9
            Top             =   1500
            Width           =   1335
         End
         Begin VB.Label lblMember
            Caption         =   "Member:"
            Height          =   255
            Left            =   240
            TabIndex        =   7
            Top             =   960
            Width           =   1335
         End
         Begin VB.Label lblEntryDate
            Caption         =   "Date:"
            Height          =   255
            Left            =   240
            TabIndex        =   5
            Top             =   420
            Width           =   1335
         End
      End
      Begin MSFlexGridLib.MSFlexGrid grdLoans
         Height          =   2535
         Left            =   -74760
         TabIndex        =   20
         Top             =   600
         Width           =   8775
         _ExtentX        =   15478
         _ExtentY        =   4471
         _Version        =   393216
         Rows            =   1
         Cols            =   7
         FixedCols       =   0
         SelectionMode   =   1
         FormatString    =   "^Loan|<Member|<Issued|>Principal|>Rate %|>Repaid|>Outstanding"
      End
      Begin VB.Frame fraLoan
         Caption         =   "Issue a loan (needs savings of at least 20% of the amount)"
         Height          =   1335
         Left            =   -74760
         TabIndex        =   21
         Top             =   3240
         Width           =   8775
         Begin VB.CommandButton cmdIssue
            Caption         =   "&Issue"
            Height          =   375
            Left            =   7320
            TabIndex        =   28
            Top             =   780
            Width           =   1215
         End
         Begin VB.TextBox txtRate
            Alignment       =   1  'Right Justify
            Height          =   315
            Left            =   5640
            TabIndex        =   27
            Text            =   "12"
            Top             =   840
            Width           =   735
         End
         Begin VB.TextBox txtPrincipal
            Alignment       =   1  'Right Justify
            Height          =   315
            Left            =   1680
            TabIndex        =   25
            Top             =   840
            Width           =   1695
         End
         Begin VB.ComboBox cboLoanMember
            Height          =   315
            Left            =   1680
            Style           =   2  'Dropdown List
            TabIndex        =   23
            Top             =   360
            Width           =   4695
         End
         Begin VB.Label lblRate
            Caption         =   "Rate % / year:"
            Height          =   255
            Left            =   4200
            TabIndex        =   26
            Top             =   900
            Width           =   1335
         End
         Begin VB.Label lblPrincipal
            Caption         =   "Amount:"
            Height          =   255
            Left            =   240
            TabIndex        =   24
            Top             =   900
            Width           =   1335
         End
         Begin VB.Label lblLoanMember
            Caption         =   "Member:"
            Height          =   255
            Left            =   240
            TabIndex        =   22
            Top             =   420
            Width           =   1335
         End
      End
      Begin VB.CommandButton cmdRepay
         Caption         =   "&Repayment for the selected loan..."
         Height          =   375
         Left            =   -74760
         TabIndex        =   29
         Top             =   4800
         Width           =   3255
      End
      Begin VB.Frame fraInterest
         Caption         =   "Interest on savings"
         Height          =   3135
         Left            =   -74760
         TabIndex        =   30
         Top             =   600
         Width           =   8775
         Begin VB.CommandButton cmdPayInterest
            Caption         =   "&Credit interest"
            Enabled         =   0   'False
            Height          =   375
            Left            =   6840
            TabIndex        =   37
            Top             =   2520
            Width           =   1695
         End
         Begin VB.CommandButton cmdCalcInterest
            Caption         =   "&Calculate"
            Height          =   375
            Left            =   5040
            TabIndex        =   36
            Top             =   2520
            Width           =   1695
         End
         Begin VB.ComboBox cboIntMember
            Height          =   315
            Left            =   1680
            Style           =   2  'Dropdown List
            TabIndex        =   32
            Top             =   360
            Width           =   4695
         End
         Begin MSComCtl2.DTPicker dtpSince
            Height          =   315
            Left            =   1680
            TabIndex        =   34
            Top             =   900
            Width           =   1815
            _ExtentX        =   3201
            _ExtentY        =   556
            _Version        =   393216
            Format          =   20512769
            CurrentDate     =   45658
         End
         Begin VB.Label lblIntResult
            Caption         =   "-"
            Height          =   975
            Left            =   240
            TabIndex        =   35
            Top             =   1440
            Width           =   8295
         End
         Begin VB.Label lblSince
            Caption         =   "Since:"
            Height          =   255
            Left            =   240
            TabIndex        =   33
            Top             =   960
            Width           =   1335
         End
         Begin VB.Label lblIntMember
            Caption         =   "Member:"
            Height          =   255
            Left            =   240
            TabIndex        =   31
            Top             =   420
            Width           =   1335
         End
      End
      Begin MSComCtl2.DTPicker dtpDay
         Height          =   315
         Left            =   -74760
         TabIndex        =   38
         Top             =   600
         Width           =   1815
         _ExtentX        =   3201
         _ExtentY        =   556
         _Version        =   393216
         Format          =   20512769
         CurrentDate     =   46023
      End
      Begin VB.CheckBox chkAllDays
         Caption         =   "All days"
         Height          =   255
         Left            =   -72720
         TabIndex        =   39
         Top             =   630
         Width           =   1215
      End
      Begin VB.CommandButton cmdDayBook
         Caption         =   "&Show"
         Height          =   315
         Left            =   -71400
         TabIndex        =   40
         Top             =   600
         Width           =   1095
      End
      Begin MSFlexGridLib.MSFlexGrid grdDayBook
         Height          =   3975
         Left            =   -74760
         TabIndex        =   41
         Top             =   1080
         Width           =   8775
         _ExtentX        =   15478
         _ExtentY        =   7011
         _Version        =   393216
         Rows            =   1
         Cols            =   5
         FixedCols       =   0
         FormatString    =   "<Date|<Member|<Narration|>Debit (out)|>Credit (in)"
      End
      Begin VB.Label lblDayTotals
         Caption         =   "-"
         Height          =   255
         Left            =   -74760
         TabIndex        =   42
         Top             =   5160
         Width           =   8775
      End
      Begin VB.Shape shpNet
         BackColor       =   &H00C0FFC0&
         BackStyle       =   1  'Opaque
         Height          =   615
         Left            =   -74760
         Shape           =   4  'Rounded Rectangle
         Top             =   2400
         Width           =   8775
      End
      Begin VB.Label lblPL
         BackStyle       =   0  'Transparent
         Caption         =   "-"
         BeginProperty Font
            Name            =   "MS Sans Serif"
            Size            =   12
            Charset         =   0
            Weight          =   700
            Underline       =   0   'False
            Italic          =   0   'False
            Strikethrough   =   0   'False
         EndProperty
         Height          =   375
         Index           =   3
         Left            =   -74520
         TabIndex        =   46
         Top             =   2520
         Width           =   8295
      End
      Begin VB.Label lblPL
         Caption         =   "-"
         Height          =   255
         Index           =   2
         Left            =   -74760
         TabIndex        =   45
         Top             =   1680
         Width           =   8775
      End
      Begin VB.Label lblPL
         Caption         =   "-"
         Height          =   255
         Index           =   1
         Left            =   -74760
         TabIndex        =   44
         Top             =   1200
         Width           =   8775
      End
      Begin VB.Label lblPL
         Caption         =   "-"
         Height          =   255
         Index           =   0
         Left            =   -74760
         TabIndex        =   43
         Top             =   720
         Width           =   8775
      End
      Begin VB.Label lblCash
         Caption         =   "-"
         Height          =   255
         Left            =   -74760
         TabIndex        =   19
         Top             =   4800
         Width           =   8775
      End
      Begin VB.Label lblMemberInfo
         Caption         =   "Click a member."
         Height          =   2535
         Left            =   4680
         TabIndex        =   47
         Top             =   600
         Width           =   4335
      End
   End
   Begin VB.Label lblStatus
      Caption         =   "-"
      Height          =   255
      Left            =   120
      TabIndex        =   48
      Top             =   6240
      Width           =   9375
   End
End
Attribute VB_Name = "frmLedger"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmLedger - the whole society on one SSTab:
'   Members   ListBox of members, details, add (modal frmMember) and (de)activate
'   Vouchers  savings deposit / withdrawal, share capital, income, expense - cash or cheque
'   Loans     MSFlexGrid of loans, issue (savings rule), repayment (InputBox)
'   Interest  tiered savings interest for a period, credited as a voucher
'   Day book  every ledger row of a day as debit / credit columns, with totals
'   P && L    income against expenses, recalculated whenever the tab is opened
Option Explicit

Private Sub Form_Load()
    cboCategory.AddItem "Savings deposit"
    cboCategory.AddItem "Savings withdrawal"
    cboCategory.AddItem "Share capital"
    cboCategory.AddItem "Income"
    cboCategory.AddItem "Expense"
    cboCategory.ListIndex = 0
    dtpEntry.Value = Date
    dtpDay.Value = Date
    dtpSince.Value = DateAdd("m", -6, Date)
    LoadMembers
    LoadLoans
    ShowCash
End Sub

' ------------------------------------------------------------------------------------------ members
Public Sub LoadMembers()
    Dim rs As New ADODB.Recordset, item As String
    lstMembers.Clear
    cboMember.Clear
    cboLoanMember.Clear
    cboIntMember.Clear
    cboMember.AddItem "(none - society)"
    rs.Open "SELECT MemberID, FullName, Active FROM Members ORDER BY MemberID", cn, adOpenStatic, adLockReadOnly
    Do While Not rs.EOF
        item = rs!MemberID & "  " & rs!FullName
        lstMembers.AddItem item & IIf(rs!Active, "", "  [inactive]")
        If rs!Active Then
            cboMember.AddItem item
            cboLoanMember.AddItem item
            cboIntMember.AddItem item
        End If
        rs.MoveNext
    Loop
    rs.Close
    cboMember.ListIndex = 0
    If cboLoanMember.ListCount > 0 Then cboLoanMember.ListIndex = 0
    If cboIntMember.ListCount > 0 Then cboIntMember.ListIndex = 0
End Sub

' "S-0001  Laila Hassan" -> "S-0001"
Private Function IdOf(ByVal item As String) As String
    If Left$(item, 1) <> "(" Then IdOf = Trim$(Left$(item, InStr(item, " ") - 1))
End Function

Private Sub lstMembers_Click()
    Dim id As String, rs As New ADODB.Recordset
    id = IdOf(lstMembers.Text)
    rs.Open "SELECT * FROM Members WHERE MemberID = " & SqlText(id), cn, adOpenStatic, adLockReadOnly
    With rs
        lblMemberInfo.Caption = !FullName & vbCrLf & "Account: " & !AccType & vbCrLf & _
            "Joined: " & Format$(!Joined, "d mmm yyyy") & vbCrLf & _
            "Entry fee: " & Format$(!EntryFee, "#,##0.00") & vbCrLf & _
            "Savings: " & Format$(SavingsOf(id), "#,##0.00") & vbCrLf & _
            "Status: " & IIf(!Active, "active", "inactive")
        .Close
    End With
End Sub

Private Sub cmdAddMember_Click()
    frmMember.Show vbModal, Me
End Sub

Private Sub cmdToggleMember_Click()
    Dim id As String
    If lstMembers.ListIndex < 0 Then Exit Sub
    id = IdOf(lstMembers.Text)
    cn.Execute "UPDATE Members SET Active = NOT Active WHERE MemberID = " & SqlText(id)
    LoadMembers
End Sub

' ------------------------------------------------------------------------------------------ vouchers
Private Sub ShowCash()
    lblCash.Caption = "Cash in hand: " & Format$(CashInHand(), "#,##0.00") & "      Bank: " & _
                      Format$(BankBalance(), "#,##0.00")
    lblStatus.Caption = "User " & gUser & "  |  " & lblCash.Caption
End Sub

Private Sub txtAmount_KeyPress(KeyAscii As Integer)
    If InStr("0123456789." & Chr$(8), Chr$(KeyAscii)) = 0 Then KeyAscii = 0
End Sub

Private Sub cmdPost_Click()
    Dim cat As String, dir As String, member As String, mode As String
    If Not IsNumeric(txtAmount.Text) Then
        MsgBox "Type the amount.", vbExclamation
        Exit Sub
    End If
    member = IdOf(cboMember.Text)
    Select Case cboCategory.ListIndex
        Case 0: cat = CAT_SAVINGS: dir = "CR"
        Case 1: cat = CAT_SAVINGS: dir = "DR"
        Case 2: cat = CAT_SHARE: dir = "CR"
        Case 3: cat = CAT_INCOME: dir = "CR"
        Case 4: cat = CAT_EXPENSE: dir = "DR"
    End Select
    If (cat = CAT_SAVINGS Or cat = CAT_SHARE) And member = "" Then
        MsgBox "Choose the member.", vbExclamation
        Exit Sub
    End If
    If cboCategory.ListIndex = 1 Then
        If SavingsOf(member) < CCur(txtAmount.Text) Then
            MsgBox "The member has only " & Format$(SavingsOf(member), "#,##0.00") & " savings.", vbExclamation
            Exit Sub
        End If
    End If
    mode = IIf(optMode(1).Value, "Cheque", "Cash")
    If PostEntry(dtpEntry.Value, member, cat, dir, CCur(txtAmount.Text), mode, txtNarration.Text) Then
        txtAmount.Text = ""
        txtNarration.Text = ""
        ShowCash
    End If
End Sub

' ------------------------------------------------------------------------------------------ loans
Public Sub LoadLoans()
    Dim rs As New ADODB.Recordset
    grdLoans.Rows = 1
    rs.Open "SELECT LoanID, MemberID, IssueDate, Principal, RatePct, Repaid FROM Loans WHERE NOT Closed ORDER BY LoanID", _
            cn, adOpenStatic, adLockReadOnly
    Do Until rs.EOF
        grdLoans.AddItem rs!LoanID & vbTab & rs!MemberID & vbTab & Format$(rs!IssueDate, "yyyy-mm-dd") & vbTab & _
                         Format$(rs!Principal, "#,##0.00") & vbTab & rs!RatePct & vbTab & _
                         Format$(rs!Repaid, "#,##0.00") & vbTab & Format$(rs!Principal - rs!Repaid, "#,##0.00")
        rs.MoveNext
    Loop
    rs.Close
End Sub

Private Sub cmdIssue_Click()
    Dim member As String, amount As Currency
    member = IdOf(cboLoanMember.Text)
    If Not IsNumeric(txtPrincipal.Text) Or Not IsNumeric(txtRate.Text) Then
        MsgBox "Type the amount and the rate.", vbExclamation
        Exit Sub
    End If
    amount = CCur(txtPrincipal.Text)
    If SavingsOf(member) < amount * 0.2 Then
        MsgBox "A loan of " & Format$(amount, "#,##0.00") & " needs savings of at least " & _
               Format$(amount * 0.2, "#,##0.00") & ".", vbExclamation
        Exit Sub
    End If
    If Not PostEntry(Date, member, CAT_LOAN_ISSUE, "DR", amount, "Cash", "Loan issued") Then Exit Sub
    cn.Execute "INSERT INTO Loans (MemberID, IssueDate, Principal, RatePct, Repaid, Closed) VALUES (" & _
               SqlText(member) & ", " & SqlDate(Date) & ", " & Str$(amount) & ", " & Val(txtRate.Text) & ", 0, False)"
    txtPrincipal.Text = ""
    LoadLoans
    ShowCash
End Sub

Private Sub cmdRepay_Click()
    Dim r As Long, id As Long, s As String, outstanding As Currency
    r = grdLoans.Row
    If r < 1 Then
        MsgBox "Select a loan in the grid first.", vbInformation
        Exit Sub
    End If
    id = Val(grdLoans.TextMatrix(r, 0))
    outstanding = CCur(grdLoans.TextMatrix(r, 6))
    s = InputBox("Repayment for loan " & id & " (outstanding " & Format$(outstanding, "#,##0.00") & "):", _
                 "Repayment", Format$(outstanding, "0.00"))
    If s = "" Or Not IsNumeric(s) Then Exit Sub
    If CCur(s) > outstanding Then
        MsgBox "That is more than the outstanding amount.", vbExclamation
        Exit Sub
    End If
    If Not PostEntry(Date, grdLoans.TextMatrix(r, 1), CAT_LOAN_REPAY, "CR", CCur(s), "Cash", "Loan " & id & " repayment") Then Exit Sub
    cn.Execute "UPDATE Loans SET Repaid = Repaid + " & Str$(CCur(s)) & ", Closed = (Repaid + " & Str$(CCur(s)) & _
               " >= Principal) WHERE LoanID = " & id
    LoadLoans
    ShowCash
End Sub

' ------------------------------------------------------------------------------------------ interest
Private Sub cmdCalcInterest_Click()
    Dim days As Long, bal As Currency
    days = DateDiff("d", dtpSince.Value, Date)
    If days <= 0 Then
        MsgBox "Pick a date in the past.", vbExclamation
        Exit Sub
    End If
    bal = SavingsOf(IdOf(cboIntMember.Text))
    lblIntResult.Caption = "Savings " & Format$(bal, "#,##0.00") & " for " & days & " days at " & _
                           RateForDays(days) & "% a year" & vbCrLf & "Interest = " & _
                           Format$(InterestFor(bal, days), "#,##0.00")
    lblIntResult.Tag = CStr(InterestFor(bal, days))
    cmdPayInterest.Enabled = (InterestFor(bal, days) > 0)
End Sub

Private Sub cmdPayInterest_Click()
    If PostEntry(Date, IdOf(cboIntMember.Text), CAT_INTEREST, "CR", CCur(lblIntResult.Tag), "Cash", "Interest") Then
        ' interest is paid out of the society's cash into the member's savings: the cash is unchanged,
        ' so the CR above is balanced by an expense of the society
        PostEntry Date, "", CAT_EXPENSE, "DR", CCur(lblIntResult.Tag), "Cash", "Interest to " & IdOf(cboIntMember.Text)
        cmdPayInterest.Enabled = False
        ShowCash
    End If
End Sub

' ------------------------------------------------------------------------------------------ day book
Private Sub cmdDayBook_Click()
    Dim rs As New ADODB.Recordset, sql As String, dr As Currency, cr As Currency
    sql = "SELECT EntryDate, MemberID, Category, Narration, Direction, Amount FROM Ledger"
    If chkAllDays.Value = vbUnchecked Then sql = sql & " WHERE EntryDate = " & SqlDate(dtpDay.Value)
    rs.Open sql & " ORDER BY EntryDate, EntryID", cn, adOpenStatic, adLockReadOnly
    grdDayBook.Rows = 1
    Do Until rs.EOF
        If rs!Direction = "DR" Then
            grdDayBook.AddItem Format$(rs!EntryDate, "yyyy-mm-dd") & vbTab & rs!MemberID & vbTab & _
                               rs!Category & ": " & rs!Narration & vbTab & Format$(rs!Amount, "#,##0.00") & vbTab & ""
            dr = dr + rs!Amount
        Else
            grdDayBook.AddItem Format$(rs!EntryDate, "yyyy-mm-dd") & vbTab & rs!MemberID & vbTab & _
                               rs!Category & ": " & rs!Narration & vbTab & "" & vbTab & Format$(rs!Amount, "#,##0.00")
            cr = cr + rs!Amount
        End If
        rs.MoveNext
    Loop
    rs.Close
    lblDayTotals.Caption = (grdDayBook.Rows - 1) & " entries   debit " & Format$(dr, "#,##0.00") & _
                           "   credit " & Format$(cr, "#,##0.00") & "   difference " & Format$(cr - dr, "#,##0.00")
End Sub

' ------------------------------------------------------------------------------------------ profit & loss
Private Sub tabMain_Click(PreviousTab As Integer)
    If tabMain.Tab = 5 Then ShowProfitAndLoss
    If tabMain.Tab = 2 Then LoadLoans
End Sub

Public Sub ShowProfitAndLoss()
    Dim income As Currency, expense As Currency, net As Currency
    income = ScalarValue("SELECT SUM(Amount) FROM Ledger WHERE Category = '" & CAT_INCOME & "'")
    expense = ScalarValue("SELECT SUM(Amount) FROM Ledger WHERE Category = '" & CAT_EXPENSE & "'")
    net = income - expense
    lblPL(0).Caption = "Income (fees, entry fees, repaid interest): " & Format$(income, "#,##0.00")
    lblPL(1).Caption = "Expenses (incl. interest paid): " & Format$(expense, "#,##0.00")
    lblPL(2).Caption = "Loans outstanding: " & Format$(ScalarValue("SELECT SUM(Principal - Repaid) FROM Loans WHERE NOT Closed"), "#,##0.00")
    If net >= 0 Then
        lblPL(3).Caption = "Net profit: " & Format$(net, "#,##0.00")
        shpNet.FillColor = &HC0FFC0
        shpNet.BackColor = &HC0FFC0
    Else
        lblPL(3).Caption = "Net loss: " & Format$(-net, "#,##0.00")
        shpNet.BackColor = &HC0C0FF
    End If
End Sub
