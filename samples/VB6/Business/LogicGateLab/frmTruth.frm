VERSION 5.00
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Begin VB.Form frmTruth 
   BorderStyle     =   4  'Fixed ToolWindow
   Caption         =   "Truth table"
   ClientHeight    =   3600
   ClientLeft      =   45
   ClientTop       =   315
   ClientWidth     =   3840
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   MinButton       =   0   'False
   ScaleHeight     =   3600
   ScaleWidth      =   3840
   ShowInTaskbar   =   0   'False
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton cmdClose 
      Caption         =   "Close"
      Height          =   375
      Left            =   2520
      TabIndex        =   3
      Top             =   3120
      Width           =   1215
   End
   Begin VB.CommandButton cmdExport 
      Caption         =   "&Export all"
      Height          =   375
      Left            =   120
      TabIndex        =   2
      Top             =   3120
      Width           =   1215
   End
   Begin MSFlexGridLib.MSFlexGrid grdTruth 
      Height          =   2055
      Left            =   120
      TabIndex        =   1
      Top             =   600
      Width           =   3615
      _ExtentX        =   6376
      _ExtentY        =   3625
      _Version        =   393216
      Rows            =   5
      Cols            =   3
      FixedCols       =   0
      FormatString    =   "^A    |^B    |^Out    "
   End
   Begin VB.Label lblExpr 
      Alignment       =   2  'Center
      Caption         =   "-"
      BeginProperty Font 
         Name            =   "Courier New"
         Size            =   9.75
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   3615
   End
   Begin VB.Label lblOnes 
      Caption         =   "-"
      Height          =   255
      Left            =   120
      TabIndex        =   4
      Top             =   2760
      Width           =   3615
   End
End
Attribute VB_Name = "frmTruth"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' frmTruth - a modeless tool window with the truth table of one gate (MSFlexGrid) and an export of
' the tables of all seven gates to a text file.
Option Explicit

Public Sub ShowGate(ByVal Kind As GateKind)
    Dim g As New clsGate, r As Integer, ones As Integer
    g.Kind = Kind
    FillTruthTable grdTruth, g
    lblExpr.Caption = "Out = " & g.Expression("A", "B")
    For r = 1 To grdTruth.Rows - 1
        If grdTruth.TextMatrix(r, 2) = "1" Then ones = ones + 1
    Next
    lblOnes.Caption = "Output is 1 in " & ones & " of " & (grdTruth.Rows - 1) & " rows"
    Me.Caption = "Truth table - " & g.Name
End Sub

' All the tables into truth_tables.txt next to the program
Public Function ExportAll() As String
    Dim f As Integer, k As Integer, r As Integer, g As clsGate, path As String
    path = App.Path & "\truth_tables.txt"
    f = FreeFile
    Open path For Output As #f
    For k = gkAnd To gkXnor
        Set g = New clsGate
        g.Kind = k
        FillTruthTable grdTruth, g
        Print #f, g.Name; Tab(8); "Out = "; g.Expression("A", "B")
        For r = 1 To grdTruth.Rows - 1
            Print #f, "  "; grdTruth.TextMatrix(r, 0); " "; grdTruth.TextMatrix(r, 1); " -> "; grdTruth.TextMatrix(r, 2)
        Next
        Print #f,
    Next
    Close #f
    ShowGate frmLab.CurrentKind
    ExportAll = path
End Function

Private Sub cmdExport_Click()
    MsgBox "Saved " & ExportAll(), vbInformation
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub
