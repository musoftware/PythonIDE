VERSION 5.00
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Begin VB.Form frmReading
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "Meter reading"
   ClientHeight    =   4440
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   6480
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   4440
   ScaleWidth      =   6480
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdClose
      Caption         =   "Close"
      Height          =   375
      Left            =   5160
      TabIndex        =   10
      Top             =   1680
      Width           =   1095
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "&Save reading"
      Height          =   375
      Left            =   3840
      TabIndex        =   9
      Top             =   1680
      Width           =   1215
   End
   Begin VB.TextBox txtCurrent
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   1560
      TabIndex        =   6
      Top             =   1200
      Width           =   1335
   End
   Begin VB.ComboBox cboConsumer
      Height          =   315
      Left            =   1560
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   240
      Width           =   4695
   End
   Begin MSComCtl2.DTPicker dtpRead
      Height          =   315
      Left            =   4560
      TabIndex        =   8
      Top             =   1200
      Width           =   1695
      _ExtentX        =   2990
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   46023
   End
   Begin MSFlexGridLib.MSFlexGrid grdHistory
      Height          =   2055
      Left            =   120
      TabIndex        =   11
      Top             =   2280
      Width           =   6255
      _ExtentX        =   11033
      _ExtentY        =   3625
      _Version        =   393216
      Rows            =   1
      Cols            =   4
      FixedCols       =   0
      FormatString    =   "<Date      |>Previous|>Current|>Units"
   End
   Begin VB.Label lblDate
      Caption         =   "Date:"
      Height          =   255
      Left            =   3960
      TabIndex        =   7
      Top             =   1260
      Width           =   615
   End
   Begin VB.Label lblCurrent
      Caption         =   "Current reading:"
      Height          =   255
      Left            =   120
      TabIndex        =   5
      Top             =   1260
      Width           =   1335
   End
   Begin VB.Label lblPrev
      Caption         =   "0"
      BeginProperty Font
         Name            =   "MS Sans Serif"
         Size            =   9.75
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   255
      Left            =   1560
      TabIndex        =   4
      Top             =   780
      Width           =   1335
   End
   Begin VB.Label lblPrevCaption
      Caption         =   "Previous reading:"
      Height          =   255
      Left            =   120
      TabIndex        =   3
      Top             =   780
      Width           =   1335
   End
   Begin VB.Label lblConsumer
      Caption         =   "Consumer:"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   300
      Width           =   1335
   End
   Begin VB.Label lblCategory
      Caption         =   "-"
      Height          =   255
      Left            =   3000
      TabIndex        =   2
      Top             =   780
      Width           =   3255
   End
End
Attribute VB_Name = "frmReading"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmReading - record a meter reading: the consumer comes from a ComboBox (meter number in
' ItemData), the previous reading is looked up, the new one must not be smaller.
' The reading history of the consumer is listed in an MSFlexGrid.
Option Explicit

Private Sub Form_Load()
    FillConsumers cboConsumer
    dtpRead.Value = Date
    If cboConsumer.ListCount > 0 Then cboConsumer.ListIndex = 0
End Sub

Private Function SelectedMeter() As Long
    If cboConsumer.ListIndex >= 0 Then SelectedMeter = cboConsumer.ItemData(cboConsumer.ListIndex)
End Function

Private Sub cboConsumer_Click()
    Dim rs As ADODB.Recordset, r As Integer
    Set rs = cn.Execute("SELECT Category FROM Consumers WHERE MeterNo = " & SelectedMeter())
    If Not rs.EOF Then lblCategory.Caption = "Tariff: " & rs!Category
    rs.Close
    ' history, newest first; the newest current reading is the next previous reading
    grdHistory.Rows = 1
    lblPrev.Caption = "0"
    Set rs = cn.Execute("SELECT ReadDate, PrevReading, CurrReading FROM Readings WHERE MeterNo = " & _
                        SelectedMeter() & " ORDER BY ReadDate DESC")
    Do Until rs.EOF
        grdHistory.AddItem Format$(rs!ReadDate, "yyyy-mm-dd") & vbTab & rs!PrevReading & vbTab & _
                           rs!CurrReading & vbTab & (rs!CurrReading - rs!PrevReading)
        If grdHistory.Rows = 2 Then lblPrev.Caption = rs!CurrReading
        rs.MoveNext
    Loop
    rs.Close
End Sub

Private Sub txtCurrent_KeyPress(KeyAscii As Integer)
    If KeyAscii <> vbKeyBack And (KeyAscii < vbKey0 Or KeyAscii > vbKey9) Then
        KeyAscii = 0
        Beep
    End If
End Sub

Private Sub cmdSave_Click()
    Dim prev As Long, curr As Long
    If SelectedMeter() = 0 Then Exit Sub
    If Not IsNumeric(txtCurrent.Text) Then
        MsgBox "Type the reading shown on the meter.", vbExclamation
        Exit Sub
    End If
    prev = CLng(lblPrev.Caption)
    curr = CLng(txtCurrent.Text)
    If curr < prev Then
        MsgBox "The new reading (" & curr & ") is smaller than the previous one (" & prev & ").", vbExclamation
        Exit Sub
    End If
    cn.Execute "INSERT INTO Readings (MeterNo, ReadDate, PrevReading, CurrReading, Billed) VALUES (" & _
               SelectedMeter() & ", " & JetDate(dtpRead.Value) & ", " & prev & ", " & curr & ", False)"
    txtCurrent.Text = ""
    cboConsumer_Click
    frmMain.RefreshSummary
    MsgBox "Reading saved: " & (curr - prev) & " units used.", vbInformation
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub
