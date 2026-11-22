VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.MDIForm mdiMain
   BackColor       =   &H8000000C&
   Caption         =   "BankManager"
   ClientHeight    =   6600
   ClientLeft      =   165
   ClientTop       =   855
   ClientWidth     =   9600
   LinkTopic       =   "MDIForm1"
   StartUpPosition =   2  'CenterScreen
   Begin MSComctlLib.StatusBar sbMain
      Align           =   2  'Align Bottom
      Height          =   315
      Left            =   0
      TabIndex        =   0
      Top             =   6285
      Width           =   9600
      _ExtentX        =   16933
      _ExtentY        =   556
      Style           =   1
      SimpleText      =   "Ready"
      _Version        =   393216
   End
   Begin VB.Menu mnuFile
      Caption         =   "&File"
      Begin VB.Menu mnuFileLog
         Caption         =   "Open activity &log"
      End
      Begin VB.Menu mnuFileSep1
         Caption         =   "-"
      End
      Begin VB.Menu mnuFileExit
         Caption         =   "E&xit"
      End
   End
   Begin VB.Menu mnuCustomers
      Caption         =   "&Customers"
      Begin VB.Menu mnuCustAccounts
         Caption         =   "&Accounts..."
         Shortcut        =   ^A
      End
   End
   Begin VB.Menu mnuTxn
      Caption         =   "&Transactions"
      Begin VB.Menu mnuTxnPost
         Caption         =   "&Deposit / Withdraw..."
         Shortcut        =   ^D
      End
      Begin VB.Menu mnuTxnStatement
         Caption         =   "Account &statement..."
         Shortcut        =   ^S
      End
   End
   Begin VB.Menu mnuReports
      Caption         =   "&Reports"
      Begin VB.Menu mnuRptBalances
         Caption         =   "Customer &balances"
      End
   End
   Begin VB.Menu mnuWindow
      Caption         =   "&Window"
      WindowList      =   -1  'True
      Begin VB.Menu mnuWinCascade
         Caption         =   "&Cascade"
      End
      Begin VB.Menu mnuWinTile
         Caption         =   "&Tile"
      End
   End
   Begin VB.Menu mnuHelp
      Caption         =   "&Help"
      Begin VB.Menu mnuHelpAbout
         Caption         =   "&About BankManager..."
      End
   End
End
Attribute VB_Name = "mdiMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' mdiMain - the MDI parent window: menus open the MDI child forms; the status bar shows who is
' signed in. Only an admin may open the customer balances report.
Option Explicit

Private Sub MDIForm_Load()
    Me.Caption = AppSetting("BankName", APP_TITLE) & " - " & gUserName
    sbMain.SimpleText = "Signed in as " & gUserName & " (" & gRole & ")   " & Format$(Date, "dddd, d mmmm yyyy")
    mnuRptBalances.Enabled = (gRole = "admin")
End Sub

Private Sub MDIForm_Unload(Cancel As Integer)
    If MsgBox("Close BankManager?", vbQuestion + vbYesNo, APP_TITLE) = vbNo Then
        Cancel = 1
        Exit Sub
    End If
    LogActivity "signed out"
    cn.Close
End Sub

Private Sub mnuCustAccounts_Click()
    frmCustomers.Show
    frmCustomers.ZOrder 0
End Sub

Private Sub mnuTxnPost_Click()
    frmTransaction.Show
End Sub

Private Sub mnuTxnStatement_Click()
    frmStatement.Show
End Sub

Private Sub mnuRptBalances_Click()
    ' DataReport bound to the DataEnvironment command cmdBalances
    rptBalances.Show
End Sub

Private Sub mnuFileLog_Click()
    Shell "notepad.exe """ & App.Path & "\bank.log""", vbNormalFocus
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub mnuWinCascade_Click()
    Me.Arrange vbCascade
End Sub

Private Sub mnuWinTile_Click()
    Me.Arrange vbTileHorizontal
End Sub

Private Sub mnuHelpAbout_Click()
    frmAbout.Show vbModal, Me
End Sub
