VERSION 5.00
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Begin VB.Form frmPurchase 
   Caption         =   "Purchase - stock in"
   ClientHeight    =   4680
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   7200
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   4680
   ScaleWidth      =   7200
   Begin VB.CommandButton cmdSave 
      Caption         =   "&Receive"
      Height          =   375
      Left            =   5760
      TabIndex        =   10
      Top             =   1440
      Width           =   1215
   End
   Begin VB.TextBox txtBatch 
      Height          =   315
      Left            =   1440
      TabIndex        =   7
      Top             =   1440
      Width           =   1455
   End
   Begin VB.TextBox txtCost 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   4200
      TabIndex        =   5
      Top             =   960
      Width           =   1215
   End
   Begin VB.TextBox txtQty 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   1440
      TabIndex        =   3
      Top             =   960
      Width           =   1215
   End
   Begin VB.ComboBox cboMedicine 
      Height          =   315
      Left            =   1440
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   360
      Width           =   5535
   End
   Begin MSComCtl2.DTPicker dtpExpiry 
      Height          =   315
      Left            =   4200
      TabIndex        =   9
      Top             =   1440
      Width           =   1455
      _ExtentX        =   2566
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   46387
   End
   Begin MSFlexGridLib.MSFlexGrid grdRecent 
      Height          =   2535
      Left            =   240
      TabIndex        =   11
      Top             =   1980
      Width           =   6735
      _ExtentX        =   11880
      _ExtentY        =   4471
      _Version        =   393216
      Rows            =   1
      Cols            =   5
      FixedCols       =   0
      FormatString    =   "<Date      |<Code |>Qty  |>Cost  |<Batch       "
   End
   Begin VB.Label lblExpiry 
      Caption         =   "Expiry:"
      Height          =   255
      Left            =   3120
      TabIndex        =   8
      Top             =   1500
      Width           =   975
   End
   Begin VB.Label lblBatch 
      Caption         =   "Batch:"
      Height          =   255
      Left            =   240
      TabIndex        =   6
      Top             =   1500
      Width           =   1095
   End
   Begin VB.Label lblCost 
      Caption         =   "Unit cost:"
      Height          =   255
      Left            =   3120
      TabIndex        =   4
      Top             =   1020
      Width           =   975
   End
   Begin VB.Label lblQty 
      Caption         =   "Quantity:"
      Height          =   255
      Left            =   240
      TabIndex        =   2
      Top             =   1020
      Width           =   1095
   End
   Begin VB.Label lblMedicine 
      Caption         =   "Medicine:"
      Height          =   255
      Left            =   240
      TabIndex        =   0
      Top             =   420
      Width           =   1095
   End
End
Attribute VB_Name = "frmPurchase"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmPurchase - receive stock: a Purchases row, Stock + qty (modStore.ChangeStock logs it); a later
' expiry date than the one on file replaces it. The last purchases are listed in an MSFlexGrid.
Option Explicit

Private Sub Form_Load()
    FillMedicines cboMedicine
    If cboMedicine.ListCount > 0 Then cboMedicine.ListIndex = 0
    dtpExpiry.Value = DateAdd("m", 18, Date)
    LoadRecent
End Sub

Private Sub LoadRecent()
    Dim rs As ADODB.Recordset
    grdRecent.Rows = 1
    Set rs = cn.Execute("SELECT TOP 10 PurchaseDate, Code, Qty, UnitCost, Batch FROM Purchases ORDER BY PurchaseID DESC")
    Do Until rs.EOF
        grdRecent.AddItem Format$(rs!PurchaseDate, "yyyy-mm-dd") & vbTab & rs!Code & vbTab & rs!Qty & vbTab & _
                          Format$(rs!UnitCost, "0.00") & vbTab & rs!Batch
        rs.MoveNext
    Loop
    rs.Close
End Sub

Private Sub txtQty_KeyPress(KeyAscii As Integer)
    If Not (KeyAscii = 8 Or IsNumeric(Chr$(KeyAscii))) Then KeyAscii = 0
End Sub

Private Sub cmdSave_Click()
    Dim code As String
    If Val(txtQty.Text) <= 0 Then
        MsgBox "Type the quantity received.", vbExclamation
        Exit Sub
    End If
    If Not IsNumeric(txtCost.Text) Then
        MsgBox "Type the unit cost.", vbExclamation
        Exit Sub
    End If
    code = CodeOf(cboMedicine.Text)
    cn.BeginTrans
    cn.Execute "INSERT INTO Purchases (Code, PurchaseDate, Qty, UnitCost, Batch, Expiry) VALUES (" & SqlStr(code) & _
               ", " & SqlDate(Date) & ", " & Val(txtQty.Text) & ", " & Str$(CCur(txtCost.Text)) & ", " & _
               SqlStr(txtBatch.Text) & ", " & SqlDate(dtpExpiry.Value) & ")"
    ChangeStock code, Val(txtQty.Text), "purchase " & txtBatch.Text
    cn.Execute "UPDATE Medicines SET Expiry = " & SqlDate(dtpExpiry.Value) & " WHERE Code = " & SqlStr(code) & _
               " AND Expiry < " & SqlDate(dtpExpiry.Value)
    cn.CommitTrans
    txtQty.Text = "": txtCost.Text = "": txtBatch.Text = ""
    LoadRecent
    mdiStore.ShowAlertsInStatus
End Sub
