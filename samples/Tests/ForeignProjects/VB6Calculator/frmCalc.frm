VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmCalc
   BorderStyle     =   1  'Fixed Single
   Caption         =   "Calculator"
   ClientHeight    =   4920
   ClientLeft      =   45
   ClientTop       =   735
   ClientWidth     =   5415
   BeginProperty Font
      Name            =   "Tahoma"
      Size            =   9.75
      Charset         =   0
      Weight          =   400
      Underline       =   0   'False
      Italic          =   0   'False
      Strikethrough   =   0   'False
   EndProperty
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   4920
   ScaleWidth      =   5415
   StartUpPosition =   2  'CenterScreen
   Begin MSComctlLib.StatusBar sbStatus
      Align           =   2  'Align Bottom
      Height          =   375
      Left            =   0
      TabIndex        =   18
      Top             =   4545
      Width           =   5415
      _ExtentX        =   9551
      _ExtentY        =   661
      Style           =   1
      SimpleText      =   "Ready"
      _Version        =   393216
      BeginProperty Panels {8E3867A5-8586-11D1-B16A-00C0F0283628}
         NumPanels       =   1
         BeginProperty Panel1 {8E3867AB-8586-11D1-B16A-00C0F0283628}
         EndProperty
      EndProperty
   End
   Begin VB.ListBox lstHistory
      Height          =   2985
      ItemData        =   "frmCalc.frx":0000
      Left            =   3120
      List            =   "frmCalc.frx":0002
      TabIndex        =   17
      Top             =   1440
      Width           =   2055
   End
   Begin VB.CommandButton cmdEquals
      Caption         =   "="
      Default         =   -1  'True
      Height          =   495
      Left            =   840
      TabIndex        =   15
      Top             =   3240
      Width           =   1335
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "+"
      Height          =   495
      Left            =   2280
      TabIndex        =   11
      Top             =   1440
      Width           =   615
   End
   Begin VB.CommandButton cmdSub
      Caption         =   "-"
      Height          =   495
      Left            =   2280
      TabIndex        =   12
      Top             =   2040
      Width           =   615
   End
   Begin VB.CommandButton cmdMul
      Caption         =   "*"
      Height          =   495
      Left            =   2280
      TabIndex        =   13
      Top             =   2640
      Width           =   615
   End
   Begin VB.CommandButton cmdDiv
      Caption         =   "/"
      Height          =   495
      Left            =   2280
      TabIndex        =   14
      Top             =   3240
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "7"
      Height          =   495
      Index           =   7
      Left            =   120
      TabIndex        =   8
      Top             =   1440
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "8"
      Height          =   495
      Index           =   8
      Left            =   840
      TabIndex        =   9
      Top             =   1440
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "9"
      Height          =   495
      Index           =   9
      Left            =   1560
      TabIndex        =   10
      Top             =   1440
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "4"
      Height          =   495
      Index           =   4
      Left            =   120
      TabIndex        =   5
      Top             =   2040
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "5"
      Height          =   495
      Index           =   5
      Left            =   840
      TabIndex        =   6
      Top             =   2040
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "6"
      Height          =   495
      Index           =   6
      Left            =   1560
      TabIndex        =   7
      Top             =   2040
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "1"
      Height          =   495
      Index           =   1
      Left            =   120
      TabIndex        =   2
      Top             =   2640
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "2"
      Height          =   495
      Index           =   2
      Left            =   840
      TabIndex        =   3
      Top             =   2640
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "3"
      Height          =   495
      Index           =   3
      Left            =   1560
      TabIndex        =   4
      Top             =   2640
      Width           =   615
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "0"
      Height          =   495
      Index           =   0
      Left            =   120
      TabIndex        =   1
      Top             =   3240
      Width           =   615
   End
   Begin VB.CommandButton cmdClear
      Caption         =   "C"
      Height          =   495
      Left            =   120
      TabIndex        =   16
      ToolTipText     =   "Clear the display"
      Top             =   840
      Width           =   2775
   End
   Begin VB.TextBox txtDisplay
      Alignment       =   1  'Right Justify
      Height          =   495
      Left            =   120
      Locked          =   -1  'True
      TabIndex        =   0
      Text            =   "0"
      Top             =   240
      Width           =   5055
   End
   Begin VB.Label lblHistory
      Caption         =   "History:"
      Height          =   255
      Left            =   3120
      TabIndex        =   19
      Top             =   1080
      Width           =   2055
   End
   Begin VB.Menu mnuFile
      Caption         =   "&File"
      Begin VB.Menu mnuFileClear
         Caption         =   "&Clear History"
         Shortcut        =   ^L
      End
      Begin VB.Menu mnuFileSep1
         Caption         =   "-"
      End
      Begin VB.Menu mnuFileExit
         Caption         =   "E&xit"
      End
   End
   Begin VB.Menu mnuHelp
      Caption         =   "&Help"
      Begin VB.Menu mnuHelpAbout
         Caption         =   "&About..."
      End
   End
   Begin VB.Menu mnuPopup
      Caption         =   "Popup"
      Visible         =   0   'False
      Begin VB.Menu mnuPopupCopy
         Caption         =   "&Copy"
      End
   End
End
Attribute VB_Name = "frmCalc"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit
' Classic four-function calculator: a control array of digit buttons,
' a class module for the history and a standard module for the maths.

Private mHistory As CHistory
Private mAcc As Double
Private mOp As String
Private mNewNumber As Boolean

Private Sub Form_Load()
    Set mHistory = New CHistory
    mNewNumber = True
    txtDisplay.Text = "0"
    sbStatus.SimpleText = "Ready"
End Sub

Private Sub cmdDigit_Click(Index As Integer)
    If mNewNumber Then
        txtDisplay.Text = CStr(Index)
        mNewNumber = False
    Else
        txtDisplay.Text = txtDisplay.Text & CStr(Index)
    End If
End Sub

Private Sub PushOp(ByVal op As String)
    mAcc = Val(txtDisplay.Text)
    mOp = op
    mNewNumber = True
End Sub

Private Sub cmdAdd_Click()
    PushOp "+"
End Sub

Private Sub cmdSub_Click()
    PushOp "-"
End Sub

Private Sub cmdMul_Click()
    PushOp "*"
End Sub

Private Sub cmdDiv_Click()
    PushOp "/"
End Sub

Private Sub cmdEquals_Click()
    Dim result As Double
    result = Calculate(mAcc, Val(txtDisplay.Text), mOp)
    mHistory.Add mAcc & " " & mOp & " " & txtDisplay.Text & " = " & result
    lstHistory.AddItem mHistory.Last
    txtDisplay.Text = CStr(result)
    mNewNumber = True
End Sub

Private Sub cmdClear_Click()
    txtDisplay.Text = "0"
    mAcc = 0
    mOp = ""
    mNewNumber = True
End Sub

Private Sub mnuFileClear_Click()
    lstHistory.Clear
    mHistory.Clear
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub mnuHelpAbout_Click()
    frmAbout.Show vbModal
End Sub
