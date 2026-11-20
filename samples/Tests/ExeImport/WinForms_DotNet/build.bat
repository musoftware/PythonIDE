@echo off
rem Rebuilds WinHello.exe (+ WinHello.dll), a small WinForms app, with the .NET SDK (dotnet 9).
rem The importer decompiles it with ilspycmd (%LOCALAPPDATA%\RADIDE\tools\ilspycmd.exe).
setlocal
dotnet build "%~dp0source\WinHello.csproj" -c Release -o "%~dp0bin" -nologo || (echo Build failed - install the .NET 9 SDK & exit /b 1)
rem dotnet leaves bin\ and obj\ next to the .csproj - they are build output only
rmdir /s /q "%~dp0source\bin" "%~dp0source\obj" 2>nul
echo Built %~dp0bin\WinHello.exe
echo Import it again with File ^> Import ^> Program (.exe / .dll)... or:
echo    python ..\reimport.py "%~dp0bin\WinHello.exe" "%~dp0Reimported" python-tk
