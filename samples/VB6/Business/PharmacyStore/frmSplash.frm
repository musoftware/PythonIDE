VERSION 5.00
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmSplash 
   BackColor       =   &H00808000&
   BorderStyle     =   0  'None
   Caption         =   "PharmacyStore"
   ClientHeight    =   2400
   ClientLeft      =   0
   ClientTop       =   0
   ClientWidth     =   5400
   LinkTopic       =   "Form1"
   ScaleHeight     =   2400
   ScaleWidth      =   5400
   ShowInTaskbar   =   0   'False
   StartUpPosition =   2  'CenterScreen
   Begin VB.Timer tmrSplash 
      Interval        =   50
      Left            =   4800
      Top             =   120
   End
   Begin MSComctlLib.ProgressBar prgSplash 
      Height          =   255
      Left            =   360
      TabIndex        =   0
      Top             =   1800
      Width           =   4680
      _ExtentX        =   8255
      _ExtentY        =   450
      _Version        =   393216
      Appearance      =   1
   End
   Begin VB.Shape shpCross 
      BackColor       =   &H0000C000&
      BackStyle       =   1  'Opaque
      BorderStyle     =   0  'Transparent
      Height          =   735
      Left            =   360
      Top             =   480
      Width           =   255
   End
   Begin VB.Shape shpCross2 
      BackColor       =   &H0000C000&
      BackStyle       =   1  'Opaque
      BorderStyle     =   0  'Transparent
      Height          =   255
      Left            =   120
      Top             =   720
      Width           =   735
   End
   Begin VB.Label lblName 
      BackStyle       =   0  'Transparent
      Caption         =   "PharmacyStore"
      BeginProperty Font 
         Name            =   "Verdana"
         Size            =   18
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      ForeColor       =   &H00FFFFFF&
      Height          =   495
      Left            =   1080
      TabIndex        =   1
      Top             =   540
      Width           =   4095
   End
   Begin VB.Label lblLoading 
      BackStyle       =   0  'Transparent
      Caption         =   "Loading..."
      ForeColor       =   &H00E0E0E0&
      Height          =   255
      Left            =   1080
      TabIndex        =   2
      Top             =   1140
      Width           =   4095
   End
End
Attribute VB_Name = "frmSplash"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmSplash - a borderless splash: the Timer fills the ProgressBar, then the login form opens.
' The green cross is two Shape controls.
Option Explicit

Private Sub tmrSplash_Timer()
    prgSplash.Value = prgSplash.Value + 5
    lblLoading.Caption = "Loading... " & prgSplash.Value & "%"
    If prgSplash.Value >= 100 Then
        tmrSplash.Enabled = False
        Unload Me
        frmLogin.Show
    End If
End Sub
