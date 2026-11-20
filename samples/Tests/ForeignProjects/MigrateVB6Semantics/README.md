# MigrateVB6Semantics

Hand-written VB6 project (`Sub Main` in `modSem.bas` + class `CStack.cls`) that prints one result per line with
`Debug.Print`: constants, Enum, Type, recursion, Select Case (Is / To / lists), Optional / ParamArray arguments,
arrays with UBound / ReDim Preserve, string functions (Left$/Right$/Mid$/InStr/Replace/Split/Join/StrReverse),
Val/CInt/Int/Fix (banker's rounding), `\`, Mod, `^`, Format, Do While / Loop Until / While-Wend, Exit For,
On Error GoTo + Err.Number, a Collection, a class with Property Get, With, And/Or on numbers and booleans.

The tests of **File > Migrate Project...** run it on the bundled VB6 interpreter and as the Python translation
(python-tk target, `modSem.py`) and compare the output line by line.
