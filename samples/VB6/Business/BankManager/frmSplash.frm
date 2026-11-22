VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmSplash
   BackColor       =   &H00804000&
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "BankManager"
   ClientHeight    =   3000
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   6000
   ControlBox      =   0   'False
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   3000
   ScaleWidth      =   6000
   ShowInTaskbar   =   0   'False
   StartUpPosition =   2  'CenterScreen
   Begin VB.Timer tmrLoad
      Interval        =   40
      Left            =   5400
      Top             =   120
   End
   Begin MSComctlLib.ProgressBar prgLoad
      Height          =   300
      Left            =   480
      TabIndex        =   0
      Top             =   2160
      Width           =   5040
      _ExtentX        =   8890
      _ExtentY        =   529
      _Version        =   393216
      Appearance      =   1
      Max             =   100
   End
   Begin VB.Shape shpFrame
      BorderColor     =   &H00FFFFFF&
      BorderWidth     =   2
      Height          =   2760
      Left            =   120
      Top             =   120
      Width           =   5760
   End
   Begin VB.Label lblStatus
      BackStyle       =   0  'Transparent
      Caption         =   "Starting..."
      ForeColor       =   &H00FFFFFF&
      Height          =   255
      Left            =   480
      TabIndex        =   3
      Top             =   2520
      Width           =   5040
   End
   Begin VB.Label lblSub
      BackStyle       =   0  'Transparent
      Caption         =   "A VB6 learning sample by Musoftware"
      ForeColor       =   &H00FFFFC0&
      Height          =   255
      Left            =   480
      TabIndex        =   2
      Top             =   1320
      Width           =   5040
   End
   Begin VB.Label lblTitle
      BackStyle       =   0  'Transparent
      Caption         =   "BankManager"
      BeginProperty Font
         Name            =   "Arial"
         Size            =   24
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H00FFFFFF&
      Height          =   615
      Left            =   480
      TabIndex        =   1
      Top             =   600
      Width           =   5040
   End
End
Attribute VB_Name = "frmSplash"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmSplash - a start-up screen: a Timer moves the ProgressBar and changes the status text,
' then the splash unloads itself and opens the login form.
Option Explicit

Private Sub Form_Load()
    lblTitle.Caption = AppSetting("BankName", APP_TITLE)
    prgLoad.Value = 0
End Sub

Private Sub tmrLoad_Timer()
    Dim v As Integer
    v = prgLoad.Value + 4
    If v > 100 Then v = 100
    prgLoad.Value = v
    Select Case v
        Case Is < 30: lblStatus.Caption = "Opening the database..."
        Case Is < 70: lblStatus.Caption = "Loading settings..."
        Case Else:    lblStatus.Caption = "Ready"
    End Select
    If v >= 100 Then
        tmrLoad.Enabled = False
        frmLogin.Show
        Unload Me
    End If
End Sub
