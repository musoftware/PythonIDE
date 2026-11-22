VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
  DataSourceBehavior  = 0  'vbNone
  MTSTransactionMode  = 0  'NotAnMTSObject
END
Attribute VB_Name = "clsGate"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' clsGate - one logic gate: set Kind, then ask Evaluate(a, b). NOT uses only the first input.
'   Dim g As New clsGate
'   g.Kind = gkXor
'   Debug.Print g.Evaluate(True, False)     ' True
Option Explicit

Public Enum GateKind
    gkAnd
    gkOr
    gkNot
    gkNand
    gkNor
    gkXor
    gkXnor
End Enum

Private mKind As GateKind
Private mEvaluations As Long        ' how many times Evaluate was called (a statistic)

Public Property Get Kind() As GateKind
    Kind = mKind
End Property

Public Property Let Kind(ByVal Value As GateKind)
    If Value < gkAnd Or Value > gkXnor Then Err.Raise 380, "clsGate", "Invalid gate kind"
    mKind = Value
End Property

Public Property Get Name() As String
    Name = Choose(mKind + 1, "AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR")
End Property

' Number of inputs the gate uses
Public Property Get Inputs() As Integer
    Inputs = IIf(mKind = gkNot, 1, 2)
End Property

Public Property Get Evaluations() As Long
    Evaluations = mEvaluations
End Property

Public Function Evaluate(ByVal A As Boolean, ByVal B As Boolean) As Boolean
    mEvaluations = mEvaluations + 1
    Select Case mKind
        Case gkAnd:  Evaluate = A And B
        Case gkOr:   Evaluate = A Or B
        Case gkNot:  Evaluate = Not A
        Case gkNand: Evaluate = Not (A And B)
        Case gkNor:  Evaluate = Not (A Or B)
        Case gkXor:  Evaluate = A Xor B
        Case gkXnor: Evaluate = Not (A Xor B)
    End Select
End Function

' The gate as a boolean expression of two input names: "A AND B", "NOT A", "NOT (A OR B)" ...
Public Function Expression(ByVal A As String, ByVal B As String) As String
    Select Case mKind
        Case gkNot:  Expression = "NOT " & A
        Case gkNand: Expression = "NOT (" & A & " AND " & B & ")"
        Case gkNor:  Expression = "NOT (" & A & " OR " & B & ")"
        Case gkXnor: Expression = "NOT (" & A & " XOR " & B & ")"
        Case Else:   Expression = A & " " & Name & " " & B
    End Select
End Function
