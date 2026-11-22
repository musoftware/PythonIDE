VERSION 5.00
Object = "{F9043C88-F6F2-101A-A3C9-08002B2F49FB}#1.2#0"; "COMDLG32.OCX"
Begin VB.Form frmLab
   BackColor       =   &H00F0F0F0&
   BorderStyle     =   1  'Fixed Single
   Caption         =   "Logic Gate Lab"
   ClientHeight    =   5640
   ClientLeft      =   45
   ClientTop       =   735
   ClientWidth     =   9000
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   5640
   ScaleWidth      =   9000
   StartUpPosition =   2  'CenterScreen
   Begin MSComDlg.CommonDialog dlgFile
      Left            =   8400
      Top             =   4920
      _ExtentX        =   847
      _ExtentY        =   847
      _Version        =   393216
      DefaultExt      =   "lgl"
      Filter          =   "Logic lab settings (*.lgl)|*.lgl|All files (*.*)|*.*"
   End
   Begin VB.Timer tmrPulse
      Enabled         =   0   'False
      Interval        =   60
      Left            =   7920
      Top             =   4920
   End
   Begin VB.Timer tmrClock
      Enabled         =   0   'False
      Interval        =   500
      Left            =   7440
      Top             =   4920
   End
   Begin VB.Frame fraGate
      Caption         =   "Gate"
      Height          =   3015
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   2295
      Begin VB.OptionButton optGate
         Caption         =   "XNOR"
         Height          =   255
         Index           =   6
         Left            =   240
         TabIndex        =   7
         Top             =   2520
         Width           =   1815
      End
      Begin VB.OptionButton optGate
         Caption         =   "XOR"
         Height          =   255
         Index           =   5
         Left            =   240
         TabIndex        =   6
         Top             =   2160
         Width           =   1815
      End
      Begin VB.OptionButton optGate
         Caption         =   "NOR"
         Height          =   255
         Index           =   4
         Left            =   240
         TabIndex        =   5
         Top             =   1800
         Width           =   1815
      End
      Begin VB.OptionButton optGate
         Caption         =   "NAND"
         Height          =   255
         Index           =   3
         Left            =   240
         TabIndex        =   4
         Top             =   1440
         Width           =   1815
      End
      Begin VB.OptionButton optGate
         Caption         =   "NOT (uses A)"
         Height          =   255
         Index           =   2
         Left            =   240
         TabIndex        =   3
         Top             =   1080
         Width           =   1815
      End
      Begin VB.OptionButton optGate
         Caption         =   "OR"
         Height          =   255
         Index           =   1
         Left            =   240
         TabIndex        =   2
         Top             =   720
         Width           =   1815
      End
      Begin VB.OptionButton optGate
         Caption         =   "AND"
         Height          =   255
         Index           =   0
         Left            =   240
         TabIndex        =   1
         Top             =   360
         Value           =   -1  'True
         Width           =   1815
      End
   End
   Begin VB.CommandButton cmdTruth
      Caption         =   "&Truth table..."
      Height          =   375
      Left            =   120
      TabIndex        =   8
      Top             =   3240
      Width           =   2295
   End
   Begin VB.CheckBox chkA
      Caption         =   "A"
      Height          =   375
      Left            =   2640
      Style           =   1  'Graphical
      TabIndex        =   9
      Top             =   540
      Width           =   495
   End
   Begin VB.CheckBox chkB
      Caption         =   "B"
      Height          =   375
      Left            =   2640
      Style           =   1  'Graphical
      TabIndex        =   10
      Top             =   1740
      Width           =   495
   End
   Begin VB.CheckBox chkClock
      Caption         =   "Clock drives A"
      Height          =   255
      Left            =   2640
      TabIndex        =   11
      Top             =   2400
      Width           =   1815
   End
   Begin VB.HScrollBar hsbSpeed
      Height          =   255
      LargeChange     =   100
      Left            =   2640
      Max             =   1000
      Min             =   100
      SmallChange     =   50
      TabIndex        =   12
      Top             =   2760
      Value           =   500
      Width           =   2055
   End
   Begin VB.Frame fraCircuit
      Caption         =   "Two-gate circuit:  (A gate1 B) gate2 C"
      Height          =   1695
      Left            =   2640
      TabIndex        =   14
      Top             =   3240
      Width           =   6255
      Begin VB.CheckBox chkC
         Caption         =   "C"
         Height          =   375
         Left            =   3360
         Style           =   1  'Graphical
         TabIndex        =   19
         Top             =   300
         Width           =   495
      End
      Begin VB.ComboBox cboOp2
         Height          =   315
         Left            =   1800
         Style           =   2  'Dropdown List
         TabIndex        =   18
         Top             =   360
         Width           =   1335
      End
      Begin VB.ComboBox cboOp1
         Height          =   315
         Left            =   240
         Style           =   2  'Dropdown List
         TabIndex        =   17
         Top             =   360
         Width           =   1335
      End
      Begin VB.Shape shpCircuitOut
         BackColor       =   &H00404040&
         BackStyle       =   1  'Opaque
         Height          =   375
         Left            =   5400
         Shape           =   3  'Circle
         Top             =   300
         Width           =   375
      End
      Begin VB.Label lblCircuit
         Caption         =   "-"
         Height          =   615
         Left            =   240
         TabIndex        =   20
         Top             =   900
         Width           =   5775
      End
   End
   Begin VB.Shape shpPulse
      BackColor       =   &H0000FFFF&
      BackStyle       =   1  'Opaque
      BorderColor     =   &H0000C0C0&
      Height          =   120
      Left            =   6300
      Shape           =   3  'Circle
      Top             =   1250
      Visible         =   0   'False
      Width           =   120
   End
   Begin VB.Shape shpOut
      BackColor       =   &H00404040&
      BackStyle       =   1  'Opaque
      Height          =   400
      Left            =   7800
      Shape           =   3  'Circle
      Top             =   1110
      Width           =   400
   End
   Begin VB.Line linOut
      BorderColor     =   &H00404040&
      BorderWidth     =   3
      X1              =   6300
      X2              =   7800
      Y1              =   1310
      Y2              =   1310
   End
   Begin VB.Line linB
      BorderColor     =   &H00404040&
      BorderWidth     =   3
      X1              =   3600
      X2              =   4800
      Y1              =   1910
      Y2              =   1910
   End
   Begin VB.Line linA
      BorderColor     =   &H00404040&
      BorderWidth     =   3
      X1              =   3600
      X2              =   4800
      Y1              =   710
      Y2              =   710
   End
   Begin VB.Shape shpInB
      BackColor       =   &H00404040&
      BackStyle       =   1  'Opaque
      Height          =   300
      Left            =   3300
      Shape           =   3  'Circle
      Top             =   1760
      Width           =   300
   End
   Begin VB.Shape shpInA
      BackColor       =   &H00404040&
      BackStyle       =   1  'Opaque
      Height          =   300
      Left            =   3300
      Shape           =   3  'Circle
      Top             =   560
      Width           =   300
   End
   Begin VB.Label lblGate
      Alignment       =   2  'Center
      BackStyle       =   0  'Transparent
      Caption         =   "AND"
      BeginProperty Font
         Name            =   "Arial"
         Size            =   14.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   4800
      TabIndex        =   13
      Top             =   1140
      Width           =   1500
   End
   Begin VB.Shape shpGate
      BackColor       =   &H00FFE0C0&
      BackStyle       =   1  'Opaque
      BorderWidth     =   2
      Height          =   1800
      Left            =   4800
      Shape           =   4  'Rounded Rectangle
      Top             =   400
      Width           =   1500
   End
   Begin VB.Label lblOut
      Caption         =   "0"
      BeginProperty Font
         Name            =   "Arial"
         Size            =   14.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   8340
      TabIndex        =   15
      Top             =   1110
      Width           =   495
   End
   Begin VB.Label lblSpeed
      Caption         =   "500 ms"
      Height          =   255
      Left            =   4800
      TabIndex        =   16
      Top             =   2760
      Width           =   975
   End
   Begin VB.Label lblStatus
      BorderStyle     =   1  'Fixed Single
      Caption         =   "Click A and B to switch the inputs."
      Height          =   285
      Left            =   120
      TabIndex        =   21
      Top             =   5280
      Width           =   8775
   End
   Begin VB.Menu mnuFile
      Caption         =   "&File"
      Begin VB.Menu mnuSave
         Caption         =   "&Save setup..."
      End
      Begin VB.Menu mnuOpen
         Caption         =   "&Open setup..."
      End
      Begin VB.Menu mnuSep
         Caption         =   "-"
      End
      Begin VB.Menu mnuExit
         Caption         =   "E&xit"
      End
   End
   Begin VB.Menu mnuHelp
      Caption         =   "&Help"
      Begin VB.Menu mnuAbout
         Caption         =   "&About"
      End
   End
