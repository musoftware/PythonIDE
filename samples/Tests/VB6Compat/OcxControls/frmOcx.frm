VERSION 5.00
Object = "{BDC217C8-ED16-11CD-956C-0000C04E4C0A}#1.1#0"; "TABCTL32.OCX"
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Object = "{86CF1D34-0C5F-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCT2.OCX"
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFLXGRD.OCX"
Object = "{C932BA88-4374-101B-A56C-00AA003668DC}#1.1#0"; "MSMASK32.OCX"
Begin VB.Form frmOcx 
   Caption         =   "ActiveX controls"
   ClientHeight    =   5400
   ClientLeft      =   60
   ClientTop       =   450
   ClientWidth     =   8400
   LinkTopic       =   "Form1"
   ScaleHeight     =   5400
   ScaleWidth      =   8400
   StartUpPosition =   3  'Windows Default
   Begin TabDlg.SSTab SSTab1 
      Height          =   4575
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   8175
      _ExtentX        =   14420
      _ExtentY        =   8070
      _Version        =   393216
      Tabs            =   3
      TabHeight       =   520
      TabCaption(0)   =   "Lists"
      TabPicture(0)   =   ""
      Tab(0).ControlEnabled=   -1  'True
      Tab(0).Control(0)=   "ListView1"
      Tab(0).Control(1)=   "TreeView1"
      Tab(0).ControlCount=   2
      TabCaption(1)   =   "Grid"
      TabPicture(1)   =   ""
      Tab(1).ControlEnabled=   0   'False
      Tab(1).Control(0)=   "MSFlexGrid1"
      Tab(1).ControlCount=   1
      TabCaption(2)   =   "Dates"
      TabPicture(2)   =   ""
      Tab(2).ControlEnabled=   0   'False
      Tab(2).Control(0)=   "DTPicker1"
      Tab(2).Control(1)=   "MonthView1"
      Tab(2).Control(2)=   "MaskEdBox1"
      Tab(2).ControlCount=   3
      Begin MSComctlLib.ListView ListView1 
         Height          =   3615
         Left            =   120
         TabIndex        =   1
         Top             =   480
         Width           =   4935
         _ExtentX        =   8705
         _ExtentY        =   6376
         View            =   3
         LabelWrap       =   -1  'True
         HideSelection   =   -1  'True
         _Version        =   393217
         ForeColor       =   -2147483640
         BackColor       =   -2147483643
         BorderStyle     =   1
         Appearance      =   1
         NumItems        =   2
         BeginProperty ColumnHeader(1) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
            Text            =   "Product"
            Object.Width           =   2540
         EndProperty
         BeginProperty ColumnHeader(2) {BDD1F052-858B-11D1-B16A-00C0F0283628} 
            SubItemIndex    =   1
            Text            =   "Price"
            Object.Width           =   2540
         EndProperty
      End
      Begin MSComctlLib.TreeView TreeView1 
         Height          =   3615
         Left            =   5160
         TabIndex        =   2
         Top             =   480
         Width           =   2775
         _ExtentX        =   4895
         _ExtentY        =   6376
         _Version        =   393217
         Style           =   7
         Appearance      =   1
      End
      Begin MSFlexGridLib.MSFlexGrid MSFlexGrid1 
         Height          =   3615
         Left            =   -74880
         TabIndex        =   3
         Top             =   480
         Width           =   7815
         _ExtentX        =   13785
         _ExtentY        =   6376
         _Version        =   393216
         Rows            =   4
         Cols            =   3
         FormatString    =   "<Code|<Description|>Qty"
      End
      Begin MSComCtl2.DTPicker DTPicker1 
         Height          =   315
         Left            =   -74880
         TabIndex        =   4
         Top             =   480
         Width           =   1935
         _ExtentX        =   3413
         _ExtentY        =   556
         _Version        =   393216
         Format          =   20512769
         CurrentDate     =   46023
      End
      Begin MSComCtl2.MonthView MonthView1 
         Height          =   2370
         Left            =   -74880
         TabIndex        =   5
         Top             =   960
         Width           =   2700
         _ExtentX        =   4763
         _ExtentY        =   4180
         _Version        =   393216
         StartOfWeek     =   20512769
         CurrentDate     =   46023
      End
      Begin MSMask.MaskEdBox MaskEdBox1 
         Height          =   315
         Left            =   -72000
         TabIndex        =   6
         Top             =   480
         Width           =   1695
         _ExtentX        =   2990
         _ExtentY        =   556
         _Version        =   393216
         MaxLength       =   10
         Mask            =   "##/##/####"
         PromptChar      =   "_"
      End
   End
   Begin VB.Line Line1 
      BorderColor     =   &H00FF0000&
      BorderWidth     =   2
      X1              =   120
      X2              =   8280
      Y1              =   4800
      Y2              =   4800
   End
   Begin VB.Label lblStatus 
      Caption         =   "Ready"
      Height          =   255
      Left            =   120
      TabIndex        =   7
      Top             =   4920
      Width           =   8175
   End
End
Attribute VB_Name = "frmOcx"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Sub Form_Load()
    Dim li As ListItem, r As Integer
    Set li = ListView1.ListItems.Add(, "k1", "Keyboard")
    li.SubItems(1) = "25.50"
    Set li = ListView1.ListItems.Add(, "k2", "Mouse")
    li.SubItems(1) = "9.99"
    TreeView1.Nodes.Add , , "root", "Shop"
    TreeView1.Nodes.Add "root", tvwChild, "hw", "Hardware"
    For r = 1 To 3
        MSFlexGrid1.TextMatrix(r, 0) = "P" & r
        MSFlexGrid1.TextMatrix(r, 1) = "Item " & r
        MSFlexGrid1.TextMatrix(r, 2) = r * 10
    Next
    MSFlexGrid1.ColWidth(1) = 3000
    Debug.Print "items=" & ListView1.ListItems.Count & " nodes=" & TreeView1.Nodes.Count & _
                " grid=" & MSFlexGrid1.TextMatrix(0, 1) & "/" & MSFlexGrid1.TextMatrix(3, 1) & _
                " date=" & Format(DTPicker1.Value, "yyyy-mm-dd") & " tab=" & SSTab1.Tab
    SSTab1.Tab = 2
End Sub

Private Sub SSTab1_Click(PreviousTab As Integer)
    lblStatus.Caption = "tab " & PreviousTab & " -> " & SSTab1.Tab & " (" & SSTab1.TabCaption(SSTab1.Tab) & ")"
    Debug.Print lblStatus.Caption
End Sub
