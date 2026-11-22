VERSION 5.00
Begin VB.Form frmLogin 
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "PharmacyStore - login"
   ClientHeight    =   1920
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   4200
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   1920
   ScaleWidth      =   4200
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton cmdLogin 
      Caption         =   "&Login"
      Default         =   -1  'True
      Height          =   375
      Left            =   2760
      TabIndex        =   4
      Top             =   1320
      Width           =   1215
   End
   Begin VB.TextBox txtPassword 
      Height          =   315
      Left            =   1320
      PasswordChar    =   "*"
      TabIndex        =   3
      Top             =   720
      Width           =   2655
   End
   Begin VB.TextBox txtUser 
      Height          =   315
      Left            =   1320
      TabIndex        =   1
      Top             =   240
      Width           =   2655
   End
   Begin VB.Label lblPassword 
      Caption         =   "Password:"
      Height          =   255
      Left            =   240
      TabIndex        =   2
      Top             =   780
      Width           =   975
   End
   Begin VB.Label lblUser 
      Caption         =   "User:"
      Height          =   255
      Left            =   240
      TabIndex        =   0
      Top             =   300
      Width           =   975
   End
   Begin VB.Label lblDemo 
      Caption         =   "demo: admin / admin"
      ForeColor       =   &H00808080&
      Height          =   255
      Left            =   240
      TabIndex        =   5
      Top             =   1380
      Width           =   2415
   End
End
Attribute VB_Name = "frmLogin"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmLogin - checks the Users table, then opens the MDI window.
Option Explicit

Private Sub cmdLogin_Click()
    Dim rs As ADODB.Recordset
    Set rs = New ADODB.Recordset
    rs.Open "SELECT FullName FROM Users WHERE UserName = " & SqlStr(txtUser.Text) & " AND Pwd = " & _
            SqlStr(txtPassword.Text), cn, adOpenStatic, adLockReadOnly
    If rs.RecordCount = 0 Then
        MsgBox "Login failed.", vbCritical
        txtPassword.Text = ""
    Else
        gUser = txtUser.Text
        Unload Me
        mdiStore.Show
    End If
    rs.Close
End Sub
