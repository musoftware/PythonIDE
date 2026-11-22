VERSION 5.00
Begin VB.Form frmAbout
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "About BankManager"
   ClientHeight    =   2160
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   4680
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   2160
   ScaleWidth      =   4680
   ShowInTaskbar   =   0   'False
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdOK
      Cancel          =   -1  'True
      Caption         =   "OK"
      Default         =   -1  'True
      Height          =   375
      Left            =   3360
      TabIndex        =   0
      Top             =   1620
      Width           =   1095
   End
   Begin VB.Label lblInfo
      Caption         =   "-"
      Height          =   855
      Left            =   240
      TabIndex        =   2
      Top             =   660
      Width           =   4215
   End
   Begin VB.Label lblTitle
      Caption         =   "BankManager"
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
      Left            =   240
      TabIndex        =   1
      Top             =   180
      Width           =   4215
   End
End
Attribute VB_Name = "frmAbout"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmAbout - a modal dialog (Show vbModal) with the version from App.Major / App.Minor.
Option Explicit

Private Sub Form_Load()
    lblInfo.Caption = "Version " & App.Major & "." & App.Minor & "." & App.Revision & vbCrLf & _
                      "A VB6 learning sample - (c) 2026 Musoftware" & vbCrLf & "https://musoftwares.com - MIT License"
End Sub

Private Sub cmdOK_Click()
    Unload Me
End Sub
