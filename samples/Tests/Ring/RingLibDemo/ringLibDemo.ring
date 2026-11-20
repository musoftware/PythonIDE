# ringLibDemo - a Ring library
# Other programs use it with:  load "ringLibDemo.ring"

func addNumbers nA, nB
    # Returns the sum of two numbers
    return nA + nB

func repeatText cText, nTimes
    # Returns cText repeated nTimes
    cOut = ""
    for i = 1 to nTimes
        cOut += cText
    next
    return cOut

class Counter
    nValue = 0
    cName = "counter"

    func init cCounterName
        cName = cCounterName
        return self

    func increment
        nValue++
        return nValue

    func reset
        nValue = 0

    func show
        see cName + " = " + nValue + nl
