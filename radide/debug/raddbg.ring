# RAD IDE - Ring debug agent
# Loaded before the user's program. Breakpoints come from the RADDBG_BP
# environment variable ("file|line;file|line", file = lower-case basename).
# Speaks the RAD IDE line protocol on stdout/stdin (see languages/base.py).

$RADDBG_BP = []
$RADDBG_MODE = "run"          # run | step | next | out
$RADDBG_DEPTH = 0
$RADDBG_V = NULL
$RADDBG_LIST = []
$RADDBG_ERR = ""
$RADDBG_INEVAL = false
$RADDBG_TAG = "@@RADDBG@@"
# breakpoints changed while the program runs: the IDE rewrites this file (Ring cannot read stdin without
# blocking), the trace reads it again at most every 0.3 s
$RADDBG_BPFILE = ""
$RADDBG_BPTEXT = ""
$RADDBG_BPTIME = 0

RadDbg_Init()

func RadDbg_Init
    cSpec = SysGet("RADDBG_BP")
    if cSpec != NULL and cSpec != ""
        RadDbg_ParseBP(cSpec)
    ok
    cFile = SysGet("RADDBG_BPFILE")
    if cFile != NULL and cFile != ""
        $RADDBG_BPFILE = cFile
    ok
    ringvm_settrace("RadDbg_Trace()")

func RadDbg_ParseBP cSpec
    # "file|line[|condition];..." (conditions / hit counts are checked by the IDE: radide/debugger.py)
    $RADDBG_BP = []
    for cItem in str2list(substr(cSpec, ";", nl))
        nPos = substr(cItem, "|")
        if nPos > 0
            cRest = substr(cItem, nPos + 1)
            nBar = substr(cRest, "|")
            if nBar > 0 cRest = left(cRest, nBar - 1) ok
            $RADDBG_BP + [lower(trim(left(cItem, nPos - 1))), 0 + trim(cRest)]
        ok
    next

func RadDbg_ReloadBP
    if not fexists($RADDBG_BPFILE) return ok
    cText = read($RADDBG_BPFILE)
    if cText != $RADDBG_BPTEXT
        $RADDBG_BPTEXT = cText
        RadDbg_ParseBP(trim(cText))
    ok

func RadDbg_Send cText
    see $RADDBG_TAG + cText + nl
    fflush(stdout)

