Attribute VB_Name = "L_vb_basic"
Option Explicit

' Other languages of the project can call the Public Functions of this module:
'     Python: from radcall import radcall;  x = radcall("L_vb_basic.AddNumbers", 2, 3)
'     Ring:   x = radcall("L_vb_basic.AddNumbers", [2, 3])
' Call functions written in other languages with:
'     x = RadCall("OtherModule.function", 2, 3)

' Return a + b. Projects that reference this library call it as <Library>.Add(a, b)
Public Function Add(ByVal a As Variant, ByVal b As Variant) As Variant
    Add = a + b
End Function
