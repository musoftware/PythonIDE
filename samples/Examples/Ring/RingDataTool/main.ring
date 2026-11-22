# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# RingDataTool - a console tool that reads a CSV file of monthly sales and prints statistics, a sorted
# table, an ASCII bar chart and a small matrix calculation; it also writes report.txt.
# Shows: functions, lists, sorting, classes, string formatting, file I/O, try/catch, command-line arguments.
# Run: F5 (Output window) - or  ring main.ring data\sales.csv  - the file name is optional.

load "stdlib.ring"

func main
    cFile = "data/sales.csv"
    if len(sysargv) >= 3 and lower(right(sysargv[len(sysargv)], 4)) = ".csv"
        cFile = sysargv[len(sysargv)]
    ok
    try
        aRows = ReadCsv(cFile)
    catch
        see "Cannot read " + cFile + ": " + cCatchError + nl
        return
    done
    see "RingDataTool - " + len(aRows) + " rows from " + cFile + nl + nl

    oStats = new Stats
    for aRow in aRows
        oStats.add(number(aRow[2]))
    next
    cReport = ""
    cReport += Line("Count", "" + oStats.count())
    cReport += Line("Total", Fmt(oStats.total()))
    cReport += Line("Mean", Fmt(oStats.mean()))
    cReport += Line("Median", Fmt(oStats.median()))
    cReport += Line("Std. deviation", Fmt(oStats.stddev()))
    cReport += Line("Minimum", Fmt(oStats.minimum()))
    cReport += Line("Maximum", Fmt(oStats.maximum()))
    see cReport + nl

    # the best months first (sort by the second column, descending)
    aSorted = SortRows(aRows)
    see "Best months:" + nl
    for i = 1 to min(3, len(aSorted))
        see "  " + i + ". " + aSorted[i][1] + "  " + Fmt(number(aSorted[i][2])) + nl
    next
    see nl + "Chart:" + nl
    cChart = Chart(aRows, oStats.maximum())
    see cChart + nl

    # a 2x2 matrix product (quarterly price x quantity) - lists of lists
    aA = [[2, 3], [1, 4]]
    aB = [[5, 1], [2, 6]]
    aC = MatMul(aA, aB)
    see "Matrix A x B = [" + aC[1][1] + " " + aC[1][2] + "; " + aC[2][1] + " " + aC[2][2] + "]" + nl

    write("report.txt", "RingDataTool report for " + cFile + nl + cReport + nl + cChart)
    see "Report written to report.txt" + nl

# ---------------------------------------------------------------- CSV
func ReadCsv cFile
    if not fexists(cFile) raise("file not found") ok
    aOut = []
    aLines = str2list(read(cFile))
    for i = 2 to len(aLines)                       # line 1 = header
        cLine = trim(substr(aLines[i], char(13), ""))
        if cLine = "" loop ok
        aOut + split(cLine, ",")
    next
    return aOut

func SortRows aRows
    aCopy = aRows
    for i = 1 to len(aCopy) - 1                    # selection sort, descending by value
        nBest = i
        for j = i + 1 to len(aCopy)
            if number(aCopy[j][2]) > number(aCopy[nBest][2]) nBest = j ok
        next
        if nBest != i
            aTmp = aCopy[i]  aCopy[i] = aCopy[nBest]  aCopy[nBest] = aTmp
        ok
    next
    return aCopy

func Chart aRows, nMax
    cOut = ""
    for aRow in aRows
        nBar = floor(number(aRow[2]) / nMax * 40)
        cOut += left(aRow[1] + "     ", 5) + "|" + copy("#", nBar) + " " + aRow[2] + nl
    next
    return cOut

func MatMul aA, aB
    aC = [[0, 0], [0, 0]]
    for i = 1 to 2
        for j = 1 to 2
            for k = 1 to 2
                aC[i][j] += aA[i][k] * aB[k][j]
            next
        next
    next
    return aC

# ---------------------------------------------------------------- formatting
func Line cName, cValue
    return left(cName + ":" + copy(" ", 18), 18) + cValue + nl

func Fmt nValue
    return "" + (floor(nValue * 100 + 0.5) / 100)

# ---------------------------------------------------------------- statistics
class Stats
    aValues = []

    func add nValue
        aValues + nValue

    func count
        return len(aValues)

    func total
        nSum = 0
        for x in aValues nSum += x next
        return nSum

    func mean
        if len(aValues) = 0 return 0 ok
        return total() / len(aValues)

    func median
        aS = sort(aValues)
        n = len(aS)
        if n = 0 return 0 ok
        if n % 2 = 1 return aS[(n + 1) / 2] ok
        return (aS[n / 2] + aS[n / 2 + 1]) / 2

    func stddev
        nMean = mean()
        nSum = 0
        for x in aValues nSum += (x - nMean) * (x - nMean) next
        return sqrt(nSum / len(aValues))

    func minimum
        return min(aValues)

    func maximum
        return max(aValues)
