# Tests of ringLibDemo.ring - run this file (it is the startup file)

load "ringLibDemo.ring"

func main
    check("addNumbers", addNumbers(2, 3) = 5)
    check("repeatText", repeatText("ab", 3) = "ababab")
    oCounter = new Counter("clicks")
    oCounter.increment()
    oCounter.increment()
    check("Counter", oCounter.nValue = 2)
    oCounter.show()

func check cName, lOk
    if lOk
        see "PASS " + cName + nl
    else
        see "FAIL " + cName + nl
    ok
