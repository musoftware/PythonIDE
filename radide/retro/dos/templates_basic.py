"""QBasic / QuickBASIC templates (FreeBASIC ``-lang qb``; most of them also run in the user's own QBASIC.EXE).

Original RAD IDE code. Box-drawing characters are written with CHR$() so the sources stay plain ASCII.
"""

HELLO = """' {name} - a QBasic program (RAD IDE)
' Build: FreeBASIC -lang qb -> a real DOS .EXE. Run: Ctrl+F5 opens it in DOSBox-X.
DEFINT A-Z

CLS
COLOR 14, 1
PRINT " Hello from {name}! "
COLOR 7, 0
PRINT
INPUT "What is your name"; N$
IF N$ = "" THEN N$ = "friend"
PRINT "Welcome to DOS programming, "; N$; "!"
FOR I = 1 TO 5
    PRINT I; "x"; I; "="; I * I
NEXT I
PRINT "Done."
END
"""

MENU = """' {name} - a text-mode menu (arrow keys / 1-4 / Enter / Esc)
DEFINT A-Z
DECLARE SUB DrawBox (Row, Col, Wid, Hgt)
DECLARE SUB ShowMenu (Sel)
DECLARE SUB RunItem (Sel)

DIM SHARED Items$(1 TO 4), Done
Items$(1) = "1  Say hello"
Items$(2) = "2  Show the time"
Items$(3) = "3  Count to ten"
Items$(4) = "4  Quit"

COLOR 7, 1
CLS
COLOR 15, 1
LOCATE 2, 28: PRINT "RAD IDE  -  DOS MENU"
DrawBox 5, 24, 32, 8
Sel = 1
DO
    ShowMenu Sel
    DO: K$ = INKEY$: LOOP WHILE K$ = ""
    IF LEN(K$) = 2 THEN
        SELECT CASE RIGHT$(K$, 1)
            CASE "H": Sel = Sel - 1: IF Sel < 1 THEN Sel = 4
            CASE "P": Sel = Sel + 1: IF Sel > 4 THEN Sel = 1
        END SELECT
    ELSEIF K$ >= "1" AND K$ <= "4" THEN
        Sel = VAL(K$)
        ShowMenu Sel
        RunItem Sel
    ELSEIF K$ = CHR$(13) THEN
        RunItem Sel
    ELSEIF K$ = CHR$(27) THEN
        Done = -1
    END IF
LOOP UNTIL Done
COLOR 7, 0
CLS
PRINT "Goodbye!"
END

SUB DrawBox (Row, Col, Wid, Hgt)
    COLOR 14, 1
    LOCATE Row, Col: PRINT CHR$(201); STRING$(Wid - 2, 205); CHR$(187);
    FOR R = Row + 1 TO Row + Hgt - 2
        LOCATE R, Col: PRINT CHR$(186); SPACE$(Wid - 2); CHR$(186);
    NEXT R
    LOCATE Row + Hgt - 1, Col: PRINT CHR$(200); STRING$(Wid - 2, 205); CHR$(188);
END SUB

SUB RunItem (Sel)
    COLOR 15, 1
    LOCATE 15, 10: PRINT SPACE$(60);
    LOCATE 15, 10
    SELECT CASE Sel
        CASE 1: PRINT "Hello! This menu was written in QBasic.";
        CASE 2: PRINT "The time is "; TIME$;
        CASE 3
            FOR I = 1 TO 10: PRINT I; : NEXT I
        CASE 4: Done = -1
    END SELECT
END SUB

SUB ShowMenu (Sel)
    FOR I = 1 TO 4
        LOCATE 6 + I, 27
        IF I = Sel THEN COLOR 0, 3 ELSE COLOR 15, 1
        PRINT " "; Items$(I); SPACE$(24 - LEN(Items$(I)));
    NEXT I
    COLOR 15, 1
END SUB
"""

MODE13 = """' {name} - mode 13h graphics (320 x 200, 256 colours). Any key quits.
DEFINT A-Z
SCREEN 13
' colour bars
FOR X = 0 TO 255
    LINE (X + 32, 150)-(X + 32, 199), X
NEXT X
' rings
FOR R = 10 TO 70 STEP 6
    CIRCLE (160, 75), R, 32 + R \\ 3
NEXT R
' a filled box with a frame
LINE (20, 20)-(80, 60), 4, BF
LINE (20, 20)-(80, 60), 15, B
' a star field
RANDOMIZE 1
FOR I = 1 TO 300
    PSET (RND * 319, RND * 140), 16 + INT(RND * 16)
NEXT I
LOCATE 1, 12: PRINT "MODE 13h DEMO"
DO: LOOP WHILE INKEY$ = ""
SCREEN 0
WIDTH 80
PRINT "Back in text mode."
END
"""

