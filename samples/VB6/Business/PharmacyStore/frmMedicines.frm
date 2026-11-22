VERSION 5.00
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Begin VB.Form frmMedicines 
   Caption         =   "Medicines"
   ClientHeight    =   4440
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   6600
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   4440
   ScaleWidth      =   6600
   Begin VB.CommandButton cmdDelete 
      Caption         =   "&Delete"
      Height          =   375
      Left            =   5280
      TabIndex        =   22
      Top             =   3360
      Width           =   1095
   End
   Begin VB.CommandButton cmdEdit 
      Caption         =   "&Edit"
      Height          =   375
      Left            =   4080
      TabIndex        =   21
      Top             =   3360
      Width           =   1095
   End
   Begin VB.CommandButton cmdAdd 
      Caption         =   "&Add"
      Height          =   375
      Left            =   2880
      TabIndex        =   20
      Top             =   3360
      Width           =   1095
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   ">|"
      Height          =   375
      Index           =   3
      Left            =   1680
      TabIndex        =   19
      Top             =   3360
      Width           =   495
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   ">"
      Height          =   375
      Index           =   2
      Left            =   1200
      TabIndex        =   18
      Top             =   3360
      Width           =   495
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   "<"
      Height          =   375
      Index           =   1
      Left            =   720
      TabIndex        =   17
      Top             =   3360
      Width           =   495
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   "|<"
      Height          =   375
      Index           =   0
      Left            =   240
      TabIndex        =   16
      Top             =   3360
      Width           =   495
   End
   Begin VB.TextBox txtSupplier 
      Height          =   315
      Left            =   1560
      TabIndex        =   15
      Top             =   2760
      Width           =   4815
   End
   Begin VB.TextBox txtReorder 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   5040
      TabIndex        =   11
      Top             =   1800
      Width           =   1335
   End
   Begin VB.TextBox txtStock 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   1560
      TabIndex        =   9
      Top             =   1800
      Width           =   1335
   End
   Begin VB.TextBox txtPrice 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   5040
      TabIndex        =   7
      Top             =   1320
      Width           =   1335
   End
   Begin VB.ComboBox cboCategory 
      Height          =   315
      Left            =   1560
      TabIndex        =   5
      Top             =   1320
      Width           =   1935
   End
   Begin VB.TextBox txtName 
      Height          =   315
      Left            =   1560
      TabIndex        =   3
      Top             =   840
      Width           =   4815
   End
   Begin VB.TextBox txtCode 
      Height          =   315
      Left            =   1560
      MaxLength       =   10
      TabIndex        =   1
      Top             =   360
      Width           =   1335
   End
   Begin MSComCtl2.DTPicker dtpExpiry 
      Height          =   315
      Left            =   1560
      TabIndex        =   13
      Top             =   2280
      Width           =   1935
      _ExtentX        =   3413
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   46023
   End
   Begin VB.Label lblRecord 
      Alignment       =   2  'Center
      Caption         =   "-"
      Height          =   255
      Left            =   240
      TabIndex        =   23
      Top             =   3900
      Width           =   1935
   End
   Begin VB.Label lblWarning 
      Caption         =   ""
      ForeColor       =   &H000000C0&
      Height          =   255
      Left            =   3600
      TabIndex        =   24
      Top             =   2340
      Width           =   2775
   End
   Begin VB.Label lblSupplier 
      Caption         =   "Supplier:"
      Height          =   255
      Left            =   240
      TabIndex        =   14
      Top             =   2820
      Width           =   1215
   End
   Begin VB.Label lblExpiry 
      Caption         =   "Expiry:"
      Height          =   255
      Left            =   240
      TabIndex        =   12
      Top             =   2340
      Width           =   1215
   End
   Begin VB.Label lblReorder 
      Caption         =   "Reorder at:"
      Height          =   255
      Left            =   3720
      TabIndex        =   10
      Top             =   1860
      Width           =   1215
   End
   Begin VB.Label lblStock 
      Caption         =   "In stock:"
      Height          =   255
      Left            =   240
      TabIndex        =   8
      Top             =   1860
      Width           =   1215
   End
   Begin VB.Label lblPrice 
      Caption         =   "Unit price:"
      Height          =   255
      Left            =   3720
      TabIndex        =   6
      Top             =   1380
      Width           =   1215
   End
   Begin VB.Label lblCategory 
      Caption         =   "Category:"
      Height          =   255
      Left            =   240
      TabIndex        =   4
      Top             =   1380
      Width           =   1215
   End
   Begin VB.Label lblName 
      Caption         =   "Name:"
      Height          =   255
      Left            =   240
      TabIndex        =   2
      Top             =   900
      Width           =   1215
   End
   Begin VB.Label lblCode 
      Caption         =   "Code:"
      Height          =   255
      Left            =   240
      TabIndex        =   0
      Top             =   420
      Width           =   1215
   End
