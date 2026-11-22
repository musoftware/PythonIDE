VERSION 5.00
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Begin VB.Form frmResults 
   Caption         =   "Results"
   ClientHeight    =   4560
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   8160
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   4560
   ScaleWidth      =   8160
   Begin VB.CommandButton cmdReport 
      Caption         =   "&Report"
      Height          =   375
      Left            =   6840
      TabIndex        =   3
      Top             =   4080
      Width           =   1095
   End
   Begin VB.ComboBox cboSubject 
      Height          =   315
      Left            =   1080
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   120
      Width           =   3255
   End
   Begin MSFlexGridLib.MSFlexGrid grdResults 
      Height          =   3375
      Left            =   120
      TabIndex        =   2
      Top             =   600
      Width           =   7815
      _ExtentX        =   13785
      _ExtentY        =   5953
      _Version        =   393216
      Rows            =   1
      Cols            =   6
      FixedCols       =   0
      FormatString    =   "<Student          |<Taken on        |>Correct|>Score  |>%     |^Result"
   End
   Begin VB.Label lblSubject 
      Caption         =   "Subject:"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   180
      Width           =   855
   End
   Begin VB.Label lblSummary 
      Caption         =   "-"
      Height          =   255
      Left            =   120
      TabIndex        =   4
      Top             =   4140
      Width           =   6615
   End
End
Attribute VB_Name = "frmResults"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmResults - the results of one subject (MSFlexGrid), the pass rate and the average, and the
' DataReport rptResults through the parameterised DataEnvironment command deExam.cmdResults.
Option Explicit

Private Sub Form_Load()
    FillSubjects cboSubject
    LoadResults
End Sub

Private Sub cboSubject_Click()
    LoadResults
End Sub

Public Sub LoadResults()
    Dim rs As DAO.Recordset, n As Integer, passed As Integer, total As Double
    grdResults.Rows = 1
    Set rs = db.OpenRecordset("SELECT u.FullName, r.TakenOn, r.Correct, r.Score, r.MaxScore, r.PercentScore, r.Passed " & _
                              "FROM Results r INNER JOIN Users u ON r.UserName = u.UserName WHERE r.SubjectID = " & _
                              cboSubject.ItemData(cboSubject.ListIndex) & " ORDER BY r.TakenOn", dbOpenSnapshot)
    Do Until rs.EOF
        grdResults.AddItem rs!FullName & vbTab & Format$(rs!TakenOn, "yyyy-mm-dd hh:nn") & vbTab & rs!Correct & vbTab & _
                           rs!Score & "/" & rs!MaxScore & vbTab & Format$(rs!PercentScore, "0.0") & vbTab & _
                           IIf(rs!Passed, "PASS", "FAIL")
        n = n + 1
        If rs!Passed Then passed = passed + 1
        total = total + rs!PercentScore
        rs.MoveNext
    Loop
    rs.Close
    If n = 0 Then
        lblSummary.Caption = "Nobody took this exam yet."
    Else
        lblSummary.Caption = n & " results, " & passed & " passed (" & Format$(passed / n, "0%") & "), average " & _
                             Format$(total / n, "0.0") & "%"
    End If
End Sub

Private Sub cmdReport_Click()
    deExam.cmdResults cboSubject.ItemData(cboSubject.ListIndex)
    rptResults.Caption = "Results - " & cboSubject.Text
    rptResults.Show
End Sub