End
Attribute VB_Name = "frmLab"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmLab - a logic gate workbench drawn with Shape and Line controls:
'   * the inputs A and B are graphical CheckBoxes; the wires (Line controls) and the lamps (Shape
'     controls) turn green for 1 and grey for 0
'   * the gate is chosen with an OptionButton control array; its logic lives in clsGate
'   * a Timer can drive A as a clock (speed from an HScrollBar); a second Timer moves a small Shape
'     along the output wire while the output is 1
'   * a two-gate circuit uses two clsGate objects in an array
'   * File > Save / Open writes the setup with Write # / Input # (CommonDialog for the file name)
Option Explicit

Private mGate As clsGate
Private mCircuit(1) As clsGate          ' gate 1 and gate 2 of the small circuit

Private Sub Form_Load()
    Dim i As Integer, names As Variant
    Set mGate = New clsGate
    Set mCircuit(0) = New clsGate
    Set mCircuit(1) = New clsGate
    names = Array("AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR")
    For i = LBound(names) To UBound(names)
        cboOp1.AddItem names(i)
        cboOp2.AddItem names(i)
    Next
    cboOp1.ListIndex = gkAnd
    cboOp2.ListIndex = gkOr
    Refresh_
End Sub

' Recalculate everything and repaint the wires and lamps
Private Sub Refresh_()
    Dim a As Boolean, b As Boolean, out As Boolean
    a = (chkA.Value = vbChecked)
    b = (chkB.Value = vbChecked)
    out = mGate.Evaluate(a, b)
    shpInA.FillColor = SignalColor(a): shpInA.BackColor = SignalColor(a)
    shpInB.BackColor = SignalColor(b)
    linA.BorderColor = SignalColor(a)
    linB.BorderColor = IIf(mGate.Inputs = 1, &HC0C0C0, SignalColor(b))
    linOut.BorderColor = SignalColor(out)
    shpOut.BackColor = SignalColor(out)
    lblOut.Caption = Bit(out)
    lblGate.Caption = mGate.Name
    lblStatus.Caption = mGate.Expression("A", "B") & " = " & Bit(out) & "   (A=" & Bit(a) & ", B=" & Bit(b) & ")"
    tmrPulse.Enabled = out
    shpPulse.Visible = out
    RefreshCircuit
