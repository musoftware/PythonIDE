import PerlLib, DartLib
print("PY", PerlLib.Add(2, 3), PerlLib.JoinWords("-", ["a", "b", "c"]), PerlLib.Stats([1, 2, 3]))
print("PY", DartLib.Times(6, 7), DartLib.Shout("hi"), DartLib.Range(3, 5))
