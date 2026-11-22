VERSION 5.00
Begin VB.MDIForm mdiStore 
   BackColor       =   &H00C0C0C0&
   Caption         =   "PharmacyStore"
   ClientHeight    =   6000
   ClientLeft      =   165
   ClientTop       =   855
   ClientWidth     =   9600
   LinkTopic       =   "MDIForm1"
   StartUpPosition =   2  'CenterScreen
   Begin VB.PictureBox picStatus 
      Align           =   2  'Align Bottom
      Height          =   375
      Left            =   0
      ScaleHeight     =   315
      ScaleWidth      =   9540
      TabIndex        =   0
      Top             =   5625
      Width           =   9600
      Begin VB.Label lblStatus 
         Caption         =   "-"
         Height          =   255
         Left            =   60
         TabIndex        =   1
         Top             =   30
         Width           =   9375
      End
   End
   Begin VB.Menu mnuStock 
      Caption         =   "&Stock"
      Begin VB.Menu mnuMedicines 
         Caption         =   "&Medicines..."
      End
      Begin VB.Menu mnuPurchase 
         Caption         =   "&Purchase (stock in)..."
      End
      Begin VB.Menu mnuStockSep 
         Caption         =   "-"
      End
      Begin VB.Menu mnuExit 
         Caption         =   "E&xit"
      End
   End
   Begin VB.Menu mnuSales 
      Caption         =   "S&ales"
      Begin VB.Menu mnuNewSale 
         Caption         =   "&New invoice..."
         Shortcut        =   {F2}
      End
   End
   Begin VB.Menu mnuReports 
      Caption         =   "&Reports"
      Begin VB.Menu mnuAlerts 
         Caption         =   "&Low stock and expiry..."
      End
      Begin VB.Menu mnuMore 
         Caption         =   "&More"
         Begin VB.Menu mnuTodaySales 
            Caption         =   "&Today's sales"
         End
         Begin VB.Menu mnuStockLog 
            Caption         =   "Stock &log count"
         End
      End
   End
End
Attribute VB_Name = "mdiStore"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' mdiStore - MDI parent with a status bar made of a PictureBox aligned to the bottom; a nested
' (second-level) menu under Reports > More.
Option Explicit

Private Sub MDIForm_Load()
    Me.Caption = "PharmacyStore - " & gUser
    ShowAlertsInStatus
End Sub

Public Sub ShowAlertsInStatus()
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT COUNT(*) FROM Medicines WHERE Stock <= ReorderLevel")
    lblStatus.Caption = "User " & gUser & "   |   medicines to reorder: " & rs(0)
    rs.Close
End Sub

Private Sub mnuMedicines_Click()
    frmMedicines.Show
End Sub

Private Sub mnuPurchase_Click()
    frmPurchase.Show
End Sub

Private Sub mnuNewSale_Click()
    frmSale.Show
End Sub

Private Sub mnuAlerts_Click()
    frmAlerts.Show
End Sub

Private Sub mnuTodaySales_Click()
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT COUNT(*), SUM(Total) FROM Sales WHERE SaleDate = Date()")
    MsgBox "Invoices today: " & rs(0) & vbCrLf & "Total: " & Format$(IIf(IsNull(rs(1)), 0, rs(1)), "#,##0.00"), _
           vbInformation, "Today's sales"
    rs.Close
End Sub

Private Sub mnuStockLog_Click()
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT COUNT(*) FROM StockLog")
    MsgBox "Stock movements logged: " & rs(0), vbInformation
    rs.Close
End Sub

Private Sub mnuExit_Click()
    Unload Me
End Sub

Private Sub MDIForm_QueryUnload(Cancel As Integer, UnloadMode As Integer)
    If MsgBox("Exit PharmacyStore?", vbYesNo + vbQuestion) = vbNo Then Cancel = True
End Sub
