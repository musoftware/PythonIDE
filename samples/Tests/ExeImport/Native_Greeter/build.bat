@echo off
rem Rebuilds Greeter.exe (Win32 dialog program: DIALOGEX resource, menu, About box)
rem with the MinGW toolchain the IDE installs (%LOCALAPPDATA%\RADIDE\toolchains\mingw64).
setlocal
set "TC=%LOCALAPPDATA%\RADIDE\toolchains\mingw64\bin"
if exist "%TC%\gcc.exe" set "PATH=%TC%;%PATH%"
pushd "%~dp0source"
windres app.rc -O coff -o "%TEMP%\greeter_app.res" || goto :fail
gcc -O2 -mwindows -o "%~dp0Greeter.exe" app.c "%TEMP%\greeter_app.res" || goto :fail
popd
echo Built %~dp0Greeter.exe
echo Import it again with File ^> Import ^> Program (.exe / .dll)... or:
echo    python ..\reimport.py "%~dp0Greeter.exe" "%~dp0Reimported" python-tk
exit /b 0
:fail
popd
echo Build failed - is MinGW installed (WinLibs into %TC%)?
exit /b 1
