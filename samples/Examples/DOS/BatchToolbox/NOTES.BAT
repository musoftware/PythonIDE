@ECHO OFF
REM (c) 2026 Musoftware - https://musoftwares.com - MIT License
REM NOTES.BAT ADD | SHOW - the notes part of BatchToolbox (called with CALL, %1 = what to do).
IF "%1"=="ADD" GOTO ADD
IF "%1"=="SHOW" GOTO SHOW
ECHO Usage: NOTES ADD or NOTES SHOW
GOTO END

:ADD
ECHO Remember to back up the floppy disks.>> NOTES.TXT
ECHO A note was added to NOTES.TXT.
GOTO END

:SHOW
IF NOT EXIST NOTES.TXT GOTO NONE
TYPE NOTES.TXT
GOTO END

:NONE
ECHO There are no notes yet.

:END