SPEAKER = """' {name} - PC speaker music through the timer chip (ports 42h, 43h, 61h).
' The same code runs in QBasic and in the FreeBASIC DOS build. QBasic also has SOUND and PLAY.
DEFINT A-Z
DECLARE SUB Tone (Freq, Ms)

PRINT "Playing a little tune on the PC speaker..."
RESTORE Tune
DO
    READ F, D
    IF D = 0 THEN EXIT DO
    Tone F, D
LOOP
PRINT "Finished."
END

Tune:
DATA 523,150, 587,150, 659,150, 698,150, 784,300, 784,300
DATA 880,150, 880,150, 880,150, 880,150, 784,450
DATA 0,0

SUB Tone (Freq, Ms)
    IF Freq > 0 THEN
        Divisor& = 1193180 \\ Freq
        OUT &H43, &HB6
        OUT &H42, Divisor& AND 255
        OUT &H42, Divisor& \\ 256
        OUT &H61, INP(&H61) OR 3
    END IF
    T! = TIMER
    DO: LOOP WHILE TIMER - T! < Ms / 1000! AND TIMER >= T!
    OUT &H61, INP(&H61) AND 252
END SUB
"""

MOUSE = """' {name} - the mouse in mode 13h. Left button paints, right button or a key quits.
' FreeBASIC -lang qb reads the mouse with __GETMOUSE (QuickBASIC 4.5 would use CALL INTERRUPT &H33).
DEFINT A-Z
DIM X AS LONG, Y AS LONG, B AS LONG
SCREEN 13
LOCATE 1, 1: PRINT "Paint with the left button"
LOCATE 25, 1: PRINT "Right button / any key: quit";
OldX = -1
DO
    __GETMOUSE X, Y, , B
    IF X >= 0 THEN
        IF B AND 1 THEN CIRCLE (X, Y), 3, 40 + (X \\ 20), , , , F
        IF X <> OldX OR Y <> OldY THEN
            LOCATE 2, 1: PRINT USING "X=### Y=###"; X; Y
            OldX = X: OldY = Y
        END IF
        IF B AND 2 THEN EXIT DO
    END IF
LOOP WHILE INKEY$ = ""
SCREEN 0
WIDTH 80
PRINT "Mouse demo finished."
END
"""

LINE_NUMBERS = """10 REM {name} - an old-style BASIC program with line numbers (GW-BASIC / QBasic)
20 CLS
30 PRINT "MULTIPLICATION TABLE"
40 FOR I = 1 TO 5
50 GOSUB 1000
60 NEXT I
70 PRINT "SUM OF DATA ="; S
80 END
1000 REM ---- one row ----
1010 FOR J = 1 TO 5
1020 PRINT USING "###"; I * J;
1030 NEXT J
1040 PRINT
1050 READ V: S = S + V
1060 RETURN
2000 DATA 10, 20, 30, 40, 50
"""

TEMPLATES = [
    ("dosqb_hello", "Hello (QBasic)", "PRINT, INPUT, COLOR and a FOR loop. Builds a real DOS .EXE with "
     "FreeBASIC -lang qb.", {"MAIN.BAS": HELLO}),
    ("dosqb_menu", "Text-Mode Menu", "A boxed menu with LOCATE / COLOR / INKEY$, arrow keys, SUBs and "
     "SELECT CASE.", {"MAIN.BAS": MENU}),
    ("dosqb_mode13", "Mode 13h Graphics", "SCREEN 13: LINE, CIRCLE, PSET and 256 colours.", {"MAIN.BAS": MODE13}),
    ("dosqb_speaker", "PC Speaker Music", "Plays a tune through the timer chip with OUT / INP (works in "
     "QBasic too).", {"MAIN.BAS": SPEAKER}),
    ("dosqb_mouse", "Mouse Painting", "Mode 13h painting with the mouse (INT 33h driver, __GETMOUSE).",
     {"MAIN.BAS": MOUSE}),
    ("dosqb_lines", "Line-Numbered BASIC", "GW-BASIC style: line numbers, GOSUB / RETURN, READ / DATA.",
     {"MAIN.BAS": LINE_NUMBERS}),
]
