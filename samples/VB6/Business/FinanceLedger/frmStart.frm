VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmStart
   BackColor       =   &H00404000&
   BorderStyle     =   1  'Fixed Single
   Caption         =   "FinanceLedger"
   ClientHeight    =   3240
   ClientLeft      =   45
   ClientTop       =   435
   ClientWidth     =   5400
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   3240
   ScaleWidth      =   5400
   StartUpPosition =   2  'CenterScreen
   Begin VB.Timer tmrProgress
      Interval        =   30
      Left            =   4800
      Top             =   120
   End
   Begin VB.Frame fraLogin
      BackColor       =   &H00404000&
      Caption         =   "Sign in"
      ForeColor       =   &H00FFFFFF&
      Height          =   1335
      Left            =   240
      TabIndex        =   2
      Top             =   1680
      Visible         =   0   'False
      Width           =   4935
      Begin VB.CommandButton cmdSignIn
         Caption         =   "&OK"
         Default         =   -1  'True
         Height          =   375
         Left            =   3720
         TabIndex        =   7
         Top             =   780
         Width           =   1095
      End
      Begin VB.TextBox txtPwd
         Height          =   315
         Left            =   1200
         PasswordChar    =   "*"
         TabIndex        =   6
         Top             =   780
         Width           =   2295
      End
      Begin VB.TextBox txtUser
         Height          =   315
         Left            =   1200
         TabIndex        =   4
         Text            =   "admin"
         Top             =   360
         Width           =   2295
      End
      Begin VB.Label lblPwd
         BackStyle       =   0  'Transparent
         Caption         =   "Password"
         ForeColor       =   &H00FFFFFF&
         Height          =   255
         Left            =   120
         TabIndex        =   5
         Top             =   840
         Width           =   975
      End
      Begin VB.Label lblUser
         BackStyle       =   0  'Transparent
         Caption         =   "User"
         ForeColor       =   &H00FFFFFF&
         Height          =   255
         Left            =   120
         TabIndex        =   3
         Top             =   420
         Width           =   975
      End
   End
   Begin MSComctlLib.ProgressBar prgStart
      Height          =   255
      Left            =   240
      TabIndex        =   1
      Top             =   1200
      Width           =   4935
      _ExtentX        =   8705
      _ExtentY        =   450
      _Version        =   393216
      Appearance      =   0
      Scrolling       =   1
   End
   Begin VB.Label lblTitle
      Alignment       =   2  'Center
      BackStyle       =   0  'Transparent
      Caption         =   "FinanceLedger"
      BeginProperty Font
         Name            =   "Georgia"
         Size            =   20.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H0080FFFF&
      Height          =   615
      Left            =   240
      TabIndex        =   0
      Top             =   360
      Width           =   4935
   End
End
Attribute VB_Name = "frmStart"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmStart - splash and sign-in on one form. The Timer changes its own Interval: the bar runs fast,
' slows down in the middle and speeds up again; when it is full the sign-in frame appears.
Option Explicit

Private Sub Form_Load()
    OpenDb
End Sub

Private Sub tmrProgress_Timer()
    prgStart.Value = prgStart.Value + 2
    Select Case prgStart.Value
        Case 40 To 60: tmrProgress.Interval = 60      ' "loading the ledger..."
        Case Else:     tmrProgress.Interval = 15
    End Select
    If prgStart.Value >= prgStart.Max Then
        tmrProgress.Enabled = False
        prgStart.Visible = False
        fraLogin.Visible = True
    End If
End Sub

Private Sub cmdSignIn_Click()
    If ScalarValue("SELECT COUNT(*) FROM Users WHERE UserName = " & SqlText(txtUser.Text) & _
                   " AND Pwd = " & SqlText(txtPwd.Text)) = 0 Then
        MsgBox "Wrong user name or password.", vbExclamation
        Exit Sub
    End If
    gUser = txtUser.Text
    frmLedger.Show
    Unload Me
End Sub
