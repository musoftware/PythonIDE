VERSION 5.00
Begin VB.Form frmMain
   Caption         =   "«·„·«ÕŸ«  - Notes"
   ClientHeight    =   4335
   ClientLeft      =   165
   ClientTop       =   855
   ClientWidth     =   6015
   LinkTopic       =   "Form1"
   RightToLeft     =   -1  'True
   ScaleHeight     =   4335
   ScaleWidth      =   6015
   StartUpPosition =   3  'Windows Default
   Begin VB.Frame fraOptions
      Caption         =   "ŒÌ«—« "
      Height          =   1335
      Left            =   3840
      TabIndex        =   2
      Top             =   120
      Width           =   2055
      Begin VB.CheckBox chkSort
         Caption         =   "Sort"
         Height          =   255
         Left            =   120
         TabIndex        =   4
         Top             =   360
         Value           =   1  'Checked
         Width           =   1695
      End
      Begin VB.OptionButton optAll
         Caption         =   "All"
         Height          =   255
         Index           =   0
         Left            =   120
         TabIndex        =   5
         Top             =   720
         Value           =   -1  'True
         Width           =   735
      End
      Begin VB.OptionButton optAll
         Caption         =   "Today"
         Height          =   255
         Index           =   1
         Left            =   960
         TabIndex        =   6
         Top             =   720
         Width           =   975
      End
   End
   Begin VB.ListBox lstNotes
      Height          =   3180
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   3615
   End
   Begin VB.CommandButton cmdNew
      Caption         =   "&New note"
      Height          =   495
      Left            =   3840
      TabIndex        =   1
      Top             =   1680
      Width           =   2055
   End
   Begin VB.Timer tmrClock
      Interval        =   1000
      Left            =   5280
      Top             =   3600
   End
   Begin VB.Label lblCount
      AutoSize        =   -1  'True
      Caption         =   "0 notes"
      Height          =   195
      Left            =   120
      TabIndex        =   3
      Top             =   3480
      Width           =   570
   End
   Begin VB.Menu mnuNotes
      Caption         =   "&Notes"
      Begin VB.Menu mnuNotesNew
         Caption         =   "&New..."
      End
      Begin VB.Menu mnuNotesExit
         Caption         =   "E&xit"
      End
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit
' „·«ÕŸ…: ‰«›–… —∆Ì”Ì… (Arabic comment, code page 1256)

Private Sub Form_Load()
    RefreshList
End Sub

Public Sub RefreshList()
    Dim i As Integer
    lstNotes.Clear
    For i = 1 To NoteCount()
        lstNotes.AddItem GetNote(i).Title
    Next i
    lblCount.Caption = NoteCount() & " notes"
End Sub

Private Sub cmdNew_Click()
    frmEdit.Show vbModal
    RefreshList
End Sub

Private Sub optAll_Click(Index As Integer)
    lblCount.Caption = "Filter " & Index
End Sub

Private Sub tmrClock_Timer()
    Me.Caption = "Notes " & Format(Now, "hh:nn:ss")
End Sub

Private Sub mnuNotesNew_Click()
    cmdNew_Click
End Sub

Private Sub mnuNotesExit_Click()
    Unload Me
End Sub
