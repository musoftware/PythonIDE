VERSION 5.00
Begin VB.Form frmMain 
   Caption         =   "DataEnvironment + DataReport"
   ClientHeight    =   1500
   ClientLeft      =   60
   ClientTop       =   450
   ClientWidth     =   4500
   LinkTopic       =   "Form1"
   ScaleHeight     =   1500
   ScaleWidth      =   4500
   StartUpPosition =   3  'Windows Default
   Begin VB.CommandButton cmdReport 
      Caption         =   "Show &report"
      Height          =   495
      Left            =   1320
      TabIndex        =   0
      Top             =   480
      Width           =   1815
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Sub Form_Load()
    Dim n As Integer, names As String
    DataEnvironment1.Command1
    With DataEnvironment1.rsCommand1
        Do Until .EOF
            n = n + 1
            .MoveNext
        Loop
        .Close
    End With
    Debug.Print "Command1 rows=" & n
    DataEnvironment1.cmdByPrice 30
    Do Until DataEnvironment1.rscmdByPrice.EOF
        names = names & DataEnvironment1.rscmdByPrice!Name & " "
        DataEnvironment1.rscmdByPrice.MoveNext
    Loop
    Debug.Print "cheaper than 30: " & Trim(names)
    Debug.Print "connection open: " & (DataEnvironment1.conShop.State = adStateOpen)
End Sub

Private Sub cmdReport_Click()
    DataReport1.Show
End Sub
