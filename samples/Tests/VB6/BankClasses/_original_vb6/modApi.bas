Attribute VB_Name = "modApi"
Option Explicit

Public Declare Function GetTickCount Lib "kernel32" () As Long
Public Declare Function GetComputerName Lib "kernel32" Alias "GetComputerNameA" (ByVal lpBuffer As String, nSize As Long) As Long
Public Declare Sub GetLocalTime Lib "kernel32" (lpSystemTime As SYSTEMTIME)
Private Declare Function GetTempPath Lib "kernel32" Alias "GetTempPathA" (ByVal nBufferLength As Long, ByVal lpBuffer As String) As Long

Public Type SYSTEMTIME
    wYear As Integer
    wMonth As Integer
    wDayOfWeek As Integer
    wDay As Integer
    wHour As Integer
    wMinute As Integer
    wSecond As Integer
    wMilliseconds As Integer
End Type

Public Function ComputerName() As String
    Dim buf As String, n As Long
    buf = String$(255, 0)
    n = 255
    If GetComputerName(buf, n) <> 0 Then ComputerName = Left$(buf, n)
End Function

Public Function TempFolder() As String
    Dim buf As String * 260, n As Long
    n = GetTempPath(260, buf)
    TempFolder = Left$(buf, n)
End Function
