Attribute VB_Name = "modStore"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modStore - start-up, the shared ADO connection, the stock movements and small helpers.
'   EnsureSchema shows runtime DDL: the StockLog table is created the first time the program runs
'   (CREATE TABLE fails with an error when it already exists - that error is ignored).
'   ChangeStock is the only place where Medicines.Stock changes; every change is logged.
Option Explicit

Public cn As ADODB.Connection
Public gUser As String

' Values passed from the stock look-up to the sale form (public module variables)
Public gPickedCode As String
Public gPickedName As String

Sub Main()
    Set cn = New ADODB.Connection
    cn.Open "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=" & App.Path & "\pharmacy.mdb"
    EnsureSchema
    frmSplash.Show
End Sub

Public Sub EnsureSchema()
    On Error Resume Next
    cn.Execute "CREATE TABLE StockLog (LogID COUNTER PRIMARY KEY, LogTime DATETIME, Code TEXT(10), " & _
               "Change LONG, Reason TEXT(40), UserName TEXT(20))"
    Err.Clear
End Sub

Public Function SqlStr(ByVal s As String) As String
    SqlStr = "'" & Replace(s, "'", "''") & "'"
End Function

Public Function SqlDate(ByVal d As Date) As String
    SqlDate = "#" & Format$(d, "yyyy-mm-dd") & "#"
End Function

' Add (or subtract, with a negative Change) stock and log the movement
Public Sub ChangeStock(ByVal Code As String, ByVal Change As Long, ByVal Reason As String)
    cn.Execute "UPDATE Medicines SET Stock = Stock + (" & Change & ") WHERE Code = " & SqlStr(Code)
    cn.Execute "INSERT INTO StockLog (LogTime, Code, Change, Reason, UserName) VALUES (Now(), " & _
               SqlStr(Code) & ", " & Change & ", " & SqlStr(Reason) & ", " & SqlStr(gUser) & ")"
End Sub

Public Function StockOf(ByVal Code As String) As Long
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT Stock FROM Medicines WHERE Code = " & SqlStr(Code))
    If Not rs.EOF Then StockOf = rs!Stock
    rs.Close
End Function

' "M001 - Pain relief ..." -> "M001"
Public Function CodeOf(ByVal ComboText As String) As String
    Dim p As Integer
    p = InStr(ComboText, " - ")
    If p > 0 Then CodeOf = Left$(ComboText, p - 1) Else CodeOf = ComboText
End Function

' Fill a ComboBox with "code - name" of every medicine
Public Sub FillMedicines(cbo As ComboBox)
    Dim rs As ADODB.Recordset
    cbo.Clear
    Set rs = cn.Execute("SELECT Code, MedName FROM Medicines ORDER BY Code")
    While Not rs.EOF
        cbo.AddItem rs!Code & " - " & rs!MedName
        rs.MoveNext
    Wend
    rs.Close
End Sub