End Sub

Private Sub RefreshCircuit()
    Dim a As Boolean, b As Boolean, c As Boolean, mid1 As Boolean, out As Boolean
    a = (chkA.Value = vbChecked)
    b = (chkB.Value = vbChecked)
    c = (chkC.Value = vbChecked)
    If cboOp1.ListIndex < 0 Or cboOp2.ListIndex < 0 Then Exit Sub
    mCircuit(0).Kind = cboOp1.ListIndex
    mCircuit(1).Kind = cboOp2.ListIndex
    mid1 = mCircuit(0).Evaluate(a, b)
    out = mCircuit(1).Evaluate(mid1, c)
    shpCircuitOut.BackColor = SignalColor(out)
    lblCircuit.Caption = mCircuit(1).Expression("(" & mCircuit(0).Expression("A", "B") & ")", "C") & " = " & Bit(out)
End Sub

Private Sub optGate_Click(Index As Integer)
    mGate.Kind = Index
    Refresh_
End Sub

Private Sub chkA_Click()
    Refresh_
End Sub

Private Sub chkB_Click()
    Refresh_
End Sub

Private Sub chkC_Click()
    RefreshCircuit
End Sub

Private Sub cboOp1_Click()
    RefreshCircuit
End Sub

Private Sub cboOp2_Click()
    RefreshCircuit
