VERSION 5.00
Object = "{6C0F7E10-3B7E-4C1E-9A65-2B5E7C1D0A11}#1.0#0"; "LEDLIB.OCX"
Begin VB.Form Form1
   Caption         =   "Rating demo"
   ClientHeight    =   3000
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   4500
   LinkTopic       =   "Form1"
   ScaleHeight     =   3000
   ScaleWidth      =   4500
   StartUpPosition =   2  'CenterScreen
   Begin VB.Label lblInfo
      Caption         =   "Rate it"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   2000
   End
   Begin RatingDemo.RatingBar rate1
      Height          =   420
      Left            =   240
      ReadOnly        =   -1  'True
      StarColor       =   &H000000FF&
      TabIndex        =   0
      Top             =   600
      Value           =   4
      Width           =   2100
   End
   Begin LedLib.Led led1
      Color           =   &H0000C000&
      Height          =   360
      Left            =   2550
      LightOn         =   -1  'True
      TabIndex        =   0
      Top             =   600
      Width           =   360
   End
End
Attribute VB_Name = "Form1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub rate1_ValueChanged()
    lblInfo.Caption = "Rating: " & rate1.Value
End Sub
