VERSION 5.00
Begin VB.Form frmMember
   BorderStyle     =   3  'Fixed Dialog
   Caption         =   "New member"
   ClientHeight    =   2640
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   5160
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   2640
   ScaleWidth      =   5160
   ShowInTaskbar   =   0   'False
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdCancel
      Cancel          =   -1  'True
      Caption         =   "Cancel"
      Height          =   375
      Left            =   3840
      TabIndex        =   8
      Top             =   2100
      Width           =   1095
   End
   Begin VB.CommandButton cmdOK
      Caption         =   "OK"
      Default         =   -1  'True
      Height          =   375
      Left            =   2640
      TabIndex        =   7
      Top             =   2100
      Width           =   1095
   End
   Begin VB.Frame fraType
      Caption         =   "Account type"
      Height          =   1095
      Left            =   240
      TabIndex        =   2
      Top             =   720
      Width           =   2535
      Begin VB.OptionButton optCurrent
         Caption         =   "Current (C-)"
         Height          =   255
         Left            =   240
         TabIndex        =   4
         Top             =   660
         Width           =   2055
      End
      Begin VB.OptionButton optSaver
         Caption         =   "Saver (S-)"
         Height          =   255
         Left            =   240
         TabIndex        =   3
         Top             =   300
         Value           =   -1  'True
         Width           =   2055
      End
   End
   Begin VB.TextBox txtName
      Height          =   315
      Left            =   1440
      TabIndex        =   1
      Top             =   240
      Width           =   3495
   End
   Begin VB.Label lblPreview
      Caption         =   "-"
      Height          =   735
      Left            =   3000
      TabIndex        =   5
      Top             =   840
      Width           =   1935
   End
   Begin VB.Label lblName
      Caption         =   "Full name:"
      Height          =   255
      Left            =   240
      TabIndex        =   0
      Top             =   300
      Width           =   1095
   End
   Begin VB.Label lblFee
      Caption         =   "The entry fee is posted as income."
      ForeColor       =   &H00808080&
      Height          =   255
      Left            =   240
      TabIndex        =   6
      Top             =   1980
      Width           =   2295
   End
End
Attribute VB_Name = "frmMember"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmMember - modal dialog: the account type decides the id prefix (S- / C-) and the entry fee.
Option Explicit

Private Function Prefix() As String
    Prefix = IIf(optSaver.Value, "S-", "C-")
End Function

Private Function EntryFee() As Currency
    EntryFee = IIf(optSaver.Value, 50, 120)
End Function

' Next id of the chosen type: S-0003 when S-0001 and S-0002 exist
Private Function NextId() As String
    Dim n As Long
    n = ScalarValue("SELECT COUNT(*) FROM Members WHERE MemberID LIKE '" & Prefix() & "%'")
    NextId = Prefix() & Format$(n + 1, "0000")
End Function

Private Sub ShowPreview()
    lblPreview.Caption = "Member id: " & NextId() & vbCrLf & "Entry fee: " & Format$(EntryFee(), "0.00")
End Sub

Private Sub Form_Load()
    ShowPreview
End Sub

Private Sub optSaver_Click()
    ShowPreview
End Sub

Private Sub optCurrent_Click()
    ShowPreview
End Sub

Private Sub cmdOK_Click()
    Dim id As String
    If Len(Trim$(txtName.Text)) = 0 Then
        MsgBox "Type the member's name.", vbExclamation
        Exit Sub
    End If
    id = NextId()
    cn.Execute "INSERT INTO Members VALUES (" & SqlText(id) & ", " & SqlText(Trim$(txtName.Text)) & ", " & _
               SqlText(IIf(optSaver.Value, "Saver", "Current")) & ", " & SqlDate(Date) & ", " & EntryFee() & ", True)"
    PostEntry Date, id, CAT_INCOME, "CR", EntryFee(), "Cash", "Entry fee " & id
    frmLedger.LoadMembers
    Unload Me
End Sub

Private Sub cmdCancel_Click()
    Unload Me
End Sub