End
Attribute VB_Name = "frmMedicines"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmMedicines - record-by-record editing with an updatable ADO Recordset:
'   |< < > >|  a CommandButton control array calling MoveFirst / MovePrevious / MoveNext / MoveLast
'   Add/Save and Edit/Update  one button each whose Caption tells the state ("&Add" -> "&Save")
'   rs!Field = value + rs.Update, rs.AddNew, rs.Delete, rs.AbsolutePosition / RecordCount
Option Explicit

Private rs As ADODB.Recordset

Private Sub Form_Load()
    cboCategory.AddItem "Tablets"
    cboCategory.AddItem "Syrup"
    cboCategory.AddItem "Cream"
    cboCategory.AddItem "Drops"
    Set rs = New ADODB.Recordset
    rs.CursorLocation = adUseClient
    rs.Open "SELECT * FROM Medicines ORDER BY Code", cn, adOpenKeyset, adLockOptimistic
    LockFields True
    ShowRecord
End Sub

Private Sub LockFields(ByVal Locked As Boolean)
    Dim ctl As Control
    For Each ctl In Me.Controls
        If TypeOf ctl Is TextBox Then ctl.Locked = Locked
    Next
    cboCategory.Enabled = Not Locked
    dtpExpiry.Enabled = Not Locked
    cmdDelete.Enabled = Locked
    cmdNav(0).Enabled = Locked: cmdNav(1).Enabled = Locked
    cmdNav(2).Enabled = Locked: cmdNav(3).Enabled = Locked
End Sub

Private Sub ShowRecord()
    If rs.EOF Or rs.BOF Then
        lblRecord.Caption = "no record"
        Exit Sub
    End If
    txtCode.Text = rs!Code
    txtName.Text = rs!MedName
    cboCategory.Text = rs!Category & ""
    txtPrice.Text = Format$(rs!UnitPrice, "0.00")
    txtStock.Text = rs!Stock
    txtReorder.Text = rs!ReorderLevel
    dtpExpiry.Value = rs!Expiry
    txtSupplier.Text = rs!Supplier & ""
    lblRecord.Caption = rs.AbsolutePosition & " / " & rs.RecordCount
    If rs!Expiry < Date Then
        lblWarning.Caption = "EXPIRED"
    ElseIf DateDiff("d", Date, rs!Expiry) <= 60 Then
        lblWarning.Caption = "expires in " & DateDiff("d", Date, rs!Expiry) & " days"
    Else
        lblWarning.Caption = ""
    End If
End Sub

Private Sub cmdNav_Click(Index As Integer)
    Select Case Index
        Case 0: rs.MoveFirst
        Case 1: rs.MovePrevious: If rs.BOF Then rs.MoveFirst
        Case 2: rs.MoveNext: If rs.EOF Then rs.MoveLast
        Case 3: rs.MoveLast
    End Select
    ShowRecord
