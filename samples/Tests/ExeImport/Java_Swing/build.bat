@echo off
rem Rebuilds JavaHello.jar (a Swing window with an anonymous ActionListener).
rem Uses the JDK the IDE downloads (%LOCALAPPDATA%\RADIDE\tools\jdk25\...) or javac/jar on PATH.
setlocal
for /d %%D in ("%LOCALAPPDATA%\RADIDE\tools\jdk25\*") do if exist "%%D\bin\javac.exe" set "PATH=%%D\bin;%PATH%"
set "CLS=%TEMP%\javahello_classes"
rmdir /s /q "%CLS%" 2>nul
javac -d "%CLS%" "%~dp0source\src\hello\MainFrame.java" || (echo Build failed - install a JDK & exit /b 1)
jar cfm "%~dp0JavaHello.jar" "%~dp0source\manifest.txt" -C "%CLS%" . || exit /b 1
echo Built %~dp0JavaHello.jar
echo Import it again with File ^> Import ^> Program (.exe / .dll)... or:
echo    python ..\reimport.py "%~dp0JavaHello.jar" "%~dp0Reimported" python-tk
