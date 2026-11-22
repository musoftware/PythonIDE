VERSION 5.00
Object = "{BDC217C8-ED16-11CD-956C-0000C04E4C0A}#1.1#0"; "TABCTL32.OCX"
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Begin VB.Form frmMain
   Caption         =   "ClinicManager"
   ClientHeight    =   5880
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   8760
   LinkTopic       =   "Form1"
   ScaleHeight     =   5880
   ScaleWidth      =   8760
   StartUpPosition =   2  'CenterScreen
   Begin TabDlg.SSTab tabClinic
      Height          =   5295
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   8535
      _ExtentX        =   15055
      _ExtentY        =   9340
      _Version        =   393216
      Tabs            =   3
      TabHeight       =   520
      TabCaption(0)   =   "Patients"
      TabPicture(0)   =   ""
      Tab(0).ControlEnabled=   -1  'True
      Tab(0).Control(0)=   "datPatients"
      Tab(0).Control(1)=   "fraPatient"
      Tab(0).Control(2)=   "cmdAdd"
      Tab(0).Control(3)=   "cmdSave"
      Tab(0).Control(4)=   "cmdRemove"
      Tab(0).Control(5)=   "cmdFind"
      Tab(0).Control(6)=   "lblPosition"
      Tab(0).ControlCount=   7
      TabCaption(1)   =   "Visits"
      TabPicture(1)   =   ""
      Tab(1).ControlEnabled=   0   'False
      Tab(1).Control(0)=   "lblVisitsOf"
      Tab(1).Control(1)=   "grdVisits"
      Tab(1).Control(2)=   "cmdNewVisit"
      Tab(1).ControlCount=   3
      TabCaption(2)   =   "Statistics"
      TabPicture(2)   =   ""
      Tab(2).ControlEnabled=   0   'False
      Tab(2).Control(0)=   "shpBar(0)"
      Tab(2).Control(1)=   "shpBar(1)"
      Tab(2).Control(2)=   "lblBar(0)"
      Tab(2).Control(3)=   "lblBar(1)"
      Tab(2).Control(4)=   "lblStats"
      Tab(2).Control(5)=   "linAxis"
      Tab(2).ControlCount=   6
      Begin VB.Data datPatients
         Caption         =   "Patients"
         Connect         =   "Access"
         DatabaseName    =   ""
         DefaultCursorType=   0  'DefaultCursor
         DefaultType     =   2  'UseODBC
         Exclusive       =   0   'False
         Height          =   345
         Left            =   240
         Options         =   0
         ReadOnly        =   0   'False
         RecordsetType   =   1  'Dynaset
         RecordSource    =   "SELECT * FROM Patients ORDER BY PatientNo"
         Top             =   4200
         Width           =   4095
      End
      Begin VB.Frame fraPatient
         Caption         =   "Patient"
         Height          =   3615
         Left            =   240
         TabIndex        =   1
         Top             =   480
         Width           =   8055
         Begin VB.TextBox txtAddress
            DataField       =   "Address"
            DataSource      =   "datPatients"
            Height          =   315
            Left            =   1560
            TabIndex        =   15
            Top             =   3120
            Width           =   6255
         End
         Begin VB.ComboBox cboBlood
            DataField       =   "BloodGroup"
            DataSource      =   "datPatients"
            Height          =   315
            Left            =   5760
            TabIndex        =   13
            Top             =   2520
            Width           =   2055
         End
         Begin VB.TextBox txtPhone
            DataField       =   "Phone"
            DataSource      =   "datPatients"
            Height          =   315
            Left            =   1560
            TabIndex        =   11
            Top             =   2520
            Width           =   2295
         End
         Begin VB.TextBox txtBirth
            DataField       =   "BirthDate"
            DataSource      =   "datPatients"
            Height          =   315
            Left            =   5760
            TabIndex        =   9
            Top             =   1920
            Width           =   2055
         End
         Begin VB.ComboBox cboGender
            DataField       =   "Gender"
            DataSource      =   "datPatients"
            Height          =   315
            Left            =   1560
            Style           =   2  'Dropdown List
            TabIndex        =   7
            Top             =   1920
            Width           =   1095
         End
         Begin VB.TextBox txtName
            DataField       =   "FullName"
            DataSource      =   "datPatients"
            Height          =   315
            Left            =   1560
            TabIndex        =   5
            Top             =   1320
            Width           =   6255
         End
         Begin VB.TextBox txtNo
            BackColor       =   &H8000000F&
            DataField       =   "PatientNo"
            DataSource      =   "datPatients"
            Height          =   315
            Left            =   1560
            Locked          =   -1  'True
            TabIndex        =   3
            Top             =   720
            Width           =   1095
         End
         Begin VB.Label lblAge
            Caption         =   "-"
            Height          =   255
            Left            =   2880
            TabIndex        =   16
            Top             =   1980
            Width           =   1575
         End
         Begin VB.Label lblAddress
            Caption         =   "Address:"
            Height          =   255
            Left            =   240
            TabIndex        =   14
            Top             =   3180
            Width           =   1215
         End
         Begin VB.Label lblBlood
            Caption         =   "Blood group:"
            Height          =   255
            Left            =   4560
            TabIndex        =   12
            Top             =   2580
            Width           =   1095
         End
         Begin VB.Label lblPhone
            Caption         =   "Phone:"
            Height          =   255
            Left            =   240
            TabIndex        =   10
            Top             =   2580
            Width           =   1215
         End
         Begin VB.Label lblBirth
            Caption         =   "Born (y-m-d):"
            Height          =   255
            Left            =   4560
            TabIndex        =   8
            Top             =   1980
            Width           =   1095
         End
         Begin VB.Label lblGender
            Caption         =   "Gender:"
            Height          =   255
            Left            =   240
            TabIndex        =   6
            Top             =   1980
            Width           =   1215
         End
         Begin VB.Label lblName
            Caption         =   "Full name:"
            Height          =   255
            Left            =   240
            TabIndex        =   4
            Top             =   1380
            Width           =   1215
         End
         Begin VB.Label lblNo
            Caption         =   "Patient no:"
            Height          =   255
            Left            =   240
            TabIndex        =   2
            Top             =   780
            Width           =   1215
         End
         Begin VB.Label lblStaff
            Alignment       =   1  'Right Justify
            Caption         =   "-"
            ForeColor       =   &H00808080&
            Height          =   255
            Left            =   4560
            TabIndex        =   17
            Top             =   300
            Width           =   3255
         End
      End
      Begin VB.CommandButton cmdAdd
         Caption         =   "&Add"
         Height          =   375
         Left            =   240
         TabIndex        =   18
         Top             =   4680
         Width           =   1215
      End
      Begin VB.CommandButton cmdSave
         Caption         =   "&Save"
         Height          =   375
         Left            =   1560
         TabIndex        =   19
         Top             =   4680
         Width           =   1215
      End
      Begin VB.CommandButton cmdRemove
         Caption         =   "&Remove..."
         Height          =   375
         Left            =   2880
         TabIndex        =   20
         Top             =   4680
         Width           =   1215
      End
      Begin VB.CommandButton cmdFind
         Caption         =   "&Find..."
         Height          =   375
         Left            =   4200
         TabIndex        =   21
         Top             =   4680
         Width           =   1215
      End
      Begin VB.Label lblPosition
         Alignment       =   1  'Right Justify
         Caption         =   "-"
         Height          =   255
         Left            =   4560
         TabIndex        =   22
         Top             =   4260
         Width           =   3735
      End
      Begin VB.Label lblVisitsOf
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
         Left            =   -74760
         TabIndex        =   23
         Top             =   540
         Width           =   8055
      End
      Begin MSFlexGridLib.MSFlexGrid grdVisits
         Height          =   3615
         Left            =   -74760
         TabIndex        =   24
         Top             =   900
         Width           =   8055
         _ExtentX        =   14208
         _ExtentY        =   6376
         _Version        =   393216
         Rows            =   1
         Cols            =   7
         FixedCols       =   0
         FormatString    =   "<Date      |>Weight|^BP     |>Pulse|>Temp|<Diagnosis              |<Medicine"
      End
      Begin VB.CommandButton cmdNewVisit
         Caption         =   "&New visit..."
         Height          =   375
         Left            =   -74760
         TabIndex        =   25
         Top             =   4680
         Width           =   1575
      End
      Begin VB.Line linAxis
         BorderWidth     =   2
         X1              =   -74280
         X2              =   -70080
         Y1              =   4200
         Y2              =   4200
      End
      Begin VB.Shape shpBar
         BackColor       =   &H00FF8080&
         BackStyle       =   1  'Opaque
         Height          =   1000
         Index           =   1
         Left            =   -72360
         Top             =   3200
         Width           =   900
      End
      Begin VB.Shape shpBar
         BackColor       =   &H008080FF&
         BackStyle       =   1  'Opaque
         Height          =   1000
         Index           =   0
         Left            =   -73800
         Top             =   3200
         Width           =   900
      End
      Begin VB.Label lblBar
         Alignment       =   2  'Center
         Caption         =   "M"
         Height          =   255
         Index           =   1
         Left            =   -72480
         TabIndex        =   27
         Top             =   4320
         Width           =   1140
      End
      Begin VB.Label lblBar
         Alignment       =   2  'Center
         Caption         =   "F"
         Height          =   255
         Index           =   0
         Left            =   -73920
         TabIndex        =   26
         Top             =   4320
         Width           =   1140
      End
      Begin VB.Label lblStats
         Caption         =   "-"
         Height          =   1335
         Left            =   -69840
         TabIndex        =   28
         Top             =   900
         Width           =   3135
      End
   End
   Begin VB.Label lblStatus
      Caption         =   "-"
      Height          =   255
      Left            =   120
      TabIndex        =   29
      Top             =   5520
      Width           =   8535
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmMain - ClinicManager:
'   Patients    the intrinsic Data control datPatients (DAO) with bound TextBoxes / ComboBoxes
'               (DataSource + DataField); Reposition shows "record n of m" and the age.
'   Visits      the visits of the current patient, read with a DAO recordset into an MSFlexGrid.
'   Statistics  a small bar chart drawn with Shape controls (a control array) and a Line axis.
Option Explicit

