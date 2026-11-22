VERSION 5.00
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Begin VB.Form frmAlerts 
   Caption         =   "Low stock and expiry"
   ClientHeight    =   4200
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   7680
   LinkTopic       =   "Form1"
   MDIChild        =   -1  'True
   ScaleHeight     =   4200
   ScaleWidth      =   7680
   Begin VB.CommandButton cmdSell 
      Caption         =   "&Sell selected..."
      Height          =   375
      Left            =   4680
      TabIndex        =   3
      Top             =   3720
      Width           =   1455
   End
   Begin VB.CommandButton cmdExport 
      Caption         =   "&Export CSV"
      Height          =   375
      Left            =   6240
      TabIndex        =   4
      Top             =   3720
      Width           =   1215
   End
   Begin VB.TextBox txtDays 
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   3240
      TabIndex        =   1
      Text            =   "60"
      Top             =   120
      Width           =   615
   End
   Begin MSFlexGridLib.MSFlexGrid grdAlerts 
      Height          =   3135
      Left            =   240
      TabIndex        =   2
      Top             =   480
      Width           =   7215
      _ExtentX        =   12726
      _ExtentY        =   5530
      _Version        =   393216
      Rows            =   1
      Cols            =   5
      FixedCols       =   0
      SelectionMode   =   1
      FormatString    =   "<Code |<Medicine                      |>Stock|>Reorder|<Problem              "
   End
   Begin VB.Label lblDays 
      Caption         =   "Warn about medicines expiring within (days):"
      Height          =   255
      Left            =   240
      TabIndex        =   0
      Top             =   180
      Width           =   3015
   End
   Begin VB.Label lblCount 
      Caption         =   "-"
      Height          =   255
      Left            =   240
      TabIndex        =   5
      Top             =   3780
      Width           =   4335
   End
End
Attribute VB_Name = "frmAlerts"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmAlerts - medicines at or below their reorder level, expired or expiring soon (DateDiff).
' "Sell selected" hands the medicine to frmSale through public module variables; Export writes a CSV.
Option Explicit

Private Sub Form_Load()
    LoadAlerts
End Sub

Private Sub txtDays_Change()
    If IsNumeric(txtDays.Text) Then LoadAlerts
End Sub

Public Sub LoadAlerts()
    Dim rs As ADODB.Recordset, problem As String, days As Long
    grdAlerts.Rows = 1
    Set rs = cn.Execute("SELECT Code, MedName, Stock, ReorderLevel, Expiry FROM Medicines ORDER BY Code")
    Do Until rs.EOF
        problem = ""
        days = DateDiff("d", Date, rs!Expiry)
        If days < 0 Then
            problem = "expired"
        ElseIf days <= Val(txtDays.Text) Then
            problem = "expires in " & days & " d"
        End If
        If rs!Stock <= rs!ReorderLevel Then problem = IIf(problem = "", "", problem & ", ") & "reorder"
        If problem <> "" Then
            grdAlerts.AddItem rs!Code & vbTab & rs!MedName & vbTab & rs!Stock & vbTab & rs!ReorderLevel & vbTab & problem
        End If
        rs.MoveNext
    Loop
    rs.Close
    lblCount.Caption = (grdAlerts.Rows - 1) & " medicines need attention"
End Sub

Private Sub cmdSell_Click()
    If grdAlerts.Row < 1 Then Exit Sub
    gPickedCode = grdAlerts.TextMatrix(grdAlerts.Row, 0)
    gPickedName = grdAlerts.TextMatrix(grdAlerts.Row, 1)
    frmSale.Show
    frmSale.UsePicked
End Sub

Public Function ExportCsv() As String
    Dim f As Integer, r As Integer, c As Integer, line As String
    ExportCsv = App.Path & "\alerts.csv"
    f = FreeFile
    Open ExportCsv For Output As #f
    For r = 0 To grdAlerts.Rows - 1
        line = ""
        For c = 0 To grdAlerts.Cols - 1
            line = line & IIf(c > 0, ",", "") & """" & Trim$(grdAlerts.TextMatrix(r, c)) & """"
        Next
        Print #f, line
    Next
    Close #f
End Function

Private Sub cmdExport_Click()
    MsgBox "Saved " & ExportCsv(), vbInformation
End Sub
