VERSION 5.00
Begin VB.Form frmWelcome 
   BorderStyle     =   1  'Fixed Single
   Caption         =   "OnlineExam"
   ClientHeight    =   3480
   ClientLeft      =   45
   ClientTop       =   435
   ClientWidth     =   5280
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   3480
   ScaleWidth      =   5280
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton cmdQuit 
      Cancel          =   -1  'True
      Caption         =   "&Quit"
      Height          =   375
      Left            =   3960
      TabIndex        =   11
      Top             =   2940
      Width           =   1095
   End
   Begin VB.CommandButton cmdSignIn 
      Caption         =   "&Sign in"
      Default         =   -1  'True
      Height          =   375
      Left            =   2760
      TabIndex        =   10
      Top             =   2940
      Width           =   1095
   End
   Begin VB.ComboBox cboSubject 
      Height          =   315
      Left            =   1560
      Style           =   2  'Dropdown List
      TabIndex        =   9
      Top             =   2400
      Width           =   3495
   End
   Begin VB.TextBox txtPwd 
      Height          =   315
      Left            =   1560
      PasswordChar    =   "*"
      TabIndex        =   7
      Top             =   1920
      Width           =   3495
   End
   Begin VB.TextBox txtUser 
      Height          =   315
      Left            =   1560
      TabIndex        =   5
      Top             =   1440
      Width           =   3495
   End
   Begin VB.Frame fraRole 
      Caption         =   "I am"
      Height          =   735
      Left            =   240
      TabIndex        =   1
      Top             =   600
      Width           =   4815
      Begin VB.OptionButton optRole 
         Caption         =   "an examiner"
         Height          =   255
         Index           =   1
         Left            =   2520
         TabIndex        =   3
         Top             =   300
         Width           =   2055
      End
      Begin VB.OptionButton optRole 
         Caption         =   "a student"
         Height          =   255
         Index           =   0
         Left            =   240
         TabIndex        =   2
         Top             =   300
         Value           =   -1  'True
         Width           =   2055
      End
   End
   Begin VB.Label lblSubject 
      Caption         =   "Exam:"
      Height          =   255
      Left            =   240
      TabIndex        =   8
      Top             =   2460
      Width           =   1215
   End
   Begin VB.Label lblPwd 
      Caption         =   "Password:"
      Height          =   255
      Left            =   240
      TabIndex        =   6
      Top             =   1980
      Width           =   1215
   End
   Begin VB.Label lblUser 
      Caption         =   "User name:"
      Height          =   255
      Left            =   240
      TabIndex        =   4
      Top             =   1500
      Width           =   1215
   End
   Begin VB.Label lblTitle 
      Caption         =   "Welcome - demo users: student1 / student1, admin / admin"
      Height          =   375
      Left            =   240
      TabIndex        =   0
      Top             =   180
      Width           =   4815
   End
End
Attribute VB_Name = "frmWelcome"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmWelcome - the startup form: a student picks an exam and starts it, an examiner opens the
' MDI administration window. The role is an OptionButton control array.
Option Explicit

Private Sub Form_Load()
    Dim rs As DAO.Recordset
    OpenDb
    ' only subjects that have a question paper can be taken
    Set rs = db.OpenRecordset("SELECT s.SubjectID, s.SubjectName FROM Subjects s INNER JOIN Papers p " & _
                              "ON s.SubjectID = p.SubjectID ORDER BY s.SubjectID", dbOpenSnapshot)
    Do Until rs.EOF
        cboSubject.AddItem rs!SubjectName
        cboSubject.ItemData(cboSubject.NewIndex) = rs!SubjectID
        rs.MoveNext
    Loop
    rs.Close
    If cboSubject.ListCount > 0 Then cboSubject.ListIndex = 0
End Sub

Private Sub optRole_Click(Index As Integer)
    cboSubject.Enabled = (Index = 0)
    lblSubject.Enabled = (Index = 0)
End Sub

Private Sub cmdSignIn_Click()
    Dim rs As DAO.Recordset, wanted As String
    wanted = IIf(optRole(0).Value, "student", "admin")
    Set rs = db.OpenRecordset("SELECT FullName, Role FROM Users WHERE UserName = " & SqlQ(txtUser.Text) & _
                              " AND Pwd = " & SqlQ(txtPwd.Text), dbOpenSnapshot)
    If rs.EOF Then
        MsgBox "Wrong user name or password.", vbExclamation
    ElseIf rs!Role <> wanted Then
        MsgBox "This account is not " & IIf(wanted = "admin", "an examiner", "a student") & " account.", vbExclamation
    Else
        gUser = txtUser.Text
        gFullName = rs!FullName
        gRole = rs!Role
        If gRole = "admin" Then
            mdiAdmin.Show
        Else
            If cboSubject.ListIndex < 0 Then
                MsgBox "There is no exam to take yet.", vbInformation
                rs.Close
                Exit Sub
            End If
            frmExam.StartExam cboSubject.ItemData(cboSubject.ListIndex)
            frmExam.Show
        End If
        Me.Hide
    End If
    rs.Close
End Sub

Private Sub cmdQuit_Click()
    Unload Me
End Sub
