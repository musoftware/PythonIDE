"""BASIC code generator: FreeBASIC (``fbc -lang qb``, DOS or Windows), QuickBASIC 4.5 and QBasic 1.1.

The program draws with LOCATE / COLOR / PRINT, reads keys with INKEY$ and the mouse with
FreeBASIC's GETMOUSE (``__GETMOUSE`` in -lang qb) or, for QuickBASIC, INT 33h through CALL INTERRUPT
(``qb /L qb.qlb``). QBasic 1.1 has no mouse access and no COMMAND$ (dialect "qbasic": keyboard only).

Identifiers have no underscore (QBasic does not allow it): the handler of btnOK's Click is ``btnOKClick``.
"""
from __future__ import annotations

from .common import App, Regions, build_app, chunks, line_of

DIALECTS = ("freebasic", "quickbasic", "qbasic")
CM = ("' ", "")


def lit(b: bytes) -> str:
    """BASIC string expression of CP437 bytes: "abc" + CHR$(196) + ..."""
    if not b:
        return '""'
    parts: list[str] = []
    run = ""
    for x in b:
        if 32 <= x < 127 and x != 34:
            run += chr(x)
        else:
            if run:
                parts.append(f'"{run}"')
                run = ""
            parts.append(f"CHR$({x})")
    if run:
        parts.append(f'"{run}"')
    return " + ".join(parts)


def assign(target: str, b: bytes, width: int = 180) -> list[str]:
    """``target = <literal>`` split over several lines when long (QBasic's editor limit is 255)."""
    e = lit(b)
    if len(e) <= width:
        return [f"{target} = {e}"]
    out = []
    pieces = e.split(" + ")
    cur = ""
    first = True
    for p in pieces:
        if cur and len(cur) + len(p) + 3 > width:
            out.append(f"{target} = {cur}" if first else f"{target} = {target} + {cur}")
            first = False
            cur = p
        else:
            cur = p if not cur else cur + " + " + p
    if cur:
        out.append(f"{target} = {cur}" if first else f"{target} = {target} + {cur}")
    return out


def bname(key: str) -> str:
    return key.replace("_", "")


RUNTIME = r"""
' ===================================================================== RAD IDE text-mode runtime
SUB TuiInit
DIM i AS INTEGER
TuiCols = @COLS@: TuiRows = @ROWS@
@MODE@
LOCATE , , 0
@TABLES@
@MOUSEINIT@
TuiRun = 1
END SUB

FUNCTION TuiReadKey
k$ = INKEY$
IF LEN(k$) = 0 THEN
  TuiReadKey = 0
ELSEIF LEN(k$) >= 2 THEN
  TuiReadKey = 256 + ASC(MID$(k$, 2, 1))
ELSE
  TuiReadKey = ASC(k$)
END IF
END FUNCTION

FUNCTION TuiAltKey (k)
s = k - 256
r = 0
IF s >= 16 AND s <= 25 THEN r = ASC(MID$("QWERTYUIOP", s - 15, 1))
IF s >= 30 AND s <= 38 THEN r = ASC(MID$("ASDFGHJKL", s - 29, 1))
IF s >= 44 AND s <= 50 THEN r = ASC(MID$("ZXCVBNM", s - 43, 1))
IF s >= 120 AND s <= 129 THEN r = ASC(MID$("1234567890", s - 119, 1))
TuiAltKey = r
END FUNCTION

SUB TuiOut (x, y, s$, a)
n = LEN(s$)
IF x + n > TuiCols THEN n = TuiCols - x
IF n <= 0 OR y < 0 OR y >= TuiRows THEN EXIT SUB
t$ = LEFT$(s$, n)
f = a AND 15
IF a AND 128 THEN f = f + 16
COLOR f, (a \ 16) AND 7
IF y = TuiRows - 1 AND x + n = TuiCols THEN
  TuiCorner ASC(RIGHT$(t$, 1)), a
  n = n - 1
  IF n = 0 THEN EXIT SUB
  t$ = LEFT$(t$, n)
  COLOR f, (a \ 16) AND 7
END IF
LOCATE y + 1, x + 1
PRINT t$;
END SUB

SUB TuiCorner (c, a)
@CORNER@
END SUB

SUB TuiPut (x, y, s$, m$, w, a, h)
IF w <= 0 THEN EXIT SUB
IF LEN(s$) < w THEN t$ = s$ + SPACE$(w - LEN(s$)) ELSE t$ = LEFT$(s$, w)
st = 1
DO WHILE st <= w
  IF MID$(m$, st, 1) = "1" THEN c = h ELSE c = a
  en = st
  DO WHILE en < w
    IF MID$(m$, en + 1, 1) = "1" THEN d = h ELSE d = a
    IF d <> c THEN EXIT DO
    en = en + 1
  LOOP
  TuiOut x + st - 1, y, MID$(t$, st, en - st + 1), c
  st = en + 1
LOOP
END SUB

SUB TuiBox (x, y, w, h, a, dbl)
IF dbl THEN
  t$ = CHR$(201) + STRING$(w - 2, 205) + CHR$(187)
  m$ = CHR$(186) + SPACE$(w - 2) + CHR$(186)
  b$ = CHR$(200) + STRING$(w - 2, 205) + CHR$(188)
ELSE
  t$ = CHR$(218) + STRING$(w - 2, 196) + CHR$(191)
  m$ = CHR$(179) + SPACE$(w - 2) + CHR$(179)
  b$ = CHR$(192) + STRING$(w - 2, 196) + CHR$(217)
END IF
TuiOut x, y, t$, a
FOR r = 1 TO h - 2
  TuiOut x, y + r, m$, a
NEXT r
TuiOut x, y + h - 1, b$, a
END SUB

SUB TuiBlit (s)
SELECT CASE s
@RESTORES@
END SELECT
x = 0: y = 0
READ n
DO WHILE n > 0
  READ c, a
  TuiOut x, y, STRING$(n, c), a
  x = x + n
  IF x >= TuiCols THEN x = 0: y = y + 1
  READ n
LOOP
END SUB

SUB TuiFace (i)
IF ZI(i) = 0 OR ZT(i) = 9 THEN EXIT SUB
TuiMouseShow 0
t = ZT(i)
a = ZA(i): h = ZB(i)
IF ZN(i) = 0 THEN
  a = (a AND &HF0) OR 8: h = a
ELSEIF i = TuiFoc AND t >= 2 AND t <= 5 THEN
  a = ZF(i): h = ZG(i)
END IF
x = ZX(i): y = ZY(i): w = ZW(i)
SELECT CASE t
CASE 1
  s$ = LEFT$(TX$(i), w): m$ = LEFT$(HM$(i), w): p = 0
  IF ZJ(i) = 1 THEN p = (w - LEN(s$)) \ 2
  IF ZJ(i) = 2 THEN p = w - LEN(s$)
  TuiPut x, y, SPACE$(p) + s$, STRING$(p, "0") + m$, w, a, h
CASE 2
  s$ = LEFT$(TX$(i), w): m$ = LEFT$(HM$(i), w): p = (w - LEN(s$)) \ 2
  TuiPut x, y, SPACE$(p) + s$, STRING$(p, "0") + m$, w, a, h
CASE 3
  s$ = TX$(i)
  IF ZJ(i) THEN s$ = STRING$(LEN(s$), "*")
  IF i = TuiFoc AND LEN(s$) >= w THEN s$ = RIGHT$(s$, w - 1)
  TuiPut x, y, s$, "", w, a, a
CASE 4
  IF ZV(i) THEN s$ = "[X] " ELSE s$ = "[ ] "
  TuiPut x, y, s$ + TX$(i), "0000" + HM$(i), w, a, h
CASE 5
  IF ZV(i) THEN s$ = "(*) " ELSE s$ = "( ) "
  TuiPut x, y, s$ + TX$(i), "0000" + HM$(i), w, a, h
CASE 6
  ix = x: iy = y: iw = w: ih = ZH(i)
  IF ZJ(i) THEN ix = ix + 1: iy = iy + 1: iw = iw - 2: ih = ih - 2
  sel = ZV(i): tp = ZP(i)
  IF sel >= 0 THEN
    IF sel < tp THEN tp = sel
    IF sel >= tp + ih THEN tp = sel - ih + 1
  END IF
  ZP(i) = tp
  sa = ZL(i)
  IF ZN(i) = 0 THEN sa = a
  FOR r = 0 TO ih - 1
    k = tp + r: s$ = ""
    IF k < Z2(i) THEN s$ = IT$(Z1(i) + k)
    b = a
    IF k = sel AND k < Z2(i) THEN b = sa
    TuiPut ix, iy + r, s$, "", iw, b, b
  NEXT r
CASE 7
  mx = ZM(i)
  IF mx < 1 THEN mx = 1
  v = ZV(i)
  IF v < 0 THEN v = 0
  IF v > mx THEN v = mx
  f = (CLNG(v) * w) \ mx
  TuiPut x, y, STRING$(f, 219) + STRING$(w - f, 176), "", w, a, a
CASE 8
  TuiPut x, y, TX$(i), HM$(i), w, a, h
END SELECT
TuiMouseShow 1
END SUB

SUB TuiCursor
i = TuiFoc
IF i = 0 THEN LOCATE , , 0: EXIT SUB
IF ZT(i) <> 3 THEN LOCATE , , 0: EXIT SUB
p = LEN(TX$(i))
IF p > ZW(i) - 1 THEN p = ZW(i) - 1
LOCATE ZY(i) + 1, ZX(i) + p + 1, 1
END SUB

SUB TuiRedraw
TuiMouseShow 0
TuiBlit TuiCur
FOR i = 1 TO NC
  IF ZS(i) = TuiCur THEN TuiFace i
NEXT i
TuiCursor
TuiMouseShow 1
END SUB

SUB TuiShowScreen (s)
TuiCur = s
TuiFoc = 0
best = 0
FOR i = 1 TO NC
  IF ZS(i) = s AND ZO(i) > 0 AND ZI(i) = 1 AND ZN(i) = 1 THEN
    IF best = 0 THEN
      best = i
    ELSEIF ZO(i) < ZO(best) THEN
      best = i
    END IF
  END IF
NEXT i
TuiFoc = best
TuiRedraw
IF SV(s) AND 1 THEN TuiFireScreen s, 4
END SUB

SUB TuiFocus (i)
o = TuiFoc
TuiFoc = i
IF o > 0 AND o <> i THEN TuiFace o
IF i > 0 THEN TuiFace i
TuiCursor
END SUB

SUB TuiNext (d)
c = 0
IF TuiFoc THEN c = ZO(TuiFoc)
best = 0: wrap = 0
FOR j = 1 TO NC
  IF ZS(j) = TuiCur AND ZO(j) > 0 AND ZI(j) = 1 AND ZN(j) = 1 THEN
    IF d > 0 THEN
      IF ZO(j) > c THEN
        IF best = 0 THEN
          best = j
        ELSEIF ZO(j) < ZO(best) THEN
          best = j
        END IF
      END IF
      IF wrap = 0 THEN
        wrap = j
      ELSEIF ZO(j) < ZO(wrap) THEN
        wrap = j
      END IF
    ELSE
      IF ZO(j) < c THEN
        IF best = 0 THEN
          best = j
        ELSEIF ZO(j) > ZO(best) THEN
          best = j
        END IF
      END IF
      IF wrap = 0 THEN
        wrap = j
      ELSEIF ZO(j) > ZO(wrap) THEN
        wrap = j
      END IF
    END IF
  END IF
NEXT j
IF best = 0 THEN best = wrap
IF best THEN TuiFocus best
END SUB

SUB TuiActivate (i)
SELECT CASE ZT(i)
CASE 2, 6
  TuiFire i, 1
CASE 4
  ZV(i) = 1 - ZV(i)
  TuiFace i
  TuiFire i, 1
CASE 5
  FOR j = 1 TO NC
    IF ZT(j) = 5 AND ZS(j) = ZS(i) AND ZR(j) = ZR(i) AND j <> i AND ZV(j) <> 0 THEN
      ZV(j) = 0: TuiFace j
    END IF
  NEXT j
  ZV(i) = 1
  TuiFace i
  TuiFire i, 1
END SELECT
END SUB

SUB TuiListMove (i, d)
n = Z2(i)
IF n = 0 THEN EXIT SUB
v = ZV(i) + d
IF v < 0 THEN v = 0
IF v > n - 1 THEN v = n - 1
IF v <> ZV(i) THEN
  ZV(i) = v
  TuiFace i
  TuiFire i, 2
END IF
END SUB

SUB TuiHandleKey (k)
TuiKey = k
i = TuiFoc
IF i > 0 THEN
  IF ZE(i) AND 4 THEN TuiFire i, 3
END IF
IF TuiKey = 0 THEN EXIT SUB
IF SV(TuiCur) AND 4 THEN TuiFireScreen TuiCur, 3
k = TuiKey
IF k = 0 THEN EXIT SUB
i = TuiFoc
t = 0
IF i > 0 THEN t = ZT(i)
IF t = 3 THEN
  IF k = 8 THEN
    IF LEN(TX$(i)) > 0 THEN
      TX$(i) = LEFT$(TX$(i), LEN(TX$(i)) - 1)
      TuiFace i: TuiCursor
      IF ZE(i) AND 2 THEN TuiFire i, 2
    END IF
    EXIT SUB
  END IF
  IF k >= 32 AND k < 256 THEN
    IF LEN(TX$(i)) < ZM(i) THEN
      TX$(i) = TX$(i) + CHR$(k)
      TuiFace i: TuiCursor
      IF ZE(i) AND 2 THEN TuiFire i, 2
    END IF
    EXIT SUB
  END IF
END IF
SELECT CASE k
CASE 9
  TuiNext 1
CASE 271
  TuiNext -1
CASE 336, 333
  IF t = 6 THEN TuiListMove i, 1 ELSE TuiNext 1
CASE 328, 331
  IF t = 6 THEN TuiListMove i, -1 ELSE TuiNext -1
CASE 13
  IF t = 3 THEN
    TuiNext 1
  ELSEIF i > 0 THEN
    TuiActivate i
  END IF
CASE 32
  IF i > 0 AND t <> 6 THEN TuiActivate i
CASE 27
  IF SK(TuiCur) > 0 THEN
    TuiActivate SK(TuiCur)
  ELSEIF SE(TuiCur) THEN
    TuiRun = 0
  END IF
CASE 324
  IF SM(TuiCur) > 0 THEN TuiMenu SM(TuiCur)
CASE ELSE
  h = 0
  IF k > 256 THEN h = TuiAltKey(k)
  IF h > 0 THEN
    FOR m = 1 TO NM
      IF MSC(m) = TuiCur AND MKY(m) = h THEN TuiMenu m: EXIT SUB
    NEXT m
  END IF
  IF h = 0 AND k < 256 AND t <> 3 THEN h = ASC(UCASE$(CHR$(k)))
  IF h > 0 THEN
    FOR j = 1 TO NC
      IF ZS(j) = TuiCur AND ZK(j) = h AND ZI(j) = 1 AND ZN(j) = 1 AND ZO(j) > 0 THEN
        TuiFocus j
        IF ZT(j) = 2 OR ZT(j) = 4 OR ZT(j) = 5 THEN TuiActivate j
        EXIT SUB
      END IF
    NEXT j
  END IF
END SELECT
END SUB

SUB TuiClick (x, y)
b = SB(TuiCur)
IF b > 0 THEN
  IF y = ZY(b) THEN
    FOR m = 1 TO NM
      IF MSC(m) = TuiCur AND x >= MTX(m) AND x < MTX(m) + LEN(MTS$(m)) THEN TuiMenu m: EXIT SUB
    NEXT m
    EXIT SUB
  END IF
END IF
FOR j = NC TO 1 STEP -1
  IF ZS(j) = TuiCur AND ZO(j) > 0 AND ZI(j) = 1 AND ZN(j) = 1 THEN
    IF x >= ZX(j) AND x < ZX(j) + ZW(j) AND y >= ZY(j) AND y < ZY(j) + ZH(j) THEN
      TuiFocus j
      IF ZT(j) = 6 THEN
        iy = ZY(j): ih = ZH(j)
        IF ZJ(j) THEN iy = iy + 1: ih = ih - 2
        r = y - iy
        IF r >= 0 AND r < ih AND ZP(j) + r < Z2(j) THEN
          IF ZV(j) <> ZP(j) + r THEN
            ZV(j) = ZP(j) + r: TuiFace j
            IF ZE(j) AND 2 THEN TuiFire j, 2
          END IF
          TuiFire j, 1
        END IF
      ELSEIF ZT(j) <> 3 THEN
        TuiActivate j
      END IF
      EXIT SUB
    END IF
  END IF
NEXT j
END SUB

FUNCTION TuiStep (m, it, d)
n = MIC(m)
TuiStep = -1
IF n = 0 THEN EXIT FUNCTION
k = it
FOR c = 1 TO n
  k = k + d
  IF k < 0 THEN k = n - 1
  IF k >= n THEN k = 0
  IF ISP(MI1(m) + k) = 0 THEN TuiStep = k: EXIT FUNCTION
NEXT c
END FUNCTION

SUB TuiDrawMenu (m, it)
TuiMouseShow 0
b = SB(MSC(m))
TuiPut MTX(m), ZY(b), MTS$(m), MTM$(m), LEN(MTS$(m)), ZL(b), ZG(b)
x = MDX(m): y = MDY(m): w = MDW(m)
TuiBox x, y, w, MDH(m), ZA(b), 0
FOR k = 0 TO MIC(m) - 1
  j = MI1(m) + k
  IF ISP(j) THEN
    TuiOut x, y + 1 + k, CHR$(195) + STRING$(w - 2, 196) + CHR$(180), ZA(b)
  ELSEIF k = it THEN
    TuiPut x + 1, y + 1 + k, IL$(j), IM$(j), w - 2, ZL(b), ZG(b)
  ELSE
    TuiPut x + 1, y + 1 + k, IL$(j), IM$(j), w - 2, ZA(b), ZB(b)
  END IF
NEXT k
TuiMouseShow 1
END SUB

SUB TuiMenu (m0)
m = m0
it = TuiStep(m, -1, 1)
fire = 0
DO
  TuiRedraw
  TuiDrawMenu m, it
  cl = 0
  DO
    k = TuiReadKey
    IF k = 0 AND INSTR(TuiCmd$, "/DUMPK") > 0 THEN TuiDump: TuiRun = 0: EXIT SUB
    TuiPollMouse
    IF TuiMb AND 1 THEN
      IF TuiMp = 0 THEN TuiMp = 1: cl = 1
    ELSE
      TuiMp = 0
    END IF
  LOOP UNTIL k <> 0 OR cl <> 0
  done = 0
  IF cl THEN
    x = TuiMx: y = TuiMy
    b = SB(TuiCur)
    done = 1
    IF y = ZY(b) THEN
      FOR m2 = SM(TuiCur) TO SL(TuiCur)
        IF x >= MTX(m2) AND x < MTX(m2) + LEN(MTS$(m2)) THEN m = m2: it = TuiStep(m, -1, 1): done = 0
      NEXT m2
    ELSEIF x > MDX(m) AND x < MDX(m) + MDW(m) - 1 AND y > MDY(m) AND y < MDY(m) + MDH(m) - 1 THEN
      j = MI1(m) + y - MDY(m) - 1
      IF ISP(j) = 0 THEN fire = j ELSE done = 0
    END IF
  ELSE
    SELECT CASE k
    CASE 27, 324
      done = 1
    CASE 331
      m = m - 1
      IF m < SM(TuiCur) THEN m = SL(TuiCur)
      it = TuiStep(m, -1, 1)
    CASE 333
      m = m + 1
      IF m > SL(TuiCur) THEN m = SM(TuiCur)
      it = TuiStep(m, -1, 1)
    CASE 328
      it = TuiStep(m, it, -1)
    CASE 336
      it = TuiStep(m, it, 1)
    CASE 13
      IF it >= 0 THEN fire = MI1(m) + it: done = 1
    CASE ELSE
      h = 0
      IF k > 256 THEN
        h = TuiAltKey(k)
        FOR m2 = SM(TuiCur) TO SL(TuiCur)
          IF MKY(m2) = h AND h > 0 THEN m = m2: it = TuiStep(m, -1, 1): h = 0
        NEXT m2
      ELSEIF k < 256 THEN
        h = ASC(UCASE$(CHR$(k)))
      END IF
      IF h > 0 THEN
        FOR k2 = 0 TO MIC(m) - 1
          IF IKY(MI1(m) + k2) = h AND ISP(MI1(m) + k2) = 0 THEN fire = MI1(m) + k2: done = 1: EXIT FOR
        NEXT k2
      END IF
    END SELECT
  END IF
  IF fire > 0 THEN done = 1
LOOP UNTIL done
TuiRedraw
IF fire > 0 THEN TuiFireMenu fire
END SUB

SUB TuiMain
IF SPL THEN
  TuiBlit 0
  IF INSTR(TuiCmd$, "/DUMP") = 0 THEN
    t! = TIMER
    DO
      k = TuiReadKey
      IF SPS > 0 THEN
        IF TIMER - t! >= SPS OR TIMER < t! THEN k = 1
      END IF
    LOOP UNTIL k <> 0
  END IF
END IF
TuiShowScreen 1
dk = INSTR(TuiCmd$, "/DUMPK")
IF dk = 0 AND INSTR(TuiCmd$, "/DUMP") > 0 THEN TuiDump: TuiRun = 0
DO WHILE TuiRun
  k = TuiReadKey
  IF k = 0 AND dk > 0 THEN
    TuiDump: TuiRun = 0
  ELSEIF k THEN
    TuiHandleKey k
  END IF
  TuiPollMouse
  IF TuiMb AND 1 THEN
    IF TuiMp = 0 THEN
      TuiMp = 1
      TuiClick TuiMx, TuiMy
    END IF
  ELSE
    TuiMp = 0
  END IF
LOOP
TuiMouseShow 0
COLOR 7, 0
CLS
LOCATE 1, 1, 1
END SUB

SUB TuiDump
TuiMouseShow 0
OPEN "SCREEN.BIN" FOR OUTPUT AS #1
CLOSE #1
OPEN "SCREEN.BIN" FOR BINARY AS #1
FOR r = 1 TO TuiRows
  FOR c = 1 TO TuiCols
    b$ = CHR$(SCREEN(r, c)) + CHR$(SCREEN(r, c, 1))
    PUT #1, , b$
  NEXT c
NEXT r
CLOSE #1
END SUB

SUB TuiMsgBox (t$, s$)
w = LEN(s$) + 4
IF LEN(t$) + 6 > w THEN w = LEN(t$) + 6
IF w < 12 THEN w = 12
IF w > TuiCols THEN w = TuiCols
h = 6
x = (TuiCols - w) \ 2: y = (TuiRows - h) \ 2
TuiMouseShow 0
TuiBox x, y, w, h, &H70, 1
IF LEN(t$) THEN
  tt$ = " " + LEFT$(t$, w - 6) + " "
  TuiOut x + (w - LEN(tt$)) \ 2, y, tt$, &H70
END IF
TuiOut x + 2, y + 2, LEFT$(s$, w - 4), &H70
TuiOut x + (w - 6) \ 2, y + 4, "  OK  ", &H2F
LOCATE , , 0
TuiMouseShow 1
DO
  k = TuiReadKey
  IF k = 0 AND INSTR(TuiCmd$, "/DUMPK") > 0 THEN TuiDump: TuiRun = 0: EXIT SUB
  TuiPollMouse
  IF TuiMb AND 1 THEN
    IF TuiMp = 0 THEN TuiMp = 1: k = 13
  ELSE
    TuiMp = 0
  END IF
LOOP UNTIL k = 13 OR k = 27 OR k = 32
TuiRedraw
END SUB

SUB TuiSetText (i, s$)
TX$(i) = s$: HM$(i) = ""
IF ZS(i) = TuiCur THEN TuiFace i: TuiCursor
END SUB

FUNCTION TuiGetText$ (i)
TuiGetText$ = TX$(i)
END FUNCTION

SUB TuiSetValue (i, v)
IF ZT(i) = 5 AND v <> 0 THEN
  FOR j = 1 TO NC
    IF ZT(j) = 5 AND ZS(j) = ZS(i) AND ZR(j) = ZR(i) THEN ZV(j) = 0
  NEXT j
  ZV(i) = 1
ELSE
  ZV(i) = v
END IF
IF ZS(i) = TuiCur THEN TuiRedraw
END SUB

FUNCTION TuiGetValue (i)
TuiGetValue = ZV(i)
END FUNCTION

SUB TuiSetVisible (i, v)
ZI(i) = v
IF TuiFoc = i AND v = 0 THEN TuiNext 1
IF TuiFoc = i AND v = 0 THEN TuiFoc = 0
IF ZS(i) = TuiCur THEN TuiRedraw
END SUB

SUB TuiSetEnabled (i, v)
ZN(i) = v
IF TuiFoc = i AND v = 0 THEN TuiNext 1
IF TuiFoc = i AND v = 0 THEN TuiFoc = 0
IF ZS(i) = TuiCur THEN TuiRedraw
END SUB

SUB TuiAddItem (i, s$)
IF Z2(i) >= Z3(i) THEN EXIT SUB
IT$(Z1(i) + Z2(i)) = s$
Z2(i) = Z2(i) + 1
IF ZV(i) < 0 THEN ZV(i) = 0
IF ZS(i) = TuiCur THEN TuiFace i
END SUB

SUB TuiClearList (i)
Z2(i) = 0: ZV(i) = -1: ZP(i) = 0
IF ZS(i) = TuiCur THEN TuiFace i
END SUB

FUNCTION TuiGetItem$ (i, k)
IF k >= 0 AND k < Z2(i) THEN TuiGetItem$ = IT$(Z1(i) + k) ELSE TuiGetItem$ = ""
END FUNCTION

SUB TuiQuit
TuiRun = 0
END SUB

SUB TuiMouseShow (v)
IF TuiMouse = 0 THEN EXIT SUB
IF v THEN
  TuiHc = TuiHc - 1
  IF TuiHc <> 0 THEN EXIT SUB
ELSE
  TuiHc = TuiHc + 1
  IF TuiHc <> 1 THEN EXIT SUB
END IF
@MOUSESHOW@
END SUB

SUB TuiPollMouse
@MOUSEPOLL@
END SUB
"""

DECLARES = """DECLARE SUB TuiInit ()
DECLARE FUNCTION TuiReadKey ()
DECLARE FUNCTION TuiAltKey (k)
DECLARE SUB TuiOut (x, y, s$, a)
DECLARE SUB TuiCorner (c, a)
DECLARE SUB TuiPut (x, y, s$, m$, w, a, h)
DECLARE SUB TuiBox (x, y, w, h, a, dbl)
DECLARE SUB TuiBlit (s)
DECLARE SUB TuiFace (i)
DECLARE SUB TuiCursor ()
DECLARE SUB TuiRedraw ()
DECLARE SUB TuiShowScreen (s)
DECLARE SUB TuiFocus (i)
DECLARE SUB TuiNext (d)
DECLARE SUB TuiActivate (i)
DECLARE SUB TuiListMove (i, d)
DECLARE SUB TuiHandleKey (k)
DECLARE SUB TuiClick (x, y)
DECLARE FUNCTION TuiStep (m, it, d)
DECLARE SUB TuiDrawMenu (m, it)
DECLARE SUB TuiMenu (m0)
DECLARE SUB TuiMain ()
DECLARE SUB TuiDump ()
DECLARE SUB TuiMsgBox (t$, s$)
DECLARE SUB TuiSetText (i, s$)
DECLARE FUNCTION TuiGetText$ (i)
DECLARE SUB TuiSetValue (i, v)
DECLARE FUNCTION TuiGetValue (i)
DECLARE SUB TuiSetVisible (i, v)
DECLARE SUB TuiSetEnabled (i, v)
DECLARE SUB TuiAddItem (i, s$)
DECLARE SUB TuiClearList (i)
DECLARE FUNCTION TuiGetItem$ (i, k)
DECLARE SUB TuiQuit ()
DECLARE SUB TuiMouseShow (v)
DECLARE SUB TuiPollMouse ()
DECLARE SUB TuiFire (i, ev)
DECLARE SUB TuiFireMenu (k)
DECLARE SUB TuiFireScreen (s, ev)"""