End Sub

' ---------------------------------------------------------------- timers
Private Sub chkClock_Click()
    tmrClock.Interval = hsbSpeed.Value
    tmrClock.Enabled = (chkClock.Value = vbChecked)
End Sub

Private Sub hsbSpeed_Change()
    lblSpeed.Caption = hsbSpeed.Value & " ms"
    tmrClock.Interval = hsbSpeed.Value
End Sub

Private Sub tmrClock_Timer()
    ' toggle input A: setting Value fires chkA_Click
    chkA.Value = IIf(chkA.Value = vbChecked, vbUnchecked, vbChecked)
End Sub

Private Sub tmrPulse_Timer()
    ' a dot runs along the output wire from linOut.X1 to linOut.X2
    shpPulse.Left = shpPulse.Left + 150
    If shpPulse.Left > linOut.X2 - shpPulse.Width Then shpPulse.Left = linOut.X1
End Sub

' ---------------------------------------------------------------- truth table
Public Property Get CurrentKind() As GateKind
    CurrentKind = mGate.Kind
End Property

Private Sub cmdTruth_Click()
    frmTruth.ShowGate mGate.Kind
    frmTruth.Show                       ' modeless: the lab stays usable
End Sub

' ---------------------------------------------------------------- save / open
Private Sub mnuSave_Click()
    Dim f As Integer
    On Error GoTo Cancelled
    dlgFile.CancelError = True
    dlgFile.DialogTitle = "Save setup"
    dlgFile.ShowSave
    f = FreeFile
    Open dlgFile.FileName For Output As #f
    Write #f, "LogicGateLab", 1
    Write #f, mGate.Kind, chkA.Value, chkB.Value, chkC.Value
    Write #f, cboOp1.ListIndex, cboOp2.ListIndex, hsbSpeed.Value
    Close #f
    lblStatus.Caption = "Saved " & dlgFile.FileTitle
Cancelled:
End Sub

Private Sub mnuOpen_Click()
    Dim f As Integer, tag As String, ver As Integer
    Dim kind As Integer, a As Integer, b As Integer, c As Integer, op1 As Integer, op2 As Integer, speed As Integer
    On Error GoTo Failed
    dlgFile.CancelError = True
    dlgFile.DialogTitle = "Open setup"
    dlgFile.ShowOpen
    f = FreeFile
    Open dlgFile.FileName For Input As #f
    Input #f, tag, ver
    If tag <> "LogicGateLab" Then
        Close #f
        MsgBox "This is not a Logic Gate Lab file.", vbExclamation
        Exit Sub
    End If
    Input #f, kind, a, b, c
    Input #f, op1, op2, speed
    Close #f
    optGate(kind).Value = True
    chkA.Value = a
    chkB.Value = b
    chkC.Value = c
    cboOp1.ListIndex = op1
    cboOp2.ListIndex = op2
    hsbSpeed.Value = speed
    Refresh_
    lblStatus.Caption = "Opened " & dlgFile.FileTitle
    Exit Sub
Failed:
    If Err.Number <> cdlCancel Then MsgBox "Could not open the file: " & Err.Description, vbExclamation
End Sub

Private Sub mnuAbout_Click()
    MsgBox "Logic Gate Lab" & vbCrLf & "A VB6 learning sample - (c) 2026 Musoftware" & vbCrLf & _
           "https://musoftwares.com - MIT License", vbInformation
End Sub

Private Sub mnuExit_Click()
    Unload Me
End Sub

Private Sub Form_Unload(Cancel As Integer)
    tmrClock.Enabled = False
    tmrPulse.Enabled = False
    Unload frmTruth
End Sub
