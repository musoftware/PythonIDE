' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' QBasicArtMenu - a QBasic program for DOS: a boxed text-mode menu (arrow keys, 1-5, Enter, Esc) with
'   1  Times table     - a multiplication table drawn with LOCATE / COLOR / PRINT USING
'   2  Mode 13h art    - SCREEN 13 (320 x 200, 256 colours): palette bars, LINE, CIRCLE, PAINT, PSET stars
'   3  Number facts    - INPUT a number: prime test, divisors, binary (a FUNCTION and a SUB with arrays)
'   4  Calendar        - DATE$ and the days of the current month
'   5  Quit
' RAD IDE builds it with FreeBASIC -lang qb (the DOS version of fbc running inside DOSBox-X, no window) into
' a real DOS .EXE; Ctrl+F5 runs it in DOSBox-X. If you own QBASIC.EXE, Project > DOS > Run in QBasic runs the
' source unchanged.
DEFINT A-Z
DECLARE SUB DrawBox (Row, Col, Wid, Hgt, Clr)
DECLARE SUB ShowMenu (Sel)
DECLARE SUB RunItem (Sel)
DECLARE SUB TimesTable ()
DECLARE SUB ArtScreen ()
DECLARE SUB NumberFacts ()
DECLARE SUB Calendar ()
DECLARE SUB Pause ()
DECLARE SUB Header ()
DECLARE FUNCTION IsPrime (N AS LONG)

CONST NITEMS = 5
DIM SHARED Items$(1 TO NITEMS), Done

Items$(1) = "1  Times table"
Items$(2) = "2  Mode 13h art"
Items$(3) = "3  Number facts"
Items$(4) = "4  Calendar"
Items$(5) = "5  Quit"

Header
Sel = 1
DO
    ShowMenu Sel
    DO: K$ = INKEY$: LOOP WHILE K$ = ""
    IF LEN(K$) = 2 THEN
        SELECT CASE RIGHT$(K$, 1)
            CASE "H": Sel = Sel - 1: IF Sel < 1 THEN Sel = NITEMS
            CASE "P": Sel = Sel + 1: IF Sel > NITEMS THEN Sel = 1
        END SELECT
    ELSEIF K$ >= "1" AND K$ <= CHR$(48 + NITEMS) THEN
        Sel = VAL(K$)
        RunItem Sel
    ELSEIF K$ = CHR$(13) THEN
        RunItem Sel
    ELSEIF K$ = CHR$(27) THEN
        Done = -1
    END IF
LOOP UNTIL Done
COLOR 7, 0
CLS
PRINT "Thank you for using QBasicArtMenu. Goodbye!"
END

' the number of days of each month (read by Calendar; DATA belongs to the main module)
MonthDays:
DATA 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31

SUB Header
    COLOR 7, 1
    CLS
    COLOR 15, 1
    LOCATE 2, 25: PRINT "QBASIC ART MENU  -  RAD IDE"
    DrawBox 5, 24, 32, 9, 14
    COLOR 7, 1
    LOCATE 23, 14: PRINT "Arrows / 1-5 choose, Enter runs, Esc quits";
END SUB

SUB DrawBox (Row, Col, Wid, Hgt, Clr)
    COLOR Clr, 1
    LOCATE Row, Col: PRINT CHR$(201); STRING$(Wid - 2, 205); CHR$(187);
    FOR R = Row + 1 TO Row + Hgt - 2
        LOCATE R, Col: PRINT CHR$(186); SPACE$(Wid - 2); CHR$(186);
    NEXT R
    LOCATE Row + Hgt - 1, Col: PRINT CHR$(200); STRING$(Wid - 2, 205); CHR$(188);
END SUB

SUB ShowMenu (Sel)
    FOR I = 1 TO NITEMS
        LOCATE 6 + I, 27
        IF I = Sel THEN COLOR 0, 3 ELSE COLOR 15, 1
        PRINT " "; Items$(I); SPACE$(24 - LEN(Items$(I)));
    NEXT I
    COLOR 15, 1
END SUB

