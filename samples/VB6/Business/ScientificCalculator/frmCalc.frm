VERSION 5.00
Begin VB.Form frmCalc 
   BorderStyle     =   1  'Fixed Single
   Caption         =   "Scientific Calculator"
   ClientHeight    =   4320
   ClientLeft      =   45
   ClientTop       =   735
   ClientWidth     =   9300
   KeyPreview      =   -1  'True
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   4320
   ScaleWidth      =   9300
   StartUpPosition =   2  'CenterScreen
   Begin VB.Timer tmrClock 
      Interval        =   1000
      Left            =   8760
      Top             =   3720
   End
   Begin VB.ListBox lstHistory 
      BeginProperty Font 
         Name            =   "Courier New"
         Size            =   8.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   3420
      Left            =   6720
      TabIndex        =   40
      Top             =   360
      Width           =   2460
   End
   Begin VB.CheckBox chkBeep 
      Caption         =   "Beep"
      Height          =   255
      Left            =   5040
      TabIndex        =   41
      Top             =   3840
      Width           =   855
   End
   Begin VB.Frame fraAngle 
      Caption         =   "Angles"
      Height          =   555
      Left            =   5040
      TabIndex        =   42
      Top             =   900
      Width           =   1500
      Begin VB.OptionButton optAngle 
         Caption         =   "Rad"
         Height          =   255
         Index           =   1
         Left            =   780
         TabIndex        =   44
         Top             =   240
         Width           =   675
      End
      Begin VB.OptionButton optAngle 
         Caption         =   "Deg"
         Height          =   255
         Index           =   0
         Left            =   90
         TabIndex        =   43
         Top             =   240
         Value           =   -1  'True
         Width           =   675
      End
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "sin"
      Height          =   480
      Index           =   0
      Left            =   120
      Style           =   1  'Graphical
      TabIndex        =   1
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "cos"
      Height          =   480
      Index           =   1
      Left            =   900
      Style           =   1  'Graphical
      TabIndex        =   2
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "tan"
      Height          =   480
      Index           =   2
      Left            =   1680
      Style           =   1  'Graphical
      TabIndex        =   3
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "log"
      Height          =   480
      Index           =   3
      Left            =   120
      Style           =   1  'Graphical
      TabIndex        =   4
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "ln"
      Height          =   480
      Index           =   4
      Left            =   900
      Style           =   1  'Graphical
      TabIndex        =   5
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "sqrt"
      Height          =   480
      Index           =   5
      Left            =   1680
      Style           =   1  'Graphical
      TabIndex        =   6
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "x^2"
      Height          =   480
      Index           =   6
      Left            =   120
      Style           =   1  'Graphical
      TabIndex        =   7
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "x^3"
      Height          =   480
      Index           =   7
      Left            =   900
      Style           =   1  'Graphical
      TabIndex        =   8
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "1/x"
      Height          =   480
      Index           =   8
      Left            =   1680
      Style           =   1  'Graphical
      TabIndex        =   9
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "n!"
      Height          =   480
      Index           =   9
      Left            =   120
      Style           =   1  'Graphical
      TabIndex        =   10
      Top             =   3180
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "%"
      Height          =   480
      Index           =   10
      Left            =   900
      Style           =   1  'Graphical
      TabIndex        =   11
      Top             =   3180
      Width           =   720
   End
   Begin VB.CommandButton cmdFunc 
      BackColor       =   &H00FFE0C0&
      Caption         =   "pi"
      Height          =   480
      Index           =   11
      Left            =   1680
      Style           =   1  'Graphical
      TabIndex        =   12
      Top             =   3180
      Width           =   720
   End
   Begin VB.CommandButton cmdMem 
      BackColor       =   &H00C0E0FF&
      Caption         =   "MC"
      Height          =   480
      Index           =   0
      Left            =   120
      Style           =   1  'Graphical
      TabIndex        =   13
      Top             =   1020
      Width           =   540
   End
   Begin VB.CommandButton cmdMem 
      BackColor       =   &H00C0E0FF&
      Caption         =   "MR"
      Height          =   480
      Index           =   1
      Left            =   690
      Style           =   1  'Graphical
      TabIndex        =   14
      Top             =   1020
      Width           =   540
   End
   Begin VB.CommandButton cmdMem 
      BackColor       =   &H00C0E0FF&
      Caption         =   "MS"
      Height          =   480
      Index           =   2
      Left            =   1260
      Style           =   1  'Graphical
      TabIndex        =   15
      Top             =   1020
      Width           =   540
   End
   Begin VB.CommandButton cmdMem 
      BackColor       =   &H00C0E0FF&
      Caption         =   "M+"
      Height          =   480
      Index           =   3
      Left            =   1830
      Style           =   1  'Graphical
      TabIndex        =   16
      Top             =   1020
      Width           =   540
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "7"
      Height          =   480
      Index           =   7
      Left            =   2700
      TabIndex        =   17
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "8"
      Height          =   480
      Index           =   8
      Left            =   3480
      TabIndex        =   18
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "9"
      Height          =   480
      Index           =   9
      Left            =   4260
      TabIndex        =   19
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "4"
      Height          =   480
      Index           =   4
      Left            =   2700
      TabIndex        =   20
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "5"
      Height          =   480
      Index           =   5
      Left            =   3480
      TabIndex        =   21
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "6"
      Height          =   480
      Index           =   6
      Left            =   4260
      TabIndex        =   22
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "1"
      Height          =   480
      Index           =   1
      Left            =   2700
      TabIndex        =   23
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "2"
      Height          =   480
      Index           =   2
      Left            =   3480
      TabIndex        =   24
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "3"
      Height          =   480
      Index           =   3
      Left            =   4260
      TabIndex        =   25
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdDigit 
      Caption         =   "0"
      Height          =   480
      Index           =   0
      Left            =   2700
      TabIndex        =   26
      Top             =   3180
      Width           =   720
   End
   Begin VB.CommandButton cmdDot 
      Caption         =   "."
      Height          =   480
      Left            =   3480
      TabIndex        =   27
      Top             =   3180
      Width           =   720
   End
   Begin VB.CommandButton cmdSign 
      Caption         =   "+/-"
      Height          =   480
      Left            =   4260
      TabIndex        =   28
      Top             =   3180
      Width           =   720
   End
   Begin VB.CommandButton cmdOp 
      BackColor       =   &H00C0FFC0&
      Caption         =   "+"
      Height          =   480
      Index           =   0
      Left            =   5040
      Style           =   1  'Graphical
      TabIndex        =   29
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdOp 
      BackColor       =   &H00C0FFC0&
      Caption         =   "-"
      Height          =   480
      Index           =   1
      Left            =   5820
      Style           =   1  'Graphical
      TabIndex        =   30
      Top             =   1560
      Width           =   720
   End
   Begin VB.CommandButton cmdOp 
      BackColor       =   &H00C0FFC0&
      Caption         =   "*"
      Height          =   480
      Index           =   2
      Left            =   5040
      Style           =   1  'Graphical
      TabIndex        =   31
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdOp 
      BackColor       =   &H00C0FFC0&
      Caption         =   "/"
      Height          =   480
      Index           =   3
      Left            =   5820
      Style           =   1  'Graphical
      TabIndex        =   32
      Top             =   2100
      Width           =   720
   End
   Begin VB.CommandButton cmdOp 
      BackColor       =   &H00C0FFC0&
      Caption         =   "Mod"
      Height          =   480
      Index           =   4
      Left            =   5040
      Style           =   1  'Graphical
      TabIndex        =   33
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdOp 
      BackColor       =   &H00C0FFC0&
      Caption         =   "x^y"
      Height          =   480
      Index           =   5
      Left            =   5820
      Style           =   1  'Graphical
      TabIndex        =   34
      Top             =   2640
      Width           =   720
   End
   Begin VB.CommandButton cmdEquals 
      BackColor       =   &H0080FF80&
      Caption         =   "="
      Height          =   480
      Left            =   5040
      Style           =   1  'Graphical
      TabIndex        =   35
      Top             =   3180
      Width           =   1500
   End
   Begin VB.CommandButton cmdBack 
      Caption         =   "<-"
      Height          =   480
      Left            =   2700
      TabIndex        =   36
      Top             =   1020
      Width           =   720
   End
   Begin VB.CommandButton cmdCE 
      Caption         =   "CE"
      Height          =   480
      Left            =   3480
      TabIndex        =   37
      Top             =   1020
      Width           =   720
   End
   Begin VB.CommandButton cmdClear 
      BackColor       =   &H008080FF&
      Caption         =   "C"
      Height          =   480
      Left            =   4260
      Style           =   1  'Graphical
      TabIndex        =   38
      Top             =   1020
      Width           =   720
   End
   Begin VB.Shape shpBezel 
      BorderColor     =   &H00808080&
      BorderWidth     =   2
      Height          =   900
      Left            =   60
      Shape           =   4  'Rounded Rectangle
      Top             =   60
      Width           =   6540
   End
   Begin VB.Label lblHistory 
      Caption         =   "History"
      Height          =   255
      Left            =   6720
      TabIndex        =   45
      Top             =   120
      Width           =   2460
   End
   Begin VB.Label lblClock 
      Alignment       =   1  'Right Justify
      Caption         =   "00:00"
      Height          =   255
      Left            =   7560
      TabIndex        =   46
      Top             =   3900
      Width           =   1095
   End
   Begin VB.Label lblStatus 
      Caption         =   "Ready"
      ForeColor       =   &H00800000&
      Height          =   255
      Left            =   120
      TabIndex        =   47
      Top             =   3840
      Width           =   4815
   End
   Begin VB.Label lblMem 
      Alignment       =   2  'Center
      Caption         =   ""
      ForeColor       =   &H000000C0&
      Height          =   255
      Left            =   120
      TabIndex        =   48
      Top             =   660
      Width           =   375
   End
   Begin VB.Label lblExpr 
      Alignment       =   1  'Right Justify
      BackColor       =   &H00E0FFFF&
      Caption         =   ""
      ForeColor       =   &H00808080&
      Height          =   255
      Left            =   600
      TabIndex        =   49
      Top             =   120
      Width           =   5880
   End
   Begin VB.Label lblDisplay 
      Alignment       =   1  'Right Justify
      BackColor       =   &H00E0FFFF&
      Caption         =   "0"
      BeginProperty Font 
         Name            =   "Courier New"
         Size            =   18
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   600
      TabIndex        =   0
      Top             =   390
      Width           =   5880
   End
   Begin VB.Menu mnuFile 
      Caption         =   "&File"
      Begin VB.Menu mnuSaveHistory 
         Caption         =   "&Save history"
      End
      Begin VB.Menu mnuLoadHistory 
         Caption         =   "&Load history"
      End
      Begin VB.Menu mnuFileSep 
         Caption         =   "-"
      End
      Begin VB.Menu mnuExit 
         Caption         =   "E&xit"
      End
   End
   Begin VB.Menu mnuEdit 
      Caption         =   "&Edit"
      Begin VB.Menu mnuCopy 
         Caption         =   "&Copy result"
         Shortcut        =   ^C
      End
      Begin VB.Menu mnuPaste 
         Caption         =   "&Paste number"
         Shortcut        =   ^V
      End
      Begin VB.Menu mnuClearHistory 
         Caption         =   "Clear &history"
      End
   End
   Begin VB.Menu mnuHelp 
      Caption         =   "&Help"
      Begin VB.Menu mnuAbout 
         Caption         =   "&About"
      End
   End
