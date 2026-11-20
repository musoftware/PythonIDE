@echo off
rem Downloads the WordPress core files (wp-admin, wp-includes, default themes) this sample leaves out of git.
cd /d "%~dp0"
set PY=%~dp0..\..\..\..\..\..\..\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
"%PY%" get_wordpress_core.py %*
pause