Private Sub Form_Load()
    cboGender.AddItem "F"
    cboGender.AddItem "M"
    cboBlood.AddItem "A+": cboBlood.AddItem "A-": cboBlood.AddItem "B+": cboBlood.AddItem "B-"
    cboBlood.AddItem "AB+": cboBlood.AddItem "AB-": cboBlood.AddItem "O+": cboBlood.AddItem "O-"
    lblStaff.Caption = "Signed in: " & gStaff
    ' the Data control opens its RecordSource after Form_Load
    datPatients.DatabaseName = DbPath()
End Sub

' The current record changed (arrows of the Data control, Find, MoveNext in code ...)
Private Sub datPatients_Reposition()
    Dim rs As DAO.Recordset
    Set rs = datPatients.Recordset
    If rs.EOF Or rs.BOF Then
        lblPosition.Caption = "no patient"
        lblAge.Caption = ""
        Exit Sub
    End If
    lblPosition.Caption = "Patient " & (rs.AbsolutePosition + 1) & " of " & rs.RecordCount
    If IsDate(txtBirth.Text) Then lblAge.Caption = AgeOn(CDate(txtBirth.Text), Date) & " years"
    lblStatus.Caption = "Current: " & rs!FullName
End Sub

Private Sub cmdAdd_Click()
    Dim n As Long
    n = NextPatientNo()
    datPatients.Recordset.AddNew              ' the bound controls are cleared
    txtNo.Text = n
    cboGender.ListIndex = 0
    txtName.SetFocus
    lblPosition.Caption = "new patient " & n