End
Attribute VB_Name = "frmCalc"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmCalc - a scientific calculator built from CommandButton control arrays:
'   cmdDigit(0-9), cmdOp(0-5) for + - * / Mod x^y, cmdFunc(0-11) for the functions, cmdMem(0-3) for
'   the memory keys and optAngle(0-1) for degrees / radians. One Click handler per array uses Index.
' The keyboard works too (KeyPreview = True + Form_KeyPress), results go to a history ListBox that can
' be saved to / loaded from a text file, and a Timer shows the time.
Option Explicit

Private Enum PendingOp
    opNone = -1
    opAdd = 0
    opSubtract = 1
    opMultiply = 2
    opDivide = 3
    opMod = 4
    opPower = 5
End Enum

Private mAcc As Double              ' the left operand
Private mOp As PendingOp            ' the operation waiting for its right operand
Private mNewEntry As Boolean        ' the next digit starts a new number
Private mMemory As Double

Private Sub Form_Load()
    mOp = opNone
    mNewEntry = True
    tmrClock_Timer
End Sub

' ---------------------------------------------------------------- the number on the display
Private Property Get Display() As Double
    Display = CDbl(lblDisplay.Caption)
End Property

Private Property Let Display(ByVal Value As Double)
    lblDisplay.Caption = FormatResult(Value)
End Property

Private Sub KeyFeedback()
    If chkBeep.Value = vbChecked Then Beep
End Sub

' ---------------------------------------------------------------- entering numbers
Private Sub cmdDigit_Click(Index As Integer)
    KeyFeedback
    If mNewEntry Or lblDisplay.Caption = "0" Then
        lblDisplay.Caption = CStr(Index)
        mNewEntry = False
    ElseIf Len(lblDisplay.Caption) < 16 Then
        lblDisplay.Caption = lblDisplay.Caption & CStr(Index)
    End If
End Sub

Private Sub cmdDot_Click()
    KeyFeedback
    If mNewEntry Then
        lblDisplay.Caption = "0."
        mNewEntry = False
    ElseIf InStr(lblDisplay.Caption, ".") = 0 Then
        lblDisplay.Caption = lblDisplay.Caption & "."
    End If
End Sub

Private Sub cmdSign_Click()
    If lblDisplay.Caption <> "0" Then
        If Left$(lblDisplay.Caption, 1) = "-" Then
            lblDisplay.Caption = Mid$(lblDisplay.Caption, 2)
        Else
            lblDisplay.Caption = "-" & lblDisplay.Caption
        End If
    End If
End Sub

Private Sub cmdBack_Click()
    If mNewEntry Then Exit Sub
    If Len(lblDisplay.Caption) > 1 Then
        lblDisplay.Caption = Left$(lblDisplay.Caption, Len(lblDisplay.Caption) - 1)
    Else
        lblDisplay.Caption = "0"
    End If