MOUSE = {
    "freebasic": {
        "init": "IF __GETMOUSE(GMx&, GMy&, GMw&, GMb&) = 0 THEN TuiMouse = 1\n__SETMOUSE , , 1",
        "show": "__SETMOUSE , , v",
        "poll": ("TuiMb = 0\nIF TuiMouse = 0 THEN EXIT SUB\n"
                 "IF __GETMOUSE(GMx&, GMy&, GMw&, GMb&) = 0 THEN\n"
                 "  TuiMx = GMx&: TuiMy = GMy&: TuiMb = GMb& AND 7\nEND IF"),
    },
    "quickbasic": {
        "init": "TuiReg.ax = 0\nCALL INTERRUPT(&H33, TuiReg, TuiReg)\nIF TuiReg.ax = -1 THEN TuiMouse = 1\nTuiMouseShow 1",
        "show": ("IF v THEN TuiReg.ax = 1 ELSE TuiReg.ax = 2\n"
                 "CALL INTERRUPT(&H33, TuiReg, TuiReg)"),
        "poll": ("TuiMb = 0\nIF TuiMouse = 0 THEN EXIT SUB\nTuiReg.ax = 3\nCALL INTERRUPT(&H33, TuiReg, TuiReg)\n"
                 "TuiMb = TuiReg.bx AND 7: TuiMx = TuiReg.cx \\ 8: TuiMy = TuiReg.dx \\ 8"),
    },
    "qbasic": {"init": "TuiMouse = 0", "show": "' QBasic 1.1 cannot reach the mouse driver",
               "poll": "TuiMb = 0"},
}
# The bottom-right cell: PRINT with ';' leaves the cursor there without scrolling (QBasic behaviour, which
# FreeBASIC copies - checked cell by cell in DOSBox-X). The same code builds with FreeBASIC, so QBasic 1.1
# sources stay buildable without the user's QBASIC.EXE.
CORNER = {d: "LOCATE TuiRows, TuiCols\nPRINT CHR$(c);" for d in DIALECTS}


