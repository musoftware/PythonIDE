VERSION 5.00
Begin VB.Form frmLogin
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "Sign in"
   ClientHeight    =   2280
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   4560
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   2280
   ScaleWidth      =   4560
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton cmdCancel
      Cancel          =   -1  'True
      Caption         =   "Cancel"
      Height          =   375
      Left            =   3120
      TabIndex        =   5
      Top             =   1680
      Width           =   1215
   End
   Begin VB.CommandButton cmdOK
      Caption         =   "&Sign in"
      Default         =   -1  'True
      Height          =   375
      Left            =   1800
      TabIndex        =   4
      Top             =   1680
      Width           =   1215
   End
   Begin VB.TextBox txtPassword
      Height          =   315
      IMEMode         =   3  'DISABLE
      Left            =   1440
      PasswordChar    =   "*"
      TabIndex        =   3
      Top             =   720
      Width           =   2895
   End
   Begin VB.TextBox txtUser
      Height          =   315
      Left            =   1440
      TabIndex        =   1
      Top             =   240
      Width           =   2895
   End
   Begin VB.Label lblHint
      Caption         =   "Demo accounts: admin / admin  or  teller / teller"
      ForeColor       =   &H00808080&
      Height          =   255
      Left            =   240
      TabIndex        =   6
      Top             =   1200
      Width           =   4095
   End
   Begin VB.Label lblPassword
      Caption         =   "&Password:"
      Height          =   255
      Left            =   240
      TabIndex        =   2
      Top             =   765
      Width           =   1095
   End
   Begin VB.Label lblUser
      Caption         =   "&User name:"
      Height          =   255
      Left            =   240
      TabIndex        =   0
      Top             =   285
      Width           =   1095
   End
End
Attribute VB_Name = "frmLogin"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmLogin - checks the Users table; three wrong tries end the program.
Option Explicit

Private mTries As Integer

Private Sub cmdOK_Click()
    Dim rs As ADODB.Recordset
    If Trim$(txtUser.Text) = "" Then
        MsgBox "Please type your user name.", vbExclamation, APP_TITLE
        txtUser.SetFocus
        Exit Sub
    End If
    Set rs = New ADODB.Recordset
    rs.Open "SELECT FullName, Role FROM Users WHERE UserName = " & Q(Trim$(txtUser.Text)) & _
            " AND Pwd = " & Q(txtPassword.Text), cn, adOpenStatic, adLockReadOnly
    If rs.EOF Then
        rs.Close
        mTries = mTries + 1
        If mTries >= 3 Then
            MsgBox "Too many wrong tries. The program will close.", vbCritical, APP_TITLE
            End
        End If
        MsgBox "Wrong user name or password (" & (3 - mTries) & " tries left).", vbExclamation, APP_TITLE
        txtPassword.Text = ""
        Exit Sub
    End If
    gUserName = Trim$(txtUser.Text)
    gRole = rs!Role & ""
    rs.Close
    LogActivity "signed in"
    mdiMain.Show
    Unload Me
End Sub

Private Sub cmdCancel_Click()
    End
End Sub
