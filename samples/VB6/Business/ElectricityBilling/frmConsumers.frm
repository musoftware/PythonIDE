VERSION 5.00
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Object = "{C932BA88-4374-101B-A56C-00AA003668DC}#1.1#0"; "MSMASK32.OCX"
Begin VB.Form frmConsumers
   Caption         =   "Consumers"
   ClientHeight    =   4500
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   7800
   LinkTopic       =   "Form1"
   ScaleHeight     =   4500
   ScaleWidth      =   7800
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdClose
      Caption         =   "Close"
      Height          =   375
      Left            =   6480
      TabIndex        =   20
      Top             =   3960
      Width           =   1095
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "&Save"
      Height          =   375
      Left            =   5280
      TabIndex        =   19
      Top             =   3960
      Width           =   1095
   End
   Begin VB.CommandButton cmdNew
      Caption         =   "&New"
      Height          =   375
      Left            =   4080
      TabIndex        =   18
      Top             =   3960
      Width           =   1095
   End
   Begin VB.CheckBox chkActive
      Caption         =   "Connection active"
      Height          =   255
      Left            =   4080
      TabIndex        =   17
      Top             =   3480
      Value           =   1  'Checked
      Width           =   2655
   End
   Begin VB.TextBox txtDeposit
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   5280
      TabIndex        =   16
      Top             =   3000
      Width           =   1335
   End
   Begin VB.ComboBox cboCategory
      Height          =   315
      Left            =   5280
      Style           =   2  'Dropdown List
      TabIndex        =   12
      Top             =   2040
      Width           =   2295
   End
   Begin VB.TextBox txtAddress
      Height          =   315
      Left            =   5280
      TabIndex        =   8
      Top             =   1080
      Width           =   2295
   End
   Begin VB.TextBox txtName
      Height          =   315
      Left            =   5280
      TabIndex        =   6
      Top             =   600
      Width           =   2295
   End
   Begin VB.TextBox txtMeter
      Height          =   315
      Left            =   5280
      MaxLength       =   6
      TabIndex        =   4
      Top             =   120
      Width           =   1335
   End
   Begin VB.ListBox lstConsumers
      Height          =   3765
      Left            =   120
      TabIndex        =   1
      Top             =   480
      Width           =   3735
   End
   Begin MSMask.MaskEdBox mskPhone
      Height          =   315
      Left            =   5280
      TabIndex        =   10
      Top             =   1560
      Width           =   2295
      _ExtentX        =   4048
      _ExtentY        =   556
      _Version        =   393216
      MaxLength       =   13
      Mask            =   "####-###-####"
      PromptChar      =   "_"
   End
   Begin MSComCtl2.DTPicker dtpConnected
      Height          =   315
      Left            =   5280
      TabIndex        =   14
      Top             =   2520
      Width           =   2295
      _ExtentX        =   4048
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   46023
   End
   Begin VB.Label lblDeposit
      Caption         =   "Deposit:"
      Height          =   255
      Left            =   4080
      TabIndex        =   15
      Top             =   3060
      Width           =   1095
   End
   Begin VB.Label lblConnected
      Caption         =   "Connected:"
      Height          =   255
      Left            =   4080
      TabIndex        =   13
      Top             =   2580
      Width           =   1095
   End
   Begin VB.Label lblCategory
      Caption         =   "Category:"
      Height          =   255
      Left            =   4080
      TabIndex        =   11
      Top             =   2100
      Width           =   1095
   End
   Begin VB.Label lblPhone
      Caption         =   "Phone:"
      Height          =   255
      Left            =   4080
      TabIndex        =   9
      Top             =   1620
      Width           =   1095
   End
   Begin VB.Label lblAddress
      Caption         =   "Address:"
      Height          =   255
      Left            =   4080
      TabIndex        =   7
      Top             =   1140
      Width           =   1095
   End
   Begin VB.Label lblName
      Caption         =   "Name:"
      Height          =   255
      Left            =   4080
      TabIndex        =   5
      Top             =   660
      Width           =   1095
   End
   Begin VB.Label lblMeter
      Caption         =   "Meter no:"
      Height          =   255
      Left            =   4080
      TabIndex        =   3
      Top             =   180
      Width           =   1095
   End
   Begin VB.Label lblList
      Caption         =   "All consumers (click one to edit):"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   180
      Width           =   3735
   End
   Begin VB.Label lblCount
      Caption         =   "-"
      Height          =   255
      Left            =   120
      TabIndex        =   2
      Top             =   4260
      Width           =   3735
   End
