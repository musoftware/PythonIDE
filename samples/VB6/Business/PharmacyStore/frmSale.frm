VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmSale 
   Caption         =   "New invoice"
   ClientHeight    =   5520
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   7680
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   5520
   ScaleWidth      =   7680
   Begin VB.CommandButton cmdPrint 
      Caption         =   "&Print"
      Enabled         =   0   'False
      Height          =   375
      Left            =   6360
      TabIndex        =   17
      Top             =   4980
      Width           =   1095
   End
   Begin VB.CommandButton cmdSave 
      Caption         =   "&Save invoice"
      Height          =   375
      Left            =   4920
      TabIndex        =   16
      Top             =   4980
      Width           =   1335
   End
   Begin VB.TextBox txtDiscount 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   1560
      TabIndex        =   13
      Text            =   "0"
      Top             =   4560
      Width           =   735
   End
   Begin VB.CommandButton cmdRemove 
      Caption         =   "&Remove line"
      Height          =   375
      Left            =   240
      TabIndex        =   11
      Top             =   4020
      Width           =   1335
   End
   Begin VB.CommandButton cmdAddItem 
      Caption         =   "A&dd"
      Height          =   315
      Left            =   6480
      TabIndex        =   9
      Top             =   960
      Width           =   975
   End
   Begin VB.TextBox txtQty 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   5520
      TabIndex        =   8
      Text            =   "1"
      Top             =   960
      Width           =   855
   End
   Begin VB.ComboBox cboMedicine 
      Height          =   315
      Left            =   1560
      Style           =   2  'Dropdown List
      TabIndex        =   5
      Top             =   960
      Width           =   3375
   End
   Begin VB.TextBox txtCustomer 
      Height          =   315
      Left            =   1560
      TabIndex        =   1
      Text            =   "Walk-in customer"
      Top             =   360
      Width           =   3375
   End
   Begin MSComctlLib.ListView lvwCart 
      Height          =   2415
      Left            =   240
      TabIndex        =   10
      Top             =   1500
      Width           =   7215
      _ExtentX        =   12726
      _ExtentY        =   4260
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
         Text            =   "Code"
         Object.Width           =   1411
      EndProperty
      BeginProperty ColumnHeader(2) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         SubItemIndex    =   1
         Text            =   "Medicine"
         Object.Width           =   5292
      EndProperty
      BeginProperty ColumnHeader(3) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         Alignment       =   1
         SubItemIndex    =   2
         Text            =   "Qty"
         Object.Width           =   1411
      EndProperty
      BeginProperty ColumnHeader(4) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         Alignment       =   1
         SubItemIndex    =   3
         Text            =   "Price"
         Object.Width           =   1764
      EndProperty
      BeginProperty ColumnHeader(5) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         Alignment       =   1
         SubItemIndex    =   4
         Text            =   "Amount"
         Object.Width           =   1764
      EndProperty
   End
   Begin VB.Label lblTotal 
      Alignment       =   1  'Right Justify
      Caption         =   "0.00"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   13.5
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   5040
      TabIndex        =   15
      Top             =   4500
      Width           =   2415
   End
   Begin VB.Label lblSubtotal 
      Alignment       =   1  'Right Justify
      Caption         =   "Subtotal: 0.00"
      Height          =   255
      Left            =   4440
      TabIndex        =   12
      Top             =   4080
      Width           =   3015
   End
   Begin VB.Label lblTotalCaption 
      Caption         =   "Total:"
      Height          =   255
      Left            =   4200
      TabIndex        =   18
      Top             =   4560
      Width           =   735
   End
   Begin VB.Label lblDiscount 
      Caption         =   "Discount %:"
      Height          =   255
      Left            =   240
      TabIndex        =   14
      Top             =   4620
      Width           =   1215
   End
   Begin VB.Label lblQty 
      Caption         =   "Qty:"
      Height          =   255
      Left            =   5040
      TabIndex        =   7
      Top             =   1020
      Width           =   435
   End
   Begin VB.Label lblAvailable 
      Caption         =   "-"
      ForeColor       =   &H00808080&
      Height          =   255
      Left            =   1560
      TabIndex        =   6
      Top             =   1260
      Width           =   3375
   End
   Begin VB.Label lblMedicine 
      Caption         =   "Medicine:"
      Height          =   255
      Left            =   240
      TabIndex        =   4
      Top             =   1020
      Width           =   1215
   End
   Begin VB.Label lblCustomer 
      Caption         =   "Customer:"
      Height          =   255
      Left            =   240
      TabIndex        =   0
      Top             =   420
      Width           =   1215
   End
   Begin VB.Label lblInvoice 
      Alignment       =   1  'Right Justify
      Caption         =   "new invoice"
      Height          =   255
      Left            =   5040
      TabIndex        =   2
      Top             =   420
      Width           =   2415
   End
   Begin VB.Label lblDate 
      Caption         =   "-"
      Height          =   255
      Left            =   5040
      TabIndex        =   3
      Top             =   120
      Width           =   2415
   End
End
Attribute VB_Name = "frmSale"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmSale - an invoice: lines in a report-style ListView (ListItems.Add + SubItems), the stock is
' checked before a line is added, the discount box recalculates the total on every Change, Save
' writes Sales + SaleItems and lowers the stock, Print shows the DataReport of the invoice.
Option Explicit

