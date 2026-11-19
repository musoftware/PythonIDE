
import JsLib, PhpLib, TsLib
print("R1", JsLib.Add(2, 3))
print("R2", JsLib.Greet("ann"))
print("R3", JsLib.Stats([1, 2, 3]))
print("R4", PhpLib.Add(4, 5), PhpLib.Info()["lang"])
print("R5", TsLib.Square(7), TsLib.Join(["a", "b"], "+"))
