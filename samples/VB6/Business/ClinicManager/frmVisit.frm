VERSION 5.00
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Object = "{C932BA88-4374-101B-A56C-00AA003668DC}#1.1#0"; "MSMASK32.OCX"
Begin VB.Form frmVisit
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "New visit"
   ClientHeight    =   4440
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   6000
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   4440
   ScaleWidth      =   6000
   ShowInTaskbar   =   0   'False
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdCancel
      Cancel          =   -1  'True
      Caption         =   "Cancel"
      Height          =   375
      Left            =   4680
      TabIndex        =   17
      Top             =   3900
      Width           =   1095
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "&Save"
      Default         =   -1  'True
      Height          =   375
      Left            =   3480
      TabIndex        =   16
      Top             =   3900
      Width           =   1095
   End
   Begin VB.ComboBox cboMedicine
      Height          =   315
      Left            =   1440
      TabIndex        =   15
      Top             =   3360
      Width           =   4335
   End
   Begin VB.TextBox txtDiagnosis
      Height          =   735
      Left            =   1440
      MultiLine       =   -1  'True
      ScrollBars      =   2  'Vertical
      TabIndex        =   13
      Top             =   2460
      Width           =   4335
   End
   Begin VB.TextBox txtTemp
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   4440
      TabIndex        =   11
      Top             =   1920
      Width           =   1335
   End
   Begin VB.TextBox txtPulse
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   1440
      TabIndex        =   9
      Top             =   1920
      Width           =   1335
   End
   Begin VB.TextBox txtWeight
      Alignment       =   1  'Right Justify
      Height          =   315
      Left            =   1440
      TabIndex        =   5
      Top             =   1380
      Width           =   1335
   End
   Begin MSMask.MaskEdBox mskBP
      Height          =   315
      Left            =   4440
      TabIndex        =   7
      Top             =   1380
      Width           =   1335
      _ExtentX        =   2355
      _ExtentY        =   556
      _Version        =   393216
      MaxLength       =   7
      Mask            =   "###/###"
      PromptChar      =   "_"
   End
   Begin MSComCtl2.DTPicker dtpVisit
      Height          =   315
      Left            =   1440
      TabIndex        =   3
      Top             =   840
      Width           =   1815
      _ExtentX        =   3201
      _ExtentY        =   556
      _Version        =   393216
      Format          =   20512769
      CurrentDate     =   46023
   End
   Begin VB.Label lblMedicine
      Caption         =   "Medicine:"
      Height          =   255
      Left            =   240
      TabIndex        =   14
      Top             =   3420
      Width           =   1095
   End
   Begin VB.Label lblDiagnosis
      Caption         =   "Diagnosis:"
      Height          =   255
      Left            =   240
      TabIndex        =   12
      Top             =   2520
      Width           =   1095
   End
   Begin VB.Label lblTemp
      Caption         =   "Temp (C):"
      Height          =   255
      Left            =   3240
      TabIndex        =   10
      Top             =   1980
      Width           =   1095
   End
   Begin VB.Label lblPulse
      Caption         =   "Pulse:"
      Height          =   255
      Left            =   240
      TabIndex        =   8
      Top             =   1980
      Width           =   1095
   End
   Begin VB.Label lblBP
      Caption         =   "BP:"
      Height          =   255
      Left            =   3240
      TabIndex        =   6
      Top             =   1440
      Width           =   1095
   End
   Begin VB.Label lblWeight
      Caption         =   "Weight (kg):"
      Height          =   255
      Left            =   240
      TabIndex        =   4
      Top             =   1440
      Width           =   1095
   End
   Begin VB.Label lblDate
      Caption         =   "Date:"
      Height          =   255
      Left            =   240
      TabIndex        =   2
      Top             =   900
      Width           =   1095
   End
   Begin VB.Label lblPatient
      Caption         =   "-"
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
      Left            =   240
      TabIndex        =   0
      Top             =   300
      Width           =   5535
   End
   Begin VB.Label lblWarn
      Caption         =   ""
      ForeColor       =   &H000000C0&
      Height          =   255
      Left            =   240
      TabIndex        =   1
      Top             =   3960
      Width           =   3135
   End
End
Attribute VB_Name = "frmVisit"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmVisit - modal dialog for one visit. frmMain calls the Public Sub StartFor before Show vbModal.
' The values are checked (IsNumeric, ranges, the MaskEdBox blood pressure) and written with DAO
' AddNew / Update. A fever (> 38 C) is pointed out while typing (Change event).
Option Explicit

Private mPatientNo As Long

Public Sub StartFor(ByVal PatientNo As Long, ByVal PatientName As String)
    Dim rs As DAO.Recordset
    mPatientNo = PatientNo
    lblPatient.Caption = "Patient " & PatientNo & ": " & PatientName
    dtpVisit.Value = Date
    txtWeight.Text = "": txtPulse.Text = "": txtTemp.Text = "": txtDiagnosis.Text = ""
    mskBP.Text = ""
    cboMedicine.Clear
    Set rs = gDb.OpenRecordset("SELECT MedName FROM Medicines ORDER BY MedName", dbOpenSnapshot)
    Do Until rs.EOF
        cboMedicine.AddItem rs!MedName
        rs.MoveNext
    Loop
    rs.Close
    cboMedicine.ListIndex = 0
End Sub

Private Sub txtTemp_Change()
    If IsNumeric(txtTemp.Text) Then
        If CDbl(txtTemp.Text) > 38 Then lblWarn.Caption = "Fever!" Else lblWarn.Caption = ""
    End If
End Sub

Private Function Problem() As String
    If Not IsNumeric(txtWeight.Text) Then
        Problem = "Weight must be a number."
    ElseIf CDbl(txtWeight.Text) <= 0 Or CDbl(txtWeight.Text) > 400 Then
        Problem = "Weight must be between 0 and 400 kg."
    ElseIf Not mskBP.Text Like "###/###" And Not mskBP.Text Like "##/##" And Not mskBP.Text Like "###/##" Then
        Problem = "Blood pressure looks like 120/80."
    ElseIf Not IsNumeric(txtPulse.Text) Then
        Problem = "Pulse must be a number."
    ElseIf Not IsNumeric(txtTemp.Text) Then
        Problem = "Temperature must be a number."
    ElseIf CDbl(txtTemp.Text) < 30 Or CDbl(txtTemp.Text) > 45 Then
        Problem = "Temperature must be between 30 and 45 C."
    End If
End Function

Private Sub cmdSave_Click()
    Dim rs As DAO.Recordset, msg As String
    msg = Problem()
    If msg <> "" Then
        MsgBox msg, vbExclamation
        Exit Sub
    End If
    Set rs = gDb.OpenRecordset("Visits", dbOpenDynaset)
    rs.AddNew
    rs!PatientNo = mPatientNo
    rs!VisitDate = dtpVisit.Value
    rs!WeightKg = CDbl(txtWeight.Text)
    rs!BloodPressure = mskBP.Text
    rs!Pulse = CInt(txtPulse.Text)
    rs!TempC = CDbl(txtTemp.Text)
    rs!Diagnosis = txtDiagnosis.Text
    rs!Medicine = cboMedicine.Text
    rs.Update
    rs.Close
    frmMain.LoadVisits
    Unload Me
End Sub

Private Sub cmdCancel_Click()
    Unload Me
End Sub
