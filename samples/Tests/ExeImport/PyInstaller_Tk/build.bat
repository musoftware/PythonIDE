@echo off
rem Rebuilds TkHello.exe (a tkinter program frozen with PyInstaller --onefile --windowed).
rem Uses the IDE's own .venv when it exists (samples\Tests\ExeImport\PyInstaller_Tk -> repo root is 4 levels up).
setlocal
set "PY=%~dp0..\..\..\..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m PyInstaller --version >nul 2>&1 || "%PY%" -m pip install pyinstaller || exit /b 1
pushd "%TEMP%"
"%PY%" -m PyInstaller --noconfirm --onefile --windowed --name TkHello --distpath "%~dp0dist" --workpath "%TEMP%\tkhello_build" --specpath "%TEMP%\tkhello_build" "%~dp0source\tkhello.py" || (popd & exit /b 1)
popd
echo Built %~dp0dist\TkHello.exe
echo Import it again with File ^> Import ^> Program (.exe / .dll)... or:
echo    python ..\reimport.py "%~dp0dist\TkHello.exe" "%~dp0Reimported" python-tk
