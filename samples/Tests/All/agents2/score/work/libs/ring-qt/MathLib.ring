# MathLib - shared code for the project
#
# Other languages of the project can call the functions of this module:
#     Python: from radcall import radcall;  x = radcall("MathLib.add", 2, 3)
#     VB6:    x = RadCall("MathLib.add", 2, 3)
# Call functions written in other languages (arguments go in one list):
#     x = radcall("OtherModule.function", [2, 3])

# Return a + b. Projects that reference this library call it as <Library>_Add(a, b)
func Add a, b
	return a + b