SUB RunItem (Sel)
    SELECT CASE Sel
        CASE 1: TimesTable
        CASE 2: ArtScreen
        CASE 3: NumberFacts
        CASE 4: Calendar
        CASE 5: Done = -1
    END SELECT
    IF NOT Done THEN Header
END SUB

SUB Pause
    COLOR 14, 0
    LOCATE 25, 28: PRINT "Press any key for the menu";
    DO: LOOP WHILE INKEY$ = ""
END SUB

SUB TimesTable
    COLOR 7, 0
    CLS
    COLOR 11, 0
    PRINT "Times table 1 .. 10"
    PRINT
    FOR R = 1 TO 10
        FOR C = 1 TO 10
            IF R = C THEN COLOR 14, 0 ELSE COLOR 7, 0
            PRINT USING "####"; R * C;
        NEXT C
        PRINT
    NEXT R
    COLOR 10, 0
    PRINT
    PRINT "7 x 8 ="; 7 * 8
    Pause
END SUB

SUB ArtScreen
    SCREEN 13
    ' palette bars: the 256 default VGA colours, one per column
    FOR X = 0 TO 255
        LINE (32 + X, 170)-(32 + X, 199), X
    NEXT X
    ' a sun with rays
    FOR A = 0 TO 359 STEP 15
        Rad! = A * 3.14159 / 180
        LINE (260, 45)-(260 + COS(Rad!) * 40, 45 + SIN(Rad!) * 40), 43
    NEXT A
    CIRCLE (260, 45), 22, 44
    PAINT (260, 45), 44, 44
    ' hills and a house
    CIRCLE (70, 175), 90, 2
    PAINT (70, 160), 2, 2
    LINE (40, 110)-(100, 150), 6, BF
    LINE (40, 110)-(70, 85), 4
    LINE (70, 85)-(100, 110), 4
    LINE (62, 128)-(76, 150), 0, BF
    ' stars
    RANDOMIZE 7
    FOR I = 1 TO 120
        PSET (INT(RND * 320), INT(RND * 60)), 15
    NEXT I
    DO: LOOP WHILE INKEY$ = ""
    SCREEN 0
    WIDTH 80, 25
END SUB

SUB NumberFacts
    COLOR 7, 0
    CLS
    COLOR 11, 0
    PRINT "Number facts"
    COLOR 7, 0
    INPUT "Type a whole number (1 - 30000)"; N&
    IF N& < 1 OR N& > 30000 THEN
        PRINT "Out of range."
    ELSE
        IF IsPrime(N&) THEN PRINT N&; "is a prime number." ELSE PRINT N&; "is not a prime number."
        PRINT "Divisors:";
        FOR D& = 1 TO N&
            IF N& MOD D& = 0 THEN PRINT D&;
        NEXT D&
        PRINT
        B$ = ""
        V& = N&
        DO
            B$ = CHR$(48 + (V& MOD 2)) + B$
            V& = V& \ 2
        LOOP WHILE V& > 0
        PRINT "Binary: "; B$
    END IF
    Pause
END SUB

FUNCTION IsPrime (N AS LONG)
    IsPrime = 0
    IF N < 2 THEN EXIT FUNCTION
    FOR D& = 2 TO INT(SQR(N))
        IF N MOD D& = 0 THEN EXIT FUNCTION
    NEXT D&
    IsPrime = -1
END FUNCTION

SUB Calendar
    DIM Days(1 TO 12)
    RESTORE MonthDays
    FOR I = 1 TO 12: READ Days(I): NEXT I
    COLOR 7, 0
    CLS
    D$ = DATE$                      ' mm-dd-yyyy
    M = VAL(LEFT$(D$, 2))
    Y = VAL(RIGHT$(D$, 4))
    IF M = 2 AND ((Y MOD 4 = 0 AND Y MOD 100 <> 0) OR Y MOD 400 = 0) THEN Days(2) = 29
    COLOR 11, 0
    PRINT "Today is "; D$; " - this month has"; Days(M); "days."
    COLOR 7, 0
    FOR I = 1 TO Days(M)
        PRINT USING "####"; I;
        IF I MOD 7 = 0 THEN PRINT
    NEXT I
    PRINT
    Pause
END SUB