Private mInvoiceNo As Long

Private Sub Form_Load()
    FillMedicines cboMedicine
    If cboMedicine.ListCount > 0 Then cboMedicine.ListIndex = 0
    lblDate.Caption = Format$(Date, "dddd d mmm yyyy")
    UsePicked
End Sub

' A medicine picked in the alerts window comes through the public variables gPickedCode / gPickedName
Public Sub UsePicked()
    Dim i As Integer
    If gPickedCode = "" Then Exit Sub
    For i = 0 To cboMedicine.ListCount - 1
        If CodeOf(cboMedicine.List(i)) = gPickedCode Then cboMedicine.ListIndex = i
    Next
    gPickedCode = ""
    gPickedName = ""
End Sub

Private Sub cboMedicine_Click()
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT UnitPrice, Stock FROM Medicines WHERE Code = " & SqlStr(CodeOf(cboMedicine.Text)))
    If Not rs.EOF Then lblAvailable.Caption = "Price " & Format$(rs!UnitPrice, "0.00") & ",  in stock " & rs!Stock
    rs.Close
End Sub

' Quantity of a code already on the invoice
Private Function QtyInCart(ByVal Code As String) As Long
    Dim li As ListItem
    For Each li In lvwCart.ListItems
        If li.Text = Code Then QtyInCart = QtyInCart + Val(li.SubItems(2))
    Next
End Function

Private Sub cmdAddItem_Click()
    Dim rs As ADODB.Recordset, li As ListItem, code As String, qty As Long
    code = CodeOf(cboMedicine.Text)
    qty = Val(txtQty.Text)
    If qty <= 0 Then
        MsgBox "Type a quantity.", vbExclamation
        Exit Sub
    End If
    Set rs = cn.Execute("SELECT MedName, UnitPrice, Stock, Expiry FROM Medicines WHERE Code = " & SqlStr(code))
    If rs!Expiry < Date Then
        MsgBox rs!MedName & " has expired and cannot be sold.", vbCritical
    ElseIf qty + QtyInCart(code) > rs!Stock Then
        MsgBox "Only " & rs!Stock & " in stock.", vbExclamation
    Else
        Set li = lvwCart.ListItems.Add(, , code)
        li.SubItems(1) = rs!MedName
        li.SubItems(2) = qty
        li.SubItems(3) = Format$(rs!UnitPrice, "0.00")
        li.SubItems(4) = Format$(qty * rs!UnitPrice, "0.00")
        txtQty.Text = "1"
    End If
    rs.Close
    Recalculate
End Sub

Private Sub cmdRemove_Click()
    If lvwCart.ListItems.Count = 0 Then Exit Sub
    lvwCart.ListItems.Remove lvwCart.SelectedItem.Index
    Recalculate
End Sub

Private Function Subtotal() As Currency
    Dim i As Integer
    For i = 1 To lvwCart.ListItems.Count
        Subtotal = Subtotal + CCur(lvwCart.ListItems(i).SubItems(4))
    Next
End Function

Public Function InvoiceTotal() As Currency
    Dim pct As Double
    If IsNumeric(txtDiscount.Text) Then pct = CDbl(txtDiscount.Text)
    If pct < 0 Or pct > 50 Then pct = 0
    InvoiceTotal = Round(Subtotal() * (100 - pct) / 100, 2)
End Function

Private Sub Recalculate()
    lblSubtotal.Caption = "Subtotal: " & Format$(Subtotal(), "#,##0.00")
    lblTotal.Caption = Format$(InvoiceTotal(), "#,##0.00")
End Sub

Private Sub txtDiscount_Change()
    Recalculate
End Sub

Private Sub cmdSave_Click()
    Dim rs As ADODB.Recordset, li As ListItem
    If lvwCart.ListItems.Count = 0 Then
        MsgBox "The invoice is empty.", vbExclamation
        Exit Sub
    End If
    cn.BeginTrans
    cn.Execute "INSERT INTO Sales (SaleDate, Customer, DiscountPct, Total) VALUES (" & SqlDate(Date) & ", " & _
               SqlStr(txtCustomer.Text) & ", " & Val(txtDiscount.Text) & ", " & Str$(InvoiceTotal()) & ")"
    Set rs = cn.Execute("SELECT MAX(InvoiceNo) FROM Sales")
    mInvoiceNo = rs(0)
    rs.Close
    For Each li In lvwCart.ListItems
        cn.Execute "INSERT INTO SaleItems (InvoiceNo, Code, Qty, UnitPrice) VALUES (" & mInvoiceNo & ", " & _
                   SqlStr(li.Text) & ", " & li.SubItems(2) & ", " & Str$(CCur(li.SubItems(3))) & ")"
        ChangeStock li.Text, -Val(li.SubItems(2)), "invoice " & mInvoiceNo
    Next
    cn.CommitTrans
    lblInvoice.Caption = "Invoice " & mInvoiceNo
    cmdSave.Enabled = False
    cmdPrint.Enabled = True
    mdiStore.ShowAlertsInStatus
End Sub

Private Sub cmdPrint_Click()
    deStore.cmdInvoice mInvoiceNo
    rptInvoice.Caption = "Invoice " & mInvoiceNo
    rptInvoice.Show
End Sub