End Sub

Private Sub cmdSave_Click()
    If Trim$(txtName.Text) = "" Then
        MsgBox "The patient's name is required.", vbExclamation
        Exit Sub
    End If
    If txtBirth.Text <> "" And Not IsDate(txtBirth.Text) Then
        MsgBox "The birth date is not a date (use yyyy-mm-dd).", vbExclamation
        Exit Sub
    End If
    With datPatients.Recordset
        If .EditMode = dbEditNone Then .Edit
        .Update                             ' the Data control copies the bound controls first
        .Bookmark = .LastModified
    End With
    lblStatus.Caption = "Saved " & txtName.Text
End Sub

' Remove a patient and every visit of that patient (asked with an InputBox)
Private Sub cmdRemove_Click()
    Dim s As String, rs As DAO.Recordset, n As Integer
    s = InputBox("Number of the patient to remove:", "Remove patient", txtNo.Text)
    If Not IsNumeric(s) Then Exit Sub
    If MsgBox("Remove patient " & s & " and all the visits?", vbYesNo + vbQuestion) <> vbYes Then Exit Sub
    Set rs = gDb.OpenRecordset("SELECT * FROM Visits WHERE PatientNo = " & CLng(s), dbOpenDynaset)
    Do While Not rs.EOF
        rs.Delete
        n = n + 1
        rs.MoveNext
    Loop
    rs.Close
    gDb.Execute "DELETE FROM Patients WHERE PatientNo = " & CLng(s)
    datPatients.Refresh
    lblStatus.Caption = "Removed patient " & s & " (" & n & " visits)"
End Sub

Private Sub cmdFind_Click()
    Dim s As String
    s = InputBox("Part of the name:", "Find patient")
    If s = "" Then Exit Sub
    datPatients.Recordset.FindFirst "FullName LIKE '*" & Replace(s, "'", "''") & "*'"
    If datPatients.Recordset.NoMatch Then
        MsgBox "No patient called """ & s & """.", vbInformation
        datPatients.Recordset.MoveFirst
    End If
End Sub

' ------------------------------------------------------------------------------------------ visits
Public Sub LoadVisits()
    Dim rs As DAO.Recordset
    grdVisits.Rows = 1
    If txtNo.Text = "" Then Exit Sub
    lblVisitsOf.Caption = "Visits of " & txtName.Text & " (patient " & txtNo.Text & ")"
    Set rs = gDb.OpenRecordset("SELECT * FROM Visits WHERE PatientNo = " & Val(txtNo.Text) & " ORDER BY VisitDate", _
                               dbOpenSnapshot)
    Do Until rs.EOF
        grdVisits.AddItem Format$(rs!VisitDate, "yyyy-mm-dd") & vbTab & Format$(rs!WeightKg, "0.0") & vbTab & _
                          rs!BloodPressure & vbTab & rs!Pulse & vbTab & Format$(rs!TempC, "0.0") & vbTab & _
                          rs!Diagnosis & vbTab & rs!Medicine
        rs.MoveNext
    Loop
    rs.Close
End Sub

Private Sub cmdNewVisit_Click()
    If txtNo.Text = "" Then Exit Sub
    frmVisit.StartFor Val(txtNo.Text), txtName.Text     ' a Public Sub of the dialog
    frmVisit.Show vbModal, Me
End Sub

' ------------------------------------------------------------------------------------------ statistics
Public Sub ShowStatistics()
    Dim rs As DAO.Recordset, f As Long, m As Long, top As Long, i As Integer, counts(1) As Long
    Set rs = gDb.OpenRecordset("SELECT Gender, COUNT(*) AS N FROM Patients GROUP BY Gender", dbOpenSnapshot)
    Do Until rs.EOF
        If rs!Gender = "F" Then f = rs!N Else m = rs!N
        rs.MoveNext
    Loop
    rs.Close
    counts(0) = f: counts(1) = m
    top = IIf(f > m, f, m)
    For i = 0 To 1
        ' bars stand on the axis (Y = 4200 inside the tab); the tallest is 2400 twips
        If top > 0 Then shpBar(i).Height = 2400 * counts(i) \ top + 15 Else shpBar(i).Height = 15
        shpBar(i).Top = 4200 - shpBar(i).Height
        lblBar(i).Caption = IIf(i = 0, "F: ", "M: ") & counts(i)
    Next
    lblStats.Caption = "Patients: " & (f + m) & vbCrLf & _
                       "Visits: " & gDb.OpenRecordset("SELECT COUNT(*) FROM Visits").Fields(0).Value & vbCrLf & _
                       "Average age: " & Format$(AverageAge(), "0.0")
End Sub

Private Function AverageAge() As Double
    Dim rs As DAO.Recordset, total As Double, n As Long
    Set rs = gDb.OpenRecordset("SELECT BirthDate FROM Patients WHERE BirthDate IS NOT NULL", dbOpenSnapshot)
    Do Until rs.EOF
        total = total + AgeOn(rs!BirthDate, Date)
        n = n + 1
        rs.MoveNext
    Loop
    rs.Close
    If n > 0 Then AverageAge = total / n
End Function

Private Sub tabClinic_Click(PreviousTab As Integer)
    Select Case tabClinic.Tab
        Case 1: LoadVisits
        Case 2: ShowStatistics
    End Select
End Sub

Private Sub Form_Unload(Cancel As Integer)
    gDb.Close
End Sub
