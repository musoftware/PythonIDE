"""PyLib - shared code for the project.

Other languages of the project can call the functions of this module:
    Ring:   x = radcall("PyLib.add", [2, 3])
    VB6:    x = RadCall("PyLib.add", 2, 3)
Call functions written in other languages from Python with:
    from radcall import radcall
    x = radcall("OtherModule.function", 2, 3)
"""

def Add(a, b):
    """Return a + b. Projects that reference this library call it as <Library>.Add(a, b)."""
    return a + b
