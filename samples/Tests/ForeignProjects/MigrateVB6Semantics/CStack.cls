VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "CStack"
Option Explicit

Private mItems As Collection

Private Sub Class_Initialize()
    Set mItems = New Collection
End Sub

Public Sub Push(ByVal v As Variant)
    mItems.Add v
End Sub

Public Function Pop() As Variant
    Pop = mItems(mItems.Count)
    mItems.Remove mItems.Count
End Function

Public Property Get Size() As Long
    Size = mItems.Count
End Property
