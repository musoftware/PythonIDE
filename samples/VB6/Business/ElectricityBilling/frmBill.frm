VERSION 5.00
Begin VB.Form frmBill
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "Generate bill"
   ClientHeight    =   4920
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   6600
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   4920
   ScaleWidth      =   6600
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdPaid
      Caption         =   "Mark &paid..."
      Height          =   375
      Left            =   120
      TabIndex        =   9
      Top             =   4440
      Width           =   1335
   End
   Begin VB.CommandButton cmdPrint
      Caption         =   "&Print bill"
      Enabled         =   0   'False
      Height          =   375
      Left            =   3960
      TabIndex        =   8
      Top             =   4440
      Width           =   1215
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "&Save bill"
      Enabled         =   0   'False
      Height          =   375
      Left            =   2640
      TabIndex        =   7
      Top             =   4440
      Width           =   1215
   End
   Begin VB.CommandButton cmdClose
      Cancel          =   -1  'True
      Caption         =   "Close"
      Height          =   375
      Left            =   5280
      TabIndex        =   10
      Top             =   4440
      Width           =   1215
   End
   Begin VB.Frame fraBill
      Caption         =   "Bill"
      Height          =   3495
      Left            =   120
      TabIndex        =   2
      Top             =   780
      Width           =   6375
      Begin VB.TextBox txtBreakdown
         BackColor       =   &H8000000F&
         BeginProperty Font
            Name            =   "Courier New"
            Size            =   9
            Charset         =   0
            Weight          =   400
            Underline       =   0   'False
            Italic          =   0   'False
            Strikethrough   =   0   'False
         EndProperty
         Height          =   1815
         Left            =   120
         Locked          =   -1  'True
         MultiLine       =   -1  'True
         ScrollBars      =   2  'Vertical
         TabIndex        =   4
         Top             =   960
         Width           =   6135
      End
      Begin VB.Label lblTotal
         Alignment       =   1  'Right Justify
         Caption         =   "0.00"
         BeginProperty Font
            Name            =   "MS Sans Serif"
            Size            =   12
            Charset         =   0
            Weight          =   700
            Underline       =   0   'False
            Italic          =   0   'False
            Strikethrough   =   0   'False
         EndProperty
         Height          =   375
         Left            =   3360
         TabIndex        =   6
         Top             =   2940
         Width           =   2895
      End
      Begin VB.Label lblTotalCaption
         Caption         =   "Total to pay:"
         Height          =   255
         Left            =   120
         TabIndex        =   5
         Top             =   3000
         Width           =   1935
      End
      Begin VB.Label lblInfo
         Caption         =   "-"
         Height          =   615
         Left            =   120
         TabIndex        =   3
         Top             =   300
         Width           =   6135
      End
   End
   Begin VB.ComboBox cboReading
      Height          =   315
      Left            =   1680
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   240
      Width           =   4815
   End
   Begin VB.Label lblReading
      Caption         =   "Unbilled reading:"
      Height          =   255
      Left            =   120
      TabIndex        =   0
      Top             =   300
      Width           =   1455
   End
End
Attribute VB_Name = "frmBill"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmBill - pick an unbilled reading, see the slab-by-slab calculation (modBilling.CalcBill returns
' a user-defined type), save the bill (the reading is marked billed) and print it through the
' DataEnvironment command cmdBill (a parameter: the bill number) and the DataReport rptBill.
Option Explicit

Private mCalc As BillCalc
Private mMeter As Long
Private mBillNo As Long

Private Sub Form_Load()
    LoadReadings
End Sub

Private Sub LoadReadings()
    Dim rs As ADODB.Recordset
    cboReading.Clear
    Set rs = cn.Execute("SELECT r.ReadingID, r.MeterNo, r.ReadDate, c.FullName FROM Readings r INNER JOIN Consumers c " & _
                        "ON r.MeterNo = c.MeterNo WHERE NOT r.Billed ORDER BY r.ReadDate")
    Do Until rs.EOF
        cboReading.AddItem Format$(rs!ReadDate, "yyyy-mm-dd") & "  meter " & rs!MeterNo & "  " & rs!FullName
        cboReading.ItemData(cboReading.NewIndex) = rs!ReadingID
        rs.MoveNext
    Loop
    rs.Close
    cmdSave.Enabled = False
    lblInfo.Caption = IIf(cboReading.ListCount = 0, "Every reading has been billed.", "-")
End Sub

Private Sub cboReading_Click()
    Dim rs As ADODB.Recordset
    If cboReading.ListIndex < 0 Then Exit Sub
    Set rs = cn.Execute("SELECT r.MeterNo, r.PrevReading, r.CurrReading, c.FullName, c.Category FROM Readings r " & _
                        "INNER JOIN Consumers c ON r.MeterNo = c.MeterNo WHERE r.ReadingID = " & _
                        cboReading.ItemData(cboReading.ListIndex))
    mMeter = rs!MeterNo
    mCalc = CalcBill(rs!Category, rs!PrevReading, rs!CurrReading)
    lblInfo.Caption = rs!FullName & " (" & rs!Category & ")" & vbCrLf & "Readings " & rs!PrevReading & _
                      " -> " & rs!CurrReading & " = " & mCalc.Units & " units"
    rs.Close
    txtBreakdown.Text = mCalc.Breakdown
    lblTotal.Caption = Format$(mCalc.Total, "#,##0.00")
    cmdSave.Enabled = True
    cmdPrint.Enabled = False
End Sub

Private Sub cmdSave_Click()
    Dim rs As ADODB.Recordset, readingId As Long, due As Date
    readingId = cboReading.ItemData(cboReading.ListIndex)
    due = DateAdd("d", Val(Setting("DueDays")), Date)
    cn.Execute "INSERT INTO Bills (MeterNo, ReadingID, BillDate, Units, Energy, FixedCharge, Tax, Total, DueDate, Paid) " & _
               "VALUES (" & mMeter & ", " & readingId & ", " & JetDate(Date) & ", " & mCalc.Units & ", " & _
               Str$(mCalc.Energy) & ", " & Str$(mCalc.FixedCharge) & ", " & Str$(mCalc.Tax) & ", " & _
               Str$(mCalc.Total) & ", " & JetDate(due) & ", False)"
    cn.Execute "UPDATE Readings SET Billed = True WHERE ReadingID = " & readingId
    Set rs = cn.Execute("SELECT MAX(BillNo) FROM Bills")
    mBillNo = rs(0)
    rs.Close
    MsgBox "Bill " & mBillNo & " saved, due on " & Format$(due, "d mmm yyyy") & ".", vbInformation
    LoadReadings
    cmdPrint.Enabled = True
    frmMain.RefreshSummary
End Sub

Private Sub cmdPrint_Click()
    deBilling.cmdBill mBillNo           ' run the parameterised command, then show its report
    rptBill.Caption = "Bill " & mBillNo
    rptBill.Show
End Sub

Private Sub cmdPaid_Click()
    Dim s As String, n As Long
    s = InputBox("Number of the bill that was paid:", "Payment")
    If Not IsNumeric(s) Then Exit Sub
    cn.Execute "UPDATE Bills SET Paid = True WHERE BillNo = " & CLng(s), n
    If n = 0 Then
        MsgBox "There is no bill " & s & ".", vbExclamation
    Else
        frmMain.RefreshSummary
    End If
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub
