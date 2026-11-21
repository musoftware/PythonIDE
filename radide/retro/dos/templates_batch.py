"""DOS Batch templates (run in DOSBox-X: COMMAND.COM of DOSBox-X, CHOICE from its Z: drive). Original code."""

HELLO = """@ECHO OFF
REM {name} - a DOS batch file (RAD IDE). Ctrl+F5 runs it in DOSBox-X.
ECHO Hello from {name}!
ECHO.
SET GREETING=Welcome to DOS batch programming
ECHO %GREETING%
ECHO Today is:
VER
FOR %%N IN (1 2 3 4 5) DO ECHO Counting %%N
IF EXIST MAIN.BAT ECHO MAIN.BAT is in the current folder.
GOTO END

:END
ECHO Done.
"""

MENU = """@ECHO OFF
REM {name} - a menu with CHOICE (1-3). ERRORLEVEL is tested from the highest value down.
:MENU
ECHO.
ECHO   ==========================
ECHO      RAD IDE  -  DOS MENU
ECHO   ==========================
ECHO   1  Show the DOS version
ECHO   2  List the files here
ECHO   3  Quit
ECHO.
CHOICE /C:123 Choose
IF ERRORLEVEL 3 GOTO QUIT
IF ERRORLEVEL 2 GOTO FILES
IF ERRORLEVEL 1 GOTO VERSION
GOTO MENU

:VERSION
VER
GOTO MENU

:FILES
DIR /W
GOTO MENU

:QUIT
ECHO Goodbye!
"""

LAUNCHER = """@ECHO OFF
REM {name} - a launcher: runs a DOS program of this project with parameters and checks its exit code.
REM Put your program (for example GAME.EXE) next to this file and change PROGRAM below.
SET PROGRAM=GAME.EXE
IF NOT EXIST %PROGRAM% GOTO MISSING
%PROGRAM% %1 %2 %3
IF ERRORLEVEL 1 ECHO %PROGRAM% ended with an error (ERRORLEVEL 1 or more).
GOTO END

:MISSING
ECHO %PROGRAM% was not found in this folder.

:END
"""

TEMPLATES = [
    ("dosbat_hello", "Hello (Batch)", "ECHO, SET, FOR, IF EXIST and GOTO.", {"MAIN.BAT": HELLO}),
    ("dosbat_menu", "CHOICE Menu", "A menu with CHOICE and IF ERRORLEVEL.", {"MAIN.BAT": MENU}),
    ("dosbat_launcher", "Program Launcher", "Starts a DOS program with parameters and checks ERRORLEVEL.",
     {"MAIN.BAT": LAUNCHER}),
]
