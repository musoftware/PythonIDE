Attribute VB_Name = "modStart"
Option Explicit

Private mNotes As Collection

Public Sub Main()
    Set mNotes = New Collection
    AddNote "„—Õ»«"
    AddNote "Shopping list"
    frmMain.Show
End Sub

Public Sub AddNote(ByVal title As String)
    Dim n As CNote
    Set n = New CNote
    n.Title = title
    mNotes.Add n
End Sub

Public Function NoteCount() As Long
    NoteCount = mNotes.Count
End Function

Public Function GetNote(ByVal i As Long) As CNote
    Set GetNote = mNotes(i)
End Function
