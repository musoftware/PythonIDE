import CsLib
import JLib
import PsLib


def run():
    return "|".join(str(x) for x in (CsLib.Add(2, 3), CsLib.Greet("Py"), CsLib.Range(3), CsLib.IsEven(3),
                                      JLib.mul(3, 3), JLib.big(2), PsLib.Sub(1, 5), PsLib.Get_Upper("q")
                                      if hasattr(PsLib, "Get_Upper") else getattr(PsLib, "Get-Upper", None)))
