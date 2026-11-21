VERSION 5.00
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Begin VB.Form frmGrid 
   Caption         =   "Products (ADO + MSFlexGrid)"
   ClientHeight    =   4200
   ClientLeft      =   60
   ClientTop       =   450
   ClientWidth     =   6600
   LinkTopic       =   "Form1"
   ScaleHeight     =   4200
   ScaleWidth      =   6600
   StartUpPosition =   3  'Windows Default
   Begin MSFlexGridLib.MSFlexGrid grdProducts 
      Height          =   2895
      Left            =   120
      TabIndex        =   0
      Top             =   600
      Width           =   6375
      _ExtentX        =   11245
      _ExtentY        =   5106
      _Version        =   393216
      Rows            =   2
      Cols            =   4
      FormatString    =   "<ID|<Name|>Price|>Stock"
   End
   Begin MSComCtl2.DTPicker dtpAdded 
      Height          =   315
      Left            =   120
      TabIndex        =   1
      Top             =   120
      Width           =   1815
      _ExtentX        =   3201
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   46023
   End
   Begin VB.CommandButton cmdReload 
      Caption         =   "&Reload"
      Height          =   375
      Left            =   5280
      TabIndex        =   2
      Top             =   3600
      Width           =   1215
   End
   Begin VB.Label lblCount 
      Caption         =   "0 products"
      Height          =   255
      Left            =   2160
      TabIndex        =   3
      Top             =   180
      Width           =   3000
   End
End
Attribute VB_Name = "frmGrid"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Sub Form_Load()
    LoadGrid
End Sub

Private Sub LoadGrid()
    Dim rs As ADODB.Recordset, r As Integer
    Set rs = New ADODB.Recordset
    rs.Open "select ID, Name, Price, Stock from Products where Added >= #" & _
            Format(dtpAdded.Value, "mm/dd/yyyy") & "# order by ID", cn, adOpenStatic, adLockReadOnly
    grdProducts.Rows = rs.RecordCount + 1
    grdProducts.ColWidth(1) = 2400
    r = 1
    Do Until rs.EOF
        grdProducts.TextMatrix(r, 0) = rs!ID
        grdProducts.TextMatrix(r, 1) = rs!Name
        grdProducts.TextMatrix(r, 2) = Format(rs!Price, "0.00")
        grdProducts.TextMatrix(r, 3) = rs!Stock
        r = r + 1
        rs.MoveNext
    Loop
    lblCount.Caption = rs.RecordCount & " products since " & Format(dtpAdded.Value, "dd/mm/yyyy")
    Debug.Print "grid rows=" & (grdProducts.Rows - 1) & " header=" & grdProducts.TextMatrix(0, 1) & _
                " first=" & grdProducts.TextMatrix(1, 1)
    rs.Close
End Sub

Private Sub cmdReload_Click()
    LoadGrid
End Sub

Private Sub Form_Unload(Cancel As Integer)
    cn.Close
End Sub