End Sub

Private Function FieldsOk() As Boolean
    If Trim$(txtCode.Text) = "" Or Trim$(txtName.Text) = "" Then
        MsgBox "Code and name are required.", vbExclamation
    ElseIf Not IsNumeric(txtPrice.Text) Or Not IsNumeric(txtStock.Text) Or Not IsNumeric(txtReorder.Text) Then
        MsgBox "Price, stock and reorder level must be numbers.", vbExclamation
    Else
        FieldsOk = True
    End If
End Function

Private Sub CopyToRecord()
    rs!Code = UCase$(Trim$(txtCode.Text))
    rs!MedName = Trim$(txtName.Text)
    rs!Category = cboCategory.Text
    rs!UnitPrice = CCur(txtPrice.Text)
    rs!Stock = CLng(txtStock.Text)
    rs!ReorderLevel = CLng(txtReorder.Text)
    rs!Expiry = dtpExpiry.Value
    rs!Supplier = txtSupplier.Text
End Sub

Private Sub cmdAdd_Click()
    If cmdAdd.Caption = "&Add" Then
        LockFields False
        txtCode.Text = "": txtName.Text = "": txtPrice.Text = "0.00"
        txtStock.Text = "0": txtReorder.Text = "10": txtSupplier.Text = ""
        cboCategory.ListIndex = 0
        dtpExpiry.Value = DateAdd("yyyy", 1, Date)
        cmdAdd.Caption = "&Save"
        cmdEdit.Caption = "&Cancel"
        txtCode.SetFocus
    Else
        If Not FieldsOk() Then Exit Sub
        rs.AddNew
        CopyToRecord
        rs.Update
        cmdAdd.Caption = "&Add"
        cmdEdit.Caption = "&Edit"
        LockFields True
        ShowRecord
        mdiStore.ShowAlertsInStatus
    End If
End Sub

Private Sub cmdEdit_Click()
    Select Case cmdEdit.Caption
        Case "&Edit"
            LockFields False
            txtCode.Locked = True                  ' the key is not changed
            cmdEdit.Caption = "&Update"
            cmdAdd.Enabled = False
        Case "&Update"
            If Not FieldsOk() Then Exit Sub
            rs!MedName = Trim$(txtName.Text)
            rs!Category = cboCategory.Text
            rs!UnitPrice = CCur(txtPrice.Text)
            rs!ReorderLevel = CLng(txtReorder.Text)
            rs!Expiry = dtpExpiry.Value
            rs!Supplier = txtSupplier.Text
            rs.Update
            cmdEdit.Caption = "&Edit"
            cmdAdd.Enabled = True
            LockFields True
            ShowRecord
        Case "&Cancel"
            cmdAdd.Caption = "&Add"
            cmdEdit.Caption = "&Edit"
            LockFields True
            ShowRecord
    End Select
End Sub

Private Sub cmdDelete_Click()
    If rs.EOF Or rs.BOF Then Exit Sub
    If MsgBox("Delete " & rs!MedName & "?", vbYesNo + vbExclamation) = vbNo Then Exit Sub
    rs.Delete
    rs.MoveNext
    If rs.EOF And rs.RecordCount > 0 Then rs.MoveLast
    ShowRecord
End Sub

' Show a given medicine (used by other forms)
Public Sub GoToCode(ByVal Code As String)
    rs.MoveFirst
    rs.Find "Code = '" & Replace(Code, "'", "''") & "'"
    If rs.EOF Then rs.MoveFirst
    ShowRecord
End Sub

Private Sub Form_Unload(Cancel As Integer)
    If cmdAdd.Caption = "&Save" Or cmdEdit.Caption = "&Update" Then
        If MsgBox("Discard the changes?", vbYesNo + vbQuestion) = vbNo Then
            Cancel = 1
            Exit Sub
        End If
    End If
    rs.Close
    Set rs = Nothing
End Sub
