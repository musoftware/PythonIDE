VERSION 5.00
Begin VB.Form frmScore 
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "Your result"
   ClientHeight    =   3120
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   4800
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   3120
   ScaleWidth      =   4800
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton cmdClose 
      Caption         =   "&Close"
      Default         =   -1  'True
      Height          =   375
      Left            =   3480
      TabIndex        =   0
      Top             =   2580
      Width           =   1095
   End
   Begin VB.Shape shpBadge 
      BackColor       =   &H0000C000&
      BackStyle       =   1  'Opaque
      Height          =   855
      Left            =   240
      Shape           =   2  'Oval
      Top             =   240
      Width           =   1335
   End
   Begin VB.Label lblVerdict 
      Alignment       =   2  'Center
      BackStyle       =   0  'Transparent
      Caption         =   "PASS"
      BeginProperty Font 
         Name            =   "Arial"
         Size            =   14.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H00FFFFFF&
      Height          =   375
      Left            =   240
      TabIndex        =   1
      Top             =   480
      Width           =   1335
   End
   Begin VB.Label lblDetails 
      Caption         =   "-"
      Height          =   1335
      Left            =   1800
      TabIndex        =   2
      Top             =   240
      Width           =   2775
   End
   Begin VB.Label lblReview 
      Caption         =   "-"
      Height          =   735
      Left            =   240
      TabIndex        =   3
      Top             =   1680
      Width           =   4335
   End
End
Attribute VB_Name = "frmScore"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmScore - the score card of one Results row; the badge Shape turns green or red.
Option Explicit

Public Sub ShowResult(ByVal ResultID As Long)
    Dim rs As DAO.Recordset, wrong As String
    Set rs = db.OpenRecordset("SELECT * FROM Results WHERE ResultID = " & ResultID, dbOpenSnapshot)
    lblDetails.Caption = SubjectName(rs!SubjectID) & vbCrLf & _
                         "Answered: " & rs!Answered & vbCrLf & _
                         "Correct: " & rs!Correct & vbCrLf & _
                         "Score: " & rs!Score & " / " & rs!MaxScore & "  (" & rs!PercentScore & "%)"
    If rs!Passed Then
        lblVerdict.Caption = "PASS"
        shpBadge.BackColor = &HC000&
    Else
        lblVerdict.Caption = "FAIL"
        shpBadge.BackColor = vbRed
    End If
    rs.Close
    ' the numbers of the questions answered wrongly
    Set rs = db.OpenRecordset("SELECT a.QID FROM Answers a INNER JOIN Questions q ON a.QID = q.QID " & _
                              "WHERE a.ResultID = " & ResultID & " AND (a.Chosen IS NULL OR a.Chosen <> q.Correct) " & _
                              "ORDER BY a.AnsID", dbOpenSnapshot)
    Do Until rs.EOF
        wrong = wrong & IIf(wrong = "", "", ", ") & rs!QID
        rs.MoveNext
    Loop
    rs.Close
    lblReview.Caption = IIf(wrong = "", "All answers are correct.", "Wrong or missing: question id " & wrong)
End Sub

Private Sub cmdClose_Click()
    Unload Me
    frmWelcome.txtPwd.Text = ""
    frmWelcome.Show
End Sub
