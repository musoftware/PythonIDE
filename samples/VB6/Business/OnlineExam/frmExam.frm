VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmExam 
   BorderStyle     =   1  'Fixed Single
   Caption         =   "Exam"
   ClientHeight    =   4920
   ClientLeft      =   45
   ClientTop       =   435
   ClientWidth     =   7680
   ControlBox      =   0   'False
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   4920
   ScaleWidth      =   7680
   StartUpPosition =   2  'CenterScreen
   Begin VB.Timer tmrCountdown 
      Enabled         =   0   'False
      Interval        =   1000
      Left            =   7080
      Top             =   4320
   End
   Begin MSComctlLib.ProgressBar prgAnswered 
      Height          =   255
      Left            =   240
      TabIndex        =   9
      Top             =   3900
      Width           =   7215
      _ExtentX        =   12726
      _ExtentY        =   450
      _Version        =   393216
      Appearance      =   1
   End
   Begin VB.CommandButton cmdFinish 
      Caption         =   "&Finish"
      Height          =   375
      Left            =   6120
      TabIndex        =   8
      Top             =   4320
      Width           =   1335
   End
   Begin VB.CommandButton cmdNext 
      Caption         =   "&Next >"
      Height          =   375
      Left            =   1560
      TabIndex        =   7
      Top             =   4320
      Width           =   1215
   End
   Begin VB.CommandButton cmdPrev 
      Caption         =   "< &Previous"
      Height          =   375
      Left            =   240
      TabIndex        =   6
      Top             =   4320
      Width           =   1215
   End
   Begin VB.Frame fraAnswers 
      Caption         =   "Your answer"
      Height          =   2055
      Left            =   240
      TabIndex        =   1
      Top             =   1680
      Width           =   7215
      Begin VB.OptionButton optAns 
         Caption         =   "A"
         Height          =   375
         Index           =   0
         Left            =   240
         TabIndex        =   2
         Top             =   300
         Width           =   6735
      End
      Begin VB.OptionButton optAns 
         Caption         =   "B"
         Height          =   375
         Index           =   1
         Left            =   240
         TabIndex        =   3
         Top             =   720
         Width           =   6735
      End
      Begin VB.OptionButton optAns 
         Caption         =   "C"
         Height          =   375
         Index           =   2
         Left            =   240
         TabIndex        =   4
         Top             =   1140
         Width           =   6735
      End
      Begin VB.OptionButton optAns 
         Caption         =   "D"
         Height          =   375
         Index           =   3
         Left            =   240
         TabIndex        =   5
         Top             =   1560
         Width           =   6735
      End
   End
   Begin VB.Label lblQuestion 
      Caption         =   "-"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   855
      Left            =   240
      TabIndex        =   0
      Top             =   720
      Width           =   7215
   End
   Begin VB.Label lblProgress 
      Caption         =   "-"
      Height          =   255
      Left            =   240
      TabIndex        =   10
      Top             =   360
      Width           =   3495
   End
   Begin VB.Label lblTime 
      Alignment       =   1  'Right Justify
      Caption         =   "00:00"
      BeginProperty Font 
         Name            =   "Courier New"
         Size            =   14.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H00800000&
      Height          =   375
      Left            =   5760
      TabIndex        =   11
      Top             =   240
      Width           =   1695
   End
   Begin VB.Label lblStudent 
      Caption         =   "-"
      ForeColor       =   &H00808080&
      Height          =   255
      Left            =   240
      TabIndex        =   12
      Top             =   60
      Width           =   5295
   End
End
Attribute VB_Name = "frmExam"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmExam - the student's exam: the questions of the paper are read into a dynamic array of a
' user-defined type (ReDim Preserve), shown one at a time with an OptionButton array for the four
' answers, a Timer counts down and ends the exam when the time is up, a ProgressBar shows how many
' questions are answered. Finish marks the answers, saves Results + Answers (DAO AddNew) and shows
' the score card.
Option Explicit

Private mQ() As ExamQuestion
Private mCount As Integer
Private mCur As Integer
Private mSecondsLeft As Long
Private mSubject As Long
Private mPassPercent As Integer
Private mFinished As Boolean

Public Sub StartExam(ByVal SubjectID As Long)
    Dim rs As DAO.Recordset
    mSubject = SubjectID
    mCount = 0
    mFinished = False
    Set rs = db.OpenRecordset("SELECT q.* FROM Questions q INNER JOIN PaperQuestions pq ON q.QID = pq.QID " & _
                              "WHERE pq.SubjectID = " & SubjectID & " ORDER BY pq.SortNo", dbOpenSnapshot)
    Do Until rs.EOF
        ReDim Preserve mQ(mCount)
        With mQ(mCount)
            .QID = rs!QID
            .Text = rs!QText
            .Options(0) = rs!OptA
            .Options(1) = rs!OptB
            .Options(2) = rs!OptC
            .Options(3) = rs!OptD
            .Correct = rs!Correct
            .Marks = rs!Marks
            .Chosen = ""
        End With
        mCount = mCount + 1
        rs.MoveNext
    Loop
    rs.Close
    Set rs = db.OpenRecordset("SELECT DurationMin, PassPercent FROM Papers WHERE SubjectID = " & SubjectID, dbOpenSnapshot)
    mSecondsLeft = rs!DurationMin * 60
    mPassPercent = rs!PassPercent
    rs.Close
    Me.Caption = "Exam - " & SubjectName(SubjectID)
    lblStudent.Caption = gFullName & " (" & gUser & ")"
    prgAnswered.Max = IIf(mCount > 0, mCount, 1)
    prgAnswered.Value = 0
    ShowQuestion 0
    ShowTime
    tmrCountdown.Enabled = True
End Sub

Public Property Get QuestionCount() As Integer
    QuestionCount = mCount
End Property

Public Property Get SecondsLeft() As Long
    SecondsLeft = mSecondsLeft
End Property

Public Property Let SecondsLeft(ByVal Value As Long)
    mSecondsLeft = Value
    ShowTime
End Property

Private Sub ShowQuestion(ByVal i As Integer)
    Dim k As Integer
    mCur = i
    lblProgress.Caption = "Question " & (i + 1) & " of " & mCount & "   (" & mQ(i).Marks & " marks)"
    lblQuestion.Caption = mQ(i).Text
    For k = 0 To 3
        optAns(k).Caption = OptionLetter(k) & ")  " & mQ(i).Options(k)
        optAns(k).Value = False
    Next
    If mQ(i).Chosen <> "" Then optAns(OptionIndex(mQ(i).Chosen)).Value = True
    cmdPrev.Enabled = (i > 0)
    cmdNext.Enabled = (i < mCount - 1)
End Sub

Private Function AnsweredCount() As Integer
    Dim i As Integer
    For i = 0 To mCount - 1
        If mQ(i).Chosen <> "" Then AnsweredCount = AnsweredCount + 1
    Next
End Function

Private Sub optAns_Click(Index As Integer)
    mQ(mCur).Chosen = OptionLetter(Index)
    prgAnswered.Value = AnsweredCount()
End Sub

Private Sub cmdPrev_Click()
    If mCur > 0 Then ShowQuestion mCur - 1
End Sub

Private Sub cmdNext_Click()
    If mCur < mCount - 1 Then ShowQuestion mCur + 1
End Sub

Private Sub ShowTime()
    lblTime.Caption = Format$(mSecondsLeft \ 60, "00") & ":" & Format$(mSecondsLeft Mod 60, "00")
    If mSecondsLeft <= 60 Then lblTime.ForeColor = vbRed
End Sub

Private Sub tmrCountdown_Timer()
    mSecondsLeft = mSecondsLeft - 1
    ShowTime
    If mSecondsLeft <= 0 Then
        tmrCountdown.Enabled = False
        MsgBox "Time is up! Your answers are being marked.", vbInformation
        FinishExam
    End If
End Sub

Private Sub cmdFinish_Click()
    Dim open_ As Integer
    open_ = mCount - AnsweredCount()
    If open_ > 0 Then
        If MsgBox(open_ & " question(s) are not answered. Finish anyway?", vbYesNo + vbQuestion) = vbNo Then Exit Sub
    End If
    FinishExam
End Sub

Private Sub FinishExam()
    Dim rs As DAO.Recordset, i As Integer, nCorrect As Integer, nScore As Integer, nMax As Integer
    Dim pct As Double, newId As Long
    If mFinished Then Exit Sub
    mFinished = True
    tmrCountdown.Enabled = False
    For i = 0 To mCount - 1
        nMax = nMax + mQ(i).Marks
        If mQ(i).Chosen = mQ(i).Correct Then
            nCorrect = nCorrect + 1
            nScore = nScore + mQ(i).Marks
        End If
    Next
    If nMax > 0 Then pct = Round(nScore * 100 / nMax, 1)
    Set rs = db.OpenRecordset("Results", dbOpenDynaset)
    rs.AddNew
    rs!UserName = gUser
    rs!SubjectID = mSubject
    rs!TakenOn = Now
    rs!Answered = AnsweredCount()
    rs!Correct = nCorrect
    rs!Score = nScore
    rs!MaxScore = nMax
    rs!PercentScore = pct
    rs!Passed = (pct >= mPassPercent)
    rs.Update
    rs.Bookmark = rs.LastModified
    newId = rs!ResultID
    rs.Close
    Set rs = db.OpenRecordset("Answers", dbOpenDynaset)
    For i = 0 To mCount - 1
        rs.AddNew
        rs!ResultID = newId
        rs!QID = mQ(i).QID
        rs!Chosen = mQ(i).Chosen
        rs.Update
    Next
    rs.Close
    frmScore.ShowResult newId
    frmScore.Show
    Unload Me
End Sub
