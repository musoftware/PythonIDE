Attribute VB_Name = "VbCons"
Public Function Test()
    Test = PyLib.Add(2, 3) & "|" & PyLib.Greet("VB")
End Function
