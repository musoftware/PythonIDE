Attribute VB_Name = "modExam"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modExam - the DAO database, the signed-in user and the marking rules of OnlineExam.
Option Explicit

Public db As DAO.Database
Public gUser As String
Public gFullName As String
Public gRole As String

' One question of a running exam (an array of these is kept by frmExam)
Public Type ExamQuestion
    QID As Long
    Text As String
    Options(3) As String
    Correct As String           ' "A".."D"
    Marks As Integer
    Chosen As String            ' "" = not answered
End Type

Public Sub OpenDb()
    If db Is Nothing Then Set db = OpenDatabase(App.Path & "\exam.mdb")
End Sub

Public Function SqlQ(ByVal s As String) As String
    SqlQ = "'" & Replace(s, "'", "''") & "'"
End Function

' "A" -> 0 ... "D" -> 3, anything else -> -1
Public Function OptionIndex(ByVal Letter As String) As Integer
    OptionIndex = InStr("ABCD", UCase$(Letter)) - 1
    If Len(Letter) <> 1 Then OptionIndex = -1
End Function

Public Function OptionLetter(ByVal Index As Integer) As String
    If Index >= 0 And Index <= 3 Then OptionLetter = Mid$("ABCD", Index + 1, 1)
End Function

Public Function SubjectName(ByVal SubjectID As Long) As String
    Dim rs As DAO.Recordset
    Set rs = db.OpenRecordset("SELECT SubjectName FROM Subjects WHERE SubjectID = " & SubjectID, dbOpenSnapshot)
    If Not rs.EOF Then SubjectName = rs!SubjectName
    rs.Close
End Function

' Fill a ComboBox with the subjects; ItemData = SubjectID
Public Sub FillSubjects(cbo As ComboBox)
    Dim rs As DAO.Recordset
    cbo.Clear
    Set rs = db.OpenRecordset("SELECT SubjectID, SubjectName FROM Subjects ORDER BY SubjectID", dbOpenSnapshot)
    Do Until rs.EOF
        cbo.AddItem rs!SubjectName
        cbo.ItemData(cbo.NewIndex) = rs!SubjectID
        rs.MoveNext
    Loop
    rs.Close
    If cbo.ListCount > 0 Then cbo.ListIndex = 0
End Sub
