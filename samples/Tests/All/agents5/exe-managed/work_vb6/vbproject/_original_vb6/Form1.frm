VERSION 5.00
Begin VB.Form Form1
   Caption         =   "Hello VB"
   ClientHeight    =   3600
   ClientWidth     =   4800
   ScaleMode       =   1  'Twip
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton Command1
      Caption         =   "Click me"
      Height          =   495
      Left            =   240
      Top             =   360
      Width           =   1455
   End
   Begin VB.TextBox Text1
      Text            =   "abc"
      Height          =   375
      Left            =   240
      Top             =   1080
      Width           =   2175
   End
   Begin VB.Label Label1
      Caption         =   "Result"
      Height          =   255
      Left            =   120
      Top             =   120
      Width           =   1815
   End
   Begin VB.Menu mnuFile
      Caption         =   "&File"
   End
End
Attribute VB_Name = "Form1"
Private Sub Command1_Click()
   ' compiled code not decompiled - rewrite this procedure (1 event(s) with code in the exe)
End Sub
Private Sub mnuFile_Click()
   ' compiled code not decompiled - rewrite this procedure (1 event(s) with code in the exe)
End Sub
