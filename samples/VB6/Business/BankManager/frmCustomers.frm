VERSION 5.00
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Begin VB.Form frmCustomers
   Caption         =   "Customer accounts"
   ClientHeight    =   5640
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   9000
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   5640
   ScaleWidth      =   9000
   Begin VB.CommandButton cmdClose
      Caption         =   "&Close"
      Height          =   375
      Left            =   7680
      TabIndex        =   19
      Top             =   5160
      Width           =   1215
   End
   Begin VB.CommandButton cmdFind
      Caption         =   "&Find..."
      Height          =   375
      Left            =   4080
      TabIndex        =   18
      Top             =   5160
      Width           =   1215
   End
   Begin VB.CommandButton cmdDelete
      Caption         =   "&Delete"
      Height          =   375
      Left            =   2760
      TabIndex        =   17
      Top             =   5160
      Width           =   1215
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "&Save"
      Height          =   375
      Left            =   1440
      TabIndex        =   16
      Top             =   5160
      Width           =   1215
   End
   Begin VB.CommandButton cmdNew
      Caption         =   "&New"
      Height          =   375
      Left            =   120
      TabIndex        =   15
      Top             =   5160
      Width           =   1215
   End
   Begin VB.Frame fraDetails
      Caption         =   "Account details"
      Height          =   2175
      Left            =   120
      TabIndex        =   1
      Top             =   2880
      Width           =   8775
      Begin VB.TextBox txtBalance
         Alignment       =   1  'Right Justify
         Height          =   315
         Left            =   6000
         TabIndex        =   14
         Top             =   1320
         Width           =   2535
      End
      Begin VB.ComboBox cboType
         Height          =   315
         Left            =   6000
         Style           =   2  'Dropdown List
         TabIndex        =   10
         Top             =   360
         Width           =   2535
      End
      Begin VB.TextBox txtAddress
         Height          =   315
         Left            =   1320
         TabIndex        =   8
         Top             =   1680
         Width           =   3255
      End
      Begin VB.TextBox txtPhone
         Height          =   315
         Left            =   1320
         TabIndex        =   6
         Top             =   1200
         Width           =   3255
      End
      Begin VB.TextBox txtName
         Height          =   315
         Left            =   1320
         TabIndex        =   4
         Top             =   780
         Width           =   3255
      End
      Begin VB.TextBox txtAccNo
         BackColor       =   &H8000000F&
         Height          =   315
         Left            =   1320
         Locked          =   -1  'True
         TabIndex        =   3
         Top             =   360
         Width           =   1455
      End
      Begin MSComCtl2.DTPicker dtpOpened
         Height          =   315
         Left            =   6000
         TabIndex        =   12
         Top             =   840
         Width           =   2535
         _ExtentX        =   4471
         _ExtentY        =   556
         _Version        =   393216
         Format          =   20512769
         CurrentDate     =   46023
      End
      Begin VB.Label lblBalance
         Caption         =   "Opening balance:"
         Height          =   255
         Left            =   4680
         TabIndex        =   13
         Top             =   1380
         Width           =   1335
      End
      Begin VB.Label lblOpened
         Caption         =   "Opened on:"
         Height          =   255
         Left            =   4680
         TabIndex        =   11
         Top             =   900
         Width           =   1335
      End
      Begin VB.Label lblType
         Caption         =   "Account type:"
         Height          =   255
         Left            =   4680
         TabIndex        =   9
         Top             =   420
         Width           =   1335
      End
      Begin VB.Label lblAddress
         Caption         =   "Address:"
         Height          =   255
         Left            =   120
         TabIndex        =   7
         Top             =   1740
         Width           =   1095
      End
      Begin VB.Label lblPhone
         Caption         =   "Phone:"
         Height          =   255
         Left            =   120
         TabIndex        =   5
         Top             =   1260
         Width           =   1095
      End
      Begin VB.Label lblName
         Caption         =   "Full name:"
         Height          =   255
         Left            =   120
         TabIndex        =   20
         Top             =   840
         Width           =   1095
      End
      Begin VB.Label lblAccNo
         Caption         =   "Account no:"
         Height          =   255
         Left            =   120
         TabIndex        =   2
         Top             =   420
         Width           =   1095
      End
   End
   Begin MSFlexGridLib.MSFlexGrid grdCustomers
      Height          =   2655
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   8775
      _ExtentX        =   15478
      _ExtentY        =   4683
      _Version        =   393216
      Rows            =   2
      Cols            =   5
      FixedCols       =   0
      SelectionMode   =   1
      AllowUserResizing=   1
      FormatString    =   "<Account|<Name|<Phone|<Type|>Balance"
   End
End
Attribute VB_Name = "frmCustomers"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmCustomers - MDI child: the account list in an MSFlexGrid plus a details frame.
'   New -> empty details with the next account number; Save -> INSERT or UPDATE;
'   Delete -> asks first, removes the account and its transactions; Find -> InputBox search by name.
Option Explicit

Private mIsNew As Boolean

Private Sub Form_Load()
    cboType.AddItem "Savings"
    cboType.AddItem "Current"
    cboType.ListIndex = 0
    grdCustomers.ColWidth(0) = 1000
    grdCustomers.ColWidth(1) = 3000
    grdCustomers.ColWidth(2) = 1800
    grdCustomers.ColWidth(3) = 1100
    grdCustomers.ColWidth(4) = 1500
    LoadGrid
    If grdCustomers.Rows > 1 Then ShowAccount Val(grdCustomers.TextMatrix(1, 0))
End Sub

