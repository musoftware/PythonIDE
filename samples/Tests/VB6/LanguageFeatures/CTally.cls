VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "CTally"
Option Explicit
' Counts words with a Scripting.Dictionary and reports progress with an event.
Public Event Progress(ByVal Done As Long, ByVal Total As Long)
Private mWords As Object

Private Sub Class_Initialize()
    Set mWords = CreateObject("Scripting.Dictionary")
    mWords.CompareMode = vbTextCompare
End Sub

Public Sub AddText(ByVal Text As String)
    Dim parts() As String, i As Long, w As String
    parts = Split(Text, " ")
    For i = 0 To UBound(parts)
        w = LCase$(Trim$(parts(i)))
        If w <> "" Then mWords(w) = mWords(w) + 1
        RaiseEvent Progress(i + 1, UBound(parts) + 1)
    Next
End Sub

Public Property Get Count(ByVal Word As String) As Long
Attribute Count.VB_UserMemId = 0
    If mWords.Exists(Word) Then Count = mWords(Word)
End Property

Public Property Get Words() As Variant
    Words = mWords.Keys
End Property
