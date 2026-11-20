# TextRing - Ring functions used by the Python form
# Python:  radcall("TextRing.shout", "hi")     VB6: RadCall("TextRing.shout", "hi")

func shout cText
    return upper(cText) + "!"

func chain n
    # Ring calling VB6 (arguments are passed as one list)
    return "Ring -> " + radcall("MathVB.Describe", [n * 2])
