Attribute VB_Name = "modMain"
' No "Option Explicit" on purpose: undeclared names read as Empty (as in VB6)
Private Declare Function GetTickCount Lib "kernel32" _
    () As Long
Private Declare Function sndPlaySound Lib "WINMM.DLL" Alias _
      "sndPlaySoundA" (ByVal lpszSoundName As String, ByVal uFlags As _
      Long) As Long

Public Enum Modes
    mdDesign
    mdTest
    mdRun = 10
    mdStop
End Enum

Public Mode As Modes

Sub Main()
    Dim a As Integer, b As Integer, s As String
    a = 3: b = 7
    ' 1. line continuation after ")" and after an operator
    If (a > 1) _
        Or (b < 0) Then
        s = "continuation ok"
    End If
    Debug.Print s
    Debug.Print "sum=" & Add3(1, _
                              2, _
                              3)
    ' 2. Enum members without values + a variable typed with the Enum (a Long, starts at 0)
    Debug.Print "enum: " & mdDesign & " " & mdTest & " " & mdRun & " " & mdStop & " mode=" & Mode
    If Mode = mdDesign Then Debug.Print "mode is design"
    ' 3. undeclared variable without Option Explicit reads as Empty
    Debug.Print "undeclared=[" & SND_MEMORY & "] or 4 = " & (SND_MEMORY Or 4)
    ' 4. Get / Put without "#"
    Dim f As Integer, by As Byte, txt As String
    f = FreeFile
    Open App.Path & "\bytes.bin" For Binary Access Write As #f
    by = 72
    Put f, , by
    by = 105
    Put f, , by
    Close #f
    Open App.Path & "\bytes.bin" For Binary Access Read As #1
    Do While Not EOF(1)
        Get 1, , by
        If Not EOF(1) Then txt = txt & Chr(by)
    Loop
    Close #1
    Kill App.Path & "\bytes.bin"
    Debug.Print "binary=" & txt
    Debug.Print "declare ok: "; GetTickCount() > 0
End Sub

Private Function Add3(ByVal x As Integer, ByVal y As Integer, _
                      ByVal z As Integer) As Integer
    Add3 = x + y + z
End Function
