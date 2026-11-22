VERSION 5.00
Begin VB.MDIForm mdiAdmin 
   BackColor       =   &H8000000C&
   Caption         =   "OnlineExam - administration"
   ClientHeight    =   6000
   ClientLeft      =   165
   ClientTop       =   855
   ClientWidth     =   9000
   LinkTopic       =   "MDIForm1"
   StartUpPosition =   2  'CenterScreen
   Begin VB.Menu mnuFile 
      Caption         =   "&File"
      Begin VB.Menu mnuSignOut 
         Caption         =   "&Sign out"
      End
      Begin VB.Menu mnuFileSep 
         Caption         =   "-"
      End
      Begin VB.Menu mnuExit 
         Caption         =   "E&xit"
      End
   End
   Begin VB.Menu mnuExam 
      Caption         =   "&Exam"
      Begin VB.Menu mnuQuestions 
         Caption         =   "&Question bank..."
      End
      Begin VB.Menu mnuPaper 
         Caption         =   "Question &paper..."
      End
      Begin VB.Menu mnuExamSep 
         Caption         =   "-"
      End
      Begin VB.Menu mnuStudents 
         Caption         =   "S&tudents"
         Begin VB.Menu mnuAddStudent 
            Caption         =   "&Add student..."
         End
         Begin VB.Menu mnuListStudents 
            Caption         =   "&List students"
         End
      End
   End
   Begin VB.Menu mnuReports 
      Caption         =   "&Reports"
      Begin VB.Menu mnuResults 
         Caption         =   "&Results..."
      End
   End
End
Attribute VB_Name = "mdiAdmin"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' mdiAdmin - the examiner's MDI window; menus two levels deep with separators.
Option Explicit

Private Sub MDIForm_Load()
    Me.Caption = "OnlineExam - administration (" & gFullName & ")"
End Sub

Private Sub mnuQuestions_Click()
    frmQuestions.Show
End Sub

Private Sub mnuPaper_Click()
    frmPaper.Show
End Sub

Private Sub mnuResults_Click()
    frmResults.Show
End Sub

Private Sub mnuAddStudent_Click()
    Dim user As String, name As String
    user = LCase$(Trim$(InputBox("User name of the new student:", "Add student")))
    If user = "" Then Exit Sub
    If db.OpenRecordset("SELECT COUNT(*) FROM Users WHERE UserName = " & SqlQ(user)).Fields(0).Value > 0 Then
        MsgBox "The user " & user & " already exists.", vbExclamation
        Exit Sub
    End If
    name = InputBox("Full name of " & user & ":", "Add student", user)
    db.Execute "INSERT INTO Users VALUES (" & SqlQ(user) & ", " & SqlQ(user) & ", 'student', " & SqlQ(name) & ")"
    MsgBox "Student " & user & " added. The first password is the user name.", vbInformation
End Sub

Private Sub mnuListStudents_Click()
    Dim rs As DAO.Recordset, s As String
    Set rs = db.OpenRecordset("SELECT UserName, FullName FROM Users WHERE Role = 'student' ORDER BY UserName", dbOpenSnapshot)
    Do Until rs.EOF
        s = s & rs!UserName & " - " & rs!FullName & vbCrLf
        rs.MoveNext
    Loop
    rs.Close
    MsgBox s, vbInformation, "Students"
End Sub

Private Sub mnuSignOut_Click()
    Unload Me
    frmWelcome.txtPwd.Text = ""
    frmWelcome.Show
End Sub

Private Sub mnuExit_Click()
    Unload Me
    Unload frmWelcome
End Sub
