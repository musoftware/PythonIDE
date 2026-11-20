VERSION 5.00
Begin VB.Form frmMain 
   BorderStyle     =   1  'Fixed Single
   Caption         =   "Notes & Calc"
   ClientHeight    =   4845
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   4815
   BeginProperty Font 
      Name            =   "MS Sans Serif"
      Size            =   8.25
      Charset         =   0
      Weight          =   400
      Underline       =   0   'False
      Italic          =   0   'False
      Strikethrough   =   0   'False
   EndProperty
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   4845
   ScaleWidth      =   4815
   StartUpPosition =   2  'CenterScreen
   Begin VB.Timer tmrClock
      Interval        =   1000
      Left            =   4680
      Top             =   120
   End
   Begin VB.TextBox txtItem
      Text            =   ""
      Height          =   315
      Left            =   240
      TabIndex        =   0
      Top             =   240
      Width           =   3135
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "&Add"
      Default         =   -1  'True
      Height          =   315
      Left            =   3480
      TabIndex        =   1
      Top             =   240
      Width           =   1095
   End
   Begin VB.ListBox lstItems
      Height          =   1815
      Left            =   240
      TabIndex        =   2
      Top             =   720
      Width           =   3135
   End
   Begin VB.CommandButton cmdRemove
      Caption         =   "&Remove"
      Height          =   315
      Left            =   3480
      TabIndex        =   3
      Top             =   720
      Width           =   1095
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "&Save"
      Height          =   315
      Left            =   3480
      TabIndex        =   4
      Top             =   1200
      Width           =   1095
   End
   Begin VB.CommandButton cmdLoad
      Caption         =   "&Load"
      Height          =   315
      Left            =   3480
      TabIndex        =   5
      Top             =   1680
      Width           =   1095
   End
   Begin VB.CheckBox chkUpper
      Caption         =   "Upper case"
      Height          =   255
      Left            =   240
      TabIndex        =   6
      Top             =   2640
      Width           =   2175
   End
   Begin VB.Label lblCount
      Caption         =   "Items: 0"
      Height          =   255
      Left            =   240
      TabIndex        =   7
      Top             =   3000
      Width           =   4335
   End
   Begin VB.TextBox txtA
      Text            =   "6"
      Height          =   315
      Left            =   240
      TabIndex        =   8
      Top             =   3480
      Width           =   975
   End
   Begin VB.TextBox txtB
      Text            =   "3"
      Height          =   315
      Left            =   1320
      TabIndex        =   9
      Top             =   3480
      Width           =   975
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "+"
      Height          =   315
      Index           =   0
      Left            =   2400
      TabIndex        =   10
      Top             =   3480
      Width           =   495
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "-"
      Height          =   315
      Index           =   1
      Left            =   2940
      TabIndex        =   11
      Top             =   3480
      Width           =   495
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "*"
      Height          =   315
      Index           =   2
      Left            =   3480
      TabIndex        =   12
      Top             =   3480
      Width           =   495
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "/"
      Height          =   315
      Index           =   3
      Left            =   4020
      TabIndex        =   13
      Top             =   3480
      Width           =   495
   End
   Begin VB.Label lblResult
      Caption         =   "="
      Height          =   255
      Left            =   240
      TabIndex        =   14
      Top             =   3960
      Width           =   4335
   End
   Begin VB.CommandButton cmdHello
      Caption         =   "&Hello..."
      Height          =   315
      Left            =   240
      TabIndex        =   15
      Top             =   4320
      Width           =   1335
   End
   Begin VB.Label lblClock
      Alignment       =   1  'Right Justify
      Caption         =   "00:00:00"
      Height          =   255
      Left            =   3240
      TabIndex        =   16
      Top             =   4380
      Width           =   1335
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

' Notes list + a small calculator - test project for File > Migrate Project
Private mCount As Integer
Private Const DATA_FILE As String = "notes.txt"
Private mClicks As CCounter

Private Sub Form_Load()
    gAppTitle = "Notes & Calc"
    Set mClicks = New CCounter
    Me.Caption = gAppTitle & " - " & SumTo(10)   ' 55
    mCount = 0
    lblResult.Caption = ""
    UpdateCount
End Sub

Private Sub cmdAdd_Click()
    Dim s As String
    s = Trim$(txtItem.Text)
    If Len(s) = 0 Then
        MsgBox "Type something first", vbExclamation, "Notes"
        Exit Sub
    End If
    If chkUpper.Value = vbChecked Then s = UCase$(s)
    lstItems.AddItem s
    txtItem.Text = ""
    mCount = mCount + 1
    mClicks.Increment
    UpdateCount
End Sub

Private Sub cmdRemove_Click()
    If lstItems.ListIndex < 0 Then
        MsgBox "Select an item", vbInformation
    Else
        lstItems.RemoveItem lstItems.ListIndex
        mCount = mCount - 1
        UpdateCount
    End If
End Sub

Private Sub UpdateCount()
    lblCount.Caption = "Items: " & lstItems.ListCount & " (added " & mCount & ")"
End Sub

Private Sub cmdOp_Click(Index As Integer)
    Dim a As Double, b As Double, r As Double
    a = Val(txtA.Text)
    b = Val(txtB.Text)
    Select Case Index
        Case 0: r = a + b
        Case 1: r = a - b
        Case 2: r = a * b
        Case 3
            If b = 0 Then
                lblResult.Caption = "Cannot divide by zero"
                Exit Sub
            End If
            r = a / b
    End Select
    lblResult.Caption = "= " & Format(r, "0.##")
End Sub

Private Sub cmdSave_Click()
    Dim f As Integer, i As Integer
    f = FreeFile
    Open App.Path & "\" & DATA_FILE For Output As #f
    For i = 0 To lstItems.ListCount - 1
        Print #f, lstItems.List(i)
    Next i
    Close #f
    MsgBox "Saved " & lstItems.ListCount & " item(s)", vbInformation, "Notes"
End Sub

Private Sub cmdLoad_Click()
    Dim f As Integer, s As String
    On Error GoTo LoadFailed
    f = FreeFile
    Open App.Path & "\" & DATA_FILE For Input As #f
    lstItems.Clear
    Do While Not EOF(f)
        Line Input #f, s
        If s <> "" Then lstItems.AddItem s
    Loop
    Close #f
    UpdateCount
    Exit Sub
LoadFailed:
    MsgBox "Could not load: " & Err.Description, vbCritical
End Sub

Private Sub cmdHello_Click()
    Dim who As String
    who = InputBox("Your name?", "Hello")
    lblResult.Caption = Greeting(who) & " (" & mClicks.Count & " added)"
End Sub

Private Sub tmrClock_Timer()
    lblClock.Caption = Format(Now, "hh:nn:ss")
End Sub

Private Sub txtItem_KeyPress(KeyAscii As Integer)
    If KeyAscii = 13 Then cmdAdd_Click
End Sub

Private Sub Form_Unload(Cancel As Integer)
    If lstItems.ListCount > 0 Then
        If MsgBox("Quit and lose unsaved items?", vbYesNo + vbQuestion, "Notes") = vbNo Then Cancel = True
    End If
End Sub