func RadDbg_BaseName cFile
    cFile = substr(cFile, "\", "/")
    nPos = 0
    for x = len(cFile) to 1 step -1
        if cFile[x] = "/" nPos = x exit ok
    next
    return lower(substr(cFile, nPos + 1))

func RadDbg_Skip cFile
    cBase = RadDbg_BaseName(cFile)
    if cBase = "raddbg.ring" or cBase = "_raddbg_run.ring" return true ok
    # ignore Ring's own libraries
    cPath = lower(substr(cFile, "\", "/"))
    if substr(cPath, "/ring/libraries/") > 0 or substr(cPath, "/ring/extensions/") > 0 return true ok
    if substr(cPath, "/") = 0 and (cBase = "guilib.ring" or cBase = "stdlibcore.ring") return true ok
    return false

func RadDbg_Trace
    if $RADDBG_INEVAL and ringvm_traceevent() = 4
        $RADDBG_ERR = "error"
        ringvm_passerror()
        return
    ok
    if $RADDBG_BPFILE != ""
        nNow = clock()
        if nNow - $RADDBG_BPTIME > clockspersecond() / 3 or nNow < $RADDBG_BPTIME
            $RADDBG_BPTIME = nNow
            RadDbg_ReloadBP()
        ok
    ok
    aData = ringvm_tracedata()
    cFile = aData[2]
    if RadDbg_Skip(cFile) return ok
    nEvent = ringvm_traceevent()
    if nEvent = 4    # error
        RadDbg_Break(cFile, aData[1], "error", len(ringvm_calllist()))
        return
    ok
    if nEvent != 1 return ok
    nLine = aData[1]
    nDepth = len(ringvm_calllist())
    lStop = false
    cReason = "step"
    switch $RADDBG_MODE
    on "step" lStop = true
    on "next" lStop = (nDepth <= $RADDBG_DEPTH)
    on "out"  lStop = (nDepth < $RADDBG_DEPTH)
    off
    if not lStop
        cBase = RadDbg_BaseName(cFile)
        for aBP in $RADDBG_BP
            if aBP[2] = nLine and aBP[1] = cBase
                lStop = true
                cReason = "breakpoint"
                exit
            ok
        next
    ok
    if lStop
        RadDbg_Break(cFile, nLine, cReason, nDepth)
    ok

func RadDbg_Str v
    if isString(v)
        v = substr(v, nl, "\n")
        if len(v) > 200 v = left(v, 200) + "..." ok
        return '"' + v + '"'
    ok
    if isNumber(v) return "" + v ok
    if isList(v) return "List (" + len(v) + " items)" ok
    if isObject(v) return "Object: " + classname(v) ok
    return type(v)

func RadDbg_Idents cExpr
    # variable names used in an expression (skips strings, members, calls, keywords)
    aKeywords = ["and", "or", "not", "new", "true", "false", "null", "nl", "see", "self", "this"]
    aOut = []
    nLen = len(cExpr)
    x = 1
    while x <= nLen
        c = cExpr[x]
        if c = '"' or c = "'" or c = "`"
            x++
            while x <= nLen and cExpr[x] != c x++ end
            x++
            loop
        ok
        if isalpha(c) or c = "_"
            nStart = x
            while x <= nLen and (isalnum(cExpr[x]) or cExpr[x] = "_") x++ end
            cName = substr(cExpr, nStart, x - nStart)
            # previous non-space char "." means member access
            nPrev = nStart - 1
            while nPrev >= 1 and cExpr[nPrev] = " " nPrev-- end
            lMember = (nPrev >= 1 and cExpr[nPrev] = ".")
            nNext = x
            while nNext <= nLen and cExpr[nNext] = " " nNext++ end
            lCall = (nNext <= nLen and cExpr[nNext] = "(")
            if not lMember and not lCall and not find(aKeywords, lower(cName))
                aOut + cName
            ok
            loop
        ok
        if isdigit(c)
            while x <= nLen and (isalnum(cExpr[x]) or cExpr[x] = ".") x++ end
            loop
        ok
        x++
    end
    return aOut

func RadDbg_Clean cText
    return substr(substr("" + cText, "|", "!"), nl, "\n")

func RadDbg_Break cFile, nLine, cReason, nDepth
    nScope = ringvm_scopescount() - 2
    RadDbg_Send("stop|" + cFile + "|" + nLine + "|" + cReason)
    # locals of the stopped function (globals when stopped at top level)
    if nScope > 1
        $RADDBG_LIST = []
        ringvm_evalinscope(nScope, "$RADDBG_LIST = locals()")
        for cName in $RADDBG_LIST
            if left(cName, 1) != "$"
                ringvm_evalinscope(nScope, "$RADDBG_V = " + cName)
                RadDbg_Send("var|" + cName + "|" + type($RADDBG_V) + "|" + RadDbg_Clean(RadDbg_Str($RADDBG_V)))
            ok
        next
    ok
    aCalls = ringvm_calllist()
    for x = len(aCalls) to 1 step -1
        aCall = aCalls[x]
        cFunc = "" + aCall[2]
        if not substr(lower(cFunc), "raddbg_") and not substr(lower(cFunc), "ringvm_")
            RadDbg_Send("frame|" + cFunc + "|" + cFile + "|" + nLine)
        ok
    next
    $RADDBG_DEPTH = nDepth
    while true
        RadDbg_Send("wait")
        give cCmd
        cCmd = trim(cCmd)
        if left(cCmd, 2) = "e "
            cExpr = substr(cCmd, 3)
            # errors raised inside ringvm_evalinscope cannot be caught from
            # here, so the try/catch is part of the evaluated code itself
            $RADDBG_ERR = ""
            $RADDBG_V = NULL
            # an unknown variable would abort the program: check names first
            cMissing = ""
            for cName in RadDbg_Idents(cExpr)
                $RADDBG_V = false
                ringvm_evalinscope(nScope, "$RADDBG_V = islocal('" + cName + "') or isglobal('" + cName + "')")
                if not $RADDBG_V cMissing = cName exit ok
            next
            $RADDBG_V = NULL
            if cMissing != ""
                RadDbg_Send("eval|Unknown variable: " + cMissing)
                loop
            ok
            $RADDBG_INEVAL = true
            if left(lower(cExpr), 4) = "see " or left(lower(cExpr), 1) = "?"
                ringvm_evalinscope(nScope, "try " + nl + cExpr + nl + "catch $RADDBG_ERR = cCatchError done")
                $RADDBG_INEVAL = false
                if $RADDBG_ERR = "" RadDbg_Send("eval|OK") else RadDbg_Send("eval|" + RadDbg_Clean($RADDBG_ERR)) ok
            else
                ringvm_evalinscope(nScope, "try " + nl + "$RADDBG_V = " + cExpr + nl + "catch $RADDBG_ERR = cCatchError done")
                $RADDBG_INEVAL = false
                if $RADDBG_ERR = ""
                    RadDbg_Send("eval|" + RadDbg_Clean(RadDbg_Str($RADDBG_V)))
                else
                    RadDbg_Send("eval|" + RadDbg_Clean($RADDBG_ERR))
                ok
            ok
            loop
        ok
        if left(cCmd, 2) = "b " or left(cCmd, 2) = "B "
            cSpec = substr(cCmd, 3)
            nPos = substr(cSpec, "|")
            if nPos > 0
                cRest = substr(cSpec, nPos + 1)
                nBar = substr(cRest, "|")
                if nBar > 0 cRest = left(cRest, nBar - 1) ok
                aBP = [lower(left(cSpec, nPos - 1)), 0 + trim(cRest)]
                if left(cCmd, 1) = "b"
                    $RADDBG_BP + aBP
                else
                    for x = len($RADDBG_BP) to 1 step -1
                        if $RADDBG_BP[x][1] = aBP[1] and $RADDBG_BP[x][2] = aBP[2]
                            del($RADDBG_BP, x)
                        ok
                    next
                ok
            ok
            loop
        ok
        switch cCmd
        on "c" $RADDBG_MODE = "run"  exit
        on "s" $RADDBG_MODE = "step" exit
        on "n" $RADDBG_MODE = "next" exit
        on "o" $RADDBG_MODE = "out"  exit
        on "q" RadDbg_Send("done") shutdown(0)
        off
    end
    if cReason = "error"
        RadDbg_Send("done")
        shutdown(1)
    ok
