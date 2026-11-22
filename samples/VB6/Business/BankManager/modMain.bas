Attribute VB_Name = "modMain"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modMain - start-up code and helpers shared by every form of BankManager.
'   * Sub Main is the startup object (Project > Properties > Startup Object = Sub Main).
'   * One global ADO connection (cn) is opened at start and used by all forms.
'   * Small helpers: SQL quoting, numeric key filters, settings table, activity log file.
Option Explicit

Public cn As ADODB.Connection          ' the one connection to bank.mdb
Public gUserName As String             ' who logged in
Public gRole As String                 ' "admin" or "teller"

Public Const APP_TITLE As String = "BankManager"

Sub Main()
    ' open the database first: nothing works without it
    If Not ConnectDatabase() Then
        MsgBox "The database bank.mdb could not be opened." & vbCrLf & _
               "It must be in the program folder: " & App.Path, vbCritical, APP_TITLE
        End
    End If
    frmSplash.Show              ' the splash shows a progress bar, then opens the login form
End Sub

Public Function ConnectDatabase() As Boolean
    On Error GoTo Failed
    Set cn = New ADODB.Connection
    cn.ConnectionString = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=" & App.Path & "\bank.mdb"
    cn.Open
    ConnectDatabase = True
    Exit Function
Failed:
    ConnectDatabase = False
End Function

' Q("O'Neil") -> 'O''Neil'  (a text value ready to be put into an SQL statement)
Public Function Q(ByVal s As String) As String
    Q = "'" & Replace(s, "'", "''") & "'"
End Function

' Jet date literal: #yyyy-mm-dd#
Public Function D(ByVal dt As Date) As String
    D = "#" & Format$(dt, "yyyy-mm-dd") & "#"
End Function

' Use from a KeyPress event: KeyAscii = DigitsOnly(KeyAscii, True)
' Lets digits, Backspace and (optionally) one decimal point through; everything else is swallowed.
Public Function DigitsOnly(ByVal KeyAscii As Integer, Optional ByVal AllowDot As Boolean = False) As Integer
    Select Case KeyAscii
        Case 8, 48 To 57
            DigitsOnly = KeyAscii
        Case 46
            If AllowDot Then DigitsOnly = KeyAscii Else DigitsOnly = 0
        Case Else
            DigitsOnly = 0
    End Select
End Function

' Read a value from the Settings table (SetKey / SetValue)
Public Function AppSetting(ByVal Key As String, Optional ByVal DefaultValue As String = "") As String
    Dim rs As ADODB.Recordset
    Set rs = New ADODB.Recordset
    rs.Open "SELECT SetValue FROM Settings WHERE SetKey = " & Q(Key), cn, adOpenStatic, adLockReadOnly
    If rs.EOF Then
        AppSetting = DefaultValue
    Else
        AppSetting = rs!SetValue & ""
    End If
    rs.Close
End Function

' The next free account number (largest + 1, first one is 1001)
Public Function NextAccountNo() As Long
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT MAX(AccountNo) AS M FROM Customers")
    If IsNull(rs!M) Then
        NextAccountNo = 1001
    Else
        NextAccountNo = rs!M + 1
    End If
    rs.Close
End Function

' Clear every TextBox of a form and reset its ComboBoxes (For Each + TypeOf)
Public Sub ClearInputs(frm As Form)
    Dim ctl As Control
    For Each ctl In frm.Controls
        If TypeOf ctl Is TextBox Then
            ctl.Text = ""
        ElseIf TypeOf ctl Is ComboBox Then
            If ctl.ListCount > 0 Then ctl.ListIndex = 0
        End If
    Next
End Sub

' Append one line to bank.log next to the program (sequential file I/O)
Public Sub LogActivity(ByVal Text As String)
    Dim f As Integer
    f = FreeFile
    Open App.Path & "\bank.log" For Append As #f
    Print #f, Format$(Now, "yyyy-mm-dd hh:nn:ss") & vbTab & gUserName & vbTab & Text
    Close #f
End Sub