' Fill the grid from the Customers table
Public Sub LoadGrid(Optional ByVal NameFilter As String = "")
    Dim rs As ADODB.Recordset, sql As String, r As Long
    sql = "SELECT AccountNo, FullName, Phone, AccType, Balance FROM Customers"
    If NameFilter <> "" Then sql = sql & " WHERE FullName LIKE " & Q("%" & NameFilter & "%")
    sql = sql & " ORDER BY AccountNo"
    Set rs = New ADODB.Recordset
    rs.Open sql, cn, adOpenStatic, adLockReadOnly
    grdCustomers.Rows = 1                       ' keep the header row only
    Do While Not rs.EOF
        r = grdCustomers.Rows
        grdCustomers.Rows = r + 1
        grdCustomers.TextMatrix(r, 0) = rs!AccountNo
        grdCustomers.TextMatrix(r, 1) = rs!FullName & ""
        grdCustomers.TextMatrix(r, 2) = rs!Phone & ""
        grdCustomers.TextMatrix(r, 3) = rs!AccType & ""
        grdCustomers.TextMatrix(r, 4) = Format$(rs!Balance, "#,##0.00")
        rs.MoveNext
    Loop
    rs.Close
End Sub

' Copy one account into the details frame
Private Sub ShowAccount(ByVal AccountNo As Long)
    Dim rs As ADODB.Recordset
    Set rs = New ADODB.Recordset
    rs.Open "SELECT * FROM Customers WHERE AccountNo = " & AccountNo, cn, adOpenStatic, adLockReadOnly
    If Not rs.EOF Then
        txtAccNo.Text = rs!AccountNo
        txtName.Text = rs!FullName & ""
        txtPhone.Text = rs!Phone & ""
        txtAddress.Text = rs!Address & ""
        cboType.Text = rs!AccType & ""
        dtpOpened.Value = rs!Opened
        txtBalance.Text = Format$(rs!Balance, "0.00")
        txtBalance.Locked = True                 ' the balance changes through transactions only
        mIsNew = False
    End If
    rs.Close
End Sub

Private Sub grdCustomers_Click()
    If grdCustomers.Row >= 1 Then ShowAccount Val(grdCustomers.TextMatrix(grdCustomers.Row, 0))
End Sub

Private Sub cmdNew_Click()
    ClearInputs Me
    txtAccNo.Text = NextAccountNo()
    dtpOpened.Value = Date
    txtBalance.Text = "0.00"
    txtBalance.Locked = False
    mIsNew = True
    txtName.SetFocus
End Sub

' Validation before saving: returns an error message, or "" when everything is fine
Private Function CheckInput() As String
    If Len(Trim$(txtName.Text)) < 3 Then
        CheckInput = "The full name must have at least 3 letters."
    ElseIf Not IsNumeric(txtBalance.Text) Then
        CheckInput = "The opening balance must be a number."
    ElseIf CCur(txtBalance.Text) < 0 Then
        CheckInput = "The opening balance cannot be negative."
    End If
End Function

Private Sub cmdSave_Click()
    Dim msg As String
    msg = CheckInput()
    If msg <> "" Then
        MsgBox msg, vbExclamation, APP_TITLE
        Exit Sub
    End If
    If mIsNew Then
        cn.Execute "INSERT INTO Customers (AccountNo, FullName, Phone, Address, AccType, Opened, Balance) VALUES (" & _
                   Val(txtAccNo.Text) & ", " & Q(txtName.Text) & ", " & Q(txtPhone.Text) & ", " & _
                   Q(txtAddress.Text) & ", " & Q(cboType.Text) & ", " & D(dtpOpened.Value) & ", " & _
                   Str$(CCur(txtBalance.Text)) & ")"
        LogActivity "new account " & txtAccNo.Text
    Else
        cn.Execute "UPDATE Customers SET FullName = " & Q(txtName.Text) & ", Phone = " & Q(txtPhone.Text) & _
                   ", Address = " & Q(txtAddress.Text) & ", AccType = " & Q(cboType.Text) & _
                   ", Opened = " & D(dtpOpened.Value) & " WHERE AccountNo = " & Val(txtAccNo.Text)
        LogActivity "updated account " & txtAccNo.Text
    End If
    mIsNew = False
    LoadGrid
    mdiMain.sbMain.SimpleText = "Account " & txtAccNo.Text & " saved"
End Sub

Private Sub cmdDelete_Click()
    Dim n As Long
    If mIsNew Or txtAccNo.Text = "" Then Exit Sub
    If MsgBox("Delete account " & txtAccNo.Text & " (" & txtName.Text & ") and all its transactions?", _
              vbQuestion + vbYesNo + vbDefaultButton2, APP_TITLE) = vbNo Then Exit Sub
    n = Val(txtAccNo.Text)
    cn.Execute "DELETE FROM Transactions WHERE AccountNo = " & n
    cn.Execute "DELETE FROM Customers WHERE AccountNo = " & n
    LogActivity "deleted account " & n
    ClearInputs Me
    LoadGrid
End Sub

Private Sub cmdFind_Click()
    Dim s As String
    s = InputBox("Part of the customer name (empty = show all):", "Find customer")
    LoadGrid Trim$(s)
    If grdCustomers.Rows > 1 Then
        ShowAccount Val(grdCustomers.TextMatrix(1, 0))
    Else
        MsgBox "No customer matches """ & s & """.", vbInformation, APP_TITLE
    End If
End Sub

Private Sub txtPhone_KeyPress(KeyAscii As Integer)
    ' phone numbers: digits, '-' and Backspace
    If KeyAscii <> 45 Then KeyAscii = DigitsOnly(KeyAscii)
End Sub

Private Sub txtBalance_KeyPress(KeyAscii As Integer)
    KeyAscii = DigitsOnly(KeyAscii, True)
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub
