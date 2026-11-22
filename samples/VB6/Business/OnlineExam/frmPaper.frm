VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmPaper 
   Caption         =   "Question paper"
   ClientHeight    =   5040
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   8640
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   5040
   ScaleWidth      =   8640
   Begin VB.CommandButton cmdSavePaper 
      Caption         =   "&Save paper"
      Height          =   375
      Left            =   7080
      TabIndex        =   9
      Top             =   4500
      Width           =   1335
   End
   Begin VB.TextBox txtPass 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   5520
      TabIndex        =   8
      Text            =   "50"
      Top             =   4530
      Width           =   615
   End
   Begin VB.TextBox txtDuration 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   2400
      TabIndex        =   6
      Text            =   "10"
      Top             =   4530
      Width           =   615
   End
   Begin VB.CommandButton cmdRemove 
      Caption         =   "<<"
      Height          =   375
      Left            =   4080
      TabIndex        =   4
      Top             =   2400
      Width           =   495
   End
   Begin VB.CommandButton cmdAdd 
      Caption         =   ">>"
      Height          =   375
      Left            =   4080
      TabIndex        =   3
      Top             =   1800
      Width           =   495
   End
   Begin VB.ComboBox cboSubject 
      Height          =   315
      Left            =   1080
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   120
      Width           =   3255
   End
   Begin MSComctlLib.ListView lvwBank 
      Height          =   3735
      Left            =   120
      TabIndex        =   2
      Top             =   600
      Width           =   3855
      _ExtentX        =   6800
      _ExtentY        =   6588
      View            =   3
      LabelEdit       =   1
      FullRowSelect   =   -1  'True
      _Version        =   393217
      ForeColor       =   -2147483640
      BackColor       =   -2147483643
      BorderStyle     =   1
      Appearance      =   1
      NumItems        =   2
      BeginProperty ColumnHeader(1) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         Text            =   "Id"
         Object.Width           =   882
      EndProperty
      BeginProperty ColumnHeader(2) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         SubItemIndex    =   1
         Text            =   "Question bank"
         Object.Width           =   5644
      EndProperty
   End
   Begin MSComctlLib.ListView lvwPaper 
      Height          =   3735
      Left            =   4680
      TabIndex        =   5
      Top             =   600
      Width           =   3855
      _ExtentX        =   6800
      _ExtentY        =   6588
      View            =   3
      LabelEdit       =   1
      FullRowSelect   =   -1  'True
      _Version        =   393217
      ForeColor       =   -2147483640
      BackColor       =   -2147483643
      BorderStyle     =   1
      Appearance      =   1
      NumItems        =   2
      BeginProperty ColumnHeader(1) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         Text            =   "Id"
         Object.Width           =   882
      EndProperty
      BeginProperty ColumnHeader(2) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
         SubItemIndex    =   1
         Text            =   "On the paper"
         Object.Width           =   5644
      EndProperty
   End
   Begin VB.Label lblPass 
      Caption         =   "Pass mark %:"
      Height          =   255
      Left            =   4440
      TabIndex        =   7
      Top             =   4590
      Width           =   1095
   End
   Begin VB.Label lblDuration 
      Caption         =   "Duration (minutes):"
      Height          =   255
      Left            =   120
      TabIndex        =   10
      Top             =   4590
      Width           =   2175
   End
   Begin VB.Label lblSubject 
      Caption         =   "Subject:"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   180
      Width           =   855
   End
   Begin VB.Label lblTotal 
      Caption         =   "-"
      Height          =   255
      Left            =   4680
      TabIndex        =   11
      Top             =   180
      Width           =   3855
   End
End
Attribute VB_Name = "frmPaper"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmPaper - build the question paper of a subject: two report-style ListViews, >> copies the
' selected bank question to the paper (PaperQuestions row), << removes it; Save paper stores the
' duration and the pass mark (Papers row: INSERT the first time, UPDATE afterwards).
Option Explicit

Private Sub Form_Load()
    FillSubjects cboSubject
    LoadLists
End Sub

Private Function SubjectId() As Long
    SubjectId = cboSubject.ItemData(cboSubject.ListIndex)
End Function

Private Sub cboSubject_Click()
    LoadLists
End Sub

Public Sub LoadLists()
    Dim rs As DAO.Recordset, li As ListItem, marks As Integer
    lvwBank.ListItems.Clear
    lvwPaper.ListItems.Clear
    Set rs = db.OpenRecordset("SELECT q.QID, q.QText, q.Marks, pq.PQID FROM Questions q LEFT JOIN PaperQuestions pq " & _
                              "ON q.QID = pq.QID WHERE q.SubjectID = " & SubjectId() & " ORDER BY pq.SortNo, q.QID", _
                              dbOpenSnapshot)
    Do Until rs.EOF
        If IsNull(rs!PQID) Then
            Set li = lvwBank.ListItems.Add(, "q" & rs!QID, rs!QID)
        Else
            Set li = lvwPaper.ListItems.Add(, "q" & rs!QID, rs!QID)
            marks = marks + rs!Marks
        End If
        li.SubItems(1) = rs!QText
        rs.MoveNext
    Loop
    rs.Close
    Set rs = db.OpenRecordset("SELECT DurationMin, PassPercent FROM Papers WHERE SubjectID = " & SubjectId(), dbOpenSnapshot)
    If Not rs.EOF Then
        txtDuration.Text = rs!DurationMin
        txtPass.Text = rs!PassPercent
    End If
    rs.Close
    lblTotal.Caption = lvwPaper.ListItems.Count & " questions, " & marks & " marks"
End Sub

Private Sub cmdAdd_Click()
    Dim n As Integer
    If lvwBank.ListItems.Count = 0 Then Exit Sub
    n = lvwPaper.ListItems.Count + 1
    db.Execute "INSERT INTO PaperQuestions (SubjectID, QID, SortNo) VALUES (" & SubjectId() & ", " & _
               lvwBank.SelectedItem.Text & ", " & n & ")"
    LoadLists
End Sub

Private Sub cmdRemove_Click()
    If lvwPaper.ListItems.Count = 0 Then Exit Sub
    db.Execute "DELETE FROM PaperQuestions WHERE SubjectID = " & SubjectId() & " AND QID = " & lvwPaper.SelectedItem.Text
    LoadLists
End Sub

Private Sub cmdSavePaper_Click()
    If Val(txtDuration.Text) < 1 Or Val(txtPass.Text) < 1 Or Val(txtPass.Text) > 100 Then
        MsgBox "Duration must be at least 1 minute and the pass mark between 1 and 100.", vbExclamation
        Exit Sub
    End If
    If lvwPaper.ListItems.Count = 0 Then
        MsgBox "Put at least one question on the paper.", vbExclamation
        Exit Sub
    End If
    db.Execute "UPDATE Papers SET DurationMin = " & Val(txtDuration.Text) & ", PassPercent = " & Val(txtPass.Text) & _
               " WHERE SubjectID = " & SubjectId()
    If db.RecordsAffected = 0 Then
        db.Execute "INSERT INTO Papers VALUES (" & SubjectId() & ", " & Val(txtDuration.Text) & ", " & Val(txtPass.Text) & ")"
    End If
    MsgBox "Paper of " & cboSubject.Text & " saved.", vbInformation
End Sub