def generate(screens, old_text: str = "", dialect: str = "freebasic", app: App | None = None) -> tuple[str, list[str]]:
    """(source of main.bas, warnings)."""
    if dialect not in DIALECTS:
        raise ValueError(f"unknown BASIC dialect {dialect!r}")
    app = app or build_app(screens, basic=True)
    rg = Regions(old_text, CM)
    out: list[str] = []
    w = out.append
    title = app.screens[0].name
    w(f"' {title} - DOS text-mode program generated by RAD IDE (Text-Mode Designer)")
    w("' Do not edit outside the USER CODE regions: the rest is rewritten when the screens change.")
    if dialect == "freebasic":
        w("' Build: fbc -lang qb main.bas      (DOS: FreeBASIC for DOS; Windows: FreeBASIC win32 / win64)")
    elif dialect == "quickbasic":
        w("' Build: QB /L QB.QLB main.bas  (or BC main.bas /O + LINK main,,,QB.LIB;)  - QuickBASIC 4.5")
        w("'$INCLUDE: 'QB.BI'")
    else:
        w("' Run: QBASIC /RUN main.bas      (QBasic 1.1: keyboard only)")
    w("DEFINT A-Z")
    w(DECLARES)
    for h in app.handlers:
        w(f"DECLARE SUB {bname(h.key)} ()")
    w("")
    nc, nm, ni, ns = max(1, len(app.ctls)), max(1, len(app.menus)), max(1, len(app.items)), len(app.screens)
    w(f"CONST NC = {len(app.ctls)}, NM = {len(app.menus)}, NI = {len(app.items)}, NS = {ns}")
    for s in app.screens:
        w(f"CONST {s.name} = {s.index}")
    for c in app.ctls:
        w(f"CONST {c.name} = {c.index}")
    w("")
    arrays = "ZT ZS ZX ZY ZW ZH ZA ZB ZF ZG ZL ZV ZM ZP ZO ZK ZR ZE ZI ZN ZJ Z1 Z2 Z3".split()
    w("DIM SHARED " + ", ".join(f"{a}({nc})" for a in arrays))
    w(f"DIM SHARED TX$({nc}), HM$({nc}), IT$({app.n_items})")
    w(f"DIM SHARED MSC({nm}), MTX({nm}), MKY({nm}), MDX({nm}), MDY({nm}), MDW({nm}), MDH({nm}), MI1({nm}), "
      f"MIC({nm}), MTS$({nm}), MTM$({nm})")
    w(f"DIM SHARED IL$({ni}), IM$({ni}), ISP({ni}), IKY({ni})")
    w(f"DIM SHARED SE({ns}), SK({ns}), SV({ns}), SB({ns}), SM({ns}), SL({ns})")
    w("DIM SHARED TuiCur, TuiFoc, TuiRun, TuiKey, TuiMouse, TuiHc, TuiMb, TuiMx, TuiMy, TuiMp, TuiRows, TuiCols, SPL, SPS")
    w("DIM SHARED TuiCmd$")
    if dialect == "quickbasic":
        w("DIM SHARED TuiReg AS RegType")
    if dialect == "freebasic":
        w("DIM SHARED GMx&, GMy&, GMw&, GMb&")
    w("")
    w(rg.region("declarations", "' your shared variables (DIM SHARED ...) and CONSTs"))
    w("")
    w("TuiCmd$ = " + ("UCASE$(COMMAND$)" if dialect != "qbasic" else '""'))
    w("TuiInit")
    w(rg.region("startup", "' code that runs before the first screen is shown"))
    w("TuiMain")
    w("END")
    w("")
    # static layers
    for s in app.screens:
        if s.index == 1 and s.splash_runs:
            w("TS0:")
            _data(w, s.splash_runs)
        w(f"TS{s.index}:")
        _data(w, s.runs)
    w("")
    # handlers
    w("' ===================================================================== event handlers")
    for h in app.handlers:
        w(f"SUB {bname(h.key)}")
        w(rg.region(h.key, ""))
        w("END SUB")
        w("")
    w(rg.region("general", "' your own SUBs and FUNCTIONs"))
    w("")
    w(rg.orphans("' "))
    w("")
    # dispatch
    w("SUB TuiFire (i, ev)")
    hs = app.ctl_handlers()
    if hs:
        w("SELECT CASE i * 4 + ev")
        for h in hs:
            w(f"CASE {h.target * 4 + {'Click': 1, 'Change': 2, 'KeyPress': 3}[h.event]}: {bname(h.key)}")
        w("END SELECT")
    w("END SUB")
    w("")
    w("SUB TuiFireMenu (k)")
    hs = app.menu_handlers()
    if hs:
        w("SELECT CASE k")
        for h in hs:
            w(f"CASE {h.target}: {bname(h.key)}")
        w("END SELECT")
    w("END SUB")
    w("")
    w("SUB TuiFireScreen (s, ev)")
    hs = app.screen_handlers()
    if hs:
        w("SELECT CASE s * 8 + ev")
        for h in hs:
            w(f"CASE {h.target * 8 + (4 if h.event == 'Load' else 3)}: {bname(h.key)}")
        w("END SELECT")
    w("END SUB")
    rt = RUNTIME
    mode = "SCREEN 0\nWIDTH {c}, {r}\nCOLOR 7, 0\nCLS".format(c=app.cols, r=app.rows)
    rt = rt.replace("@COLS@", str(app.cols)).replace("@ROWS@", str(app.rows)).replace("@MODE@", mode)
    rt = rt.replace("@TABLES@", "\n".join(_tables(app)))
    rt = rt.replace("@RESTORES@", "\n".join(
        (["CASE 0: RESTORE TS0"] if app.splash() else []) +
        [f"CASE {s.index}: RESTORE TS{s.index}" for s in app.screens]))
    m = MOUSE[dialect]
    rt = rt.replace("@MOUSEINIT@", m["init"]).replace("@MOUSESHOW@", m["show"]).replace("@MOUSEPOLL@", m["poll"])
    rt = rt.replace("@CORNER@", CORNER[dialect])
    out.append(rt)
    return "\n".join(out).replace("\r", "") + "\n", list(app.warnings)


