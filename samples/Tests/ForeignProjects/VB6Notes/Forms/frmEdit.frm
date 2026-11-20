VERSION 5.00
Begin VB.Form frmEdit
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "New note"
   ClientHeight    =   1815
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   4680
   LinkTopic       =   "Form2"
   ScaleHeight     =   1815
   ScaleWidth      =   4680
   StartUpPosition =   1  'CenterOwner
   Begin VB.TextBox txtTitle
      Height          =   375
      Left            =   120
      TabIndex        =   0
      Top             =   480
      Width           =   4455
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "ÍÝÙ"
      Default         =   -1  'True
      Height          =   375
      Left            =   3360
      TabIndex        =   1
      Top             =   1200
      Width           =   1215
   End
   Begin VB.Label lblTitle
      Caption         =   "Title:"
      Height          =   255
      Left            =   120
      TabIndex        =   2
      Top             =   120
      Width           =   1215
   End
End
Attribute VB_Name = "frmEdit"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Sub cmdSave_Click()
    If Len(Trim$(txtTitle.Text)) > 0 Then AddNote txtTitle.Text
    Unload Me
End Sub
