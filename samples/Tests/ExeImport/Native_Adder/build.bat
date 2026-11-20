@echo off
rem Rebuilds Adder.exe (window built in code with CreateWindowEx, no resources)
rem with the MinGW toolchain the IDE installs (%LOCALAPPDATA%\RADIDE\toolchains\mingw64).
setlocal
set "TC=%LOCALAPPDATA%\RADIDE\toolchains\mingw64\bin"
if exist "%TC%\gcc.exe" set "PATH=%TC%;%PATH%"
gcc -O2 -mwindows -o "%~dp0Adder.exe" "%~dp0source\calc.c" || (echo Build failed - is MinGW installed? & exit /b 1)
echo Built %~dp0Adder.exe
echo Import it again with File ^> Import ^> Program (.exe / .dll)... or:
echo    python ..\reimport.py "%~dp0Adder.exe" "%~dp0Reimported" python-tk
