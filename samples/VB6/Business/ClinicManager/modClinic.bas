Attribute VB_Name = "modClinic"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modClinic - start-up (Sub Main asks for the staff PIN with an InputBox) and the DAO database
' object shared by the forms. ClinicManager uses DAO only: the intrinsic Data control on frmMain
' and DAO Database / Recordset objects in code.
Option Explicit

Public gDb As DAO.Database
Public gStaff As String

Public Function DbPath() As String
    DbPath = App.Path & "\clinic.mdb"
End Function

Sub Main()
    Dim pin As String, rs As DAO.Recordset, tries As Integer
    Set gDb = DBEngine.Workspaces(0).OpenDatabase(DbPath())
    Do
        pin = InputBox("Staff PIN (demo: 1234):", "ClinicManager")
        If pin = "" Then End                      ' Cancel
        Set rs = gDb.OpenRecordset("SELECT FullName FROM Staff WHERE StaffPin = '" & Replace(pin, "'", "") & "'", _
                                   dbOpenSnapshot)
        If Not rs.EOF Then
            gStaff = rs!FullName
            rs.Close
            Exit Do
        End If
        rs.Close
        tries = tries + 1
        MsgBox "Unknown PIN.", vbExclamation, "ClinicManager"
    Loop Until tries >= 3
    If gStaff = "" Then End
    frmMain.Show
End Sub

' Age in whole years on a given day
Public Function AgeOn(ByVal BirthDate As Date, ByVal OnDay As Date) As Integer
    AgeOn = DateDiff("yyyy", BirthDate, OnDay)
    If DateSerial(Year(OnDay), Month(BirthDate), Day(BirthDate)) > OnDay Then AgeOn = AgeOn - 1
End Function

' Next patient number: highest + 1
Public Function NextPatientNo() As Long
    Dim rs As DAO.Recordset
    Set rs = gDb.OpenRecordset("SELECT MAX(PatientNo) AS M FROM Patients", dbOpenSnapshot)
    NextPatientNo = IIf(IsNull(rs!M), 1, rs!M + 1)
    rs.Close
End Function