def _data(w, runs) -> None:
    flat = [f"{n},{c},{a}" for n, c, a in runs]
    for ch in chunks(flat, 16):
        w("DATA " + ",".join(ch))
    w("DATA 0")


def _tables(app: App) -> list[str]:
    t: list[str] = []
    for c in app.ctls:
        i = c.index
        vals = {"ZT": c.code, "ZS": c.screen, "ZX": c.x, "ZY": c.y, "ZW": c.w, "ZH": c.h, "ZA": c.a, "ZB": c.ha,
                "ZF": c.fa, "ZG": c.fha, "ZL": c.sa, "ZV": c.value, "ZM": c.max, "ZP": 0, "ZO": c.tab,
                "ZK": c.hotkey, "ZR": c.group, "ZE": c.events, "ZI": c.visible, "ZN": c.enabled, "ZJ": c.flag,
                "Z1": c.first_item, "Z2": len(c.items), "Z3": c.capacity}
        line = ": ".join(f"{k}({i}) = {v}" for k, v in vals.items() if v)
        t.append(line if line else f"ZT({i}) = {c.code}")
        if c.text:
            t.extend(assign(f"TX$({i})", c.text))
        if "1" in c.mask:
            t.append(f'HM$({i}) = "{c.mask}"')
        for k, it in enumerate(c.items):
            t.extend(assign(f"IT$({c.first_item + k})", it))
    for m in app.menus:
        i = m.index
        x, y, ww, hh = m.box
        t.append(f"MSC({i}) = {m.screen}: MTX({i}) = {m.title_x}: MKY({i}) = {m.hotkey}: MDX({i}) = {x}: "
                 f"MDY({i}) = {y}: MDW({i}) = {ww}: MDH({i}) = {hh}: MI1({i}) = {m.first_item}: MIC({i}) = {m.count}")
        t.extend(assign(f"MTS$({i})", m.title))
        t.append(f'MTM$({i}) = "{m.mask}"')
    for it in app.items:
        i = it.index
        if it.sep:
            t.append(f"ISP({i}) = 1")
            continue
        t.extend(assign(f"IL$({i})", it.line))
        t.append(f'IM$({i}) = "{it.mask}": IKY({i}) = {it.hotkey}')
    for s in app.screens:
        i = s.index
        t.append(f"SE({i}) = {s.esc_quits}: SK({i}) = {s.cancel}: SV({i}) = {s.events}: SB({i}) = {s.bar}: "
                 f"SM({i}) = {s.menu_first}: SL({i}) = {s.menu_last}")
    sp = app.splash()
    if sp:
        t.append(f"SPL = 1: SPS = {sp.splash_seconds}")
    return t


def handler_line(text: str, key: str) -> int:
    return line_of(text, rf"^SUB\s+{bname(key)}\b")


def handler_name(key: str) -> str:
    return bname(key)
