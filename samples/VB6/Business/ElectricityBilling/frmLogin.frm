VERSION 5.00
Begin VB.Form frmLogin
   BackColor       =   &H00E0E0E0&
   BorderStyle     =   1  'Fixed Single
   Caption         =   "ElectricityBilling - sign in"
   ClientHeight    =   2655
   ClientLeft      =   45
   ClientTop       =   435
   ClientWidth     =   5070
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   2655
   ScaleWidth      =   5070
   StartUpPosition =   2  'CenterScreen
   Begin VB.Frame fraLogin
      BackColor       =   &H00E0E0E0&
      Caption         =   "Meter office"
      Height          =   1695
      Left            =   1200
      TabIndex        =   0
      Top             =   120
      Width           =   3735
      Begin VB.TextBox txtPwd
         Height          =   315
         Left            =   1320
         PasswordChar    =   "*"
         TabIndex        =   4
         Top             =   960
         Width           =   2175
      End
      Begin VB.TextBox txtUser
         Height          =   315
         Left            =   1320
         TabIndex        =   2
         Top             =   420
         Width           =   2175
      End
      Begin VB.Label lblPwd
         BackStyle       =   0  'Transparent
         Caption         =   "Password"
         Height          =   255
         Left            =   240
         TabIndex        =   3
         Top             =   1000
         Width           =   975
      End
      Begin VB.Label lblUser
         BackStyle       =   0  'Transparent
         Caption         =   "User"
         Height          =   255
         Left            =   240
         TabIndex        =   1
         Top             =   460
         Width           =   975
      End
   End
   Begin VB.CommandButton cmdExit
      Caption         =   "E&xit"
      Height          =   375
      Left            =   3720
      TabIndex        =   6
      Top             =   2040
      Width           =   1215
   End
   Begin VB.CommandButton cmdLogin
      Caption         =   "&Login"
      Default         =   -1  'True
      Height          =   375
      Left            =   2400
      TabIndex        =   5
      Top             =   2040
      Width           =   1215
   End
   Begin VB.Shape shpBolt
      BackColor       =   &H0000C0C0&
      BackStyle       =   1  'Opaque
      BorderColor     =   &H00004080&
      Height          =   855
      Left            =   240
      Shape           =   3  'Circle
      Top             =   360
      Width           =   855
   End
   Begin VB.Label lblDemo
      BackStyle       =   0  'Transparent
      Caption         =   "admin / admin"
      ForeColor       =   &H00808080&
      Height          =   255
      Left            =   120
      TabIndex        =   7
      Top             =   2100
      Width           =   2055
   End
End
Attribute VB_Name = "frmLogin"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmLogin - the startup form: opens the database, checks the Users table and opens frmMain.
Option Explicit

Private Sub Form_Load()
    On Error GoTo NoDb
    OpenDb
    Exit Sub
NoDb:
    MsgBox "billing.mdb could not be opened: " & Err.Description, vbCritical
    End
End Sub

Private Sub cmdLogin_Click()
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT Role FROM Users WHERE UserName = " & Q(txtUser.Text) & " AND Pwd = " & Q(txtPwd.Text))
    If rs.EOF Then
        MsgBox "Unknown user or wrong password.", vbExclamation, "Sign in"
        txtPwd.SetFocus
    Else
        gUser = txtUser.Text
        gRole = rs!Role
        frmMain.Show
        Unload Me
    End If
    rs.Close
End Sub

Private Sub cmdExit_Click()
    Unload Me
End Sub
