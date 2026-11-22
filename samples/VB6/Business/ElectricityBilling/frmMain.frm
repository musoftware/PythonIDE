VERSION 5.00
Begin VB.Form frmMain
   Caption         =   "ElectricityBilling"
   ClientHeight    =   4320
   ClientLeft      =   165
   ClientTop       =   855
   ClientWidth     =   7680
   LinkTopic       =   "Form1"
   ScaleHeight     =   4320
   ScaleWidth      =   7680
   StartUpPosition =   2  'CenterScreen
   Begin VB.Timer tmrClock
      Interval        =   1000
      Left            =   7080
      Top             =   3720
   End
   Begin VB.PictureBox picToolbar
      Align           =   1  'Align Top
      BackColor       =   &H00C0C0C0&
      Height          =   615
      Left            =   0
      ScaleHeight     =   555
      ScaleWidth      =   7620
      TabIndex        =   0
      Top             =   0
      Width           =   7680
      Begin VB.CommandButton cmdTool
         Caption         =   "Bills report"
         Height          =   435
         Index           =   3
         Left            =   4560
         TabIndex        =   4
         Top             =   60
         Width           =   1455
      End
      Begin VB.CommandButton cmdTool
         Caption         =   "New bill"
         Height          =   435
         Index           =   2
         Left            =   3060
         TabIndex        =   3
         Top             =   60
         Width           =   1455
      End
      Begin VB.CommandButton cmdTool
         Caption         =   "Meter reading"
         Height          =   435
         Index           =   1
         Left            =   1560
         TabIndex        =   2
         Top             =   60
         Width           =   1455
      End
      Begin VB.CommandButton cmdTool
         Caption         =   "Consumers"
         Height          =   435
         Index           =   0
         Left            =   60
         TabIndex        =   1
         Top             =   60
         Width           =   1455
      End
   End
   Begin VB.Frame fraSummary
      Caption         =   "Today"
      Height          =   2655
      Left            =   240
      TabIndex        =   5
      Top             =   840
      Width           =   7215
      Begin VB.Label lblStat
         Caption         =   "-"
         Height          =   315
         Index           =   3
         Left            =   240
         TabIndex        =   9
         Top             =   1920
         Width           =   6735
      End
      Begin VB.Label lblStat
         Caption         =   "-"
         Height          =   315
         Index           =   2
         Left            =   240
         TabIndex        =   8
         Top             =   1440
         Width           =   6735
      End
      Begin VB.Label lblStat
         Caption         =   "-"
         Height          =   315
         Index           =   1
         Left            =   240
         TabIndex        =   7
         Top             =   960
         Width           =   6735
      End
      Begin VB.Label lblStat
         Caption         =   "-"
         Height          =   315
         Index           =   0
         Left            =   240
         TabIndex        =   6
         Top             =   480
         Width           =   6735
      End
   End
   Begin VB.Label lblClock
      Alignment       =   1  'Right Justify
      Caption         =   "--:--:--"
      Height          =   255
      Left            =   4560
      TabIndex        =   11
      Top             =   3840
      Width           =   2415
   End
   Begin VB.Label lblUser
      Caption         =   "-"
      Height          =   255
      Left            =   240
      TabIndex        =   10
      Top             =   3840
      Width           =   4095
   End
   Begin VB.Menu mnuMasters
      Caption         =   "&Masters"
      Begin VB.Menu mnuConsumers
         Caption         =   "&Consumers..."
      End
      Begin VB.Menu mnuSep1
         Caption         =   "-"
      End
      Begin VB.Menu mnuExit
         Caption         =   "E&xit"
      End
   End
   Begin VB.Menu mnuBilling
      Caption         =   "&Billing"
      Begin VB.Menu mnuReading
         Caption         =   "Meter &reading..."
         Shortcut        =   {F5}
      End
      Begin VB.Menu mnuBill
         Caption         =   "&Generate bill..."
         Shortcut        =   {F6}
      End
   End
   Begin VB.Menu mnuReports
      Caption         =   "&Reports"
      Begin VB.Menu mnuRptUnpaid
         Caption         =   "&Unpaid bills"
      End
      Begin VB.Menu mnuRptTariffs
         Caption         =   "&Tariff slabs (text file)"
      End
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmMain - menus, a "toolbar" (a PictureBox aligned to the top holding a CommandButton
' control array), a summary of the database (a Label control array) and a Timer clock.
Option Explicit

Private Sub Form_Load()
    Me.Caption = Setting("CompanyName") & " - billing"
    lblUser.Caption = "User: " & gUser & " (" & gRole & ")"
    RefreshSummary
    tmrClock_Timer
End Sub

' Counts shown in the "Today" frame
Public Sub RefreshSummary()
    lblStat(0).Caption = "Consumers: " & Scalar("SELECT COUNT(*) FROM Consumers WHERE Active")
    lblStat(1).Caption = "Readings waiting for a bill: " & Scalar("SELECT COUNT(*) FROM Readings WHERE NOT Billed")
    lblStat(2).Caption = "Unpaid bills: " & Scalar("SELECT COUNT(*) FROM Bills WHERE NOT Paid")
    lblStat(3).Caption = "Amount due: " & Format$(Val(Scalar("SELECT SUM(Total) FROM Bills WHERE NOT Paid") & ""), "#,##0.00")
End Sub

Private Function Scalar(ByVal sql As String) As Variant
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute(sql)
    Scalar = rs.Fields(0).Value
    If IsNull(Scalar) Then Scalar = 0
    rs.Close
End Function

Private Sub tmrClock_Timer()
    lblClock.Caption = Format$(Now, "ddd dd mmm yyyy  hh:nn:ss")
End Sub

Private Sub cmdTool_Click(Index As Integer)
    Select Case Index
        Case 0: mnuConsumers_Click
        Case 1: mnuReading_Click
        Case 2: mnuBill_Click
        Case 3: mnuRptUnpaid_Click
    End Select
End Sub

Private Sub mnuConsumers_Click()
    frmConsumers.Show
End Sub

Private Sub mnuReading_Click()
    frmReading.Show
End Sub

Private Sub mnuBill_Click()
    frmBill.Show
End Sub

Private Sub mnuRptUnpaid_Click()
    deBilling.cmdUnpaid
    rptUnpaid.Show
End Sub

' Write the tariff slabs to a text file and open it in Notepad
Private Sub mnuRptTariffs_Click()
    Dim f As Integer, rs As ADODB.Recordset, path As String
    path = App.Path & "\tariffs.txt"
    f = FreeFile
    Open path For Output As #f
    Print #f, "Tariff slabs - " & Format$(Date, "yyyy-mm-dd")
    Set rs = cn.Execute("SELECT Category, FromUnit, ToUnit, Rate FROM Tariffs ORDER BY Category, FromUnit")
    Do Until rs.EOF
        Write #f, rs!Category, rs!FromUnit, rs!ToUnit, CDbl(rs!Rate)
        rs.MoveNext
    Loop
    rs.Close
    Close #f
    Shell "notepad.exe """ & path & """", vbNormalFocus
End Sub

Private Sub mnuExit_Click()
    Unload Me
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Dim f As Form
    For Each f In Forms                     ' close the other windows too
        If Not f Is Me Then Unload f
    Next
    If cn.State = adStateOpen Then cn.Close
End Sub