End
Attribute VB_Name = "frmConsumers"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmConsumers - consumer master: a ListBox whose ItemData holds the meter number, a MaskEdBox for
' the phone, a DTPicker and a CheckBox. Save does an INSERT for a new meter, an UPDATE otherwise.
Option Explicit

Private Sub Form_Load()
    cboCategory.AddItem "Domestic"
    cboCategory.AddItem "Commercial"
    cboCategory.ListIndex = 0
    LoadList
End Sub

Private Sub LoadList()
    Dim rs As ADODB.Recordset
    lstConsumers.Clear
    Set rs = cn.Execute("SELECT MeterNo, FullName, Active FROM Consumers ORDER BY MeterNo")
    Do While Not rs.EOF
        lstConsumers.AddItem rs!MeterNo & "  " & rs!FullName & IIf(rs!Active, "", "  (inactive)")
        lstConsumers.ItemData(lstConsumers.NewIndex) = rs!MeterNo
        rs.MoveNext
    Loop
    rs.Close
    lblCount.Caption = lstConsumers.ListCount & " consumers"
End Sub

Private Sub lstConsumers_Click()
    Dim rs As ADODB.Recordset
    If lstConsumers.ListIndex < 0 Then Exit Sub
    Set rs = cn.Execute("SELECT * FROM Consumers WHERE MeterNo = " & lstConsumers.ItemData(lstConsumers.ListIndex))
    If Not rs.EOF Then
        txtMeter.Text = rs!MeterNo
        txtMeter.Locked = True
        txtName.Text = rs!FullName
        txtAddress.Text = rs!Address & ""
        mskPhone.Text = rs!Phone & ""
        cboCategory.Text = rs!Category
        dtpConnected.Value = rs!Connected
        txtDeposit.Text = Format$(rs!Deposit, "0.00")
        chkActive.Value = IIf(rs!Active, vbChecked, vbUnchecked)
    End If
    rs.Close
End Sub

Private Sub cmdNew_Click()
    txtMeter.Locked = False
    txtMeter.Text = ""
    txtName.Text = ""
    txtAddress.Text = ""
    mskPhone.Text = ""
    txtDeposit.Text = "100.00"
    dtpConnected.Value = Date
    chkActive.Value = vbChecked
    txtMeter.SetFocus
End Sub

Private Sub txtMeter_KeyPress(KeyAscii As Integer)
    If KeyAscii <> 8 And Not (Chr$(KeyAscii) Like "[0-9]") Then KeyAscii = 0
End Sub

Private Sub cmdSave_Click()
    Dim rs As ADODB.Recordset, exists As Boolean
    If Len(txtMeter.Text) <> 5 Then
        MsgBox "A meter number has 5 digits.", vbExclamation: Exit Sub
    End If
    If Trim$(txtName.Text) = "" Then
        MsgBox "Type the consumer's name.", vbExclamation: Exit Sub
    End If
    If Not IsNumeric(txtDeposit.Text) Then
        MsgBox "The deposit must be a number.", vbExclamation: Exit Sub
    End If
    Set rs = cn.Execute("SELECT COUNT(*) FROM Consumers WHERE MeterNo = " & txtMeter.Text)
    exists = rs(0) > 0
    rs.Close
    If exists And Not txtMeter.Locked Then
        MsgBox "Meter " & txtMeter.Text & " is already registered.", vbExclamation: Exit Sub
    End If
    If exists Then
        cn.Execute "UPDATE Consumers SET FullName = " & Q(txtName.Text) & ", Address = " & Q(txtAddress.Text) & _
                   ", Phone = " & Q(mskPhone.Text) & ", Category = " & Q(cboCategory.Text) & _
                   ", Connected = " & JetDate(dtpConnected.Value) & ", Deposit = " & Val(txtDeposit.Text) & _
                   ", Active = " & IIf(chkActive.Value = vbChecked, "True", "False") & _
                   " WHERE MeterNo = " & txtMeter.Text
    Else
        cn.Execute "INSERT INTO Consumers VALUES (" & txtMeter.Text & ", " & Q(txtName.Text) & ", " & _
                   Q(txtAddress.Text) & ", " & Q(mskPhone.Text) & ", " & Q(cboCategory.Text) & ", " & _
                   JetDate(dtpConnected.Value) & ", " & Val(txtDeposit.Text) & ", " & _
                   IIf(chkActive.Value = vbChecked, "True", "False") & ")"
    End If
    txtMeter.Locked = True
    LoadList
    frmMain.RefreshSummary
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub
