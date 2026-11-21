VERSION 5.00
Begin VB.Form frmData 
   Caption         =   "Products (DAO Data control)"
   ClientHeight    =   3330
   ClientLeft      =   60
   ClientTop       =   450
   ClientWidth     =   5490
   LinkTopic       =   "Form1"
   ScaleHeight     =   3330
   ScaleWidth      =   5490
   StartUpPosition =   3  'Windows Default
   Begin VB.Data Data1 
      Caption         =   "Products"
      Connect         =   "Access"
      DatabaseName    =   "C:\Apps\Shop\shop.mdb"
      DefaultCursorType=   0  'DefaultCursor
      DefaultType     =   2  'UseODBC
      Exclusive       =   0   'False
      Height          =   345
      Left            =   120
      Options         =   0
      ReadOnly        =   0   'False
      RecordsetType   =   1  'Dynaset
      RecordSource    =   "select * from Products order by ID"
      Top             =   2280
      Width           =   3375
   End
   Begin VB.TextBox txtName 
      DataField       =   "Name"
      DataSource      =   "Data1"
      Height          =   315
      Left            =   1320
      TabIndex        =   0
      Top             =   240
      Width           =   2175
   End
   Begin VB.TextBox txtPrice 
      DataField       =   "Price"
      DataSource      =   "Data1"
      Height          =   315
      Left            =   1320
      TabIndex        =   1
      Top             =   720
      Width           =   1095
   End
   Begin VB.CommandButton cmdAdd 
      Caption         =   "&Add"
      Height          =   375
      Left            =   3840
      TabIndex        =   2
      Top             =   240
      Width           =   1335
   End
   Begin VB.CommandButton cmdSave 
      Caption         =   "&Save"
      Height          =   375
      Left            =   3840
      TabIndex        =   3
      Top             =   720
      Width           =   1335
   End
   Begin VB.CommandButton cmdFind 
      Caption         =   "&Find Monitor"
      Height          =   375
      Left            =   3840
      TabIndex        =   4
      Top             =   1200
      Width           =   1335
   End
   Begin VB.Label lblStock 
      DataField       =   "Stock"
      DataSource      =   "Data1"
      Height          =   255
      Left            =   1320
      TabIndex        =   7
      Top             =   1200
      Width           =   1095
   End
   Begin VB.Label Label1 
      Caption         =   "Name"
      Height          =   255
      Index           =   0
      Left            =   240
      TabIndex        =   5
      Top             =   300
      Width           =   975
   End
   Begin VB.Label Label1 
      Caption         =   "Price"
      Height          =   255
      Index           =   1
      Left            =   240
      TabIndex        =   6
      Top             =   780
      Width           =   975
   End
   Begin VB.Label Label1 
      Caption         =   "Stock"
      Height          =   255
      Index           =   2
      Left            =   240
      TabIndex        =   8
      Top             =   1200
      Width           =   975
   End
End
Attribute VB_Name = "frmData"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Sub Form_Load()
    ' DAO in code: OpenDatabase (hard-coded path -> shop.mdb next to the program), OpenRecordset, FindFirst,
    ' Edit / Update, TableDefs
    Dim db As Database, rs As Recordset, t As Variant, names As String
    Set db = OpenDatabase("C:\Apps\Shop\shop.mdb")
    For Each t In db.TableDefs
        names = names & t.Name & " "
    Next
    Debug.Print "tables: " & Trim(names)
    Set rs = db.OpenRecordset("Products", dbOpenDynaset)
    rs.FindFirst "Price < 10"
    If Not rs.NoMatch Then Debug.Print "cheapest: " & rs!Name
    rs.FindFirst "Name = 'Nothing'"
    Debug.Print "NoMatch: " & rs.NoMatch
    rs.MoveFirst
    rs.Edit
    rs!Notes = "checked"
    rs.Update
    rs.Close
    db.Execute "UPDATE Products SET Notes = 'USB' WHERE ID = 1"
    db.Close
    ' the Data control opens its RecordSource after Form_Load (VB6 order)
    Data1.DatabaseName = App.Path & "\shop.mdb"
End Sub

Private Sub cmdAdd_Click()
    Data1.Recordset.AddNew          ' bound controls are cleared, Save writes them
End Sub

Private Sub cmdSave_Click()
    Data1.Recordset.Update
    Debug.Print "saved: " & Data1.Recordset.RecordCount & " records"
End Sub

Private Sub cmdFind_Click()
    Data1.Recordset.FindFirst "Name = 'Monitor'"
    Debug.Print "found: " & txtName.Text & " " & txtPrice.Text & " stock " & lblStock.Caption
End Sub
