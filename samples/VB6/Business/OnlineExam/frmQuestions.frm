VERSION 5.00
Begin VB.Form frmQuestions 
   Caption         =   "Question bank"
   ClientHeight    =   5160
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   7680
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   5160
   ScaleWidth      =   7680
   Begin VB.ComboBox cboSubject 
      Height          =   315
      Left            =   1440
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   120
      Width           =   3255
   End
   Begin VB.TextBox txtQuestion 
      Height          =   735
      Left            =   1440
      MultiLine       =   -1  'True
      ScrollBars      =   2  'Vertical
      TabIndex        =   2
      Top             =   600
      Width           =   6015
   End
   Begin VB.TextBox txtOpt 
      Height          =   315
      Index           =   0
      Left            =   1440
      TabIndex        =   3
      Top             =   1440
      Width           =   6015
   End
   Begin VB.Label lblOpt 
      Caption         =   "Option A:"
      Height          =   255
      Index           =   0
      Left            =   240
      TabIndex        =   4
      Top             =   1500
      Width           =   1095
   End
   Begin VB.TextBox txtOpt 
      Height          =   315
      Index           =   1
      Left            =   1440
      TabIndex        =   5
      Top             =   1860
      Width           =   6015
   End
   Begin VB.Label lblOpt 
      Caption         =   "Option B:"
      Height          =   255
      Index           =   1
      Left            =   240
      TabIndex        =   6
      Top             =   1920
      Width           =   1095
   End
   Begin VB.TextBox txtOpt 
      Height          =   315
      Index           =   2
      Left            =   1440
      TabIndex        =   7
      Top             =   2280
      Width           =   6015
   End
   Begin VB.Label lblOpt 
      Caption         =   "Option C:"
      Height          =   255
      Index           =   2
      Left            =   240
      TabIndex        =   8
      Top             =   2340
      Width           =   1095
   End
   Begin VB.TextBox txtOpt 
      Height          =   315
      Index           =   3
      Left            =   1440
      TabIndex        =   9
      Top             =   2700
      Width           =   6015
   End
   Begin VB.Label lblOpt 
      Caption         =   "Option D:"
      Height          =   255
      Index           =   3
      Left            =   240
      TabIndex        =   10
      Top             =   2760
      Width           =   1095
   End
   Begin VB.ComboBox cboCorrect 
      Height          =   315
      Left            =   1440
      Style           =   2  'Dropdown List
      TabIndex        =   11
      Top             =   3180
      Width           =   855
   End
   Begin VB.TextBox txtMarks 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   3720
      TabIndex        =   12
      Text            =   "1"
      Top             =   3180
      Width           =   615
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   "|<"
      Height          =   375
      Index           =   0
      Left            =   240
      TabIndex        =   13
      Top             =   3840
      Width           =   480
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   "<"
      Height          =   375
      Index           =   1
      Left            =   720
      TabIndex        =   14
      Top             =   3840
      Width           =   480
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   ">"
      Height          =   375
      Index           =   2
      Left            =   1200
      TabIndex        =   15
      Top             =   3840
      Width           =   480
   End
   Begin VB.CommandButton cmdNav 
      Caption         =   ">|"
      Height          =   375
      Index           =   3
      Left            =   1680
      TabIndex        =   16
      Top             =   3840
      Width           =   480
   End
   Begin VB.CommandButton cmdNew 
      Caption         =   "&New"
      Height          =   375
      Left            =   2400
      TabIndex        =   17
      Top             =   3840
      Width           =   1095
   End
   Begin VB.CommandButton cmdSave 
      Caption         =   "&Save"
      Height          =   375
      Left            =   3600
      TabIndex        =   18
      Top             =   3840
      Width           =   1095
   End
   Begin VB.CommandButton cmdDelete 
      Caption         =   "&Delete"
      Height          =   375
      Left            =   4800
      TabIndex        =   19
      Top             =   3840
      Width           =   1095
   End
   Begin VB.CommandButton cmdFind 
      Caption         =   "&Find..."
      Height          =   375
      Left            =   6000
      TabIndex        =   20
      Top             =   3840
      Width           =   1095
   End
   Begin VB.Label lblSubject 
      Caption         =   "Subject:"
      Height          =   255
      Left            =   240
      TabIndex        =   21
      Top             =   180
      Width           =   1095
   End
   Begin VB.Label lblQuestion 
      Caption         =   "Question:"
      Height          =   255
      Left            =   240
      TabIndex        =   22
      Top             =   660
      Width           =   1095
   End
   Begin VB.Label lblCorrect 
      Caption         =   "Correct:"
      Height          =   255
      Left            =   240
      TabIndex        =   23
      Top             =   3240
      Width           =   1095
   End
   Begin VB.Label lblMarks 
      Caption         =   "Marks:"
      Height          =   255
      Left            =   2640
      TabIndex        =   24
      Top             =   3240
      Width           =   975
   End
   Begin VB.Label lblNav 
      Caption         =   "-"
      Height          =   255
      Left            =   240
      TabIndex        =   25
      Top             =   4440
      Width           =   3000
   End
   Begin VB.Label lblCount 
      Caption         =   "-"
      Height          =   255
      Left            =   4800
      TabIndex        =   26
      Top             =   180
      Width           =   2655
   End
End
Attribute VB_Name = "frmQuestions"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmQuestions - the question bank of one subject, edited record by record with a DAO dynaset:
' |< < > >| (a CommandButton array), New / Save (AddNew or Edit + Update), Delete, Find (FindFirst +
' NoMatch). The four answers are a TextBox control array txtOpt(0..3).
Option Explicit

Private rs As DAO.Recordset
Private mAdding As Boolean

Private Sub Form_Load()
    Dim i As Integer
    For i = 0 To 3
        cboCorrect.AddItem OptionLetter(i)
    Next
    FillSubjects cboSubject                 ' fires cboSubject_Click -> OpenSubject
    If rs Is Nothing Then OpenSubject
End Sub

Private Function CurrentSubject() As Long
    CurrentSubject = cboSubject.ItemData(cboSubject.ListIndex)
End Function

Private Sub OpenSubject()
    If Not rs Is Nothing Then rs.Close
    Set rs = db.OpenRecordset("SELECT * FROM Questions WHERE SubjectID = " & CurrentSubject() & " ORDER BY QID", _
                              dbOpenDynaset)
    If Not rs.EOF Then rs.MoveLast: rs.MoveFirst          ' DAO: RecordCount is exact after MoveLast
    mAdding = False
    ShowQuestion
End Sub

Private Sub cboSubject_Click()
    OpenSubject
End Sub

Private Sub ShowQuestion()
    Dim i As Integer
    lblCount.Caption = rs.RecordCount & " questions in this subject"
    If rs.EOF Or rs.BOF Then
        txtQuestion.Text = ""
        For i = 0 To 3: txtOpt(i).Text = "": Next
        lblNav.Caption = "no question"
        Exit Sub
    End If
    txtQuestion.Text = rs!QText & ""
    txtOpt(0).Text = rs!OptA & ""
    txtOpt(1).Text = rs!OptB & ""
    txtOpt(2).Text = rs!OptC & ""
    txtOpt(3).Text = rs!OptD & ""
    cboCorrect.ListIndex = OptionIndex(rs!Correct & "")
    txtMarks.Text = rs!Marks
    lblNav.Caption = "Question " & (rs.AbsolutePosition + 1) & " of " & rs.RecordCount & "  (id " & rs!QID & ")"
End Sub

Private Sub cmdNav_Click(Index As Integer)
    If rs.RecordCount = 0 Then Exit Sub
    Select Case Index
        Case 0: rs.MoveFirst
        Case 1
            rs.MovePrevious
            If rs.BOF Then rs.MoveFirst
        Case 2
            rs.MoveNext
            If rs.EOF Then rs.MoveLast
        Case 3: rs.MoveLast
    End Select
    mAdding = False
    ShowQuestion
End Sub

Private Sub cmdNew_Click()
    Dim i As Integer
    mAdding = True
    txtQuestion.Text = ""
    For i = 0 To 3: txtOpt(i).Text = "": Next
    cboCorrect.ListIndex = 0
    txtMarks.Text = "1"
    lblNav.Caption = "new question"
    txtQuestion.SetFocus
End Sub

Private Sub cmdSave_Click()
    Dim i As Integer
    If Trim$(txtQuestion.Text) = "" Then
        MsgBox "Type the question.", vbExclamation
        Exit Sub
    End If
    For i = 0 To 3
        If Trim$(txtOpt(i).Text) = "" Then
            MsgBox "Option " & OptionLetter(i) & " is empty.", vbExclamation
            txtOpt(i).SetFocus
            Exit Sub
        End If
    Next
    If Not IsNumeric(txtMarks.Text) Then
        MsgBox "Marks must be a number.", vbExclamation
        Exit Sub
    End If
    If mAdding Then rs.AddNew Else rs.Edit
    rs!SubjectID = CurrentSubject()
    rs!QText = Trim$(txtQuestion.Text)
    rs!OptA = txtOpt(0).Text
    rs!OptB = txtOpt(1).Text
    rs!OptC = txtOpt(2).Text
    rs!OptD = txtOpt(3).Text
    rs!Correct = cboCorrect.Text
    rs!Marks = CInt(txtMarks.Text)
    rs.Update
    If mAdding Then rs.Bookmark = rs.LastModified
    mAdding = False
    ShowQuestion
End Sub

Private Sub cmdDelete_Click()
    If rs.EOF Or rs.BOF Then Exit Sub
    If db.OpenRecordset("SELECT COUNT(*) FROM PaperQuestions WHERE QID = " & rs!QID).Fields(0).Value > 0 Then
        MsgBox "This question is used in a question paper; remove it from the paper first.", vbExclamation
        Exit Sub
    End If
    If MsgBox("Delete this question?", vbYesNo + vbQuestion) = vbNo Then Exit Sub
    rs.Delete
    rs.MoveNext
    If rs.EOF And rs.RecordCount > 0 Then rs.MoveLast
    ShowQuestion
End Sub

Private Sub cmdFind_Click()
    Dim s As String
    s = InputBox("A word of the question:", "Find question")
    If s = "" Then Exit Sub
    rs.FindFirst "QText LIKE '*" & Replace(s, "'", "''") & "*'"
    If rs.NoMatch Then MsgBox "Not found: " & s, vbInformation Else ShowQuestion
End Sub

Private Sub Form_Unload(Cancel As Integer)
    If Not rs Is Nothing Then rs.Close
    Set rs = Nothing
End Sub
