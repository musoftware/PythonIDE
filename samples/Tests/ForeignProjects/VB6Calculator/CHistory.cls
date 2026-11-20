VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "CHistory"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

Private mItems As Collection

Private Sub Class_Initialize()
    Set mItems = New Collection
End Sub

Public Sub Add(ByVal entry As String)
    mItems.Add entry
End Sub

Public Sub Clear()
    Set mItems = New Collection
End Sub

Public Property Get Count() As Long
    Count = mItems.Count
End Property

Public Property Get Last() As String
    If mItems.Count > 0 Then Last = mItems(mItems.Count)
End Property