End Sub

Private Sub cmdCE_Click()
    lblDisplay.Caption = "0"
    mNewEntry = True
End Sub

Private Sub cmdClear_Click()
    cmdCE_Click
    mAcc = 0
    mOp = opNone
    lblExpr.Caption = ""
    lblStatus.Caption = "Cleared"
End Sub

' ---------------------------------------------------------------- binary operations
Private Function OpSymbol(ByVal op As PendingOp) As String
    OpSymbol = Choose(op + 1, "+", "-", "*", "/", "Mod", "^")
End Function

' Apply the waiting operation to mAcc and the display; returns False on an error
Private Function ApplyPending() As Boolean
    Dim b As Double, r As Double
    On Error GoTo CalcError
    b = Display
    Select Case mOp
        Case opNone:     r = b
        Case opAdd:      r = mAcc + b
        Case opSubtract: r = mAcc - b
        Case opMultiply: r = mAcc * b
        Case opDivide:   r = mAcc / b
        Case opMod:      r = mAcc - b * Int(mAcc / b)     ' floating-point modulo
        Case opPower:    r = mAcc ^ b
    End Select
    If mOp <> opNone Then AddHistory FormatResult(mAcc) & " " & OpSymbol(mOp) & " " & FormatResult(b) & " = " & FormatResult(r)
    mAcc = r
    Display = r
    ApplyPending = True
    Exit Function
CalcError:
    ShowError Err.Number, Err.Description
End Function

Private Sub cmdOp_Click(Index As Integer)
    KeyFeedback
    If Not mNewEntry Or mOp = opNone Then
        If Not ApplyPending() Then Exit Sub
    End If
    mOp = Index
    mNewEntry = True
    lblExpr.Caption = FormatResult(mAcc) & " " & OpSymbol(mOp)
    lblStatus.Caption = Choose(Index + 1, "Add", "Subtract", "Multiply", "Divide", _
                               "Remainder of the division", "Raise to a power") & ": type the second number"
End Sub

Private Sub cmdEquals_Click()
    KeyFeedback
    If mOp = opNone Then Exit Sub
    If ApplyPending() Then
        lblStatus.Caption = "Result"
        lblExpr.Caption = ""
    End If
    mOp = opNone
    mNewEntry = True
End Sub

' ---------------------------------------------------------------- functions of the displayed number
Private Sub cmdFunc_Click(Index As Integer)
    Dim x As Double, r As Double, name As String, angle As Double
    KeyFeedback
    On Error GoTo CalcError
    x = Display
    angle = IIf(optAngle(0).Value, ToRadians(x), x)
    Select Case Index
        Case 0: r = Sin(angle): name = "sin"
        Case 1: r = Cos(angle): name = "cos"
        Case 2
            If Abs(Cos(angle)) < 0.000000000001 Then Err.Raise 11, , "tan is not defined here"
            r = Tan(angle): name = "tan"
        Case 3: r = Log10(x): name = "log"
        Case 4: r = Log(x): name = "ln"
        Case 5: r = Sqr(x): name = "sqrt"
        Case 6: r = x * x: name = "sqr"
        Case 7: r = x ^ 3: name = "cube"
        Case 8: r = 1 / x: name = "1/"
        Case 9: r = Factorial(x): name = "fact"
        Case 10: r = mAcc * x / 100: name = "%"       ' 200 + 10 % -> 20
        Case 11: r = PI: name = "pi"
    End Select
    ' sin(180 deg) should print 0, not 1.2E-16
    If Abs(r) < 0.000000000001 Then r = 0
    If Index <> 11 Then AddHistory name & "(" & FormatResult(x) & ") = " & FormatResult(r)
    Display = r
    mNewEntry = True
    lblStatus.Caption = cmdFunc(Index).Caption & " of " & FormatResult(x)
    Exit Sub
