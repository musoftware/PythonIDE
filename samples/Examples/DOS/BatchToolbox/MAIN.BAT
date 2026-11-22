@ECHO OFF
REM (c) 2026 Musoftware - https://musoftwares.com - MIT License
REM
REM BatchToolbox - a DOS batch menu (COMMAND.COM in DOSBox-X):
REM   CHOICE with ERRORLEVEL tested from the highest value down, GOTO labels, CALL of a second batch file,
REM   IF EXIST / NOT EXIST, environment variables (SET, %VAR%), output redirection (> and >>), TYPE, DIR,
REM   FOR loops and a second batch file (NOTES.BAT) called with an argument.
REM RAD IDE checks every GOTO / CALL target when it "builds" a batch project; Ctrl+F5 runs it in DOSBox-X.
SET TOOLBOX=1.0
IF EXIST NOTES.TXT GOTO MENU
ECHO Notes of BatchToolbox> NOTES.TXT
ECHO ---------------------->> NOTES.TXT

:MENU
ECHO.
ECHO   ===================================
ECHO      BATCH TOOLBOX %TOOLBOX%  (RAD IDE)
ECHO   ===================================
ECHO   1  Add a note (a fixed line)
ECHO   2  Show the notes
ECHO   3  Count to five (FOR loop)
ECHO   4  List the batch files here
ECHO   5  Clear the notes
ECHO   6  Quit
ECHO.
CHOICE /C:123456 Choose
IF ERRORLEVEL 6 GOTO QUIT
IF ERRORLEVEL 5 GOTO CLEAR
IF ERRORLEVEL 4 GOTO FILES
IF ERRORLEVEL 3 GOTO COUNT
IF ERRORLEVEL 2 GOTO SHOW
IF ERRORLEVEL 1 GOTO ADD
GOTO MENU

:ADD
CALL NOTES.BAT ADD
GOTO MENU

:SHOW
CALL NOTES.BAT SHOW
GOTO MENU

:COUNT
FOR %%N IN (1 2 3 4 5) DO ECHO   counting %%N
GOTO MENU

:FILES
DIR /B *.BAT
GOTO MENU

:CLEAR
IF EXIST NOTES.TXT DEL NOTES.TXT
ECHO Notes of BatchToolbox> NOTES.TXT
ECHO ---------------------->> NOTES.TXT
ECHO The notes were cleared.
GOTO MENU

:QUIT
ECHO Goodbye from BatchToolbox!
SET TOOLBOX=
