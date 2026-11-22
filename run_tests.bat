@echo off
rem RAD IDE tests - double-click for a menu, or pass the arguments of tools\run_tests.py:
rem   run_tests smoke | changed | area designer native | full | list | check   (see docs\TESTING.md)
setlocal
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

if not "%~1"=="" (
    "%PY%" tools\run_tests.py %*
    exit /b %ERRORLEVEL%
)

:menu
echo.
echo  RAD IDE tests
echo  -------------
echo   1  Smoke      pyflakes + the fastest check of each area  (about 5-10 min)
echo   2  Changed    suites related to the files you changed
echo   3  Area...    one or more areas (designer, native, vsx, events, robustness, fuzz, a11y, e2e, ...)
echo   4  Fast tier  what CI runs on every push
echo   5  Full       everything runnable, one at a time (long)
echo   6  List       what exists
echo   0  Exit
echo.
set "CHOICE="
set "ARGS="
set /p "CHOICE=Choose: "
if "%CHOICE%"=="1" set "ARGS=smoke --open"
if "%CHOICE%"=="2" set "ARGS=changed --open"
if "%CHOICE%"=="3" (
    "%PY%" tools\run_tests.py areas
    set "AREA="
    set /p "AREA=Area name(s): "
)
if "%CHOICE%"=="3" set "ARGS=area %AREA% --open"
if "%CHOICE%"=="4" set "ARGS=fast --open"
if "%CHOICE%"=="5" set "ARGS=full --open"
if "%CHOICE%"=="6" set "ARGS=list"
if "%CHOICE%"=="0" exit /b 0
if not defined ARGS goto menu
"%PY%" tools\run_tests.py %ARGS%
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo All tests passed.) else (echo %RC% test^(s^) failed - see the report.)
pause
exit /b %RC%