CalcError:
    ShowError Err.Number, Err.Description
End Sub

' ---------------------------------------------------------------- memory
Private Sub cmdMem_Click(Index As Integer)
    Select Case Index
        Case 0: mMemory = 0                     ' MC
        Case 1: Display = mMemory: mNewEntry = True     ' MR
        Case 2: mMemory = Display               ' MS
        Case 3: mMemory = mMemory + Display     ' M+
    End Select
    lblMem.Caption = IIf(mMemory <> 0, "M", "")
    lblStatus.Caption = "Memory = " & FormatResult(mMemory)
End Sub

Private Sub optAngle_Click(Index As Integer)
    lblStatus.Caption = "Angles in " & IIf(Index = 0, "degrees", "radians")
End Sub

' ---------------------------------------------------------------- errors and history
Private Sub ShowError(ByVal Number As Long, ByVal Description As String)
    lblDisplay.Caption = "Error"
    Select Case Number
        Case 11: lblStatus.Caption = "Cannot divide by zero"
        Case 5:  lblStatus.Caption = "Invalid input for this function"
        Case 6:  lblStatus.Caption = "The result is too large"
        Case Else: lblStatus.Caption = Description
    End Select
    mOp = opNone
    mNewEntry = True
End Sub

Private Sub AddHistory(ByVal Line As String)
    lstHistory.AddItem Line
    lstHistory.ListIndex = lstHistory.NewIndex
End Sub

Private Sub lstHistory_DblClick()
    ' double-click a history line: its result comes back to the display
    Dim p As Integer
    p = InStrRev(lstHistory.Text, "=")
    If p > 0 Then
        lblDisplay.Caption = Trim$(Mid$(lstHistory.Text, p + 1))
        mNewEntry = True
    End If
End Sub

' ---------------------------------------------------------------- keyboard
Private Sub Form_KeyPress(KeyAscii As Integer)
    Select Case KeyAscii
        Case 48 To 57: cmdDigit_Click KeyAscii - 48
        Case 46, 44: cmdDot_Click
        Case 43: cmdOp_Click opAdd
        Case 45: cmdOp_Click opSubtract
        Case 42: cmdOp_Click opMultiply
        Case 47: cmdOp_Click opDivide
        Case 94: cmdOp_Click opPower
        Case 13, 61: cmdEquals_Click
        Case 8: cmdBack_Click
        Case 27: cmdClear_Click
        Case Else: Exit Sub
    End Select
    KeyAscii = 0
End Sub

Private Sub tmrClock_Timer()
    lblClock.Caption = Format$(Time, "hh:nn:ss")
End Sub

' ---------------------------------------------------------------- menus
Private Sub mnuCopy_Click()
    Clipboard.Clear
    Clipboard.SetText lblDisplay.Caption
End Sub

Private Sub mnuPaste_Click()
    Dim s As String
    s = Trim$(Clipboard.GetText)
    If IsNumeric(s) Then
        Display = CDbl(s)
        mNewEntry = True
    Else
        lblStatus.Caption = "The clipboard has no number"
    End If
End Sub

Private Sub mnuClearHistory_Click()
    lstHistory.Clear
End Sub

Private Sub mnuSaveHistory_Click()
    Dim f As Integer, i As Integer
    f = FreeFile
    Open App.Path & "\history.txt" For Output As #f
    For i = 0 To lstHistory.ListCount - 1
        Print #f, lstHistory.List(i)
    Next
    Close #f
    lblStatus.Caption = lstHistory.ListCount & " lines saved to history.txt"
End Sub

Private Sub mnuLoadHistory_Click()
    Dim f As Integer, s As String
    If Dir$(App.Path & "\history.txt") = "" Then
        MsgBox "There is no saved history yet.", vbInformation
        Exit Sub
    End If
    lstHistory.Clear
    f = FreeFile
    Open App.Path & "\history.txt" For Input As #f
    Do While Not EOF(f)
        Line Input #f, s
        If s <> "" Then lstHistory.AddItem s
    Loop
    Close #f
    lblStatus.Caption = lstHistory.ListCount & " lines loaded"
End Sub

Private Sub mnuAbout_Click()
    MsgBox "Scientific Calculator" & vbCrLf & "A VB6 learning sample - (c) 2026 Musoftware" & vbCrLf & _
           "https://musoftwares.com - MIT License", vbInformation, "About"
End Sub

Private Sub mnuExit_Click()
    Unload Me
End Sub
